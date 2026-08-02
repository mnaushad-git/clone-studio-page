from __future__ import annotations

from app.integrations.payments.stub_provider import StubPaymentProvider


def test_stub_provider_always_succeeds_and_never_calls_a_real_gateway() -> None:
    provider = StubPaymentProvider()

    result = provider.charge(
        amount=58.15, currency="SAR", method_label="Credit Card", order_number="TB-ABC123"
    )

    assert result.success is True
    assert result.status == "succeeded"
    assert result.provider_reference.startswith("stub_")
    assert result.raw["note"] == "Stub provider — no real charge was attempted."


def test_stub_provider_generates_a_unique_reference_per_charge() -> None:
    provider = StubPaymentProvider()

    first = provider.charge(amount=10, currency="SAR", method_label="Cash", order_number="TB-1")
    second = provider.charge(amount=10, currency="SAR", method_label="Cash", order_number="TB-2")

    assert first.provider_reference != second.provider_reference
