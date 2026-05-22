from __future__ import annotations

import base64
import json
import mimetypes
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .llm_extract import (
    _build_chat_completions_endpoint,
    _extract_assistant_content,
    _extract_first_json_object,
    _load_json_dict,
    _post_chat_completions,
    _strip_code_fence,
)


SUPPORTED_QWEN_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif"}
DEFAULT_DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_QWEN_MAX_IMAGE_COUNT = 12
DEFAULT_QWEN_TIMEOUT_SECONDS = 180


def validate_qwen_vision_suffix(file_name: str) -> None:
    suffix = Path(str(file_name or "")).suffix.lower()
    if suffix not in SUPPORTED_QWEN_SUFFIXES:
        raise ValueError("Qwen3.5-Plus 端到端仅支持 PDF 和图片文件")


def render_qwen_input_images(*, file_name: str, file_bytes: bytes) -> list[dict[str, Any]]:
    validate_qwen_vision_suffix(file_name)
    if not file_bytes:
        raise ValueError("上传文件为空")
    suffix = Path(file_name).suffix.lower()
    if suffix == ".pdf":
        return _render_pdf_images(file_bytes=file_bytes)
    return [_build_image_input(name=Path(file_name).name or f"input{suffix or '.png'}", content=file_bytes)]


def build_qwen_vision_messages(
    *,
    vendor: str,
    doc_type: str,
    llm_prompt: str,
    image_inputs: list[dict[str, Any]],
    targets: list[str] | None = None,
) -> list[dict[str, Any]]:
    if not image_inputs:
        raise ValueError("Qwen3.5-Plus 输入图像为空")
    field_hint = ""
    if targets:
        field_hint = f"\n目标字段参考：{', '.join(str(item).strip() for item in targets if str(item).strip())}"
    user_prompt = (
        f"厂商：{str(vendor or '').strip() or '-'}\n"
        f"单据类型：{str(doc_type or '').strip() or '-'}\n"
        f"用户提取要求：{str(llm_prompt or '').strip()}{field_hint}\n"
        "请基于图片中可见内容直接完成 OCR 与信息抽取。"
        "只输出一个 JSON 对象，不要输出解释，不要输出 markdown 代码块。"
        "普通字段返回字符串；多项明细放在数组字段中。"
        "字段缺失时返回空字符串；缺失的明细数组返回空数组。"
    )
    content = [{"type": "text", "text": user_prompt}]
    for item in image_inputs:
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": item["data_url"]},
            }
        )
    return [
        {
            "role": "system",
            "content": "你是单证 OCR 与字段抽取助手。必须严格依据图像中可见内容提取，不得编造。只返回 JSON 对象。",
        },
        {
            "role": "user",
            "content": content,
        },
    ]


def parse_qwen_vision_response(raw_content: str) -> dict[str, Any]:
    raw = str(raw_content or "").strip()
    if not raw:
        raise RuntimeError("Qwen3.5-Plus 未返回提取结果")
    candidate = _strip_code_fence(raw)
    parsed = _load_json_dict(candidate)
    if parsed is None:
        maybe_json = _extract_first_json_object(candidate)
        if maybe_json:
            parsed = _load_json_dict(maybe_json)
    if parsed is None:
        raise RuntimeError(f"Qwen3.5-Plus 输出不是 JSON 对象: {raw[:300]}")
    normalized: dict[str, Any] = {}
    for key, value in parsed.items():
        key_text = str(key).strip()
        if not key_text:
            continue
        if value is None:
            normalized[key_text] = ""
        elif isinstance(value, str):
            normalized[key_text] = value.strip()
        elif isinstance(value, (int, float, bool, list, dict)):
            normalized[key_text] = value
        else:
            normalized[key_text] = str(value)
    return normalized


def run_qwen_vision_extract(
    *,
    file_name: str,
    file_bytes: bytes,
    vendor: str,
    doc_type: str,
    llm_prompt: str,
    base_url: str,
    model: str,
    api_key: str,
    targets: list[str] | None = None,
    timeout_seconds: int = DEFAULT_QWEN_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    resolved_base_url = str(base_url or os.getenv("LLM_BASE_URL", "")).strip() or DEFAULT_DASHSCOPE_BASE_URL
    resolved_model = str(model or os.getenv("LLM_MODEL", "")).strip()
    if not resolved_model:
        raise ValueError("未配置 Qwen3.5-Plus 模型名，请设置 LLM_MODEL 或在界面填写")
    resolved_api_key = str(api_key or os.getenv("LLM_API_KEY", "")).strip()
    if not resolved_api_key:
        raise ValueError("未配置 Qwen3.5-Plus API Key，请设置 LLM_API_KEY 或在界面填写")

    image_inputs = render_qwen_input_images(file_name=file_name, file_bytes=file_bytes)
    messages = build_qwen_vision_messages(
        vendor=vendor,
        doc_type=doc_type,
        llm_prompt=llm_prompt,
        image_inputs=image_inputs,
        targets=targets,
    )
    response_data, endpoint = _post_qwen_chat_completion(
        base_url=resolved_base_url,
        model=resolved_model,
        api_key=resolved_api_key,
        messages=messages,
        timeout_seconds=timeout_seconds,
    )
    content = _extract_assistant_content(response_data)
    detected = parse_qwen_vision_response(content)
    preview = json.dumps(detected, ensure_ascii=False, indent=2)
    return {
        "detected": detected,
        "content": content,
        "model": resolved_model,
        "endpoint": endpoint,
        "preview": preview,
        "markdown": f"```json\n{preview}\n```",
        "history_assets": _build_history_assets(
            image_inputs=image_inputs,
            response_data=response_data,
            preview=preview,
            raw_content=content,
        ),
    }


def _post_qwen_chat_completion(
    *,
    base_url: str,
    model: str,
    api_key: str,
    messages: list[dict[str, Any]],
    timeout_seconds: int,
) -> tuple[dict[str, Any], str]:
    endpoint = _build_chat_completions_endpoint(base_url)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0,
    }
    status_code, response_text = _post_chat_completions(
        endpoint=endpoint,
        headers=headers,
        payload=payload,
        timeout_seconds=timeout_seconds,
    )
    if status_code != 200:
        raise RuntimeError(f"Qwen3.5-Plus 返回非 200: {status_code}, body: {response_text[:1200]}")
    try:
        data = json.loads(response_text)
    except ValueError as exc:
        raise RuntimeError("Qwen3.5-Plus 返回非 JSON") from exc
    return data, endpoint


