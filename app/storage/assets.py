from __future__ import annotations

import hashlib
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any


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


@dataclass(frozen=True)
class AssetRef:
    tenant_id: str
    record_id: str
    relative_path: str
    asset_key: str
    path: Path
    mime: str
    size: int
    checksum: str
    is_text: bool


class LocalAssetStorage:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def put_bytes(self, tenant_id: str, record_id: str, relative_path: str, data: bytes) -> AssetRef:
        normalized = _normalize_relative_path(relative_path)
        tenant_part = _normalize_component(tenant_id, "tenant_id")
        record_part = _normalize_component(record_id, "record_id")
        target = self.root / tenant_part / "history" / record_part / normalized
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return self._asset_ref(tenant_part, record_part, normalized, target)

    def get_path(self, tenant_id: str, record_id: str, relative_path: str) -> Path | None:
        normalized = _normalize_relative_path(relative_path)
        tenant_part = _normalize_component(tenant_id, "tenant_id")
        record_part = _normalize_component(record_id, "record_id")
        base = (self.root / tenant_part / "history" / record_part).resolve()
        candidate = (base / normalized).resolve()
        if not str(candidate).startswith(str(base)):
            return None
        if not candidate.is_file():
            return None
        return candidate

    def read_text(self, tenant_id: str, record_id: str, relative_path: str) -> dict[str, Any] | None:
        path = self.get_path(tenant_id=tenant_id, record_id=record_id, relative_path=relative_path)
        if path is None:
            return None
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if not _is_text_file(path, mime):
            return None
        raw = path.read_bytes()
        text = _decode_text(raw)
        max_chars = 300000
        return {
            "path": relative_path,
            "mime": mime,
            "content": text[:max_chars],
            "truncated": len(text) > max_chars,
            "size": len(raw),
        }

    def _asset_ref(self, tenant_id: str, record_id: str, relative_path: Path, path: Path) -> AssetRef:
        raw = path.read_bytes()
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        return AssetRef(
            tenant_id=tenant_id,
            record_id=record_id,
            relative_path=relative_path.as_posix(),
            asset_key=f"history/{record_id}/{relative_path.as_posix()}",
            path=path,
            mime=mime,
            size=len(raw),
            checksum=hashlib.sha256(raw).hexdigest(),
            is_text=_is_text_file(path, mime),
        )


def _normalize_component(raw: str, name: str) -> str:
    value = str(raw or "").strip()
    if not value or "/" in value or "\\" in value or value in {".", ".."}:
        raise ValueError(f"invalid {name}")
    return value


def _normalize_relative_path(raw: str) -> Path:
    value = str(raw or "").replace("\\", "/").strip()
    if not value:
        raise ValueError("relative_path is required")
    path = Path(value)
    if path.is_absolute():
        raise ValueError("relative_path must not be absolute")
    parts: list[str] = []
    for part in path.parts:
        if part in {"", "."}:
            continue
        if part == "..":
            raise ValueError("relative_path must not contain parent traversal")
        parts.append(part)
    if not parts:
        raise ValueError("relative_path is required")
    return Path(*parts)


def _is_text_file(path: Path, mime: str) -> bool:
    return path.suffix.lower() in TEXT_EXTENSIONS or mime.startswith("text/")


def _decode_text(raw: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")
