"""Production must refuse to start on development defaults, and admin cookies must be
readable by a frontend on a different host from the API."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import Response
from pydantic import ValidationError

from app.core.config import Settings
from app.core.security import clear_admin_auth_cookies, set_admin_auth_cookies

GOOD: dict[str, Any] = {
    "app_env": "production",
    "deployment_stage": "demo",
    "debug": False,
    "admin_jwt_secret": "x" * 48,
    "admin_cookie_domain": "terrific-bites.trunexus.ai",
    "cors_allowed_origins": "https://terrific-bites.trunexus.ai",
    "trusted_hosts": "api.terrific-bites.trunexus.ai",
    "media_base_url": "https://api.terrific-bites.trunexus.ai/media",
    "database_url": "postgresql+psycopg://terrific_bites:unit-test@postgres:5432/terrific_bites",
}


def test_valid_production_settings_are_accepted() -> None:
    assert Settings(**GOOD).app_env == "production"


@pytest.mark.parametrize(
    ("override", "expected_message"),
    [
        ({"debug": True}, "DEBUG"),
        ({"admin_jwt_secret": "dev-insecure-admin-jwt-secret-change-me"}, "ADMIN_JWT_SECRET"),
        ({"admin_jwt_secret": "short"}, "ADMIN_JWT_SECRET"),
        ({"admin_cookie_domain": ""}, "ADMIN_COOKIE_DOMAIN"),
        ({"cors_allowed_origins": "*"}, "CORS_ALLOWED_ORIGINS"),
        ({"cors_allowed_origins": "http://terrific-bites.trunexus.ai"}, "CORS_ALLOWED_ORIGINS"),
        ({"cors_allowed_origins": "https://localhost:3000"}, "CORS_ALLOWED_ORIGINS"),
        ({"trusted_hosts": "*"}, "TRUSTED_HOSTS"),
        ({"trusted_hosts": "localhost"}, "TRUSTED_HOSTS"),
        ({"media_base_url": "http://localhost:8020/media"}, "MEDIA_BASE_URL"),
        (
            {"database_url": "postgresql+psycopg://postgres:postgres@postgres:5432/x"},
            "DATABASE_URL",
        ),
    ],
)
def test_unsafe_production_settings_are_refused(
    override: dict[str, Any], expected_message: str
) -> None:
    with pytest.raises(ValidationError, match=expected_message):
        Settings(**{**GOOD, **override})


def test_refusal_message_never_contains_the_secret_value() -> None:
    with pytest.raises(ValidationError) as excinfo:
        Settings(**{**GOOD, "admin_jwt_secret": "short-secret-value"})
    message = str(excinfo.value.errors()[0]["msg"])
    assert "Unsafe production configuration" in message
    assert "short-secret-value" not in message


def test_non_production_environments_are_not_restricted() -> None:
    assert Settings(app_env="development", debug=True).debug is True


def _set_cookie_headers(response: Response) -> list[str]:
    return [v.decode() for k, v in response.raw_headers if k == b"set-cookie"]


def test_admin_cookies_carry_the_configured_domain_and_secure_in_production() -> None:
    response = Response()
    set_admin_auth_cookies(
        response,
        access_token="a",
        refresh_token="r",
        csrf_token="c",
        settings=Settings(**GOOD),
    )
    headers = _set_cookie_headers(response)
    assert len(headers) == 3
    for header in headers:
        assert "Domain=terrific-bites.trunexus.ai" in header
        assert "Secure" in header
        assert "SameSite=lax" in header


def test_logout_clears_cookies_on_the_same_domain_they_were_set_on() -> None:
    response = Response()
    clear_admin_auth_cookies(response, Settings(**GOOD))
    headers = _set_cookie_headers(response)
    assert len(headers) == 3
    assert all("Domain=terrific-bites.trunexus.ai" in header for header in headers)


def test_production_requires_an_explicit_stage() -> None:
    with pytest.raises(ValidationError, match="DEPLOYMENT_STAGE must be demo or live"):
        Settings(**{**GOOD, "deployment_stage": "development"})


def test_unknown_stage_is_refused() -> None:
    with pytest.raises(ValidationError, match="DEPLOYMENT_STAGE must be one of"):
        Settings(deployment_stage="staging")


@pytest.mark.parametrize(
    "override",
    [
        {"odoo_order_push_provider": "live"},
        {"payment_provider": "real_gateway"},
        {"notification_provider": "real_sender"},
    ],
)
def test_demo_stage_refuses_any_real_provider(override: dict[str, Any]) -> None:
    with pytest.raises(ValidationError, match="DEPLOYMENT_STAGE=demo requires stub"):
        Settings(deployment_stage="demo", **override)


def test_live_stage_refuses_any_stub_provider() -> None:
    with pytest.raises(ValidationError, match="DEPLOYMENT_STAGE=live refuses stub") as excinfo:
        Settings(
            deployment_stage="live",
            payment_provider="real_gateway",
            notification_provider="real_sender",
            odoo_order_push_provider="stub",
        )
    assert "ODOO_ORDER_PUSH_PROVIDER" in str(excinfo.value)
    assert "PAYMENT_PROVIDER" not in str(excinfo.value)


def test_live_stage_refuses_to_start_before_finance_approval() -> None:
    with pytest.raises(ValidationError, match="FINANCE_RULES_APPROVED"):
        Settings(
            deployment_stage="live",
            payment_provider="real_gateway",
            notification_provider="real_sender",
            odoo_order_push_provider="live",
        )


def test_live_stage_accepts_only_real_providers() -> None:
    settings = Settings(
        deployment_stage="live",
        payment_provider="real_gateway",
        notification_provider="real_sender",
        odoo_order_push_provider="live",
        finance_rules_approved=True,
    )
    assert settings.is_demo_stage is False
