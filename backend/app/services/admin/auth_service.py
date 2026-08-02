"""Admin login/refresh/logout/change-password.

Login failures always return the same generic message (task brief §2: "Return
generic login failure messages") regardless of whether the email doesn't exist, the
password is wrong, the account is disabled, or it's locked — the *reason* is only
ever recorded internally, in the audit log. Account lockout is DB-backed
(admin_users.failed_login_count/locked_until) so it keeps working even when Redis is
down; a Redis-backed per-IP+email throttle is layered on top when Redis is reachable,
but its unavailability never blocks a login attempt (task brief §9: never silently
skip a safety check, but also never turn an optional layer into a hard dependency).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session
from starlette.requests import Request

from app.core.config import Settings, get_settings
from app.core.exceptions import UnauthorizedError, ValidationAppError
from app.core.redis import get_redis_client
from app.core.security import (
    create_access_token,
    generate_csrf_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.admin.admin_session import AdminSession
from app.models.admin.admin_user import AdminUser
from app.repositories.admin.admin_session_repository import AdminSessionRepository
from app.repositories.admin.admin_user_repository import AdminUserRepository
from app.services.admin.audit_service import AuditService

logger = logging.getLogger("app.services.admin.auth")

_GENERIC_LOGIN_ERROR = "Invalid email or password."
_MIN_PASSWORD_LENGTH = 8


@dataclass(frozen=True)
class IssuedTokens:
    access_token: str
    refresh_token: str
    csrf_token: str


def _client_ip(request: Request | None) -> str | None:
    return request.client.host if request and request.client else None


class AuthService:
    def __init__(self, session: Session, settings: Settings | None = None) -> None:
        self.session = session
        self.users = AdminUserRepository(session)
        self.sessions = AdminSessionRepository(session)
        self.audit = AuditService(session)
        self.settings = settings or get_settings()

    def _throttle_ok(self, *, email: str, ip: str | None) -> bool:
        """Best-effort Redis sliding-window throttle. Returns True (allow) whenever
        Redis is unreachable — it is a defence-in-depth layer, not the primary one."""
        try:
            client = get_redis_client()
            key = f"admin:login_throttle:{ip or 'unknown'}:{email}"
            count = client.incr(key)
            if count == 1:
                client.expire(key, self.settings.admin_login_throttle_window_seconds)
            return int(count) <= self.settings.admin_login_throttle_max_attempts
        except Exception:  # noqa: BLE001 - Redis being down must never block login
            logger.warning("admin_login_throttle_unavailable")
            return True

    def _issue_tokens(self, admin: AdminUser, *, request: Request | None) -> IssuedTokens:
        access_token = create_access_token(
            admin_user_id=admin.id, role=admin.role, settings=self.settings
        )
        refresh_token = generate_refresh_token()
        now = datetime.now(UTC)
        self.sessions.create(
            AdminSession(
                admin_user_id=admin.id,
                refresh_token_hash=hash_refresh_token(refresh_token),
                user_agent=(request.headers.get("user-agent") if request else None),
                ip_address=_client_ip(request),
                expires_at=now + timedelta(days=self.settings.admin_refresh_token_ttl_days),
            )
        )
        return IssuedTokens(
            access_token=access_token, refresh_token=refresh_token, csrf_token=generate_csrf_token()
        )

    def login(
        self, email: str, password: str, *, request: Request | None = None
    ) -> tuple[AdminUser, IssuedTokens]:
        normalized_email = email.strip().lower()
        ip = _client_ip(request)

        if not self._throttle_ok(email=normalized_email, ip=ip):
            self.audit.record(
                admin=None,
                admin_email=normalized_email,
                action="admin.login_failed",
                entity_type="admin_user",
                reason="rate_limited",
                request=request,
            )
            raise UnauthorizedError(_GENERIC_LOGIN_ERROR)

        admin = self.users.get_by_email(normalized_email)
        now = datetime.now(UTC)

        if admin is None:
            self.audit.record(
                admin=None,
                admin_email=normalized_email,
                action="admin.login_failed",
                entity_type="admin_user",
                reason="no_such_account",
                request=request,
            )
            raise UnauthorizedError(_GENERIC_LOGIN_ERROR)

        if admin.locked_until is not None and admin.locked_until > now:
            self.audit.record(
                admin=admin,
                admin_email=admin.email,
                action="admin.login_failed",
                entity_type="admin_user",
                entity_id=str(admin.id),
                reason="locked",
                request=request,
            )
            raise UnauthorizedError(_GENERIC_LOGIN_ERROR)

        if not admin.is_active:
            self.audit.record(
                admin=admin,
                admin_email=admin.email,
                action="admin.login_failed",
                entity_type="admin_user",
                entity_id=str(admin.id),
                reason="inactive",
                request=request,
            )
            raise UnauthorizedError(_GENERIC_LOGIN_ERROR)

        if not verify_password(password, admin.password_hash):
            admin.failed_login_count += 1
            reason = "bad_password"
            if admin.failed_login_count >= self.settings.admin_login_max_attempts:
                admin.locked_until = now + timedelta(
                    minutes=self.settings.admin_login_lockout_minutes
                )
                admin.failed_login_count = 0
                reason = "bad_password_now_locked"
            self.session.flush()
            self.audit.record(
                admin=admin,
                admin_email=admin.email,
                action="admin.login_failed",
                entity_type="admin_user",
                entity_id=str(admin.id),
                reason=reason,
                request=request,
            )
            raise UnauthorizedError(_GENERIC_LOGIN_ERROR)

        admin.failed_login_count = 0
        admin.locked_until = None
        admin.last_login_at = now
        self.session.flush()

        tokens = self._issue_tokens(admin, request=request)
        self.audit.record(
            admin=admin,
            admin_email=admin.email,
            action="admin.login_succeeded",
            entity_type="admin_user",
            entity_id=str(admin.id),
            request=request,
        )
        return admin, tokens

    def refresh(
        self, refresh_token: str, *, request: Request | None = None
    ) -> tuple[AdminUser, IssuedTokens]:
        session_row = self.sessions.get_by_refresh_token_hash(hash_refresh_token(refresh_token))
        now = datetime.now(UTC)
        if (
            session_row is None
            or session_row.revoked_at is not None
            or session_row.expires_at < now
        ):
            raise UnauthorizedError("Admin session has expired, please log in again.")

        admin = self.users.get_by_id(session_row.admin_user_id)
        if admin is None or not admin.is_active:
            raise UnauthorizedError("Admin session has expired, please log in again.")

        # Rotate: revoke the presented refresh token so it can't be replayed, issue a
        # fresh pair.
        session_row.revoked_at = now
        self.session.flush()

        tokens = self._issue_tokens(admin, request=request)
        return admin, tokens

    def logout(
        self,
        refresh_token: str | None,
        *,
        admin: AdminUser | None = None,
        request: Request | None = None,
    ) -> None:
        if refresh_token:
            session_row = self.sessions.get_by_refresh_token_hash(hash_refresh_token(refresh_token))
            if session_row is not None and session_row.revoked_at is None:
                session_row.revoked_at = datetime.now(UTC)
                self.session.flush()

        if admin is not None:
            self.audit.record(
                admin=admin,
                admin_email=admin.email,
                action="admin.logout",
                entity_type="admin_user",
                entity_id=str(admin.id),
                request=request,
            )

    def change_password(
        self,
        admin: AdminUser,
        *,
        current_password: str,
        new_password: str,
        request: Request | None = None,
    ) -> None:
        if not verify_password(current_password, admin.password_hash):
            raise UnauthorizedError("Current password is incorrect.")
        if len(new_password) < _MIN_PASSWORD_LENGTH:
            raise ValidationAppError(
                f"New password must be at least {_MIN_PASSWORD_LENGTH} characters."
            )

        admin.password_hash = hash_password(new_password)
        self.session.flush()

        # Force re-login everywhere else — a changed password should invalidate any
        # session issued under the old one.
        for other_session in admin.sessions:
            if other_session.revoked_at is None:
                other_session.revoked_at = datetime.now(UTC)
        self.session.flush()

        self.audit.record(
            admin=admin,
            admin_email=admin.email,
            action="admin.password_changed",
            entity_type="admin_user",
            entity_id=str(admin.id),
            request=request,
        )
