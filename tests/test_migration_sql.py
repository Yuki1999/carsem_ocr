from pathlib import Path


MIGRATION_PATH = Path("app/db/migrations/versions/20260601_0001_multitenant_foundation.py")


def test_initial_migration_enables_rls_for_tenant_tables():
    migration = MIGRATION_PATH.read_text(encoding="utf-8")

    assert "ENABLE ROW LEVEL SECURITY" in migration
    assert "current_setting('app.current_tenant_id'" in migration
    assert "tenant_isolation_templates" in migration
    assert "tenant_isolation_history_records" in migration
    assert "tenant_isolation_extraction_jobs" in migration
