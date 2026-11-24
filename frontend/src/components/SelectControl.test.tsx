import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useForm } from 'react-hook-form';
import { describe, expect, it, vi } from 'vitest';

import { FormField } from './FormField';
import { SelectControl } from './SelectControl';

function Form({ options, onTeacherChange }: { options: string[]; onTeacherChange?: () => void }) {
  const { control } = useForm({ defaultValues: { teacher: 'Hopper' } });
  return (
    <FormField label="Teacher">
      {(p) => (
        <SelectControl
          control={control}
          name="teacher"
          fieldProps={p}
          onValueChange={onTeacherChange}
        >
          <option value="">None</option>
          {options.map((o) => (
            <option key={o} value={o}>
              {o}
            </option>
          ))}
        </SelectControl>
      )}
    </FormField>
  );
}

describe('SelectControl', () => {
  it('shows the form value once options that load later arrive (regression)', () => {
    const { rerender } = render(<Form options={[]} />); // options still loading

    rerender(<Form options={['Kay', 'Hopper']} />);

    expect(screen.getByLabelText('Teacher')).toHaveValue('Hopper');
  });

  it('updates the form value and reports changes', async () => {
    const onTeacherChange = vi.fn();
    render(<Form options={['Kay', 'Hopper']} onTeacherChange={onTeacherChange} />);

    await userEvent.setup().selectOptions(screen.getByLabelText('Teacher'), 'Kay');

    expect(screen.getByLabelText('Teacher')).toHaveValue('Kay');
    expect(onTeacherChange).toHaveBeenCalledWith('Kay');
  });
});
