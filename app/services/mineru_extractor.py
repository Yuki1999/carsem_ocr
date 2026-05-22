import io
import json
import os
import time
import uuid
import zipfile
from typing import Any

import requests


OFFICIAL_FILE_URL_BATCH_ENDPOINT = "https://mineru.net/api/v4/file-urls/batch"
OFFICIAL_QUERY_BATCH_RESULT_ENDPOINT = "https://mineru.net/api/v4/extract-results/batch/{batch_id}"
DEFAULT_MINERU_MODEL_VERSION = "vlm"


def run_mineru_and_read_text(
    file_name: str,
    file_bytes: bytes,
    server_url: str = "",
    backend: str = DEFAULT_MINERU_MODEL_VERSION,
    parse_method: str = "auto",
    lang_list: list[str] | None = None,
    timeout_seconds: int = 300,
    api_token: str | None = None,
    model_version: str | None = None,
) -> dict[str, Any]:
    del server_url  # kept for compatibility with existing call sites
    if not file_bytes:
        raise ValueError("上传文件为空")
    resolved_token = (api_token or os.getenv("MINERU_API_TOKEN", "")).strip()
    if not resolved_token:
        raise ValueError("未配置 MinerU 官方 API Token")
    resolved_model_version = _normalize_model_version(model_version or backend)
    del parse_method, lang_list  # official batch flow does not consume these params

    batch_id, data_id, upload_url, file_url = _request_upload_slot(
        token=resolved_token,
        file_name=file_name,
        model_version=resolved_model_version,
        timeout_seconds=timeout_seconds,
    )
    _upload_file(upload_url, file_bytes, timeout_seconds=timeout_seconds)
    batch_result = _poll_batch_result(
        token=resolved_token,
        batch_id=batch_id,
        data_id=data_id,
        timeout_seconds=timeout_seconds,
    )
    zip_url = (batch_result.get("full_zip_url") or batch_result.get("md_zip_url") or "").strip()
    if not zip_url:
        raise RuntimeError("MinerU 官方任务已完成，但未返回结果下载地址")
    outputs = _download_and_parse_zip(zip_url, timeout_seconds=timeout_seconds)
    outputs["zip_url"] = zip_url
    parsed_json = outputs.get("json")
    if not isinstance(parsed_json, dict):
        parsed_json = {"result": parsed_json}
    parsed_json.setdefault("batch_result", batch_result)
    parsed_json.setdefault("batch_id", batch_id)
    parsed_json.setdefault("data_id", data_id)
    parsed_json.setdefault("file_url", file_url)
    outputs["json"] = parsed_json
    if outputs.get("middle_json") is None:
        outputs["middle_json"] = extract_middle_json(parsed_json)
    if not outputs.get("text"):
        outputs["text"] = json_to_text(parsed_json)
    return outputs


def _request_upload_slot(
    token: str,
    file_name: str,
    model_version: str,
    timeout_seconds: int,
) -> tuple[str, str, str, str]:
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    data_id = uuid.uuid4().hex
    payload = {
        "files": [{"name": file_name, "data_id": data_id}],
        "model_version": model_version,
    }
    data = _post_json(
        OFFICIAL_FILE_URL_BATCH_ENDPOINT,
        headers=headers,
        payload=payload,
        timeout_seconds=timeout_seconds,
        error_prefix="申请 MinerU 官方上传地址失败",
    )
    block = data.get("data") if isinstance(data, dict) else None
    if not isinstance(block, dict):
        raise RuntimeError("MinerU 官方上传地址响应缺少 data")
    batch_id = (block.get("batch_id") or "").strip() if isinstance(block.get("batch_id"), str) else ""
    if not batch_id:
        raise RuntimeError("MinerU 官方上传地址响应缺少 batch_id")
    file_urls = block.get("file_urls")
    if not isinstance(file_urls, list) or not file_urls:
        raise RuntimeError("MinerU 官方上传地址响应缺少 file_urls")
    file_url = _extract_file_url(file_urls[0])
    upload_urls = block.get("upload_urls")
    upload_url = _first_str(upload_urls) if isinstance(upload_urls, list) else ""
    if not upload_url:
        upload_url = file_url
    if not upload_url or not file_url:
        raise RuntimeError("MinerU 官方上传地址响应字段不完整")
    return batch_id, data_id, upload_url, file_url


