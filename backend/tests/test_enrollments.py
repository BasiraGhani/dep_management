"""Tests for the enrollments API (T4.1): FR-6.1–FR-6.4, BR-4, BR-5, semester format
and the Enrollments row of the permission matrix.

`world`:
    dept A (DEPA): head HA (`hod`) teaches A2; TA (`teacher`) teaches A1 (capacity 2)
    dept B (DEPB): TB (`teacher_b`) teaches B1
    students: alice (A, active, `student` login), bob (B, active),
              sue (A, suspended), gina (A, graduated), walt (A, withdrawn)
    enrollments: alice-A1 2026-Fall, bob-B1 2026-Fall, alice-B1 2026-Spring,
                 bob-A2 2026-Spring
"""

from dataclasses import dataclass
from typing import cast

import httpx2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Course, Department, Enrollment, Student, StudentStatus, User, UserRole
from tests.conftest import Factory
from tests.helpers import auth_headers

URL = "/api/v1/enrollments"


@dataclass
class World:
    dept_a: Department
    dept_b: Department
    a1: Course
    a2: Course
    b1: Course
    alice: Student
    bob: Student
    sue: Student
    gina: Student
    walt: Student
    alice_a1: Enrollment
    bob_b1: Enrollment
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
    dept_a = factory.department(code="DEPA", name="Department A")
    dept_b = factory.department(code="DEPB", name="Department B")
    head_a, teacher_a = factory.teacher(dept_a), factory.teacher(dept_a)
    dept_a.head_id = head_a.id
    teacher_b = factory.teacher(dept_b)
    a1 = factory.course(dept_a, teacher=teacher_a, code="A1", capacity=2)
    a2 = factory.course(dept_a, teacher=head_a, code="A2")
    b1 = factory.course(dept_b, teacher=teacher_b, code="B1")

    def student(dept: Department, first: str, number: str, status: StudentStatus) -> Student:
        return factory.student(
            dept, first_name=first, last_name="Tester", student_no=number, status=status
        )

    alice = student(dept_a, "Alice", "S-ALICE", StudentStatus.ACTIVE)
    bob = student(dept_b, "Bob", "S-BOB", StudentStatus.ACTIVE)
    world = World(
        dept_a=dept_a,
        dept_b=dept_b,
        a1=a1,
        a2=a2,
        b1=b1,
        alice=alice,
        bob=bob,
        sue=student(dept_a, "Sue", "S-SUE", StudentStatus.SUSPENDED),
        gina=student(dept_a, "Gina", "S-GINA", StudentStatus.GRADUATED),
        walt=student(dept_a, "Walt", "S-WALT", StudentStatus.WITHDRAWN),
        alice_a1=factory.enrollment(alice, a1, "2026-Fall"),
        bob_b1=factory.enrollment(bob, b1, "2026-Fall"),
        alice_b1=factory.enrollment(alice, b1, "2026-Spring"),
        bob_a2=factory.enrollment(bob, a2, "2026-Spring"),
        admin=factory.user(UserRole.ADMIN),
        hod=factory.user(UserRole.HOD, teacher=head_a),
        teacher=factory.user(UserRole.TEACHER, teacher=teacher_a),
        teacher_b=factory.user(UserRole.TEACHER, teacher=teacher_b),
        student=factory.user(UserRole.STUDENT, student=alice),
    )
    session.commit()
    return world


def enroll(
    client: TestClient, user: User, student: Student, course: Course, semester: str = "2027-Spring"
) -> httpx2.Response:
    payload = {"student_id": student.id, "course_id": course.id, "semester": semester}
    response: httpx2.Response = client.post(URL, json=payload, headers=auth_headers(user))
    return response


def listed(response: httpx2.Response) -> set[int]:
    return {e["id"] for e in response.json()["items"]}


# ===================================================================== list scoping


