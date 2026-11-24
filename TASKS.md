# TASKS.md

Implement tasks **in order**, **one per PR**. Don't start a task until the tasks it depends on are merged.

**Status legend:** `[ ]` todo · `[~]` in review · `[x]` done (set by the reviewer) · `[!]` blocked

References: **FR/BR/NFR** → `docs/REQUIREMENTS.md` · **§** → `docs/ARCHITECTURE.md`

---

## Phase 0 — Project setup

### [ ] T0.1 Repository scaffolding
- **Depends on:** —
- **Do:** Create a root `.gitignore` (Python, Node, `.env`, `*.db`, coverage, build output), `.editorconfig`, and empty `backend/` and `frontend/` folders containing placeholder READMEs. Don't change the planning documents.
- **Acceptance:**
  - [ ] Folder layout matches §5 (top level only)
  - [ ] `.env` and `*.db` files are git-ignored

### [ ] T0.2 Backend tooling
- **Depends on:** T0.1
- **Do:** Create `requirements.txt` and `requirements-dev.txt` (pinned), and a `pyproject.toml` configuring ruff, mypy (strict-ish: `disallow_untyped_defs`) and pytest. Add a minimal `app/main.py` with `GET /api/v1/health → {"status": "ok"}` and one test for it. Add `.env.example`.
- **Acceptance:**
  - [ ] `ruff check`, `mypy app` and `pytest` all pass
  - [ ] `uvicorn app.main:app` serves `/docs` and `/api/v1/health`

### [ ] T0.3 Frontend tooling + CI
- **Depends on:** T0.1
- **Do:** Scaffold Vite React + TypeScript in `frontend/` with strict TS. Add ESLint, Prettier, Tailwind, Vitest + RTL (with one passing smoke test), and the `lint`, `typecheck`, `test` and `build` npm scripts. Add `.github/workflows/ci.yml` running all backend and frontend checks on every PR.
- **Acceptance:**
  - [ ] `npm run lint`, `typecheck`, `test -- --run` and `build` all pass
  - [ ] CI runs on the PR and is green

**🚦 Gate 0 → 1** (see PHASES.md)

---

## Phase 1 — Backend foundation

