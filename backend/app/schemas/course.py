from datetime import datetime
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.course import DEFAULT_CAPACITY
from app.models.enrollment import Grade
from app.schemas.common import TeacherBrief

# Validation rules (BR-8). Whitespace is stripped before lengths are checked.
CourseCode = Annotated[str, Field(min_length=1, max_length=15, pattern=r"^[A-Za-z0-9-]+$")]
Title = Annotated[str, Field(min_length=1, max_length=150)]
Description = Annotated[str, Field(max_length=5000)]
Credits = Annotated[int, Field(ge=1, le=6)]
Capacity = Annotated[int, Field(ge=1, le=1000)]


class CourseCreate(BaseModel):
    """Body of POST /courses (admin; HOD for the department they head).

    The teacher, if given, must belong to the course's department (BR-2).
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    code: CourseCode
    title: Title
    description: Description | None = None
    credits: Credits
    capacity: Capacity = DEFAULT_CAPACITY
    department_id: int
    teacher_id: int | None = None


class CourseUpdate(BaseModel):
    """Body of PATCH /courses/{id}. Only the fields sent are changed.

    Admin: any field. HOD: courses of the department they head, without moving
    them elsewhere. Teacher: only the description of a course they teach.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    code: CourseCode | None = None
    title: Title | None = None
    description: Description | None = None
    credits: Credits | None = None
    capacity: Capacity | None = None
    department_id: int | None = None
    teacher_id: int | None = None  # null unassigns the teacher

    @model_validator(mode="after")
    def required_fields_cannot_be_null(self) -> Self:
        for field in ("code", "title", "credits", "capacity", "department_id"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class CourseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    title: str
    description: str | None
    credits: int
    capacity: int
    department_id: int
    teacher_id: int | None
    created_at: datetime
    updated_at: datetime


class CourseListOut(BaseModel):
    items: list[CourseOut]
    total: int


class RosterEntry(BaseModel):
    """One enrolled student on a course roster (FR-5.4)."""

    enrollment_id: int
    student_id: int
    student_no: str
    first_name: str
    last_name: str
    semester: str
    grade: Grade | None


class CourseDetailOut(CourseOut):
    """GET /courses/{id}: the course, its teacher and its roster.

    `roster` is null for users who may not see enrollments of this course
    (students; teachers of other courses; HODs of other departments).
    """

    teacher: TeacherBrief | None
    roster: list[RosterEntry] | None
