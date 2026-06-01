from app.db.models import Base


def test_required_tables_exist():
    tables = set(Base.metadata.tables)

    assert "tenants" in tables
    assert "users" in tables
    assert "tenant_memberships" in tables
    assert "api_clients" in tables
    assert "api_keys" in tables
    assert "templates" in tables
    assert "llm_configs" in tables
    assert "tenant_settings" in tables
    assert "history_records" in tables
    assert "history_assets" in tables
    assert "extraction_jobs" in tables
    assert "customs_submit_jobs" in tables
    assert "submission_drafts" in tables
    assert "audit_logs" in tables
    assert "usage_events" in tables


def test_tenant_owned_tables_have_tenant_id():
    tenant_owned = [
        "api_clients",
        "api_keys",
        "templates",
        "llm_configs",
        "tenant_settings",
        "history_records",
        "history_assets",
        "extraction_jobs",
        "customs_submit_jobs",
        "submission_drafts",
        "audit_logs",
        "usage_events",
    ]

    for table_name in tenant_owned:
        assert "tenant_id" in Base.metadata.tables[table_name].columns


def test_api_keys_store_hash_and_scopes_not_plain_secret():
    columns = Base.metadata.tables["api_keys"].columns

    assert "key_hash" in columns
    assert "scopes" in columns
    assert "plain_key" not in columns
