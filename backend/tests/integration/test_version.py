from __future__ import annotations

from fastapi.testclient import TestClient


def test_version_returns_expected_shape(client: TestClient) -> None:
    response = client.get("/api/v1/version")

    assert response.status_code == 200
    body = response.json()
    assert body["api_version"] == "v1"
    assert "app_version" in body
    assert "app_env" in body


def test_version_does_not_expose_secrets_or_infra_details(client: TestClient) -> None:
    response = client.get("/api/v1/version")
    body = response.json()

    assert set(body.keys()) == {"app_version", "app_env", "api_version"}
    assert "database_url" not in body
    assert "odoo_password" not in body
