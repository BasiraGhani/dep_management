/**
 * Access-token storage (localStorage, so a page refresh keeps the user logged in).
 * Storage can be unavailable (private mode, blocked site data), so every access is
 * guarded and failures simply mean "no token".
 */

const TOKEN_KEY = 'dept.accessToken';

export function getToken(): string | null {
  try {
    return window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string): void {
  try {
    window.localStorage.setItem(TOKEN_KEY, token);
  } catch {
    // Without storage the user stays logged in only until the page reloads.
  }
}

export function clearToken(): void {
  try {
    window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    // Nothing stored, nothing to clear.
  }
}
