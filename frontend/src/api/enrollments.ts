import type {
  EnrollmentCreate,
  EnrollmentListOut,
  EnrollmentOut,
  Grade,
  ListParams,
  Semester,
} from '../types';
import { api } from './client';

export interface EnrollmentFilters extends ListParams {
  student_id?: number;
  course_id?: number;
  semester?: Semester;
}

/** Scoped to what the user may see (admin all, HOD/teacher their courses, student own). */
export async function listEnrollments(params: EnrollmentFilters = {}): Promise<EnrollmentListOut> {
  const { data } = await api.get<EnrollmentListOut>('/enrollments', { params });
  return data;
}

export async function enroll(body: EnrollmentCreate): Promise<EnrollmentOut> {
  const { data } = await api.post<EnrollmentOut>('/enrollments', body);
  return data;
}

export async function unenroll(id: number): Promise<void> {
  await api.delete(`/enrollments/${id}`);
}

/** PATCH /enrollments/{id}/grade; `null` clears the grade. */
export async function setGrade(id: number, grade: Grade | null): Promise<EnrollmentOut> {
  const { data } = await api.patch<EnrollmentOut>(`/enrollments/${id}/grade`, { grade });
  return data;
}
