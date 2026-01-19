/**
 * Tests for duration parsing and formatting utilities.
 *
 * VSS-s9s: Human-readable duration input for refresh intervals
 */

import { describe, it, expect } from 'vitest';
import {
  parseDuration,
  formatDuration,
  formatDurationSimple,
} from './duration-utils';

describe('parseDuration', () => {
  describe('plain numbers (seconds)', () => {
    it('parses plain integer as seconds', () => {
      const result = parseDuration('300');
      expect(result.success).toBe(true);
      expect(result.seconds).toBe(300);
    });

    it('parses zero', () => {
      const result = parseDuration('0');
      expect(result.success).toBe(true);
      expect(result.seconds).toBe(0);
    });
  });

  describe('seconds unit', () => {
    it.each([
      ['30s', 30],
      ['30sec', 30],
      ['30secs', 30],
      ['30 second', 30],
      ['30 seconds', 30],
      ['30 s', 30],
    ])('parses "%s" as %d seconds', (input, expected) => {
      const result = parseDuration(input);
      expect(result.success).toBe(true);
      expect(result.seconds).toBe(expected);
    });
  });

  describe('minutes unit', () => {
    it.each([
      ['5m', 300],
      ['5min', 300],
      ['5mins', 300],
      ['5 minute', 300],
      ['5 minutes', 300],
      ['30m', 1800],
    ])('parses "%s" as %d seconds', (input, expected) => {
      const result = parseDuration(input);
      expect(result.success).toBe(true);
      expect(result.seconds).toBe(expected);
    });
  });

  describe('hours unit', () => {
    it.each([
      ['1h', 3600],
      ['1hr', 3600],
      ['1hrs', 3600],
      ['1 hour', 3600],
      ['1 hours', 3600],
      ['4h', 14400],
      ['24h', 86400],
    ])('parses "%s" as %d seconds', (input, expected) => {
      const result = parseDuration(input);
      expect(result.success).toBe(true);
      expect(result.seconds).toBe(expected);
    });
  });

  describe('days unit', () => {
    it.each([
      ['1d', 86400],
      ['1 day', 86400],
      ['1 days', 86400],
      ['7d', 604800],
    ])('parses "%s" as %d seconds', (input, expected) => {
      const result = parseDuration(input);
      expect(result.success).toBe(true);
      expect(result.seconds).toBe(expected);
    });
  });

  describe('compound durations', () => {
    it.each([
      ['1h30m', 5400],
      ['1h 30m', 5400],
      ['2h30m45s', 9045],
      ['1d12h', 129600],
      ['1d 12h 30m', 131400],
    ])('parses "%s" as %d seconds', (input, expected) => {
      const result = parseDuration(input);
      expect(result.success).toBe(true);
      expect(result.seconds).toBe(expected);
    });
  });

  describe('decimal values', () => {
    it('parses decimal hours', () => {
      const result = parseDuration('1.5h');
      expect(result.success).toBe(true);
      expect(result.seconds).toBe(5400);
    });

    it('parses decimal minutes', () => {
      const result = parseDuration('2.5m');
      expect(result.success).toBe(true);
      expect(result.seconds).toBe(150);
    });
  });

  describe('case insensitivity', () => {
    it.each([
      ['4H', 14400],
      ['30M', 1800],
      ['1D', 86400],
      ['1HOUR', 3600],
    ])('parses "%s" (uppercase) correctly', (input, expected) => {
      const result = parseDuration(input);
      expect(result.success).toBe(true);
      expect(result.seconds).toBe(expected);
    });
  });

  describe('whitespace handling', () => {
    it('trims leading/trailing whitespace', () => {
      const result = parseDuration('  4h  ');
      expect(result.success).toBe(true);
      expect(result.seconds).toBe(14400);
    });

    it('handles internal whitespace', () => {
      const result = parseDuration('1 h 30 m');
      expect(result.success).toBe(true);
      expect(result.seconds).toBe(5400);
    });
  });

  describe('error cases', () => {
    it('rejects empty string', () => {
      const result = parseDuration('');
      expect(result.success).toBe(false);
      expect(result.error).toBe('Duration cannot be empty');
    });

    it('rejects whitespace-only string', () => {
      const result = parseDuration('   ');
      expect(result.success).toBe(false);
      expect(result.error).toBe('Duration cannot be empty');
    });

    it('rejects unknown unit', () => {
      const result = parseDuration('5w');
      expect(result.success).toBe(false);
      expect(result.error).toContain('Unknown unit');
    });

    it('rejects invalid format', () => {
      const result = parseDuration('invalid');
      expect(result.success).toBe(false);
      expect(result.error).toContain('Invalid duration format');
    });

    it('rejects text before number', () => {
      const result = parseDuration('about 5m');
      expect(result.success).toBe(false);
      expect(result.error).toContain('unexpected');
    });
  });
});

