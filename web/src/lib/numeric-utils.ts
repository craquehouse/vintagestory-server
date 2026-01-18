/**
 * Numeric validation and formatting utilities.
 *
 * Story 12.4: Dashboard Stats Cards
 *
 * Provides shared validation functions for numeric values
 * to handle null, undefined, NaN, Infinity, and negative values consistently.
 */

/**
 * Check if a value is a valid, displayable numeric value.
 * Returns false for null, undefined, NaN, Infinity, and negative values.
 *
 * @param value - The value to validate
 * @returns True if the value is a valid non-negative finite number
 *
 * @example
 * isValidNumeric(123)      // true
 * isValidNumeric(0)        // true
 * isValidNumeric(-5)       // false
 * isValidNumeric(NaN)      // false
 * isValidNumeric(Infinity) // false
 * isValidNumeric(null)     // false
 * isValidNumeric(undefined)// false
 */
export function isValidNumeric(value: number | null | undefined): value is number {
  return (
    value !== null &&
    value !== undefined &&
    Number.isFinite(value) &&
    value >= 0
  );
}

/**
 * Format a numeric value to a fixed decimal string, or return a fallback.
 * Handles invalid values (null, undefined, NaN, Infinity, negative) gracefully.
 *
 * @param value - The value to format
 * @param decimals - Number of decimal places (default: 1)
 * @param fallback - String to return for invalid values (default: 'N/A')
 * @returns Formatted string or fallback
 *
 * @example
 * formatNumericOrFallback(123.456)        // "123.5"
 * formatNumericOrFallback(123.456, 2)     // "123.46"
 * formatNumericOrFallback(null)           // "N/A"
 * formatNumericOrFallback(NaN, 1, '-')    // "-"
 */
export function formatNumericOrFallback(
  value: number | null | undefined,
  decimals: number = 1,
  fallback: string = 'N/A'
): string {
  if (!isValidNumeric(value)) {
    return fallback;
  }
  return value.toFixed(decimals);
}

/**
 * Format memory value with adaptive units (MB or GB).
 * Uses GB for values >= 1024 MB, MB for smaller values.
 * Handles invalid values gracefully.
 *
 * @param mb - Memory value in megabytes
 * @param fallback - String to return for invalid values (default: 'N/A')
 * @returns Formatted string with unit (e.g., "512.0 MB" or "2.5 GB")
 *
 * @example
 * formatMemoryAdaptive(512)     // "512.0 MB"
 * formatMemoryAdaptive(1024)    // "1.0 GB"
 * formatMemoryAdaptive(2560)    // "2.5 GB"
 * formatMemoryAdaptive(null)    // "N/A"
 * formatMemoryAdaptive(-100)    // "N/A"
 */
export function formatMemoryAdaptive(
  mb: number | null | undefined,
  fallback: string = 'N/A'
): string {
  if (!isValidNumeric(mb)) {
    return fallback;
  }

  // Use GB for values >= 1024 MB (1 GB)
  if (mb >= 1024) {
    const gb = mb / 1024;
    return `${gb.toFixed(1)} GB`;
  }

  return `${mb.toFixed(1)} MB`;
}