def _upload_file(upload_url: str, file_bytes: bytes, timeout_seconds: int) -> None:
    try:
        response = requests.put(
            upload_url,
            data=file_bytes,
            timeout=max(60, min(timeout_seconds, 180)),
            proxies={"http": None, "https": None},
        )
    except requests.RequestException:
        try:
            response = requests.put(
                upload_url,
                data=file_bytes,
                timeout=max(60, min(timeout_seconds, 180)),
            )
        except requests.RequestException as exc:
            raise RuntimeError(f"上传文件到 MinerU 官方存储失败: {exc}") from exc
    if response.status_code not in (200, 201):
        body = response.text[:1000]
        raise RuntimeError(f"上传文件失败: {response.status_code}, body: {body}")


def _poll_batch_result(token: str, batch_id: str, data_id: str, timeout_seconds: int) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}"}
    deadline = time.time() + max(timeout_seconds, 60)
    last_state = ""
    while time.time() < deadline:
        data = _get_json(
            OFFICIAL_QUERY_BATCH_RESULT_ENDPOINT.format(batch_id=batch_id),
            headers=headers,
            timeout_seconds=timeout_seconds,
            error_prefix="查询 MinerU 官方批量任务失败",
        )
        block = data.get("data") if isinstance(data, dict) else None
        if not isinstance(block, dict):
            raise RuntimeError("MinerU 官方批量任务查询响应缺少 data")
        entry = _pick_batch_result_entry(block.get("extract_result"), data_id=data_id)
        state = str(entry.get("state", "")).strip().lower()
        if state == "done":
            return entry
        if state == "failed":
            err_msg = (entry.get("err_msg") or "").strip() or "未知错误"
            raise RuntimeError(f"MinerU 官方任务失败: {err_msg}")
        last_state = state or last_state
        time.sleep(2)
    raise RuntimeError(f"MinerU 官方任务超时: batch_id={batch_id}, 最后状态={last_state or 'unknown'}")


def _pick_batch_result_entry(raw: Any, data_id: str) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, list):
        return {}
    for item in raw:
        if not isinstance(item, dict):
            continue
        if str(item.get("data_id") or "").strip() == data_id:
            return item
    for item in raw:
        if isinstance(item, dict):
            return item
    return {}


def _download_and_parse_zip(zip_url: str, timeout_seconds: int) -> dict[str, Any]:
    try:
        response = requests.get(
            zip_url,
            timeout=max(60, min(timeout_seconds, 180)),
            proxies={"http": None, "https": None},
        )
    except requests.RequestException:
        try:
            response = requests.get(
                zip_url,
                timeout=max(60, min(timeout_seconds, 180)),
            )
        except requests.RequestException as exc:
            raise RuntimeError(f"下载 MinerU 官方结果失败: {exc}") from exc
    if response.status_code != 200:
        body = response.text[:1000]
        raise RuntimeError(f"下载 MinerU 结果 ZIP 失败: {response.status_code}, body: {body}")
    outputs = _parse_zip_content(response.content)
    outputs["zip_bytes"] = response.content
    outputs["zip_size"] = len(response.content)
    return outputs


