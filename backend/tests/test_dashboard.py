"""Tests for GET /dashboard (T4.5, FR-7.1–FR-7.4).

Two kinds of checks:
* a small hand-built world with exact expected numbers, and
* the real `seed-demo` dataset, compared against independent SQL counts.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.cli import seed_demo
from app.models import Course, Department, Grade, Student, User, UserRole
from tests.conftest import Factory
from tests.helpers import auth_headers

URL = "/api/v1/dashboard"


@dataclass
class World:
    dept_a: Department
    dept_b: Department
    a1: Course
    a2: Course
    alice: Student
    admin: User
    hod: User
    teacher: User
    student: User


@pytest.fixture
def world(session: Session, factory: Factory) -> World:
    """dept A: head HA + teacher TA, students alice/carl/ed, courses A1 and A2;
    dept B: teacher TB, student dana, course B1; dept C: empty.

    A1 (4 credits, TA): alice (A), carl (ungraded), ed (ungraded)
    A2 (3 credits, HA): alice (B+)
    B1 (2 credits, TB): dana (ungraded)
    Enrollments are created one day apart in that order (A1 first, B1 last).
    """
    dept_a = factory.department(code="DEPA", name="Department A")
    dept_b = factory.department(code="DEPB", name="Department B")
    factory.department(code="DEPC", name="Department C")
    head_a, teacher_a = factory.teacher(dept_a), factory.teacher(dept_a)
    dept_a.head_id = head_a.id
    teacher_b = factory.teacher(dept_b)
    a1 = factory.course(dept_a, teacher=teacher_a, code="A1", credits=4, capacity=30)
    a2 = factory.course(dept_a, teacher=head_a, code="A2", credits=3)
    b1 = factory.course(dept_b, teacher=teacher_b, code="B1", credits=2)
    alice, carl, ed = factory.student(dept_a), factory.student(dept_a), factory.student(dept_a)
    dana = factory.student(dept_b)
    base = datetime(2026, 9, 1, tzinfo=UTC)
    for i, (student, course, grade) in enumerate(
        [
            (alice, a1, Grade.A),
            (carl, a1, None),
            (ed, a1, None),
            (alice, a2, Grade.B_PLUS),
            (dana, b1, None),
        ]
    ):
        factory.enrollment(student, course, grade=grade, created_at=base + timedelta(days=i))
    world = World(
        dept_a=dept_a,
        dept_b=dept_b,
        a1=a1,
        a2=a2,
        alice=alice,
        admin=factory.user(UserRole.ADMIN),
        hod=factory.user(UserRole.HOD, teacher=head_a),
        teacher=factory.user(UserRole.TEACHER, teacher=teacher_a),
        student=factory.user(UserRole.STUDENT, student=alice),
    )
    session.commit()
    return world


def get(client: TestClient, user: User) -> dict[str, Any]:
    response = client.get(URL, headers=auth_headers(user))
    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    return body


# ===================================================== small world, exact numbers


def test_dashboard_requires_authentication(client: TestClient, world: World) -> None:
    assert client.get(URL).status_code == 401


def test_admin_dashboard(client: TestClient, world: World) -> None:
    body = get(client, world.admin)

    assert body["role"] == "admin"
    assert body["totals"] == {"departments": 3, "teachers": 3, "students": 4, "courses": 3}
    assert body["students_per_department"] == [
        {"department_id": world.dept_a.id, "code": "DEPA", "name": "Department A", "students": 3},
        {"department_id": world.dept_b.id, "code": "DEPB", "name": "Department B", "students": 1},
        {
            "department_id": world.dept_b.id + 1,
            "code": "DEPC",
            "name": "Department C",
            "students": 0,
        },
    ]
    recent = body["recent_enrollments"]
    assert [(e["course"]["code"], e["grade"]) for e in recent] == [
        ("B1", None),
        ("A2", "B+"),
        ("A1", None),
        ("A1", None),
        ("A1", "A"),
    ]  # newest first


def test_recent_enrollments_are_capped_at_10(
    client: TestClient, factory: Factory, world: World
) -> None:
    for _ in range(12):
        factory.enrollment(course=world.a2)

    assert len(get(client, world.admin)["recent_enrollments"]) == 10


def test_hod_dashboard_covers_only_their_department(client: TestClient, world: World) -> None:
    body = get(client, world.hod)

    assert body["role"] == "hod"
    assert body["department"] == {"id": world.dept_a.id, "code": "DEPA", "name": "Department A"}
    assert body["totals"] == {"departments": 1, "teachers": 2, "students": 3, "courses": 2}
    assert body["students_per_department"] == [
        {"department_id": world.dept_a.id, "code": "DEPA", "name": "Department A", "students": 3}
    ]
    recent = body["recent_enrollments"]
    assert {e["course"]["code"] for e in recent} == {"A1", "A2"}
    assert len(recent) == 4


def test_hod_whose_head_role_is_stale_gets_an_empty_dashboard(
    client: TestClient, session: Session, factory: Factory, world: World
) -> None:
    world.dept_a.head_id = factory.teacher(world.dept_a).id
    session.commit()

    body = get(client, world.hod)

    assert body["department"] is None
    assert body["totals"] == {"departments": 0, "teachers": 0, "students": 0, "courses": 0}
    assert body["students_per_department"] == body["recent_enrollments"] == []


def test_teacher_dashboard_lists_their_courses_with_counts(
    client: TestClient, factory: Factory, world: World
) -> None:
    assert world.teacher.teacher is not None
    empty = factory.course(world.dept_a, teacher=world.teacher.teacher, code="A9", capacity=12)

    body = get(client, world.teacher)

    assert body["role"] == "teacher"
    assert [
        (c["course"]["code"], c["capacity"], c["enrolled"], c["ungraded"]) for c in body["courses"]
    ] == [("A1", 30, 3, 2), ("A9", 12, 0, 0)]
    assert empty.id in {c["course"]["id"] for c in body["courses"]}


def test_teacher_without_courses_has_an_empty_list(
    client: TestClient, factory: Factory, world: World
) -> None:
    idle = factory.user(UserRole.TEACHER, teacher=factory.teacher(world.dept_b))
    assert get(client, idle) == {"role": "teacher", "courses": []}


def test_student_dashboard_has_enrollments_grades_and_gpa(client: TestClient, world: World) -> None:
    body = get(client, world.student)

    assert body["role"] == "student"
    assert [(e["course"]["code"], e["grade"]) for e in body["enrollments"]] == [
        ("A1", "A"),
        ("A2", "B+"),
    ]
    assert body["gpa"] == 3.7  # (4.0 x 4 + 3.3 x 3) / 7 = 3.7
    assert body["graded_credits"] == 7


def test_student_with_nothing_graded_has_no_gpa(
    client: TestClient, factory: Factory, world: World
) -> None:
    new = factory.user(UserRole.STUDENT, student=factory.student(world.dept_a))
    assert get(client, new) == {
        "role": "student",
        "enrollments": [],
        "gpa": None,
        "graded_credits": 0,
    }


# ===================================================== seed-demo data vs independent SQL


@pytest.fixture
def demo(session: Session) -> dict[str, User]:
    """The seed-demo dataset; returns its four logins by role."""
    seed_demo(session)
    users = session.query(User).filter(User.username.like("demo.%")).all()
    return {u.role.value: u for u in users}


def sql(session: Session, query: str, **params: object) -> int:
    return int(session.execute(text(query), params).scalar_one())


def test_admin_figures_match_the_seeded_data(
    client: TestClient, session: Session, demo: dict[str, User]
) -> None:
    body = get(client, demo["admin"])

    assert (
        body["totals"]
        == {
            "departments": sql(session, "SELECT count(*) FROM departments"),
            "teachers": sql(session, "SELECT count(*) FROM teachers"),
            "students": sql(session, "SELECT count(*) FROM students"),
            "courses": sql(session, "SELECT count(*) FROM courses"),
        }
        == {"departments": 3, "teachers": 10, "students": 60, "courses": 12}
    )
    for bar in body["students_per_department"]:
        expected = sql(
            session,
            "SELECT count(*) FROM students WHERE department_id = :d",
            d=bar["department_id"],
        )
        assert bar["students"] == expected == 20


def test_hod_figures_match_the_seeded_data(
    client: TestClient, session: Session, demo: dict[str, User]
) -> None:
    body = get(client, demo["hod"])
    dept = sql(
        session,
        "SELECT d.id FROM departments d JOIN users u ON u.teacher_id = d.head_id "
        "WHERE u.username = 'demo.hod'",
    )

    assert body["department"]["code"] == "CS"
    assert body["totals"] == {
        "departments": 1,
        "teachers": sql(session, "SELECT count(*) FROM teachers WHERE department_id = :d", d=dept),
        "students": sql(session, "SELECT count(*) FROM students WHERE department_id = :d", d=dept),
        "courses": sql(session, "SELECT count(*) FROM courses WHERE department_id = :d", d=dept),
    }
    for enrollment in body["recent_enrollments"]:
        course_dept = sql(
            session, "SELECT department_id FROM courses WHERE id = :c", c=enrollment["course_id"]
        )
        assert course_dept == dept


def test_teacher_figures_match_the_seeded_data(
    client: TestClient, session: Session, demo: dict[str, User]
) -> None:
    body = get(client, demo["teacher"])

    assert body["courses"]
    for stats in body["courses"]:
        course_id = stats["course"]["id"]
        assert stats["enrolled"] == sql(
            session, "SELECT count(*) FROM enrollments WHERE course_id = :c", c=course_id
        )
        assert stats["ungraded"] == sql(
            session,
            "SELECT count(*) FROM enrollments WHERE course_id = :c AND grade IS NULL",
            c=course_id,
        )
    taught = sql(
        session,
        "SELECT count(*) FROM courses c JOIN users u ON u.teacher_id = c.teacher_id "
        "WHERE u.username = 'demo.teacher'",
    )
    assert len(body["courses"]) == taught


def test_student_figures_match_the_seeded_data(
    client: TestClient, session: Session, demo: dict[str, User]
) -> None:
    student_id = demo["student"].student_id
    body = get(client, demo["student"])

    assert len(body["enrollments"]) == sql(
        session, "SELECT count(*) FROM enrollments WHERE student_id = :s", s=student_id
    )
    points = {"A": 4.0, "A-": 3.7, "B+": 3.3, "B": 3.0, "B-": 2.7}
    points |= {"C+": 2.3, "C": 2.0, "C-": 1.7, "D": 1.0, "F": 0.0}
    graded = session.execute(
        text(
            "SELECT e.grade, c.credits FROM enrollments e JOIN courses c ON c.id = e.course_id "
            "WHERE e.student_id = :s AND e.grade IS NOT NULL"
        ),
        {"s": student_id},
    ).all()
    credits = sum(c for _, c in graded)
    assert body["graded_credits"] == credits
    assert body["gpa"] == round(sum(points[g] * c for g, c in graded) / credits + 1e-9, 2)
