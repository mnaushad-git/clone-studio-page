from __future__ import annotations

from typing import ClassVar

from app.models.storefront.section import StorefrontSection
from app.repositories.base import (
    ActiveListRepositoryMixin,
    BaseRepository,
    ExternalKeyRepositoryMixin,
)


class StorefrontSectionRepository(
    ExternalKeyRepositoryMixin[StorefrontSection],
    ActiveListRepositoryMixin[StorefrontSection],
    BaseRepository[StorefrontSection],
):
    model = StorefrontSection
    order_by: ClassVar[tuple] = (StorefrontSection.display_order,)
