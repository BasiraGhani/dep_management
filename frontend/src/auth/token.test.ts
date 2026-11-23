import { afterEach, describe, expect, it, vi } from 'vitest';

import { clearToken, getToken, setToken } from './token';

afterEach(() => {
  clearToken();
  vi.restoreAllMocks();
});

describe('token storage', () => {
  it('stores, reads and clears the token', () => {
    expect(getToken()).toBeNull();
    setToken('a.b.c');
    expect(getToken()).toBe('a.b.c');
    clearToken();
    expect(getToken()).toBeNull();
  });

  it('treats unavailable storage as "no token" instead of crashing', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('SecurityError');
    });
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('QuotaExceededError');
    });
    vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => {
      throw new Error('SecurityError');
    });

    expect(() => {
      setToken('a.b.c');
    }).not.toThrow();
    expect(getToken()).toBeNull();
    expect(() => {
      clearToken();
    }).not.toThrow();
  });
});
