from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.config import Settings
from app.integrations.odoo.exceptions import OdooRemoteError
from app.scripts import verify_odoo_connection
from tests.unit.odoo.conftest import FakeTransport

SECRET_MARKER = "super-secret-do-not-log-1234"  # noqa: S105 - test fixture value


class ClosableFakeTransport(FakeTransport):
    def close(self) -> None:  # OdooTransport's real interface; FakeTransport has none
        pass


def _configured_settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "_env_file": None,
        "odoo_base_url": "http://localhost:8069",
        "odoo_database": "terrific_bites_dev",
        "odoo_username": "admin",
        "odoo_password": SECRET_MARKER,
    }
    defaults.update(overrides)
    return Settings(**defaults)  # type: ignore[arg-type]


def test_main_exits_2_when_odoo_not_configured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    unconfigured = Settings(_env_file=None, odoo_base_url="", odoo_database="", odoo_username="")
    monkeypatch.setattr(verify_odoo_connection, "get_settings", lambda: unconfigured)
    output_path = tmp_path / "report.json"

    exit_code = verify_odoo_connection.main(["--output", str(output_path)])

    assert exit_code == 2
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["overall_status"] == "BLOCKED"
    assert "not configured" in report["blocker_reason"]


def test_report_never_contains_the_configured_secret(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    settings = _configured_settings()
    monkeypatch.setattr(verify_odoo_connection, "get_settings", lambda: settings)

    fake_transport = ClosableFakeTransport()
    fake_transport.queue(
        ("common", "version"),
        {
            "server_version": "19.0",
            "server_version_info": [],
            "server_serie": "19.0",
            "protocol_version": 1,
        },
    )
    fake_transport.queue(("common", "authenticate"), OdooRemoteError("bad credentials"))
    monkeypatch.setattr(verify_odoo_connection, "OdooTransport", lambda config: fake_transport)

    output_path = tmp_path / "report.json"
    exit_code = verify_odoo_connection.main(
        ["--check-connection", "--check-authentication", "--output", str(output_path)]
    )

    assert exit_code == 1
    written = output_path.read_text(encoding="utf-8")
    assert SECRET_MARKER not in written

    captured = capsys.readouterr()
    assert SECRET_MARKER not in captured.out
