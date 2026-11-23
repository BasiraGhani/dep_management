import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import App from './App';
import { clearToken } from './auth/token';

vi.mock('./api/auth', () => ({ login: vi.fn(), getMe: vi.fn(), changePassword: vi.fn() }));

beforeEach(() => {
  clearToken();
  window.history.pushState({}, '', '/');
});

describe('App', () => {
  it('starts at the login page when nobody is logged in', async () => {
    render(<App />);

    expect(await screen.findByRole('button', { name: 'Sign in' })).toBeInTheDocument();
    expect(window.location.pathname).toBe('/login');
  });
});
