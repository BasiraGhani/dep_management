import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { getMe } from '../api/auth';
import { listDepartments } from '../api/departments';
import { createStudent, listStudents } from '../api/students';
import { clearToken, setToken } from '../auth/token';
import { amiraDetail, apiError, csDepartment, kayDetail, meFor } from '../test/fixtures';
import { renderApp } from '../test/render';
import type { CurrentUserOut, DepartmentOut, StudentOut, UserRole } from '../types';

vi.mock('../api/auth', () => ({ login: vi.fn(), getMe: vi.fn(), changePassword: vi.fn() }));
vi.mock('../api/departments');
vi.mock('../api/students');

const math: DepartmentOut = { ...csDepartment, id: 4, code: 'MATH', name: 'Mathematics' };
const rows: StudentOut[] = [
  amiraDetail,
  {
    ...amiraDetail,
    id: 2,
    student_no: 'MATH2026002',
    first_name: 'Bilal',
    last_name: 'Brown',
    department_id: 4,
    year: 3,
    status: 'suspended',
    email: 'bilal@student.uni.example',
  },
];
const hodOfCs: CurrentUserOut = { ...meFor('hod'), teacher: { ...kayDetail, department_id: 3 } };

beforeEach(() => {
  clearToken();
  vi.mocked(listDepartments).mockResolvedValue({ items: [csDepartment, math], total: 2 });
  vi.mocked(listStudents).mockResolvedValue({ items: rows, total: 2 });
});
afterEach(() => {
  vi.clearAllMocks();
});

function logIn(me: CurrentUserOut) {
  setToken('valid.token');
  vi.mocked(getMe).mockResolvedValue(me);
}
const as = (role: UserRole) => {
  logIn(meFor(role));
};

describe('FR-4.1 list, search and filter', () => {
  it('lists students with number, name, department, year, status and email', async () => {
    as('admin');
    renderApp('/students');

    const table = await screen.findByRole('table', { name: 'Students' });
    expect(
      within(table)
        .getAllByRole('columnheader')
        .map((h) => h.textContent),
    ).toEqual(['Student no.', 'Name', 'Department', 'Year', 'Status', 'Email']);
    expect(within(table).getByRole('link', { name: 'CS2026001' })).toHaveAttribute(
      'href',
      '/students/1',
    );
    const bilal = within(table).getByRole('cell', { name: 'Bilal Brown' }).closest('tr');
    expect(bilal).not.toBeNull();
    expect(
      within(bilal as HTMLElement)
        .getAllByRole('cell')
        .map((c) => c.textContent),
    ).toEqual([
      'MATH2026002',
      'Bilal Brown',
      'MATH',
      '3',
      'Suspended',
      'bilal@student.uni.example',
    ]);
  });

  it('searches by name, email or number', async () => {
    as('admin');
    const user = userEvent.setup();
    renderApp('/students');
    await screen.findByRole('table', { name: 'Students' });

    await user.type(screen.getByLabelText('Search students'), 'CS2026');

    await waitFor(() => {
      expect(listStudents).toHaveBeenLastCalledWith(
        expect.objectContaining({ search: 'CS2026', skip: 0 }),
      );
    });
  });

  it('filters by department, year and status from the first page', async () => {
    as('admin');
    const user = userEvent.setup();
    renderApp('/students');
    await screen.findByRole('table', { name: 'Students' });

    await user.selectOptions(screen.getByLabelText('Department'), 'MATH — Mathematics');
    await user.selectOptions(screen.getByLabelText('Year'), 'Year 3');
    await user.selectOptions(screen.getByLabelText('Status'), 'Suspended');

    await waitFor(() => {
      expect(listStudents).toHaveBeenLastCalledWith({
        search: undefined,
        department_id: 4,
        year: 3,
        status: 'suspended',
        skip: 0,
        limit: 20,
      });
    });
  });

  it('says when no student matches', async () => {
    as('admin');
    const user = userEvent.setup();
    renderApp('/students');
    await screen.findByRole('table', { name: 'Students' });
    vi.mocked(listStudents).mockResolvedValue({ items: [], total: 0 });

    await user.selectOptions(screen.getByLabelText('Year'), 'Year 6');

    expect(
      await screen.findByRole('cell', { name: 'No students match these filters.' }),
    ).toBeInTheDocument();
  });

  it('tells teachers the list is limited to their courses and offers no "New student"', async () => {
    as('teacher');
    renderApp('/students');

    expect(
      await screen.findByText('Showing students enrolled in your courses.'),
    ).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'New student' })).not.toBeInTheDocument();
  });

  it.each(['admin', 'hod'] as const)('%s can add students', async (role) => {
    as(role);
    renderApp('/students');
    expect(await screen.findByRole('button', { name: 'New student' })).toBeInTheDocument();
  });
});

