"""Readiness tests monkeypatch the connectivity checks at their call site.

This sandbox has no reachable PostgreSQL/Redis instance, so these tests prove the
readiness endpoint's branching/status-code/response-shape behaviour without
depending on live infrastructure. A live-infra smoke test (curl against a real
docker-compose stack) is documented in docs/backend/local-development.md.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_readiness_success_when_dependencies_available(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("app.api.v1.endpoints.health.check_database_connection", lambda: True)
    monkeypatch.setattr("app.api.v1.endpoints.health.check_redis_connection", lambda: True)

    response = client.get("/api/v1/readiness")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["dependencies"] == {"database": "ok", "redis": "ok"}


def test_readiness_fails_when_database_unavailable(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("app.api.v1.endpoints.health.check_database_connection", lambda: False)
    monkeypatch.setattr("app.api.v1.endpoints.health.check_redis_connection", lambda: True)

    response = client.get("/api/v1/readiness")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "unavailable"
    assert body["dependencies"] == {"database": "unavailable", "redis": "ok"}


def test_readiness_fails_when_redis_unavailable(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("app.api.v1.endpoints.health.check_database_connection", lambda: True)
    monkeypatch.setattr("app.api.v1.endpoints.health.check_redis_connection", lambda: False)

    response = client.get("/api/v1/readiness")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "unavailable"
    assert body["dependencies"] == {"database": "ok", "redis": "unavailable"}
