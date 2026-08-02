from __future__ import annotations

from app.models.orders.order_notification import OrderNotification
from app.repositories.base import BaseRepository


class OrderNotificationRepository(BaseRepository[OrderNotification]):
    model = OrderNotification
