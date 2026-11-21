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
  /** Structured context for some errors, e.g. confirmation reasons. */
  details?: Record<string, unknown>;
  /** Other keys some errors carry directly, e.g. a config save's `parse_error` (Story 23.5). */
  [key: string]: unknown;
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
  'idle' | 'downloading' | 'extracting' | 'configuring' | 'complete' | 'error';

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
  assetId: number;
  name: string | null;
  authors: string[] | null;
  description: string | null;
  side: ModSide | null;
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
  /**
   * Most recent game version the evaluated mod ID's releases are tagged for, or null
   * when none of its tags is a version (Story 16.3, Epic 16 ADR-2).
   */
  latestSupportedGameVersion: string | null;
}

/**
 * Individual release/version of a mod.
 * Story 10.6: Added for mod detail view.
 */
export interface ModRelease {
  version: string;
  filename: string;
  /** File ID for the download endpoint; null when the release has no downloadable file (Story 17.1). */
  fileId: number | null;
  downloads: number;
  gameVersions: string[];
  created: string;
  changelog: string | null;
  /** Mod ID inside this release; one database entry can ship several mod IDs. */
  modidstr: string;
}

/**
 * One screenshot of a mod database entry (Story 18.1, Epic 18 ADR-1).
 */
export interface ModScreenshot {
  /** Full-size image on the mod database CDN. */
  imageUrl: string;
  /** The 55x60 thumbnail, or the image URL when the mod database gave no usable thumbnail. */
  thumbnailUrl: string;
  /** The uploaded file name; may be `''`. */
  filename: string;
}

/**
 * Mod lookup response from GET /api/v1alpha1/mods/lookup/{slug}.
 * Story 10.6: Extended to include full release data for detail views.
 *
 * VSS-brs: slug is always from modidstrs[0] (for API lookups), urlalias is
 * separate (for website URLs). These may differ for some mods.
 */
export interface ModLookupData {
  /** Mod identifier from modidstrs[0] - use this for API calls like /mods/lookup/{slug} */
  slug: string;
  /** URL alias for website links (mods.vintagestory.at/{urlalias}). May differ from slug. */
  urlalias: string | null;
  assetId: number;
  name: string;
  author: string;
  description: string | null;
  /**
   * The version an install without a named version picks for `installModId`: its
   * newest stable release with a downloadable file (Story 17.2, Epic 17 ADR-2).
   * Null when none of its releases has a file.
   */
  latestVersion: string | null;
  /**
   * The mod ID an install of the looked-up slug installs (Story 17.2): the slug when
   * a release carries it, otherwise the newest release's mod ID. May differ from `slug`.
   */
  installModId: string;
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
  /** The entry's screenshots in mod database order; only https URLs on the mod database CDN. */
  screenshots: ModScreenshot[];
  /** `https://www.youtube-nocookie.com/embed/<id>` when the entry names a YouTube trailer, else null. */
  trailerUrl: string | null;
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

/** Why the manager does not use a file in the mods folder (Story 24.5, Epic 24 ADR-3). */
export type UnusedFileReason = 'leftover' | 'unreadable' | 'duplicate_mod_id';

/** A file in the mods folder the manager does not use (GET /mods/unused-files). */
export interface UnusedFile {
  name: string;
  sizeBytes: number;
  modifiedAt: string; // ISO 8601
  reason: UnusedFileReason;
  /** For `duplicate_mod_id`: the file the same mod is installed as */
  installedAs: string | null;
}

export interface UnusedFilesData {
  files: UnusedFile[];
}

export interface UnusedFileDeleteData {
  name: string;
  pendingRestart: boolean;
}

/** Result of POST /mods/rescan (Story 24.5, Epic 24 ADR-4). */
export interface ModRescanData {
  added: number;
  removed: number;
  skipped: number;
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
  /**
   * Story 16.8: null when the setting has no value. Story 17.5: null also when the
   * value is a secret withheld from this key (`configured` is then present).
   */
  value: string | number | boolean | null;
  type: SettingType;
  liveUpdate: boolean;
  envManaged: boolean;
  requiresRestart?: boolean;
  /** Story 17.5: the value is a secret; only an Admin key receives it */
  secret?: boolean;
  /**
   * Story 17.5: present only when the value was withheld: whether the secret is set;
   * `value` is then null
   */
  configured?: boolean;
  /**
   * Story 17.6: the game's value when `value` is null; absent when unknown
   */
  default?: boolean;
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
 * How a path in serverconfig.json stands (Story 25.1, Epic 25 ADR-2 decision 2).
 * `not_installed` and `not_created_yet` are normal on a fresh install (values are not
 * camel-cased; only keys are).
 */
export type ServerConfigPathStatus =
  | 'ok'
  | 'missing'
  | 'not_a_directory'
  | 'not_a_file'
  | 'not_readable'
  | 'not_writable'
  | 'not_installed'
  | 'not_created_yet'
  | 'invalid';

/** One `ModPaths` entry, or the save file (Story 25.1). */
export interface ServerConfigPathEntry {
  /** As written in serverconfig.json; null for a null save location or invalid ModPaths */
  given: string | null;
  /** The path the game uses; null when it cannot be resolved */
  resolved: string | null;
  status: ServerConfigPathStatus;
  problem: boolean;
}

/** Response from GET /api/v1alpha1/config/game/paths (Story 25.1, FR346, FR347). */
export interface ServerConfigPathCheck {
  modPaths: ServerConfigPathEntry[];
  saveFile: ServerConfigPathEntry;
  /** The folder the manager installs mods into (Story 25.2) */
  managerModsFolder: string;
  managerModsFolderListed: boolean;
}

/**
 * Response from POST /api/v1alpha1/config/game/settings/{key}.
 */
export interface GameSettingUpdateData {
  key: string;
  /** Story 16.8: null when the setting has no value */
  value: string | number | boolean | null;
  method: 'console_command' | 'file_update';
  pendingRestart: boolean;
}

// ===== API Settings Types =====

/**
 * The value of an API setting. A list only for `scheduled_restart_times` (Story 22.6).
 */
export type ApiSettingValue = string | number | boolean | string[];

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
    /** Story 22.5: seconds between metrics collections (0: off) */
    metricsCollectionInterval: number;
    /** Story 14.6: whether a mod update webhook is set; the URL is never returned */
    modUpdateWebhookConfigured: boolean;
    /** Story 22.6: daily `HH:MM` restart times in server time, sorted; `[]`: none */
    scheduledRestartTimes: string[];
    /** Story 22.6: newest backup files kept; 0: keep all */
    backupKeepCount: number;
    /** Story 23.7: earlier versions kept per config file (1 to 200) */
    configHistoryKeepCount: number;
    /** Story 23.7: days an earlier version is kept; 0: any age */
    configHistoryMaxAgeDays: number;
  };
}

