"""End-to-end lifecycle tests that chain multiple layers in one test, the way the
individual suites (test_catalogue_seed_service.py, test_odoo_import_service.py,
test_orders_api.py, test_odoo_sync_service.py, test_admin_products_api.py,
test_admin_orders_api.py) each only cover in isolation:

1. Product: canonical catalogue -> CatalogueSeedService -> PostgreSQL -> visible via
   both the Storefront catalogue API and the Admin Portal products API -> Odoo import
   (OdooCatalogueImportService against a FakeTransport, never a real Odoo instance)
   links the Postgres row to an Odoo id -> Admin Portal reflects the synced state.
2. Order: Storefront checkout (POST /orders) -> PostgreSQL order + outbox event in one
   transaction -> pay -> Celery's push_paid_orders_to_odoo runs synchronously (eager
   mode, see conftest.py) -> Admin Portal and the Storefront tracking endpoint both
   reflect the resulting Odoo sync state -> a failed push is retryable from the Admin
   Portal.

Two important, deliberate facts about *this* codebase that these tests document
rather than hide:

- Product identity/SKU/pricing is not created through the Admin Portal UI at all
  (CLAUDE.md rule 3) — "adding a product" here means adding it to the canonical
  data/catalogue/*.json files and re-running the seed + Odoo import, which is what
  test_new_product_seed_reflects_in_postgres_and_both_portals below actually does
  (with a synthetic one-product catalogue instead of touching the committed JSON).
- Odoo order-sync is currently a deliberate stub (StubOdooOrderPusher docstring:
  "Real write support doesn't exist yet") — every "sync with Odoo" assertion below
  is therefore about the PostgreSQL-side contract (odoo_sync_status, outbox event
  status/attempts, sale_order_id) that a real pusher will have to satisfy, not proof
  that a real Odoo instance received the order. See test_odoo_integration.py for the
  smaller, explicitly-marked suite that would run against a real Odoo sandbox.
"""

from __future__ import annotations

from collections.abc import Generator
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.integrations.odoo.client import OdooClient
from app.integrations.odoo.order_push import OdooPushResult
from app.main import app
from app.models.catalogue.category import CatalogueCategory
from app.models.catalogue.product import CatalogueProduct
from app.models.orders.order import Order
from app.services.catalogue import odoo_import_service as odoo_import_service_module
from app.services.catalogue import seed_service as seed_service_module
from app.services.catalogue.odoo_import_service import OdooCatalogueImportService
from app.services.catalogue.seed_data_loader import CatalogueSeedData
from app.services.catalogue.seed_service import CatalogueSeedService
from app.services.checkout import odoo_sync_service as odoo_sync_service_module
from app.services.checkout.odoo_sync_service import OdooOrderSyncService
from tests.integration.admin_factories import login_as, make_admin_user
from tests.unit.odoo.conftest import FakeTransport, make_config


@pytest.fixture
def api_client(db_session: Session) -> Generator[TestClient, None, None]:
    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app, raise_server_exceptions=False)
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------------
# Shared fixtures: a synthetic one-category/one-product canonical catalogue, and a
# FakeTransport pre-loaded to CREATE that same product in Odoo. Kept deliberately
# tiny (vs. the real ~26-product catalogue test_odoo_import_service.py exercises)
# so this file stays about the cross-layer wiring, not about re-proving the seed/
# import services' own field-mapping logic — that's already covered elsewhere.
# ---------------------------------------------------------------------------------


def _one_product_seed_data(*, suffix: str) -> CatalogueSeedData:
    category_key = f"e2e.category.{suffix}"
    product_key = f"e2e.product.{suffix}"
    return CatalogueSeedData(
        categories=[
            {
                "external_key": category_key,
                "code": f"E2E{suffix.upper()}",
                "slug": f"e2e-category-{suffix}",
                "name_en": "E2E Test Category",
                "active": True,
                "display_order": 0,
            }
        ],
        products=[
            {
                "external_key": product_key,
                "sku": f"E2E-{suffix.upper()}",
                "slug": f"e2e-product-{suffix}",
                "name_en": "E2E Test Cake",
                "category_external_key": category_key,
                "sales_price": 42.0,
                "currency": "SAR",
                "active": True,
                "sellable": True,
                "product_type": "simple",
            }
        ],
        merchandising=[
            {
                "product_external_key": product_key,
                "storefront_visible": True,
                "featured": True,
            }
        ],
        moments=[],
        recipients=[],
        recommendations=[],
        source_checksum=f"sha256:test-{suffix}",
    )


