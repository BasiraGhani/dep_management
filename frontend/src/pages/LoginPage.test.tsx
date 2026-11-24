import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { getMe, login } from '../api/auth';
import { clearToken, getToken, setToken } from '../auth/token';
import { apiError, networkError, teacherMe } from '../test/fixtures';
import { renderApp } from '../test/render';

vi.mock('../api/auth', () => ({ login: vi.fn(), getMe: vi.fn(), changePassword: vi.fn() }));

beforeEach(() => {
  clearToken();
});
afterEach(() => {
  vi.clearAllMocks();
});

async function submit(username: string, password: string) {
  const user = userEvent.setup();
  if (username) await user.type(screen.getByLabelText('Username'), username);
  if (password) await user.type(screen.getByLabelText('Password'), password);
  await user.click(screen.getByRole('button', { name: 'Sign in' }));
}

describe('LoginPage', () => {
  it('shows the sign-in form with labelled fields', () => {
    renderApp('/login');

    expect(
      screen.getByRole('heading', { name: /Department Management System/ }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText('Username')).toHaveAttribute('autocomplete', 'username');
    expect(screen.getByLabelText('Password')).toHaveAttribute('type', 'password');
  });

  it('logs in with valid credentials and goes to /', async () => {
    vi.mocked(login).mockResolvedValue({ access_token: 'good.token', token_type: 'bearer' });
    vi.mocked(getMe).mockResolvedValue(teacherMe);
    renderApp('/login');

    await submit('demo.teacher', 'demo-password');

    expect(await screen.findByRole('heading', { name: 'Welcome, Alan Kay' })).toBeInTheDocument();
    expect(login).toHaveBeenCalledWith('demo.teacher', 'demo-password');
    expect(getToken()).toBe('good.token');
  });

  it('shows the API error for invalid credentials and stays on the form', async () => {
    vi.mocked(login).mockRejectedValue(apiError(401, 'Incorrect username or password'));
    renderApp('/login');

    await submit('demo.teacher', 'wrong-password');

    expect(await screen.findByRole('alert')).toHaveTextContent('Incorrect username or password');
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeEnabled();
    expect(getToken()).toBeNull();
    expect(getMe).not.toHaveBeenCalled();
  });

  it('shows the API error for a deactivated account', async () => {
    vi.mocked(login).mockRejectedValue(apiError(403, 'Account is deactivated'));
    renderApp('/login');

    await submit('gone', 'demo-password');

    expect(await screen.findByRole('alert')).toHaveTextContent('Account is deactivated');
  });

  it('shows the wait after too many failed attempts (429)', async () => {
    vi.mocked(login).mockRejectedValue(
      apiError(429, 'Too many failed login attempts. Try again in 15 minute(s).'),
    );
    renderApp('/login');

    await submit('demo.teacher', 'demo-password');

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Too many failed login attempts. Try again in 15 minute(s).',
    );
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeEnabled();
  });

  it('explains when the server cannot be reached', async () => {
    vi.mocked(login).mockRejectedValue(networkError);
    renderApp('/login');

    await submit('demo.teacher', 'demo-password');

    expect(await screen.findByRole('alert')).toHaveTextContent('Cannot reach the server');
  });

  it('validates the fields before calling the API', async () => {
    renderApp('/login');

    await submit('', '');

    expect(await screen.findByText('Enter your username')).toBeInTheDocument();
    expect(screen.getByText('Enter your password')).toBeInTheDocument();
    expect(screen.getByLabelText('Username')).toHaveAttribute('aria-invalid', 'true');
    expect(login).not.toHaveBeenCalled();
  });

  it('treats a username of only spaces as empty', async () => {
    renderApp('/login');

    await submit('   ', 'demo-password');

    expect(await screen.findByText('Enter your username')).toBeInTheDocument();
    expect(login).not.toHaveBeenCalled();
  });

  it('does not keep the token if loading the user fails after login', async () => {
    vi.mocked(login).mockResolvedValue({ access_token: 'good.token', token_type: 'bearer' });
    vi.mocked(getMe).mockRejectedValue(networkError);
    renderApp('/login');

    await submit('demo.teacher', 'demo-password');

    expect(await screen.findByRole('alert')).toHaveTextContent('Cannot reach the server');
    expect(getToken()).toBeNull();
  });

  it('sends a logged-in user straight to /', async () => {
    setToken('good.token');
    vi.mocked(getMe).mockResolvedValue(teacherMe);

    renderApp('/login');

    expect(await screen.findByRole('heading', { name: 'Welcome, Alan Kay' })).toBeInTheDocument();
  });

  it('disables the button while signing in', async () => {
    let finish: (value: { access_token: string; token_type: 'bearer' }) => void = () => undefined;
    vi.mocked(login).mockReturnValue(new Promise((resolve) => (finish = resolve)));
    vi.mocked(getMe).mockResolvedValue(teacherMe);
    renderApp('/login');

    await submit('demo.teacher', 'demo-password');

    expect(screen.getByRole('button', { name: 'Signing in…' })).toBeDisabled();
    finish({ access_token: 'good.token', token_type: 'bearer' });
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Welcome, Alan Kay' })).toBeInTheDocument();
    });
  });
});
