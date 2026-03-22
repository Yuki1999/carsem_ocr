import json
import os
import subprocess
from typing import Any

import requests


MAX_OCR_CONTEXT_CHARS = 120000


def run_llm_extract(
    text: str,
    user_prompt: str,
    targets: list[str] | None = None,
    base_url: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    prompt = (user_prompt or "").strip()
    if not prompt:
        raise ValueError("大模型提示词不能为空")
    source_text = (text or "").strip()
    if not source_text:
        raise ValueError("MinerU 识别结果为空，无法进行大模型提取")
    resolved_base_url = (base_url or os.getenv("LLM_BASE_URL", "")).strip()
    if not resolved_base_url:
        raise ValueError("未配置大模型地址，请设置 LLM_BASE_URL 或在界面填写")
    resolved_model = (model or os.getenv("LLM_MODEL", "")).strip()
    if not resolved_model:
        raise ValueError("未配置大模型模型名，请设置 LLM_MODEL 或在界面填写")
    resolved_api_key = (api_key or os.getenv("LLM_API_KEY", "")).strip()
    endpoint = _build_chat_completions_endpoint(resolved_base_url)
    system_prompt = (
        "你是文档信息抽取助手。"
        "必须严格依据输入文本提取，不得编造。"
        "仅返回 JSON 对象，不要返回 markdown 代码块，不要输出额外说明。"
        "普通字段值使用字符串；若存在多项商品，优先输出数组字段“商品明细”（每项为对象）。"
        "明细项按单据原文选择合适字段，不要强制固定字段名。缺失字段返回空字符串；缺失商品明细返回空数组。"
    )
    target_tip = ""
    if targets:
        target_tip = f"\n目标字段参考：{', '.join(targets)}"
    user_content = (
        f"用户提取要求：\n{prompt}"
        f"{target_tip}\n\n"
        "文档 OCR 文本：\n"
        f"{source_text[:MAX_OCR_CONTEXT_CHARS]}\n\n"
        "请直接输出 JSON 对象。"
    )
    headers = {"Content-Type": "application/json"}
    if resolved_api_key:
        headers["Authorization"] = f"Bearer {resolved_api_key}"
    payload = {
        "model": resolved_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0,
    }
    status_code, response_text = _post_chat_completions(
        endpoint=endpoint,
        headers=headers,
        payload=payload,
        timeout_seconds=timeout_seconds,
    )
    if status_code != 200:
        body = response_text[:1200]
        raise RuntimeError(f"大模型返回非 200: {status_code}, body: {body}")
    try:
        data = json.loads(response_text)
    except ValueError as exc:
        raise RuntimeError("大模型返回非 JSON") from exc
    content = _extract_assistant_content(data)
    detected = _parse_detected_dict(content)
    return {
        "detected": detected,
        "content": content,
        "model": resolved_model,
        "endpoint": endpoint,
    }


def _build_chat_completions_endpoint(base_url: str) -> str:
    normalized = base_url.strip().rstrip("/")
    if normalized.endswith("/chat/completions"):
        return normalized
    if normalized.endswith("/openai"):
        return f"{normalized}/chat/completions"
    if normalized.endswith("/v1"):
        return f"{normalized}/chat/completions"
    if "generativelanguage.googleapis.com" in normalized and "/openai" in normalized:
        return f"{normalized}/chat/completions"
    return f"{normalized}/v1/chat/completions"


def _post_chat_completions(
    endpoint: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout_seconds: int,
) -> tuple[int, str]:
    try:
        response = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=timeout_seconds,
        )
    except requests.RequestException as exc:
        if _should_fallback_to_curl(endpoint=endpoint, exc=exc):
            return _post_chat_completions_with_curl(
                endpoint=endpoint,
                headers=headers,
                payload=payload,
                timeout_seconds=timeout_seconds,
                original_exc=exc,
            )
        raise RuntimeError(f"调用大模型失败: {exc}") from exc
    return response.status_code, response.text


def _should_fallback_to_curl(endpoint: str, exc: requests.RequestException) -> bool:
    if "generativelanguage.googleapis.com" not in str(endpoint or ""):
        return False
    if not isinstance(exc, requests.exceptions.SSLError):
        return False
    message = str(exc)
    return "UNEXPECTED_EOF_WHILE_READING" in message or "SSLEOFError" in message


