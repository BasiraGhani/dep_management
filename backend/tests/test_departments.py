"""Tests for the departments API (T3.1): FR-2.1–FR-2.4, BR-1, BR-3, BR-7, BR-8 and
the Departments row of the permission matrix (REQUIREMENTS §3).

The `world` fixture has two departments:

    A (code DEPA): head teacher with the `hod` login, one more teacher, a student
                   with the `student` login, one course
    B (code DEPB): empty

plus an `admin` login and a `teacher` login (the extra teacher in A).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Department, User, UserRole
from tests.conftest import Factory
from tests.helpers import auth_headers

URL = "/api/v1/departments"
ROLES = ["admin", "hod", "teacher", "student"]


@dataclass
class World:
    dept_a: Department
    dept_b: Department
    admin: User
    hod: User
    teacher: User
    student: User
    head_teacher_id: int
    other_teacher_id: int

    def user(self, role: str) -> User:
        return cast(User, getattr(self, role))


@pytest.fixture
def world(session: Session, factory: Factory) -> World:
    dept_a = factory.department(code="DEPA", name="Department A")
    dept_b = factory.department(code="DEPB", name="Department B")
    head = factory.teacher(dept_a, first_name="Hedy", last_name="Head")
    other = factory.teacher(dept_a)
    dept_a.head_id = head.id
    student = factory.student(dept_a)
    factory.course(dept_a, teacher=other, code="A101")
    world = World(
        dept_a=dept_a,
        dept_b=dept_b,
        admin=factory.user(UserRole.ADMIN),
        hod=factory.user(UserRole.HOD, teacher=head),
        teacher=factory.user(UserRole.TEACHER, teacher=other),
        student=factory.user(UserRole.STUDENT, student=student),
        head_teacher_id=head.id,
        other_teacher_id=other.id,
    )
    session.commit()
    return world


# ===================================================================== list


@pytest.mark.parametrize("role", ROLES)
def test_every_role_can_list_departments(client: TestClient, world: World, role: str) -> None:
    response = client.get(URL, headers=auth_headers(world.user(role)))

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert [d["code"] for d in body["items"]] == ["DEPA", "DEPB"]


def test_list_requires_authentication(client: TestClient, world: World) -> None:
    assert client.get(URL).status_code == 401


@pytest.mark.parametrize(
    ("search", "codes"),
    [
        ("depb", ["DEPB"]),  # code only ("Department B" doesn't contain "depb")
        ("DEPARTMENT a", ["DEPA"]),  # name only, any case
        ("dep", ["DEPA", "DEPB"]),
        ("zzz", []),
    ],
)
def test_search_matches_name_or_code_case_insensitively(
    client: TestClient, world: World, search: str, codes: list[str]
) -> None:
    body = client.get(URL, params={"search": search}, headers=auth_headers(world.admin)).json()

    assert [d["code"] for d in body["items"]] == codes
    assert body["total"] == len(codes)


def test_search_treats_like_wildcards_literally(
    client: TestClient, factory: Factory, world: World
) -> None:
    factory.department(code="PCT", name="100% Science")

    def codes(search: str) -> list[str]:
        response = client.get(URL, params={"search": search}, headers=auth_headers(world.admin))
        return [d["code"] for d in response.json()["items"]]

    assert codes("%") == ["PCT"]
    assert codes("_") == []


def test_pagination_returns_a_page_and_the_full_total(
    client: TestClient, factory: Factory, world: World
) -> None:
    for i in range(5):
        factory.department(code=f"X{i}", name=f"Extra {i}")

    body = client.get(URL, params={"skip": 2, "limit": 3}, headers=auth_headers(world.admin)).json()

    assert body["total"] == 7
    assert [d["code"] for d in body["items"]] == ["X0", "X1", "X2"]


def test_limit_defaults_to_20(client: TestClient, factory: Factory, world: World) -> None:
    for i in range(25):
        factory.department(code=f"X{i:02d}", name=f"Extra {i}")

    body = client.get(URL, headers=auth_headers(world.admin)).json()

    assert len(body["items"]) == 20
    assert body["total"] == 27


@pytest.mark.parametrize(
    "params",
    [{"limit": 0}, {"limit": 101}, {"skip": -1}, {"limit": "abc"}, {"search": "x" * 101}],
)
def test_invalid_list_parameters_are_rejected(
    client: TestClient, world: World, params: dict[str, object]
) -> None:
    response = client.get(URL, params=params, headers=auth_headers(world.admin))
    assert response.status_code == 422


# ===================================================================== create


def test_admin_creates_a_department(client: TestClient, world: World) -> None:
    payload = {
        "code": " ee ",
        "name": "  Electrical Engineering ",
        "description": "Circuits and signals",
        "building": "Volta Hall",
        "phone": "+1 (555) 010-2030",
    }
    response = client.post(URL, json=payload, headers=auth_headers(world.admin))

    assert response.status_code == 201
    body = response.json()
    assert body["code"] == "EE"  # stored uppercase
    assert body["name"] == "Electrical Engineering"  # whitespace stripped
    assert body["description"] == "Circuits and signals"
    assert body["building"] == "Volta Hall"
    assert body["phone"] == "+1 (555) 010-2030"
    assert body["head_id"] is None
    assert isinstance(body["id"], int)


def test_create_with_only_the_required_fields(client: TestClient, world: World) -> None:
    response = client.post(
        URL, json={"code": "EE", "name": "Electrical"}, headers=auth_headers(world.admin)
    )

    assert response.status_code == 201
    assert response.json()["description"] is None


@pytest.mark.parametrize("role", ["hod", "teacher", "student"])
def test_only_admin_can_create(client: TestClient, world: World, role: str) -> None:
    response = client.post(
        URL, json={"code": "EE", "name": "Electrical"}, headers=auth_headers(world.user(role))
    )
    assert response.status_code == 403


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"code": "depa", "name": "Another"}, "code 'DEPA' already exists"),
        ({"code": "NEW", "name": "Department A"}, "named 'Department A' already exists"),
    ],
)
def test_duplicate_code_or_name_is_a_conflict(
    client: TestClient, world: World, payload: dict[str, str], message: str
) -> None:
    response = client.post(URL, json=payload, headers=auth_headers(world.admin))

    assert response.status_code == 409
    assert message in response.json()["detail"]


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"name": "No code"}, "code"),
        ({"code": "NC"}, "name"),
        ({"code": "", "name": "Empty code"}, "code"),
        ({"code": "   ", "name": "Blank code"}, "code"),
        ({"code": "C" * 11, "name": "Long code"}, "code"),
        ({"code": "C-S", "name": "Bad characters"}, "code"),
        ({"code": "LN", "name": "N" * 121}, "name"),
        ({"code": "LB", "name": "Long building", "building": "B" * 81}, "building"),
        ({"code": "BP", "name": "Bad phone", "phone": "call me"}, "phone"),
        ({"code": "HD", "name": "Head on create", "head_id": 1}, "head_id"),
        ({"code": "XF", "name": "Unknown field", "budget": 1}, "budget"),
    ],
)
def test_create_validates_fields(
    client: TestClient, world: World, payload: dict[str, object], field: str
) -> None:
    response = client.post(URL, json=payload, headers=auth_headers(world.admin))

    assert response.status_code == 422
    assert field in {error["loc"][-1] for error in response.json()["detail"]}


# ===================================================================== detail


@pytest.mark.parametrize("role", ROLES)
def test_every_role_can_read_a_department_with_counts_head_and_courses(
    client: TestClient, world: World, role: str
) -> None:
    response = client.get(f"{URL}/{world.dept_a.id}", headers=auth_headers(world.user(role)))

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == "DEPA"
    assert body["head"] == {
        "id": world.head_teacher_id,
        "first_name": "Hedy",
        "last_name": "Head",
        "title": "lecturer",
    }
    assert (body["teacher_count"], body["student_count"], body["course_count"]) == (2, 1, 1)
    assert [c["code"] for c in body["courses"]] == ["A101"]
    assert body["courses"][0]["teacher_id"] == world.other_teacher_id


def test_detail_of_an_empty_department(client: TestClient, world: World) -> None:
    body = client.get(f"{URL}/{world.dept_b.id}", headers=auth_headers(world.student)).json()

    assert body["head"] is None
    assert (body["teacher_count"], body["student_count"], body["course_count"]) == (0, 0, 0)
    assert body["courses"] == []


def test_detail_of_a_missing_department_is_404(client: TestClient, world: World) -> None:
    response = client.get(f"{URL}/999999", headers=auth_headers(world.admin))

    assert response.status_code == 404
    assert response.json() == {"detail": "Department not found"}


def test_detail_requires_authentication(client: TestClient, world: World) -> None:
    assert client.get(f"{URL}/{world.dept_a.id}").status_code == 401


# ===================================================================== update: admin


def patch(
    client: TestClient, user: User, dept: Department, payload: Mapping[str, object]
) -> httpx.Response:
    response: httpx.Response = client.patch(
        f"{URL}/{dept.id}", json=dict(payload), headers=auth_headers(user)
    )
    return response


def test_admin_can_update_every_field(client: TestClient, world: World) -> None:
    payload = {
        "code": "deb",
        "name": "Dept B renamed",
        "description": "New text",
        "building": "Annex",
        "phone": "555-0199",
    }
    response = patch(client, world.admin, world.dept_b, payload)

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == "DEB"
    assert {k: body[k] for k in ("name", "description", "building", "phone")} == {
        "name": "Dept B renamed",
        "description": "New text",
        "building": "Annex",
        "phone": "555-0199",
    }


def test_update_changes_only_the_fields_sent(client: TestClient, world: World) -> None:
    patch(client, world.admin, world.dept_a, {"building": "Old Wing", "phone": "555-1000"})

    body = patch(client, world.admin, world.dept_a, {"building": "New Wing"}).json()

    assert body["building"] == "New Wing"
    assert body["phone"] == "555-1000"
    assert body["name"] == "Department A"


def test_optional_fields_can_be_cleared_with_null(client: TestClient, world: World) -> None:
    patch(client, world.admin, world.dept_a, {"building": "Old Wing"})

    body = patch(client, world.admin, world.dept_a, {"building": None}).json()

    assert body["building"] is None


@pytest.mark.parametrize("field", ["code", "name"])
def test_required_fields_cannot_be_cleared(client: TestClient, world: World, field: str) -> None:
    response = patch(client, world.admin, world.dept_a, {field: None})

    assert response.status_code == 422
    assert f"{field} cannot be null" in response.text


def test_keeping_your_own_code_and_name_is_not_a_conflict(client: TestClient, world: World) -> None:
    response = patch(client, world.admin, world.dept_a, {"code": "depa", "name": "Department A"})
    assert response.status_code == 200


@pytest.mark.parametrize("payload", [{"code": "DEPB"}, {"code": "depb"}, {"name": "Department B"}])
def test_update_to_another_departments_code_or_name_is_a_conflict(
    client: TestClient, world: World, payload: dict[str, str]
) -> None:
    assert patch(client, world.admin, world.dept_a, payload).status_code == 409


def test_update_validates_fields(client: TestClient, world: World) -> None:
    response = patch(client, world.admin, world.dept_a, {"code": "BAD CODE"})
    assert response.status_code == 422


def test_admin_sets_a_head_from_the_department(client: TestClient, world: World) -> None:
    response = patch(client, world.admin, world.dept_a, {"head_id": world.other_teacher_id})

    assert response.status_code == 200
    assert response.json()["head_id"] == world.other_teacher_id


def test_head_from_another_department_is_rejected(
    client: TestClient, factory: Factory, world: World
) -> None:
    outsider = factory.teacher(world.dept_b)

    response = patch(client, world.admin, world.dept_a, {"head_id": outsider.id})

    assert response.status_code == 422
    assert response.json() == {"detail": "The head must be a teacher in this department"}


def test_head_that_does_not_exist_is_rejected(client: TestClient, world: World) -> None:
    response = patch(client, world.admin, world.dept_a, {"head_id": 999_999})

    assert response.status_code == 422
    assert response.json() == {"detail": "Teacher 999999 does not exist"}


def test_admin_removes_the_head(client: TestClient, world: World) -> None:
    body = patch(client, world.admin, world.dept_a, {"head_id": None}).json()
    assert body["head_id"] is None


def test_update_of_a_missing_department_is_404(client: TestClient, world: World) -> None:
    response = client.patch(
        f"{URL}/999999", json={"building": "X"}, headers=auth_headers(world.admin)
    )
    assert response.status_code == 404


# ===================================================================== update: HOD and others


def test_hod_updates_description_building_and_phone_of_own_department(
    client: TestClient, world: World
) -> None:
    payload = {"description": "Our department", "building": "East Wing", "phone": "555-2000"}

    response = patch(client, world.hod, world.dept_a, payload)

    assert response.status_code == 200
    assert {k: response.json()[k] for k in payload} == payload


@pytest.mark.parametrize(
    ("payload", "named"),
    [
        ({"name": "Renamed"}, "name"),
        ({"code": "NEWA"}, "code"),
        ({"head_id": None}, "head_id"),
        ({"building": "Ok", "code": "NEWA"}, "code"),
    ],
)
def test_hod_cannot_change_name_code_or_head(
    client: TestClient, world: World, payload: dict[str, object], named: str
) -> None:
    response = patch(client, world.hod, world.dept_a, payload)

    assert response.status_code == 403
    assert f"(not {named})" in response.json()["detail"]


def test_hod_change_that_is_refused_changes_nothing(
    client: TestClient, session: Session, world: World
) -> None:
    patch(client, world.hod, world.dept_a, {"building": "Sneaky", "name": "Renamed"})

    session.refresh(world.dept_a)
    assert (world.dept_a.building, world.dept_a.name) == (None, "Department A")


def test_hod_cannot_update_another_department(client: TestClient, world: World) -> None:
    response = patch(client, world.hod, world.dept_b, {"building": "Not mine"})

    assert response.status_code == 403
    assert response.json() == {"detail": "You can only edit the department you head"}


def test_hod_whose_head_role_is_stale_cannot_update(
    client: TestClient, session: Session, world: World
) -> None:
    world.dept_a.head_id = world.other_teacher_id
    session.commit()

    response = patch(client, world.hod, world.dept_a, {"building": "Still mine?"})

    assert response.status_code == 403


@pytest.mark.parametrize("role", ["teacher", "student"])
def test_teachers_and_students_cannot_update(client: TestClient, world: World, role: str) -> None:
    response = patch(client, world.user(role), world.dept_a, {"building": "X"})

    assert response.status_code == 403
    assert response.json() == {"detail": "Not enough permissions"}


def test_update_requires_authentication(client: TestClient, world: World) -> None:
    assert client.patch(f"{URL}/{world.dept_a.id}", json={"building": "X"}).status_code == 401


# ===================================================================== delete


def test_admin_deletes_an_empty_department(client: TestClient, world: World) -> None:
    response = client.delete(f"{URL}/{world.dept_b.id}", headers=auth_headers(world.admin))

    assert response.status_code == 204
    assert response.content == b""
    gone = client.get(f"{URL}/{world.dept_b.id}", headers=auth_headers(world.admin))
    assert gone.status_code == 404


def test_department_with_dependents_cannot_be_deleted(client: TestClient, world: World) -> None:
    response = client.delete(f"{URL}/{world.dept_a.id}", headers=auth_headers(world.admin))

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Department DEPA can't be deleted while it has 2 teachers, 1 student, "
        "1 course. Move or delete them first."
    }


@pytest.mark.parametrize("kind", ["teacher", "student", "course"])
def test_any_single_kind_of_dependent_blocks_deletion(
    client: TestClient, factory: Factory, world: World, kind: str
) -> None:
    getattr(factory, kind)(world.dept_b)

    response = client.delete(f"{URL}/{world.dept_b.id}", headers=auth_headers(world.admin))

    assert response.status_code == 409
    assert f"1 {kind}" in response.json()["detail"]


@pytest.mark.parametrize("role", ["hod", "teacher", "student"])
def test_only_admin_can_delete(client: TestClient, world: World, role: str) -> None:
    response = client.delete(f"{URL}/{world.dept_b.id}", headers=auth_headers(world.user(role)))
    assert response.status_code == 403


def test_delete_of_a_missing_department_is_404(client: TestClient, world: World) -> None:
    response = client.delete(f"{URL}/999999", headers=auth_headers(world.admin))
    assert response.status_code == 404
