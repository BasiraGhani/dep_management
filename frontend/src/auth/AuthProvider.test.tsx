import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { getMe, login } from '../api/auth';
import { apiError, networkError, teacherMe } from '../test/fixtures';
import { renderApp } from '../test/render';
import { clearToken, getToken, setToken } from './token';

vi.mock('../api/auth', () => ({ login: vi.fn(), getMe: vi.fn(), changePassword: vi.fn() }));

beforeEach(() => {
  clearToken();
});
afterEach(() => {
  vi.clearAllMocks();
});

describe('AuthProvider', () => {
  it('keeps the user logged in after a page refresh (token restored from storage)', async () => {
    setToken('stored.token'); // what a previous session left behind
    vi.mocked(getMe).mockResolvedValue(teacherMe);

    renderApp('/'); // a fresh page load

    expect(await screen.findByRole('heading', { name: 'Welcome, Alan Kay' })).toBeInTheDocument();
    expect(login).not.toHaveBeenCalled();
    expect(getMe).toHaveBeenCalledTimes(1);
  });

  it('shows a loading state while the stored token is checked', () => {
    setToken('stored.token');
    vi.mocked(getMe).mockReturnValue(new Promise(() => undefined));

    renderApp('/');

    expect(screen.getByText('Loading…')).toBeInTheDocument();
  });

  it('sends visitors without a token to the login page', async () => {
    renderApp('/');

    expect(await screen.findByRole('button', { name: 'Sign in' })).toBeInTheDocument();
    expect(getMe).not.toHaveBeenCalled();
  });

  it('treats a stored token the server rejects as logged out', async () => {
    setToken('expired.token');
    vi.mocked(getMe).mockRejectedValue(apiError(401, 'Token has expired'));

    renderApp('/');

    expect(await screen.findByRole('button', { name: 'Sign in' })).toBeInTheDocument();
  });

  it('keeps the token when the server is unreachable, and can retry', async () => {
    setToken('stored.token');
    vi.mocked(getMe).mockRejectedValueOnce(networkError).mockResolvedValueOnce(teacherMe);
    const user = userEvent.setup();

    renderApp('/');

    expect(await screen.findByRole('alert')).toHaveTextContent('Cannot reach the server');
    expect(getToken()).toBe('stored.token');
    await user.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await screen.findByRole('heading', { name: 'Welcome, Alan Kay' })).toBeInTheDocument();
  });

  it('logging out clears the token and returns to the login page (FR-1.4)', async () => {
    setToken('stored.token');
    vi.mocked(getMe).mockResolvedValue(teacherMe);
    const user = userEvent.setup();
    renderApp('/');

    await user.click(await screen.findByRole('button', { name: 'Log out' }));

    expect(await screen.findByRole('button', { name: 'Sign in' })).toBeInTheDocument();
    expect(getToken()).toBeNull();
  });

  it('a visitor sent from / to the login page lands back on / after logging in', async () => {
    vi.mocked(login).mockResolvedValue({ access_token: 'good.token', token_type: 'bearer' });
    vi.mocked(getMe).mockResolvedValue(teacherMe);
    const user = userEvent.setup();
    renderApp('/');

    await user.type(await screen.findByLabelText('Username'), 'demo.teacher');
    await user.type(screen.getByLabelText('Password'), 'demo-password');
    await user.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(await screen.findByRole('heading', { name: 'Welcome, Alan Kay' })).toBeInTheDocument();
  });
});
