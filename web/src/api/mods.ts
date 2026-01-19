/**
 * Mod management API functions.
 *
 * These functions wrap the apiClient to provide typed access to
 * mod management endpoints.
 */

import { apiClient } from './client';
import type {
  ApiResponse,
  BrowseParams,
  GameVersionsData,
  ModBrowseData,
  ModsListData,
  ModLookupData,
  ModInstallData,
  ModEnableDisableData,
  ModRemoveData,
  ModTagsData,
} from './types';

const API_PREFIX = '/api/v1alpha1/mods';

/**
 * Fetch list of installed mods with pending restart status.
 *
 * Accessible to both Admin and Monitor roles.
 */
export async function fetchMods(): Promise<ApiResponse<ModsListData>> {
  return apiClient<ApiResponse<ModsListData>>(API_PREFIX);
}

/**
 * Look up mod details from the VintageStory mod database.
 *
 * @param slugOrUrl - Mod slug or full URL to look up
 * @returns Mod details including compatibility information
 *
 * Accessible to both Admin and Monitor roles.
 */
export async function lookupMod(
  slugOrUrl: string
): Promise<ApiResponse<ModLookupData>> {
  // URL-encode the slug/URL since it may contain special characters
  const encoded = encodeURIComponent(slugOrUrl);
  return apiClient<ApiResponse<ModLookupData>>(`${API_PREFIX}/lookup/${encoded}`);
}

/**
 * Install a mod from the VintageStory mod database.
 *
 * @param slug - Mod slug or URL to install
 * @param version - Optional specific version to install (defaults to latest)
 * @returns Installation result with compatibility status
 *
 * Requires Admin role.
 */
export async function installMod(
  slug: string,
  version?: string
): Promise<ApiResponse<ModInstallData>> {
  return apiClient<ApiResponse<ModInstallData>>(API_PREFIX, {
    method: 'POST',
    body: { slug, version },
  });
}

/**
 * Enable a disabled mod.
 *
 * @param slug - Mod slug to enable
 * @returns Enable result with pending restart status
 *
 * Requires Admin role.
 */
export async function enableMod(
  slug: string
): Promise<ApiResponse<ModEnableDisableData>> {
  return apiClient<ApiResponse<ModEnableDisableData>>(
    `${API_PREFIX}/${encodeURIComponent(slug)}/enable`,
    { method: 'POST' }
  );
}

/**
 * Disable an enabled mod.
 *
 * @param slug - Mod slug to disable
 * @returns Disable result with pending restart status
 *
 * Requires Admin role.
 */
export async function disableMod(
  slug: string
): Promise<ApiResponse<ModEnableDisableData>> {
  return apiClient<ApiResponse<ModEnableDisableData>>(
    `${API_PREFIX}/${encodeURIComponent(slug)}/disable`,
    { method: 'POST' }
  );
}

/**
 * Remove an installed mod.
 *
 * @param slug - Mod slug to remove
 * @returns Remove result with pending restart status
 *
 * Requires Admin role.
 */
export async function removeMod(
  slug: string
): Promise<ApiResponse<ModRemoveData>> {
  return apiClient<ApiResponse<ModRemoveData>>(
    `${API_PREFIX}/${encodeURIComponent(slug)}`,
    { method: 'DELETE' }
  );
}

/**
 * Fetch list of available game versions for mod filtering.
 *
 * Returns versions from the VintageStory mod database API.
 * Versions are sorted newest to oldest.
 *
 * Story VSS-vth: Game version filter for mod browser.
 *
 * @returns List of game version strings
 *
 * Accessible to both Admin and Monitor roles.
 */
export async function fetchGameVersions(): Promise<
  ApiResponse<GameVersionsData>
> {
  return apiClient<ApiResponse<GameVersionsData>>(`${API_PREFIX}/gameversions`);
}

/**
 * Fetch list of all unique mod tags.
 *
 * Returns all tags across all mods in the database, sorted alphabetically.
 * Used for populating the tag filter dropdown with complete tag list.
 *
 * VSS-y7u: Server-side filtering for mod browser.
 *
 * @returns List of tag strings
 *
 * Accessible to both Admin and Monitor roles.
 */
export async function fetchModTags(): Promise<ApiResponse<ModTagsData>> {
  return apiClient<ApiResponse<ModTagsData>>(`${API_PREFIX}/tags`);
}

/**
 * Fetch paginated list of mods from the browse API.
 *
 * Returns mods from the VintageStory mod database with pagination.
 * The API caches results for 5 minutes.
 *
 * VSS-y7u: All filters (side, modType, tags) are now server-side for accurate pagination.
 *
 * @param params - Pagination, sort, search, and filter parameters
 * @returns Paginated mod list with metadata
 *
 * Accessible to both Admin and Monitor roles.
 */
export async function fetchBrowseMods(
  params: BrowseParams = {}
): Promise<ApiResponse<ModBrowseData>> {
  const searchParams = new URLSearchParams();

  if (params.page !== undefined) {
    searchParams.set('page', String(params.page));
  }
  if (params.pageSize !== undefined) {
    searchParams.set('page_size', String(params.pageSize));
  }
  if (params.sort !== undefined && params.sort !== 'name') {
    // 'name' sort is still client-side only
    searchParams.set('sort', params.sort);
  }
  if (params.search?.trim()) {
    searchParams.set('search', params.search.trim());
  }
  // VSS-vth: Server-side game version filtering
  if (params.version?.trim()) {
    searchParams.set('version', params.version.trim());
  }
  // VSS-y7u: Server-side filters (previously client-side)
  if (params.side) {
    searchParams.set('side', params.side);
  }
  if (params.modType) {
    searchParams.set('mod_type', params.modType);
  }
  if (params.tags && params.tags.length > 0) {
    searchParams.set('tags', params.tags.join(','));
  }

  const query = searchParams.toString();
  const url = query ? `${API_PREFIX}/browse?${query}` : `${API_PREFIX}/browse`;

  return apiClient<ApiResponse<ModBrowseData>>(url);
}
