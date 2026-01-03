# Story 8.1: Mod Cache Refresh Job

Status: in-progress

## Story

As an **administrator**,
I want **the mod API cache to refresh automatically**,
So that **mod information stays current without manual intervention**.

## Acceptance Criteria

1. **Given** `mod_list_refresh_interval` is set to 3600 (1 hour), **When** the scheduler runs, **Then** the mod cache refresh job executes every hour.

2. **Given** the mod API is unreachable during refresh, **When** the job executes, **Then** the error is logged but the job continues on schedule, and stale cache data is preserved.

3. **Given** `mod_list_refresh_interval` is set to 0, **When** the scheduler starts, **Then** the mod cache refresh job is NOT registered.

## Tasks / Subtasks

<!--
CRITICAL TASK STRUCTURE RULES:
1. Each functional task MUST include "+ tests" in its name
2. Do NOT create separate "Write tests" tasks at the end
3. A task is NOT complete until its tests pass
4. Tests verify the specific AC listed for that task

✅ CORRECT PATTERN:
- [ ] Task 1: Implement feature + tests (AC: 1, 2)
  - [ ] Subtask 1.1: Implementation detail
  - [ ] Subtask 1.2: Write tests for feature

❌ WRONG PATTERN (tests batched at end):
- [ ] Task 1: Implement feature (AC: 1, 2)
- [ ] Task 2: Write all tests  <- NEVER DO THIS
-->

- [x] Task 1: Create mod_cache_refresh job function + tests (AC: 1, 2)
  - [x] Subtask 1.1: Create `api/src/vintagestory_api/jobs/mod_cache_refresh.py` with `refresh_mod_cache()` function
  - [x] Subtask 1.2: Use `@safe_job("mod_cache_refresh")` decorator from `jobs/base.py`
  - [x] Subtask 1.3: Implement cache refresh logic using ModService/ModApiClient
  - [x] Subtask 1.4: Write tests for successful cache refresh execution
  - [x] Subtask 1.5: Write tests for error handling (API unreachable - job continues, stale data preserved)

- [x] Task 2: Register job in register_default_jobs + tests (AC: 1, 3)
  - [x] Subtask 2.1: Update `jobs/__init__.py` to register mod_cache_refresh job
  - [x] Subtask 2.2: Verify job respects `mod_list_refresh_interval` setting
  - [x] Subtask 2.3: Write test verifying job is registered when interval > 0
  - [x] Subtask 2.4: Write test verifying job is NOT registered when interval = 0

- [ ] Task 3: Implement cache data structure + tests (AC: 2)
  - [ ] Subtask 3.1: Define what "cache" means for installed mods (update mod metadata from API)
  - [ ] Subtask 3.2: Implement cache update logic that preserves state on API failure
  - [ ] Subtask 3.3: Write tests verifying cache integrity after API failures

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Do not batch tests into a separate "Write tests" task at the end
- Run `just test-api` to verify all tests pass before marking task complete

**Test Files to Create:**
- `api/tests/jobs/test_mod_cache_refresh.py` - Tests for mod cache refresh job

### Job Pattern (from architecture.md & jobs/base.py)

Use the `@safe_job` decorator for standardized error handling:

```python
# api/src/vintagestory_api/jobs/mod_cache_refresh.py
import structlog
from vintagestory_api.jobs.base import safe_job

logger = structlog.get_logger()


@safe_job("mod_cache_refresh")
async def refresh_mod_cache() -> None:
    """Refresh cached mod data from VintageStory mod API.

    This job updates metadata for installed mods by querying the
    mod API. On API failure, existing cache data is preserved.
    """
    # ... implementation ...
```

The `@safe_job` decorator:
- Logs `{job_name}_started` before execution
- Logs `{job_name}_completed` after successful execution
- Catches exceptions, logs `{job_name}_failed`, and does NOT re-raise
- Ensures scheduler continues running even if job fails

### Cache Refresh Logic

**What should the cache refresh do?**

Looking at the existing codebase:
- `ModApiClient.get_mod(slug)` fetches mod details from the API
- `ModStateManager` tracks installed mods and their state
- `ModService.list_mods()` returns installed mod information

The cache refresh should:
1. Get list of installed mod slugs from ModStateManager
2. For each installed mod, fetch updated data from ModApiClient
3. Update stored metadata (e.g., latest version available, compatibility info)
4. If API fails for a mod, keep existing cached data
5. Log summary of updated/failed refreshes

**Key considerations:**
- Job runs on a scheduler - should not hold locks for extended periods
- Should handle partial failures gracefully (some mods refresh, others fail)
- Should not modify mod files - only update cached metadata
- May need to add a cache timestamp to track freshness

### Registration Pattern (from 8-0)

Update `jobs/__init__.py`:

```python
def register_default_jobs(scheduler: SchedulerService) -> None:
    settings = ApiSettingsService().get_settings()
    jobs_registered = 0

    # Story 8.1: mod_cache_refresh job
    if settings.mod_list_refresh_interval > 0:
        from vintagestory_api.jobs.mod_cache_refresh import refresh_mod_cache
        scheduler.add_interval_job(
            refresh_mod_cache,
            seconds=settings.mod_list_refresh_interval,
            job_id="mod_cache_refresh"
        )
        jobs_registered += 1
        logger.info("job_registered", job_id="mod_cache_refresh",
                    interval_seconds=settings.mod_list_refresh_interval)

    # ... rest of jobs ...
```

