from fastapi.testclient import TestClient


def test_platform_insights_api_summarizes_queue_templates_review_and_automation(tmp_path, monkeypatch):
    import app.main as main_mod
    from app.history_store import save_history_record
    from app.llm_settings_store import save_llm_settings
    from app.template_store import save_templates

    monkeypatch.setattr(main_mod, "project_root", tmp_path)
    main_mod._EXTRACT_TASKS.clear()
    main_mod._CUSTOMS_SUBMIT_TASKS.clear()
    main_mod._EXTRACT_TASKS.update(
        {
            "extract-running": {"id": "extract-running", "status": "running", "updated_at": "2026-05-22T01:00:00+00:00"},
            "extract-failed": {"id": "extract-failed", "status": "failed", "updated_at": "2026-05-22T01:01:00+00:00"},
        }
    )
    main_mod._CUSTOMS_SUBMIT_TASKS.update(
        {
            "submit-queued": {"id": "submit-queued", "status": "queued", "updated_at": "2026-05-22T01:02:00+00:00"},
        }
    )

    save_templates(
        project_root=tmp_path,
        payload={
            "items": [
                {"vendor": "通用模板", "doc_type": "发票", "llm_prompt": "发票"},
                {"vendor": "Samsung", "doc_type": "发票", "llm_prompt": "Samsung 发票"},
                {"vendor": "Samsung", "doc_type": "报关单", "llm_prompt": "Samsung 报关单"},
            ]
        },
    )
    save_llm_settings(
        project_root=tmp_path,
        payload={
            "active_id": "cfg-1",
            "items": [
                {
                    "id": "cfg-1",
                    "name": "Qwen Production",
                    "provider": "bailian",
                    "llm_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                    "llm_model": "qwen3.5-plus",
                    "llm_api_key": "",
                }
            ],
            "auto_mode_enabled": True,
            "customs_submit_mode": "playwright",
        },
    )
    history = save_history_record(
        project_root=tmp_path,
        response_payload={
            "filename": "DS12650253_IV.xlsx",
            "vendor": "Samsung",
            "doc_type": "发票",
            "submission": {
                "meta": {
                    "required_missing": ["InvoiceNo"],
                    "submit_status": "idle",
                    "packet": {
                        "field_reviews": [{"field": "CustomerName", "review_required": True}],
                        "detail_reviews": [{"detail_index": 0, "review_required": True}],
                    },
                }
            },
        },
        zip_bytes=None,
    )

    client = TestClient(main_mod.app)
    response = client.get("/api/platform-insights")

    assert response.status_code == 200
    payload = response.json()
    assert payload["queue"]["running"] == 1
    assert payload["queue"]["queued"] == 1
    assert payload["queue"]["failed"] == 1
    assert payload["templates"]["common"] == 1
    assert payload["templates"]["vendor"] == 2
    assert payload["templates"]["doc_types"] == ["发票", "报关单"]
    assert payload["review"]["drafts_checked"] == 1
    assert payload["review"]["drafts_with_warnings"] == 1
    assert payload["review"]["missing_fields"] == 1
    assert payload["review"]["review_items"] == 2
    assert payload["automation"]["enabled"] is True
    assert payload["automation"]["submit_mode"] == "playwright"
    assert payload["automation"]["active_model"] == "qwen3.5-plus"
    assert payload["history"]["recent"][0]["id"] == history["id"]
    assert payload["history"]["recent"][0]["review_label"] == "缺失 1 / 复核 2"
    assert any("待复核" in item for item in payload["recommendations"])
