/**
 * Duration parsing and formatting utilities.
 *
 * VSS-s9s: Human-readable duration input for refresh intervals
 *
 * Provides functions to parse human-readable duration strings (e.g., "4h", "30m", "2d")
 * and format seconds back to human-readable strings.
 */

/**
 * Result of parsing a duration string.
 */
export interface ParseDurationResult {
  /** Whether parsing succeeded */
  success: boolean;
  /** Duration in seconds (only valid if success is true) */
  seconds: number;
  /** Error message (only present if success is false) */
  error?: string;
}

/**
 * Supported duration units with their multipliers to seconds.
 */
const DURATION_UNITS: Record<string, number> = {
  s: 1,
  sec: 1,
  secs: 1,
  second: 1,
  seconds: 1,
  m: 60,
  min: 60,
  mins: 60,
  minute: 60,
  minutes: 60,
  h: 3600,
  hr: 3600,
  hrs: 3600,
  hour: 3600,
  hours: 3600,
  d: 86400,
  day: 86400,
  days: 86400,
};

/**
 * Parse a human-readable duration string to seconds.
 *
 * Supports formats like:
 * - "30" or "30s" - 30 seconds
 * - "5m" or "5 min" - 5 minutes (300 seconds)
 * - "4h" or "4 hours" - 4 hours (14400 seconds)
 * - "1d" or "1 day" - 1 day (86400 seconds)
 * - "1h30m" or "1h 30m" - 1 hour 30 minutes (5400 seconds)
 *
 * @param input - The duration string to parse
 * @returns ParseDurationResult with success status, seconds, and optional error
 *
 * @example
 * parseDuration("4h")      // { success: true, seconds: 14400 }
 * parseDuration("30m")     // { success: true, seconds: 1800 }
 * parseDuration("1h30m")   // { success: true, seconds: 5400 }
 * parseDuration("300")     // { success: true, seconds: 300 }
 * parseDuration("invalid") // { success: false, seconds: 0, error: "..." }
 */
export function parseDuration(input: string): ParseDurationResult {
  const trimmed = input.trim().toLowerCase();

  if (!trimmed) {
    return { success: false, seconds: 0, error: 'Duration cannot be empty' };
  }

  // Check for plain number (interpret as seconds)
  if (/^\d+$/.test(trimmed)) {
    const seconds = parseInt(trimmed, 10);
    return { success: true, seconds };
  }

  // Match pattern: optional spaces, number, optional spaces, unit
  // Supports compound durations like "1h30m" or "1h 30m"
  const pattern = /(\d+(?:\.\d+)?)\s*([a-z]+)/g;
  let match;
  let totalSeconds = 0;
  let hasMatch = false;

  // Verify the entire string is covered by valid patterns
  let lastIndex = 0;

  while ((match = pattern.exec(trimmed)) !== null) {
    // Check for unexpected characters between matches
    const gapBefore = trimmed.slice(lastIndex, match.index).trim();
    if (gapBefore) {
      return {
        success: false,
        seconds: 0,
        error: `Invalid duration format: unexpected "${gapBefore}"`,
      };
    }

    const value = parseFloat(match[1]);
    const unit = match[2];

    const multiplier = DURATION_UNITS[unit];
    if (multiplier === undefined) {
      return {
        success: false,
        seconds: 0,
        error: `Unknown unit "${unit}". Use s, m, h, or d`,
      };
    }

    totalSeconds += value * multiplier;
    hasMatch = true;
    lastIndex = match.index + match[0].length;
  }

  // Check for trailing unexpected characters
  const trailing = trimmed.slice(lastIndex).trim();
  if (trailing) {
    return {
      success: false,
      seconds: 0,
      error: `Invalid duration format: unexpected "${trailing}"`,
    };
  }

  if (!hasMatch) {
    return {
      success: false,
      seconds: 0,
      error: 'Invalid duration format. Examples: "30s", "5m", "4h", "1d"',
    };
  }

  return { success: true, seconds: Math.round(totalSeconds) };
}

/**
 * Format seconds to a human-readable duration string.
 *
 * Uses the most appropriate unit(s) for readability.
 * For exact values, uses single units. For non-exact, uses compound notation.
 *
 * @param seconds - Duration in seconds
 * @param options - Formatting options
 * @returns Human-readable duration string
 *
 * @example
 * formatDuration(30)      // "30s"
 * formatDuration(300)     // "5m"
 * formatDuration(3600)    // "1h"
 * formatDuration(5400)    // "1h 30m"
 * formatDuration(86400)   // "1d"
 * formatDuration(90000)   // "1d 1h"
 */
export function formatDuration(
  seconds: number,
  options: { verbose?: boolean } = {}
): string {
  const { verbose = false } = options;

  if (!Number.isFinite(seconds) || seconds < 0) {
    return verbose ? '0 seconds' : '0s';
  }

  // Round to whole seconds
  seconds = Math.round(seconds);

  if (seconds === 0) {
    return verbose ? '0 seconds' : '0s';
  }

  const parts: string[] = [];

  // Days
  const days = Math.floor(seconds / 86400);
  if (days > 0) {
    parts.push(verbose ? `${days} ${days === 1 ? 'day' : 'days'}` : `${days}d`);
    seconds %= 86400;
  }

  // Hours
  const hours = Math.floor(seconds / 3600);
  if (hours > 0) {
    parts.push(verbose ? `${hours} ${hours === 1 ? 'hour' : 'hours'}` : `${hours}h`);
    seconds %= 3600;
  }

  // Minutes
  const minutes = Math.floor(seconds / 60);
  if (minutes > 0) {
    parts.push(verbose ? `${minutes} ${minutes === 1 ? 'minute' : 'minutes'}` : `${minutes}m`);
    seconds %= 60;
  }

  // Seconds (only show if no larger units, or if there are remaining seconds)
  if (seconds > 0 || parts.length === 0) {
    // Skip seconds if we have larger units (e.g., "1h 30m" not "1h 30m 0s")
    if (seconds > 0) {
      parts.push(verbose ? `${seconds} ${seconds === 1 ? 'second' : 'seconds'}` : `${seconds}s`);
    }
  }

  return parts.join(' ');
}

/**
 * Format seconds to a simple human-readable string for display.
 *
 * Uses a simplified format optimized for display (not editing).
 * Rounds to the most significant unit when appropriate.
 *
 * @param seconds - Duration in seconds
 * @returns Simple human-readable string like "4h", "30m", "1d"
 *
 * @example
 * formatDurationSimple(14400) // "4h"
 * formatDurationSimple(1800)  // "30m"
 * formatDurationSimple(86400) // "1d"
 * formatDurationSimple(5400)  // "1h 30m"
 */
export function formatDurationSimple(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) {
    return '0s';
  }

  seconds = Math.round(seconds);

  if (seconds === 0) {
    return '0s';
  }

  // For exact unit values, show single unit
  if (seconds % 86400 === 0) {
    const days = seconds / 86400;
    return `${days}d`;
  }

  if (seconds % 3600 === 0) {
    const hours = seconds / 3600;
    return `${hours}h`;
  }

  if (seconds % 60 === 0) {
    const minutes = seconds / 60;
    return `${minutes}m`;
  }

  // For compound values, use formatDuration
  return formatDuration(seconds);
}
