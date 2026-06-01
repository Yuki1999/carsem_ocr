from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Tenant


def get_or_create_tenant(session: Session, tenant_ref: str, name: str | None = None) -> Tenant:
    ref = str(tenant_ref or "").strip() or "default"
    tenant = _load_tenant(session, ref)
    if tenant is not None:
        return tenant
    slug = ref if not _looks_like_uuid(ref) else "default"
    tenant = Tenant(slug=slug, name=name or slug, status="active", plan="standard")
    session.add(tenant)
    session.flush()
    return tenant


def load_tenant(session: Session, tenant_ref: str) -> Tenant | None:
    ref = str(tenant_ref or "").strip()
    if not ref:
        return None
    return _load_tenant(session, ref)


def _load_tenant(session: Session, tenant_ref: str) -> Tenant | None:
    if _looks_like_uuid(tenant_ref):
        tenant_id = uuid.UUID(tenant_ref)
        return session.get(Tenant, tenant_id)
    stmt = select(Tenant).where(Tenant.slug == tenant_ref)
    return session.execute(stmt).scalar_one_or_none()


def _looks_like_uuid(value: str) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except ValueError:
        return False
