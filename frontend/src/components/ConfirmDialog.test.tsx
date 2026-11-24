import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { ConfirmDialog } from './ConfirmDialog';

function setup(pending = false) {
  const onConfirm = vi.fn();
  const onCancel = vi.fn();
  render(
    <ConfirmDialog
      open
      title="Delete student?"
      message="Their enrollments are deleted too."
      pending={pending}
      onConfirm={onConfirm}
      onCancel={onCancel}
    />,
  );
  return { onConfirm, onCancel, user: userEvent.setup() };
}

describe('ConfirmDialog', () => {
  it('asks the question and confirms', async () => {
    const { onConfirm, onCancel, user } = setup();

    expect(screen.getByRole('dialog', { name: 'Delete student?' })).toHaveTextContent(
      'Their enrollments are deleted too.',
    );
    await user.click(screen.getByRole('button', { name: 'Delete' }));

    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onCancel).not.toHaveBeenCalled();
  });

  it('cancels with the Cancel button or Escape', async () => {
    const { onConfirm, onCancel, user } = setup();

    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    await user.keyboard('{Escape}');

    expect(onCancel).toHaveBeenCalledTimes(2);
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it('disables both buttons while the action runs', async () => {
    const { onCancel, user } = setup(true);

    expect(screen.getByRole('button', { name: 'Working…' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled();
    await user.keyboard('{Escape}');
    expect(onCancel).not.toHaveBeenCalled();
  });
});
