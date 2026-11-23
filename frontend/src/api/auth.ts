import type { ChangePasswordRequest, CurrentUserOut, Token } from '../types';
import { api } from './client';

/** POST /auth/login. The backend expects an OAuth2 password form, not JSON. */
export async function login(username: string, password: string): Promise<Token> {
  const form = new URLSearchParams({ username, password });
  const { data } = await api.post<Token>('/auth/login', form);
  return data;
}

/** GET /auth/me: the logged-in user and their linked teacher or student record. */
export async function getMe(): Promise<CurrentUserOut> {
  const { data } = await api.get<CurrentUserOut>('/auth/me');
  return data;
}

/** POST /auth/change-password (204). */
export async function changePassword(body: ChangePasswordRequest): Promise<void> {
  await api.post('/auth/change-password', body);
}