### [ ] T1.1 Config and database setup
- **Depends on:** T0.2
- **Do:** Add `config.py` (pydantic-settings: `DATABASE_URL`, `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `CORS_ORIGINS`, `FIRST_ADMIN_USERNAME`, `FIRST_ADMIN_PASSWORD`). Add `database.py` (engine, `SessionLocal`, `Base` with `id`, `created_at` and `updated_at` mixins, and `get_db`). Turn on SQLite foreign key enforcement. Add CORS to `main.py`. Initialize Alembic using the app's `Base` and `DATABASE_URL`.
- **Acceptance:**
  - [ ] Settings load from `.env`, and `.env.example` documents every variable
  - [ ] `alembic upgrade head` runs with no errors (no tables yet)
  - [ ] Foreign keys are enforced on SQLite (tested)

### [ ] T1.2 Models: departments, teachers, students
- **Depends on:** T1.1
- **Do:** Create the SQLAlchemy 2.x typed models for `departments`, `teachers` and `students` exactly as in §2, including enums and relationships. Generate the Alembic migration.
- **Acceptance:**
  - [ ] The migration creates all 3 tables with the correct constraints
  - [ ] Tests confirm unique constraints (code, name, email, student_no) and the foreign keys

### [ ] T1.3 Models: courses, enrollments, users
- **Depends on:** T1.2
- **Do:** Add the `courses`, `enrollments` (unique `student_id + course_id + semester`, cascade on student delete) and `users` (role enum, optional unique links) models. Generate the migration.
- **Acceptance:**
  - [ ] `alembic downgrade base && alembic upgrade head` works
  - [ ] Tests cover the enrollment unique constraint and cascade delete

### [ ] T1.4 Test infrastructure
- **Depends on:** T1.3
- **Do:** In `tests/conftest.py`, add an isolated test database (a fresh SQLite database per test session, transaction rollback per test), a `TestClient` fixture, and factory helpers for creating departments, teachers, students, courses and users.
- **Acceptance:**
  - [ ] Tests don't share state (verified by running them in random order: `pytest -p random_order` or equivalent)
  - [ ] Factories are documented with docstrings

**🚦 Gate 1 → 2**

---

## Phase 2 — Authentication & roles

### [ ] T2.1 Security utilities
- **Depends on:** T1.4
- **Do:** In `core/security.py`: argon2 hashing and verification with pwdlib, plus JWT creation and decoding with PyJWT (`sub` = user id, `role`, `exp`).
- **Acceptance:**
  - [ ] Unit tests: a correct password verifies and a wrong one fails; expired and tampered tokens are rejected

### [ ] T2.2 Login and current user
- **Depends on:** T2.1
- **Do:** Add `POST /auth/login` (OAuth2 password form so `/docs` "Authorize" works), `GET /auth/me` and `POST /auth/change-password`. In `core/deps.py`, add `get_current_user`, which rejects missing, invalid or expired tokens and inactive users.
- **Acceptance:**
  - [ ] FR-1.1, FR-1.2, FR-1.3, FR-1.6 and FR-8.2 met and tested
  - [ ] The password hash never appears in any response (tested)

### [ ] T2.3 Role and scope helpers
- **Depends on:** T2.2
- **Do:** In `core/deps.py`, add `require_roles(*roles)`. In `core/permissions.py`, add scope helpers: `user_department_id(user)`, `can_manage_department(user, dept_id)`, `teaches_course(user, course_id)` and `is_self_student(user, student_id)`.
- **Acceptance:**
  - [ ] Tests for each helper cover all 4 roles (allowed and denied cases)

### [ ] T2.4 CLI: seed admin and demo data
- **Depends on:** T2.2
- **Do:** In `app/cli.py`, add `python -m app.cli seed-admin` (idempotent, reads the env variables) and `python -m app.cli seed-demo` (3 departments, ~10 teachers including one HOD per department, ~60 students, ~12 courses, enrollments with some grades, and one login per role). Print the demo logins.
- **Acceptance:**
  - [ ] Running either command twice doesn't create duplicates
  - [ ] Each printed demo login works at `/auth/login`

**🚦 Gate 2 → 3**

---

## Phase 3 — Core APIs

> For every resource in this phase: schemas (`Create`, `Update`, `Out`, `ListOut`), a service with all rules and permission checks, a thin router, and tests for success, 404, 409, 422 and 403 for each role from the permission matrix (REQUIREMENTS §3).

### [ ] T3.1 Departments API
- **Depends on:** T2.3
- **Do:** Build the department endpoints in §3, including detail counts (teachers, students, courses) and the head. Enforce BR-1, BR-3 and BR-7 (delete blocked while dependents exist). Let a HOD update their own department (everything except name and code).
- **Acceptance:**
  - [ ] FR-2.1–FR-2.4 met and tested
  - [ ] Search and pagination return `{items, total}`

### [ ] T3.2 Teachers API
- **Depends on:** T3.1
- **Do:** Build the teacher endpoints in §3. Support an optional account on create (`create_account: {username, temp_password}`). Let a teacher update their own contact fields. Block deletion while the teacher heads a department or teaches a course (409).
- **Acceptance:**
  - [ ] FR-3.1–FR-3.4 met and tested
  - [ ] A HOD can only create or edit teachers in their own department (tested)

### [ ] T3.3 Students API
- **Depends on:** T3.1
- **Do:** Build the student endpoints in §3 with `department_id`, `year` and `status` filters and an optional account on create. Apply role scoping to list and detail: HODs see their own department, teachers see students in their courses, students see only themselves.
- **Acceptance:**
  - [ ] FR-4.1–FR-4.4 met and tested
  - [ ] Scoping tests: a student can't read another student (403), and a teacher can't read students outside their courses

### [ ] T3.4 Courses API
- **Depends on:** T3.2
- **Do:** Build the course endpoints in §3. Enforce BR-2 (the teacher must be in the same department). Let a teacher update only the description of their own courses. Block deletion while enrollments exist (409). The roster on the course detail is hidden from students.
- **Acceptance:**
  - [ ] FR-5.1–FR-5.4 met and tested
  - [ ] BR-2 violation returns 422 or 409 with a clear message (tested)

**🚦 Gate 3 → 4**

---

## Phase 4 — Enrollments, grades & dashboard

### [ ] T4.1 Enrollments API
- **Depends on:** T3.3, T3.4
- **Do:** Build `GET/POST/DELETE /enrollments` with role scoping. Validate the semester format. Enforce BR-4 (active students only), BR-5 (capacity) and FR-6.2 (no duplicates).
- **Acceptance:**
  - [ ] Tests cover each rule's failure case with the correct status code and message

### [ ] T4.2 Grades and GPA
- **Depends on:** T4.1
- **Do:** Build `PATCH /enrollments/{id}/grade` and bulk `PUT /courses/{id}/grades` (all-or-nothing transaction). Add a GPA service using the §2 grade points, weighted by credits and counting graded enrollments only. Include the GPA in the student detail.
- **Acceptance:**
  - [ ] FR-6.5–FR-6.7 met
  - [ ] GPA unit tests: no grades → `null`, mixed credits, all F → 0.0
  - [ ] A teacher can't grade another teacher's course (403)

### [ ] T4.3 Department head role sync
- **Depends on:** T3.1, T3.2
- **Do:** Enforce BR-6. Setting or changing `head_id` promotes the new head's user to `hod` and demotes the previous head to `teacher`, in the same transaction.
- **Acceptance:**
  - [ ] Tests: assign a head, replace the head, remove the head, and a head with no user account (no error)

### [ ] T4.4 Users API (admin)
- **Depends on:** T2.3
- **Do:** Build the `/users` endpoints in §3: list with filters, create (link validation per the §2 constraint), PATCH (activate, deactivate, role, links) and reset password.
- **Acceptance:**
  - [ ] FR-8.1 and FR-8.2 met; non-admins get 403 on every endpoint (tested)
  - [ ] Invalid role and link combinations are rejected (tested)

### [ ] T4.5 Dashboard + CSV export
- **Depends on:** T4.2
- **Do:** Build `GET /dashboard`, which returns a role-specific payload (FR-7.1–FR-7.4, with a documented response schema for each role). Build `GET /export/{resource}.csv` that respects the same filters and scoping as the list endpoints.
- **Acceptance:**
  - [ ] Dashboard tests for each role check the numbers against seeded data
  - [ ] The CSV has a header row and the correct rows for the filters (tested)
  - [ ] Backend coverage ≥ 80% for `services/` and `routers/` (report the figure)

**🚦 Gate 4 → 5 (backend complete)**

---

## Phase 5 — Frontend foundation

### [ ] T5.1 Types and API client
- **Depends on:** T4.5, T0.3
- **Do:** Add `src/types/` mirroring every backend schema, and an axios client in `src/api/client.ts` that uses `VITE_API_URL`, attaches the token, and logs out on a 401. Add one API module per resource.
- **Acceptance:**
  - [ ] Types match the backend schemas field for field (list any differences in the report)
  - [ ] Unit test: a 401 response clears the token and redirects

### [ ] T5.2 Auth context and login page
- **Depends on:** T5.1
- **Do:** Add `AuthContext` (token, current user from `/auth/me`, `login()`, `logout()`), a login page (React Hook Form + Zod) and token persistence.
- **Acceptance:**
  - [ ] Logging in with valid demo credentials goes to `/`, and invalid ones show an error
  - [ ] Refreshing the page keeps the user logged in

### [ ] T5.3 Routing and guards
- **Depends on:** T5.2
- **Do:** Add all routes from §4. `ProtectedRoute` redirects to `/login` when there's no token. `RoleGate` shows a "Not authorized" page. Add a 404 page.
- **Acceptance:**
  - [ ] Tests: unauthenticated users are redirected, and a student visiting `/users` sees "Not authorized"

### [ ] T5.4 App layout and shared components
- **Depends on:** T5.3
- **Do:** Build the layout (a sidebar filtered by role, a top bar with name, role and logout) and the shared components: `DataTable` (pagination, sorting header, empty state), `SearchInput` (debounced), `FormField`, `ConfirmDialog`, `Modal`, toast notifications, `LoadingSpinner` and `ErrorMessage`.
- **Acceptance:**
  - [ ] Each shared component has at least one test
  - [ ] Sidebar items match the role table in §4 (tested for every role)

**🚦 Gate 5 → 6**

---

## Phase 6 — Frontend features

> Each page: TanStack Query hooks, loading, error and empty states, search, filters and pagination, Zod validation, server error messages shown in the form, delete confirmation, success toasts, and actions hidden by role.

### [ ] T6.1 Departments pages
- **Depends on:** T5.4
- **Do:** Build the list page and a detail page (head, counts, course list, teachers) with create and edit (admin) and HOD edit of their own department.
- **Acceptance:**
  - [ ] Deleting a department with dependents shows the server's 409 message
  - [ ] Component tests for the list and form

### [ ] T6.2 Teachers pages
- **Depends on:** T6.1
- **Do:** Build the list (department and title filters), the detail page (courses taught), and create and edit with the optional "create login account" section.
- **Acceptance:**
  - [ ] A HOD can only pick their own department in the form
  - [ ] Component tests

### [ ] T6.3 Students pages
- **Depends on:** T6.1
- **Do:** Build the list (department, year and status filters) and the detail page (profile, enrollments, grades, GPA), with create and edit including the optional account.
- **Acceptance:**
  - [ ] FR-4 is fully usable from the UI
  - [ ] Component tests

### [ ] T6.4 Courses pages
- **Depends on:** T6.2
- **Do:** Build the list (department and teacher filters) and the detail page (roster with grades, hidden from students), with create and edit. The teacher dropdown only lists teachers in the selected department (BR-2).
- **Acceptance:**
  - [ ] Changing the department in the form resets the teacher choice
  - [ ] Component tests

### [~] T6.5 Enrollment management
- **Depends on:** T6.3, T6.4
- **Do:** On the course detail page, add an "Enroll student" picker (search for active students) with a semester selector, plus unenroll. Show capacity as "28 / 40".
- **Acceptance:**
  - [ ] Capacity, duplicate and inactive-student errors are shown clearly
  - [ ] Component tests

**🚦 Gate 6 → 7**

---

## Phase 7 — Dashboards, grades UI & polish

### [~] T7.1 Role dashboards
- **Depends on:** T6.5
- **Do:** Build the `/` dashboard for each role using the `/dashboard` payload: stat cards, a "students per department" bar chart (Recharts) for admin and HOD, a course list with ungraded counts for teachers, and enrollments, grades and GPA for students.
- **Acceptance:**
  - [ ] Each role's dashboard renders correctly (tested with mocked payloads)

### [~] T7.2 Bulk grade entry
- **Depends on:** T6.5
- **Do:** Build `/courses/:id/grades`: a table of enrolled students with a grade dropdown in each row, a semester filter, and "Save all" calling the bulk endpoint. Warn before leaving the page with unsaved changes.
- **Acceptance:**
  - [ ] FR-6.7 works end to end; a failed save keeps the user's edits
  - [ ] Component tests

### [ ] T7.3 Profile page and user management
- **Depends on:** T6.1
- **Do:** Build `/profile` (view your own record, edit contact fields, change password) and `/users` for admins (list, filters, create, activate or deactivate, reset password showing the temporary password once).
- **Acceptance:**
  - [ ] FR-1.6 and FR-8 are usable from the UI
  - [ ] Component tests

### [ ] T7.4 CSV export buttons and UX polish
- **Depends on:** T7.1–T7.3
- **Do:** Add "Export CSV" buttons to the students, teachers and courses lists (using the current filters). Check the layout on tablet width, make sure every form has labels and is accessible, and use consistent empty states.
- **Acceptance:**
  - [ ] FR-9.1 met
  - [ ] Manual walkthrough checklist for all 4 roles included in the report

**🚦 Gate 7 → 8 (feature complete)**

---

## Phase 8 — Hardening & deployment

### [ ] T8.1 PostgreSQL support
- **Depends on:** T7.4
- **Do:** Add the `psycopg` driver and confirm that the migrations and the full test suite run against PostgreSQL (CI service container). Fix any SQLite-only behavior, such as case-insensitive uniqueness.
- **Acceptance:**
  - [ ] CI runs the backend tests on both SQLite and PostgreSQL, and both are green

### [ ] T8.2 Docker
- **Depends on:** T8.1
- **Do:** Add a backend Dockerfile (migrations run on start), a frontend Dockerfile (build, then serve with Nginx and proxy `/api` to the backend) and `docker-compose.yml` with `db`, `backend` and `frontend` plus a Postgres volume.
- **Acceptance:**
  - [ ] `docker compose up --build` gives a working app at `http://localhost`
  - [ ] Secrets come from `.env`, and `.env.example` is updated

### [ ] T8.3 End-to-end smoke test
- **Depends on:** T8.2
- **Do:** Add a Playwright smoke test (or a documented script): log in as each role, open the dashboard, and run one key action per role (admin creates a department, HOD creates a course, teacher saves grades, student sees their GPA).
- **Acceptance:**
  - [ ] The smoke test passes against the Docker stack

### [ ] T8.4 Documentation and security review
- **Depends on:** T8.3
- **Do:** Write the final README (setup in under 10 steps, demo logins, architecture summary, how to run tests). Run a security pass: CORS limited to the frontend origin, `SECRET_KEY` required in production, rate-limit or delay repeated failed logins, and no secrets in the repo.
- **Acceptance:**
  - [ ] NFR-1 and NFR-7 met
  - [ ] Security checklist included in the report

**🏁 Gate 8 → Done**
