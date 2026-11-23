import type {
  DepartmentCreate,
  DepartmentDetailOut,
  DepartmentListOut,
  DepartmentOut,
  DepartmentUpdate,
  ListParams,
} from '../types';
import { api } from './client';

export async function listDepartments(params: ListParams = {}): Promise<DepartmentListOut> {
  const { data } = await api.get<DepartmentListOut>('/departments', { params });
  return data;
}

export async function getDepartment(id: number): Promise<DepartmentDetailOut> {
  const { data } = await api.get<DepartmentDetailOut>(`/departments/${id}`);
  return data;
}

export async function createDepartment(body: DepartmentCreate): Promise<DepartmentOut> {
  const { data } = await api.post<DepartmentOut>('/departments', body);
  return data;
}

export async function updateDepartment(id: number, body: DepartmentUpdate): Promise<DepartmentOut> {
  const { data } = await api.patch<DepartmentOut>(`/departments/${id}`, body);
  return data;
}

export async function deleteDepartment(id: number): Promise<void> {
  await api.delete(`/departments/${id}`);
}
