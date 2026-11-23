"""Tests for grading (T4.2): PATCH /enrollments/{id}/grade, PUT /courses/{id}/grades
(all-or-nothing) and the GPA in the student detail (FR-6.5–FR-6.7).

`world`:
    dept A: head HA (`hod`) teaches A2; TA (`teacher`) teaches A1 (4 credits)
    dept B: TB (`teacher_b`) teaches B1 (2 credits)
    enrollments (all ungraded): alice-A1, bob-A1, alice-B1, bob-A2
    plus `admin` and `student` (alice) logins
"""

from dataclasses import dataclass
from typing import cast

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Course, Enrollment, Grade, Student, User, UserRole
from tests.conftest import Factory
from tests.helpers import auth_headers


@dataclass
class World:
    a1: Course
    a2: Course
    b1: Course
    alice: Student
    bob: Student
    alice_a1: Enrollment
    bob_a1: Enrollment
    alice_b1: Enrollment
    bob_a2: Enrollment
    admin: User
    hod: User
    teacher: User
    teacher_b: User
    student: User

    def user(self, role: str) -> User:
        return cast(User, getattr(self, role))

    def get(self, name: str) -> Enrollment:
        return cast(Enrollment, getattr(self, name))


@pytest.fixture
def world(session: Session, factory: Factory) -> World:
    dept_a, dept_b = factory.department(), factory.department()
    head_a, teacher_a = factory.teacher(dept_a), factory.teacher(dept_a)
    dept_a.head_id = head_a.id
    teacher_b = factory.teacher(dept_b)
    a1 = factory.course(dept_a, teacher=teacher_a, code="A1", credits=4)
    a2 = factory.course(dept_a, teacher=head_a, code="A2", credits=3)
    b1 = factory.course(dept_b, teacher=teacher_b, code="B1", credits=2)
    alice, bob = factory.student(dept_a), factory.student(dept_a)
    world = World(
        a1=a1,
        a2=a2,
        b1=b1,
        alice=alice,
        bob=bob,
        alice_a1=factory.enrollment(alice, a1),
        bob_a1=factory.enrollment(bob, a1),
        alice_b1=factory.enrollment(alice, b1),
        bob_a2=factory.enrollment(bob, a2),
        admin=factory.user(UserRole.ADMIN),
        hod=factory.user(UserRole.HOD, teacher=head_a),
        teacher=factory.user(UserRole.TEACHER, teacher=teacher_a),
        teacher_b=factory.user(UserRole.TEACHER, teacher=teacher_b),
        student=factory.user(UserRole.STUDENT, student=alice),
    )
    session.commit()
    return world


def set_grade(
    client: TestClient, user: User, enrollment: Enrollment, grade: object
) -> httpx.Response:
    response: httpx.Response = client.patch(
        f"/api/v1/enrollments/{enrollment.id}/grade",
        json={"grade": grade},
        headers=auth_headers(user),
    )
    return response


def bulk(client: TestClient, user: User, course: Course, rows: object) -> httpx.Response:
    response: httpx.Response = client.put(
        f"/api/v1/courses/{course.id}/grades", json=rows, headers=auth_headers(user)
    )
    return response


def grades(session: Session, *enrollments: Enrollment) -> list[Grade | None]:
    for enrollment in enrollments:
        session.refresh(enrollment)
    return [e.grade for e in enrollments]


# ======================================== PATCH /enrollments/{id}/grade


def test_teacher_grades_an_enrollment_of_their_course(
    client: TestClient, session: Session, world: World
) -> None:
    response = set_grade(client, world.teacher, world.alice_a1, "A-")

    assert response.status_code == 200
    assert response.json()["grade"] == "A-"
    assert response.json()["course"]["code"] == "A1"
    assert grades(session, world.alice_a1) == [Grade.A_MINUS]


@pytest.mark.parametrize("letter", [g.value for g in Grade])
def test_every_letter_grade_is_accepted(client: TestClient, world: World, letter: str) -> None:
    assert set_grade(client, world.teacher, world.alice_a1, letter).json()["grade"] == letter


def test_grade_can_be_cleared(client: TestClient, session: Session, world: World) -> None:
    set_grade(client, world.teacher, world.alice_a1, "B")

    response = set_grade(client, world.teacher, world.alice_a1, None)

    assert response.json()["grade"] is None
    assert grades(session, world.alice_a1) == [None]


@pytest.mark.parametrize("bad", ["E", "a", "A+", "", 4.0])
def test_invalid_grades_are_rejected(client: TestClient, world: World, bad: object) -> None:
    assert set_grade(client, world.teacher, world.alice_a1, bad).status_code == 422


