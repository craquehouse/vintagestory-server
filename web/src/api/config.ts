/**
 * Configuration API functions for game and API settings.
 *
 * These functions wrap the apiClient to provide typed access to
 * configuration endpoints.
 *
 * Story 6.4: Settings UI
 * Story 6.6: File Manager UI
 */

import { apiClient } from './client';
import type {
  ApiResponse,
  GameConfigData,
  GameSettingUpdateData,
  ApiSettingsData,
  ApiSettingUpdateData,
  ModUpdateWebhookUpdateData,
  ConfigDirectoryListData,
  ConfigFileListData,
  ConfigFileContentData,
} from './types';

const API_PREFIX = '/api/v1alpha1/config';

// ===== Game Config API =====

/**
 * Fetch all game settings with metadata.
 *
 * Accessible to both Admin and Monitor roles.
 */
export async function fetchGameConfig(): Promise<ApiResponse<GameConfigData>> {
  return apiClient<ApiResponse<GameConfigData>>(`${API_PREFIX}/game`);
}

/**
 * Update a specific game setting.
 *
 * @param key - Setting key to update (e.g., 'ServerName', 'Port')
 * @param value - New value for the setting
 * @returns Update result with method used and pending restart status
 *
 * Requires Admin role.
 */
export async function updateGameSetting(
  key: string,
  value: string | number | boolean
): Promise<ApiResponse<GameSettingUpdateData>> {
  return apiClient<ApiResponse<GameSettingUpdateData>>(
    `${API_PREFIX}/game/settings/${encodeURIComponent(key)}`,
    {
      method: 'POST',
      body: { value },
    }
  );
}

// ===== API Settings API =====

/**
 * Fetch API operational settings.
 *
 * Requires Admin role.
 */
export async function fetchApiSettings(): Promise<ApiResponse<ApiSettingsData>> {
  return apiClient<ApiResponse<ApiSettingsData>>(`${API_PREFIX}/api`);
}

/**
 * API settings whose values are secrets (Story 14.6). The generic update path refuses
 * them; use their dedicated functions, which never cache or return the value.
 */
export const SECRET_API_SETTINGS: ReadonlySet<string> = new Set(['mod_update_webhook_url']);

/**
 * API settings whose change reschedules a job (Story 17.6).
 *
 * Keep in step with the API: `INTERVAL_JOBS` in `api/src/vintagestory_api/jobs/__init__.py`
 * (and `SCHEDULED_SETTINGS` in `services/api_settings.py`, which an API test ties to it).
 */
export const INTERVAL_API_SETTINGS: ReadonlySet<string> = new Set([
  'mod_list_refresh_interval',
  'server_versions_refresh_interval',
  'metrics_collection_interval',
]);

/**
 * The API's maximum for an interval setting: 365 days (`MAX_INTERVAL_SECONDS` in
 * `api/src/vintagestory_api/services/api_settings.py`; pinned by `TestWebDefaults` in
 * `api/tests/test_api_settings.py`).
 */
export const MAX_INTERVAL_SECONDS = 31_536_000;

/**
 * The API's default for each setting the API Settings tab shows (Story 22.5, Epic 22
 * ADR-11 decision 4): the tab's fallback when a value is missing, and the value an
 * interval's On switch saves when the page has seen no earlier value for it. Keys are the
 * API's setting keys. Keep each value a plain
 * literal on its own line: `TestWebDefaults` in `api/tests/test_api_settings.py` reads
 * this block and compares it with `ApiSettings()`.
 */
export const API_SETTING_DEFAULTS = {
  auto_start_server: false,
  block_env_managed_settings: true,
  enforce_env_on_restart: false,
  mod_list_refresh_interval: 14400,
  server_versions_refresh_interval: 86400,
  metrics_collection_interval: 10,
} as const;

/**
 * Set or clear the mod update webhook (Story 14.6). `null` clears it.
 *
 * Requires Admin role. The response reports only whether a webhook is configured.
 */
export async function setModUpdateWebhook(
  url: string | null
): Promise<ApiResponse<ModUpdateWebhookUpdateData>> {
  return apiClient<ApiResponse<ModUpdateWebhookUpdateData>>(
    `${API_PREFIX}/api/settings/mod_update_webhook_url`,
    {
      method: 'POST',
      body: { value: url },
    }
  );
}

/**
 * Update a specific API setting.
 *
 * @param key - Setting key to update (e.g., 'auto_start_server')
 * @param value - New value for the setting
 * @returns Update result with the new value
 * @throws Error for a secret setting; use its dedicated function instead
 *
 * Requires Admin role.
 */
export async function updateApiSetting(
  key: string,
  value: string | number | boolean
): Promise<ApiResponse<ApiSettingUpdateData>> {
  if (SECRET_API_SETTINGS.has(key)) {
    throw new Error(`${key} is a secret; use setModUpdateWebhook`);
  }
  return apiClient<ApiResponse<ApiSettingUpdateData>>(
    `${API_PREFIX}/api/settings/${encodeURIComponent(key)}`,
    {
      method: 'POST',
      body: { value },
    }
  );
}

// ===== Config Files API (Story 6.6, Story 9.7) =====

/**
 * Fetch list of directories in serverdata or a subdirectory.
 *
 * @param directory - Optional subdirectory to list directories from (Story 9.7)
 *
 * Story 9.7: Dynamic File Browser
 * Accessible to both Admin and Monitor roles.
 */
export async function fetchConfigDirectories(
  directory?: string
): Promise<ApiResponse<ConfigDirectoryListData>> {
  const params = directory ? `?directory=${encodeURIComponent(directory)}` : '';
  return apiClient<ApiResponse<ConfigDirectoryListData>>(`${API_PREFIX}/directories${params}`);
}

/**
 * Fetch list of available configuration files.
 *
 * @param directory - Optional subdirectory to list files from (Story 9.7)
 *
 * Accessible to both Admin and Monitor roles.
 */
export async function fetchConfigFiles(
  directory?: string
): Promise<ApiResponse<ConfigFileListData>> {
  const params = directory ? `?directory=${encodeURIComponent(directory)}` : '';
  return apiClient<ApiResponse<ConfigFileListData>>(`${API_PREFIX}/files${params}`);
}

/**
 * Fetch the content of a specific configuration file.
 *
 * @param filename - Name of the config file (e.g., 'serverconfig.json')
 * @returns File content as parsed JSON
 *
 * Accessible to both Admin and Monitor roles.
 */
export async function fetchConfigFileContent(
  filename: string
): Promise<ApiResponse<ConfigFileContentData>> {
  return apiClient<ApiResponse<ConfigFileContentData>>(
    `${API_PREFIX}/files/${encodeURIComponent(filename)}`
  );
}
