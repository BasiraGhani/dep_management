"""Shared test setup. T1.4 extends this with a client, rollback isolation and factories."""

import os

# Settings require SECRET_KEY. Set a test value before any `app` module is imported,
# so the suite runs without a .env file (e.g. in CI). A real env var still wins.
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")

from collections.abc import Iterator  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import Engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.config import BACKEND_DIR  # noqa: E402
from app.database import create_db_engine  # noqa: E402


def make_alembic_config(database_url: str) -> Config:
    """Alembic config for the real migrations, pointed at `database_url`."""
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


@pytest.fixture
def engine(tmp_path: Path) -> Iterator[Engine]:
    """A fresh SQLite database built with `alembic upgrade head`."""
    database_url = f"sqlite:///{tmp_path / 'test.db'}"
    command.upgrade(make_alembic_config(database_url), "head")
    db_engine = create_db_engine(database_url)
    yield db_engine
    db_engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    """A session on the `engine` database."""
    with Session(engine) as db_session:
        yield db_session
