from typing import Annotated, Any

from fastapi import APIRouter, Depends, status

from app.core.deps import CurrentUser, DbSession, ListParams, require_roles
from app.models import User, UserRole
from app.schemas.department import (
    DepartmentCreate,
    DepartmentDetailOut,
    DepartmentListOut,
    DepartmentOut,
    DepartmentUpdate,
)
from app.services import departments as service

router = APIRouter(prefix="/departments", tags=["departments"])

AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN))]
AdminOrHod = Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.HOD))]

Responses = dict[int | str, dict[str, Any]]
NOT_FOUND: Responses = {status.HTTP_404_NOT_FOUND: {"description": "Department not found"}}
FORBIDDEN: Responses = {status.HTTP_403_FORBIDDEN: {"description": "Not allowed for your role"}}
CONFLICT: Responses = {status.HTTP_409_CONFLICT: {"description": "Duplicate code or name"}}


@router.get("", response_model=DepartmentListOut)
def list_departments(
    db: DbSession, _user: CurrentUser, params: Annotated[ListParams, Depends()]
) -> DepartmentListOut:
    """List departments. `search` matches name or code."""
    items, total = service.list_departments(db, params.search_term, params.skip, params.limit)
    return DepartmentListOut(items=[DepartmentOut.model_validate(d) for d in items], total=total)


@router.post(
    "",
    response_model=DepartmentOut,
    status_code=status.HTTP_201_CREATED,
    responses=FORBIDDEN | CONFLICT,
)
def create_department(db: DbSession, _admin: AdminUser, body: DepartmentCreate) -> Any:
    """Create a department (admin). Set its head afterwards with PATCH."""
    return service.create_department(db, body)


@router.get("/{department_id}", response_model=DepartmentDetailOut, responses=NOT_FOUND)
def get_department(db: DbSession, _user: CurrentUser, department_id: int) -> DepartmentDetailOut:
    """A department with its head, teacher/student/course counts and course list."""
    detail = service.get_department_detail(db, department_id)
    return DepartmentDetailOut(
        **DepartmentOut.model_validate(detail.department).model_dump(),
        head=detail.department.head,
        teacher_count=detail.teacher_count,
        student_count=detail.student_count,
        course_count=len(detail.courses),
        courses=detail.courses,
    )


@router.patch(
    "/{department_id}",
    response_model=DepartmentOut,
    responses=NOT_FOUND | FORBIDDEN | CONFLICT,
)
def update_department(
    db: DbSession, user: AdminOrHod, department_id: int, body: DepartmentUpdate
) -> Any:
    """Update a department. Admin: any field. HOD (own department): description,
    building and phone only."""
    return service.update_department(db, department_id, body, user)


@router.delete(
    "/{department_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=NOT_FOUND
    | FORBIDDEN
    | {status.HTTP_409_CONFLICT: {"description": "Department still has dependents"}},
)
def delete_department(db: DbSession, _admin: AdminUser, department_id: int) -> None:
    """Delete a department (admin). Blocked (409) while it has teachers, students
    or courses."""
    service.delete_department(db, department_id)
