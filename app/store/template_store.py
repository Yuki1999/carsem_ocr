from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any


SETTINGS_DIR_NAME = "settings"
TEMPLATES_FILE_NAME = "templates.json"
MAX_TEMPLATE_ITEMS = 200

DEFAULT_MODEL_VERSION = "vlm"
DEFAULT_PARSE_METHOD = "auto"
DEFAULT_LANG_LIST = "en"
DOC_TYPES = ["到货单", "物流通知书", "送货单", "发票", "报关单"]
PARSE_METHODS = ["auto", "txt", "ocr"]


def load_templates(project_root: Path) -> list[dict[str, Any]]:
    data = _read_json(_templates_file(project_root), default=None)
    return normalize_templates(data)


def save_templates(project_root: Path, payload: Any) -> list[dict[str, Any]]:
    normalized = normalize_templates(payload)
    file_path = _templates_file(project_root)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json_atomic(file_path, normalized)
    return normalized


def reset_templates(project_root: Path) -> list[dict[str, Any]]:
    defaults = _default_templates()
    file_path = _templates_file(project_root)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json_atomic(file_path, defaults)
    return defaults


def normalize_templates(payload: Any) -> list[dict[str, Any]]:
    raw_items = payload
    if isinstance(payload, dict):
        raw_items = payload.get("items")
    if not isinstance(raw_items, list):
        return _default_templates()

    cleaned: list[dict[str, Any]] = []
    seen = set()
    for index, item in enumerate(raw_items, start=1):
        normalized = _normalize_template(item, index=index)
        key = f"{normalized['vendor']}__{normalized['doc_type']}"
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(normalized)
        if len(cleaned) >= MAX_TEMPLATE_ITEMS:
            break
    return cleaned or _default_templates()


def _default_templates() -> list[dict[str, Any]]:
    return [
        _normalize_template(
            {
                "id": uuid.uuid4().hex,
                "vendor": "嘉盛半导体",
                "doc_type": "到货单",
                "llm_prompt": '请提取到货单关键信息，以 JSON 返回：{"通知书编号":"","供应商名称":"","到货日期":"","采购订单号":"","商品明细":[{}]}。如存在多项商品，请在“商品明细”数组中逐项输出，每项字段按单据原文提取且不固定；无明细返回空数组 []。',
            },
            index=1,
        ),
        _normalize_template(
            {
                "id": uuid.uuid4().hex,
                "vendor": "嘉盛半导体",
                "doc_type": "物流通知书",
                "llm_prompt": '请提取物流通知书信息，以 JSON 返回：{"通知日期":"","承运商":"","车牌号":"","起运地":"","目的地":"","预计到厂时间":"","联系人":"","联系电话":"","商品明细":[{}]}。如存在多项商品，请在“商品明细”数组中逐项输出，每项字段按单据原文提取且不固定；无明细返回空数组 []。',
            },
            index=2,
        ),
        _normalize_template(
            {
                "id": uuid.uuid4().hex,
                "vendor": "嘉盛半导体",
                "doc_type": "送货单",
                "llm_prompt": '请提取送货单关键信息，以 JSON 返回：{"送货单号":"","供应商代码":"","收货单位":"","送货日期":"","商品明细":[{}]}。如存在多项商品，请在“商品明细”数组中逐项输出，每项字段按单据原文提取且不固定；无明细返回空数组 []。',
            },
            index=3,
        ),
        _normalize_template(
            {
                "id": uuid.uuid4().hex,
                "vendor": "嘉盛半导体",
                "doc_type": "发票",
                "llm_prompt": '请从发票文本中提取信息，以 JSON 返回：{"发票号":"","开票日期":"","价税合计":"","购买方名称":""}',
            },
            index=4,
        ),
        _normalize_template(
            {
                "id": uuid.uuid4().hex,
                "vendor": "嘉盛半导体",
                "doc_type": "报关单",
                "llm_prompt": '请提取报关单关键信息，以 JSON 返回：{"报关单号":"","申报日期":"","境内收发货人":"","消费使用单位":"","贸易方式":"","商品明细":[{}]}。如存在多项商品，请在“商品明细”数组中逐项输出，每项字段按单据原文提取且不固定；无明细返回空数组 []。',
            },
            index=5,
        ),
        _normalize_template(
            {
                "id": uuid.uuid4().hex,
                "vendor": "UPI  Semi",
                "doc_type": "物流通知书",
                "llm_prompt": '请提取物流通知书关键信息，以 JSON 返回：{"Mawb":"","Hawb":"","Country（启运国/From）":"","Total Pieces（Shipment Information）":"","Total Weight（Shipment Information）":"","ORIGINAL OF COUNTRY":"","Freight Terms":"","Part No.":"","QTY":"","Die Qty":"","Unit Price":"","AMOUNT":"","N/W":"","G/W":"","件数（如 CTN）":"","商品明细":[{}],"Shipper\'s Name":""}。如存在多项商品，请在“商品明细”数组中逐项输出，每项字段按单据原文提取且不固定；无明细返回空数组 []。',
                "backend": "vlm",
                "parse_method": "auto",
                "lang_list": "en",
            },
            index=6,
        ),
        _normalize_template(
            {
                "id": uuid.uuid4().hex,
                "vendor": "STMicroelectronics",
                "doc_type": "物流通知书",
                "llm_prompt": '请提取物流通知书关键信息，以 JSON 返回：{"MAWB No":"","HAWB No":"","Airport of Departure (Addr. of First Carrier) and Requested Routing":"","No. of Process RCP":"","Gross Weight":"","INV":"","Incoterm":"","Net Wt.":"","Material Code":"","Qty":"","Gross Qty":"","Wafer Qty":"","Unit Price":"","Value":"","COO":"","Summary Quantity":"","Summary Gross Qty":"","Summary WaferQty":"","Summary Value":"","商品明细":[{}],"Shipper\'s Name":""}。如存在多项商品，请在“商品明细”数组中逐项输出，每项字段按单据原文提取且不固定；无明细返回空数组 []。',
                "backend": "pipeline",
                "parse_method": "auto",
                "lang_list": "en",
            },
            index=7,
        ),
        _normalize_template(
            {
                "id": uuid.uuid4().hex,
                "vendor": "TI",
                "doc_type": "物流通知书",
                "llm_prompt": '请提取物流通知书关键信息，以 JSON 返回：{"MAWB NO.":"","HAWB NO.":"","Airport of Departure (Addr. of First Carrier) and Requested Routing":"","No. of Process RCP":"","Gross Weight":"","Invoice Number":"","Incoterms":"","CCO":"","TI Part#":"","Quantity":"","Unit Price":"","Value in USD":"","Material":"","Net weight":"","Wafer Count":"","Gross Die":"","商品明细":[{}],"Shipper\'s Name":""}。如存在多项商品，请在“商品明细”数组中逐项输出，每项字段按单据原文提取且不固定；无明细返回空数组 []。',
                "backend": "vlm",
                "parse_method": "auto",
                "lang_list": "en",
            },
            index=8,
        ),
    ]


