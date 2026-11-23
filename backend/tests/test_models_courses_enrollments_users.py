"""Schema tests for courses, enrollments and users (T1.3).

The `engine` / `session` fixtures (conftest.py) use a database built with the real
Alembic migrations, so these tests cover the migrations and the models together.
"""

import pytest
from sqlalchemy import Engine, func, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Course, Enrollment, Grade, Student, StudentStatus, UserRole
from tests.conftest import Factory
from tests.helpers import foreign_keys, insert_raw, nullable_columns, unique_columns


def add_enrollment(
    session: Session, student_id: int, course_id: int, semester: str = "2026-Fall"
) -> Enrollment:
    """Create and flush an enrollment (no factory yet: enrollments arrive in T4.1)."""
    enrollment = Enrollment(student_id=student_id, course_id=course_id, semester=semester)
    session.add(enrollment)
    session.flush()
    return enrollment


def enrollment_count(session: Session, course_id: int) -> int:
    query = select(func.count()).select_from(Enrollment).where(Enrollment.course_id == course_id)
    return session.scalar(query) or 0


# ---------- Schema created by the migrations ----------


def test_unique_constraints_exist(engine: Engine) -> None:
    assert unique_columns(engine, "courses") == {("code",)}
    assert unique_columns(engine, "enrollments") == {("student_id", "course_id", "semester")}
    assert unique_columns(engine, "users") == {("username",), ("teacher_id",), ("student_id",)}


def test_foreign_keys_exist(engine: Engine) -> None:
    assert foreign_keys(engine, "courses") == {
        ("department_id", "departments"),
        ("teacher_id", "teachers"),
    }
    assert foreign_keys(engine, "enrollments") == {
        ("student_id", "students"),
        ("course_id", "courses"),
    }
    assert foreign_keys(engine, "users") == {
        ("teacher_id", "teachers"),
        ("student_id", "students"),
    }


def test_only_enrollment_student_fk_cascades_on_delete(engine: Engine) -> None:
    on_delete = {
        (table, fk["constrained_columns"][0]): fk["options"].get("ondelete")
        for table in ("courses", "enrollments", "users")
        for fk in inspect(engine).get_foreign_keys(table)
    }

    assert on_delete.pop(("enrollments", "student_id")) == "CASCADE"
    assert set(on_delete.values()) == {None}


def test_nullable_columns_match_the_spec(engine: Engine) -> None:
    assert nullable_columns(engine, "courses") == {"description", "teacher_id"}
    assert nullable_columns(engine, "enrollments") == {"grade"}
    assert nullable_columns(engine, "users") == {"teacher_id", "student_id"}


# ---------- Courses ----------


def test_duplicate_course_code_is_rejected_case_insensitively(factory: Factory) -> None:
    factory.course(code="cs101")
    with pytest.raises(IntegrityError, match="courses.code"):
        factory.course(code="CS101")


def test_course_code_is_stored_uppercase(factory: Factory) -> None:
    assert factory.course(code=" cs101 ").code == "CS101"


def test_capacity_defaults_to_40(factory: Factory) -> None:
    assert factory.course().capacity == 40


def test_capacity_database_default_is_40(session: Session, factory: Factory) -> None:
    department = factory.department()
    insert_raw(session, "courses", code="RAW1", title="T", credits=3, department_id=department.id)
    capacity = session.execute(text("SELECT capacity FROM courses WHERE code = 'RAW1'"))
    assert capacity.scalar_one() == 40


@pytest.mark.parametrize("credits", [0, 7])
def test_credits_outside_1_to_6_are_rejected(factory: Factory, credits: int) -> None:
    with pytest.raises(IntegrityError, match="ck_courses_credits_range"):
        factory.course(credits=credits)


@pytest.mark.parametrize("credits", [1, 6])
def test_credit_boundaries_are_accepted(factory: Factory, credits: int) -> None:
    assert factory.course(credits=credits).credits == credits


def test_capacity_below_1_is_rejected(factory: Factory) -> None:
    with pytest.raises(IntegrityError, match="ck_courses_capacity_positive"):
        factory.course(capacity=0)


def test_course_with_unknown_department_is_rejected(factory: Factory) -> None:
    with pytest.raises(IntegrityError, match="FOREIGN KEY"):
        factory.course(department_id=999_999)


