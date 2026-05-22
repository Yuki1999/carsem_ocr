from __future__ import annotations

from copy import deepcopy
import re
from typing import Any


DEFAULT_FIELD_TEXT = "-1"
LEGACY_HEADER_FIELD_MAP = {
    "MainBLNo": "Mawb",
    "SubBLNo": "Hawb",
}

CUSTOMS_HEADER_FIELDS = [
    "Mawb",
    "Hawb",
    "CustomerName",
    "TradeType",
    "OriginCountry",
    "InvoiceNo",
    "Quantity",
    "GrossWeight",
    "NetWeight",
    "TotalSheets",
    "TotalQuantity",
    "GoodQuantity",
    "TotalPrice",
]

CUSTOMS_DETAIL_FIELDS = [
    "ItemCode",
    "ItemOrigin",
    "ItemQuantity",
    "ItemGoodQuantity",
    "ItemPrice",
    "ItemUnitPrice",
]

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
SPACE_STRIPPED_HEADER_FIELDS = {
    "Mawb",
    "Hawb",
}

HEADER_ALIASES = {
    "Mawb": ["主提单号", "主提运单号", "主单号", "Mawb", "MAWB", "MAWB No", "MAWB NO."],
    "Hawb": ["分提单号", "分提运单号", "Hawb", "HAWB", "HAWB No", "HAWB NO."],
    "CustomerName": ["Shipper's Name", "Shipper Name", "发货客户", "客户名称", "客户", "收货客户"],
    "TradeType": ["Freight Terms", "Incoterm", "Incoterms"],
    "OriginCountry": ["原产国", "Country of Origin", "ORIGINAL OF COUNTRY"],
    "Quantity": ["No. of Process RCP","Nr.of Parcels", "Total Number of Parcels"],
    "TotalQuantity": ["总数量", "Qty", "QTY", "Summary Quantity"],
    "GoodQuantity": ["良品总数量", "Gross Qty", "Summary Gross Qty"],
    "TotalSheets": ["总片数", "Die Qty", "WaferQty", "Wafer Qty", "Summary WaferQty"],
    "TotalPrice": ["总价格", "总价", "货值", "金额"],
}

DETAIL_ALIASES = {
    "ItemCode": ["料号", "商品料号", "商品编码"],
    "ItemOrigin": ["原产国"],
    "ItemQuantity": ["数量", "总数量"],
    "ItemGoodQuantity": ["良品数量"],
    "ItemPrice": ["总价"],
    "ItemUnitPrice": ["单价"],
}


