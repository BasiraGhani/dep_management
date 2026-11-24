import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { getMe } from '../api/auth';
import { getCourse, setCourseGrades } from '../api/courses';
import { getDepartment, listDepartments } from '../api/departments';
import { listStudents } from '../api/students';
import { listTeachers } from '../api/teachers';
import { clearToken, setToken } from '../auth/token';
import {
  apiError,
  cs101Detail,
  csDepartment,
  csDepartmentDetail,
  csTeachers,
  kayDetail,
  meFor,
} from '../test/fixtures';
import { renderApp } from '../test/render';
import type { CourseDetailOut, CurrentUserOut, EnrollmentOut } from '../types';

vi.mock('../api/auth', () => ({ login: vi.fn(), getMe: vi.fn(), changePassword: vi.fn() }));
vi.mock('../api/courses');
vi.mock('../api/departments');
vi.mock('../api/teachers');
vi.mock('../api/students');
vi.mock('../api/enrollments');

/** CS101 (teacher 2, department 3): Bo (ungraded) and Cy (B) in 2026-Fall, Amira (A) in 2026-Spring. */
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
      grade: 'B',
    },
  ],
};
const savedRows: EnrollmentOut[] = [];
const hodOf = (departmentId: number): CurrentUserOut => ({
  ...meFor('hod'),
  teacher_id: 50,
  teacher: { ...kayDetail, id: 50, department_id: departmentId },
}); // the page only uses the response to know it succeeded

beforeEach(() => {
  clearToken();
  vi.mocked(getCourse).mockResolvedValue(course);
  vi.mocked(setCourseGrades).mockResolvedValue(savedRows);
  vi.mocked(getDepartment).mockResolvedValue(csDepartmentDetail);
  vi.mocked(listDepartments).mockResolvedValue({ items: [csDepartment], total: 1 });
  vi.mocked(listTeachers).mockResolvedValue(csTeachers);
  vi.mocked(listStudents).mockResolvedValue({ items: [], total: 0 });
});
afterEach(() => {
  vi.clearAllMocks();
});

async function open(me: CurrentUserOut = meFor('teacher')) {
  setToken('valid.token');
  vi.mocked(getMe).mockResolvedValue(me);
  const user = userEvent.setup();
  renderApp('/courses/11/grades');
  await screen.findByRole('heading', { name: 'Grades: CS101 Programming' });
  return user;
}
const gradeBox = (name: string, semester: string) =>
  screen.getByRole('combobox', { name: `Grade for ${name} (${semester})` });
const shownNames = () =>
  within(screen.getByRole('table'))
    .getAllByRole('row')
    .slice(1)
    .map((row) => within(row).getAllByRole('cell')[1].textContent);

