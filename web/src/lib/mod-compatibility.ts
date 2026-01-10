/**
 * Mod Compatibility Utilities
 *
 * Story 10.5: Conservative default for browse grid cards.
 * Story 10.6: Full compatibility check will be implemented here.
 *
 * The browse API endpoint does NOT include version compatibility data.
 * Full compatibility checks require fetching individual mod details.
 */

import type { CompatibilityStatus } from '@/api/types';

/**
 * Default compatibility status for browse grid cards.
 *
 * We use 'not_verified' as a conservative default because:
 * 1. The browse endpoint doesn't include version compatibility data
 * 2. lastReleased is a timestamp, NOT a game version
 * 3. Full compatibility requires mod detail API call (Story 10.6)
 *
 * This aligns with UX spec's "Trust through transparency" principle -
 * users see accurate "Not verified" rather than false "Compatible".
 */
export const BROWSE_CARD_DEFAULT_STATUS: CompatibilityStatus = 'not_verified';

/**
 * Get compatibility status for a mod in the browse grid.
 *
 * For browse grid, always returns 'not_verified' since the browse API
 * doesn't include version compatibility data.
 *
 * @returns 'not_verified' - conservative default for browse cards
 *
 * @example
 * const status = getBrowseCardCompatibility();
 * // Always returns 'not_verified'
 */
export function getBrowseCardCompatibility(): CompatibilityStatus {
  return BROWSE_CARD_DEFAULT_STATUS;
}

/**
 * Placeholder for full compatibility check (Story 10.6).
 *
 * Will compare mod's supported game versions against server version.
 *
 * @param _modVersions - Array of game versions the mod supports
 * @param _serverVersion - Current server version
 * @returns Compatibility status (currently placeholder)
 *
 * @example
 * // Future usage in Story 10.6:
 * const status = checkVersionCompatibility(
 *   mod.gameVersions,  // From mod detail API
 *   serverStatus.version
 * );
 */
export function checkVersionCompatibility(
  _modVersions: string[],
  _serverVersion: string | null
): CompatibilityStatus {
  // TODO(Story 10.6): Implement actual version comparison
  // For now, return not_verified as conservative default
  return 'not_verified';
}
