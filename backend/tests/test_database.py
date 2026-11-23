from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine, ForeignKey, String, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.database import Base, IdMixin, TimestampMixin, create_db_engine, get_db


class _TestBase(DeclarativeBase):
    """Separate metadata so these throwaway tables never reach the app's migrations."""


class Parent(IdMixin, TimestampMixin, _TestBase):
    __tablename__ = "parents"
    name: Mapped[str] = mapped_column(String(20))


class Child(IdMixin, _TestBase):
    __tablename__ = "children"
    parent_id: Mapped[int] = mapped_column(ForeignKey("parents.id"))


@pytest.fixture
def engine(tmp_path: Path) -> Iterator[Engine]:
    db_engine = create_db_engine(f"sqlite:///{tmp_path / 'test.db'}")
    _TestBase.metadata.create_all(db_engine)
    yield db_engine
    db_engine.dispose()


def test_sqlite_foreign_keys_pragma_is_on(engine: Engine) -> None:
    with engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1


def test_foreign_key_violation_is_rejected(engine: Engine) -> None:
    with Session(engine) as session:
        session.add(Child(parent_id=999))
        with pytest.raises(IntegrityError, match="FOREIGN KEY constraint failed"):
            session.commit()


def test_valid_foreign_key_is_accepted(engine: Engine) -> None:
    with Session(engine) as session:
        parent = Parent(name="p")
        session.add(parent)
        session.flush()
        session.add(Child(parent_id=parent.id))
        session.commit()


def test_mixins_add_id_and_timestamps(engine: Engine) -> None:
    with Session(engine) as session:
        parent = Parent(name="p")
        session.add(parent)
        session.commit()

        assert isinstance(parent.id, int)
        assert isinstance(parent.created_at, datetime)
        assert isinstance(parent.updated_at, datetime)


def test_updated_at_changes_on_update(engine: Engine) -> None:
    past = datetime(2000, 1, 1, tzinfo=UTC)
    with Session(engine) as session:
        parent = Parent(name="p", created_at=past, updated_at=past)
        session.add(parent)
        session.commit()

        parent.name = "renamed"
        session.commit()
        session.refresh(parent)

        assert parent.updated_at.replace(tzinfo=UTC) > past
        assert parent.created_at.replace(tzinfo=UTC) == past


def test_app_metadata_uses_naming_convention() -> None:
    assert Base.metadata.naming_convention["fk"] == (
        "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"
    )


def test_get_db_yields_a_session_and_closes_it(monkeypatch: pytest.MonkeyPatch) -> None:
    closed: list[bool] = []
    original_close = Session.close

    def tracking_close(self: Session) -> None:
        closed.append(True)
        original_close(self)

    monkeypatch.setattr(Session, "close", tracking_close)

    dependency = get_db()
    session = next(dependency)
    assert isinstance(session, Session)

    with pytest.raises(StopIteration):
        next(dependency)
    assert closed == [True]
