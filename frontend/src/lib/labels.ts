import type { StudentStatus, TeacherTitle, UserRole } from '../types';

/** Display names for the API's enum values. */
export const TITLE_LABEL: Record<TeacherTitle, string> = {
  lecturer: 'Lecturer',
  assistant_professor: 'Assistant Professor',
  associate_professor: 'Associate Professor',
  professor: 'Professor',
};

export const STATUS_LABEL: Record<StudentStatus, string> = {
  active: 'Active',
  graduated: 'Graduated',
  suspended: 'Suspended',
  withdrawn: 'Withdrawn',
};

export const ROLE_LABEL: Record<UserRole, string> = {
  admin: 'Administrator',
  hod: 'Head of department',
  teacher: 'Teacher',
  student: 'Student',
};
