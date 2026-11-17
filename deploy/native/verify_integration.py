#!/usr/bin/env python3
"""End-to-end proof of the Odoo integration against the running native stack.

Real API calls, the real Celery worker, a real Odoo. It stops and restarts only the stack's
own Odoo process. Run through `native_stack.py verify`, which supplies the worker's
environment. Every run uses fresh orders, so it can be repeated on the same stack.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import httpx
from app.integrations.odoo.order_push import LiveOdooOrderPusher, OdooOrderLine
from app.workers.celery_app import celery_app
from sqlalchemy import create_engine, text

REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / ".local-integration" / "verify-results.json"
API = "http://127.0.0.1:18020"
DEMO_API = "http://127.0.0.1:18021"
ODOO_URL = os.environ["ODOO_BASE_URL"] + "/jsonrpc"
DB, LOGIN, PASSWORD = (
    os.environ[k] for k in ("ODOO_DATABASE", "ODOO_USERNAME", "ODOO_PASSWORD")
)
PUSH_TASK = "app.workers.tasks.order_sync.push_paid_orders_to_odoo"
SYNC_TASK = "app.workers.tasks.catalogue_sync.sync_catalogue_from_odoo"
EXPECTED_TEMPLATES = 26
EXPECTED_VARIANTS = 55

engine = create_engine(os.environ["DATABASE_URL"])
http = httpx.Client(timeout=30)
results: list[dict[str, Any]] = []
evidence: dict[str, Any] = {}


def check(name: str, ok: bool, detail: object = "") -> None:
    results.append({"name": name, "ok": bool(ok), "detail": str(detail)})
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}", flush=True)


def rpc(service: str, method: str, args: list[Any]) -> dict[str, Any]:
    body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "call",
        "params": {"service": service, "method": method, "args": args},
    }
    return httpx.post(ODOO_URL, json=body, timeout=30).json()


UID = rpc("common", "authenticate", [DB, LOGIN, PASSWORD, {}])["result"]


def odoo_raw(model: str, method: str, args: list[Any], **kwargs: Any) -> dict[str, Any]:
    return rpc("object", "execute_kw", [DB, UID, PASSWORD, model, method, args, kwargs])


def odoo(model: str, method: str, args: list[Any], **kwargs: Any) -> Any:
    response = odoo_raw(model, method, args, **kwargs)
    if "error" in response:
        raise RuntimeError(response["error"]["data"]["message"])
    return response["result"]


def so_count_for(key: str) -> int:
    return odoo("sale.order", "search_count", [[["tb_order_key", "=", key]]])


def stack(*args: str) -> None:
    script = str(Path(__file__).with_name("native_stack.py"))
    subprocess.run([sys.executable, script, *args], check=True)


def sql(statement: str, **params: Any) -> list[Any]:
    with engine.begin() as connection:
        result = connection.execute(text(statement), params)
        return list(result.mappings()) if result.returns_rows else []


def poll(ready: Callable[[], Any], *, timeout: float = 120, nudge: bool = True) -> Any:
    """Waits for ready() to be truthy, nudging the worker the way Beat would, only sooner."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = ready()
        if value:
            return value
        if nudge:
            celery_app.send_task(PUSH_TASK)
        time.sleep(3)
    return ready()


def order_state(order_id: str) -> dict[str, Any]:
    return sql(
        "select o.order_number, o.is_demo, o.odoo_sync_status, o.odoo_sale_order_id, "
        "e.status as event_status, e.attempts, e.last_error, e.next_attempt_at "
        "from orders o join order_outbox_events e on e.order_id = o.id "
        "where o.id = :id and e.event_type = 'order.paid'",
        id=order_id,
    )[0]


def pick_product() -> tuple[str, int]:
    products = http.get(
        f"{API}/api/v1/catalogue/products", params={"page_size": 100}
    ).json()
    items = products.get("items") or products.get("data") or products
    item = next(p for p in items if float(p.get("price") or 0) >= 30)
    return item["slug"], 1


