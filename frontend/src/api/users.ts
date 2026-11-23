import type {
  ListParams,
  TemporaryPassword,
  UserCreate,
  UserListOut,
  UserOut,
  UserRole,
  UserUpdate,
} from '../types';
import { api } from './client';

export interface UserFilters extends ListParams {
  role?: UserRole;
  is_active?: boolean;
}

/** Admin only, like every /users endpoint. */
export async function listUsers(params: UserFilters = {}): Promise<UserListOut> {
  const { data } = await api.get<UserListOut>('/users', { params });
  return data;
}

export async function createUser(body: UserCreate): Promise<UserOut> {
  const { data } = await api.post<UserOut>('/users', body);
  return data;
}

export async function updateUser(id: number, body: UserUpdate): Promise<UserOut> {
  const { data } = await api.patch<UserOut>(`/users/${id}`, body);
  return data;
}

/** Returns a new temporary password; it is only shown this once. */
export async function resetPassword(id: number): Promise<TemporaryPassword> {
  const { data } = await api.post<TemporaryPassword>(`/users/${id}/reset-password`);
  return data;
}

export async function deleteUser(id: number): Promise<void> {
  await api.delete(`/users/${id}`);
}
