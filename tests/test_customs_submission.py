import asyncio
import json
import sys
import types
from pathlib import Path

from app.llm_settings_store import normalize_llm_settings
from app.template_store import normalize_templates
from fastapi.testclient import TestClient


def test_build_submission_draft_maps_header_and_detail_fields():
    from app.customs_submission import build_submission_draft

    payload = {
        "detected": {
            "主提单号": "MBL001",
            "客户名称": "嘉盛",
            "总价格": "1000",
            "商品明细": [
                {
                    "料号": "P-01",
                    "原产国": "JP",
                    "数量": "10",
                    "良品数量": "9",
                    "总价": "900",
                    "单价": "90",
                }
            ],
        }
    }
    template = {
        "customs_mapping": {
            "header": {
                "主提单号": "Mawb",
                "客户名称": "CustomerName",
                "总价格": "TotalPrice",
            },
            "detail": {
                "料号": "ItemCode",
                "原产国": "ItemOrigin",
                "数量": "ItemQuantity",
                "良品数量": "ItemGoodQuantity",
                "总价": "ItemPrice",
                "单价": "ItemUnitPrice",
            },
        }
    }

    draft = build_submission_draft(response_payload=payload, template=template)

    assert draft["header"]["Mawb"] == "MBL001"
    assert draft["header"]["Hawb"] == "-1"
    assert draft["header"]["CustomerName"] == "嘉盛"
    assert draft["header"]["TotalPrice"] == "1000"
    assert draft["details"][0]["ItemCode"] == "P-01"


def test_submit_to_customs_site_routes_to_playwright_engine(monkeypatch):
    from app.customs_browser import submit_to_customs_site

    fake_module = types.SimpleNamespace(
        submit_to_customs_site_with_playwright=lambda draft, credentials: {
            "ok": True,
            "message": "playwright ok",
            "declaration_no": "IB-PLAY-1",
            "submit_engine": "playwright",
        }
    )
    monkeypatch.setitem(sys.modules, "app.customs_playwright", fake_module)

    result = submit_to_customs_site(
        {"header": {}, "details": []},
        {"site_url": "https://vatest.carsem.com.cn", "username": "u", "password": "p"},
        "playwright",
    )

    assert result["submit_engine"] == "playwright"
    assert result["declaration_no"] == "IB-PLAY-1"


def test_submit_to_customs_site_reports_playwright_unavailable(monkeypatch):
    from app.customs_browser import submit_to_customs_site

    monkeypatch.setitem(sys.modules, "app.customs_playwright", None)

    try:
        submit_to_customs_site(
            {"header": {}, "details": []},
            {"site_url": "https://vatest.carsem.com.cn", "username": "u", "password": "p"},
            "playwright",
        )
    except RuntimeError as exc:
        assert "playwright_unavailable" in str(exc)
    else:
        raise AssertionError("expected playwright mode to fail when module is unavailable")


def test_build_submission_draft_uses_aliases_when_template_mapping_missing():
    from app.customs_submission import build_submission_draft

    payload = {
        "detected": {
            "主提运单号": "MBL002",
            "客户": "Carsem",
            "商品明细": [
                {
                    "商品料号": "X1",
                    "原产国": "MY",
                    "总价": "50",
                    "单价": "5",
                    "总数量": "10",
                    "良品数量": "10",
                }
            ],
        }
    }

    draft = build_submission_draft(response_payload=payload, template={})

    assert draft["header"]["Mawb"] == "MBL002"
    assert draft["header"]["CustomerName"] == "Carsem"
    assert draft["details"][0]["ItemCode"] == "X1"


def test_build_submission_draft_prefers_shippers_name_for_customer_name():
    from app.customs_submission import build_submission_draft

    payload = {
        "detected": {
            "Shipper's Name": "STMICROELECTRONICS PTE LTD",
            "客户名称": "CARSEM",
            "主提单号": "MBL003",
        }
    }

    draft = build_submission_draft(response_payload=payload, template={})

    assert draft["header"]["CustomerName"] == "STMICROELECTRONICS PTE LTD"


def test_build_submission_draft_prefers_llm_submission_output():
    from app.customs_submission import build_submission_draft

    payload = {
        "detected": {
            "主提单号": "MBL-FALLBACK",
            "客户名称": "Fallback 客户",
        }
    }
    llm_output = {
        "header": {
            "Mawb": "MBL-LLM-001",
            "CustomerName": "LLM 客户",
            "TradeType": "FOB",
        },
        "details": [
            {
                "ItemCode": "LLM-ITEM-01",
                "ItemOrigin": "CN",
                "ItemQuantity": "2",
                "ItemGoodQuantity": "2",
                "ItemPrice": "10",
                "ItemUnitPrice": "5",
            }
        ],
        "meta": {
            "mapping_notes": "由大模型直接生成报关草稿",
        },
    }

    draft = build_submission_draft(response_payload=payload, template={}, llm_output=llm_output)

    assert draft["header"]["Mawb"] == "MBL-LLM-001"
    assert draft["header"]["Hawb"] == "-1"
    assert draft["header"]["CustomerName"] == "LLM 客户"
    assert draft["details"][0]["ItemCode"] == "LLM-ITEM-01"
    assert draft["meta"]["mapping_source"] == "llm"


def test_build_submission_draft_strips_spaces_from_mawb_and_hawb():
    from app.customs_submission import build_submission_draft

    draft = build_submission_draft(
        response_payload={"detected": {}},
        template={},
        llm_output={
            "header": {
                "Mawb": " MBL 00 1 ",
                "Hawb": " HBL  00 2 ",
            }
        },
    )

    assert draft["header"]["Mawb"] == "MBL001"
    assert draft["header"]["Hawb"] == "HBL002"


def test_build_submission_draft_fills_missing_fields_with_default_text():
    from app.customs_submission import build_submission_draft

    draft = build_submission_draft(
        response_payload={
            "detected": {
                "客户名称": "嘉盛",
            }
        },
        template={},
    )

    assert draft["header"]["Mawb"] == "-1"
    assert draft["header"]["Hawb"] == "-1"
    assert draft["header"]["CustomerName"] == "嘉盛"
    assert draft["header"]["TradeType"] == "-1"
    assert draft["details"] == [
        {
            "ItemCode": "-1",
            "ItemOrigin": "-1",
            "ItemQuantity": "-1",
            "ItemGoodQuantity": "-1",
            "ItemPrice": "-1",
            "ItemUnitPrice": "-1",
        }
    ]


def test_build_submission_draft_normalizes_numeric_fields_for_site_format():
    from app.customs_submission import build_submission_draft

    draft = build_submission_draft(
        response_payload={
            "detected": {
                "主提单号": "MBL004",
                "Shipper's Name": "STMICROELECTRONICS PTE LTD",
                "商品明细": [
                    {
                        "数量": "1 EA",
                        "总价": "10.5 USD",
                        "单价": "10.5 USD/EA",
                    }
                ],
                "Gross Weight": "2.0 K",
                "Net Wt.": "0.19 KG",
                "Summary Quantity": "287111 EA",
                "Summary Value": "4880.89 USD",
            }
        },
        template={},
        llm_output={
            "header": {
                "Mawb": "MBL004",
                "CustomerName": "STMICROELECTRONICS PTE LTD",
                "TradeType": "DAP",
                "OriginCountry": "SINGAPORE",
                "GrossWeight": "2.0 K",
                "NetWeight": "0.19 KG",
                "TotalQuantity": "287111 EA",
                "TotalPrice": "4880.89 USD",
            },
            "details": [
                {
                    "ItemCode": "A1",
                    "ItemOrigin": "SINGAPORE",
                    "ItemQuantity": "1 EA",
                    "ItemGoodQuantity": "-1",
                    "ItemPrice": "10.5 USD",
                    "ItemUnitPrice": "10.5 USD/EA",
                }
            ],
        },
    )

    assert draft["header"]["GrossWeight"] == "2.0"
    assert draft["header"]["NetWeight"] == "0.19"
    assert draft["header"]["TotalQuantity"] == "287111"
    assert draft["header"]["TotalPrice"] == "4880.89"
    assert draft["details"][0]["ItemQuantity"] == "1"
    assert draft["details"][0]["ItemPrice"] == "10.5"
    assert draft["details"][0]["ItemUnitPrice"] == "10.5"


