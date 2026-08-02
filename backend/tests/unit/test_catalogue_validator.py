"""Unit tests for scripts/validate_catalogue.py (Phase 2A catalogue tooling).

scripts/ is a standalone script directory (not part of the app.* package), so
it is added to sys.path directly here rather than via an installed package.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import validate_catalogue as vc  # noqa: E402


def make_category(key="terrific_bites.category.cakes", slug="cakes", name="Cakes", parent=None):
    return {
        "external_key": key,
        "slug": slug,
        "name_en": name,
        "parent_external_key": parent,
    }


def make_product(
    key="terrific_bites.product.a",
    slug="a",
    sku="TB-CAK-001",
    category="terrific_bites.category.cakes",
    price=10,
    name="A",
):
    return {
        "external_key": key,
        "slug": slug,
        "sku": sku,
        "sku_generated": True,
        "sku_requires_confirmation": True,
        "name_en": name,
        "description_en": "A description",
        "description_ar": None,
        "name_ar": None,
        "category_external_key": category,
        "sales_price": price,
        "primary_image": {
            "original_path": "src/assets/does-not-exist-for-testing.jpg",
            "exists": True,
        },
        "additional_images": [],
    }


def make_merch(product_key="terrific_bites.product.a", moments=None, recipients=None):
    return {
        "product_external_key": product_key,
        "moments": moments or [],
        "recipients": recipients or [],
    }


def base_data(**overrides) -> vc.CatalogueData:
    defaults = dict(
        categories=[make_category()],
        products=[make_product()],
        merchandising=[make_merch()],
        moments=[
            {
                "external_key": "terrific_bites.moment.birthday",
                "slug": "birthday",
                "name_en": "Birthday",
            }
        ],
        recipients=[
            {
                "external_key": "terrific_bites.recipient.for-him",
                "slug": "for-him",
                "name_en": "For Him",
            }
        ],
        recommendations=[],
    )
    defaults.update(overrides)
    return vc.CatalogueData(**defaults)


def errors_of(issues: list[vc.Issue]) -> list[vc.Issue]:
    return [i for i in issues if i.severity == vc.ERROR]


def test_duplicate_sku_detected():
    data = base_data(
        products=[
            make_product(key="terrific_bites.product.a", slug="a", sku="TB-CAK-001"),
            make_product(key="terrific_bites.product.b", slug="b", sku="TB-CAK-001"),
        ],
        merchandising=[
            make_merch("terrific_bites.product.a"),
            make_merch("terrific_bites.product.b"),
        ],
    )
    issues = vc.run_validation(data)
    codes = {i.code for i in errors_of(issues)}
    assert "duplicate_sku" in codes


def test_duplicate_external_key_detected():
    data = base_data(
        products=[
            make_product(key="terrific_bites.product.a", slug="a", sku="TB-CAK-001"),
            make_product(key="terrific_bites.product.a", slug="a-2", sku="TB-CAK-002"),
        ],
        merchandising=[make_merch("terrific_bites.product.a")],
    )
    issues = vc.run_validation(data)
    codes = {i.code for i in errors_of(issues)}
    assert "duplicate_external_key" in codes


def test_duplicate_slug_detected():
    data = base_data(
        categories=[
            make_category(key="terrific_bites.category.cakes", slug="cakes"),
            make_category(key="terrific_bites.category.cupcakes", slug="cakes"),
        ],
    )
    issues = vc.run_validation(data)
    codes = {i.code for i in errors_of(issues)}
    assert "duplicate_slug" in codes


def test_missing_category_reference_detected():
    data = base_data(
        products=[make_product(category="terrific_bites.category.does-not-exist")],
    )
    issues = vc.run_validation(data)
    codes = {i.code for i in errors_of(issues)}
    assert "product_invalid_category_reference" in codes


def test_product_without_category_detected():
    product = make_product()
    product["category_external_key"] = None
    data = base_data(products=[product])
    issues = vc.run_validation(data)
    codes = {i.code for i in errors_of(issues)}
    assert "product_missing_category" in codes


def test_missing_image_file_detected():
    # make_product() already points at a deliberately nonexistent asset path
    data = base_data()
    issues = vc.run_validation(data)
    codes = {i.code for i in errors_of(issues)}
    assert "missing_image_file" in codes


def test_invalid_merchandising_reference_detected():
    data = base_data(
        merchandising=[make_merch(product_key="terrific_bites.product.does-not-exist")],
    )
    issues = vc.run_validation(data)
    codes = {i.code for i in errors_of(issues)}
    assert "invalid_merchandising_product_reference" in codes


def test_invalid_moment_reference_detected():
    data = base_data(
        merchandising=[make_merch(moments=["terrific_bites.moment.does-not-exist"])],
    )
    issues = vc.run_validation(data)
    codes = {i.code for i in errors_of(issues)}
    assert "invalid_moment_reference" in codes


def test_invalid_recipient_reference_detected():
    data = base_data(
        merchandising=[make_merch(recipients=["terrific_bites.recipient.does-not-exist"])],
    )
    issues = vc.run_validation(data)
    codes = {i.code for i in errors_of(issues)}
    assert "invalid_recipient_reference" in codes


def test_invalid_recommendation_reference_detected():
    data = base_data(
        recommendations=[
            {
                "product_external_key": "terrific_bites.product.a",
                "recommended_product_external_key": "terrific_bites.product.does-not-exist",
            },
        ],
    )
    issues = vc.run_validation(data)
    codes = {i.code for i in errors_of(issues)}
    assert "invalid_recommendation_reference" in codes


def test_self_referencing_recommendation_detected():
    data = base_data(
        recommendations=[
            {
                "product_external_key": "terrific_bites.product.a",
                "recommended_product_external_key": "terrific_bites.product.a",
            },
        ],
    )
    issues = vc.run_validation(data)
    codes = {i.code for i in errors_of(issues)}
    assert "self_referencing_recommendation" in codes


def test_invalid_price_detected():
    data = base_data(products=[make_product(price=-5)])
    issues = vc.run_validation(data)
    codes = {i.code for i in errors_of(issues)}
    assert "invalid_price" in codes


def test_missing_mandatory_name_detected():
    product = make_product()
    product["name_en"] = ""
    data = base_data(products=[product])
    issues = vc.run_validation(data)
    codes = {i.code for i in errors_of(issues)}
    assert "missing_mandatory_name_en" in codes


def test_circular_category_parent_detected():
    a = make_category(key="terrific_bites.category.a", slug="a", parent="terrific_bites.category.b")
    b = make_category(key="terrific_bites.category.b", slug="b", parent="terrific_bites.category.a")
    data = base_data(categories=[a, b], products=[], merchandising=[])
    issues = vc.run_validation(data)
    codes = {i.code for i in errors_of(issues)}
    assert "circular_category_parent" in codes


def test_minimal_valid_catalogue_has_no_errors():
    product = make_product()
    product["primary_image"] = {"original_path": "src/assets/prod-swiss.jpg", "exists": True}
    data = base_data(products=[product])
    issues = vc.run_validation(data)
    assert errors_of(issues) == []


def test_real_seed_data_passes_validation():
    """Acceptance check: the canonical data/catalogue/*.json files this phase
    produced must themselves be internally consistent."""
    data = vc.load_catalogue()
    issues = vc.run_validation(data)
    errors = errors_of(issues)
    assert errors == [], f"Unexpected blocking errors in real catalogue data: {errors}"
    assert len(data.products) >= 1
    assert len(data.categories) >= 1
