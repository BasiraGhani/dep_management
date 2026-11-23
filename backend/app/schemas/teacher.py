from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.teacher import TeacherTitle


class TeacherOut(BaseModel):
    """A teacher record as returned by the API. T3.2 adds Create/Update schemas."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: str
    email: str
    phone: str | None
    title: TeacherTitle
    department_id: int
    hire_date: date | None
    created_at: datetime
    updated_at: datetime
