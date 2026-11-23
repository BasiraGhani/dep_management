"""GET /dashboard response schemas, one per role (FR-7.1–FR-7.4).

The response is a union with `role` as the discriminator, so clients (and the
generated OpenAPI docs) can tell which shape they received.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.schemas.common import CourseBrief
from app.schemas.enrollment import EnrollmentOut
from app.schemas.student import StudentEnrollmentOut


class Totals(BaseModel):
    departments: int
    teachers: int
    students: int
    courses: int


class DepartmentStudents(BaseModel):
    """One bar of the "students per department" chart."""

    department_id: int
    code: str
    name: str
    students: int


class DepartmentRef(BaseModel):
    id: int
    code: str
    name: str


class AdminDashboard(BaseModel):
    """FR-7.1: everything, across all departments."""

    role: Literal["admin"] = "admin"
    totals: Totals
    students_per_department: list[DepartmentStudents]
    recent_enrollments: list[EnrollmentOut]


class HodDashboard(BaseModel):
    """FR-7.2: the admin figures for the department the HOD heads.

    `department` is null (and every figure zero) if the account no longer heads
    a department.
    """

    role: Literal["hod"] = "hod"
    department: DepartmentRef | None
    totals: Totals
    students_per_department: list[DepartmentStudents]
    recent_enrollments: list[EnrollmentOut]


class TeacherCourseStats(BaseModel):
    """FR-7.3: one of the teacher's courses, counted over all semesters."""

    course: CourseBrief
    capacity: int
    enrolled: int
    ungraded: int


class TeacherDashboard(BaseModel):
    role: Literal["teacher"] = "teacher"
    courses: list[TeacherCourseStats]


class StudentDashboard(BaseModel):
    """FR-7.4: the student's enrollments with grades, and their GPA."""

    role: Literal["student"] = "student"
    enrollments: list[StudentEnrollmentOut]
    gpa: float | None
    graded_credits: int


Dashboard = Annotated[
    AdminDashboard | HodDashboard | TeacherDashboard | StudentDashboard,
    Field(discriminator="role"),
]
