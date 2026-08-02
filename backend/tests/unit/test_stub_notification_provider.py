from __future__ import annotations

from app.integrations.notifications.stub_provider import StubNotificationProvider


def test_stub_provider_email_always_succeeds_and_never_sends_a_real_email() -> None:
    provider = StubNotificationProvider()

    result = provider.send_email(to="sara@example.com", subject="Order confirmed", body="Thanks!")

    assert result.success is True
    assert result.status == "sent"
    assert result.provider_reference.startswith("stub_email_")
    assert result.raw["note"] == "Stub provider — no real email was sent."


def test_stub_provider_sms_always_succeeds_and_never_sends_a_real_sms() -> None:
    provider = StubNotificationProvider()

    result = provider.send_sms(to="+966500000000", body="Order confirmed")

    assert result.success is True
    assert result.status == "sent"
    assert result.provider_reference.startswith("stub_sms_")
    assert result.raw["note"] == "Stub provider — no real SMS was sent."


def test_stub_provider_generates_unique_references_per_send() -> None:
    provider = StubNotificationProvider()

    first = provider.send_email(to="a@example.com", subject="x", body="y")
    second = provider.send_email(to="a@example.com", subject="x", body="y")

    assert first.provider_reference != second.provider_reference
