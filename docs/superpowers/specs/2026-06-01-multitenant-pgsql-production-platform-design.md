# Multitenant PostgreSQL Production Platform Design

## Goal

Evolve TeleIDP from a single-tenant, file-backed FastAPI/Vue application into a production-grade multitenant platform backed by PostgreSQL, with a stable API surface that agents can call as skills/tools.

## Current State

- FastAPI routes in `app/api/app.py` call file-backed stores directly.
- Templates live in `output/settings/templates.json`.
- LLM settings live in `output/settings/llm_settings.json`.
- History records and extracted assets live under `output/history/`.
- Extract/customs task state is held in process-local dictionaries.
- There is no user identity, tenant context, API key model, scope model, audit log, or database migration layer.

## Recommended Tenancy Model

Use one PostgreSQL database with shared tables and mandatory `tenant_id` on all tenant-owned data.

PostgreSQL Row Level Security should be enabled for tenant-owned tables. Application code must set the current tenant for each transaction, and repository functions must also require a `TenantContext`. RLS is a safety net, not the only guard.

This model is best for future agent/skill access because each call can resolve to a clear tuple:

- `tenant_id`
- `actor_type`: `user`, `agent`, or `system`
- `actor_id`
- `api_key_id` or OAuth client id when applicable
- granted scopes
- `request_id`

Independent schema or database per tenant should remain an enterprise-only option for future high-compliance customers, not the default foundation.

## Core Data Model

Platform and identity:

- `tenants`: tenant id, slug, name, status, plan, timestamps.
- `users`: user id, email, display name, password hash or external identity fields, status.
- `tenant_memberships`: tenant id, user id, role, status.
- `api_clients`: tenant-owned agent/client registrations.
- `api_keys`: hashed key material, client id, tenant id, scopes, status, last used at.
- `audit_logs`: tenant id, actor fields, action, resource, request id, ip/user agent, result, timestamps.
- `usage_events`: tenant id, actor fields, event type, counters, billable dimensions.

Business configuration:

- `templates`: tenant id, vendor, doc type, prompt, region rules, OCR settings, customs mapping.
- `llm_configs`: tenant id, provider, base URL, model, encrypted API key reference/value, active flag.
- `tenant_settings`: tenant-level switches such as auto mode, submit mode, feature flags.

Documents and workflow:

- `documents`: tenant id, filename, mime, size, checksum, source metadata.
- `extraction_jobs`: tenant id, document id, status, stage, progress, error, request payload, result summary.
- `history_records`: tenant id, document id, response payload, vendor, doc type, created at.
- `history_assets`: tenant id, record id, asset key/path, mime, size, checksum, text flag.
- `submission_drafts`: tenant id, history record id, draft JSON, validation summary, status.
- `customs_submit_jobs`: tenant id, draft id, status, submit engine, result payload, error.

## Storage Strategy

PostgreSQL is the system of record for metadata, settings, jobs, and JSON payloads.

Extracted binary/text assets should use an asset abstraction:

- Phase 1: local disk under `output/tenants/{tenant_id}/history/{record_id}/...`.
- Phase 2: S3-compatible object storage such as MinIO/OSS/S3.

The database stores stable asset keys, mime type, checksum, size, and display path. API routes never derive tenant identity from a path.

## API and Agent Access

Keep browser APIs and agent APIs separate.

Browser UI:

- Continue current `/api/...` routes initially.
- Add authentication and a tenant resolver dependency.
- Later move to `/api/v1/...` without breaking the UI all at once.

Agent/skill API:

- Add `/api/v1/agent/...` routes designed for machine clients.
- Authenticate with scoped API keys first; support OAuth clients later.
- Require idempotency keys for job-creating endpoints.
- Return async job ids for long-running extraction and submission operations.
- Provide stable polling endpoints and later webhooks.

Initial agent scopes:

- `documents:extract`
- `templates:read`
- `templates:write`
- `history:read`
- `submission:read`
- `customs:submit`
- `settings:read`
- `settings:write`

Agent endpoints should avoid frontend-specific response shapes. They should return stable typed payloads with explicit status, errors, and resource ids.

## Application Architecture

Add a database and repository layer instead of letting route handlers call storage files directly.

Proposed backend modules:

- `app/db/session.py`: engine/session creation and transaction helpers.
- `app/db/models.py`: SQLAlchemy models or SQLModel models.
- `app/db/migrations/`: Alembic migrations.
- `app/security/tenant_context.py`: request auth, tenant resolution, scope checks.
- `app/repositories/templates.py`
- `app/repositories/llm_settings.py`
- `app/repositories/history.py`
- `app/repositories/jobs.py`
- `app/repositories/audit.py`
- `app/storage/assets.py`: local/object asset abstraction.

Route handlers should accept `TenantContext`, call repositories with it, and never query tenant-owned data without it.

## Migration Strategy

Add an import command that migrates the existing file-backed data into a default tenant.

Default migration behavior:

- Create tenant `default`.
- Import `output/settings/templates.json` into `templates`.
- Import `output/settings/llm_settings.json` into `llm_configs` and `tenant_settings`.
- Import `output/history/index.json` and per-record `meta.json` into `history_records`.
- Register files under `output/history/{record_id}/unzipped` as `history_assets`.
- Preserve old files during migration; do not delete them.

This allows the app to switch to PostgreSQL without losing current data.

## Production Concerns

Required for production readiness:

- PostgreSQL connection pooling and migration management.
- Environment-based configuration with `.env.example`.
- API key hashing and secret redaction.
- Tenant-aware audit logs for all state-changing operations.
- Rate limits and quotas per tenant and API key.
- Background worker for extraction/customs jobs; current in-process task dicts are not production-safe.
- Health checks for DB, asset storage, and external OCR/LLM dependencies.
- Structured logs with request id and tenant id.
- Backup/restore plan for PostgreSQL and object storage.

## Phased Delivery

### Phase 1: PostgreSQL Foundation and Tenant Context

Create DB config, migrations, tenant/user/API key models, `TenantContext`, RLS conventions, and repository interfaces. Keep business behavior mostly unchanged.

### Phase 2: Move Settings, Templates, History, and Jobs to PostgreSQL

Replace JSON/file index stores with repositories. Keep local asset files behind an asset abstraction. Add migration/import tooling for existing `output/` data.

### Phase 3: Production Agent API

Add `/api/v1/agent` endpoints with API key auth, scopes, idempotency keys, job polling, and audit logs.

### Phase 4: Production Hardening

Add background worker, rate limits, quotas, structured logging, health checks, and deployment docs.

### Phase 5: Object Storage and Enterprise Isolation Options

Move assets to S3-compatible object storage. Add optional dedicated schema/database mode only for tenants that require stronger operational isolation.

## Testing Strategy

- Unit tests for tenant context resolution and scope checks.
- Repository tests against PostgreSQL, preferably via testcontainers or a docker compose test database.
- RLS tests proving tenant A cannot read tenant B data even if code omits a filter.
- Migration tests using temporary `output/` fixtures.
- API tests for browser routes with user auth.
- Agent API tests for scoped API keys, forbidden scopes, idempotency behavior, and audit logs.

## Open Decisions

- Authentication provider: local username/password, OIDC, or both.
- ORM choice: SQLAlchemy 2.x async/sync or SQLModel.
- Background worker: ARQ, Celery, Dramatiq, or RQ.
- Asset storage target: local disk first, MinIO/OSS/S3 later.
- Whether customs credentials are tenant-level secrets or per-user secrets.
