"""Tests for core.deps.require_roles (T2.3), through real HTTP requests."""

from collections.abc import Iterator
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_roles
from app.core.security import create_access_token
from app.models import User, UserRole
from tests.conftest import Factory

ALL_ROLES = list(UserRole)


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    """A small app whose routes are guarded by require_roles."""
    app = FastAPI()

    @app.get("/admin-only")
    def admin_only(user: Annotated[User, Depends(require_roles(UserRole.ADMIN))]) -> int:
        return user.id

    @app.get("/staff", dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.HOD))])
    def staff() -> str:
        return "ok"

    @app.get("/teaching")
    def teaching(
        user: Annotated[User, Depends(require_roles(UserRole.HOD, UserRole.TEACHER))],
    ) -> str:
        return user.role.value

    @app.get("/anyone")
    def anyone(user: Annotated[User, Depends(require_roles(*UserRole))]) -> str:
        return user.username

    def _get_test_db() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_db] = _get_test_db
    with TestClient(app) as test_client:
        yield test_client


def auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role)}"}


@pytest.mark.parametrize(
    ("path", "allowed"),
    [
        ("/admin-only", {UserRole.ADMIN}),
        ("/staff", {UserRole.ADMIN, UserRole.HOD}),
        ("/teaching", {UserRole.HOD, UserRole.TEACHER}),
        ("/anyone", set(UserRole)),
    ],
)
@pytest.mark.parametrize("role", ALL_ROLES)
def test_each_role_is_allowed_or_denied(
    client: TestClient, factory: Factory, path: str, allowed: set[UserRole], role: UserRole
) -> None:
    user = factory.user(role)

    response = client.get(path, headers=auth(user))

    if role in allowed:
        assert response.status_code == 200, response.text
    else:
        assert response.status_code == 403
        assert response.json() == {"detail": "Not enough permissions"}


def test_dependency_returns_the_current_user(client: TestClient, factory: Factory) -> None:
    admin = factory.user(UserRole.ADMIN)
    assert client.get("/admin-only", headers=auth(admin)).json() == admin.id


@pytest.mark.parametrize("path", ["/admin-only", "/staff", "/teaching", "/anyone"])
def test_missing_token_is_401_not_403(client: TestClient, path: str) -> None:
    assert client.get(path).status_code == 401


def test_deactivated_user_is_401_even_with_an_allowed_role(
    client: TestClient, factory: Factory
) -> None:
    admin = factory.user(UserRole.ADMIN, is_active=False)
    assert client.get("/admin-only", headers=auth(admin)).status_code == 401


def test_require_roles_needs_at_least_one_role() -> None:
    with pytest.raises(ValueError, match="at least one role"):
        require_roles()
