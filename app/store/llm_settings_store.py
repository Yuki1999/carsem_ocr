from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any


SETTINGS_DIR_NAME = "settings"
LLM_SETTINGS_FILE_NAME = "llm_settings.json"
MAX_CONFIG_ITEMS = 50

DEFAULT_LLM_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
DEFAULT_LLM_MODEL = "gemini-3-flash-preview"
DEFAULT_LLM_API_KEY = ""
DEFAULT_PROVIDER = "gemini"
DEFAULT_AUTO_MODE_ENABLED = False
DEFAULT_CUSTOMS_SUBMIT_MODE = "http"

_ALLOWED_PROVIDERS = {"deepseek", "gemini", "bailian", "custom"}
_ALLOWED_CUSTOMS_SUBMIT_MODES = {"http", "playwright"}


def load_llm_settings(project_root: Path) -> dict[str, Any]:
    settings_file = _settings_file(project_root)
    payload = _read_json(settings_file, default=None)
    return normalize_llm_settings(payload)


def save_llm_settings(project_root: Path, payload: Any) -> dict[str, Any]:
    normalized = normalize_llm_settings(payload)
    settings_file = _settings_file(project_root)
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    _write_json_atomic(settings_file, normalized)
    return normalized


def normalize_llm_settings(payload: Any) -> dict[str, Any]:
    fallback = _default_settings()
    if not isinstance(payload, dict):
        return fallback

    # Legacy single-profile compatibility.
    if isinstance(payload.get("llm_base_url"), str) or isinstance(payload.get("llm_model"), str):
        single = _normalize_item(
            {
                "id": payload.get("id"),
                "name": payload.get("name") or "迁移配置",
                "provider": payload.get("provider"),
                "llm_base_url": payload.get("llm_base_url"),
                "llm_model": payload.get("llm_model"),
                "llm_api_key": payload.get("llm_api_key"),
            },
            index=1,
        )
        return {
            "active_id": single["id"],
            "items": [single],
            "auto_mode_enabled": bool(payload.get("auto_mode_enabled", DEFAULT_AUTO_MODE_ENABLED)),
            "customs_submit_mode": _normalize_customs_submit_mode(payload.get("customs_submit_mode")),
        }

    raw_items = payload.get("items")
    if not isinstance(raw_items, list) or len(raw_items) == 0:
        return fallback

    items: list[dict[str, Any]] = []
    seen = set()
    for index, raw_item in enumerate(raw_items, start=1):
        item = _normalize_item(raw_item, index=index)
        item_id = item["id"]
        if item_id in seen:
            item["id"] = uuid.uuid4().hex
            item_id = item["id"]
        seen.add(item_id)
        items.append(item)
        if len(items) >= MAX_CONFIG_ITEMS:
            break

    if not items:
        return fallback

    active_id = str(payload.get("active_id") or "").strip()
    if not any(x["id"] == active_id for x in items):
        active_id = items[0]["id"]
    return {
        "active_id": active_id,
        "items": items,
        "auto_mode_enabled": bool(payload.get("auto_mode_enabled", DEFAULT_AUTO_MODE_ENABLED)),
        "customs_submit_mode": _normalize_customs_submit_mode(payload.get("customs_submit_mode")),
    }


def resolve_active_llm_config(settings: Any) -> dict[str, str]:
    normalized = normalize_llm_settings(settings)
    items = normalized.get("items")
    if not isinstance(items, list):
        items = []
    active_id = str(normalized.get("active_id") or "").strip()

    active: dict[str, Any] | None = None
    for item in items:
        if isinstance(item, dict) and str(item.get("id") or "").strip() == active_id:
            active = item
            break
    if active is None:
        active = items[0] if items and isinstance(items[0], dict) else None
    if active is None:
        active = _default_settings()["items"][0]

    return {
        "llm_base_url": str(active.get("llm_base_url") or DEFAULT_LLM_BASE_URL).strip() or DEFAULT_LLM_BASE_URL,
        "llm_model": str(active.get("llm_model") or DEFAULT_LLM_MODEL).strip() or DEFAULT_LLM_MODEL,
        "llm_api_key": str(active.get("llm_api_key") or DEFAULT_LLM_API_KEY),
        "auto_mode_enabled": bool(normalized.get("auto_mode_enabled", DEFAULT_AUTO_MODE_ENABLED)),
        "customs_submit_mode": _normalize_customs_submit_mode(normalized.get("customs_submit_mode")),
    }


def _default_settings() -> dict[str, Any]:
    item = _normalize_item(
        {
            "id": uuid.uuid4().hex,
            "name": "Gemini 默认",
            "provider": DEFAULT_PROVIDER,
            "llm_base_url": DEFAULT_LLM_BASE_URL,
            "llm_model": DEFAULT_LLM_MODEL,
            "llm_api_key": DEFAULT_LLM_API_KEY,
        },
        index=1,
    )
    return {
        "active_id": item["id"],
        "items": [item],
        "auto_mode_enabled": DEFAULT_AUTO_MODE_ENABLED,
        "customs_submit_mode": DEFAULT_CUSTOMS_SUBMIT_MODE,
    }


def _normalize_item(raw_item: Any, index: int) -> dict[str, Any]:
    item = raw_item if isinstance(raw_item, dict) else {}
    base_url = str(item.get("llm_base_url") or "").strip() or DEFAULT_LLM_BASE_URL
    model = str(item.get("llm_model") or "").strip() or DEFAULT_LLM_MODEL
    provider_raw = str(item.get("provider") or "").strip().lower()
    provider = provider_raw if provider_raw in _ALLOWED_PROVIDERS else _infer_provider(base_url, model)
    if provider not in _ALLOWED_PROVIDERS:
        provider = DEFAULT_PROVIDER
    name = str(item.get("name") or "").strip() or f"LLM 配置 {index}"
    item_id = str(item.get("id") or "").strip() or uuid.uuid4().hex
    return {
        "id": item_id,
        "name": name,
        "provider": provider,
        "llm_base_url": base_url,
        "llm_model": model,
        "llm_api_key": str(item.get("llm_api_key") or ""),
    }


def _infer_provider(base_url: str, model: str) -> str:
    base = str(base_url or "").lower()
    mdl = str(model or "").lower()
    if "deepseek.com" in base or "deepseek" in mdl:
        return "deepseek"
    if "generativelanguage.googleapis.com" in base or "gemini" in mdl:
        return "gemini"
    if "dashscope.aliyuncs.com" in base or "dashscope-intl.aliyuncs.com" in base or "qwen" in mdl:
        return "bailian"
    return "custom"


def _normalize_customs_submit_mode(value: Any) -> str:
    mode = str(value or "").strip().lower()
    if mode in _ALLOWED_CUSTOMS_SUBMIT_MODES:
        return mode
    return DEFAULT_CUSTOMS_SUBMIT_MODE

def _settings_file(project_root: Path) -> Path:
    return project_root / "output" / SETTINGS_DIR_NAME / LLM_SETTINGS_FILE_NAME


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json_atomic(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)
