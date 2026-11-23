import { AxiosError, AxiosHeaders } from 'axios';

import type { CurrentUserOut } from '../types';

/** A logged-in teacher, as GET /auth/me returns it. */
export const teacherMe: CurrentUserOut = {
  id: 3,
  username: 'demo.teacher',
  role: 'teacher',
  is_active: true,
  teacher_id: 2,
  student_id: null,
  created_at: '2026-09-01T10:00:00Z',
  updated_at: '2026-09-01T10:00:00Z',
  teacher: {
    id: 2,
    first_name: 'Alan',
    last_name: 'Kay',
    title: 'associate_professor',
    email: 'alan.kay@uni.example',
    department_id: 1,
    phone: null,
    hire_date: '2015-09-01',
    created_at: '2026-09-01T10:00:00Z',
    updated_at: '2026-09-01T10:00:00Z',
  },
  student: null,
};

/** An AxiosError as the API client would throw it for `status`. */
export function apiError(status: number, detail: string): AxiosError {
  const config = { headers: new AxiosHeaders() };
  return new AxiosError(`Request failed with status ${status}`, 'ERR_BAD_REQUEST', config, null, {
    status,
    statusText: String(status),
    data: { detail },
    headers: {},
    config,
  });
}

export const networkError = new AxiosError('Network Error', 'ERR_NETWORK');
