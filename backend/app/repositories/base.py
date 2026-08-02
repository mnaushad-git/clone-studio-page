"""Shared repository base class and reusable capability mixins.

Repositories are the only place raw SQLAlchemy queries are allowed to live (rule 6,
CLAUDE.md) — services and the seed script must go through these, never construct
their own `select()`/`session.query()` calls.

Session lifecycle (commit/rollback) is owned by the caller (service layer, script, or
test fixture) — repositories only add/flush, never commit, so callers can compose
several repository calls into one transaction.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, ClassVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import Base


class BaseRepository[ModelT: Base]:
    model: type[ModelT]

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, id_: uuid.UUID) -> ModelT | None:
        return self.session.get(self.model, id_)

    def create(self, obj: ModelT) -> ModelT:
        self.session.add(obj)
        self.session.flush()
        return obj

    def update(self, obj: ModelT, **values: Any) -> ModelT:
        for key, value in values.items():
            setattr(obj, key, value)
        self.session.flush()
        return obj


class ExternalKeyRepositoryMixin[ModelT: Base]:
    """For models with a unique `external_key` column — the stable pre-Odoo join key
    every canonical seed JSON file uses (docs/catalogue/postgresql-field-mapping-draft.md).
    """

    model: type[ModelT]
    session: Session

    def get_by_external_key(self, external_key: str) -> ModelT | None:
        stmt = select(self.model).where(self.model.external_key == external_key)  # type: ignore[attr-defined]
        return self.session.execute(stmt).scalar_one_or_none()

    def upsert_by_external_key(
        self, external_key: str, values: dict[str, Any]
    ) -> tuple[ModelT, bool, bool]:
        """Create-or-update by external_key. Returns (row, created, changed) — both
        False on an idempotent no-op (existing row already matched every value).
        `created` and `changed` are mutually exclusive; a new row is never also
        reported as "changed" — callers that need three-way created/updated/skipped
        bookkeeping can rely on that.
        """
        existing = self.get_by_external_key(external_key)
        if existing is None:
            obj = self.model(external_key=external_key, **values)
            self.session.add(obj)
            self.session.flush()
            return obj, True, False

        changed = False
        for key, value in values.items():
            if getattr(existing, key) != value:
                setattr(existing, key, value)
                changed = True
        if changed:
            self.session.flush()
        return existing, False, changed


class SkuRepositoryMixin[ModelT: Base]:
    """For models with a unique `sku` column (products, product variants)."""

    model: type[ModelT]
    session: Session

    def get_by_sku(self, sku: str) -> ModelT | None:
        stmt = select(self.model).where(self.model.sku == sku)  # type: ignore[attr-defined]
        return self.session.execute(stmt).scalar_one_or_none()


class SlugRepositoryMixin[ModelT: Base]:
    """For models with a unique `slug` column (categories, products, moments,
    recipients) — the stable, human-readable identifier the public catalogue API
    routes on (never the internal UUID primary key).
    """

    model: type[ModelT]
    session: Session

    def get_by_slug(self, slug: str) -> ModelT | None:
        stmt = select(self.model).where(self.model.slug == slug)  # type: ignore[attr-defined]
        return self.session.execute(stmt).scalar_one_or_none()


class ActiveListRepositoryMixin[ModelT: Base]:
    """For models with an `active` column — lists only currently-active rows."""

    model: type[ModelT]
    session: Session
    # Optional ordering column(s), set by subclasses that have one (e.g. display_order).
    order_by: ClassVar[tuple[Any, ...]] = ()

    def list_active(self) -> Sequence[ModelT]:
        stmt = select(self.model).where(self.model.active.is_(True))  # type: ignore[attr-defined]
        if self.order_by:
            stmt = stmt.order_by(*self.order_by)
        return self.session.execute(stmt).scalars().all()
