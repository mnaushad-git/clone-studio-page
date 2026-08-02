from __future__ import annotations

from typing import ClassVar

from app.models.catalogue.recipient import CatalogueRecipient
from app.repositories.base import (
    ActiveListRepositoryMixin,
    BaseRepository,
    ExternalKeyRepositoryMixin,
    SlugRepositoryMixin,
)


class RecipientRepository(
    ExternalKeyRepositoryMixin[CatalogueRecipient],
    SlugRepositoryMixin[CatalogueRecipient],
    ActiveListRepositoryMixin[CatalogueRecipient],
    BaseRepository[CatalogueRecipient],
):
    model = CatalogueRecipient
    order_by: ClassVar[tuple] = (CatalogueRecipient.display_order,)
