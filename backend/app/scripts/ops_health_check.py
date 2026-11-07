"""Prints the operational health checks as JSON. Exits 0 when all pass, 1 otherwise.

python -m app.scripts.ops_health_check
"""

from __future__ import annotations

import json
import sys

from app.core.config import get_settings
from app.core.database import session_scope
from app.core.redis import get_redis_client
from app.services.ops.health_monitor import run_health_checks, summarize


def main() -> int:
    with session_scope() as session:
        checks = run_health_checks(session, get_redis_client(), get_settings())
    summary = summarize(checks)
    print(json.dumps(summary))
    return 0 if summary["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
