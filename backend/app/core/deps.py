"""FastAPI dependencies shared by the routers."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.services import auth as auth_service

__all__ = ["CurrentUser", "DbSession", "get_current_user", "get_db", "require_roles"]

# tokenUrl makes the "Authorize" button in /docs log in through POST /auth/login.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(db: DbSession, token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    """The authenticated, active user making the request (401 otherwise).

    A missing `Authorization: Bearer` header is rejected by `oauth2_scheme`; see
    `auth_service.user_from_token` for everything else that is rejected.
    """
    return auth_service.user_from_token(db, token)


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole) -> Callable[[User], User]:
    """Dependency factory: allow only users whose role is one of `roles`.

    Usage: `user: Annotated[User, Depends(require_roles(UserRole.ADMIN))]`, or
    `dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.HOD))]` on a
    route. Unauthenticated requests get 401 (from `get_current_user`); an
    authenticated user with another role gets 403. Scope rules ("own
    department") are checked separately with app.core.permissions.
    """
    if not roles:
        raise ValueError("require_roles() needs at least one role")
    allowed = frozenset(roles)

    def check_role(current_user: CurrentUser) -> User:
        if current_user.role not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
        return current_user

    return check_role
