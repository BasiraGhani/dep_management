# Requirements — University Department Management System

## 1. Purpose

A web application that lets a university manage its academic departments and the people and courses in them. Each user's role decides what they can see and change.

## 2. Users and roles

| Role | Who | Scope |
|---|---|---|
| **Admin** | University IT or registrar staff | Everything in the system |
| **Head of Department (HOD)** | A teacher who leads a department | Their own department only |
| **Teacher** | Faculty member | Their own courses, their students' grades, their profile |
| **Student** | Enrolled student | Their own profile, enrollments and grades (read-only) |

- Every person who logs in has one **user account** with exactly one role.
- A Teacher or HOD account is linked to one `teachers` record. A Student account is linked to one `students` record. An Admin account has no linked record.
- A HOD is a teacher whose `teacher.id` is the `head_id` of a department. The HOD role is set on the user account, and it must match the department's `head_id` (see BR-6).

## 3. Permission matrix

Legend: **C** create · **R** read · **U** update · **D** delete · *own* = only records in their department, courses or profile · — = no access

| Resource | Admin | HOD | Teacher | Student |
|---|---|---|---|---|
| Users (accounts) | CRUD | — | — | — |
| Departments | CRUD | R (all), U (own dept: name excluded) | R | R |
| Teachers | CRUD | R (all), CU (own dept) | R (all), U (own profile: contact fields) | R (all: public fields) |
| Students | CRUD | CRUD (own dept) | R (students in own courses) | R (own), U (own profile: contact fields) |
| Courses | CRUD | CRUD (own dept) | R (all), U (own courses: description only) | R (all) |
| Enrollments | CRUD | CRUD (own dept courses) | R (own courses) | R (own) |
| Grades | CRUD | RU (own dept courses) | RU (own courses) | R (own) |
| Dashboard stats | All depts | Own dept | Own courses | Own summary |

The backend must enforce every rule in this matrix. The frontend only hides what a user isn't allowed to do.

## 4. Functional requirements

### FR-1 Authentication
- FR-1.1 Users log in with a username and password and receive a JWT access token (valid 60 minutes, configurable).
- FR-1.2 `GET /auth/me` returns the current user, their role, and their linked teacher or student record.
- FR-1.3 Passwords are hashed (argon2) and never returned by any API.
- FR-1.4 Logging out on the frontend clears the stored token.
- FR-1.5 A seed command creates the first Admin from environment variables.
- FR-1.6 Users can change their own password by giving the current password.

### FR-2 Departments
- FR-2.1 Admin can create, edit and delete departments (name, code, description, building, phone, head).
- FR-2.2 Department `code` (e.g. `CS`) and `name` are unique.
- FR-2.3 A department's detail view shows its head, teacher count, student count and course list.
- FR-2.4 A department can't be deleted while it still has teachers, students or courses (409).

### FR-3 Teachers
- FR-3.1 Create, edit, list, search (by name or email) and delete teachers.
- FR-3.2 Fields: first name, last name, email (unique), phone, title (Lecturer, Assistant Professor, Associate Professor, Professor), department, hire date.
- FR-3.3 Creating a teacher can optionally create a linked user account (username + temporary password).
- FR-3.4 A teacher can't be deleted while they head a department or teach a course (409).

### FR-4 Students
- FR-4.1 Create, edit, list, search (by name, email or student number), filter by department and year, and delete students.
- FR-4.2 Fields: student number (unique), first name, last name, email (unique), phone, date of birth, department, year of study (1–6), status (active, graduated, suspended, withdrawn), enrollment date.
- FR-4.3 Creating a student can optionally create a linked user account.
- FR-4.4 Deleting a student also deletes their enrollments. The UI must ask for confirmation.

### FR-5 Courses
- FR-5.1 Create, edit, list, search (by code or title), filter by department and teacher, and delete courses.
- FR-5.2 Fields: code (unique, e.g. `CS101`), title, description, credits (1–6), department, teacher (optional), capacity (default 40).
- FR-5.3 A course's teacher must belong to the same department (BR-2).
- FR-5.4 The course detail view lists enrolled students with their grades.

### FR-6 Enrollments and grades
- FR-6.1 Enroll a student in a course for a semester (e.g. `2026-Fall`).
- FR-6.2 A student can't be enrolled in the same course twice in the same semester (409).
- FR-6.3 Enrollment fails when the course is at capacity (409).
- FR-6.4 Only `active` students can be enrolled (BR-4).
- FR-6.5 Grades use letters: A, A-, B+, B, B-, C+, C, C-, D, F, or empty (not graded yet).
- FR-6.6 The system calculates a student's GPA on a 4.0 scale, weighted by credits and counting graded enrollments only.
- FR-6.7 A teacher can enter all grades for their course on one screen (bulk grade entry).

### FR-7 Dashboard
- FR-7.1 Admin: total departments, teachers, students and courses; students per department (bar chart); recent enrollments.
- FR-7.2 HOD: the same figures for their own department only.
- FR-7.3 Teacher: their courses with enrolled count and number of ungraded students.
- FR-7.4 Student: their enrollments, grades and GPA.

### FR-8 User management (Admin)
- FR-8.1 List, create, deactivate, reactivate and reset the password of user accounts.
- FR-8.2 Deactivated users can't log in.

### FR-9 Reports
- FR-9.1 Export the students, teachers or courses list to CSV, with the current filters applied.

## 5. Business rules

| ID | Rule |
|---|---|
| BR-1 | Codes, emails, usernames and student numbers are unique (case-insensitive). |
| BR-2 | A course's teacher must belong to the course's department. |
| BR-3 | A department head must be a teacher in that department. |
| BR-4 | Only students with status `active` can be enrolled in a course. |
| BR-5 | Course enrollment can't exceed its capacity in a semester. |
| BR-6 | Setting a department's head sets that teacher's user role to HOD. Replacing the head reverts the previous head to Teacher. |
| BR-7 | Records with dependents aren't deleted silently; the API returns 409 with a message explaining why. |
| BR-8 | Every create and update request validates its input (lengths, formats, ranges) and returns 422 with field errors. |

## 6. Non-functional requirements

| ID | Requirement |
|---|---|
| NFR-1 | **Security:** argon2 password hashing, JWT auth, role checks on every protected endpoint, CORS limited to the frontend origin, no secrets in Git. |
| NFR-2 | **Portability:** the app runs on SQLite in development and PostgreSQL in production with no code changes, only `DATABASE_URL`. |
| NFR-3 | **Testing:** backend test coverage ≥ 80% for `services/` and `routers/`. Every permission rule has at least one test. |
| NFR-4 | **Performance:** list endpoints are paginated, and typical requests respond in under 300 ms with 10k students. |
| NFR-5 | **Usability:** responsive layout (desktop and tablet), clear form errors, confirmation before deleting, toast messages for success and errors. |
| NFR-6 | **Code quality:** strict TypeScript, mypy, ruff and ESLint all pass in CI. |
| NFR-7 | **Docs:** the API documentation at `/docs` is always accurate, and the README explains setup in under 10 steps. |
| NFR-8 | **Deployment:** Docker Compose runs the full stack (frontend, backend, Postgres) with one command. |

## 7. Out of scope (for now)

Attendance, timetables and room booking, fees and payments, email notifications, file uploads, multi-language UI, SSO and OAuth. Ideas like these go in the "Suggestions" section of a task report.
