from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class RegionRule:
    field: str
    page_idx: int | None
    bbox: tuple[float, float, float, float]


@dataclass
class TextNode:
    page_idx: int | None
    bbox: tuple[float, float, float, float]
    text: str


def extract_fields_by_regions(middle_json: Any, rules: list[RegionRule]) -> dict[str, str]:
    if not middle_json or not rules:
        return {}
    nodes: list[TextNode] = []
    _walk_nodes(middle_json, nodes, current_page=None)
    if not nodes:
        return {}
    result: dict[str, str] = {}
    for rule in rules:
        matched = []
        for node in nodes:
            if rule.page_idx is not None and node.page_idx is not None and node.page_idx != rule.page_idx:
                continue
            if _bbox_intersects(node.bbox, rule.bbox):
                matched.append(node)
        if not matched:
            continue
        matched.sort(key=lambda n: (n.page_idx if n.page_idx is not None else 10**9, n.bbox[1], n.bbox[0]))
        seen = set()
        chunks: list[str] = []
        for m in matched:
            key = (m.page_idx, m.bbox, m.text)
            if key in seen:
                continue
            seen.add(key)
            chunks.append(m.text)
        value = " ".join(chunks).strip()
        if value:
            result[rule.field] = value
    return result


def _walk_nodes(node: Any, out: list[TextNode], current_page: int | None) -> None:
    if isinstance(node, list):
        for item in node:
            _walk_nodes(item, out, current_page)
        return
    if not isinstance(node, dict):
        return

    page = _page_idx_from_dict(node)
    if page is not None:
        current_page = page

    bbox = _bbox_from_obj(node)
    text = _text_from_dict(node)
    if bbox and text:
        out.append(TextNode(page_idx=current_page, bbox=bbox, text=text))

    for value in node.values():
        _walk_nodes(value, out, current_page)


def _page_idx_from_dict(data: dict[str, Any]) -> int | None:
    for key in ("page_idx", "page_id", "page_no", "page_number", "p_idx"):
        value = data.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return None


def _bbox_from_obj(data: dict[str, Any]) -> tuple[float, float, float, float] | None:
    for key in ("bbox", "box", "position", "rect"):
        box = data.get(key)
        bbox = _to_bbox(box)
        if bbox:
            return bbox
    return None


def _to_bbox(value: Any) -> tuple[float, float, float, float] | None:
    if isinstance(value, (list, tuple)) and len(value) >= 4:
        try:
            x1, y1, x2, y2 = float(value[0]), float(value[1]), float(value[2]), float(value[3])
        except (TypeError, ValueError):
            return None
        if x2 < x1:
            x1, x2 = x2, x1
        if y2 < y1:
            y1, y2 = y2, y1
        return (x1, y1, x2, y2)
    if isinstance(value, dict):
        keys = ("x1", "y1", "x2", "y2")
        if all(k in value for k in keys):
            try:
                x1, y1, x2, y2 = float(value["x1"]), float(value["y1"]), float(value["x2"]), float(value["y2"])
            except (TypeError, ValueError):
                return None
            if x2 < x1:
                x1, x2 = x2, x1
            if y2 < y1:
                y1, y2 = y2, y1
            return (x1, y1, x2, y2)
    return None


def _text_from_dict(data: dict[str, Any]) -> str:
    for key in ("text", "content", "value", "raw_text", "line_text", "span_content"):
        value = data.get(key)
        if isinstance(value, str):
            text = value.strip()
            if text:
                return text
    return ""


def _bbox_intersects(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    inter_w = min(ax2, bx2) - max(ax1, bx1)
    inter_h = min(ay2, by2) - max(ay1, by1)
    return inter_w > 0 and inter_h > 0


def parse_region_rules(raw: str) -> list[RegionRule]:
    import json

    if not raw or not raw.strip():
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"region_rules 不是合法 JSON: {exc.msg}") from exc
    if not isinstance(data, list):
        raise ValueError("region_rules 必须是数组")

    rules: list[RegionRule] = []
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"region_rules[{idx}] 必须是对象")
        field = str(item.get("field", "")).strip()
        if not field:
            raise ValueError(f"region_rules[{idx}].field 不能为空")
        page_idx_raw = item.get("page_idx")
        page_idx: int | None
        if page_idx_raw is None or page_idx_raw == "":
            page_idx = None
        elif isinstance(page_idx_raw, int):
            page_idx = page_idx_raw
        elif isinstance(page_idx_raw, str) and page_idx_raw.isdigit():
            page_idx = int(page_idx_raw)
        else:
            raise ValueError(f"region_rules[{idx}].page_idx 必须是整数或空")

        bbox = _to_bbox(item.get("bbox"))
        if not bbox:
            raise ValueError(f"region_rules[{idx}].bbox 必须是 [x1,y1,x2,y2]")
        rules.append(RegionRule(field=field, page_idx=page_idx, bbox=bbox))
    return rules
