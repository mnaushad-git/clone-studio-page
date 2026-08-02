"""Stub payment provider — Launch Sprint default. Never contacts a real gateway; every
charge succeeds immediately. Exists so the checkout flow is fully exercisable (and the
Order/OrderPayment/outbox plumbing fully real) before a live payment gateway is wired
up. Swap via PAYMENT_PROVIDER in settings once real credentials exist.
"""

from __future__ import annotations

import uuid

from app.integrations.payments.base import PaymentResult


class StubPaymentProvider:
    name = "stub"

    def charge(
        self, *, amount: float, currency: str, method_label: str, order_number: str
    ) -> PaymentResult:
        reference = f"stub_{uuid.uuid4().hex[:16]}"
        return PaymentResult(
            success=True,
            status="succeeded",
            provider_reference=reference,
            raw={
                "provider": self.name,
                "note": "Stub provider — no real charge was attempted.",
                "amount": amount,
                "currency": currency,
                "method_label": method_label,
                "order_number": order_number,
            },
        )
