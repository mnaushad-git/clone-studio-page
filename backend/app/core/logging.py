"""Structured JSON logging with correlation-id propagation and secret redaction."""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from typing import Any

from app.core.config import SECRET_FIELD_NAMES, get_settings

# Set by CorrelationIdMiddleware for the lifetime of a request; read by every log
# record emitted while handling that request, without threading the value through
# every function signature.
correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="-")

_RESERVED_LOG_RECORD_ATTRS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "message",
    "asctime",
    "taskName",
}


class CorrelationIdLogFilter(logging.Filter):
    """Attaches the active request's correlation id to every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "correlation_id"):
            record.correlation_id = correlation_id_ctx.get()
        return True


class SecretRedactionFilter(logging.Filter):
    """Replaces any configured secret value that appears verbatim in a log message.

    Belt-and-braces alongside not logging settings.<secret> directly: if a secret
    value is accidentally interpolated into a message, it is still masked before
    reaching any log sink.
    """

    def __init__(self, secret_values: list[str]) -> None:
        super().__init__()
        self._secret_values = [value for value in secret_values if value]

    def filter(self, record: logging.LogRecord) -> bool:
        if not self._secret_values:
            return True
        message = record.getMessage()
        redacted = message
        for secret in self._secret_values:
            if secret in redacted:
                redacted = redacted.replace(secret, "***REDACTED***")
        if redacted != message:
            record.msg = redacted
            record.args = ()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "correlation_id": getattr(record, "correlation_id", "-"),
            "module": record.name,
            "event": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED_LOG_RECORD_ATTRS and key not in payload:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    """Install one JSON stdout handler on the root logger for app and uvicorn logs."""
    settings = get_settings()
    secret_values = [
        str(getattr(settings, field))
        for field in SECRET_FIELD_NAMES
        if getattr(settings, field, None)
    ]

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(CorrelationIdLogFilter())
    handler.addFilter(SecretRedactionFilter(secret_values))

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(settings.log_level.upper())

    for uvicorn_logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(uvicorn_logger_name)
        uvicorn_logger.handlers = [handler]
        uvicorn_logger.propagate = False
