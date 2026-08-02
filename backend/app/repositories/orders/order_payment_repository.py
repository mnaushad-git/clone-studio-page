from __future__ import annotations

from app.models.orders.order_payment import OrderPayment
from app.repositories.base import BaseRepository


class OrderPaymentRepository(BaseRepository[OrderPayment]):
    model = OrderPayment
