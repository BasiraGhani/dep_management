"""Schema tests for courses, enrollments and users (T1.3).

The `engine`/`session` fixtures (conftest.py) build the database with the real
Alembic migrations, so these tests cover the migrations and the models together.
"""

from datetime import date

import pytest
from sqlalchemy import Engine, func, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    Course,
    Department,
    Enrollment,
    Grade,
    Student,
    StudentStatus,
    Teacher,
    User,
    UserRole,
)
from tests.test_models_core import (
    add_department,
    add_student,
    add_teacher,
    foreign_keys,
    insert_raw,
    unique_columns,
)


def add_course(
    session: Session,
    department_id: int,
    code: str = "CS101",
    teacher_id: int | None = None,
    credits: int = 3,
    capacity: int | None = None,
) -> Course:
    course = Course(
        code=code,
        title="Intro to Programming",
        credits=credits,
        department_id=department_id,
        teacher_id=teacher_id,
    )
    if capacity is not None:
        course.capacity = capacity
    session.add(course)
    session.flush()
    return course


def add_enrollment(
    session: Session, student_id: int, course_id: int, semester: str = "2026-Fall"
) -> Enrollment:
    enrollment = Enrollment(student_id=student_id, course_id=course_id, semester=semester)
    session.add(enrollment)
    session.flush()
    return enrollment


def add_user(
    session: Session,
    username: str = "ada",
    role: UserRole = UserRole.TEACHER,
    teacher_id: int | None = None,
    student_id: int | None = None,
) -> User:
    user = User(
        username=username,
        password_hash="argon2-hash-placeholder",
        role=role,
        teacher_id=teacher_id,
        student_id=student_id,
    )
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def department(session: Session) -> Department:
    return add_department(session)


@pytest.fixture
def teacher(session: Session, department: Department) -> Teacher:
    return add_teacher(session, department.id)


@pytest.fixture
def student(session: Session, department: Department) -> Student:
    return add_student(session, department.id)


@pytest.fixture
def course(session: Session, department: Department) -> Course:
    return add_course(session, department.id)


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
    def nullable(table: str) -> set[str]:
        return {c["name"] for c in inspect(engine).get_columns(table) if c["nullable"]}

    assert nullable("courses") == {"description", "teacher_id"}
    assert nullable("enrollments") == {"grade"}
    assert nullable("users") == {"teacher_id", "student_id"}


# ---------- Courses ----------


def test_duplicate_course_code_is_rejected_case_insensitively(
    session: Session,
    department: Department,
) -> None:
    add_course(session, department.id, code="cs101")
    with pytest.raises(IntegrityError, match="courses.code"):
        add_course(session, department.id, code="CS101")


def test_course_code_is_stored_uppercase(session: Session, department: Department) -> None:
    assert add_course(session, department.id, code=" cs101 ").code == "CS101"


def test_capacity_defaults_to_40(session: Session, department: Department) -> None:
    assert add_course(session, department.id).capacity == 40


def test_capacity_database_default_is_40(session: Session, department: Department) -> None:
    insert_raw(session, "courses", code="RAW1", title="T", credits=3, department_id=department.id)
    capacity = session.execute(text("SELECT capacity FROM courses WHERE code = 'RAW1'"))
    assert capacity.scalar_one() == 40


@pytest.mark.parametrize("credits", [0, 7])
def test_credits_outside_1_to_6_are_rejected(
    session: Session,
    department: Department,
    credits: int,
) -> None:
    with pytest.raises(IntegrityError, match="ck_courses_credits_range"):
        add_course(session, department.id, credits=credits)


@pytest.mark.parametrize("credits", [1, 6])
def test_credit_boundaries_are_accepted(
    session: Session,
    department: Department,
    credits: int,
) -> None:
    assert add_course(session, department.id, credits=credits).credits == credits


def test_capacity_below_1_is_rejected(session: Session, department: Department) -> None:
    with pytest.raises(IntegrityError, match="ck_courses_capacity_positive"):
        add_course(session, department.id, capacity=0)


def test_course_with_unknown_department_is_rejected(session: Session) -> None:
    with pytest.raises(IntegrityError, match="FOREIGN KEY"):
        add_course(session, department_id=999)


