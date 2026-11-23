"""Plain helper functions shared by tests (fixtures live in conftest.py)."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Engine, inspect, text
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models import User


def insert_raw(session: Session, table: str, **values: Any) -> None:
    """Insert a row with plain SQL, bypassing model validation, to test DB constraints.

    `created_at` / `updated_at` are filled in unless given.
    """
    now = datetime.now(UTC).isoformat()
    values = {"created_at": now, "updated_at": now, **values}
    columns = ", ".join(values)
    params = ", ".join(f":{name}" for name in values)
    session.execute(text(f"INSERT INTO {table} ({columns}) VALUES ({params})"), values)


def unique_columns(engine: Engine, table: str) -> set[tuple[str, ...]]:
    """Column tuples of every UNIQUE constraint on `table`."""
    return {tuple(uq["column_names"]) for uq in inspect(engine).get_unique_constraints(table)}


def foreign_keys(engine: Engine, table: str) -> set[tuple[str, str]]:
    """(column, referred table) for every foreign key on `table`."""
    return {
        (fk["constrained_columns"][0], fk["referred_table"])
        for fk in inspect(engine).get_foreign_keys(table)
    }


def nullable_columns(engine: Engine, table: str) -> set[str]:
    """Names of the nullable columns of `table`."""
    return {c["name"] for c in inspect(engine).get_columns(table) if c["nullable"]}


def auth_headers(user: User) -> dict[str, str]:
    """`Authorization` header with a valid token for `user` (no password needed)."""
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role)}"}
