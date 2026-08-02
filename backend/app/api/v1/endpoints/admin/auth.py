"""Admin authentication endpoints: login, refresh, logout, me, change-password.

Tokens travel only as httpOnly cookies (app/core/security.py) — never in the JSON
response body. Login/refresh are the only two admin endpoints that don't require an
existing session; every other admin route is protected by get_current_admin at the
router level (see app/api/v1/endpoints/admin/__init__.py).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.api.deps.admin_auth import get_current_admin, require_csrf
from app.api.v1.schemas.admin_auth import (
    AdminChangePasswordRequest,
    AdminLoginRequest,
    AdminUserOut,
)
from app.core.exceptions import UnauthorizedError
from app.core.security import (
    ADMIN_REFRESH_COOKIE,
    clear_admin_auth_cookies,
    set_admin_auth_cookies,
)
from app.dependencies import get_app_settings, get_db
from app.models.admin.admin_user import AdminUser
from app.services.admin.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["admin-auth"])


def _user_out(admin: AdminUser) -> AdminUserOut:
    return AdminUserOut(
        id=str(admin.id),
        email=admin.email,
        full_name=admin.full_name,
        role=admin.role,
        is_active=admin.is_active,
        last_login_at=admin.last_login_at,
    )


@router.post("/login", summary="Admin email/password login")
def login(
    body: AdminLoginRequest,
    request: Request,
    response: Response,
    session: Session = Depends(get_db),
) -> AdminUserOut:
    settings = get_app_settings()
    admin, tokens = AuthService(session, settings).login(body.email, body.password, request=request)
    session.commit()

    set_admin_auth_cookies(
        response,
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        csrf_token=tokens.csrf_token,
        settings=settings,
    )
    return _user_out(admin)


@router.post("/refresh", summary="Rotate the access/refresh token pair")
def refresh(
    request: Request,
    response: Response,
    session: Session = Depends(get_db),
) -> AdminUserOut:
    settings = get_app_settings()
    refresh_token = request.cookies.get(ADMIN_REFRESH_COOKIE)
    if not refresh_token:
        raise UnauthorizedError("Admin session has expired, please log in again.")

    admin, tokens = AuthService(session, settings).refresh(refresh_token, request=request)
    session.commit()

    set_admin_auth_cookies(
        response,
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        csrf_token=tokens.csrf_token,
        settings=settings,
    )
    return _user_out(admin)


@router.post(
    "/logout",
    summary="Revoke the current session",
    dependencies=[Depends(require_csrf)],
)
def logout(
    request: Request,
    response: Response,
    session: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> dict[str, bool]:
    refresh_token = request.cookies.get(ADMIN_REFRESH_COOKIE)
    AuthService(session).logout(refresh_token, admin=admin, request=request)
    session.commit()
    clear_admin_auth_cookies(response)
    return {"ok": True}


@router.get("/me", summary="Current admin profile")
def me(admin: AdminUser = Depends(get_current_admin)) -> AdminUserOut:
    return _user_out(admin)


@router.post(
    "/change-password",
    summary="Change the current admin's password",
    dependencies=[Depends(require_csrf)],
)
def change_password(
    body: AdminChangePasswordRequest,
    request: Request,
    response: Response,
    session: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> dict[str, bool]:
    AuthService(session).change_password(
        admin,
        current_password=body.current_password,
        new_password=body.new_password,
        request=request,
    )
    session.commit()
    # The password change revoked every session (including this request's) —
    # the client must log in again.
    clear_admin_auth_cookies(response)
    return {"ok": True}