def _post_chat_completions_with_curl(
    endpoint: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout_seconds: int,
    original_exc: Exception,
) -> tuple[int, str]:
    command = [
        "curl",
        "-sS",
        "-X",
        "POST",
        endpoint,
        "--max-time",
        str(timeout_seconds),
        "-H",
        "Content-Type: application/json",
        "--data-binary",
        json.dumps(payload, ensure_ascii=False),
        "-w",
        "\n__HTTP_STATUS__:%{http_code}",
    ]
    for key, value in headers.items():
        if str(key).lower() == "content-type":
            continue
        command.extend(["-H", f"{key}: {value}"])

    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds + 5,
            check=False,
        )
    except Exception as curl_exc:
        raise RuntimeError(f"调用大模型失败: {original_exc}; curl 回退也失败: {curl_exc}") from curl_exc

    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or f"exit={proc.returncode}").strip()
        raise RuntimeError(f"调用大模型失败: {original_exc}; curl 回退也失败: {detail[:500]}") from original_exc

    marker = "\n__HTTP_STATUS__:"
    stdout = proc.stdout or ""
    index = stdout.rfind(marker)
    if index < 0:
        raise RuntimeError("调用大模型失败: curl 回退响应缺少状态码") from original_exc
    body = stdout[:index].rstrip()
    status_text = stdout[index + len(marker) :].strip()
    try:
        status_code = int(status_text)
    except ValueError as exc:
        raise RuntimeError(f"调用大模型失败: curl 回退状态码异常: {status_text}") from exc
    return status_code, body


def _extract_assistant_content(data: Any) -> str:
    if not isinstance(data, dict):
        raise RuntimeError("大模型响应格式异常")
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            msg = first.get("message")
            if isinstance(msg, dict):
                content = msg.get("content")
                text = _normalize_content(content)
                if text:
                    return text
            text = first.get("text")
            if isinstance(text, str) and text.strip():
                return text.strip()
    output_text = data.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()
    raise RuntimeError("大模型响应中未找到可解析文本")


def _normalize_content(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                text = item.strip()
                if text:
                    parts.append(text)
                continue
            if isinstance(item, dict):
                text_value = item.get("text")
                if isinstance(text_value, str) and text_value.strip():
                    parts.append(text_value.strip())
                    continue
                inner = item.get("content")
                if isinstance(inner, str) and inner.strip():
                    parts.append(inner.strip())
        return "\n".join(parts).strip()
    if isinstance(content, dict):
        text_value = content.get("text")
        if isinstance(text_value, str):
            return text_value.strip()
    return ""


def _parse_detected_dict(content: str) -> dict[str, Any]:
    raw = (content or "").strip()
    if not raw:
        raise RuntimeError("大模型未返回提取结果")
    candidate = _strip_code_fence(raw)
    parsed = _load_json_dict(candidate)
    if parsed is None:
        maybe_json = _extract_first_json_object(candidate)
        if maybe_json:
            parsed = _load_json_dict(maybe_json)
    if parsed is None:
        preview = raw[:300]
        raise RuntimeError(f"大模型输出不是 JSON 对象: {preview}")
    normalized: dict[str, Any] = {}
    for key, value in parsed.items():
        key_text = str(key).strip()
        if not key_text:
            continue
        if value is None:
            normalized[key_text] = ""
            continue
        if isinstance(value, str):
            normalized[key_text] = value.strip()
            continue
        if isinstance(value, (int, float, bool, list, dict)):
            normalized[key_text] = value
            continue
        normalized[key_text] = str(value)
    return normalized


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if len(lines) <= 2:
        return stripped
    if lines[0].startswith("```") and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()
    return stripped


def _load_json_dict(text: str) -> dict[str, Any] | None:
    try:
        data = json.loads(text)
    except Exception:
        return None
    if isinstance(data, dict):
        return data
    return None


def _extract_first_json_object(text: str) -> str | None:
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_str = False
    escaped = False
    for idx in range(start, len(text)):
        ch = text[idx]
        if in_str:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == "\"":
                in_str = False
            continue
        if ch == "\"":
            in_str = True
            continue
        if ch == "{":
            depth += 1
            continue
        if ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : idx + 1]
    return None
