# Cache Invalidation

Single call site: `CacheInvalidationService` (`backend/app/cache/invalidation.py`).
Nothing else in the codebase calls `RedisCache.delete*`/`delete_by_prefix` for
catalogue keys.

## Ordering contract

Every caller invalidates **strictly after** the PostgreSQL transaction that changed
the underlying data has committed — never before, and never from data that might
still be rolled back. Invalidation failure (Redis down) never rolls back or fails an
otherwise-successful write; it's logged and the TTL eventually expires the stale
entry instead.

```
Odoo/Admin write -> PostgreSQL transaction -> commit succeeds -> cache invalidation
                                                                     (best-effort)
```

## Methods

| Method | Deletes |
|---|---|
| `invalidate_homepage()` | Homepage key, every locale |
| `invalidate_categories()` | Categories key, every locale |
| `invalidate_moments()` | Moments key, every locale |
| `invalidate_recipients()` | Recipients key, every locale |
| `invalidate_product(slug)` | That slug's product-detail key, every locale (bounded SCAN, not namespace-wide) |
| `invalidate_product_lists()` | The entire product-list namespace (SCAN-based) |
| `invalidate_catalogue_all()` | Every one of the above, in one call |
| `invalidate_after_product_sync(sync_status)` | `invalidate_catalogue_all()` — but only if `sync_status` is `SUCCEEDED` or `PARTIALLY_COMPLETED`; a `FAILED` run invalidates nothing |
| `invalidate_after_merchandising_update(slug)` | Product detail + homepage + product lists — never categories/moments/recipients, since one product's merchandising fields can't change those |

## Odoo catalogue sync hook

`OdooCatalogueSyncService.sync_all()` (`app/services/catalogue/
odoo_catalogue_sync_service.py`) calls `invalidate_after_product_sync(status)`
immediately after the run's final `self.session.commit()` — after the whole six-phase
run (categories -> products -> variants -> prices -> images -> stock) has finished,
not per-record.

This is the documented MVP trade-off: precise per-changed-product invalidation would
require threading a set of changed slugs/categories through six phases run by a
Celery beat task. The task brief explicitly sanctions the coarser alternative:

> "Because targeted product-list invalidation may be complex initially, it is
> acceptable for the MVP to invalidate the full catalogue product-list namespace
> after catalogue sync. Prefer correctness over overly precise invalidation."

If `sync_all()` can't even reach Odoo (`client is None` — Odoo unconfigured or
unreachable), the run is marked `FAILED` and returns before the invalidation call is
ever reached — equivalent to, and tested via, the same "`FAILED` invalidates
nothing" contract.

## Admin merchandising update hook

`PATCH /api/v1/admin/products/{id}/merchandising`
(`app/api/v1/endpoints/admin/products.py`) calls
`invalidate_after_merchandising_update(product.slug)` immediately after
`session.commit()`. A request that never commits (disallowed field, validation
error) never invalidates anything.

## Manual invalidation

`POST /api/v1/admin/system/cache/invalidate` (SUPER_ADMIN only, CSRF-protected) —
see `app/api/v1/endpoints/admin/system.py`. Body:

```json
{"operation": "homepage" | "categories" | "product" | "moments" | "recipients" | "product_lists" | "all", "slug": "only-for-product"}
```

Returns `{"operation": ..., "slug": ..., "deleted_keys": <int>}`. No arbitrary Redis
command or raw key input is ever accepted; every operation maps to one of the
`CacheInvalidationService` methods above. Every call is written to the admin audit
log (`action="admin.cache_invalidated"`).

## Prefix invalidation strategy

`RedisCache.delete_by_prefix` uses `SCAN` (never `KEYS`), matching in bounded batches
of 500 keys per `DELETE`, and logs the number of keys actually deleted
(`cache_deleted_keys`). This is what backs `invalidate_product`,
`invalidate_product_lists`, and the product-detail-namespace sweep inside
`invalidate_catalogue_all`.

## Known limitation

Moment/recipient product-mapping changes have no dedicated Admin endpoint yet (see
`app/services/admin/product_admin_service.py`'s own note on this gap) —
`invalidate_moments()`/`invalidate_recipients()` exist and are ready to be wired into
that endpoint once it lands, per the task brief's guidance for that case.
