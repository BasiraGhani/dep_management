import type { Grade, IsoDateTime, Page, TeacherBrief } from './common';

export interface CourseOut {
  id: number;
  code: string;
  title: string;
  description: string | null;
  credits: number;
  capacity: number;
  department_id: number;
  teacher_id: number | null;
  created_at: IsoDateTime;
  updated_at: IsoDateTime;
}

export type CourseListOut = Page<CourseOut>;

/** One enrolled student on a course roster. */
export interface RosterEntry {
  enrollment_id: number;
  student_id: number;
  student_no: string;
  first_name: string;
  last_name: string;
  semester: string;
  grade: Grade | null;
}

export interface CourseDetailOut extends CourseOut {
  teacher: TeacherBrief | null;
  /** Null for users who may not see this course's enrollments (e.g. students). */
  roster: RosterEntry[] | null;
}

export interface CourseCreate {
  code: string;
  title: string;
  description?: string | null;
  credits: number;
  /** Defaults to 40. */
  capacity?: number;
  department_id: number;
  /** Must belong to the course's department (BR-2). */
  teacher_id?: number | null;
}

/** Admin: any field. HOD: own department's courses (no move). Teacher: own description. */
export interface CourseUpdate {
  code?: string;
  title?: string;
  description?: string | null;
  credits?: number;
  capacity?: number;
  department_id?: number;
  teacher_id?: number | null;
}
