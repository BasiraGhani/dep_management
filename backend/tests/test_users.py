"""Tests for the users API (T4.4): FR-8.1, FR-8.2, the §2 role/link rules, BR-6 and
the approved DELETE /users/{id}.

`world`:
    dept A: head HA (`hod` login), TA (`teacher` login), T_FREE (no account)
    dept B: head HB (no account)
    students: S1 (`student` login), S_FREE (no account)
    plus `admin` (the caller) and `other_admin`
"""

from dataclasses import dataclass
from typing import cast

import httpx2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models import Student, Teacher, User, UserRole
from tests.conftest import Factory
from tests.helpers import auth_headers

URL = "/api/v1/users"
PASSWORD = "users-test-pass"


@dataclass
class World:
    head_a: Teacher
    teacher_a: Teacher
    t_free: Teacher
    head_b: Teacher
    s1: Student
    s_free: Student
    admin: User
    other_admin: User
    hod: User
    teacher: User
    student: User

    def user(self, role: str) -> User:
        return cast(User, getattr(self, role))


@pytest.fixture
def world(session: Session, factory: Factory) -> World:
    dept_a, dept_b = factory.department(code="DEPA"), factory.department(code="DEPB")
    head_a = factory.teacher(dept_a, first_name="Hedy", last_name="Head")
    teacher_a, t_free = (
        factory.teacher(dept_a),
        factory.teacher(dept_a, first_name="Fran", last_name="Free"),
    )
    head_b = factory.teacher(dept_b, first_name="Bert", last_name="Boss")
    dept_a.head_id, dept_b.head_id = head_a.id, head_b.id
    s1, s_free = factory.student(dept_a), factory.student(dept_a)
    world = World(
        head_a=head_a,
        teacher_a=teacher_a,
        t_free=t_free,
        head_b=head_b,
        s1=s1,
        s_free=s_free,
        admin=factory.user(UserRole.ADMIN, username="admin"),
        other_admin=factory.user(UserRole.ADMIN, username="other-admin"),
        hod=factory.user(UserRole.HOD, teacher=head_a, username="hod"),
        teacher=factory.user(
            UserRole.TEACHER, teacher=teacher_a, username="teacher", password=PASSWORD
        ),
        student=factory.user(UserRole.STUDENT, student=s1, username="student"),
    )
    session.commit()
    return world


def create(client: TestClient, world: World, **payload: object) -> httpx2.Response:
    body = {"username": "newbie", "password": PASSWORD, **payload}
    response: httpx2.Response = client.post(URL, json=body, headers=auth_headers(world.admin))
    return response


def patch(client: TestClient, world: World, user: User, **payload: object) -> httpx2.Response:
    response: httpx2.Response = client.patch(
        f"{URL}/{user.id}", json=payload, headers=auth_headers(world.admin)
    )
    return response


def login(client: TestClient, username: str, password: str = PASSWORD) -> int:
    response: httpx2.Response = client.post(
        "/api/v1/auth/login", data={"username": username, "password": password}
    )
    return response.status_code


# ===================================================== admins only (FR-8)


