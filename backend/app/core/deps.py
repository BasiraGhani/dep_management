"""FastAPI dependencies shared by the routers."""

from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services import auth as auth_service

__all__ = ["CurrentUser", "DbSession", "get_current_user", "get_db"]

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
