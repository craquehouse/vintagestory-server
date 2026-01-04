# Story 9.3: Mod Cache Eviction Strategy

## Story

As an **administrator**,
I want **the mod cache to automatically clean up old files**,
So that **disk space is managed without manual intervention**.

## Status: In Progress

## Acceptance Criteria

- [x] **Given** the mod cache directory exists
  **When** total cache size exceeds the configured limit (default 500MB)
  **Then** the oldest accessed files are evicted until under limit (LRU strategy)
  *(Covers FR44)*

- [x] **Given** I set `VS_MOD_CACHE_MAX_SIZE_MB` environment variable
  **When** the API server starts
  **Then** the cache limit is set to the configured value
  *(Covers FR45)*

- [x] **Given** cache eviction occurs
  **When** files are removed
  **Then** log entries are emitted: `{"event": "cache_evicted", "file": "...", "reason": "<reason>"}`
  where `reason` is one of: `"size_limit"` (automatic LRU eviction) or `"manual_clear"` (via `evict_all()`)
  *(Covers FR46)*

- [x] **Given** the cache is under the size limit
  **When** eviction check runs
  **Then** no files are removed

## Technical Notes

### Implementation Summary

1. **Configuration** (`api/src/vintagestory_api/config.py`):
   - Added `mod_cache_max_size_mb: int = 500` setting
   - Added validator to reject negative values
   - Set to 0 to disable eviction entirely

2. **CacheEvictionService** (`api/src/vintagestory_api/services/cache_eviction.py`):
   - LRU eviction strategy based on file access times (atime)
   - Scans `cache_dir/mods/` for `.zip` and `.cs` files
   - `evict_if_needed()`: Runs after each mod download
   - `evict_all()`: Manual cache clearing
   - `get_cache_stats()`: Returns file count, total size, max size

3. **Integration** (`api/src/vintagestory_api/services/mod_api.py`):
   - `ModApiClient` accepts optional `cache_eviction_service` parameter
   - Eviction runs automatically after successful downloads

4. **ModService** (`api/src/vintagestory_api/services/mods.py`):
   - Creates `CacheEvictionService` based on config
   - Passes to `ModApiClient` on initialization
   - Exposes `cache_eviction` property for external access

### Environment Variable

| Variable | Default | Description |
|----------|---------|-------------|
| `VS_MOD_CACHE_MAX_SIZE_MB` | `500` | Maximum mod cache size in MB. Set to `0` to disable eviction. |

### Test Coverage

- `tests/test_cache_eviction.py`: 16 tests covering:
  - Initialization and configuration
  - Cache statistics
  - LRU eviction order
  - Edge cases (empty cache, missing directories)
  - File pattern filtering (.zip, .cs only)
- `tests/test_config.py`: 4 tests for configuration validation

## Dev Technical Tasks

1. [x] Add `VS_MOD_CACHE_MAX_SIZE_MB` configuration with validator
2. [x] Create `CacheEvictionService` with LRU strategy
3. [x] Integrate eviction into `ModApiClient.download_mod()`
4. [x] Update `ModService` to create and wire up eviction service
5. [x] Write comprehensive tests
6. [x] Run lint and type checks

## Review Follow-ups (AI)

### HIGH Priority

- [x] [AI-Review][HIGH] Fix LRU eviction logic bug - cache_eviction.py:192-215. Current implementation may keep middle-aged files instead of newest. Issue: Early break logic doesn't account for file order. Expected: Always evict oldest files first until under limit.
  - **Fixed**: Simplified loop to use `break` when under limit, track `current_size` properly, re-scan for remaining files after eviction.

- [x] [AI-Review][HIGH] Update AC3 to document all log reason values - cache_eviction.py:200-205, 252-256. Current AC only shows `reason="size_limit"`, but `evict_all()` uses `reason="manual_clear"`. Add both values to AC3 or document in Technical Notes.
  - **Fixed**: Updated AC3 to document both reason values.

- [ ] [AI-Review][HIGH] Document APScheduler type suppressions with tracking issue - scheduler.py:22-27, 180, 186, 188, 197; jobs.py:73; jobs.py models:51, 54. 12 instances of `# type: ignore[import-untyped]` lack inline comments explaining WHY and no tracking issue linked. Per project-context.md Rule #8: "Code suppressions require justification and tracking".
  - **Deferred**: Out of scope for this story - pre-existing code.

### MEDIUM Priority

- [x] [AI-Review][MEDIUM] Add log event verification tests - test_cache_eviction.py. Story claims "Write comprehensive tests" but has NO tests verifying FR46 (log cache eviction events). Missing: test `cache_evicted` events emitted correctly, test `cache_eviction_failed` on errors, test `cache_eviction_complete` summary logging.
  - **Fixed**: Added `TestLogging` test class with 3 tests for log event verification.

### LOW Priority

- [x] [AI-Review][LOW] Fix misleading comment in evict_if_needed() - cache_eviction.py:193. Comment says "handles the case where we break early" but there is no `break` statement. Loop completes normally. Remove or correct comment.
  - **Fixed**: Removed misleading comment, now uses actual `break` statement.

- [ ] [AI-Review][LOW] Reorganize git commits for task-level history. Current story has 1 commit for all 6 tasks. Per project-context.md: "Task-Level Commits Are Mandatory". Split into 6 commits (one per task) for better traceability and Epic 1 retro compliance (tests written with features, not batched).
  - **Deferred**: Would require rewriting history on already-pushed branch.

## Files Changed

- `api/src/vintagestory_api/config.py` - Added mod_cache_max_size_mb setting
- `api/src/vintagestory_api/services/cache_eviction.py` - New CacheEvictionService
- `api/src/vintagestory_api/services/mod_api.py` - Eviction integration
- `api/src/vintagestory_api/services/mods.py` - Wiring and initialization
- `api/tests/test_cache_eviction.py` - New test file
- `api/tests/test_config.py` - Config validation tests