/**
 * Response from setting the mod update webhook (Story 14.6). Reports only whether one
 * is configured; the URL is never returned.
 */
export interface ModUpdateWebhookUpdateData {
  key: string;
  configured: boolean;
}

/**
 * Response from POST /api/v1alpha1/config/api/settings/{key}.
 */
export interface ApiSettingUpdateData {
  key: string;
  value: ApiSettingValue;
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
/**
 * Why a config file did not parse, and where (Story 23.1).
 * `line` and `column` are 1-based, null when unknown.
 */
export interface ConfigParseError {
  message: string;
  line: number | null;
  column: number | null;
}

/** An earlier version of a config file (Story 23.7; API: Story 23.6). */
export interface ConfigRevision {
  id: string;
  /** ISO 8601, UTC */
  savedAt: string;
  savedBy: string;
  /** Bytes */
  size: number;
  sha256: string;
}

/** A config file's earlier versions, newest first (Story 23.7). */
export interface ConfigHistoryData {
  filename: string;
  revisions: ConfigRevision[];
}

/** One earlier version and its text (Story 23.7). */
export interface ConfigRevisionData {
  filename: string;
  revision: ConfigRevision;
  text: string;
}

/** A config file save's answer (Story 23.5). */
export interface ConfigFileSaveData {
  filename: string;
  /** The SHA-256 of the bytes written */
  version: string;
}

/** The answer of a text check (Story 23.5). */
export interface ConfigTextCheck {
  valid: boolean;
  parseError: ConfigParseError | null;
}

export interface ConfigFileContentData {
  filename: string;
  /** The parsed content, keys as in the file; `_raw`/`_parse_error` when it does not parse */
  content: unknown;
  /** Null when the file parsed (Story 23.1) */
  parseError: ConfigParseError | null;
  /** The file's text, with comments: Admin keys only (Story 23.1) */
  text?: string;
  /** The SHA-256 of the file's bytes: Admin keys only (Story 23.1) */
  version?: string;
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
 *
 * VSS-brs: slug is always from modidstrs[0] (for API lookups), urlalias is
 * separate (for website URLs). These may differ for some mods.
 */
export interface ModBrowseItem {
  /** Mod identifier from modidstrs[0] - use this for API calls like /mods/lookup/{slug} */
  slug: string;
  /**
   * Every mod ID of the mod database entry (the listing's modidstrs), in listing
   * order, each once; `slug` is the first when the entry has mod IDs (an entry with
   * none has `[]`, and `slug` falls back to its numeric ID). Used to recognize an
   * installed mod by any of them (Story 17.4).
   */
  modIds: string[];
  /** URL alias for website links (mods.vintagestory.at/{urlalias}). May differ from slug. */
  urlalias: string | null;
  assetId: number;
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
  /**
   * Whether at least one release of this entry is tagged for exactly the installed game
   * version (`ModBrowseData.gameVersion`); per entry, not per mod ID (Story 18.3). Not the
   * detail page's compatibility verdict, which judges the one release an install would
   * pick, so the two can differ. `null` when not known: no server installed, the version
   * has no tag in the mod database, the mod database failed with no earlier copy, or the
   * item has no numeric mod ID.
   */
  hasReleaseForGameVersion: boolean | null;
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
  /**
   * The installed game version the items' `hasReleaseForGameVersion` flags refer to,
   * without a "v" prefix (Story 18.3); a release tagged for it, not a compatibility
   * verdict. `null` exactly when the flags are `null`.
   */
  gameVersion: string | null;
}

/**
 * Response data from GET /api/v1alpha1/mods/gameversions.
 * Story VSS-vth: Game version filter for mod browser.
 */
export interface GameVersionsData {
  versions: string[];
}

/**
 * Response data from GET /api/v1alpha1/mods/tags.
 * VSS-y7u: Server-side filtering for mod browser.
 */
export interface ModTagsData {
  tags: string[];
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
 * VSS-y7u: All filters are now server-side for accurate pagination.
 */
export interface BrowseParams {
  page?: number;
  pageSize?: number;
  sort?: BrowseSortOption;
  search?: string; // Server-side search
  version?: string; // Server-side game version filter (VSS-vth)
  // VSS-y7u: Server-side filters (previously client-side)
  side?: BrowseModSide;
  modType?: ModType;
  tags?: string[]; // OR logic - mod must have at least one matching tag
  filters?: ModFilters; // Deprecated: kept for backwards compatibility
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
 * Game metrics and the players online are null if the game server is not running
 * (playersOnline: Story 22.1).
 */
export interface MetricsSnapshot {
  timestamp: string; // ISO 8601
  apiMemoryMb: number;
  apiCpuPercent: number;
  gameMemoryMb: number | null;
  gameCpuPercent: number | null;
  /** Players online while the game server runs; null otherwise (Story 22.1) */
  playersOnline: number | null;
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

// ============================================
// Mod updates and version changes (Epic 14)
// ============================================

/** Update state of an installed mod (Story 14.1). */
export type ModUpdateState = 'update_available' | 'up_to_date' | 'blocked' | 'unknown';

/** Why an installed mod's update state is unknown. */
export type ModUpdateUnknownReason =
  'not_checked' | 'not_in_database' | 'installed_release_not_listed' | 'version_unparsable';

/** Update status of one installed mod from GET /mods/updates. */
export interface ModUpdateStatus {
  slug: string;
  name: string;
  installedVersion: string;
  status: ModUpdateState;
  offeredVersion: string | null;
  offeredCompatibility: CompatibilityStatus | null;
  offeredPrerelease: boolean | null;
  reason: ModUpdateUnknownReason | null;
  checkedAt: string | null;
  error: string | null;
}

/** Response data from GET /api/v1alpha1/mods/updates. */
export interface ModUpdatesData {
  gameVersion: string | null;
  /** When the last full check finished without failures. */
  checkedAt: string | null;
  updateCount: number;
  mods: ModUpdateStatus[];
}

/** Outcome of one update check. */
export interface ModUpdateCheckSummary {
  checked: number;
  failed: number;
  failedSlugs: string[];
}

/** Response data from POST /api/v1alpha1/mods/updates/check. */
export interface ModUpdateCheckData extends ModUpdatesData {
  check: ModUpdateCheckSummary;
}

/** Why a version change needs confirmation (409 MOD_CONFIRMATION_REQUIRED). */
export type VersionChangeReason = 'not_verified' | 'incompatible' | 'prerelease' | 'older';

/** Response data from PUT /api/v1alpha1/mods/{slug}/version. */
export interface ModVersionChangeData {
  slug: string;
  previousVersion: string;
  version: string;
  filename: string;
  /** Compatibility of the new version; null when nothing changed. */
  compatibility: CompatibilityStatus | null;
  changed: boolean;
  pendingRestart: boolean;
}

/** Outcome of update all for one mod (Story 14.4). */
export type ModUpdateAllOutcome = 'updated' | 'skipped' | 'failed';

/** One mod's result from POST /mods/updates/apply-all. */
export interface ModUpdateAllItem {
  slug: string;
  name: string;
  fromVersion: string;
  toVersion: string;
  outcome: ModUpdateAllOutcome;
  /** Why it was skipped, e.g. 'not_verified' */
  reasons: string[];
  error: string | null;
}

/** Response data from POST /api/v1alpha1/mods/updates/apply-all. */
export interface ModUpdateAllData {
  results: ModUpdateAllItem[];
  updated: number;
  skipped: number;
  failed: number;
  pendingRestart: boolean;
}
