from datetime import date, datetime
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enrollment import Grade
from app.models.student import StudentStatus
from app.schemas.common import AccountCreate, CourseBrief, Email, PersonName, Phone

StudentNo = Annotated[str, Field(min_length=1, max_length=20, pattern=r"^[A-Za-z0-9-]+$")]
Year = Annotated[int, Field(ge=1, le=6)]


def _not_in_future(value: date | None) -> date | None:
    if value is not None and value > date.today():
        raise ValueError("date cannot be in the future")
    return value


class StudentCreate(BaseModel):
    """Body of POST /students (admin; HOD for the department they head)."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    student_no: StudentNo
    first_name: PersonName
    last_name: PersonName
    email: Email
    phone: Phone | None = None
    date_of_birth: date | None = None
    department_id: int
    year: Year
    status: StudentStatus = StudentStatus.ACTIVE
    enrollment_date: date = Field(default_factory=date.today)
    create_account: AccountCreate | None = None  # FR-4.3

    _past_dates = field_validator("date_of_birth", "enrollment_date")(_not_in_future)


class StudentUpdate(BaseModel):
    """Body of PATCH /students/{id}. Only the fields sent are changed.

    Admin: any field. HOD: students of the department they head, without moving
    them elsewhere. Student: their own `phone` and `email` only.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    student_no: StudentNo | None = None
    first_name: PersonName | None = None
    last_name: PersonName | None = None
    email: Email | None = None
    phone: Phone | None = None
    date_of_birth: date | None = None
    department_id: int | None = None
    year: Year | None = None
    status: StudentStatus | None = None
    enrollment_date: date | None = None

    _past_dates = field_validator("date_of_birth", "enrollment_date")(_not_in_future)

    @model_validator(mode="after")
    def required_fields_cannot_be_null(self) -> Self:
        required = (
            "student_no",
            "first_name",
            "last_name",
            "email",
            "department_id",
            "year",
            "status",
            "enrollment_date",
        )
        for field in required:
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class StudentOut(BaseModel):
    """A student record as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    student_no: str
    first_name: str
    last_name: str
    email: str
    phone: str | None
    date_of_birth: date | None
    department_id: int
    year: int
    status: StudentStatus
    enrollment_date: date
    created_at: datetime
    updated_at: datetime


class StudentListOut(BaseModel):
    items: list[StudentOut]
    total: int


class StudentEnrollmentOut(BaseModel):
    """One of the student's enrollments, with its course."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    semester: str
    grade: Grade | None
    course: CourseBrief


class StudentDetailOut(StudentOut):
    """GET /students/{id}: the student, their enrollments and account link.

    The GPA is added in T4.2.
    """

    enrollments: list[StudentEnrollmentOut]
    user_id: int | None
