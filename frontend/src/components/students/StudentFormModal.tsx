import { zodResolver } from '@hookform/resolvers/zod';
import { useForm, useWatch } from 'react-hook-form';
import { z } from 'zod';

import { useDepartmentsQuery } from '../../hooks/useDepartments';
import { useCreateStudent, useUpdateStudent } from '../../hooks/useStudents';
import { applyServerErrors, emptyToNull } from '../../lib/formErrors';
import { STATUS_LABEL } from '../../lib/labels';
import {
  accountFields,
  checkAccount,
  email,
  optionalPastDate,
  optionalPhone,
  personName,
  todayIso,
} from '../../lib/validation';
import type { StudentCreate, StudentOut, StudentStatus, StudentUpdate } from '../../types';
import { AccountFields } from '../AccountFields';
import { FormField, inputClass } from '../FormField';
import { Modal } from '../Modal';
import { useToast } from '../useToast';

/**
 * * admin: every field, any department
 * * hod: every field, only their own department (and no moving students out)
 */
export type StudentFormMode = 'admin' | 'hod';

const STATUSES = Object.keys(STATUS_LABEL) as StudentStatus[];
const YEARS = [1, 2, 3, 4, 5, 6];

const schema = z
  .object({
    student_no: z
      .string()
      .trim()
      .min(1, 'Enter a student number')
      .max(20, 'At most 20 characters')
      .regex(/^[A-Za-z0-9-]+$/, 'Letters, digits and dashes only'),
    first_name: personName('first name'),
    last_name: personName('last name'),
    email,
    phone: optionalPhone,
    date_of_birth: optionalPastDate,
    department_id: z.string().min(1, 'Choose a department'),
    year: z.string().regex(/^[1-6]$/, 'Choose a year from 1 to 6'),
    status: z.enum(STATUSES as [StudentStatus, ...StudentStatus[]]),
    enrollment_date: z
      .string()
      .min(1, 'Enter the enrollment date')
      .refine((v) => v <= todayIso(), "Can't be in the future"),
    ...accountFields,
  })
  .superRefine(checkAccount);

type FormValues = z.infer<typeof schema>;
const FIELDS = [
  'student_no',
  'first_name',
  'last_name',
  'email',
  'phone',
  'date_of_birth',
  'department_id',
  'year',
  'status',
  'enrollment_date',
  'username',
  'temp_password',
] as const;

interface StudentFormModalProps {
  open: boolean;
  onClose: () => void;
  mode: StudentFormMode;
  /** Omit to create a student; give one to edit it. */
  student?: StudentOut;
  /** The HOD's department: the only one a HOD may choose. */
  hodDepartmentId?: number | null;
}

function defaults(student: StudentOut | undefined, hodDepartmentId: number | null): FormValues {
  return {
    student_no: student?.student_no ?? '',
    first_name: student?.first_name ?? '',
    last_name: student?.last_name ?? '',
    email: student?.email ?? '',
    phone: student?.phone ?? '',
    date_of_birth: student?.date_of_birth ?? '',
    department_id: String(student?.department_id ?? hodDepartmentId ?? ''),
    year: String(student?.year ?? 1),
    status: student?.status ?? 'active',
    enrollment_date: student?.enrollment_date ?? todayIso(),
    create_account: false,
    username: '',
    temp_password: '',
  };
}