def test_build_customs_submission_prompt_distinguishes_origin_country_from_dispatch_country():
    from app.main import _build_customs_submission_prompt

    prompt = _build_customs_submission_prompt(
        template={},
        response_payload={"vendor": "STM", "doc_type": "物流通知书"},
    )

    assert "OriginCountry 表示原产国" in prompt
    assert "不能使用启运国、From" in prompt
    assert "如果同时存在原产国和启运国，OriginCountry 只能取原产国" in prompt


def test_build_customs_submission_prompt_maps_trade_type_from_freight_terms_or_incoterm():
    from app.main import _build_customs_submission_prompt

    prompt = _build_customs_submission_prompt(
        template={},
        response_payload={"vendor": "STM", "doc_type": "物流通知书"},
    )

    assert "TradeType 对应单据中的 Freight Terms 或 Incoterm" in prompt
    assert "必须优先从 `Freight Terms`、`Incoterm` 或 `Incoterms` 提取" in prompt


def test_build_customs_submission_prompt_maps_total_sheets_from_package_count():
    from app.main import _build_customs_submission_prompt

    prompt = _build_customs_submission_prompt(
        template={},
        response_payload={"vendor": "STM", "doc_type": "物流通知书"},
    )

    assert "TotalQuantity 对应总数量" in prompt
    assert "必须优先从 `Qty`、`QTY` 或 `Summary Quantity` 提取" in prompt
    assert "GoodQuantity 对应良品总数量" in prompt
    assert "必须优先从 `Gross Qty` 或 `Summary Gross Qty` 提取" in prompt
    assert "TotalSheets 对应总片数" in prompt
    assert "必须优先从 `Die Qty`、`WaferQty`、`Wafer Qty` 或 `Summary WaferQty` 提取" in prompt


def test_build_customs_submission_prompt_maps_quantity_from_no_of_process_rcp():
    from app.main import _build_customs_submission_prompt

    prompt = _build_customs_submission_prompt(
        template={},
        response_payload={"vendor": "STM", "doc_type": "物流通知书"},
    )

    assert "Quantity 对应件数" in prompt
    assert "必须优先从 `No. of Process RCP` 提取" in prompt


def test_build_customs_submission_prompt_requests_packet_structures():
    from app.main import _build_customs_submission_prompt

    prompt = _build_customs_submission_prompt(
        template={},
        response_payload={"vendor": "Samsung", "doc_type": "报关单"},
    )

    assert "invoice_lines" in prompt
    assert "packing_lines" in prompt
    assert "header_candidates" in prompt
    assert "商品明细按发票原始商品行生成" in prompt
    assert "箱单按 ITEM + P/O No + SAMSUNG P/N 汇总校验" in prompt


def test_build_submission_draft_maps_trade_type_from_freight_terms():
    from app.customs_submission import build_submission_draft

    draft = build_submission_draft(
        response_payload={
            "detected": {
                "Freight Terms": "FOB",
            }
        },
        template={},
    )

    assert draft["header"]["TradeType"] == "FOB"


def test_build_submission_draft_maps_quantity_from_no_of_process_rcp():
    from app.customs_submission import build_submission_draft

    draft = build_submission_draft(
        response_payload={
            "detected": {
                "No. of Process RCP": "24",
            }
        },
        template={},
    )

    assert draft["header"]["Quantity"] == "24"


def test_build_submission_draft_maps_total_sheets_from_package_count():
    from app.customs_submission import build_submission_draft

    draft = build_submission_draft(
        response_payload={
            "detected": {
                "Die Qty": "12",
            }
        },
        template={},
    )

    assert draft["header"]["TotalSheets"] == "12"


def test_build_submission_draft_maps_total_quantity_from_qty():
    from app.customs_submission import build_submission_draft

    draft = build_submission_draft(
        response_payload={
            "detected": {
                "Qty": "200",
            }
        },
        template={},
    )

    assert draft["header"]["TotalQuantity"] == "200"


def test_build_submission_draft_maps_good_quantity_from_gross_qty():
    from app.customs_submission import build_submission_draft

    draft = build_submission_draft(
        response_payload={
            "detected": {
                "Gross Qty": "180",
            }
        },
        template={},
    )

    assert draft["header"]["GoodQuantity"] == "180"


def test_build_submission_draft_prefers_detected_header_quantities_over_llm_values():
    from app.customs_submission import build_submission_draft

    draft = build_submission_draft(
        response_payload={
            "detected": {
                "Summary Quantity": "300",
                "Summary Gross Qty": "280",
                "Summary WaferQty": "200",
            }
        },
        template={},
        llm_output={
            "header": {
                "TotalQuantity": "100",
                "GoodQuantity": "90",
                "TotalSheets": "100",
            }
        },
    )

    assert draft["header"]["TotalQuantity"] == "300"
    assert draft["header"]["GoodQuantity"] == "280"
    assert draft["header"]["TotalSheets"] == "200"


def test_build_submission_draft_prefers_origin_country_over_dispatch_country():
    from app.customs_submission import build_submission_draft

    draft = build_submission_draft(
        response_payload={
            "detected": {
                "原产国": "SG",
                "Country（启运国/From）": "MY",
            }
        },
        template={},
        llm_output={
            "header": {
                "OriginCountry": "MY",
            }
        },
    )

    assert draft["header"]["OriginCountry"] == "SG"


def test_build_submission_draft_swaps_header_quantity_fields_when_good_quantity_is_larger():
    from app.customs_submission import build_submission_draft

    draft = build_submission_draft(
        response_payload={"detected": {}},
        template={},
        llm_output={
            "header": {
                "TotalQuantity": "10",
                "GoodQuantity": "12",
            }
        },
    )

    assert draft["header"]["TotalQuantity"] == "12"
    assert draft["header"]["GoodQuantity"] == "10"


def test_build_submission_draft_swaps_detail_quantity_fields_when_good_quantity_is_larger():
    from app.customs_submission import build_submission_draft

    draft = build_submission_draft(
        response_payload={"detected": {}},
        template={},
        llm_output={
            "details": [
                {
                    "ItemQuantity": "3",
                    "ItemGoodQuantity": "5",
                }
            ]
        },
    )

    assert draft["details"][0]["ItemQuantity"] == "5"
    assert draft["details"][0]["ItemGoodQuantity"] == "3"


def test_build_submission_draft_does_not_swap_quantity_fields_for_placeholder_values():
    from app.customs_submission import build_submission_draft

    draft = build_submission_draft(
        response_payload={"detected": {}},
        template={},
        llm_output={
            "header": {
                "TotalQuantity": "-1",
                "GoodQuantity": "5",
            }
        },
    )

    assert draft["header"]["TotalQuantity"] == "-1"
    assert draft["header"]["GoodQuantity"] == "5"


def test_submit_form_with_page_actions_prefers_clickable_submit_button():
    from app import customs_playwright as customs_playwright_mod

    class FakeLocator:
        def __init__(self, exists: bool = False):
            self.exists = exists
            self.clicked = False
            self.evaluated = []

        def first(self):
            return self

        def count(self):
            return 1 if self.exists else 0

        def click(self):
            self.clicked = True

        def evaluate(self, script):
            self.evaluated.append(script)

    class FakePage:
        def __init__(self):
            self.submit_button = FakeLocator(True)
            self.form = FakeLocator(True)
            self.seen = []

        def locator(self, selector):
            self.seen.append(selector)
            if selector == "#btnSave":
                return self.submit_button
            return FakeLocator(False)

    page = FakePage()

    customs_playwright_mod._submit_form_with_page_actions(page)

    assert page.submit_button.clicked is True


def test_submit_form_with_page_actions_falls_back_to_form_submit():
    from app import customs_playwright as customs_playwright_mod

    class FakeLocator:
        def __init__(self, exists: bool = False):
            self.exists = exists
            self.clicked = False
            self.evaluated = []

        def first(self):
            return self

        def count(self):
            return 1 if self.exists else 0

        def click(self):
            self.clicked = True

        def evaluate(self, script):
            self.evaluated.append(script)

    class FakePage:
        def __init__(self):
            self.form = FakeLocator(True)

        def locator(self, selector):
            if selector == "#dataForm":
                return self.form
            return FakeLocator(False)

    page = FakePage()

    customs_playwright_mod._submit_form_with_page_actions(page)

    assert page.form.evaluated == ["(form) => { if (form.requestSubmit) { form.requestSubmit(); } else { form.submit(); } }"]


