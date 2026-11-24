import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { getMe, login } from './api/auth';
import { getDepartment, listDepartments } from './api/departments';
import { listTeachers } from './api/teachers';
import { browser } from './api/browser';
import { api } from './api/client';
import { clearToken, getToken, setToken } from './auth/token';
import { stubApi } from './test/apiStub';
import { csDepartment, csDepartmentDetail, csTeachers, meFor } from './test/fixtures';
import { renderApp } from './test/render';
import type { UserRole } from './types';

vi.mock('./api/auth', () => ({ login: vi.fn(), getMe: vi.fn(), changePassword: vi.fn() }));
vi.mock('./api/departments');
vi.mock('./api/teachers');

/**
 * ARCHITECTURE §4, copied here on purpose (not imported from auth/access.ts), so a
 * mistake in the app's table can't hide behind the same mistake in the test.
 */
const ROUTES: [path: string, heading: string, roles: UserRole[]][] = [
  ['/', 'Welcome', ['admin', 'hod', 'teacher', 'student']],
  ['/departments', 'Departments', ['admin', 'hod', 'teacher', 'student']],
  ['/departments/3', 'Computer Science', ['admin', 'hod', 'teacher', 'student']],
  ['/teachers', 'Teachers', ['admin', 'hod', 'teacher', 'student']],
  ['/teachers/3', 'Teacher #3', ['admin', 'hod', 'teacher', 'student']],
  ['/students', 'Students', ['admin', 'hod', 'teacher']],
  ['/students/3', 'Student #3', ['admin', 'hod', 'teacher']],
  ['/courses', 'Courses', ['admin', 'hod', 'teacher', 'student']],
  ['/courses/3', 'Course #3', ['admin', 'hod', 'teacher', 'student']],
  ['/courses/3/grades', 'Grade entry #3', ['admin', 'hod', 'teacher']],
  ['/users', 'User management', ['admin']],
  ['/profile', 'My profile', ['admin', 'hod', 'teacher', 'student']],
];
const ROLES: UserRole[] = ['admin', 'hod', 'teacher', 'student'];

beforeEach(() => {
  clearToken();
  vi.mocked(listDepartments).mockResolvedValue({ items: [csDepartment], total: 1 });
  vi.mocked(getDepartment).mockResolvedValue(csDepartmentDetail);
  vi.mocked(listTeachers).mockResolvedValue(csTeachers);
});
afterEach(() => {
  vi.restoreAllMocks();
  vi.clearAllMocks();
});

function logInAs(role: UserRole) {
  setToken('valid.token');
  vi.mocked(getMe).mockResolvedValue(meFor(role));
}

describe('ProtectedRoute', () => {
  it.each(ROUTES.map(([path]) => path))(
    'sends a logged-out visitor from %s to /login',
    async (path) => {
      renderApp(path);

      expect(await screen.findByRole('button', { name: 'Sign in' })).toBeInTheDocument();
      expect(getMe).not.toHaveBeenCalled();
    },
  );

  it('returns the visitor to the page they asked for after logging in', async () => {
    vi.mocked(login).mockResolvedValue({ access_token: 'good.token', token_type: 'bearer' });
    vi.mocked(getMe).mockResolvedValue(meFor('teacher'));
    const user = userEvent.setup();
    renderApp('/courses/7');

    await user.type(await screen.findByLabelText('Username'), 'demo.teacher');
    await user.type(screen.getByLabelText('Password'), 'demo-password');
    await user.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(await screen.findByRole('heading', { name: 'Course #7' })).toBeInTheDocument();
  });

  it('shows a loading state while the stored token is being checked', () => {
    setToken('valid.token');
    vi.mocked(getMe).mockReturnValue(new Promise(() => undefined));

    renderApp('/courses');

    expect(screen.getByRole('status')).toHaveTextContent('Loading…');
  });
});

describe('RoleGate', () => {
  it('shows "Not authorized" to a student visiting /users', async () => {
    logInAs('student');

    renderApp('/users');

    expect(await screen.findByRole('heading', { name: 'Not authorized' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'User management' })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Go to the dashboard' })).toHaveAttribute('href', '/');
  });

  const cases = ROUTES.flatMap(([path, heading, allowed]) =>
    ROLES.map((role) => ({ path, heading, role, allowed: allowed.includes(role) })),
  );

  it.each(cases)('$role on $path: allowed=$allowed', async ({ path, heading, role, allowed }) => {
    logInAs(role);

    renderApp(path);

    if (allowed) {
      expect(
        await screen.findByRole('heading', { name: new RegExp(`^${heading}`) }),
      ).toBeInTheDocument();
      expect(screen.queryByText('Not authorized')).not.toBeInTheDocument();
    } else {
      expect(await screen.findByRole('heading', { name: 'Not authorized' })).toBeInTheDocument();
    }
  });
});

describe('404', () => {
  it.each(['/nope', '/departments/3/edit/extra', '/departmentsx'])(
    'shows "Page not found" at %s',
    async (path) => {
      logInAs('admin');

      renderApp(path);

      expect(await screen.findByRole('heading', { name: 'Page not found' })).toBeInTheDocument();
    },
  );
});

describe('session expiry', () => {
  it('a 401 on any request returns the user to the login page through the router', async () => {
    logInAs('teacher');
    vi.spyOn(browser, 'goTo').mockImplementation(() => undefined);
    renderApp('/courses');
    expect(await screen.findByRole('heading', { name: 'Courses' })).toBeInTheDocument();
    const stub = stubApi(401, { detail: 'Token has expired' });

    await expect(api.get('/courses')).rejects.toThrow();

    expect(await screen.findByRole('button', { name: 'Sign in' })).toBeInTheDocument();
    expect(getToken()).toBeNull();
    expect(browser.goTo).not.toHaveBeenCalled(); // no full page reload
    stub.restore();
  });
});
