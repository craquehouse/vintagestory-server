/**
 * Mod Compatibility Utilities
 *
 * Story 10.6: Full compatibility check will be implemented here (placeholder).
 *
 * Story 18.3 (Epic 18 ADR-3): browse cards no longer use a compatibility default. The
 * browse API reports whether each entry has a release tagged for the installed game
 * version (`hasReleaseForGameVersion`), and the card shows that, not a compatibility
 * verdict; the compatibility of a specific release is judged on the detail page.
 */

import type { CompatibilityStatus } from '@/api/types';

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