def _build_history_assets(
    *,
    image_inputs: list[dict[str, Any]],
    response_data: dict[str, Any],
    preview: str,
    raw_content: str,
) -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = [
        {
            "path": "qwen_vision/raw-response.json",
            "content": json.dumps(response_data, ensure_ascii=False, indent=2).encode("utf-8"),
        },
        {
            "path": "qwen_vision/preview.md",
            "content": preview.encode("utf-8"),
        },
        {
            "path": "qwen_vision/raw-content.txt",
            "content": str(raw_content or "").encode("utf-8"),
        },
    ]
    for index, item in enumerate(image_inputs, start=1):
        suffix = Path(item["name"]).suffix.lower() or _suffix_for_mime(item["mime_type"])
        page_name = f"page-{index}{suffix}"
        assets.append(
            {
                "path": f"qwen_vision/pages/{page_name}",
                "content": item["content"],
            }
        )
    return assets


def _render_pdf_images(*, file_bytes: bytes) -> list[dict[str, Any]]:
    command = shutil.which("pdftoppm")
    if command:
        try:
            return _render_pdf_images_with_pdftoppm(file_bytes=file_bytes, command=command)
        except OSError as exc:
            if exc.errno != 13:
                raise
        except RuntimeError:
            pass
    return _render_pdf_images_with_pypdfium2(file_bytes=file_bytes)


def _render_pdf_images_with_pdftoppm(*, file_bytes: bytes, command: str) -> list[dict[str, Any]]:
    with tempfile.TemporaryDirectory(prefix="qwen_pdf_") as tmp_dir:
        tmp_path = Path(tmp_dir)
        input_path = tmp_path / "input.pdf"
        output_prefix = tmp_path / "page"
        input_path.write_bytes(file_bytes)
        proc = subprocess.run(
            [command, "-png", str(input_path), str(output_prefix)],
            capture_output=True,
            text=True,
            timeout=240,
            check=False,
        )
        if proc.returncode != 0:
            message = (proc.stderr or proc.stdout or "").strip().replace("\n", " ")
            raise RuntimeError(f"Qwen3.5-Plus PDF 转图片失败: {message[:300]}")
        images = []
        for image_path in sorted(tmp_path.glob("page-*.png"), key=lambda path: path.name):
            images.append(_build_image_input(name=image_path.name, content=image_path.read_bytes()))
        if not images:
            raise RuntimeError("Qwen3.5-Plus PDF 转图片失败: 未生成页面图像")
        if len(images) > DEFAULT_QWEN_MAX_IMAGE_COUNT:
            return images[:DEFAULT_QWEN_MAX_IMAGE_COUNT]
        return images


def _render_pdf_images_with_pypdfium2(*, file_bytes: bytes) -> list[dict[str, Any]]:
    try:
        import pypdfium2 as pdfium
    except Exception as exc:
        raise RuntimeError("Qwen3.5-Plus PDF 转图片失败: 未安装 pdftoppm，且 pypdfium2 不可用") from exc

    images: list[dict[str, Any]] = []
    pdf = None
    try:
        pdf = pdfium.PdfDocument(file_bytes)
        page_count = min(len(pdf), DEFAULT_QWEN_MAX_IMAGE_COUNT)
        for index in range(page_count):
            page = pdf[index]
            bitmap = page.render(scale=2)
            pil_image = bitmap.to_pil()
            with tempfile.NamedTemporaryFile(suffix=".png") as tmp_file:
                pil_image.save(tmp_file.name, format="PNG")
                images.append(_build_image_input(name=f"page-{index + 1}.png", content=Path(tmp_file.name).read_bytes()))
            page.close()
        if not images:
            raise RuntimeError("Qwen3.5-Plus PDF 转图片失败: 未生成页面图像")
        return images
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Qwen3.5-Plus PDF 转图片失败: {str(exc)[:300]}") from exc
    finally:
        if pdf is not None:
            try:
                pdf.close()
            except Exception:
                pass


def _build_image_input(*, name: str, content: bytes) -> dict[str, Any]:
    mime_type = mimetypes.guess_type(name)[0] or "image/png"
    data_url = f"data:{mime_type};base64,{base64.b64encode(content).decode('ascii')}"
    return {
        "name": name,
        "mime_type": mime_type,
        "data_url": data_url,
        "content": content,
    }


def _suffix_for_mime(mime_type: str) -> str:
    return {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/bmp": ".bmp",
        "image/tiff": ".tiff",
    }.get(str(mime_type or "").lower(), ".png")
