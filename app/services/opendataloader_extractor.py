from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .mineru_extractor import extract_middle_json, json_to_text, normalize_newlines


DEFAULT_OPENDATALOADER_COMMAND = "opendataloader-pdf"
DEFAULT_OPENDATALOADER_FORMAT = "markdown,json,text"


def run_opendataloader_and_read_text(
    *,
    file_name: str,
    file_bytes: bytes,
    timeout_seconds: int = 300,
) -> dict[str, Any]:
    if not file_bytes:
        raise ValueError("上传文件为空")

    command = str(os.getenv("OPENDATALOADER_PDF_COMMAND") or DEFAULT_OPENDATALOADER_COMMAND).strip()
    if not command:
        command = DEFAULT_OPENDATALOADER_COMMAND
    output_format = str(os.getenv("OPENDATALOADER_PDF_OUTPUT_FORMAT") or DEFAULT_OPENDATALOADER_FORMAT).strip()
    extra_args = shlex.split(str(os.getenv("OPENDATALOADER_PDF_EXTRA_ARGS") or "").strip())

    if shutil.which(command) is None:
        raise RuntimeError(
            f"未找到 OpenDataLoader PDF 命令: {command}。"
            "请确认已安装 opendataloader-pdf，并将可执行文件加入 PATH。"
        )

    suffix = Path(file_name).suffix or ".pdf"
    with tempfile.TemporaryDirectory(prefix="odl_pdf_") as tmp_dir:
        tmp_path = Path(tmp_dir)
        input_path = tmp_path / f"input{suffix}"
        output_dir = tmp_path / "output"
        input_path.write_bytes(file_bytes)
        output_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            command,
            str(input_path),
            "--output-dir",
            str(output_dir),
            "--format",
            output_format,
            *extra_args,
        ]
        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=max(30, int(timeout_seconds)),
                check=False,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(f"OpenDataLoader PDF 命令不可用: {command}") from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"OpenDataLoader PDF 解析超时: {timeout_seconds}s") from exc

        if completed.returncode != 0:
            stderr = (completed.stderr or completed.stdout or "").strip()
            raise RuntimeError(f"OpenDataLoader PDF 解析失败: {stderr[:800]}")

        outputs = _read_output_dir(output_dir)
        outputs["command"] = cmd
        outputs["stderr"] = (completed.stderr or "").strip()
        outputs["stdout"] = (completed.stdout or "").strip()
        return outputs


def _read_output_dir(output_dir: Path) -> dict[str, Any]:
    markdown = _read_first_text(output_dir, (".md", ".markdown"))
    text_value = _read_first_text(output_dir, (".txt",))
    parsed_json = _read_first_json(output_dir)
    middle_json = extract_middle_json(parsed_json) if parsed_json is not None else None
    if middle_json is None:
        middle_json = parsed_json

    if not markdown and parsed_json is not None:
        markdown = json_to_text(parsed_json)
    if not text_value:
        if markdown:
            text_value = markdown
        elif parsed_json is not None:
            text_value = json_to_text(parsed_json)

    zip_entries = [
        str(path.relative_to(output_dir)).replace("\\", "/")
        for path in sorted(output_dir.rglob("*"))
        if path.is_file()
    ]
    history_assets = []
    for entry in zip_entries:
        path = output_dir / entry
        try:
            content = path.read_bytes()
        except OSError:
            continue
        history_assets.append(
            {
                "path": f"opendataloader/{entry}",
                "content": content,
            }
        )
    return {
        "text": normalize_newlines(text_value or ""),
        "markdown": normalize_newlines(markdown or text_value or ""),
        "json": parsed_json if parsed_json is not None else {"files": zip_entries},
        "middle_json": middle_json,
        "zip_entries": zip_entries,
        "zip_size": sum((output_dir / entry).stat().st_size for entry in zip_entries) if zip_entries else 0,
        "history_assets": history_assets,
    }


def _read_first_text(root: Path, suffixes: tuple[str, ...]) -> str | None:
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in suffixes:
            continue
        return path.read_text(encoding="utf-8", errors="ignore")
    return None


def _read_first_json(root: Path) -> Any:
    preferred: list[Path] = []
    fallback: list[Path] = []
    for path in sorted(root.rglob("*.json")):
        lower = path.name.lower()
        if any(marker in lower for marker in ("content", "layout", "result", "document")):
            preferred.append(path)
        else:
            fallback.append(path)
    for path in [*preferred, *fallback]:
        try:
            return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except json.JSONDecodeError:
            continue
    return None
