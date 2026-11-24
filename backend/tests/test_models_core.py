"""Schema tests for departments, teachers and students (T1.2).

The `engine` / `session` fixtures (conftest.py) use a database built with the real
Alembic migrations, so these tests cover the migrations and the models together.
"""

from datetime import date

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Department, Teacher, TeacherTitle
from tests.conftest import Factory
from tests.helpers import (
    FK_VIOLATION,
    foreign_keys,
    insert_raw,
    nullable_columns,
    unique_columns,
    unique_violation,
)

# ---------- Schema created by the migration ----------


def test_unique_constraints_exist(engine: Engine) -> None:
    assert unique_columns(engine, "departments") == {("code",), ("name",)}
    assert unique_columns(engine, "teachers") == {("email",)}
    assert unique_columns(engine, "students") == {("student_no",), ("email",)}


def test_foreign_keys_exist(engine: Engine) -> None:
    assert foreign_keys(engine, "departments") == {("head_id", "teachers")}
    assert foreign_keys(engine, "teachers") == {("department_id", "departments")}
    assert foreign_keys(engine, "students") == {("department_id", "departments")}


def test_nullable_columns_match_the_spec(engine: Engine) -> None:
    assert nullable_columns(engine, "departments") == {
        "description",
        "building",
        "phone",
        "head_id",
    }
    assert nullable_columns(engine, "teachers") == {"phone", "hire_date"}
    assert nullable_columns(engine, "students") == {"phone", "date_of_birth"}


# ---------- Unique constraints (BR-1) ----------


def test_duplicate_department_code_is_rejected(factory: Factory) -> None:
    factory.department(code="CS")
    with pytest.raises(IntegrityError, match=unique_violation("departments", "code")):
        factory.department(code="cs")


def test_duplicate_department_name_is_rejected(factory: Factory) -> None:
    factory.department(name="Computer Science")
    with pytest.raises(IntegrityError, match=unique_violation("departments", "name")):
        factory.department(name="Computer Science")


def test_duplicate_teacher_email_is_rejected_case_insensitively(factory: Factory) -> None:
    factory.teacher(email="ada@uni.edu")
    with pytest.raises(IntegrityError, match=unique_violation("teachers", "email")):
        factory.teacher(email="ADA@Uni.edu")


def test_duplicate_student_number_is_rejected_case_insensitively(factory: Factory) -> None:
    factory.student(student_no="s0001")
    with pytest.raises(IntegrityError, match=unique_violation("students", "student_no")):
        factory.student(student_no="S0001")


def test_duplicate_student_email_is_rejected_case_insensitively(factory: Factory) -> None:
    factory.student(email="alan@uni.edu")
    with pytest.raises(IntegrityError, match=unique_violation("students", "email")):
        factory.student(email="Alan@UNI.edu")


def test_codes_numbers_and_emails_are_normalized(factory: Factory) -> None:
    assert factory.department(code=" cs ").code == "CS"
    assert factory.teacher(email=" Ada@Uni.EDU ").email == "ada@uni.edu"
    student = factory.student(student_no="s0001", email="Alan@Uni.edu")
    assert student.student_no == "S0001"
    assert student.email == "alan@uni.edu"


# ---------- Foreign keys ----------


def test_teacher_with_unknown_department_is_rejected(factory: Factory) -> None:
    with pytest.raises(IntegrityError, match=FK_VIOLATION):
        factory.teacher(department_id=999_999)


def test_student_with_unknown_department_is_rejected(factory: Factory) -> None:
    with pytest.raises(IntegrityError, match=FK_VIOLATION):
        factory.student(department_id=999_999)


def test_department_head_must_be_an_existing_teacher(session: Session, factory: Factory) -> None:
    department = factory.department()
    department.head_id = 999_999
    with pytest.raises(IntegrityError, match=FK_VIOLATION):
        session.flush()


def test_department_with_teachers_cannot_be_deleted(session: Session, factory: Factory) -> None:
    department = factory.department()
    factory.teacher(department)
    session.commit()

    with pytest.raises(IntegrityError, match=FK_VIOLATION):
        session.execute(text("DELETE FROM departments WHERE id = :id"), {"id": department.id})


def test_teacher_who_heads_a_department_cannot_be_deleted(
    session: Session, factory: Factory
) -> None:
    department = factory.department()
    teacher = factory.teacher(department)
    department.head_id = teacher.id
    session.commit()

    with pytest.raises(IntegrityError, match=FK_VIOLATION):
        session.execute(text("DELETE FROM teachers WHERE id = :id"), {"id": teacher.id})


# ---------- Check constraints and enums ----------


@pytest.mark.parametrize("year", [0, 7])
def test_year_outside_1_to_6_is_rejected(factory: Factory, year: int) -> None:
    with pytest.raises(IntegrityError, match="ck_students_year_range"):
        factory.student(year=year)


@pytest.mark.parametrize("year", [1, 6])
def test_year_boundaries_are_accepted(factory: Factory, year: int) -> None:
    assert factory.student(year=year).year == year


def test_unknown_teacher_title_is_rejected_by_the_database(
    session: Session, factory: Factory
) -> None:
    department = factory.department()
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


def test_unknown_student_status_is_rejected_by_the_database(
    session: Session, factory: Factory
) -> None:
    department = factory.department()
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


def test_enums_are_stored_as_their_lowercase_values(session: Session, factory: Factory) -> None:
    teacher = factory.teacher(title=TeacherTitle.ASSISTANT_PROFESSOR)
    student = factory.student()

    stored_title = session.execute(
        text("SELECT title FROM teachers WHERE id = :id"), {"id": teacher.id}
    ).scalar_one()
    stored_status = session.execute(
        text("SELECT status FROM students WHERE id = :id"), {"id": student.id}
    ).scalar_one()
    assert stored_title == "assistant_professor"
    assert stored_status == "active"


# ---------- Relationships ----------


def test_relationships_link_departments_teachers_and_students(
    session: Session, factory: Factory
) -> None:
    department = factory.department()
    teacher = factory.teacher(department)
    student = factory.student(department)
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
        hire_date=date(2020, 1, 1),
        department=department,
    )
    department.head = head
    session.add(department)
    session.commit()
    session.expire_all()

    assert department.head_id == head.id
    assert department.head is head
    assert head.department_id == department.id
