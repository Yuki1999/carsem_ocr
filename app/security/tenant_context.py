from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Literal

from fastapi import HTTPException, Request

from app.config import AppSettings, get_settings


ActorType = Literal["user", "agent", "system"]


class ScopeError(PermissionError):
    pass


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    actor_type: ActorType
    actor_id: str
    scopes: frozenset[str]
    request_id: str
    api_key_id: str | None = None


def require_scopes(context: TenantContext, required_scopes: set[str] | frozenset[str]) -> None:
    missing = set(required_scopes) - set(context.scopes)
    if missing:
        raise ScopeError(f"missing required scope(s): {', '.join(sorted(missing))}")


def require_scopes_http(context: TenantContext, required_scopes: set[str] | frozenset[str]) -> None:
    try:
        require_scopes(context, required_scopes)
    except ScopeError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


def build_system_tenant_context(
    *,
    tenant_id: str,
    request_id: str | None = None,
    scopes: set[str] | frozenset[str] | None = None,
) -> TenantContext:
    return TenantContext(
        tenant_id=str(tenant_id),
        actor_type="system",
        actor_id="system",
        scopes=frozenset(scopes or {"*"}),
        request_id=request_id or uuid.uuid4().hex,
    )


async def get_dev_tenant_context(request: Request, settings: AppSettings | None = None) -> TenantContext:
    resolved_settings = settings or get_settings()
    tenant_id = request.headers.get("X-Tenant-ID") or resolved_settings.default_tenant_slug
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    scopes_raw = request.headers.get("X-Tenant-Scopes") or "*"
    scopes = frozenset(part.strip() for part in scopes_raw.split(",") if part.strip())
    return TenantContext(
        tenant_id=tenant_id,
        actor_type="user",
        actor_id=request.headers.get("X-Actor-ID") or "dev-user",
        scopes=scopes,
        request_id=request_id,
    )
