# Catalogue SQLAlchemy Models

Companion to [postgresql-catalogue-schema.md](postgresql-catalogue-schema.md) — this
document covers the ORM layer specifically: module layout, mixins, and where each
model deviates from a literal 1:1 schema mirror.

## Module layout

```
backend/app/models/
    mixins.py              UUIDPrimaryKeyMixin, TimestampMixin, SourceSyncMixin
    catalogue/
        category.py, product.py, product_variant.py, product_price.py,
        product_availability.py, product_image.py, product_merchandising.py,
        moment.py, recipient.py, product_moment.py, product_recipient.py,
        product_recommendation.py
    storefront/
        section.py, section_product.py
    integration/
        sync_checkpoint.py, seed_run.py
    __init__.py             imports every model so app.core.database.Base.metadata
                             is complete — required by Alembic autogenerate and by
                             the test-database fixture
```

This tree follows the phase's explicit instruction
(`backend/app/models/catalogue|storefront|integration/`), which differs from
[target-architecture.md](../architecture/target-architecture.md) §7's aspirational
`app/modules/catalogue/` layout. That target tree doesn't exist yet anywhere in the
codebase (no business module has been built until now) — this is a deviation from an
unrealized target, not a conflict with anything implemented. Revisit when/if the
`modules/` restructuring actually happens.

## Mixins (`app/models/mixins.py`)

- **`UUIDPrimaryKeyMixin`** — `id: UUID`, Python-side `default=uuid.uuid4`. Not used
  by `CatalogueProductMoment`/`CatalogueProductRecipient` (composite PK) or
  `CatalogueSeedRun`... actually seed runs *do* use it; only the two pure join tables
  opt out.
- **`TimestampMixin`** — `created_at`/`updated_at`, both `server_default=func.now()`,
  `updated_at` also `onupdate=func.now()`. `CatalogueSeedRun` does **not** use this
  mixin — it declares its own bare `created_at` only, since a seed-run record is
  append-only and should never appear to have been "updated" after the fact.
- **`SourceSyncMixin`** — `source_system` (default `"seed"`), `source_updated_at`,
  `last_synced_at`. Applied to every entity that will eventually sync from Odoo
  (categories, products, variants, prices, availability, images) and to nothing else
  (moments/recipients/merchandising/sections are PostgreSQL/Admin-native and have no
  Odoo counterpart to sync from).

## Why `Base.metadata` needs `app/models/__init__.py`

`app/core/database.py` defines the single `Base` all models inherit from, but doesn't
import any model itself (avoiding a circular import: models import `Base` from
`core.database`, so `core.database` can't import models back). `app/models/__init__.py`
is the one place that imports every model, purely for its side effect of registering
each table on `Base.metadata`. `app/db/alembic/env.py` imports `app.models` for exactly
this reason; the test-database fixture (`tests/conftest.py`) relies on the same
migration path, not a direct metadata import, so it doesn't need this import itself.

## Repository-facing contract

Every model that a repository's `ExternalKeyRepositoryMixin`/`SkuRepositoryMixin`/
`ActiveListRepositoryMixin` operates on must expose the matching plain attribute
(`external_key`, `sku`, `active`) — see
[catalogue-repositories.md](catalogue-repositories.md). This is enforced by mypy's
generic bound (`class ExternalKeyRepositoryMixin[ModelT: Base]`) only loosely (the
bound is `Base`, not a protocol with `external_key`); a model missing the column would
fail at runtime (`AttributeError`) rather than at type-check time. Acceptable for
Phase 3's scope — introducing a `Protocol` for this is deferred until it's actually
needed by a second consumer.
