# Backend

FastAPI + SQLAlchemy 2.x + Alembic (Python 3.12+). Planned layout: `../docs/ARCHITECTURE.md` §5.

## Setup

```bash
cd backend
python3.12 -m venv .venv          # must be Python 3.12+
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env              # then set SECRET_KEY
alembic upgrade head              # create / update the database schema
```

## Run

```bash
uvicorn app.main:app --reload     # http://localhost:8000/docs
```

## Migrations

```bash
alembic revision --autogenerate -m "describe change"   # after changing models
alembic upgrade head
alembic downgrade -1
```

## Checks

```bash
ruff check . && ruff format --check .
mypy app
pytest -q
```

Tests run in a random order on every run (pytest-random-order), so state leaking
between tests shows up as a failure. The run prints its seed; to repeat that order:

```bash
pytest --random-order-seed=<seed>
```

Test fixtures (`tests/conftest.py`): `session` (rolled back after each test),
`client` (a `TestClient` using that session) and `factory` (creates valid rows).
