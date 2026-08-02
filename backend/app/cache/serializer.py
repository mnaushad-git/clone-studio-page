"""Safe JSON codec for cached values.

Uses the stdlib `json` module (the same codec app/core/logging.py already relies on —
task brief §7: "Prefer a stable JSON codec already used by the project"), with a
`default=` hook so any Decimal/UUID/datetime/date that slips through is still encoded
losslessly as a string rather than raising. In practice every catalogue response DTO
(app/api/v1/schemas/catalogue.py) already stores money as a formatted string and ids as
`str(uuid)` before it reaches here, so this hook is a safety net, not the common path.

Only the final public response DTO (a `pydantic.BaseModel.model_dump(mode="json")`
dict) is ever passed to `dumps` — never a SQLAlchemy ORM object, session, or raw
exception (task brief §7).
"""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

# Arabic text (and any other non-ASCII content) must round-trip byte-for-byte —
# ensure_ascii=False keeps it as literal UTF-8 rather than \uXXXX escapes, which is
# both more compact and easier to eyeball in redis-cli.
_ENSURE_ASCII = False


def _default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def dumps(value: Any) -> str:
    return json.dumps(value, default=_default, ensure_ascii=_ENSURE_ASCII, separators=(",", ":"))


def loads(raw: str | bytes) -> Any:
    """Raises json.JSONDecodeError on corrupt input — callers (RedisCache.get_json)
    are responsible for catching it, deleting the corrupt key, and falling back."""
    return json.loads(raw)
