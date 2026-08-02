"""Admin auth primitives: password hashing, JWT access tokens, opaque refresh tokens,
and the cookie/CSRF plumbing around them.

Tokens live in httpOnly cookies, never localStorage (CLAUDE.md admin-auth
instructions) — a JS-readable `admin_csrf` cookie is the one deliberate exception,
echoed back as the `X-CSRF-Token` header on every mutating request (double-submit
CSRF pattern). The access JWT carries `aud: "admin"` so it can never be confused with
a future customer-facing token even if both end up HS256-signed with the same
mechanism later.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Response
from starlette.requests import Request

from app.core.config import Settings

_JWT_ALGORITHM = "HS256"
_JWT_AUDIENCE = "admin"
_JWT_ACCESS_TYPE = "access"

ADMIN_ACCESS_COOKIE = "admin_access_token"
ADMIN_REFRESH_COOKIE = "admin_refresh_token"
ADMIN_CSRF_COOKIE = "admin_csrf"
CSRF_HEADER_NAME = "X-CSRF-Token"

_password_hasher = PasswordHasher()


class InvalidTokenError(Exception):
    """Raised for any unusable access token — expired, malformed, wrong audience."""


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False
    except Exception:  # noqa: BLE001 - a malformed/legacy hash must never crash login
        return False


def create_access_token(*, admin_user_id: uuid.UUID, role: str, settings: Settings) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(admin_user_id),
        "role": role,
        "aud": _JWT_AUDIENCE,
        "type": _JWT_ACCESS_TYPE,
        "iat": now,
        "exp": now + timedelta(minutes=settings.admin_access_token_ttl_minutes),
    }
    return jwt.encode(payload, settings.admin_jwt_secret, algorithm=_JWT_ALGORITHM)


def decode_access_token(token: str, *, settings: Settings) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.admin_jwt_secret,
            algorithms=[_JWT_ALGORITHM],
            audience=_JWT_AUDIENCE,
        )
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc

    if payload.get("type") != _JWT_ACCESS_TYPE:
        raise InvalidTokenError("Not an access token.")
    return payload


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def verify_csrf(request: Request) -> bool:
    cookie_value = request.cookies.get(ADMIN_CSRF_COOKIE)
    header_value = request.headers.get(CSRF_HEADER_NAME)
    if not cookie_value or not header_value:
        return False
    return secrets.compare_digest(cookie_value, header_value)


def set_admin_auth_cookies(
    response: Response,
    *,
    access_token: str,
    refresh_token: str,
    csrf_token: str,
    settings: Settings,
) -> None:
    # Secure cookies are only ever resent by a browser (or httpx's TestClient) over
    # an HTTPS connection — gating this on "== production" rather than
    # "!= development" means test/staging/local-non-TLS environments still get a
    # working cookie round-trip, while the one environment that truly serves over
    # HTTPS still gets Secure.
    secure = settings.app_env == "production"
    response.set_cookie(
        ADMIN_ACCESS_COOKIE,
        access_token,
        max_age=settings.admin_access_token_ttl_minutes * 60,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        ADMIN_REFRESH_COOKIE,
        refresh_token,
        max_age=settings.admin_refresh_token_ttl_days * 24 * 60 * 60,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )
    # Deliberately NOT httponly — the admin-api.ts client reads this to echo it back
    # as X-CSRF-Token on writes (double-submit pattern).
    response.set_cookie(
        ADMIN_CSRF_COOKIE,
        csrf_token,
        max_age=settings.admin_refresh_token_ttl_days * 24 * 60 * 60,
        httponly=False,
        secure=secure,
        samesite="lax",
        path="/",
    )


def clear_admin_auth_cookies(response: Response) -> None:
    for name in (ADMIN_ACCESS_COOKIE, ADMIN_REFRESH_COOKIE, ADMIN_CSRF_COOKIE):
        response.delete_cookie(name, path="/")
