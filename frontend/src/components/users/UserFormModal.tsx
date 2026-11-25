import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { z } from 'zod';

import { useStudentQuery, useStudentsQuery } from '../../hooks/useStudents';
import { useTeachersQuery } from '../../hooks/useTeachers';
import { useCreateUser, useUpdateUser } from '../../hooks/useUsers';
import { applyServerErrors } from '../../lib/formErrors';
import { ROLE_LABEL } from '../../lib/labels';
import type { UserCreate, UserOut, UserRole, UserUpdate } from '../../types';
import { FormField, inputClass } from '../FormField';
import { Modal } from '../Modal';
import { SearchInput } from '../SearchInput';
import { SelectControl } from '../SelectControl';
import { useToast } from '../useToast';

const ROLES = Object.keys(ROLE_LABEL) as UserRole[];

/**
 * Mirrors the backend: links must match the role (ARCHITECTURE §2). Username and
 * password are only checked when creating (an account's username can't change,
 * and its password is reset separately).
 */
const schema = z
  .object({
    editing: z.boolean(),
    username: z.string().trim(),
    password: z.string(),
    role: z.enum(ROLES as [UserRole, ...UserRole[]]),
    teacher_id: z.string(),
    student_id: z.string(),
  })
  .superRefine((v, ctx) => {
    if (!v.editing && !/^[A-Za-z0-9._-]{3,50}$/.test(v.username)) {
      ctx.addIssue({
        code: 'custom',
        path: ['username'],
        message: '3–50 letters, digits, dots, dashes or underscores',
      });
    }
    if (!v.editing && (v.password.length < 8 || v.password.length > 128)) {
      ctx.addIssue({
        code: 'custom',
        path: ['password'],
        message: v.password.length < 8 ? 'At least 8 characters' : 'At most 128 characters',
      });
    }
    if ((v.role === 'teacher' || v.role === 'hod') && !v.teacher_id) {
      ctx.addIssue({ code: 'custom', path: ['teacher_id'], message: 'Choose the teacher' });
    }
    if (v.role === 'student' && !v.student_id) {
      ctx.addIssue({ code: 'custom', path: ['student_id'], message: 'Choose the student' });
    }
  });

type FormValues = z.infer<typeof schema>;
const FIELDS = ['username', 'password', 'role', 'teacher_id', 'student_id'] as const;
function defaults(user: UserOut | undefined): FormValues {
  return {
    editing: user !== undefined,
    username: user?.username ?? '',
    password: '',
    role: user?.role ?? 'teacher',
    teacher_id: user?.teacher_id == null ? '' : String(user.teacher_id),
    student_id: user?.student_id == null ? '' : String(user.student_id),
  };
}

/** The linked student as an option, even when the search doesn't list them. */
function CurrentStudentOption({ id, listed }: { id: number; listed: boolean }) {
  const student = useStudentQuery(id);
  if (listed) return null;
  return (
    <option value={id}>
      {student.data
        ? `${student.data.student_no} — ${student.data.first_name} ${student.data.last_name}`
        : `Student #${String(id)}`}
    </option>
  );
}

/** "Alan Kay doesn't head a department, so the account can't be hod" etc. (BR-6). */
const ALIASES = { head: 'role', 'account must be': 'role' } as const;

interface UserFormModalProps {
  open: boolean;
  onClose: () => void;
  /** Omit to create an account; give one to change its role or linked record. */
  user?: UserOut;
}

