import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { z } from 'zod';

import { useStudentsQuery } from '../../hooks/useStudents';
import { useTeachersQuery } from '../../hooks/useTeachers';
import { useCreateUser } from '../../hooks/useUsers';
import { applyServerErrors } from '../../lib/formErrors';
import { ROLE_LABEL } from '../../lib/labels';
import type { UserCreate, UserRole } from '../../types';
import { FormField, inputClass } from '../FormField';
import { Modal } from '../Modal';
import { SearchInput } from '../SearchInput';
import { SelectControl } from '../SelectControl';
import { useToast } from '../useToast';

const ROLES = Object.keys(ROLE_LABEL) as UserRole[];

/** Mirrors the backend: links must match the role (ARCHITECTURE §2). */
const schema = z
  .object({
    username: z
      .string()
      .trim()
      .regex(/^[A-Za-z0-9._-]{3,50}$/, '3–50 letters, digits, dots, dashes or underscores'),
    password: z.string().min(8, 'At least 8 characters').max(128, 'At most 128 characters'),
    role: z.enum(ROLES as [UserRole, ...UserRole[]]),
    teacher_id: z.string(),
    student_id: z.string(),
  })
  .superRefine((v, ctx) => {
    if ((v.role === 'teacher' || v.role === 'hod') && !v.teacher_id) {
      ctx.addIssue({ code: 'custom', path: ['teacher_id'], message: 'Choose the teacher' });
    }
    if (v.role === 'student' && !v.student_id) {
      ctx.addIssue({ code: 'custom', path: ['student_id'], message: 'Choose the student' });
    }
  });

type FormValues = z.infer<typeof schema>;
const FIELDS = ['username', 'password', 'role', 'teacher_id', 'student_id'] as const;
const EMPTY: FormValues = {
  username: '',
  password: '',
  role: 'teacher',
  teacher_id: '',
  student_id: '',
};

/** "Alan Kay doesn't head a department, so the account can't be hod" etc. (BR-6). */
const ALIASES = { head: 'role', 'account must be': 'role' } as const;

/** Create a login account (FR-8.1). Admin only. */
export function UserFormModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const toast = useToast();
  const create = useCreateUser();
  const [studentSearch, setStudentSearch] = useState('');
  const {
    register,
    handleSubmit,
    setError,
    setValue,
    reset,
    control,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: EMPTY });
  const role = useWatch({ control, name: 'role' });
  const needsTeacher = role === 'teacher' || role === 'hod';
  const needsStudent = role === 'student';
  const teachers = useTeachersQuery({ limit: 100 }, { enabled: open && needsTeacher });
  const students = useStudentsQuery({ search: studentSearch || undefined, limit: 20 });

  const close = () => {
    reset(EMPTY);
    setStudentSearch('');
    onClose();
  };

  const onSubmit = handleSubmit(async (v) => {
    const body: UserCreate = {
      username: v.username,
      password: v.password,
      role: v.role,
      teacher_id: needsTeacher ? Number(v.teacher_id) : null,
      student_id: needsStudent ? Number(v.student_id) : null,
    };
    try {
      await create.mutateAsync(body);
      toast.success(`Account ${v.username} created`);
      close();
    } catch (error) {
      applyServerErrors(error, setError, FIELDS, ALIASES);
    }
  });

  return (
    <Modal
      open={open}
      title="New account"
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
            {isSubmitting ? 'Creating…' : 'Create account'}
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
