from __future__ import annotations

from typing import Any

from app.integrations.odoo.client import OdooClient
from app.integrations.odoo.config import OdooConfig
from app.services.catalogue.approval_gate import ApprovalDecision
from app.services.catalogue.odoo_import_planning import (
    EnvironmentSnapshot,
    plan_attributes,
    plan_categories,
    plan_products,
    plan_variants,
    unresolved_attribute_values,
)
from tests.unit.odoo.conftest import FakeTransport


def _approval(
    decision_id: str, *, status: str = "PROPOSED", approved_value: Any = None
) -> ApprovalDecision:
    return ApprovalDecision(
        decision_id=decision_id,
        title=f"Decision {decision_id}",
        status=status,
        approved_value=approved_value,
        blocks_import=True,
        approved_by=None,
        approved_at=None,
        approval_notes=None,
    )


def _category(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "external_key": "category.cupcakes",
        "code": "CUP",
        "slug": "cupcakes",
        "name_en": "Cupcakes",
        "active": True,
        "display_order": 1,
    }
    base.update(overrides)
    return base


def _product(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "external_key": "product.swiss-frosting",
        "sku": "TB-CUP-001",
        "slug": "swiss-frosting",
        "name_en": "Swiss Frosting",
        "category_external_key": "category.cupcakes",
        "sales_price": 12.5,
        "currency": "SAR",
        "product_type": "simple",
        "active": True,
        "sellable": True,
        "description_en": "A cupcake.",
    }
    base.update(overrides)
    return base


def _no_match_transport() -> FakeTransport:
    transport = FakeTransport()
    transport.queue(("common", "authenticate"), 7)
    transport.queue(("execute_kw", "ir.model.data", "search_read"), [])
    transport.queue(("execute_kw", "product.category", "search_read"), [])
    transport.queue(("execute_kw", "product.template", "search_read"), [])
    return transport


def _authenticated_client(config: OdooConfig, transport: FakeTransport) -> OdooClient:
    client = OdooClient(config, transport)
    client.authenticate()
    return client


# -- categories -----------------------------------------------------------------------


def test_plan_categories_creates_when_no_match_and_decisions_approved(config: OdooConfig) -> None:
    fake_transport = _no_match_transport()
    client = _authenticated_client(config, fake_transport)
    approvals = [_approval("D03", status="APPROVED", approved_value=["CUP"])]

    items = plan_categories([_category()], approvals, client, None, {}, "corr-1")

    assert len(items) == 1
    assert items[0].planned_action == "CREATE"
    assert items[0].xml_id_name == "category_cupcakes"
    assert items[0].proposed_values == {"name": "Cupcakes"}


def test_plan_categories_blocked_when_decision_not_approved(config: OdooConfig) -> None:
    fake_transport = _no_match_transport()
    client = _authenticated_client(config, fake_transport)
    approvals = [_approval("D03", status="PROPOSED")]

    items = plan_categories([_category()], approvals, client, None, {}, "corr-1")

    assert items[0].planned_action == "BLOCKED"
    assert any("D03" in issue for issue in items[0].blocking_issues)


def test_plan_categories_matches_by_postgres_stored_id_without_any_odoo_call(
    config: OdooConfig,
) -> None:
    transport = FakeTransport()
    transport.queue(("common", "authenticate"), 7)
    client = _authenticated_client(config, transport)

    items = plan_categories(
        [_category()], [_approval("D03")], client, None, {"category.cupcakes": 501}, "corr-1"
    )

    assert items[0].planned_action == "MATCH"
    assert items[0].match_strategy == "POSTGRES_STORED_ID"
    assert items[0].existing_odoo_id == 501
    # Only the authenticate() call happened — no search/search_read at all.
    assert len(transport.calls) == 1


def test_plan_categories_matches_by_external_xml_id(config: OdooConfig) -> None:
    transport = FakeTransport()
    transport.queue(("common", "authenticate"), 7)
    transport.queue(
        ("execute_kw", "ir.model.data", "search_read"),
        [
            {
                "id": 1,
                "res_id": 77,
                "module": "terrific_bites",
                "name": "category_cupcakes",
                "model": "product.category",
            }
        ],
    )
    client = _authenticated_client(config, transport)

    items = plan_categories([_category()], [_approval("D03")], client, None, {}, "corr-1")

    assert items[0].planned_action == "MATCH"
    assert items[0].match_strategy == "EXTERNAL_KEY"
    assert items[0].existing_odoo_id == 77


