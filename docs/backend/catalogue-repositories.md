# Catalogue Repository Layer

Repositories are the **only** place raw SQLAlchemy `select()`/query construction is
allowed to live (rule 6, [CLAUDE.md](../../CLAUDE.md)). Services (the seed service) and
scripts must go through them.

## Module layout

```
backend/app/repositories/
    base.py                  BaseRepository + capability mixins
    catalogue/                one repository per catalogue entity
    storefront/                StorefrontSectionRepository, StorefrontSectionProductRepository
    integration/                SeedRunRepository
```

## `base.py`

`BaseRepository[ModelT: Base]` provides `get_by_id`, `create`, `update`. Three
capability mixins add behaviour to models that have the matching column, composed via
multiple inheritance (e.g. `CategoryRepository(ExternalKeyRepositoryMixin[...],
ActiveListRepositoryMixin[...], BaseRepository[...])`):

- **`ExternalKeyRepositoryMixin`** — `get_by_external_key`, `upsert_by_external_key`.
- **`SkuRepositoryMixin`** — `get_by_sku`.
- **`ActiveListRepositoryMixin`** — `list_active`, optionally ordered by a subclass's
  `order_by: ClassVar[tuple]`.

### The `(row, created, changed)` contract

Every upsert method — `upsert_by_external_key` and the bespoke `upsert_*` methods on
repositories without a stable `external_key` (prices, availability, images,
merchandising, the two join tables, recommendations) — returns a **3-tuple**, not 2:

```python
obj, created, changed = repo.upsert_by_external_key(key, values)
```

`created` and `changed` are mutually exclusive. This exists because an earlier version
returned a 2-tuple `(obj, bool)` where the bool meant "created" in the not-found branch
but "changed" in the found-and-differs branch — collapsing two different facts into one
value made every caller's "was this newly created?" check silently wrong whenever an
existing row's value changed (it counted as "created"). The seed service's
`created`/`updated`/`skipped` bookkeeping depends on telling these apart; see
[catalogue-seeding.md](catalogue-seeding.md) for how that bug was caught (idempotency
tests against real re-runs, not just single-run assertions).

## Composite-key repositories

`ProductMomentRepository` and `ProductRecipientRepository` don't extend
`BaseRepository` — their models have a composite `(product_id, moment_id)` /
`(product_id, recipient_id)` primary key, incompatible with `BaseRepository.get_by_id`'s
single-column `session.get(model, id_)`. They implement their own minimal `get`/
`list_for_product`/`upsert` instead.

## What repositories deliberately don't do

No repository commits or rolls back the session — that's the caller's job (the seed
service wraps a whole run in one `session.begin_nested()` savepoint; tests wrap each
test in an outer transaction). Repositories only `add()`/`flush()`.
