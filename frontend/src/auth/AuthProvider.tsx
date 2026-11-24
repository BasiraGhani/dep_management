import { useQueryClient } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import { useCallback, useMemo, useState, type ReactNode } from 'react';

import { getMe, login as apiLogin } from '../api/auth';
import { currentUserKey, useCurrentUserQuery } from '../hooks/useCurrentUser';
import type { CurrentUserOut } from '../types';
import { AuthContext, type AuthContextValue, type AuthStatus } from './authContext';
import { clearToken, getToken, setToken } from './token';

function isUnauthorized(error: unknown): boolean {
  return error instanceof AxiosError && error.response?.status === 401;
}

/**
 * Keeps the access token (persisted in localStorage, so a refresh keeps the user
 * logged in) and the current user loaded from GET /auth/me.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [token, setTokenState] = useState<string | null>(getToken);
  const me = useCurrentUserQuery(token);

  let status: AuthStatus;
  if (token === null) status = 'anonymous';
  else if (me.isSuccess) status = 'authenticated';
  else if (me.isError) status = isUnauthorized(me.error) ? 'anonymous' : 'error';
  else status = 'loading';

  const login = useCallback(
    async (username: string, password: string): Promise<CurrentUserOut> => {
      const { access_token: newToken } = await apiLogin(username, password);
      setToken(newToken);
      try {
        const user = await queryClient.query({
          queryKey: currentUserKey(newToken),
          queryFn: getMe,
        });
        setTokenState(newToken);
        return user;
      } catch (error) {
        clearToken();
        throw error;
      }
    },
    [queryClient],
  );

  const logout = useCallback(() => {
    clearToken();
    setTokenState(null);
    queryClient.clear();
  }, [queryClient]);

  const { refetch } = me;
  const retry = useCallback(() => {
    void refetch();
  }, [refetch]);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      token: status === 'anonymous' ? null : token,
      user: status === 'authenticated' ? (me.data ?? null) : null,
      login,
      logout,
      retry,
    }),
    [status, token, me.data, login, logout, retry],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
