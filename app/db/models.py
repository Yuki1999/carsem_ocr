from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UuidPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class TenantOwnedMixin:
    @declared_attr
    def tenant_id(cls) -> Mapped[uuid.UUID]:
        return mapped_column(
            PG_UUID(as_uuid=True),
            ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )


class Tenant(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tenants"

    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    plan: Mapped[str] = mapped_column(String(32), nullable=False, default="standard")


class User(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    password_hash: Mapped[str] = mapped_column(Text, nullable=False, default="")
    external_subject: Mapped[str] = mapped_column(String(320), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")


class TenantMembership(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tenant_memberships"
    __table_args__ = (UniqueConstraint("tenant_id", "user_id", name="uq_tenant_memberships_tenant_user"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(64), nullable=False, default="member")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")


class ApiClient(UuidPrimaryKeyMixin, TenantOwnedMixin, TimestampMixin, Base):
    __tablename__ = "api_clients"

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    scopes: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class ApiKey(UuidPrimaryKeyMixin, TenantOwnedMixin, TimestampMixin, Base):
    __tablename__ = "api_keys"
    __table_args__ = (Index("ix_api_keys_tenant_client", "tenant_id", "client_id"),)

    client_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("api_clients.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    key_hash: Mapped[str] = mapped_column(Text, nullable=False)
    scopes: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Template(UuidPrimaryKeyMixin, TenantOwnedMixin, TimestampMixin, Base):
    __tablename__ = "templates"
    __table_args__ = (UniqueConstraint("tenant_id", "vendor", "doc_type", name="uq_templates_tenant_vendor_doc"),)

    vendor: Mapped[str] = mapped_column(String(160), nullable=False)
    external_id: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    doc_type: Mapped[str] = mapped_column(String(80), nullable=False)
    llm_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    region_rules: Mapped[str] = mapped_column(Text, nullable=False, default="")
    backend: Mapped[str] = mapped_column(String(64), nullable=False, default="vlm")
    parse_method: Mapped[str] = mapped_column(String(32), nullable=False, default="auto")
    lang_list: Mapped[str] = mapped_column(String(80), nullable=False, default="en")
    customs_mapping: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class LlmConfig(UuidPrimaryKeyMixin, TenantOwnedMixin, TimestampMixin, Base):
    __tablename__ = "llm_configs"

    external_id: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(String(200), nullable=False)
    encrypted_api_key: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    is_active: Mapped[bool] = mapped_column(nullable=False, default=False)


class TenantSetting(UuidPrimaryKeyMixin, TenantOwnedMixin, TimestampMixin, Base):
    __tablename__ = "tenant_settings"
    __table_args__ = (UniqueConstraint("tenant_id", "key", name="uq_tenant_settings_tenant_key"),)

    key: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class Document(UuidPrimaryKeyMixin, TenantOwnedMixin, TimestampMixin, Base):
    __tablename__ = "documents"

    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    mime: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    size: Mapped[int] = mapped_column(nullable=False, default=0)
    checksum: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    source: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class HistoryRecord(UuidPrimaryKeyMixin, TenantOwnedMixin, TimestampMixin, Base):
    __tablename__ = "history_records"
    __table_args__ = (
        UniqueConstraint("tenant_id", "external_id", name="uq_history_records_tenant_external"),
        Index("ix_history_records_tenant_created", "tenant_id", "created_at"),
    )

    external_id: Mapped[str] = mapped_column(String(64), nullable=False)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    vendor: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    doc_type: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    response_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class HistoryAsset(UuidPrimaryKeyMixin, TenantOwnedMixin, TimestampMixin, Base):
    __tablename__ = "history_assets"
    __table_args__ = (
        UniqueConstraint("tenant_id", "history_record_id", "asset_key", name="uq_history_assets_record_key"),
    )

    history_record_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("history_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset_key: Mapped[str] = mapped_column(String(800), nullable=False)
    display_path: Mapped[str] = mapped_column(String(800), nullable=False, default="")
    mime: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    size: Mapped[int] = mapped_column(nullable=False, default=0)
    checksum: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    is_text: Mapped[bool] = mapped_column(nullable=False, default=False)


class ExtractionJob(UuidPrimaryKeyMixin, TenantOwnedMixin, TimestampMixin, Base):
    __tablename__ = "extraction_jobs"
    __table_args__ = (Index("ix_extraction_jobs_tenant_created", "tenant_id", "created_at"),)

    document_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    stage: Mapped[str] = mapped_column(String(80), nullable=False, default="queued")
    progress: Mapped[int] = mapped_column(nullable=False, default=0)
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    error: Mapped[str] = mapped_column(Text, nullable=False, default="")
    request_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    result_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    request_hash: Mapped[str] = mapped_column(String(128), nullable=False, default="")


class SubmissionDraft(UuidPrimaryKeyMixin, TenantOwnedMixin, TimestampMixin, Base):
    __tablename__ = "submission_drafts"

    history_record_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("history_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    draft_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    validation_summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")


class CustomsSubmitJob(UuidPrimaryKeyMixin, TenantOwnedMixin, TimestampMixin, Base):
    __tablename__ = "customs_submit_jobs"
    __table_args__ = (Index("ix_customs_submit_jobs_tenant_created", "tenant_id", "created_at"),)

    draft_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("submission_drafts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    submit_engine: Mapped[str] = mapped_column(String(64), nullable=False, default="http")
    result_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    error: Mapped[str] = mapped_column(Text, nullable=False, default="")


class AuditLog(UuidPrimaryKeyMixin, TenantOwnedMixin, TimestampMixin, Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_tenant_created", "tenant_id", "created_at"),)

    actor_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(160), nullable=False)
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    action: Mapped[str] = mapped_column(String(160), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    resource_id: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    request_id: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    ip_address: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    user_agent: Mapped[str] = mapped_column(Text, nullable=False, default="")
    result: Mapped[str] = mapped_column(String(32), nullable=False, default="success")
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class UsageEvent(UuidPrimaryKeyMixin, TenantOwnedMixin, TimestampMixin, Base):
    __tablename__ = "usage_events"
    __table_args__ = (Index("ix_usage_events_tenant_created", "tenant_id", "created_at"),)

    actor_type: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    actor_id: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    counters: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    billable_dimensions: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
