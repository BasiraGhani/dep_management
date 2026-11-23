"""Tests for /auth/login, /auth/me, /auth/change-password and get_current_user (T2.2)."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.security import create_access_token, decode_access_token, verify_password
from app.models import User, UserRole
from tests.conftest import Factory

LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"
CHANGE_PASSWORD = "/api/v1/auth/change-password"
PASSWORD = "s3cret-password"
NEW_PASSWORD = "an0ther-password"


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def token_for(client: TestClient, user: User, password: str = PASSWORD) -> str:
    response = client.post(LOGIN, data={"username": user.username, "password": password})
    assert response.status_code == 200, response.text
    token: str = response.json()["access_token"]
    return token


@pytest.fixture
def admin(factory: Factory) -> User:
    return factory.user(UserRole.ADMIN, username="admin", password=PASSWORD)


# ---------- POST /auth/login (FR-1.1) ----------


def test_login_returns_a_bearer_token(client: TestClient, admin: User) -> None:
    response = client.post(LOGIN, data={"username": "admin", "password": PASSWORD})

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"access_token", "token_type"}
    assert body["token_type"] == "bearer"
    data = decode_access_token(body["access_token"])
    assert (data.user_id, data.role) == (admin.id, UserRole.ADMIN)


def test_login_token_lasts_the_configured_60_minutes(client: TestClient, admin: User) -> None:
    before = datetime.now(UTC)
    response = client.post(LOGIN, data={"username": "admin", "password": PASSWORD})
    expires_at = decode_access_token(response.json()["access_token"]).expires_at

    assert get_settings().access_token_expire_minutes == 60
    assert abs((expires_at - before - timedelta(minutes=60)).total_seconds()) < 5


def test_login_username_is_case_insensitive(client: TestClient, admin: User) -> None:
    response = client.post(LOGIN, data={"username": " ADMIN ", "password": PASSWORD})
    assert response.status_code == 200


def test_login_with_wrong_password_is_rejected(client: TestClient, admin: User) -> None:
    response = client.post(LOGIN, data={"username": "admin", "password": "wrong-password"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Incorrect username or password"}
    assert response.headers["www-authenticate"] == "Bearer"


def test_login_with_unknown_username_gives_the_same_error(client: TestClient) -> None:
    response = client.post(LOGIN, data={"username": "nobody", "password": PASSWORD})

    assert response.status_code == 401
    assert response.json() == {"detail": "Incorrect username or password"}


def test_password_is_case_sensitive(client: TestClient, admin: User) -> None:
    response = client.post(LOGIN, data={"username": "admin", "password": PASSWORD.upper()})
    assert response.status_code == 401


@pytest.mark.parametrize(
    "form",
    [{}, {"username": "admin"}, {"password": PASSWORD}],
    ids=["empty", "no-password", "no-username"],
)
def test_login_with_missing_fields_is_a_validation_error(
    client: TestClient, admin: User, form: dict[str, str]
) -> None:
    assert client.post(LOGIN, data=form).status_code == 422


def test_login_requires_form_data_not_json(client: TestClient, admin: User) -> None:
    response = client.post(LOGIN, json={"username": "admin", "password": PASSWORD})
    assert response.status_code == 422


# ---------- Deactivated users (FR-8.2) ----------


def test_deactivated_user_cannot_log_in(client: TestClient, factory: Factory) -> None:
    factory.user(username="gone", password=PASSWORD, is_active=False)

    response = client.post(LOGIN, data={"username": "gone", "password": PASSWORD})

    assert response.status_code == 403
    assert response.json() == {"detail": "Account is deactivated"}


def test_deactivated_user_with_wrong_password_gets_the_generic_error(
    client: TestClient, factory: Factory
) -> None:
    """Deactivation is only revealed to someone who knows the password."""
    factory.user(username="gone", password=PASSWORD, is_active=False)

    response = client.post(LOGIN, data={"username": "gone", "password": "wrong-password"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Incorrect username or password"}


def test_token_stops_working_once_the_user_is_deactivated(
    client: TestClient, session: Session, admin: User
) -> None:
    token = token_for(client, admin)
    admin.is_active = False
    session.commit()

    response = client.get(ME, headers=bearer(token))

    assert response.status_code == 401
    assert response.json() == {"detail": "Account is deactivated"}


# ---------- GET /auth/me (FR-1.2) ----------


def test_me_for_admin_has_no_linked_record(client: TestClient, admin: User) -> None:
    response = client.get(ME, headers=bearer(token_for(client, admin)))

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == admin.id
    assert body["username"] == "admin"
    assert body["role"] == "admin"
    assert body["is_active"] is True
    assert body["teacher"] is None
    assert body["student"] is None


@pytest.mark.parametrize("role", [UserRole.TEACHER, UserRole.HOD])
def test_me_for_teacher_and_hod_includes_the_teacher_record(
    client: TestClient, factory: Factory, role: UserRole
) -> None:
    teacher = factory.teacher(first_name="Ada", email="ada@uni.edu")
    user = factory.user(role, teacher=teacher, password=PASSWORD)

    body = client.get(ME, headers=bearer(token_for(client, user))).json()

    assert body["role"] == role.value
    assert body["teacher_id"] == teacher.id
    assert body["teacher"]["id"] == teacher.id
    assert body["teacher"]["first_name"] == "Ada"
    assert body["teacher"]["email"] == "ada@uni.edu"
    assert body["teacher"]["department_id"] == teacher.department_id
    assert body["student"] is None


def test_me_for_student_includes_the_student_record(client: TestClient, factory: Factory) -> None:
    student = factory.student(student_no="S0042")
    user = factory.user(UserRole.STUDENT, student=student, password=PASSWORD)

    body = client.get(ME, headers=bearer(token_for(client, user))).json()

    assert body["role"] == "student"
    assert body["student"]["id"] == student.id
    assert body["student"]["student_no"] == "S0042"
    assert body["student"]["status"] == "active"
    assert body["teacher"] is None


# ---------- get_current_user: rejected tokens ----------


def test_me_without_a_token_is_rejected(client: TestClient) -> None:
    response = client.get(ME)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "header",
    ["Bearer not-a-jwt", "Bearer ", "Basic YWRtaW46cGFzcw==", "not-even-a-scheme"],
)
def test_me_with_a_malformed_authorization_header_is_rejected(
    client: TestClient, header: str
) -> None:
    assert client.get(ME, headers={"Authorization": header}).status_code == 401


def test_me_with_an_expired_token_is_rejected(client: TestClient, admin: User) -> None:
    token = create_access_token(admin.id, admin.role, expires_delta=timedelta(seconds=-1))

    response = client.get(ME, headers=bearer(token))

    assert response.status_code == 401
    assert response.json() == {"detail": "Token has expired"}


def test_me_with_a_tampered_token_is_rejected(client: TestClient, admin: User) -> None:
    token = token_for(client, admin)
    tampered = token[:-2] + ("AA" if not token.endswith("AA") else "BB")

    response = client.get(ME, headers=bearer(tampered))

    assert response.status_code == 401
    assert response.json() == {"detail": "Could not validate credentials"}


def test_token_for_a_user_that_no_longer_exists_is_rejected(client: TestClient) -> None:
    token = create_access_token(999_999, UserRole.ADMIN)
    assert client.get(ME, headers=bearer(token)).status_code == 401


def test_token_issued_before_a_role_change_is_rejected(
    client: TestClient, session: Session, factory: Factory
) -> None:
    """A demoted user can't keep using a token that still says the old role."""
    user = factory.user(UserRole.HOD, password=PASSWORD)
    token = token_for(client, user)
    user.role = UserRole.TEACHER
    session.commit()

    response = client.get(ME, headers=bearer(token))

    assert response.status_code == 401
    assert response.json() == {"detail": "Token is out of date; please log in again"}


