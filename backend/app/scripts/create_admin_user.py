"""Bootstrap the first admin user(s). Never seeds a default/hardcoded password —
either pass one via the ADMIN_BOOTSTRAP_PASSWORD environment variable (e.g. for
scripted/CI provisioning) or you'll be prompted securely (no terminal echo).

Usage (from the backend/ virtualenv, migrations already applied):
    python -m app.scripts.create_admin_user --email owner@terrificbites.sa \\
        --full-name "Store Owner" --role SUPER_ADMIN
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys

from app.core.database import session_scope
from app.core.security import hash_password
from app.models.admin.admin_user import ADMIN_ROLES, AdminUser
from app.repositories.admin.admin_user_repository import AdminUserRepository

_MIN_PASSWORD_LENGTH = 8


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create (or reactivate) an admin user.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--full-name", required=True)
    parser.add_argument("--role", required=True, choices=ADMIN_ROLES)
    return parser.parse_args(argv)


def _read_password() -> str:
    password = os.environ.get("ADMIN_BOOTSTRAP_PASSWORD")
    if password:
        return password
    password = getpass.getpass("Password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        raise SystemExit("Passwords did not match.")
    return password


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    password = _read_password()
    if len(password) < _MIN_PASSWORD_LENGTH:
        print(f"Password must be at least {_MIN_PASSWORD_LENGTH} characters.", file=sys.stderr)
        return 1

    email = args.email.strip().lower()

    with session_scope() as session:
        repo = AdminUserRepository(session)
        existing = repo.get_by_email(email)
        if existing is not None:
            print(
                f"An admin user already exists for {email!r} (id={existing.id}).",
                file=sys.stderr,
            )
            return 1

        admin = AdminUser(
            email=email,
            password_hash=hash_password(password),
            full_name=args.full_name,
            role=args.role,
            is_active=True,
        )
        repo.create(admin)
        session.commit()
        print(f"Created admin user {email!r} (role={args.role}, id={admin.id}).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
