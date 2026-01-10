import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Formats a number with K/M suffix for compact display.
 *
 * @param num - Number to format
 * @returns Formatted string (e.g., "1.2K", "3.4M")
 *
 * @example
 * formatNumber(1234) // "1.2K"
 * formatNumber(1234567) // "1.2M"
 * formatNumber(999) // "999"
 */
export function formatNumber(num: number): string {
  if (num >= 1_000_000) {
    return `${(num / 1_000_000).toFixed(1)}M`;
  }
  if (num >= 1_000) {
    return `${(num / 1_000).toFixed(1)}K`;
  }
  return String(num);
}
