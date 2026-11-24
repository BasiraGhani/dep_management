import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { useChangePassword } from '../../hooks/useUsers';
import { applyServerErrors } from '../../lib/formErrors';
import { FormField, inputClass } from '../FormField';
import { useToast } from '../useToast';

const schema = z
  .object({
    current_password: z.string().min(1, 'Enter your current password'),
    new_password: z.string().min(8, 'At least 8 characters').max(128, 'At most 128 characters'),
    confirm_password: z.string(),
  })
  .superRefine((v, ctx) => {
    if (v.new_password && v.new_password === v.current_password) {
      ctx.addIssue({
        code: 'custom',
        path: ['new_password'],
        message: 'Choose a password different from the current one',
      });
    }
    if (v.confirm_password !== v.new_password) {
      ctx.addIssue({
        code: 'custom',
        path: ['confirm_password'],
        message: "Passwords don't match",
      });
    }
  });

type FormValues = z.infer<typeof schema>;
const FIELDS = ['current_password', 'new_password'] as const;
const EMPTY: FormValues = { current_password: '', new_password: '', confirm_password: '' };

/** FR-1.6: change your own password by giving the current one. */
export function ChangePasswordForm() {
  const toast = useToast();
  const change = useChangePassword();
  const {
    register,
    handleSubmit,
    setError,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: EMPTY });

  const onSubmit = handleSubmit(async (v) => {
    try {
      await change.mutateAsync({
        current_password: v.current_password,
        new_password: v.new_password,
      });
      reset(EMPTY);
      toast.success('Password changed');
    } catch (error) {
      // e.g. 400 "Current password is incorrect" goes under that field.
      applyServerErrors(error, setError, FIELDS, { 'current password': 'current_password' });
    }
  });

  return (
    <section aria-labelledby="password-heading" className="rounded-lg border bg-white p-4">
      <h2 id="password-heading" className="mb-3 text-lg font-semibold text-slate-800">
        Change password
      </h2>
      <form
        className="max-w-md space-y-4"
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
        <FormField label="Current password" required error={errors.current_password?.message}>
          {(p) => (
            <input
              {...p}
              type="password"
              autoComplete="current-password"
              {...register('current_password')}
              className={inputClass}
            />
          )}
        </FormField>
        <FormField
          label="New password"
          required
          error={errors.new_password?.message}
          hint="Use 8 or more characters."
        >
          {(p) => (
            <input
              {...p}
              type="password"
              autoComplete="new-password"
              {...register('new_password')}
              className={inputClass}
            />
          )}
        </FormField>
        <FormField label="Confirm new password" required error={errors.confirm_password?.message}>
          {(p) => (
            <input
              {...p}
              type="password"
              autoComplete="new-password"
              {...register('confirm_password')}
              className={inputClass}
            />
          )}
        </FormField>
        <button
          type="submit"
          disabled={isSubmitting}
          className="rounded bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700 disabled:opacity-60"
        >
          {isSubmitting ? 'Changing…' : 'Change password'}
        </button>
      </form>
    </section>
  );
}