def build_submission_draft(
    response_payload: dict[str, Any],
    template: dict[str, Any] | None = None,
    llm_output: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from .customs_packet import build_packet_submission_draft, has_packet_structures

    if has_packet_structures(response_payload, llm_output):
        return build_packet_submission_draft(response_payload, llm_output)

    if isinstance(llm_output, dict) and (isinstance(llm_output.get("header"), dict) or isinstance(llm_output.get("details"), list)):
        draft = _build_submission_draft_from_llm(llm_output)
        detected = response_payload.get("detected") if isinstance(response_payload, dict) else {}
        if isinstance(detected, dict):
            draft["header"] = _apply_detected_header_alias_overrides(
                draft.get("header"),
                detected,
                ["TradeType", "OriginCountry", "TotalQuantity", "GoodQuantity", "TotalSheets"],
            )
        return draft

    detected = response_payload.get("detected") if isinstance(response_payload, dict) else {}
    detected = detected if isinstance(detected, dict) else {}
    template = template if isinstance(template, dict) else {}
    customs_mapping = template.get("customs_mapping") if isinstance(template.get("customs_mapping"), dict) else {}
    header_mapping = customs_mapping.get("header") if isinstance(customs_mapping.get("header"), dict) else {}
    detail_mapping = customs_mapping.get("detail") if isinstance(customs_mapping.get("detail"), dict) else {}

    header = {field: DEFAULT_FIELD_TEXT for field in CUSTOMS_HEADER_FIELDS}
    auto_mapped: dict[str, str] = {}

    for source_field, target_field in header_mapping.items():
        mapped_target = LEGACY_HEADER_FIELD_MAP.get(target_field, target_field)
        if mapped_target not in header:
            continue
        value = detected.get(source_field)
        if _has_value(value):
            header[mapped_target] = _stringify_value(value)
            auto_mapped[source_field] = mapped_target

    for target_field, aliases in HEADER_ALIASES.items():
        if _has_meaningful_value(header.get(target_field)):
            continue
        source_field = _first_matching_key(detected, aliases)
        if not source_field:
            continue
        header[target_field] = _stringify_value(detected.get(source_field))
        auto_mapped[source_field] = target_field

    details_source = detected.get("商品明细")
    details: list[dict[str, str]] = []
    if isinstance(details_source, list):
        for item in details_source:
            if not isinstance(item, dict):
                continue
            detail_row = {field: DEFAULT_FIELD_TEXT for field in CUSTOMS_DETAIL_FIELDS}
            for source_field, target_field in detail_mapping.items():
                if target_field not in detail_row:
                    continue
                value = item.get(source_field)
                if _has_value(value):
                    detail_row[target_field] = _stringify_value(value)
            for target_field, aliases in DETAIL_ALIASES.items():
                if _has_meaningful_value(detail_row.get(target_field)):
                    continue
                source_field = _first_matching_key(item, aliases)
                if not source_field:
                    continue
                detail_row[target_field] = _stringify_value(item.get(source_field))
            if any(_has_meaningful_value(v) for v in detail_row.values()):
                details.append(detail_row)

    return {
        "target": "vatest.carsem.com.cn",
        "header": _fill_default_header_values(header),
        "details": _ensure_details(details),
        "meta": {
            "required_missing": [],
            "unmapped_fields": [],
            "auto_mapped": auto_mapped,
            "last_edited_at": "",
            "submit_status": "idle",
            "submit_message": "",
            "submit_result": None,
        },
    }


def _build_submission_draft_from_llm(llm_output: dict[str, Any]) -> dict[str, Any]:
    draft = build_empty_submission_draft()
    header = _normalize_legacy_header(llm_output.get("header") if isinstance(llm_output.get("header"), dict) else {})
    for field in CUSTOMS_HEADER_FIELDS:
        draft["header"][field] = _normalize_field_value(field, header.get(field))
    draft["header"] = _fill_default_header_values(draft["header"])

    details = llm_output.get("details")
    if isinstance(details, list):
        normalized_details: list[dict[str, str]] = []
        for item in details:
            if not isinstance(item, dict):
                continue
            row = {field: _normalize_field_value(field, item.get(field)) for field in CUSTOMS_DETAIL_FIELDS}
            if any(_has_meaningful_value(value) for value in row.values()):
                normalized_details.append(row)
        draft["details"] = _ensure_details(normalized_details)

    meta = llm_output.get("meta")
    if isinstance(meta, dict):
        draft["meta"].update(meta)
    draft["meta"]["mapping_source"] = "llm"
    draft["meta"]["required_missing"] = []
    return draft


def attach_submission_draft(response_payload: dict[str, Any], draft: dict[str, Any]) -> dict[str, Any]:
    updated = deepcopy(response_payload if isinstance(response_payload, dict) else {})
    updated["submission"] = deepcopy(draft if isinstance(draft, dict) else {})
    return updated


def merge_submission_draft(existing_draft: dict[str, Any], incoming_draft: dict[str, Any]) -> dict[str, Any]:
    merged = build_empty_submission_draft()
    for source in (existing_draft, incoming_draft):
        if not isinstance(source, dict):
            continue
        header = _normalize_legacy_header(source.get("header") if isinstance(source.get("header"), dict) else {})
        for field in CUSTOMS_HEADER_FIELDS:
            if field in header:
                merged["header"][field] = _normalize_field_value(field, header.get(field))
        details = source.get("details")
        if isinstance(details, list):
            merged["details"] = []
            for item in details:
                if not isinstance(item, dict):
                    continue
                row = {field: _normalize_field_value(field, item.get(field)) for field in CUSTOMS_DETAIL_FIELDS}
                if any(_has_meaningful_value(value) for value in row.values()):
                    merged["details"].append(row)
        meta = source.get("meta")
        if isinstance(meta, dict):
            merged["meta"].update(meta)
        if source.get("target"):
            merged["target"] = str(source.get("target"))
    merged["header"] = _fill_default_header_values(merged["header"])
    merged["details"] = _ensure_details(merged["details"])
    merged["meta"]["required_missing"] = []
    return merged


def validate_submission_draft(draft: dict[str, Any]) -> dict[str, Any]:
    normalized = merge_submission_draft({}, draft)
    required_missing: list[str] = []
    normalized["meta"]["required_missing"] = required_missing
    return {
        "ok": True,
        "required_missing": required_missing,
        "message": "校验通过",
        "draft": normalized,
    }


def build_empty_submission_draft() -> dict[str, Any]:
    return {
        "target": "vatest.carsem.com.cn",
        "header": {field: DEFAULT_FIELD_TEXT for field in CUSTOMS_HEADER_FIELDS},
        "details": [_build_default_detail_row()],
        "meta": {
            "required_missing": [],
            "unmapped_fields": [],
            "auto_mapped": {},
            "mapping_source": "rules",
            "last_edited_at": "",
            "submit_status": "idle",
            "submit_message": "",
            "submit_result": None,
        },
    }


def _first_matching_key(source: dict[str, Any], aliases: list[str]) -> str:
    for alias in aliases:
        if alias in source and _has_value(source.get(alias)):
            return alias
    return ""


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def _has_meaningful_value(value: Any) -> bool:
    text = _stringify_value(value)
    return bool(text and text != DEFAULT_FIELD_TEXT)


def _stringify_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float, bool)):
        return str(value)
    return str(deepcopy(value))


