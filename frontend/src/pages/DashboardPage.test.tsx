import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { getMe } from '../api/auth';
import { getDashboard } from '../api/dashboard';
import { clearToken, setToken } from '../auth/token';
import { apiError, meFor } from '../test/fixtures';
import { renderApp } from '../test/render';
import type {
  AdminDashboard,
  CurrentUserOut,
  EnrollmentOut,
  HodDashboard,
  StudentDashboard,
  TeacherDashboard,
} from '../types';

vi.mock('../api/auth', () => ({ login: vi.fn(), getMe: vi.fn(), changePassword: vi.fn() }));
vi.mock('../api/dashboard');

const cs101 = { id: 11, code: 'CS101', title: 'Programming', credits: 4, teacher_id: 2 };
const ma201 = { id: 21, code: 'MA201', title: 'Linear Algebra', credits: 3, teacher_id: 2 };

const recent: EnrollmentOut = {
  id: 501,
  student_id: 1,
  course_id: 11,
  semester: '2026-Fall',
  grade: null,
  student: { id: 1, student_no: 'CS2026001', first_name: 'Amira', last_name: 'Costa' },
  course: cs101,
  created_at: '2026-11-20T09:30:00Z',
  updated_at: '2026-11-20T09:30:00Z',
};

const adminData: AdminDashboard = {
  role: 'admin',
  totals: { departments: 3, teachers: 12, students: 140, courses: 25 },
  students_per_department: [
    { department_id: 3, code: 'CS', name: 'Computer Science', students: 80 },
    { department_id: 4, code: 'MATH', name: 'Mathematics', students: 45 },
    { department_id: 5, code: 'PHYS', name: 'Physics', students: 15 },
  ],
  recent_enrollments: [recent],
};
const hodData: HodDashboard = {
  role: 'hod',
  department: { id: 3, code: 'CS', name: 'Computer Science' },
  totals: { departments: 1, teachers: 5, students: 80, courses: 9 },
  students_per_department: [adminData.students_per_department[0]],
  recent_enrollments: [recent],
};
const teacherData: TeacherDashboard = {
  role: 'teacher',
  courses: [
    { course: cs101, capacity: 40, enrolled: 28, ungraded: 6 },
    { course: ma201, capacity: 30, enrolled: 12, ungraded: 0 },
  ],
};
const studentData: StudentDashboard = {
  role: 'student',
  enrollments: [
    { id: 1, semester: '2026-Spring', grade: 'A', course: ma201 },
    { id: 2, semester: '2026-Fall', grade: null, course: cs101 },
  ],
  gpa: 4,
  graded_credits: 3,
};

beforeEach(() => {
  clearToken();
});
afterEach(() => {
  vi.clearAllMocks();
});

function open(me: CurrentUserOut) {
  setToken('valid.token');
  vi.mocked(getMe).mockResolvedValue(me);
  renderApp('/');
}
const stat = (label: string, value: string) => {
  expect(screen.getByLabelText(`${label}: ${value}`)).toBeInTheDocument();
};
const rowsOf = (table: HTMLElement) =>
  within(table)
    .getAllByRole('row')
    .slice(1)
    .map((row) =>
      within(row)
        .getAllByRole('cell')
        .map((cell) => cell.textContent),
    );

describe('admin dashboard (FR-7.1)', () => {
  beforeEach(() => {
    vi.mocked(getDashboard).mockResolvedValue(adminData);
    open(meFor('admin'));
  });

  it('shows the four totals, each linking to its list', async () => {
    await screen.findByLabelText('Departments: 3');
    stat('Teachers', '12');
    stat('Students', '140');
    stat('Courses', '25');
    expect(screen.getByRole('link', { name: 'Departments: 3' })).toHaveAttribute(
      'href',
      '/departments',
    );
    expect(screen.getByRole('link', { name: 'Students: 140' })).toHaveAttribute(
      'href',
      '/students',
    );
  });

  it('charts students per department, with the figures in an accessible table', async () => {
    const section = await screen.findByRole('region', { name: 'Students per department' });
    const table = within(section).getByRole('table', { name: 'Students per department' });

    expect(rowsOf(table)).toEqual([
      ['Computer Science (CS)', '80'],
      ['Mathematics (MATH)', '45'],
      ['Physics (PHYS)', '15'],
    ]);
  });

  it('lists recent enrollments with links to the student and course', async () => {
    const section = await screen.findByRole('region', { name: 'Recent enrollments' });

    expect(rowsOf(within(section).getByRole('table'))).toEqual([
      ['Amira Costa', 'CS101 Programming', '2026-Fall', '2026-11-20'],
    ]);
    expect(within(section).getByRole('link', { name: 'Amira Costa' })).toHaveAttribute(
      'href',
      '/students/1',
    );
    expect(within(section).getByRole('link', { name: 'CS101 Programming' })).toHaveAttribute(
      'href',
      '/courses/11',
    );
  });
});

