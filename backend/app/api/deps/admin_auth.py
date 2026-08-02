"""Admin authentication/authorization dependencies.

`get_current_admin` is the single place an access-token cookie is read and verified;
`require_role` is a plain per-endpoint permission check (task brief §2: "Do not build
a complex RBAC engine. Use explicit endpoint-level permission checks."), not a general
RBAC engine. `require_csrf` guards every mutating admin endpoint against the
double-submit CSRF cookie (app/core/security.py).
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import (
    ADMIN_ACCESS_COOKIE,
    InvalidTokenError,
    decode_access_token,
    verify_csrf,
)
from app.dependencies import get_app_settings, get_db
from app.models.admin.admin_user import AdminUser
from app.repositories.admin.admin_user_repository import AdminUserRepository


def get_current_admin(
    request: Request,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> AdminUser:
    token = request.cookies.get(ADMIN_ACCESS_COOKIE)
    if not token:
        raise UnauthorizedError("Admin authentication is required.")

    try:
        payload = decode_access_token(token, settings=settings)
    except InvalidTokenError as exc:
        raise UnauthorizedError("Admin session has expired or is invalid.") from exc

    try:
        admin_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise UnauthorizedError("Admin session has expired or is invalid.") from exc

    admin = AdminUserRepository(session).get_by_id(admin_id)
    if admin is None or not admin.is_active:
        raise UnauthorizedError("Admin session has expired or is invalid.")

    request.state.admin = admin
    return admin


def require_role(*roles: str) -> Callable[[AdminUser], AdminUser]:
    allowed = set(roles)

    def _check(admin: AdminUser = Depends(get_current_admin)) -> AdminUser:
        if admin.role not in allowed:
            raise ForbiddenError("You do not have permission to perform this action.")
        return admin

    return _check


def require_csrf(request: Request) -> None:
    if not verify_csrf(request):
        raise ForbiddenError("Missing or invalid CSRF token.")
