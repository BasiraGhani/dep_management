"""Tests for the teachers API (T3.2): FR-3.1–FR-3.4, BR-1/2/3/7/8 and the Teachers
row of the permission matrix, with the T3.2 decisions (teacher self-edit = phone and
email; students see public fields; deleting a teacher with an account -> 409).

`world`:
    dept A: head `hod` (Hedy Head), `teacher` (Tom Teach, teaches A101, has a login),
            `spare` (Sam Spare: no course, no login)
    dept B: `outsider` (Olga Out, no login, no course)
    plus `admin` and `student` (in A) logins
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from typing import cast

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Department, Teacher, TeacherTitle, User, UserRole
from tests.conftest import Factory
from tests.helpers import auth_headers

URL = "/api/v1/teachers"
ROLES = ["admin", "hod", "teacher", "student"]
STAFF_ONLY_FIELDS = {"phone", "hire_date", "created_at", "updated_at", "user_id"}


@dataclass
class World:
    dept_a: Department
    dept_b: Department
    head: Teacher
    teaching: Teacher
    spare: Teacher
    outsider: Teacher
    admin: User
    hod: User
    teacher: User
    student: User

    def user(self, role: str) -> User:
        return cast(User, getattr(self, role))


@pytest.fixture
def world(session: Session, factory: Factory) -> World:
    dept_a = factory.department(code="DEPA", name="Department A")
    dept_b = factory.department(code="DEPB", name="Department B")
    head = factory.teacher(
        dept_a, first_name="Hedy", last_name="Head", email="hedy@uni.edu", phone="555-0001"
    )
    teaching = factory.teacher(
        dept_a,
        first_name="Tom",
        last_name="Teach",
        email="tom@uni.edu",
        title=TeacherTitle.ASSISTANT_PROFESSOR,
        phone="555-0002",
        hire_date=date(2020, 9, 1),
    )
    spare = factory.teacher(dept_a, first_name="Sam", last_name="Spare", email="sam@uni.edu")
    outsider = factory.teacher(dept_b, first_name="Olga", last_name="Out", email="olga@uni.edu")
    dept_a.head_id = head.id
    factory.course(dept_a, teacher=teaching, code="A101")
    world = World(
        dept_a=dept_a,
        dept_b=dept_b,
        head=head,
        teaching=teaching,
        spare=spare,
        outsider=outsider,
        admin=factory.user(UserRole.ADMIN),
        hod=factory.user(UserRole.HOD, teacher=head),
        teacher=factory.user(UserRole.TEACHER, teacher=teaching),
        student=factory.user(UserRole.STUDENT, student=factory.student(dept_a)),
    )
    session.commit()
    return world


def new_teacher(department_id: int, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "first_name": "Nora",
        "last_name": "New",
        "email": "nora@uni.edu",
        "title": "lecturer",
        "department_id": department_id,
    }
    return payload | overrides


def patch(
    client: TestClient, user: User, teacher: Teacher, payload: Mapping[str, object]
) -> httpx.Response:
    response: httpx.Response = client.patch(
        f"{URL}/{teacher.id}", json=dict(payload), headers=auth_headers(user)
    )
    return response


# ===================================================================== list (FR-3.1)


@pytest.mark.parametrize("role", ROLES)
def test_every_role_can_list_teachers(client: TestClient, world: World, role: str) -> None:
    body = client.get(URL, headers=auth_headers(world.user(role))).json()

    assert body["total"] == 4
    assert [t["last_name"] for t in body["items"]] == ["Head", "Out", "Spare", "Teach"]


@pytest.mark.parametrize("role", ["admin", "hod", "teacher"])
def test_staff_see_every_field(client: TestClient, world: World, role: str) -> None:
    items = client.get(URL, headers=auth_headers(world.user(role))).json()["items"]
    tom = next(t for t in items if t["last_name"] == "Teach")

    assert tom["phone"] == "555-0002"
    assert tom["hire_date"] == "2020-09-01"
    assert {"created_at", "updated_at"} <= set(tom)


def test_students_see_only_public_fields(client: TestClient, world: World) -> None:
    items = client.get(URL, headers=auth_headers(world.student)).json()["items"]

    for teacher in items:
        assert set(teacher) == {"id", "first_name", "last_name", "title", "email", "department_id"}
    assert "555-0002" not in str(items)


def test_list_requires_authentication(client: TestClient, world: World) -> None:
    assert client.get(URL).status_code == 401


@pytest.mark.parametrize(
    ("search", "last_names"),
    [
        ("tom", ["Teach"]),  # first name
        ("SPARE", ["Spare"]),  # last name, any case
        ("hedy head", ["Head"]),  # full name
        ("olga@uni", ["Out"]),  # email
        ("@uni.edu", ["Head", "Out", "Spare", "Teach"]),
        ("nobody", []),
    ],
)
def test_search_by_name_or_email(
    client: TestClient, world: World, search: str, last_names: list[str]
) -> None:
    body = client.get(URL, params={"search": search}, headers=auth_headers(world.admin)).json()

    assert [t["last_name"] for t in body["items"]] == last_names
    assert body["total"] == len(last_names)


def test_filter_by_department(client: TestClient, world: World) -> None:
    params = {"department_id": world.dept_b.id}
    body = client.get(URL, params=params, headers=auth_headers(world.admin)).json()

    assert [t["last_name"] for t in body["items"]] == ["Out"]


def test_filter_by_title(client: TestClient, world: World) -> None:
    params = {"title": "assistant_professor"}
    body = client.get(URL, params=params, headers=auth_headers(world.admin)).json()

    assert [t["last_name"] for t in body["items"]] == ["Teach"]


def test_filters_and_search_combine(client: TestClient, world: World) -> None:
    params = {"department_id": world.dept_a.id, "search": "o"}  # Tom, Olga(B) excluded
    body = client.get(URL, params=params, headers=auth_headers(world.admin)).json()

    assert [t["last_name"] for t in body["items"]] == ["Teach"]


def test_pagination(client: TestClient, world: World) -> None:
    params = {"skip": 1, "limit": 2}
    body = client.get(URL, params=params, headers=auth_headers(world.admin)).json()

    assert body["total"] == 4
    assert [t["last_name"] for t in body["items"]] == ["Out", "Spare"]


@pytest.mark.parametrize("params", [{"title": "dean"}, {"department_id": "x"}, {"limit": 101}])
def test_invalid_filters_are_rejected(
    client: TestClient, world: World, params: dict[str, object]
) -> None:
    assert client.get(URL, params=params, headers=auth_headers(world.admin)).status_code == 422


# ===================================================================== create (FR-3.1–3.3)


def test_admin_creates_a_teacher_in_any_department(client: TestClient, world: World) -> None:
    payload = new_teacher(
        world.dept_b.id,
        email=" Nora@Uni.EDU ",
        phone="+44 20 7946 0000",
        title="professor",
        hire_date="2024-01-15",
    )
    response = client.post(URL, json=payload, headers=auth_headers(world.admin))

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "nora@uni.edu"
    assert (body["title"], body["department_id"]) == ("professor", world.dept_b.id)
    assert (body["phone"], body["hire_date"]) == ("+44 20 7946 0000", "2024-01-15")


def test_create_with_an_account_creates_a_teacher_login(
    client: TestClient, session: Session, world: World
) -> None:
    payload = new_teacher(
        world.dept_a.id, create_account={"username": "Nora.New", "temp_password": "temporary-1"}
    )
    response = client.post(URL, json=payload, headers=auth_headers(world.admin))

    assert response.status_code == 201
    account = session.scalars(select(User).where(User.username == "nora.new")).one()
    assert account.role is UserRole.TEACHER
    assert account.teacher_id == response.json()["id"]
    assert "temporary-1" not in response.text
    login = client.post(
        "/api/v1/auth/login", data={"username": "nora.new", "password": "temporary-1"}
    )
    assert login.status_code == 200


def test_hod_creates_a_teacher_in_their_own_department(client: TestClient, world: World) -> None:
    response = client.post(URL, json=new_teacher(world.dept_a.id), headers=auth_headers(world.hod))
    assert response.status_code == 201


def test_hod_creates_a_teacher_with_an_account(client: TestClient, world: World) -> None:
    payload = new_teacher(
        world.dept_a.id, create_account={"username": "nora", "temp_password": "temporary-1"}
    )
    assert client.post(URL, json=payload, headers=auth_headers(world.hod)).status_code == 201


def test_hod_cannot_create_a_teacher_in_another_department(
    client: TestClient, world: World
) -> None:
    response = client.post(URL, json=new_teacher(world.dept_b.id), headers=auth_headers(world.hod))

    assert response.status_code == 403
    assert response.json() == {"detail": "You can only add teachers to the department you head"}


@pytest.mark.parametrize("role", ["teacher", "student"])
def test_teachers_and_students_cannot_create(client: TestClient, world: World, role: str) -> None:
    response = client.post(
        URL, json=new_teacher(world.dept_a.id), headers=auth_headers(world.user(role))
    )
    assert response.status_code == 403


def test_duplicate_email_is_a_conflict(client: TestClient, world: World) -> None:
    payload = new_teacher(world.dept_a.id, email="TOM@uni.edu")
    response = client.post(URL, json=payload, headers=auth_headers(world.admin))

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_duplicate_username_is_a_conflict_and_creates_nothing(
    client: TestClient, session: Session, world: World
) -> None:
    taken = world.teacher.username
    payload = new_teacher(
        world.dept_a.id, create_account={"username": taken.upper(), "temp_password": "temporary-1"}
    )
    response = client.post(URL, json=payload, headers=auth_headers(world.admin))

    assert response.status_code == 409
    assert "already taken" in response.json()["detail"]
    assert session.scalar(select(Teacher).where(Teacher.email == "nora@uni.edu")) is None


def test_create_in_a_missing_department_is_rejected(client: TestClient, world: World) -> None:
    response = client.post(URL, json=new_teacher(999_999), headers=auth_headers(world.admin))

    assert response.status_code == 422
    assert response.json() == {"detail": "Department 999999 does not exist"}


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"first_name": ""}, "first_name"),
        ({"last_name": "L" * 61}, "last_name"),
        ({"email": "not-an-email"}, "email"),
        ({"email": "a@b"}, "email"),
        ({"title": "dean"}, "title"),
        ({"phone": "phone me"}, "phone"),
        ({"hire_date": "2024-02-30"}, "hire_date"),
        ({"hire_date": (date.today() + timedelta(days=1)).isoformat()}, "hire_date"),
        ({"create_account": {"username": "ab", "temp_password": "temporary-1"}}, "username"),
        ({"create_account": {"username": "has space", "temp_password": "x" * 8}}, "username"),
        ({"create_account": {"username": "nora", "temp_password": "short"}}, "temp_password"),
        ({"salary": 1}, "salary"),
    ],
)
def test_create_validates_fields(
    client: TestClient, world: World, overrides: dict[str, object], field: str
) -> None:
    payload = new_teacher(world.dept_a.id, **overrides)
    response = client.post(URL, json=payload, headers=auth_headers(world.admin))

    assert response.status_code == 422
    assert field in {str(error["loc"][-1]) for error in response.json()["detail"]}


@pytest.mark.parametrize("missing", ["first_name", "last_name", "email", "title", "department_id"])
def test_create_requires_fields(client: TestClient, world: World, missing: str) -> None:
    payload = new_teacher(world.dept_a.id)
    del payload[missing]
    response = client.post(URL, json=payload, headers=auth_headers(world.admin))
    assert response.status_code == 422


# ===================================================================== detail


@pytest.mark.parametrize("role", ["admin", "hod", "teacher"])
def test_staff_detail_has_courses_and_account(client: TestClient, world: World, role: str) -> None:
    response = client.get(f"{URL}/{world.teaching.id}", headers=auth_headers(world.user(role)))

    assert response.status_code == 200
    body = response.json()
    assert body["last_name"] == "Teach"
    assert body["phone"] == "555-0002"
    assert [c["code"] for c in body["courses"]] == ["A101"]
    assert body["user_id"] == world.teacher.id


def test_student_detail_has_public_fields_and_courses(client: TestClient, world: World) -> None:
    body = client.get(f"{URL}/{world.teaching.id}", headers=auth_headers(world.student)).json()

    assert not STAFF_ONLY_FIELDS & set(body)
    assert body["email"] == "tom@uni.edu"
    assert [c["code"] for c in body["courses"]] == ["A101"]


def test_detail_of_a_teacher_without_account_or_courses(client: TestClient, world: World) -> None:
    body = client.get(f"{URL}/{world.spare.id}", headers=auth_headers(world.admin)).json()

    assert (body["courses"], body["user_id"]) == ([], None)


def test_detail_of_a_missing_teacher_is_404(client: TestClient, world: World) -> None:
    response = client.get(f"{URL}/999999", headers=auth_headers(world.student))

    assert response.status_code == 404
    assert response.json() == {"detail": "Teacher not found"}


# ===================================================================== update: admin


def test_admin_updates_any_field(client: TestClient, world: World) -> None:
    payload = {
        "first_name": "Samuel",
        "title": "professor",
        "email": "samuel@uni.edu",
        "phone": "555-9999",
        "hire_date": "2019-01-01",
    }
    response = patch(client, world.admin, world.spare, payload)

    assert response.status_code == 200
    assert {k: response.json()[k] for k in payload} == payload


def test_admin_moves_a_free_teacher_to_another_department(client: TestClient, world: World) -> None:
    response = patch(client, world.admin, world.spare, {"department_id": world.dept_b.id})

    assert response.status_code == 200
    assert response.json()["department_id"] == world.dept_b.id


def test_moving_a_department_head_is_a_conflict(client: TestClient, world: World) -> None:
    response = patch(client, world.admin, world.head, {"department_id": world.dept_b.id})

    assert response.status_code == 409
    assert "heads department DEPA" in response.json()["detail"]


def test_moving_a_teacher_with_courses_is_a_conflict(client: TestClient, world: World) -> None:
    response = patch(client, world.admin, world.teaching, {"department_id": world.dept_b.id})

    assert response.status_code == 409
    assert "teaches 1 course" in response.json()["detail"]


def test_moving_to_a_missing_department_is_rejected(client: TestClient, world: World) -> None:
    response = patch(client, world.admin, world.spare, {"department_id": 999_999})
    assert response.status_code == 422


def test_setting_the_same_department_is_not_a_move(client: TestClient, world: World) -> None:
    response = patch(client, world.admin, world.head, {"department_id": world.dept_a.id})
    assert response.status_code == 200


def test_update_to_another_teachers_email_is_a_conflict(client: TestClient, world: World) -> None:
    response = patch(client, world.admin, world.spare, {"email": "OLGA@uni.edu"})
    assert response.status_code == 409


def test_keeping_your_own_email_is_not_a_conflict(client: TestClient, world: World) -> None:
    response = patch(client, world.admin, world.spare, {"email": "SAM@uni.edu"})
    assert response.status_code == 200


@pytest.mark.parametrize("field", ["first_name", "last_name", "email", "title", "department_id"])
def test_required_fields_cannot_be_cleared(client: TestClient, world: World, field: str) -> None:
    response = patch(client, world.admin, world.spare, {field: None})

    assert response.status_code == 422
    assert f"{field} cannot be null" in response.text


def test_optional_fields_can_be_cleared(client: TestClient, world: World) -> None:
    body = patch(client, world.admin, world.teaching, {"phone": None, "hire_date": None}).json()
    assert (body["phone"], body["hire_date"]) == (None, None)


def test_update_of_a_missing_teacher_is_404(client: TestClient, world: World) -> None:
    response = client.patch(
        f"{URL}/999999", json={"phone": "555"}, headers=auth_headers(world.admin)
    )
    assert response.status_code == 404


# ===================================================================== update: HOD


def test_hod_updates_a_teacher_in_their_department(client: TestClient, world: World) -> None:
    payload = {"title": "professor", "last_name": "Spare-Jones", "phone": "555-3333"}
    response = patch(client, world.hod, world.spare, payload)

    assert response.status_code == 200
    assert {k: response.json()[k] for k in payload} == payload


def test_hod_updates_their_own_record(client: TestClient, world: World) -> None:
    assert patch(client, world.hod, world.head, {"title": "professor"}).status_code == 200


def test_hod_cannot_move_a_teacher_out_of_their_department(
    client: TestClient, world: World
) -> None:
    response = patch(client, world.hod, world.spare, {"department_id": world.dept_b.id})

    assert response.status_code == 403
    assert "can't move teachers" in response.json()["detail"]


def test_hod_cannot_edit_a_teacher_in_another_department(client: TestClient, world: World) -> None:
    response = patch(client, world.hod, world.outsider, {"phone": "555-0000"})

    assert response.status_code == 403
    assert response.json() == {"detail": "You can't edit this teacher"}


# ===================================================================== update: teacher self


def test_teacher_updates_own_phone_and_email(client: TestClient, world: World) -> None:
    payload = {"phone": "555-7777", "email": "Tom.Teach@uni.edu"}
    response = patch(client, world.teacher, world.teaching, payload)

    assert response.status_code == 200
    assert (response.json()["phone"], response.json()["email"]) == ("555-7777", "tom.teach@uni.edu")


@pytest.mark.parametrize(
    "payload",
    [
        {"title": "professor"},
        {"first_name": "Thomas"},
        {"hire_date": "2010-01-01"},
        {"department_id": 1},
        {"phone": "555-1", "title": "professor"},
    ],
)
def test_teacher_cannot_change_other_fields_of_their_own_record(
    client: TestClient, world: World, payload: dict[str, object]
) -> None:
    response = patch(client, world.teacher, world.teaching, payload)

    assert response.status_code == 403
    assert response.json()["detail"].startswith("You can only change your own phone and email")


def test_teacher_cannot_edit_another_teacher(client: TestClient, world: World) -> None:
    assert patch(client, world.teacher, world.spare, {"phone": "555-0000"}).status_code == 403


def test_teacher_email_change_is_still_unique(client: TestClient, world: World) -> None:
    response = patch(client, world.teacher, world.teaching, {"email": "sam@uni.edu"})
    assert response.status_code == 409


def test_refused_update_changes_nothing(client: TestClient, session: Session, world: World) -> None:
    patch(client, world.teacher, world.teaching, {"phone": "555-1234", "title": "professor"})

    session.refresh(world.teaching)
    assert (world.teaching.phone, world.teaching.title) == (
        "555-0002",
        TeacherTitle.ASSISTANT_PROFESSOR,
    )


# ===================================================================== update: student


def test_student_cannot_update_teachers(client: TestClient, world: World) -> None:
    response = patch(client, world.student, world.teaching, {"phone": "555"})

    assert response.status_code == 403
    assert response.json() == {"detail": "Not enough permissions"}


def test_update_requires_authentication(client: TestClient, world: World) -> None:
    assert client.patch(f"{URL}/{world.spare.id}", json={"phone": "555"}).status_code == 401


# ===================================================================== delete (FR-3.4)


def test_admin_deletes_a_free_teacher(client: TestClient, world: World) -> None:
    response = client.delete(f"{URL}/{world.spare.id}", headers=auth_headers(world.admin))

    assert response.status_code == 204
    assert (
        client.get(f"{URL}/{world.spare.id}", headers=auth_headers(world.admin)).status_code == 404
    )


def test_department_head_cannot_be_deleted(client: TestClient, world: World) -> None:
    response = client.delete(f"{URL}/{world.head.id}", headers=auth_headers(world.admin))

    assert response.status_code == 409
    assert "they head department DEPA" in response.json()["detail"]


def test_teacher_with_courses_cannot_be_deleted(
    client: TestClient, factory: Factory, world: World
) -> None:
    factory.course(world.dept_b, teacher=world.outsider)

    response = client.delete(f"{URL}/{world.outsider.id}", headers=auth_headers(world.admin))

    assert response.status_code == 409
    assert response.json() == {"detail": "Teacher can't be deleted: they teach 1 course"}


def test_teacher_with_a_login_account_cannot_be_deleted(
    client: TestClient, factory: Factory, world: World
) -> None:
    factory.user(UserRole.TEACHER, teacher=world.outsider)

    response = client.delete(f"{URL}/{world.outsider.id}", headers=auth_headers(world.admin))

    assert response.status_code == 409
    assert "have a login account" in response.json()["detail"]


def test_conflict_message_lists_every_reason(client: TestClient, world: World) -> None:
    response = client.delete(f"{URL}/{world.teaching.id}", headers=auth_headers(world.admin))

    assert response.json() == {
        "detail": "Teacher can't be deleted: they teach 1 course and have a login account "
        "(deactivate or delete it first)"
    }


@pytest.mark.parametrize("role", ["hod", "teacher", "student"])
def test_only_admin_can_delete(client: TestClient, world: World, role: str) -> None:
    response = client.delete(f"{URL}/{world.spare.id}", headers=auth_headers(world.user(role)))
    assert response.status_code == 403


def test_delete_of_a_missing_teacher_is_404(client: TestClient, world: World) -> None:
    assert client.delete(f"{URL}/999999", headers=auth_headers(world.admin)).status_code == 404
