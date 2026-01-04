# Story 9.3: Mod Cache Eviction Strategy

## Story

As an **administrator**,
I want **the mod cache to automatically clean up old files**,
So that **disk space is managed without manual intervention**.

## Status: Complete

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
  **Then** log entries are emitted: `{"event": "cache_evicted", "file": "...", "reason": "size_limit"}`
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

## Files Changed

- `api/src/vintagestory_api/config.py` - Added mod_cache_max_size_mb setting
- `api/src/vintagestory_api/services/cache_eviction.py` - New CacheEvictionService
- `api/src/vintagestory_api/services/mod_api.py` - Eviction integration
- `api/src/vintagestory_api/services/mods.py` - Wiring and initialization
- `api/tests/test_cache_eviction.py` - New test file
- `api/tests/test_config.py` - Config validation tests
