import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { useCreateDepartment, useUpdateDepartment } from '../../hooks/useDepartments';
import { useTeachersQuery } from '../../hooks/useTeachers';
import { applyServerErrors, emptyToNull } from '../../lib/formErrors';
import type { DepartmentOut, DepartmentUpdate } from '../../types';
import { FormField, inputClass } from '../FormField';
import { Modal } from '../Modal';
import { SelectControl } from '../SelectControl';
import { useToast } from '../useToast';

// Mirrors the backend rules (schemas/department.py) so most mistakes are caught here.
const optionalText = (max: number) => z.string().trim().max(max, `At most ${max} characters`);
const phone = z
  .string()
  .trim()
  .refine((v) => v === '' || /^\+?[0-9()\- ]{3,30}$/.test(v), 'Digits, spaces, + ( ) - only');

const limitedSchema = z.object({
  description: optionalText(2000),
  building: optionalText(80),
  phone,
});
const fullSchema = limitedSchema.extend({
  code: z
    .string()
    .trim()
    .min(1, 'Enter a code')
    .max(10, 'At most 10 characters')
    .regex(/^[A-Za-z0-9]+$/, 'Letters and digits only'),
  name: z.string().trim().min(1, 'Enter a name').max(120, 'At most 120 characters'),
  head_id: z.string(),
});

type FormValues = z.infer<typeof fullSchema>;
const FIELDS = ['code', 'name', 'description', 'building', 'phone', 'head_id'] as const;

interface DepartmentFormModalProps {
  open: boolean;
  onClose: () => void;
  /** Omit to create a department; give one to edit it. */
  department?: DepartmentOut;
  /**
   * Admin: every field. Otherwise (the department's HOD) only description,
   * building and phone, matching what the backend allows.
   */
  canEditAll: boolean;
}

function defaults(department: DepartmentOut | undefined): FormValues {
  return {
    code: department?.code ?? '',
    name: department?.name ?? '',
    description: department?.description ?? '',
    building: department?.building ?? '',
    phone: department?.phone ?? '',
    head_id: department?.head_id ? String(department.head_id) : '',
  };
}

export function DepartmentFormModal({
  open,
  onClose,
  department,
  canEditAll,
}: DepartmentFormModalProps) {
  const toast = useToast();
  const editing = department !== undefined;
  const create = useCreateDepartment();
  const update = useUpdateDepartment(department?.id ?? 0);
  const teachers = useTeachersQuery(
    { department_id: department?.id, limit: 100 },
    { enabled: open && editing && canEditAll },
  );

  const {
    register,
    handleSubmit,
    setError,
    reset,
    control,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    // A HOD's hidden code/name/head fields keep the department's current (valid) values.
    resolver: zodResolver(fullSchema),
    defaultValues: defaults(department),
  });

  const close = () => {
    reset(defaults(department));
    onClose();
  };

  const onSubmit = handleSubmit(async (values) => {
    const contact = {
      description: emptyToNull(values.description),
      building: emptyToNull(values.building),
      phone: emptyToNull(values.phone),
    };
    try {
      if (!editing) {
        await create.mutateAsync({ code: values.code, name: values.name, ...contact });
        toast.success(`Department ${values.code.toUpperCase()} created`);
      } else {
        const body: DepartmentUpdate = canEditAll
          ? {
              code: values.code,
              name: values.name,
              ...contact,
              head_id: values.head_id === '' ? null : Number(values.head_id),
            }
          : contact;
        await update.mutateAsync(body);
        toast.success(`Department ${department.code} updated`);
      }
      close();
    } catch (error) {
      applyServerErrors(error, setError, FIELDS);
    }
  });

  return (
    <Modal
      open={open}
      title={editing ? `Edit ${department.code}` : 'New department'}
      onClose={close}
      footer={
        <>
          <button type="button" onClick={close} className="rounded border px-4 py-2">
            Cancel
          </button>
          <button
            type="submit"
            form="department-form"
            disabled={isSubmitting}
            className="rounded bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {isSubmitting ? 'Saving…' : editing ? 'Save changes' : 'Create department'}
          </button>
        </>
      }
    >
      <form
        id="department-form"
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
        {canEditAll && (
          <>
            <FormField label="Code" required error={errors.code?.message} hint="e.g. CS">
              {(p) => <input {...p} {...register('code')} className={inputClass} />}
            </FormField>
            <FormField label="Name" required error={errors.name?.message}>
              {(p) => <input {...p} {...register('name')} className={inputClass} />}
            </FormField>
          </>
        )}
        <FormField label="Description" error={errors.description?.message}>
          {(p) => <textarea {...p} rows={3} {...register('description')} className={inputClass} />}
        </FormField>
        <FormField label="Building" error={errors.building?.message}>
          {(p) => <input {...p} {...register('building')} className={inputClass} />}
        </FormField>
        <FormField label="Phone" error={errors.phone?.message}>
          {(p) => <input {...p} type="tel" {...register('phone')} className={inputClass} />}
        </FormField>
        {canEditAll && editing && (
          <FormField
            label="Head of department"
            error={errors.head_id?.message}
            hint="Must be a teacher in this department. Their account becomes HOD."
          >
            {(p) => (
              <SelectControl control={control} name="head_id" fieldProps={p}>
                <option value="">No head</option>
                {teachers.data?.items.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.first_name} {t.last_name}
                  </option>
                ))}
              </SelectControl>
            )}
          </FormField>
        )}
      </form>
    </Modal>
  );
}
