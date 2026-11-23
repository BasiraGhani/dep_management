"""Tests for the courses API (T3.4): FR-5.1–FR-5.4, BR-1/2/7/8 and the Courses row
of the permission matrix (roster visibility follows the Enrollments row).

`world`:
    dept A (DEPA): head HA (`hod` login) teaches A2; TA (`teacher` login) teaches A1;
                   TA2 (no login); A3 has no teacher
    dept B (DEPB): TB (`teacher_b` login) teaches B1
    A1 roster: Alice (2026-Fall, A-) and Bob (2026-Fall, ungraded)
    B1 roster: Alice (2026-Spring, B)
    plus `admin` and `student` (Alice) logins
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Course, Department, Enrollment, Grade, Teacher, User, UserRole
from tests.conftest import Factory
from tests.helpers import auth_headers

URL = "/api/v1/courses"
ROLES = ["admin", "hod", "teacher", "teacher_b", "student"]


@dataclass
class World:
    dept_a: Department
    dept_b: Department
    head_a: Teacher
    teacher_a: Teacher
    teacher_a2: Teacher
    teacher_b: Teacher
    a1: Course
    a2: Course
    a3: Course
    b1: Course
    admin: User
    hod: User
    teacher: User
    teacher_b_login: User
    student: User

    def user(self, role: str) -> User:
        return self.teacher_b_login if role == "teacher_b" else cast(User, getattr(self, role))


@pytest.fixture
def world(session: Session, factory: Factory) -> World:
    dept_a = factory.department(code="DEPA", name="Department A")
    dept_b = factory.department(code="DEPB", name="Department B")
    head_a = factory.teacher(dept_a, first_name="Hedy", last_name="Head")
    dept_a.head_id = head_a.id
    teacher_a = factory.teacher(dept_a, first_name="Tom", last_name="Teach")
    teacher_a2 = factory.teacher(dept_a)
    teacher_b = factory.teacher(dept_b, first_name="Bea", last_name="Bee")
    a1 = factory.course(dept_a, teacher=teacher_a, code="A1", title="Algorithms", credits=4)
    a2 = factory.course(dept_a, teacher=head_a, code="A2", title="Databases")
    a3 = factory.course(dept_a, code="A3", title="Ethics", capacity=25)
    b1 = factory.course(dept_b, teacher=teacher_b, code="B1", title="Biology")
    alice = factory.student(dept_a, first_name="Alice", last_name="Anders", student_no="S1")
    bob = factory.student(dept_b, first_name="Bob", last_name="Brown", student_no="S2")
    for student, course, semester, grade in [
        (alice, a1, "2026-Fall", Grade.A_MINUS),
        (bob, a1, "2026-Fall", None),
        (alice, b1, "2026-Spring", Grade.B),
    ]:
        session.add(
            Enrollment(student_id=student.id, course_id=course.id, semester=semester, grade=grade)
        )
    world = World(
        dept_a=dept_a,
        dept_b=dept_b,
        head_a=head_a,
        teacher_a=teacher_a,
        teacher_a2=teacher_a2,
        teacher_b=teacher_b,
        a1=a1,
        a2=a2,
        a3=a3,
        b1=b1,
        admin=factory.user(UserRole.ADMIN),
        hod=factory.user(UserRole.HOD, teacher=head_a),
        teacher=factory.user(UserRole.TEACHER, teacher=teacher_a),
        teacher_b_login=factory.user(UserRole.TEACHER, teacher=teacher_b),
        student=factory.user(UserRole.STUDENT, student=alice),
    )
    session.commit()
    return world


def new_course(department_id: int, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "code": "N101",
        "title": "Networks",
        "credits": 3,
        "department_id": department_id,
    }
    return payload | overrides


def patch(
    client: TestClient, user: User, course: Course, payload: Mapping[str, object]
) -> httpx.Response:
    response: httpx.Response = client.patch(
        f"{URL}/{course.id}", json=dict(payload), headers=auth_headers(user)
    )
    return response


def codes(response: httpx.Response) -> list[str]:
    return [c["code"] for c in response.json()["items"]]


# ===================================================================== list (FR-5.1)


@pytest.mark.parametrize("role", ROLES)
def test_every_role_can_list_courses(client: TestClient, world: World, role: str) -> None:
    response = client.get(URL, headers=auth_headers(world.user(role)))

    assert response.status_code == 200
    assert codes(response) == ["A1", "A2", "A3", "B1"]
    assert response.json()["total"] == 4


def test_list_requires_authentication(client: TestClient, world: World) -> None:
    assert client.get(URL).status_code == 401


@pytest.mark.parametrize(
    ("search", "expected"),
    [("a1", ["A1"]), ("DATA", ["A2"]), ("bio", ["B1"]), ("a", ["A1", "A2", "A3"]), ("zz", [])],
)
def test_search_by_code_or_title(
    client: TestClient, world: World, search: str, expected: list[str]
) -> None:
    response = client.get(URL, params={"search": search}, headers=auth_headers(world.student))
    assert codes(response) == expected


def test_filter_by_department_and_teacher(client: TestClient, world: World) -> None:
    def listed(**params: object) -> list[str]:
        return codes(client.get(URL, params=params, headers=auth_headers(world.admin)))

    assert listed(department_id=world.dept_b.id) == ["B1"]
    assert listed(teacher_id=world.teacher_a.id) == ["A1"]
    assert listed(department_id=world.dept_a.id, teacher_id=world.teacher_b.id) == []


def test_pagination(client: TestClient, world: World) -> None:
    response = client.get(URL, params={"skip": 1, "limit": 2}, headers=auth_headers(world.admin))

    assert codes(response) == ["A2", "A3"]
    assert response.json()["total"] == 4


@pytest.mark.parametrize("params", [{"teacher_id": "x"}, {"limit": 0}, {"skip": -1}])
def test_invalid_list_parameters(
    client: TestClient, world: World, params: dict[str, object]
) -> None:
    assert client.get(URL, params=params, headers=auth_headers(world.admin)).status_code == 422


# ===================================================================== create (FR-5.1–5.3)


def test_admin_creates_a_course(client: TestClient, world: World) -> None:
    payload = new_course(
        world.dept_b.id,
        code=" b202 ",
        description="Cells and life",
        credits=6,
        capacity=120,
        teacher_id=world.teacher_b.id,
    )
    response = client.post(URL, json=payload, headers=auth_headers(world.admin))

    assert response.status_code == 201
    body = response.json()
    assert body["code"] == "B202"
    assert (body["credits"], body["capacity"], body["teacher_id"]) == (6, 120, world.teacher_b.id)
    assert body["description"] == "Cells and life"


def test_capacity_defaults_to_40_and_teacher_is_optional(client: TestClient, world: World) -> None:
    body = client.post(
        URL, json=new_course(world.dept_a.id), headers=auth_headers(world.admin)
    ).json()
    assert (body["capacity"], body["teacher_id"]) == (40, None)


def test_hod_creates_a_course_in_their_department(client: TestClient, world: World) -> None:
    payload = new_course(world.dept_a.id, teacher_id=world.teacher_a2.id)
    assert client.post(URL, json=payload, headers=auth_headers(world.hod)).status_code == 201


def test_hod_cannot_create_a_course_in_another_department(client: TestClient, world: World) -> None:
    response = client.post(URL, json=new_course(world.dept_b.id), headers=auth_headers(world.hod))

    assert response.status_code == 403
    assert response.json() == {"detail": "You can only add courses to the department you head"}


@pytest.mark.parametrize("role", ["teacher", "student"])
def test_teachers_and_students_cannot_create(client: TestClient, world: World, role: str) -> None:
    response = client.post(
        URL, json=new_course(world.dept_a.id), headers=auth_headers(world.user(role))
    )
    assert response.status_code == 403


def test_teacher_from_another_department_is_rejected_br2(client: TestClient, world: World) -> None:
    payload = new_course(world.dept_a.id, teacher_id=world.teacher_b.id)
    response = client.post(URL, json=payload, headers=auth_headers(world.admin))

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Bea Bee is not in department DEPA; "
        "a course's teacher must belong to the course's department"
    }


@pytest.mark.parametrize(
    ("overrides", "detail"),
    [
        ({"teacher_id": 999_999}, "Teacher 999999 does not exist"),
        ({"department_id": 999_999}, "Department 999999 does not exist"),
    ],
)
def test_missing_teacher_or_department_is_rejected(
    client: TestClient, world: World, overrides: dict[str, object], detail: str
) -> None:
    payload = new_course(world.dept_a.id) | overrides
    response = client.post(URL, json=payload, headers=auth_headers(world.admin))

    assert response.status_code == 422
    assert response.json() == {"detail": detail}


def test_duplicate_code_is_a_conflict(client: TestClient, world: World) -> None:
    response = client.post(
        URL, json=new_course(world.dept_a.id, code="a1"), headers=auth_headers(world.admin)
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "A course with code 'A1' already exists"}


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"code": ""}, "code"),
        ({"code": "C" * 16}, "code"),
        ({"code": "CS 101"}, "code"),
        ({"title": ""}, "title"),
        ({"title": "T" * 151}, "title"),
        ({"credits": 0}, "credits"),
        ({"credits": 7}, "credits"),
        ({"capacity": 0}, "capacity"),
        ({"capacity": 1001}, "capacity"),
        ({"room": "101"}, "room"),
    ],
)
def test_create_validates_fields(
    client: TestClient, world: World, overrides: dict[str, object], field: str
) -> None:
    payload = new_course(world.dept_a.id, **overrides)
    response = client.post(URL, json=payload, headers=auth_headers(world.admin))

    assert response.status_code == 422
    assert field in {str(error["loc"][-1]) for error in response.json()["detail"]}


@pytest.mark.parametrize("missing", ["code", "title", "credits", "department_id"])
def test_create_requires_fields(client: TestClient, world: World, missing: str) -> None:
    payload = new_course(world.dept_a.id)
    del payload[missing]
    assert client.post(URL, json=payload, headers=auth_headers(world.admin)).status_code == 422


# ===================================================================== detail and roster (FR-5.4)


@pytest.mark.parametrize("role", ["admin", "hod", "teacher"])
def test_staff_in_scope_see_the_roster_with_grades(
    client: TestClient, world: World, role: str
) -> None:
    body = client.get(f"{URL}/{world.a1.id}", headers=auth_headers(world.user(role))).json()

    assert body["teacher"] == {
        "id": world.teacher_a.id,
        "first_name": "Tom",
        "last_name": "Teach",
        "title": "lecturer",
    }
    assert [
        (r["student_no"], r["first_name"], r["semester"], r["grade"]) for r in body["roster"]
    ] == [("S1", "Alice", "2026-Fall", "A-"), ("S2", "Bob", "2026-Fall", None)]
    assert {"enrollment_id", "student_id", "last_name"} <= set(body["roster"][0])


@pytest.mark.parametrize(
    ("role", "course"),
    [
        ("student", "a1"),  # students never see rosters
        ("teacher_b", "a1"),  # a teacher of another course
        ("teacher", "a2"),  # same department, but the HOD's course
        ("hod", "b1"),  # a HOD for another department's course
    ],
)
def test_roster_is_hidden_outside_scope(
    client: TestClient, world: World, role: str, course: str
) -> None:
    target = cast(Course, getattr(world, course))
    response = client.get(f"{URL}/{target.id}", headers=auth_headers(world.user(role)))

    assert response.status_code == 200
    assert response.json()["roster"] is None
    assert "Alice" not in response.text


def test_empty_roster_is_an_empty_list_not_hidden(client: TestClient, world: World) -> None:
    body = client.get(f"{URL}/{world.a3.id}", headers=auth_headers(world.hod)).json()

    assert body["roster"] == []
    assert body["teacher"] is None
    assert body["capacity"] == 25


def test_detail_of_a_missing_course_is_404(client: TestClient, world: World) -> None:
    response = client.get(f"{URL}/999999", headers=auth_headers(world.student))

    assert response.status_code == 404
    assert response.json() == {"detail": "Course not found"}


# ===================================================================== update: admin and BR-2


def test_admin_updates_any_field(client: TestClient, world: World) -> None:
    payload = {"title": "Ethics II", "credits": 2, "capacity": 30, "description": "Hard choices"}
    response = patch(client, world.admin, world.a3, payload)

    assert response.status_code == 200
    assert {k: response.json()[k] for k in payload} == payload


def test_assigning_a_teacher_from_another_department_is_rejected(
    client: TestClient, world: World
) -> None:
    response = patch(client, world.admin, world.a3, {"teacher_id": world.teacher_b.id})

    assert response.status_code == 422
    assert "must belong to the course's department" in response.json()["detail"]


def test_moving_a_course_away_from_its_teachers_department_is_rejected(
    client: TestClient, world: World
) -> None:
    response = patch(client, world.admin, world.a1, {"department_id": world.dept_b.id})

    assert response.status_code == 422
    assert "Tom Teach is not in department DEPB" in response.json()["detail"]


def test_moving_a_course_with_a_new_teacher_from_the_new_department(
    client: TestClient, world: World
) -> None:
    payload = {"department_id": world.dept_b.id, "teacher_id": world.teacher_b.id}
    response = patch(client, world.admin, world.a1, payload)

    assert response.status_code == 200
    assert (response.json()["department_id"], response.json()["teacher_id"]) == (
        world.dept_b.id,
        world.teacher_b.id,
    )


def test_moving_a_course_and_unassigning_its_teacher(client: TestClient, world: World) -> None:
    payload = {"department_id": world.dept_b.id, "teacher_id": None}
    assert patch(client, world.admin, world.a1, payload).status_code == 200


def test_moving_an_unassigned_course(client: TestClient, world: World) -> None:
    assert (
        patch(client, world.admin, world.a3, {"department_id": world.dept_b.id}).status_code == 200
    )


@pytest.mark.parametrize(
    ("payload", "status_code"),
    [
        ({"code": "a2"}, 409),
        ({"code": "a1"}, 200),  # own code: not a conflict
        ({"credits": None}, 422),
        ({"capacity": 0}, 422),
        ({"department_id": 999_999}, 422),
        ({"teacher_id": 999_999}, 422),
    ],
)
def test_update_rules(
    client: TestClient, world: World, payload: dict[str, object], status_code: int
) -> None:
    assert patch(client, world.admin, world.a1, payload).status_code == status_code


def test_update_of_a_missing_course_is_404(client: TestClient, world: World) -> None:
    response = client.patch(f"{URL}/999999", json={"title": "X"}, headers=auth_headers(world.admin))
    assert response.status_code == 404


# ========================================================= update: HOD, teacher, student


def test_hod_updates_a_course_of_their_department(client: TestClient, world: World) -> None:
    payload = {"title": "Algorithms II", "teacher_id": world.teacher_a2.id, "capacity": 60}
    response = patch(client, world.hod, world.a1, payload)

    assert response.status_code == 200
    assert {k: response.json()[k] for k in payload} == payload


def test_hod_cannot_move_a_course_out(client: TestClient, world: World) -> None:
    response = patch(client, world.hod, world.a3, {"department_id": world.dept_b.id})

    assert response.status_code == 403
    assert "can't move courses" in response.json()["detail"]


def test_hod_cannot_edit_another_departments_course(client: TestClient, world: World) -> None:
    response = patch(client, world.hod, world.b1, {"title": "X"})

    assert response.status_code == 403
    assert response.json() == {"detail": "You can't edit this course"}


def test_teacher_updates_the_description_of_their_own_course(
    client: TestClient, world: World
) -> None:
    response = patch(client, world.teacher, world.a1, {"description": "Sorting and graphs"})

    assert response.status_code == 200
    assert response.json()["description"] == "Sorting and graphs"


@pytest.mark.parametrize(
    "payload",
    [{"title": "Mine"}, {"capacity": 99}, {"teacher_id": None}, {"description": "x", "credits": 1}],
)
def test_teacher_cannot_change_anything_else(
    client: TestClient, world: World, payload: dict[str, object]
) -> None:
    response = patch(client, world.teacher, world.a1, payload)

    assert response.status_code == 403
    assert response.json()["detail"].startswith("You can only change the description")


def test_teacher_cannot_edit_another_teachers_course(client: TestClient, world: World) -> None:
    response = patch(client, world.teacher, world.a2, {"description": "Not mine"})
    assert response.status_code == 403


def test_refused_update_changes_nothing(client: TestClient, session: Session, world: World) -> None:
    patch(client, world.teacher, world.a1, {"description": "New", "title": "Hijacked"})

    session.refresh(world.a1)
    assert (world.a1.title, world.a1.description) == ("Algorithms", None)


def test_students_cannot_update_courses(client: TestClient, world: World) -> None:
    response = patch(client, world.student, world.a1, {"description": "x"})

    assert response.status_code == 403
    assert response.json() == {"detail": "Not enough permissions"}


def test_update_requires_authentication(client: TestClient, world: World) -> None:
    assert client.patch(f"{URL}/{world.a1.id}", json={"title": "X"}).status_code == 401


# ===================================================================== delete


def test_admin_deletes_a_course_without_enrollments(client: TestClient, world: World) -> None:
    response = client.delete(f"{URL}/{world.a3.id}", headers=auth_headers(world.admin))

    assert response.status_code == 204
    assert client.get(f"{URL}/{world.a3.id}", headers=auth_headers(world.admin)).status_code == 404


def test_course_with_enrollments_cannot_be_deleted(
    client: TestClient, session: Session, world: World
) -> None:
    response = client.delete(f"{URL}/{world.a1.id}", headers=auth_headers(world.admin))

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Course A1 can't be deleted while it has 2 enrollments. Remove them first."
    }
    count = select(func.count()).select_from(Enrollment).where(Enrollment.course_id == world.a1.id)
    assert session.scalar(count) == 2


def test_hod_deletes_a_course_of_their_department(client: TestClient, world: World) -> None:
    assert client.delete(f"{URL}/{world.a2.id}", headers=auth_headers(world.hod)).status_code == 204


def test_hod_cannot_delete_another_departments_course(
    client: TestClient, factory: Factory, world: World
) -> None:
    empty_b = factory.course(world.dept_b)

    response = client.delete(f"{URL}/{empty_b.id}", headers=auth_headers(world.hod))

    assert response.status_code == 403
    assert "department you head" in response.json()["detail"]


@pytest.mark.parametrize("role", ["teacher", "student"])
def test_teachers_and_students_cannot_delete(client: TestClient, world: World, role: str) -> None:
    response = client.delete(f"{URL}/{world.a3.id}", headers=auth_headers(world.user(role)))
    assert response.status_code == 403


def test_delete_of_a_missing_course_is_404(client: TestClient, world: World) -> None:
    assert client.delete(f"{URL}/999999", headers=auth_headers(world.admin)).status_code == 404
