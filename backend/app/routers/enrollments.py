from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import CurrentUser, DbSession, ListParams, require_roles
from app.models import User, UserRole
from app.schemas.enrollment import (
    SEMESTER_PATTERN,
    EnrollmentCreate,
    EnrollmentListOut,
    EnrollmentOut,
)
from app.services import enrollments as service

router = APIRouter(prefix="/enrollments", tags=["enrollments"])

AdminOrHod = Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.HOD))]

Responses = dict[int | str, dict[str, Any]]


@router.get("", response_model=EnrollmentListOut)
def list_enrollments(
    db: DbSession,
    user: CurrentUser,
    params: Annotated[ListParams, Depends()],
    student_id: Annotated[int | None, Query()] = None,
    course_id: Annotated[int | None, Query()] = None,
    semester: Annotated[str | None, Query(pattern=SEMESTER_PATTERN)] = None,
) -> EnrollmentListOut:
    """List the enrollments you may see (admin: all; HOD: own department's courses
    and own courses; teacher: own courses; student: own). `search` matches the
    student's number or name, or the course code."""
    items, total = service.list_enrollments(
        db,
        user,
        params.search_term,
        student_id,
        course_id,
        semester,
        params.skip,
        params.limit,
    )
    return EnrollmentListOut(items=[EnrollmentOut.model_validate(e) for e in items], total=total)


@router.post(
    "",
    response_model=EnrollmentOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Course outside your department"},
        status.HTTP_409_CONFLICT: {
            "description": "Student not active, already enrolled, or course full"
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Bad semester format, or unknown student or course"
        },
    },
)
def enroll(db: DbSession, user: AdminOrHod, body: EnrollmentCreate) -> Any:
    """Enroll a student in a course for a semester (admin; HOD for courses of
    their department). Only active students; no duplicates; not over capacity."""
    return service.enroll(db, body, user)


@router.delete(
    "/{enrollment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Course outside your department"},
        status.HTTP_404_NOT_FOUND: {"description": "Enrollment not found"},
    },
)
def unenroll(db: DbSession, user: AdminOrHod, enrollment_id: int) -> None:
    """Remove an enrollment (admin; HOD for courses of their department)."""
    service.unenroll(db, enrollment_id, user)