@pytest.mark.parametrize(
    ("role", "visible"),
    [
        ("admin", {"alice_a1", "bob_b1", "alice_b1", "bob_a2"}),
        ("hod", {"alice_a1", "bob_a2"}),  # courses of department A
        ("teacher", {"alice_a1"}),  # A1 only
        ("teacher_b", {"bob_b1", "alice_b1"}),  # B1 only
        ("student", {"alice_a1", "alice_b1"}),  # own enrollments
    ],
)
def test_list_is_scoped_by_role(
    client: TestClient, world: World, role: str, visible: set[str]
) -> None:
    response = client.get(URL, headers=auth_headers(world.user(role)))

    assert response.status_code == 200
    assert listed(response) == {world.get(name).id for name in visible}
    assert response.json()["total"] == len(visible)


def test_list_requires_authentication(client: TestClient, world: World) -> None:
    assert client.get(URL).status_code == 401


def test_list_items_include_student_and_course(client: TestClient, world: World) -> None:
    item = client.get(URL, headers=auth_headers(world.teacher)).json()["items"][0]

    assert item["student"] == {
        "id": world.alice.id,
        "student_no": "S-ALICE",
        "first_name": "Alice",
        "last_name": "Tester",
    }
    assert (item["course"]["code"], item["semester"], item["grade"]) == ("A1", "2026-Fall", None)


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        ({"student_id": "alice"}, {"alice_a1", "alice_b1"}),
        ({"course_id": "b1"}, {"bob_b1", "alice_b1"}),
        ({"semester": "2026-Spring"}, {"alice_b1", "bob_a2"}),
        ({"student_id": "bob", "semester": "2026-Fall"}, {"bob_b1"}),
        ({"search": "s-bob"}, {"bob_b1", "bob_a2"}),
        ({"search": "a2"}, {"bob_a2"}),
    ],
)
def test_filters_and_search(
    client: TestClient, world: World, params: dict[str, str], expected: set[str]
) -> None:
    refs = {"alice": world.alice.id, "bob": world.bob.id, "b1": world.b1.id}
    resolved = {k: refs.get(v, v) for k, v in params.items()}

    response = client.get(URL, params=resolved, headers=auth_headers(world.admin))

    assert listed(response) == {world.get(name).id for name in expected}


def test_filters_cannot_widen_the_scope(client: TestClient, world: World) -> None:
    params = {"student_id": world.bob.id}
    response = client.get(URL, params=params, headers=auth_headers(world.student))

    assert response.json() == {"items": [], "total": 0}


def test_pagination_is_newest_first(client: TestClient, world: World) -> None:
    response = client.get(URL, params={"limit": 2}, headers=auth_headers(world.admin))

    assert [e["id"] for e in response.json()["items"]] == [world.bob_a2.id, world.alice_b1.id]
    assert response.json()["total"] == 4


@pytest.mark.parametrize("semester", ["2026-fall", "Fall-2026", "2026"])
def test_invalid_semester_filter_is_rejected(
    client: TestClient, world: World, semester: str
) -> None:
    response = client.get(URL, params={"semester": semester}, headers=auth_headers(world.admin))
    assert response.status_code == 422


# ===================================================================== enroll: success (FR-6.1)


def test_admin_enrolls_a_student(client: TestClient, world: World) -> None:
    response = enroll(client, world.admin, world.alice, world.a2, " 2027-Spring ")

    assert response.status_code == 201
    body = response.json()
    assert (body["student_id"], body["course_id"]) == (world.alice.id, world.a2.id)
    assert (body["semester"], body["grade"]) == ("2027-Spring", None)
    assert body["student"]["student_no"] == "S-ALICE"
    assert body["course"]["code"] == "A2"


@pytest.mark.parametrize(
    "semester", ["2026-Spring", "2026-Summer", "2026-Fall", "1999-Fall", "2100-Summer"]
)
def test_every_semester_season_is_accepted(client: TestClient, world: World, semester: str) -> None:
    assert enroll(client, world.admin, world.alice, world.a2, semester).status_code == 201


def test_hod_enrolls_any_student_in_a_course_of_their_department(
    client: TestClient, world: World
) -> None:
    assert enroll(client, world.hod, world.bob, world.a1).status_code == 201  # bob is in dept B


