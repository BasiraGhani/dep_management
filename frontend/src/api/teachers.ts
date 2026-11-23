import type {
  ListParams,
  TeacherCreate,
  TeacherDetailOut,
  TeacherListOut,
  TeacherOut,
  TeacherPublicDetailOut,
  TeacherPublicListOut,
  TeacherTitle,
  TeacherUpdate,
} from '../types';
import { api } from './client';

export interface TeacherFilters extends ListParams {
  department_id?: number;
  title?: TeacherTitle;
}

/** Students receive the public shape (no phone, hire date or timestamps). */
export async function listTeachers(
  params: TeacherFilters = {},
): Promise<TeacherListOut | TeacherPublicListOut> {
  const { data } = await api.get<TeacherListOut | TeacherPublicListOut>('/teachers', { params });
  return data;
}

export async function getTeacher(id: number): Promise<TeacherDetailOut | TeacherPublicDetailOut> {
  const { data } = await api.get<TeacherDetailOut | TeacherPublicDetailOut>(`/teachers/${id}`);
  return data;
}

export async function createTeacher(body: TeacherCreate): Promise<TeacherOut> {
  const { data } = await api.post<TeacherOut>('/teachers', body);
  return data;
}

export async function updateTeacher(id: number, body: TeacherUpdate): Promise<TeacherOut> {
  const { data } = await api.patch<TeacherOut>(`/teachers/${id}`, body);
  return data;
}

export async function deleteTeacher(id: number): Promise<void> {
  await api.delete(`/teachers/${id}`);
}