export function StudentFormModal({
  open,
  onClose,
  mode,
  student,
  hodDepartmentId = null,
}: StudentFormModalProps) {
  const toast = useToast();
  const editing = student !== undefined;
  const create = useCreateStudent();
  const update = useUpdateStudent(student?.id ?? 0);
  const departments = useDepartmentsQuery({ limit: 100 });

  const {
    register,
    handleSubmit,
    setError,
    reset,
    control,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: defaults(student, hodDepartmentId),
  });
  const wantsAccount = useWatch({ control, name: 'create_account' });
  const departmentOptions = (departments.data?.items ?? []).filter(
    (d) => mode === 'admin' || d.id === hodDepartmentId,
  );

  const close = () => {
    reset(defaults(student, hodDepartmentId));
    onClose();
  };

  const onSubmit = handleSubmit(async (v) => {
    const record = {
      student_no: v.student_no,
      first_name: v.first_name,
      last_name: v.last_name,
      email: v.email,
      phone: emptyToNull(v.phone),
      date_of_birth: v.date_of_birth || null,
      year: Number(v.year),
      status: v.status,
      enrollment_date: v.enrollment_date,
    };
    const name = `${v.first_name} ${v.last_name}`;
    try {
      if (!editing) {
        const body: StudentCreate = {
          ...record,
          department_id: Number(v.department_id),
          create_account: v.create_account
            ? { username: v.username, temp_password: v.temp_password }
            : null,
        };
        await create.mutateAsync(body);
        toast.success(`${name} added${v.create_account ? ' with a login account' : ''}`);
      } else {
        // A HOD can't move students to another department, so never sends it.
        const body: StudentUpdate =
          mode === 'hod' ? record : { ...record, department_id: Number(v.department_id) };
        await update.mutateAsync(body);
        toast.success(`${name} updated`);
      }
      close();
    } catch (error) {
      applyServerErrors(error, setError, FIELDS, { 'student number': 'student_no' });
    }
  });

  return (
    <Modal
      open={open}
      title={editing ? `Edit ${student.first_name} ${student.last_name}` : 'New student'}
      onClose={close}
      footer={
        <>
          <button type="button" onClick={close} className="rounded border px-4 py-2">
            Cancel
          </button>
          <button
            type="submit"
            form="student-form"
            disabled={isSubmitting}
            className="rounded bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {isSubmitting ? 'Saving…' : editing ? 'Save changes' : 'Add student'}
          </button>
        </>
      }
    >
      <form
        id="student-form"
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
        <FormField
          label="Student number"
          required
          error={errors.student_no?.message}
          hint="e.g. CS2026001"
        >
          {(p) => <input {...p} {...register('student_no')} className={inputClass} />}
        </FormField>
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField label="First name" required error={errors.first_name?.message}>
            {(p) => <input {...p} {...register('first_name')} className={inputClass} />}
          </FormField>
          <FormField label="Last name" required error={errors.last_name?.message}>
            {(p) => <input {...p} {...register('last_name')} className={inputClass} />}
          </FormField>
          <FormField label="Email" required error={errors.email?.message}>
            {(p) => <input {...p} type="email" {...register('email')} className={inputClass} />}
          </FormField>
          <FormField label="Phone" error={errors.phone?.message}>
            {(p) => <input {...p} type="tel" {...register('phone')} className={inputClass} />}
          </FormField>
          <FormField label="Date of birth" error={errors.date_of_birth?.message}>
            {(p) => (
              <input {...p} type="date" {...register('date_of_birth')} className={inputClass} />
            )}
          </FormField>
          <FormField label="Enrollment date" required error={errors.enrollment_date?.message}>
            {(p) => (
              <input {...p} type="date" {...register('enrollment_date')} className={inputClass} />
            )}
          </FormField>
          <FormField label="Year of study" required error={errors.year?.message}>
            {(p) => (
              <select {...p} {...register('year')} className={inputClass}>
                {YEARS.map((y) => (
                  <option key={y} value={y}>
                    Year {y}
                  </option>
                ))}
              </select>
            )}
          </FormField>
          <FormField label="Status" required error={errors.status?.message}>
            {(p) => (
              <select {...p} {...register('status')} className={inputClass}>
                {STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {STATUS_LABEL[s]}
                  </option>
                ))}
              </select>
            )}
          </FormField>
        </div>
        <FormField
          label="Department"
          required
          error={errors.department_id?.message}
          hint={
            mode === 'hod'
              ? 'Heads of department manage students of their own department only.'
              : undefined
          }
        >
          {(p) => (
            <select {...p} {...register('department_id')} className={inputClass}>
              {mode === 'admin' && <option value="">Choose…</option>}
              {departmentOptions.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.code} — {d.name}
                </option>
              ))}
            </select>
          )}
        </FormField>
        {!editing && (
          <AccountFields
            who="student"
            register={register}
            errors={errors}
            wantsAccount={wantsAccount}
          />
        )}
      </form>
    </Modal>
  );
}
