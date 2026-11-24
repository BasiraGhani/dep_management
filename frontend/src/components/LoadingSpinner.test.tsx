import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { LoadingSpinner } from './LoadingSpinner';

describe('LoadingSpinner', () => {
  it('announces loading to screen readers', () => {
    render(<LoadingSpinner />);
    expect(screen.getByRole('status')).toHaveTextContent('Loading…');
  });

  it('accepts a custom label', () => {
    render(<LoadingSpinner label="Loading courses…" />);
    expect(screen.getByRole('status')).toHaveTextContent('Loading courses…');
  });
});