def create_order(base: str = API) -> dict[str, Any]:
    slug, quantity = pick_product()
    payload = {
        "items": [{"product_slug": slug, "quantity": quantity}],
        "promo_code": None,
        "customer": {
            "name": "Native Verify",
            "email": "verify@example.test",
            "phone": f"+9665{uuid.uuid4().int % 100000000:08d}",
        },
        "delivery": {
            "is_gift": False,
            "recipient_name": "Native Verify",
            "recipient_phone": "+966500000000",
            "area": "Al Olaya",
            "address": "1 Verification Street",
            "delivery_date": "Tomorrow",
            "delivery_time": "10:00am - 12:00pm",
        },
    }
    response = http.post(f"{base}/api/v1/orders", json=payload)
    response.raise_for_status()
    return response.json()


def pay(order: dict[str, Any], base: str = API) -> httpx.Response:
    return http.post(
        f"{base}/api/v1/orders/{order['id']}/pay",
        json={"method_label": "Native verify"},
    )


def place_order(base: str = API) -> dict[str, Any]:
    order = create_order(base)
    pay(order, base).raise_for_status()
    return order


def verify_catalogue() -> None:
    # Goods only: the website_sale module brings its own delivery service product.
    goods = [["type", "=", "consu"]]
    templates = odoo("product.template", "search_count", [goods])
    variants = odoo("product.product", "search_read", [goods], fields=["default_code"])
    codes = [v["default_code"] for v in variants if v["default_code"]]
    check("Odoo has 26 product templates", templates == EXPECTED_TEMPLATES, templates)
    check(
        "Odoo has 55 product variants",
        len(variants) == EXPECTED_VARIANTS,
        len(variants),
    )
    check(
        "every Odoo variant has a distinct SKU",
        len(set(codes)) == EXPECTED_VARIANTS,
        len(codes),
    )

    row = sql(
        "select (select count(*) from catalogue_products) p, (select count(*) from catalogue_product_variants) v, "
        "(select count(*) from catalogue_product_variants where odoo_product_variant_id is not null) m"
    )[0]
    check("PostgreSQL has 26 products", row["p"] == EXPECTED_TEMPLATES, row["p"])
    check("PostgreSQL has 55 variants", row["v"] == EXPECTED_VARIANTS, row["v"])
    check(
        "every PostgreSQL variant maps to Odoo", row["m"] == EXPECTED_VARIANTS, row["m"]
    )

    before = sql("select count(*) c from odoo_catalogue_sync_runs")[0]["c"]
    celery_app.send_task(SYNC_TASK)

    def finished() -> Any:
        rows = sql(
            "select status, started_at from odoo_catalogue_sync_runs "
            "where status <> 'RUNNING' order by started_at desc limit 1"
        )
        count = sql("select count(*) c from odoo_catalogue_sync_runs")[0]["c"]
        return rows[0] if count > before and rows else None

    run = poll(finished, timeout=240, nudge=False)
    check(
        "worker catalogue sync finished",
        bool(run),
        run["status"] if run else "timed out",
    )
    if run:
        check(
            "catalogue sync succeeded",
            "FAIL" not in run["status"].upper(),
            run["status"],
        )
    after = sql("select count(*) c from catalogue_product_variants")[0]["c"]
    check("catalogue sync left 55 variants", after == EXPECTED_VARIANTS, after)


def verify_order() -> dict[str, Any]:
    order = place_order()
    state = poll(
        lambda: (s := order_state(order["id"]))["odoo_sync_status"] == "synced" and s
    )
    check("worker pushed a paid order", bool(state), order_state(order["id"]))
    so = odoo(
        "sale.order",
        "read",
        [[state["odoo_sale_order_id"]]],
        fields=[
            "name",
            "state",
            "client_order_ref",
            "tb_order_key",
            "amount_total",
            "order_line",
        ],
    )[0]
    evidence["sale_order"] = so
    check("sale order is confirmed in Odoo", so["state"] == "sale", so["name"])
    check(
        "key matches the order",
        so["tb_order_key"] == order["order_number"],
        so["tb_order_key"],
    )
    check("sale order has lines", len(so["order_line"]) >= 1, so["order_line"])
    return order


