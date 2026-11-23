from datetime import datetime
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.course import CourseBrief
from app.schemas.teacher import TeacherBrief

# Validation rules (BR-8). Whitespace is stripped before lengths are checked.
Code = Annotated[str, Field(min_length=1, max_length=10, pattern=r"^[A-Za-z0-9]+$")]
Name = Annotated[str, Field(min_length=1, max_length=120)]
Description = Annotated[str, Field(max_length=2000)]
Building = Annotated[str, Field(max_length=80)]
Phone = Annotated[str, Field(min_length=3, max_length=30, pattern=r"^\+?[0-9()\- ]+$")]


class DepartmentCreate(BaseModel):
    """Body of POST /departments (admin).

    The head is set afterwards with PATCH: a head must already be a teacher in
    the department (BR-3), and a new department has no teachers yet.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    code: Code
    name: Name
    description: Description | None = None
    building: Building | None = None
    phone: Phone | None = None


class DepartmentUpdate(BaseModel):
    """Body of PATCH /departments/{id}. Only the fields sent are changed.

    Admins may change every field. A HOD may change only description, building
    and phone of the department they head (decision recorded for T3.1).
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    code: Code | None = None
    name: Name | None = None
    description: Description | None = None
    building: Building | None = None
    phone: Phone | None = None
    head_id: int | None = None  # null removes the head

    @model_validator(mode="after")
    def required_fields_cannot_be_null(self) -> Self:
        for field in ("code", "name"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: str | None
    building: str | None
    phone: str | None
    head_id: int | None
    created_at: datetime
    updated_at: datetime


class DepartmentListOut(BaseModel):
    items: list[DepartmentOut]
    total: int


class DepartmentDetailOut(DepartmentOut):
    """GET /departments/{id}: the department plus its head, counts and courses (FR-2.3)."""

    head: TeacherBrief | None
    teacher_count: int
    student_count: int
    course_count: int
    courses: list[CourseBrief]
