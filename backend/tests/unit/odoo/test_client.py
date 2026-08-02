from __future__ import annotations

import pytest

from app.integrations.odoo.client import KNOWN_WRITE_METHODS, OdooClient
from app.integrations.odoo.exceptions import (
    OdooAuthenticationError,
    OdooReadOnlyViolationError,
    OdooRemoteError,
)
from tests.unit.odoo.conftest import FakeTransport


def test_session_property_raises_before_authenticate(client: OdooClient) -> None:
    with pytest.raises(OdooAuthenticationError):
        _ = client.session


@pytest.mark.parametrize("method", sorted(KNOWN_WRITE_METHODS))
def test_execute_readonly_rejects_every_known_write_method(
    authenticated_client: OdooClient, transport: FakeTransport, method: str
) -> None:
    with pytest.raises(OdooReadOnlyViolationError):
        authenticated_client.execute_readonly("product.template", method, [1])

    assert transport.write_call_count() == 0


def test_execute_readonly_rejects_unknown_method(authenticated_client: OdooClient) -> None:
    with pytest.raises(OdooReadOnlyViolationError):
        authenticated_client.execute_readonly("product.template", "some_custom_rpc_method", [])


def test_search_passes_domain_and_pagination(
    authenticated_client: OdooClient, transport: FakeTransport
) -> None:
    transport.queue(("execute_kw", "product.template", "search"), [1, 2, 3])

    ids = authenticated_client.search(
        "product.template", [["active", "=", True]], offset=10, limit=5, order="id"
    )

    assert ids == [1, 2, 3]
    call = transport.calls[-1]
    assert call.args[3:6] == ["product.template", "search", [[["active", "=", True]]]]
    assert call.args[6] == {"offset": 10, "limit": 5, "order": "id"}


def test_read_requests_specified_fields(
    authenticated_client: OdooClient, transport: FakeTransport
) -> None:
    transport.queue(
        ("execute_kw", "product.template", "read"), [{"id": 1, "name": "Swiss Frosting"}]
    )

    records = authenticated_client.read("product.template", [1], ["name"])

    assert records == [{"id": 1, "name": "Swiss Frosting"}]
    call = transport.calls[-1]
    assert call.args[6] == {"fields": ["name"]}


def test_search_read_defaults_limit_to_read_batch_size(
    authenticated_client: OdooClient, transport: FakeTransport
) -> None:
    transport.queue(("execute_kw", "product.template", "search_read"), [{"id": 1}])

    page = authenticated_client.search_read("product.template", [])

    assert page.limit == authenticated_client.config.read_batch_size
    assert page.returned_count == 1


def test_iter_search_read_pages_through_batches_and_respects_max_records(
    authenticated_client: OdooClient, transport: FakeTransport
) -> None:
    # read_batch_size=5 (see conftest.make_config); ask for at most 7 records across
    # two pages: first page full (5, has_more True), second page partial (2, has_more False).
    transport.queue(
        ("execute_kw", "product.template", "search_read"), [{"id": i} for i in range(1, 6)]
    )
    transport.queue(
        ("execute_kw", "product.template", "search_read"), [{"id": i} for i in range(6, 8)]
    )

    records = list(authenticated_client.iter_search_read("product.template", [], max_records=7))

    assert [r["id"] for r in records] == [1, 2, 3, 4, 5, 6, 7]
    search_read_calls = [
        c
        for c in transport.calls
        if c.service == "object" and c.args[3:5] == ["product.template", "search_read"]
    ]
    assert len(search_read_calls) == 2
    assert search_read_calls[0].args[6]["offset"] == 0
    assert search_read_calls[0].args[6]["limit"] == 5
    assert search_read_calls[1].args[6]["offset"] == 5
    assert search_read_calls[1].args[6]["limit"] == 2


def test_iter_search_read_stops_when_page_returns_no_records(
    authenticated_client: OdooClient, transport: FakeTransport
) -> None:
    transport.queue(("execute_kw", "product.template", "search_read"), [])

    records = list(authenticated_client.iter_search_read("product.template", [], max_records=100))

    assert records == []


def test_fields_get_parses_descriptors(
    authenticated_client: OdooClient, transport: FakeTransport
) -> None:
    transport.queue(
        ("execute_kw", "product.template", "fields_get"),
        {
            "type": {
                "string": "Product Type",
                "type": "selection",
                "required": True,
                "readonly": False,
                "selection": [["consu", "Goods"], ["service", "Service"]],
            }
        },
    )

    fields = authenticated_client.fields_get("product.template")

    assert fields["type"].field_type == "selection"
    assert fields["type"].selection == [("consu", "Goods"), ("service", "Service")]
    assert fields["type"].required is True


def test_name_get_falls_back_to_display_name_when_unsupported(
    authenticated_client: OdooClient, transport: FakeTransport
) -> None:
    transport.queue(
        ("execute_kw", "product.template", "name_get"), OdooRemoteError("name_get is not supported")
    )
    transport.queue(
        ("execute_kw", "product.template", "read"), [{"id": 1, "display_name": "Swiss Frosting"}]
    )

    result = authenticated_client.name_get("product.template", [1])

    assert result == [(1, "Swiss Frosting")]


def test_check_access_rights_returns_denial_as_data_not_exception(
    authenticated_client: OdooClient, transport: FakeTransport
) -> None:
    transport.queue(("execute_kw", "product.template", "check_access_rights"), False)

    access = authenticated_client.check_access_rights("product.template", "write")

    assert access.allowed is False
    assert access.operation == "write"
