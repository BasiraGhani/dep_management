from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.deps import DbSession, require_roles
from app.models import StudentStatus, TeacherTitle, User, UserRole
from app.services import export as service
from app.services.export import ExportResource

router = APIRouter(prefix="/export", tags=["export"])

AdminOrHod = Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.HOD))]


@router.get(
    "/{resource}.csv",
    response_class=Response,
    responses={
        status.HTTP_200_OK: {"content": {"text/csv": {}}, "description": "CSV with a header row"},
        status.HTTP_403_FORBIDDEN: {"description": "Admins and heads of department only"},
    },
)
def export_csv(
    db: DbSession,
    user: AdminOrHod,
    resource: ExportResource,
    search: Annotated[str | None, Query(max_length=100)] = None,
    department_id: Annotated[int | None, Query()] = None,
    year: Annotated[int | None, Query(ge=1, le=6)] = None,
    status_: Annotated[StudentStatus | None, Query(alias="status")] = None,
    title: Annotated[TeacherTitle | None, Query()] = None,
    teacher_id: Annotated[int | None, Query()] = None,
) -> Response:
    """Download the students, teachers or courses list as CSV, with the same filters
    as the list endpoint (FR-9.1). Admin: all rows; HOD: their department only.

    Filters that don't apply to the resource are ignored (students: search,
    department_id, year, status; teachers: search, department_id, title;
    courses: search, department_id, teacher_id).
    """
    content = service.export_csv(
        db,
        user,
        resource,
        search=(search or "").strip() or None,
        department_id=department_id,
        year=year,
        status_=status_,
        title=title,
        teacher_id=teacher_id,
    )
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{resource.value}.csv"'},
    )
