"""Correlation-ID assignment and request-duration logging middleware."""

from __future__ import annotations

import logging
import re
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import correlation_id_ctx

logger = logging.getLogger("app.request")

CORRELATION_ID_HEADER = "X-Correlation-ID"

# Conservative allowlist for a client-supplied correlation id: avoids header-injection
# characters or absurd lengths ending up in logs/response headers verbatim.
_VALID_CORRELATION_ID = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")


def _resolve_correlation_id(incoming: str | None) -> str:
    if incoming and _VALID_CORRELATION_ID.match(incoming):
        return incoming
    return f"req_{uuid.uuid4().hex}"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Reads X-Correlation-ID if valid, otherwise generates one; echoes it back."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        correlation_id = _resolve_correlation_id(request.headers.get(CORRELATION_ID_HEADER))
        token = correlation_id_ctx.set(correlation_id)
        request.state.correlation_id = correlation_id
        try:
            response = await call_next(request)
        finally:
            correlation_id_ctx.reset(token)
        response.headers[CORRELATION_ID_HEADER] = correlation_id
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs one structured line per request with method, path, status, and duration."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "http_request_completed",
            extra={
                "http_method": request.method,
                "http_path": request.url.path,
                "http_status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response
