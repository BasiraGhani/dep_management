"""Student rules and permissions (FR-4, BR-1, BR-7, BR-8, REQUIREMENTS §3).

Who may see which students (list and detail):
* admin: everyone
* hod: students of the department they head, plus students in courses they teach
* teacher: students enrolled (any semester) in courses they teach
* student: only themselves, via the detail endpoint (the list is 403, user decision)

Writes:
* create: admin anywhere; HOD only in the department they head
* update: admin any field; HOD students of their department, without moving them
  elsewhere; a student their own phone and email (user decision)
* delete: admin; HOD in their department. Enrollments are deleted with the
  student (FR-4.4); 409 while the student has a login account (user decision)
"""

from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import ColumnElement, Select, false, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.permissions import (
    is_self_student,
    managed_department_id,
    teaches_student,
)
from app.core.security import hash_password
from app.models import Course, Department, Enrollment, Student, StudentStatus, User, UserRole
from app.schemas.common import AccountCreate
from app.schemas.student import StudentCreate, StudentUpdate
from app.services.common import LIKE_ESCAPE, contains_pattern
from app.services.gpa import calculate_gpa

SELF_EDITABLE_FIELDS = frozenset({"phone", "email"})


@dataclass(frozen=True)
class StudentDetail:
    student: Student
    enrollments: list[Enrollment]
    gpa: float | None
    user_id: int | None


def _http(code: int, detail: str) -> HTTPException:
    return HTTPException(code, detail=detail)


# ---------------------------------------------------------------------------
# Scope
# ---------------------------------------------------------------------------


def _taught_student_ids(teacher_id: int) -> Select[int]:
    return (
        select(Enrollment.student_id)
        .join(Course, Course.id == Enrollment.course_id)
        .where(Course.teacher_id == teacher_id)
    )


def _visibility_filter(user: User) -> ColumnElement[bool] | None:
    """SQL condition for the students `user` may see; None means no restriction."""
    if user.role is UserRole.ADMIN:
        return None
    conditions: list[ColumnElement[bool]] = []
    if user.role in (UserRole.HOD, UserRole.TEACHER) and user.teacher_id is not None:
        conditions.append(Student.id.in_(_taught_student_ids(user.teacher_id)))
    department_id = managed_department_id(user)
    if department_id is not None:
        conditions.append(Student.department_id == department_id)
    return or_(*conditions) if conditions else false()


def _can_read(user: User, student: Student) -> bool:
    if user.role is UserRole.ADMIN:
        return True
    if user.role is UserRole.STUDENT:
        return is_self_student(user, student.id)
    in_department = managed_department_id(user) == student.department_id
    return in_department or teaches_student(user, student.id)


def _can_manage(user: User, student: Student) -> bool:
    """Admin, or the HOD of the student's department."""
    if user.role is UserRole.ADMIN:
        return True
    return managed_department_id(user) == student.department_id


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------


def students_query(
    user: User,
    search: str | None,
    department_id: int | None,
    year: int | None,
    status_: StudentStatus | None,
) -> Select[Student]:
    """The students `user` may see, filtered (no ordering or paging).

    `search` matches first name, last name, "first last", email or student number.
    """
    query = select(Student)
    visible = _visibility_filter(user)
    if visible is not None:
        query = query.where(visible)
    if search:
        pattern = contains_pattern(search)
        full_name = Student.first_name + " " + Student.last_name
        columns = (
            Student.first_name,
            Student.last_name,
            full_name,
            Student.email,
            Student.student_no,
        )
        query = query.where(or_(*(c.ilike(pattern, escape=LIKE_ESCAPE) for c in columns)))
    if department_id is not None:
        query = query.where(Student.department_id == department_id)
    if year is not None:
        query = query.where(Student.year == year)
    if status_ is not None:
        query = query.where(Student.status == status_)
    return query


def list_students(
    db: Session,
    user: User,
    search: str | None,
    department_id: int | None,
    year: int | None,
    status_: StudentStatus | None,
    skip: int,
    limit: int,
) -> tuple[list[Student], int]:
    """A page of the students `user` may see, ordered by name, plus the total.

    `search` matches first name, last name, "first last", email or student number.
    """
    query = students_query(user, search, department_id, year, status_)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    order = (Student.last_name, Student.first_name, Student.id)
    items = db.scalars(query.order_by(*order).offset(skip).limit(limit)).all()
    return list(items), total


def get_student(db: Session, student_id: int) -> Student:
    """The student, or 404."""
    student = db.get(Student, student_id)
    if student is None:
        raise _http(status.HTTP_404_NOT_FOUND, "Student not found")
    return student


def get_student_detail(db: Session, student_id: int, user: User) -> StudentDetail:
    """The student with enrollments, GPA and account id; 404, or 403 outside the
    user's scope."""
    student = get_student(db, student_id)
    if not _can_read(user, student):
        raise _http(status.HTTP_403_FORBIDDEN, "You can't view this student")
    enrollments = db.scalars(
        select(Enrollment)
        .where(Enrollment.student_id == student_id)
        .options(selectinload(Enrollment.course))
        .order_by(Enrollment.id)
    ).all()
    user_id = db.scalar(select(User.id).where(User.student_id == student_id))
    gpa = calculate_gpa((e.grade, e.course.credits) for e in enrollments)
    return StudentDetail(student=student, enrollments=list(enrollments), gpa=gpa, user_id=user_id)