def test_plan_categories_name_match_requires_adoption_and_blocks(config: OdooConfig) -> None:
    transport = FakeTransport()
    transport.queue(("common", "authenticate"), 7)
    transport.queue(("execute_kw", "ir.model.data", "search_read"), [])
    transport.queue(
        ("execute_kw", "product.category", "search_read"),
        [{"id": 12, "name": "Cupcakes"}, {"id": 13, "name": "Cupcakes"}],
    )
    client = _authenticated_client(config, transport)

    items = plan_categories([_category()], [_approval("D03")], client, None, {}, "corr-1")

    # Multiple matches block import just as surely as a single one does — never
    # silently created, always requires human review.
    assert items[0].planned_action == "BLOCKED"
    assert "MATCH_REQUIRES_ADOPTION" in items[0].blocking_issues[0]


def test_plan_categories_blocked_when_odoo_unreachable() -> None:
    items = plan_categories(
        [_category()], [_approval("D03")], None, "connection refused", {}, "corr-1"
    )

    assert items[0].planned_action == "BLOCKED"
    assert "connection refused" in items[0].blocking_issues[0]


# -- products ---------------------------------------------------------------------------


def test_plan_products_creates_with_uom_and_type_from_approved_decisions(
    config: OdooConfig,
) -> None:
    fake_transport = _no_match_transport()
    client = _authenticated_client(config, fake_transport)
    approvals = [
        _approval("D04", status="APPROVED", approved_value="TB-<CAT>-<SEQ>"),
        _approval("D08", status="APPROVED", approved_value={"odoo_sales_tax_record": 5}),
        _approval(
            "D09", status="APPROVED", approved_value={"odoo_uom_id": 1, "odoo_uom_name": "Units"}
        ),
        _approval("D10", status="APPROVED", approved_value={"odoo_product_type": "consu"}),
        _approval("D19", status="APPROVED", approved_value={"import_stock_quantities": False}),
    ]

    items = plan_products([_product()], approvals, client, None, {}, "corr-1")

    assert items[0].planned_action == "CREATE"
    assert items[0].proposed_values["default_code"] == "TB-CUP-001"
    assert items[0].proposed_values["uom_id"] == 1
    assert items[0].proposed_values["type"] == "consu"
    assert items[0].xml_id_name == "product_swiss-frosting"
    assert items[0].category_external_key == "category.cupcakes"


def test_plan_products_blocked_when_any_required_decision_unapproved(config: OdooConfig) -> None:
    fake_transport = _no_match_transport()
    client = _authenticated_client(config, fake_transport)
    approvals = [
        _approval("D04"),
        _approval("D08"),
        _approval("D09", status="APPROVED", approved_value={}),
        _approval("D10"),
        _approval("D19"),
    ]

    items = plan_products([_product()], approvals, client, None, {}, "corr-1")

    assert items[0].planned_action == "BLOCKED"
    blocked_ids = {issue.split(" ")[0] for issue in items[0].blocking_issues}
    assert blocked_ids == {"D04", "D08", "D10", "D19"}  # D09 already approved, doesn't block


def test_plan_products_sku_match_requires_adoption_and_blocks(config: OdooConfig) -> None:
    transport = FakeTransport()
    transport.queue(("common", "authenticate"), 7)
    transport.queue(("execute_kw", "ir.model.data", "search_read"), [])
    transport.queue(
        ("execute_kw", "product.template", "search_read"),
        [{"id": 900, "default_code": "TB-CUP-001"}],
    )
    client = _authenticated_client(config, transport)

    items = plan_products([_product()], [_approval("D04")], client, None, {}, "corr-1")

    assert items[0].planned_action == "BLOCKED"
    assert items[0].match_strategy == "SKU"
    assert items[0].existing_odoo_id == 900