@pytest.mark.parametrize("body", [{}, {"grade": "A", "semester": "2027-Fall"}])
def test_grade_body_is_validated(client: TestClient, world: World, body: dict[str, object]) -> None:
    response = client.patch(
        f"/api/v1/enrollments/{world.alice_a1.id}/grade",
        json=body,
        headers=auth_headers(world.teacher),
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    ("role", "enrollment", "allowed"),
    [
        ("admin", "alice_b1", True),
        ("hod", "alice_a1", True),  # a course of their department, taught by someone else
        ("hod", "bob_a2", True),  # their own course
        ("hod", "alice_b1", False),  # another department
        ("teacher", "alice_a1", True),
        ("teacher", "alice_b1", False),  # another teacher's course (other department)
        ("teacher", "bob_a2", False),  # another teacher's course (same department)
        ("teacher_b", "alice_a1", False),
    ],
)
def test_who_may_grade(
    client: TestClient, session: Session, world: World, role: str, enrollment: str, allowed: bool
) -> None:
    target = world.get(enrollment)

    response = set_grade(client, world.user(role), target, "B")

    if allowed:
        assert response.status_code == 200
    else:
        assert response.status_code == 403
        assert response.json() == {
            "detail": "You can only grade courses you teach or courses of the department you head"
        }
        assert grades(session, target) == [None]


def test_a_teacher_cannot_grade_another_teachers_course(client: TestClient, world: World) -> None:
    assert set_grade(client, world.teacher, world.alice_b1, "A").status_code == 403


def test_students_cannot_grade(client: TestClient, world: World) -> None:
    response = set_grade(client, world.student, world.alice_a1, "A")

    assert response.status_code == 403
    assert response.json() == {"detail": "Not enough permissions"}


def test_grading_requires_authentication(client: TestClient, world: World) -> None:
    response = client.patch(f"/api/v1/enrollments/{world.alice_a1.id}/grade", json={"grade": "A"})
    assert response.status_code == 401


def test_grading_a_missing_enrollment_is_404(client: TestClient, world: World) -> None:
    response = client.patch(
        "/api/v1/enrollments/999999/grade", json={"grade": "A"}, headers=auth_headers(world.admin)
    )
    assert response.status_code == 404


# ======================================== PUT /courses/{id}/grades (FR-6.7)


def test_teacher_saves_all_grades_of_their_course_at_once(
    client: TestClient, session: Session, world: World
) -> None:
    rows = [
        {"enrollment_id": world.bob_a1.id, "grade": "C+"},
        {"enrollment_id": world.alice_a1.id, "grade": "A"},
    ]
    response = bulk(client, world.teacher, world.a1, rows)

    assert response.status_code == 200
    assert [(e["id"], e["grade"]) for e in response.json()] == [
        (world.bob_a1.id, "C+"),
        (world.alice_a1.id, "A"),
    ]  # same order as sent
    assert grades(session, world.alice_a1, world.bob_a1) == [Grade.A, Grade.C_PLUS]


def test_bulk_can_clear_grades(client: TestClient, session: Session, world: World) -> None:
    bulk(client, world.teacher, world.a1, [{"enrollment_id": world.alice_a1.id, "grade": "B"}])

    bulk(client, world.teacher, world.a1, [{"enrollment_id": world.alice_a1.id, "grade": None}])

    assert grades(session, world.alice_a1) == [None]


@pytest.mark.parametrize(
    ("bad_row", "message"),
    [
        ("alice_b1", "Not enrollments of course A1: {id}. No grades were changed."),
        (999_999, "Not enrollments of course A1: 999999. No grades were changed."),
    ],
)
def test_bulk_is_all_or_nothing_for_foreign_or_unknown_rows(
    client: TestClient, session: Session, world: World, bad_row: object, message: str
) -> None:
    bad_id = world.get(bad_row).id if isinstance(bad_row, str) else bad_row
    rows = [
        {"enrollment_id": world.alice_a1.id, "grade": "A"},
        {"enrollment_id": bad_id, "grade": "B"},
    ]

    response = bulk(client, world.teacher, world.a1, rows)

    assert response.status_code == 422
    assert response.json() == {"detail": message.format(id=bad_id)}
    assert grades(session, world.alice_a1, world.alice_b1) == [None, None]


