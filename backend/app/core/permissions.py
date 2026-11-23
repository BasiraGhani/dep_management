"""Scope helpers: which department, courses and records a user may act on.

These answer "is this record inside the user's scope?". Role checks (which
roles may call an endpoint at all) are done with `require_roles` in deps.py.
Services combine both, following the permission matrix in REQUIREMENTS §3.

All helpers are pure reads that follow the user's relationships, so they need
no extra arguments. A user whose role link is missing (e.g. a teacher account
without a teacher record) gets the most restrictive answer.
"""

from app.models.teacher import Teacher
from app.models.user import User, UserRole

TEACHING_ROLES = frozenset({UserRole.HOD, UserRole.TEACHER})


def _linked_teacher(user: User) -> Teacher | None:
    """The user's teacher record, if their role is HOD or teacher."""
    return user.teacher if user.role in TEACHING_ROLES else None


def user_department_id(user: User) -> int | None:
    """The id of the department the user belongs to.

    * admin: None (not tied to a department; admins see everything)
    * hod / teacher: their teacher record's department
    * student: their student record's department
    """
    if user.role in TEACHING_ROLES:
        teacher = user.teacher
        return teacher.department_id if teacher else None
    if user.role is UserRole.STUDENT:
        student = user.student
        return student.department_id if student else None
    return None


def can_manage_department(user: User, dept_id: int) -> bool:
    """True if the user may manage records in department `dept_id`.

    * admin: any department
    * hod: only the department they actually head (their teacher record is
      that department's `head_id`, REQUIREMENTS §2), not merely the one they
      belong to
    * teacher / student: never
    """
    if user.role is UserRole.ADMIN:
        return True
    if user.role is not UserRole.HOD:
        return False
    teacher = user.teacher
    if teacher is None or teacher.department_id != dept_id:
        return False
    return teacher.department.head_id == teacher.id


def teaches_course(user: User, course_id: int) -> bool:
    """True if the user is the assigned teacher of course `course_id`.

    * hod / teacher: only courses assigned to their teacher record
    * admin / student: never (admins have authority, but they don't teach)
    """
    teacher = _linked_teacher(user)
    if teacher is None:
        return False
    return any(course.id == course_id for course in teacher.courses)


def is_self_student(user: User, student_id: int) -> bool:
    """True if `student_id` is the user's own student record.

    Only student accounts can match; other roles never do.
    """
    return user.role is UserRole.STUDENT and user.student_id == student_id
