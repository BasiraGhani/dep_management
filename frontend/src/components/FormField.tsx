import { useId, type ReactNode } from 'react';

/** Props to spread on the field's input so the label and messages are linked. */
export interface FieldProps {
  id: string;
  'aria-invalid': true | undefined;
  'aria-describedby': string | undefined;
}

interface FormFieldProps {
  label: string;
  /** A validation or server error; shown under the field and marks it invalid. */
  error?: string;
  hint?: string;
  required?: boolean;
  /** Render the input with the given props, e.g. `(p) => <input {...p} {...register('x')} />`. */
  children: (props: FieldProps) => ReactNode;
}

/** A label, the field, an optional hint and an error, wired together for screen readers. */
export function FormField({ label, error, hint, required, children }: FormFieldProps) {
  const id = useId();
  const hintId = `${id}-hint`;
  const errorId = `${id}-error`;
  const describedBy = [hint ? hintId : null, error ? errorId : null].filter(Boolean).join(' ');

  return (
    <div className="space-y-1">
      <label htmlFor={id} className="block text-sm font-medium text-slate-700">
        {label}
        {required && (
          <span className="text-red-600" aria-hidden="true">
            {' '}
            *
          </span>
        )}
      </label>
      {children({
        id,
        'aria-invalid': error ? true : undefined,
        'aria-describedby': describedBy || undefined,
      })}
      {hint && (
        <p id={hintId} className="text-sm text-slate-500">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} className="text-sm text-red-600">
          {error}
        </p>
      )}
    </div>
  );
}

const fieldLook =
  'rounded border border-slate-300 px-3 py-2 focus:border-blue-500 focus:outline-none aria-[invalid=true]:border-red-500';

/** Tailwind classes for text inputs and selects inside a FormField. */
export const inputClass = `w-full ${fieldLook}`;

/** Filter selects above a list: full width on phones, side by side from tablet width up. */
export const filterClass = `w-full sm:w-auto ${fieldLook}`;
