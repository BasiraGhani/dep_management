# CLAUDE.md — Instructions for the Coding Agent

You are building the **University Department Management System**, one task at a time.
This file defines how you work. Read it fully at the start of every session.

## Source-of-truth documents

Read these before starting any task. If they contradict each other, stop and ask. Don't guess.

1. `TASKS.md`: the task list. Do **only** the task you were assigned.
2. `docs/REQUIREMENTS.md`: what the system must do, including roles, permissions and business rules.
3. `docs/ARCHITECTURE.md`: data model, API contract, pages and folder structure. **Follow it exactly.**
4. `docs/PHASES.md`: the phase you're in and its exit gate.

## Golden rules

1. **One task per session/PR.** Implement only the assigned task ID. Don't start the next task, even if it looks easy.
2. **Don't expand scope.** If you notice something missing, write it under "Suggestions" in your report. Don't build it.
3. **Don't change the architecture silently.** If the data model, API paths, folder layout or dependencies need to change, propose the change in your report and wait for approval. The only exception is a minor helper inside a file you're already editing.
4. **Every task ends green.** Before reporting, all linters, type checks and tests must pass (see "Commands").
5. **Write tests with the code.** Every backend endpoint needs tests for success, validation failure, not found, and permission denied (once auth exists). Frontend tasks need at least one component test per page.
6. **Never commit secrets.** Use `.env` files (git-ignored) and commit `.env.example` with placeholder values.
7. **Don't mark tasks done in `TASKS.md` yourself.** The reviewer does that after approval. You may set the status to `[~]` (in review) on your branch.
8. **If you're blocked, stop and report.** Explain what's blocking you and the options. Don't work around a blocker with hacks.

## Tech stack (fixed — don't substitute)

### Backend (`backend/`)
- Python 3.12+
- FastAPI, Uvicorn
- SQLAlchemy 2.x (typed `Mapped[]` / `mapped_column` style)
- Pydantic v2 + `pydantic-settings` for config
- Alembic for migrations (from the very first table)
- Auth: JWT access tokens with `PyJWT`; password hashing with `pwdlib[argon2]`
- Testing: `pytest`, `httpx` (FastAPI `TestClient`)
- Lint/format: `ruff`; type check: `mypy`
- Dependencies in `requirements.txt` and `requirements-dev.txt` (pinned versions)

### Frontend (`frontend/`)
- Node 20+ LTS, Vite, React 18+, TypeScript (strict mode)
- React Router for routing
- TanStack Query for server state
- Axios for HTTP
- React Hook Form + Zod for forms and validation
- Tailwind CSS for styling
- Testing: Vitest + React Testing Library
- Lint/format: ESLint + Prettier

### Database
- SQLite in development (`backend/dept.db`, git-ignored)
- Must stay PostgreSQL-compatible: don't use raw SQL that only works on SQLite, and use Alembic for every schema change
- The DB URL comes from the environment variable `DATABASE_URL`

## Coding conventions

### Backend
- Layering: `routers/` (HTTP only) → `services/` (business rules and permission checks) → `models/` (SQLAlchemy). Routers never contain business logic.
- Pydantic schemas live in `schemas/`, one file per resource, using the `XCreate`, `XUpdate` and `XOut` naming pattern.
- Use dependency injection for the DB session (`get_db`) and the current user (`get_current_user`).
- Errors: raise `HTTPException` with clear messages. Use 404 for not found, 409 for conflicts and duplicates, 403 for forbidden, 422 for validation errors.
- List endpoints support `?search=`, `?skip=` and `?limit=` (default 20, max 100) and return `{ "items": [...], "total": n }`.
- Use type hints everywhere. `mypy` must pass.
- Names: `snake_case` for Python and DB columns, plural table names.

### Frontend
- TypeScript types in `src/types/` must mirror the backend `XOut` and `XCreate` schemas exactly.
- All HTTP calls go through `src/api/` (one file per resource). Components never call axios directly.
- Server data is read with TanStack Query hooks (`src/hooks/`), never with `useEffect` + `fetch`.
- Pages go in `src/pages/` and reusable UI in `src/components/`.
- No `any`. No `// @ts-ignore` unless there's a comment explaining why.
- Every page handles loading, error and empty states.
- Show and hide UI by role, but the backend is always the real security check.

### Git
- Branch per task: `task/<TASK-ID>-<short-slug>`, e.g. `task/T1.2-department-model`
- Commit format: `<TASK-ID>: <imperative summary>`, e.g. `T1.2: add Department model and migration`
- One PR per task, titled `<TASK-ID>: <task title>`
- Don't merge your own PR. The reviewer merges.

## Commands

Run these before every report. Each one must pass.

```bash
# Backend (from backend/)
ruff check . && ruff format --check .
mypy app
pytest -q

# Frontend (from frontend/)
npm run lint
npm run typecheck      # tsc --noEmit
npm run test -- --run
npm run build
```

Run the dev servers with:
```bash
cd backend && uvicorn app.main:app --reload       # http://localhost:8000/docs
cd frontend && npm run dev                         # http://localhost:5173
```

(Until a task creates one of these commands, skip it and say so in your report.)

## Task Report (required at the end of every task)

Reply with exactly this structure so the reviewer can check your work quickly:

```markdown
## Task Report — <TASK-ID>: <title>

**Branch / PR:** <branch name> / <PR link>
**Status:** Ready for review | Blocked | Partially done

### What I did
- <bullet per meaningful change>

### Files changed
- `path/to/file` — <one-line reason>

### Acceptance criteria
- [x] <criterion copied from TASKS.md> — <how verified>
- [ ] <criterion not met> — <why>

### Checks
- ruff: pass | mypy: pass | pytest: N passed | eslint: pass | tsc: pass | vitest: N passed | build: pass
  (mark "n/a" for anything that doesn't exist yet)

### How to verify manually
1. <steps the reviewer can run>

### Deviations from the plan
- None | <what changed and why>

### Open questions / Suggestions
- None | <items for the reviewer>
```

## When the reviewer requests changes

- Work on the **same branch** and update the same PR.
- Reply with a short **Revision Report** listing each review comment and how you addressed it.
- Re-run every check in "Commands".