def test_plan_products_matches_by_postgres_stored_id(config: OdooConfig) -> None:
    transport = FakeTransport()
    transport.queue(("common", "authenticate"), 7)
    client = _authenticated_client(config, transport)

    items = plan_products(
        [_product()], [_approval("D04")], client, None, {"product.swiss-frosting": 321}, "corr-1"
    )

    assert items[0].planned_action == "MATCH"
    assert items[0].existing_odoo_id == 321
    assert len(transport.calls) == 1  # authenticate only


# -- attribute/variant planning ----------------------------------------------------------


def _buttercream(**overrides: Any) -> dict[str, Any]:
    base = _product(
        external_key="product.buttercream-cake",
        sku="TB-CAK-001",
        slug="buttercream-cake",
        name_en="Buttercream Cake",
        product_type="variant_parent",
        variants={
            "attributes": [
                {
                    "code": "size",
                    "name_en": "Size",
                    "values": [
                        {"label": "6 INCH", "sub": "3 Layers", "delta": 0},
                        {"label": "9 INCH", "sub": "3 Layers", "delta": 80},
                    ],
                },
                {
                    "code": "flavor",
                    "name_en": "Flavor",
                    "values": [
                        {"label": "Vanilla", "delta": 0},
                        {"label": "Chocolate", "delta": 0},
                    ],
                },
            ]
        },
    )
    base.update(overrides)
    return base


def test_plan_attributes_creates_attribute_and_values_when_no_match(config: OdooConfig) -> None:
    transport = FakeTransport()
    transport.queue(("common", "authenticate"), 7)
    transport.queue(("execute_kw", "product.attribute", "search_read"), [])
    transport.queue(("execute_kw", "product.attribute.value", "search_read"), [])
    client = _authenticated_client(config, transport)

    items = plan_attributes([_buttercream()], [], client, None, {}, {}, "corr-1")

    size_attr = next(i for i in items if i.entity_type == "PRODUCT_ATTRIBUTE" and i.canonical_name == "Size")
    assert size_attr.planned_action == "CREATE"
    assert size_attr.proposed_values == {"name": "Size", "create_variant": "always"}

    size_values = [
        i
        for i in items
        if i.entity_type == "PRODUCT_ATTRIBUTE_VALUE"
        and i.proposed_values.get("attribute_name_en") == "Size"
    ]
    assert {v.proposed_values["value_label_en"] for v in size_values} == {"6 INCH", "9 INCH"}
    assert all(v.planned_action == "CREATE" for v in size_values)


def test_plan_attributes_matches_existing_attribute_by_name(config: OdooConfig) -> None:
    transport = FakeTransport()
    transport.queue(("common", "authenticate"), 7)
    transport.queue(
        ("execute_kw", "product.attribute", "search_read"),
        [{"id": 5, "name": "Size", "create_variant": "always"}],
    )
    transport.queue(
        ("execute_kw", "product.attribute.value", "search_read"),
        [{"id": 50, "name": "6 INCH", "attribute_id": [5, "Size"]}],
    )
    client = _authenticated_client(config, transport)

    items = plan_attributes([_buttercream()], [], client, None, {}, {}, "corr-1")

    size_attr = next(i for i in items if i.entity_type == "PRODUCT_ATTRIBUTE" and i.canonical_name == "Size")
    assert size_attr.planned_action == "MATCH"
    assert size_attr.match_strategy == "NAME"
    assert size_attr.existing_odoo_id == 5


def test_plan_attributes_blocks_when_existing_attribute_has_wrong_create_variant_mode(
    config: OdooConfig,
) -> None:
    transport = FakeTransport()
    transport.queue(("common", "authenticate"), 7)
    transport.queue(
        ("execute_kw", "product.attribute", "search_read"),
        [{"id": 5, "name": "Size", "create_variant": "dynamic"}],
    )
    client = _authenticated_client(config, transport)

    items = plan_attributes([_buttercream()], [], client, None, {}, {}, "corr-1")

    size_attr = next(i for i in items if i.entity_type == "PRODUCT_ATTRIBUTE" and i.canonical_name == "Size")
    assert size_attr.planned_action == "BLOCKED"
    assert "EXISTING_ATTRIBUTE_WRONG_CREATE_VARIANT_MODE" in size_attr.blocking_issues

    # Every value under a BLOCKED attribute is BLOCKED too — never a dangling attribute id.
    size_values = [
        i
        for i in items
        if i.entity_type == "PRODUCT_ATTRIBUTE_VALUE"
        and i.proposed_values.get("attribute_name_en") == "Size"
    ]
    assert all(v.planned_action == "BLOCKED" for v in size_values)
    assert all("ATTRIBUTE_NOT_RESOLVED" in v.blocking_issues for v in size_values)


