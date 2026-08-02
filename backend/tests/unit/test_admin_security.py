"""Unit tests for app/core/security.py — password hashing and JWT access tokens.
Pure functions, no database needed."""

from __future__ import annotations

import uuid

import jwt
import pytest

from app.core.config import Settings
from app.core.security import (
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    generate_csrf_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {"admin_jwt_secret": "test-secret-test-secret-32bytes!"}
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


def test_hash_password_is_not_plaintext() -> None:
    hashed = hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"


def test_verify_password_accepts_correct_password() -> None:
    hashed = hash_password("hunter2")
    assert verify_password("hunter2", hashed) is True


def test_verify_password_rejects_wrong_password() -> None:
    hashed = hash_password("hunter2")
    assert verify_password("wrong", hashed) is False


def test_verify_password_never_raises_on_garbage_hash() -> None:
    assert verify_password("anything", "not-a-real-hash") is False


def test_access_token_round_trip() -> None:
    settings = _settings()
    admin_id = uuid.uuid4()

    token = create_access_token(admin_user_id=admin_id, role="SUPER_ADMIN", settings=settings)
    payload = decode_access_token(token, settings=settings)

    assert payload["sub"] == str(admin_id)
    assert payload["role"] == "SUPER_ADMIN"
    assert payload["aud"] == "admin"


def test_expired_access_token_rejected() -> None:
    settings = _settings(admin_access_token_ttl_minutes=-1)
    token = create_access_token(admin_user_id=uuid.uuid4(), role="SUPER_ADMIN", settings=settings)

    with pytest.raises(InvalidTokenError):
        decode_access_token(token, settings=settings)


def test_token_signed_with_wrong_secret_rejected() -> None:
    settings = _settings()
    token = create_access_token(admin_user_id=uuid.uuid4(), role="SUPER_ADMIN", settings=settings)

    other_settings = _settings(admin_jwt_secret="a-different-secret")
    with pytest.raises(InvalidTokenError):
        decode_access_token(token, settings=other_settings)


def test_non_admin_audience_token_rejected() -> None:
    settings = _settings()
    # A token that would otherwise decode fine, but was never issued by
    # create_access_token — simulates a token minted for some other audience.
    token = jwt.encode(
        {"sub": str(uuid.uuid4()), "aud": "not-admin", "type": "access"},
        settings.admin_jwt_secret,
        algorithm="HS256",
    )

    with pytest.raises(InvalidTokenError):
        decode_access_token(token, settings=settings)


def test_refresh_token_is_unique_and_hashed_deterministically() -> None:
    token_a = generate_refresh_token()
    token_b = generate_refresh_token()
    assert token_a != token_b

    assert hash_refresh_token(token_a) == hash_refresh_token(token_a)
    assert hash_refresh_token(token_a) != hash_refresh_token(token_b)


def test_csrf_tokens_are_unique() -> None:
    assert generate_csrf_token() != generate_csrf_token()
