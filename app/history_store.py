from __future__ import annotations

import io
import json
import mimetypes
import shutil
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HISTORY_DIR_NAME = "history"
INDEX_FILE_NAME = "index.json"
META_FILE_NAME = "meta.json"
ZIP_FILE_NAME = "result.zip"
UNZIP_DIR_NAME = "unzipped"
MAX_INDEX_ITEMS = 300
MAX_TEXT_PREVIEW_CHARS = 3000
MAX_TEXT_CONTENT_CHARS = 300000

TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".markdown",
    ".json",
    ".xml",
    ".csv",
    ".yaml",
    ".yml",
    ".log",
    ".html",
    ".htm",
}


def save_history_record(
    project_root: Path,
    response_payload: dict[str, Any],
    zip_bytes: bytes | None,
    extra_assets: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    history_root = _history_root(project_root)
    history_root.mkdir(parents=True, exist_ok=True)

    record_id = uuid.uuid4().hex
    created_at = datetime.now(timezone.utc).isoformat()
    record_dir = history_root / record_id
    record_dir.mkdir(parents=True, exist_ok=True)

    files: list[dict[str, Any]] = []
    zip_available = bool(zip_bytes)
    unzip_dir = record_dir / UNZIP_DIR_NAME
    if zip_available or extra_assets:
        unzip_dir.mkdir(parents=True, exist_ok=True)
    if zip_available:
        zip_path = record_dir / ZIP_FILE_NAME
        zip_path.write_bytes(zip_bytes or b"")
        _extract_zip_to_dir(zip_bytes or b"", unzip_dir)
    if extra_assets:
        _write_extra_assets(unzip_dir, extra_assets)
    if zip_available or extra_assets:
        files = _scan_unzipped_files(unzip_dir)

    summary = _build_summary(
        record_id=record_id,
        created_at=created_at,
        response_payload=response_payload,
        zip_available=zip_available,
        files=files,
    )

    meta = {
        **summary,
        "response": response_payload,
        "files": files,
    }
    _write_json_atomic(record_dir / META_FILE_NAME, meta)

    index_file = history_root / INDEX_FILE_NAME
    index = _read_json(index_file, default=[])
    if not isinstance(index, list):
        index = []
    index = [item for item in index if isinstance(item, dict) and item.get("id") != record_id]
    index.insert(0, summary)
    if len(index) > MAX_INDEX_ITEMS:
        index = index[:MAX_INDEX_ITEMS]
    _write_json_atomic(index_file, index)
    return summary


def list_history_records(project_root: Path, limit: int = 50) -> list[dict[str, Any]]:
    index_file = _history_root(project_root) / INDEX_FILE_NAME
    items = _read_json(index_file, default=[])
    if not isinstance(items, list):
        return []
    cleaned = [item for item in items if isinstance(item, dict)]
    return cleaned[: max(1, min(limit, 200))]


def delete_history_record(project_root: Path, record_id: str) -> bool:
    if not record_id:
        return False
    history_root = _history_root(project_root)
    record_dir = history_root / record_id
    existed = record_dir.exists()

    if existed:
        shutil.rmtree(record_dir, ignore_errors=True)

    index_file = history_root / INDEX_FILE_NAME
    index = _read_json(index_file, default=[])
    if isinstance(index, list):
        filtered = [item for item in index if not (isinstance(item, dict) and item.get("id") == record_id)]
        if len(filtered) != len(index):
            _write_json_atomic(index_file, filtered[:MAX_INDEX_ITEMS])
            existed = True

    return existed


def load_history_record(project_root: Path, record_id: str) -> dict[str, Any] | None:
    if not record_id:
        return None
    meta_file = _history_root(project_root) / record_id / META_FILE_NAME
    data = _read_json(meta_file, default=None)
    if isinstance(data, dict):
        return data
    return None


def update_history_record_response(
    project_root: Path,
    record_id: str,
    response_payload: dict[str, Any],
) -> dict[str, Any] | None:
    if not record_id:
        return None
    history_root = _history_root(project_root)
    record_dir = history_root / record_id
    meta_file = record_dir / META_FILE_NAME
    meta = _read_json(meta_file, default=None)
    if not isinstance(meta, dict):
        return None

    created_at = str(meta.get("created_at") or "")
    if not created_at:
        created_at = datetime.now(timezone.utc).isoformat()
    files = meta.get("files")
    if not isinstance(files, list):
        files = []
    zip_available = (record_dir / ZIP_FILE_NAME).is_file()
    summary = _build_summary(
        record_id=record_id,
        created_at=created_at,
        response_payload=response_payload,
        zip_available=zip_available,
        files=files,
    )

    meta.update(summary)
    meta["response"] = response_payload
    if "files" not in meta or not isinstance(meta.get("files"), list):
        meta["files"] = files
    _write_json_atomic(meta_file, meta)

    index_file = history_root / INDEX_FILE_NAME
    index = _read_json(index_file, default=[])
    if not isinstance(index, list):
        index = []
    replaced = False
    for i, item in enumerate(index):
        if isinstance(item, dict) and item.get("id") == record_id:
            index[i] = summary
            replaced = True
            break
    if not replaced:
        index.insert(0, summary)
    _write_json_atomic(index_file, index[:MAX_INDEX_ITEMS])
    return summary


def get_history_zip_path(project_root: Path, record_id: str) -> Path | None:
    path = _history_root(project_root) / record_id / ZIP_FILE_NAME
    if path.is_file():
        return path
    return None


def get_history_asset_path(project_root: Path, record_id: str, file_path: str) -> Path | None:
    if not record_id or not file_path:
        return None
    base = (_history_root(project_root) / record_id / UNZIP_DIR_NAME).resolve()
    if not base.exists():
        return None
    normalized = _normalize_relative_path(file_path)
    if normalized is None:
        return None
    candidate = (base / normalized).resolve()
    if not str(candidate).startswith(str(base)):
        return None
    if not candidate.is_file():
        return None
    return candidate


def read_history_text_file(project_root: Path, record_id: str, file_path: str) -> dict[str, Any] | None:
    asset = get_history_asset_path(project_root, record_id, file_path)
    if not asset:
        return None
    mime = mimetypes.guess_type(asset.name)[0] or "application/octet-stream"
    if not _is_text_file(asset, mime):
        return None
    raw = asset.read_bytes()
    text = _decode_text(raw)
    truncated = len(text) > MAX_TEXT_CONTENT_CHARS
    content = text[:MAX_TEXT_CONTENT_CHARS]
    return {
        "path": file_path,
        "mime": mime,
        "content": content,
        "truncated": truncated,
        "size": len(raw),
    }


def get_history_primary_text(project_root: Path, record_id: str) -> dict[str, Any] | None:
    detail = load_history_record(project_root, record_id)
    if not detail:
        return None
    files = detail.get("files")
    if isinstance(files, list):
        text_candidates = [x for x in files if isinstance(x, dict) and bool(x.get("is_text")) and isinstance(x.get("path"), str)]
        text_candidates.sort(key=lambda x: x["path"])
        preferred = None
        for item in text_candidates:
            p = item["path"].lower()
            if p == "full.md" or p.endswith("/full.md"):
                preferred = item
                break
        if not preferred and text_candidates:
            preferred = text_candidates[0]
        if preferred:
            text_data = read_history_text_file(project_root, record_id, preferred["path"])
            if text_data and str(text_data.get("content") or "").strip():
                return {
                    "text": str(text_data.get("content") or ""),
                    "source": "asset",
                    "path": preferred["path"],
                    "truncated": bool(text_data.get("truncated")),
                }

    response = detail.get("response")
    if isinstance(response, dict):
        preview = str(response.get("preview") or "")
        if preview.strip():
            return {
                "text": preview,
                "source": "response.preview",
                "path": "",
                "truncated": False,
            }
    return None


def _history_root(project_root: Path) -> Path:
    return project_root / "output" / HISTORY_DIR_NAME


def _extract_zip_to_dir(zip_bytes: bytes, target_dir: Path) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                rel = _normalize_relative_path(info.filename)
                if rel is None:
                    continue
                dest = target_dir / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info, "r") as src, dest.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
    except zipfile.BadZipFile:
        return


