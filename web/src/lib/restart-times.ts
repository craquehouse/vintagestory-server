/**
 * Restart-time rules for the Scheduled Restarts editor (Story 22.6).
 *
 * The client's copy of the API's validator, `ApiSettings._validate_restart_times` in
 * `api/src/vintagestory_api/services/api_settings.py`, with the API's messages, so a list
 * the API would refuse is refused before it is sent. The API stays the enforcement.
 */

import { MAX_RESTART_TIMES, MIN_RESTART_GAP_MINUTES } from '@/api/config';

const MINUTES_PER_DAY = 1440;
/** The API cuts a longer entry in its message (`_SHOWN_ENTRY_LENGTH`). */
const SHOWN_ENTRY_LENGTH = 16;

/**
 * A restart time, `HH:MM` 24-hour, 00:00 to 23:59: the API's `_RESTART_TIME`, matched in
 * full as the API does with `fullmatch`.
 */
export const RESTART_TIME_PATTERN = /^([01][0-9]|2[0-3]):[0-5][0-9]$/;

/**
 * A sorted copy of the times. Zero-padded `HH:MM` sorts as text, as the API sorts them in
 * `_validate_restart_times`.
 */
export function sortRestartTimes(times: readonly string[]): string[] {
  return [...times].sort();
}

function minutes(time: string): number {
  const [hours, mins] = time.split(':');
  return Number(hours) * 60 + Number(mins);
}

/**
 * Why the API would refuse these restart times, or `null` when it would accept them
 * (`_validate_restart_times`). Checked in order: a cleared entry, the format, a duplicate
 * (the API drops one silently; the editor refuses it so no row vanishes), the count, and
 * the gap between each sorted time and the next, the last wrapping to the first.
 */
export function restartTimesError(times: readonly string[]): string | null {
  if (times.some((time) => time === '')) {
    return 'Enter a time, or remove it';
  }
  for (const time of times) {
    if (!RESTART_TIME_PATTERN.test(time)) {
      const shown =
        time.length > SHOWN_ENTRY_LENGTH ? `${time.slice(0, SHOWN_ENTRY_LENGTH)}...` : time;
      return `'${shown}' is not a time in HH:MM (24-hour, 00:00 to 23:59)`;
    }
  }
  const seen = new Set<string>();
  for (const time of times) {
    if (seen.has(time)) {
      return `'${time}' is already in the list`;
    }
    seen.add(time);
  }
  if (times.length > MAX_RESTART_TIMES) {
    return `at most ${MAX_RESTART_TIMES} times, got ${times.length}`;
  }
  if (times.length >= 2) {
    const sorted = sortRestartTimes(times);
    for (let i = 0; i < sorted.length; i += 1) {
      const current = sorted[i];
      const following = sorted[(i + 1) % sorted.length];
      const gap =
        (((minutes(following) - minutes(current)) % MINUTES_PER_DAY) + MINUTES_PER_DAY) %
        MINUTES_PER_DAY;
      if (gap < MIN_RESTART_GAP_MINUTES) {
        const apart = gap === 1 ? '1 minute' : `${gap} minutes`;
        return (
          `'${current}' and '${following}' are ${apart} apart; restart times ` +
          `must be at least ${MIN_RESTART_GAP_MINUTES} minutes apart`
        );
      }
    }
  }
  return null;
}
