from __future__ import annotations

from app.core.config import Settings
from app.integrations.notifications.base import NotificationProvider
from app.integrations.notifications.stub_provider import StubNotificationProvider

_PROVIDERS: dict[str, type[NotificationProvider]] = {
    "stub": StubNotificationProvider,
}


def get_notification_provider(settings: Settings) -> NotificationProvider:
    provider_cls = _PROVIDERS.get(settings.notification_provider)
    if provider_cls is None:
        raise ValueError(
            f"Unknown NOTIFICATION_PROVIDER {settings.notification_provider!r} — "
            f"expected one of {sorted(_PROVIDERS)}."
        )
    return provider_cls()
