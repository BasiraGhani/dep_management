import { useContext } from 'react';

import { AuthContext, type AuthContextValue } from './authContext';

/** The auth state and actions. Must be used inside `<AuthProvider>`. */
export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (value === null) {
    throw new Error('useAuth() must be used inside <AuthProvider>');
  }
  return value;
}
