from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import BACKEND_DIR, Settings

SECRET = "s" * 32


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove every setting from the process environment."""
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)


@pytest.mark.usefixtures("clean_env")
def test_settings_load_from_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_URL=sqlite:///./other.db\n"
        f"SECRET_KEY={SECRET}\n"
        "ACCESS_TOKEN_EXPIRE_MINUTES=15\n"
        "CORS_ORIGINS=http://a.test, http://b.test\n"
        "FIRST_ADMIN_USERNAME=root\n"
        "FIRST_ADMIN_PASSWORD=root-password\n"
    )

    settings = Settings(_env_file=env_file)

    assert settings.database_url == "sqlite:///./other.db"
    assert settings.secret_key == SECRET
    assert settings.access_token_expire_minutes == 15
    assert settings.cors_origins == ["http://a.test", "http://b.test"]
    assert settings.first_admin_username == "root"
    assert settings.first_admin_password == "root-password"


@pytest.mark.usefixtures("clean_env")
def test_environment_variable_overrides_env_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(f"SECRET_KEY={SECRET}\nACCESS_TOKEN_EXPIRE_MINUTES=15\n")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")

    settings = Settings(_env_file=env_file)

    assert settings.access_token_expire_minutes == 30


@pytest.mark.usefixtures("clean_env")
def test_defaults_apply_when_only_secret_key_is_set() -> None:
    settings = Settings(_env_file=None, secret_key=SECRET)

    assert settings.database_url == "sqlite:///./dept.db"
    assert settings.access_token_expire_minutes == 60
    assert settings.cors_origins == ["http://localhost:5173"]
    assert settings.first_admin_username is None
    assert settings.first_admin_password is None


@pytest.mark.usefixtures("clean_env")
def test_missing_secret_key_is_rejected() -> None:
    with pytest.raises(ValidationError, match="secret_key"):
        Settings(_env_file=None)


@pytest.mark.usefixtures("clean_env")
@pytest.mark.parametrize("secret_key", ["too-short", "s" * 31])
def test_secret_key_shorter_than_32_characters_is_rejected(secret_key: str) -> None:
    with pytest.raises(ValidationError, match="secret_key"):
        Settings(_env_file=None, secret_key=secret_key)


@pytest.mark.usefixtures("clean_env")
def test_token_lifetime_must_be_positive() -> None:
    with pytest.raises(ValidationError, match="access_token_expire_minutes"):
        Settings(_env_file=None, secret_key=SECRET, access_token_expire_minutes=0)


def test_env_example_documents_every_setting() -> None:
    lines = (BACKEND_DIR / ".env.example").read_text().splitlines()
    documented = {
        line.split("=", 1)[0].strip()
        for line in lines
        if line.strip() and not line.lstrip().startswith("#")
    }

    assert documented == {name.upper() for name in Settings.model_fields}


@pytest.mark.usefixtures("clean_env")
def test_env_example_values_are_valid_once_a_real_secret_is_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SECRET_KEY", SECRET)
    Settings(_env_file=BACKEND_DIR / ".env.example")


@pytest.mark.usefixtures("clean_env")
def test_env_example_secret_key_is_refused_as_is() -> None:
    """Copying .env.example unchanged must not give a working (guessable) secret."""
    with pytest.raises(ValidationError, match="SECRET_KEY is still the example value"):
        Settings(_env_file=BACKEND_DIR / ".env.example")


@pytest.mark.usefixtures("clean_env")
@pytest.mark.parametrize("value", ["*", "http://localhost:5173,*"])
def test_wildcard_cors_origin_is_refused(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("CORS_ORIGINS", value)
    with pytest.raises(ValidationError, match="not '\\*'"):
        Settings(_env_file=None, secret_key=SECRET)
