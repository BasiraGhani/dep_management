import { z } from 'zod';

/** Zod rules shared by the forms; each mirrors the backend rule (schemas/common.py). */

export const personName = (label: string) =>
  z.string().trim().min(1, `Enter a ${label}`).max(60, 'At most 60 characters');

export const email = z
  .string()
  .trim()
  .min(1, 'Enter an email')
  .max(120, 'At most 120 characters')
  .regex(/^[^@\s]+@[^@\s]+\.[^@\s]+$/, 'Enter a valid email');

/** Optional phone: empty, or digits, spaces and + ( ) - (3–30 characters). */
export const optionalPhone = z
  .string()
  .trim()
  .refine((v) => v === '' || /^\+?[0-9()\- ]{3,30}$/.test(v), 'Digits, spaces, + ( ) - only');

export const todayIso = () => new Date().toISOString().slice(0, 10);

/** An optional yyyy-mm-dd date that can't be after today. */
export const optionalPastDate = z
  .string()
  .refine((v) => v === '' || v <= todayIso(), "Can't be in the future");

/** Form fields for the optional login account created with a teacher or student. */
export const accountFields = {
  create_account: z.boolean(),
  username: z.string().trim(),
  temp_password: z.string(),
};

/** Adds username/password errors when "create a login account" is ticked. */
export function checkAccount(
  v: { create_account: boolean; username: string; temp_password: string },
  ctx: z.RefinementCtx,
): void {
  if (!v.create_account) return;
  if (!/^[A-Za-z0-9._-]{3,50}$/.test(v.username)) {
    ctx.addIssue({
      code: 'custom',
      path: ['username'],
      message: '3–50 letters, digits, dots, dashes or underscores',
    });
  }
  if (v.temp_password.length < 8 || v.temp_password.length > 128) {
    ctx.addIssue({ code: 'custom', path: ['temp_password'], message: 'At least 8 characters' });
  }
}