@pytest.mark.parametrize("role", ["hod", "teacher", "student"])
@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("GET", "", None),
        ("POST", "", {"username": "x-user", "password": PASSWORD, "role": "admin"}),
        ("PATCH", "/{id}", {"is_active": False}),
        ("POST", "/{id}/reset-password", None),
        ("DELETE", "/{id}", None),
    ],
    ids=["list", "create", "update", "reset-password", "delete"],
)
def test_non_admins_get_403_on_every_endpoint(
    client: TestClient,
    session: Session,
    world: World,
    role: str,
    method: str,
    path: str,
    body: dict[str, object] | None,
) -> None:
    target = world.other_admin
    response = client.request(
        method,
        URL + path.format(id=target.id),
        json=body,
        headers=auth_headers(world.user(role)),
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Not enough permissions"}
    session.refresh(target)
    assert target.is_active is True


@pytest.mark.parametrize(
    ("method", "path"),
    [("GET", ""), ("POST", ""), ("PATCH", "/1"), ("POST", "/1/reset-password"), ("DELETE", "/1")],
)
def test_every_endpoint_requires_authentication(
    client: TestClient, world: World, method: str, path: str
) -> None:
    assert client.request(method, URL + path, json={}).status_code == 401


# ===================================================== list


def test_admin_lists_all_accounts(client: TestClient, world: World) -> None:
    body = client.get(URL, headers=auth_headers(world.admin)).json()

    assert [u["username"] for u in body["items"]] == [
        "admin",
        "hod",
        "other-admin",
        "student",
        "teacher",
    ]
    assert body["total"] == 5
    assert "password" not in str(body)


@pytest.mark.parametrize(
    ("params", "usernames"),
    [
        ({"role": "admin"}, ["admin", "other-admin"]),
        ({"role": "student"}, ["student"]),
        ({"is_active": "false"}, ["teacher"]),
        ({"is_active": "true", "role": "hod"}, ["hod"]),
        ({"search": "ADMIN"}, ["admin", "other-admin"]),
    ],
)
def test_list_filters(
    client: TestClient,
    session: Session,
    world: World,
    params: dict[str, str],
    usernames: list[str],
) -> None:
    world.teacher.is_active = False
    session.commit()

    body = client.get(URL, params=params, headers=auth_headers(world.admin)).json()

    assert [u["username"] for u in body["items"]] == usernames


def test_list_pagination(client: TestClient, world: World) -> None:
    body = client.get(URL, params={"skip": 1, "limit": 2}, headers=auth_headers(world.admin)).json()
    assert ([u["username"] for u in body["items"]], body["total"]) == (["hod", "other-admin"], 5)


@pytest.mark.parametrize("params", [{"role": "dean"}, {"is_active": "maybe"}])
def test_invalid_list_filters(client: TestClient, world: World, params: dict[str, str]) -> None:
    assert client.get(URL, params=params, headers=auth_headers(world.admin)).status_code == 422


# ===================================================== create (FR-8.1)


@pytest.mark.parametrize(
    ("role", "link"),
    [
        ("admin", {}),
        ("teacher", {"teacher_id": "t_free"}),
        ("hod", {"teacher_id": "head_b"}),  # B's head has no account yet
        ("student", {"student_id": "s_free"}),
    ],
)
def test_admin_creates_a_valid_account_that_can_log_in(
    client: TestClient, world: World, role: str, link: dict[str, str]
) -> None:
    ids = {k: cast(Teacher | Student, getattr(world, v)).id for k, v in link.items()}

    response = create(client, world, username=" New.User ", role=role, **ids)

    assert response.status_code == 201
    body = response.json()
    assert (body["username"], body["role"], body["is_active"]) == ("new.user", role, True)
    assert body.get("teacher_id") == ids.get("teacher_id")
    assert body.get("student_id") == ids.get("student_id")
    assert "password" not in response.text
    assert login(client, "new.user") == 200


@pytest.mark.parametrize(
    ("payload", "detail"),
    [
        (
            {"role": "admin", "teacher_id": "t_free"},
            "An admin account can't be linked to a teacher or student",
        ),
        (
            {"role": "admin", "student_id": "s_free"},
            "An admin account can't be linked to a teacher or student",
        ),
        ({"role": "teacher"}, "A teacher account must be linked to a teacher (teacher_id)"),
        ({"role": "hod"}, "A hod account must be linked to a teacher (teacher_id)"),
        (
            {"role": "teacher", "teacher_id": "t_free", "student_id": "s_free"},
            "A teacher account can't be linked to a student",
        ),
        ({"role": "student"}, "A student account must be linked to a student (student_id)"),
        (
            {"role": "student", "student_id": "s_free", "teacher_id": "t_free"},
            "A student account can't be linked to a teacher",
        ),
    ],
)
def test_invalid_role_and_link_combinations_are_rejected(
    client: TestClient, session: Session, world: World, payload: dict[str, str], detail: str
) -> None:
    resolved = {
        k: (cast(Teacher | Student, getattr(world, v)).id if k.endswith("_id") else v)
        for k, v in payload.items()
    }

    response = create(client, world, **resolved)

    assert response.status_code == 422
    assert response.json() == {"detail": detail}
    assert session.scalar(select(User).where(User.username == "newbie")) is None


@pytest.mark.parametrize(
    ("payload", "detail"),
    [
        (
            {"role": "hod", "teacher_id": "t_free"},
            "Fran Free doesn't head a department, so the account can't be hod. "
            "Make them a department head instead (PATCH /departments/{id}).",
        ),
        (
            {"role": "teacher", "teacher_id": "head_b"},
            "Bert Boss is the head of DEPB, so the account must be hod. "
            "Appoint another head first to make them a teacher.",
        ),
    ],
)
def test_br6_is_enforced_on_create(
    client: TestClient, world: World, payload: dict[str, str], detail: str
) -> None:
    resolved = {k: (getattr(world, v).id if k == "teacher_id" else v) for k, v in payload.items()}

    response = create(client, world, **resolved)

    assert response.status_code == 422
    assert response.json() == {"detail": detail}


@pytest.mark.parametrize(
    ("payload", "detail"),
    [
        ({"role": "teacher", "teacher_id": 999_999}, "Teacher 999999 does not exist"),
        ({"role": "student", "student_id": 999_999}, "Student 999999 does not exist"),
    ],
)
def test_links_to_missing_records_are_rejected(
    client: TestClient, world: World, payload: dict[str, object], detail: str
) -> None:
    response = create(client, world, **payload)
    assert (response.status_code, response.json()) == (422, {"detail": detail})


def test_a_teacher_or_student_can_only_have_one_account(client: TestClient, world: World) -> None:
    taken_teacher = create(client, world, role="teacher", teacher_id=world.teacher_a.id)
    taken_student = create(client, world, role="student", student_id=world.s1.id)

    assert taken_teacher.status_code == taken_student.status_code == 409
    assert taken_teacher.json() == {
        "detail": f"Teacher {world.teacher_a.id} already has an account ('teacher')"
    }


def test_duplicate_username_is_a_conflict(client: TestClient, world: World) -> None:
    response = create(client, world, username="TEACHER", role="admin")
    assert (response.status_code, response.json()) == (
        409,
        {"detail": "Username 'teacher' is already taken"},
    )


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"role": "admin", "password": "short"}, "password"),
        ({"role": "admin", "username": "ab"}, "username"),
        ({"role": "admin", "username": "has space"}, "username"),
        ({"role": "dean"}, "role"),
        ({"role": "admin", "is_active": False}, "is_active"),
    ],
)
def test_create_validates_fields(
    client: TestClient, world: World, payload: dict[str, object], field: str
) -> None:
    response = create(client, world, **payload)

    assert response.status_code == 422
    assert field in {str(e["loc"][-1]) for e in response.json()["detail"]}


