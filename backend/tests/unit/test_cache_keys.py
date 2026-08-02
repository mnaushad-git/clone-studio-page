from __future__ import annotations

from app.cache import keys
from app.cache.keys import ProductListFilters

PREFIX = "tb"


def test_homepage_key_format() -> None:
    assert keys.homepage_key(PREFIX) == "tb:v1:catalogue:homepage:all"


def test_categories_key_format() -> None:
    assert keys.categories_key(PREFIX) == "tb:v1:catalogue:categories:all"


def test_moments_and_recipients_key_format() -> None:
    assert keys.moments_key(PREFIX) == "tb:v1:catalogue:moments:all"
    assert keys.recipients_key(PREFIX) == "tb:v1:catalogue:recipients:all"


def test_different_locales_create_different_keys() -> None:
    assert keys.homepage_key(PREFIX, locale="en") != keys.homepage_key(PREFIX, locale="ar")
    assert keys.product_detail_key(PREFIX, "cake", locale="en") != keys.product_detail_key(
        PREFIX, "cake", locale="ar"
    )


def test_product_detail_key_normalizes_slug_casing() -> None:
    assert keys.product_detail_key(PREFIX, "Chocolate-Cake") == keys.product_detail_key(
        PREFIX, "chocolate-cake"
    )
    assert keys.product_detail_key(PREFIX, "  cake  ") == keys.product_detail_key(PREFIX, "cake")


def test_product_detail_prefix_covers_every_locale_of_one_slug() -> None:
    prefix = keys.product_detail_prefix(PREFIX, "cake")
    assert keys.product_detail_key(PREFIX, "cake", locale="en").startswith(prefix)
    assert keys.product_detail_key(PREFIX, "cake", locale="ar").startswith(prefix)
    assert not keys.product_detail_key(PREFIX, "other-cake", locale="en").startswith(prefix)


def test_product_list_filters_hash_is_stable_regardless_of_argument_order() -> None:
    a = ProductListFilters(category="cakes", featured=True, limit=10, offset=0)
    b = ProductListFilters(featured=True, limit=10, offset=0, category="cakes")

    assert a.hash() == b.hash()


def test_product_list_filters_hash_differs_for_different_filters() -> None:
    a = ProductListFilters(category="cakes")
    b = ProductListFilters(category="cupcakes")

    assert a.hash() != b.hash()


def test_product_list_unsupported_parameters_do_not_alter_key() -> None:
    """Only the fields ProductListFilters declares affect the hash — anything not
    accepted by the dataclass (an unsupported query param) simply can't reach the
    normalized dict at all."""
    a = ProductListFilters(category="cakes", search="Choco ")
    b = ProductListFilters(category="cakes", search="choco")

    assert a.hash() == b.hash()


def test_product_list_key_format() -> None:
    filters = ProductListFilters(category="cakes")
    key = keys.product_list_key(PREFIX, filters)

    assert key.startswith("tb:v1:catalogue:products:")
    assert key.endswith(":all")


def test_product_list_is_cacheable_rejects_long_search() -> None:
    short = ProductListFilters(search="cake")
    long = ProductListFilters(search="x" * 41)

    assert short.is_cacheable() is True
    assert long.is_cacheable() is False


def test_product_list_is_cacheable_rejects_high_offset() -> None:
    shallow = ProductListFilters(offset=50)
    deep = ProductListFilters(offset=500)

    assert shallow.is_cacheable() is True
    assert deep.is_cacheable() is False


def test_product_list_namespace_prefix_covers_generated_keys() -> None:
    namespace = keys.product_list_namespace_prefix(PREFIX)
    key = keys.product_list_key(PREFIX, ProductListFilters(category="cakes"))

    assert key.startswith(namespace)


def test_catalogue_namespace_prefix_covers_every_resource() -> None:
    namespace = keys.catalogue_namespace_prefix(PREFIX)

    assert keys.homepage_key(PREFIX).startswith(namespace)
    assert keys.categories_key(PREFIX).startswith(namespace)
    assert keys.product_detail_key(PREFIX, "cake").startswith(namespace)
    assert keys.product_list_key(PREFIX, ProductListFilters()).startswith(namespace)