# ---------- POST /auth/change-password (FR-1.6) ----------


def test_change_password_replaces_the_password(
    client: TestClient, session: Session, admin: User
) -> None:
    old_hash = admin.password_hash
    response = client.post(
        CHANGE_PASSWORD,
        headers=bearer(token_for(client, admin)),
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
    )

    assert response.status_code == 204
    assert response.content == b""
    session.refresh(admin)
    assert admin.password_hash != old_hash
    assert admin.password_hash.startswith("$argon2id$")
    assert verify_password(NEW_PASSWORD, admin.password_hash)


def test_after_changing_password_only_the_new_one_logs_in(client: TestClient, admin: User) -> None:
    client.post(
        CHANGE_PASSWORD,
        headers=bearer(token_for(client, admin)),
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
    )

    old = client.post(LOGIN, data={"username": "admin", "password": PASSWORD})
    new = client.post(LOGIN, data={"username": "admin", "password": NEW_PASSWORD})
    assert (old.status_code, new.status_code) == (401, 200)


def test_change_password_with_wrong_current_password_is_rejected(
    client: TestClient, admin: User
) -> None:
    response = client.post(
        CHANGE_PASSWORD,
        headers=bearer(token_for(client, admin)),
        json={"current_password": "wrong-password", "new_password": NEW_PASSWORD},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Current password is incorrect"}
    assert client.post(LOGIN, data={"username": "admin", "password": PASSWORD}).status_code == 200


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({"current_password": PASSWORD, "new_password": "short"}, "new_password"),
        ({"current_password": PASSWORD, "new_password": "x" * 129}, "new_password"),
        ({"current_password": "", "new_password": NEW_PASSWORD}, "current_password"),
        ({"new_password": NEW_PASSWORD}, "current_password"),
        ({"current_password": PASSWORD}, "new_password"),
    ],
    ids=["too-short", "too-long", "empty-current", "missing-current", "missing-new"],
)
def test_change_password_validates_input(
    client: TestClient, admin: User, body: dict[str, str], field: str
) -> None:
    response = client.post(CHANGE_PASSWORD, headers=bearer(token_for(client, admin)), json=body)

    assert response.status_code == 422
    assert field in {error["loc"][-1] for error in response.json()["detail"]}


