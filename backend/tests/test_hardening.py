"""Security pass (T8.4, NFR-1): login throttling, authentication on every
endpoint, CORS limited to the frontend origin, and accurate API docs."""

import re

import httpx2
import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.config import get_settings
from app.core import security
from app.core.security import (
    FAILURE_WINDOW_SECONDS,
    MAX_FAILURES_PER_ACCOUNT,
    MAX_FAILURES_PER_CLIENT,
    LoginThrottle,
)
from app.main import API_PREFIX
from app.models import UserRole
from app.routers import (
    auth,
    courses,
    dashboard,
    departments,
    enrollments,
    export,
    students,
    teachers,
    users,
)
from tests.conftest import Factory

PASSWORD = "correct-horse-battery"
LOGIN = "/api/v1/auth/login"


def login(client: TestClient, username: str, password: str) -> httpx2.Response:
    response: httpx2.Response = client.post(
        LOGIN, data={"username": username, "password": password}
    )
    return response


# ===================================================== failed-login throttle (API)


def test_repeated_wrong_passwords_are_throttled(client: TestClient, factory: Factory) -> None:
    factory.user(UserRole.ADMIN, username="ada", password=PASSWORD)
    for _ in range(MAX_FAILURES_PER_ACCOUNT):
        assert login(client, "ada", "wrong-password").status_code == 401

    blocked = login(client, "ada", PASSWORD)  # even the right password now waits

    assert blocked.status_code == 429
    assert blocked.json() == {
        "detail": "Too many failed login attempts. Try again in 15 minute(s)."
    }
    assert 0 < int(blocked.headers["Retry-After"]) <= FAILURE_WINDOW_SECONDS


def test_fewer_failures_than_the_limit_still_allow_a_login(
    client: TestClient, factory: Factory
) -> None:
    factory.user(UserRole.ADMIN, username="ada", password=PASSWORD)
    for _ in range(MAX_FAILURES_PER_ACCOUNT - 1):
        login(client, "ada", "wrong-password")

    assert login(client, "ada", PASSWORD).status_code == 200


def test_a_successful_login_clears_the_count(client: TestClient, factory: Factory) -> None:
    factory.user(UserRole.ADMIN, username="ada", password=PASSWORD)
    for _ in range(MAX_FAILURES_PER_ACCOUNT - 1):
        login(client, "ada", "wrong-password")
    assert login(client, "ada", PASSWORD).status_code == 200

    for _ in range(MAX_FAILURES_PER_ACCOUNT - 1):
        assert login(client, "ada", "wrong-password").status_code == 401
    assert login(client, "ada", PASSWORD).status_code == 200


def test_unknown_usernames_count_too_and_case_does_not_matter(
    client: TestClient, factory: Factory
) -> None:
    for _ in range(MAX_FAILURES_PER_ACCOUNT):
        login(client, "Nobody", "x")
    assert login(client, "NOBODY", "x").status_code == 429


def test_another_username_from_the_same_client_is_not_blocked(
    client: TestClient, factory: Factory
) -> None:
    factory.user(UserRole.ADMIN, username="bea", password=PASSWORD)
    for _ in range(MAX_FAILURES_PER_ACCOUNT):
        login(client, "ada", "wrong-password")

    assert login(client, "bea", PASSWORD).status_code == 200


def test_many_usernames_from_one_client_are_throttled(client: TestClient, factory: Factory) -> None:
    factory.user(UserRole.ADMIN, username="bea", password=PASSWORD)
    for i in range(MAX_FAILURES_PER_CLIENT):
        login(client, f"guess{i}", "x")  # never more than one try per username

    assert login(client, "bea", PASSWORD).status_code == 429


def test_the_429_is_documented(client: TestClient) -> None:
    responses = client.get("/openapi.json").json()["paths"][LOGIN]["post"]["responses"]
    assert "429" in responses


