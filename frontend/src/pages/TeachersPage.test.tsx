import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { getMe } from '../api/auth';
import { listDepartments } from '../api/departments';
import { createTeacher, listTeachers } from '../api/teachers';
import { clearToken, setToken } from '../auth/token';
import { apiError, csDepartment, csTeachers, kayDetail, meFor } from '../test/fixtures';
import { renderApp } from '../test/render';
import type { CurrentUserOut, DepartmentOut, TeacherOut, UserRole } from '../types';

vi.mock('../api/auth', () => ({ login: vi.fn(), getMe: vi.fn(), changePassword: vi.fn() }));
vi.mock('../api/departments');
vi.mock('../api/teachers');

const math: DepartmentOut = { ...csDepartment, id: 4, code: 'MATH', name: 'Mathematics' };
const staffRows: TeacherOut[] = [
  { ...kayDetail },
  {
    ...kayDetail,
    id: 5,
    first_name: 'Grace',
    last_name: 'Hopper',
    title: 'professor',
    email: 'grace@uni.example',
    phone: null,
    department_id: 4,
  },
];

/** The HOD of CS (department 3). */
const hodOfCs: CurrentUserOut = {
  ...meFor('hod'),
  teacher: { ...kayDetail, department_id: 3 },
};

beforeEach(() => {
  clearToken();
  vi.mocked(listDepartments).mockResolvedValue({ items: [csDepartment, math], total: 2 });
  vi.mocked(listTeachers).mockResolvedValue({ items: staffRows, total: 2 });
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

describe('TeachersPage list', () => {
  it('lists teachers for staff, with phone numbers', async () => {
    as('admin');
    renderApp('/teachers');

    const table = await screen.findByRole('table', { name: 'Teachers' });
    expect(
      within(table)
        .getAllByRole('columnheader')
        .map((h) => h.textContent),
    ).toEqual(['Name', 'Title', 'Department', 'Email', 'Phone']);
    expect(within(table).getByRole('link', { name: 'Alan Kay' })).toHaveAttribute(
      'href',
      '/teachers/2',
    );
    expect(within(table).getByRole('cell', { name: 'Associate Professor' })).toBeInTheDocument();
    expect(within(table).getByRole('cell', { name: 'MATH' })).toBeInTheDocument();
    expect(within(table).getByRole('cell', { name: '555-0102' })).toBeInTheDocument();
  });

  it('shows students the public fields only (no phone column)', async () => {
    as('student');
    vi.mocked(listTeachers).mockResolvedValue(csTeachers); // the public shape
    renderApp('/teachers');

    const table = await screen.findByRole('table', { name: 'Teachers' });
    expect(
      within(table)
        .getAllByRole('columnheader')
        .map((h) => h.textContent),
    ).toEqual(['Name', 'Title', 'Department', 'Email']);
  });

  it('filters by department and title from the first page', async () => {
    as('admin');
    const user = userEvent.setup();
    renderApp('/teachers');
    await screen.findByRole('table', { name: 'Teachers' });

    await user.selectOptions(screen.getByLabelText('Department'), 'MATH — Mathematics');
    await user.selectOptions(screen.getByLabelText('Title'), 'Professor');

    await waitFor(() => {
      expect(listTeachers).toHaveBeenLastCalledWith({
        search: undefined,
        department_id: 4,
        title: 'professor',
        skip: 0,
        limit: 20,
      });
    });
  });

  it('says when no teacher matches the filters', async () => {
    as('admin');
    const user = userEvent.setup();
    renderApp('/teachers');
    await screen.findByRole('table', { name: 'Teachers' });
    vi.mocked(listTeachers).mockResolvedValue({ items: [], total: 0 });

    await user.selectOptions(screen.getByLabelText('Title'), 'Lecturer');

    expect(
      await screen.findByRole('cell', { name: 'No teachers match these filters.' }),
    ).toBeInTheDocument();
  });

  it.each([
    ['admin', true],
    ['hod', true],
    ['teacher', false],
    ['student', false],
  ] as const)('"New teacher" for %s: %s', async (role, shown) => {
    as(role);
    renderApp('/teachers');
    await screen.findByRole('table', { name: 'Teachers' });

    expect(screen.queryByRole('button', { name: 'New teacher' }) !== null).toBe(shown);
  });
});

describe('Teacher form (create)', () => {
  async function open(me: CurrentUserOut) {
    logIn(me);
    const user = userEvent.setup();
    renderApp('/teachers');
    await user.click(await screen.findByRole('button', { name: 'New teacher' }));
    return { user, dialog: screen.getByRole('dialog', { name: 'New teacher' }) };
  }

  async function fill(user: ReturnType<typeof userEvent.setup>, dialog: HTMLElement) {
    await user.type(within(dialog).getByLabelText(/First name/), 'Nora');
    await user.type(within(dialog).getByLabelText(/Last name/), 'New');
    await user.type(within(dialog).getByLabelText(/Email/), 'nora@uni.example');
  }

  it('a HOD can only pick their own department', async () => {
    const { dialog } = await open(hodOfCs);

    const department = within(dialog).getByLabelText(/Department/);
    await waitFor(() => {
      expect(
        within(department)
          .getAllByRole('option')
          .map((o) => o.textContent),
      ).toEqual(['CS — Computer Science']);
    });
    expect(department).toHaveValue('3');
    expect(
      within(dialog).getByText(/manage teachers of their own department only/),
    ).toBeInTheDocument();
  });

  it("a HOD's new teacher goes into the HOD's department", async () => {
    vi.mocked(createTeacher).mockResolvedValue({ ...kayDetail, id: 9 });
    const { user, dialog } = await open(hodOfCs);
    await fill(user, dialog);

    await user.click(within(dialog).getByRole('button', { name: 'Add teacher' }));

    expect(createTeacher).toHaveBeenCalledWith(expect.objectContaining({ department_id: 3 }));
  });

  it('an admin picks any department', async () => {
    const { dialog } = await open(meFor('admin'));

    const department = within(dialog).getByLabelText(/Department/);
    await waitFor(() => {
      expect(
        within(department)
          .getAllByRole('option')
          .map((o) => o.textContent),
      ).toEqual(['Choose…', 'CS — Computer Science', 'MATH — Mathematics']);
    });
  });

  it('creates a teacher with a login account', async () => {
    vi.mocked(createTeacher).mockResolvedValue({ ...kayDetail, id: 9 });
    const { user, dialog } = await open(meFor('admin'));
    await fill(user, dialog);
    await user.selectOptions(within(dialog).getByLabelText(/Title/), 'Professor');
    await user.selectOptions(within(dialog).getByLabelText(/Department/), 'MATH — Mathematics');
    await user.type(within(dialog).getByLabelText('Hire date'), '2024-01-15');
    await user.click(within(dialog).getByRole('checkbox', { name: /Create a login account/ }));
    await user.type(within(dialog).getByLabelText(/Username/), 'nora.new');
    await user.type(within(dialog).getByLabelText(/Temporary password/), 'welcome-123');

    await user.click(within(dialog).getByRole('button', { name: 'Add teacher' }));

    expect(createTeacher).toHaveBeenCalledWith({
      first_name: 'Nora',
      last_name: 'New',
      email: 'nora@uni.example',
      phone: null,
      title: 'professor',
      hire_date: '2024-01-15',
      department_id: 4,
      create_account: { username: 'nora.new', temp_password: 'welcome-123' },
    });
    expect(await screen.findByRole('status')).toHaveTextContent(
      'Nora New added with a login account',
    );
  });

  it('sends no account unless asked', async () => {
    vi.mocked(createTeacher).mockResolvedValue({ ...kayDetail, id: 9 });
    const { user, dialog } = await open(meFor('admin'));
    await fill(user, dialog);
    await user.selectOptions(within(dialog).getByLabelText(/Department/), 'CS — Computer Science');

    await user.click(within(dialog).getByRole('button', { name: 'Add teacher' }));

    expect(createTeacher).toHaveBeenCalledWith(expect.objectContaining({ create_account: null }));
    expect(within(dialog).queryByLabelText(/Username/)).not.toBeInTheDocument();
  });

  it('validates the fields and the account section before calling the API', async () => {
    const { user, dialog } = await open(meFor('admin'));
    await user.type(within(dialog).getByLabelText(/Email/), 'not-an-email');
    await user.type(within(dialog).getByLabelText('Hire date'), '2999-01-01');
    await user.click(within(dialog).getByRole('checkbox', { name: /Create a login account/ }));
    await user.type(within(dialog).getByLabelText(/Username/), 'a b');
    await user.type(within(dialog).getByLabelText(/Temporary password/), 'short');

    await user.click(within(dialog).getByRole('button', { name: 'Add teacher' }));

    for (const message of [
      'Enter a first name',
      'Enter a valid email',
      'Choose a department',
      "Can't be in the future",
      '3–50 letters, digits, dots, dashes or underscores',
      'At least 8 characters',
    ]) {
      expect(await within(dialog).findByText(message)).toBeInTheDocument();
    }
    expect(createTeacher).not.toHaveBeenCalled();
  });

  it.each([
    ["A teacher with email 'nora@uni.example' already exists", /Email/],
    ["Username 'nora' is already taken", /Username/],
  ])('shows the 409 "%s" under its field', async (message, field) => {
    vi.mocked(createTeacher).mockRejectedValue(apiError(409, message));
    const { user, dialog } = await open(meFor('admin'));
    await fill(user, dialog);
    await user.selectOptions(within(dialog).getByLabelText(/Department/), 'CS — Computer Science');
    await user.click(within(dialog).getByRole('checkbox', { name: /Create a login account/ }));
    await user.type(within(dialog).getByLabelText(/Username/), 'nora');
    await user.type(within(dialog).getByLabelText(/Temporary password/), 'welcome-123');

    await user.click(within(dialog).getByRole('button', { name: 'Add teacher' }));

    expect(await within(dialog).findByText(message)).toBeInTheDocument();
    expect(within(dialog).getByLabelText(field)).toHaveAttribute('aria-invalid', 'true');
  });
});
