"""DEPLOYMENT_STAGE=staging: payments and notifications stay stubs, and Odoo, read or written,
is only ever the deployment's own staging instance with its restricted integration users.
Every rejection is checked at startup (Settings) and again where a client is built or a write
is made, so a misconfigured staging process fails closed."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from app.core.config import (
    STAGING_ODOO_BASE_URL,
    STAGING_ODOO_DATABASE,
    STAGING_ODOO_WRITE_TARGET,
    Settings,
)
from app.integrations.odoo import order_push as order_push_module
from app.integrations.odoo.config import OdooConfig
from app.integrations.odoo.exceptions import OdooConfigurationError, OdooWriteNotAllowedError
from app.integrations.odoo.write_target_guard import assert_odoo_write_target_approved

DEPLOY = Path(__file__).resolve().parents[3] / "deploy"
TEST_ONLY_PASSWORD = "unit-test-staging-password"

# The hardened production values every deployed staging process runs with.
BASE: dict[str, Any] = {
    "_env_file": None,
    "app_env": "production",
    "deployment_stage": "staging",
    "debug": False,
    "admin_jwt_secret": "s" * 48,
    "admin_cookie_domain": "terrific-bites.trunexus.ai",
    "cors_allowed_origins": "https://terrific-bites.trunexus.ai",
    "trusted_hosts": "api.terrific-bites.trunexus.ai,api",
    "media_base_url": "https://api.terrific-bites.trunexus.ai/media",
    "database_url": "postgresql+psycopg://terrific_bites:unit-test@postgres:5432/terrific_bites",
    "payment_provider": "stub",
    "notification_provider": "stub",
    "odoo_order_push_provider": "live",
    "odoo_base_url": STAGING_ODOO_BASE_URL,
    "odoo_database": STAGING_ODOO_DATABASE,
}
WORKER: dict[str, Any] = {
    **BASE,
    "service_role": "worker",
    "odoo_username": "terrific-order-sync",
    "odoo_password": TEST_ONLY_PASSWORD,
    "odoo_write_approved_target": STAGING_ODOO_WRITE_TARGET,
}
IMPORTER: dict[str, Any] = {
    **BASE,
    "service_role": "catalogue_import",
    "odoo_username": "terrific-catalogue-import",
    "odoo_password": TEST_ONLY_PASSWORD,
}


def _staging(base: dict[str, Any], **overrides: Any) -> Settings:
    return Settings(**{**base, **overrides})


# --- Permitted --------------------------------------------------------------------------


@pytest.mark.parametrize("role", ["api", "beat", "migrate"])
def test_credential_free_services_start_on_staging(role: str) -> None:
    settings = _staging(BASE, service_role=role)
    assert settings.deployment_stage == "staging"
    assert settings.is_demo_stage is False


def test_the_worker_starts_with_the_staging_odoo_and_order_sync_user() -> None:
    settings = _staging(WORKER)
    assert OdooConfig.from_settings(settings).jsonrpc_endpoint == "http://odoo:8069/jsonrpc"
    assert_odoo_write_target_approved(settings)


def test_the_worker_accepts_a_trailing_slash_on_the_staging_address() -> None:
    _staging(WORKER, odoo_base_url="http://odoo:8069/")


def test_the_catalogue_import_starts_with_writes_refused_by_default() -> None:
    settings = _staging(IMPORTER)
    with pytest.raises(OdooWriteNotAllowedError):
        assert_odoo_write_target_approved(settings)


def test_an_approved_catalogue_import_may_write_only_to_the_staging_odoo() -> None:
    settings = _staging(IMPORTER, odoo_write_approved_target=STAGING_ODOO_WRITE_TARGET)
    assert_odoo_write_target_approved(settings)


def test_staging_may_keep_the_stub_order_pusher_without_any_odoo() -> None:
    _staging(BASE, odoo_order_push_provider="stub", odoo_base_url="", odoo_database="")


# --- Rejected ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"payment_provider": "tap"}, "PAYMENT_PROVIDER must be stub"),
        ({"notification_provider": "twilio"}, "NOTIFICATION_PROVIDER must be stub"),
        ({"odoo_order_push_provider": "other"}, "ODOO_ORDER_PUSH_PROVIDER"),
        ({"odoo_base_url": "https://erp.trunexus.ai"}, "ODOO_BASE_URL"),
        ({"odoo_base_url": "https://odoo.example.com"}, "ODOO_BASE_URL"),
        ({"odoo_base_url": "http://2.25.11.35:8069"}, "ODOO_BASE_URL"),
        ({"odoo_base_url": "http://localhost:8069"}, "ODOO_BASE_URL"),
        ({"odoo_base_url": "http://host.docker.internal:8069"}, "ODOO_BASE_URL"),
        ({"odoo_base_url": "https://odoo:8069"}, "ODOO_BASE_URL"),
        ({"odoo_base_url": "http://odoo:8070"}, "ODOO_BASE_URL"),
        ({"odoo_base_url": "http://odoo:8069.evil.example"}, "ODOO_BASE_URL"),
        ({"odoo_base_url": ""}, "ODOO_BASE_URL"),
        ({"odoo_database": "terrific_production"}, "ODOO_DATABASE"),
        ({"odoo_database": ""}, "ODOO_DATABASE"),
        ({"odoo_write_approved_target": "https://erp.trunexus.ai#prod"}, "APPROVED_TARGET"),
        ({"odoo_write_approved_target": ""}, "APPROVED_TARGET"),
        ({"odoo_username": "admin"}, "ODOO_USERNAME"),
        ({"odoo_username": "terrific-catalogue-import"}, "ODOO_USERNAME"),
        ({"odoo_password": ""}, "order-sync credential"),
    ],
)
def test_the_worker_refuses_anything_but_the_approved_staging_odoo(
    override: dict[str, Any], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        _staging(WORKER, **override)


@pytest.mark.parametrize(
    "override",
    [
        {"odoo_username": "admin"},
        {"odoo_username": "terrific-order-sync"},
        {"odoo_base_url": "https://erp.trunexus.ai"},
        {"odoo_write_approved_target": "https://erp.trunexus.ai#prod"},
    ],
)
def test_the_catalogue_import_refuses_anything_but_its_own_staging_user(
    override: dict[str, Any],
) -> None:
    with pytest.raises(ValidationError, match="Unsafe staging configuration"):
        _staging(IMPORTER, **override)


@pytest.mark.parametrize("role", ["api", "beat", "migrate", ""])
@pytest.mark.parametrize("secret", ["odoo_password", "odoo_api_key"])
def test_services_without_an_odoo_job_refuse_a_credential(role: str, secret: str) -> None:
    with pytest.raises(ValidationError, match="must not hold Odoo credentials"):
        _staging(BASE, service_role=role, **{secret: TEST_ONLY_PASSWORD})


def test_an_external_odoo_is_refused_even_with_the_stub_pusher() -> None:
    with pytest.raises(ValidationError, match="ODOO_BASE_URL"):
        _staging(BASE, odoo_order_push_provider="stub", odoo_base_url="https://erp.trunexus.ai")


def test_staging_still_gets_the_production_hardening() -> None:
    with pytest.raises(ValidationError, match="ADMIN_JWT_SECRET"):
        _staging(BASE, service_role="api", admin_jwt_secret="short")


def test_a_refusal_never_contains_a_secret_value() -> None:
    with pytest.raises(ValidationError) as excinfo:
        _staging(WORKER, odoo_username="admin", odoo_base_url="https://erp.trunexus.ai")
    assert TEST_ONLY_PASSWORD not in str(excinfo.value)


# --- Second line: the checks where a client is built and a write is made ----------------


def _unvalidated(**overrides: Any) -> Settings:
    """Settings that skipped startup validation, as if staging were misconfigured anyway."""
    values = {key: value for key, value in {**WORKER, **overrides}.items() if key != "_env_file"}
    return Settings.model_construct(**{**Settings().model_dump(), **values})


@pytest.mark.parametrize(
    "override",
    [
        {
            "odoo_base_url": "https://erp.trunexus.ai",
            "odoo_write_approved_target": "https://erp.trunexus.ai#terrific_odoo",
        },
        {
            "odoo_database": "terrific_production",
            "odoo_write_approved_target": "http://odoo:8069#terrific_production",
        },
    ],
)
def test_staging_writes_are_refused_for_any_other_target_even_if_approved(
    override: dict[str, Any],
) -> None:
    with pytest.raises(OdooWriteNotAllowedError, match="Staging may write only"):
        assert_odoo_write_target_approved(_unvalidated(**override))


@pytest.mark.parametrize(
    "override", [{"odoo_base_url": "https://erp.trunexus.ai"}, {"odoo_database": "other"}]
)
def test_no_odoo_client_can_be_built_for_another_instance_on_staging(
    override: dict[str, Any],
) -> None:
    with pytest.raises(OdooConfigurationError, match="Staging may connect only"):
        OdooConfig.from_settings(_unvalidated(**override))


def test_the_live_pusher_refuses_another_odoo_before_any_network_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    misdirected = _unvalidated(
        odoo_base_url="https://erp.trunexus.ai",
        odoo_write_approved_target="https://erp.trunexus.ai#terrific_odoo",
    )
    monkeypatch.setattr("app.core.config.get_settings", lambda: misdirected)

    def _no_network(*_: Any, **__: Any) -> None:
        raise AssertionError("a network transport was created")

    monkeypatch.setattr(order_push_module, "OdooTransport", _no_network)
    with pytest.raises(OdooWriteNotAllowedError):
        order_push_module._connect()


def test_the_live_pusher_connects_only_to_the_staging_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.core.config.get_settings", lambda: _staging(WORKER))
    endpoints: list[str] = []

    class _Stop(Exception):
        pass

    def _record(config: OdooConfig) -> None:
        endpoints.append(config.jsonrpc_endpoint)
        raise _Stop

    monkeypatch.setattr(order_push_module, "OdooTransport", _record)
    with pytest.raises(_Stop):
        order_push_module._connect()
    assert endpoints == ["http://odoo:8069/jsonrpc"]


# --- Existing stages keep their behaviour ----------------------------------------------


def test_demo_still_refuses_the_live_order_pusher() -> None:
    with pytest.raises(ValidationError, match="DEPLOYMENT_STAGE=demo requires stub"):
        Settings(_env_file=None, deployment_stage="demo", odoo_order_push_provider="live")


def test_live_still_requires_finance_approval() -> None:
    with pytest.raises(ValidationError, match="FINANCE_RULES_APPROVED"):
        Settings(
            _env_file=None,
            deployment_stage="live",
            payment_provider="real",
            notification_provider="real",
            odoo_order_push_provider="live",
        )


def test_demo_is_unaffected_by_the_staging_odoo_rules() -> None:
    settings = Settings(
        _env_file=None, deployment_stage="demo", odoo_base_url="https://odoo.example.com"
    )
    assert settings.is_demo_stage is True


# --- The Compose file runs every service as a valid staging process ---------------------


def _compose() -> dict[str, Any]:
    return yaml.safe_load((DEPLOY / "docker-compose.prod.yml").read_text(encoding="utf-8"))


def _resolve(value: Any) -> str:
    """Fills ${VAR...} with a stand-in test value, as `docker compose` would from .env.prod."""
    text = str(value)
    defaults = {
        "ODOO_ORDER_SYNC_LOGIN": "terrific-order-sync",
        "ODOO_CATALOGUE_IMPORT_LOGIN": "terrific-catalogue-import",
        "ODOO_WRITE_APPROVED_TARGET": "",
        "LOG_LEVEL": "INFO",
        "API_PUBLIC_HOST": "api.terrific-bites.trunexus.ai",
        "TRUSTED_HOSTS": "api.terrific-bites.trunexus.ai,api",
        "CORS_ALLOWED_ORIGINS": "https://terrific-bites.trunexus.ai",
        "ADMIN_COOKIE_DOMAIN": "terrific-bites.trunexus.ai",
        "MEDIA_BASE_URL": "https://api.terrific-bites.trunexus.ai/media",
    }

    def _fill(match: re.Match[str]) -> str:
        name = match.group(1)
        return defaults.get(name, "unit-test-" + "x" * 40)

    return re.sub(r"\$\{([A-Z0-9_]+)[^}]*\}", _fill, text)


@pytest.mark.parametrize(
    "service", ["api", "celery-worker", "celery-beat", "migrate", "catalogue-import"]
)
def test_every_backend_service_in_compose_is_a_valid_staging_process(service: str) -> None:
    env = {
        key: _resolve(value)
        for key, value in _compose()["services"][service]["environment"].items()
    }
    settings = Settings(_env_file=None, **{key.lower(): value for key, value in env.items()})
    assert settings.deployment_stage == "staging"
    assert settings.payment_provider == "stub"
    assert settings.notification_provider == "stub"


def test_compose_fixes_the_staging_odoo_address_and_worker_approval() -> None:
    services = _compose()["services"]
    for name in ("api", "celery-worker", "celery-beat", "migrate", "catalogue-import"):
        env = services[name]["environment"]
        assert env["DEPLOYMENT_STAGE"] == "staging", name
        assert env["ODOO_BASE_URL"] == STAGING_ODOO_BASE_URL, name
        assert env["ODOO_DATABASE"] == STAGING_ODOO_DATABASE, name
        assert env["PAYMENT_PROVIDER"] == "stub", name
        assert env["NOTIFICATION_PROVIDER"] == "stub", name
    assert services["celery-worker"]["environment"]["ODOO_WRITE_APPROVED_TARGET"] == (
        STAGING_ODOO_WRITE_TARGET
    )


def test_the_services_holding_odoo_logins_have_no_route_off_the_host() -> None:
    compose = _compose()
    assert compose["networks"]["internal"]["internal"] is True
    for name in ("celery-worker", "catalogue-import"):
        assert compose["services"][name]["networks"] == ["internal"], name
    assert "internal" in compose["services"]["odoo"]["networks"]
