from __future__ import annotations

from app.integrations.odoo.client import OdooClient
from app.integrations.odoo.config import OdooConfig
from app.integrations.odoo.discovery.capabilities import (
    FIELD_CHECKS,
    REQUIRED_MODELS,
    CheckStatus,
    run_environment_verification,
)
from app.integrations.odoo.exceptions import OdooConnectionError, OdooRemoteError
from tests.unit.odoo.conftest import FakeTransport

PRODUCT_TEMPLATE_FIELDS = {
    "image_1920": {"string": "Image", "type": "binary", "required": False, "readonly": False},
    "barcode": {"string": "Barcode", "type": "char", "required": False, "readonly": False},
    "description_sale": {
        "string": "Sales Description",
        "type": "text",
        "required": False,
        "readonly": False,
    },
    "default_code": {
        "string": "Internal Reference",
        "type": "char",
        "required": False,
        "readonly": False,
    },
    "sale_ok": {"string": "Can be Sold", "type": "boolean", "required": False, "readonly": False},
    "active": {"string": "Active", "type": "boolean", "required": False, "readonly": False},
    "type": {
        "string": "Product Type",
        "type": "selection",
        "required": True,
        "readonly": False,
        "selection": [["consu", "Goods"], ["service", "Service"]],
    },
    "attribute_line_ids": {
        "string": "Attributes",
        "type": "one2many",
        "required": False,
        "readonly": False,
    },
}
PRODUCT_PRODUCT_FIELDS = {
    "default_code": {
        "string": "Internal Reference",
        "type": "char",
        "required": False,
        "readonly": False,
    },
}
PRODUCT_ATTRIBUTE_FIELDS = {
    "create_variant": {
        "string": "Variants Creation Mode",
        "type": "selection",
        "required": False,
        "readonly": False,
        "selection": [["always", "Instantly"], ["dynamic", "Dynamically"], ["no_variant", "Never"]],
    },
}
PRODUCT_TEMPLATE_ATTRIBUTE_VALUE_FIELDS = {
    "price_extra": {
        "string": "Extra Price",
        "type": "float",
        "required": False,
        "readonly": False,
    },
}


def test_reachability_failure_blocks_immediately(
    config: OdooConfig, transport: FakeTransport
) -> None:
    transport.queue(("common", "version"), OdooConnectionError("refused"))
    client = OdooClient(config, transport)

    report = run_environment_verification(config, client)

    assert report.overall_status == "BLOCKED"
    ids = {c.check_id for c in report.checks}
    assert ids == {"server_reachable", "server_version"}
    assert all(c.status == CheckStatus.BLOCKED for c in report.checks)


def test_authentication_failure_marks_remaining_checks_unverified(
    config: OdooConfig, transport: FakeTransport
) -> None:
    transport.queue(
        ("common", "version"),
        {
            "server_version": "19.0",
            "server_version_info": [],
            "server_serie": "19.0",
            "protocol_version": 1,
        },
    )
    transport.queue(("common", "authenticate"), OdooRemoteError("bad credentials"))
    client = OdooClient(config, transport)

    report = run_environment_verification(config, client)

    assert report.overall_status == "BLOCKED"
    auth_check = next(c for c in report.checks if c.check_id == "authentication")
    assert auth_check.status == CheckStatus.BLOCKED
    unverified = [c for c in report.checks if c.status == CheckStatus.UNVERIFIED]
    assert len(unverified) > 0
    assert all(c.detail == "Skipped: authentication did not succeed" for c in unverified)


