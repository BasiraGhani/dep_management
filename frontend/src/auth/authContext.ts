import { createContext } from 'react';

import type { CurrentUserOut } from '../types';

/**
 * * loading: a stored token is being checked against /auth/me
 * * authenticated: `user` is set
 * * anonymous: no token, or the server rejected it
 * * error: the server couldn't be reached; the token is kept so a retry can succeed
 */
export type AuthStatus = 'loading' | 'authenticated' | 'anonymous' | 'error';

export interface AuthContextValue {
  status: AuthStatus;
  token: string | null;
  user: CurrentUserOut | null;
  /** Logs in, stores the token and loads the user. Rejects with the API error. */
  login: (username: string, password: string) => Promise<CurrentUserOut>;
  /** Forgets the token and every cached server response (FR-1.4). */
  logout: () => void;
  /** Tries /auth/me again after an `error` status. */
  retry: () => void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);