def test_hod_cannot_enroll_in_another_departments_course(client: TestClient, world: World) -> None:
    response = enroll(client, world.hod, world.alice, world.b1)

    assert response.status_code == 403
    assert response.json() == {
        "detail": "You can only enroll students in courses of the department you head"
    }


@pytest.mark.parametrize("role", ["teacher", "student"])
def test_teachers_and_students_cannot_enroll(client: TestClient, world: World, role: str) -> None:
    response = enroll(client, world.user(role), world.alice, world.a1)

    assert response.status_code == 403
    assert response.json() == {"detail": "Not enough permissions"}


def test_enroll_requires_authentication(client: TestClient, world: World) -> None:
    payload = {"student_id": world.alice.id, "course_id": world.a2.id, "semester": "2027-Fall"}
    assert client.post(URL, json=payload).status_code == 401


# ===================================================================== enroll: BR-4 (FR-6.4)


@pytest.mark.parametrize(
    ("name", "status_word"),
    [("sue", "suspended"), ("gina", "graduated"), ("walt", "withdrawn")],
)
def test_only_active_students_can_be_enrolled(
    client: TestClient, session: Session, world: World, name: str, status_word: str
) -> None:
    student = cast(Student, getattr(world, name))

    response = enroll(client, world.admin, student, world.a2)

    assert response.status_code == 409
    assert response.json() == {
        "detail": f"{student.first_name} Tester ({student.student_no}) is {status_word}; "
        "only active students can be enrolled"
    }
    created = session.scalar(select(Enrollment).where(Enrollment.student_id == student.id))
    assert created is None


# ===================================================================== enroll: FR-6.2 duplicates


def test_same_course_and_semester_twice_is_a_conflict(client: TestClient, world: World) -> None:
    response = enroll(client, world.admin, world.alice, world.a1, "2026-Fall")

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Alice Tester (S-ALICE) is already enrolled in A1 for 2026-Fall"
    }


def test_same_course_in_another_semester_is_allowed(client: TestClient, world: World) -> None:
    assert enroll(client, world.admin, world.alice, world.a1, "2027-Fall").status_code == 201


# =========================================================== enroll: BR-5 capacity (FR-6.3)


def test_full_course_is_a_conflict(client: TestClient, factory: Factory, world: World) -> None:
    assert enroll(client, world.admin, world.bob, world.a1, "2026-Fall").status_code == 201  # 2 / 2
    extra = factory.student(world.dept_a)

    response = enroll(client, world.admin, extra, world.a1, "2026-Fall")

    assert response.status_code == 409
    assert response.json() == {"detail": "A1 is full for 2026-Fall (2 / 2)"}


def test_capacity_counts_each_semester_separately(
    client: TestClient, factory: Factory, world: World
) -> None:
    enroll(client, world.admin, world.bob, world.a1, "2026-Fall")  # Fall is now full

    response = enroll(client, world.admin, factory.student(world.dept_a), world.a1, "2027-Spring")

    assert response.status_code == 201


def test_unenrolling_frees_a_place(client: TestClient, factory: Factory, world: World) -> None:
    enroll(client, world.admin, world.bob, world.a1, "2026-Fall")  # full
    client.delete(f"{URL}/{world.alice_a1.id}", headers=auth_headers(world.admin))

    response = enroll(client, world.admin, factory.student(world.dept_a), world.a1, "2026-Fall")

    assert response.status_code == 201


def test_rules_are_checked_in_order(client: TestClient, world: World) -> None:
    """A suspended student in a full course gets the BR-4 message, not the capacity one."""
    enroll(client, world.admin, world.bob, world.a1, "2026-Fall")  # full

    response = enroll(client, world.admin, world.sue, world.a1, "2026-Fall")

    assert "only active students" in response.json()["detail"]


# ===================================================================== enroll: validation


