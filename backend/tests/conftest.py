"""Shared test fixtures.

Isolation model
---------------
* One SQLite database per test session, built once with `alembic upgrade head`
  (so every test runs against the real migrations).
* Each test runs inside an outer transaction that is rolled back afterwards.
  The test's `session` joins it with SAVEPOINTs, so code under test may call
  `commit()` or `rollback()` freely: nothing outlives the test.
* `client` is a `TestClient` whose `get_db` dependency yields that same session,
  so API tests see (and leave behind) nothing beyond their own test.

Tests run in random order (`--random-order-bucket=global` in pyproject.toml), so
any state leaking between tests shows up as a failure.
"""

import os

# Settings require SECRET_KEY. Set a test value before any `app` module is imported,
# so the suite runs without a .env file (e.g. in CI). A real env var still wins.
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")

import itertools  # noqa: E402
from collections.abc import Iterator  # noqa: E402
from datetime import date  # noqa: E402
from typing import Any  # noqa: E402

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import Connection, Engine, event  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.config import BACKEND_DIR  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.database import create_db_engine, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: E402
    Course,
    Department,
    Student,
    StudentStatus,
    Teacher,
    TeacherTitle,
    User,
    UserRole,
)

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------


def make_alembic_config(database_url: str) -> Config:
    """Alembic config for the real migrations, pointed at `database_url`."""
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _enable_sqlite_savepoints(engine: Engine) -> None:
    """Make pysqlite issue BEGIN itself, so SAVEPOINT / ROLLBACK TO work.

    The sqlite3 driver normally starts transactions lazily and ignores SAVEPOINT
    semantics. This is SQLAlchemy's documented recipe for "SAVEPOINT on pysqlite".
    """

    @event.listens_for(engine, "connect")
    def _disable_driver_transactions(dbapi_connection: Any, _record: Any) -> None:
        dbapi_connection.isolation_level = None

    @event.listens_for(engine, "begin")
    def _emit_begin(connection: Connection) -> None:
        connection.exec_driver_sql("BEGIN")


@pytest.fixture(scope="session")
def engine(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Engine]:
    """A fresh SQLite database for the whole test session, migrated to head."""
    database_url = f"sqlite:///{tmp_path_factory.mktemp('db') / 'test.db'}"
    command.upgrade(make_alembic_config(database_url), "head")
    db_engine = create_db_engine(database_url)
    _enable_sqlite_savepoints(db_engine)
    yield db_engine
    db_engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    """A session whose changes are rolled back when the test ends."""
    connection = engine.connect()
    outer = connection.begin()
    db_session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,  # same as app.database.SessionLocal
    )
    try:
        yield db_session
    finally:
        db_session.close()
        outer.rollback()
        connection.close()


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    """`TestClient` for the app, with `get_db` overridden to use the test `session`."""

    def _get_test_db() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_db] = _get_test_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

_sequence = itertools.count(1)


def _next() -> int:
    """A number unique within the test session, for unique default values."""
    return next(_sequence)


class Factory:
    """Creates valid, flushed model rows with unique defaults.

    Every method accepts keyword overrides for any column, e.g.
    `factory.teacher(email="ada@uni.edu")` or `factory.course(department_id=999)`
    (useful for constraint tests). Related rows that aren't given are created
    automatically, so `factory.course()` alone builds a department too.

    Each row is flushed, so it has an `id` and database constraint errors
    (IntegrityError) are raised by the factory call itself.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def _save[ModelT](self, obj: ModelT) -> ModelT:
        self.session.add(obj)
        self.session.flush()
        return obj

    def department(self, **overrides: Any) -> Department:
        """Create a department.

        Defaults: code `D<n>`, name `Department <n>`, no head.
        """
        n = _next()
        fields: dict[str, Any] = {"code": f"D{n}", "name": f"Department {n}"}
        return self._save(Department(**(fields | overrides)))

    def teacher(self, department: Department | None = None, **overrides: Any) -> Teacher:
        """Create a teacher in `department` (a new department if not given).

        Defaults: name `Teacher <n>`, email `teacher<n>@uni.test`, title lecturer.
        Pass `department_id=` instead of `department` to set the raw foreign key.
        """
        n = _next()
        fields: dict[str, Any] = {
            "first_name": "Teacher",
            "last_name": str(n),
            "email": f"teacher{n}@uni.test",
            "title": TeacherTitle.LECTURER,
        }
        if "department_id" not in overrides:
            fields["department_id"] = (department or self.department()).id
        return self._save(Teacher(**(fields | overrides)))

    def student(self, department: Department | None = None, **overrides: Any) -> Student:
        """Create an active first-year student in `department` (new one if not given).

        Defaults: student_no `S<n>`, email `student<n>@uni.test`, enrolled 2026-09-01.
        Pass `department_id=` instead of `department` to set the raw foreign key.
        """
        n = _next()
        fields: dict[str, Any] = {
            "student_no": f"S{n:05d}",
            "first_name": "Student",
            "last_name": str(n),
            "email": f"student{n}@uni.test",
            "year": 1,
            "status": StudentStatus.ACTIVE,
            "enrollment_date": date(2026, 9, 1),
        }
        if "department_id" not in overrides:
            fields["department_id"] = (department or self.department()).id
        return self._save(Student(**(fields | overrides)))

    def course(
        self,
        department: Department | None = None,
        teacher: Teacher | None = None,
        **overrides: Any,
    ) -> Course:
        """Create a 3-credit course in `department` (new one if not given).

        Defaults: code `C<n>`, title `Course <n>`, no teacher, capacity 40 (the
        model default). `teacher` is optional; BR-2 (same department) is a
        service rule and is not checked here.
        """
        n = _next()
        fields: dict[str, Any] = {"code": f"C{n}", "title": f"Course {n}", "credits": 3}
        if "department_id" not in overrides:
            fields["department_id"] = (department or self.department()).id
        if teacher is not None:
            fields["teacher_id"] = teacher.id
        return self._save(Course(**(fields | overrides)))

    def user(
        self,
        role: UserRole = UserRole.ADMIN,
        teacher: Teacher | None = None,
        student: Student | None = None,
        password: str | None = None,
        **overrides: Any,
    ) -> User:
        """Create an active user account with a link that is valid for `role`.

        * admin: no link
        * hod / teacher: linked to `teacher` (a new teacher if not given)
        * student: linked to `student` (a new student if not given)

        Pass `teacher_id=` / `student_id=` to set the links directly, e.g. to test
        invalid combinations. Default username: `user<n>`.

        `password`: if given, it is hashed (argon2) so the user can log in with it.
        Otherwise `password_hash` is a placeholder that matches no password, which
        keeps tests that don't log in fast (hashing takes ~30 ms).
        """
        n = _next()
        fields: dict[str, Any] = {
            "username": f"user{n}",
            "password_hash": "not-a-real-hash" if password is None else hash_password(password),
            "role": role,
        }
        links_given = "teacher_id" in overrides or "student_id" in overrides
        if not links_given:
            if role in (UserRole.HOD, UserRole.TEACHER):
                fields["teacher_id"] = (teacher or self.teacher()).id
            elif role is UserRole.STUDENT:
                fields["student_id"] = (student or self.student()).id
        return self._save(User(**(fields | overrides)))


@pytest.fixture
def factory(session: Session) -> Factory:
    """A `Factory` bound to the test `session`."""
    return Factory(session)
