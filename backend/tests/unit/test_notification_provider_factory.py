from __future__ import annotations

import pytest

from app.core.config import Settings
from app.integrations.notifications.factory import get_notification_provider
from app.integrations.notifications.stub_provider import StubNotificationProvider


def test_default_settings_resolve_to_the_stub_provider() -> None:
    provider = get_notification_provider(Settings())

    assert isinstance(provider, StubNotificationProvider)


def test_unknown_notification_provider_raises_instead_of_silently_falling_back() -> None:
    settings = Settings(notification_provider="some_future_provider")

    with pytest.raises(ValueError, match="some_future_provider"):
        get_notification_provider(settings)
