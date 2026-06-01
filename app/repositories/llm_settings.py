from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import LlmConfig, TenantSetting
from app.store.llm_settings_store import normalize_llm_settings


LLM_SETTINGS_KEY = "llm_settings"


class LlmSettingsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def load_settings(self, tenant_id: str) -> dict[str, Any]:
        tenant_uuid = _tenant_uuid(tenant_id)
        configs = self.session.execute(
            select(LlmConfig).where(LlmConfig.tenant_id == tenant_uuid).order_by(LlmConfig.created_at, LlmConfig.name)
        ).scalars().all()
        setting = self.session.execute(
            select(TenantSetting).where(TenantSetting.tenant_id == tenant_uuid, TenantSetting.key == LLM_SETTINGS_KEY)
        ).scalar_one_or_none()
        if not configs:
            return normalize_llm_settings(None)
        setting_value = setting.value if setting and isinstance(setting.value, dict) else {}
        active_id = str(setting_value.get("active_id") or "")
        items = [
            {
                "id": row.external_id or row.id.hex,
                "name": row.name,
                "provider": row.provider,
                "llm_base_url": row.base_url,
                "llm_model": row.model,
                "llm_api_key": row.encrypted_api_key,
            }
            for row in configs
        ]
        if not active_id:
            active = next((row for row in configs if row.is_active), configs[0])
            active_id = active.external_id or active.id.hex
        return normalize_llm_settings(
            {
                "active_id": active_id,
                "items": items,
                "auto_mode_enabled": bool(setting_value.get("auto_mode_enabled", False)),
                "customs_submit_mode": str(setting_value.get("customs_submit_mode") or "http"),
            }
        )

    def save_settings(self, tenant_id: str, payload: Any) -> dict[str, Any]:
        normalized = normalize_llm_settings(payload)
        tenant_uuid = _tenant_uuid(tenant_id)
        self.session.execute(delete(LlmConfig).where(LlmConfig.tenant_id == tenant_uuid))
        active_id = str(normalized.get("active_id") or "")
        for item in normalized.get("items") or []:
            if not isinstance(item, dict):
                continue
            external_id = str(item.get("id") or "")
            self.session.add(
                LlmConfig(
                    tenant_id=tenant_uuid,
                    external_id=external_id,
                    name=str(item.get("name") or ""),
                    provider=str(item.get("provider") or "custom"),
                    base_url=str(item.get("llm_base_url") or ""),
                    model=str(item.get("llm_model") or ""),
                    encrypted_api_key=str(item.get("llm_api_key") or ""),
                    is_active=external_id == active_id,
                    status="active",
                )
            )
        setting = self.session.execute(
            select(TenantSetting).where(TenantSetting.tenant_id == tenant_uuid, TenantSetting.key == LLM_SETTINGS_KEY)
        ).scalar_one_or_none()
        value = {
            "active_id": active_id,
            "auto_mode_enabled": bool(normalized.get("auto_mode_enabled", False)),
            "customs_submit_mode": str(normalized.get("customs_submit_mode") or "http"),
        }
        if setting is None:
            self.session.add(TenantSetting(tenant_id=tenant_uuid, key=LLM_SETTINGS_KEY, value=value))
        else:
            setting.value = value
        self.session.flush()
        return normalized


def _tenant_uuid(tenant_id: str) -> uuid.UUID:
    return uuid.UUID(str(tenant_id))
