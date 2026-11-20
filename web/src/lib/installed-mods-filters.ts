/**
 * Filters of the installed mods list (Story 24.7, FR341, FR342, Epic 24 ADR-6).
 *
 * Kept in the URL as `q` (part of the name or mod ID), `compat` (a compatibility status)
 * and `updates=1` (only mods with an update available). Invalid values are ignored.
 */

import type { CompatibilityStatus, ModUpdateStatus } from '@/api/types';

export interface InstalledModsFilters {
  /** Part of the name or mod ID, any letter case; empty for no filter */
  query: string;
  /** Only mods with this compatibility status; null for all */
  compat: CompatibilityStatus | null;
  /** Only mods with an update available */
  updates: boolean;
}

export const EMPTY_FILTERS: InstalledModsFilters = { query: '', compat: null, updates: false };

export const COMPATIBILITY_STATUSES: readonly CompatibilityStatus[] = [
  'compatible',
  'not_verified',
  'incompatible',
];

function isCompatibilityStatus(value: string | null): value is CompatibilityStatus {
  return COMPATIBILITY_STATUSES.some((status) => status === value);
}

export function filtersFromSearchParams(params: URLSearchParams): InstalledModsFilters {
  const compat = params.get('compat');
  return {
    query: params.get('q') ?? '',
    compat: isCompatibilityStatus(compat) ? compat : null,
    updates: params.get('updates') === '1',
  };
}

/** The URL parameters for `filters`, keeping any other parameters of `current`. */
export function filtersToSearchParams(
  filters: InstalledModsFilters,
  current: URLSearchParams
): URLSearchParams {
  const params = new URLSearchParams(current);
  params.delete('q');
  params.delete('compat');
  params.delete('updates');
  // A query of only spaces is no filter, so it is not written (Story 24.7 review)
  if (filters.query.trim()) params.set('q', filters.query);
  if (filters.compat) params.set('compat', filters.compat);
  if (filters.updates) params.set('updates', '1');
  return params;
}

export function hasFilters(filters: InstalledModsFilters): boolean {
  return filters.query.trim() !== '' || filters.compat !== null || filters.updates;
}

/** What the filters read from an installed mod's row. */
export interface FilterableMod {
  slug: string;
  name: string | null;
  compatibilityStatus: CompatibilityStatus;
  /** False while the mod's compatibility is still loading */
  compatibilityKnown?: boolean;
  updateStatus?: Pick<ModUpdateStatus, 'status'>;
}

export function matchesFilters(mod: FilterableMod, filters: InstalledModsFilters): boolean {
  const query = filters.query.trim().toLowerCase();
  if (
    query &&
    !mod.slug.toLowerCase().includes(query) &&
    !(mod.name ?? '').toLowerCase().includes(query)
  ) {
    return false;
  }
  // A status still loading reads as not_verified; it matches only "All" (ADR-6 decision 4)
  if (
    filters.compat !== null &&
    (mod.compatibilityKnown === false || mod.compatibilityStatus !== filters.compat)
  ) {
    return false;
  }
  if (filters.updates && mod.updateStatus?.status !== 'update_available') {
    return false;
  }
  return true;
}
