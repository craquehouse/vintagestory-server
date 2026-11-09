import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { reloadForStaleChunk, STALE_CHUNK_RELOAD_COOLDOWN_MS } from './stale-chunk-reload';

describe('reloadForStaleChunk', () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-01-01T00:00:00Z'));
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('reloads when a chunk first fails', () => {
    const reload = vi.fn();

    reloadForStaleChunk(reload);

    expect(reload).toHaveBeenCalledTimes(1);
  });

  it('does not reload again during the cooldown', () => {
    const reload = vi.fn();
    reloadForStaleChunk(reload);

    vi.advanceTimersByTime(STALE_CHUNK_RELOAD_COOLDOWN_MS - 1);
    reloadForStaleChunk(reload);

    expect(reload).toHaveBeenCalledTimes(1);
  });

  it('reloads again after the cooldown', () => {
    const reload = vi.fn();
    reloadForStaleChunk(reload);

    vi.advanceTimersByTime(STALE_CHUNK_RELOAD_COOLDOWN_MS);
    reloadForStaleChunk(reload);

    expect(reload).toHaveBeenCalledTimes(2);
  });

  it('does not reload when session storage is unavailable', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('storage blocked');
    });
    const reload = vi.fn();

    reloadForStaleChunk(reload);

    expect(reload).not.toHaveBeenCalled();
  });
});
