from datetime import date, datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.models.teacher import TeacherTitle
from app.schemas.common import AccountCreate, CourseBrief, Email, PersonName, Phone


def _not_in_future(value: date | None) -> date | None:
    if value is not None and value > date.today():
        raise ValueError("hire_date cannot be in the future")
    return value


class TeacherCreate(BaseModel):
    """Body of POST /teachers (admin; HOD for their own department)."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    first_name: PersonName
    last_name: PersonName
    email: Email
    phone: Phone | None = None
    title: TeacherTitle
    department_id: int
    hire_date: date | None = None
    create_account: AccountCreate | None = None  # FR-3.3

    _hire_date_not_in_future = field_validator("hire_date")(_not_in_future)


class TeacherUpdate(BaseModel):
    """Body of PATCH /teachers/{id}. Only the fields sent are changed.

    Admin: any field. HOD: teachers of the department they head, without moving
    them to another department. Teacher: their own `phone` and `email` only.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    first_name: PersonName | None = None
    last_name: PersonName | None = None
    email: Email | None = None
    phone: Phone | None = None
    title: TeacherTitle | None = None
    department_id: int | None = None
    hire_date: date | None = None

    _hire_date_not_in_future = field_validator("hire_date")(_not_in_future)

    @model_validator(mode="after")
    def required_fields_cannot_be_null(self) -> Self:
        for field in ("first_name", "last_name", "email", "title", "department_id"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class TeacherPublicOut(BaseModel):
    """What students see of a teacher (decision for T3.2: no phone or hire date)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: str
    title: TeacherTitle
    email: str
    department_id: int


class TeacherOut(TeacherPublicOut):
    """A teacher record as admins, HODs and teachers see it."""

    phone: str | None
    hire_date: date | None
    created_at: datetime
    updated_at: datetime


class TeacherListOut(BaseModel):
    items: list[TeacherOut]
    total: int


class TeacherPublicListOut(BaseModel):
    items: list[TeacherPublicOut]
    total: int


class TeacherDetailOut(TeacherOut):
    """GET /teachers/{id} for staff: the teacher, their courses and account link."""

    courses: list[CourseBrief]
    user_id: int | None  # the linked login account, if any


class TeacherPublicDetailOut(TeacherPublicOut):
    """GET /teachers/{id} for students: public fields and courses taught."""

    courses: list[CourseBrief]
