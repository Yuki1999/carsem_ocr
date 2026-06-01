"""Create multitenant foundation schema.

Revision ID: 20260601_0001
Revises:
Create Date: 2026-06-01
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260601_0001"
down_revision = None
branch_labels = None
depends_on = None


TENANT_TABLES = [
    "api_clients",
    "api_keys",
    "templates",
    "llm_configs",
    "tenant_settings",
    "documents",
    "history_records",
    "history_assets",
    "extraction_jobs",
    "submission_drafts",
    "customs_submit_jobs",
    "audit_logs",
    "usage_events",
]

TENANT_RLS_POLICY_NAMES = {
    "api_clients": "tenant_isolation_api_clients",
    "api_keys": "tenant_isolation_api_keys",
    "templates": "tenant_isolation_templates",
    "llm_configs": "tenant_isolation_llm_configs",
    "tenant_settings": "tenant_isolation_tenant_settings",
    "documents": "tenant_isolation_documents",
    "history_records": "tenant_isolation_history_records",
    "history_assets": "tenant_isolation_history_assets",
    "extraction_jobs": "tenant_isolation_extraction_jobs",
    "submission_drafts": "tenant_isolation_submission_drafts",
    "customs_submit_jobs": "tenant_isolation_customs_submit_jobs",
    "audit_logs": "tenant_isolation_audit_logs",
    "usage_events": "tenant_isolation_usage_events",
}


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("plan", sa.String(length=32), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tenants_slug"), "tenants", ["slug"], unique=True)

    op.create_table(
        "users",
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("external_subject", sa.String(length=320), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "tenant_memberships",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_tenant_memberships_tenant_user"),
    )
    op.create_index(op.f("ix_tenant_memberships_tenant_id"), "tenant_memberships", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_tenant_memberships_user_id"), "tenant_memberships", ["user_id"], unique=False)

    op.create_table(
        "api_clients",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("scopes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_api_clients_tenant_id"), "api_clients", ["tenant_id"], unique=False)

    op.create_table(
        "api_keys",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("key_hash", sa.Text(), nullable=False),
        sa.Column("scopes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["api_clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_api_keys_tenant_client", "api_keys", ["tenant_id", "client_id"], unique=False)
    op.create_index(op.f("ix_api_keys_client_id"), "api_keys", ["client_id"], unique=False)
    op.create_index(op.f("ix_api_keys_tenant_id"), "api_keys", ["tenant_id"], unique=False)

    op.create_table(
        "templates",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vendor", sa.String(length=160), nullable=False),
        sa.Column("external_id", sa.String(length=80), nullable=False),
        sa.Column("doc_type", sa.String(length=80), nullable=False),
        sa.Column("llm_prompt", sa.Text(), nullable=False),
        sa.Column("region_rules", sa.Text(), nullable=False),
        sa.Column("backend", sa.String(length=64), nullable=False),
        sa.Column("parse_method", sa.String(length=32), nullable=False),
        sa.Column("lang_list", sa.String(length=80), nullable=False),
        sa.Column("customs_mapping", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "vendor", "doc_type", name="uq_templates_tenant_vendor_doc"),
    )
    op.create_index(op.f("ix_templates_tenant_id"), "templates", ["tenant_id"], unique=False)

    op.create_table(
        "llm_configs",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("model", sa.String(length=200), nullable=False),
        sa.Column("encrypted_api_key", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_llm_configs_tenant_id"), "llm_configs", ["tenant_id"], unique=False)

    op.create_table(
        "tenant_settings",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "key", name="uq_tenant_settings_tenant_key"),
    )
    op.create_index(op.f("ix_tenant_settings_tenant_id"), "tenant_settings", ["tenant_id"], unique=False)

    op.create_table(
        "documents",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filename", sa.String(length=500), nullable=False),
        sa.Column("mime", sa.String(length=200), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(length=128), nullable=False),
        sa.Column("source", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_documents_tenant_id"), "documents", ["tenant_id"], unique=False)

    op.create_table(
        "history_records",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(length=64), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("filename", sa.String(length=500), nullable=False),
        sa.Column("vendor", sa.String(length=160), nullable=False),
        sa.Column("doc_type", sa.String(length=80), nullable=False),
        sa.Column("response_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "external_id", name="uq_history_records_tenant_external"),
    )
    op.create_index("ix_history_records_tenant_created", "history_records", ["tenant_id", "created_at"], unique=False)
    op.create_index(op.f("ix_history_records_document_id"), "history_records", ["document_id"], unique=False)
    op.create_index(op.f("ix_history_records_tenant_id"), "history_records", ["tenant_id"], unique=False)

    op.create_table(
        "history_assets",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("history_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_key", sa.String(length=800), nullable=False),
        sa.Column("display_path", sa.String(length=800), nullable=False),
        sa.Column("mime", sa.String(length=200), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(length=128), nullable=False),
        sa.Column("is_text", sa.Boolean(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["history_record_id"], ["history_records.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "history_record_id", "asset_key", name="uq_history_assets_record_key"),
    )
    op.create_index(op.f("ix_history_assets_history_record_id"), "history_assets", ["history_record_id"], unique=False)
    op.create_index(op.f("ix_history_assets_tenant_id"), "history_assets", ["tenant_id"], unique=False)

    op.create_table(
        "extraction_jobs",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("stage", sa.String(length=80), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("error", sa.Text(), nullable=False),
        sa.Column("request_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("result_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("request_hash", sa.String(length=128), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_extraction_jobs_tenant_created", "extraction_jobs", ["tenant_id", "created_at"], unique=False)
    op.create_index(op.f("ix_extraction_jobs_document_id"), "extraction_jobs", ["document_id"], unique=False)
    op.create_index(op.f("ix_extraction_jobs_tenant_id"), "extraction_jobs", ["tenant_id"], unique=False)

    op.create_table(
        "submission_drafts",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("history_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("draft_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("validation_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["history_record_id"], ["history_records.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_submission_drafts_history_record_id"), "submission_drafts", ["history_record_id"], unique=False)
    op.create_index(op.f("ix_submission_drafts_tenant_id"), "submission_drafts", ["tenant_id"], unique=False)

    op.create_table(
        "customs_submit_jobs",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("draft_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("submit_engine", sa.String(length=64), nullable=False),
        sa.Column("result_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error", sa.Text(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["draft_id"], ["submission_drafts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_customs_submit_jobs_tenant_created", "customs_submit_jobs", ["tenant_id", "created_at"], unique=False)
    op.create_index(op.f("ix_customs_submit_jobs_draft_id"), "customs_submit_jobs", ["draft_id"], unique=False)
    op.create_index(op.f("ix_customs_submit_jobs_tenant_id"), "customs_submit_jobs", ["tenant_id"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("actor_id", sa.String(length=160), nullable=False),
        sa.Column("api_key_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=160), nullable=False),
        sa.Column("resource_type", sa.String(length=120), nullable=False),
        sa.Column("resource_id", sa.String(length=160), nullable=False),
        sa.Column("request_id", sa.String(length=160), nullable=False),
        sa.Column("ip_address", sa.String(length=80), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=False),
        sa.Column("result", sa.String(length=32), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_tenant_created", "audit_logs", ["tenant_id", "created_at"], unique=False)
    op.create_index(op.f("ix_audit_logs_tenant_id"), "audit_logs", ["tenant_id"], unique=False)

    op.create_table(
        "usage_events",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("actor_id", sa.String(length=160), nullable=False),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("counters", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("billable_dimensions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_usage_events_tenant_created", "usage_events", ["tenant_id", "created_at"], unique=False)
    op.create_index(op.f("ix_usage_events_tenant_id"), "usage_events", ["tenant_id"], unique=False)

    for table_name in TENANT_TABLES:
        _enable_tenant_rls(table_name)
    _grant_app_role_privileges()


def downgrade() -> None:
    for table_name in reversed(TENANT_TABLES):
        op.execute(sa.text(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY"))
    op.drop_index(op.f("ix_usage_events_tenant_id"), table_name="usage_events")
    op.drop_index("ix_usage_events_tenant_created", table_name="usage_events")
    op.drop_table("usage_events")
    op.drop_index(op.f("ix_audit_logs_tenant_id"), table_name="audit_logs")
    op.drop_index("ix_audit_logs_tenant_created", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index(op.f("ix_customs_submit_jobs_tenant_id"), table_name="customs_submit_jobs")
    op.drop_index(op.f("ix_customs_submit_jobs_draft_id"), table_name="customs_submit_jobs")
    op.drop_index("ix_customs_submit_jobs_tenant_created", table_name="customs_submit_jobs")
    op.drop_table("customs_submit_jobs")
    op.drop_index(op.f("ix_submission_drafts_tenant_id"), table_name="submission_drafts")
    op.drop_index(op.f("ix_submission_drafts_history_record_id"), table_name="submission_drafts")
    op.drop_table("submission_drafts")
    op.drop_index(op.f("ix_extraction_jobs_tenant_id"), table_name="extraction_jobs")
    op.drop_index(op.f("ix_extraction_jobs_document_id"), table_name="extraction_jobs")
    op.drop_index("ix_extraction_jobs_tenant_created", table_name="extraction_jobs")
    op.drop_table("extraction_jobs")
    op.drop_index(op.f("ix_history_assets_tenant_id"), table_name="history_assets")
    op.drop_index(op.f("ix_history_assets_history_record_id"), table_name="history_assets")
    op.drop_table("history_assets")
    op.drop_index(op.f("ix_history_records_tenant_id"), table_name="history_records")
    op.drop_index(op.f("ix_history_records_document_id"), table_name="history_records")
    op.drop_index("ix_history_records_tenant_created", table_name="history_records")
    op.drop_table("history_records")
    op.drop_index(op.f("ix_documents_tenant_id"), table_name="documents")
    op.drop_table("documents")
    op.drop_index(op.f("ix_tenant_settings_tenant_id"), table_name="tenant_settings")
    op.drop_table("tenant_settings")
    op.drop_index(op.f("ix_llm_configs_tenant_id"), table_name="llm_configs")
    op.drop_table("llm_configs")
    op.drop_index(op.f("ix_templates_tenant_id"), table_name="templates")
    op.drop_table("templates")
    op.drop_index(op.f("ix_api_keys_tenant_id"), table_name="api_keys")
    op.drop_index(op.f("ix_api_keys_client_id"), table_name="api_keys")
    op.drop_index("ix_api_keys_tenant_client", table_name="api_keys")
    op.drop_table("api_keys")
    op.drop_index(op.f("ix_api_clients_tenant_id"), table_name="api_clients")
    op.drop_table("api_clients")
    op.drop_index(op.f("ix_tenant_memberships_user_id"), table_name="tenant_memberships")
    op.drop_index(op.f("ix_tenant_memberships_tenant_id"), table_name="tenant_memberships")
    op.drop_table("tenant_memberships")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    op.drop_index(op.f("ix_tenants_slug"), table_name="tenants")
    op.drop_table("tenants")


def _enable_tenant_rls(table_name: str) -> None:
    policy_name = TENANT_RLS_POLICY_NAMES[table_name]
    op.execute(sa.text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY"))
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {policy_name} ON {table_name}
            USING (tenant_id::text = current_setting('app.current_tenant_id', true))
            WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true))
            """
        )
    )


def _grant_app_role_privileges() -> None:
    op.execute(sa.text("GRANT USAGE ON SCHEMA public TO teleidp_app"))
    op.execute(sa.text("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO teleidp_app"))
    op.execute(sa.text("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO teleidp_app"))
