/**
 * Mod ID matching for mod database entries.
 *
 * Story 16.2 (Epic 16 ADR-2 decision 2): one mod database entry can ship several
 * mod IDs (for example `instruments`, `vsinstruments` and `vsinstrumentsbase`), and
 * its browse slug is only the first of them. An installed mod belongs to an entry
 * when its ID is the URL slug or the `modidstr` of any of the entry's releases.
 *
 * Mod IDs are compared exactly, as the update check and the version change API do.
 */

import type { ModRelease } from '@/api/types';

/** One version a version list offers (Story 17.2). */
export interface VersionChoice {
  version: string;
  /** Whether the release has a downloadable file (a positive file ID) */
  installable: boolean;
}

/**
 * The entry's mod IDs, each once, in release order (newest release first).
 * Releases without a mod ID are skipped.
 */
export function entryModIds(releases: readonly Pick<ModRelease, 'modidstr'>[]): string[] {
  const ids: string[] = [];
  for (const release of releases) {
    if (release.modidstr && !ids.includes(release.modidstr)) {
      ids.push(release.modidstr);
    }
  }
  return ids;
}

/**
 * The installed mod that belongs to a mod database entry, if any.
 *
 * When several of the entry's mod IDs are installed, the one whose ID is the URL
 * slug wins; otherwise the one whose mod ID has the newest release.
 *
 * @param installedMods - Installed mods (their `slug` is the mod ID); undefined while loading
 * @param entry - The URL slug the entry was opened with, and the entry's releases
 */
export function findInstalledModForEntry<T extends { slug: string }>(
  installedMods: readonly T[] | undefined,
  entry: { slug: string; releases: readonly Pick<ModRelease, 'modidstr'>[] }
): T | undefined {
  if (!installedMods || installedMods.length === 0) return undefined;
  for (const modId of [entry.slug, ...entryModIds(entry.releases)]) {
    const match = installedMods.find((mod) => mod.slug === modId);
    if (match) return match;
  }
  return undefined;
}

/**
 * The versions a version list offers for one mod ID (Story 17.2, Epic 17 ADR-2).
 *
 * Only the releases whose `modidstr` is exactly `modId`, newest first. A re-uploaded
 * version is listed once, by its first (newest) listing, as the update check and the
 * version change API do. A release without a positive file ID is not installable.
 */
export function versionChoices(
  releases: readonly Pick<ModRelease, 'modidstr' | 'version' | 'fileId'>[],
  modId: string
): VersionChoice[] {
  const seen = new Set<string>();
  const choices: VersionChoice[] = [];
  for (const release of releases) {
    if (release.modidstr !== modId || seen.has(release.version)) continue;
    seen.add(release.version);
    choices.push({
      version: release.version,
      installable: typeof release.fileId === 'number' && release.fileId > 0,
    });
  }
  return choices;
}
