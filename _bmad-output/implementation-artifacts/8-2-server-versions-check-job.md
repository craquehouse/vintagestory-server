# Story 8.2: Server Versions Check Job

Status: complete

## Story

As an **administrator**,
I want **automatic checks for new VintageStory versions**,
So that **I'm notified when updates are available**.

## Acceptance Criteria

1. **Given** `server_versions_refresh_interval` is set to 86400 (24 hours), **When** the scheduler runs, **Then** the version check job executes daily.

2. **Given** a new version is available, **When** the job detects it, **Then** the new version is logged **And** the version info is available via status API.

3. **Given** the VintageStory versions API is unreachable during check, **When** the job executes, **Then** the error is logged but the job continues on schedule, **And** the last known version data is preserved.

4. **Given** `server_versions_refresh_interval` is set to 0, **When** the scheduler starts, **Then** the server versions check job is NOT registered.

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

- [x] Task 1: Create LatestVersionsCache service + tests (AC: 2, 3)
  - [x] Subtask 1.1: Create `api/src/vintagestory_api/services/versions_cache.py` with `LatestVersionsCache` class
  - [x] Subtask 1.2: Implement in-memory cache for latest stable and unstable versions
  - [x] Subtask 1.3: Add `get_latest_versions()` and `set_latest_versions()` methods
  - [x] Subtask 1.4: Add `get_versions_cache()` singleton accessor
  - [x] Subtask 1.5: Write tests for cache operations (get, set, initial empty state)

- [x] Task 2: Create check_server_versions job function + tests (AC: 1, 2, 3)
  - [x] Subtask 2.1: Create `api/src/vintagestory_api/jobs/server_versions.py` with `check_server_versions()` function
  - [x] Subtask 2.2: Use `@safe_job("server_versions_check")` decorator from `jobs/base.py`
  - [x] Subtask 2.3: Implement version fetching from ServerService and caching
  - [x] Subtask 2.4: Add detection of new versions vs previous check (log when new version found)
  - [x] Subtask 2.5: Write tests for successful version check execution
  - [x] Subtask 2.6: Write tests for error handling (API unreachable - job continues, stale data preserved)

- [x] Task 3: Register job in register_default_jobs + tests (AC: 1, 4)
  - [x] Subtask 3.1: Update `jobs/__init__.py` to register server_versions_check job (uncomment and update placeholder)
  - [x] Subtask 3.2: Verify job respects `server_versions_refresh_interval` setting
  - [x] Subtask 3.3: Write test verifying job is registered when interval > 0
  - [x] Subtask 3.4: Write test verifying job is NOT registered when interval = 0

- [x] Task 4: Expose latest versions in status API + tests (AC: 2)
  - [x] Subtask 4.1: Update ServerStatus model to include `available_stable_version` and `available_unstable_version` fields
  - [x] Subtask 4.2: Update `GET /api/v1alpha1/server/status` to include cached latest versions
  - [x] Subtask 4.3: Write tests for status endpoint including version fields

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Do not batch tests into a separate "Write tests" task at the end
- Run `just test-api` to verify all tests pass before marking task complete

**Test Files to Create:**
- `api/tests/test_versions_cache.py` - Tests for LatestVersionsCache service
- `api/tests/jobs/test_server_versions.py` - Tests for server versions check job

### Job Pattern (from architecture.md & jobs/base.py)

Use the `@safe_job` decorator for standardized error handling:

```python
# api/src/vintagestory_api/jobs/server_versions.py
import structlog
from vintagestory_api.jobs.base import safe_job

logger = structlog.get_logger()


@safe_job("server_versions_check")
async def check_server_versions() -> None:
    """Check for new VintageStory server versions.

    This job queries the VintageStory API for the latest stable and
    unstable versions and caches them for display in the status API.
    """
    # ... implementation ...
```

The `@safe_job` decorator:
- Logs `{job_name}_started` before execution
- Logs `{job_name}_completed` after successful execution
- Catches exceptions, logs `{job_name}_failed`, and does NOT re-raise
- Ensures scheduler continues running even if job fails

### LatestVersionsCache Design

The cache is an in-memory singleton that stores:
- `stable_version`: Latest stable version string (e.g., "1.21.3")
- `unstable_version`: Latest unstable/pre-release version string (e.g., "1.22.0-pre.1")
- `last_checked`: Timestamp of last successful check (for staleness detection)

