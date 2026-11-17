"""The last check before anything writes to Odoo: is this exact instance approved?

Business approvals say what may be written. This says where. ODOO_WRITE_APPROVED_TARGET
must name the instance in full as <ODOO_BASE_URL>#<ODOO_DATABASE>, so that changing either
one in the environment can't redirect writes to an instance nobody approved.
"""

from __future__ import annotations

from app.core.config import Settings
from app.integrations.odoo.exceptions import OdooWriteNotAllowedError


def odoo_write_target(settings: Settings) -> str:
    return f"{settings.odoo_base_url.rstrip('/')}#{settings.odoo_database}"


def assert_odoo_write_target_approved(settings: Settings) -> None:
    target = odoo_write_target(settings)
    if settings.odoo_write_approved_target.strip() != target:
        raise OdooWriteNotAllowedError(
            f"Odoo target {target!r} is not approved for writes: "
            "ODOO_WRITE_APPROVED_TARGET must name exactly this instance."
        )
