#!/usr/bin/env python3
"""Proves the catalogue import can be rerun, including after a create that timed out.

The timeout is simulated faithfully: the create really happens in Odoo and commits, and only
then does the client see a timeout. `apply-with-timeout` runs one import that way on an empty
catalogue; rerunning the import must then adopt that record rather than copy it.

    native_stack.py run --role catalogue_import -- python
        deploy/native/verify_import_idempotency.py apply-with-timeout
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path
from typing import Any

from app.integrations.odoo.exceptions import OdooTimeoutError
from app.integrations.odoo.write_client import OdooWriteClient

REPO = Path(__file__).resolve().parents[2]
OUTPUT = REPO / ".local-integration" / "import-timeout-run.json"
# The third product, far enough in that earlier records have committed around it.
TIME_OUT_ON_PRODUCT = 3


def apply_with_timeout() -> None:
    real_create = OdooWriteClient.create
    created = {"count": 0}

    def create_then_time_out(
        self: OdooWriteClient, model: str, values: dict[str, Any], **kw: Any
    ) -> int:
        record_id = real_create(self, model, values, **kw)
        if model == "product.template":
            created["count"] += 1
            if created["count"] == TIME_OUT_ON_PRODUCT:
                print(
                    f"SIMULATED TIMEOUT after committing product.template {record_id}",
                    flush=True,
                )
                raise OdooTimeoutError(
                    "simulated: the create committed, the client timed out"
                )
        return record_id

    OdooWriteClient.create = create_then_time_out  # type: ignore[method-assign]
    sys.argv = [
        "import_odoo_catalogue",
        "--apply",
        "--confirm-import",
        "--output",
        str(OUTPUT),
    ]
    runpy.run_module("app.scripts.import_odoo_catalogue", run_name="__main__")


if __name__ == "__main__":
    if sys.argv[1:] != ["apply-with-timeout"]:
        raise SystemExit("usage: verify_import_idempotency.py apply-with-timeout")
    apply_with_timeout()
