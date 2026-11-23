"""Tests for the test infrastructure itself (T1.4): isolation, client and factories."""

import inspect as pyinspect
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.main import app
from app.models import Course, Department, Student, Teacher, User, UserRole
from tests.conftest import Factory

ALL_MODELS = (Department, Teacher, Student, Course, User)

# ---------- Isolation ----------
# The suite runs in random order. If committed rows leaked out of a test, whichever
# of these ran second would hit a unique violation or see a non-empty table.


def row_counts(session: Session) -> dict[str, int]:
    return {
        model.__tablename__: session.scalar(select(func.count()).select_from(model)) or 0
        for model in ALL_MODELS
    }


@pytest.mark.parametrize("attempt", [1, 2, 3])
def test_committed_rows_do_not_leak_between_tests(
    session: Session, factory: Factory, attempt: int
) -> None:
    assert set(row_counts(session).values()) == {0}, "a previous test left rows behind"

    factory.user(UserRole.ADMIN, username="isolation-check")
    factory.course(code="ISOLATION1")
    session.commit()

    assert row_counts(session)["users"] == 1


def test_rollback_inside_a_test_only_undoes_that_tests_work(
    session: Session, factory: Factory
) -> None:
    kept = factory.department()
    session.commit()
    factory.department()
    session.rollback()

    assert session.scalars(select(Department)).all() == [kept]


# ---------- Client ----------


def test_client_serves_the_app(client: TestClient) -> None:
    assert client.get("/api/v1/health").json() == {"status": "ok"}


def test_client_overrides_get_db_with_the_test_session(
    client: TestClient, session: Session
) -> None:
    override = app.dependency_overrides[get_db]
    dependency: Iterator[Session] = override()

    assert next(dependency) is session


def test_get_db_override_is_removed_after_the_client_fixture() -> None:
    assert get_db not in app.dependency_overrides


# ---------- Factories ----------


def test_every_factory_method_is_documented() -> None:
    methods = {
        name: member
        for name, member in pyinspect.getmembers(Factory, pyinspect.isfunction)
        if not name.startswith("_")
    }
    assert set(methods) == {"department", "teacher", "student", "course", "user"}
    assert Factory.__doc__
    for name, method in methods.items():
        assert method.__doc__, f"Factory.{name} has no docstring"


def test_factories_create_flushed_rows_with_ids(factory: Factory) -> None:
    ids = [
        factory.department().id,
        factory.teacher().id,
        factory.student().id,
        factory.course().id,
        factory.user().id,
    ]
    assert all(isinstance(row_id, int) for row_id in ids)


def test_factory_defaults_are_unique(factory: Factory) -> None:
    departments = [factory.department() for _ in range(3)]
    teachers = [factory.teacher() for _ in range(3)]
    students = [factory.student() for _ in range(3)]
    courses = [factory.course() for _ in range(3)]

    assert len({d.code for d in departments}) == 3
    assert len({d.name for d in departments}) == 3
    assert len({t.email for t in teachers}) == 3
    assert len({s.student_no for s in students}) == 3
    assert len({s.email for s in students}) == 3
    assert len({c.code for c in courses}) == 3


def test_factories_create_missing_related_rows(factory: Factory) -> None:
    course = factory.course()
    assert course.department_id is not None
    assert course.teacher_id is None


def test_factories_use_the_given_related_rows(factory: Factory) -> None:
    department = factory.department()
    teacher = factory.teacher(department)
    student = factory.student(department)
    course = factory.course(department, teacher=teacher)

    assert teacher.department_id == department.id
    assert student.department_id == department.id
    assert course.department_id == department.id
    assert course.teacher_id == teacher.id


def test_factory_overrides_win(factory: Factory) -> None:
    teacher = factory.teacher(first_name="Ada", email="ada@uni.edu")
    assert (teacher.first_name, teacher.email) == ("Ada", "ada@uni.edu")


@pytest.mark.parametrize(
    ("role", "has_teacher", "has_student"),
    [
        (UserRole.ADMIN, False, False),
        (UserRole.HOD, True, False),
        (UserRole.TEACHER, True, False),
        (UserRole.STUDENT, False, True),
    ],
)
def test_user_factory_links_match_the_role(
    factory: Factory, role: UserRole, has_teacher: bool, has_student: bool
) -> None:
    user = factory.user(role)

    assert user.role is role
    assert user.is_active is True
    assert (user.teacher_id is not None) is has_teacher
    assert (user.student_id is not None) is has_student


def test_user_factory_uses_the_given_teacher_or_student(factory: Factory) -> None:
    teacher, student = factory.teacher(), factory.student()

    assert factory.user(UserRole.HOD, teacher=teacher).teacher_id == teacher.id
    assert factory.user(UserRole.STUDENT, student=student).student_id == student.id


def test_user_factory_allows_explicit_links_for_invalid_combinations(factory: Factory) -> None:
    student = factory.student()
    user = factory.user(UserRole.ADMIN, student_id=student.id)
    assert (user.teacher_id, user.student_id) == (None, student.id)
