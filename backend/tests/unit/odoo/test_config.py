from __future__ import annotations

import pytest

from app.core.config import Settings
from app.integrations.odoo.config import OdooConfig
from app.integrations.odoo.exceptions import OdooConfigurationError


def _settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "_env_file": None,
        "odoo_base_url": "http://localhost:8069",
        "odoo_database": "terrific_bites_dev",
        "odoo_username": "admin",
        "odoo_password": "admin-password",
    }
    defaults.update(overrides)
    return Settings(**defaults)  # type: ignore[arg-type]


def test_from_settings_builds_valid_config() -> None:
    config = OdooConfig.from_settings(_settings())

    assert config.base_url == "http://localhost:8069"
    assert config.database == "terrific_bites_dev"
    assert config.credential == "admin-password"
    assert config.jsonrpc_endpoint == "http://localhost:8069/jsonrpc"


def test_from_settings_accepts_api_key_instead_of_password() -> None:
    config = OdooConfig.from_settings(_settings(odoo_password="", odoo_api_key="a-real-api-key"))

    assert config.credential == "a-real-api-key"


def test_from_settings_rejects_missing_base_url() -> None:
    with pytest.raises(OdooConfigurationError, match="ODOO_BASE_URL"):
        OdooConfig.from_settings(_settings(odoo_base_url=""))


def test_from_settings_rejects_invalid_base_url() -> None:
    with pytest.raises(OdooConfigurationError, match="valid absolute"):
        OdooConfig.from_settings(_settings(odoo_base_url="not-a-url"))


def test_from_settings_rejects_missing_database() -> None:
    with pytest.raises(OdooConfigurationError, match="ODOO_DATABASE"):
        OdooConfig.from_settings(_settings(odoo_database=""))


def test_from_settings_rejects_neither_password_nor_api_key() -> None:
    with pytest.raises(OdooConfigurationError, match="Neither"):
        OdooConfig.from_settings(_settings(odoo_password=""))


def test_from_settings_rejects_both_password_and_api_key() -> None:
    with pytest.raises(OdooConfigurationError, match="Both"):
        OdooConfig.from_settings(_settings(odoo_api_key="also-set"))


def test_from_settings_rejects_non_positive_timeout() -> None:
    with pytest.raises(OdooConfigurationError, match="ODOO_TIMEOUT_SECONDS"):
        OdooConfig.from_settings(_settings(odoo_timeout_seconds=0))


def test_from_settings_rejects_unsupported_protocol() -> None:
    with pytest.raises(OdooConfigurationError, match="ODOO_PROTOCOL"):
        OdooConfig.from_settings(_settings(odoo_protocol="xmlrpc"))


def test_is_configured_false_when_all_empty() -> None:
    assert (
        OdooConfig.is_configured(_settings(odoo_base_url="", odoo_database="", odoo_username=""))
        is False
    )


def test_is_configured_true_when_any_set() -> None:
    assert OdooConfig.is_configured(_settings(odoo_database="", odoo_username="")) is True


def test_settings_treats_blank_optional_int_env_vars_as_unset() -> None:
    settings = Settings(
        _env_file=None,
        odoo_company_id="",
        odoo_default_pricelist_id="",
        odoo_default_warehouse_id="",
    )

    assert settings.odoo_company_id is None
    assert settings.odoo_default_pricelist_id is None
    assert settings.odoo_default_warehouse_id is None


def test_masked_dict_redacts_password_and_api_key() -> None:
    config = OdooConfig.from_settings(_settings())
    masked = config.masked_dict()

    assert masked["password"] == "***REDACTED***"
    serialized = str(masked)
    assert "admin-password" not in serialized
