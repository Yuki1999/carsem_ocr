from __future__ import annotations

import re
from typing import Any

import requests

DEFAULT_FIELD_TEXT = "-1"
NUMERIC_HEADER_FIELDS = {
    "Quantity",
    "GrossWeight",
    "NetWeight",
    "TotalSheets",
    "TotalQuantity",
    "GoodQuantity",
    "TotalPrice",
}
NUMERIC_DETAIL_FIELDS = {
    "ItemQuantity",
    "ItemGoodQuantity",
    "ItemPrice",
    "ItemUnitPrice",
}


def submit_to_customs_site(
    draft: dict[str, Any],
    credentials: dict[str, str] | None = None,
    mode: str = "http",
) -> dict[str, Any]:
    credentials = credentials if isinstance(credentials, dict) else {}
    resolved_mode = str(mode or "http").strip().lower() or "http"
    if resolved_mode != "http":
        try:
            from .customs_playwright import submit_to_customs_site_with_playwright
        except Exception as exc:
            raise RuntimeError(f"playwright_unavailable: {exc}") from exc
        return submit_to_customs_site_with_playwright(draft, credentials)

    site_url = str(credentials.get("site_url") or "https://vatest.carsem.com.cn").rstrip("/")
    username = str(credentials.get("username") or "vip@dianxin").strip()
    password = str(credentials.get("password") or "xinpwd@@@2026").strip()
    if not site_url or not username or not password:
        raise RuntimeError("缺少报关系统登录凭据")

    session = requests.Session()
    session.headers.update({"User-Agent": "carsem-ocr-customs-submit/1.0"})

    login_resp = session.post(
        f"{site_url}/Home/Login",
        data={"username": username, "password": password},
        allow_redirects=True,
        timeout=30,
    )
    login_resp.raise_for_status()
    if "/Home/Login" in login_resp.url:
        raise RuntimeError("login_failed: 登录后仍停留在登录页")

    declaration_no = _get_next_declaration_no(session, site_url)
    payload = _flatten_submission_payload(draft, declaration_no)

    save_resp = session.post(f"{site_url}/Home/SaveData", data=payload, timeout=30)
    save_resp.raise_for_status()
    data = _safe_json(save_resp)
    if not bool(data.get("success")):
        raise RuntimeError(f"submission_rejected: {str(data.get('message') or '网站返回失败')}")

    return {
        "ok": True,
        "message": str(data.get("message") or "数据保存成功"),
        "declaration_no": declaration_no,
        "site_url": site_url,
        "submit_engine": "http",
    }


def _flatten_submission_payload(draft: dict[str, Any], declaration_no: str) -> list[tuple[str, str]]:
    header = draft.get("header") if isinstance(draft.get("header"), dict) else {}
    details = draft.get("details") if isinstance(draft.get("details"), list) else []

    pairs = [
        ("DeclarationNo", declaration_no),
        ("MainBLNo", _clean_payload_text("MainBLNo", header.get("Mawb") or header.get("MainBLNo"))),
        ("SubBLNo", _clean_payload_text("SubBLNo", header.get("Hawb") or header.get("SubBLNo"))),
        ("CustomerName", _clean_payload_text("CustomerName", header.get("CustomerName"))),
        ("TradeType", _clean_payload_text("TradeType", header.get("TradeType"))),
        ("OriginCountry", _clean_payload_text("OriginCountry", header.get("OriginCountry"))),
        ("InvoiceNo", _clean_payload_text("InvoiceNo", header.get("InvoiceNo"))),
        ("Quantity", _clean_payload_text("Quantity", header.get("Quantity"))),
        ("GrossWeight", _clean_payload_text("GrossWeight", header.get("GrossWeight"))),
        ("NetWeight", _clean_payload_text("NetWeight", header.get("NetWeight"))),
        ("TotalSheets", _clean_payload_text("TotalSheets", header.get("TotalSheets"))),
        ("TotalQuantity", _clean_payload_text("TotalQuantity", header.get("TotalQuantity"))),
        ("GoodQuantity", _clean_payload_text("GoodQuantity", header.get("GoodQuantity"))),
        ("TotalPrice", _clean_payload_text("TotalPrice", header.get("TotalPrice"))),
    ]

    for item in details:
        if not isinstance(item, dict):
            continue
        pairs.extend(
            [
                ("ItemCode", _clean_payload_text("ItemCode", item.get("ItemCode"))),
                ("ItemOrigin", _clean_payload_text("ItemOrigin", item.get("ItemOrigin"))),
                ("ItemQuantity", _clean_payload_text("ItemQuantity", item.get("ItemQuantity"))),
                ("ItemGoodQuantity", _clean_payload_text("ItemGoodQuantity", item.get("ItemGoodQuantity"))),
                ("ItemPrice", _clean_payload_text("ItemPrice", item.get("ItemPrice"))),
                ("ItemUnitPrice", _clean_payload_text("ItemUnitPrice", item.get("ItemUnitPrice"))),
            ]
        )
    return pairs


def _get_next_declaration_no(session: requests.Session, site_url: str) -> str:
    resp = session.get(f"{site_url}/Home/GetNextDeclarationNo", timeout=30)
    resp.raise_for_status()
    data = _safe_json(resp)
    declaration_no = str(data.get("declarationNo") or "").strip()
    if not declaration_no:
        raise RuntimeError("page_structure_changed: 未获取到报关单号")
    return declaration_no


def _safe_json(response: requests.Response) -> dict[str, Any]:
    try:
        data = response.json()
    except Exception as exc:
        raise RuntimeError(f"unexpected_error: 目标站点未返回 JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError("unexpected_error: 目标站点返回的 JSON 结构无效")
    return data


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value)


def _clean_payload_text(field_name: str, value: Any) -> str:
    text = _to_text(value)
    if field_name in NUMERIC_HEADER_FIELDS or field_name in NUMERIC_DETAIL_FIELDS:
        if text == DEFAULT_FIELD_TEXT:
            return DEFAULT_FIELD_TEXT
        match = re.search(r"-?\d+(?:\.\d+)?", text)
        return match.group(0) if match else DEFAULT_FIELD_TEXT
    return text
