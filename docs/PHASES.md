# Phases

The project is built in 9 phases. Each phase ends with a **gate**: a short review where the orchestrator checks that the whole phase works together before the next phase starts.

| Phase | Name | Goal | Tasks |
|---|---|---|---|
| 0 | Project setup | Repo, tooling and CI ready; nothing functional yet | T0.1–T0.3 |
| 1 | Backend foundation | Config, database, all models and the first migration | T1.1–T1.4 |
| 2 | Authentication & roles | Login, JWT, role checks, seed admin | T2.1–T2.4 |
| 3 | Core APIs | Departments, teachers, students and courses with permissions | T3.1–T3.4 |
| 4 | Enrollments, grades & dashboard | Enrollment rules, grading, GPA, stats, users API, CSV | T4.1–T4.5 |
| 5 | Frontend foundation | Vite app, API client, auth flow, layout | T5.1–T5.4 |
| 6 | Frontend features | All CRUD pages | T6.1–T6.5 |
| 7 | Dashboards, grades UI & polish | Role dashboards, grade entry, profile, UX polish | T7.1–T7.4 |
| 8 | Hardening & deployment | PostgreSQL, Docker, end-to-end checks, docs | T8.1–T8.4 |

## Phase gates

### Gate 0 → 1
- [ ] `backend/` and `frontend/` folders exist with lint, type check and test commands that pass
- [ ] CI runs on every PR and is green

### Gate 1 → 2
- [ ] `alembic upgrade head` creates every table from `ARCHITECTURE.md` on a fresh SQLite database
- [ ] Model constraints (unique fields, foreign keys) are covered by tests
- [ ] `/api/v1/health` returns 200

### Gate 2 → 3
- [ ] You can log in at `/docs` with the seeded admin
- [ ] `require_roles` and the scope helpers have tests for all 4 roles
- [ ] A deactivated user can't log in

### Gate 3 → 4
- [ ] CRUD for departments, teachers, students and courses works at `/docs`
- [ ] Every permission row in `REQUIREMENTS.md` §3 for these resources has a passing test
- [ ] BR-1, BR-2, BR-3, BR-7 and BR-8 are enforced and tested

### Gate 4 → 5 (backend complete)
- [ ] Every endpoint in `ARCHITECTURE.md` §3 exists and is tested
- [ ] BR-4, BR-5 and BR-6 are enforced and tested; GPA calculation is tested
- [ ] Coverage ≥ 80% for `services/` and `routers/`
- [ ] The demo seed command creates realistic data

### Gate 5 → 6
- [ ] Login and logout work against the real backend; the token is attached automatically
- [ ] Protected routes redirect to `/login`, and pages you don't have access to show "Not authorized"
- [ ] The layout and sidebar menu change by role

### Gate 6 → 7
- [ ] Every list page has search, filters and pagination, plus loading, error and empty states
- [ ] Create, edit and delete work with validation and server errors shown in the form
- [ ] Manual walkthrough done as each of the 4 roles

### Gate 7 → 8 (feature complete)
- [ ] Every FR in `REQUIREMENTS.md` is implemented
- [ ] Bulk grade entry and GPA display work end to end

### Gate 8 → Done
- [ ] `docker compose up` runs the full stack on PostgreSQL
- [ ] Smoke test passes on the Docker stack
- [ ] The README lets a new developer run the project in under 10 steps