### API Settings Reference (from 6-3)

`ApiSettings` model fields relevant to this story:
- `mod_list_refresh_interval: int` (default 3600 = 1 hour, ge=0)
  - 0 means disabled (job not registered)
  - Positive integer = interval in seconds

Access via: `ApiSettingsService().get_settings().mod_list_refresh_interval`

### ModService/ModApiClient Reference (from Epic 5)

**ModService** (`services/mods.py`):
- `get_mod_service()` - Get singleton instance
- `list_mods()` - List installed mods with state
- `close()` - Cleanup resources

**ModApiClient** (`services/mod_api.py`):
- `get_mod(slug)` - Fetch mod details from API
- `close()` - Cleanup HTTP client
- Raises `ExternalApiError` on API failures

### Security Considerations

- Job runs with full API server context
- Do not log sensitive data (API keys, etc.)
- Error handling should not crash the scheduler
- Limit concurrent API requests to avoid rate limiting

### Development Commands

Use `just` for all development tasks:
- `just test-api` - Run all API tests
- `just test-api -k "mod_cache"` - Run mod cache tests only
- `just test-api tests/jobs/test_mod_cache_refresh.py -xvs` - Run specific file, verbose
- `just check` - Full validation (lint + typecheck + test)
- `just lint-api` - Run API linter

### Git Workflow for This Story

```bash
# Create feature branch
git checkout -b story/8-1-mod-cache-refresh-job

# Task-level commits
git commit -m "feat(story-8.1/task-1): create refresh_mod_cache job function"
git commit -m "feat(story-8.1/task-2): register mod_cache_refresh in register_default_jobs"
git commit -m "feat(story-8.1/task-3): implement cache data structure"

# Push and create PR
git push -u origin story/8-1-mod-cache-refresh-job
gh pr create --title "Story 8.1: Mod Cache Refresh Job" --body "..."
```

### Source Tree Components

**Files to CREATE:**
- `api/src/vintagestory_api/jobs/mod_cache_refresh.py` - Job implementation
- `api/tests/jobs/test_mod_cache_refresh.py` - Job tests

**Files to MODIFY:**
- `api/src/vintagestory_api/jobs/__init__.py` - Register job in `register_default_jobs()`

### Previous Story Intelligence (8-0)

**From Story 8.0 (Epic 8 Preparation):**
- Jobs infrastructure is set up in `jobs/` directory
- `register_default_jobs()` function exists and is called during lifespan startup
- `@safe_job` decorator available in `jobs/base.py` for error handling
- Jobs with interval=0 should NOT be registered (already tested)
- 890+ tests passing as of Epic 8 preparation

**Key patterns established:**
- Jobs are async functions decorated with `@safe_job`
- Registration happens in `register_default_jobs()` based on settings
- Logging uses structured format: `{job_name}_started`, `{job_name}_completed`, `{job_name}_failed`

### References

- `project-context.md` - Critical implementation rules and patterns
- `_bmad-output/planning-artifacts/architecture.md` - Job patterns and APScheduler usage
- `_bmad-output/planning-artifacts/epics.md#Story 8.1` - Story requirements
- `_bmad-output/implementation-artifacts/8-0-epic-8-preparation.md` - Jobs infrastructure
- `api/src/vintagestory_api/jobs/base.py` - `@safe_job` decorator implementation
- `api/src/vintagestory_api/services/mod_api.py` - ModApiClient for API access
- `api/src/vintagestory_api/services/mods.py` - ModService orchestrator

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- All 921 tests passing after Task 1 completion
- All 925 tests passing after Task 2 completion (4 new registration tests)

### Completion Notes List

**Task 1 Completed:**
- Created `api/src/vintagestory_api/jobs/mod_cache_refresh.py` with `refresh_mod_cache()` function
- Uses `@safe_job("mod_cache_refresh")` decorator for standardized error handling
- Queries installed mods and attempts to refresh each from the external API
- Handles partial failures gracefully (one mod failing doesn't stop others)
- Logs summary with counts of refreshed/failed mods
- Added `api_client` property to ModService for external access to ModApiClient
- Created comprehensive test suite in `api/tests/jobs/test_mod_cache_refresh.py` (12 tests)

### File List

**Task 1:**
- `api/src/vintagestory_api/jobs/mod_cache_refresh.py` (created)
- `api/tests/jobs/__init__.py` (created)
- `api/tests/jobs/test_mod_cache_refresh.py` (created)
- `api/src/vintagestory_api/services/mods.py` (modified - added `api_client` property)

**Task 2:**
- `api/src/vintagestory_api/jobs/__init__.py` (modified - register mod_cache_refresh job)
- `api/src/vintagestory_api/services/scheduler.py` (modified - added `replace_existing=True`)
- `api/tests/test_jobs_registration.py` (modified - added 4 registration tests)
