"""Admin product catalogue view + merchandising edits (task brief §10).

Read-only over everything Odoo-owned (identity, SKU, price, variants) — only
CatalogueProductMerchandising columns are ever written here, and only the ones
already schema-separated as Admin-Portal-owned (data-ownership.md). Moments/
recipients tagging is display-only in this MVP pass (editing that many-to-many
association is a separate feature, not a merchandising-column PATCH — noted as a
known gap in the Admin Portal MVP completion report).
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy.orm import Session
from starlette.requests import Request

from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.admin.admin_user import AdminUser
from app.models.catalogue.product import CatalogueProduct
from app.models.catalogue.product_merchandising import CatalogueProductMerchandising
from app.repositories.catalogue.moment_repository import MomentRepository
from app.repositories.catalogue.product_merchandising_repository import (
    ProductMerchandisingRepository,
)
from app.repositories.catalogue.product_moment_repository import ProductMomentRepository
from app.repositories.catalogue.product_recipient_repository import ProductRecipientRepository
from app.repositories.catalogue.product_repository import ProductRepository
from app.repositories.catalogue.recipient_repository import RecipientRepository
from app.services.admin.audit_service import AuditService
from app.services.catalogue.catalogue_query_service import (
    _current_price,
    _default_variant,
    _format_price,
    _image_out,
    _primary_image,
)

# Every field a PATCH request is allowed to touch — anything else on the merchandising
# row (or any field on CatalogueProduct itself) is Odoo/seed-owned and read-only here.
_EDITABLE_MERCHANDISING_FIELDS = frozenset(
    {
        "featured",
        "is_new",
        "is_bestseller",
        "storefront_visible",
        "display_order",
        "badge_en",
        "badge_ar",
    }
)


class ProductAdminService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.products = ProductRepository(session)
        self.merchandising = ProductMerchandisingRepository(session)
        self.product_moments = ProductMomentRepository(session)
        self.product_recipients = ProductRecipientRepository(session)
        self.moments = MomentRepository(session)
        self.recipients = RecipientRepository(session)
        self.audit = AuditService(session)

    def list_products(
        self,
        *,
        category_slug: str | None = None,
        active: bool | None = None,
        featured: bool | None = None,
        is_bestseller: bool | None = None,
        is_new: bool | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[CatalogueProduct], int]:
        return self.products.search_admin(
            category_slug=category_slug,
            active=active,
            featured=featured,
            is_bestseller=is_bestseller,
            is_new=is_new,
            search=search,
            limit=limit,
            offset=offset,
        )

    def get_product(self, product_id: uuid.UUID) -> CatalogueProduct:
        product = self.products.get_by_id(product_id)
        if product is None:
            raise NotFoundError(f"No product found with id {product_id}.")
        return product

    def moment_recipient_names(self, product: CatalogueProduct) -> tuple[list[str], list[str]]:
        moment_links = [
            link for link in self.product_moments.list_for_product(product.id) if link.active
        ]
        recipient_links = [
            link for link in self.product_recipients.list_for_product(product.id) if link.active
        ]
        moments_by_id = {m.id: m.name_en for m in self.moments.list_active()}
        recipients_by_id = {r.id: r.name_en for r in self.recipients.list_active()}
        moment_names = [
            moments_by_id[link.moment_id]
            for link in moment_links
            if link.moment_id in moments_by_id
        ]
        recipient_names = [
            recipients_by_id[link.recipient_id]
            for link in recipient_links
            if link.recipient_id in recipients_by_id
        ]
        return moment_names, recipient_names

    @staticmethod
    def price_and_currency(product: CatalogueProduct) -> tuple[str | None, str | None]:
        variant = _default_variant(product)
        price = _current_price(variant)
        if price is None:
            return None, None
        return _format_price(price), price.currency

    @staticmethod
    def primary_image_url(product: CatalogueProduct) -> str | None:
        image_out = _image_out(_primary_image(product))
        return image_out.url if image_out else None

    def update_merchandising(
        self,
        product_id: uuid.UUID,
        updates: dict[str, Any],
        *,
        admin: AdminUser,
        request: Request | None = None,
    ) -> CatalogueProductMerchandising:
        product = self.get_product(product_id)

        disallowed = set(updates) - _EDITABLE_MERCHANDISING_FIELDS
        if disallowed:
            raise ForbiddenError(
                f"Fields {sorted(disallowed)} are Odoo/seed-owned and cannot be edited here."
            )

        merch = product.merchandising
        if merch is None:
            raise NotFoundError(
                f"Product {product.sku!r} has no merchandising row — this indicates an "
                "incomplete catalogue seed/import, not a normal admin-editable state."
            )

        before = {field: getattr(merch, field) for field in updates}
        for field, value in updates.items():
            setattr(merch, field, value)
        self.session.flush()

        self.audit.record(
            admin=admin,
            admin_email=admin.email,
            action="admin.product_merchandising_updated",
            entity_type="product",
            entity_id=str(product.id),
            before=before,
            after=dict(updates),
            request=request,
        )
        return merch