def _normalize_template(item: Any, index: int) -> dict[str, Any]:
    row = item if isinstance(item, dict) else {}
    doc_type = str(row.get("doc_type") or "").strip()
    if doc_type not in DOC_TYPES:
        doc_type = "到货单"
    parse_method = str(row.get("parse_method") or "").strip().lower()
    if parse_method not in PARSE_METHODS:
        parse_method = DEFAULT_PARSE_METHOD
    vendor = str(row.get("vendor") or row.get("name") or "").strip()
    customs_mapping = _normalize_customs_mapping(row.get("customs_mapping"))
    return {
        "id": str(row.get("id") or "").strip() or uuid.uuid4().hex,
        "vendor": vendor,
        "doc_type": doc_type,
        "llm_prompt": str(row.get("llm_prompt") or ""),
        "region_rules": str(row.get("region_rules") or ""),
        "backend": str(row.get("backend") or "").strip() or DEFAULT_MODEL_VERSION,
        "parse_method": parse_method,
        "lang_list": str(row.get("lang_list") or "").strip() or DEFAULT_LANG_LIST,
        "customs_mapping": customs_mapping,
    }


def _normalize_customs_mapping(raw: Any) -> dict[str, dict[str, str]]:
    if not isinstance(raw, dict):
        return {"header": {}, "detail": {}}

    def _normalize_map(value: Any) -> dict[str, str]:
        if not isinstance(value, dict):
            return {}
        normalized: dict[str, str] = {}
        for key, target in value.items():
            src = str(key or "").strip()
            dst = str(target or "").strip()
            if not src or not dst:
                continue
            normalized[src] = dst
        return normalized

    return {
        "header": _normalize_map(raw.get("header")),
        "detail": _normalize_map(raw.get("detail")),
    }


def _templates_file(project_root: Path) -> Path:
    return project_root / "output" / SETTINGS_DIR_NAME / TEMPLATES_FILE_NAME


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json_atomic(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)
