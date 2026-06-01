from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import Template
from app.store.template_store import normalize_templates


class TemplateRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_templates(self, tenant_id: str) -> list[dict[str, Any]]:
        stmt = select(Template).where(Template.tenant_id == _tenant_uuid(tenant_id)).order_by(Template.vendor, Template.doc_type)
        rows = self.session.execute(stmt).scalars().all()
        if not rows:
            return normalize_templates(None)
        return [template_to_payload(row) for row in rows]

    def replace_templates(self, tenant_id: str, payload: Any) -> list[dict[str, Any]]:
        normalized = normalize_templates(payload)
        tenant_uuid = _tenant_uuid(tenant_id)
        self.session.execute(delete(Template).where(Template.tenant_id == tenant_uuid))
        for item in normalized:
            self.session.add(
                Template(
                    tenant_id=tenant_uuid,
                    external_id=str(item.get("id") or ""),
                    vendor=str(item.get("vendor") or ""),
                    doc_type=str(item.get("doc_type") or ""),
                    llm_prompt=str(item.get("llm_prompt") or ""),
                    region_rules=str(item.get("region_rules") or ""),
                    backend=str(item.get("backend") or "vlm"),
                    parse_method=str(item.get("parse_method") or "auto"),
                    lang_list=str(item.get("lang_list") or "en"),
                    customs_mapping=item.get("customs_mapping") if isinstance(item.get("customs_mapping"), dict) else {},
                )
            )
        self.session.flush()
        return normalized

    def reset_templates(self, tenant_id: str) -> list[dict[str, Any]]:
        return self.replace_templates(tenant_id, None)


def template_to_payload(row: Template) -> dict[str, Any]:
    return {
        "id": row.external_id or row.id.hex,
        "vendor": row.vendor,
        "doc_type": row.doc_type,
        "llm_prompt": row.llm_prompt,
        "region_rules": row.region_rules,
        "backend": row.backend,
        "parse_method": row.parse_method,
        "lang_list": row.lang_list,
        "customs_mapping": row.customs_mapping if isinstance(row.customs_mapping, dict) else {"header": {}, "detail": {}},
    }


def _tenant_uuid(tenant_id: str) -> uuid.UUID:
    return uuid.UUID(str(tenant_id))
