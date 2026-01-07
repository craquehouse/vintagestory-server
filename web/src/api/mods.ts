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
  ModBrowseData,
  ModsListData,
  ModLookupData,
  ModInstallData,
  ModEnableDisableData,
  ModRemoveData,
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
 * Fetch paginated list of mods from the browse API.
 *
 * Returns mods from the VintageStory mod database with pagination.
 * The API caches results for 5 minutes.
 *
 * @param params - Pagination and sort parameters
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
  if (params.sort !== undefined) {
    searchParams.set('sort', params.sort);
  }
  // Note: search param is not sent to API - it's handled client-side in the hook

  const query = searchParams.toString();
  const url = query ? `${API_PREFIX}/browse?${query}` : `${API_PREFIX}/browse`;

  return apiClient<ApiResponse<ModBrowseData>>(url);
}
