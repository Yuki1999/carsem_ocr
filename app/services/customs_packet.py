from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from .customs_submission import (
    CUSTOMS_HEADER_FIELDS,
    CUSTOMS_DETAIL_FIELDS,
    DEFAULT_FIELD_TEXT,
)


INVOICE_LINE_KEYS = ("invoice_lines", "invoiceLines", "发票明细", "发票商品明细")
PACKING_LINE_KEYS = ("packing_lines", "packingLines", "箱单明细", "装箱明细")
HEADER_CANDIDATE_KEYS = ("header_candidates", "headerCandidates", "表头候选值")

ITEM_ALIASES = ("ITEM", "Item", "item", "商品项号", "项号")
PO_ALIASES = ("P/O No", "P/O NO", "P/O", "PO No", "PO", "P.O. No", "订单号")
PN_ALIASES = ("SAMSUNG P/N", "Samsung P/N", "P/N", "PN", "Part No", "产品编号", "实际料号", "料号")
QUANTITY_ALIASES = ("PC", "PCS", "Quantity", "Qty", "QTY", "数量", "申报数量")
UNIT_PRICE_ALIASES = ("@RMB/1000", "@USD/1000", "Unit Price", "UnitPrice", "单价")
AMOUNT_ALIASES = ("RMB", "USD", "Amount", "Total Amount", "Value", "金额", "总价")
ORIGIN_ALIASES = ("Country of Origin", "ORIGINAL OF COUNTRY", "Origin", "原产国", "产地")
SOURCE_ROW_ALIASES = ("source_row", "sourceRow", "源行", "row", "行号")


