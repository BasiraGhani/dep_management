import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { getMe } from '../api/auth';
import { getCourse, listCourses } from '../api/courses';
import { getDepartment, listDepartments } from '../api/departments';
import { enroll, unenroll } from '../api/enrollments';
import { listStudents } from '../api/students';
import { listTeachers } from '../api/teachers';
import { clearToken, setToken } from '../auth/token';
import {
  amiraDetail,
  apiError,
  cs101Detail,
  csDepartment,
  csDepartmentDetail,
  csTeachers,
  kayDetail,
  meFor,
} from '../test/fixtures';
import { renderApp } from '../test/render';
import type { CourseDetailOut, CurrentUserOut, StudentOut } from '../types';

vi.mock('../api/auth', () => ({ login: vi.fn(), getMe: vi.fn(), changePassword: vi.fn() }));
vi.mock('../api/courses');
vi.mock('../api/departments');
vi.mock('../api/teachers');
vi.mock('../api/students');
vi.mock('../api/enrollments');

/** CS101 with 2 students in 2026-Fall (Bo, Cy) and 1 in 2026-Spring (Amira, graded A). */
const course: CourseDetailOut = {
  ...cs101Detail,
  roster: [
    {
      enrollment_id: 101,
      student_id: 1,
      student_no: 'CS2026001',
      first_name: 'Amira',
      last_name: 'Costa',
      semester: '2026-Spring',
      grade: 'A',
    },
    {
      enrollment_id: 103,
      student_id: 7,
      student_no: 'CS2026007',
      first_name: 'Bo',
      last_name: 'Diallo',
      semester: '2026-Fall',
      grade: null,
    },
    {
      enrollment_id: 104,
      student_id: 8,
      student_no: 'CS2026008',
      first_name: 'Cy',
      last_name: 'Evans',
      semester: '2026-Fall',
      grade: null,
    },
  ],
};
const student = (id: number, first: string, last: string, no: string): StudentOut => ({
  ...amiraDetail,
  id,
  first_name: first,
  last_name: last,
  student_no: no,
});
const candidates = [
  student(1, 'Amira', 'Costa', 'CS2026001'),
  student(7, 'Bo', 'Diallo', 'CS2026007'),
  student(9, 'Dana', 'Fox', 'CS2026009'),
];
const hodOf = (departmentId: number): CurrentUserOut => ({
  ...meFor('hod'),
  teacher_id: 50,
  teacher: { ...kayDetail, id: 50, department_id: departmentId },
});

beforeEach(() => {
  vi.useFakeTimers({
    toFake: ['Date'],
    shouldAdvanceTime: true,
    now: new Date('2026-11-24T12:00:00'),
  }); // -> 2026-Fall
  clearToken();
  vi.mocked(getCourse).mockResolvedValue(course);
  vi.mocked(getDepartment).mockResolvedValue(csDepartmentDetail);
  vi.mocked(listDepartments).mockResolvedValue({ items: [csDepartment], total: 1 });
  vi.mocked(listTeachers).mockResolvedValue(csTeachers);
  vi.mocked(listCourses).mockResolvedValue({ items: [], total: 0 });
  vi.mocked(listStudents).mockResolvedValue({ items: candidates, total: 3 });
});
afterEach(() => {
  vi.useRealTimers();
  vi.clearAllMocks();
});

function logIn(me: CurrentUserOut) {
  setToken('valid.token');
  vi.mocked(getMe).mockResolvedValue(me);
}
async function openAsAdmin() {
  logIn(meFor('admin'));
  const user = userEvent.setup();
  renderApp('/courses/11');
  const panel = await screen.findByRole('region', { name: 'Enroll student' });
  return { user, panel };
}

