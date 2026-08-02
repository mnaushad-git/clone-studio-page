"""Payment provider contract. Every provider (stub or real) implements this Protocol —
app.services.checkout.payment_service never imports a concrete provider class directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class PaymentResult:
    success: bool
    status: str  # "succeeded" | "failed"
    provider_reference: str
    raw: dict[str, Any]


class PaymentProvider(Protocol):
    name: str

    def charge(
        self, *, amount: float, currency: str, method_label: str, order_number: str
    ) -> PaymentResult:
        """Attempt to charge `amount` for the given order. Must never raise for a
        declined/failed charge — that's a normal PaymentResult(success=False, ...), not
        an exception. Only truly exceptional conditions (provider unreachable, invalid
        config) should raise.
        """
        ...
