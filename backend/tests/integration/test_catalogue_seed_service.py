"""Integration tests for the catalogue seed service, run against real PostgreSQL and
the actual canonical JSON files under data/catalogue/ (26 products, 6 categories — see
docs/catalogue/current-catalogue-audit.md for the authoritative counts these assert
against).
"""

from __future__ import annotations

import copy

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.catalogue import seed_service as seed_service_module
from app.services.catalogue.seed_data_loader import CatalogueSeedData, load_catalogue_seed_data
from app.services.catalogue.seed_service import CatalogueSeedService


def _table_count(session: Session, table: str) -> int:
    return session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()  # noqa: S608


def test_seed_dry_run_does_not_write(db_session: Session) -> None:
    service = CatalogueSeedService(db_session)

    result = service.run(dry_run=True)

    assert result.status == "DRY_RUN"
    assert result.created_count == 344
    assert _table_count(db_session, "catalogue_products") == 0
    assert _table_count(db_session, "catalogue_categories") == 0
    # The dry-run attempt itself is still recorded for auditability.
    assert _table_count(db_session, "catalogue_seed_runs") == 1


def test_first_seed_inserts_expected_records(db_session: Session) -> None:
    service = CatalogueSeedService(db_session)

    result = service.run(dry_run=False)

    assert result.status == "SUCCESS"
    assert result.failed_count == 0
    assert result.counts_by_entity["categories"]["created"] == 6
    assert result.counts_by_entity["products"]["created"] == 26
    assert result.counts_by_entity["moments"]["created"] == 6
    assert result.counts_by_entity["recipients"]["created"] == 4
    # 24 simple-turned-variant_parent products x 2 sizes + extra-icecream's 3 sizes
    # (51) + buttercream-cake's 4 combinations (2 sizes x 2 flavors) = 55. Every
    # category-default size picker (Pack 6/12, Small/Large Box, Single/Pack,
    # Standard/Deluxe) is now a real, priced backend variant, not client-side-only
    # decoration.
    assert result.counts_by_entity["product_variants"]["created"] == 55
    assert result.counts_by_entity["product_prices"]["created"] == 55
    assert result.counts_by_entity["product_images"]["created"] == 29
    assert result.counts_by_entity["product_merchandising"]["created"] == 26
    # One row per (variant, axis) — 51 single-axis variants + 4 buttercream-cake
    # variants x 2 axes (size, flavor) = 51 + 8 = 59.
    assert result.counts_by_entity["product_attribute_values"]["created"] == 59
    assert "product_recommendations" not in result.counts_by_entity  # source file is empty

    assert _table_count(db_session, "catalogue_categories") == 6
    assert _table_count(db_session, "catalogue_products") == 26
    assert _table_count(db_session, "catalogue_product_variants") == 55
    assert _table_count(db_session, "catalogue_product_recommendations") == 0


def test_second_seed_is_idempotent(db_session: Session) -> None:
    service = CatalogueSeedService(db_session)

    first = service.run(dry_run=False)
    second = service.run(dry_run=False)

    assert second.status == "SUCCESS"
    assert second.created_count == 0
    assert second.updated_count == 0
    assert second.skipped_count == first.created_count
    assert _table_count(db_session, "catalogue_products") == 26


def test_seed_updates_changed_canonical_values(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = CatalogueSeedService(db_session)
    service.run(dry_run=False)

    real_data = load_catalogue_seed_data()
    modified = copy.deepcopy(real_data)
    modified.products[0]["name_en"] = "Changed Product Name For Test"
    monkeypatch.setattr(seed_service_module, "load_catalogue_seed_data", lambda: modified)

    service2 = CatalogueSeedService(db_session)
    result = service2.run(dry_run=False)

    assert result.status == "SUCCESS"
    assert result.counts_by_entity["products"]["updated"] == 1
    assert result.counts_by_entity["products"]["created"] == 0
    row = db_session.execute(
        text("SELECT name_en FROM catalogue_products WHERE external_key = :key"),
        {"key": real_data.products[0]["external_key"]},
    ).scalar_one()
    assert row == "Changed Product Name For Test"


def test_seed_preserves_null_arabic_values(db_session: Session) -> None:
    service = CatalogueSeedService(db_session)
    service.run(dry_run=False)

    name_ar_values = (
        db_session.execute(text("SELECT name_ar FROM catalogue_products")).scalars().all()
    )
    # Per current-catalogue-audit.md, all 26 products have no Arabic name yet — none of
    # them should have been fabricated.
    assert all(value is None for value in name_ar_values)


def test_seed_does_not_create_fake_inventory(db_session: Session) -> None:
    service = CatalogueSeedService(db_session)
    service.run(dry_run=False)

    assert _table_count(db_session, "catalogue_product_availability") == 0


def test_seed_stores_unresolved_tax_inclusion_as_null(db_session: Session) -> None:
    service = CatalogueSeedService(db_session)
    service.run(dry_run=False)

    non_null_count = db_session.execute(
        text("SELECT count(*) FROM catalogue_product_prices WHERE price_includes_tax IS NOT NULL")
    ).scalar_one()
    assert non_null_count == 0


def test_seed_rollback_on_invalid_reference(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    broken_data = CatalogueSeedData(
        categories=[],
        products=[
            {
                "external_key": "test.product.broken",
                "sku": "TEST-BROKEN",
                "slug": "test-broken",
                "name_en": "Broken Product",
                "category_external_key": "does.not.exist",
                "sales_price": 10,
                "currency": "SAR",
                "product_type": "simple",
            }
        ],
        merchandising=[],
        moments=[],
        recipients=[],
        recommendations=[],
        source_checksum="test-broken-checksum",
    )
    monkeypatch.setattr(seed_service_module, "load_catalogue_seed_data", lambda: broken_data)

    service = CatalogueSeedService(db_session)
    result = service.run(dry_run=False)

    assert result.status == "FAILED"
    assert result.error_summary is not None
    assert "does.not.exist" in result.error_summary
    assert _table_count(db_session, "catalogue_products") == 0


def test_seed_run_history_recorded(db_session: Session) -> None:
    service = CatalogueSeedService(db_session)

    dry_run_result = service.run(dry_run=True)
    apply_result = service.run(dry_run=False)

    rows = db_session.execute(
        text("SELECT status, id FROM catalogue_seed_runs ORDER BY started_at")
    ).all()
    assert [r.status for r in rows] == ["DRY_RUN", "SUCCESS"]
    assert {r.id for r in rows} == {dry_run_result.seed_run_id, apply_result.seed_run_id}