describe('formatDuration', () => {
  describe('single units', () => {
    it.each([
      [30, '30s'],
      [60, '1m'],
      [90, '1m 30s'],
      [3600, '1h'],
      [5400, '1h 30m'],
      [86400, '1d'],
      [90000, '1d 1h'],
    ])('formats %d seconds as "%s"', (seconds, expected) => {
      expect(formatDuration(seconds)).toBe(expected);
    });
  });

  describe('edge cases', () => {
    it('formats zero', () => {
      expect(formatDuration(0)).toBe('0s');
    });

    it('handles negative values', () => {
      expect(formatDuration(-100)).toBe('0s');
    });

    it('handles NaN', () => {
      expect(formatDuration(NaN)).toBe('0s');
    });

    it('handles Infinity', () => {
      expect(formatDuration(Infinity)).toBe('0s');
    });
  });

  describe('verbose mode', () => {
    it.each([
      [30, '30 seconds'],
      [60, '1 minute'],
      [90, '1 minute 30 seconds'],
      [3600, '1 hour'],
      [7200, '2 hours'],
      [86400, '1 day'],
      [172800, '2 days'],
    ])('formats %d seconds verbosely as "%s"', (seconds, expected) => {
      expect(formatDuration(seconds, { verbose: true })).toBe(expected);
    });

    it('uses singular forms correctly', () => {
      expect(formatDuration(1, { verbose: true })).toBe('1 second');
      expect(formatDuration(60, { verbose: true })).toBe('1 minute');
      expect(formatDuration(3600, { verbose: true })).toBe('1 hour');
      expect(formatDuration(86400, { verbose: true })).toBe('1 day');
    });
  });

  describe('rounding', () => {
    it('rounds fractional seconds', () => {
      expect(formatDuration(30.7)).toBe('31s');
      expect(formatDuration(30.4)).toBe('30s');
    });
  });
});

describe('formatDurationSimple', () => {
  describe('exact unit values', () => {
    it.each([
      [60, '1m'],
      [300, '5m'],
      [3600, '1h'],
      [14400, '4h'],
      [86400, '1d'],
      [604800, '7d'],
    ])('formats %d seconds as "%s"', (seconds, expected) => {
      expect(formatDurationSimple(seconds)).toBe(expected);
    });
  });

  describe('compound values', () => {
    it.each([
      [90, '1m 30s'],      // 90s has no exact unit, falls through to formatDuration
      [5400, '90m'],       // 90 minutes exactly - uses minute form
      [90000, '25h'],      // 25 hours exactly - uses hour form
      [93600, '26h'],      // 26 hours exactly - uses hour form
      [93660, '1561m'],    // 1561 minutes exactly - uses minute form
      [93661, '1d 2h 1m 1s'], // True compound - no exact unit match
    ])('formats %d seconds as "%s"', (seconds, expected) => {
      expect(formatDurationSimple(seconds)).toBe(expected);
    });
  });

  describe('edge cases', () => {
    it('formats zero', () => {
      expect(formatDurationSimple(0)).toBe('0s');
    });

    it('handles seconds less than a minute', () => {
      expect(formatDurationSimple(45)).toBe('45s');
    });

    it('handles negative values', () => {
      expect(formatDurationSimple(-100)).toBe('0s');
    });
  });
});

describe('round-trip consistency', () => {
  it.each([
    '30s',
    '5m',
    '1h',
    '4h',
    '1d',
    '1h30m',
  ])('parses and formats "%s" back to equivalent', (input) => {
    const parsed = parseDuration(input);
    expect(parsed.success).toBe(true);
    const formatted = formatDurationSimple(parsed.seconds);
    // Re-parse the formatted output should give same seconds
    const reparsed = parseDuration(formatted);
    expect(reparsed.success).toBe(true);
    expect(reparsed.seconds).toBe(parsed.seconds);
  });
});
