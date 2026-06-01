from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _load_dotenv() -> None:
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if not env_file.is_file():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        os.environ[key] = value.strip().strip('"').strip("'")


_load_dotenv()


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class AppSettings:
    app_name: str = "TeleIDP"
    environment: str = field(default_factory=lambda: _env("APP_ENV", "development"))
    database_url: str = field(
        default_factory=lambda: _env(
            "DATABASE_URL",
            "postgresql+psycopg://teleidp_app:teleidp_app@127.0.0.1:55432/teleidp",
        )
    )
    migration_database_url: str = field(default_factory=lambda: _env("MIGRATION_DATABASE_URL", ""))
    default_tenant_slug: str = field(default_factory=lambda: _env("DEFAULT_TENANT_SLUG", "default"))
    secret_key: str = field(default_factory=lambda: _env("SECRET_KEY", ""))
    api_key_prefix: str = field(default_factory=lambda: _env("API_KEY_PREFIX", "tidp"))
    local_asset_root: str = field(default_factory=lambda: _env("LOCAL_ASSET_ROOT", "output/tenants"))
    use_database_stores: bool = field(default_factory=lambda: _env_bool("USE_DATABASE_STORES", False))
    use_database_jobs: bool = field(default_factory=lambda: _env_bool("USE_DATABASE_JOBS", False))

    def validate_for_startup(self) -> list[str]:
        errors: list[str] = []
        if self.environment.strip().lower() == "production":
            if not self.database_url.strip():
                errors.append("DATABASE_URL is required in production")
            if not self.secret_key.strip():
                errors.append("SECRET_KEY is required in production")
        return errors


def get_settings() -> AppSettings:
    return AppSettings()
