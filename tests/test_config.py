from app.config import AppSettings


def test_default_settings_are_development_safe():
    settings = AppSettings()

    assert settings.app_name == "TeleIDP"
    assert settings.environment == "development"
    assert settings.default_tenant_slug == "default"
    assert settings.database_url.startswith("postgresql+psycopg://")


def test_production_requires_database_url_and_secret_key():
    settings = AppSettings(
        environment="production",
        database_url="",
        secret_key="",
    )

    errors = settings.validate_for_startup()

    assert any("DATABASE_URL" in item for item in errors)
    assert any("SECRET_KEY" in item for item in errors)
