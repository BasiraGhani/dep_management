"""Grading rules and permissions (FR-6.5, FR-6.7, REQUIREMENTS §3).

Who may grade a course's enrollments: admin, the HOD of the course's department,
and the course's own teacher. Everyone else gets 403.

Bulk grading (PUT /courses/{id}/grades) is all-or-nothing: every row is checked
before anything is written, so one bad row leaves every grade unchanged.
"""

from collections import Counter
from collections.abc import Sequence

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.permissions import managed_department_id, teaches_course
from app.models import Course, Enrollment, Grade, User, UserRole
from app.schemas.enrollment import BulkGradeItem

FORBIDDEN = "You can only grade courses you teach or courses of the department you head"


def _http(code: int, detail: str) -> HTTPException:
    return HTTPException(code, detail=detail)


def can_grade(user: User, course: Course) -> bool:
    """Admin, the HOD of the course's department, or the course's teacher."""
    return (
        user.role is UserRole.ADMIN
        or managed_department_id(user) == course.department_id
        or teaches_course(user, course.id)
    )


def set_grade(db: Session, enrollment_id: int, grade: Grade | None, user: User) -> Enrollment:
    """Set or clear (None) one enrollment's grade (FR-6.5)."""
    enrollment = db.get(Enrollment, enrollment_id)
    if enrollment is None:
        raise _http(status.HTTP_404_NOT_FOUND, "Enrollment not found")
    if not can_grade(user, enrollment.course):
        raise _http(status.HTTP_403_FORBIDDEN, FORBIDDEN)
    enrollment.grade = grade
    db.commit()
    db.refresh(enrollment)
    return enrollment


def _ids(ids: Sequence[int]) -> str:
    return ", ".join(str(i) for i in sorted(ids))


def set_course_grades(
    db: Session, course_id: int, items: Sequence[BulkGradeItem], user: User
) -> list[Enrollment]:
    """Set the grades of several enrollments of one course at once (FR-6.7).

    All-or-nothing: 422 (and no change) if an enrollment appears twice, or does
    not exist or belongs to another course. Returns the updated enrollments in
    the order they were sent.
    """
    course = db.get(Course, course_id)
    if course is None:
        raise _http(status.HTTP_404_NOT_FOUND, "Course not found")
    if not can_grade(user, course):
        raise _http(status.HTTP_403_FORBIDDEN, FORBIDDEN)

    repeated = [i for i, n in Counter(item.enrollment_id for item in items).items() if n > 1]
    if repeated:
        raise _http(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Enrollments listed more than once: {_ids(repeated)}",
        )

    wanted = {item.enrollment_id for item in items}
    found = {
        e.id: e
        for e in db.scalars(
            select(Enrollment)
            .where(Enrollment.id.in_(wanted), Enrollment.course_id == course.id)
            .options(joinedload(Enrollment.student), joinedload(Enrollment.course))
        )
    }
    missing = wanted - found.keys()
    if missing:
        raise _http(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Not enrollments of course {course.code}: {_ids(list(missing))}. "
            "No grades were changed.",
        )

    for item in items:
        found[item.enrollment_id].grade = item.grade
    db.commit()
    return [found[item.enrollment_id] for item in items]
