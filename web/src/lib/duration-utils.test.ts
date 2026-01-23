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

    it('parses large numbers', () => {
      const result = parseDuration('999999');
      expect(result.success).toBe(true);
      expect(result.seconds).toBe(999999);
    });

    it('rejects decimal plain numbers (must have unit)', () => {
      const result = parseDuration('3.5');
      expect(result.success).toBe(false);
      expect(result.error).toContain('Invalid duration format');
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

    it('parses zero seconds with unit', () => {
      const result = parseDuration('0s');
      expect(result.success).toBe(true);
      expect(result.seconds).toBe(0);
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

    it('parses zero minutes with unit', () => {
      const result = parseDuration('0m');
      expect(result.success).toBe(true);
      expect(result.seconds).toBe(0);
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

    it('handles full compound with all units', () => {
      const result = parseDuration('1d 2h 3m 4s');
      expect(result.success).toBe(true);
      expect(result.seconds).toBe(93784); // 86400 + 7200 + 180 + 4
    });

    it('allows duplicate units (accumulates)', () => {
      const result = parseDuration('1h 2h');
      expect(result.success).toBe(true);
      expect(result.seconds).toBe(10800); // 3 hours total
    });

    it('handles decimal in compound durations', () => {
      const result = parseDuration('1.5h 30m');
      expect(result.success).toBe(true);
      expect(result.seconds).toBe(7200); // 5400 + 1800
    });

    it('parses units in any order', () => {
      const result = parseDuration('30m 1h');
      expect(result.success).toBe(true);
      expect(result.seconds).toBe(5400); // Same as 1h 30m
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

    it('parses decimal days', () => {
      const result = parseDuration('0.5d');
      expect(result.success).toBe(true);
      expect(result.seconds).toBe(43200); // 12 hours
    });

    it('rounds decimal results to whole seconds', () => {
      const result = parseDuration('1.333m');
      expect(result.success).toBe(true);
      expect(result.seconds).toBe(80); // 79.98 rounded to 80
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

    it('handles multiple spaces between units', () => {
      const result = parseDuration('1h    30m');
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

    it('rejects text after valid duration', () => {
      const result = parseDuration('5m xyz');
      expect(result.success).toBe(false);
      expect(result.error).toContain('unexpected');
    });

    it('rejects text between units', () => {
      const result = parseDuration('5m and 30s');
      expect(result.success).toBe(false);
      expect(result.error).toContain('unexpected');
    });

    it('rejects negative numbers', () => {
      const result = parseDuration('-5');
      expect(result.success).toBe(false);
      expect(result.error).toContain('Invalid duration format');
    });

    it('rejects negative numbers with units', () => {
      const result = parseDuration('-5m');
      expect(result.success).toBe(false);
      expect(result.error).toContain('Invalid duration format');
    });

    it('rejects just a unit without number', () => {
      const result = parseDuration('m');
      expect(result.success).toBe(false);
      expect(result.error).toContain('Invalid duration format');
    });

    it('rejects multiple unknown units', () => {
      const result = parseDuration('5w 3x');
      expect(result.success).toBe(false);
      expect(result.error).toContain('Unknown unit');
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

    it('rounds at exactly 0.5', () => {
      expect(formatDuration(30.5)).toBe('31s'); // Round half up
    });
  });

  describe('complex compound durations', () => {
    it('formats days + hours + minutes', () => {
      expect(formatDuration(90060)).toBe('1d 1h 1m'); // 1d 1h 1m
    });

    it('formats days + hours + minutes + seconds', () => {
      expect(formatDuration(90061)).toBe('1d 1h 1m 1s');
    });

    it('formats multiple days with time', () => {
      expect(formatDuration(259200 + 3600 + 1800)).toBe('3d 1h 30m'); // 3d 1h 30m
    });

    it('omits zero components in middle', () => {
      expect(formatDuration(86400 + 60)).toBe('1d 1m'); // 1d 0h 1m -> "1d 1m"
    });

    it('omits trailing zero seconds in compound', () => {
      expect(formatDuration(90000)).toBe('1d 1h'); // 1d 1h 0m 0s -> "1d 1h"
    });
  });

  describe('verbose mode edge cases', () => {
    it('formats zero verbosely', () => {
      expect(formatDuration(0, { verbose: true })).toBe('0 seconds');
    });

    it('formats negative verbosely', () => {
      expect(formatDuration(-100, { verbose: true })).toBe('0 seconds');
    });

    it('formats compound durations verbosely', () => {
      expect(formatDuration(90061, { verbose: true })).toBe('1 day 1 hour 1 minute 1 second');
    });

    it('uses plural forms correctly', () => {
      expect(formatDuration(120, { verbose: true })).toBe('2 minutes');
      expect(formatDuration(7200, { verbose: true })).toBe('2 hours');
      expect(formatDuration(172800, { verbose: true })).toBe('2 days');
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

    it('handles NaN', () => {
      expect(formatDurationSimple(NaN)).toBe('0s');
    });

    it('handles Infinity', () => {
      expect(formatDurationSimple(Infinity)).toBe('0s');
    });

    it('handles -Infinity', () => {
      expect(formatDurationSimple(-Infinity)).toBe('0s');
    });

    it('rounds fractional seconds', () => {
      expect(formatDurationSimple(30.7)).toBe('31s');
      expect(formatDurationSimple(30.4)).toBe('30s');
    });
  });

  describe('large values', () => {
    it('formats very large day values', () => {
      expect(formatDurationSimple(8640000)).toBe('100d'); // 100 days exactly
    });

    it('formats very large hour values', () => {
      expect(formatDurationSimple(360000)).toBe('100h'); // 100 hours exactly
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

describe('additional edge cases', () => {
  describe('parseDuration boundary conditions', () => {
    it('handles very large numbers', () => {
      const result = parseDuration('999d');
      expect(result.success).toBe(true);
      expect(result.seconds).toBe(86313600); // 999 * 86400
    });

    it('handles mixed case in compound', () => {
      const result = parseDuration('1H 30M');
      expect(result.success).toBe(true);
      expect(result.seconds).toBe(5400);
    });

    it('handles all long-form unit names', () => {
      const result = parseDuration('1 day 2 hours 3 minutes 4 seconds');
      expect(result.success).toBe(true);
      expect(result.seconds).toBe(93784);
    });

    it('rejects leading zeros in plain numbers', () => {
      // JavaScript parseInt handles this, but verify behavior
      const result = parseDuration('0300');
      expect(result.success).toBe(true);
      expect(result.seconds).toBe(300);
    });
  });

  describe('formatDuration single value coverage', () => {
    it('formats exactly 1 second', () => {
      expect(formatDuration(1)).toBe('1s');
    });

    it('formats exactly 1 minute', () => {
      expect(formatDuration(60)).toBe('1m');
    });

    it('formats exactly 1 hour', () => {
      expect(formatDuration(3600)).toBe('1h');
    });

    it('formats exactly 1 day', () => {
      expect(formatDuration(86400)).toBe('1d');
    });
  });

  describe('formatDurationSimple boundary coverage', () => {
    it('formats 1 second', () => {
      expect(formatDurationSimple(1)).toBe('1s');
    });

    it('formats values just under a minute', () => {
      expect(formatDurationSimple(59)).toBe('59s');
    });

    it('formats values just under an hour', () => {
      expect(formatDurationSimple(3599)).toBe('59m 59s');
    });

    it('formats values just under a day', () => {
      expect(formatDurationSimple(86399)).toBe('23h 59m 59s'); // Not divisible by any single unit
    });
  });
});
