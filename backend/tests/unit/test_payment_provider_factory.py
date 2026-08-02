from __future__ import annotations

import pytest

from app.core.config import Settings
from app.integrations.payments.factory import get_payment_provider
from app.integrations.payments.stub_provider import StubPaymentProvider


def test_default_settings_resolve_to_the_stub_provider() -> None:
    provider = get_payment_provider(Settings())

    assert isinstance(provider, StubPaymentProvider)


def test_unknown_payment_provider_raises_instead_of_silently_falling_back() -> None:
    settings = Settings(payment_provider="some_future_gateway")

    with pytest.raises(ValueError, match="some_future_gateway"):
        get_payment_provider(settings)