def test_course_with_unknown_teacher_is_rejected(session: Session, department: Department) -> None:
    with pytest.raises(IntegrityError, match="FOREIGN KEY"):
        add_course(session, department.id, teacher_id=999)


def test_teacher_who_teaches_a_course_cannot_be_deleted(
    session: Session,
    department: Department,
    teacher: Teacher,
) -> None:
    add_course(session, department.id, teacher_id=teacher.id)
    with pytest.raises(IntegrityError, match="FOREIGN KEY"):
        session.execute(text("DELETE FROM teachers WHERE id = :id"), {"id": teacher.id})


# ---------- Enrollments: unique constraint ----------


def test_same_student_course_and_semester_is_rejected(
    session: Session,
    student: Student,
    course: Course,
) -> None:
    add_enrollment(session, student.id, course.id, "2026-Fall")
    with pytest.raises(IntegrityError, match="enrollments.student_id, enrollments.course_id"):
        add_enrollment(session, student.id, course.id, "2026-Fall")


def test_same_course_in_another_semester_is_allowed(
    session: Session,
    student: Student,
    course: Course,
) -> None:
    add_enrollment(session, student.id, course.id, "2026-Fall")
    add_enrollment(session, student.id, course.id, "2027-Spring")


def test_other_student_in_same_course_and_semester_is_allowed(
    session: Session,
    department: Department,
    student: Student,
    course: Course,
) -> None:
    other = add_student(session, department.id, student_no="S0002", email="other@uni.edu")
    add_enrollment(session, student.id, course.id)
    add_enrollment(session, other.id, course.id)


# ---------- Enrollments: cascade and foreign keys ----------


def enrollment_count(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(Enrollment)) or 0


def test_deleting_a_student_in_sql_cascades_to_enrollments(
    session: Session,
    student: Student,
    course: Course,
) -> None:
    add_enrollment(session, student.id, course.id, "2026-Fall")
    add_enrollment(session, student.id, course.id, "2027-Spring")
    session.commit()

    session.execute(text("DELETE FROM students WHERE id = :id"), {"id": student.id})
    session.commit()

    assert enrollment_count(session) == 0


def test_deleting_a_student_through_the_orm_removes_enrollments(
    session: Session,
    student: Student,
    course: Course,
) -> None:
    add_enrollment(session, student.id, course.id)
    session.commit()

    session.delete(student)
    session.commit()

    assert enrollment_count(session) == 0
    assert session.get(Course, course.id) is not None  # the course is untouched


def test_deleting_a_student_keeps_other_students_enrollments(
    session: Session,
    department: Department,
    student: Student,
    course: Course,
) -> None:
    other = add_student(session, department.id, student_no="S0002", email="other@uni.edu")
    add_enrollment(session, student.id, course.id)
    add_enrollment(session, other.id, course.id)
    session.commit()

    session.delete(student)
    session.commit()

    assert enrollment_count(session) == 1


def test_course_with_enrollments_cannot_be_deleted(
    session: Session,
    student: Student,
    course: Course,
) -> None:
    add_enrollment(session, student.id, course.id)
    session.commit()

    with pytest.raises(IntegrityError, match="FOREIGN KEY"):
        session.execute(text("DELETE FROM courses WHERE id = :id"), {"id": course.id})


def test_enrollment_with_unknown_student_or_course_is_rejected(
    session: Session,
    student: Student,
    course: Course,
) -> None:
    with pytest.raises(IntegrityError, match="FOREIGN KEY"):
        add_enrollment(session, student_id=999, course_id=course.id)
    session.rollback()
    with pytest.raises(IntegrityError, match="FOREIGN KEY"):
        add_enrollment(session, student_id=student.id, course_id=999)


# ---------- Enrollments: grades ----------


def test_grade_is_null_until_graded(session: Session, student: Student, course: Course) -> None:
    assert add_enrollment(session, student.id, course.id).grade is None


@pytest.mark.parametrize("grade", list(Grade))
def test_every_letter_grade_is_stored_as_its_letter(
    session: Session,
    student: Student,
    course: Course,
    grade: Grade,
) -> None:
    enrollment = add_enrollment(session, student.id, course.id)
    enrollment.grade = grade
    session.flush()

    stored = session.execute(text("SELECT grade FROM enrollments")).scalar_one()
    assert stored == grade.value