def test_full_success_path_yields_verified_overall_status(
    config: OdooConfig, transport: FakeTransport
) -> None:
    transport.queue(
        ("common", "version"),
        {
            "server_version": "19.0",
            "server_version_info": [19, 0],
            "server_serie": "19.0",
            "protocol_version": 1,
        },
    )
    transport.queue(("common", "authenticate"), 2)
    transport.queue(
        ("execute_kw", "res.company", "search_read"),
        [{"id": 1, "name": "Terrific Bites LLC", "currency_id": [12, "SAR"]}],
    )
    # One repeatable response covers every model-existence check.
    transport.queue(("execute_kw", "ir.model", "search_count"), 1)
    for model_name, _, _ in REQUIRED_MODELS:
        transport.queue(("execute_kw", model_name, "check_access_rights"), True)
    transport.queue(("execute_kw", "product.template", "fields_get"), PRODUCT_TEMPLATE_FIELDS)
    transport.queue(("execute_kw", "product.product", "fields_get"), PRODUCT_PRODUCT_FIELDS)
    transport.queue(("execute_kw", "product.attribute", "fields_get"), PRODUCT_ATTRIBUTE_FIELDS)
    transport.queue(
        ("execute_kw", "product.template.attribute.value", "fields_get"),
        PRODUCT_TEMPLATE_ATTRIBUTE_VALUE_FIELDS,
    )
    transport.queue(("execute_kw", "product.category", "search_read"), [])

    client = OdooClient(config, transport)
    report = run_environment_verification(config, client)

    blockers = report.blockers
    assert blockers == [], f"unexpected blockers: {[b.to_dict() for b in blockers]}"
    assert report.overall_status == "VERIFIED"
    # reachability(2) + authentication(1) + company/multi_company(2) + one check per
    # REQUIRED_MODELS + one check per FIELD_CHECKS + product_type_values(1) +
    # existing_terrific_bites_category(1)
    assert len(report.checks) == 2 + 1 + 2 + len(REQUIRED_MODELS) + len(FIELD_CHECKS) + 1 + 1

    company_check = next(c for c in report.checks if c.check_id == "company_currency")
    assert company_check.evidence is not None
    assert company_check.evidence["currency_name"] == "SAR"


def test_missing_required_model_is_reported_as_blocked(
    config: OdooConfig, transport: FakeTransport
) -> None:
    transport.queue(
        ("common", "version"),
        {
            "server_version": "19.0",
            "server_version_info": [],
            "server_serie": "19.0",
            "protocol_version": 1,
        },
    )
    transport.queue(("common", "authenticate"), 2)
    transport.queue(
        ("execute_kw", "res.company", "search_read"),
        [{"id": 1, "name": "TB", "currency_id": [12, "SAR"]}],
    )
    # model_exists() shares one key across every model checked (FakeTransport keys on
    # (model, method), and model_exists always queries "ir.model"/"search_count"
    # regardless of which model it's checking for). Queuing [0, 1] means the first
    # model_availability() call (REQUIRED_MODELS[0] == product.template) sees "not
    # installed"; every later one reuses the repeated "1" (installed).
    transport.queue(("execute_kw", "ir.model", "search_count"), 0)
    transport.queue(("execute_kw", "ir.model", "search_count"), 1)
    for model_name, _, _ in REQUIRED_MODELS:
        transport.queue(("execute_kw", model_name, "check_access_rights"), True)
    transport.queue(("execute_kw", "product.template", "fields_get"), PRODUCT_TEMPLATE_FIELDS)
    transport.queue(("execute_kw", "product.product", "fields_get"), PRODUCT_PRODUCT_FIELDS)
    transport.queue(("execute_kw", "product.attribute", "fields_get"), PRODUCT_ATTRIBUTE_FIELDS)
    transport.queue(
        ("execute_kw", "product.template.attribute.value", "fields_get"),
        PRODUCT_TEMPLATE_ATTRIBUTE_VALUE_FIELDS,
    )
    transport.queue(("execute_kw", "product.category", "search_read"), [])

    client = OdooClient(config, transport)
    report = run_environment_verification(config, client)

    assert report.overall_status == "PARTIAL"
    first_model_check = next(
        c for c in report.checks if c.check_id == f"model_{REQUIRED_MODELS[0][0]}"
    )
    assert first_model_check.status == CheckStatus.BLOCKED
