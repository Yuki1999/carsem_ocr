from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ApiKey
from app.db.session import get_db_session, set_current_tenant
from app.repositories.audit import AuditRepository
from app.repositories.history import HistoryRepository
from app.repositories.jobs import JobRepository, extraction_job_to_payload
from app.repositories.templates import TemplateRepository
from app.repositories.tenants import load_tenant
from app.security.api_keys import verify_api_key
from app.security.tenant_context import TenantContext, require_scopes_http
from app.storage.assets import LocalAssetStorage
from app.config import get_settings


router = APIRouter(tags=["agent"])
ExtractionEnqueueCallback = Callable[[str, dict[str, Any]], Awaitable[None]]
_extraction_enqueue_callback: ExtractionEnqueueCallback | None = None

AGENT_ENDPOINT_SCOPES = {
    "POST /extractions": {"documents:extract"},
    "GET /extractions/{job_id}": {"documents:extract"},
    "GET /templates": {"templates:read"},
    "GET /history": {"history:read"},
    "GET /history/{record_id}": {"history:read"},
}


async def get_agent_context(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    session: Session = Depends(get_db_session),
) -> TenantContext:
    raw = str(authorization or "").strip()
    if not raw.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing bearer API key")
    presented = raw.split(" ", 1)[1].strip()
    if not presented:
        raise HTTPException(status_code=401, detail="missing bearer API key")
    tenant_ref = str(x_tenant_id or get_settings().default_tenant_slug).strip()
    tenant = load_tenant(session, tenant_ref)
    if tenant is None:
        raise HTTPException(status_code=401, detail="invalid tenant")
    set_current_tenant(session, str(tenant.id))
    rows = session.execute(select(ApiKey).where(ApiKey.tenant_id == tenant.id, ApiKey.status == "active")).scalars()
    for row in rows:
        if verify_api_key(presented, row.key_hash):
            set_current_tenant(session, str(row.tenant_id))
            scopes = _scopes_from_payload(row.scopes)
            return TenantContext(
                tenant_id=str(row.tenant_id),
                actor_type="agent",
                actor_id=str(row.client_id or row.id),
                api_key_id=str(row.id),
                scopes=frozenset(scopes),
                request_id=x_request_id or request.headers.get("X-Request-ID") or uuid.uuid4().hex,
            )
    raise HTTPException(status_code=401, detail="invalid API key")


@router.post("/extractions")
async def create_extraction(
    payload: dict[str, Any] = Body(default_factory=dict),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    context: TenantContext = Depends(get_agent_context),
    session: Session = Depends(get_db_session),
):
    require_scopes_http(context, AGENT_ENDPOINT_SCOPES["POST /extractions"])
    job = JobRepository(session).create_extraction_job(
        tenant_id=context.tenant_id,
        request_payload=payload if isinstance(payload, dict) else {},
        idempotency_key=str(idempotency_key or ""),
    )
    AuditRepository(session).write(
        context,
        action="agent.extraction.create",
        resource_type="extraction_job",
        resource_id=str(job.id),
        payload=payload if isinstance(payload, dict) else {},
    )
    if _extraction_enqueue_callback is not None:
        try:
            await _extraction_enqueue_callback(str(job.id), payload if isinstance(payload, dict) else {})
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return extraction_job_to_payload(job)


@router.get("/extractions/{job_id}")
async def get_extraction(
    job_id: str,
    context: TenantContext = Depends(get_agent_context),
    session: Session = Depends(get_db_session),
):
    require_scopes_http(context, AGENT_ENDPOINT_SCOPES["GET /extractions/{job_id}"])
    job = JobRepository(session).get_extraction_job(context.tenant_id, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="extraction job not found")
    return extraction_job_to_payload(job)


@router.get("/templates")
async def list_templates(
    context: TenantContext = Depends(get_agent_context),
    session: Session = Depends(get_db_session),
):
    require_scopes_http(context, AGENT_ENDPOINT_SCOPES["GET /templates"])
    return {"items": TemplateRepository(session).list_templates(context.tenant_id)}


@router.get("/history")
async def list_history(
    limit: int = Query(default=50, ge=1, le=200),
    context: TenantContext = Depends(get_agent_context),
    session: Session = Depends(get_db_session),
):
    require_scopes_http(context, AGENT_ENDPOINT_SCOPES["GET /history"])
    repo = HistoryRepository(session, LocalAssetStorage(get_settings().local_asset_root))
    return {"items": repo.list_history_records(context.tenant_id, limit=limit)}


@router.get("/history/{record_id}")
async def get_history(
    record_id: str,
    context: TenantContext = Depends(get_agent_context),
    session: Session = Depends(get_db_session),
):
    require_scopes_http(context, AGENT_ENDPOINT_SCOPES["GET /history/{record_id}"])
    repo = HistoryRepository(session, LocalAssetStorage(get_settings().local_asset_root))
    detail = repo.load_history_record(context.tenant_id, record_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="history record not found")
    return detail


def _scopes_from_payload(payload: Any) -> set[str]:
    if isinstance(payload, list):
        return {str(item) for item in payload if str(item).strip()}
    if isinstance(payload, dict):
        items = payload.get("items") or payload.get("scopes") or []
        if isinstance(items, list):
            return {str(item) for item in items if str(item).strip()}
    return set()


def set_extraction_enqueue_callback(callback: ExtractionEnqueueCallback | None) -> None:
    global _extraction_enqueue_callback
    _extraction_enqueue_callback = callback
