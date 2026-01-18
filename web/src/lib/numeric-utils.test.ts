/**
 * Tests for numeric validation and formatting utilities.
 *
 * Story 12.4: Dashboard Stats Cards
 */

import { describe, it, expect } from 'vitest';
import {
  isValidNumeric,
  formatNumericOrFallback,
  formatMemoryAdaptive,
} from './numeric-utils';

describe('isValidNumeric', () => {
  it('returns true for positive numbers', () => {
    expect(isValidNumeric(123)).toBe(true);
    expect(isValidNumeric(0.5)).toBe(true);
    expect(isValidNumeric(999999)).toBe(true);
  });

  it('returns true for zero', () => {
    expect(isValidNumeric(0)).toBe(true);
  });

  it('returns false for negative numbers', () => {
    expect(isValidNumeric(-1)).toBe(false);
    expect(isValidNumeric(-0.5)).toBe(false);
    expect(isValidNumeric(-999999)).toBe(false);
  });

  it('returns false for NaN', () => {
    expect(isValidNumeric(NaN)).toBe(false);
  });

  it('returns false for Infinity', () => {
    expect(isValidNumeric(Infinity)).toBe(false);
    expect(isValidNumeric(-Infinity)).toBe(false);
  });

  it('returns false for null', () => {
    expect(isValidNumeric(null)).toBe(false);
  });

  it('returns false for undefined', () => {
    expect(isValidNumeric(undefined)).toBe(false);
  });
});

describe('formatNumericOrFallback', () => {
  it('formats valid numbers with default decimals', () => {
    expect(formatNumericOrFallback(123.456)).toBe('123.5');
    expect(formatNumericOrFallback(0)).toBe('0.0');
    expect(formatNumericOrFallback(100)).toBe('100.0');
  });

  it('formats numbers with custom decimal places', () => {
    expect(formatNumericOrFallback(123.456, 2)).toBe('123.46');
    expect(formatNumericOrFallback(123.456, 0)).toBe('123');
    expect(formatNumericOrFallback(123.456, 3)).toBe('123.456');
  });

  it('returns fallback for null', () => {
    expect(formatNumericOrFallback(null)).toBe('N/A');
    expect(formatNumericOrFallback(null, 1, '-')).toBe('-');
  });

  it('returns fallback for undefined', () => {
    expect(formatNumericOrFallback(undefined)).toBe('N/A');
    expect(formatNumericOrFallback(undefined, 1, 'Unknown')).toBe('Unknown');
  });

  it('returns fallback for NaN', () => {
    expect(formatNumericOrFallback(NaN)).toBe('N/A');
  });

  it('returns fallback for Infinity', () => {
    expect(formatNumericOrFallback(Infinity)).toBe('N/A');
    expect(formatNumericOrFallback(-Infinity)).toBe('N/A');
  });

  it('returns fallback for negative numbers', () => {
    expect(formatNumericOrFallback(-100)).toBe('N/A');
  });

  it('allows custom fallback string', () => {
    expect(formatNumericOrFallback(null, 1, 'N/A')).toBe('N/A');
    expect(formatNumericOrFallback(null, 1, '-')).toBe('-');
    expect(formatNumericOrFallback(null, 1, 'Unknown')).toBe('Unknown');
  });
});

describe('formatMemoryAdaptive', () => {
  it('formats values under 1024 MB in MB', () => {
    expect(formatMemoryAdaptive(512)).toBe('512.0 MB');
    expect(formatMemoryAdaptive(128.5)).toBe('128.5 MB');
    expect(formatMemoryAdaptive(0)).toBe('0.0 MB');
    expect(formatMemoryAdaptive(1023.9)).toBe('1023.9 MB');
  });

  it('formats values >= 1024 MB in GB', () => {
    expect(formatMemoryAdaptive(1024)).toBe('1.0 GB');
    expect(formatMemoryAdaptive(2048)).toBe('2.0 GB');
    expect(formatMemoryAdaptive(2560)).toBe('2.5 GB');
    expect(formatMemoryAdaptive(4096)).toBe('4.0 GB');
  });

  it('handles fractional GB values', () => {
    expect(formatMemoryAdaptive(1536)).toBe('1.5 GB');
    expect(formatMemoryAdaptive(3584)).toBe('3.5 GB');
  });

  it('returns fallback for null', () => {
    expect(formatMemoryAdaptive(null)).toBe('N/A');
    expect(formatMemoryAdaptive(null, '-')).toBe('-');
  });

  it('returns fallback for undefined', () => {
    expect(formatMemoryAdaptive(undefined)).toBe('N/A');
  });

  it('returns fallback for NaN', () => {
    expect(formatMemoryAdaptive(NaN)).toBe('N/A');
  });

  it('returns fallback for Infinity', () => {
    expect(formatMemoryAdaptive(Infinity)).toBe('N/A');
  });

  it('returns fallback for negative values', () => {
    expect(formatMemoryAdaptive(-100)).toBe('N/A');
  });
});
