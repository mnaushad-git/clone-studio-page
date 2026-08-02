"""Verifies the catalogue migration (0002) actually upgrades and downgrades cleanly
against a real PostgreSQL database — not just that the offline --sql dump parses.

Self-contained: doesn't use the shared db_session/db_engine fixtures (those assume a
stable, always-migrated schema) since this test deliberately mutates schema state. It
always restores to head in a finally block so it doesn't affect any other test.
"""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.core.config import get_settings

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


def _alembic_config() -> Config:
    settings = get_settings()
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "app" / "db" / "alembic"))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    return cfg


def test_alembic_upgrade_and_downgrade_round_trip() -> None:
    cfg = _alembic_config()
    engine = create_engine(get_settings().database_url)
    try:
        command.upgrade(cfg, "head")
        tables_at_head = set(inspect(engine).get_table_names())
        assert "catalogue_products" in tables_at_head
        assert "catalogue_categories" in tables_at_head
        assert "catalogue_seed_runs" in tables_at_head

        command.downgrade(cfg, "0001")
        tables_after_downgrade = set(inspect(engine).get_table_names())
        assert "catalogue_products" not in tables_after_downgrade
        assert "catalogue_categories" not in tables_after_downgrade
        assert "alembic_version" in tables_after_downgrade

        command.upgrade(cfg, "head")
        tables_after_reupgrade = set(inspect(engine).get_table_names())
        assert tables_after_reupgrade == tables_at_head
    finally:
        command.upgrade(cfg, "head")
        engine.dispose()
