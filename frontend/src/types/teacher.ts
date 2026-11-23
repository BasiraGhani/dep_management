import type {
  AccountCreate,
  CourseBrief,
  IsoDate,
  IsoDateTime,
  Page,
  TeacherTitle,
} from './common';

/** What students see of a teacher. */
export interface TeacherPublicOut {
  id: number;
  first_name: string;
  last_name: string;
  title: TeacherTitle;
  email: string;
  department_id: number;
}

/** What admins, HODs and teachers see. */
export interface TeacherOut extends TeacherPublicOut {
  phone: string | null;
  hire_date: IsoDate | null;
  created_at: IsoDateTime;
  updated_at: IsoDateTime;
}

export type TeacherListOut = Page<TeacherOut>;
export type TeacherPublicListOut = Page<TeacherPublicOut>;

export interface TeacherDetailOut extends TeacherOut {
  courses: CourseBrief[];
  user_id: number | null;
}

export interface TeacherPublicDetailOut extends TeacherPublicOut {
  courses: CourseBrief[];
}

export interface TeacherCreate {
  first_name: string;
  last_name: string;
  email: string;
  phone?: string | null;
  title: TeacherTitle;
  department_id: number;
  hire_date?: IsoDate | null;
  create_account?: AccountCreate | null;
}

/** Admin: any field. HOD: own department's teachers (no move). Teacher: own phone/email. */
export interface TeacherUpdate {
  first_name?: string;
  last_name?: string;
  email?: string;
  phone?: string | null;
  title?: TeacherTitle;
  department_id?: number;
  hire_date?: IsoDate | null;
}

/** True for the staff shape (students get `TeacherPublicOut`). */
export function isFullTeacher(teacher: TeacherPublicOut): teacher is TeacherOut {
  return 'created_at' in teacher;
}
