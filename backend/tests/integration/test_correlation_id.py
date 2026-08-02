from __future__ import annotations

import re

from fastapi.testclient import TestClient

_GENERATED_CORRELATION_ID = re.compile(r"^req_[0-9a-f]{32}$")


def test_correlation_id_generated_when_absent(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    correlation_id = response.headers.get("X-Correlation-ID")
    assert correlation_id is not None
    assert _GENERATED_CORRELATION_ID.match(correlation_id)


def test_correlation_id_propagated_when_supplied(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"X-Correlation-ID": "test-corr-id-123"})

    assert response.headers.get("X-Correlation-ID") == "test-corr-id-123"


def test_invalid_correlation_id_is_replaced_with_generated_one(client: TestClient) -> None:
    response = client.get(
        "/api/v1/health", headers={"X-Correlation-ID": "not valid! id with spaces"}
    )

    correlation_id = response.headers.get("X-Correlation-ID")
    assert correlation_id is not None
    assert correlation_id != "not valid! id with spaces"
    assert _GENERATED_CORRELATION_ID.match(correlation_id)


def test_correlation_id_is_included_in_error_envelope(client: TestClient) -> None:
    response = client.get(
        "/api/v1/does-not-exist", headers={"X-Correlation-ID": "test-corr-id-456"}
    )

    assert response.status_code == 404
    assert response.json()["error"]["correlation_id"] == "test-corr-id-456"
    assert response.headers.get("X-Correlation-ID") == "test-corr-id-456"
