"""User account management (FR-8, ARCHITECTURE §2 link rules, BR-6). Admin only.

Every create and update is checked as the account will look afterwards:

1. links match the role (§2): admin none; hod/teacher only `teacher_id`;
   student only `student_id`                                         -> 422
2. linked records exist                                              -> 422
3. a teacher/student has at most one account                         -> 409
4. BR-6: `hod` only for a teacher who heads a department, and a head's
   account must be `hod` (user decision, T4.4)                       -> 422

Admins can't deactivate, demote or delete their own account (403), so the
system can't be left without a working admin by accident.
"""

import secrets

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.security import hash_password
from app.models import Department, Student, Teacher, User, UserRole
from app.schemas.user import UserCreate, UserUpdate
from app.services.common import LIKE_ESCAPE, contains_pattern

TEACHER_ROLES = frozenset({UserRole.HOD, UserRole.TEACHER})


def _http(code: int, detail: str) -> HTTPException:
    return HTTPException(code, detail=detail)


def _unprocessable(detail: str) -> HTTPException:
    return _http(status.HTTP_422_UNPROCESSABLE_CONTENT, detail)


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------


def list_users(
    db: Session,
    search: str | None,
    role: UserRole | None,
    is_active: bool | None,
    skip: int,
    limit: int,
) -> tuple[list[User], int]:
    """A page of accounts ordered by username, plus the total. `search` matches the username."""
    query = select(User)
    if search:
        query = query.where(User.username.ilike(contains_pattern(search), escape=LIKE_ESCAPE))
    if role is not None:
        query = query.where(User.role == role)
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    # Load the linked records with the page (for `linked_name`): no query per row.
    page = query.options(joinedload(User.teacher), joinedload(User.student))
    items = db.scalars(page.order_by(User.username).offset(skip).limit(limit)).all()
    return list(items), total


def get_user(db: Session, user_id: int) -> User:
    """The account, or 404."""
    user = db.get(User, user_id)
    if user is None:
        raise _http(status.HTTP_404_NOT_FOUND, "User not found")
    return user


# ---------------------------------------------------------------------------
# Validation of the resulting account
# ---------------------------------------------------------------------------


def _check_links_match_role(role: UserRole, teacher_id: int | None, student_id: int | None) -> None:
    if role is UserRole.ADMIN and (teacher_id is not None or student_id is not None):
        raise _unprocessable("An admin account can't be linked to a teacher or student")
    if role in TEACHER_ROLES:
        if teacher_id is None:
            raise _unprocessable(f"A {role.value} account must be linked to a teacher (teacher_id)")
        if student_id is not None:
            raise _unprocessable(f"A {role.value} account can't be linked to a student")
    if role is UserRole.STUDENT:
        if student_id is None:
            raise _unprocessable("A student account must be linked to a student (student_id)")
        if teacher_id is not None:
            raise _unprocessable("A student account can't be linked to a teacher")


def _check_link_free(
    db: Session, column_name: str, record_id: int, exclude_user_id: int | None
) -> None:
    column = User.teacher_id if column_name == "teacher" else User.student_id
    query = select(User.username).where(column == record_id)
    if exclude_user_id is not None:
        query = query.where(User.id != exclude_user_id)
    owner = db.scalar(query)
    if owner is not None:
        raise _http(
            status.HTTP_409_CONFLICT,
            f"{column_name.capitalize()} {record_id} already has an account ({owner!r})",
        )


def _check_br6(db: Session, role: UserRole, teacher: Teacher) -> None:
    headed = db.scalar(select(Department).where(Department.head_id == teacher.id))
    name = f"{teacher.first_name} {teacher.last_name}"
    if role is UserRole.HOD and headed is None:
        raise _unprocessable(
            f"{name} doesn't head a department, so the account can't be hod. "
            "Make them a department head instead (PATCH /departments/{id})."
        )
    if role is UserRole.TEACHER and headed is not None:
        raise _unprocessable(
            f"{name} is the head of {headed.code}, so the account must be hod. "
            "Appoint another head first to make them a teacher."
        )


def _validate(
    db: Session,
    role: UserRole,
    teacher_id: int | None,
    student_id: int | None,
    exclude_user_id: int | None = None,
) -> None:
    """Check the resulting account; see the module docstring for the rules."""
    _check_links_match_role(role, teacher_id, student_id)
    if teacher_id is not None:
        teacher = db.get(Teacher, teacher_id)
        if teacher is None:
            raise _unprocessable(f"Teacher {teacher_id} does not exist")
        _check_link_free(db, "teacher", teacher_id, exclude_user_id)
        _check_br6(db, role, teacher)
    if student_id is not None:
        if db.get(Student, student_id) is None:
            raise _unprocessable(f"Student {student_id} does not exist")
        _check_link_free(db, "student", student_id, exclude_user_id)


def _commit(db: Session) -> None:
    """Commit; a uniqueness race that slipped past the checks becomes a 409."""
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise _http(
            status.HTTP_409_CONFLICT, "This username, teacher or student already has an account"
        ) from exc


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------


def create_user(db: Session, data: UserCreate) -> User:
    """Create an account (FR-8.1)."""
    username = data.username.strip().lower()
    if db.scalar(select(User.id).where(User.username == username)) is not None:
        raise _http(status.HTTP_409_CONFLICT, f"Username {username!r} is already taken")
    _validate(db, data.role, data.teacher_id, data.student_id)

    user = User(
        username=username,
        password_hash=hash_password(data.password),
        role=data.role,
        teacher_id=data.teacher_id,
        student_id=data.student_id,
    )
    db.add(user)
    _commit(db)
    return user


def update_user(db: Session, user_id: int, data: UserUpdate, admin: User) -> User:
    """Activate/deactivate (FR-8.1, FR-8.2) or change role and links."""
    user = get_user(db, user_id)
    changes = data.model_dump(exclude_unset=True)

    if user.id == admin.id:
        if changes.get("is_active") is False:
            raise _http(status.HTTP_403_FORBIDDEN, "You can't deactivate your own account")
        if changes.get("role", UserRole.ADMIN) is not UserRole.ADMIN:
            raise _http(status.HTTP_403_FORBIDDEN, "You can't change the role of your own account")

    if {"role", "teacher_id", "student_id"} & changes.keys():
        _validate(
            db,
            changes.get("role", user.role),
            changes.get("teacher_id", user.teacher_id),
            changes.get("student_id", user.student_id),
            exclude_user_id=user.id,
        )
    for field, value in changes.items():
        setattr(user, field, value)
    _commit(db)
    return user


def reset_password(db: Session, user_id: int) -> str:
    """Replace the password with a random temporary one and return it (shown once)."""
    user = get_user(db, user_id)
    temporary = secrets.token_urlsafe(12)
    user.password_hash = hash_password(temporary)
    db.commit()
    return temporary


def delete_user(db: Session, user_id: int, admin: User) -> None:
    """Delete an account (approved addition to §3). The linked teacher or student
    record is kept; only the login goes."""
    user = get_user(db, user_id)
    if user.id == admin.id:
        raise _http(status.HTTP_403_FORBIDDEN, "You can't delete your own account")
    db.delete(user)
    db.commit()