def _stringify_or_default(value: Any) -> str:
    text = _stringify_value(value)
    return text if text else DEFAULT_FIELD_TEXT


def _normalize_legacy_header(header: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(header)
    for legacy_field, current_field in LEGACY_HEADER_FIELD_MAP.items():
        if legacy_field in normalized and current_field not in normalized:
            normalized[current_field] = normalized.get(legacy_field)
    return normalized


def _fill_default_header_values(header: dict[str, str]) -> dict[str, str]:
    normalized = {field: _normalize_field_value(field, header.get(field)) for field in CUSTOMS_HEADER_FIELDS}
    return _normalize_quantity_pair(normalized, "TotalQuantity", "GoodQuantity")


def _build_default_detail_row() -> dict[str, str]:
    return {field: DEFAULT_FIELD_TEXT for field in CUSTOMS_DETAIL_FIELDS}


def _ensure_details(details: list[dict[str, str]]) -> list[dict[str, str]]:
    normalized = [_normalize_quantity_pair(item, "ItemQuantity", "ItemGoodQuantity") for item in details]
    return normalized if normalized else [_build_default_detail_row()]


def _extract_numeric_text(value: str) -> str:
    match = re.search(r"-?\d+(?:\.\d+)?", value or "")
    return match.group(0) if match else ""


def _normalize_field_value(field_name: str, value: Any) -> str:
    text = _stringify_value(value)
    if field_name in SPACE_STRIPPED_HEADER_FIELDS:
        compact = re.sub(r"\s+", "", text)
        return compact if compact else DEFAULT_FIELD_TEXT
    if field_name in NUMERIC_HEADER_FIELDS or field_name in NUMERIC_DETAIL_FIELDS:
        numeric = _extract_numeric_text(text)
        return numeric if numeric else DEFAULT_FIELD_TEXT
    return text if text else DEFAULT_FIELD_TEXT


def _apply_detected_header_alias_overrides(header: Any, detected: dict[str, Any], fields: list[str]) -> dict[str, str]:
    normalized = dict(header) if isinstance(header, dict) else {field: DEFAULT_FIELD_TEXT for field in CUSTOMS_HEADER_FIELDS}
    for field_name in fields:
        source_field = _first_matching_key(detected, HEADER_ALIASES.get(field_name, []))
        if not source_field:
            continue
        normalized[field_name] = _normalize_field_value(field_name, detected.get(source_field))
    return normalized


def _normalize_quantity_pair(row: dict[str, str], total_field: str, good_field: str) -> dict[str, str]:
    normalized = dict(row)
    total_value = normalized.get(total_field, DEFAULT_FIELD_TEXT)
    good_value = normalized.get(good_field, DEFAULT_FIELD_TEXT)
    total_number = _parse_quantity_number(total_value)
    good_number = _parse_quantity_number(good_value)
    if total_number is None or good_number is None:
        return normalized
    if good_number > total_number:
        normalized[total_field], normalized[good_field] = good_value, total_value
    return normalized


def _parse_quantity_number(value: Any) -> float | None:
    text = _stringify_value(value)
    if not text or text == DEFAULT_FIELD_TEXT:
        return None
    try:
        return float(text)
    except ValueError:
        return None
