from __future__ import annotations

from app.core.config import Settings


def test_settings_load_with_expected_defaults_and_types() -> None:
    settings = Settings(_env_file=None)

    assert settings.app_name
    assert settings.api_v1_prefix == "/api/v1"
    assert isinstance(settings.database_pool_size, int)
    assert isinstance(settings.database_max_overflow, int)
    assert isinstance(settings.cors_allowed_origins, list)
    assert isinstance(settings.trusted_hosts, list)
    assert isinstance(settings.odoo_verify_ssl, bool)


def test_settings_parses_comma_separated_lists() -> None:
    settings = Settings(
        _env_file=None,
        cors_allowed_origins="https://a.example.com, https://b.example.com",
        trusted_hosts="a.example.com,b.example.com",
    )

    assert settings.cors_allowed_origins == ["https://a.example.com", "https://b.example.com"]
    assert settings.trusted_hosts == ["a.example.com", "b.example.com"]


def test_masked_dict_redacts_secret_fields() -> None:
    settings = Settings(
        _env_file=None,
        odoo_password="super-secret-value",  # noqa: S106 - test fixture value
        odoo_api_key="super-secret-api-key",  # noqa: S106 - test fixture value
        database_url="postgresql+psycopg://user:pw@host:5432/db",
    )

    masked = settings.masked_dict()

    assert masked["odoo_password"] == "***REDACTED***"
    assert masked["odoo_api_key"] == "***REDACTED***"
    assert masked["database_url"] == "***REDACTED***"
    serialized = str(masked)
    assert "super-secret-value" not in serialized
    assert "super-secret-api-key" not in serialized
    assert "pw@host" not in serialized
