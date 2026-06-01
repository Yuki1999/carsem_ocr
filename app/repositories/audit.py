from __future__ import annotations

import uuid
from copy import deepcopy
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import AuditLog
from app.security.tenant_context import TenantContext


SECRET_FIELD_NAMES = {
    "api_key",
    "apiKey",
    "llm_api_key",
    "password",
    "secret",
    "token",
    "authorization",
}


def redact_audit_payload(payload: Any) -> Any:
    value = deepcopy(payload)
    return _redact(value)


class AuditRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def write(
        self,
        context: TenantContext,
        *,
        action: str,
        resource_type: str = "",
        resource_id: str = "",
        result: str = "success",
        payload: dict[str, Any] | None = None,
        ip_address: str = "",
        user_agent: str = "",
    ) -> AuditLog:
        row = AuditLog(
            tenant_id=uuid.UUID(context.tenant_id),
            actor_type=context.actor_type,
            actor_id=context.actor_id,
            api_key_id=uuid.UUID(context.api_key_id) if context.api_key_id else None,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            request_id=context.request_id,
            ip_address=ip_address,
            user_agent=user_agent,
            result=result,
            payload=redact_audit_payload(payload or {}),
        )
        self.session.add(row)
        self.session.flush()
        return row


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        for key, item in list(value.items()):
            if str(key) in SECRET_FIELD_NAMES or _looks_secret_key(key):
                value[key] = "***REDACTED***"
            else:
                value[key] = _redact(item)
        return value
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def _looks_secret_key(key: Any) -> bool:
    text = str(key or "").lower()
    return any(part in text for part in ("password", "secret", "token", "api_key", "apikey"))
