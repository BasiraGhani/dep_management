import { AxiosError } from 'axios';
import type { FieldValues, Path, UseFormSetError } from 'react-hook-form';

import { errorMessage } from '../api/client';
import type { ApiErrorBody } from '../types';

/**
 * Show a failed save in the form: field errors from a 422 go under their fields,
 * a message that names one of `fields` (e.g. "A department with code 'CS' already
 * exists") goes under that field, and anything else goes to the form's root error.
 */
export function applyServerErrors<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>,
  fields: readonly Path<T>[],
): void {
  const detail =
    error instanceof AxiosError
      ? (error.response?.data as Partial<ApiErrorBody> | undefined)?.detail
      : undefined;

  if (Array.isArray(detail)) {
    let placed = false;
    for (const item of detail) {
      const field = item.loc.at(-1);
      if (typeof field === 'string' && (fields as readonly string[]).includes(field)) {
        setError(field as Path<T>, { type: 'server', message: item.msg });
        placed = true;
      }
    }
    if (placed) return;
  }

  const message = errorMessage(error, 'Could not save. Please try again.');
  if (typeof detail === 'string') {
    const lower = detail.toLowerCase();
    const named = fields.find((field) =>
      [field, field.replace(/_id$/, ''), field.replace(/_/g, ' ')].some((word) =>
        new RegExp(`\\b${word}\\b`).test(lower),
      ),
    );
    if (named) {
      setError(named, { type: 'server', message });
      return;
    }
  }
  setError('root', { type: 'server', message });
}

/** '' -> null, so cleared optional fields are sent as null rather than "". */
export function emptyToNull(value: string | null | undefined): string | null {
  const trimmed = (value ?? '').trim();
  return trimmed === '' ? null : trimmed;
}
