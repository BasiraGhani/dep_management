"""Schema tests for departments, teachers and students (T1.2).

The database is built with the real Alembic migration, so these tests cover the
migration and the models together.
"""

from collections.abc import Iterator
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import create_db_engine
from app.models import Department, Student, StudentStatus, Teacher, TeacherTitle
from tests.test_migrations import make_alembic_config


@pytest.fixture
def engine(tmp_path: Path) -> Iterator[Engine]:
    database_url = f"sqlite:///{tmp_path / 'models.db'}"
    command.upgrade(make_alembic_config(database_url), "head")
    db_engine = create_db_engine(database_url)
    yield db_engine
    db_engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    with Session(engine) as db_session:
        yield db_session


def add_department(
    session: Session, code: str = "CS", name: str = "Computer Science"
) -> Department:
    department = Department(code=code, name=name)
    session.add(department)
    session.flush()
    return department


def add_teacher(session: Session, department_id: int, email: str = "ada@uni.edu") -> Teacher:
    teacher = Teacher(
        first_name="Ada",
        last_name="Lovelace",
        email=email,
        title=TeacherTitle.PROFESSOR,
        department_id=department_id,
    )
    session.add(teacher)
    session.flush()
    return teacher


def add_student(
    session: Session,
    department_id: int,
    student_no: str = "S0001",
    email: str = "alan@uni.edu",
    year: int = 1,
) -> Student:
    student = Student(
        student_no=student_no,
        first_name="Alan",
        last_name="Turing",
        email=email,
        department_id=department_id,
        year=year,
        status=StudentStatus.ACTIVE,
        enrollment_date=date(2026, 9, 1),
    )
    session.add(student)
    session.flush()
    return student


def insert_raw(session: Session, table: str, **values: Any) -> None:
    """Insert with plain SQL, bypassing model validation, to test DB constraints."""
    now = datetime.now(UTC).isoformat()
    values = {"created_at": now, "updated_at": now, **values}
    columns = ", ".join(values)
    params = ", ".join(f":{name}" for name in values)
    session.execute(text(f"INSERT INTO {table} ({columns}) VALUES ({params})"), values)


# ---------- Schema created by the migration ----------


def unique_columns(engine: Engine, table: str) -> set[tuple[str, ...]]:
    return {tuple(uq["column_names"]) for uq in inspect(engine).get_unique_constraints(table)}


def foreign_keys(engine: Engine, table: str) -> set[tuple[str, str]]:
    return {
        (fk["constrained_columns"][0], fk["referred_table"])
        for fk in inspect(engine).get_foreign_keys(table)
    }


def test_unique_constraints_exist(engine: Engine) -> None:
    assert unique_columns(engine, "departments") == {("code",), ("name",)}
    assert unique_columns(engine, "teachers") == {("email",)}
    assert unique_columns(engine, "students") == {("student_no",), ("email",)}


def test_foreign_keys_exist(engine: Engine) -> None:
    assert foreign_keys(engine, "departments") == {("head_id", "teachers")}
    assert foreign_keys(engine, "teachers") == {("department_id", "departments")}
    assert foreign_keys(engine, "students") == {("department_id", "departments")}


def test_nullable_columns_match_the_spec(engine: Engine) -> None:
    def nullable(table: str) -> set[str]:
        return {c["name"] for c in inspect(engine).get_columns(table) if c["nullable"]}

    assert nullable("departments") == {"description", "building", "phone", "head_id"}
    assert nullable("teachers") == {"phone", "hire_date"}
    assert nullable("students") == {"phone", "date_of_birth"}


# ---------- Unique constraints (BR-1) ----------


def test_duplicate_department_code_is_rejected(session: Session) -> None:
    add_department(session, code="CS", name="Computer Science")
    with pytest.raises(IntegrityError, match="departments.code"):
        add_department(session, code="cs", name="Cyber Security")


def test_duplicate_department_name_is_rejected(session: Session) -> None:
    add_department(session, code="CS", name="Computer Science")
    with pytest.raises(IntegrityError, match="departments.name"):
        add_department(session, code="CSC", name="Computer Science")


def test_duplicate_teacher_email_is_rejected_case_insensitively(session: Session) -> None:
    department = add_department(session)
    add_teacher(session, department.id, email="ada@uni.edu")
    with pytest.raises(IntegrityError, match="teachers.email"):
        add_teacher(session, department.id, email="ADA@Uni.edu")


def test_duplicate_student_number_is_rejected_case_insensitively(session: Session) -> None:
    department = add_department(session)
    add_student(session, department.id, student_no="s0001", email="a@uni.edu")
    with pytest.raises(IntegrityError, match="students.student_no"):
        add_student(session, department.id, student_no="S0001", email="b@uni.edu")