# ---------------------------------------------------------------------------
# Checks used by writes
# ---------------------------------------------------------------------------


def _require_department(db: Session, department_id: int) -> None:
    if db.get(Department, department_id) is None:
        raise _http(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"Department {department_id} does not exist"
        )


def _ensure_unique(
    db: Session,
    student_no: str | None,
    email: str | None,
    exclude_id: int | None = None,
) -> None:
    """409 if another student has this student number or email (BR-1, any case)."""
    others = select(Student.id)
    if exclude_id is not None:
        others = others.where(Student.id != exclude_id)
    if student_no is not None:
        number = student_no.strip().upper()
        if db.scalar(others.where(Student.student_no == number)) is not None:
            raise _http(status.HTTP_409_CONFLICT, f"Student number {number!r} already exists")
    if email is not None:
        address = email.strip().lower()
        if db.scalar(others.where(Student.email == address)) is not None:
            raise _http(
                status.HTTP_409_CONFLICT, f"A student with email {address!r} already exists"
            )


def _ensure_username_free(db: Session, username: str) -> None:
    if db.scalar(select(User.id).where(User.username == username.strip().lower())) is not None:
        raise _http(status.HTTP_409_CONFLICT, f"Username {username!r} is already taken")


def _commit(db: Session) -> None:
    """Commit; a uniqueness race that slipped past the checks becomes a 409."""
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise _http(
            status.HTTP_409_CONFLICT,
            "A student with this number or email, or this username, already exists",
        ) from exc


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


def _create_account(db: Session, student: Student, account: AccountCreate) -> None:
    db.add(
        User(
            username=account.username,
            password_hash=hash_password(account.temp_password),
            role=UserRole.STUDENT,
            student_id=student.id,
        )
    )


def create_student(db: Session, data: StudentCreate, user: User) -> Student:
    """Create a student, optionally with a student login account (FR-4.1, FR-4.3)."""
    if user.role is not UserRole.ADMIN and managed_department_id(user) != data.department_id:
        raise _http(
            status.HTTP_403_FORBIDDEN, "You can only add students to the department you head"
        )
    _require_department(db, data.department_id)
    _ensure_unique(db, data.student_no, data.email)
    if data.create_account is not None:
        _ensure_username_free(db, data.create_account.username)

    student = Student(**data.model_dump(exclude={"create_account"}))
    db.add(student)
    db.flush()
    if data.create_account is not None:
        _create_account(db, student, data.create_account)
    _commit(db)
    return student


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


def _check_update_allowed(user: User, student: Student, data: StudentUpdate) -> None:
    fields = data.model_fields_set
    if user.role is UserRole.ADMIN:
        return
    if user.role is UserRole.HOD and _can_manage(user, student):
        if "department_id" in fields and data.department_id != student.department_id:
            raise _http(
                status.HTTP_403_FORBIDDEN,
                "A head of department can't move students to another department",
            )
        return
    if is_self_student(user, student.id):
        not_allowed = fields - SELF_EDITABLE_FIELDS
        if not_allowed:
            raise _http(
                status.HTTP_403_FORBIDDEN,
                "You can only change your own phone and email "
                f"(not {', '.join(sorted(not_allowed))})",
            )
        return
    raise _http(status.HTTP_403_FORBIDDEN, "You can't edit this student")


def update_student(db: Session, student_id: int, data: StudentUpdate, user: User) -> Student:
    """Apply a partial update; see the module docstring for who may change what."""
    student = get_student(db, student_id)
    _check_update_allowed(user, student, data)

    changes = data.model_dump(exclude_unset=True)
    _ensure_unique(db, changes.get("student_no"), changes.get("email"), exclude_id=student.id)
    new_department = changes.get("department_id")
    if new_department is not None and new_department != student.department_id:
        _require_department(db, new_department)

    for field, value in changes.items():
        setattr(student, field, value)
    _commit(db)
    return student


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


def delete_student(db: Session, student_id: int, user: User) -> None:
    """Delete a student and their enrollments (FR-4.4).

    Admin, or the HOD of the student's department. 409 while the student has a
    login account, so it is never removed silently (BR-7).
    """
    student = get_student(db, student_id)
    if not _can_manage(user, student):
        raise _http(
            status.HTTP_403_FORBIDDEN, "You can only delete students of the department you head"
        )
    if db.scalar(select(User.id).where(User.student_id == student.id)) is not None:
        raise _http(
            status.HTTP_409_CONFLICT,
            "Student can't be deleted: they have a login account "
            "(delete it on the Users page first)",
        )
    db.delete(student)  # enrollments go too: ON DELETE CASCADE + ORM cascade
    db.commit()
