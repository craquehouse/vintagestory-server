/**
 * Recovery for page chunks that fail to load.
 *
 * A tab left open across a deploy still references chunk filenames from the old build,
 * and those files no longer exist. Reloading picks up the new build.
 */

const LAST_RELOAD_KEY = 'stale-chunk-last-reload';
export const STALE_CHUNK_RELOAD_COOLDOWN_MS = 10_000;

/**
 * Reloads the page after a chunk fails to load, at most once per cooldown so a chunk
 * that stays missing cannot cause a reload loop.
 */
export function reloadForStaleChunk(reload: () => void = () => window.location.reload()): void {
  try {
    const lastReload = Number(sessionStorage.getItem(LAST_RELOAD_KEY) ?? 0);
    if (Date.now() - lastReload < STALE_CHUNK_RELOAD_COOLDOWN_MS) {
      return;
    }
    sessionStorage.setItem(LAST_RELOAD_KEY, String(Date.now()));
  } catch {
    // Without storage there is no way to tell whether this would loop.
    return;
  }
  reload();
}
