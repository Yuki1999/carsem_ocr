from __future__ import annotations

import io
import mimetypes
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import HistoryAsset, HistoryRecord
from app.storage.assets import LocalAssetStorage
from app.store.history_store import _build_summary, _scan_unzipped_files


class HistoryRepository:
    def __init__(self, session: Session, storage: LocalAssetStorage) -> None:
        self.session = session
        self.storage = storage

    def save_history_record(
        self,
        *,
        tenant_id: str,
        response_payload: dict[str, Any],
        zip_bytes: bytes | None,
        extra_assets: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        record_id = uuid.uuid4().hex
        files: list[dict[str, Any]] = []
        zip_available = bool(zip_bytes)
        if zip_bytes:
            self.storage.put_bytes(tenant_id, record_id, "result.zip", zip_bytes)
            files.extend(self._write_zip_assets(tenant_id, record_id, zip_bytes))
        for item in extra_assets or []:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, (bytes, bytearray)):
                continue
            relative_path = str(item.get("path") or "").strip()
            if not relative_path:
                continue
            ref = self.storage.put_bytes(tenant_id, record_id, f"unzipped/{relative_path}", bytes(content))
            files.append(_asset_file_payload(ref.relative_path.removeprefix("unzipped/"), ref.path))
        files = _dedupe_files(files)
        created_at = datetime.now(timezone.utc).isoformat()
        summary = _build_summary(
            record_id=record_id,
            created_at=created_at,
            response_payload=response_payload,
            zip_available=zip_available,
            files=files,
        )
        meta = {**summary, "response": response_payload, "files": files}
        record = HistoryRecord(
            tenant_id=uuid.UUID(tenant_id),
            external_id=record_id,
            filename=str(summary.get("filename") or ""),
            vendor=str(summary.get("vendor") or ""),
            doc_type=str(summary.get("doc_type") or ""),
            response_payload=response_payload,
            summary=summary,
        )
        self.session.add(record)
        self.session.flush()
        self._replace_asset_rows(tenant_id=tenant_id, record=row_id(record), record_id=record_id, files=files)
        return summary

    def upsert_legacy_record(
        self,
        *,
        tenant_id: str,
        record_id: str,
        meta: dict[str, Any],
        asset_paths: list[str],
    ) -> None:
        tenant_uuid = uuid.UUID(tenant_id)
        response_payload = meta.get("response") if isinstance(meta.get("response"), dict) else {}
        files = meta.get("files") if isinstance(meta.get("files"), list) else []
        if not files:
            files = [{"path": path, "size": 0, "mime": mimetypes.guess_type(path)[0] or "", "is_text": _looks_text(path)} for path in asset_paths]
        summary = dict(meta)
        summary.pop("response", None)
        summary.pop("files", None)
        summary.setdefault("id", record_id)
        summary.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        summary.setdefault("filename", str(response_payload.get("filename") or ""))
        existing = self.session.execute(
            select(HistoryRecord).where(HistoryRecord.tenant_id == tenant_uuid, HistoryRecord.external_id == record_id)
        ).scalar_one_or_none()
        if existing is None:
            existing = HistoryRecord(tenant_id=tenant_uuid, external_id=record_id)
            self.session.add(existing)
        existing.filename = str(summary.get("filename") or "")
        existing.vendor = str(summary.get("vendor") or response_payload.get("vendor") or "")
        existing.doc_type = str(summary.get("doc_type") or response_payload.get("doc_type") or "")
        existing.response_payload = response_payload
        existing.summary = summary
        self.session.flush()
        self._replace_asset_rows(tenant_id=tenant_id, record=row_id(existing), record_id=record_id, files=files)

    def list_history_records(self, tenant_id: str, limit: int = 50) -> list[dict[str, Any]]:
        rows = self.session.execute(
            select(HistoryRecord)
            .where(HistoryRecord.tenant_id == uuid.UUID(tenant_id))
            .order_by(HistoryRecord.created_at.desc())
            .limit(max(1, min(limit, 200)))
        ).scalars()
        return [dict(row.summary or {}) for row in rows]

    def load_history_record(self, tenant_id: str, record_id: str) -> dict[str, Any] | None:
        row = self._load_record(tenant_id, record_id)
        if row is None:
            return None
        files = self._list_asset_files(tenant_id=tenant_id, history_record_id=row_id(row))
        return {**dict(row.summary or {}), "response": row.response_payload or {}, "files": files}

    def update_history_record_response(self, tenant_id: str, record_id: str, response_payload: dict[str, Any]) -> dict[str, Any] | None:
        row = self._load_record(tenant_id, record_id)
        if row is None:
            return None
        files = self._list_asset_files(tenant_id=tenant_id, history_record_id=row_id(row))
        created_at = str((row.summary or {}).get("created_at") or datetime.now(timezone.utc).isoformat())
        zip_available = self.get_history_zip_path(tenant_id, record_id) is not None
        summary = _build_summary(
            record_id=record_id,
            created_at=created_at,
            response_payload=response_payload,
            zip_available=zip_available,
            files=files,
        )
        row.response_payload = response_payload
        row.summary = summary
        row.filename = str(summary.get("filename") or "")
        row.vendor = str(summary.get("vendor") or "")
        row.doc_type = str(summary.get("doc_type") or "")
        self.session.flush()
        return summary

    def delete_history_record(self, tenant_id: str, record_id: str) -> bool:
        row = self._load_record(tenant_id, record_id)
        if row is None:
            return False
        self.session.delete(row)
        self.session.flush()
        return True

    def get_history_zip_path(self, tenant_id: str, record_id: str) -> Path | None:
        return self.storage.get_path(tenant_id, record_id, "result.zip")

    def get_history_asset_path(self, tenant_id: str, record_id: str, file_path: str) -> Path | None:
        return self.storage.get_path(tenant_id, record_id, f"unzipped/{file_path}")

    def read_history_text_file(self, tenant_id: str, record_id: str, file_path: str) -> dict[str, Any] | None:
        data = self.storage.read_text(tenant_id, record_id, f"unzipped/{file_path}")
        if data is not None:
            data["path"] = file_path
        return data

    def _load_record(self, tenant_id: str, record_id: str) -> HistoryRecord | None:
        return self.session.execute(
            select(HistoryRecord).where(HistoryRecord.tenant_id == uuid.UUID(tenant_id), HistoryRecord.external_id == record_id)
        ).scalar_one_or_none()

    def _write_zip_assets(self, tenant_id: str, record_id: str, zip_bytes: bytes) -> list[dict[str, Any]]:
        files: list[dict[str, Any]] = []
        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                for info in zf.infolist():
                    if info.is_dir():
                        continue
                    with zf.open(info, "r") as src:
                        ref = self.storage.put_bytes(tenant_id, record_id, f"unzipped/{info.filename}", src.read())
                    files.append(_asset_file_payload(ref.relative_path.removeprefix("unzipped/"), ref.path))
        except zipfile.BadZipFile:
            return []
        return files

    def _replace_asset_rows(self, *, tenant_id: str, record: uuid.UUID, record_id: str, files: list[dict[str, Any]]) -> None:
        tenant_uuid = uuid.UUID(tenant_id)
        self.session.execute(
            delete(HistoryAsset).where(HistoryAsset.tenant_id == tenant_uuid, HistoryAsset.history_record_id == record)
        )
        for item in files:
            path = str(item.get("path") or "")
            self.session.add(
                HistoryAsset(
                    tenant_id=tenant_uuid,
                    history_record_id=record,
                    asset_key=f"history/{record_id}/unzipped/{path}",
                    display_path=path,
                    mime=str(item.get("mime") or ""),
                    size=int(item.get("size") or 0),
                    checksum=str(item.get("checksum") or ""),
                    is_text=bool(item.get("is_text")),
                )
            )

    def _list_asset_files(self, *, tenant_id: str, history_record_id: uuid.UUID) -> list[dict[str, Any]]:
        rows = self.session.execute(
            select(HistoryAsset)
            .where(HistoryAsset.tenant_id == uuid.UUID(tenant_id), HistoryAsset.history_record_id == history_record_id)
            .order_by(HistoryAsset.display_path)
        ).scalars()
        return [
            {
                "path": row.display_path,
                "size": row.size,
                "mime": row.mime,
                "is_text": row.is_text,
                "is_image": row.mime.startswith("image/"),
                "preview": "",
            }
            for row in rows
        ]


def row_id(row: HistoryRecord) -> uuid.UUID:
    return row.id


def _asset_file_payload(display_path: str, path: Path) -> dict[str, Any]:
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return {
        "path": display_path,
        "size": path.stat().st_size if path.is_file() else 0,
        "mime": mime,
        "is_text": _looks_text(display_path) or mime.startswith("text/"),
        "is_image": mime.startswith("image/"),
        "preview": "",
    }


def _dedupe_files(files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}
    for item in files:
        path = str(item.get("path") or "")
        if path:
            deduped[path] = item
    return [deduped[path] for path in sorted(deduped)]


def _looks_text(path: str) -> bool:
    suffix = Path(path).suffix.lower()
    return suffix in {".txt", ".md", ".markdown", ".json", ".xml", ".csv", ".yaml", ".yml", ".log", ".html", ".htm"}
