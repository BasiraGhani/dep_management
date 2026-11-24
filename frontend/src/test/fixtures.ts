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

/** GET /auth/me for an account with `role` (teacher/student links filled as needed). */
export function meFor(role: CurrentUserOut['role']): CurrentUserOut {
  const base = { ...teacherMe, id: 10, username: `demo.${role}`, role };
  if (role === 'admin') return { ...base, teacher_id: null, teacher: null };
  if (role === 'student') {
    return {
      ...base,
      teacher_id: null,
      teacher: null,
      student_id: 1,
      student: {
        id: 1,
        student_no: 'CS2026001',
        first_name: 'Amira',
        last_name: 'Costa',
        email: 'amira@student.uni.example',
        phone: null,
        date_of_birth: null,
        department_id: 1,
        year: 1,
        status: 'active',
        enrollment_date: '2026-09-01',
        created_at: '2026-09-01T10:00:00Z',
        updated_at: '2026-09-01T10:00:00Z',
      },
    };
  }
  return base;
}

export const csDepartment = {
  id: 3,
  code: 'CS',
  name: 'Computer Science',
  description: 'Programming and systems',
  building: 'Turing Hall',
  phone: '+1 555 0100',
  head_id: 2,
  created_at: '2026-09-01T10:00:00Z',
  updated_at: '2026-09-01T10:00:00Z',
};

export const csDepartmentDetail = {
  ...csDepartment,
  head: { id: 2, first_name: 'Alan', last_name: 'Kay', title: 'associate_professor' as const },
  teacher_count: 2,
  student_count: 20,
  course_count: 2,
  courses: [
    { id: 11, code: 'CS101', title: 'Programming', credits: 4, teacher_id: 2 },
    { id: 12, code: 'CS201', title: 'Data Structures', credits: 4, teacher_id: 5 },
  ],
};

export const csTeachers = {
  total: 2,
  items: [
    {
      id: 2,
      first_name: 'Alan',
      last_name: 'Kay',
      title: 'associate_professor' as const,
      email: 'alan@uni.example',
      department_id: 3,
    },
    {
      id: 5,
      first_name: 'Grace',
      last_name: 'Hopper',
      title: 'professor' as const,
      email: 'grace@uni.example',
      department_id: 3,
    },
  ],
};

/** GET /teachers/2 as staff see it (Alan Kay, CS head, teaches CS101). */
export const kayDetail = {
  id: 2,
  first_name: 'Alan',
  last_name: 'Kay',
  title: 'associate_professor' as const,
  email: 'alan@uni.example',
  department_id: 3,
  phone: '555-0102',
  hire_date: '2015-09-01',
  created_at: '2026-09-01T10:00:00Z',
  updated_at: '2026-09-01T10:00:00Z',
  courses: [{ id: 11, code: 'CS101', title: 'Programming', credits: 4, teacher_id: 2 }],
  user_id: 10,
};

/** GET /students/1 (Amira Costa, CS, 2 enrollments, one graded). */
export const amiraDetail = {
  id: 1,
  student_no: 'CS2026001',
  first_name: 'Amira',
  last_name: 'Costa',
  email: 'amira@student.uni.example',
  phone: '555-0110',
  date_of_birth: '2006-01-01',
  department_id: 3,
  year: 1,
  status: 'active' as const,
  enrollment_date: '2026-09-01',
  created_at: '2026-09-01T10:00:00Z',
  updated_at: '2026-09-01T10:00:00Z',
  enrollments: [
    {
      id: 101,
      semester: '2026-Spring',
      grade: 'A' as const,
      course: { id: 11, code: 'CS101', title: 'Programming', credits: 4, teacher_id: 2 },
    },
    {
      id: 102,
      semester: '2026-Fall',
      grade: null,
      course: { id: 12, code: 'CS201', title: 'Data Structures', credits: 4, teacher_id: 5 },
    },
  ],
  gpa: 4.0,
  user_id: 4,
};
