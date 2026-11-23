import type {
  BulkGradeItem,
  CourseCreate,
  CourseDetailOut,
  CourseListOut,
  CourseOut,
  CourseUpdate,
  EnrollmentOut,
  ListParams,
} from '../types';
import { api } from './client';

export interface CourseFilters extends ListParams {
  department_id?: number;
  teacher_id?: number;
}

export async function listCourses(params: CourseFilters = {}): Promise<CourseListOut> {
  const { data } = await api.get<CourseListOut>('/courses', { params });
  return data;
}

/** `roster` is null for users who may not see this course's enrollments. */
export async function getCourse(id: number): Promise<CourseDetailOut> {
  const { data } = await api.get<CourseDetailOut>(`/courses/${id}`);
  return data;
}

export async function createCourse(body: CourseCreate): Promise<CourseOut> {
  const { data } = await api.post<CourseOut>('/courses', body);
  return data;
}

export async function updateCourse(id: number, body: CourseUpdate): Promise<CourseOut> {
  const { data } = await api.patch<CourseOut>(`/courses/${id}`, body);
  return data;
}

export async function deleteCourse(id: number): Promise<void> {
  await api.delete(`/courses/${id}`);
}

/** PUT /courses/{id}/grades: all-or-nothing bulk grade entry (FR-6.7). */
export async function setCourseGrades(
  courseId: number,
  rows: BulkGradeItem[],
): Promise<EnrollmentOut[]> {
  const { data } = await api.put<EnrollmentOut[]>(`/courses/${courseId}/grades`, rows);
  return data;
}
