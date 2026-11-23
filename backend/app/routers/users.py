from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import DbSession, ListParams, require_roles
from app.models import User, UserRole
from app.schemas.user import TemporaryPassword, UserCreate, UserListOut, UserOut, UserUpdate
from app.services import users as service

# Every endpoint here is admin-only (REQUIREMENTS §3, FR-8).
router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={status.HTTP_403_FORBIDDEN: {"description": "Admins only"}},
)

Admin = Annotated[User, Depends(require_roles(UserRole.ADMIN))]

Responses = dict[int | str, dict[str, Any]]
NOT_FOUND: Responses = {status.HTTP_404_NOT_FOUND: {"description": "User not found"}}
INVALID: Responses = {
    status.HTTP_422_UNPROCESSABLE_CONTENT: {
        "description": "Invalid role/link combination, unknown record, or BR-6 violation"
    }
}
CONFLICT: Responses = {
    status.HTTP_409_CONFLICT: {"description": "Username taken, or record already has an account"}
}


@router.get("", response_model=UserListOut)
def list_users(
    db: DbSession,
    _admin: Admin,
    params: Annotated[ListParams, Depends()],
    role: Annotated[UserRole | None, Query()] = None,
    is_active: Annotated[bool | None, Query()] = None,
) -> UserListOut:
    """List accounts. `search` matches the username."""
    items, total = service.list_users(
        db, params.search_term, role, is_active, params.skip, params.limit
    )
    return UserListOut(items=[UserOut.model_validate(u) for u in items], total=total)


@router.post(
    "",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    responses=INVALID | CONFLICT,
)
def create_user(db: DbSession, _admin: Admin, body: UserCreate) -> Any:
    """Create an account. Links must match the role; `hod` only for a department head."""
    return service.create_user(db, body)


@router.patch("/{user_id}", response_model=UserOut, responses=NOT_FOUND | INVALID | CONFLICT)
def update_user(db: DbSession, admin: Admin, user_id: int, body: UserUpdate) -> Any:
    """Activate, deactivate, or change the role or links. You can't deactivate or
    demote your own account."""
    return service.update_user(db, user_id, body, admin)


@router.post("/{user_id}/reset-password", response_model=TemporaryPassword, responses=NOT_FOUND)
def reset_password(db: DbSession, _admin: Admin, user_id: int) -> TemporaryPassword:
    """Set a random temporary password and return it. It is shown only this once."""
    return TemporaryPassword(temporary_password=service.reset_password(db, user_id))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, responses=NOT_FOUND)
def delete_user(db: DbSession, admin: Admin, user_id: int) -> None:
    """Delete an account (the teacher or student record is kept). You can't delete
    your own account."""
    service.delete_user(db, user_id, admin)
