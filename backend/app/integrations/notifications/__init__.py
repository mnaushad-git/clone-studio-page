"""Notification provider integration boundary — same isolation shape as
app/integrations/payments/: NotificationService never imports a concrete provider
class, only NotificationProvider (base.py) via the factory.
"""

from __future__ import annotations

from app.integrations.notifications.base import NotificationProvider, NotificationResult
from app.integrations.notifications.factory import get_notification_provider

__all__ = ["NotificationProvider", "NotificationResult", "get_notification_provider"]