def test_course_with_unknown_teacher_is_rejected(factory: Factory) -> None:
    with pytest.raises(IntegrityError, match="FOREIGN KEY"):
        factory.course(teacher_id=999_999)


def test_teacher_who_teaches_a_course_cannot_be_deleted(session: Session, factory: Factory) -> None:
    teacher = factory.teacher()
    factory.course(teacher.department, teacher=teacher)
    with pytest.raises(IntegrityError, match="FOREIGN KEY"):
        session.execute(text("DELETE FROM teachers WHERE id = :id"), {"id": teacher.id})


# ---------- Enrollments: unique constraint ----------


def test_same_student_course_and_semester_is_rejected(session: Session, factory: Factory) -> None:
    student, course = factory.student(), factory.course()
    add_enrollment(session, student.id, course.id, "2026-Fall")
    with pytest.raises(IntegrityError, match="enrollments.student_id, enrollments.course_id"):
        add_enrollment(session, student.id, course.id, "2026-Fall")


def test_same_course_in_another_semester_is_allowed(session: Session, factory: Factory) -> None:
    student, course = factory.student(), factory.course()
    add_enrollment(session, student.id, course.id, "2026-Fall")
    add_enrollment(session, student.id, course.id, "2027-Spring")


def test_other_student_in_same_course_and_semester_is_allowed(
    session: Session, factory: Factory
) -> None:
    course = factory.course()
    add_enrollment(session, factory.student().id, course.id)
    add_enrollment(session, factory.student().id, course.id)


# ---------- Enrollments: cascade and foreign keys ----------


def test_deleting_a_student_in_sql_cascades_to_enrollments(
    session: Session, factory: Factory
) -> None:
    student, course = factory.student(), factory.course()
    add_enrollment(session, student.id, course.id, "2026-Fall")
    add_enrollment(session, student.id, course.id, "2027-Spring")
    session.commit()

    session.execute(text("DELETE FROM students WHERE id = :id"), {"id": student.id})
    session.commit()

    assert enrollment_count(session, course.id) == 0


def test_deleting_a_student_through_the_orm_removes_enrollments(
    session: Session, factory: Factory
) -> None:
    student, course = factory.student(), factory.course()
    add_enrollment(session, student.id, course.id)
    session.commit()

    session.delete(student)
    session.commit()

    assert enrollment_count(session, course.id) == 0
    assert session.get(Course, course.id) is not None  # the course is untouched


def test_deleting_a_student_keeps_other_students_enrollments(
    session: Session, factory: Factory
) -> None:
    student, other, course = factory.student(), factory.student(), factory.course()
    add_enrollment(session, student.id, course.id)
    add_enrollment(session, other.id, course.id)
    session.commit()

    session.delete(student)
    session.commit()

    assert enrollment_count(session, course.id) == 1


def test_course_with_enrollments_cannot_be_deleted(session: Session, factory: Factory) -> None:
    course = factory.course()
    add_enrollment(session, factory.student().id, course.id)
    session.commit()

    with pytest.raises(IntegrityError, match="FOREIGN KEY"):
        session.execute(text("DELETE FROM courses WHERE id = :id"), {"id": course.id})


def test_enrollment_with_unknown_student_or_course_is_rejected(
    session: Session, factory: Factory
) -> None:
    student, course = factory.student(), factory.course()
    session.commit()

    with pytest.raises(IntegrityError, match="FOREIGN KEY"):
        add_enrollment(session, student_id=999_999, course_id=course.id)
    session.rollback()
    with pytest.raises(IntegrityError, match="FOREIGN KEY"):
        add_enrollment(session, student_id=student.id, course_id=999_999)


# ---------- Enrollments: grades ----------


def test_grade_is_null_until_graded(session: Session, factory: Factory) -> None:
    assert add_enrollment(session, factory.student().id, factory.course().id).grade is None


@pytest.mark.parametrize("grade", list(Grade))
def test_every_letter_grade_is_stored_as_its_letter(
    session: Session, factory: Factory, grade: Grade
) -> None:
    enrollment = add_enrollment(session, factory.student().id, factory.course().id)
    enrollment.grade = grade
    session.flush()

    stored = session.execute(
        text("SELECT grade FROM enrollments WHERE id = :id"), {"id": enrollment.id}
    ).scalar_one()
    assert stored == grade.value


