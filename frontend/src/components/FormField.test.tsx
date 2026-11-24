import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { FormField, inputClass } from './FormField';

describe('FormField', () => {
  it('links the label to the field', () => {
    render(
      <FormField label="Course code">
        {(props) => <input {...props} className={inputClass} />}
      </FormField>,
    );

    const input = screen.getByLabelText('Course code');
    expect(input).not.toHaveAttribute('aria-invalid');
    expect(input).not.toHaveAttribute('aria-describedby');
  });

  it('shows an error, marks the field invalid and links the message', () => {
    render(
      <FormField label="Course code" error="Code is required" hint="Letters and digits" required>
        {(props) => <input {...props} />}
      </FormField>,
    );

    const input = screen.getByLabelText(/Course code/);
    expect(input).toHaveAttribute('aria-invalid', 'true');
    expect(input).toHaveAccessibleDescription('Letters and digits Code is required');
    expect(screen.getByText('Code is required')).toBeInTheDocument();
  });
});
