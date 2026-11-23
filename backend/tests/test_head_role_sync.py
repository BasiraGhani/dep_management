"""Tests for BR-6 department head role sync (T4.3).

`world`:
    dept A: `head` (login: hod, is the head), `next_up` (login: teacher),
            `no_login` (teacher record without an account)
    dept B: no head; `b_teacher` (login: teacher)
"""

from dataclasses import dataclass

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Department, Teacher, User, UserRole
from tests.conftest import Factory
from tests.helpers import auth_headers

PASSWORD = "head-sync-pass"


@dataclass
class World:
    dept_a: Department
    dept_b: Department
    head: Teacher
    next_up: Teacher
    no_login: Teacher
    b_teacher: Teacher
    head_user: User
    next_user: User
    b_user: User
    admin: User


@pytest.fixture
def world(session: Session, factory: Factory) -> World:
    dept_a, dept_b = factory.department(code="DEPA"), factory.department(code="DEPB")
    head, next_up, no_login = (
        factory.teacher(dept_a),
        factory.teacher(dept_a),
        factory.teacher(dept_a),
    )
    b_teacher = factory.teacher(dept_b)
    dept_a.head_id = head.id
    world = World(
        dept_a=dept_a,
        dept_b=dept_b,
        head=head,
        next_up=next_up,
        no_login=no_login,
        b_teacher=b_teacher,
        head_user=factory.user(UserRole.HOD, teacher=head, username="head", password=PASSWORD),
        next_user=factory.user(
            UserRole.TEACHER, teacher=next_up, username="next", password=PASSWORD
        ),
        b_user=factory.user(UserRole.TEACHER, teacher=b_teacher),
        admin=factory.user(UserRole.ADMIN),
    )
    session.commit()
    return world


def set_head(
    client: TestClient, world: World, department: Department, head: Teacher | None
) -> httpx.Response:
    response: httpx.Response = client.patch(
        f"/api/v1/departments/{department.id}",
        json={"head_id": head.id if head else None},
        headers=auth_headers(world.admin),
    )
    return response


def roles(session: Session, *users: User) -> list[UserRole]:
    for user in users:
        session.refresh(user)
    return [u.role for u in users]


# ===================================================== the four required cases


def test_assigning_a_head_promotes_their_account_to_hod(
    client: TestClient, session: Session, world: World
) -> None:
    response = set_head(client, world, world.dept_b, world.b_teacher)

    assert response.status_code == 200
    assert response.json()["head_id"] == world.b_teacher.id
    assert roles(session, world.b_user) == [UserRole.HOD]


def test_replacing_the_head_swaps_the_roles(
    client: TestClient, session: Session, world: World
) -> None:
    response = set_head(client, world, world.dept_a, world.next_up)

    assert response.status_code == 200
    assert roles(session, world.head_user, world.next_user) == [UserRole.TEACHER, UserRole.HOD]


def test_removing_the_head_demotes_the_previous_head(
    client: TestClient, session: Session, world: World
) -> None:
    response = set_head(client, world, world.dept_a, None)

    assert response.status_code == 200
    assert response.json()["head_id"] is None
    assert roles(session, world.head_user) == [UserRole.TEACHER]


def test_a_head_without_a_login_account_works(
    client: TestClient, session: Session, world: World
) -> None:
    to_no_login = set_head(client, world, world.dept_a, world.no_login)
    assert to_no_login.status_code == 200
    assert roles(session, world.head_user) == [UserRole.TEACHER]  # previous head demoted

    back_to_someone = set_head(client, world, world.dept_a, world.next_up)
    assert back_to_someone.status_code == 200  # previous head had no account: nothing to demote
    assert roles(session, world.next_user) == [UserRole.HOD]


# ===================================================== edge cases


def test_setting_the_same_head_again_changes_nothing(
    client: TestClient, session: Session, world: World
) -> None:
    assert set_head(client, world, world.dept_a, world.head).status_code == 200
    assert roles(session, world.head_user) == [UserRole.HOD]


def test_updates_without_head_id_leave_roles_alone(
    client: TestClient, session: Session, world: World
) -> None:
    response = client.patch(
        f"/api/v1/departments/{world.dept_a.id}",
        json={"building": "North"},
        headers=auth_headers(world.admin),
    )

    assert response.status_code == 200
    assert roles(session, world.head_user, world.next_user) == [UserRole.HOD, UserRole.TEACHER]


@pytest.mark.parametrize(
    "extra",
    [{}, {"name": "TAKEN"}],
    ids=["head-from-another-department", "valid-head-but-duplicate-name"],
)
def test_refused_update_changes_no_roles(
    client: TestClient, session: Session, factory: Factory, world: World, extra: dict[str, str]
) -> None:
    """The head change and the role changes succeed or fail together."""
    factory.department(name="TAKEN")
    session.commit()
    new_head = world.b_teacher if not extra else world.next_up

    response = client.patch(
        f"/api/v1/departments/{world.dept_a.id}",
        json={"head_id": new_head.id, **extra},
        headers=auth_headers(world.admin),
    )

    assert response.status_code in (409, 422)
    session.refresh(world.dept_a)
    assert world.dept_a.head_id == world.head.id
    assert roles(session, world.head_user, world.next_user, world.b_user) == [
        UserRole.HOD,
        UserRole.TEACHER,
        UserRole.TEACHER,
    ]


def test_deactivated_accounts_are_synced_too(
    client: TestClient, session: Session, world: World
) -> None:
    world.next_user.is_active = False
    session.commit()

    set_head(client, world, world.dept_a, world.next_up)

    assert roles(session, world.next_user) == [UserRole.HOD]


def test_roles_other_than_teacher_and_hod_are_left_alone(
    client: TestClient, session: Session, factory: Factory, world: World
) -> None:
    """An (invalid) admin account linked to a teacher isn't turned into a HOD."""
    odd = factory.user(UserRole.ADMIN, teacher_id=world.no_login.id)
    session.commit()

    set_head(client, world, world.dept_a, world.no_login)

    assert roles(session, odd) == [UserRole.ADMIN]


# ===================================================== the sync has real effect at login


def login(client: TestClient, username: str) -> str:
    response = client.post("/api/v1/auth/login", data={"username": username, "password": PASSWORD})
    assert response.status_code == 200
    token: str = response.json()["access_token"]
    return token


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_new_and_old_heads_get_their_new_rights_after_logging_in_again(
    client: TestClient, world: World
) -> None:
    old_head_token, new_head_token = login(client, "head"), login(client, "next")

    set_head(client, world, world.dept_a, world.next_up)

    # Tokens issued before the change carry the old role and are refused.
    for token in (old_head_token, new_head_token):
        response = client.get("/api/v1/auth/me", headers=bearer(token))
        assert response.status_code == 401
        assert response.json() == {"detail": "Token is out of date; please log in again"}

    # After logging in again each has the right role and rights.
    new_head = bearer(login(client, "next"))
    old_head = bearer(login(client, "head"))
    assert client.get("/api/v1/auth/me", headers=new_head).json()["role"] == "hod"
    assert client.get("/api/v1/auth/me", headers=old_head).json()["role"] == "teacher"

    edit = {"building": "Head office"}
    url = f"/api/v1/departments/{world.dept_a.id}"
    assert client.patch(url, json=edit, headers=new_head).status_code == 200
    assert client.patch(url, json=edit, headers=old_head).status_code == 403
