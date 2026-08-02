"""Importing this package registers every ORM model against app.core.database.Base's
metadata — required for Alembic autogenerate/upgrade and for any code that needs the
full schema (e.g. test-database setup) to see every table.
"""

from __future__ import annotations

from app.models.admin import (
    AdminAuditEvent,
    AdminSession,
    AdminUser,
    DeliverySettings,
    DeliverySlot,
    PromoCode,
)
from app.models.catalogue import (
    CatalogueCategory,
    CatalogueMoment,
    CatalogueProduct,
    CatalogueProductAvailability,
    CatalogueProductImage,
    CatalogueProductMerchandising,
    CatalogueProductMoment,
    CatalogueProductPrice,
    CatalogueProductRecipient,
    CatalogueProductRecommendation,
    CatalogueProductVariant,
    CatalogueRecipient,
)
from app.models.integration import CatalogueSeedRun, IntegrationSyncCheckpoint
from app.models.orders import (
    Order,
    OrderItem,
    OrderNotification,
    OrderOutboxEvent,
    OrderPayment,
    OrderStatusEvent,
)
from app.models.storefront import StorefrontSection, StorefrontSectionProduct

__all__ = [
    "AdminAuditEvent",
    "AdminSession",
    "AdminUser",
    "DeliverySettings",
    "DeliverySlot",
    "PromoCode",
    "Order",
    "OrderItem",
    "OrderNotification",
    "OrderOutboxEvent",
    "OrderPayment",
    "OrderStatusEvent",
    "CatalogueCategory",
    "CatalogueMoment",
    "CatalogueProduct",
    "CatalogueProductAvailability",
    "CatalogueProductImage",
    "CatalogueProductMerchandising",
    "CatalogueProductMoment",
    "CatalogueProductPrice",
    "CatalogueProductRecipient",
    "CatalogueProductRecommendation",
    "CatalogueProductVariant",
    "CatalogueRecipient",
    "CatalogueSeedRun",
    "IntegrationSyncCheckpoint",
    "StorefrontSection",
    "StorefrontSectionProduct",
]
