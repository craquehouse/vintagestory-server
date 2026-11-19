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
  ApiSettingValue,
  ModUpdateWebhookUpdateData,
  ConfigDirectoryListData,
  ConfigParseError,
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
 * API settings whose save changes the scheduled jobs (Story 22.6): the interval keys and
 * the restart times. Mirrors `SCHEDULED_SETTINGS` in
 * `api/src/vintagestory_api/services/api_settings.py`.
 */
export const SCHEDULED_API_SETTINGS: ReadonlySet<string> = new Set([
  ...INTERVAL_API_SETTINGS,
  'scheduled_restart_times',
]);

/**
 * The API's maximum number of daily restart times (`MAX_RESTART_TIMES` in
 * `api/src/vintagestory_api/services/api_settings.py`; pinned by `TestWebDefaults` in
 * `api/tests/test_api_settings.py`). Story 22.6.
 */
export const MAX_RESTART_TIMES = 24;

/**
 * The API's minimum gap between two restart times, in minutes, across midnight too
 * (`MIN_RESTART_GAP_MINUTES` in `api/src/vintagestory_api/services/api_settings.py`;
 * pinned by `TestWebDefaults`). Story 22.6.
 */
export const MIN_RESTART_GAP_MINUTES = 16;

/**
 * The API's maximum for `backup_keep_count` (`MAX_BACKUP_KEEP_COUNT` in
 * `api/src/vintagestory_api/services/api_settings.py`; pinned by `TestWebDefaults`).
 * Story 22.6.
 */
export const MAX_BACKUP_KEEP_COUNT = 1000;

/**
 * The API's default for each setting the API Settings tab shows (Story 22.5, Epic 22
 * ADR-11 decision 4): the tab's fallback when a value is missing, and the value an
 * interval's On switch saves when the page has seen no earlier value for it. Keys are the
 * API's setting keys. Story 22.6 adds the restart times and the backup limit. Keep each value a plain
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
  scheduled_restart_times: [],
  backup_keep_count: 0,
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
  value: ApiSettingValue
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
 * A directory or file name that cannot be part of a config path (Story 23.2).
 */
export class InvalidConfigPathError extends Error {
  constructor(name: string) {
    super(`Invalid name in path: ${JSON.stringify(name)}`);
    this.name = 'InvalidConfigPathError';
  }
}

/**
 * Join a list of directory names (and a file name) into the API's relative path.
 *
 * The only place a config path string is built (Story 23.2, Epic 23 ADR-3 decision 2).
 * A name that is empty, `.` or `..`, or that contains `/` or a NUL character, cannot
 * come from a directory listing on the server; it is refused, so no request is sent.
 *
 * @param segments - Directory names from the root, then the file name if any; `[]` is the root
 * @throws InvalidConfigPathError for a name that cannot be part of a path
 */
export function toConfigPath(segments: readonly string[]): string {
  for (const name of segments) {
    if (name === '' || name === '.' || name === '..' || name.includes('/') || name.includes('\0')) {
      throw new InvalidConfigPathError(name);
    }
  }
  return segments.join('/');
}

/** The `?directory=` query for a directory, or nothing for the root. */
function directoryQuery(directory: readonly string[]): string {
  const path = toConfigPath(directory);
  return path ? `?directory=${encodeURIComponent(path)}` : '';
}

/**
 * Fetch list of directories in serverdata or a subdirectory.
 *
 * @param directory - Directory names from the root (Story 9.7, Story 23.2); `[]` is the root
 *
 * Story 9.7: Dynamic File Browser
 * Accessible to both Admin and Monitor roles.
 */
export async function fetchConfigDirectories(
  directory: readonly string[] = []
): Promise<ApiResponse<ConfigDirectoryListData>> {
  const params = directoryQuery(directory);
  return apiClient<ApiResponse<ConfigDirectoryListData>>(`${API_PREFIX}/directories${params}`);
}

/**
 * Fetch list of available configuration files.
 *
 * @param directory - Directory names from the root (Story 9.7, Story 23.2); `[]` is the root
 *
 * Accessible to both Admin and Monitor roles.
 */
export async function fetchConfigFiles(
  directory: readonly string[] = []
): Promise<ApiResponse<ConfigFileListData>> {
  const params = directoryQuery(directory);
  return apiClient<ApiResponse<ConfigFileListData>>(`${API_PREFIX}/files${params}`);
}

/** The read's data as the API sends it (snake_case, Story 23.1). */
interface RawConfigFileContentData {
  filename?: unknown;
  content?: unknown;
  parse_error?: unknown;
  text?: unknown;
  version?: unknown;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function toParseError(value: unknown): ConfigParseError | null {
  if (!isRecord(value) || typeof value.message !== 'string') return null;
  const position = (n: unknown) => (typeof n === 'number' ? n : null);
  return { message: value.message, line: position(value.line), column: position(value.column) };
}

/**
 * Fetch the content of a specific configuration file.
 *
 * The response is read without the client's key transform, so the keys inside the
 * file's content stay as they are in the file (Story 23.1, Epic 23 ADR-2 decision 5);
 * the read's own keys are mapped here.
 *
 * @param path - Directory names from the root, then the file name (Story 23.2),
 *   e.g. `['ModConfig', 'x.json']`
 * @returns File content as parsed JSON, the parse error, and (Admin only) its text and version
 *
 * Accessible to both Admin and Monitor roles.
 */
export async function fetchConfigFileContent(
  path: readonly string[]
): Promise<ApiResponse<ConfigFileContentData>> {
  const filename = toConfigPath(path);
  const raw = await apiClient<ApiResponse<RawConfigFileContentData>>(
    `${API_PREFIX}/files/${encodeURIComponent(filename)}`,
    { transformResponse: false }
  );
  const source = raw.data;
  const data: ConfigFileContentData = {
    filename: typeof source.filename === 'string' ? source.filename : filename,
    content: source.content,
    parseError: toParseError(source.parse_error),
  };
  if (typeof source.text === 'string') data.text = source.text;
  if (typeof source.version === 'string') data.version = source.version;
  return { status: raw.status, data };
}
