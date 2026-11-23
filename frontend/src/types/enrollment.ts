import type { CourseBrief, Grade, IsoDateTime, Page, StudentBrief } from './common';

/** "YYYY-Spring", "YYYY-Summer" or "YYYY-Fall", e.g. "2026-Fall". */
export type Semester = string;
export const SEMESTER_PATTERN = /^(19|20|21)\d{2}-(Spring|Summer|Fall)$/;

export interface EnrollmentOut {
  id: number;
  student_id: number;
  course_id: number;
  semester: Semester;
  grade: Grade | null;
  student: StudentBrief;
  course: CourseBrief;
  created_at: IsoDateTime;
  updated_at: IsoDateTime;
}

export type EnrollmentListOut = Page<EnrollmentOut>;

export interface EnrollmentCreate {
  student_id: number;
  course_id: number;
  semester: Semester;
}

/** `grade: null` clears the grade. */
export interface GradeUpdate {
  grade: Grade | null;
}

/** One row of the bulk grade request (PUT /courses/{id}/grades). */
export interface BulkGradeItem {
  enrollment_id: number;
  grade: Grade | null;
}
