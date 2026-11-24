import { useAuth } from './useAuth';

/** Role checks for showing and hiding actions. The backend still enforces every rule. */
export function useRole() {
  const { user } = useAuth();
  return {
    role: user?.role ?? null,
    isAdmin: user?.role === 'admin',
    /** True if the user is the HOD whose teacher record heads this department. */
    headsDepartment: (headId: number | null) =>
      user?.role === 'hod' && headId !== null && user.teacher_id === headId,
  };
}
