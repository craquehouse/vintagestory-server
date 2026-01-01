/**
 * Configuration API functions for game and API settings.
 *
 * These functions wrap the apiClient to provide typed access to
 * configuration endpoints.
 *
 * Story 6.4: Settings UI
 */

import { apiClient } from './client';
import type {
  ApiResponse,
  GameConfigData,
  GameSettingUpdateData,
  ApiSettingsData,
  ApiSettingUpdateData,
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
 * Update a specific API setting.
 *
 * @param key - Setting key to update (e.g., 'auto_start_server')
 * @param value - New value for the setting
 * @returns Update result with the new value
 *
 * Requires Admin role.
 */
export async function updateApiSetting(
  key: string,
  value: string | number | boolean
): Promise<ApiResponse<ApiSettingUpdateData>> {
  return apiClient<ApiResponse<ApiSettingUpdateData>>(
    `${API_PREFIX}/api/settings/${encodeURIComponent(key)}`,
    {
      method: 'POST',
      body: { value },
    }
  );
}
