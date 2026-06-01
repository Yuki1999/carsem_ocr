import json

from app.commands.import_legacy_output import collect_legacy_output, copy_legacy_record_assets
from app.storage.assets import LocalAssetStorage


def test_collect_legacy_output_counts_settings_history_and_assets(tmp_path):
    settings_dir = tmp_path / "output" / "settings"
    history_dir = tmp_path / "output" / "history" / "record-1"
    unzipped_dir = history_dir / "unzipped"
    settings_dir.mkdir(parents=True)
    unzipped_dir.mkdir(parents=True)
    (settings_dir / "templates.json").write_text(
        json.dumps(
            [
                {
                    "id": "tpl-1",
                    "vendor": "Vendor A",
                    "doc_type": "发票",
                    "llm_prompt": "extract invoice",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (settings_dir / "llm_settings.json").write_text(
        json.dumps(
            {
                "active_id": "llm-1",
                "items": [
                    {
                        "id": "llm-1",
                        "name": "LLM",
                        "provider": "custom",
                        "llm_base_url": "http://example.test/v1",
                        "llm_model": "model-a",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "output" / "history" / "index.json").write_text(
        json.dumps([{"id": "record-1", "filename": "a.pdf"}]),
        encoding="utf-8",
    )
    (history_dir / "meta.json").write_text(
        json.dumps({"id": "record-1", "response": {"filename": "a.pdf"}, "files": []}),
        encoding="utf-8",
    )
    (unzipped_dir / "full.md").write_text("ocr text", encoding="utf-8")

    legacy = collect_legacy_output(tmp_path)

    assert len(legacy.templates) >= 1
    assert len(legacy.llm_settings["items"]) == 1
    assert len(legacy.history_records) == 1
    assert legacy.history_records[0].asset_paths == ["full.md"]
    assert (unzipped_dir / "full.md").is_file()


def test_copy_legacy_record_assets_moves_files_to_tenant_asset_root(tmp_path):
    history_dir = tmp_path / "output" / "history" / "record-1"
    unzipped_dir = history_dir / "unzipped" / "qwen_vision"
    unzipped_dir.mkdir(parents=True)
    (unzipped_dir / "preview.md").write_text("preview", encoding="utf-8")
    (history_dir / "result.zip").write_bytes(b"zip")
    legacy = collect_legacy_output(tmp_path)
    record = legacy.history_records[0] if legacy.history_records else None
    if record is None:
        record = type("LegacyRecord", (), {"record_id": "record-1", "asset_paths": ["qwen_vision/preview.md"]})()
    storage = LocalAssetStorage(tmp_path / "output" / "tenants")

    copied = copy_legacy_record_assets(
        project_root=tmp_path,
        storage=storage,
        tenant_id="tenant-a",
        record=record,
    )

    assert copied == 2
    assert (tmp_path / "output" / "tenants" / "tenant-a" / "history" / "record-1" / "result.zip").is_file()
    assert (
        tmp_path / "output" / "tenants" / "tenant-a" / "history" / "record-1" / "unzipped" / "qwen_vision" / "preview.md"
    ).read_text(encoding="utf-8") == "preview"
