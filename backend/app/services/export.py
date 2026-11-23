"""CSV export of the students, teachers and courses lists (FR-9.1).

* who: admin (all rows) or a HOD (only the department they head: user decision)
* rows: the same filters as the list endpoints, in the same order, not paginated
* cells that a spreadsheet would run as a formula (=, @, +, - not followed by a
  plain number) are prefixed with a quote (CSV injection, OWASP)
"""

import csv
import enum
import io
import re
from collections.abc import Callable, Iterable, Sequence
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.permissions import managed_department_id
from app.models import Course, Student, StudentStatus, Teacher, TeacherTitle, User, UserRole
from app.services.courses import courses_query
from app.services.students import students_query
from app.services.teachers import teachers_query

FORMULA_START = ("=", "@", "+", "-", "\t", "\r")
PLAIN_NUMBER = re.compile(r"[+-]?[0-9 ()\-.]+")


class ExportResource(enum.StrEnum):
    STUDENTS = "students"
    TEACHERS = "teachers"
    COURSES = "courses"


def safe_cell(value: object) -> str:
    """The value as CSV text, neutralised if a spreadsheet would treat it as a formula."""
    if value is None:
        return ""
    text = value.isoformat() if isinstance(value, date) else str(value)
    if text.startswith(FORMULA_START) and not PLAIN_NUMBER.fullmatch(text):
        return "'" + text
    return text


def _to_csv(header: Sequence[str], rows: Iterable[Sequence[object]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(header)
    writer.writerows([safe_cell(v) for v in row] for row in rows)
    return buffer.getvalue()


STUDENT_HEADER = (
    "id", "student_no", "first_name", "last_name", "email", "phone",
    "date_of_birth", "department", "year", "status", "enrollment_date",
)  # fmt: skip
TEACHER_HEADER = (
    "id", "first_name", "last_name", "email", "phone", "title", "department", "hire_date",
)  # fmt: skip
COURSE_HEADER = (
    "id", "code", "title", "credits", "capacity", "department", "teacher",
)  # fmt: skip


def _student_row(s: Student) -> tuple[object, ...]:
    return (
        s.id, s.student_no, s.first_name, s.last_name, s.email, s.phone,
        s.date_of_birth, s.department.code, s.year, s.status.value, s.enrollment_date,
    )  # fmt: skip


def _teacher_row(t: Teacher) -> tuple[object, ...]:
    return (
        t.id, t.first_name, t.last_name, t.email, t.phone, t.title.value,
        t.department.code, t.hire_date,
    )  # fmt: skip


def _course_row(c: Course) -> tuple[object, ...]:
    teacher = f"{c.teacher.first_name} {c.teacher.last_name}" if c.teacher else ""
    return (c.id, c.code, c.title, c.credits, c.capacity, c.department.code, teacher)


def export_csv(
    db: Session,
    user: User,
    resource: ExportResource,
    search: str | None = None,
    department_id: int | None = None,
    year: int | None = None,
    status_: StudentStatus | None = None,
    title: TeacherTitle | None = None,
    teacher_id: int | None = None,
) -> str:
    """The resource's list as CSV text with a header row.

    Filters that don't apply to the resource (e.g. `year` for courses) are ignored.
    """
    own_department: int | None = None
    if user.role is not UserRole.ADMIN:
        own_department = managed_department_id(user)
        if own_department is None:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="You can only export the department you head",
            )

    header: Sequence[str]
    rows: Iterable[tuple[object, ...]]
    to_row: Callable[..., tuple[object, ...]]
    if resource is ExportResource.STUDENTS:
        query = students_query(user, search, department_id, year, status_).options(
            joinedload(Student.department)
        )
        if own_department is not None:
            query = query.where(Student.department_id == own_department)
        order = (Student.last_name, Student.first_name, Student.id)
        header, to_row = STUDENT_HEADER, _student_row
        rows = (to_row(s) for s in db.scalars(query.order_by(*order)))
    elif resource is ExportResource.TEACHERS:
        query_t = teachers_query(search, department_id, title).options(
            joinedload(Teacher.department)
        )
        if own_department is not None:
            query_t = query_t.where(Teacher.department_id == own_department)
        order_t = (Teacher.last_name, Teacher.first_name, Teacher.id)
        header, to_row = TEACHER_HEADER, _teacher_row
        rows = (to_row(t) for t in db.scalars(query_t.order_by(*order_t)))
    else:
        query_c = courses_query(search, department_id, teacher_id).options(
            joinedload(Course.department), joinedload(Course.teacher)
        )
        if own_department is not None:
            query_c = query_c.where(Course.department_id == own_department)
        header, to_row = COURSE_HEADER, _course_row
        rows = (to_row(c) for c in db.scalars(query_c.order_by(Course.code)))
    return _to_csv(header, rows)
