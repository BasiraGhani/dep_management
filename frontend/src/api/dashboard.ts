import type { Dashboard } from '../types';
import { api } from './client';

/** GET /dashboard: the payload's `role` says which shape it is. */
export async function getDashboard(): Promise<Dashboard> {
  const { data } = await api.get<Dashboard>('/dashboard');
  return data;
}
