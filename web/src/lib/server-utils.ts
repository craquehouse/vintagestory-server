/**
 * Server utility functions.
 *
 * Shared utilities for server state checks and common operations.
 */

import type { ServerState } from '@/api/types';

/**
 * Determines if the server is in an "installed" state (has a version installed).
 *
 * A server is considered installed if it's NOT in one of these states:
 * - 'not_installed': No server version has been downloaded
 * - 'installing': Server installation is in progress
 *
 * All other states (installed, starting, running, stopping) indicate a
 * server version is present.
 */
export function isServerInstalled(state: ServerState): boolean {
  return state !== 'not_installed' && state !== 'installing';
}