```python
# api/src/vintagestory_api/services/versions_cache.py
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class LatestVersions:
    stable_version: str | None = None
    unstable_version: str | None = None
    last_checked: datetime | None = None

class LatestVersionsCache:
    """In-memory cache for latest VintageStory version information."""

    def __init__(self) -> None:
        self._versions = LatestVersions()

    def get_latest_versions(self) -> LatestVersions:
        """Get cached latest versions."""
        return self._versions

    def set_latest_versions(
        self,
        stable: str | None = None,
        unstable: str | None = None
    ) -> None:
        """Update cached versions."""
        if stable is not None:
            self._versions.stable_version = stable
        if unstable is not None:
            self._versions.unstable_version = unstable
        self._versions.last_checked = datetime.utcnow()
```

### Version Detection Logic

The job should:
1. Call `ServerService.get_available_versions("stable")` and find the version marked `is_latest=True`
2. Call `ServerService.get_available_versions("unstable")` and find the version marked `is_latest=True`
3. Compare with cached values to detect new versions
4. If new version detected, log with appropriate level (info)
5. Update cache with new values

```python
async def check_server_versions() -> None:
    from vintagestory_api.services.server import get_server_service
    from vintagestory_api.services.versions_cache import get_versions_cache

    server_service = get_server_service()
    cache = get_versions_cache()
    old_versions = cache.get_latest_versions()

    # Check stable channel
    stable_versions = await server_service.get_available_versions("stable")
    new_stable = next(
        (v for v, info in stable_versions.items() if info.is_latest),
        None
    )

    # Check unstable channel
    unstable_versions = await server_service.get_available_versions("unstable")
    new_unstable = next(
        (v for v, info in unstable_versions.items() if info.is_latest),
        None
    )

    # Detect new versions
    if new_stable and new_stable != old_versions.stable_version:
        logger.info("new_stable_version_detected",
                    old_version=old_versions.stable_version,
                    new_version=new_stable)

    if new_unstable and new_unstable != old_versions.unstable_version:
        logger.info("new_unstable_version_detected",
                    old_version=old_versions.unstable_version,
                    new_version=new_unstable)

    # Update cache
    cache.set_latest_versions(stable=new_stable, unstable=new_unstable)

    logger.info("version_check_summary",
                stable=new_stable,
                unstable=new_unstable)
```

### Registration Pattern (from 8-0, 8-1)

Update `jobs/__init__.py` - the placeholder already exists, just uncomment and update:

```python
# Story 8.2: server_versions_check job
# Registered when settings.server_versions_refresh_interval > 0
if settings.server_versions_refresh_interval > 0:
    from vintagestory_api.jobs.server_versions import check_server_versions
    scheduler.add_interval_job(
        check_server_versions,
        seconds=settings.server_versions_refresh_interval,
        job_id="server_versions_check",
    )
    jobs_registered += 1
    logger.info("job_registered", job_id="server_versions_check",
                interval_seconds=settings.server_versions_refresh_interval)
```

### Status API Update

Add optional fields to `ServerStatus` model:

```python
# In api/src/vintagestory_api/models/server.py
class ServerStatus(BaseModel):
    state: ServerState
    version: str | None = None
    uptime_seconds: int | None = None
    last_exit_code: int | None = None
    # Story 8.2: Latest available versions from cache
    available_stable_version: str | None = None
    available_unstable_version: str | None = None
    versions_last_checked: datetime | None = None
```

### API Settings Reference (from 6-3)

`ApiSettings` model fields relevant to this story:
- `server_versions_refresh_interval: int` (default 86400 = 24 hours, ge=0)
  - 0 means disabled (job not registered)
  - Positive integer = interval in seconds

Access via: `ApiSettingsService().get_settings().server_versions_refresh_interval`

### ServerService Reference

From `services/server.py`:
- `get_available_versions(channel)` - Fetches versions from VS API
- Returns `dict[str, VersionInfo]` where key is version string
- Each `VersionInfo` has `is_latest: bool` to identify the latest version in that channel

### Security Considerations

- Job runs with full API server context
- Do not log sensitive data (API keys, etc.)
- Error handling should not crash the scheduler
- HTTP client in ServerService has 300s timeout (suitable for version checks)

