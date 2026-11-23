"""Password hashing (argon2 via pwdlib) and JWT access tokens (PyJWT)."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash
from pwdlib.exceptions import HashVerificationError, UnknownHashError
from pwdlib.hashers.argon2 import Argon2Hasher

from app.config import get_settings
from app.models.user import UserRole

ALGORITHM = "HS256"
REQUIRED_CLAIMS = ["sub", "role", "exp", "iat"]

_password_hash = PasswordHash((Argon2Hasher(),))


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------


def hash_password(password: str) -> str:
    """Hash `password` with argon2id. Each call uses a new random salt."""
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """True if `password` matches `password_hash`.

    A hash in an unknown or malformed format never matches: it returns False
    instead of raising, so a corrupt stored hash can't turn a login into a 500.
    """
    try:
        return _password_hash.verify(password, password_hash)
    except (UnknownHashError, HashVerificationError):
        return False


# ---------------------------------------------------------------------------
# Access tokens
# ---------------------------------------------------------------------------


class InvalidTokenError(Exception):
    """The token is malformed, has a bad signature, or is missing claims."""


class ExpiredTokenError(InvalidTokenError):
    """The token was valid but its `exp` time has passed."""


@dataclass(frozen=True)
class TokenData:
    """The verified contents of an access token."""

    user_id: int
    role: UserRole
    expires_at: datetime


def create_access_token(
    user_id: int, role: UserRole, expires_delta: timedelta | None = None
) -> str:
    """Create a signed access token for a user.

    Claims: `sub` (the user id, as a string per the JWT spec), `role`, `iat` and
    `exp`. The lifetime defaults to ACCESS_TOKEN_EXPIRE_MINUTES (FR-1.1).
    """
    settings = get_settings()
    now = datetime.now(UTC)
    lifetime = expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "role": role.value,
        "iat": now,
        "exp": now + lifetime,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> TokenData:
    """Verify a token and return its contents.

    Raises `ExpiredTokenError` if it has expired and `InvalidTokenError` for any
    other problem: bad signature or algorithm, malformed token, missing claims,
    or claims with invalid values. Only HS256 is accepted.
    """
    try:
        payload = jwt.decode(
            token,
            get_settings().secret_key,
            algorithms=[ALGORITHM],
            options={"require": REQUIRED_CLAIMS},
        )
    except jwt.ExpiredSignatureError as exc:
        raise ExpiredTokenError("Token has expired") from exc
    except jwt.PyJWTError as exc:
        raise InvalidTokenError("Invalid token") from exc

    try:
        user_id = int(payload["sub"])
        role = UserRole(payload["role"])
    except (TypeError, ValueError) as exc:
        raise InvalidTokenError("Invalid token claims") from exc

    return TokenData(
        user_id=user_id,
        role=role,
        expires_at=datetime.fromtimestamp(payload["exp"], UTC),
    )
