"""Unit tests for app.core.security: password hashing and JWT access tokens (T2.1)."""

import base64
import json
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest

from app.config import get_settings
from app.core.security import (
    ALGORITHM,
    ExpiredTokenError,
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.models import UserRole

PASSWORD = "correct horse battery staple"


def secret() -> str:
    return get_settings().secret_key


def sign(payload: dict[str, Any], key: str | None = None, algorithm: str = ALGORITHM) -> str:
    """Sign an arbitrary payload, to build tokens the app would never issue."""
    return jwt.encode(payload, key or secret(), algorithm=algorithm)


def valid_claims(**overrides: Any) -> dict[str, Any]:
    """Claims for a valid token; times are JWT NumericDates (integer seconds)."""
    now = int(datetime.now(UTC).timestamp())
    claims: dict[str, Any] = {
        "sub": "7",
        "role": "teacher",
        "iat": now,
        "exp": now + 300,
    }
    return claims | overrides


def b64url(data: dict[str, Any]) -> str:
    raw = json.dumps(data, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


# ---------- Passwords ----------


@pytest.fixture(scope="module")
def stored_hash() -> str:
    return hash_password(PASSWORD)


def test_correct_password_verifies(stored_hash: str) -> None:
    assert verify_password(PASSWORD, stored_hash) is True


@pytest.mark.parametrize(
    "attempt",
    ["wrong password", "", PASSWORD.upper(), PASSWORD + " ", PASSWORD[:-1]],
)
def test_wrong_password_fails(stored_hash: str, attempt: str) -> None:
    assert verify_password(attempt, stored_hash) is False


def test_hash_is_argon2id_and_not_the_plain_password(stored_hash: str) -> None:
    assert stored_hash.startswith("$argon2id$")
    assert PASSWORD not in stored_hash


def test_same_password_hashes_differently_each_time(stored_hash: str) -> None:
    second = hash_password(PASSWORD)

    assert second != stored_hash  # random salt
    assert verify_password(PASSWORD, second) is True


@pytest.mark.parametrize(
    "bad_hash",
    [
        "",
        "not-a-hash",
        "$2b$12$abcdefghijklmnopqrstuv",  # bcrypt-looking: hasher not configured
        "$argon2id$v=19$m=65536,t=3,p=4$broken",  # argon2 prefix, corrupt body
    ],
)
def test_malformed_stored_hash_never_matches_and_does_not_raise(bad_hash: str) -> None:
    assert verify_password(PASSWORD, bad_hash) is False


# ---------- Tokens: happy path ----------


def test_token_round_trips_user_id_and_role() -> None:
    data = decode_access_token(create_access_token(42, UserRole.HOD))

    assert data.user_id == 42
    assert data.role is UserRole.HOD


@pytest.mark.parametrize("role", list(UserRole))
def test_every_role_round_trips(role: UserRole) -> None:
    assert decode_access_token(create_access_token(1, role)).role is role


def test_token_claims_follow_the_spec() -> None:
    token = create_access_token(42, UserRole.ADMIN)
    claims = jwt.decode(token, secret(), algorithms=[ALGORITHM])

    assert claims["sub"] == "42"  # JWT `sub` is a string
    assert claims["role"] == "admin"
    assert set(claims) == {"sub", "role", "iat", "exp"}
    assert jwt.get_unverified_header(token)["alg"] == "HS256"


def test_default_lifetime_comes_from_settings() -> None:
    before = datetime.now(UTC)
    data = decode_access_token(create_access_token(1, UserRole.ADMIN))
    expected = before + timedelta(minutes=get_settings().access_token_expire_minutes)

    assert abs((data.expires_at - expected).total_seconds()) < 5


def test_lifetime_setting_is_honoured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "5")
    get_settings.cache_clear()
    try:
        data = decode_access_token(create_access_token(1, UserRole.ADMIN))
    finally:
        get_settings.cache_clear()

    remaining = data.expires_at - datetime.now(UTC)
    assert timedelta(minutes=4) < remaining <= timedelta(minutes=5)


def test_custom_lifetime_is_honoured() -> None:
    data = decode_access_token(create_access_token(1, UserRole.ADMIN, timedelta(minutes=2)))
    remaining = data.expires_at - datetime.now(UTC)

    assert timedelta(minutes=1) < remaining <= timedelta(minutes=2)


# ---------- Tokens: expired ----------


def test_expired_token_is_rejected() -> None:
    token = create_access_token(1, UserRole.ADMIN, expires_delta=timedelta(seconds=-1))

    with pytest.raises(ExpiredTokenError) as exc_info:
        decode_access_token(token)
    assert isinstance(exc_info.value.__cause__, jwt.ExpiredSignatureError)


def test_expired_error_is_also_an_invalid_token_error() -> None:
    token = create_access_token(1, UserRole.ADMIN, expires_delta=timedelta(seconds=-1))

    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


# ---------- Tokens: tampered or forged ----------


def test_token_with_edited_payload_is_rejected() -> None:
    """Changing the role inside a real token breaks its signature."""
    header, _payload, signature = create_access_token(7, UserRole.STUDENT).split(".")
    forged_payload = b64url(valid_claims(sub="7", role="admin"))

    with pytest.raises(InvalidTokenError) as exc_info:
        decode_access_token(f"{header}.{forged_payload}.{signature}")
    assert isinstance(exc_info.value.__cause__, jwt.InvalidSignatureError)


def test_token_with_edited_signature_is_rejected() -> None:
    header, payload, signature = create_access_token(7, UserRole.STUDENT).split(".")
    flipped = ("A" if signature[0] != "A" else "B") + signature[1:]

    with pytest.raises(InvalidTokenError) as exc_info:
        decode_access_token(f"{header}.{payload}.{flipped}")
    assert isinstance(exc_info.value.__cause__, jwt.InvalidSignatureError)


def test_token_signed_with_another_key_is_rejected() -> None:
    with pytest.raises(InvalidTokenError) as exc_info:
        decode_access_token(sign(valid_claims(), key="some-other-secret-key-0123456789"))
    assert isinstance(exc_info.value.__cause__, jwt.InvalidSignatureError)


def test_unsigned_alg_none_token_is_rejected() -> None:
    token = f"{b64url({'alg': 'none', 'typ': 'JWT'})}.{b64url(valid_claims())}."

    with pytest.raises(InvalidTokenError) as exc_info:
        decode_access_token(token)
    assert isinstance(exc_info.value.__cause__, jwt.InvalidAlgorithmError)


# Signing HS512 with the (HS256-sized) test key is the point of this test.
@pytest.mark.filterwarnings("ignore::jwt.warnings.InsecureKeyLengthWarning")
def test_token_with_another_algorithm_is_rejected() -> None:
    """Only HS256 is accepted, even when the same secret signs the token."""
    with pytest.raises(InvalidTokenError) as exc_info:
        decode_access_token(sign(valid_claims(), algorithm="HS512"))
    assert isinstance(exc_info.value.__cause__, jwt.InvalidAlgorithmError)


@pytest.mark.parametrize("token", ["", "garbage", "a.b.c", "a.b"])
def test_malformed_token_is_rejected(token: str) -> None:
    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


# ---------- Tokens: bad claims ----------


@pytest.mark.parametrize("missing", ["sub", "role", "exp", "iat"])
def test_token_missing_a_required_claim_is_rejected(missing: str) -> None:
    claims = valid_claims()
    del claims[missing]

    with pytest.raises(InvalidTokenError):
        decode_access_token(sign(claims))


@pytest.mark.parametrize("sub", ["abc", "1.5", ""])
def test_token_with_non_integer_subject_is_rejected(sub: str) -> None:
    with pytest.raises(InvalidTokenError):
        decode_access_token(sign(valid_claims(sub=sub)))


@pytest.mark.parametrize("role", ["superuser", "ADMIN", ""])
def test_token_with_unknown_role_is_rejected(role: str) -> None:
    with pytest.raises(InvalidTokenError):
        decode_access_token(sign(valid_claims(role=role)))
