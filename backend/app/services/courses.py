"""Course rules and permissions (FR-5, BR-1, BR-2, BR-7, BR-8, REQUIREMENTS §3).

Who may do what:
* read (list, detail): everyone. The roster (FR-5.4) is shown only to users who
  may read the course's enrollments: admin, the HOD of the course's department,
  and the course's own teacher (Enrollments row of the permission matrix)
* create: admin anywhere; HOD only in the department they head
* update: admin any field; HOD courses of their department, without moving them
  elsewhere; a teacher only the description of a course they teach. Capacity
  can't drop below a semester's current enrollment (BR-5, added in T4.1)
* delete: admin; HOD in their department. 409 while the course has enrollments
"""

from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.permissions import managed_department_id, teaches_course
from app.models import Course, Department, Enrollment, Student, Teacher, User, UserRole
from app.schemas.course import CourseCreate, CourseUpdate
from app.services.common import LIKE_ESCAPE, contains_pattern
from app.services.enrollments import busiest_semester_count

TEACHER_EDITABLE_FIELDS = frozenset({"description"})


@dataclass(frozen=True)
class CourseDetail:
    course: Course
    roster: list[Enrollment] | None  # None: hidden from this user


def _http(code: int, detail: str) -> HTTPException:
    return HTTPException(code, detail=detail)


def _manages(user: User, department_id: int) -> bool:
    """Admin, or the HOD of `department_id`."""
    return user.role is UserRole.ADMIN or managed_department_id(user) == department_id


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------


def list_courses(
    db: Session,
    search: str | None,
    department_id: int | None,
    teacher_id: int | None,
    skip: int,
    limit: int,
) -> tuple[list[Course], int]:
    """A page of courses ordered by code, plus the total. `search` matches code or title."""
    query = select(Course)
    if search:
        pattern = contains_pattern(search)
        query = query.where(
            or_(
                Course.code.ilike(pattern, escape=LIKE_ESCAPE),
                Course.title.ilike(pattern, escape=LIKE_ESCAPE),
            )
        )
    if department_id is not None:
        query = query.where(Course.department_id == department_id)
    if teacher_id is not None:
        query = query.where(Course.teacher_id == teacher_id)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(query.order_by(Course.code).offset(skip).limit(limit)).all()
    return list(items), total


def get_course(db: Session, course_id: int) -> Course:
    """The course, or 404."""
    course = db.get(Course, course_id)
    if course is None:
        raise _http(status.HTTP_404_NOT_FOUND, "Course not found")
    return course


def _can_see_roster(user: User, course: Course) -> bool:
    return _manages(user, course.department_id) or teaches_course(user, course.id)


def get_course_detail(db: Session, course_id: int, user: User) -> CourseDetail:
    """The course and, if the user may see it, its roster (FR-5.4), or 404."""
    course = get_course(db, course_id)
    if not _can_see_roster(user, course):
        return CourseDetail(course=course, roster=None)
    roster = db.scalars(
        select(Enrollment)
        .join(Student, Student.id == Enrollment.student_id)
        .where(Enrollment.course_id == course_id)
        .options(joinedload(Enrollment.student))
        .order_by(Enrollment.semester, Student.last_name, Student.first_name, Enrollment.id)
    ).all()
    return CourseDetail(course=course, roster=list(roster))


# ---------------------------------------------------------------------------
# Checks used by writes
# ---------------------------------------------------------------------------


def _unprocessable(detail: str) -> HTTPException:
    return _http(status.HTTP_422_UNPROCESSABLE_CONTENT, detail)


def _require_department(db: Session, department_id: int) -> Department:
    department = db.get(Department, department_id)
    if department is None:
        raise _unprocessable(f"Department {department_id} does not exist")
    return department


def _check_teacher(db: Session, teacher_id: int | None, department: Department) -> None:
    """BR-2: a course's teacher must belong to the course's department (422)."""
    if teacher_id is None:
        return
    teacher = db.get(Teacher, teacher_id)
    if teacher is None:
        raise _unprocessable(f"Teacher {teacher_id} does not exist")
    if teacher.department_id != department.id:
        raise _unprocessable(
            f"{teacher.first_name} {teacher.last_name} is not in department {department.code}; "
            "a course's teacher must belong to the course's department"
        )