def build_packet_submission_draft(
    response_payload: dict[str, Any],
    llm_output: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source = _merge_packet_sources(response_payload, llm_output)
    invoice_lines = _extract_list_by_keys(source, INVOICE_LINE_KEYS)
    packing_lines = _extract_list_by_keys(source, PACKING_LINE_KEYS)
    header_candidates = _extract_header_candidates(source)

    details = [_detail_from_invoice_line(line) for line in invoice_lines]
    details = [row for row in details if any(_has_meaningful_value(value) for value in row.values())]
    if not details:
        details = [_default_detail()]

    packing_groups = _build_packing_groups(packing_lines)
    invoice_group_quantities = _build_invoice_group_quantities(invoice_lines)
    detail_reviews = _build_detail_reviews(invoice_lines, packing_groups, invoice_group_quantities)
    required_missing = [
        review["field_path"]
        for review in detail_reviews
        if review.get("quantity_check") in {"mismatch", "missing_packing"}
    ]

    header = _build_header(source, header_candidates)
    field_reviews = _build_field_reviews(header_candidates)
    required_missing.extend(review["field"] for review in field_reviews if review.get("review_required"))

    packet_meta = {
        "packet_id": _packet_id(source, response_payload),
        "source_files": _source_files(response_payload),
        "header_candidates": header_candidates,
        "field_reviews": field_reviews,
        "invoice_lines": deepcopy(invoice_lines),
        "packing_groups": packing_groups,
        "detail_reviews": detail_reviews,
    }

    return {
        "target": "vatest.carsem.com.cn",
        "header": header,
        "details": details,
        "meta": {
            "required_missing": required_missing,
            "unmapped_fields": [],
            "auto_mapped": {},
            "mapping_source": "packet",
            "last_edited_at": "",
            "submit_status": "idle",
            "submit_message": "",
            "submit_result": None,
            "packet": packet_meta,
        },
    }


def has_packet_structures(response_payload: dict[str, Any], llm_output: dict[str, Any] | None = None) -> bool:
    source = _merge_packet_sources(response_payload, llm_output)
    return bool(_extract_list_by_keys(source, INVOICE_LINE_KEYS) or _extract_list_by_keys(source, PACKING_LINE_KEYS))


def _merge_packet_sources(response_payload: dict[str, Any], llm_output: dict[str, Any] | None) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    if isinstance(response_payload, dict):
        merged.update(response_payload)
        detected = response_payload.get("detected")
        if isinstance(detected, dict):
            merged.update(detected)
    if isinstance(llm_output, dict):
        merged.update(llm_output)
    return merged


def _extract_list_by_keys(source: dict[str, Any], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    for key in keys:
        value = source.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _extract_header_candidates(source: dict[str, Any]) -> dict[str, Any]:
    for key in HEADER_CANDIDATE_KEYS:
        value = source.get(key)
        if isinstance(value, dict):
            return deepcopy(value)
    return {}


def _build_header(source: dict[str, Any], header_candidates: dict[str, Any]) -> dict[str, str]:
    header = {field: DEFAULT_FIELD_TEXT for field in CUSTOMS_HEADER_FIELDS}
    raw_header = source.get("header")
    if isinstance(raw_header, dict):
        for field in CUSTOMS_HEADER_FIELDS:
            if _has_meaningful_value(raw_header.get(field)):
                header[field] = _stringify(raw_header.get(field))
    for field, candidate in header_candidates.items():
        if field not in header or not isinstance(candidate, dict):
            continue
        recommended = candidate.get("recommended")
        if _has_meaningful_value(recommended):
            header[field] = _stringify(recommended)
    return header


def _build_field_reviews(header_candidates: dict[str, Any]) -> list[dict[str, Any]]:
    reviews: list[dict[str, Any]] = []
    for field, candidate in header_candidates.items():
        if not isinstance(candidate, dict):
            continue
        review_required = bool(candidate.get("review_required"))
        candidates = candidate.get("candidates")
        if isinstance(candidates, list) and len(candidates) > 1:
            review_required = True
        if not review_required:
            continue
        reviews.append(
            {
                "field": str(field),
                "recommended": _stringify(candidate.get("recommended")),
                "candidates": deepcopy(candidates if isinstance(candidates, list) else []),
                "reason": _stringify(candidate.get("reason")),
                "review_required": True,
            }
        )
    return reviews


def _detail_from_invoice_line(line: dict[str, Any]) -> dict[str, str]:
    quantity = _normalize_number(_first_value(line, QUANTITY_ALIASES))
    return {
        "ItemCode": _stringify_or_default(_first_value(line, PN_ALIASES)),
        "ItemOrigin": _stringify_or_default(_first_value(line, ORIGIN_ALIASES)),
        "ItemQuantity": quantity or DEFAULT_FIELD_TEXT,
        "ItemGoodQuantity": quantity or DEFAULT_FIELD_TEXT,
        "ItemPrice": _normalize_number(_first_value(line, AMOUNT_ALIASES)) or DEFAULT_FIELD_TEXT,
        "ItemUnitPrice": _normalize_number(_first_value(line, UNIT_PRICE_ALIASES)) or DEFAULT_FIELD_TEXT,
    }


def _build_packing_groups(packing_lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], dict[str, Any]] = {}
    for line in packing_lines:
        key = _line_key(line)
        if not any(key):
            continue
        quantity = _parse_number(_first_value(line, QUANTITY_ALIASES))
        group = groups.setdefault(
            key,
            {
                "key": _key_dict(key),
                "quantity_number": 0.0,
                "quantity": "0",
                "source_rows": [],
                "lines": [],
            },
        )
        group["quantity_number"] += quantity or 0.0
        source_row = _stringify(_first_value(line, SOURCE_ROW_ALIASES))
        if source_row:
            group["source_rows"].append(source_row)
        group["lines"].append(deepcopy(line))

    result = []
    for group in groups.values():
        group["quantity"] = _format_number(group.pop("quantity_number", 0.0))
        result.append(group)
    return result


def _build_invoice_group_quantities(invoice_lines: list[dict[str, Any]]) -> dict[tuple[str, str, str], float]:
    groups: dict[tuple[str, str, str], float] = {}
    for line in invoice_lines:
        key = _line_key(line)
        if not any(key):
            continue
        groups[key] = groups.get(key, 0.0) + (_parse_number(_first_value(line, QUANTITY_ALIASES)) or 0.0)
    return groups


def _build_detail_reviews(
    invoice_lines: list[dict[str, Any]],
    packing_groups: list[dict[str, Any]],
    invoice_group_quantities: dict[tuple[str, str, str], float],
) -> list[dict[str, Any]]:
    packing_by_key = {
        _tuple_key(group.get("key")): group
        for group in packing_groups
        if isinstance(group, dict)
    }
    reviews: list[dict[str, Any]] = []
    for index, line in enumerate(invoice_lines):
        key = _line_key(line)
        invoice_quantity = _parse_number(_first_value(line, QUANTITY_ALIASES))
        group = packing_by_key.get(key)
        packing_quantity = _parse_number(group.get("quantity")) if isinstance(group, dict) else None
        invoice_group_quantity = invoice_group_quantities.get(key)
        quantity_check = "missing_packing"
        if group is not None and packing_quantity is not None and invoice_quantity is not None:
            if _numbers_equal(invoice_quantity, packing_quantity):
                quantity_check = "matched"
            elif invoice_group_quantity is not None and _numbers_equal(invoice_group_quantity, packing_quantity):
                quantity_check = "matched_by_invoice_group"
            else:
                quantity_check = "mismatch"
        reviews.append(
            {
                "detail_index": index,
                "field_path": f"details[{index}].ItemQuantity",
                "key": _key_dict(key),
                "source_invoice_row": _stringify(_first_value(line, SOURCE_ROW_ALIASES)),
                "source_packing_rows": deepcopy(group.get("source_rows") if isinstance(group, dict) else []),
                "invoice_quantity": _normalize_number(_first_value(line, QUANTITY_ALIASES)),
                "invoice_group_quantity": _format_number(invoice_group_quantity) if invoice_group_quantity is not None else "",
                "packing_quantity": _format_number(packing_quantity) if packing_quantity is not None else "",
                "quantity_check": quantity_check,
                "review_required": quantity_check in {"mismatch", "missing_packing"},
            }
        )
    return reviews


def _line_key(line: dict[str, Any]) -> tuple[str, str, str]:
    return (
        _stringify(_first_value(line, ITEM_ALIASES)),
        _stringify(_first_value(line, PO_ALIASES)),
        _stringify(_first_value(line, PN_ALIASES)),
    )


def _key_dict(key: tuple[str, str, str]) -> dict[str, str]:
    return {"item": key[0], "po": key[1], "pn": key[2]}


def _tuple_key(value: Any) -> tuple[str, str, str]:
    if not isinstance(value, dict):
        return ("", "", "")
    return (_stringify(value.get("item")), _stringify(value.get("po")), _stringify(value.get("pn")))


def _first_value(source: dict[str, Any], aliases: tuple[str, ...]) -> Any:
    for alias in aliases:
        value = source.get(alias)
        if _has_meaningful_value(value):
            return value
    normalized_map = {_normalize_label(key): value for key, value in source.items()}
    for alias in aliases:
        value = normalized_map.get(_normalize_label(alias))
        if _has_meaningful_value(value):
            return value
    return ""


def _normalize_label(value: str) -> str:
    return re.sub(r"[^A-Z0-9/@]+", "", str(value or "").upper())


def _normalize_number(value: Any) -> str:
    number = _parse_number(value)
    if number is None:
        return ""
    return _format_number(number)


def _parse_number(value: Any) -> float | None:
    text = _stringify(value)
    if not text:
        return None
    match = re.search(r"-?\d[\d,]*(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", ""))
    except ValueError:
        return None


