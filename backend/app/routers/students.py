from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import CurrentUser, DbSession, ListParams, require_roles
from app.models import StudentStatus, User, UserRole
from app.schemas.student import (
    StudentCreate,
    StudentDetailOut,
    StudentEnrollmentOut,
    StudentListOut,
    StudentOut,
    StudentUpdate,
)
from app.services import students as service

router = APIRouter(prefix="/students", tags=["students"])

Staff = Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.HOD, UserRole.TEACHER))]
AdminOrHod = Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.HOD))]
Editor = Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.HOD, UserRole.STUDENT))]

Responses = dict[int | str, dict[str, Any]]
NOT_FOUND: Responses = {status.HTTP_404_NOT_FOUND: {"description": "Student not found"}}
FORBIDDEN: Responses = {status.HTTP_403_FORBIDDEN: {"description": "Outside your scope"}}
CONFLICT: Responses = {
    status.HTTP_409_CONFLICT: {"description": "Duplicate student number, email or username"}
}


@router.get("", response_model=StudentListOut, responses=FORBIDDEN)
def list_students(
    db: DbSession,
    user: Staff,
    params: Annotated[ListParams, Depends()],
    department_id: Annotated[int | None, Query()] = None,
    year: Annotated[int | None, Query(ge=1, le=6)] = None,
    status_: Annotated[StudentStatus | None, Query(alias="status")] = None,
) -> StudentListOut:
    """List the students you may see (admin: all; HOD: own department and own
    courses; teacher: own courses). `search` matches name, email or student number."""
    items, total = service.list_students(
        db,
        user,
        params.search_term,
        department_id,
        year,
        status_,
        params.skip,
        params.limit,
    )
    return StudentListOut(items=[StudentOut.model_validate(s) for s in items], total=total)


@router.post(
    "",
    response_model=StudentOut,
    status_code=status.HTTP_201_CREATED,
    responses=FORBIDDEN | CONFLICT,
)
def create_student(db: DbSession, user: AdminOrHod, body: StudentCreate) -> Any:
    """Create a student (admin; HOD in their own department). Add `create_account`
    to also create a student login with a temporary password."""
    return service.create_student(db, body, user)


@router.get("/{student_id}", response_model=StudentDetailOut, responses=NOT_FOUND | FORBIDDEN)
def get_student(db: DbSession, user: CurrentUser, student_id: int) -> StudentDetailOut:
    """A student with their enrollments. Students can only read their own record."""
    detail = service.get_student_detail(db, student_id, user)
    return StudentDetailOut(
        **StudentOut.model_validate(detail.student).model_dump(),
        enrollments=[StudentEnrollmentOut.model_validate(e) for e in detail.enrollments],
        user_id=detail.user_id,
    )


@router.patch(
    "/{student_id}",
    response_model=StudentOut,
    responses=NOT_FOUND | FORBIDDEN | CONFLICT,
)
def update_student(db: DbSession, user: Editor, student_id: int, body: StudentUpdate) -> Any:
    """Update a student. Admin: any field. HOD: students of their department.
    Student: their own phone and email."""
    return service.update_student(db, student_id, body, user)


@router.delete(
    "/{student_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=NOT_FOUND
    | FORBIDDEN
    | {status.HTTP_409_CONFLICT: {"description": "Student has a login account"}},
)
def delete_student(db: DbSession, user: AdminOrHod, student_id: int) -> None:
    """Delete a student and their enrollments (admin; HOD in their department).
    Blocked (409) while the student has a login account."""
    service.delete_student(db, student_id, user)