@pytest.mark.parametrize(
    "semester",
    [
        "2026-fall",
        "2026-Winter",
        "26-Fall",
        "2026 Fall",
        "Fall-2026",
        "",
        "3026-Fall",
        "2026-Fall-1",
    ],
)
def test_semester_format_is_validated(client: TestClient, world: World, semester: str) -> None:
    response = enroll(client, world.admin, world.alice, world.a2, semester)

    assert response.status_code == 422
    assert "semester" in {str(error["loc"][-1]) for error in response.json()["detail"]}


@pytest.mark.parametrize(
    ("field", "detail"),
    [
        ("student_id", "Student 999999 does not exist"),
        ("course_id", "Course 999999 does not exist"),
    ],
)
def test_unknown_student_or_course_is_rejected(
    client: TestClient, world: World, field: str, detail: str
) -> None:
    payload = {"student_id": world.alice.id, "course_id": world.a2.id, "semester": "2027-Fall"}
    payload[field] = 999_999

    response = client.post(URL, json=payload, headers=auth_headers(world.admin))

    assert response.status_code == 422
    assert response.json() == {"detail": detail}


def test_permission_is_checked_before_the_student(client: TestClient, world: World) -> None:
    payload = {"student_id": 999_999, "course_id": world.b1.id, "semester": "2027-Fall"}
    response = client.post(URL, json=payload, headers=auth_headers(world.hod))
    assert response.status_code == 403


@pytest.mark.parametrize(
    "payload",
    [
        {"course_id": 1, "semester": "2027-Fall"},
        {"student_id": 1, "semester": "2027-Fall"},
        {"student_id": 1, "course_id": 1},
        {"student_id": 1, "course_id": 1, "semester": "2027-Fall", "grade": "A"},
    ],
    ids=["no-student", "no-course", "no-semester", "grade-not-allowed"],
)
def test_enroll_body_is_validated(
    client: TestClient, world: World, payload: dict[str, object]
) -> None:
    assert client.post(URL, json=payload, headers=auth_headers(world.admin)).status_code == 422


# ===================================================================== unenroll


def test_admin_unenrolls(client: TestClient, session: Session, world: World) -> None:
    response = client.delete(f"{URL}/{world.bob_b1.id}", headers=auth_headers(world.admin))

    assert response.status_code == 204
    assert session.get(Enrollment, world.bob_b1.id) is None


def test_hod_unenrolls_from_a_course_of_their_department(client: TestClient, world: World) -> None:
    response = client.delete(f"{URL}/{world.alice_a1.id}", headers=auth_headers(world.hod))
    assert response.status_code == 204


def test_hod_cannot_unenroll_from_another_departments_course(
    client: TestClient, world: World
) -> None:
    response = client.delete(f"{URL}/{world.bob_b1.id}", headers=auth_headers(world.hod))

    assert response.status_code == 403
    assert "department you head" in response.json()["detail"]


@pytest.mark.parametrize("role", ["teacher", "student"])
def test_teachers_and_students_cannot_unenroll(client: TestClient, world: World, role: str) -> None:
    response = client.delete(f"{URL}/{world.alice_a1.id}", headers=auth_headers(world.user(role)))
    assert response.status_code == 403


def test_unenroll_of_a_missing_enrollment_is_404(client: TestClient, world: World) -> None:
    response = client.delete(f"{URL}/999999", headers=auth_headers(world.admin))

    assert response.status_code == 404
    assert response.json() == {"detail": "Enrollment not found"}


# ===================================================================== BR-5 on course capacity


def test_course_capacity_cannot_drop_below_current_enrollment(
    client: TestClient, world: World
) -> None:
    enroll(client, world.admin, world.bob, world.a1, "2026-Fall")  # 2 students in Fall

    response = client.patch(
        f"/api/v1/courses/{world.a1.id}", json={"capacity": 1}, headers=auth_headers(world.admin)
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Capacity can't be lower than the 2 students already enrolled "
        "in A1 in one semester (BR-5)"
    }


def test_course_capacity_can_drop_to_current_enrollment(client: TestClient, world: World) -> None:
    response = client.patch(
        f"/api/v1/courses/{world.b1.id}", json={"capacity": 1}, headers=auth_headers(world.admin)
    )
    assert response.status_code == 200  # B1 has 1 student per semester
