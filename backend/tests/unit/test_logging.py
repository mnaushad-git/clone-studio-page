from __future__ import annotations

import json
import logging

from app.core.logging import (
    CorrelationIdLogFilter,
    JsonFormatter,
    SecretRedactionFilter,
    correlation_id_ctx,
)


def _make_record(message: str) -> logging.LogRecord:
    return logging.LogRecord(
        name="app.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=None,
    )


def test_secret_redaction_filter_masks_configured_secret_values() -> None:
    record = _make_record("connecting to db with password=topsecret123")
    result = SecretRedactionFilter(["topsecret123"]).filter(record)

    assert result is True
    assert "topsecret123" not in record.getMessage()
    assert "***REDACTED***" in record.getMessage()


def test_secret_redaction_filter_is_noop_when_no_secret_present() -> None:
    record = _make_record("normal log line")
    SecretRedactionFilter(["topsecret123"]).filter(record)

    assert record.getMessage() == "normal log line"


def test_json_formatter_emits_valid_json_with_correlation_id() -> None:
    token = correlation_id_ctx.set("req_abc123")
    try:
        record = _make_record("something happened")
        CorrelationIdLogFilter().filter(record)
        formatted = JsonFormatter().format(record)
    finally:
        correlation_id_ctx.reset(token)

    payload = json.loads(formatted)
    assert payload["correlation_id"] == "req_abc123"
    assert payload["event"] == "something happened"
    assert payload["level"] == "INFO"
    assert payload["module"] == "app.test"