def _seed_one_product(
    db_session: Session, monkeypatch: pytest.MonkeyPatch, *, suffix: str
) -> tuple[CatalogueCategory, CatalogueProduct]:
    monkeypatch.setattr(
        seed_service_module,
        "load_catalogue_seed_data",
        lambda: _one_product_seed_data(suffix=suffix),
    )
    result = CatalogueSeedService(db_session).run(dry_run=False)
    assert result.status == "SUCCESS", result.error_summary

    category = (
        db_session.query(CatalogueCategory).filter_by(external_key=f"e2e.category.{suffix}").one()
    )
    product = (
        db_session.query(CatalogueProduct).filter_by(external_key=f"e2e.product.{suffix}").one()
    )
    return category, product


def _fake_odoo_client_for_create(
    monkeypatch: pytest.MonkeyPatch, *, category_odoo_id: int, product_odoo_id: int
) -> FakeTransport:
    """Wires _connect() to an authenticated OdooClient over a FakeTransport that
    reports nothing pre-existing, then queues CREATE responses for exactly the one
    category + one product this file's synthetic catalogue plans — mirrors
    test_odoo_import_service.py's _fake_connected_client, scaled to one product.
    """
    config = make_config()
    transport = FakeTransport()
    transport.queue(("common", "version"), {"server_version": "19.0-test"})
    transport.queue(("common", "authenticate"), 7)
    transport.queue(
        ("execute_kw", "res.company", "search_read"),
        [{"id": 1, "name": "My Company", "currency_id": [151, "SAR"]}],
    )
    transport.queue(("execute_kw", "ir.model.data", "search_read"), [])
    transport.queue(("execute_kw", "product.category", "search_read"), [])
    transport.queue(("execute_kw", "product.template", "search_read"), [])
    # CREATE responses, in call order: category, its xml-id pin, product template,
    # its xml-id pin.
    transport.queue(("execute_kw", "product.category", "create"), category_odoo_id)
    transport.queue(("execute_kw", "ir.model.data", "create"), 9001)
    transport.queue(("execute_kw", "product.template", "create"), product_odoo_id)
    transport.queue(("execute_kw", "ir.model.data", "create"), 9002)

    client = OdooClient(config, transport)
    client.get_server_version()
    client.authenticate()
    monkeypatch.setattr(odoo_import_service_module, "_connect", lambda: (client, None))
    return transport


def _approve_all_blocking_decisions(monkeypatch: pytest.MonkeyPatch) -> None:
    """The real committed approval file already has every blocking decision
    (D03/D04/D08/D09/D10/D19) approved (Phase 6) — reuse it as-is rather than
    monkeypatching approvals, so this test exercises the same gate production runs
    would hit.
    """
    del monkeypatch  # kept for symmetry/readability at call sites; no patch needed


# ===================================================================================
# 1. Product lifecycle: canonical catalogue -> Postgres -> Storefront + Admin -> Odoo
# ===================================================================================


