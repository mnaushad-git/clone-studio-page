"""Admin Portal domain models: staff identity/sessions, promo codes, delivery
configuration, and the administrative audit trail. All PostgreSQL/FastAPI-owned —
never touched by Odoo sync (matches data-ownership.md's separation of
Odoo-controlled vs. Admin-Portal-controlled tables).
"""

from __future__ import annotations

from app.models.admin.admin_audit_event import AdminAuditEvent
from app.models.admin.admin_session import AdminSession
from app.models.admin.admin_user import AdminUser
from app.models.admin.delivery_settings import DeliverySettings
from app.models.admin.delivery_slot import DeliverySlot
from app.models.admin.promo_code import PromoCode

__all__ = [
    "AdminAuditEvent",
    "AdminSession",
    "AdminUser",
    "DeliverySettings",
    "DeliverySlot",
    "PromoCode",
]
