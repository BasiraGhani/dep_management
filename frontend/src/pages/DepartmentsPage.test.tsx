import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { getMe } from '../api/auth';
import { createDepartment, listDepartments } from '../api/departments';
import { listTeachers } from '../api/teachers';
import { clearToken, setToken } from '../auth/token';
import { apiError, csDepartment, csTeachers, meFor, networkError } from '../test/fixtures';
import { renderApp } from '../test/render';
import type { DepartmentOut, UserRole } from '../types';

vi.mock('../api/auth', () => ({ login: vi.fn(), getMe: vi.fn(), changePassword: vi.fn() }));
vi.mock('../api/departments');
vi.mock('../api/teachers');

const math: DepartmentOut = {
  ...csDepartment,
  id: 4,
  code: 'MATH',
  name: 'Mathematics',
  building: null,
  phone: null,
};

function page(items: DepartmentOut[], total = items.length) {
  return { items, total };
}

beforeEach(() => {
  clearToken();
  vi.mocked(listDepartments).mockResolvedValue(page([csDepartment, math]));
  vi.mocked(listTeachers).mockResolvedValue(csTeachers);
});
afterEach(() => {
  vi.clearAllMocks();
});

function logInAs(role: UserRole) {
  setToken('valid.token');
  vi.mocked(getMe).mockResolvedValue(meFor(role));
}

describe('DepartmentsPage list', () => {
  it('lists departments with links to their pages', async () => {
    logInAs('student');
    renderApp('/departments');

    const table = await screen.findByRole('table', { name: 'Departments' });
    expect(within(table).getByRole('link', { name: 'CS' })).toHaveAttribute(
      'href',
      '/departments/3',
    );
    expect(within(table).getByRole('cell', { name: 'Mathematics' })).toBeInTheDocument();
    expect(within(table).getByRole('cell', { name: 'Turing Hall' })).toBeInTheDocument();
    expect(within(table).getAllByRole('cell', { name: '—' })).toHaveLength(2); // MATH has no building/phone
    expect(listDepartments).toHaveBeenCalledWith({ search: undefined, skip: 0, limit: 20 });
  });

  it('shows a loading state, then the table', async () => {
    logInAs('admin');
    let resolve: (value: ReturnType<typeof page>) => void = () => undefined;
    vi.mocked(listDepartments).mockReturnValue(new Promise((r) => (resolve = r)));
    renderApp('/departments');

    expect(await screen.findByText('Loading departments…')).toBeInTheDocument();
    resolve(page([csDepartment]));
    expect(await screen.findByRole('table', { name: 'Departments' })).toBeInTheDocument();
  });

  it('shows an error with a retry', async () => {
    logInAs('admin');
    vi.mocked(listDepartments)
      .mockRejectedValueOnce(networkError)
      .mockResolvedValueOnce(page([math]));
    const user = userEvent.setup();
    renderApp('/departments');

    expect(await screen.findByRole('alert')).toHaveTextContent('Cannot reach the server');
    await user.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await screen.findByRole('link', { name: 'MATH' })).toBeInTheDocument();
  });

  it('shows an empty state', async () => {
    logInAs('admin');
    vi.mocked(listDepartments).mockResolvedValue(page([]));
    renderApp('/departments');

    expect(await screen.findByRole('cell', { name: 'No departments yet.' })).toBeInTheDocument();
  });

  it('searches (debounced) from the first page and says when nothing matches', async () => {
    logInAs('admin');
    const user = userEvent.setup();
    renderApp('/departments');
    await screen.findByRole('link', { name: 'CS' });
    vi.mocked(listDepartments).mockResolvedValue(page([]));

    await user.type(screen.getByLabelText('Search departments'), 'phys');

    await waitFor(() => {
      expect(listDepartments).toHaveBeenLastCalledWith({ search: 'phys', skip: 0, limit: 20 });
    });
    expect(
      await screen.findByRole('cell', { name: 'No departments match "phys".' }),
    ).toBeInTheDocument();
    expect(listDepartments).not.toHaveBeenCalledWith(expect.objectContaining({ search: 'p' }));
  });

  it('pages through results', async () => {
    logInAs('admin');
    vi.mocked(listDepartments).mockResolvedValue(page([csDepartment], 45));
    const user = userEvent.setup();
    renderApp('/departments');

    expect(await screen.findByText('Showing 1–1 of 45')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Next' }));

    await waitFor(() => {
      expect(listDepartments).toHaveBeenLastCalledWith({ search: undefined, skip: 20, limit: 20 });
    });
  });

  it.each(['hod', 'teacher', 'student'] as const)(
    'hides "New department" from %s',
    async (role) => {
      logInAs(role);
      renderApp('/departments');

      await screen.findByRole('table', { name: 'Departments' });
      expect(screen.queryByRole('button', { name: 'New department' })).not.toBeInTheDocument();
    },
  );
});

