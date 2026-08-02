# Cache Key Conventions

All key-building logic lives in `backend/app/cache/keys.py`
(unit-tested in `backend/tests/unit/test_cache_keys.py`). Route handlers and services
never hand-build a cache key string themselves.

## Format

```
{prefix}:{version}:catalogue:{resource}[:{qualifier}]:{locale}
```

- `prefix` — `CACHE_KEY_PREFIX`, default `tb`.
- `version` — `CACHE_KEY_VERSION` constant (`"v1"`), bumped on any incompatible change
  to what a cached value's JSON shape means, so an old TTL'd-but-not-yet-expired entry
  is never misread by new code.
- `locale` — every catalogue response today returns both `_en`/`_ar` fields in one
  payload (there is no `?locale=` parameter anywhere in this API), so `DEFAULT_LOCALE
  = "all"` is the only locale bucket actually produced. The parameter is real, not
  hardcoded away, so a future per-locale response variant only needs to pass a
  different value here.

## Examples

```
tb:v1:catalogue:homepage:all
tb:v1:catalogue:categories:all
tb:v1:catalogue:moments:all
tb:v1:catalogue:recipients:all
tb:v1:catalogue:product:chocolate-fudge-cake:all
tb:v1:catalogue:products:3f9a2c1e7b4d5f60:all
```

## Product detail

- Slug is normalized (`.strip().lower()`) before being placed in the key —
  `/products/Chocolate-Cake` and `/products/chocolate-cake` hit the same entry.
- `product_detail_prefix(prefix, slug)` returns the prefix covering every locale
  variant of one slug, used for a bounded SCAN delete when only that product changed.

## Product-list keys (optional endpoint)

`GET /catalogue/products` supports `category`, `moment`, `recipient`, `featured`,
`bestseller`, `new`, `search`, `limit`, `offset` — the only filters this endpoint
actually accepts (no `sort` parameter exists on it today, so none is normalized for
hashing either).

`ProductListFilters` (`app/cache/keys.py`):

1. Normalizes: slug filters lowercased/trimmed, booleans coerced to `bool | None`,
   `search` lowercased/trimmed.
2. Builds a canonical dict and hashes it with `sha256`, `sort_keys=True` — parameter
   order in the query string never changes the resulting key.
3. Unsupported query parameters can't reach the hash at all (they're not fields on
   the dataclass), so they can't cause an unintended cache-key split.
4. `is_cacheable()` rejects (falls back to `BYPASS`, no caching) search terms longer
   than 40 characters and offsets past 200 — arbitrary one-off searches and deep
   pagination aren't worth a cache slot.
5. `CACHE_MAX_PRODUCT_LIST_KEYS` bounds how many distinct filter combinations get
   cached at once (tracked via a bounded Redis `SADD`, see `RedisCache.sadd_bounded`)
   — once the cap is hit, new combinations are served normally but not cached; an
   already-tracked combination keeps working.

## Testing

`test_cache_keys.py` covers: exact key format per resource, locale variance, slug-case
normalization, parameter-order independence, unsupported-parameter exclusion, and the
cacheability guards. `test_cache_redis.py::test_sadd_bounded_*` covers the key-space
cap at the Redis layer.