# ===================================================== update: (de)activate (FR-8.1, 8.2)


def test_deactivated_user_cannot_log_in_until_reactivated(client: TestClient, world: World) -> None:
    assert patch(client, world, world.teacher, is_active=False).json()["is_active"] is False
    assert login(client, "teacher") == 403

    assert patch(client, world, world.teacher, is_active=True).json()["is_active"] is True
    assert login(client, "teacher") == 200


def test_deactivating_ends_existing_sessions(client: TestClient, world: World) -> None:
    headers = auth_headers(world.teacher)
    patch(client, world, world.teacher, is_active=False)

    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_admin_can_deactivate_another_admin(client: TestClient, world: World) -> None:
    assert patch(client, world, world.other_admin, is_active=False).status_code == 200


@pytest.mark.parametrize(
    ("payload", "detail"),
    [
        ({"is_active": False}, "You can't deactivate your own account"),
        ({"role": "teacher", "teacher_id": 1}, "You can't change the role of your own account"),
    ],
)
def test_admin_cannot_lock_themselves_out(
    client: TestClient, world: World, payload: dict[str, object], detail: str
) -> None:
    response = patch(client, world, world.admin, **payload)
    assert (response.status_code, response.json()) == (403, {"detail": detail})


# ===================================================== update: role and links


def test_relink_a_teacher_account_to_another_teacher(client: TestClient, world: World) -> None:
    response = patch(client, world, world.teacher, teacher_id=world.t_free.id)

    assert response.status_code == 200
    assert response.json()["teacher_id"] == world.t_free.id


def test_turn_an_account_into_a_student_account(client: TestClient, world: World) -> None:
    response = patch(
        client, world, world.teacher, role="student", teacher_id=None, student_id=world.s_free.id
    )

    assert response.status_code == 200
    assert (response.json()["role"], response.json()["teacher_id"]) == ("student", None)


