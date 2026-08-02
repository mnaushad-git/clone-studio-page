from __future__ import annotations

from typing import ClassVar

from app.models.catalogue.moment import CatalogueMoment
from app.repositories.base import (
    ActiveListRepositoryMixin,
    BaseRepository,
    ExternalKeyRepositoryMixin,
    SlugRepositoryMixin,
)


class MomentRepository(
    ExternalKeyRepositoryMixin[CatalogueMoment],
    SlugRepositoryMixin[CatalogueMoment],
    ActiveListRepositoryMixin[CatalogueMoment],
    BaseRepository[CatalogueMoment],
):
    model = CatalogueMoment
    order_by: ClassVar[tuple] = (CatalogueMoment.display_order,)
