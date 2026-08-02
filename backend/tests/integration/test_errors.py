"""Standard error envelope: {"error": {"code", "message", "correlation_id", "details"?}}.

The 404 case is exercised end-to-end via TestClient (no route needs to exist for
that). VALIDATION_ERROR and a custom AppError are exercised directly against the
registered handler functions, since Phase 1 ships no endpoint that accepts
request parameters to trigger a 422 organically.
"""

from __future__ import annotations

import asyncio
import json

from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.core.errors import app_error_handler, validation_error_handler
from app.core.exceptions import ConflictError


def _fake_request(correlation_id: str) -> Request:
    request = Request(scope={"type": "http", "method": "GET", "path": "/x", "headers": []})
    request.state.correlation_id = correlation_id
    return request


def test_not_found_route_uses_standard_error_envelope(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    body = response.json()
    assert set(body.keys()) == {"error"}
    error = body["error"]
    assert error["code"] == "NOT_FOUND"
    assert isinstance(error["message"], str)
    assert "correlation_id" in error


def test_validation_error_handler_produces_standard_envelope_with_details() -> None:
    request = _fake_request("req_validation_test")
    exc = RequestValidationError(
        errors=[
            {
                "loc": ("query", "limit"),
                "msg": "value is not a valid integer",
                "type": "type_error.integer",
            }
        ]
    )

    response = asyncio.run(validation_error_handler(request, exc))
    payload = json.loads(bytes(response.body))

    assert response.status_code == 422
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert payload["error"]["correlation_id"] == "req_validation_test"
    assert payload["error"]["details"] == [
        {"field": "query.limit", "issue": "value is not a valid integer"}
    ]


def test_app_error_handler_produces_standard_envelope() -> None:
    request = _fake_request("req_conflict_test")
    exc = ConflictError("already exists", details=[{"field": "sku", "issue": "duplicate"}])

    response = asyncio.run(app_error_handler(request, exc))
    payload = json.loads(bytes(response.body))

    assert response.status_code == 409
    assert payload == {
        "error": {
            "code": "CONFLICT",
            "message": "already exists",
            "correlation_id": "req_conflict_test",
            "details": [{"field": "sku", "issue": "duplicate"}],
        }
    }
