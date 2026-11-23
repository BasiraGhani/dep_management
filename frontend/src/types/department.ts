import type { CourseBrief, IsoDateTime, Page, TeacherBrief } from './common';

export interface DepartmentOut {
  id: number;
  code: string;
  name: string;
  description: string | null;
  building: string | null;
  phone: string | null;
  head_id: number | null;
  created_at: IsoDateTime;
  updated_at: IsoDateTime;
}

export type DepartmentListOut = Page<DepartmentOut>;

export interface DepartmentDetailOut extends DepartmentOut {
  head: TeacherBrief | null;
  teacher_count: number;
  student_count: number;
  course_count: number;
  courses: CourseBrief[];
}

/** The head is set afterwards with an update (it must already be in the department). */
export interface DepartmentCreate {
  code: string;
  name: string;
  description?: string | null;
  building?: string | null;
  phone?: string | null;
}

/** Admin: any field. HOD (own department): description, building and phone only. */
export interface DepartmentUpdate {
  code?: string;
  name?: string;
  description?: string | null;
  building?: string | null;
  phone?: string | null;
  head_id?: number | null;
}
