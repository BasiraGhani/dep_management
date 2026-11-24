import type { FieldErrors, UseFormRegister } from 'react-hook-form';

import { FormField, inputClass } from './FormField';

interface AccountValues {
  create_account: boolean;
  username: string;
  temp_password: string;
}

interface AccountFieldsProps<T extends AccountValues> {
  /** "teacher" or "student", used in the labels. */
  who: string;
  register: UseFormRegister<T>;
  errors: FieldErrors<T>;
  /** The current value of the create_account checkbox. */
  wantsAccount: boolean;
}

/** The optional "create a login account" section of the teacher and student forms. */
export function AccountFields<T extends AccountValues>({
  who,
  register,
  errors,
  wantsAccount,
}: AccountFieldsProps<T>) {
  // The generic form type always has these three fields (see AccountValues).
  const reg = register as unknown as UseFormRegister<AccountValues>;
  const err = errors as FieldErrors<AccountValues>;
  return (
    <fieldset className="space-y-3 rounded border border-slate-200 p-3">
      <legend className="px-1 text-sm font-medium text-slate-700">Login account</legend>
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" {...reg('create_account')} />
        Create a login account for this {who}
      </label>
      {wantsAccount && (
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField label="Username" required error={err.username?.message}>
            {(p) => <input {...p} autoComplete="off" {...reg('username')} className={inputClass} />}
          </FormField>
          <FormField
            label="Temporary password"
            required
            error={err.temp_password?.message}
            hint={`Give this to the ${who}; they can change it on their profile.`}
          >
            {(p) => (
              <input
                {...p}
                type="password"
                autoComplete="new-password"
                {...reg('temp_password')}
                className={inputClass}
              />
            )}
          </FormField>
        </div>
      )}
    </fieldset>
  );
}