def verify_duplicates(order: dict[str, Any]) -> None:
    number, first = (
        order["order_number"],
        order_state(order["id"])["odoo_sale_order_id"],
    )
    sql(
        "update order_outbox_events set status='pending', next_attempt_at=null, "
        "processed_at=null where order_id=:id and event_type='order.paid'",
        id=order["id"],
    )
    done = poll(lambda: order_state(order["id"])["event_status"] == "completed")
    state = order_state(order["id"])
    check("re-delivered event completes", done, state["event_status"])
    check(
        "re-delivery reuses the same sale order",
        state["odoo_sale_order_id"] == first,
        first,
    )
    check(
        "re-delivery created no duplicate",
        so_count_for(number) == 1,
        so_count_for(number),
    )

    variant = odoo("product.product", "search_read", [[]], fields=["id"], limit=1)[0][
        "id"
    ]
    partner = odoo("res.partner", "create", [{"name": "Race Partner"}])
    race_key = f"RACE-{uuid.uuid4().hex[:10]}"
    values = {
        "partner_id": partner,
        "tb_order_key": race_key,
        "order_line": [(0, 0, {"product_id": variant, "product_uom_qty": 1})],
    }
    with ThreadPoolExecutor(8) as pool:
        raced = list(
            pool.map(lambda _: odoo_raw("sale.order", "create", [values]), range(8))
        )
    won = [r for r in raced if "result" in r]
    check(
        "8 raw concurrent creates: exactly one commits",
        len(won) == 1,
        f"won={len(won)}",
    )
    check(
        "raw race left one sale order",
        so_count_for(race_key) == 1,
        so_count_for(race_key),
    )

    push_key = f"PUSH-{uuid.uuid4().hex[:10]}"

    def push(_: int) -> Any:
        return LiveOdooOrderPusher().push_order(
            order_number=push_key,
            total_amount=50.0,
            tax_amount=6.52,
            discount_amount=0.0,
            delivery_fee_amount=0.0,
            promo_code=None,
            currency="SAR",
            customer_name="Race Partner",
            customer_phone="+966511111111",
            lines=[OdooOrderLine("n/a", "Race", 1, 50.0, odoo_variant_id=variant)],
        )

    with ThreadPoolExecutor(6) as pool:
        pushes = list(pool.map(push, range(6)))
    ids = {p.odoo_sale_order_id for p in pushes if p.success}
    check("6 concurrent pushes agree on one order", len(ids) == 1, ids)
    # A loser can also lose the race to confirm. It reports failure and the outbox retries.
    losers = [p.raw.get("error") for p in pushes if not p.success]
    retried = push(0)
    check("a retry after the race succeeds", retried.success, f"losers={losers}")
    state_after = odoo("sale.order", "search_read", [[["tb_order_key", "=", push_key]]], fields=["state"])
    check("the raced order ends confirmed", state_after[0]["state"] == "sale", state_after)
    check(
        "concurrent pushes left one order",
        so_count_for(push_key) == 1,
        so_count_for(push_key),
    )

    copied = odoo("sale.order", "copy", [[first]])
    copied = copied[0] if isinstance(copied, list) else copied
    key = odoo("sale.order", "read", [[copied]], fields=["tb_order_key"])[0][
        "tb_order_key"
    ]
    check("duplicating in Odoo doesn't copy the key", key is False, key)
    changed = odoo_raw("sale.order", "write", [[first], {"tb_order_key": "CHANGED"}])
    check("the key cannot be changed", "error" in changed)


def verify_least_privilege() -> None:
    admin = odoo("res.users", "has_group", [[UID], "base.group_system"])
    check("order sync user is not an administrator", admin is False, admin)
    for model, values in (
        ("product.template", {"name": "denied"}),
        (
            "ir.model.data",
            {"name": "x", "module": "terrific_bites", "model": "res.partner"},
        ),
    ):
        response = odoo_raw(model, "create", [values])
        name = response.get("error", {}).get("data", {}).get("name", "allowed")
        check(f"order sync user cannot create {model}", "AccessError" in name, name)


def verify_downtime() -> None:
    stack("stop", "odoo")
    try:
        started = time.monotonic()
        catalogue = http.get(
            f"{API}/api/v1/catalogue/products", params={"page_size": 1}
        )
        order = place_order()
        elapsed = time.monotonic() - started
        check(
            "API serves and takes orders with Odoo down",
            catalogue.status_code == 200,
            elapsed,
        )
        failed = poll(
            lambda: (s := order_state(order["id"]))["attempts"] >= 1 and s, timeout=60
        )
        check("failed push is recorded", bool(failed), failed and failed["last_error"])
        check(
            "status shows failed with a retry scheduled",
            bool(failed)
            and failed["odoo_sync_status"] == "failed"
            and failed["event_status"] == "failed"
            and failed["next_attempt_at"] is not None,
            failed and failed["odoo_sync_status"],
        )
    finally:
        stack("start", "odoo")
    state = poll(
        lambda: (s := order_state(order["id"]))["odoo_sync_status"] == "synced" and s
    )
    check("order syncs after Odoo returns", bool(state), order_state(order["id"]))
    number = order["order_number"]
    check(
        "recovery created exactly one order",
        so_count_for(number) == 1,
        so_count_for(number),
    )
    evidence["downtime_recovery"] = {
        "order": number,
        "attempts": order_state(order["id"])["attempts"],
    }


