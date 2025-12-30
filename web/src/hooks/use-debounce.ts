/**
 * useDebounce - Debounces a value by delaying updates until after a period of inactivity.
 *
 * Useful for search inputs where you want to wait for the user to stop typing
 * before making an API request.
 */

import { useState, useEffect } from 'react';

/**
 * Returns a debounced version of the input value.
 *
 * The returned value only updates after `delay` milliseconds have passed
 * since the last change to the input value.
 *
 * @param value - The value to debounce
 * @param delay - Delay in milliseconds (default: 300)
 * @returns The debounced value
 *
 * @example
 * function SearchInput() {
 *   const [inputValue, setInputValue] = useState('');
 *   const debouncedValue = useDebounce(inputValue, 300);
 *
 *   useEffect(() => {
 *     // This only runs 300ms after the user stops typing
 *     if (debouncedValue) {
 *       fetchSearchResults(debouncedValue);
 *     }
 *   }, [debouncedValue]);
 *
 *   return <input value={inputValue} onChange={e => setInputValue(e.target.value)} />;
 * }
 */
export function useDebounce<T>(value: T, delay = 300): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(timer);
    };
  }, [value, delay]);

  return debouncedValue;
}