def test_plan_attributes_value_search_scoped_to_its_own_resolved_attribute_id(
    config: OdooConfig,
) -> None:
    """Confirms the value lookup is scoped by attribute_id, not matched by name alone —
    two different attributes are allowed to share a value's display name.
    """
    transport = FakeTransport()
    transport.queue(("common", "authenticate"), 7)
    transport.queue(
        ("execute_kw", "product.attribute", "search_read"),
        [{"id": 5, "name": "Size", "create_variant": "always"}],
    )
    transport.queue(("execute_kw", "product.attribute.value", "search_read"), [])
    client = _authenticated_client(config, transport)

    plan_attributes([_buttercream()], [], client, None, {}, {}, "corr-1")

    value_search_calls = [
        c for c in transport.calls if c.args[3] == "product.attribute.value" and c.args[4] == "search_read"
    ]
    assert value_search_calls  # at least one value lookup happened
    for call in value_search_calls:
        domain = call.args[5][0]
        assert ["attribute_id", "=", 5] in domain


def test_plan_variants_creates_full_combination_matrix_when_attributes_resolved(
    config: OdooConfig,
) -> None:
    transport = FakeTransport()
    transport.queue(("common", "authenticate"), 7)
    transport.queue(("execute_kw", "product.product", "search_read"), [])
    client = _authenticated_client(config, transport)

    items = plan_variants([_buttercream()], [], client, None, {}, set(), "corr-1")

    assert len(items) == 4  # 2 sizes x 2 flavors
    assert all(i.planned_action == "CREATE" for i in items)
    skus = {i.canonical_sku for i in items}
    assert skus == {
        "TB-CAK-001-6INCH-VANILLA",
        "TB-CAK-001-6INCH-CHOCOLATE",
        "TB-CAK-001-9INCH-VANILLA",
        "TB-CAK-001-9INCH-CHOCOLATE",
    }
    six_inch_vanilla = next(i for i in items if i.canonical_sku == "TB-CAK-001-6INCH-VANILLA")
    assert six_inch_vanilla.proposed_values["template_external_key"] == "product.buttercream-cake"
    assert six_inch_vanilla.proposed_values["attribute_lines"] == [
        {"attribute_name_en": "Size", "value_label_en": "6 INCH"},
        {"attribute_name_en": "Flavor", "value_label_en": "Vanilla"},
    ]


def test_plan_variants_matches_by_postgres_stored_id_without_any_odoo_call(
    config: OdooConfig,
) -> None:
    transport = FakeTransport()
    transport.queue(("common", "authenticate"), 7)
    transport.queue(("execute_kw", "product.product", "search_read"), [])
    client = _authenticated_client(config, transport)

    stored_ids = {"product.buttercream-cake.variant.6-inch.vanilla": 900}
    items = plan_variants([_buttercream()], [], client, None, stored_ids, set(), "corr-1")

    matched = next(i for i in items if i.canonical_external_key.endswith("6-inch.vanilla"))
    assert matched.planned_action == "MATCH"
    assert matched.match_strategy == "POSTGRES_STORED_ID"
    assert matched.existing_odoo_id == 900


def test_plan_variants_blocked_when_referenced_attribute_value_unresolved(
    config: OdooConfig,
) -> None:
    unresolved = {("Flavor", "Chocolate")}
    items = plan_variants([_buttercream()], [], None, "unreachable", {}, unresolved, "corr-1")

    chocolate_items = [i for i in items if "Chocolate" in i.canonical_name]
    vanilla_items = [i for i in items if "Vanilla" in i.canonical_name]
    assert all(i.planned_action == "BLOCKED" for i in chocolate_items)
    assert all("ATTRIBUTE_NOT_RESOLVED" in i.blocking_issues for i in chocolate_items)
    # Vanilla combinations don't reference the unresolved (Flavor, Chocolate) pair, but
    # with no client they still can't proceed past the connectivity check — both end up
    # BLOCKED here, just for a different, non-attribute reason.
    assert all(i.planned_action == "BLOCKED" for i in vanilla_items)


