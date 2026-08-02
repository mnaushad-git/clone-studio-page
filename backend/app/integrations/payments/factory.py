from __future__ import annotations

from app.core.config import Settings
from app.integrations.payments.base import PaymentProvider
from app.integrations.payments.stub_provider import StubPaymentProvider

_PROVIDERS: dict[str, type[PaymentProvider]] = {
    "stub": StubPaymentProvider,
}


def get_payment_provider(settings: Settings) -> PaymentProvider:
    provider_cls = _PROVIDERS.get(settings.payment_provider)
    if provider_cls is None:
        raise ValueError(
            f"Unknown PAYMENT_PROVIDER {settings.payment_provider!r} — "
            f"expected one of {sorted(_PROVIDERS)}."
        )
    return provider_cls()