/** Create a login account, or change an account's role and link (FR-8.1). Admin only. */
export function UserFormModal({ open, onClose, user }: UserFormModalProps) {
  const toast = useToast();
  const create = useCreateUser();
  const update = useUpdateUser();
  const editing = user !== undefined;
  const [studentSearch, setStudentSearch] = useState('');
  const {
    register,
    handleSubmit,
    setError,
    setValue,
    reset,
    control,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: defaults(user) });
  const role = useWatch({ control, name: 'role' });
  const needsTeacher = role === 'teacher' || role === 'hod';
  const needsStudent = role === 'student';
  const teachers = useTeachersQuery({ limit: 100 }, { enabled: open && needsTeacher });
  const students = useStudentsQuery({ search: studentSearch || undefined, limit: 20 });

  const linkedStudentId = user?.role === 'student' ? user.student_id : null;

  const close = () => {
    reset(defaults(user));
    setStudentSearch('');
    onClose();
  };

  const onSubmit = handleSubmit(async (v) => {
    const links = {
      role: v.role,
      teacher_id: needsTeacher ? Number(v.teacher_id) : null,
      student_id: needsStudent ? Number(v.student_id) : null,
    };
    try {
      if (user) {
        const body: UserUpdate = links;
        await update.mutateAsync({ id: user.id, body });
        toast.success(`Account ${user.username} updated`);
      } else {
        const body: UserCreate = { username: v.username, password: v.password, ...links };
        await create.mutateAsync(body);
        toast.success(`Account ${v.username} created`);
      }
      close();
    } catch (error) {
      applyServerErrors(error, setError, FIELDS, ALIASES);
    }
  });

  return (
    <Modal
      open={open}
      title={user ? `Edit account ${user.username}` : 'New account'}
      onClose={close}
      footer={
        <>
          <button type="button" onClick={close} className="rounded border px-4 py-2">
            Cancel
          </button>
          <button
            type="submit"
            form="user-form"
            disabled={isSubmitting}
            className="rounded bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {isSubmitting ? 'Saving…' : editing ? 'Save changes' : 'Create account'}
          </button>
        </>
      }
    >
      <form
        id="user-form"
        className="space-y-4"
        noValidate
        onSubmit={(event) => {
          void onSubmit(event);
        }}
      >
        {errors.root?.message && (
          <p role="alert" className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">
            {errors.root.message}
          </p>
        )}
        {editing ? (
          <p className="text-sm text-slate-600">
            Change what <strong>{user.username}</strong> can do. The username stays the same; use
            Reset password for a new password.
          </p>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField label="Username" required error={errors.username?.message}>
              {(p) => (
                <input {...p} autoComplete="off" {...register('username')} className={inputClass} />
              )}
            </FormField>
            <FormField
              label="Temporary password"
              required
              error={errors.password?.message}
              hint="Give it to the user; they can change it on their profile."
            >
              {(p) => (
                <input
                  {...p}
                  type="password"
                  autoComplete="new-password"
                  {...register('password')}
                  className={inputClass}
                />
              )}
            </FormField>
          </div>
        )}
        <FormField
          label="Role"
          required
          error={errors.role?.message}
          hint={role === 'hod' ? 'The teacher must be the head of a department.' : undefined}
        >
          {(p) => (
            <SelectControl
              control={control}
              name="role"
              fieldProps={p}
              onValueChange={() => {
                // A role has its own kind of link: forget the other one.
                setValue('teacher_id', '');
                setValue('student_id', '');
              }}
            >
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {ROLE_LABEL[r]}
                </option>
              ))}
            </SelectControl>
          )}
        </FormField>
        {needsTeacher && (
          <FormField label="Teacher" required error={errors.teacher_id?.message}>
            {(p) => (
              <SelectControl control={control} name="teacher_id" fieldProps={p}>
                <option value="">Choose…</option>
                {teachers.data?.items.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.last_name}, {t.first_name}
                  </option>
                ))}
              </SelectControl>
            )}
          </FormField>
        )}
        {needsStudent && (
          <div className="space-y-2">
            <SearchInput
              label="Find student"
              placeholder="Name, email or student number…"
              onSearch={setStudentSearch}
            />
            <FormField label="Student" required error={errors.student_id?.message}>
              {(p) => (
                <SelectControl control={control} name="student_id" fieldProps={p}>
                  <option value="">Choose…</option>
                  {linkedStudentId !== null && (
                    <CurrentStudentOption
                      id={linkedStudentId}
                      listed={students.data?.items.some((s) => s.id === linkedStudentId) ?? false}
                    />
                  )}
                  {students.data?.items.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.student_no} — {s.first_name} {s.last_name}
                    </option>
                  ))}
                </SelectControl>
              )}
            </FormField>
          </div>
        )}
      </form>
    </Modal>
  );
}
