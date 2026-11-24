import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { Modal } from './Modal';

describe('Modal', () => {
  it('renders nothing when closed', () => {
    render(
      <Modal open={false} title="Edit course" onClose={vi.fn()}>
        Body
      </Modal>,
    );
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('is an accessible dialog named by its title, and takes focus', () => {
    render(
      <Modal
        open
        title="Edit course"
        onClose={vi.fn()}
        footer={<button type="button">Save</button>}
      >
        Body text
      </Modal>,
    );

    const dialog = screen.getByRole('dialog', { name: 'Edit course' });
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(dialog).toHaveFocus();
    expect(screen.getByText('Body text')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Save' })).toBeInTheDocument();
  });

  it.each([
    [
      'the Close button',
      async (user: ReturnType<typeof userEvent.setup>) => {
        await user.click(screen.getByRole('button', { name: 'Close' }));
      },
    ],
    [
      'Escape',
      async (user: ReturnType<typeof userEvent.setup>) => {
        await user.keyboard('{Escape}');
      },
    ],
    [
      'a backdrop click',
      async (user: ReturnType<typeof userEvent.setup>) => {
        const backdrop = screen.getByRole('dialog').parentElement;
        if (backdrop) await user.click(backdrop);
      },
    ],
  ])('closes with %s', async (_how, close) => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(
      <Modal open title="Edit course" onClose={onClose}>
        Body
      </Modal>,
    );

    await close(user);

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('does not close when clicking inside the dialog', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(
      <Modal open title="Edit course" onClose={onClose}>
        Body
      </Modal>,
    );

    await user.click(screen.getByText('Body'));

    expect(onClose).not.toHaveBeenCalled();
  });

  it('returns focus to where it was when closed', () => {
    const { rerender } = render(
      <>
        <button type="button">Open</button>
        <Modal open={false} title="Edit" onClose={vi.fn()}>
          Body
        </Modal>
      </>,
    );
    screen.getByRole('button', { name: 'Open' }).focus();

    rerender(
      <>
        <button type="button">Open</button>
        <Modal open title="Edit" onClose={vi.fn()}>
          Body
        </Modal>
      </>,
    );
    expect(screen.getByRole('dialog')).toHaveFocus();

    rerender(
      <>
        <button type="button">Open</button>
        <Modal open={false} title="Edit" onClose={vi.fn()}>
          Body
        </Modal>
      </>,
    );
    expect(screen.getByRole('button', { name: 'Open' })).toHaveFocus();
  });
});
