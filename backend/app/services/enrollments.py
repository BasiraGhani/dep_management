"""Enrollment rules and permissions (FR-6.1–FR-6.4, BR-4, BR-5, REQUIREMENTS §3).

Who sees which enrollments (Enrollments row of the permission matrix):
* admin: all
* hod: enrollments in courses of the department they head, and in courses they teach
* teacher: enrollments in courses they teach
* student: their own

Writes (enroll, unenroll): admin anywhere; HOD for courses of their department.

Enrolling checks, in this order: the course exists (422), the user may manage
it (403), the student exists (422), the student is active (BR-4, 409), they
aren't already enrolled in that course and semester (FR-6.2, 409), and the course
has room in that semester (BR-5, 409).
"""

from fastapi import HTTPException, status
from sqlalchemy import ColumnElement, false, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.permissions import managed_department_id
from app.models import Course, Enrollment, Student, StudentStatus, User, UserRole
from app.schemas.enrollment import EnrollmentCreate
from app.services.common import LIKE_ESCAPE, contains_pattern


def _http(code: int, detail: str) -> HTTPException:
    return HTTPException(code, detail=detail)


def _manages(user: User, course: Course) -> bool:
    """Admin, or the HOD of the course's department."""
    return user.role is UserRole.ADMIN or managed_department_id(user) == course.department_id


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------


def _visibility_filter(user: User) -> ColumnElement[bool] | None:
    """SQL condition for the enrollments `user` may see; None means no restriction.

    Applied to a query that joins Course.
    """
    if user.role is UserRole.ADMIN:
        return None
    if user.role is UserRole.STUDENT:
        return Enrollment.student_id == user.student_id if user.student_id else false()
    conditions: list[ColumnElement[bool]] = []
    if user.teacher_id is not None:
        conditions.append(Course.teacher_id == user.teacher_id)
    department_id = managed_department_id(user)
    if department_id is not None:
        conditions.append(Course.department_id == department_id)
    return or_(*conditions) if conditions else false()


def list_enrollments(
    db: Session,
    user: User,
    search: str | None,
    student_id: int | None,
    course_id: int | None,
    semester: str | None,
    skip: int,
    limit: int,
) -> tuple[list[Enrollment], int]:
    """A page of the enrollments `user` may see, newest first, plus the total.

    `search` matches the student's number or name, or the course code.
    """
    query = (
        select(Enrollment)
        .join(Course, Course.id == Enrollment.course_id)
        .join(Student, Student.id == Enrollment.student_id)
    )
    visible = _visibility_filter(user)
    if visible is not None:
        query = query.where(visible)
    if search:
        pattern = contains_pattern(search)
        full_name = Student.first_name + " " + Student.last_name
        columns = (
            Student.student_no,
            Student.first_name,
            Student.last_name,
            full_name,
            Course.code,
        )
        query = query.where(or_(*(c.ilike(pattern, escape=LIKE_ESCAPE) for c in columns)))
    if student_id is not None:
        query = query.where(Enrollment.student_id == student_id)
    if course_id is not None:
        query = query.where(Enrollment.course_id == course_id)
    if semester is not None:
        query = query.where(Enrollment.semester == semester)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    page = (
        query.options(joinedload(Enrollment.student), joinedload(Enrollment.course))
        .order_by(Enrollment.id.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(page).all()), total


# ---------------------------------------------------------------------------
# Capacity (BR-5)
# ---------------------------------------------------------------------------


def enrolled_count(db: Session, course_id: int, semester: str) -> int:
    """How many students are enrolled in a course in a semester."""
    query = (
        select(func.count())
        .select_from(Enrollment)
        .where(Enrollment.course_id == course_id, Enrollment.semester == semester)
    )
    return db.scalar(query) or 0


def busiest_semester_count(db: Session, course_id: int) -> int:
    """The highest number of students enrolled in the course in any one semester."""
    per_semester = (
        select(func.count().label("n"))
        .where(Enrollment.course_id == course_id)
        .group_by(Enrollment.semester)
        .subquery()
    )
    return db.scalar(select(func.max(per_semester.c.n))) or 0


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------


def enroll(db: Session, data: EnrollmentCreate, user: User) -> Enrollment:
    """Enroll a student in a course for a semester (FR-6.1); see the module
    docstring for the checks and their order."""
    course = db.get(Course, data.course_id)
    if course is None:
        raise _http(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"Course {data.course_id} does not exist"
        )
    if not _manages(user, course):
        raise _http(
            status.HTTP_403_FORBIDDEN,
            "You can only enroll students in courses of the department you head",
        )
    student = db.get(Student, data.student_id)
    if student is None:
        raise _http(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"Student {data.student_id} does not exist"
        )
    name = f"{student.first_name} {student.last_name} ({student.student_no})"

    if student.status is not StudentStatus.ACTIVE:
        raise _http(
            status.HTTP_409_CONFLICT,
            f"{name} is {student.status.value}; only active students can be enrolled",
        )
    duplicate = db.scalar(
        select(Enrollment.id).where(
            Enrollment.student_id == student.id,
            Enrollment.course_id == course.id,
            Enrollment.semester == data.semester,
        )
    )
    if duplicate is not None:
        raise _http(
            status.HTTP_409_CONFLICT,
            f"{name} is already enrolled in {course.code} for {data.semester}",
        )
    taken = enrolled_count(db, course.id, data.semester)
    if taken >= course.capacity:
        raise _http(
            status.HTTP_409_CONFLICT,
            f"{course.code} is full for {data.semester} ({taken} / {course.capacity})",
        )

    enrollment = Enrollment(student_id=student.id, course_id=course.id, semester=data.semester)
    db.add(enrollment)
    try:
        db.commit()
    except IntegrityError as exc:  # a concurrent duplicate slipped past the check
        db.rollback()
        raise _http(
            status.HTTP_409_CONFLICT,
            f"{name} is already enrolled in {course.code} for {data.semester}",
        ) from exc
    db.refresh(enrollment)
    return enrollment


def unenroll(db: Session, enrollment_id: int, user: User) -> None:
    """Remove an enrollment (admin; HOD for courses of their department)."""
    enrollment = db.get(Enrollment, enrollment_id)
    if enrollment is None:
        raise _http(status.HTTP_404_NOT_FOUND, "Enrollment not found")
    if not _manages(user, enrollment.course):
        raise _http(
            status.HTTP_403_FORBIDDEN,
            "You can only unenroll students from courses of the department you head",
        )
    db.delete(enrollment)
    db.commit()