@pytest.mark.parametrize(
    ("target", "payload", "detail_start"),
    [
        ("teacher", {"teacher_id": None}, "A teacher account must be linked"),
        ("teacher", {"role": "student"}, "A student account must be linked"),
        ("teacher", {"student_id": "s_free"}, "A teacher account can't be linked to a student"),
        ("student", {"role": "admin"}, "An admin account can't be linked"),
        ("teacher", {"role": "hod"}, "doesn't head a department"),  # BR-6
        ("hod", {"role": "teacher"}, "Hedy Head is the head of DEPA"),  # BR-6
    ],
)
def test_invalid_updates_are_rejected_and_change_nothing(
    client: TestClient,
    session: Session,
    world: World,
    target: str,
    payload: dict[str, object],
    detail_start: str,
) -> None:
    user = world.user(target)
    before = (user.role, user.teacher_id, user.student_id)
    resolved = {
        k: (getattr(world, v).id if isinstance(v, str) and k.endswith("_id") else v)
        for k, v in payload.items()
    }

    response = patch(client, world, user, **resolved)

    assert response.status_code == 422
    assert detail_start in response.json()["detail"]
    session.refresh(user)
    assert (user.role, user.teacher_id, user.student_id) == before


def test_linking_to_a_record_that_has_an_account_is_a_conflict(
    client: TestClient, world: World
) -> None:
    response = patch(client, world, world.teacher, teacher_id=world.head_a.id, role="hod")
    assert response.status_code == 409


@pytest.mark.parametrize("payload", [{"role": None}, {"is_active": None}, {"username": "x"}])
def test_update_body_is_validated(
    client: TestClient, world: World, payload: dict[str, object]
) -> None:
    assert patch(client, world, world.teacher, **payload).status_code == 422


def test_update_of_a_missing_user_is_404(client: TestClient, world: World) -> None:
    response = client.patch(
        f"{URL}/999999", json={"is_active": False}, headers=auth_headers(world.admin)
    )
    assert response.status_code == 404


# ===================================================== reset password (FR-8.1)


def test_reset_password_returns_a_working_temporary_password(
    client: TestClient, session: Session, world: World
) -> None:
    response = client.post(
        f"{URL}/{world.teacher.id}/reset-password", headers=auth_headers(world.admin)
    )

    assert response.status_code == 200
    temporary = response.json()["temporary_password"]
    assert len(temporary) >= 12
    assert login(client, "teacher", PASSWORD) == 401  # old password no longer works
    assert login(client, "teacher", temporary) == 200
    session.refresh(world.teacher)
    assert temporary not in world.teacher.password_hash
    assert verify_password(temporary, world.teacher.password_hash)


def test_each_reset_gives_a_different_password(client: TestClient, world: World) -> None:
    url, headers = f"{URL}/{world.teacher.id}/reset-password", auth_headers(world.admin)
    first = client.post(url, headers=headers).json()["temporary_password"]
    second = client.post(url, headers=headers).json()["temporary_password"]
    assert first != second


def test_reset_password_of_a_missing_user_is_404(client: TestClient, world: World) -> None:
    assert (
        client.post(f"{URL}/999999/reset-password", headers=auth_headers(world.admin)).status_code
        == 404
    )


# ===================================================== delete (approved addition)


def test_deleting_an_account_keeps_the_teacher_and_unblocks_deleting_them(
    client: TestClient, session: Session, world: World
) -> None:
    teacher_url = f"/api/v1/teachers/{world.teacher_a.id}"
    blocked = client.delete(teacher_url, headers=auth_headers(world.admin))
    assert blocked.status_code == 409
    assert "DELETE /users/{id}" in blocked.json()["detail"]

    response = client.delete(f"{URL}/{world.teacher.id}", headers=auth_headers(world.admin))

    assert response.status_code == 204
    assert session.get(Teacher, world.teacher_a.id) is not None
    assert login(client, "teacher") == 401
    assert client.delete(teacher_url, headers=auth_headers(world.admin)).status_code == 204


def test_deleting_a_student_account_unblocks_deleting_the_student(
    client: TestClient, world: World
) -> None:
    student_url = f"/api/v1/students/{world.s1.id}"
    assert client.delete(student_url, headers=auth_headers(world.admin)).status_code == 409

    client.delete(f"{URL}/{world.student.id}", headers=auth_headers(world.admin))

    assert client.delete(student_url, headers=auth_headers(world.admin)).status_code == 204


def test_admin_cannot_delete_their_own_account(client: TestClient, world: World) -> None:
    response = client.delete(f"{URL}/{world.admin.id}", headers=auth_headers(world.admin))
    assert (response.status_code, response.json()) == (
        403,
        {"detail": "You can't delete your own account"},
    )


def test_delete_of_a_missing_user_is_404(client: TestClient, world: World) -> None:
    assert client.delete(f"{URL}/999999", headers=auth_headers(world.admin)).status_code == 404