def _write_extra_assets(unzip_dir: Path, extra_assets: list[dict[str, Any]]) -> None:
    for item in extra_assets:
        if not isinstance(item, dict):
            continue
        normalized = _normalize_relative_path(str(item.get("path") or ""))
        if normalized is None:
            continue
        content = item.get("content")
        if not isinstance(content, (bytes, bytearray)):
            continue
        dest = unzip_dir / normalized
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(bytes(content))


def _scan_unzipped_files(unzip_dir: Path) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    for path in sorted(unzip_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(unzip_dir).as_posix()
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        is_text = _is_text_file(path, mime)
        is_image = mime.startswith("image/")
        item = {
            "path": rel,
            "size": path.stat().st_size,
            "mime": mime,
            "is_text": is_text,
            "is_image": is_image,
            "preview": "",
        }
        if is_text:
            try:
                item["preview"] = _decode_text(path.read_bytes())[:MAX_TEXT_PREVIEW_CHARS]
            except Exception:
                item["preview"] = ""
        files.append(item)
    return files


def _build_summary(
    record_id: str,
    created_at: str,
    response_payload: dict[str, Any],
    zip_available: bool,
    files: list[dict[str, Any]],
) -> dict[str, Any]:
    detected = response_payload.get("detected")
    hit_count = 0
    if isinstance(detected, dict):
        hit_count = sum(1 for value in detected.values() if _has_meaningful_value(value))
    targets = response_payload.get("targets")
    target_count = len(targets) if isinstance(targets, list) else 0
    return {
        "id": record_id,
        "created_at": created_at,
        "filename": str(response_payload.get("filename") or ""),
        "vendor": str(response_payload.get("vendor") or ""),
        "doc_type": str(response_payload.get("doc_type") or ""),
        "model_version": str(response_payload.get("model_version") or ""),
        "parse_method": str(response_payload.get("parse_method") or ""),
        "fallback_used": bool(response_payload.get("fallback_used")),
        "hit_count": hit_count,
        "target_count": target_count,
        "zip_available": zip_available,
        "files_count": len(files),
    }


def _has_meaningful_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def _normalize_relative_path(raw: str) -> Path | None:
    if not raw:
        return None
    raw = raw.replace("\\", "/").strip()
    p = Path(raw)
    if p.is_absolute():
        return None
    cleaned_parts: list[str] = []
    for part in p.parts:
        if part in ("", "."):
            continue
        if part == "..":
            return None
        cleaned_parts.append(part)
    if not cleaned_parts:
        return None
    return Path(*cleaned_parts)


def _read_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json_atomic(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _is_text_file(path: Path, mime: str) -> bool:
    if path.suffix.lower() in TEXT_EXTENSIONS:
        return True
    return mime.startswith("text/")


def _decode_text(raw: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            return raw.decode(encoding)
        except Exception:
            continue
    return raw.decode("utf-8", errors="ignore")
