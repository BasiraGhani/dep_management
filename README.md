# University Department Management System

A web application for managing a university's departments, teachers, students, courses, enrollments and grades, with role-based access control.

**Stack:** Python (FastAPI) · React + TypeScript (Vite) · SQLite (PostgreSQL later)

> This repository currently contains the **planning kit only**. No application code has been written yet.
> A coding agent builds the system one task at a time from `TASKS.md`, and each task is reviewed before the next one starts.

## Run with Docker

Runs the whole stack (PostgreSQL, backend, frontend behind Nginx) with one command:

```bash
cp .env.example .env      # then set POSTGRES_PASSWORD, SECRET_KEY and FIRST_ADMIN_PASSWORD
docker compose up --build
```

Open http://localhost and sign in as the admin from `.env`. Set `SEED_DEMO=true` in `.env`
for demo data with one login per role (password `demo-password`). Migrations run each time
the backend starts; the database lives in the `pgdata` volume (`docker compose down -v`
deletes it).

## What's in this kit

| File | Purpose | Who reads it |
|---|---|---|
| `CLAUDE.md` | Rules, conventions, and workflow for the coding agent | Coding agent (loads automatically) |
| `TASKS.md` | Every task in order, with acceptance criteria and status | Coding agent + reviewer |
| `docs/REQUIREMENTS.md` | What the system must do: roles, permissions, features, rules | Everyone |
| `docs/ARCHITECTURE.md` | Data model, API contract, pages, folder structure | Coding agent + reviewer |
| `docs/PHASES.md` | The 9 phases, their goals, and the gate to pass each one | Reviewer |
| `docs/REVIEW_CHECKLIST.md` | What the orchestrator checks before approving a task | Reviewer (orchestrator) |

## Workflow

```
┌──────────────────┐   1. "Do task T1.2"     ┌──────────────────┐
│   Orchestrator   │ ──────────────────────▶ │   Coding agent   │
│  (review chat)   │                         │                  │
│                  │ ◀────────────────────── │  branch + PR +   │
│                  │   2. Task report + PR   │  task report     │
└──────────────────┘                         └──────────────────┘
        │
        │ 3. Review against REVIEW_CHECKLIST.md
        ▼
   Approve → merge → mark [x] in TASKS.md → next task
   Changes requested → send feedback to agent → repeat
```

1. Put this kit at the root of a new Git repository and push it.
2. Open a coding-agent session on the repo. It reads `CLAUDE.md` automatically.
3. Tell the agent: **"Implement task T0.1 from TASKS.md."**
4. The agent works on a branch, opens a PR, and replies with a **Task Report** (format is in `CLAUDE.md`).
5. Paste the report and PR link (or diff) into the orchestrator chat for review.
6. If it's approved, merge the PR and move on to the next task. If changes are requested, send the review notes back to the agent.
