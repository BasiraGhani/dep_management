import type {
  ListParams,
  StudentCreate,
  StudentDetailOut,
  StudentListOut,
  StudentOut,
  StudentStatus,
  StudentUpdate,
} from '../types';
import { api } from './client';

export interface StudentFilters extends ListParams {
  department_id?: number;
  year?: number;
  status?: StudentStatus;
}

/** Admin, HOD and teacher only; results are scoped to what the user may see. */
export async function listStudents(params: StudentFilters = {}): Promise<StudentListOut> {
  const { data } = await api.get<StudentListOut>('/students', { params });
  return data;
}

export async function getStudent(id: number): Promise<StudentDetailOut> {
  const { data } = await api.get<StudentDetailOut>(`/students/${id}`);
  return data;
}

export async function createStudent(body: StudentCreate): Promise<StudentOut> {
  const { data } = await api.post<StudentOut>('/students', body);
  return data;
}

export async function updateStudent(id: number, body: StudentUpdate): Promise<StudentOut> {
  const { data } = await api.patch<StudentOut>(`/students/${id}`, body);
  return data;
}

/** Also deletes the student's enrollments; ask the user to confirm first (FR-4.4). */
export async function deleteStudent(id: number): Promise<void> {
  await api.delete(`/students/${id}`);
}
