from __future__ import annotations

import io
import json
import re
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from .mineru_extractor import normalize_newlines


SPREADSHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
SUPPORTED_EXCEL_SUFFIXES = {".xlsx"}


def run_excel_and_read_text(
    *,
    file_name: str,
    file_bytes: bytes,
) -> dict[str, Any]:
    suffix = Path(str(file_name or "")).suffix.lower()
    if suffix not in SUPPORTED_EXCEL_SUFFIXES:
        raise ValueError("第一版 Excel 识别仅支持 .xlsx 文件")
    if not file_bytes:
        raise ValueError("上传文件为空")

    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as workbook_zip:
            sheets = _read_workbook(workbook_zip)
    except zipfile.BadZipFile as exc:
        raise ValueError("上传的 xlsx 文件无效") from exc

    if not sheets:
        raise ValueError("xlsx 文件未读取到工作表内容")

    preview = _render_workbook_markdown(sheets)
    workbook_json = {"sheets": sheets}
    preview_bytes = preview.encode("utf-8")
    json_bytes = json.dumps(workbook_json, ensure_ascii=False, indent=2).encode("utf-8")
    return {
        "text": normalize_newlines(preview),
        "markdown": normalize_newlines(preview),
        "json": workbook_json,
        "middle_json": None,
        "zip_entries": ["excel/preview.md", "excel/workbook.json"],
        "zip_size": len(preview_bytes) + len(json_bytes),
        "history_assets": [
            {"path": "excel/preview.md", "content": preview_bytes},
            {"path": "excel/workbook.json", "content": json_bytes},
        ],
    }


def _read_workbook(workbook_zip: zipfile.ZipFile) -> list[dict[str, Any]]:
    shared_strings = _read_shared_strings(workbook_zip)
    sheet_defs = _read_sheet_defs(workbook_zip)
    sheets: list[dict[str, Any]] = []
    for index, sheet_def in enumerate(sheet_defs, start=1):
        path = sheet_def["path"]
        if path not in workbook_zip.namelist():
            continue
        rows = _read_sheet_rows(workbook_zip.read(path), shared_strings)
        sheets.append(
            {
                "name": sheet_def.get("name") or f"Sheet{index}",
                "path": path,
                "rows": rows,
            }
        )
    return sheets


def _read_sheet_defs(workbook_zip: zipfile.ZipFile) -> list[dict[str, str]]:
    try:
        workbook_root = ET.fromstring(workbook_zip.read("xl/workbook.xml"))
        rel_root = ET.fromstring(workbook_zip.read("xl/_rels/workbook.xml.rels"))
    except (KeyError, ET.ParseError):
        return _fallback_sheet_defs(workbook_zip)

    rels: dict[str, str] = {}
    for rel in rel_root.findall(f"{{{PACKAGE_REL_NS}}}Relationship"):
        rel_id = str(rel.attrib.get("Id") or "")
        target = str(rel.attrib.get("Target") or "")
        if not rel_id or not target:
            continue
        rels[rel_id] = _resolve_xl_target(target)

    sheet_defs: list[dict[str, str]] = []
    for sheet in workbook_root.findall(f".//{{{SPREADSHEET_NS}}}sheet"):
        name = str(sheet.attrib.get("name") or "").strip()
        rel_id = str(sheet.attrib.get(f"{{{REL_NS}}}id") or "")
        path = rels.get(rel_id, "")
        if path:
            sheet_defs.append({"name": name, "path": path})
    return sheet_defs or _fallback_sheet_defs(workbook_zip)


def _fallback_sheet_defs(workbook_zip: zipfile.ZipFile) -> list[dict[str, str]]:
    paths = [
        name
        for name in workbook_zip.namelist()
        if name.startswith("xl/worksheets/") and name.endswith(".xml")
    ]
    return [{"name": f"Sheet{index}", "path": path} for index, path in enumerate(sorted(paths), start=1)]


def _resolve_xl_target(target: str) -> str:
    normalized = target.replace("\\", "/").lstrip("/")
    if normalized.startswith("xl/"):
        return normalized
    return f"xl/{normalized}"


def _read_shared_strings(workbook_zip: zipfile.ZipFile) -> list[str]:
    try:
        root = ET.fromstring(workbook_zip.read("xl/sharedStrings.xml"))
    except (KeyError, ET.ParseError):
        return []
    return [_node_text(item) for item in root.findall(f"{{{SPREADSHEET_NS}}}si")]


def _read_sheet_rows(sheet_xml: bytes, shared_strings: list[str]) -> list[list[str]]:
    try:
        root = ET.fromstring(sheet_xml)
    except ET.ParseError:
        return []

    rows: list[list[str]] = []
    for row in root.findall(f".//{{{SPREADSHEET_NS}}}row"):
        values_by_col: dict[int, str] = {}
        fallback_col = 0
        for cell in row.findall(f"{{{SPREADSHEET_NS}}}c"):
            ref = str(cell.attrib.get("r") or "")
            col_index = _column_index_from_cell_ref(ref)
            if col_index is None:
                col_index = fallback_col
            fallback_col = max(fallback_col + 1, col_index + 1)
            value = _cell_value(cell, shared_strings)
            if value:
                values_by_col[col_index] = value
        rows.append(_compact_row(values_by_col))
    return _trim_empty_rows(rows)


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = str(cell.attrib.get("t") or "").strip()
    if cell_type == "inlineStr":
        return _node_text(cell.find(f"{{{SPREADSHEET_NS}}}is")).strip()

    raw_value = cell.findtext(f"{{{SPREADSHEET_NS}}}v", default="")
    text = str(raw_value or "").strip()
    if cell_type == "s":
        try:
            return shared_strings[int(text)].strip()
        except (ValueError, IndexError):
            return ""
    if cell_type == "b":
        return "TRUE" if text == "1" else "FALSE" if text == "0" else text
    return text