def test_duplicate_student_email_is_rejected_case_insensitively(session: Session) -> None:
    department = add_department(session)
    add_student(session, department.id, student_no="S0001", email="alan@uni.edu")
    with pytest.raises(IntegrityError, match="students.email"):
        add_student(session, department.id, student_no="S0002", email="Alan@UNI.edu")


def test_codes_numbers_and_emails_are_normalized(session: Session) -> None:
    department = add_department(session, code=" cs ")
    teacher = add_teacher(session, department.id, email=" Ada@Uni.EDU ")
    student = add_student(session, department.id, student_no="s0001", email="Alan@Uni.edu")

    assert department.code == "CS"
    assert teacher.email == "ada@uni.edu"
    assert student.student_no == "S0001"
    assert student.email == "alan@uni.edu"


# ---------- Foreign keys ----------


def test_teacher_with_unknown_department_is_rejected(session: Session) -> None:
    with pytest.raises(IntegrityError, match="FOREIGN KEY"):
        add_teacher(session, department_id=999)


def test_student_with_unknown_department_is_rejected(session: Session) -> None:
    with pytest.raises(IntegrityError, match="FOREIGN KEY"):
        add_student(session, department_id=999)


def test_department_head_must_be_an_existing_teacher(session: Session) -> None:
    department = add_department(session)
    department.head_id = 999
    with pytest.raises(IntegrityError, match="FOREIGN KEY"):
        session.flush()


def test_department_with_teachers_cannot_be_deleted(session: Session) -> None:
    department = add_department(session)
    add_teacher(session, department.id)
    session.commit()

    with pytest.raises(IntegrityError, match="FOREIGN KEY"):
        session.execute(text("DELETE FROM departments WHERE id = :id"), {"id": department.id})


def test_teacher_who_heads_a_department_cannot_be_deleted(session: Session) -> None:
    department = add_department(session)
    teacher = add_teacher(session, department.id)
    department.head_id = teacher.id
    session.commit()

    with pytest.raises(IntegrityError, match="FOREIGN KEY"):
        session.execute(text("DELETE FROM teachers WHERE id = :id"), {"id": teacher.id})


# ---------- Check constraints and enums ----------


@pytest.mark.parametrize("year", [0, 7])
def test_year_outside_1_to_6_is_rejected(session: Session, year: int) -> None:
    department = add_department(session)
    with pytest.raises(IntegrityError, match="ck_students_year_range"):
        add_student(session, department.id, year=year)


@pytest.mark.parametrize("year", [1, 6])
def test_year_boundaries_are_accepted(session: Session, year: int) -> None:
    department = add_department(session)
    assert add_student(session, department.id, year=year).year == year


def test_unknown_teacher_title_is_rejected_by_the_database(session: Session) -> None:
    department = add_department(session)
    with pytest.raises(IntegrityError, match="ck_teachers_title"):
        insert_raw(
            session,
            "teachers",
            first_name="X",
            last_name="Y",
            email="x@uni.edu",
            title="dean",
            department_id=department.id,
        )


def test_unknown_student_status_is_rejected_by_the_database(session: Session) -> None:
    department = add_department(session)
    with pytest.raises(IntegrityError, match="ck_students_status"):
        insert_raw(
            session,
            "students",
            student_no="S9",
            first_name="X",
            last_name="Y",
            email="x@uni.edu",
            department_id=department.id,
            year=1,
            status="expelled",
            enrollment_date="2026-09-01",
        )


def test_enums_are_stored_as_their_lowercase_values(session: Session) -> None:
    department = add_department(session)
    teacher = add_teacher(session, department.id)
    teacher.title = TeacherTitle.ASSISTANT_PROFESSOR
    add_student(session, department.id)
    session.flush()

    assert session.execute(text("SELECT title FROM teachers")).scalar_one() == "assistant_professor"
    assert session.execute(text("SELECT status FROM students")).scalar_one() == "active"


# ---------- Relationships ----------


def test_relationships_link_departments_teachers_and_students(session: Session) -> None:
    department = add_department(session)
    teacher = add_teacher(session, department.id)
    student = add_student(session, department.id)
    session.commit()
    session.expire_all()

    assert department.teachers == [teacher]
    assert department.students == [student]
    assert teacher.department is department
    assert student.department is department


def test_department_and_its_head_can_be_created_in_one_flush(session: Session) -> None:
    department = Department(code="EE", name="Electrical Engineering")
    head = Teacher(
        first_name="Grace",
        last_name="Hopper",
        email="grace@uni.edu",
        title=TeacherTitle.PROFESSOR,
        department=department,
    )
    department.head = head
    session.add(department)
    session.commit()
    session.expire_all()

    assert department.head_id == head.id
    assert department.head is head
    assert head.department_id == department.id
