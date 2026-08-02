from __future__ import annotations

from app.integrations.odoo.exceptions import OdooIntegrationError


def test_safe_context_redacts_known_sensitive_keys() -> None:
    exc = OdooIntegrationError(
        "boom",
        context={
            "password": "super-secret",
            "api_key": "another-secret",
            "session_id": "sess-123",
            "auth_payload": {"password": "x"},
            "cookie": "abc",
            "model": "product.template",
        },
    )

    safe = exc.safe_context()

    assert safe == {"model": "product.template"}
    assert "password" not in safe
    assert "api_key" not in safe


def test_safe_context_empty_when_no_context_given() -> None:
    exc = OdooIntegrationError("boom")

    assert exc.safe_context() == {}
