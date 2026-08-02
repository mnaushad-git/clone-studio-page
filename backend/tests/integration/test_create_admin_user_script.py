"""Integration test for app/scripts/create_admin_user.py. Runs against the real
(migrated) test database via session_scope — unlike the endpoint tests, this isn't
wrapped in the savepoint-rollback db_session fixture (the script opens its own
session), so it cleans up the row it creates explicitly.
"""

from __future__ import annotations

import os
import uuid

from sqlalchemy import delete

from app.core.database import session_scope
from app.models.admin.admin_user import AdminUser
from app.scripts.create_admin_user import main


def test_bootstrap_creates_admin_user(db_engine: object) -> None:
    email = f"bootstrap-{uuid.uuid4().hex[:8]}@test.terrificbites.sa"
    os.environ["ADMIN_BOOTSTRAP_PASSWORD"] = "BootstrapPassw0rd!"
    try:
        exit_code = main(
            ["--email", email, "--full-name", "Bootstrap Admin", "--role", "SUPER_ADMIN"]
        )
        assert exit_code == 0

        with session_scope() as session:
            created = session.query(AdminUser).filter(AdminUser.email == email).one_or_none()
            assert created is not None
            assert created.role == "SUPER_ADMIN"
            assert created.is_active is True
            assert created.password_hash != "BootstrapPassw0rd!"
    finally:
        del os.environ["ADMIN_BOOTSTRAP_PASSWORD"]
        with session_scope() as session:
            session.execute(delete(AdminUser).where(AdminUser.email == email))
            session.commit()


def test_bootstrap_rejects_short_password(db_engine: object) -> None:
    email = f"bootstrap-short-{uuid.uuid4().hex[:8]}@test.terrificbites.sa"
    os.environ["ADMIN_BOOTSTRAP_PASSWORD"] = "short"
    try:
        exit_code = main(
            ["--email", email, "--full-name", "Bootstrap Admin", "--role", "SUPER_ADMIN"]
        )
        assert exit_code == 1

        with session_scope() as session:
            created = session.query(AdminUser).filter(AdminUser.email == email).one_or_none()
            assert created is None
    finally:
        del os.environ["ADMIN_BOOTSTRAP_PASSWORD"]


def test_bootstrap_refuses_duplicate_email(db_engine: object) -> None:
    email = f"bootstrap-dup-{uuid.uuid4().hex[:8]}@test.terrificbites.sa"
    os.environ["ADMIN_BOOTSTRAP_PASSWORD"] = "BootstrapPassw0rd!"
    try:
        assert main(["--email", email, "--full-name", "A", "--role", "SUPER_ADMIN"]) == 0
        assert main(["--email", email, "--full-name", "B", "--role", "SUPER_ADMIN"]) == 1
    finally:
        del os.environ["ADMIN_BOOTSTRAP_PASSWORD"]
        with session_scope() as session:
            session.execute(delete(AdminUser).where(AdminUser.email == email))
            session.commit()
