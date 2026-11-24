"""Password hashing (argon2 via pwdlib), JWT access tokens (PyJWT) and the
failed-login throttle."""

import math
import threading
import time
from collections import deque
from collections.abc import Callable
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


# ---------------------------------------------------------------------------
# Failed-login throttle
# ---------------------------------------------------------------------------

# Failed logins allowed in the window before further attempts get 429:
MAX_FAILURES_PER_ACCOUNT = 5  # one client trying one username
MAX_FAILURES_PER_CLIENT = 20  # one client trying any usernames (credential stuffing)
FAILURE_WINDOW_SECONDS = 15 * 60


class LoginThrottle:
    """Counts failed logins in a sliding window and says when to slow down.

    Keyed by client IP and username, so an attacker elsewhere can't lock a real
    user out, plus by client IP alone. In memory: per backend process, and reset
    on restart (enough for the single-process deployment in docker-compose.yml).
    """

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._failures: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _keys(client: str, username: str) -> tuple[str, str]:
        return f"account:{client}:{username.strip().lower()}", f"client:{client}"

    def _recent(self, key: str, now: float) -> deque[float]:
        times = self._failures.get(key, deque())
        while times and times[0] <= now - FAILURE_WINDOW_SECONDS:
            times.popleft()
        if not times:
            self._failures.pop(key, None)
        return times

    def retry_after(self, client: str, username: str) -> int | None:
        """Seconds until this client may try this username again, or None if it may now."""
        now = self._clock()
        account_key, client_key = self._keys(client, username)
        with self._lock:
            waits = [
                times[0] + FAILURE_WINDOW_SECONDS - now
                for key, limit in (
                    (account_key, MAX_FAILURES_PER_ACCOUNT),
                    (client_key, MAX_FAILURES_PER_CLIENT),
                )
                if len(times := self._recent(key, now)) >= limit
            ]
        return max(1, math.ceil(max(waits))) if waits else None

    def record_failure(self, client: str, username: str) -> None:
        now = self._clock()
        with self._lock:
            for key in self._keys(client, username):
                times = self._recent(key, now)
                times.append(now)
                self._failures[key] = times

    def record_success(self, client: str, username: str) -> None:
        """A correct password clears that account's count (not the client's)."""
        account_key, _ = self._keys(client, username)
        with self._lock:
            self._failures.pop(account_key, None)

    def reset(self) -> None:
        with self._lock:
            self._failures.clear()


login_throttle = LoginThrottle()