def test_unknown_grade_is_rejected_by_the_database(
    session: Session,
    student: Student,
    course: Course,
) -> None:
    with pytest.raises(IntegrityError, match="ck_enrollments_grade"):
        insert_raw(
            session,
            "enrollments",
            student_id=student.id,
            course_id=course.id,
            semester="2026-Fall",
            grade="E",
        )


# ---------- Users ----------


def test_duplicate_username_is_rejected_case_insensitively(session: Session) -> None:
    add_user(session, username="ada", role=UserRole.ADMIN)
    with pytest.raises(IntegrityError, match="users.username"):
        add_user(session, username="ADA", role=UserRole.ADMIN)


def test_username_is_stored_lowercase(session: Session) -> None:
    assert add_user(session, username=" Ada.Lovelace ", role=UserRole.ADMIN).username == (
        "ada.lovelace"
    )


def test_a_teacher_can_have_only_one_account(session: Session, teacher: Teacher) -> None:
    add_user(session, username="one", teacher_id=teacher.id)
    with pytest.raises(IntegrityError, match="users.teacher_id"):
        add_user(session, username="two", teacher_id=teacher.id)


def test_a_student_can_have_only_one_account(session: Session, student: Student) -> None:
    add_user(session, username="one", role=UserRole.STUDENT, student_id=student.id)
    with pytest.raises(IntegrityError, match="users.student_id"):
        add_user(session, username="two", role=UserRole.STUDENT, student_id=student.id)


def test_many_accounts_without_links_are_allowed(session: Session) -> None:
    add_user(session, username="admin1", role=UserRole.ADMIN)
    add_user(session, username="admin2", role=UserRole.ADMIN)


def test_user_links_must_point_to_existing_records(session: Session) -> None:
    with pytest.raises(IntegrityError, match="FOREIGN KEY"):
        add_user(session, username="ghost-teacher", teacher_id=999)
    session.rollback()
    with pytest.raises(IntegrityError, match="FOREIGN KEY"):
        add_user(session, username="ghost-student", role=UserRole.STUDENT, student_id=999)


def test_new_users_are_active_by_default(session: Session) -> None:
    assert add_user(session, role=UserRole.ADMIN).is_active is True


def test_is_active_database_default_is_true(session: Session) -> None:
    insert_raw(session, "users", username="raw", password_hash="h", role="admin")
    is_active = session.execute(text("SELECT is_active FROM users WHERE username = 'raw'"))
    assert bool(is_active.scalar_one()) is True


def test_unknown_role_is_rejected_by_the_database(session: Session) -> None:
    with pytest.raises(IntegrityError, match="ck_users_role"):
        insert_raw(session, "users", username="x", password_hash="h", role="superuser")


@pytest.mark.parametrize("role", list(UserRole))
def test_roles_are_stored_as_lowercase_values(session: Session, role: UserRole) -> None:
    add_user(session, username=f"user-{role.value}", role=role)
    stored = session.execute(text("SELECT role FROM users")).scalar_one()
    assert stored == role.value


# ---------- Relationships ----------


def test_course_relationships(
    session: Session,
    department: Department,
    teacher: Teacher,
    student: Student,
) -> None:
    course = add_course(session, department.id, teacher_id=teacher.id)
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


def test_user_links_to_teacher_and_student(
    session: Session,
    teacher: Teacher,
    student: Student,
) -> None:
    teacher_user = add_user(session, username="t", teacher_id=teacher.id)
    student_user = add_user(session, username="s", role=UserRole.STUDENT, student_id=student.id)
    session.commit()
    session.expire_all()

    assert teacher_user.teacher is teacher
    assert teacher.user is teacher_user
    assert student_user.student is student
    assert student.user is student_user


def test_records_without_an_account_have_no_user(
    session: Session,
    teacher: Teacher,
    student: Student,
) -> None:
    assert teacher.user is None
    assert student.user is None


def test_status_enum_still_round_trips(session: Session, student: Student) -> None:
    student.status = StudentStatus.GRADUATED
    student.enrollment_date = date(2020, 9, 1)
    session.commit()
    session.expire_all()
    assert student.status is StudentStatus.GRADUATED