def _node_text(node: ET.Element | None) -> str:
    if node is None:
        return ""
    parts: list[str] = []
    for child in node.iter():
        if child.tag == f"{{{SPREADSHEET_NS}}}t" and child.text:
            parts.append(child.text)
    return "".join(parts)


def _column_index_from_cell_ref(ref: str) -> int | None:
    match = re.match(r"^([A-Za-z]+)", ref)
    if not match:
        return None
    index = 0
    for char in match.group(1).upper():
        index = index * 26 + (ord(char) - ord("A") + 1)
    return index - 1


def _compact_row(values_by_col: dict[int, str]) -> list[str]:
    if not values_by_col:
        return []
    max_col = max(values_by_col)
    row = [values_by_col.get(index, "") for index in range(max_col + 1)]
    while row and not row[-1]:
        row.pop()
    return row


def _trim_empty_rows(rows: list[list[str]]) -> list[list[str]]:
    while rows and not any(rows[-1]):
        rows.pop()
    return rows


def _render_workbook_markdown(sheets: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for sheet in sheets:
        name = str(sheet.get("name") or "Sheet").strip() or "Sheet"
        rows = sheet.get("rows") if isinstance(sheet.get("rows"), list) else []
        parts.append(f"## {name}")
        if not rows:
            parts.append("")
            continue
        compact_tables = _render_compact_tables(name, rows)
        if compact_tables:
            parts.extend(compact_tables)
            parts.append("### 原始工作表")
        max_cols = max((len(row) for row in rows if isinstance(row, list)), default=0)
        headers = ["行号", *(_column_name(index) for index in range(max_cols))]
        parts.append("| " + " | ".join(headers) + " |")
        parts.append("| " + " | ".join("---" for _ in headers) + " |")
        for row_index, row in enumerate(rows, start=1):
            values = [str(row[index]) if index < len(row) else "" for index in range(max_cols)]
            parts.append("| " + " | ".join([str(row_index), *(_escape_markdown_cell(value) for value in values)]) + " |")
        parts.append("")
    return "\n".join(parts).strip() + "\n"


def _render_compact_tables(sheet_name: str, rows: list[list[str]]) -> list[str]:
    tables: list[str] = []
    row_index = 0
    while row_index < len(rows):
        header_map = _detail_header_map(rows[row_index])
        if not header_map:
            row_index += 1
            continue
        data_rows: list[tuple[int, list[str]]] = []
        cursor = row_index + 1
        while cursor < len(rows):
            row = rows[cursor]
            if _detail_header_map(row):
                break
            if _row_contains_total_marker(row):
                break
            values = [str(row[col]).strip() if col < len(row) else "" for col, _ in header_map]
            if not any(values):
                break
            if sum(1 for value in values if value) >= 2:
                data_rows.append((cursor + 1, values))
            cursor += 1
        if data_rows:
            labels = [label for _, label in header_map]
            tables.append(f"### 结构化表格：{sheet_name} 第 {row_index + 1} 行")
            tables.append("| " + " | ".join(["源行", *labels]) + " |")
            tables.append("| " + " | ".join("---" for _ in ["源行", *labels]) + " |")
            for source_row, values in data_rows:
                tables.append(
                    "| "
                    + " | ".join([str(source_row), *(_escape_markdown_cell(value) for value in values)])
                    + " |"
                )
            tables.append("")
        row_index = max(cursor, row_index + 1)
    return tables


def _detail_header_map(row: list[str]) -> list[tuple[int, str]]:
    labels: list[tuple[int, str]] = []
    for col_index, value in enumerate(row):
        label = str(value or "").strip()
        if not label:
            continue
        normalized = _normalize_header_label(label)
        if normalized in DETAIL_TABLE_HEADER_LABELS:
            labels.append((col_index, label))
    normalized_labels = {_normalize_header_label(label) for _, label in labels}
    if "ITEM" not in normalized_labels:
        return []
    if len(labels) < 3:
        return []
    return labels


def _normalize_header_label(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).upper()


DETAIL_TABLE_HEADER_LABELS = {
    "ITEM",
    "P/O",
    "PO",
    "P/N",
    "PN",
    "SAMSUNG P/N",
    "PC",
    "@RMB/1000",
    "@USD/1000",
    "RMB",
    "USD",
}


def _row_contains_total_marker(row: list[str]) -> bool:
    for value in row:
        text = str(value or "").strip().upper()
        if text.startswith("TOTAL"):
            return True
    return False


def _column_name(index: int) -> str:
    index += 1
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(ord("A") + remainder) + name
    return name


def _escape_markdown_cell(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ").strip()