def admin_client() -> httpx.Client:
    client = httpx.Client(base_url=API, timeout=30)
    response = client.post(
        "/api/v1/admin/auth/login",
        json={
            "email": os.environ["NATIVE_ADMIN_EMAIL"],
            "password": os.environ["NATIVE_ADMIN_PASSWORD"],
        },
    )
    response.raise_for_status()
    client.headers["X-CSRF-Token"] = client.cookies["admin_csrf"]
    return client


def verify_retries_and_dead_letter() -> None:
    order = create_order()
    original = sql(
        "select sku, product_variant_id from order_items where order_id=:id",
        id=order["id"],
    )[0]
    sql(
        "update order_items set sku='TB-MISSING', product_variant_id=null where order_id=:id",
        id=order["id"],
    )
    pay(order).raise_for_status()
    maximum = int(os.environ["ORDER_SYNC_MAX_ATTEMPTS"])
    dead = poll(
        lambda: (s := order_state(order["id"]))["event_status"] == "dead_letter" and s,
        timeout=180,
    )
    state = order_state(order["id"])
    check(
        "unsyncable order retries then dead-letters", bool(dead), state["event_status"]
    )
    check("attempts reached the limit", state["attempts"] == maximum, state["attempts"])
    check(
        "dead-lettered order shows failed",
        state["odoo_sync_status"] == "failed",
        state["odoo_sync_status"],
    )
    check("no sale order for the failed push", so_count_for(order["order_number"]) == 0)

    sql(
        "update order_items set sku=:sku, product_variant_id=:v where order_id=:id",
        sku=original["sku"],
        v=original["product_variant_id"],
        id=order["id"],
    )
    response = admin_client().post(
        f"/api/v1/admin/orders/{order['id']}/retry-odoo-sync"
    )
    check("operator retry accepted", response.status_code == 200, response.status_code)
    synced = poll(lambda: order_state(order["id"])["odoo_sync_status"] == "synced")
    check(
        "operator retry syncs the order",
        bool(synced),
        order_state(order["id"])["event_status"],
    )
    check("retry created one order", so_count_for(order["order_number"]) == 1)


def verify_demo_isolation() -> None:
    stack("app", "--stage", "demo", "--only", "api-demo")
    try:
        before = odoo("sale.order", "search_count", [[]])
        order = place_order(DEMO_API)
        check(
            "demo order is labelled",
            order["order_number"].startswith("DEMO-"),
            order["order_number"],
        )
        state = poll(
            lambda: (s := order_state(order["id"]))["event_status"] == "completed" and s
        )
        check(
            "the live worker marks it simulated",
            bool(state) and state["odoo_sync_status"] == "simulated",
            state,
        )
        check(
            "demo order flagged in PostgreSQL", bool(state) and state["is_demo"] is True
        )
        check(
            "demo order has no Odoo id",
            bool(state) and state["odoo_sale_order_id"] is None,
        )
        after = odoo("sale.order", "search_count", [[]])
        check("demo order reached no Odoo", after == before, f"{before} -> {after}")
        key = order["order_number"]
        check("nothing in Odoo carries the demo key", so_count_for(key) == 0, key)
    finally:
        stack("stop", "api-demo")


def main() -> int:
    for section in (
        verify_catalogue,
        verify_least_privilege,
        verify_order,
    ):
        result = section()
    verify_duplicates(result)
    for section in (
        verify_retries_and_dead_letter,
        verify_downtime,
        verify_demo_isolation,
    ):
        section()
    failed = [r for r in results if not r["ok"]]
    print(f"\nSUMMARY {len(results) - len(failed)}/{len(results)} passed")
    print(json.dumps(evidence, indent=1, default=str))
    RESULTS.write_text(
        json.dumps({"results": results, "evidence": evidence}, indent=1, default=str)
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
