"""Payment provider integration boundary.

Mirrors app/integrations/odoo/'s isolation principle: every payment-gateway-specific
detail lives behind PaymentProvider (base.py). Swapping the stub for a real gateway
(Moyasar, HyperPay, Tap, Stripe, ...) later means adding one new module here and
changing `payment_provider` in settings — app/services/checkout/payment_service.py and
everything above it never changes.
"""

from __future__ import annotations

from app.integrations.payments.base import PaymentProvider, PaymentResult
from app.integrations.payments.factory import get_payment_provider

__all__ = ["PaymentProvider", "PaymentResult", "get_payment_provider"]
