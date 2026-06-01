from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.db.session import create_engine_from_settings, create_session_factory, session_scope, set_current_tenant
from app.repositories.history import HistoryRepository
from app.repositories.llm_settings import LlmSettingsRepository
from app.repositories.templates import TemplateRepository
from app.repositories.tenants import get_or_create_tenant
from app.storage.assets import LocalAssetStorage
from app.store.llm_settings_store import normalize_llm_settings
from app.store.template_store import normalize_templates


@dataclass(frozen=True)
class LegacyHistoryRecord:
    record_id: str
    meta: dict[str, Any]
    asset_paths: list[str]


@dataclass(frozen=True)
class LegacyOutput:
    templates: list[dict[str, Any]]
    llm_settings: dict[str, Any]
    history_records: list[LegacyHistoryRecord]


@dataclass(frozen=True)
class ImportSummary:
    tenant_id: str
    tenant_slug: str
    templates: int
    llm_configs: int
    history_records: int
    history_assets: int
    dry_run: bool


def collect_legacy_output(project_root: Path) -> LegacyOutput:
    output_root = project_root / "output"
    templates = normalize_templates(_read_json(output_root / "settings" / "templates.json", None))
    llm_settings = normalize_llm_settings(_read_json(output_root / "settings" / "llm_settings.json", None))
    history_records = []
    index = _read_json(output_root / "history" / "index.json", [])
    if not isinstance(index, list):
        index = []
    for item in index:
        if not isinstance(item, dict):
            continue
        record_id = str(item.get("id") or "").strip()
        if not record_id:
            continue
        record_dir = output_root / "history" / record_id
        meta = _read_json(record_dir / "meta.json", None)
        if not isinstance(meta, dict):
            meta = dict(item)
        asset_paths = [
            path.relative_to(record_dir / "unzipped").as_posix()
            for path in sorted((record_dir / "unzipped").rglob("*"))
            if path.is_file()
        ]
        history_records.append(LegacyHistoryRecord(record_id=record_id, meta=meta, asset_paths=asset_paths))
    return LegacyOutput(templates=templates, llm_settings=llm_settings, history_records=history_records)


def import_legacy_output(
    project_root: Path,
    session,
    tenant_slug: str = "default",
    dry_run: bool = False,
) -> ImportSummary:
    legacy = collect_legacy_output(project_root)
    if dry_run:
        return ImportSummary(
            tenant_id="",
            tenant_slug=tenant_slug,
            templates=len(legacy.templates),
            llm_configs=len(legacy.llm_settings.get("items") or []),
            history_records=len(legacy.history_records),
            history_assets=sum(len(item.asset_paths) for item in legacy.history_records),
            dry_run=True,
        )
    tenant = get_or_create_tenant(session, tenant_slug, name=tenant_slug)
    set_current_tenant(session, str(tenant.id))
    TemplateRepository(session).replace_templates(str(tenant.id), legacy.templates)
    LlmSettingsRepository(session).save_settings(str(tenant.id), legacy.llm_settings)
    storage_root = _storage_root(project_root)
    storage = LocalAssetStorage(storage_root)
    history_repo = HistoryRepository(session, storage)
    for record in legacy.history_records:
        copy_legacy_record_assets(
            project_root=project_root,
            storage=storage,
            tenant_id=str(tenant.id),
            record=record,
        )
        history_repo.upsert_legacy_record(
            tenant_id=str(tenant.id),
            record_id=record.record_id,
            meta=record.meta,
            asset_paths=record.asset_paths,
        )
    return ImportSummary(
        tenant_id=str(tenant.id),
        tenant_slug=tenant.slug,
        templates=len(legacy.templates),
        llm_configs=len(legacy.llm_settings.get("items") or []),
        history_records=len(legacy.history_records),
        history_assets=sum(len(item.asset_paths) for item in legacy.history_records),
        dry_run=False,
    )


def copy_legacy_record_assets(
    *,
    project_root: Path,
    storage: LocalAssetStorage,
    tenant_id: str,
    record: LegacyHistoryRecord,
) -> int:
    copied = 0
    legacy_record_dir = project_root / "output" / "history" / record.record_id
    zip_path = legacy_record_dir / "result.zip"
    if zip_path.is_file():
        storage.put_bytes(
            tenant_id=tenant_id,
            record_id=record.record_id,
            relative_path="result.zip",
            data=zip_path.read_bytes(),
        )
        copied += 1
    for asset_path in record.asset_paths:
        source = legacy_record_dir / "unzipped" / asset_path
        if not source.is_file():
            continue
        storage.put_bytes(
            tenant_id=tenant_id,
            record_id=record.record_id,
            relative_path=f"unzipped/{asset_path}",
            data=source.read_bytes(),
        )
        copied += 1
    return copied


def main() -> None:
    parser = argparse.ArgumentParser(description="Import legacy output/ data into the default PostgreSQL tenant.")
    parser.add_argument("--project-root", default=".", help="Repository/project root containing output/.")
    parser.add_argument("--tenant", default="default", help="Tenant slug to create or update.")
    parser.add_argument("--dry-run", action="store_true", help="Only scan files and print a summary.")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    if args.dry_run:
        summary = import_legacy_output(project_root=project_root, session=None, tenant_slug=args.tenant, dry_run=True)
    else:
        engine = create_engine_from_settings(get_settings())
        factory = create_session_factory(engine)
        with session_scope(factory) as session:
            summary = import_legacy_output(project_root=project_root, session=session, tenant_slug=args.tenant)
    print(json.dumps(summary.__dict__, ensure_ascii=False, indent=2))


def _read_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _storage_root(project_root: Path) -> Path:
    configured = Path(get_settings().local_asset_root)
    if configured.is_absolute():
        return configured
    return project_root / configured


if __name__ == "__main__":
    main()
