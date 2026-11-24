import { useEffect, useId, useRef, useState } from 'react';

interface SearchInputProps {
  /** Called with the trimmed text once typing pauses for `delay` ms. */
  onSearch: (value: string) => void;
  label?: string;
  placeholder?: string;
  initialValue?: string;
  delay?: number;
}

/** A labelled search box that reports its value after typing pauses (debounced). */
export function SearchInput({
  onSearch,
  label = 'Search',
  placeholder = 'Search…',
  initialValue = '',
  delay = 300,
}: SearchInputProps) {
  const id = useId();
  const [value, setValue] = useState(initialValue);
  const latest = useRef(onSearch);
  const firstRun = useRef(true);

  useEffect(() => {
    latest.current = onSearch;
  }, [onSearch]);

  useEffect(() => {
    if (firstRun.current) {
      firstRun.current = false;
      return;
    }
    const timer = window.setTimeout(() => {
      latest.current(value.trim());
    }, delay);
    return () => {
      window.clearTimeout(timer);
    };
  }, [value, delay]);

  return (
    <div className="relative w-full max-w-xs">
      <label htmlFor={id} className="sr-only">
        {label}
      </label>
      <input
        id={id}
        type="search"
        value={value}
        placeholder={placeholder}
        onChange={(event) => {
          setValue(event.target.value);
        }}
        className="w-full rounded border border-slate-300 px-3 py-2 focus:border-blue-500 focus:outline-none"
      />
    </div>
  );
}