describe('capacity', () => {
  it('shows "enrolled / capacity" for the current semester, and per semester', async () => {
    const { user, panel } = await openAsAdmin();

    expect(within(panel).getByLabelText('Semester')).toHaveValue('2026-Fall');
    expect(within(panel).getByText('2 / 40')).toBeInTheDocument();

    await user.selectOptions(within(panel).getByLabelText('Semester'), '2026-Spring');
    expect(within(panel).getByText('1 / 40')).toBeInTheDocument();

    await user.selectOptions(within(panel).getByLabelText('Semester'), '2027-Spring');
    expect(within(panel).getByText('0 / 40')).toBeInTheDocument();
  });

  it('lists the semesters in calendar order', async () => {
    const { panel } = await openAsAdmin();
    const options = within(within(panel).getByLabelText('Semester'))
      .getAllByRole('option')
      .map((o) => o.textContent);

    expect(options.slice(0, 6)).toEqual([
      '2025-Spring',
      '2025-Summer',
      '2025-Fall',
      '2026-Spring',
      '2026-Summer',
      '2026-Fall',
    ]);
  });

  it('says when the course is full and disables enrolling', async () => {
    vi.mocked(getCourse).mockResolvedValue({ ...course, capacity: 2 });
    const { panel } = await openAsAdmin();

    expect(within(panel).getByText('2 / 2')).toBeInTheDocument();
    expect(within(panel).getByText(/CS101 is full for 2026-Fall/)).toBeInTheDocument();
    await waitFor(() => {
      expect(within(panel).getByRole('button', { name: 'Enroll Dana Fox' })).toBeDisabled();
    });
  });
});

describe('picker', () => {
  it('searches active students only', async () => {
    const { user, panel } = await openAsAdmin();
    await waitFor(() => {
      expect(listStudents).toHaveBeenCalledWith({ search: undefined, status: 'active', limit: 10 });
    });

    await user.type(within(panel).getByLabelText('Search active students'), 'dana');

    await waitFor(() => {
      expect(listStudents).toHaveBeenLastCalledWith({
        search: 'dana',
        status: 'active',
        limit: 10,
      });
    });
  });

  it('marks students already enrolled in the selected semester', async () => {
    const { user, panel } = await openAsAdmin();
    const list = await within(panel).findByRole('list', { name: 'Matching students' });

    // Bo is enrolled for 2026-Fall; Amira only for 2026-Spring.
    expect(within(list).getByText('Bo Diallo').closest('li')).toHaveTextContent('Already enrolled');
    expect(within(list).getByRole('button', { name: 'Enroll Amira Costa' })).toBeEnabled();

    await user.selectOptions(within(panel).getByLabelText('Semester'), '2026-Spring');
    expect(within(list).getByText('Amira Costa').closest('li')).toHaveTextContent(
      'Already enrolled',
    );
    expect(within(list).getByRole('button', { name: 'Enroll Bo Diallo' })).toBeEnabled();
  });

  it('says when no active student matches', async () => {
    vi.mocked(listStudents).mockResolvedValue({ items: [], total: 0 });
    const { panel } = await openAsAdmin();
    expect(
      await within(panel).findByText('No active students match this search.'),
    ).toBeInTheDocument();
  });

  it('enrolls a student for the selected semester and refreshes the roster', async () => {
    vi.mocked(enroll).mockResolvedValue({
      id: 200,
      student_id: 9,
      course_id: 11,
      semester: '2027-Spring',
      grade: null,
      student: { id: 9, student_no: 'CS2026009', first_name: 'Dana', last_name: 'Fox' },
      course: { id: 11, code: 'CS101', title: 'Programming', credits: 4, teacher_id: 2 },
      created_at: '2026-11-24T12:00:00Z',
      updated_at: '2026-11-24T12:00:00Z',
    });
    const { user, panel } = await openAsAdmin();
    await user.selectOptions(within(panel).getByLabelText('Semester'), '2027-Spring');

    await user.click(await within(panel).findByRole('button', { name: 'Enroll Dana Fox' }));

    expect(enroll).toHaveBeenCalledWith({ student_id: 9, course_id: 11, semester: '2027-Spring' });
    expect(await screen.findByRole('status')).toHaveTextContent(
      'Dana Fox enrolled in CS101 for 2027-Spring',
    );
    await waitFor(() => {
      expect(getCourse).toHaveBeenCalledTimes(2); // the roster is reloaded
    });
  });
});

