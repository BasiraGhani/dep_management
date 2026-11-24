# University Department Management System

A web application for running a university department: departments, teachers,
students, courses, enrollments and grades, with role-based access for
administrators, heads of department (HODs), teachers and students.

**Stack:** FastAPI · SQLAlchemy 2 · Alembic · PostgreSQL (SQLite in development) ·
React 19 + TypeScript (Vite) · TanStack Query · Tailwind CSS · Docker Compose + Nginx

## Quick start (Docker, 5 steps)

You need Docker with Compose v2.

1. `git clone https://github.com/BasiraGhani/dep_management.git && cd dep_management`
2. `cp .env.example .env`
3. In `.env`, set `POSTGRES_PASSWORD`, `SECRET_KEY` (32+ characters:
   `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`) and
   `FIRST_ADMIN_PASSWORD`. Set `SEED_DEMO=true` for the demo data below.
4. `docker compose up --build`
5. Open **http://localhost** and sign in as `admin` with your `FIRST_ADMIN_PASSWORD`.

Migrations run each time the backend starts. The database lives in the `pgdata`
volume: `docker compose down` keeps it, `docker compose down -v` deletes it.

## Demo logins

With `SEED_DEMO=true` (or `python -m app.cli seed-demo` without Docker) you get 3
departments, 10 teachers, 60 students, 12 courses with enrollments and grades, and
one login per role. The password for all of them is `demo-password`, so use them
for trying the app only.

| Username | Role | Try |
|---|---|---|
| `demo.admin` | Administrator | Dashboard chart; users page; CSV export |
| `demo.hod` | Head of Computer Science | Their department's dashboard; enroll students |
| `demo.teacher` | Teacher | "Enter grades" from the dashboard |
| `demo.student` | Student | Grades and GPA; edit contact details |

## Development without Docker (8 steps)

Needs Python 3.12+ and Node 20+. Two terminals:

```bash
# Backend: http://localhost:8000/docs
cd backend
python3.12 -m venv .venv && source .venv/bin/activate   # 1
pip install -r requirements-dev.txt                      # 2
cp .env.example .env            # 3: set SECRET_KEY and FIRST_ADMIN_PASSWORD
alembic upgrade head                                     # 4: SQLite in backend/dept.db
python -m app.cli seed-admin && python -m app.cli seed-demo   # 5
uvicorn app.main:app --reload                            # 6

# Frontend: http://localhost:5173
cd frontend
npm ci                                                   # 7
npm run dev                                              # 8
```

To use PostgreSQL instead of SQLite, set `DATABASE_URL=postgresql+psycopg://…` in
`backend/.env`; nothing else changes.

## Running the tests

| What | Where | Command |
|---|---|---|
| Backend lint, types, tests (SQLite) | `backend/` | `ruff check . && ruff format --check . && mypy app && pytest -q` |
| Backend tests on PostgreSQL | `backend/` | `TEST_DATABASE_URL=postgresql+psycopg://user:pw@host/db pytest -q` (wipes that DB) |
| Frontend lint, types, tests, build | `frontend/` | `npm run lint && npm run typecheck && npm run test -- --run && npm run build` |
| End-to-end smoke test (Playwright) | `frontend/` | `npx playwright install chromium`, then `npm run e2e` (Docker stack with demo data) |

CI (`.github/workflows/ci.yml`) runs all of them on every pull request, including
the smoke test against `docker compose up --build`.

## Architecture

```
Browser ──▶ Nginx (frontend container, port 80)
              ├─ /          built React app (client-side routing)
              └─ /api/...   ──▶ FastAPI backend ──▶ PostgreSQL
```

- **Backend** (`backend/app`): `routers/` handle HTTP only, `services/` hold the
  business rules and permission checks, `models/` are SQLAlchemy tables and
  `schemas/` the Pydantic request/response models. Alembic migrations in
  `backend/alembic`. JWT bearer tokens, argon2 password hashing.
- **Frontend** (`frontend/src`): `api/` (one file per resource, axios), `hooks/`
  (TanStack Query), `pages/`, `components/`, `types/` (mirrors the API schemas).
  The UI hides what a role can't do; the backend enforces it.
- **API docs:** http://localhost:8000/docs (or `/docs` on the backend container),
  generated from the code.

Details: [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) (roles, permissions,
rules), [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) (data model, API, pages),
[`backend/README.md`](backend/README.md), [`frontend/README.md`](frontend/README.md).

## Security

- Passwords hashed with argon2; tokens are JWTs signed with `SECRET_KEY`, which is
  required (32+ characters) and can't be left at the example value.
- Every endpoint except login and the health check requires a token, and every
  permission rule is checked on the server.
- Repeated failed logins from one client are slowed down (HTTP 429 with
  `Retry-After`: 5 failures per username or 20 overall in 15 minutes).
- CORS allows only the configured frontend origin(s), never `*`. In Docker the API
  is served from the same origin as the app.
- Nginx sends a strict Content-Security-Policy and other security headers.
- No secrets in Git: `.env` files are ignored; only `.env.example` files are committed.

## How this project was built

Task by task from [`TASKS.md`](TASKS.md), each on its own branch and pull request,
following [`CLAUDE.md`](CLAUDE.md) and reviewed against
[`docs/REVIEW_CHECKLIST.md`](docs/REVIEW_CHECKLIST.md). Phases and their gates are
in [`docs/PHASES.md`](docs/PHASES.md).
