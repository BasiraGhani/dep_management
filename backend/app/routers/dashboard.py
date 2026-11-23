from typing import Any

from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession
from app.schemas.dashboard import Dashboard
from app.services import dashboard as service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=Dashboard)
def get_dashboard(db: DbSession, user: CurrentUser) -> Any:
    """Figures for the caller's role; the `role` field says which shape it is.

    * admin: totals, students per department, recent enrollments (FR-7.1)
    * hod: the same for the department they head (FR-7.2)
    * teacher: their courses with enrolled and ungraded counts (FR-7.3)
    * student: their enrollments, grades and GPA (FR-7.4)
    """
    return service.dashboard_for(db, user)
