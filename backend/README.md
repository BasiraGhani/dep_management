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

## Seed data

```bash
python -m app.cli seed-admin   # first admin from FIRST_ADMIN_USERNAME / FIRST_ADMIN_PASSWORD
python -m app.cli seed-demo    # 3 departments, 10 teachers, 60 students, 12 courses,
                               # enrollments with grades, and one login per role
```

Both are safe to run again: they never create duplicates or change existing rows.
`seed-demo` prints its logins (`demo.admin`, `demo.hod`, `demo.teacher`,
`demo.student`, password `demo-password`). Use them for development only.

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

Coverage of the services and routers (the Gate 4 target is 80%):

```bash
pytest --cov=app.services --cov=app.routers
```

Tests run in a random order on every run (pytest-random-order), so state leaking
between tests shows up as a failure. The run prints its seed; to repeat that order:

```bash
pytest --random-order-seed=<seed>
```

### PostgreSQL

The app runs on SQLite (default) or PostgreSQL: set `DATABASE_URL` to e.g.
`postgresql+psycopg://user:password@localhost:5432/dept` and run `alembic upgrade head`.

The tests use a temporary SQLite database unless `TEST_DATABASE_URL` points at a
PostgreSQL database, which is **wiped** and migrated at the start of the run:

```bash
TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/dept_test pytest -q
```

CI runs the suite on both (the "Backend tests on PostgreSQL" job uses a `postgres:16`
service container).

Test fixtures (`tests/conftest.py`): `session` (rolled back after each test),
`client` (a `TestClient` using that session) and `factory` (creates valid rows).
