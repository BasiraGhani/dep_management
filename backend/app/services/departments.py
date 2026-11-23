"""Department rules and permissions (FR-2, BR-1, BR-3, BR-7, REQUIREMENTS §3).

Who may do what:
* read (list, detail): every authenticated user
* create, delete: admin (the router enforces the role)
* update: admin, any field; a HOD, only description / building / phone of the
  department they head (decision recorded for T3.1)
"""

from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.permissions import can_manage_department
from app.models import Course, Department, Student, Teacher, User, UserRole
from app.schemas.department import DepartmentCreate, DepartmentUpdate
from app.services.common import LIKE_ESCAPE, contains_pattern

HOD_EDITABLE_FIELDS = frozenset({"description", "building", "phone"})


@dataclass(frozen=True)
class DepartmentDetail:
    """A department with what its detail view shows (FR-2.3)."""

    department: Department
    teacher_count: int
    student_count: int
    courses: list[Course]


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------


def list_departments(
    db: Session, search: str | None, skip: int, limit: int
) -> tuple[list[Department], int]:
    """A page of departments ordered by code, plus the total matching `search`
    (case-insensitive, in name or code)."""
    query = select(Department)
    if search:
        pattern = contains_pattern(search)
        query = query.where(
            or_(
                Department.name.ilike(pattern, escape=LIKE_ESCAPE),
                Department.code.ilike(pattern, escape=LIKE_ESCAPE),
            )
        )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(query.order_by(Department.code).offset(skip).limit(limit)).all()
    return list(items), total


def get_department(db: Session, department_id: int) -> Department:
    """The department, or 404."""
    department = db.get(Department, department_id)
    if department is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Department not found")
    return department


def _count(db: Session, model: type[Teacher | Student | Course], department_id: int) -> int:
    query = select(func.count()).select_from(model).where(model.department_id == department_id)
    return db.scalar(query) or 0


def get_department_detail(db: Session, department_id: int) -> DepartmentDetail:
    """The department with its counts and course list, or 404."""
    department = get_department(db, department_id)
    courses = db.scalars(
        select(Course).where(Course.department_id == department_id).order_by(Course.code)
    ).all()
    return DepartmentDetail(
        department=department,
        teacher_count=_count(db, Teacher, department_id),
        student_count=_count(db, Student, department_id),
        courses=list(courses),
    )


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, detail=detail)


def _ensure_unique(
    db: Session, code: str | None, name: str | None, exclude_id: int | None = None
) -> None:
    """409 if another department already uses this code or name (BR-1).

    Codes are compared case-insensitively (they are stored uppercase).
    """
    others = select(Department)
    if exclude_id is not None:
        others = others.where(Department.id != exclude_id)
    if code is not None and db.scalar(others.where(Department.code == code.upper())):
        raise _conflict(f"A department with code {code.upper()!r} already exists")
    if name is not None and db.scalar(others.where(Department.name == name)):
        raise _conflict(f"A department named {name!r} already exists")


def _check_head(db: Session, department: Department, head_id: int) -> None:
    """422 unless `head_id` is a teacher in this department (BR-3)."""
    teacher = db.get(Teacher, head_id)
    if teacher is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"Teacher {head_id} does not exist"
        )
    if teacher.department_id != department.id:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The head must be a teacher in this department",
        )


def _commit(db: Session) -> None:
    """Commit; a uniqueness race that slipped past the checks becomes a 409."""
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise _conflict("A department with this code or name already exists") from exc


def create_department(db: Session, data: DepartmentCreate) -> Department:
    """Create a department (admin; FR-2.1). 409 on a duplicate code or name."""
    _ensure_unique(db, data.code, data.name)
    department = Department(**data.model_dump())
    db.add(department)
    _commit(db)
    return department


def _check_update_allowed(user: User, department: Department, data: DepartmentUpdate) -> None:
    """403 unless the user may make this particular change."""
    if user.role is UserRole.ADMIN:
        return
    if user.role is UserRole.HOD and can_manage_department(user, department.id):
        forbidden = data.model_fields_set - HOD_EDITABLE_FIELDS
        if forbidden:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="A head of department can only change description, building and phone "
                f"(not {', '.join(sorted(forbidden))})",
            )
        return
    raise HTTPException(
        status.HTTP_403_FORBIDDEN, detail="You can only edit the department you head"
    )


def update_department(
    db: Session, department_id: int, data: DepartmentUpdate, user: User
) -> Department:
    """Apply a partial update (FR-2.1); see the module docstring for who may change what."""
    department = get_department(db, department_id)
    _check_update_allowed(user, department, data)

    changes = data.model_dump(exclude_unset=True)
    _ensure_unique(db, changes.get("code"), changes.get("name"), exclude_id=department.id)
    if changes.get("head_id") is not None:
        _check_head(db, department, changes["head_id"])

    for field, value in changes.items():
        setattr(department, field, value)
    _commit(db)
    return department


def delete_department(db: Session, department_id: int) -> None:
    """Delete a department (admin). 409 while it has teachers, students or courses
    (FR-2.4, BR-7), with a message saying what is left."""
    department = get_department(db, department_id)
    dependents = {
        "teacher": _count(db, Teacher, department_id),
        "student": _count(db, Student, department_id),
        "course": _count(db, Course, department_id),
    }
    remaining = [f"{n} {kind}{'s' if n != 1 else ''}" for kind, n in dependents.items() if n]
    if remaining:
        raise _conflict(
            f"Department {department.code} can't be deleted while it has "
            f"{', '.join(remaining)}. Move or delete them first."
        )
    db.delete(department)
    db.commit()
