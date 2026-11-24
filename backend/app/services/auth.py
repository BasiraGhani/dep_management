"""Authentication rules: login, token -> user, and password changes."""

import math
from functools import lru_cache

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import (
    ExpiredTokenError,
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    login_throttle,
    verify_password,
)
from app.models.user import User

INVALID_CREDENTIALS = "Incorrect username or password"
ACCOUNT_DEACTIVATED = "Account is deactivated"
TOO_MANY_ATTEMPTS = "Too many failed login attempts. Try again in {minutes} minute(s)."
BEARER = {"WWW-Authenticate": "Bearer"}


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail=detail, headers=BEARER)


@lru_cache
def _dummy_hash() -> str:
    """A real argon2 hash, used to spend the same time on unknown usernames."""
    return hash_password("dummy-password-for-timing")


def authenticate(db: Session, username: str, password: str, client: str = "unknown") -> User:
    """Check a username/password pair and return the user (FR-1.1).

    * Unknown username or wrong password: 401 with one generic message, and the
      same hashing work in both cases, so usernames can't be discovered.
    * Correct password on a deactivated account: 403 (FR-8.2).
    * Too many recent failures from this client (for this username, or overall):
      429 with Retry-After, before the password is even checked (T8.4).
    """
    wait = login_throttle.retry_after(client, username)
    if wait is not None:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail=TOO_MANY_ATTEMPTS.format(minutes=math.ceil(wait / 60)),
            headers={"Retry-After": str(wait)},
        )
    user = db.scalar(select(User).where(User.username == username.strip().lower()))
    if user is None:
        verify_password(password, _dummy_hash())
        login_throttle.record_failure(client, username)
        raise _unauthorized(INVALID_CREDENTIALS)
    if not verify_password(password, user.password_hash):
        login_throttle.record_failure(client, username)
        raise _unauthorized(INVALID_CREDENTIALS)
    login_throttle.record_success(client, username)
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=ACCOUNT_DEACTIVATED)
    return user


def issue_token(user: User) -> str:
    """Create an access token for an authenticated user."""
    return create_access_token(user.id, user.role)


def user_from_token(db: Session, token: str) -> User:
    """Resolve a bearer token to an active user, or raise 401.

    Rejected: invalid or expired tokens, users that no longer exist, deactivated
    users (FR-8.2) and tokens whose role no longer matches the account (the role
    was changed after the token was issued, so the user must log in again).
    """
    try:
        data = decode_access_token(token)
    except ExpiredTokenError:
        raise _unauthorized("Token has expired") from None
    except InvalidTokenError:
        raise _unauthorized("Could not validate credentials") from None

    user = db.get(User, data.user_id)
    if user is None:
        raise _unauthorized("Could not validate credentials")
    if not user.is_active:
        raise _unauthorized(ACCOUNT_DEACTIVATED)
    if user.role is not data.role:
        raise _unauthorized("Token is out of date; please log in again")
    return user


def change_password(db: Session, user: User, current_password: str, new_password: str) -> None:
    """Replace the user's password after checking the current one (FR-1.6)."""
    if not verify_password(current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    user.password_hash = hash_password(new_password)
    db.commit()
