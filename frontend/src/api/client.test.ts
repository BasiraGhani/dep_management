import { AxiosError } from 'axios';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { clearToken, getToken, setToken } from '../auth/token';
import { stubApi } from '../test/apiStub';
import { browser } from './browser';
import { DEFAULT_API_URL, api, errorMessage } from './client';

let stub: ReturnType<typeof stubApi> | undefined;

beforeEach(() => {
  clearToken();
  vi.spyOn(browser, 'currentPath').mockReturnValue('/courses');
  vi.spyOn(browser, 'goTo').mockImplementation(() => undefined);
});

afterEach(() => {
  stub?.restore();
  vi.restoreAllMocks();
});

describe('api client', () => {
  it('uses VITE_API_URL or the default base URL', () => {
    expect(api.defaults.baseURL).toBe(import.meta.env.VITE_API_URL || DEFAULT_API_URL);
  });

  it('attaches the bearer token when logged in', async () => {
    setToken('abc.def.ghi');
    stub = stubApi();

    await api.get('/departments');

    expect(stub.calls[0].headers.get('Authorization')).toBe('Bearer abc.def.ghi');
  });

  it('sends no Authorization header when logged out', async () => {
    stub = stubApi();

    await api.get('/departments');

    expect(stub.calls[0].headers.has('Authorization')).toBe(false);
  });

  it('clears the token and redirects to /login on a 401', async () => {
    setToken('expired.token.value');
    stub = stubApi(401, { detail: 'Token has expired' });

    await expect(api.get('/auth/me')).rejects.toBeInstanceOf(AxiosError);

    expect(getToken()).toBeNull();
    expect(browser.goTo).toHaveBeenCalledWith('/login');
  });

  it('does not redirect again when already on the login page', async () => {
    vi.mocked(browser.currentPath).mockReturnValue('/login');
    setToken('expired.token.value');
    stub = stubApi(401, { detail: 'Token has expired' });

    await expect(api.get('/auth/me')).rejects.toBeInstanceOf(AxiosError);

    expect(getToken()).toBeNull();
    expect(browser.goTo).not.toHaveBeenCalled();
  });

  it('leaves a failed login alone so the form can show the error', async () => {
    setToken('still.valid.token');
    stub = stubApi(401, { detail: 'Incorrect username or password' });

    await expect(api.post('/auth/login', new URLSearchParams())).rejects.toBeInstanceOf(AxiosError);

    expect(getToken()).toBe('still.valid.token');
    expect(browser.goTo).not.toHaveBeenCalled();
  });

  it.each([403, 404, 409, 422, 500])('keeps the session on a %i', async (status) => {
    setToken('valid.token.value');
    stub = stubApi(status, { detail: 'Nope' });

    await expect(api.get('/users')).rejects.toBeInstanceOf(AxiosError);

    expect(getToken()).toBe('valid.token.value');
    expect(browser.goTo).not.toHaveBeenCalled();
  });
});

describe('errorMessage', () => {
  async function failure(status: number, data: unknown): Promise<unknown> {
    stub = stubApi(status, data);
    try {
      await api.get('/anything');
    } catch (error) {
      return error;
    } finally {
      stub.restore();
    }
    throw new Error('expected the request to fail');
  }

  it('returns the API message', async () => {
    const error = await failure(409, { detail: 'A1 is full for 2026-Fall (2 / 2)' });
    expect(errorMessage(error)).toBe('A1 is full for 2026-Fall (2 / 2)');
  });

  it('joins field errors from a validation 422', async () => {
    const error = await failure(422, {
      detail: [
        { loc: ['body', 'code'], msg: 'String should have at most 10 characters', type: 'x' },
        { loc: ['body', 'name'], msg: 'Field required', type: 'missing' },
      ],
    });
    expect(errorMessage(error)).toBe('String should have at most 10 characters; Field required');
  });

  it('explains network errors', () => {
    expect(errorMessage(new AxiosError('Network Error', 'ERR_NETWORK'))).toBe(
      'Cannot reach the server. Check your connection.',
    );
  });

  it('falls back for anything else', () => {
    expect(errorMessage(new Error('boom'), 'Could not save')).toBe('Could not save');
  });
});
