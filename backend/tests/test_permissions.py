"""Tests for the scope helpers in core.permissions (T2.3).

The `world` fixture has two departments, A and B:

    A: head teacher `hod_a` (HOD account), teacher `teacher_a` (teaches course_a1),
       student `student_a`; hod_a teaches course_a2
    B: head teacher `hod_b` (HOD account), teacher `teacher_b` (teaches course_b1),
       student `student_b`

plus an admin. Every helper is checked for all 4 roles, allowed and denied.
"""

from dataclasses import dataclass

import pytest
from sqlalchemy.orm import Session

from app.core.permissions import (
    can_manage_department,
    is_self_student,
    managed_department_id,
    teaches_course,
    teaches_student,
    user_department_id,
)
from app.models import Course, Department, Enrollment, Student, User, UserRole
from tests.conftest import Factory


@dataclass
class World:
    dept_a: Department
    dept_b: Department
    admin: User
    hod_a: User
    hod_b: User
    teacher_a: User
    teacher_b: User
    student_a: User
    student_b: User
    student_a_record: Student
    student_b_record: Student
    course_a1: Course  # taught by teacher_a
    course_a2: Course  # taught by hod_a
    course_b1: Course  # taught by teacher_b
    course_unassigned: Course  # in A, no teacher


@pytest.fixture
def world(session: Session, factory: Factory) -> World:
    dept_a, dept_b = factory.department(), factory.department()

    head_a, head_b = factory.teacher(dept_a), factory.teacher(dept_b)
    dept_a.head_id, dept_b.head_id = head_a.id, head_b.id
    plain_a, plain_b = factory.teacher(dept_a), factory.teacher(dept_b)
    student_a_record, student_b_record = factory.student(dept_a), factory.student(dept_b)
    session.flush()

    world = World(
        dept_a=dept_a,
        dept_b=dept_b,
        admin=factory.user(UserRole.ADMIN),
        hod_a=factory.user(UserRole.HOD, teacher=head_a),
        hod_b=factory.user(UserRole.HOD, teacher=head_b),
        teacher_a=factory.user(UserRole.TEACHER, teacher=plain_a),
        teacher_b=factory.user(UserRole.TEACHER, teacher=plain_b),
        student_a=factory.user(UserRole.STUDENT, student=student_a_record),
        student_b=factory.user(UserRole.STUDENT, student=student_b_record),
        student_a_record=student_a_record,
        student_b_record=student_b_record,
        course_a1=factory.course(dept_a, teacher=plain_a),
        course_a2=factory.course(dept_a, teacher=head_a),
        course_b1=factory.course(dept_b, teacher=plain_b),
        course_unassigned=factory.course(dept_a),
    )
    session.commit()
    session.expire_all()  # helpers must load relationships from the database
    return world


# ---------- user_department_id ----------


def test_user_department_id_for_admin_is_none(world: World) -> None:
    assert user_department_id(world.admin) is None


@pytest.mark.parametrize(
    ("user", "dept"),
    [
        ("hod_a", "dept_a"),
        ("hod_b", "dept_b"),
        ("teacher_a", "dept_a"),
        ("teacher_b", "dept_b"),
        ("student_a", "dept_a"),
        ("student_b", "dept_b"),
    ],
)
def test_user_department_id_is_the_linked_records_department(
    world: World, user: str, dept: str
) -> None:
    assert user_department_id(getattr(world, user)) == getattr(world, dept).id


@pytest.mark.parametrize("role", [UserRole.HOD, UserRole.TEACHER, UserRole.STUDENT])
def test_user_department_id_without_a_linked_record_is_none(
    factory: Factory, role: UserRole
) -> None:
    unlinked = factory.user(role, teacher_id=None, student_id=None)
    assert user_department_id(unlinked) is None


# ---------- can_manage_department ----------


@pytest.mark.parametrize(
    ("user", "dept", "allowed"),
    [
        ("admin", "dept_a", True),
        ("admin", "dept_b", True),
        ("hod_a", "dept_a", True),
        ("hod_a", "dept_b", False),
        ("hod_b", "dept_b", True),
        ("hod_b", "dept_a", False),
        ("teacher_a", "dept_a", False),  # member, but not the head
        ("teacher_a", "dept_b", False),
        ("student_a", "dept_a", False),
        ("student_a", "dept_b", False),
    ],
)
def test_can_manage_department(world: World, user: str, dept: str, allowed: bool) -> None:
    assert can_manage_department(getattr(world, user), getattr(world, dept).id) is allowed


def test_admin_can_manage_a_department_that_does_not_exist_yet(world: World) -> None:
    """Admins aren't scoped; existence is checked by the service (404)."""
    assert can_manage_department(world.admin, 999_999) is True


def test_hod_role_without_actually_heading_the_department_is_denied(
    session: Session, world: World
) -> None:
    """A stale HOD role (head was replaced) grants nothing (REQUIREMENTS §2)."""
    assert world.teacher_a.teacher is not None
    world.dept_a.head_id = world.teacher_a.teacher.id
    session.commit()
    session.expire_all()

    assert can_manage_department(world.hod_a, world.dept_a.id) is False