def test_plan_attributes_create_blocked_when_d20_not_approved(config: OdooConfig) -> None:
    transport = FakeTransport()
    transport.queue(("common", "authenticate"), 7)
    transport.queue(("execute_kw", "product.attribute", "search_read"), [])
    client = _authenticated_client(config, transport)

    items = plan_attributes(
        [_buttercream()], [_approval("D20", status="PROPOSED")], client, None, {}, {}, "corr-1"
    )

    size_attr = next(i for i in items if i.entity_type == "PRODUCT_ATTRIBUTE" and i.canonical_name == "Size")
    assert size_attr.planned_action == "BLOCKED"
    assert any("D20" in issue for issue in size_attr.blocking_issues)


def test_plan_attributes_create_allowed_when_d20_approved(config: OdooConfig) -> None:
    transport = FakeTransport()
    transport.queue(("common", "authenticate"), 7)
    transport.queue(("execute_kw", "product.attribute", "search_read"), [])
    transport.queue(("execute_kw", "product.attribute.value", "search_read"), [])
    client = _authenticated_client(config, transport)

    items = plan_attributes(
        [_buttercream()],
        [_approval("D20", status="APPROVED", approved_value=True)],
        client,
        None,
        {},
        {},
        "corr-1",
    )

    size_attr = next(i for i in items if i.entity_type == "PRODUCT_ATTRIBUTE" and i.canonical_name == "Size")
    assert size_attr.planned_action == "CREATE"


def test_unresolved_attribute_values_collects_blocked_value_pairs(config: OdooConfig) -> None:
    # A single-axis product (unlike _buttercream()'s two axes) avoids FakeTransport's
    # shared-response-per-(model,method) limitation muddying which attribute resolved.
    flavor_only = _product(
        external_key="product.single-axis",
        sku="TB-CUP-002",
        product_type="variant_parent",
        variants={
            "attributes": [
                {
                    "code": "flavor",
                    "name_en": "Flavor",
                    "values": [{"label": "Vanilla", "delta": 0}, {"label": "Chocolate", "delta": 0}],
                }
            ]
        },
    )
    transport = FakeTransport()
    transport.queue(("common", "authenticate"), 7)
    transport.queue(
        ("execute_kw", "product.attribute", "search_read"),
        [{"id": 5, "name": "Flavor", "create_variant": "dynamic"}],
    )
    client = _authenticated_client(config, transport)

    attribute_items = plan_attributes([flavor_only], [], client, None, {}, {}, "corr-1")

    unresolved = unresolved_attribute_values(attribute_items)
    assert unresolved == {("Flavor", "Vanilla"), ("Flavor", "Chocolate")}


# -- environment fingerprint --------------------------------------------------------------


def test_environment_fingerprint_deterministic_for_same_values() -> None:
    snap_a = EnvironmentSnapshot(
        odoo_version="19.0-20260720",
        company_id=1,
        company_name="My Company",
        currency="SAR",
        base_url="http://localhost:8069",
        database="terrific_dev",
        captured_at="2026-07-28T00:00:00Z",
    )
    snap_b = EnvironmentSnapshot(
        odoo_version="19.0-20260720",
        company_id=1,
        company_name="My Company",
        currency="SAR",
        base_url="http://localhost:8069",
        database="terrific_dev",
        captured_at="2026-07-29T12:00:00Z",  # captured_at deliberately differs
    )

    assert (
        snap_a.fingerprint == snap_b.fingerprint
    )  # only identity fields matter, not the timestamp


def test_environment_fingerprint_changes_when_company_changes() -> None:
    snap_a = EnvironmentSnapshot(
        odoo_version="19.0",
        company_id=1,
        company_name="My Company",
        currency="SAR",
        base_url="http://localhost:8069",
        database="terrific_dev",
        captured_at="2026-07-28T00:00:00Z",
    )
    snap_b = EnvironmentSnapshot(
        odoo_version="19.0",
        company_id=2,
        company_name="Another Company",
        currency="SAR",
        base_url="http://localhost:8069",
        database="terrific_dev",
        captured_at="2026-07-28T00:00:00Z",
    )

    assert snap_a.fingerprint != snap_b.fingerprint
