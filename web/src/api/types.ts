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
 * Disk space data from /server/status endpoint.
 */
export interface DiskSpaceData {
  totalGb: number;
  usedGb: number;
  availableGb: number;
  usagePercent: number;
  warning: boolean;
}

/**
 * Server status response from GET /api/v1alpha1/server/status.
 * Note: API returns snake_case, but apiClient transforms to camelCase.
 */
export interface ServerStatus {
  state: ServerState;
  version: string | null;
  uptimeSeconds: number | null;
  lastExitCode: number | null;
  // Story 8.2: Version cache fields
  availableStableVersion: string | null;
  availableUnstableVersion: string | null;
  versionLastChecked: string | null;
  // API-008: Disk space monitoring
  diskSpace: DiskSpaceData | null;
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
 * Individual release/version of a mod.
 * Story 10.6: Added for mod detail view.
 */
export interface ModRelease {
  version: string;
  filename: string;
  fileId: number;
  downloads: number;
  gameVersions: string[];
  created: string;
  changelog: string | null;
}

/**
 * Mod lookup response from GET /api/v1alpha1/mods/lookup/{slug}.
 * Story 10.6: Extended to include full release data for detail views.
 */
export interface ModLookupData {
  slug: string;
  name: string;
  author: string;
  description: string | null;
  latestVersion: string;
  downloads: number;
  follows: number;
  side: ModSide;
  compatibility: ModCompatibility;
  logoUrl: string | null;
  releases: ModRelease[];
  tags: string[];
  homepageUrl: string | null;
  sourceUrl: string | null;
  created: string | null;
  lastReleased: string | null;
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

// ===== Config File Types (Story 6.6, Story 9.7) =====

/**
 * Response from GET /api/v1alpha1/config/directories (list directories).
 * Story 9.7: Dynamic File Browser
 */
export interface ConfigDirectoryListData {
  directories: string[];
}

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

// ===== Log Types =====

/**
 * Information about a single log file.
 */
export interface LogFileInfo {
  name: string;
  sizeBytes: number;
  modifiedAt: string; // ISO 8601
}

/**
 * Response from GET /api/v1alpha1/console/logs.
 */
export interface LogFilesData {
  files: LogFileInfo[];
  logsDir: string;
}

// ===== Mod Browse Types (Story 10.3) =====

/**
 * Sort options for the mod browse API.
 * Note: 'name' is client-side only (API doesn't support it yet - see polish backlog API-029)
 */
export type BrowseSortOption = 'downloads' | 'trending' | 'recent' | 'name';

/**
 * Mod type from the browse API.
 */
export type ModType = 'mod' | 'externaltool' | 'other';

/**
 * Mod side values from the browse API (lowercase version).
 * Note: Different from ModSide used for installed mods which uses capitalized values.
 */
export type BrowseModSide = 'client' | 'server' | 'both';

/**
 * Single mod from the browse API.
 * Note: API returns snake_case, apiClient transforms to camelCase.
 */
export interface ModBrowseItem {
  slug: string;
  name: string;
  author: string;
  summary: string | null;
  downloads: number;
  follows: number;
  trendingPoints: number;
  side: BrowseModSide;
  modType: ModType;
  logoUrl: string | null;
  tags: string[];
  lastReleased: string | null;
}

/**
 * Pagination metadata from browse API.
 */
export interface BrowsePaginationMeta {
  page: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
  hasNext: boolean;
  hasPrev: boolean;
}

/**
 * Response data from GET /api/v1alpha1/mods/browse.
 */
export interface ModBrowseData {
  mods: ModBrowseItem[];
  pagination: BrowsePaginationMeta;
}

/**
 * Filter criteria for client-side filtering.
 */
export interface ModFilters {
  side?: BrowseModSide;
  tags?: string[]; // Filter by any of these tags (OR logic)
  modType?: ModType;
  gameVersion?: string; // Filter by compatibility
}

/**
 * Parameters for browse API request.
 */
export interface BrowseParams {
  page?: number;
  pageSize?: number;
  sort?: BrowseSortOption;
  search?: string; // For client-side filtering (API doesn't support search yet)
  filters?: ModFilters; // For client-side filtering
}

// ===== Version Types (Story 13.2) =====

/**
 * Channel options for VintageStory versions.
 */
export type VersionChannel = 'stable' | 'unstable';

/**
 * Version information from GET /api/v1alpha1/versions.
 * Story 13.2: Version Card Component
 *
 * Note: API returns snake_case, apiClient transforms to camelCase.
 */
export interface VersionInfo {
  version: string;
  filename: string;
  filesize: string; // Human-readable, e.g., "40.2 MB"
  md5: string;
  cdnUrl: string;
  localUrl: string;
  isLatest: boolean;
  channel: VersionChannel;
}

/**
 * Response from GET /api/v1alpha1/versions.
 */
export interface VersionListResponse {
  versions: VersionInfo[];
  total: number;
  cached: boolean;
  cachedAt: string | null; // ISO 8601
}

/**
 * Response from GET /api/v1alpha1/versions/{version}.
 */
export interface VersionDetailResponse {
  version: VersionInfo;
  cached: boolean;
  cachedAt: string | null; // ISO 8601
}

// ===== Metrics Types (Story 12.4) =====

/**
 * Single metrics snapshot from GET /api/v1alpha1/metrics/current.
 * Story 12.4: Dashboard Stats Cards
 *
 * Note: API returns snake_case with serialization aliases, apiClient transforms to camelCase.
 * Game metrics are null if the game server is not running.
 */
export interface MetricsSnapshot {
  timestamp: string; // ISO 8601
  apiMemoryMb: number;
  apiCpuPercent: number;
  gameMemoryMb: number | null;
  gameCpuPercent: number | null;
}

/**
 * Response from GET /api/v1alpha1/metrics/history.
 */
export interface MetricsHistoryResponse {
  metrics: MetricsSnapshot[];
  count: number;
}

// ===== Debug Types (VSS-c9o) =====

/**
 * Response from GET /api/v1alpha1/debug.
 * VSS-c9o: Debug logging toggle
 */
export interface DebugStatusData {
  debugEnabled: boolean;
}

/**
 * Response from POST /api/v1alpha1/debug/enable or disable.
 */
export interface DebugToggleData {
  debugEnabled: boolean;
  changed: boolean;
}
