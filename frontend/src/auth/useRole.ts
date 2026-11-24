import { useAuth } from './useAuth';

/** Role checks for showing and hiding actions. The backend still enforces every rule. */
export function useRole() {
  const { user } = useAuth();
  const role = user?.role ?? null;
  return {
    role,
    isAdmin: role === 'admin',
    isStudent: role === 'student',
    /** The user's own teacher record id (HODs and teachers), else null. */
    teacherId: role === 'hod' || role === 'teacher' ? (user?.teacher_id ?? null) : null,
    /**
     * The department a HOD manages (their teacher record's department; BR-6
     * keeps the HOD role in step with actually heading it). Null for other roles.
     */
    hodDepartmentId: role === 'hod' ? (user?.teacher?.department_id ?? null) : null,
    /** True if the user is the HOD whose teacher record heads this department. */
    headsDepartment: (headId: number | null) =>
      role === 'hod' && headId !== null && user?.teacher_id === headId,
  };
}
