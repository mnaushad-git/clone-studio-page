"""Opt-in, real-Odoo integration tests.

Never runs as part of a normal `pytest` invocation or CI: skipped unless
RUN_ODOO_INTEGRATION_TESTS=1 is set *and* ODOO_BASE_URL/DATABASE/USERNAME are
configured (backend/.env, never committed). Run explicitly with:

    RUN_ODOO_INTEGRATION_TESTS=1 pytest -m odoo_integration

Every call here is read-only (same OdooClient read-only surface as the rest of the
suite) — these tests must never create, update, archive, or delete a real Odoo
record.
"""

from __future__ import annotations

import os
from collections.abc import Generator

import pytest

from app.core.config import get_settings
from app.integrations.odoo.client import OdooClient
from app.integrations.odoo.config import OdooConfig
from app.integrations.odoo.discovery.capabilities import run_environment_verification
from app.integrations.odoo.repositories.metadata import MetadataRepository
from app.integrations.odoo.transport import OdooTransport

_ENV_VAR = "RUN_ODOO_INTEGRATION_TESTS"


def _skip_reason() -> str | None:
    if os.environ.get(_ENV_VAR) != "1":
        return (
            f"Set {_ENV_VAR}=1 to run live Odoo integration tests "
            "(see docs/integrations/odoo-testing.md)"
        )
    if not OdooConfig.is_configured(get_settings()):
        return "ODOO_BASE_URL/ODOO_DATABASE/ODOO_USERNAME are not configured in backend/.env"
    return None


_SKIP_REASON = _skip_reason()
pytestmark = [
    pytest.mark.odoo_integration,
    pytest.mark.skipif(_SKIP_REASON is not None, reason=_SKIP_REASON or ""),
]


@pytest.fixture
def odoo_client() -> Generator[OdooClient, None, None]:
    config = OdooConfig.from_settings(get_settings())
    transport = OdooTransport(config)
    client = OdooClient(config, transport)
    try:
        yield client
    finally:
        transport.close()


def test_server_is_reachable_and_reports_a_version(odoo_client: OdooClient) -> None:
    version = odoo_client.get_server_version()

    assert version.server_version


def test_authentication_succeeds_with_configured_credentials(odoo_client: OdooClient) -> None:
    session = odoo_client.authenticate()

    assert session.uid > 0


def test_core_catalogue_models_are_available(odoo_client: OdooClient) -> None:
    odoo_client.authenticate()
    metadata = MetadataRepository(odoo_client)

    for model in ("product.template", "product.product", "product.category", "res.company"):
        availability = metadata.model_availability(model)
        assert availability.status.value == "AVAILABLE", f"{model}: {availability.detail}"


def test_full_environment_verification_does_not_report_blocked_overall(
    odoo_client: OdooClient,
) -> None:
    config = OdooConfig.from_settings(get_settings())

    report = run_environment_verification(config, odoo_client)

    # A real, reachable, correctly-credentialed instance should get at least past
    # reachability + authentication — individual optional checks (e.g. an
    # Enterprise-only gallery model) may still be NOT_APPLICABLE/BLOCKED without
    # that meaning the whole environment is unusable.
    assert report.overall_status in ("VERIFIED", "PARTIAL")
    assert report.session is not None
