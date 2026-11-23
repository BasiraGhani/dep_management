"""Field rules and small schemas shared by several resources (BR-8)."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.models.teacher import TeacherTitle

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128

PersonName = Annotated[str, Field(min_length=1, max_length=60)]
# Deliberately simple: one @, no spaces, a dot in the domain. Stored lowercase.
Email = Annotated[str, Field(max_length=120, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")]
Phone = Annotated[str, Field(min_length=3, max_length=30, pattern=r"^\+?[0-9()\- ]+$")]
Username = Annotated[str, Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9._-]+$")]


class AccountCreate(BaseModel):
    """Optional login account created together with a teacher or student (FR-3.3, FR-4.3)."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    username: Username
    temp_password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)


class TeacherBrief(BaseModel):
    """A teacher's name and title only, used inside other resources (e.g. a
    department's head or a course's teacher). Contains no contact details."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: str
    title: TeacherTitle


class CourseBrief(BaseModel):
    """A short course summary, used inside other resources (e.g. a department's
    course list or a student's enrollments)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    title: str
    credits: int
    teacher_id: int | None
