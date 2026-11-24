import { zodResolver } from '@hookform/resolvers/zod';
import { useForm, useWatch } from 'react-hook-form';
import { z } from 'zod';

import { useDepartmentsQuery } from '../../hooks/useDepartments';
import { useCreateTeacher, useUpdateTeacher } from '../../hooks/useTeachers';
import { applyServerErrors, emptyToNull } from '../../lib/formErrors';
import { TITLE_LABEL } from '../../lib/labels';
import {
  accountFields,
  checkAccount,
  email,
  optionalPastDate,
  optionalPhone,
  personName,
} from '../../lib/validation';
import type { TeacherCreate, TeacherOut, TeacherTitle, TeacherUpdate } from '../../types';
import { AccountFields } from '../AccountFields';
import { FormField, inputClass } from '../FormField';
import { Modal } from '../Modal';
import { SelectControl } from '../SelectControl';
import { useToast } from '../useToast';

/**
 * Who is using the form decides what it offers (mirrors the backend rules):
 * * admin: every field, any department
 * * hod: every field, but only their own department (and no moving teachers out)
 * * self: a teacher editing their own record: phone and email only
 */
export type TeacherFormMode = 'admin' | 'hod' | 'self';

const TITLES = Object.keys(TITLE_LABEL) as TeacherTitle[];

const schema = z
  .object({
    first_name: personName('first name'),
    last_name: personName('last name'),
    email,
    phone: optionalPhone,
    title: z.enum(TITLES as [TeacherTitle, ...TeacherTitle[]]),
    department_id: z.string().min(1, 'Choose a department'),
    hire_date: optionalPastDate,
    ...accountFields,
  })
  .superRefine(checkAccount);

type FormValues = z.infer<typeof schema>;
const FIELDS = [
  'first_name',
  'last_name',
  'email',
  'phone',
  'title',
  'department_id',
  'hire_date',
  'username',
  'temp_password',
] as const;

interface TeacherFormModalProps {
  open: boolean;
  onClose: () => void;
  mode: TeacherFormMode;
  /** Omit to create a teacher; give one to edit it. */
  teacher?: TeacherOut;
  /** The HOD's department: the only one a HOD may choose. */
  hodDepartmentId?: number | null;
}

function defaults(teacher: TeacherOut | undefined, hodDepartmentId: number | null): FormValues {
  return {
    first_name: teacher?.first_name ?? '',
    last_name: teacher?.last_name ?? '',
    email: teacher?.email ?? '',
    phone: teacher?.phone ?? '',
    title: teacher?.title ?? 'lecturer',
    department_id: String(teacher?.department_id ?? hodDepartmentId ?? ''),
    hire_date: teacher?.hire_date ?? '',
    create_account: false,
    username: '',
    temp_password: '',
  };
}

export function TeacherFormModal({
  open,
  onClose,
  mode,
  teacher,
  hodDepartmentId = null,
}: TeacherFormModalProps) {
  const toast = useToast();
  const editing = teacher !== undefined;
  const create = useCreateTeacher();
  const update = useUpdateTeacher(teacher?.id ?? 0);
  const departments = useDepartmentsQuery({ limit: 100 });
  const selfOnly = mode === 'self';

  const {
    register,
    handleSubmit,
    setError,
    reset,
    control,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: defaults(teacher, hodDepartmentId),
  });
  const wantsAccount = useWatch({ control, name: 'create_account' });

  // A HOD only ever sees their own department; an admin sees them all.
  const departmentOptions = (departments.data?.items ?? []).filter(
    (d) => mode === 'admin' || d.id === hodDepartmentId,
  );

  const close = () => {
    reset(defaults(teacher, hodDepartmentId));
    onClose();
  };

  const onSubmit = handleSubmit(async (v) => {
    const contact = { email: v.email, phone: emptyToNull(v.phone) };
    const record = {
      first_name: v.first_name,
      last_name: v.last_name,
      ...contact,
      title: v.title,
      hire_date: v.hire_date || null,
    };
    try {
      if (!editing) {
        const body: TeacherCreate = {
          ...record,
          department_id: Number(v.department_id),
          create_account: v.create_account
            ? { username: v.username, temp_password: v.temp_password }
            : null,
        };
        await create.mutateAsync(body);
        toast.success(
          `${v.first_name} ${v.last_name} added${v.create_account ? ' with a login account' : ''}`,
        );
      } else {
        const body: TeacherUpdate =
          mode === 'self'
            ? contact
            : mode === 'hod'
              ? record // a HOD can't move teachers to another department
              : { ...record, department_id: Number(v.department_id) };
        await update.mutateAsync(body);
        toast.success(`${v.first_name} ${v.last_name} updated`);
      }
      close();
    } catch (error) {
      applyServerErrors(error, setError, FIELDS);
    }
  });

  const title = editing
    ? selfOnly
      ? 'Edit my contact details'
      : `Edit ${teacher.first_name} ${teacher.last_name}`
    : 'New teacher';

  return (
    <Modal
      open={open}
      title={title}
      onClose={close}
      footer={
        <>
          <button type="button" onClick={close} className="rounded border px-4 py-2">
            Cancel
          </button>
          <button
            type="submit"
            form="teacher-form"
            disabled={isSubmitting}
            className="rounded bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {isSubmitting ? 'Saving…' : editing ? 'Save changes' : 'Add teacher'}
          </button>
        </>
      }
    >
      <form
        id="teacher-form"
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

        {!selfOnly && (
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField label="First name" required error={errors.first_name?.message}>
              {(p) => <input {...p} {...register('first_name')} className={inputClass} />}
            </FormField>
            <FormField label="Last name" required error={errors.last_name?.message}>
              {(p) => <input {...p} {...register('last_name')} className={inputClass} />}
            </FormField>
          </div>
        )}

        <FormField label="Email" required error={errors.email?.message}>
          {(p) => <input {...p} type="email" {...register('email')} className={inputClass} />}
        </FormField>
        <FormField label="Phone" error={errors.phone?.message}>
          {(p) => <input {...p} type="tel" {...register('phone')} className={inputClass} />}
        </FormField>

        {!selfOnly && (
          <>
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField label="Title" required error={errors.title?.message}>
                {(p) => (
                  <select {...p} {...register('title')} className={inputClass}>
                    {TITLES.map((t) => (
                      <option key={t} value={t}>
                        {TITLE_LABEL[t]}
                      </option>
                    ))}
                  </select>
                )}
              </FormField>
              <FormField label="Hire date" error={errors.hire_date?.message}>
                {(p) => (
                  <input {...p} type="date" {...register('hire_date')} className={inputClass} />
                )}
              </FormField>
            </div>
            <FormField
              label="Department"
              required
              error={errors.department_id?.message}
              hint={
                mode === 'hod'
                  ? 'Heads of department manage teachers of their own department only.'
                  : undefined
              }
            >
              {(p) => (
                <SelectControl control={control} name="department_id" fieldProps={p}>
                  {mode === 'admin' && <option value="">Choose…</option>}
                  {departmentOptions.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.code} — {d.name}
                    </option>
                  ))}
                </SelectControl>
              )}
            </FormField>
          </>
        )}

        {!editing && (
          <AccountFields
            who="teacher"
            register={register}
            errors={errors}
            wantsAccount={wantsAccount}
          />
        )}
      </form>
    </Modal>
  );
}
