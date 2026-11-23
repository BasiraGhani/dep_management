from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH
from app.schemas.student import StudentOut
from app.schemas.teacher import TeacherOut
from app.schemas.user import UserOut


class Token(BaseModel):
    """Response of POST /auth/login."""

    access_token: str
    token_type: Literal["bearer"] = "bearer"


class CurrentUserOut(UserOut):
    """Response of GET /auth/me: the account plus its linked record (FR-1.2)."""

    teacher: TeacherOut | None
    student: StudentOut | None


class ChangePasswordRequest(BaseModel):
    """Body of POST /auth/change-password (FR-1.6)."""

    current_password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)
    new_password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)

    @model_validator(mode="after")
    def new_password_must_differ(self) -> Self:
        if self.new_password == self.current_password:
            raise ValueError("New password must be different from the current password")
        return self