### Development Commands

Use `just` for all development tasks:
- `just test-api` - Run all API tests
- `just test-api -k "server_versions"` - Run server versions tests only
- `just test-api tests/jobs/test_server_versions.py -xvs` - Run specific file, verbose
- `just check` - Full validation (lint + typecheck + test)
- `just lint-api` - Run API linter

### Git Workflow for This Story

```bash
# Branch already created: MatthewStockdale/story-8-2

# Task-level commits
git commit -m "feat(story-8.2/task-1): create LatestVersionsCache service"
git commit -m "feat(story-8.2/task-2): create check_server_versions job function"
git commit -m "feat(story-8.2/task-3): register server_versions_check in register_default_jobs"
git commit -m "feat(story-8.2/task-4): expose latest versions in status API"

# Push and create PR
git push -u origin MatthewStockdale/story-8-2
gh pr create --title "Story 8.2: Server Versions Check Job" --body "..."
```

### Source Tree Components

**Files to CREATE:**
- `api/src/vintagestory_api/services/versions_cache.py` - LatestVersionsCache service
- `api/src/vintagestory_api/jobs/server_versions.py` - Job implementation
- `api/tests/test_versions_cache.py` - Cache service tests
- `api/tests/jobs/test_server_versions.py` - Job tests

**Files to MODIFY:**
- `api/src/vintagestory_api/jobs/__init__.py` - Register job in `register_default_jobs()` (uncomment placeholder)
- `api/src/vintagestory_api/models/server.py` - Add version fields to ServerStatus
- `api/src/vintagestory_api/services/server.py` - Update get_server_status to include cached versions
- `api/tests/test_jobs_registration.py` - Add registration tests for server_versions_check

### Previous Story Intelligence (8-1)

**From Story 8.1 (Mod Cache Refresh Job):**
- Jobs infrastructure is fully operational with 925 tests passing
- `@safe_job` decorator works correctly for error isolation
- Registration pattern with settings-based conditional logic is proven
- Test patterns for job execution and error handling established

**Key patterns established:**
- Jobs are async functions decorated with `@safe_job`
- Registration happens in `register_default_jobs()` based on settings
- Logging uses structured format: `{job_name}_started`, `{job_name}_completed`, `{job_name}_failed`
- `replace_existing=True` in scheduler for idempotent registration

### References

- `project-context.md` - Critical implementation rules and patterns
- `_bmad-output/planning-artifacts/architecture.md` - Job patterns and APScheduler usage
- `_bmad-output/planning-artifacts/epics.md#Story 8.2` - Story requirements
- `_bmad-output/implementation-artifacts/8-0-epic-8-preparation.md` - Jobs infrastructure
- `_bmad-output/implementation-artifacts/8-1-mod-cache-refresh-job.md` - Job implementation patterns
- `api/src/vintagestory_api/jobs/base.py` - `@safe_job` decorator implementation
- `api/src/vintagestory_api/services/server.py` - ServerService with get_available_versions

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- **Task 1 complete:** Created LatestVersionsCache service with singleton accessor, LatestVersions dataclass, and comprehensive test suite (13 tests all passing). Uses UTC timestamps and follows existing singleton patterns from project.
- **Task 2 complete:** Created check_server_versions job function with @safe_job decorator, version detection and caching, error handling for API failures, and comprehensive test suite (17 tests all passing).
- **Task 3 complete:** Registered server_versions_check job in register_default_jobs(), job respects server_versions_refresh_interval setting, 5 tests added to test_jobs_registration.py.
- **Task 4 complete:** Updated ServerStatus model with 3 new version fields, updated get_server_status() to include cached versions, added 6 tests for status endpoint version fields.

### File List

- `api/src/vintagestory_api/services/versions_cache.py` (created)
- `api/tests/test_versions_cache.py` (created)
- `api/src/vintagestory_api/jobs/server_versions.py` (created)
- `api/tests/jobs/test_server_versions.py` (created)
- `api/src/vintagestory_api/jobs/__init__.py` (modified)
- `api/tests/test_jobs_registration.py` (modified)
- `api/src/vintagestory_api/models/server.py` (modified)
- `api/src/vintagestory_api/services/server.py` (modified)
- `api/tests/server/test_endpoints.py` (modified)
