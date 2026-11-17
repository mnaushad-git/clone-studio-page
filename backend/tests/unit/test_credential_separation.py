"""Each deployed service holds only the secrets its job needs. Read from the compose files
themselves, so a later edit that widens access fails here without needing Docker."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

from app.core.config import Settings

DEPLOY = Path(__file__).resolve().parents[3] / "deploy"
ODOO_LOGIN_VARS = {"ODOO_USERNAME", "ODOO_PASSWORD", "ODOO_API_KEY"}
ADMIN_SECRETS = {"ODOO_ADMIN_PASSWD", "POSTGRES_ADMIN_PASSWORD", "ODOO_DB_PASSWORD"}


def _services(relative: str) -> dict[str, dict[str, Any]]:
    return yaml.safe_load((DEPLOY / relative).read_text(encoding="utf-8"))["services"]


COMPOSE_NAMES = [
    ("docker-compose.prod.yml", "api", "celery-worker", "celery-beat", "catalogue-import", "odoo"),
    (
        "local/docker-compose.yml",
        "terrific-api",
        "terrific-worker",
        "terrific-beat",
        "terrific-catalogue-import",
        "terrific-odoo",
    ),
]


@pytest.mark.parametrize(("file", "api", "worker", "beat", "importer", "odoo"), COMPOSE_NAMES)
def test_compose_gives_each_service_only_its_own_credentials(
    file: str, api: str, worker: str, beat: str, importer: str, odoo: str
) -> None:
    services = _services(file)

    for name in (api, beat):
        env = services[name]["environment"]
        assert not ODOO_LOGIN_VARS & set(env), name
        assert not ADMIN_SECRETS & set(env), name
        assert "env_file" not in services[name], name

    assert "ODOO_ORDER_SYNC_PASSWORD" in services[worker]["environment"]["ODOO_PASSWORD"]
    assert "ODOO_CATALOGUE_IMPORT_PASSWORD" in services[importer]["environment"]["ODOO_PASSWORD"]
    assert not ADMIN_SECRETS & set(services[worker]["environment"])
    # The long-running Odoo server doesn't need the integration users' passwords.
    assert not any("ORDER_SYNC" in key for key in services[odoo]["environment"])


@pytest.mark.parametrize("file", ["docker-compose.prod.yml", "local/docker-compose.yml"])
def test_the_postgres_admin_role_is_a_name_initdb_accepts(file: str) -> None:
    postgres = next(s for n, s in _services(file).items() if n.endswith("postgres"))
    assert not postgres["environment"]["POSTGRES_USER"].startswith("pg_")


def test_every_required_compose_variable_is_in_the_env_template() -> None:
    compose = (DEPLOY / "docker-compose.prod.yml").read_text(encoding="utf-8")
    template = (DEPLOY / ".env.prod.example").read_text(encoding="utf-8")
    required = set(re.findall(r"\$\{([A-Z0-9_]+)(?::[-?])", compose))
    defined = set(re.findall(r"^([A-Z0-9_]+)=", template, flags=re.MULTILINE))
    assert required - defined == set()


@pytest.mark.parametrize("role", ["api", "beat", "migrate"])
@pytest.mark.parametrize("secret", [{"odoo_password": "x"}, {"odoo_api_key": "x"}])
def test_services_that_never_talk_to_odoo_refuse_a_credential(
    role: str, secret: dict[str, str]
) -> None:
    with pytest.raises(ValueError, match="must not hold Odoo credentials"):
        Settings(_env_file=None, service_role=role, **secret)


@pytest.mark.parametrize("role", ["worker", "catalogue_import", ""])
def test_services_that_talk_to_odoo_accept_a_credential(role: str) -> None:
    assert Settings(_env_file=None, service_role=role, odoo_password="x").odoo_password == "x"
