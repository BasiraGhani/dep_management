from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import CurrentUser, DbSession, ListParams, require_roles
from app.models import TeacherTitle, User, UserRole
from app.schemas.common import CourseBrief
from app.schemas.teacher import (
    TeacherCreate,
    TeacherDetailOut,
    TeacherListOut,
    TeacherOut,
    TeacherPublicDetailOut,
    TeacherPublicListOut,
    TeacherPublicOut,
    TeacherUpdate,
)
from app.services import teachers as service

router = APIRouter(prefix="/teachers", tags=["teachers"])

AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN))]
AdminOrHod = Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.HOD))]
Staff = Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.HOD, UserRole.TEACHER))]

Responses = dict[int | str, dict[str, Any]]
NOT_FOUND: Responses = {status.HTTP_404_NOT_FOUND: {"description": "Teacher not found"}}
FORBIDDEN: Responses = {status.HTTP_403_FORBIDDEN: {"description": "Not allowed for your role"}}
CONFLICT: Responses = {status.HTTP_409_CONFLICT: {"description": "Duplicate email or username"}}


@router.get("", response_model=TeacherListOut | TeacherPublicListOut)
def list_teachers(
    db: DbSession,
    user: CurrentUser,
    params: Annotated[ListParams, Depends()],
    department_id: Annotated[int | None, Query()] = None,
    title: Annotated[TeacherTitle | None, Query()] = None,
) -> TeacherListOut | TeacherPublicListOut:
    """List teachers. `search` matches name or email. Students see public fields only."""
    items, total = service.list_teachers(
        db, params.search_term, department_id, title, params.skip, params.limit
    )
    if user.role is UserRole.STUDENT:
        return TeacherPublicListOut(
            items=[TeacherPublicOut.model_validate(t) for t in items], total=total
        )
    return TeacherListOut(items=[TeacherOut.model_validate(t) for t in items], total=total)


@router.post(
    "",
    response_model=TeacherOut,
    status_code=status.HTTP_201_CREATED,
    responses=FORBIDDEN | CONFLICT,
)
def create_teacher(db: DbSession, user: AdminOrHod, body: TeacherCreate) -> Any:
    """Create a teacher (admin; HOD in their own department). Add `create_account`
    to also create a teacher login with a temporary password."""
    return service.create_teacher(db, body, user)


@router.get(
    "/{teacher_id}",
    response_model=TeacherDetailOut | TeacherPublicDetailOut,
    responses=NOT_FOUND,
)
def get_teacher(
    db: DbSession, user: CurrentUser, teacher_id: int
) -> TeacherDetailOut | TeacherPublicDetailOut:
    """A teacher and the courses they teach. Students see public fields only."""
    detail = service.get_teacher_detail(db, teacher_id)
    courses = [CourseBrief.model_validate(c) for c in detail.courses]
    if user.role is UserRole.STUDENT:
        public = TeacherPublicOut.model_validate(detail.teacher).model_dump()
        return TeacherPublicDetailOut(**public, courses=courses)
    full = TeacherOut.model_validate(detail.teacher).model_dump()
    return TeacherDetailOut(**full, courses=courses, user_id=detail.user_id)


@router.patch(
    "/{teacher_id}",
    response_model=TeacherOut,
    responses=NOT_FOUND | FORBIDDEN | CONFLICT,
)
def update_teacher(db: DbSession, user: Staff, teacher_id: int, body: TeacherUpdate) -> Any:
    """Update a teacher. Admin: any field. HOD: teachers of their department.
    Teacher: their own phone and email."""
    return service.update_teacher(db, teacher_id, body, user)


@router.delete(
    "/{teacher_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=NOT_FOUND
    | FORBIDDEN
    | {status.HTTP_409_CONFLICT: {"description": "Heads a department, teaches, or has an account"}},
)
def delete_teacher(db: DbSession, _admin: AdminUser, teacher_id: int) -> None:
    """Delete a teacher (admin). Blocked (409) while they head a department, teach
    a course or have a login account."""
    service.delete_teacher(db, teacher_id)