describe('FR-4.1–4.3 create (with every FR-4.2 field and an optional account)', () => {
  async function open(me: CurrentUserOut) {
    logIn(me);
    const user = userEvent.setup();
    renderApp('/students');
    await user.click(await screen.findByRole('button', { name: 'New student' }));
    return { user, dialog: screen.getByRole('dialog', { name: 'New student' }) };
  }

  async function fillRequired(user: ReturnType<typeof userEvent.setup>, dialog: HTMLElement) {
    await user.type(within(dialog).getByLabelText(/Student number/), 'CS2026050');
    await user.type(within(dialog).getByLabelText(/First name/), 'Nina');
    await user.type(within(dialog).getByLabelText(/Last name/), 'New');
    await user.type(within(dialog).getByLabelText(/Email/), 'nina@student.uni.example');
  }

  it('creates a student with every field and a login account', async () => {
    vi.mocked(createStudent).mockResolvedValue({ ...amiraDetail, id: 50 });
    const { user, dialog } = await open(meFor('admin'));
    await fillRequired(user, dialog);
    await user.type(within(dialog).getByLabelText('Phone'), '555-0150');
    await user.type(within(dialog).getByLabelText('Date of birth'), '2006-04-12');
    const enrolled = within(dialog).getByLabelText(/Enrollment date/);
    await user.clear(enrolled);
    await user.type(enrolled, '2025-09-01');
    await user.selectOptions(within(dialog).getByLabelText(/Year of study/), 'Year 2');
    await user.selectOptions(within(dialog).getByLabelText(/Status/), 'Withdrawn');
    await user.selectOptions(within(dialog).getByLabelText(/Department/), 'MATH — Mathematics');
    await user.click(within(dialog).getByRole('checkbox', { name: /Create a login account/ }));
    await user.type(within(dialog).getByLabelText(/Username/), 'nina.new');
    await user.type(within(dialog).getByLabelText(/Temporary password/), 'welcome-123');

    await user.click(within(dialog).getByRole('button', { name: 'Add student' }));

    expect(createStudent).toHaveBeenCalledWith({
      student_no: 'CS2026050',
      first_name: 'Nina',
      last_name: 'New',
      email: 'nina@student.uni.example',
      phone: '555-0150',
      date_of_birth: '2006-04-12',
      year: 2,
      status: 'withdrawn',
      enrollment_date: '2025-09-01',
      department_id: 4,
      create_account: { username: 'nina.new', temp_password: 'welcome-123' },
    });
    expect(await screen.findByRole('status')).toHaveTextContent(
      'Nina New added with a login account',
    );
  });

  it('defaults to an active first-year student enrolled today, without an account', async () => {
    vi.mocked(createStudent).mockResolvedValue({ ...amiraDetail, id: 50 });
    const { user, dialog } = await open(meFor('admin'));
    await fillRequired(user, dialog);
    await user.selectOptions(within(dialog).getByLabelText(/Department/), 'CS — Computer Science');

    await user.click(within(dialog).getByRole('button', { name: 'Add student' }));

    expect(createStudent).toHaveBeenCalledWith(
      expect.objectContaining({
        year: 1,
        status: 'active',
        enrollment_date: new Date().toISOString().slice(0, 10),
        phone: null,
        date_of_birth: null,
        create_account: null,
      }),
    );
  });

  it('a HOD can only add students to their own department', async () => {
    vi.mocked(createStudent).mockResolvedValue({ ...amiraDetail, id: 50 });
    const { user, dialog } = await open(hodOfCs);
    const department = within(dialog).getByLabelText(/Department/);
    await waitFor(() => {
      expect(
        within(department)
          .getAllByRole('option')
          .map((o) => o.textContent),
      ).toEqual(['CS — Computer Science']);
    });
    await fillRequired(user, dialog);

    await user.click(within(dialog).getByRole('button', { name: 'Add student' }));

    expect(createStudent).toHaveBeenCalledWith(expect.objectContaining({ department_id: 3 }));
  });

  it('validates before calling the API', async () => {
    const { user, dialog } = await open(meFor('admin'));
    await user.type(within(dialog).getByLabelText(/Student number/), 'CS 01');
    await user.type(within(dialog).getByLabelText('Date of birth'), '2999-01-01');
    await user.click(within(dialog).getByRole('checkbox', { name: /Create a login account/ }));

    await user.click(within(dialog).getByRole('button', { name: 'Add student' }));

    for (const message of [
      'Letters, digits and dashes only',
      'Enter a first name',
      'Enter an email',
      "Can't be in the future",
      'Choose a department',
      '3–50 letters, digits, dots, dashes or underscores',
    ]) {
      expect(await within(dialog).findByText(message)).toBeInTheDocument();
    }
    expect(createStudent).not.toHaveBeenCalled();
  });

  it.each([
    ["Student number 'CS2026050' already exists", /Student number/],
    ["A student with email 'nina@student.uni.example' already exists", /Email/],
  ])('shows the 409 "%s" under its field', async (message, field) => {
    vi.mocked(createStudent).mockRejectedValue(apiError(409, message));
    const { user, dialog } = await open(meFor('admin'));
    await fillRequired(user, dialog);
    await user.selectOptions(within(dialog).getByLabelText(/Department/), 'CS — Computer Science');

    await user.click(within(dialog).getByRole('button', { name: 'Add student' }));

    expect(await within(dialog).findByText(message)).toBeInTheDocument();
    expect(within(dialog).getByLabelText(field)).toHaveAttribute('aria-invalid', 'true');
  });
});