# ===================================================== throttle window (unit, fake clock)


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_the_block_lifts_when_the_window_has_passed() -> None:
    clock = FakeClock()
    throttle = LoginThrottle(clock)
    for _ in range(MAX_FAILURES_PER_ACCOUNT):
        throttle.record_failure("1.2.3.4", "ada")
    assert throttle.retry_after("1.2.3.4", "ada") == FAILURE_WINDOW_SECONDS

    clock.now += FAILURE_WINDOW_SECONDS - 60
    assert throttle.retry_after("1.2.3.4", "ada") == 60

    clock.now += 60
    assert throttle.retry_after("1.2.3.4", "ada") is None


def test_old_failures_drop_out_of_the_window() -> None:
    clock = FakeClock()
    throttle = LoginThrottle(clock)
    for _ in range(MAX_FAILURES_PER_ACCOUNT - 1):
        throttle.record_failure("1.2.3.4", "ada")
    clock.now += FAILURE_WINDOW_SECONDS  # those four are now too old to count
    throttle.record_failure("1.2.3.4", "ada")

    assert throttle.retry_after("1.2.3.4", "ada") is None


def test_clients_are_counted_separately() -> None:
    throttle = LoginThrottle(FakeClock())
    for _ in range(MAX_FAILURES_PER_ACCOUNT):
        throttle.record_failure("1.2.3.4", "ada")

    assert throttle.retry_after("5.6.7.8", "ada") is None  # an attacker can't lock Ada out


def test_the_app_uses_one_shared_throttle() -> None:
    assert isinstance(security.login_throttle, LoginThrottle)


# ===================================================== every endpoint needs a token

PUBLIC = {("POST", LOGIN), ("GET", "/api/v1/health")}
ROUTERS = (auth, courses, dashboard, departments, enrollments, export, students, teachers, users)


def api_endpoints() -> list[tuple[str, str]]:
    """Every (method, path) the routers define, plus the health check.

    Read from the router modules rather than FastAPI's internals; the docs test
    below fails if the app serves an endpoint this list misses.
    """
    endpoints = {("GET", f"{API_PREFIX}/health")}
    for module in ROUTERS:
        for route in module.router.routes:
            assert isinstance(route, APIRoute)
            endpoints |= {(method, API_PREFIX + route.path) for method in route.methods or ()}
    return sorted(endpoints)


def concrete(path: str) -> str:
    """A real URL for a path template: every {parameter} becomes 1."""
    return re.sub(r"\{resource\}", "students", re.sub(r"\{\w+_id\}", "1", path))


def test_only_login_and_health_are_public() -> None:
    assert set(api_endpoints()) >= PUBLIC


@pytest.mark.parametrize(("method", "path"), [e for e in api_endpoints() if e not in PUBLIC])
def test_every_other_endpoint_requires_a_token(client: TestClient, method: str, path: str) -> None:
    response = client.request(method, concrete(path))

    assert response.status_code == 401, f"{method} {path} answered {response.status_code}"


# ===================================================== CORS (NFR-1)


def frontend_origin() -> str:
    """The configured frontend origin (from CORS_ORIGINS, so a developer's own
    backend/.env doesn't break these tests)."""
    return get_settings().cors_origins[0]


@pytest.mark.parametrize(("which", "allowed"), [("frontend", True), ("other", False)])
def test_cors_allows_only_the_frontend_origin(
    client: TestClient, which: str, allowed: bool
) -> None:
    origin = frontend_origin() if which == "frontend" else "https://evil.example"
    response = client.options(
        "/api/v1/departments",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    allow_origin = response.headers.get("access-control-allow-origin")
    assert allow_origin == (origin if allowed else None)  # never "*", never an outsider


def test_cors_does_not_allow_credentials_or_unexpected_headers(client: TestClient) -> None:
    response = client.options(
        "/api/v1/departments",
        headers={
            "Origin": frontend_origin(),  # an allowed origin: only the header is wrong
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "x-custom-header",
        },
    )
    assert response.status_code == 400
    assert "access-control-allow-credentials" not in response.headers


# ===================================================== API docs (NFR-7)


def test_the_api_docs_list_every_endpoint(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    documented = {(m.upper(), p) for p, ops in paths.items() for m in ops}

    assert documented == set(api_endpoints())
    assert client.get("/docs").status_code == 200
