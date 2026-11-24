import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ToastProvider } from './ToastProvider';
import { useToast } from './useToast';

function Buttons() {
  const toast = useToast();
  return (
    <>
      <button
        type="button"
        onClick={() => {
          toast.success('Course saved');
        }}
      >
        ok
      </button>
      <button
        type="button"
        onClick={() => {
          toast.error('A1 is full for 2026-Fall (2 / 2)');
        }}
      >
        fail
      </button>
    </>
  );
}

afterEach(() => {
  vi.useRealTimers();
});

describe('toasts', () => {
  it('shows a success toast that disappears on its own', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const user = userEvent.setup({ advanceTimers: (ms) => vi.advanceTimersByTime(ms) });
    render(
      <ToastProvider duration={4000}>
        <Buttons />
      </ToastProvider>,
    );

    await user.click(screen.getByRole('button', { name: 'ok' }));
    expect(screen.getByRole('status')).toHaveTextContent('Course saved');

    act(() => {
      vi.advanceTimersByTime(4000);
    });
    expect(screen.queryByText('Course saved')).not.toBeInTheDocument();
  });

  it('keeps an error toast until it is dismissed', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const user = userEvent.setup({ advanceTimers: (ms) => vi.advanceTimersByTime(ms) });
    render(
      <ToastProvider duration={4000}>
        <Buttons />
      </ToastProvider>,
    );

    await user.click(screen.getByRole('button', { name: 'fail' }));
    act(() => {
      vi.advanceTimersByTime(10_000);
    });
    expect(screen.getByRole('alert')).toHaveTextContent('A1 is full for 2026-Fall (2 / 2)');

    await user.click(screen.getByRole('button', { name: 'Dismiss' }));
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('stacks several toasts', async () => {
    const user = userEvent.setup();
    render(
      <ToastProvider>
        <Buttons />
      </ToastProvider>,
    );

    await user.click(screen.getByRole('button', { name: 'ok' }));
    await user.click(screen.getByRole('button', { name: 'fail' }));

    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('useToast outside the provider is a programming error', () => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
    expect(() => render(<Buttons />)).toThrow('useToast() must be used inside <ToastProvider>');
  });
});