def _parse_zip_content(zip_bytes: bytes) -> dict[str, Any]:
    markdown: str | None = None
    middle_json: Any = None
    layout_json: Any = None
    json_entries: list[tuple[str, Any]] = []
    page_margin_items: list[tuple[str, str]] = []
    zip_entries: list[str] = []
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                name = info.filename
                lower = name.lower()
                zip_entries.append(name)
                raw = zf.read(name)
                if lower.endswith(".md") and markdown is None:
                    markdown = _decode_text(raw)
                    continue
                if not lower.endswith(".json"):
                    continue
                parsed = _try_parse_json(raw)
                if parsed is None:
                    continue
                json_entries.append((name, parsed))
                page_margin_items.extend(_extract_page_margin_items(parsed))
                if middle_json is None and "middle" in lower:
                    middle_json = parsed
                if layout_json is None and "layout" in lower:
                    layout_json = parsed
    except zipfile.BadZipFile as exc:
        raise RuntimeError("MinerU 官方返回的结果文件不是有效 ZIP") from exc

    parsed_json = _pick_primary_json(json_entries)
    if parsed_json is None:
        parsed_json = {"zip_entries": [name for name, _ in json_entries]}
    if middle_json is None:
        middle_json = extract_middle_json(parsed_json)
    if middle_json is None and layout_json is not None:
        middle_json = layout_json
    if middle_json is not None:
        page_margin_items.extend(_extract_page_margin_items(middle_json))
    page_margin_items = _dedupe_page_margin_items(page_margin_items)
    base_markdown = markdown.strip() if isinstance(markdown, str) and markdown.strip() else json_to_text(parsed_json)
    text = _append_page_margins_to_markdown(base_markdown, page_margin_items)
    return {
        "text": text,
        "json": parsed_json,
        "middle_json": middle_json,
        "markdown": text,
        "zip_entries": zip_entries,
    }


def _pick_primary_json(items: list[tuple[str, Any]]) -> Any:
    if not items:
        return None
    priority_markers = ("content_list", "middle", "result")
    for marker in priority_markers:
        for name, payload in items:
            if marker in name.lower():
                return payload
    return items[0][1]


def _post_json(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout_seconds: int,
    error_prefix: str,
) -> dict[str, Any]:
    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=max(30, min(timeout_seconds, 120)),
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"{error_prefix}: {exc}") from exc
    return _parse_api_response(response, error_prefix=error_prefix)


def _get_json(
    url: str,
    headers: dict[str, str],
    timeout_seconds: int,
    error_prefix: str,
) -> dict[str, Any]:
    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=max(30, min(timeout_seconds, 120)),
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"{error_prefix}: {exc}") from exc
    return _parse_api_response(response, error_prefix=error_prefix)


def _parse_api_response(response: requests.Response, error_prefix: str) -> dict[str, Any]:
    if response.status_code != 200:
        body = response.text[:1000]
        raise RuntimeError(f"{error_prefix}: {response.status_code}, body: {body}")
    try:
        data = response.json()
    except ValueError as exc:
        raise RuntimeError(f"{error_prefix}: 返回非 JSON") from exc
    code = data.get("code") if isinstance(data, dict) else None
    if code not in (None, 0):
        msg = (data.get("msg") or "").strip() if isinstance(data, dict) else ""
        trace_id = data.get("trace_id") if isinstance(data, dict) else ""
        tail = f", trace_id={trace_id}" if trace_id else ""
        raise RuntimeError(f"{error_prefix}: code={code}, msg={msg}{tail}")
    return data if isinstance(data, dict) else {}


