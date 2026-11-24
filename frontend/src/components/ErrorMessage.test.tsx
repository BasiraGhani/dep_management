import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { apiError, networkError } from '../test/fixtures';
import { ErrorMessage } from './ErrorMessage';

describe('ErrorMessage', () => {
  it("shows the API's message", () => {
    render(<ErrorMessage error={apiError(409, 'Course CS101 has 18 enrollments')} />);
    expect(screen.getByRole('alert')).toHaveTextContent('Course CS101 has 18 enrollments');
  });

  it('explains network errors', () => {
    render(<ErrorMessage error={networkError} />);
    expect(screen.getByRole('alert')).toHaveTextContent('Cannot reach the server');
  });

  it('uses the fallback for other errors', () => {
    render(<ErrorMessage error={new Error('x')} fallback="Could not load courses." />);
    expect(screen.getByRole('alert')).toHaveTextContent('Could not load courses.');
  });

  it('offers a retry when given one', async () => {
    const onRetry = vi.fn();
    render(<ErrorMessage error={networkError} onRetry={onRetry} />);

    await userEvent.setup().click(screen.getByRole('button', { name: 'Try again' }));

    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('has no retry button by default', () => {
    render(<ErrorMessage error={networkError} />);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});
