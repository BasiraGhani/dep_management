from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.deps import CurrentUser, DbSession
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, CurrentUserOut, Token
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

UNAUTHORIZED: dict[int | str, dict[str, Any]] = {
    status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid token"}
}


@router.post(
    "/login",
    response_model=Token,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Incorrect username or password"},
        status.HTTP_403_FORBIDDEN: {"description": "Account is deactivated"},
    },
)
def login(db: DbSession, form: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    """Log in with username and password (form fields) and get a bearer token."""
    user = auth_service.authenticate(db, form.username, form.password)
    return Token(access_token=auth_service.issue_token(user))


@router.get("/me", response_model=CurrentUserOut, responses=UNAUTHORIZED)
def read_me(current_user: CurrentUser) -> User:
    """The logged-in user, their role and their linked teacher or student record."""
    return current_user


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        **UNAUTHORIZED,
        status.HTTP_400_BAD_REQUEST: {"description": "Current password is incorrect"},
    },
)
def change_password(body: ChangePasswordRequest, db: DbSession, current_user: CurrentUser) -> None:
    """Change your own password; the current password is required."""
    auth_service.change_password(db, current_user, body.current_password, body.new_password)
