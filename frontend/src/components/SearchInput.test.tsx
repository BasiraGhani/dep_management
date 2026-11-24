import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { SearchInput } from './SearchInput';

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
});
afterEach(() => {
  vi.useRealTimers();
});

describe('SearchInput', () => {
  it('reports the trimmed text once typing pauses (debounced)', async () => {
    const onSearch = vi.fn();
    const user = userEvent.setup({ advanceTimers: (ms) => vi.advanceTimersByTime(ms) });
    render(<SearchInput label="Search courses" onSearch={onSearch} delay={300} />);

    await user.type(screen.getByLabelText('Search courses'), ' cs10 ');
    expect(onSearch).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(300);
    });
    expect(onSearch).toHaveBeenCalledTimes(1);
    expect(onSearch).toHaveBeenCalledWith('cs10');
  });

  it('does not search on first render', () => {
    const onSearch = vi.fn();
    render(<SearchInput onSearch={onSearch} initialValue="cs" />);

    act(() => {
      vi.advanceTimersByTime(1000);
    });

    expect(onSearch).not.toHaveBeenCalled();
    expect(screen.getByLabelText('Search')).toHaveValue('cs');
  });

  it('reports an empty string when the box is cleared', async () => {
    const onSearch = vi.fn();
    const user = userEvent.setup({ advanceTimers: (ms) => vi.advanceTimersByTime(ms) });
    render(<SearchInput onSearch={onSearch} initialValue="cs" />);

    await user.clear(screen.getByLabelText('Search'));
    act(() => {
      vi.advanceTimersByTime(300);
    });

    expect(onSearch).toHaveBeenLastCalledWith('');
  });
});