def test_new_product_seed_reflects_in_postgres_and_both_portals(
    api_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    category, product = _seed_one_product(db_session, monkeypatch, suffix="seedflow")

    # Storefront: unauthenticated, PostgreSQL-served (CLAUDE.md rule 2). Filtered by
    # this test's own category slug rather than SKU — the public search deliberately
    # doesn't expose SKU search (product_repository.py: that's admin-only).
    storefront_list = api_client.get(
        "/api/v1/catalogue/products", params={"category": category.slug}
    )
    assert storefront_list.status_code == 200
    assert storefront_list.json()["total"] == 1
    assert storefront_list.json()["items"][0]["sku"] == product.sku

    storefront_detail = api_client.get(f"/api/v1/catalogue/products/{product.slug}")
    assert storefront_detail.status_code == 200
    assert storefront_detail.json()["name_en"] == "E2E Test Cake"

    # Admin Portal: same underlying row, different (authenticated) view.
    admin = make_admin_user(db_session, role="CATALOGUE_ADMIN")
    login_as(api_client, admin)
    admin_list = api_client.get("/api/v1/admin/products", params={"search": product.sku})
    assert admin_list.status_code == 200
    assert admin_list.json()["items"][0]["sku"] == product.sku
    assert admin_list.json()["items"][0]["odoo_mapped"] is False  # not synced to Odoo yet

    admin_detail = api_client.get(f"/api/v1/admin/products/{product.id}")
    assert admin_detail.status_code == 200
    assert admin_detail.json()["odoo_product_template_id"] is None


def test_odoo_import_links_seeded_product_and_admin_reflects_sync_state(
    api_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_one_product(db_session, monkeypatch, suffix="oimport")
    monkeypatch.setattr(
        odoo_import_service_module,
        "_load_canonical_catalogue",
        lambda: (
            _one_product_seed_data(suffix="oimport").categories,
            [
                {
                    **_one_product_seed_data(suffix="oimport").products[0],
                    "primary_image": None,
                    "additional_images": [],
                }
            ],
        ),
    )
    transport = _fake_odoo_client_for_create(
        monkeypatch, category_odoo_id=5001, product_odoo_id=5002
    )

    service = OdooCatalogueImportService(db_session)
    result = service.run_apply(
        confirmed=True, allow_partial=False, initiated_by="e2e-test", correlation_id="e2e-corr-1"
    )

    assert result.run.status == "SUCCEEDED", [i.error_message for i in result.items]
    assert transport.write_call_count() == 4  # category, its xml-id, product, its xml-id

    product = db_session.query(CatalogueProduct).filter_by(external_key="e2e.product.oimport").one()
    assert product.odoo_product_template_id == 5002
    assert product.last_synced_at is not None

    admin = make_admin_user(db_session, role="CATALOGUE_ADMIN")
    login_as(api_client, admin)
    admin_detail = api_client.get(f"/api/v1/admin/products/{product.id}")
    assert admin_detail.status_code == 200
    assert admin_detail.json()["odoo_product_template_id"] == 5002
    assert admin_detail.json()["last_synced_at"] is not None


# ===================================================================================
# 2. Order lifecycle: Storefront checkout -> Postgres -> pay -> Odoo sync -> Admin
# ===================================================================================


def _checkout_payload(product_slug: str) -> dict[str, Any]:
    return {
        "items": [{"product_slug": product_slug, "quantity": 2}],
        "promo_code": None,
        "customer": {"name": "Layla A.", "phone": "+966501112222"},
        "delivery": {
            "is_gift": False,
            "recipient_name": "Layla A.",
            "recipient_phone": "+966501112222",
            "area": "Al Olaya",
            "address": "456 Test Avenue",
        },
    }


def test_storefront_order_flows_through_postgres_pay_and_odoo_sync_into_admin_and_tracking(
    api_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, product = _seed_one_product(db_session, monkeypatch, suffix="orderflow")

    # 1. Storefront places the order — server prices it from Postgres, never trusts
    # a client-submitted price (orders.py docstring).
    created = api_client.post("/api/v1/orders", json=_checkout_payload(product.slug))
    assert created.status_code == 200, created.text
    order_body = created.json()
    assert order_body["status"] == "pending_payment"
    assert order_body["subtotal_amount"] == f"{Decimal('42.00') * 2:.2f}"
    # tax_amount is informational/tax-inclusive here, not additive — pricing_service.py
    # computes total as net (subtotal - discount) + delivery_fee.
    assert Decimal(order_body["total_amount"]) == (
        Decimal(order_body["subtotal_amount"])
        - Decimal(order_body["discount_amount"])
        + Decimal(order_body["delivery_fee_amount"])
    )

    db_order = db_session.get(Order, order_body["id"])
    assert db_order is not None
    assert len(db_order.items) == 1
    assert len(db_order.outbox_events) == 1
    assert db_order.outbox_events[0].event_type == "order.created"

    # 2. Pay — flips status to "paid". The endpoint also fires push_paid_orders_to_
    # odoo.delay(), but (as test_odoo_sync_service.py's own tests do) that task runs
    # against a brand-new session_scope() session, a different DB connection than
    # db_session's savepoint-transaction, so its effects aren't visible to this test
    # via that path — run OdooOrderSyncService against db_session directly, exactly
    # what the eager task would have done had it shared this connection.
    paid = api_client.post(f"/api/v1/orders/{order_body['id']}/pay", json={"method_label": "Cash"})
    assert paid.status_code == 200, paid.text
    assert paid.json()["status"] == "paid"
    assert paid.json()["payment_method"] == "Cash"

    sync_summary = OdooOrderSyncService(db_session).sync_paid_orders()
    assert sync_summary.succeeded == 1

    db_session.refresh(db_order)
    assert db_order.odoo_sync_status == "synced"
    assert db_order.odoo_last_synced_at is not None
    paid_event = next(e for e in db_order.outbox_events if e.event_type == "order.paid")
    assert paid_event.status == "completed"

    # 3. Admin Portal sees the same order, including its Odoo sync state.
    admin = make_admin_user(db_session, role="OPERATIONS_ADMIN")
    login_as(api_client, admin)
    admin_detail = api_client.get(f"/api/v1/admin/orders/{order_body['id']}")
    assert admin_detail.status_code == 200
    body = admin_detail.json()
    assert body["status"] == "paid"
    assert body["odoo"]["sync_status"] == "synced"
    assert body["payments"][0]["status"] == "succeeded"

    # 4. The Storefront's own customer-facing tracking view reflects the same state
    # (no admin auth — resolved by tracking_token, per orders.py).
    tracking = api_client.get(f"/api/v1/orders/by-tracking-token/{order_body['tracking_token']}")
    assert tracking.status_code == 200
    assert tracking.json()["status"] == "paid"
    assert tracking.json()["id"] == order_body["id"]


def test_failed_odoo_push_is_visible_to_admin_and_a_retry_recovers_it(
    api_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, product = _seed_one_product(db_session, monkeypatch, suffix="retryflow")

    class _FailsOnceThenSucceeds:
        name = "stub"
        calls = 0

        def push_order(self, **kwargs: object) -> OdooPushResult:
            type(self).calls += 1
            if type(self).calls == 1:
                return OdooPushResult(success=False, odoo_sale_order_id=None, raw={})
            return OdooPushResult(
                success=True, odoo_sale_order_id=777, raw={"provider": "stub-retry-test"}
            )

    monkeypatch.setattr(
        odoo_sync_service_module,
        "get_odoo_order_pusher",
        lambda settings: _FailsOnceThenSucceeds(),
    )

    created = api_client.post("/api/v1/orders", json=_checkout_payload(product.slug)).json()
    paid = api_client.post(
        f"/api/v1/orders/{created['id']}/pay", json={"method_label": "Cash"}
    ).json()
    assert paid["status"] == "paid"

    # First sync attempt fails (the pusher's call #1) — run it directly against
    # db_session; see the comment in the previous test for why the pay endpoint's own
    # .delay() dispatch isn't observable here.
    first_summary = OdooOrderSyncService(db_session).sync_paid_orders()
    assert first_summary.failed == 1

    db_order = db_session.get(Order, created["id"])
    assert db_order is not None
    db_session.refresh(db_order)
    assert db_order.odoo_sync_status == "failed"

    # Admin sees the failure...
    admin = make_admin_user(db_session, role="OPERATIONS_ADMIN")
    csrf = login_as(api_client, admin)
    admin_detail = api_client.get(f"/api/v1/admin/orders/{created['id']}")
    assert admin_detail.json()["odoo"]["sync_status"] == "failed"

    # ...and retries it — the endpoint flips the failed outbox event back to
    # "pending" and commits that (session.commit() runs inside the request, on this
    # same db_session, per the api_client fixture's get_db override) so a follow-up
    # sync pass against db_session picks it up, mirroring what Celery Beat's next
    # periodic poll would do in production.
    retry = api_client.post(
        f"/api/v1/admin/orders/{created['id']}/retry-odoo-sync",
        headers={"X-CSRF-Token": csrf},
    )
    assert retry.status_code == 200, retry.text
    assert retry.json()["queued"] is True

    second_summary = OdooOrderSyncService(db_session).sync_paid_orders()
    assert second_summary.succeeded == 1

    db_session.refresh(db_order)
    assert db_order.odoo_sync_status == "synced"
    assert db_order.odoo_sale_order_id == 777

    admin_detail_after = api_client.get(f"/api/v1/admin/orders/{created['id']}")
    assert admin_detail_after.json()["odoo"]["sync_status"] == "synced"


def test_sync_paid_orders_is_idempotent_on_a_re_run(
    api_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CLAUDE.md rule 7: sync must be idempotent/retryable. A second sync pass over
    an already-synced order must not re-push it or change its sale_order_id."""
    _, product = _seed_one_product(db_session, monkeypatch, suffix="idemflow")

    created = api_client.post("/api/v1/orders", json=_checkout_payload(product.slug)).json()
    api_client.post(f"/api/v1/orders/{created['id']}/pay", json={"method_label": "Cash"})

    first_pass = OdooOrderSyncService(db_session).sync_paid_orders()
    assert first_pass.succeeded == 1

    db_order = db_session.get(Order, created["id"])
    assert db_order is not None
    db_session.refresh(db_order)
    first_synced_at = db_order.odoo_last_synced_at
    assert db_order.odoo_sync_status == "synced"

    # A second, independent sync pass (e.g. Beat's periodic poll running again)
    # should find nothing pending — the order is already "synced", not "pending".
    summary = OdooOrderSyncService(db_session).sync_paid_orders()
    assert summary.processed == 0

    db_session.refresh(db_order)
    assert db_order.odoo_last_synced_at == first_synced_at