def test_normalize_templates_keeps_customs_mapping():
    items = normalize_templates(
        {
            "items": [
                {
                    "vendor": "嘉盛半导体",
                    "doc_type": "到货单",
                    "llm_prompt": "{}",
                    "customs_mapping": {
                        "header": {"主提单号": "Mawb"},
                        "detail": {"料号": "ItemCode"},
                    },
                }
            ]
        }
    )

    target = next(item for item in items if item["vendor"] == "嘉盛半导体" and item["doc_type"] == "到货单")
    assert target["customs_mapping"]["header"]["主提单号"] == "Mawb"


def test_normalize_templates_accepts_customs_declaration_doc_type():
    items = normalize_templates(
        {
            "items": [
                {
                    "vendor": "嘉盛半导体",
                    "doc_type": "报关单",
                    "llm_prompt": "{}",
                }
            ]
        }
    )

    target = next(item for item in items if item["vendor"] == "嘉盛半导体")
    assert target["doc_type"] == "报关单"


def test_normalize_templates_default_set_includes_remote_logistics_templates():
    items = normalize_templates(None)
    pairs = {(item["vendor"], item["doc_type"]) for item in items}

    assert ("通用模板", "到货单") in pairs
    assert ("通用模板", "发票") in pairs
    assert ("通用模板", "报关单") in pairs
    assert ("UPI  Semi", "物流通知书") in pairs
    assert ("STMicroelectronics", "物流通知书") in pairs
    assert ("TI", "物流通知书") in pairs


def test_normalize_templates_adds_common_baseline_to_legacy_vendor_only_store():
    items = normalize_templates(
        {
            "items": [
                {
                    "vendor": "Samsung",
                    "doc_type": "报关单",
                    "llm_prompt": "{}",
                }
            ]
        }
    )
    pairs = {(item["vendor"], item["doc_type"]) for item in items}

    assert ("Samsung", "报关单") in pairs
    assert ("通用模板", "到货单") in pairs
    assert ("通用模板", "发票") in pairs


def test_normalize_llm_settings_keeps_auto_mode_enabled():
    settings = normalize_llm_settings(
        {
            "active_id": "cfg-1",
            "auto_mode_enabled": True,
            "items": [
                {
                    "id": "cfg-1",
                    "name": "Gemini 默认",
                    "provider": "gemini",
                    "llm_base_url": "https://example.com/v1",
                    "llm_model": "demo-model",
                    "llm_api_key": "secret",
                }
            ],
        }
    )

    assert settings["auto_mode_enabled"] is True


def test_normalize_llm_settings_supports_customs_submit_mode():
    settings = normalize_llm_settings(
        {
            "active_id": "cfg-1",
            "auto_mode_enabled": True,
            "customs_submit_mode": "playwright",
            "items": [
                {
                    "id": "cfg-1",
                    "name": "cfg",
                    "provider": "gemini",
                    "llm_base_url": "https://example.com/v1",
                    "llm_model": "demo-model",
                    "llm_api_key": "secret",
                }
            ],
        }
    )

    assert settings["customs_submit_mode"] == "playwright"

    invalid = normalize_llm_settings({"customs_submit_mode": "bad-mode"})
    assert invalid["customs_submit_mode"] == "http"


def test_normalize_llm_settings_rejects_local_agent_mode_and_drops_agent_id():
    settings = normalize_llm_settings(
        {
            "active_id": "cfg-1",
            "auto_mode_enabled": True,
            "customs_submit_mode": "local_agent",
            "local_agent_id": "sz-ops-01",
            "items": [
                {
                    "id": "cfg-1",
                    "name": "cfg",
                    "provider": "gemini",
                    "llm_base_url": "https://example.com/v1",
                    "llm_model": "demo-model",
                    "llm_api_key": "secret",
                }
            ],
        }
    )

    assert settings["customs_submit_mode"] == "http"
    assert "local_agent_id" not in settings

    invalid = normalize_llm_settings({"customs_submit_mode": "local_agent", "local_agent_id": 123})
    assert invalid["customs_submit_mode"] == "http"
    assert "local_agent_id" not in invalid


def test_normalize_llm_settings_accepts_bailian_provider():
    settings = normalize_llm_settings(
        {
            "active_id": "cfg-1",
            "items": [
                {
                    "id": "cfg-1",
                    "name": "百炼 Qwen",
                    "provider": "bailian",
                    "llm_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                    "llm_model": "qwen3.5-plus",
                    "llm_api_key": "secret",
                }
            ],
        }
    )

    assert settings["items"][0]["provider"] == "bailian"
    assert settings["items"][0]["llm_base_url"] == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert settings["items"][0]["llm_model"] == "qwen3.5-plus"


def test_attach_submission_draft_writes_submission_into_response_payload():
    from app.customs_submission import attach_submission_draft

    payload = {"detected": {"主提单号": "MBL001"}}
    draft = {"header": {}, "details": [], "meta": {}}

    updated = attach_submission_draft(payload, draft)

    assert "submission" in updated
    assert updated["submission"] == draft
    assert "submission" not in payload


def test_validate_submission_draft_requires_header_and_detail_fields():
    from app.customs_submission import validate_submission_draft

    draft = {
        "header": {"Mawb": "", "CustomerName": ""},
        "details": [],
        "meta": {},
    }

    result = validate_submission_draft(draft)

    assert result["ok"] is True
    assert result["required_missing"] == []


def test_submission_draft_api_generates_and_persists_draft(tmp_path, monkeypatch):
    from app.history_store import save_history_record
    from app.main import app
    import app.main as main_mod

    monkeypatch.setattr(main_mod, "project_root", tmp_path)
    monkeypatch.setattr(
        main_mod,
        "run_llm_extract",
        lambda **kwargs: {
            "detected": {
                "header": {
                    "Mawb": "LLM-MBL-100",
                    "CustomerName": "LLM 嘉盛",
                    "TradeType": "FOB",
                },
                "details": [
                    {
                        "ItemCode": "LLM-A1",
                        "ItemOrigin": "CN",
                        "ItemQuantity": "10",
                        "ItemGoodQuantity": "10",
                        "ItemPrice": "20",
                        "ItemUnitPrice": "2",
                    }
                ],
                "meta": {"mapping_notes": "llm generated"},
            },
            "content": "{}",
            "model": "fake-model",
            "endpoint": "fake-endpoint",
        },
    )

    history = save_history_record(
        project_root=tmp_path,
        response_payload={
            "filename": "demo.pdf",
            "vendor": "嘉盛半导体",
            "doc_type": "到货单",
            "detected": {
                "主提单号": "MBL100",
                "客户名称": "嘉盛",
                "商品明细": [{"料号": "A1", "原产国": "CN", "数量": "10", "良品数量": "10", "总价": "20", "单价": "2"}],
            },
        },
        zip_bytes=None,
    )

    client = TestClient(app)
    response = client.post(f"/api/history/{history['id']}/submission-draft")

    assert response.status_code == 200
    payload = response.json()
    assert payload["submission"]["header"]["Mawb"] == "LLM-MBL-100"
    assert payload["submission"]["details"][0]["ItemCode"] == "LLM-A1"
    assert payload["submission"]["meta"]["mapping_source"] == "llm"


def test_submission_draft_api_regenerates_existing_submission_with_llm(tmp_path, monkeypatch):
    from app.history_store import save_history_record
    from app.main import app
    import app.main as main_mod

    monkeypatch.setattr(main_mod, "project_root", tmp_path)
    monkeypatch.setattr(
        main_mod,
        "run_llm_extract",
        lambda **kwargs: {
            "detected": {
                "header": {
                    "Mawb": "REGEN-MBL",
                    "CustomerName": "重新生成客户",
                },
                "details": [
                    {
                        "ItemCode": "REGEN-1",
                        "ItemOrigin": "CN",
                        "ItemQuantity": "2",
                        "ItemGoodQuantity": "2",
                        "ItemPrice": "6",
                        "ItemUnitPrice": "3",
                    }
                ],
                "meta": {"mapping_notes": "regenerated"},
            },
            "content": "{}",
            "model": "fake-model",
            "endpoint": "fake-endpoint",
        },
    )

    history = save_history_record(
        project_root=tmp_path,
        response_payload={
            "filename": "demo.pdf",
            "vendor": "嘉盛半导体",
            "doc_type": "到货单",
            "detected": {"主提单号": "MBL100"},
            "submission": {
                "target": "vatest.carsem.com.cn",
                "header": {"Mawb": "CACHED-MBL", "CustomerName": "缓存客户"},
                "details": [{"ItemCode": "CACHE-1", "ItemOrigin": "CN", "ItemQuantity": "1", "ItemGoodQuantity": "1", "ItemPrice": "1", "ItemUnitPrice": "1"}],
                "meta": {"mapping_source": "llm", "submit_status": "idle"},
            },
        },
        zip_bytes=None,
    )

    client = TestClient(app)
    response = client.post(f"/api/history/{history['id']}/submission-draft")

    assert response.status_code == 200
    payload = response.json()
    assert payload["submission"]["header"]["Mawb"] == "REGEN-MBL"
    assert payload["submission"]["header"]["CustomerName"] == "重新生成客户"
    assert payload["submission"]["details"][0]["ItemCode"] == "REGEN-1"