describe('HOD dashboard (FR-7.2)', () => {
  it("shows their department's figures, without a departments total", async () => {
    vi.mocked(getDashboard).mockResolvedValue(hodData);
    open(meFor('hod'));

    await screen.findByLabelText('Students: 80');
    stat('Teachers', '5');
    stat('Courses', '9');
    expect(screen.queryByLabelText(/^Departments:/)).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Computer Science (CS)' })).toHaveAttribute(
      'href',
      '/departments/3',
    );
    const chart = screen.getByRole('region', { name: 'Students per department' });
    expect(rowsOf(within(chart).getByRole('table'))).toEqual([['Computer Science (CS)', '80']]);
    expect(screen.getByRole('region', { name: 'Recent enrollments' })).toHaveTextContent(
      'Amira Costa',
    );
  });

  it('explains when the account no longer heads a department', async () => {
    vi.mocked(getDashboard).mockResolvedValue({
      ...hodData,
      department: null,
      totals: { departments: 0, teachers: 0, students: 0, courses: 0 },
      students_per_department: [],
      recent_enrollments: [],
    });
    open(meFor('hod'));

    expect(
      await screen.findByText(/You don't head a department at the moment/),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText(/^Students:/)).not.toBeInTheDocument();
  });
});

describe('teacher dashboard (FR-7.3)', () => {
  it('lists their courses with enrolled and ungraded counts', async () => {
    vi.mocked(getDashboard).mockResolvedValue(teacherData);
    open(meFor('teacher'));

    const section = await screen.findByRole('region', { name: 'My courses' });
    expect(rowsOf(within(section).getByRole('table'))).toEqual([
      ['CS101 Programming', '4', '28 / 40', '6', 'Enter grades'],
      ['MA201 Linear Algebra', '3', '12 / 30', 'All graded', 'Enter grades'],
    ]);
    expect(within(section).getByRole('link', { name: 'Enter grades for CS101' })).toHaveAttribute(
      'href',
      '/courses/11/grades',
    );
    stat('My courses', '2');
    stat('Enrollments', '40');
    stat('Still to grade', '6');
  });

  it('has no grade link for a course nobody is enrolled in', async () => {
    vi.mocked(getDashboard).mockResolvedValue({
      role: 'teacher',
      courses: [{ course: cs101, capacity: 40, enrolled: 0, ungraded: 0 }],
    });
    open(meFor('teacher'));

    await screen.findByRole('link', { name: 'CS101 Programming' });
    expect(screen.queryByRole('link', { name: /Enter grades/ })).not.toBeInTheDocument();
  });

  it('says when they teach no courses', async () => {
    vi.mocked(getDashboard).mockResolvedValue({ role: 'teacher', courses: [] });
    open(meFor('teacher'));

    expect(await screen.findByText("You aren't teaching any courses yet.")).toBeInTheDocument();
    stat('My courses', '0');
  });
});

describe('student dashboard (FR-7.4)', () => {
  it('shows GPA and enrollments with grades, newest semester first', async () => {
    vi.mocked(getDashboard).mockResolvedValue(studentData);
    open(meFor('student'));

    const section = await screen.findByRole('region', { name: 'My enrollments and grades' });
    expect(rowsOf(within(section).getByRole('table'))).toEqual([
      ['CS101 Programming', '2026-Fall', '4', 'Not graded'],
      ['MA201 Linear Algebra', '2026-Spring', '3', 'A'],
    ]);
    stat('GPA', '4.00');
    stat('Graded credits', '3');
    stat('Courses taken', '2');
    stat('Awaiting a grade', '1');
  });

  it('shows a dash and a note while nothing is graded', async () => {
    vi.mocked(getDashboard).mockResolvedValue({
      ...studentData,
      enrollments: [studentData.enrollments[1]],
      gpa: null,
      graded_credits: 0,
    });
    open(meFor('student'));

    await screen.findByLabelText('GPA: —');
    expect(screen.getByText('Your GPA appears once a course has been graded.')).toBeInTheDocument();
  });

  it('says when they are not enrolled in anything', async () => {
    vi.mocked(getDashboard).mockResolvedValue({
      role: 'student',
      enrollments: [],
      gpa: null,
      graded_credits: 0,
    });
    open(meFor('student'));

    expect(await screen.findByText("You aren't enrolled in any course yet.")).toBeInTheDocument();
    expect(screen.queryByText(/Your GPA appears/)).not.toBeInTheDocument();
  });
});

describe('loading, errors and empty data', () => {
  it('shows a spinner while loading', async () => {
    vi.mocked(getDashboard).mockReturnValue(new Promise(() => undefined));
    open(meFor('admin'));

    expect(await screen.findByText('Loading dashboard…')).toBeInTheDocument();
  });

  it('shows the error with a retry that reloads', async () => {
    vi.mocked(getDashboard).mockRejectedValueOnce(apiError(500, 'Something broke'));
    vi.mocked(getDashboard).mockResolvedValueOnce(adminData);
    open(meFor('admin'));
    const user = userEvent.setup();

    await user.click(await screen.findByRole('button', { name: 'Try again' }));

    expect(await screen.findByLabelText('Departments: 3')).toBeInTheDocument();
  });

  it('admin with no data yet sees empty messages', async () => {
    vi.mocked(getDashboard).mockResolvedValue({
      role: 'admin',
      totals: { departments: 0, teachers: 0, students: 0, courses: 0 },
      students_per_department: [],
      recent_enrollments: [],
    });
    open(meFor('admin'));

    expect(await screen.findByText('No departments yet.')).toBeInTheDocument();
    expect(screen.getByText('No enrollments yet.')).toBeInTheDocument();
    stat('Students', '0');
  });

  it('greets the user by name and role', async () => {
    vi.mocked(getDashboard).mockResolvedValue(teacherData);
    open(meFor('teacher'));

    expect(await screen.findByRole('heading', { level: 1 })).toHaveTextContent(/^Welcome, /);
    expect(screen.getByText('Teacher dashboard')).toBeInTheDocument();
    await waitFor(() => {
      expect(getDashboard).toHaveBeenCalledTimes(1);
    });
  });
});