def _extract_file_url(item: Any) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        for key in ("url", "file_url"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def _first_str(items: Any) -> str:
    if not isinstance(items, list):
        return ""
    for item in items:
        if isinstance(item, str) and item.strip():
            return item.strip()
    return ""


def _normalize_model_version(raw: str | None) -> str:
    text = (raw or "").strip()
    if not text:
        return DEFAULT_MINERU_MODEL_VERSION
    lowered = text.lower()
    if "vlm" in lowered:
        return "vlm"
    if "pipeline" in lowered:
        return "pipeline"
    if "hybrid" in lowered:
        return "pipeline"
    return text


def _normalize_language(lang_list: list[str] | None) -> str:
    if not lang_list:
        return "ch"
    for item in lang_list:
        value = str(item or "").strip()
        if not value:
            continue
        first = value.split(",")[0].strip()
        if first:
            return first
    return "ch"


def _decode_text(raw: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            return raw.decode(encoding)
        except Exception:
            continue
    return raw.decode("utf-8", errors="ignore")


def _try_parse_json(raw: bytes) -> Any:
    try:
        return json.loads(_decode_text(raw))
    except Exception:
        return None


def _extract_page_margin_items(data: Any) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    _collect_page_margin_items(data, items)
    return items


def _collect_page_margin_items(node: Any, out: list[tuple[str, str]]) -> None:
    if isinstance(node, dict):
        kind = str(node.get("type") or "").strip().lower()
        if kind in {"page_header", "page_footer"}:
            text = _extract_margin_text(node)
            if text:
                out.append((kind, text))
        for value in node.values():
            _collect_page_margin_items(value, out)
        return
    if isinstance(node, list):
        for item in node:
            _collect_page_margin_items(item, out)


def _extract_margin_text(block: dict[str, Any]) -> str:
    parts: list[str] = []
    _collect_text_nodes(block.get("content"), parts)
    if not parts:
        _collect_text_nodes(block, parts)
    text = " ".join(part.strip() for part in parts if str(part).strip())
    return " ".join(text.split()).strip()


def _dedupe_page_margin_items(items: list[tuple[str, str]]) -> list[tuple[str, str]]:
    deduped: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for kind, text in items:
        cleaned = normalize_newlines(str(text or "")).strip()
        if not cleaned:
            continue
        key = (kind, cleaned)
        if key in seen:
            continue
        deduped.append(key)
        seen.add(key)
    return deduped


def _append_page_margins_to_markdown(markdown_text: str, margin_items: list[tuple[str, str]]) -> str:
    base = normalize_newlines(str(markdown_text or "")).strip()
    if not margin_items:
        return base
    extra_lines: list[str] = []
    for kind, text in margin_items:
        if text in base:
            continue
        label = "页眉" if kind == "page_header" else "页脚"
        extra_lines.append(f"- {label}: {text}")
    if not extra_lines:
        return base
    appendix = "## 页眉页脚\n\n" + "\n".join(extra_lines)
    if not base:
        return appendix
    return f"{base}\n\n{appendix}"


def _find_markdown(data: Any) -> str | None:
    if isinstance(data, dict):
        for key in ("md", "markdown", "markdown_content"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value
        for value in data.values():
            found = _find_markdown(value)
            if found:
                return found
    elif isinstance(data, list):
        for item in data:
            found = _find_markdown(item)
            if found:
                return found
    return None


def extract_middle_json(data: Any) -> Any:
    if isinstance(data, dict):
        for key in ("middle_json", "middle", "middle_data"):
            value = data.get(key)
            if value is not None:
                return value
        for value in data.values():
            found = extract_middle_json(value)
            if found is not None:
                return found
    elif isinstance(data, list):
        for item in data:
            found = extract_middle_json(item)
            if found is not None:
                return found
    return None


def json_to_text(data: Any) -> str:
    md = _find_markdown(data)
    if md:
        return md
    parts: list[str] = []
    _collect_text_nodes(data, parts)
    if parts:
        return "\n".join(parts)
    return json.dumps(data, ensure_ascii=False, indent=2)


def _collect_text_nodes(node: Any, out: list[str]) -> None:
    if isinstance(node, str):
        text = node.strip()
        if text:
            out.append(text)
        return
    if isinstance(node, list):
        for item in node:
            _collect_text_nodes(item, out)
        return
    if isinstance(node, dict):
        text_keys = {"text", "content", "value", "line", "raw_text"}
        for key, value in node.items():
            if key in text_keys and isinstance(value, str):
                text = value.strip()
                if text:
                    out.append(text)
                continue
            _collect_text_nodes(value, out)


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def guess_text_from_outputs(outputs: dict) -> str:
    if outputs.get("markdown"):
        return outputs["markdown"]
    if outputs.get("json"):
        try:
            return json_to_text(outputs["json"])
        except Exception:
            pass
    return outputs.get("text", "")