describe('table and semester filter', () => {
  it('starts on the newest semester, with each saved grade selected', async () => {
    await open();

    expect(screen.getByLabelText('Semester')).toHaveValue('2026-Fall');
    expect(shownNames()).toEqual(['Bo Diallo', 'Cy Evans']);
    expect(gradeBox('Bo Diallo', '2026-Fall')).toHaveValue('');
    expect(gradeBox('Cy Evans', '2026-Fall')).toHaveValue('B');
    expect(screen.getByText('2 students · 1 not graded')).toBeInTheDocument();
  });

  it('filters by semester, or shows all', async () => {
    const user = await open();

    await user.selectOptions(screen.getByLabelText('Semester'), '2026-Spring');
    expect(shownNames()).toEqual(['Amira Costa']);
    expect(gradeBox('Amira Costa', '2026-Spring')).toHaveValue('A');

    await user.selectOptions(screen.getByLabelText('Semester'), 'All semesters');
    expect(shownNames()).toEqual(['Amira Costa', 'Bo Diallo', 'Cy Evans']);
  });

  it('offers "Not graded" and the ten letter grades, best first', async () => {
    await open();
    const options = within(gradeBox('Bo Diallo', '2026-Fall'))
      .getAllByRole('option')
      .map((o) => o.textContent);
    expect(options).toEqual(['Not graded', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D', 'F']);
  });

  it('says when nobody is enrolled', async () => {
    vi.mocked(getCourse).mockResolvedValue({ ...course, roster: [] });
    await open();
    expect(screen.getByText(/No students are enrolled in CS101 yet/)).toBeInTheDocument();
  });
});

describe('Save all (FR-6.7)', () => {
  it('sends only the changed rows, from every semester, in one request', async () => {
    const user = await open();
    expect(screen.getByRole('button', { name: 'Save all' })).toBeDisabled();

    await user.selectOptions(gradeBox('Bo Diallo', '2026-Fall'), 'A-');
    await user.selectOptions(screen.getByLabelText('Semester'), '2026-Spring');
    await user.selectOptions(gradeBox('Amira Costa', '2026-Spring'), ''); // clear the grade
    expect(screen.getByText('2 unsaved changes')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Save all' }));

    expect(setCourseGrades).toHaveBeenCalledTimes(1);
    expect(setCourseGrades).toHaveBeenCalledWith(11, [
      { enrollment_id: 101, grade: null },
      { enrollment_id: 103, grade: 'A-' },
    ]);
    expect(await screen.findByRole('status')).toHaveTextContent('Saved 2 grades for CS101');
    expect(screen.getByText('No unsaved changes')).toBeInTheDocument();
    await waitFor(() => {
      expect(getCourse).toHaveBeenCalledTimes(2); // reloaded with the saved grades
    });
  });

  it('changing a grade back to the saved one is not a change', async () => {
    const user = await open();

    await user.selectOptions(gradeBox('Cy Evans', '2026-Fall'), 'C');
    expect(screen.getByText('1 unsaved change')).toBeInTheDocument();
    expect(
      within(gradeBox('Cy Evans', '2026-Fall').closest('td') as HTMLElement).getByText('Unsaved'),
    ).toBeInTheDocument();
    await user.selectOptions(gradeBox('Cy Evans', '2026-Fall'), 'B');

    expect(screen.getByText('No unsaved changes')).toBeInTheDocument();
    expect(screen.queryByText('Unsaved')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Save all' })).toBeDisabled();
  });

  it('Discard changes puts the saved grades back', async () => {
    const user = await open();
    await user.selectOptions(gradeBox('Bo Diallo', '2026-Fall'), 'F');

    await user.click(screen.getByRole('button', { name: 'Discard changes' }));

    expect(gradeBox('Bo Diallo', '2026-Fall')).toHaveValue('');
    expect(setCourseGrades).not.toHaveBeenCalled();
  });

  it("a failed save shows the server's message and keeps the user's edits", async () => {
    vi.mocked(setCourseGrades).mockRejectedValueOnce(
      apiError(422, 'Not enrollments of course CS101: 103. No grades were changed.'),
    );
    const user = await open();
    await user.selectOptions(gradeBox('Bo Diallo', '2026-Fall'), 'A');
    await user.selectOptions(gradeBox('Cy Evans', '2026-Fall'), 'B+');

    await user.click(screen.getByRole('button', { name: 'Save all' }));

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(
      'Not enrollments of course CS101: 103. No grades were changed.',
    );
    expect(alert).toHaveTextContent('they are still here');
    expect(gradeBox('Bo Diallo', '2026-Fall')).toHaveValue('A');
    expect(gradeBox('Cy Evans', '2026-Fall')).toHaveValue('B+');
    expect(screen.getByText('2 unsaved changes')).toBeInTheDocument();

    // Trying again sends the same edits.
    await user.click(screen.getByRole('button', { name: 'Save all' }));
    expect(setCourseGrades).toHaveBeenLastCalledWith(11, [
      { enrollment_id: 103, grade: 'A' },
      { enrollment_id: 104, grade: 'B+' },
    ]);
    expect(await screen.findByRole('status')).toHaveTextContent('Saved 2 grades');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});

describe('leaving with unsaved changes', () => {
  it('asks before leaving; Cancel stays with the edits, Leave goes', async () => {
    const user = await open();
    await user.selectOptions(gradeBox('Bo Diallo', '2026-Fall'), 'C+');

    await user.click(screen.getByRole('link', { name: '← CS101 Programming' }));
    const dialog = screen.getByRole('dialog', { name: 'Leave without saving?' });
    expect(dialog).toHaveTextContent('You have 1 unsaved grade change.');
    await user.click(within(dialog).getByRole('button', { name: 'Cancel' }));

    expect(screen.getByRole('heading', { name: 'Grades: CS101 Programming' })).toBeInTheDocument();
    expect(gradeBox('Bo Diallo', '2026-Fall')).toHaveValue('C+');

    await user.click(screen.getByRole('link', { name: 'Dashboard' }));
    await user.click(screen.getByRole('button', { name: 'Leave without saving' }));

    expect(await screen.findByText('Teacher dashboard')).toBeInTheDocument();
    expect(setCourseGrades).not.toHaveBeenCalled();
  });

  it('leaves without asking when nothing is unsaved', async () => {
    const user = await open();

    await user.click(screen.getByRole('link', { name: '← CS101 Programming' }));

    expect(await screen.findByRole('heading', { name: 'CS101 Programming' })).toBeInTheDocument();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('asks the browser to confirm a reload or tab close only while changes are unsaved', async () => {
    const user = await open();
    const unload = () => {
      const event = new Event('beforeunload', { cancelable: true });
      window.dispatchEvent(event);
      return event.defaultPrevented;
    };
    expect(unload()).toBe(false);

    await user.selectOptions(gradeBox('Bo Diallo', '2026-Fall'), 'D');
    expect(unload()).toBe(true);

    await user.click(screen.getByRole('button', { name: 'Save all' }));
    await screen.findByRole('status');
    expect(unload()).toBe(false);
  });
});

describe('who may enter grades', () => {
  it.each([
    ['admin', meFor('admin')],
    ["the course's teacher", meFor('teacher')],
    ['HOD of the department', hodOf(3)],
  ] as const)('%s gets the table', async (_who, me) => {
    await open(me);
    expect(screen.getByRole('button', { name: 'Save all' })).toBeInTheDocument();
  });

  it('a teacher of another course gets an explanation, not the table', async () => {
    vi.mocked(getCourse).mockResolvedValue({ ...course, teacher_id: 99 });
    await open(meFor('teacher'));
    expect(screen.getByText(/You can only enter grades for courses you teach/)).toBeInTheDocument();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });

  it('a HOD of another department gets an explanation', async () => {
    vi.mocked(getCourse).mockResolvedValue({ ...course, roster: null });
    await open(meFor('hod'));
    expect(screen.getByText(/You can only enter grades for courses you teach/)).toBeInTheDocument();
  });

  it('the course page links to grade entry for those who can grade', async () => {
    setToken('valid.token');
    vi.mocked(getMe).mockResolvedValue(meFor('teacher'));
    renderApp('/courses/11');
    expect(await screen.findByRole('link', { name: 'Enter grades' })).toHaveAttribute(
      'href',
      '/courses/11/grades',
    );
  });

  it('the course page has no grade link for students', async () => {
    vi.mocked(getCourse).mockResolvedValue({ ...course, roster: null });
    setToken('valid.token');
    vi.mocked(getMe).mockResolvedValue(meFor('student'));
    renderApp('/courses/11');
    await screen.findByRole('heading', { name: 'CS101 Programming' });
    expect(screen.queryByRole('link', { name: 'Enter grades' })).not.toBeInTheDocument();
  });
});