def _format_number(value: float | None) -> str:
    if value is None:
        return ""
    if float(value).is_integer():
        return str(int(value))
    return str(value).rstrip("0").rstrip(".")


def _numbers_equal(a: float, b: float) -> bool:
    return abs(a - b) < 0.000001


def _packet_id(source: dict[str, Any], response_payload: dict[str, Any]) -> str:
    for key in ("packet_id", "packetId", "发票号码", "发票号", "InvoiceNo", "invoice_no"):
        value = source.get(key)
        if _has_meaningful_value(value):
            return _stringify(value)
    filename = _stringify(response_payload.get("filename") if isinstance(response_payload, dict) else "")
    stem = filename.rsplit(".", 1)[0]
    return stem


def _source_files(response_payload: dict[str, Any]) -> list[dict[str, str]]:
    filename = _stringify(response_payload.get("filename") if isinstance(response_payload, dict) else "")
    if not filename:
        return []
    return [
        {
            "filename": filename,
            "doc_type": _stringify(response_payload.get("doc_type")),
            "vendor": _stringify(response_payload.get("vendor")),
        }
    ]


def _default_detail() -> dict[str, str]:
    return {field: DEFAULT_FIELD_TEXT for field in CUSTOMS_DETAIL_FIELDS}


def _stringify_or_default(value: Any) -> str:
    text = _stringify(value)
    return text if text else DEFAULT_FIELD_TEXT


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _has_meaningful_value(value: Any) -> bool:
    text = _stringify(value)
    return bool(text and text != DEFAULT_FIELD_TEXT)