def test_unknown_grade_is_rejected_by_the_database(session: Session, factory: Factory) -> None:
    with pytest.raises(IntegrityError, match="ck_enrollments_grade"):
        insert_raw(
            session,
            "enrollments",
            student_id=factory.student().id,
            course_id=factory.course().id,
            semester="2026-Fall",
            grade="E",
        )


# ---------- Users ----------


def test_duplicate_username_is_rejected_case_insensitively(factory: Factory) -> None:
    factory.user(username="ada")
    with pytest.raises(IntegrityError, match="users.username"):
        factory.user(username="ADA")


def test_username_is_stored_lowercase(factory: Factory) -> None:
    assert factory.user(username=" Ada.Lovelace ").username == "ada.lovelace"


def test_a_teacher_can_have_only_one_account(factory: Factory) -> None:
    teacher = factory.teacher()
    factory.user(UserRole.TEACHER, teacher=teacher)
    with pytest.raises(IntegrityError, match="users.teacher_id"):
        factory.user(UserRole.TEACHER, teacher=teacher)


def test_a_student_can_have_only_one_account(factory: Factory) -> None:
    student = factory.student()
    factory.user(UserRole.STUDENT, student=student)
    with pytest.raises(IntegrityError, match="users.student_id"):
        factory.user(UserRole.STUDENT, student=student)


def test_many_accounts_without_links_are_allowed(factory: Factory) -> None:
    factory.user(UserRole.ADMIN)
    factory.user(UserRole.ADMIN)


def test_user_links_must_point_to_existing_records(session: Session, factory: Factory) -> None:
    with pytest.raises(IntegrityError, match="FOREIGN KEY"):
        factory.user(UserRole.TEACHER, teacher_id=999_999)
    session.rollback()
    with pytest.raises(IntegrityError, match="FOREIGN KEY"):
        factory.user(UserRole.STUDENT, student_id=999_999)


def test_new_users_are_active_by_default(factory: Factory) -> None:
    assert factory.user().is_active is True


def test_is_active_database_default_is_true(session: Session) -> None:
    insert_raw(session, "users", username="raw", password_hash="h", role="admin")
    is_active = session.execute(text("SELECT is_active FROM users WHERE username = 'raw'"))
    assert bool(is_active.scalar_one()) is True


def test_unknown_role_is_rejected_by_the_database(session: Session) -> None:
    with pytest.raises(IntegrityError, match="ck_users_role"):
        insert_raw(session, "users", username="x", password_hash="h", role="superuser")


@pytest.mark.parametrize("role", list(UserRole))
def test_roles_are_stored_as_lowercase_values(
    session: Session, factory: Factory, role: UserRole
) -> None:
    user = factory.user(role)
    stored = session.execute(
        text("SELECT role FROM users WHERE id = :id"), {"id": user.id}
    ).scalar_one()
    assert stored == role.value


# ---------- Relationships ----------


def test_course_relationships(session: Session, factory: Factory) -> None:
    department = factory.department()
    teacher = factory.teacher(department)
    student = factory.student(department)
    course = factory.course(department, teacher=teacher)
    enrollment = add_enrollment(session, student.id, course.id)
    session.commit()
    session.expire_all()

    assert course.department is department
    assert course.teacher is teacher
    assert department.courses == [course]
    assert teacher.courses == [course]
    assert course.enrollments == [enrollment]
    assert student.enrollments == [enrollment]
    assert enrollment.student is student
    assert enrollment.course is course


def test_user_links_to_teacher_and_student(session: Session, factory: Factory) -> None:
    teacher, student = factory.teacher(), factory.student()
    teacher_user = factory.user(UserRole.TEACHER, teacher=teacher)
    student_user = factory.user(UserRole.STUDENT, student=student)
    session.commit()
    session.expire_all()

    assert teacher_user.teacher is teacher
    assert teacher.user is teacher_user
    assert student_user.student is student
    assert student.user is student_user


def test_records_without_an_account_have_no_user(factory: Factory) -> None:
    assert factory.teacher().user is None
    assert factory.student().user is None


def test_status_enum_round_trips(session: Session, factory: Factory) -> None:
    student: Student = factory.student(status=StudentStatus.GRADUATED)
    session.commit()
    session.expire_all()
    assert student.status is StudentStatus.GRADUATED
