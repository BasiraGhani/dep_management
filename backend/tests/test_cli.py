"""Tests for app.cli: seed-admin and seed-demo (T2.4)."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.cli import (
    CURRENT_SEMESTER,
    DEMO_PASSWORD,
    PREVIOUS_SEMESTER,
    SeedError,
    seed_admin,
    seed_demo,
)
from app.config import BACKEND_DIR, Settings
from app.core.security import verify_password
from app.models import (
    Course,
    Department,
    Enrollment,
    Student,
    StudentStatus,
    Teacher,
    User,
    UserRole,
)
from tests.conftest import Factory, make_alembic_config

ADMIN_PASSWORD = "first-admin-password"
TABLES = (Department, Teacher, Student, Course, Enrollment, User)


def admin_settings(
    username: str | None = "Admin", password: str | None = ADMIN_PASSWORD
) -> Settings:
    return Settings(
        _env_file=None,
        secret_key="s" * 32,
        first_admin_username=username,
        first_admin_password=password,
    )


def counts(session: Session) -> dict[str, int]:
    return {
        model.__tablename__: session.scalar(select(func.count()).select_from(model)) or 0
        for model in TABLES
    }


# ---------- seed-admin (FR-1.5) ----------


def test_seed_admin_creates_an_active_admin(session: Session) -> None:
    assert seed_admin(session, admin_settings()) is True

    admin = session.scalars(select(User)).one()
    assert admin.username == "admin"  # normalized like every username
    assert admin.role is UserRole.ADMIN
    assert admin.is_active is True
    assert (admin.teacher_id, admin.student_id) == (None, None)
    assert verify_password(ADMIN_PASSWORD, admin.password_hash)


def test_seed_admin_twice_creates_no_duplicate_and_keeps_the_password(session: Session) -> None:
    seed_admin(session, admin_settings())
    original_hash = session.scalars(select(User)).one().password_hash

    assert seed_admin(session, admin_settings(password="a-different-password")) is False

    admin = session.scalars(select(User)).one()
    assert admin.password_hash == original_hash


@pytest.mark.parametrize(
    ("username", "password"),
    [(None, ADMIN_PASSWORD), ("admin", None), ("", ADMIN_PASSWORD), ("  ", ADMIN_PASSWORD)],
)
def test_seed_admin_requires_both_settings(
    session: Session, username: str | None, password: str | None
) -> None:
    with pytest.raises(SeedError, match="FIRST_ADMIN_USERNAME and FIRST_ADMIN_PASSWORD"):
        seed_admin(session, admin_settings(username, password))
    assert counts(session)["users"] == 0


def test_seed_admin_rejects_a_short_password(session: Session) -> None:
    with pytest.raises(SeedError, match="at least 8 characters"):
        seed_admin(session, admin_settings(password="short"))


def test_seed_admin_refuses_to_reuse_a_non_admin_username(
    session: Session, factory: Factory
) -> None:
    factory.user(UserRole.STUDENT, username="admin")

    with pytest.raises(SeedError, match="is a student, not an admin"):
        seed_admin(session, admin_settings())


def test_seeded_admin_can_log_in(client: TestClient, session: Session) -> None:
    seed_admin(session, admin_settings())

    response = client.post(
        "/api/v1/auth/login", data={"username": "admin", "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200


# ---------- seed-demo: contents ----------


def test_seed_demo_creates_the_specified_dataset(session: Session) -> None:
    seed_demo(session)

    assert counts(session) == {
        "departments": 3,
        "teachers": 10,
        "students": 60,
        "courses": 12,
        "enrollments": counts(session)["enrollments"],
        "users": 4,
    }
    assert counts(session)["enrollments"] > 100


def test_every_department_has_a_head_from_its_own_staff(session: Session) -> None:
    seed_demo(session)

    for department in session.scalars(select(Department)):
        assert department.head is not None
        assert department.head.department_id == department.id  # BR-3


def test_courses_are_taught_within_their_department(session: Session) -> None:
    seed_demo(session)

    for course in session.scalars(select(Course)):
        assert course.teacher is not None
        assert course.teacher.department_id == course.department_id  # BR-2


def test_only_active_students_are_enrolled(session: Session) -> None:
    seed_demo(session)

    statuses = set(
        session.scalars(
            select(Student.status).join(Enrollment, Enrollment.student_id == Student.id)
        )
    )
    assert statuses == {StudentStatus.ACTIVE}  # BR-4
    other = session.scalar(
        select(func.count()).select_from(Student).where(Student.status != StudentStatus.ACTIVE)
    )
    assert other  # the dataset does include non-active students


def test_no_course_is_over_capacity(session: Session) -> None:
    seed_demo(session)

    per_course_semester = session.execute(
        select(Enrollment.course_id, Enrollment.semester, func.count()).group_by(
            Enrollment.course_id, Enrollment.semester
        )
    ).all()
    capacity = {course.id: course.capacity for course in session.scalars(select(Course))}
    assert all(n <= capacity[course_id] for course_id, _, n in per_course_semester)  # BR-5


def test_enrollments_have_some_grades(session: Session) -> None:
    seed_demo(session)

    def graded(semester: str, is_graded: bool) -> int:
        condition = Enrollment.grade.is_not(None) if is_graded else Enrollment.grade.is_(None)
        query = (
            select(func.count())
            .select_from(Enrollment)
            .where(Enrollment.semester == semester, condition)
        )
        return session.scalar(query) or 0

    assert graded(PREVIOUS_SEMESTER, False) == 0  # past semester fully graded
    assert graded(CURRENT_SEMESTER, True) > 0  # some current grades entered
    assert graded(CURRENT_SEMESTER, False) > 0  # ...and some still pending


def test_seed_demo_creates_one_login_per_role(session: Session) -> None:
    report = seed_demo(session)

    users = {user.username: user for user in session.scalars(select(User))}
    assert sorted(role for _, role in report.logins) == sorted(UserRole)
    assert {name for name, _ in report.logins} == set(users)

    hod, teacher, student = users["demo.hod"], users["demo.teacher"], users["demo.student"]
    assert hod.teacher is not None and hod.teacher.department.head_id == hod.teacher_id
    assert teacher.teacher is not None and teacher.teacher.department.head_id != teacher.teacher_id
    assert student.student is not None and student.student.status is StudentStatus.ACTIVE
    assert users["demo.admin"].teacher_id is None and users["demo.admin"].student_id is None


def test_every_printed_demo_login_works(client: TestClient, session: Session) -> None:
    report = seed_demo(session)

    for username, role in report.logins:
        login = client.post(
            "/api/v1/auth/login", data={"username": username, "password": DEMO_PASSWORD}
        )
        assert login.status_code == 200, username
        token = login.json()["access_token"]
        me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.json()["role"] == role.value


# ---------- seed-demo: idempotent ----------


def test_seed_demo_twice_creates_no_duplicates(session: Session) -> None:
    first = seed_demo(session)
    after_first = counts(session)

    second = seed_demo(session)

    assert counts(session) == after_first
    assert sum(first.created.values()) > 0
    assert second.created == {}
    assert second.logins == first.logins


def test_seed_demo_does_not_overwrite_changed_data(session: Session) -> None:
    seed_demo(session)
    student = session.scalars(select(User).where(User.username == "demo.student")).one()
    student.password_hash = "changed-by-the-user"
    session.commit()

    seed_demo(session)

    session.refresh(student)
    assert student.password_hash == "changed-by-the-user"


def test_seed_admin_and_seed_demo_coexist(session: Session) -> None:
    seed_admin(session, admin_settings())
    seed_demo(session)
    seed_admin(session, admin_settings())

    admins = session.scalars(select(User.username).where(User.role == UserRole.ADMIN)).all()
    assert sorted(admins) == ["admin", "demo.admin"]


# ---------- The real command line ----------


@pytest.fixture
def cli_env(tmp_path: Path) -> dict[str, str]:
    """Environment for running `python -m app.cli` against a fresh, migrated database."""
    database_url = f"sqlite:///{tmp_path / 'cli.db'}"
    command.upgrade(make_alembic_config(database_url), "head")
    return os.environ | {
        "DATABASE_URL": database_url,
        "SECRET_KEY": "cli-test-secret-key-0123456789abcdef",
        "FIRST_ADMIN_USERNAME": "root",
        "FIRST_ADMIN_PASSWORD": ADMIN_PASSWORD,
    }


def run_cli(env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "app.cli", *args],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_cli_seed_admin_twice(cli_env: dict[str, str]) -> None:
    first, second = run_cli(cli_env, "seed-admin"), run_cli(cli_env, "seed-admin")

    assert (first.returncode, first.stdout) == (0, "Created admin 'root'.\n")
    assert (second.returncode, second.stdout) == (0, "Already exists: admin 'root'.\n")


def test_cli_seed_admin_without_settings_fails_clearly(cli_env: dict[str, str]) -> None:
    result = run_cli(cli_env | {"FIRST_ADMIN_USERNAME": ""}, "seed-admin")

    assert result.returncode == 1
    assert "Set FIRST_ADMIN_USERNAME and FIRST_ADMIN_PASSWORD" in result.stderr


def test_cli_seed_demo_twice_prints_the_logins(cli_env: dict[str, str]) -> None:
    first, second = run_cli(cli_env, "seed-demo"), run_cli(cli_env, "seed-demo")

    assert first.returncode == second.returncode == 0
    assert "created 3 departments, 10 teachers, 12 courses, 60 students" in first.stdout
    assert "created nothing new" in second.stdout
    for output in (first.stdout, second.stdout):
        assert f"password for all: {DEMO_PASSWORD}" in output
        for username in ("demo.admin", "demo.hod", "demo.teacher", "demo.student"):
            assert username in output


def test_cli_requires_a_command(cli_env: dict[str, str]) -> None:
    result = run_cli(cli_env)
    assert result.returncode == 2
    assert "seed-admin" in result.stderr