def test_bulk_rejects_repeated_rows(client: TestClient, session: Session, world: World) -> None:
    rows = [
        {"enrollment_id": world.alice_a1.id, "grade": "A"},
        {"enrollment_id": world.alice_a1.id, "grade": "F"},
    ]
    response = bulk(client, world.teacher, world.a1, rows)

    assert response.status_code == 422
    assert response.json() == {"detail": f"Enrollments listed more than once: {world.alice_a1.id}"}
    assert grades(session, world.alice_a1) == [None]


def test_bulk_with_one_invalid_grade_changes_nothing(
    client: TestClient, session: Session, world: World
) -> None:
    rows = [
        {"enrollment_id": world.alice_a1.id, "grade": "A"},
        {"enrollment_id": world.bob_a1.id, "grade": "Z"},
    ]
    assert bulk(client, world.teacher, world.a1, rows).status_code == 422
    assert grades(session, world.alice_a1, world.bob_a1) == [None, None]


@pytest.mark.parametrize(
    "rows",
    [[], {"enrollment_id": 1, "grade": "A"}, [{"grade": "A"}], [{"enrollment_id": 1}]],
    ids=["empty", "not-a-list", "no-id", "no-grade"],
)
def test_bulk_body_is_validated(client: TestClient, world: World, rows: object) -> None:
    assert bulk(client, world.teacher, world.a1, rows).status_code == 422


@pytest.mark.parametrize(
    ("role", "course", "allowed"),
    [
        ("admin", "b1", True),
        ("hod", "a1", True),
        ("hod", "b1", False),
        ("teacher", "a1", True),
        ("teacher", "a2", False),
        ("teacher_b", "a1", False),
    ],
)
def test_who_may_bulk_grade(
    client: TestClient, session: Session, world: World, role: str, course: str, allowed: bool
) -> None:
    target = cast(Course, getattr(world, course))
    enrollment = {"a1": world.alice_a1, "a2": world.bob_a2, "b1": world.alice_b1}[course]

    response = bulk(
        client, world.user(role), target, [{"enrollment_id": enrollment.id, "grade": "B"}]
    )

    assert response.status_code == (200 if allowed else 403)
    assert grades(session, enrollment) == [Grade.B if allowed else None]


def test_a_teacher_cannot_bulk_grade_another_teachers_course(
    client: TestClient, world: World
) -> None:
    rows = [{"enrollment_id": world.alice_b1.id, "grade": "A"}]
    assert bulk(client, world.teacher, world.b1, rows).status_code == 403


def test_students_cannot_bulk_grade(client: TestClient, world: World) -> None:
    rows = [{"enrollment_id": world.alice_a1.id, "grade": "A"}]
    assert bulk(client, world.student, world.a1, rows).status_code == 403


def test_bulk_grading_a_missing_course_is_404(client: TestClient, world: World) -> None:
    response = client.put(
        "/api/v1/courses/999999/grades",
        json=[{"enrollment_id": 1, "grade": "A"}],
        headers=auth_headers(world.admin),
    )
    assert response.status_code == 404


# ======================================== GPA in the student detail (FR-6.6)


def student_gpa(client: TestClient, user: User, student: Student) -> object:
    return client.get(f"/api/v1/students/{student.id}", headers=auth_headers(user)).json()["gpa"]


def test_gpa_is_null_until_something_is_graded(client: TestClient, world: World) -> None:
    assert student_gpa(client, world.student, world.alice) is None


def test_gpa_is_weighted_by_credits(client: TestClient, world: World) -> None:
    set_grade(client, world.admin, world.alice_a1, "A")  # 4.0 x 4 credits
    set_grade(client, world.admin, world.alice_b1, "C")  # 2.0 x 2 credits

    assert student_gpa(client, world.student, world.alice) == 3.33  # 20 / 6


def test_gpa_ignores_ungraded_enrollments(client: TestClient, world: World) -> None:
    set_grade(client, world.admin, world.alice_b1, "B")  # A1 stays ungraded

    assert student_gpa(client, world.student, world.alice) == 3.0


def test_gpa_of_all_f_is_zero(client: TestClient, world: World) -> None:
    set_grade(client, world.admin, world.alice_a1, "F")
    set_grade(client, world.admin, world.alice_b1, "F")

    assert student_gpa(client, world.student, world.alice) == 0.0


def test_gpa_follows_grade_changes(client: TestClient, world: World) -> None:
    set_grade(client, world.admin, world.alice_a1, "A")
    assert student_gpa(client, world.admin, world.alice) == 4.0

    set_grade(client, world.admin, world.alice_a1, None)
    assert student_gpa(client, world.admin, world.alice) is None
