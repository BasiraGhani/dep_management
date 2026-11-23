"""Teacher rules and permissions (FR-3, BR-1, BR-2, BR-3, BR-7, REQUIREMENTS §3).

Who may do what:
* read (list, detail): everyone; students get public fields only (the router
  picks the schema)
* create: admin anywhere; HOD only in the department they head
* update: admin any field; HOD teachers of their department, without moving them
  elsewhere; a teacher their own phone and email
* delete: admin; 409 while the teacher heads a department, teaches a course or
  has a login account (decision for T3.2)
"""

from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.permissions import can_manage_department
from app.core.security import hash_password
from app.models import Course, Department, Teacher, TeacherTitle, User, UserRole
from app.schemas.common import AccountCreate
from app.schemas.teacher import TeacherCreate, TeacherUpdate
from app.services.common import LIKE_ESCAPE, contains_pattern

SELF_EDITABLE_FIELDS = frozenset({"phone", "email"})


@dataclass(frozen=True)
class TeacherDetail:
    teacher: Teacher
    courses: list[Course]
    user_id: int | None


def _http(code: int, detail: str) -> HTTPException:
    return HTTPException(code, detail=detail)


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------


def list_teachers(
    db: Session,
    search: str | None,
    department_id: int | None,
    title: TeacherTitle | None,
    skip: int,
    limit: int,
) -> tuple[list[Teacher], int]:
    """A page of teachers ordered by last then first name, plus the total.

    `search` matches first name, last name, "first last" or email (any case).
    """
    query = select(Teacher)
    if search:
        pattern = contains_pattern(search)
        full_name = Teacher.first_name + " " + Teacher.last_name
        query = query.where(
            or_(
                *(
                    column.ilike(pattern, escape=LIKE_ESCAPE)
                    for column in (Teacher.first_name, Teacher.last_name, full_name, Teacher.email)
                )
            )
        )
    if department_id is not None:
        query = query.where(Teacher.department_id == department_id)
    if title is not None:
        query = query.where(Teacher.title == title)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    order = (Teacher.last_name, Teacher.first_name, Teacher.id)
    items = db.scalars(query.order_by(*order).offset(skip).limit(limit)).all()
    return list(items), total


def get_teacher(db: Session, teacher_id: int) -> Teacher:
    """The teacher, or 404."""
    teacher = db.get(Teacher, teacher_id)
    if teacher is None:
        raise _http(status.HTTP_404_NOT_FOUND, "Teacher not found")
    return teacher


def get_teacher_detail(db: Session, teacher_id: int) -> TeacherDetail:
    """The teacher with the courses they teach and their account id, or 404."""
    teacher = get_teacher(db, teacher_id)
    courses = db.scalars(
        select(Course).where(Course.teacher_id == teacher_id).order_by(Course.code)
    ).all()
    user_id = db.scalar(select(User.id).where(User.teacher_id == teacher_id))
    return TeacherDetail(teacher=teacher, courses=list(courses), user_id=user_id)


# ---------------------------------------------------------------------------
# Checks used by writes
# ---------------------------------------------------------------------------


def _require_department(db: Session, department_id: int) -> Department:
    department = db.get(Department, department_id)
    if department is None:
        raise _http(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"Department {department_id} does not exist"
        )
    return department


def _ensure_email_free(db: Session, email: str, exclude_id: int | None = None) -> None:
    query = select(Teacher.id).where(Teacher.email == email.strip().lower())
    if exclude_id is not None:
        query = query.where(Teacher.id != exclude_id)
    if db.scalar(query) is not None:
        raise _http(status.HTTP_409_CONFLICT, f"A teacher with email {email!r} already exists")


def _ensure_username_free(db: Session, username: str) -> None:
    if db.scalar(select(User.id).where(User.username == username.strip().lower())) is not None:
        raise _http(status.HTTP_409_CONFLICT, f"Username {username!r} is already taken")


def _headed_department(db: Session, teacher: Teacher) -> Department | None:
    return db.scalar(select(Department).where(Department.head_id == teacher.id))


def _course_count(db: Session, teacher: Teacher) -> int:
    query = select(func.count()).select_from(Course).where(Course.teacher_id == teacher.id)
    return db.scalar(query) or 0


