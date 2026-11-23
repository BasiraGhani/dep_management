from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.user import UserRole
from app.schemas.common import PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH, Username


class UserOut(BaseModel):
    """A user account as returned by the API.

    Deliberately has no password field: the hash is never sent to clients (FR-1.3).
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: UserRole
    is_active: bool
    teacher_id: int | None
    student_id: int | None
    created_at: datetime
    updated_at: datetime


class UserListOut(BaseModel):
    items: list[UserOut]
    total: int


class UserCreate(BaseModel):
    """Body of POST /users (admin).

    Links must match the role (ARCHITECTURE §2): admin has none; hod and teacher
    have only `teacher_id`; student has only `student_id`. A `hod` must be the
    head of a department, and a head's account must be `hod` (BR-6).
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    username: Username
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)
    role: UserRole
    teacher_id: int | None = None
    student_id: int | None = None


class UserUpdate(BaseModel):
    """Body of PATCH /users/{id} (admin): activate/deactivate, change role or links.

    The resulting combination is checked with the same rules as on create.
    """

    model_config = ConfigDict(extra="forbid")

    is_active: bool | None = None
    role: UserRole | None = None
    teacher_id: int | None = None  # null unlinks
    student_id: int | None = None  # null unlinks

    @model_validator(mode="after")
    def required_fields_cannot_be_null(self) -> Self:
        for field in ("is_active", "role"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class TemporaryPassword(BaseModel):
    """Response of POST /users/{id}/reset-password. Shown once; it isn't stored."""

    temporary_password: str
