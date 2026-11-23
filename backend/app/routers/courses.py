from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Query, status

from app.core.deps import CurrentUser, DbSession, ListParams, require_roles
from app.models import User, UserRole
from app.schemas.course import (
    CourseCreate,
    CourseDetailOut,
    CourseListOut,
    CourseOut,
    CourseUpdate,
    RosterEntry,
)
from app.schemas.enrollment import BulkGradeItem, EnrollmentOut
from app.services import courses as service
from app.services import grades as grades_service

router = APIRouter(prefix="/courses", tags=["courses"])

AdminOrHod = Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.HOD))]
Staff = Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.HOD, UserRole.TEACHER))]

Responses = dict[int | str, dict[str, Any]]
NOT_FOUND: Responses = {status.HTTP_404_NOT_FOUND: {"description": "Course not found"}}
FORBIDDEN: Responses = {status.HTTP_403_FORBIDDEN: {"description": "Outside your scope"}}
CONFLICT: Responses = {status.HTTP_409_CONFLICT: {"description": "Duplicate course code"}}
BR2: Responses = {
    status.HTTP_422_UNPROCESSABLE_CONTENT: {
        "description": "Invalid fields, or a teacher from another department (BR-2)"
    }
}


@router.get("", response_model=CourseListOut)
def list_courses(
    db: DbSession,
    _user: CurrentUser,
    params: Annotated[ListParams, Depends()],
    department_id: Annotated[int | None, Query()] = None,
    teacher_id: Annotated[int | None, Query()] = None,
) -> CourseListOut:
    """List courses. `search` matches code or title."""
    items, total = service.list_courses(
        db, params.search_term, department_id, teacher_id, params.skip, params.limit
    )
    return CourseListOut(items=[CourseOut.model_validate(c) for c in items], total=total)


@router.post(
    "",
    response_model=CourseOut,
    status_code=status.HTTP_201_CREATED,
    responses=FORBIDDEN | CONFLICT | BR2,
)
def create_course(db: DbSession, user: AdminOrHod, body: CourseCreate) -> Any:
    """Create a course (admin; HOD in their own department). The teacher must
    belong to the course's department."""
    return service.create_course(db, body, user)


@router.get("/{course_id}", response_model=CourseDetailOut, responses=NOT_FOUND)
def get_course(db: DbSession, user: CurrentUser, course_id: int) -> CourseDetailOut:
    """A course with its teacher and, for staff allowed to see it, the roster of
    enrolled students with grades. `roster` is null otherwise (e.g. students)."""
    detail = service.get_course_detail(db, course_id, user)
    roster = (
        None
        if detail.roster is None
        else [
            RosterEntry(
                enrollment_id=e.id,
                student_id=e.student_id,
                student_no=e.student.student_no,
                first_name=e.student.first_name,
                last_name=e.student.last_name,
                semester=e.semester,
                grade=e.grade,
            )
            for e in detail.roster
        ]
    )
    return CourseDetailOut(
        **CourseOut.model_validate(detail.course).model_dump(),
        teacher=detail.course.teacher,
        roster=roster,
    )


@router.patch(
    "/{course_id}",
    response_model=CourseOut,
    responses=NOT_FOUND | FORBIDDEN | CONFLICT | BR2,
)
def update_course(db: DbSession, user: Staff, course_id: int, body: CourseUpdate) -> Any:
    """Update a course. Admin: any field. HOD: courses of their department.
    Teacher: only the description of a course they teach."""
    return service.update_course(db, course_id, body, user)


@router.delete(
    "/{course_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=NOT_FOUND
    | FORBIDDEN
    | {status.HTTP_409_CONFLICT: {"description": "Course has enrollments"}},
)
def delete_course(db: DbSession, user: AdminOrHod, course_id: int) -> None:
    """Delete a course (admin; HOD in their department). Blocked (409) while it
    has enrollments."""
    service.delete_course(db, course_id, user)


@router.put(
    "/{course_id}/grades",
    response_model=list[EnrollmentOut],
    responses=NOT_FOUND
    | FORBIDDEN
    | {
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Bad grade, repeated row, or enrollment not in this course"
        }
    },
)
def set_course_grades(
    db: DbSession,
    user: Staff,
    course_id: int,
    items: Annotated[list[BulkGradeItem], Body(min_length=1, max_length=1000)],
) -> Any:
    """Set many grades of one course at once (bulk grade entry). All-or-nothing:
    if any row is invalid, no grade is changed."""
    return grades_service.set_course_grades(db, course_id, items, user)