def _commit(db: Session) -> None:
    """Commit; a uniqueness race that slipped past the checks becomes a 409."""
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise _http(
            status.HTTP_409_CONFLICT, "A teacher with this email, or this username, already exists"
        ) from exc


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


def _create_account(db: Session, teacher: Teacher, account: AccountCreate) -> None:
    db.add(
        User(
            username=account.username,
            password_hash=hash_password(account.temp_password),
            role=UserRole.TEACHER,
            teacher_id=teacher.id,
        )
    )


def create_teacher(db: Session, data: TeacherCreate, user: User) -> Teacher:
    """Create a teacher, optionally with a teacher login account (FR-3.1, FR-3.3)."""
    if user.role is not UserRole.ADMIN and not can_manage_department(user, data.department_id):
        raise _http(
            status.HTTP_403_FORBIDDEN, "You can only add teachers to the department you head"
        )
    _require_department(db, data.department_id)
    _ensure_email_free(db, data.email)
    if data.create_account is not None:
        _ensure_username_free(db, data.create_account.username)

    teacher = Teacher(**data.model_dump(exclude={"create_account"}))
    db.add(teacher)
    db.flush()
    if data.create_account is not None:
        _create_account(db, teacher, data.create_account)
    _commit(db)
    return teacher


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


def _check_update_allowed(user: User, teacher: Teacher, data: TeacherUpdate) -> None:
    fields = data.model_fields_set
    if user.role is UserRole.ADMIN:
        return
    if user.role is UserRole.HOD and can_manage_department(user, teacher.department_id):
        moving = "department_id" in fields and data.department_id != teacher.department_id
        if moving:
            raise _http(
                status.HTTP_403_FORBIDDEN,
                "A head of department can't move teachers to another department",
            )
        return
    if user.teacher_id == teacher.id and user.role in (UserRole.TEACHER, UserRole.HOD):
        not_allowed = fields - SELF_EDITABLE_FIELDS
        if not_allowed:
            raise _http(
                status.HTTP_403_FORBIDDEN,
                "You can only change your own phone and email "
                f"(not {', '.join(sorted(not_allowed))})",
            )
        return
    raise _http(status.HTTP_403_FORBIDDEN, "You can't edit this teacher")


def _check_department_move(db: Session, teacher: Teacher, new_department_id: int) -> None:
    """A move must keep BR-2 and BR-3 true: no headed department, no courses."""
    _require_department(db, new_department_id)
    headed = _headed_department(db, teacher)
    if headed is not None:
        raise _http(
            status.HTTP_409_CONFLICT,
            f"This teacher heads department {headed.code}; appoint another head first",
        )
    courses = _course_count(db, teacher)
    if courses:
        raise _http(
            status.HTTP_409_CONFLICT,
            f"This teacher teaches {courses} course{'s' if courses != 1 else ''} in their "
            "current department; reassign them first",
        )


def update_teacher(db: Session, teacher_id: int, data: TeacherUpdate, user: User) -> Teacher:
    """Apply a partial update; see the module docstring for who may change what."""
    teacher = get_teacher(db, teacher_id)
    _check_update_allowed(user, teacher, data)

    changes = data.model_dump(exclude_unset=True)
    if "email" in changes:
        _ensure_email_free(db, changes["email"], exclude_id=teacher.id)
    new_department = changes.get("department_id")
    if new_department is not None and new_department != teacher.department_id:
        _check_department_move(db, teacher, new_department)

    for field, value in changes.items():
        setattr(teacher, field, value)
    _commit(db)
    return teacher


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


def delete_teacher(db: Session, teacher_id: int) -> None:
    """Delete a teacher (admin). 409 with every reason that blocks it (FR-3.4, BR-7)."""
    teacher = get_teacher(db, teacher_id)
    reasons = []
    headed = _headed_department(db, teacher)
    if headed is not None:
        reasons.append(f"head department {headed.code}")
    courses = _course_count(db, teacher)
    if courses:
        reasons.append(f"teach {courses} course{'s' if courses != 1 else ''}")
    if db.scalar(select(User.id).where(User.teacher_id == teacher.id)) is not None:
        reasons.append("have a login account (deactivate or delete it first)")
    if reasons:
        raise _http(
            status.HTTP_409_CONFLICT,
            f"Teacher can't be deleted: they {' and '.join(reasons)}",
        )
    db.delete(teacher)
    db.commit()
