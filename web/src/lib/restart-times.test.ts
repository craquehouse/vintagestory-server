import { describe, it, expect } from 'vitest';
import { RESTART_TIME_PATTERN, restartTimesError, sortRestartTimes } from './restart-times';

/**
 * Story 22.6: the client's copy of the API's restart-time rules
 * (`_validate_restart_times` in `api/src/vintagestory_api/services/api_settings.py`).
 * The expected messages are the API's (`api/tests/test_api_settings.py`).
 */

/** `count` times `step` minutes apart from 00:00, as `HH:MM`. */
function spacedTimes(count: number, step: number): string[] {
  return Array.from({ length: count }, (_, i) => {
    const minutes = i * step;
    const hours = String(Math.floor(minutes / 60)).padStart(2, '0');
    return `${hours}:${String(minutes % 60).padStart(2, '0')}`;
  });
}

describe('RESTART_TIME_PATTERN', () => {
  it.each(['00:00', '04:00', '23:59'])('matches %s', (time) => {
    expect(RESTART_TIME_PATTERN.test(time)).toBe(true);
  });

  it.each(['4:00', '24:00', '04:60', '04:00:00', '04:00\n', ''])('does not match %j', (time) => {
    expect(RESTART_TIME_PATTERN.test(time)).toBe(false);
  });
});

describe('sortRestartTimes', () => {
  it('returns a sorted copy and leaves its input alone', () => {
    const times = ['16:00', '04:00'];

    expect(sortRestartTimes(times)).toEqual(['04:00', '16:00']);
    expect(times).toEqual(['16:00', '04:00']);
  });
});

describe('restartTimesError', () => {
  it.each([
    ['no time', []],
    ['one time', ['04:00']],
    ['two times 16 minutes apart', ['04:00', '04:16']],
    ['16 minutes across midnight', ['23:52', '00:08']],
    ['24 times an hour apart', spacedTimes(24, 60)],
  ])('accepts %s', (_name, times) => {
    expect(restartTimesError(times)).toBeNull();
  });

  it.each([
    [
      ['04:00', '04:10'],
      "'04:00' and '04:10' are 10 minutes apart; restart times must be at least 16 minutes apart",
    ],
    [
      ['23:55', '00:05'],
      "'23:55' and '00:05' are 10 minutes apart; restart times must be at least 16 minutes apart",
    ],
    [
      ['00:00', '23:59'],
      "'23:59' and '00:00' are 1 minute apart; restart times must be at least 16 minutes apart",
    ],
  ])('refuses %j with the API gap message', (times, message) => {
    expect(restartTimesError(times)).toBe(message);
  });

  it('refuses the same time twice', () => {
    expect(restartTimesError(['04:00', '04:00'])).toBe("'04:00' is already in the list");
  });

  it('refuses more than 24 times with the API count message', () => {
    const times = spacedTimes(25, 57);
    expect(new Set(times).size).toBe(25);

    expect(restartTimesError(times)).toBe('at most 24 times, got 25');
  });

  it.each(['4:00', '24:00', '04:60', '04:00:00'])(
    'refuses %j with the API format message',
    (time) => {
      expect(restartTimesError([time])).toBe(
        `'${time}' is not a time in HH:MM (24-hour, 00:00 to 23:59)`
      );
    }
  );

  it('asks for a time when a row was cleared', () => {
    expect(restartTimesError([''])).toBe('Enter a time, or remove it');
    expect(restartTimesError(['04:00', ''])).toBe('Enter a time, or remove it');
  });
});
