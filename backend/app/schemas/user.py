from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.user import UserRole


class UserOut(BaseModel):
    """A user account as returned by the API.

    Deliberately has no password field: the hash is never sent to clients (FR-1.3).
    T4.4 adds Create/Update schemas.
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