describe('errors are shown clearly', () => {
  it.each([
    ['capacity', 'CS101 is full for 2026-Fall (40 / 40)'],
    ['duplicate', 'Dana Fox (CS2026009) is already enrolled in CS101 for 2026-Fall'],
    ['inactive student', 'Dana Fox (CS2026009) is suspended; only active students can be enrolled'],
  ])('%s: the server message is shown in the panel', async (_kind, message) => {
    vi.mocked(enroll).mockRejectedValue(apiError(409, message));
    const { user, panel } = await openAsAdmin();

    await user.click(await within(panel).findByRole('button', { name: 'Enroll Dana Fox' }));

    expect(await within(panel).findByRole('alert')).toHaveTextContent(message);
    expect(screen.queryByRole('status')).not.toBeInTheDocument(); // no success toast
  });

  it('the message clears when another semester is chosen', async () => {
    vi.mocked(enroll).mockRejectedValue(apiError(409, 'CS101 is full for 2026-Fall (40 / 40)'));
    const { user, panel } = await openAsAdmin();
    await user.click(await within(panel).findByRole('button', { name: 'Enroll Dana Fox' }));
    await within(panel).findByRole('alert');

    await user.selectOptions(within(panel).getByLabelText('Semester'), '2027-Spring');

    expect(within(panel).queryByRole('alert')).not.toBeInTheDocument();
  });
});

describe('unenroll', () => {
  it('asks first, mentioning the grade, then unenrolls', async () => {
    vi.mocked(unenroll).mockResolvedValue(undefined);
    const { user } = await openAsAdmin();

    await user.click(screen.getByRole('button', { name: 'Unenroll Amira Costa (2026-Spring)' }));
    const dialog = screen.getByRole('dialog', { name: 'Unenroll student?' });
    expect(dialog).toHaveTextContent(
      'Amira Costa will be removed from CS101 for 2026-Spring, including their grade (A).',
    );
    expect(unenroll).not.toHaveBeenCalled();
    await user.click(within(dialog).getByRole('button', { name: 'Unenroll' }));

    expect(unenroll).toHaveBeenCalledWith(101);
    expect(await screen.findByRole('status')).toHaveTextContent(
      'Amira Costa unenrolled from CS101 (2026-Spring)',
    );
  });

  it('cancelling keeps the enrollment', async () => {
    const { user } = await openAsAdmin();

    await user.click(screen.getByRole('button', { name: 'Unenroll Bo Diallo (2026-Fall)' }));
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Cancel' }));

    expect(unenroll).not.toHaveBeenCalled();
  });

  it("shows the server's message if unenrolling fails", async () => {
    vi.mocked(unenroll).mockRejectedValue(
      apiError(403, 'You can only unenroll students from courses of the department you head'),
    );
    const { user } = await openAsAdmin();

    await user.click(screen.getByRole('button', { name: 'Unenroll Bo Diallo (2026-Fall)' }));
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Unenroll' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('department you head');
  });
});

describe('who can manage enrollments', () => {
  it.each([
    ['admin', meFor('admin'), true],
    ['HOD of the department', hodOf(3), true],
    ['HOD of another department', hodOf(4), false],
    ["the course's teacher (sees the roster)", meFor('teacher'), false],
  ] as const)('%s: %s', async (_who, me, canManage) => {
    logIn(me);
    if (!canManage && me.role === 'hod')
      vi.mocked(getCourse).mockResolvedValue({ ...course, roster: null });
    renderApp('/courses/11');
    await screen.findByRole('heading', { name: 'CS101 Programming' });

    expect(screen.queryByRole('region', { name: 'Enroll student' }) !== null).toBe(canManage);
    expect(screen.queryAllByRole('button', { name: /^Unenroll/ }).length > 0).toBe(canManage);
  });

  it('students see neither the roster nor the enrollment tools', async () => {
    logIn(meFor('student'));
    vi.mocked(getCourse).mockResolvedValue({ ...course, roster: null });
    renderApp('/courses/11');
    await screen.findByRole('heading', { name: 'CS101 Programming' });

    expect(screen.queryByRole('region', { name: 'Enroll student' })).not.toBeInTheDocument();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });
});
