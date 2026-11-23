from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.models.enrollment import Grade
from app.schemas.common import CourseBrief, StudentBrief

SEMESTER_PATTERN = r"^(19|20|21)\d{2}-(Spring|Summer|Fall)$"
# e.g. 2026-Fall. Years 1900-2199 keep obvious typos (e.g. 0226-Fall) out.
Semester = Annotated[
    str,
    Field(
        min_length=9,
        max_length=11,
        pattern=SEMESTER_PATTERN,
        examples=["2026-Fall"],
        description="YYYY-Spring, YYYY-Summer or YYYY-Fall",
    ),
]


class EnrollmentCreate(BaseModel):
    """Body of POST /enrollments (admin; HOD for courses of their department).

    New enrollments are ungraded; grades are set separately (T4.2).
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    student_id: int
    course_id: int
    semester: Semester


class EnrollmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    course_id: int
    semester: str
    grade: Grade | None
    student: StudentBrief
    course: CourseBrief
    created_at: datetime
    updated_at: datetime


class EnrollmentListOut(BaseModel):
    items: list[EnrollmentOut]
    total: int
