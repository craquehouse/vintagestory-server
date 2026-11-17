/// <reference types="vitest/jsdom" />
/**
 * Page URL for tests (Story 20.2).
 *
 * Under Vitest's `vmThreads` pool, `window.location` cannot be redefined, so tests
 * change the URL through the jsdom instance and `window.location` follows.
 * `tests/setup.ts` calls `resetTestUrl` after each test, because one jsdom serves
 * every test file in a worker.
 */

/** Vitest's jsdom default URL; every test starts here. */
export const DEFAULT_TEST_URL = 'http://localhost:3000/';

/** Point the jsdom document at another URL; window.location follows. */
export function setTestUrl(url: string): void {
  jsdom.reconfigure({ url });
}

/** Back to the default URL (called after each test by tests/setup.ts). */
export function resetTestUrl(): void {
  jsdom.reconfigure({ url: DEFAULT_TEST_URL });
}