def test_department_with_no_head_cannot_be_managed_by_a_hod(session: Session, world: World) -> None:
    world.dept_a.head_id = None
    session.commit()
    session.expire_all()

    assert can_manage_department(world.hod_a, world.dept_a.id) is False
    assert can_manage_department(world.admin, world.dept_a.id) is True


def test_hod_without_a_teacher_record_is_denied(factory: Factory, world: World) -> None:
    unlinked_hod = factory.user(UserRole.HOD, teacher_id=None)
    assert can_manage_department(unlinked_hod, world.dept_a.id) is False


# ---------- teaches_course ----------


@pytest.mark.parametrize(
    ("user", "course", "allowed"),
    [
        ("teacher_a", "course_a1", True),
        ("teacher_a", "course_a2", False),  # same department, someone else's course
        ("teacher_a", "course_b1", False),
        ("teacher_a", "course_unassigned", False),
        ("hod_a", "course_a2", True),  # a HOD teaches their own courses
        ("hod_a", "course_a1", False),  # managing the dept isn't teaching the course
        ("hod_b", "course_a2", False),
        ("admin", "course_a1", False),
        ("admin", "course_unassigned", False),
        ("student_a", "course_a1", False),
    ],
)
def test_teaches_course(world: World, user: str, course: str, allowed: bool) -> None:
    assert teaches_course(getattr(world, user), getattr(world, course).id) is allowed


def test_teaches_course_for_an_unknown_course_is_false(world: World) -> None:
    assert teaches_course(world.teacher_a, 999_999) is False


def test_teaches_course_follows_reassignment(session: Session, world: World) -> None:
    assert world.teacher_b.teacher is not None
    world.course_a1.teacher_id = world.teacher_b.teacher.id
    session.commit()
    session.expire_all()

    assert teaches_course(world.teacher_a, world.course_a1.id) is False
    assert teaches_course(world.teacher_b, world.course_a1.id) is True


# ---------- is_self_student ----------


@pytest.mark.parametrize(
    ("user", "student", "allowed"),
    [
        ("student_a", "student_a_record", True),
        ("student_a", "student_b_record", False),
        ("student_b", "student_b_record", True),
        ("admin", "student_a_record", False),
        ("hod_a", "student_a_record", False),
        ("teacher_a", "student_a_record", False),
    ],
)
def test_is_self_student(world: World, user: str, student: str, allowed: bool) -> None:
    assert is_self_student(getattr(world, user), getattr(world, student).id) is allowed


def test_non_student_with_a_matching_student_link_is_still_denied(factory: Factory) -> None:
    """Only the student role counts, even if an invalid account carries a student link."""
    record = factory.student()
    odd_teacher = factory.user(UserRole.TEACHER, student_id=record.id)

    assert is_self_student(odd_teacher, record.id) is False


# ---------- managed_department_id (T3.3) ----------


@pytest.mark.parametrize(
    ("user", "dept"),
    [
        ("admin", None),
        ("hod_a", "dept_a"),
        ("hod_b", "dept_b"),
        ("teacher_a", None),
        ("student_a", None),
    ],
)
def test_managed_department_id(world: World, user: str, dept: str | None) -> None:
    expected = getattr(world, dept).id if dept else None
    assert managed_department_id(getattr(world, user)) == expected


def test_managed_department_id_is_none_for_a_stale_hod(session: Session, world: World) -> None:
    assert world.teacher_a.teacher is not None
    world.dept_a.head_id = world.teacher_a.teacher.id
    session.commit()
    session.expire_all()

    assert managed_department_id(world.hod_a) is None


# ---------- teaches_student (T3.3) ----------


@pytest.fixture
def enrolled(session: Session, world: World) -> World:
    """student_a in course_a1 (teacher_a) and student_b in course_a2 (hod_a)."""
    session.add_all(
        [
            Enrollment(
                student_id=world.student_a_record.id,
                course_id=world.course_a1.id,
                semester="2026-Fall",
            ),
            Enrollment(
                student_id=world.student_b_record.id,
                course_id=world.course_a2.id,
                semester="2026-Spring",
            ),
        ]
    )
    session.commit()
    return world


@pytest.mark.parametrize(
    ("user", "student", "allowed"),
    [
        ("teacher_a", "student_a_record", True),
        ("teacher_a", "student_b_record", False),  # enrolled, but in someone else's course
        ("hod_a", "student_b_record", True),  # in the HOD's own course, other department
        ("hod_a", "student_a_record", False),  # own department, but not their course
        ("teacher_b", "student_a_record", False),
        ("admin", "student_a_record", False),
        ("student_a", "student_a_record", False),
    ],
)
def test_teaches_student(enrolled: World, user: str, student: str, allowed: bool) -> None:
    world = enrolled
    assert teaches_student(getattr(world, user), getattr(world, student).id) is allowed


def test_teaches_student_with_no_enrollments_is_false(world: World) -> None:
    assert teaches_student(world.teacher_a, world.student_a_record.id) is False
