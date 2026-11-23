import type { CourseBrief } from './common';
import type { EnrollmentOut } from './enrollment';
import type { StudentEnrollmentOut } from './student';

export interface Totals {
  departments: number;
  teachers: number;
  students: number;
  courses: number;
}

/** One bar of the "students per department" chart. */
export interface DepartmentStudents {
  department_id: number;
  code: string;
  name: string;
  students: number;
}

export interface DepartmentRef {
  id: number;
  code: string;
  name: string;
}

export interface AdminDashboard {
  role: 'admin';
  totals: Totals;
  students_per_department: DepartmentStudents[];
  recent_enrollments: EnrollmentOut[];
}

export interface HodDashboard {
  role: 'hod';
  /** Null if the account no longer heads a department. */
  department: DepartmentRef | null;
  totals: Totals;
  students_per_department: DepartmentStudents[];
  recent_enrollments: EnrollmentOut[];
}

export interface TeacherCourseStats {
  course: CourseBrief;
  capacity: number;
  enrolled: number;
  ungraded: number;
}

export interface TeacherDashboard {
  role: 'teacher';
  courses: TeacherCourseStats[];
}

export interface StudentDashboard {
  role: 'student';
  enrollments: StudentEnrollmentOut[];
  gpa: number | null;
  graded_credits: number;
}

/** GET /dashboard response; narrow on `role`. */
export type Dashboard = AdminDashboard | HodDashboard | TeacherDashboard | StudentDashboard;
