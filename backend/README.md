# Backend

FastAPI + SQLAlchemy 2.x + Alembic (Python 3.12+). Planned layout: `../docs/ARCHITECTURE.md` §5.

## Setup

```bash
cd backend
python3.12 -m venv .venv          # must be Python 3.12+
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

## Run

```bash
uvicorn app.main:app --reload     # http://localhost:8000/docs
```

## Checks

```bash
ruff check . && ruff format --check .
mypy app
pytest -q
```