def _ensure_code_free(db: Session, code: str, exclude_id: int | None = None) -> None:
    """409 if another course has this code (BR-1, any case)."""
    normalized = code.strip().upper()
    query = select(Course.id).where(Course.code == normalized)
    if exclude_id is not None:
        query = query.where(Course.id != exclude_id)
    if db.scalar(query) is not None:
        raise _http(status.HTTP_409_CONFLICT, f"A course with code {normalized!r} already exists")


def _commit(db: Session) -> None:
    """Commit; a uniqueness race that slipped past the checks becomes a 409."""
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise _http(status.HTTP_409_CONFLICT, "A course with this code already exists") from exc


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------


def create_course(db: Session, data: CourseCreate, user: User) -> Course:
    """Create a course (FR-5.1, FR-5.2), checking BR-1 and BR-2."""
    if not _manages(user, data.department_id):
        raise _http(
            status.HTTP_403_FORBIDDEN, "You can only add courses to the department you head"
        )
    department = _require_department(db, data.department_id)
    _check_teacher(db, data.teacher_id, department)
    _ensure_code_free(db, data.code)

    course = Course(**data.model_dump())
    db.add(course)
    _commit(db)
    return course


def _check_update_allowed(user: User, course: Course, data: CourseUpdate) -> None:
    fields = data.model_fields_set
    if user.role is UserRole.ADMIN:
        return
    if user.role is UserRole.HOD and _manages(user, course.department_id):
        if "department_id" in fields and data.department_id != course.department_id:
            raise _http(
                status.HTTP_403_FORBIDDEN,
                "A head of department can't move courses to another department",
            )
        return
    if teaches_course(user, course.id):
        not_allowed = fields - TEACHER_EDITABLE_FIELDS
        if not_allowed:
            raise _http(
                status.HTTP_403_FORBIDDEN,
                "You can only change the description of your own course "
                f"(not {', '.join(sorted(not_allowed))})",
            )
        return
    raise _http(status.HTTP_403_FORBIDDEN, "You can't edit this course")


def update_course(db: Session, course_id: int, data: CourseUpdate, user: User) -> Course:
    """Apply a partial update; see the module docstring for who may change what.

    BR-2 is checked on the result: after a department change, the course's
    teacher (kept or newly given) must belong to the new department.
    """
    course = get_course(db, course_id)
    _check_update_allowed(user, course, data)
    changes = data.model_dump(exclude_unset=True)

    if "code" in changes:
        _ensure_code_free(db, changes["code"], exclude_id=course.id)
    if "capacity" in changes:
        busiest = busiest_semester_count(db, course.id)
        if changes["capacity"] < busiest:
            raise _http(
                status.HTTP_409_CONFLICT,
                f"Capacity can't be lower than the {busiest} students already enrolled "
                f"in {course.code} in one semester (BR-5)",
            )
    if "department_id" in changes or "teacher_id" in changes:
        department = _require_department(db, changes.get("department_id", course.department_id))
        _check_teacher(db, changes.get("teacher_id", course.teacher_id), department)

    for field, value in changes.items():
        setattr(course, field, value)
    _commit(db)
    return course


def delete_course(db: Session, course_id: int, user: User) -> None:
    """Delete a course (admin; HOD in their department). 409 while it has
    enrollments (BR-7), with the number of enrollments in the message."""
    course = get_course(db, course_id)
    if not _manages(user, course.department_id):
        raise _http(
            status.HTTP_403_FORBIDDEN, "You can only delete courses of the department you head"
        )
    query = select(func.count()).select_from(Enrollment).where(Enrollment.course_id == course_id)
    enrollments = db.scalar(query) or 0
    if enrollments:
        noun = "enrollment" if enrollments == 1 else "enrollments"
        raise _http(
            status.HTTP_409_CONFLICT,
            f"Course {course.code} can't be deleted while it has {enrollments} {noun}. "
            "Remove them first.",
        )
    db.delete(course)
    db.commit()
