"""Deterministic, namespaced cache-key builders for the catalogue endpoints.

Format (task brief §6): tb:v1:catalogue:<resource>[:<qualifier>]:<locale>

No route currently varies its response by locale — the catalogue API returns every
bilingual field (name_en/name_ar, description_en/description_ar) in a single response
rather than accepting a `?locale=` parameter (there is no locale concept anywhere else
in this backend). DEFAULT_LOCALE is therefore the only locale bucket actually produced
today; the `locale` parameter is kept real (not hardcoded away) so a future per-locale
endpoint variant, or a Content-Language-negotiated response, only has to pass a
different value here rather than touching the key format.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

CACHE_KEY_VERSION = "v1"
DEFAULT_LOCALE = "all"

_NAMESPACE = "catalogue"

# Product-list cache-key hash length — short enough to keep keys compact, long enough
# that accidental collisions across the (bounded) real filter combination space are
# not a practical concern.
_HASH_LENGTH = 16


def _base(prefix: str) -> str:
    return f"{prefix}:{CACHE_KEY_VERSION}:{_NAMESPACE}"


def homepage_key(prefix: str, locale: str = DEFAULT_LOCALE) -> str:
    return f"{_base(prefix)}:homepage:{locale}"


def categories_key(prefix: str, locale: str = DEFAULT_LOCALE) -> str:
    return f"{_base(prefix)}:categories:{locale}"


def moments_key(prefix: str, locale: str = DEFAULT_LOCALE) -> str:
    return f"{_base(prefix)}:moments:{locale}"


def recipients_key(prefix: str, locale: str = DEFAULT_LOCALE) -> str:
    return f"{_base(prefix)}:recipients:{locale}"


def normalize_slug(slug: str) -> str:
    """Case is not a meaningful distinction in a slug — /products/CAKE-1 and
    /products/cake-1 must hit the same cache entry."""
    return slug.strip().lower()


def product_detail_key(prefix: str, slug: str, locale: str = DEFAULT_LOCALE) -> str:
    return f"{_base(prefix)}:product:{normalize_slug(slug)}:{locale}"


def product_detail_prefix(prefix: str, slug: str) -> str:
    """Covers every locale variant of one product's detail key — used for a bounded
    SCAN-based delete, never a full-namespace scan, when only one product changed."""
    return f"{_base(prefix)}:product:{normalize_slug(slug)}:"


def product_detail_namespace_prefix(prefix: str) -> str:
    """Every cached product-detail key across every slug and locale — used only for
    the invalidate-everything MVP path (invalidate_catalogue_all), never for a
    single-product update (see product_detail_prefix, which is scoped to one slug)."""
    return f"{_base(prefix)}:product:"


def product_list_namespace_prefix(prefix: str) -> str:
    return f"{_base(prefix)}:products:"


def catalogue_namespace_prefix(prefix: str) -> str:
    """Every cached catalogue key, across every resource and locale — the MVP
    invalidate-everything fallback (task brief §9: "acceptable for the MVP to
    invalidate the full catalogue product-list namespace after catalogue sync";
    extended here to the whole catalogue namespace for invalidate_catalogue_all)."""
    return f"{_base(prefix)}:"


# -- product-list filter normalization (task brief §15) -----------------------------

# Mirrors the actual, current query parameters on GET /api/v1/catalogue/products
# (app/api/v1/endpoints/catalogue.py) — no "sort" parameter exists on that endpoint
# today, so it is deliberately not included here; adding a normalization slot for a
# filter the endpoint doesn't accept would be misleading, not forward-compatible.
_BOOL_FIELDS = ("featured", "bestseller", "new")
_SLUG_FIELDS = ("category", "moment", "recipient")


@dataclass(frozen=True)
class ProductListFilters:
    category: str | None = None
    moment: str | None = None
    recipient: str | None = None
    featured: bool | None = None
    bestseller: bool | None = None
    new: bool | None = None
    search: str | None = None
    limit: int = 20
    offset: int = 0
    normalized: dict[str, object] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        data: dict[str, object] = {}
        for name in _SLUG_FIELDS:
            value = getattr(self, name)
            data[name] = value.strip().lower() if value else None
        for name in _BOOL_FIELDS:
            value = getattr(self, name)
            data[name] = bool(value) if value is not None else None
        data["search"] = self.search.strip().lower() if self.search else None
        data["limit"] = self.limit
        data["offset"] = self.offset
        object.__setattr__(self, "normalized", data)

    def hash(self) -> str:
        # sort_keys makes parameter order irrelevant to the resulting hash (task
        # brief §6: "Sort query parameters before hashing"); the dataclass fields
        # themselves are already a fixed, ordered set.
        canonical = json.dumps(self.normalized, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:_HASH_LENGTH]

    def is_cacheable(self, *, max_search_length: int = 40, max_offset: int = 200) -> bool:
        """Guards against unbounded key-space growth from long/arbitrary search terms
        or deep pagination (task brief §15: "Do not cache extremely high offsets",
        "Do not cache clearly one-off arbitrary searches")."""
        search = self.normalized["search"]
        if isinstance(search, str) and len(search) > max_search_length:
            return False
        offset = self.normalized["offset"]
        return not (isinstance(offset, int) and offset > max_offset)


def product_list_key(prefix: str, filters: ProductListFilters, locale: str = DEFAULT_LOCALE) -> str:
    return f"{product_list_namespace_prefix(prefix)}{filters.hash()}:{locale}"
