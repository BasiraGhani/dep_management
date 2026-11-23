import type { IsoDateTime, Page, UserRole } from './common';

export interface UserOut {
  id: number;
  username: string;
  role: UserRole;
  is_active: boolean;
  teacher_id: number | null;
  student_id: number | null;
  created_at: IsoDateTime;
  updated_at: IsoDateTime;
}

export type UserListOut = Page<UserOut>;

export interface UserCreate {
  username: string;
  password: string;
  role: UserRole;
  teacher_id?: number | null;
  student_id?: number | null;
}

/** Only the fields sent are changed. `teacher_id`/`student_id: null` unlinks. */
export interface UserUpdate {
  is_active?: boolean;
  role?: UserRole;
  teacher_id?: number | null;
  student_id?: number | null;
}

export interface TemporaryPassword {
  temporary_password: string;
}
