from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.cache import serializer


def test_round_trips_plain_json_values() -> None:
    value = {"a": 1, "b": [1, 2, 3], "c": None, "d": True}

    assert serializer.loads(serializer.dumps(value)) == value


def test_encodes_decimal_as_string() -> None:
    payload = serializer.dumps({"amount": Decimal("19.99")})

    assert serializer.loads(payload) == {"amount": "19.99"}


def test_encodes_uuid_as_string() -> None:
    value = uuid.uuid4()

    payload = serializer.dumps({"id": value})

    assert serializer.loads(payload) == {"id": str(value)}


def test_encodes_datetime_as_iso8601() -> None:
    value = datetime(2026, 7, 31, 12, 30, 0, tzinfo=UTC)

    payload = serializer.dumps({"ts": value})

    assert serializer.loads(payload) == {"ts": value.isoformat()}


def test_encodes_date_as_iso8601() -> None:
    value = date(2026, 7, 31)

    payload = serializer.dumps({"d": value})

    assert serializer.loads(payload) == {"d": "2026-07-31"}


def test_null_values_survive_round_trip() -> None:
    payload = serializer.dumps({"badge_en": None, "badge_ar": None})

    assert serializer.loads(payload) == {"badge_en": None, "badge_ar": None}


def test_arabic_text_round_trips_intact() -> None:
    arabic = "كعكة الشوكولاتة الفاخرة"

    payload = serializer.dumps({"name_ar": arabic})

    assert serializer.loads(payload) == {"name_ar": arabic}
    # Not escaped to \uXXXX — stored as literal UTF-8.
    assert "\\u" not in payload


def test_loads_raises_on_corrupt_json() -> None:
    with pytest.raises(ValueError):
        serializer.loads("{not valid json")


def test_dumps_raises_on_unserializable_object() -> None:
    class Unserializable:
        pass

    with pytest.raises(TypeError):
        serializer.dumps({"x": Unserializable()})
