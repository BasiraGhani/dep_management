from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app

ALLOWED = "http://allowed.test"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("CORS_ORIGINS", ALLOWED)
    get_settings.cache_clear()
    yield TestClient(create_app())
    get_settings.cache_clear()


def test_preflight_from_allowed_origin_is_accepted(client: TestClient) -> None:
    response = client.options(
        "/api/v1/health",
        headers={"Origin": ALLOWED, "Access-Control-Request-Method": "GET"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED


def test_request_from_other_origin_gets_no_cors_header(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"Origin": "http://evil.test"})

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
