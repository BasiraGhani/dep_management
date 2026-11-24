import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { getMe } from '../api/auth';
import { clearToken, getToken, setToken } from '../auth/token';
import { meFor } from '../test/fixtures';
import { renderApp } from '../test/render';
import type { UserRole } from '../types';

vi.mock('../api/auth', () => ({ login: vi.fn(), getMe: vi.fn(), changePassword: vi.fn() }));

/** ARCHITECTURE §4 as a sidebar, written out here independently of the app's table. */
const EXPECTED_MENU: Record<UserRole, string[]> = {
  admin: ['Dashboard', 'Departments', 'Teachers', 'Students', 'Courses', 'Users', 'My profile'],
  hod: ['Dashboard', 'Departments', 'Teachers', 'Students', 'Courses', 'My profile'],
  teacher: ['Dashboard', 'Departments', 'Teachers', 'Students', 'Courses', 'My profile'],
  student: ['Dashboard', 'Departments', 'Teachers', 'Courses', 'My profile'],
};

beforeEach(() => {
  clearToken();
});
afterEach(() => {
  vi.clearAllMocks();
});

function logInAs(role: UserRole) {
  setToken('valid.token');
  vi.mocked(getMe).mockResolvedValue(meFor(role));
}

async function menu() {
  const nav = await screen.findByRole('navigation', { name: 'Main' });
  return within(nav).getAllByRole('link');
}

describe('Layout', () => {
  it.each(Object.entries(EXPECTED_MENU))(
    'sidebar for %s matches the §4 role table',
    async (role, expected) => {
      logInAs(role as UserRole);
      renderApp('/');

      expect((await menu()).map((link) => link.textContent)).toEqual(expected);
    },
  );

  it('every sidebar link opens a page the role may see (no "Not authorized")', async () => {
    for (const role of Object.keys(EXPECTED_MENU) as UserRole[]) {
      logInAs(role);
      const view = renderApp('/');
      const links = await menu();
      const user = userEvent.setup();
      for (const link of links) {
        await user.click(link);
        expect(screen.queryByRole('heading', { name: 'Not authorized' })).not.toBeInTheDocument();
      }
      view.unmount();
    }
  });

  it('links point to the §4 routes', async () => {
    logInAs('admin');
    renderApp('/');

    expect((await menu()).map((link) => link.getAttribute('href'))).toEqual([
      '/',
      '/departments',
      '/teachers',
      '/students',
      '/courses',
      '/users',
      '/profile',
    ]);
  });

  it('marks the current page in the sidebar', async () => {
    logInAs('teacher');
    renderApp('/courses/4');

    const courses = (await menu()).find((link) => link.textContent === 'Courses');
    expect(courses).toHaveAttribute('aria-current', 'page');
    const dashboard = (await menu()).find((link) => link.textContent === 'Dashboard');
    expect(dashboard).not.toHaveAttribute('aria-current');
  });

  it.each([
    ['admin', 'demo.admin', 'Administrator'],
    ['hod', 'Alan Kay', 'Head of department'],
    ['teacher', 'Alan Kay', 'Teacher'],
    ['student', 'Amira Costa', 'Student'],
  ] as const)('top bar shows the %s user name and role', async (role, name, label) => {
    logInAs(role);
    renderApp('/');

    const header = await screen.findByRole('banner');
    expect(within(header).getByText(name)).toBeInTheDocument();
    expect(within(header).getByText(label)).toBeInTheDocument();
  });

  it('logs out from the top bar', async () => {
    logInAs('teacher');
    const user = userEvent.setup();
    renderApp('/courses');

    await user.click(
      within(await screen.findByRole('banner')).getByRole('button', { name: 'Log out' }),
    );

    expect(await screen.findByRole('button', { name: 'Sign in' })).toBeInTheDocument();
    expect(getToken()).toBeNull();
  });

  it('the Menu button toggles the sidebar on small screens', async () => {
    logInAs('student');
    const user = userEvent.setup();
    renderApp('/');

    const toggle = await screen.findByRole('button', { name: 'Menu' });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    await user.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
  });

  it('shows "Not authorized" inside the layout, keeping the sidebar', async () => {
    logInAs('student');
    renderApp('/users');

    expect(await screen.findByRole('heading', { name: 'Not authorized' })).toBeInTheDocument();
    expect(await menu()).toHaveLength(5);
  });
});
