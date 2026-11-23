import type { StudentOut } from './student';
import type { TeacherOut } from './teacher';
import type { UserOut } from './user';

/** POST /auth/login response. */
export interface Token {
  access_token: string;
  token_type: 'bearer';
}

/** GET /auth/me response: the account plus its linked record. */
export interface CurrentUserOut extends UserOut {
  teacher: TeacherOut | null;
  student: StudentOut | null;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}
