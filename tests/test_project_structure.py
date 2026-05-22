def test_backend_structure_imports():
    from app.api.app import app
    from app.services.customs_submission import build_submission_draft
    from app.store.llm_settings_store import normalize_llm_settings

    assert app is not None
    assert callable(build_submission_draft)
    assert callable(normalize_llm_settings)
