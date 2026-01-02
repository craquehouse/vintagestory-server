/**
 * Type definitions for API responses.
 *
 * These types match the backend API response envelope pattern:
 * - Success: { status: "ok", data: {...} }
 * - Error: { detail: { code: "...", message: "..." } }
 */

/**
 * Standard success response envelope from the API.
 */
export interface ApiResponse<T> {
  status: 'ok';
  data: T;
}

/**
 * Error detail structure from FastAPI HTTPException.
 */
export interface ApiErrorDetail {
  code?: string;
  message?: string;
}

/**
 * Error response envelope from the API.
 */
export interface ApiErrorResponse {
  detail?: ApiErrorDetail | string;
}

/**
 * Server state values from the backend API.
 */
export type ServerState =
  | 'not_installed'
  | 'installing'
  | 'installed' // This means stopped
  | 'starting'
  | 'running'
  | 'stopping'
  | 'error';

/**
 * Server status response from GET /api/v1alpha1/server/status.
 * Note: API returns snake_case, but apiClient transforms to camelCase.
 */
export interface ServerStatus {
  state: ServerState;
  version: string | null;
  uptimeSeconds: number | null;
  lastExitCode: number | null;
}

/**
 * Installation status response from GET /api/v1alpha1/server/install/status.
 */
export type InstallState =
  | 'idle'
  | 'downloading'
  | 'extracting'
  | 'configuring'
  | 'complete'
  | 'error';

export interface InstallStatus {
  state: InstallState;
  progress: number;
  message: string;
}

/**
 * Generic message response from server action endpoints.
 */
export interface ActionMessage {
  message: string;
}

// ===== Mod Types =====

/**
 * Compatibility status values from the mod API.
 */
export type CompatibilityStatus = 'compatible' | 'not_verified' | 'incompatible';

/**
 * Mod side values (where the mod runs).
 */
export type ModSide = 'Both' | 'Client' | 'Server';

/**
 * Installed mod information from GET /api/v1alpha1/mods.
 */
export interface ModInfo {
  filename: string;
  slug: string;
  version: string;
  enabled: boolean;
  installedAt: string; // ISO 8601
  name: string | null;
  authors: string[] | null;
  description: string | null;
}

/**
 * Response from GET /api/v1alpha1/mods (list installed mods).
 */
export interface ModsListData {
  mods: ModInfo[];
  pendingRestart: boolean;
}

/**
 * Compatibility details for a mod version.
 */
export interface ModCompatibility {
  status: CompatibilityStatus;
  gameVersion: string | null;
  modVersion: string | null;
  message: string;
}

/**
 * Mod lookup response from GET /api/v1alpha1/mods/lookup/{slug}.
 */
export interface ModLookupData {
  slug: string;
  name: string;
  author: string;
  description: string | null;
  latestVersion: string;
  downloads: number;
  side: ModSide;
  compatibility: ModCompatibility;
  logoUrl: string | null;
}

/**
 * Response from POST /api/v1alpha1/mods (install mod).
 */
export interface ModInstallData {
  slug: string;
  version: string;
  filename: string;
  compatibility: CompatibilityStatus;
  pendingRestart: boolean;
}

/**
 * Response from POST /api/v1alpha1/mods/{slug}/enable or disable.
 */
export interface ModEnableDisableData {
  slug: string;
  enabled: boolean;
  pendingRestart: boolean;
}

/**
 * Response from DELETE /api/v1alpha1/mods/{slug}.
 */
export interface ModRemoveData {
  slug: string;
  pendingRestart: boolean;
}

// ===== Game Config Types =====

/**
 * Setting type values for game configuration.
 */
export type SettingType = 'string' | 'int' | 'bool' | 'float';

/**
 * Individual game setting with metadata.
 */
export interface GameSetting {
  key: string;
  value: string | number | boolean;
  type: SettingType;
  liveUpdate: boolean;
  envManaged: boolean;
  requiresRestart?: boolean;
}

/**
 * Response from GET /api/v1alpha1/config/game.
 */
export interface GameConfigData {
  settings: GameSetting[];
  sourceFile: string;
  lastModified: string; // ISO 8601
}

/**
 * Response from POST /api/v1alpha1/config/game/settings/{key}.
 */
export interface GameSettingUpdateData {
  key: string;
  value: string | number | boolean;
  method: 'console_command' | 'file_update';
  pendingRestart: boolean;
}

// ===== API Settings Types =====

/**
 * API operational settings from GET /api/v1alpha1/config/api.
 */
export interface ApiSettingsData {
  settings: {
    autoStartServer: boolean;
    blockEnvManagedSettings: boolean;
    enforceEnvOnRestart: boolean;
    modListRefreshInterval: number;
    serverVersionsRefreshInterval: number;
  };
}

/**
 * Response from POST /api/v1alpha1/config/api/settings/{key}.
 */
export interface ApiSettingUpdateData {
  key: string;
  value: string | number | boolean;
}

// ===== Config File Types (Story 6.6) =====

/**
 * Response from GET /api/v1alpha1/config/files (list config files).
 */
export interface ConfigFileListData {
  files: string[];
}

/**
 * Response from GET /api/v1alpha1/config/files/{filename} (read config file).
 */
export interface ConfigFileContentData {
  filename: string;
  content: unknown;
}
