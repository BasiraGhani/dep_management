import type { ReactNode } from 'react';
import { Controller, type Control, type FieldValues, type Path } from 'react-hook-form';

import { inputClass, type FieldProps } from './FormField';

interface SelectControlProps<T extends FieldValues> {
  control: Control<T>;
  name: Path<T>;
  /** The props FormField passes to its field (id, aria-*). */
  fieldProps: FieldProps;
  children: ReactNode;
  /** Called after the value changes, e.g. to reset a dependent field. */
  onValueChange?: (value: string) => void;
}

/**
 * A <select> bound to the form as a controlled field. Use it when the options load
 * after the form opens (departments, teachers): an uncontrolled select would show
 * the first option while the form still holds the real value.
 */
export function SelectControl<T extends FieldValues>({
  control,
  name,
  fieldProps,
  children,
  onValueChange,
}: SelectControlProps<T>) {
  return (
    <Controller
      control={control}
      name={name}
      render={({ field }) => (
        <select
          {...fieldProps}
          name={field.name}
          ref={field.ref}
          value={field.value}
          onBlur={field.onBlur}
          onChange={(event) => {
            field.onChange(event.target.value);
            onValueChange?.(event.target.value);
          }}
          className={inputClass}
        >
          {children}
        </select>
      )}
    />
  );
}
