/**
 * Types shared by several resources. Every interface in src/types mirrors a
 * backend Pydantic schema of the same name (backend/app/schemas), field for field.
 * Dates and timestamps arrive as ISO-8601 strings.
 */

export type UserRole = 'admin' | 'hod' | 'teacher' | 'student';
export type TeacherTitle = 'lecturer' | 'assistant_professor' | 'associate_professor' | 'professor';
export type StudentStatus = 'active' | 'graduated' | 'suspended' | 'withdrawn';
export type Grade = 'A' | 'A-' | 'B+' | 'B' | 'B-' | 'C+' | 'C' | 'C-' | 'D' | 'F';
/** The lists that GET /export/{resource}.csv can export. */
export type ExportResource = 'students' | 'teachers' | 'courses';

/** An ISO date, e.g. "2026-09-01". */
export type IsoDate = string;
/** An ISO date-time with time zone, e.g. "2026-09-01T10:00:00Z". */
export type IsoDateTime = string;

/** `{ items, total }` returned by every list endpoint (backend `XListOut`). */
export interface Page<T> {
  items: T[];
  total: number;
}

/** `?search=&skip=&limit=` accepted by every list endpoint (limit 1–100, default 20). */
export interface ListParams {
  search?: string;
  skip?: number;
  limit?: number;
}

export interface AccountCreate {
  username: string;
  temp_password: string;
}

export interface TeacherBrief {
  id: number;
  first_name: string;
  last_name: string;
  title: TeacherTitle;
}

export interface CourseBrief {
  id: number;
  code: string;
  title: string;
  credits: number;
  teacher_id: number | null;
}

export interface StudentBrief {
  id: number;
  student_no: string;
  first_name: string;
  last_name: string;
}

/** One entry of a 422 response's `detail` list (FastAPI `ValidationError`). */
export interface ValidationError {
  loc: (string | number)[];
  msg: string;
  type: string;
  input?: unknown;
  ctx?: Record<string, unknown>;
}

/**
 * Error body of every failed request: `detail` is a message (401/403/404/409 and
 * business-rule 422s) or a list of field errors (request validation 422s).
 */
export interface ApiErrorBody {
  detail: string | ValidationError[];
}
