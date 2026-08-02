from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "app_name" in body
    assert "version" in body


def test_health_does_not_depend_on_database_or_redis(client: TestClient, monkeypatch) -> None:
    def _fail() -> bool:
        raise AssertionError("health endpoint must not check dependencies")

    monkeypatch.setattr("app.api.v1.endpoints.health.check_database_connection", _fail)
    monkeypatch.setattr("app.api.v1.endpoints.health.check_redis_connection", _fail)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
