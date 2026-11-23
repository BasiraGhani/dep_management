import type {
  AccountCreate,
  CourseBrief,
  Grade,
  IsoDate,
  IsoDateTime,
  Page,
  StudentStatus,
} from './common';

export interface StudentOut {
  id: number;
  student_no: string;
  first_name: string;
  last_name: string;
  email: string;
  phone: string | null;
  date_of_birth: IsoDate | null;
  department_id: number;
  year: number;
  status: StudentStatus;
  enrollment_date: IsoDate;
  created_at: IsoDateTime;
  updated_at: IsoDateTime;
}

export type StudentListOut = Page<StudentOut>;

/** One of a student's enrollments, with its course. */
export interface StudentEnrollmentOut {
  id: number;
  semester: string;
  grade: Grade | null;
  course: CourseBrief;
}

export interface StudentDetailOut extends StudentOut {
  enrollments: StudentEnrollmentOut[];
  /** 4.0 scale, weighted by credits; null until something is graded. */
  gpa: number | null;
  user_id: number | null;
}

export interface StudentCreate {
  student_no: string;
  first_name: string;
  last_name: string;
  email: string;
  phone?: string | null;
  date_of_birth?: IsoDate | null;
  department_id: number;
  year: number;
  /** Defaults to "active". */
  status?: StudentStatus;
  /** Defaults to today. */
  enrollment_date?: IsoDate;
  create_account?: AccountCreate | null;
}

/** Admin: any field. HOD: own department's students (no move). Student: own phone/email. */
export interface StudentUpdate {
  student_no?: string;
  first_name?: string;
  last_name?: string;
  email?: string;
  phone?: string | null;
  date_of_birth?: IsoDate | null;
  department_id?: number;
  year?: number;
  status?: StudentStatus;
  enrollment_date?: IsoDate;
}
