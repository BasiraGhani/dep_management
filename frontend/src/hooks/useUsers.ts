import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { changePassword } from '../api/auth';
import { createUser, listUsers, resetPassword, updateUser, type UserFilters } from '../api/users';
import type { ChangePasswordRequest, UserCreate, UserUpdate } from '../types';
import { studentKeys } from './useStudents';
import { teacherKeys } from './useTeachers';

export const userKeys = {
  all: ['users'] as const,
  list: (params: UserFilters) => ['users', 'list', params] as const,
};

/** Admin only (FR-8.1). */
export function useUsersQuery(params: UserFilters) {
  return useQuery({
    queryKey: userKeys.list(params),
    queryFn: () => listUsers(params),
    placeholderData: keepPreviousData,
  });
}

/** Accounts show on teacher and student pages ("has a login account"), so refresh those too. */
function useInvalidateUsers() {
  const queryClient = useQueryClient();
  return async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: userKeys.all }),
      queryClient.invalidateQueries({ queryKey: teacherKeys.all }),
      queryClient.invalidateQueries({ queryKey: studentKeys.all }),
    ]);
  };
}

export function useCreateUser() {
  const invalidate = useInvalidateUsers();
  return useMutation({ mutationFn: (body: UserCreate) => createUser(body), onSuccess: invalidate });
}

export function useUpdateUser() {
  const invalidate = useInvalidateUsers();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: UserUpdate }) => updateUser(id, body),
    onSuccess: invalidate,
  });
}

/** The response holds the temporary password; it can't be fetched again. */
export function useResetPassword() {
  return useMutation({ mutationFn: (id: number) => resetPassword(id) });
}

/** FR-1.6: change your own password. */
export function useChangePassword() {
  return useMutation({ mutationFn: (body: ChangePasswordRequest) => changePassword(body) });
}
