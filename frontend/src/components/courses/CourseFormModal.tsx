import { zodResolver } from '@hookform/resolvers/zod';
import { useForm, useWatch } from 'react-hook-form';
import { z } from 'zod';

import { useCreateCourse, useUpdateCourse } from '../../hooks/useCourses';
import { useDepartmentsQuery } from '../../hooks/useDepartments';
import { useTeachersQuery } from '../../hooks/useTeachers';
import { applyServerErrors, emptyToNull } from '../../lib/formErrors';
import type { CourseCreate, CourseOut, CourseUpdate } from '../../types';
import { FormField, inputClass } from '../FormField';
import { Modal } from '../Modal';
import { SelectControl } from '../SelectControl';
import { useToast } from '../useToast';

/**
 * * admin: every field, any department
 * * hod: every field, only their own department (and no moving courses out)
 * * teacher: the course's own teacher, description only
 */
export type CourseFormMode = 'admin' | 'hod' | 'teacher';

const schema = z.object({
  code: z
    .string()
    .trim()
    .min(1, 'Enter a code')
    .max(15, 'At most 15 characters')
    .regex(/^[A-Za-z0-9-]+$/, 'Letters, digits and dashes only'),
  title: z.string().trim().min(1, 'Enter a title').max(150, 'At most 150 characters'),
  description: z.string().trim().max(5000, 'At most 5000 characters'),
  credits: z.string().regex(/^[1-6]$/, 'Choose 1 to 6 credits'),
  capacity: z
    .string()
    .trim()
    .regex(/^\d+$/, 'Enter a whole number')
    .refine((v) => Number(v) >= 1 && Number(v) <= 1000, 'Between 1 and 1000'),
  department_id: z.string().min(1, 'Choose a department'),
  teacher_id: z.string(),
});

type FormValues = z.infer<typeof schema>;
const FIELDS = [
  'code',
  'title',
  'description',
  'credits',
  'capacity',
  'department_id',
  'teacher_id',
] as const;

interface CourseFormModalProps {
  open: boolean;
  onClose: () => void;
  mode: CourseFormMode;
  /** Omit to create a course; give one to edit it. */
  course?: CourseOut;
  /** The HOD's department: the only one a HOD may choose. */
  hodDepartmentId?: number | null;
}

function defaults(course: CourseOut | undefined, hodDepartmentId: number | null): FormValues {
  return {
    code: course?.code ?? '',
    title: course?.title ?? '',
    description: course?.description ?? '',
    credits: String(course?.credits ?? 3),
    capacity: String(course?.capacity ?? 40),
    department_id: String(course?.department_id ?? hodDepartmentId ?? ''),
    teacher_id: course?.teacher_id ? String(course.teacher_id) : '',
  };
}

export function CourseFormModal({
  open,
  onClose,
  mode,
  course,
  hodDepartmentId = null,
}: CourseFormModalProps) {
  const toast = useToast();
  const editing = course !== undefined;
  const descriptionOnly = mode === 'teacher';
  const create = useCreateCourse();
  const update = useUpdateCourse(course?.id ?? 0);
  const departments = useDepartmentsQuery({ limit: 100 });

  const {
    register,
    handleSubmit,
    setError,
    setValue,
    reset,
    control,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: defaults(course, hodDepartmentId),
  });

  // BR-2: only teachers of the chosen department can teach the course.
  const departmentId = useWatch({ control, name: 'department_id' });
  const teachers = useTeachersQuery(
    { department_id: Number(departmentId), limit: 100 },
    { enabled: open && !descriptionOnly && departmentId !== '' },
  );
  const departmentOptions = (departments.data?.items ?? []).filter(
    (d) => mode === 'admin' || d.id === hodDepartmentId,
  );

  const close = () => {
    reset(defaults(course, hodDepartmentId));
    onClose();
  };

  const onSubmit = handleSubmit(async (v) => {
    const fields = {
      code: v.code,
      title: v.title,
      description: emptyToNull(v.description),
      credits: Number(v.credits),
      capacity: Number(v.capacity),
      teacher_id: v.teacher_id === '' ? null : Number(v.teacher_id),
    };
    try {
      if (!editing) {
        const body: CourseCreate = { ...fields, department_id: Number(v.department_id) };
        await create.mutateAsync(body);
        toast.success(`Course ${v.code.toUpperCase()} created`);
      } else {
        const body: CourseUpdate =
          mode === 'teacher'
            ? { description: fields.description }
            : mode === 'hod'
              ? fields // a HOD can't move courses to another department
              : { ...fields, department_id: Number(v.department_id) };
        await update.mutateAsync(body);
        toast.success(`Course ${course.code} updated`);
      }
      close();
    } catch (error) {
      applyServerErrors(error, setError, FIELDS, { "course's teacher": 'teacher_id' });
    }
  });

  return (
    <Modal
      open={open}
      title={editing ? `Edit ${course.code}` : 'New course'}
      onClose={close}
      footer={
        <>
          <button type="button" onClick={close} className="rounded border px-4 py-2">
            Cancel
          </button>
          <button
            type="submit"
            form="course-form"
            disabled={isSubmitting}
            className="rounded bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {isSubmitting ? 'Saving…' : editing ? 'Save changes' : 'Create course'}
          </button>
        </>
      }
    >
      <form
        id="course-form"
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
        {!descriptionOnly && (
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField label="Code" required error={errors.code?.message} hint="e.g. CS101">
              {(p) => <input {...p} {...register('code')} className={inputClass} />}
            </FormField>
            <FormField label="Title" required error={errors.title?.message}>
              {(p) => <input {...p} {...register('title')} className={inputClass} />}
            </FormField>
          </div>
        )}
        <FormField label="Description" error={errors.description?.message}>
          {(p) => <textarea {...p} rows={4} {...register('description')} className={inputClass} />}
        </FormField>
        {!descriptionOnly && (
          <>
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField label="Credits" required error={errors.credits?.message}>
                {(p) => (
                  <select {...p} {...register('credits')} className={inputClass}>
                    {[1, 2, 3, 4, 5, 6].map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                )}
              </FormField>
              <FormField label="Capacity" required error={errors.capacity?.message}>
                {(p) => (
                  <input
                    {...p}
                    type="number"
                    min={1}
                    max={1000}
                    {...register('capacity')}
                    className={inputClass}
                  />
                )}
              </FormField>
            </div>
            <FormField
              label="Department"
              required
              error={errors.department_id?.message}
              hint={
                mode === 'hod'
                  ? 'Heads of department manage courses of their own department only.'
                  : undefined
              }
            >
              {(p) => (
                <SelectControl
                  control={control}
                  name="department_id"
                  fieldProps={p}
                  onValueChange={() => {
                    // A teacher from the old department would break BR-2.
                    setValue('teacher_id', '');
                  }}
                >
                  {mode === 'admin' && <option value="">Choose…</option>}
                  {departmentOptions.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.code} — {d.name}
                    </option>
                  ))}
                </SelectControl>
              )}
            </FormField>
            <FormField
              label="Teacher"
              error={errors.teacher_id?.message}
              hint="Only teachers of the chosen department can teach the course."
            >
              {(p) => (
                <SelectControl control={control} name="teacher_id" fieldProps={p}>
                  <option value="">No teacher yet</option>
                  {departmentId !== '' &&
                    teachers.data?.items.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.first_name} {t.last_name}
                      </option>
                    ))}
                </SelectControl>
              )}
            </FormField>
          </>
        )}
      </form>
    </Modal>
  );
}