def test_submission_draft_api_saves_user_edit(tmp_path, monkeypatch):
    from app.history_store import save_history_record
    from app.main import app
    import app.main as main_mod

    monkeypatch.setattr(main_mod, "project_root", tmp_path)

    history = save_history_record(
        project_root=tmp_path,
        response_payload={
            "filename": "demo.pdf",
            "vendor": "嘉盛半导体",
            "doc_type": "到货单",
            "detected": {},
            "submission": {
                "target": "vatest.carsem.com.cn",
                "header": {"Mawb": "OLD", "CustomerName": "旧客户"},
                "details": [{"ItemCode": "OLD"}],
                "meta": {},
            },
        },
        zip_bytes=None,
    )

    client = TestClient(app)
    response = client.put(
        f"/api/history/{history['id']}/submission-draft",
        json={
            "header": {"Mawb": "NEW", "CustomerName": "新客户"},
            "details": [{"ItemCode": "A9", "ItemOrigin": "CN", "ItemQuantity": "1", "ItemGoodQuantity": "1", "ItemPrice": "8", "ItemUnitPrice": "8"}],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["submission"]["header"]["Mawb"] == "NEW"
    assert payload["submission"]["details"][0]["ItemCode"] == "A9"


def test_submit_customs_api_allows_placeholder_minus_one_draft_to_submit(tmp_path, monkeypatch):
    from app.history_store import save_history_record
    from app.main import app
    import app.main as main_mod

    monkeypatch.setattr(main_mod, "project_root", tmp_path)
    monkeypatch.setattr(
        main_mod,
        "submit_to_customs_site",
        lambda draft, credentials: {"ok": True, "message": "submitted", "declaration_no": "DEC-BLANK-1"},
    )
    history = save_history_record(
        project_root=tmp_path,
        response_payload={
            "filename": "demo.pdf",
            "vendor": "嘉盛半导体",
            "doc_type": "到货单",
            "detected": {},
            "submission": {
                "target": "vatest.carsem.com.cn",
                "header": {"Mawb": "", "CustomerName": ""},
                "details": [],
                "meta": {},
            },
        },
        zip_bytes=None,
    )

    client = TestClient(app)
    response = client.post(f"/api/history/{history['id']}/submit-customs")

    assert response.status_code == 200
    assert response.json()["status"] == "queued"


def test_build_customs_submission_prompt_requires_customer_name_to_use_shipper():
    import app.main as main_mod

    prompt = main_mod._build_customs_submission_prompt(
        template={"customs_mapping": {}},
        response_payload={"doc_type": "物流通知书", "vendor": "STMicroelectronics"},
    )

    assert "CustomerName 表示发货客户" in prompt
    assert "Shipper's Name" in prompt
    assert "不能取 Consignee" in prompt


def test_flatten_submission_payload_maps_mawb_and_hawb_to_site_fields():
    from app.customs_browser import _flatten_submission_payload

    payload = _flatten_submission_payload(
        {
            "header": {
                "Mawb": "MBL-001",
                "Hawb": "HBL-002",
                "CustomerName": "嘉盛",
            },
            "details": [],
        },
        "DEC-1",
    )

    assert ("MainBLNo", "MBL-001") in payload
    assert ("SubBLNo", "HBL-002") in payload


def test_flatten_submission_payload_strips_spaces_from_mawb_and_hawb():
    from app.customs_browser import _flatten_submission_payload

    payload = _flatten_submission_payload(
        {
            "header": {
                "Mawb": " MB L-0 01 ",
                "Hawb": " HB L-0 02 ",
                "CustomerName": "嘉盛",
            },
            "details": [],
        },
        "DEC-1",
    )

    assert ("MainBLNo", "MBL-001") in payload
    assert ("SubBLNo", "HBL-002") in payload


def test_flatten_submission_payload_cleans_default_text_from_numeric_fields():
    from app.customs_browser import _flatten_submission_payload

    payload = _flatten_submission_payload(
        {
            "header": {
                "Mawb": "MBL-001",
                "Hawb": "HBL-002",
                "CustomerName": "嘉盛",
                "Quantity": "-1",
                "GrossWeight": "-1",
                "NetWeight": "-1",
                "TotalSheets": "-1",
                "TotalQuantity": "-1",
                "GoodQuantity": "-1",
                "TotalPrice": "-1",
            },
            "details": [
                {
                    "ItemCode": "A1",
                    "ItemOrigin": "CN",
                    "ItemQuantity": "-1",
                    "ItemGoodQuantity": "-1",
                    "ItemPrice": "-1",
                    "ItemUnitPrice": "-1",
                }
            ],
        },
        "DEC-2",
    )

    assert ("Quantity", "-1") in payload
    assert ("GrossWeight", "-1") in payload
    assert ("NetWeight", "-1") in payload
    assert ("TotalSheets", "-1") in payload
    assert ("TotalQuantity", "-1") in payload
    assert ("GoodQuantity", "-1") in payload
    assert ("TotalPrice", "-1") in payload
    assert ("ItemQuantity", "-1") in payload
    assert ("ItemGoodQuantity", "-1") in payload
    assert ("ItemPrice", "-1") in payload
    assert ("ItemUnitPrice", "-1") in payload


def test_flatten_submission_payload_strips_units_from_numeric_fields():
    from app.customs_browser import _flatten_submission_payload

    payload = _flatten_submission_payload(
        {
            "header": {
                "Mawb": "MBL-001",
                "CustomerName": "嘉盛",
                "TradeType": "FOB",
                "OriginCountry": "SG",
                "Quantity": "1 CTN",
                "GrossWeight": "2.0 K",
                "NetWeight": "0.19 KG",
                "TotalSheets": "2 sheets",
                "TotalQuantity": "287111 EA",
                "GoodQuantity": "380325 PCS",
                "TotalPrice": "4880.89 USD",
            },
            "details": [
                {
                    "ItemCode": "A1",
                    "ItemOrigin": "SG",
                    "ItemQuantity": "1 EA",
                    "ItemGoodQuantity": "1 EA",
                    "ItemPrice": "10.5 USD",
                    "ItemUnitPrice": "10.5 USD/EA",
                }
            ],
        },
        "DEC-3",
    )

    assert ("Quantity", "1") in payload
    assert ("GrossWeight", "2.0") in payload
    assert ("NetWeight", "0.19") in payload
    assert ("TotalSheets", "2") in payload
    assert ("TotalQuantity", "287111") in payload
    assert ("GoodQuantity", "380325") in payload
    assert ("TotalPrice", "4880.89") in payload
    assert ("ItemQuantity", "1") in payload
    assert ("ItemGoodQuantity", "1") in payload
    assert ("ItemPrice", "10.5") in payload
    assert ("ItemUnitPrice", "10.5") in payload


def test_build_customs_submission_context_returns_compact_json():
    import app.main as main_mod

    context = main_mod._build_customs_submission_context(
        {
            "vendor": "嘉盛半导体",
            "doc_type": "到货单",
            "detected": {"主提单号": "MBL-1"},
            "fallback_detected": {"客户名称": "Carsem"},
            "region_detected": {},
            "preview": "X" * 20000,
        }
    )

    parsed = json.loads(context)
    assert parsed["vendor"] == "嘉盛半导体"
    assert parsed["detected"]["主提单号"] == "MBL-1"
    assert len(parsed["preview"]) == 4000


def test_submit_customs_api_starts_task_for_valid_draft(tmp_path, monkeypatch):
    from app.history_store import save_history_record
    from app.main import app
    import app.main as main_mod

    monkeypatch.setattr(main_mod, "project_root", tmp_path)
    monkeypatch.setattr(
        main_mod,
        "submit_to_customs_site",
        lambda draft, credentials: {"ok": True, "message": "submitted", "declaration_no": "DEC001"},
    )

    history = save_history_record(
        project_root=tmp_path,
        response_payload={
            "filename": "demo.pdf",
            "vendor": "嘉盛半导体",
            "doc_type": "到货单",
            "detected": {},
            "submission": {
                "target": "vatest.carsem.com.cn",
                "header": {
                    "Mawb": "MBL1",
                    "CustomerName": "客户A",
                    "TradeType": "FOB",
                    "OriginCountry": "CN",
                    "Quantity": "1",
                    "GrossWeight": "1",
                    "NetWeight": "1",
                    "TotalSheets": "1",
                    "TotalQuantity": "1",
                    "GoodQuantity": "1",
                    "TotalPrice": "10",
                },
                "details": [
                    {
                        "ItemCode": "A1",
                        "ItemOrigin": "CN",
                        "ItemQuantity": "1",
                        "ItemGoodQuantity": "1",
                        "ItemPrice": "10",
                        "ItemUnitPrice": "10",
                    }
                ],
                "meta": {},
            },
        },
        zip_bytes=None,
    )

    client = TestClient(app)
    response = client.post(f"/api/history/{history['id']}/submit-customs")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "queued"
    task_detail = client.get(f"/api/customs-submit/tasks/{payload['task_id']}")
    assert task_detail.status_code == 200


def test_run_extract_task_auto_mode_continues_to_submission(tmp_path, monkeypatch):
    import app.main as main_mod

    monkeypatch.setattr(main_mod, "project_root", tmp_path)
    monkeypatch.setattr(
        main_mod,
        "load_llm_settings",
        lambda project_root: {
            "active_id": "cfg-1",
            "auto_mode_enabled": True,
            "customs_submit_mode": "playwright",
            "items": [
                {
                    "id": "cfg-1",
                    "name": "cfg",
                    "provider": "gemini",
                    "llm_base_url": "https://example.com/v1",
                    "llm_model": "demo-model",
                    "llm_api_key": "secret",
                }
            ],
        },
    )
    monkeypatch.setattr(
        main_mod,
        "_build_extract_payload",
        lambda **kwargs: {
            "filename": "auto.pdf",
            "vendor": "嘉盛半导体",
            "doc_type": "到货单",
            "detected": {"主提单号": "AUTO-MBL-1"},
            "history": {"id": "history-1"},
            "fallback_used": False,
            "model_version": "vlm",
        },
    )
    monkeypatch.setattr(
        main_mod,
        "_generate_submission_draft_with_llm",
        lambda response_payload, template: {
            "target": "vatest.carsem.com.cn",
            "header": {"Mawb": "AUTO-MBL-1", "CustomerName": "AUTO"},
            "details": [
                {
                    "ItemCode": "A1",
                    "ItemOrigin": "CN",
                    "ItemQuantity": "1",
                    "ItemGoodQuantity": "1",
                    "ItemPrice": "1",
                    "ItemUnitPrice": "1",
                }
            ],
            "meta": {"required_missing": ["TradeType"], "mapping_source": "llm"},
        },
    )
    monkeypatch.setattr(
        main_mod,
        "load_history_record",
        lambda project_root, record_id: {
            "id": record_id,
            "response": {
                "filename": "auto.pdf",
                "vendor": "嘉盛半导体",
                "doc_type": "到货单",
                "detected": {"主提单号": "AUTO-MBL-1"},
            },
        },
    )
    monkeypatch.setattr(main_mod, "update_history_record_response", lambda **kwargs: {"id": "history-1"})
    monkeypatch.setattr(main_mod, "_resolve_template_for_history", lambda detail: {})
    monkeypatch.setattr(
        main_mod,
        "submit_to_customs_site",
        lambda draft, credentials, mode="http": {
            "ok": True,
            "message": "自动填报完成",
            "declaration_no": "DEC-AUTO-1",
            "submit_engine": mode,
        },
    )

    async def run_case():
        async with main_mod._EXTRACT_TASKS_LOCK:
            main_mod._EXTRACT_TASKS.clear()
            main_mod._EXTRACT_TASKS["task-auto"] = {
                "id": "task-auto",
                "status": "queued",
                "stage": "queued",
                "progress": 0,
                "message": "等待调度",
                "error": "",
                "created_at": main_mod._utc_now_iso(),
                "updated_at": main_mod._utc_now_iso(),
                "filename": "auto.pdf",
                "vendor": "嘉盛半导体",
                "doc_type": "到货单",
                "result": None,
            }
        await main_mod._run_extract_task(
            "task-auto",
            {
                "file_name": "auto.pdf",
                "file_bytes": b"demo",
                "vendor": "嘉盛半导体",
                "doc_type": "到货单",
                "fields": "",
                "region_rules": "",
                "llm_prompt": "demo",
                "llm_base_url": "",
                "llm_model": "",
                "llm_api_key": "",
                "mineru_model_version": "vlm",
                "backend": "vlm",
                "parse_method": "auto",
                "lang_list": "en",
            },
        )
        return main_mod._EXTRACT_TASKS["task-auto"]

    task = asyncio.run(run_case())
    assert task["status"] == "succeeded"
    assert task["stage"] == "done"
    assert task["result"]["auto_mode_enabled"] is True
    assert task["result"]["auto_mode_status"] == "succeeded"
    assert task["result"]["auto_mode_message"] == "自动填报完成"
    assert task["result"]["submit_engine"] == "playwright"


def test_run_extract_task_auto_mode_marks_task_failed_when_customs_submit_fails(tmp_path, monkeypatch):
    import app.main as main_mod

    monkeypatch.setattr(main_mod, "project_root", tmp_path)
    monkeypatch.setattr(
        main_mod,
        "load_llm_settings",
        lambda project_root: {
            "active_id": "cfg-1",
            "auto_mode_enabled": True,
            "customs_submit_mode": "playwright",
            "items": [
                {
                    "id": "cfg-1",
                    "name": "cfg",
                    "provider": "gemini",
                    "llm_base_url": "https://example.com/v1",
                    "llm_model": "demo-model",
                    "llm_api_key": "secret",
                }
            ],
        },
    )
    monkeypatch.setattr(
        main_mod,
        "_build_extract_payload",
        lambda **kwargs: {
            "filename": "auto-failed.pdf",
            "vendor": "嘉盛半导体",
            "doc_type": "到货单",
            "detected": {"主提单号": "AUTO-MBL-2"},
            "history": {"id": "history-2"},
            "fallback_used": False,
            "model_version": "vlm",
        },
    )
    monkeypatch.setattr(
        main_mod,
        "_generate_submission_draft_with_llm",
        lambda response_payload, template: {
            "target": "vatest.carsem.com.cn",
            "header": {"Mawb": "AUTO-MBL-2", "CustomerName": "AUTO"},
            "details": [
                {
                    "ItemCode": "A2",
                    "ItemOrigin": "CN",
                    "ItemQuantity": "1",
                    "ItemGoodQuantity": "1",
                    "ItemPrice": "1",
                    "ItemUnitPrice": "1",
                }
            ],
            "meta": {"mapping_source": "llm"},
        },
    )
    monkeypatch.setattr(
        main_mod,
        "load_history_record",
        lambda project_root, record_id: {
            "id": record_id,
            "response": {
                "filename": "auto-failed.pdf",
                "vendor": "嘉盛半导体",
                "doc_type": "到货单",
                "detected": {"主提单号": "AUTO-MBL-2"},
            },
        },
    )
    monkeypatch.setattr(main_mod, "_resolve_template_for_history", lambda detail: {})

    updates = []

    def record_update(**kwargs):
        updates.append(kwargs["response_payload"])
        return {"id": "history-2"}

    monkeypatch.setattr(main_mod, "update_history_record_response", record_update)

    def fail_submit(draft, credentials, mode="http"):
        raise RuntimeError(f"submission_rejected:{mode}: 保存失败")

    monkeypatch.setattr(main_mod, "submit_to_customs_site", fail_submit)

    async def run_case():
        async with main_mod._EXTRACT_TASKS_LOCK:
            main_mod._EXTRACT_TASKS.clear()
            main_mod._EXTRACT_TASKS["task-auto-failed"] = {
                "id": "task-auto-failed",
                "status": "queued",
                "stage": "queued",
                "progress": 0,
                "message": "等待调度",
                "error": "",
                "created_at": main_mod._utc_now_iso(),
                "updated_at": main_mod._utc_now_iso(),
                "filename": "auto-failed.pdf",
                "vendor": "嘉盛半导体",
                "doc_type": "到货单",
                "result": None,
            }
        await main_mod._run_extract_task(
            "task-auto-failed",
            {
                "file_name": "auto-failed.pdf",
                "file_bytes": b"demo",
                "vendor": "嘉盛半导体",
                "doc_type": "到货单",
                "fields": "",
                "region_rules": "",
                "llm_prompt": "demo",
                "llm_base_url": "",
                "llm_model": "",
                "llm_api_key": "",
                "mineru_model_version": "vlm",
                "backend": "vlm",
                "parse_method": "auto",
                "lang_list": "en",
            },
        )
        return main_mod._EXTRACT_TASKS["task-auto-failed"]

    task = asyncio.run(run_case())

    assert task["status"] == "failed"
    assert task["stage"] == "failed"
    assert task["error"] == "submission_rejected:playwright: 保存失败"
    assert updates[-1]["submission"]["meta"]["submit_status"] == "failed"
    assert updates[-1]["submission"]["meta"]["submit_message"] == "submission_rejected:playwright: 保存失败"


def test_run_extract_task_auto_mode_persists_success_submission_meta(tmp_path, monkeypatch):
    import app.main as main_mod

    monkeypatch.setattr(main_mod, "project_root", tmp_path)
    monkeypatch.setattr(
        main_mod,
        "load_llm_settings",
        lambda project_root: {
            "active_id": "cfg-1",
            "auto_mode_enabled": True,
            "customs_submit_mode": "playwright",
            "items": [
                {
                    "id": "cfg-1",
                    "name": "cfg",
                    "provider": "gemini",
                    "llm_base_url": "https://example.com/v1",
                    "llm_model": "demo-model",
                    "llm_api_key": "secret",
                }
            ],
        },
    )
    monkeypatch.setattr(
        main_mod,
        "_build_extract_payload",
        lambda **kwargs: {
            "filename": "auto-success.pdf",
            "vendor": "嘉盛半导体",
            "doc_type": "到货单",
            "detected": {"主提单号": "AUTO-MBL-3"},
            "history": {"id": "history-3"},
            "fallback_used": False,
            "model_version": "vlm",
        },
    )
    monkeypatch.setattr(
        main_mod,
        "_generate_submission_draft_with_llm",
        lambda response_payload, template: {
            "target": "vatest.carsem.com.cn",
            "header": {"Mawb": "AUTO-MBL-3", "CustomerName": "AUTO"},
            "details": [
                {
                    "ItemCode": "A3",
                    "ItemOrigin": "CN",
                    "ItemQuantity": "1",
                    "ItemGoodQuantity": "1",
                    "ItemPrice": "1",
                    "ItemUnitPrice": "1",
                }
            ],
            "meta": {"mapping_source": "llm"},
        },
    )
    monkeypatch.setattr(
        main_mod,
        "load_history_record",
        lambda project_root, record_id: {
            "id": record_id,
            "response": {
                "filename": "auto-success.pdf",
                "vendor": "嘉盛半导体",
                "doc_type": "到货单",
                "detected": {"主提单号": "AUTO-MBL-3"},
            },
        },
    )
    monkeypatch.setattr(main_mod, "_resolve_template_for_history", lambda detail: {})

    updates = []

    def record_update(**kwargs):
        updates.append(kwargs["response_payload"])
        return {"id": "history-3"}

    monkeypatch.setattr(main_mod, "update_history_record_response", record_update)
    monkeypatch.setattr(
        main_mod,
        "submit_to_customs_site",
        lambda draft, credentials, mode="http": {
            "ok": True,
            "message": "自动填报完成",
            "declaration_no": "DEC-AUTO-3",
            "submit_engine": mode,
        },
    )

    async def run_case():
        async with main_mod._EXTRACT_TASKS_LOCK:
            main_mod._EXTRACT_TASKS.clear()
            main_mod._EXTRACT_TASKS["task-auto-success"] = {
                "id": "task-auto-success",
                "status": "queued",
                "stage": "queued",
                "progress": 0,
                "message": "等待调度",
                "error": "",
                "created_at": main_mod._utc_now_iso(),
                "updated_at": main_mod._utc_now_iso(),
                "filename": "auto-success.pdf",
                "vendor": "嘉盛半导体",
                "doc_type": "到货单",
                "result": None,
            }
        await main_mod._run_extract_task(
            "task-auto-success",
            {
                "file_name": "auto-success.pdf",
                "file_bytes": b"demo",
                "vendor": "嘉盛半导体",
                "doc_type": "到货单",
                "fields": "",
                "region_rules": "",
                "llm_prompt": "demo",
                "llm_base_url": "",
                "llm_model": "",
                "llm_api_key": "",
                "mineru_model_version": "vlm",
                "backend": "vlm",
                "parse_method": "auto",
                "lang_list": "en",
            },
        )
        return main_mod._EXTRACT_TASKS["task-auto-success"]

    task = asyncio.run(run_case())

    assert task["status"] == "succeeded"
    assert task["result"]["auto_mode_enabled"] is True
    assert task["result"]["auto_mode_status"] == "succeeded"
    assert task["result"]["auto_mode_message"] == "自动填报完成"
    assert task["result"]["submit_engine"] == "playwright"
    assert updates[0]["submission"]["meta"]["submit_status"] == "idle"
    assert updates[-1]["submission"]["meta"]["submit_status"] == "succeeded"
    assert updates[-1]["submission"]["meta"]["submit_message"] == "自动填报完成"
    assert updates[-1]["submission"]["meta"]["submit_engine"] == "playwright"


def test_run_extract_task_manual_mode_stops_after_extract(tmp_path, monkeypatch):
    import app.main as main_mod

    monkeypatch.setattr(main_mod, "project_root", tmp_path)
    monkeypatch.setattr(
        main_mod,
        "load_llm_settings",
        lambda project_root: {
            "active_id": "cfg-1",
            "auto_mode_enabled": False,
            "items": [
                {
                    "id": "cfg-1",
                    "name": "cfg",
                    "provider": "gemini",
                    "llm_base_url": "https://example.com/v1",
                    "llm_model": "demo-model",
                    "llm_api_key": "secret",
                }
            ],
        },
    )
    monkeypatch.setattr(
        main_mod,
        "_build_extract_payload",
        lambda **kwargs: {
            "filename": "manual.pdf",
            "vendor": "嘉盛半导体",
            "doc_type": "到货单",
            "detected": {"主提单号": "MANUAL-MBL-1"},
            "history": {"id": "history-1"},
            "fallback_used": False,
            "model_version": "vlm",
        },
    )
    called = {"mapped": False, "submitted": False}
    monkeypatch.setattr(main_mod, "_generate_submission_draft_with_llm", lambda *args, **kwargs: called.__setitem__("mapped", True))
    monkeypatch.setattr(main_mod, "submit_to_customs_site", lambda *args, **kwargs: called.__setitem__("submitted", True))

    async def run_case():
        async with main_mod._EXTRACT_TASKS_LOCK:
            main_mod._EXTRACT_TASKS.clear()
            main_mod._EXTRACT_TASKS["task-manual"] = {
                "id": "task-manual",
                "status": "queued",
                "stage": "queued",
                "progress": 0,
                "message": "等待调度",
                "error": "",
                "created_at": main_mod._utc_now_iso(),
                "updated_at": main_mod._utc_now_iso(),
                "filename": "manual.pdf",
                "vendor": "嘉盛半导体",
                "doc_type": "到货单",
                "result": None,
            }
        await main_mod._run_extract_task(
            "task-manual",
            {
                "file_name": "manual.pdf",
                "file_bytes": b"demo",
                "vendor": "嘉盛半导体",
                "doc_type": "到货单",
                "fields": "",
                "region_rules": "",
                "llm_prompt": "demo",
                "llm_base_url": "",
                "llm_model": "",
                "llm_api_key": "",
                "mineru_model_version": "vlm",
                "backend": "vlm",
                "parse_method": "auto",
                "lang_list": "en",
            },
        )
        return main_mod._EXTRACT_TASKS["task-manual"]

    task = asyncio.run(run_case())
    assert task["status"] == "succeeded"
    assert task["result"]["auto_mode_enabled"] is False
    assert task["result"]["auto_mode_status"] == "idle"
    assert called["mapped"] is False
    assert called["submitted"] is False


def test_build_extract_payload_defaults_to_mineru_engine(monkeypatch):
    import app.main as main_mod

    calls = {"mineru": 0, "opendataloader": 0}

    monkeypatch.setattr(main_mod, "_resolve_runtime_llm_settings", lambda **kwargs: ("https://example.com/v1", "demo-model", "secret"))
    monkeypatch.setattr(main_mod, "_build_history_preview_assets", lambda **kwargs: [])
    monkeypatch.setattr(main_mod, "save_history_record", lambda **kwargs: {"id": "history-mineru"})
    monkeypatch.setattr(main_mod, "_build_rotation_candidates", lambda **kwargs: [(0, kwargs["file_bytes"])])
    monkeypatch.setattr(main_mod, "_should_try_rotation_retry", lambda *args, **kwargs: False)
    monkeypatch.setattr(main_mod, "_count_detected_hits", lambda detected: len(detected or {}))
    monkeypatch.setattr(main_mod, "_estimate_text_quality", lambda preview: len(str(preview or "")))
    monkeypatch.setattr(
        main_mod,
        "run_llm_extract",
        lambda **kwargs: {
            "detected": {"发票号": "INV-001"},
            "endpoint": kwargs["base_url"],
            "model": kwargs["model"],
            "content": '{"发票号":"INV-001"}',
        },
    )
    monkeypatch.setattr(main_mod, "extract_fields_by_regions", lambda *args, **kwargs: {})

    def fake_mineru(**kwargs):
        calls["mineru"] += 1
        return {
            "text": "Invoice No: INV-001",
            "markdown": "# Invoice\n\nInvoice No: INV-001",
            "json": {"content": "Invoice No: INV-001"},
            "middle_json": {"pages": []},
            "zip_entries": [],
            "zip_size": 0,
        }

    monkeypatch.setattr(main_mod, "run_mineru_and_read_text", fake_mineru)

    def should_not_run(**kwargs):
        calls["opendataloader"] += 1
        raise AssertionError("opendataloader extractor should not be used by default")

    monkeypatch.setattr(main_mod, "run_opendataloader_and_read_text", should_not_run)

    payload = main_mod._build_extract_payload(
        file_name="invoice.png",
        file_bytes=b"demo",
        vendor="Vendor A",
        doc_type="发票",
        fields="发票号",
        region_rules="",
        llm_prompt="提取发票号",
        llm_base_url="",
        llm_model="",
        llm_api_key="",
        mineru_model_version="vlm",
        backend="vlm",
        parse_method="auto",
        lang_list="en",
    )

    assert calls["mineru"] == 1
    assert calls["opendataloader"] == 0
    assert payload["ocr_engine"] == "mineru"
    assert payload["ocr_engine_label"] == "MinerU"
    assert payload["detected"] == {"发票号": "INV-001"}


def test_build_extract_payload_routes_to_opendataloader_engine(monkeypatch):
    import app.main as main_mod

    calls = {"mineru": 0, "opendataloader": 0}

    monkeypatch.setattr(main_mod, "_resolve_runtime_llm_settings", lambda **kwargs: ("https://example.com/v1", "demo-model", "secret"))
    monkeypatch.setattr(main_mod, "_build_history_preview_assets", lambda **kwargs: [])
    monkeypatch.setattr(main_mod, "save_history_record", lambda **kwargs: {"id": "history-opendataloader"})
    monkeypatch.setattr(main_mod, "_build_rotation_candidates", lambda **kwargs: [(0, kwargs["file_bytes"])])
    monkeypatch.setattr(main_mod, "_should_try_rotation_retry", lambda *args, **kwargs: False)
    monkeypatch.setattr(main_mod, "_count_detected_hits", lambda detected: len(detected or {}))
    monkeypatch.setattr(main_mod, "_estimate_text_quality", lambda preview: len(str(preview or "")))
    monkeypatch.setattr(
        main_mod,
        "run_llm_extract",
        lambda **kwargs: {
            "detected": {"发票号": "INV-ODL-001"},
            "endpoint": kwargs["base_url"],
            "model": kwargs["model"],
            "content": '{"发票号":"INV-ODL-001"}',
        },
    )
    monkeypatch.setattr(main_mod, "extract_fields_by_regions", lambda *args, **kwargs: {})

    def should_not_run(**kwargs):
        calls["mineru"] += 1
        raise AssertionError("mineru extractor should not be used when ocr_engine=opendataloader")

    monkeypatch.setattr(main_mod, "run_mineru_and_read_text", should_not_run)

    def fake_opendataloader(**kwargs):
        calls["opendataloader"] += 1
        return {
            "text": "Invoice No: INV-ODL-001",
            "markdown": "# Parsed\n\nInvoice No: INV-ODL-001",
            "json": {"blocks": [{"text": "Invoice No: INV-ODL-001"}]},
            "middle_json": {"pages": [{"blocks": [{"text": "Invoice No: INV-ODL-001"}]}]},
            "zip_entries": ["document.md", "document.json"],
            "zip_size": 321,
        }

    monkeypatch.setattr(main_mod, "run_opendataloader_and_read_text", fake_opendataloader)

    payload = main_mod._build_extract_payload(
        file_name="invoice.png",
        file_bytes=b"demo",
        vendor="Vendor A",
        doc_type="发票",
        fields="发票号",
        region_rules="",
        llm_prompt="提取发票号",
        llm_base_url="",
        llm_model="",
        llm_api_key="",
        mineru_model_version="vlm",
        backend="vlm",
        parse_method="auto",
        lang_list="en",
        ocr_engine="opendataloader",
    )

    assert calls["mineru"] == 0
    assert calls["opendataloader"] == 1
    assert payload["ocr_engine"] == "opendataloader"
    assert payload["ocr_engine_label"] == "OpenDataLoader PDF"
    assert payload["detected"] == {"发票号": "INV-ODL-001"}


def test_build_extract_payload_uses_markdown_fallback_when_opendataloader_text_is_empty(monkeypatch):
    import app.main as main_mod

    seen = {}

    monkeypatch.setattr(main_mod, "_resolve_runtime_llm_settings", lambda **kwargs: ("https://example.com/v1", "demo-model", "secret"))
    monkeypatch.setattr(main_mod, "_build_history_preview_assets", lambda **kwargs: [])
    monkeypatch.setattr(main_mod, "save_history_record", lambda **kwargs: {"id": "history-opendataloader-fallback"})
    monkeypatch.setattr(main_mod, "_build_rotation_candidates", lambda **kwargs: [(0, kwargs["file_bytes"])])
    monkeypatch.setattr(main_mod, "_should_try_rotation_retry", lambda *args, **kwargs: False)
    monkeypatch.setattr(main_mod, "_count_detected_hits", lambda detected: len(detected or {}))
    monkeypatch.setattr(main_mod, "_estimate_text_quality", lambda preview: len(str(preview or "")))
    monkeypatch.setattr(main_mod, "extract_fields_by_regions", lambda *args, **kwargs: {})

    def fake_llm_extract(**kwargs):
        seen["text"] = kwargs["text"]
        return {
            "detected": {"发票号": "INV-ODL-MD-001"},
            "endpoint": kwargs["base_url"],
            "model": kwargs["model"],
            "content": '{"发票号":"INV-ODL-MD-001"}',
        }

    monkeypatch.setattr(main_mod, "run_llm_extract", fake_llm_extract)
    monkeypatch.setattr(main_mod, "run_mineru_and_read_text", lambda **kwargs: (_ for _ in ()).throw(AssertionError("mineru should not run")))
    monkeypatch.setattr(
        main_mod,
        "run_opendataloader_and_read_text",
        lambda **kwargs: {
            "text": "",
            "markdown": "# Parsed\n\nInvoice No: INV-ODL-MD-001",
            "json": {"blocks": [{"text": "Invoice No: INV-ODL-MD-001"}]},
            "middle_json": {"pages": []},
            "zip_entries": ["document.md"],
            "zip_size": 123,
        },
    )

    payload = main_mod._build_extract_payload(
        file_name="invoice.pdf",
        file_bytes=b"demo",
        vendor="Vendor A",
        doc_type="发票",
        fields="发票号",
        region_rules="",
        llm_prompt="提取发票号",
        llm_base_url="",
        llm_model="",
        llm_api_key="",
        mineru_model_version="vlm",
        backend="vlm",
        parse_method="auto",
        lang_list="en",
        ocr_engine="opendataloader",
    )

    assert seen["text"].startswith("# Parsed")
    assert payload["preview"].startswith("# Parsed")
    assert payload["detected"] == {"发票号": "INV-ODL-MD-001"}


def test_build_extract_payload_persists_opendataloader_output_files_as_history_assets(monkeypatch):
    import app.main as main_mod

    captured = {}

    monkeypatch.setattr(main_mod, "_resolve_runtime_llm_settings", lambda **kwargs: ("https://example.com/v1", "demo-model", "secret"))
    monkeypatch.setattr(main_mod, "_build_history_preview_assets", lambda **kwargs: [])
    monkeypatch.setattr(main_mod, "_build_rotation_candidates", lambda **kwargs: [(0, kwargs["file_bytes"])])
    monkeypatch.setattr(main_mod, "_should_try_rotation_retry", lambda *args, **kwargs: False)
    monkeypatch.setattr(main_mod, "_count_detected_hits", lambda detected: len(detected or {}))
    monkeypatch.setattr(main_mod, "_estimate_text_quality", lambda preview: len(str(preview or "")))
    monkeypatch.setattr(main_mod, "extract_fields_by_regions", lambda *args, **kwargs: {})
    monkeypatch.setattr(
        main_mod,
        "run_llm_extract",
        lambda **kwargs: {
            "detected": {"发票号": "INV-ODL-002"},
            "endpoint": kwargs["base_url"],
            "model": kwargs["model"],
            "content": '{"发票号":"INV-ODL-002"}',
        },
    )
    monkeypatch.setattr(main_mod, "run_mineru_and_read_text", lambda **kwargs: (_ for _ in ()).throw(AssertionError("mineru should not run")))
    monkeypatch.setattr(
        main_mod,
        "run_opendataloader_and_read_text",
        lambda **kwargs: {
            "text": "Invoice No: INV-ODL-002",
            "markdown": "# Parsed\n\nInvoice No: INV-ODL-002",
            "json": {"blocks": [{"text": "Invoice No: INV-ODL-002"}]},
            "middle_json": {"pages": []},
            "zip_entries": ["document.md", "document.json", "images/p1.png"],
            "zip_size": 456,
            "history_assets": [
                {"path": "opendataloader/document.md", "content": b"# Parsed\n\nInvoice No: INV-ODL-002\n"},
                {"path": "opendataloader/document.json", "content": b'{"blocks":[{"text":"Invoice No: INV-ODL-002"}]}'},
                {"path": "opendataloader/images/p1.png", "content": b"\x89PNG\r\n"},
            ],
        },
    )

    def fake_save_history_record(**kwargs):
        captured["extra_assets"] = kwargs.get("extra_assets") or []
        return {"id": "history-opendataloader-assets"}

    monkeypatch.setattr(main_mod, "save_history_record", fake_save_history_record)

    payload = main_mod._build_extract_payload(
        file_name="invoice.pdf",
        file_bytes=b"demo",
        vendor="Vendor A",
        doc_type="发票",
        fields="发票号",
        region_rules="",
        llm_prompt="提取发票号",
        llm_base_url="",
        llm_model="",
        llm_api_key="",
        mineru_model_version="vlm",
        backend="vlm",
        parse_method="auto",
        lang_list="en",
        ocr_engine="opendataloader",
    )

    saved_paths = {item["path"] for item in captured["extra_assets"]}
    assert "opendataloader/document.md" in saved_paths
    assert "opendataloader/document.json" in saved_paths
    assert "opendataloader/images/p1.png" in saved_paths
    assert payload["history"]["id"] == "history-opendataloader-assets"


def test_save_history_record_includes_selected_preview_asset(tmp_path):
    from app.history_store import save_history_record

    summary = save_history_record(
        project_root=tmp_path,
        response_payload={
            "filename": "demo.pdf",
            "vendor": "A",
            "doc_type": "B",
            "detected": {"单号": "123"},
            "targets": ["单号"],
        },
        zip_bytes=None,
        extra_assets=[
            {
                "path": "preview/final_selected.pdf",
                "content": b"%PDF-1.4\npreview\n",
                "mime": "application/pdf",
            }
        ],
    )

    meta_path = tmp_path / "output" / "history" / summary["id"] / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    files = meta["files"]

    assert any(item["path"] == "preview/final_selected.pdf" for item in files)
    saved_path = tmp_path / "output" / "history" / summary["id"] / "unzipped" / "preview" / "final_selected.pdf"
    assert saved_path.is_file()


def test_normalize_ocr_engine_accepts_qwen_vision():
    import app.main as main_mod

    assert main_mod._normalize_ocr_engine("qwen_vision") == "qwen_vision"


def test_ocr_engine_label_for_qwen_vision():
    import app.main as main_mod

    assert main_mod._ocr_engine_label("qwen_vision") == "Qwen3.5-Plus 端到端"


def test_build_extract_payload_routes_qwen_vision_without_text_llm(tmp_path, monkeypatch):
    import app.main as main_mod

    monkeypatch.setattr(main_mod, "project_root", tmp_path)
    monkeypatch.setattr(main_mod, "_auto_rotate_pdf_with_osd", lambda file_bytes: (file_bytes, False, "skip", []))
    monkeypatch.setattr(main_mod, "_build_rotation_candidates", lambda **kwargs: [(0, kwargs["file_bytes"])])

    called = {"qwen": 0, "llm": 0, "mineru": 0, "odl": 0}

    def fake_qwen_extract(**kwargs):
        called["qwen"] += 1
        return {
            "detected": {"发票号": "INV-001"},
            "content": '{"发票号":"INV-001"}',
            "model": "qwen3.5-plus",
            "endpoint": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            "preview": "# OCR\n\n发票号: INV-001",
            "markdown": "# OCR\n\n发票号: INV-001",
            "history_assets": [
                {"path": "qwen_vision/raw-response.json", "content": b'{"ok":true}'},
                {"path": "qwen_vision/preview.md", "content": "# OCR\n\n发票号: INV-001".encode("utf-8")},
            ],
        }

    monkeypatch.setattr(main_mod, "run_qwen_vision_extract", fake_qwen_extract)
    monkeypatch.setattr(
        main_mod,
        "run_llm_extract",
        lambda **kwargs: called.__setitem__("llm", called["llm"] + 1) or {},
    )
    monkeypatch.setattr(
        main_mod,
        "run_mineru_and_read_text",
        lambda **kwargs: called.__setitem__("mineru", called["mineru"] + 1) or {},
    )
    monkeypatch.setattr(
        main_mod,
        "run_opendataloader_and_read_text",
        lambda **kwargs: called.__setitem__("odl", called["odl"] + 1) or {},
    )

    payload = main_mod._build_extract_payload(
        file_name="invoice.pdf",
        file_bytes=b"%PDF-1.4 fake",
        vendor="ASE",
        doc_type="invoice",
        fields="",
        region_rules="",
        llm_prompt="提取发票号",
        llm_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        llm_model="qwen3.5-plus",
        llm_api_key="secret",
        mineru_model_version="vlm",
        backend="vlm",
        parse_method="auto",
        lang_list="en",
        ocr_engine="qwen_vision",
    )

    assert called == {"qwen": 1, "llm": 0, "mineru": 0, "odl": 0}
    assert payload["ocr_engine"] == "qwen_vision"
    assert payload["ocr_engine_label"] == "Qwen3.5-Plus 端到端"
    assert payload["llm_model"] == "qwen3.5-plus"
    assert payload["detected"] == {"发票号": "INV-001"}
    assert payload["preview"].startswith("# OCR")
    history_path = Path(tmp_path) / "output" / "history" / payload["history"]["id"] / "unzipped" / "qwen_vision" / "preview.md"
    assert history_path.is_file()


def test_build_extract_payload_rejects_office_files_for_qwen_vision():
    import app.main as main_mod

    try:
        main_mod._build_extract_payload(
            file_name="invoice.docx",
            file_bytes=b"fake",
            vendor="ASE",
            doc_type="invoice",
            fields="",
            region_rules="",
            llm_prompt="提取发票号",
            llm_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            llm_model="qwen3.5-plus",
            llm_api_key="secret",
            mineru_model_version="vlm",
            backend="vlm",
            parse_method="auto",
            lang_list="en",
            ocr_engine="qwen_vision",
        )
    except ValueError as exc:
        assert "Qwen3.5-Plus" in str(exc)
    else:
        raise AssertionError("expected qwen_vision office file validation to fail")