describe('Department form (create)', () => {
  async function openForm() {
    logInAs('admin');
    const user = userEvent.setup();
    renderApp('/departments');
    await user.click(await screen.findByRole('button', { name: 'New department' }));
    const dialog = screen.getByRole('dialog', { name: 'New department' });
    return { user, dialog };
  }

  it('creates a department, shows a toast and refreshes the list', async () => {
    vi.mocked(createDepartment).mockResolvedValue({
      ...csDepartment,
      id: 9,
      code: 'EE',
      name: 'Electrical',
    });
    const { user, dialog } = await openForm();

    await user.type(within(dialog).getByLabelText(/Code/), ' ee ');
    await user.type(within(dialog).getByLabelText(/^Name/), 'Electrical');
    await user.type(within(dialog).getByLabelText('Building'), 'Volta Hall');
    await user.click(within(dialog).getByRole('button', { name: 'Create department' }));

    expect(createDepartment).toHaveBeenCalledWith({
      code: 'ee',
      name: 'Electrical',
      description: null,
      building: 'Volta Hall',
      phone: null,
    });
    expect(await screen.findByRole('status')).toHaveTextContent('Department EE created');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    await waitFor(() => {
      expect(listDepartments).toHaveBeenCalledTimes(2); // refetched after the change
    });
  });

  it('has no head field on create (a head must already be in the department)', async () => {
    const { dialog } = await openForm();
    expect(within(dialog).queryByLabelText(/Head of department/)).not.toBeInTheDocument();
  });

  it('validates before calling the API', async () => {
    const { user, dialog } = await openForm();

    await user.type(within(dialog).getByLabelText(/Code/), 'C-S');
    await user.type(within(dialog).getByLabelText('Phone'), 'call me');
    await user.click(within(dialog).getByRole('button', { name: 'Create department' }));

    expect(await within(dialog).findByText('Letters and digits only')).toBeInTheDocument();
    expect(within(dialog).getByText('Enter a name')).toBeInTheDocument();
    expect(within(dialog).getByText('Digits, spaces, + ( ) - only')).toBeInTheDocument();
    expect(createDepartment).not.toHaveBeenCalled();
  });

  it('shows a duplicate-code 409 under the code field', async () => {
    vi.mocked(createDepartment).mockRejectedValue(
      apiError(409, "A department with code 'CS' already exists"),
    );
    const { user, dialog } = await openForm();

    await user.type(within(dialog).getByLabelText(/Code/), 'cs');
    await user.type(within(dialog).getByLabelText(/^Name/), 'Another');
    await user.click(within(dialog).getByRole('button', { name: 'Create department' }));

    expect(
      await within(dialog).findByText("A department with code 'CS' already exists"),
    ).toBeInTheDocument();
    expect(within(dialog).getByLabelText(/Code/)).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByRole('dialog')).toBeInTheDocument(); // stays open to fix it
  });

  it('shows other server errors at the top of the form', async () => {
    vi.mocked(createDepartment).mockRejectedValue(networkError);
    const { user, dialog } = await openForm();

    await user.type(within(dialog).getByLabelText(/Code/), 'EE');
    await user.type(within(dialog).getByLabelText(/^Name/), 'Electrical');
    await user.click(within(dialog).getByRole('button', { name: 'Create department' }));

    expect(await within(dialog).findByRole('alert')).toHaveTextContent('Cannot reach the server');
  });

  it('Cancel closes the form without saving', async () => {
    const { user, dialog } = await openForm();

    await user.type(within(dialog).getByLabelText(/Code/), 'EE');
    await user.click(within(dialog).getByRole('button', { name: 'Cancel' }));

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(createDepartment).not.toHaveBeenCalled();
  });
});