def test_new_password_must_differ_from_the_current_one(client: TestClient, admin: User) -> None:
    response = client.post(
        CHANGE_PASSWORD,
        headers=bearer(token_for(client, admin)),
        json={"current_password": PASSWORD, "new_password": PASSWORD},
    )

    assert response.status_code == 422
    assert "must be different" in response.text


def test_change_password_requires_authentication(client: TestClient) -> None:
    response = client.post(
        CHANGE_PASSWORD, json={"current_password": PASSWORD, "new_password": NEW_PASSWORD}
    )
    assert response.status_code == 401


# ---------- Password hashes never leave the API (FR-1.3) ----------


def test_no_auth_response_contains_the_password_or_its_hash(
    client: TestClient, factory: Factory
) -> None:
    user = factory.user(UserRole.STUDENT, username="leaky", password=PASSWORD)
    token = token_for(client, user)
    responses = [
        client.post(LOGIN, data={"username": "leaky", "password": PASSWORD}),
        client.post(LOGIN, data={"username": "leaky", "password": "wrong-password"}),
        client.get(ME, headers=bearer(token)),
        client.post(
            CHANGE_PASSWORD,
            headers=bearer(token),
            json={"current_password": "wrong-password", "new_password": NEW_PASSWORD},
        ),
    ]

    for response in responses:
        assert "password_hash" not in response.text
        assert user.password_hash not in response.text
        assert "$argon2" not in response.text
        assert PASSWORD not in response.text


def test_no_response_schema_exposes_a_password_hash(client: TestClient) -> None:
    schemas = client.get("/openapi.json").json()["components"]["schemas"]

    for name, schema in schemas.items():
        assert "password_hash" not in schema.get("properties", {}), name


# ---------- /docs "Authorize" support ----------


def test_openapi_declares_the_oauth2_password_flow(client: TestClient) -> None:
    security_schemes = client.get("/openapi.json").json()["components"]["securitySchemes"]

    flow = security_schemes["OAuth2PasswordBearer"]["flows"]["password"]
    assert flow["tokenUrl"] == "/api/v1/auth/login"
