# Story 13.1: Server Versions API

Status: done

## Story

As a **frontend developer**,
I want **an API endpoint to list available server versions**,
So that **the version browser can display all available releases**.

## Acceptance Criteria

1. **Given** I call `GET /api/v1alpha1/versions` as Admin or Monitor
   **When** the endpoint is called
   **Then** I receive a list of available versions from both stable and unstable channels
   **And** each version includes: version, channel, filename, filesize, md5, is_latest

2. **Given** I call `GET /api/v1alpha1/versions?channel=stable`
   **When** the channel filter is applied
   **Then** I receive only stable versions

3. **Given** I call `GET /api/v1alpha1/versions?channel=unstable`
   **When** the channel filter is applied
   **Then** I receive only unstable versions

4. **Given** the VintageStory API is unavailable
   **When** I call the versions endpoint
   **Then** I receive cached data if available
   **And** the response includes a `cached: true` indicator

5. **Given** I call `GET /api/v1alpha1/versions/{version}`
   **When** the version exists
   **Then** I receive detailed information for that specific version

## Tasks / Subtasks

- [x] Task 1: Extend VersionsCache to store full version lists + tests (AC: 4)
  - [x] Subtask 1.1: Rename/extend `LatestVersionsCache` to also store full version lists (not just latest)
  - [x] Subtask 1.2: Add methods: `get_versions(channel)`, `set_versions(channel, versions)`, `get_all_versions()`
  - [x] Subtask 1.3: Add `cached_at` timestamp for staleness detection
  - [x] Subtask 1.4: Write unit tests for new cache methods

- [x] Task 2: Create Pydantic models for versions response + tests (AC: 1)
  - [x] Subtask 2.1: Create `VersionListItem` model extending existing `VersionInfo`
  - [x] Subtask 2.2: Create `VersionListResponse` with pagination-like metadata
  - [x] Subtask 2.3: Write unit tests for model serialization

- [x] Task 3: Create /versions router with list and detail endpoints + tests (AC: 1, 2, 3, 5)
  - [x] Subtask 3.1: Create `api/src/vintagestory_api/routers/versions.py` router
  - [x] Subtask 3.2: Implement `GET /versions` endpoint with channel filter
  - [x] Subtask 3.3: Implement `GET /versions/{version}` detail endpoint
  - [x] Subtask 3.4: Register router in `main.py`
  - [x] Subtask 3.5: Write integration tests for all endpoints

- [x] Task 4: Add cache indicator and staleness handling + tests (AC: 4) [Completed in Task 3]
  - [x] Subtask 4.1: Add `cached: bool` and `cached_at: datetime | None` to response
  - [x] Subtask 4.2: Return cached data with indicator when API fails
  - [x] Subtask 4.3: Write tests for cache fallback behavior

- [x] Task 5: Update server_versions job to populate new cache + tests (AC: 4)
  - [x] Subtask 5.1: Modify `check_server_versions()` to also cache full version lists
  - [x] Subtask 5.2: Ensure cache is populated on job run
  - [x] Subtask 5.3: Write tests for job populating cache

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Do not batch tests into a separate "Write tests" task at the end
- Run `just test` to verify all tests pass before marking task complete

### Security Requirements

**Follow patterns in `project-context.md` → Security Patterns section:**

- Both Admin and Monitor roles can access versions endpoint (read-only)
- No sensitive data in version responses
- DEBUG mode gating not needed (read-only public data)

### Development Commands

Use `just` for all development tasks:
- `just test` - Run all tests
- `just test-api` - Run API tests only
- `just test-api -k "versions"` - Run version-related tests
- `just check` - Full validation (lint + typecheck + test)
- `just lint` - Run all linters

### Architecture & Patterns

**Existing Infrastructure:**

The project already has significant version-related infrastructure from Story 8.2:

1. **VersionsCache** (`api/src/vintagestory_api/services/versions_cache.py`):
   - Currently stores only `stable_version` and `unstable_version` (latest only)
   - Singleton pattern with `get_versions_cache()` accessor
   - Has `last_checked` timestamp
   - **Extend this** to also cache full version lists

2. **ServerService** (`api/src/vintagestory_api/services/server.py`):
   - `get_available_versions(channel)` - Already fetches full version data from API
   - Returns `dict[str, VersionInfo]` - Use this method, don't duplicate
   - Handles both stable and unstable channels

3. **VersionInfo Model** (`api/src/vintagestory_api/models/server.py`):
   - Already exists with: version, filename, filesize, md5, cdn_url, local_url, is_latest, channel
   - **Reuse this model** for list items

4. **server_versions job** (`api/src/vintagestory_api/jobs/server_versions.py`):
   - Runs periodically to check for new versions
   - Currently calls `ServerService.get_available_versions()` for both channels
   - Populates LatestVersionsCache with just the latest versions
   - **Modify** to also populate full version list cache

**VintageStory Version API Reference:**

```
Stable: https://api.vintagestory.at/stable.json
Unstable: https://api.vintagestory.at/unstable.json

Response Format:
{
  "1.21.6": {
    "linuxserver": {
      "filename": "vs_server_linux-x64_1.21.6.tar.gz",
      "filesize": "40.2 MB",
      "md5": "checksum_here",
      "urls": {
        "cdn": "https://cdn.vintagestory.at/gamefiles/stable/vs_server_linux-x64_1.21.6.tar.gz",
        "local": "https://vintagestory.at/api/gamefiles/stable/vs_server_linux-x64_1.21.6.tar.gz"
      },
      "latest": true  // Only one version has this
    }
  },
  "1.21.5": { ... }
}
```

**Important Notes:**
- Version keys are NOT guaranteed to be ordered (use is_latest flag to find latest)
- Each version has data for multiple platforms (linuxserver, windows, mac, etc.)
- We only care about `linuxserver` for this server management tool
- `filesize` is human-readable string (e.g., "40.2 MB")

**API Response Pattern (project-context.md):**

```python
# Success
{
  "status": "ok",
  "data": {
    "versions": [...],
    "cached": false,
    "cached_at": null
  }
}

# Error
{
  "detail": {
    "code": "EXTERNAL_API_ERROR",
    "message": "VintageStory API unavailable"
  }
}
```

**Cache Strategy:**

1. **Primary Cache Population:** The `server_versions` background job fetches version data periodically
2. **On-Demand Fetch:** If cache is empty, endpoint can fetch directly
3. **Staleness:** Include `cached: true` and `cached_at` in response so frontend knows data freshness
4. **Error Handling:** If API fails and cache exists, return cached data with `cached: true`

**New Router Pattern:**

```python
# api/src/vintagestory_api/routers/versions.py
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Literal

from vintagestory_api.middleware.auth import RequireAuth
from vintagestory_api.services.server import get_server_service
from vintagestory_api.services.versions_cache import get_versions_cache

router = APIRouter(prefix="/versions", tags=["versions"])

@router.get("")
async def list_versions(
    channel: Literal["stable", "unstable"] | None = Query(None),
    _: RequireAuth = Depends(),
):
    """List available server versions."""
    ...

@router.get("/{version}")
async def get_version_detail(
    version: str,
    _: RequireAuth = Depends(),
):
    """Get details for a specific version."""
    ...
```

### Project Structure Notes

**Files to modify:**
- `api/src/vintagestory_api/services/versions_cache.py` - Extend cache to store full lists
- `api/src/vintagestory_api/jobs/server_versions.py` - Populate full cache
- `api/src/vintagestory_api/main.py` - Register new router
- `api/tests/test_versions_cache.py` - Add tests for new methods

**Files to create:**
- `api/src/vintagestory_api/routers/versions.py` - New versions router
- `api/tests/test_versions_router.py` - Integration tests for versions endpoints
- `api/src/vintagestory_api/models/versions.py` - (Optional) Version response models if not fitting in server.py

**Naming Conventions (project-context.md):**
- Python files: snake_case
- Python classes: PascalCase
- API routes: kebab-case in URLs (but `/versions` is already lowercase)
- JSON fields: snake_case (API boundary)

### Previous Story Context

**Epic 13 Status:**
- Epic 13 is "in-progress" (set from this story creation)
- Story 13-0 (Technical Preparation) is still in backlog - this story proceeds without it
- The existing infrastructure from Story 8.2 provides most of what's needed

**Key Learnings from Story 10.1 (Mod Browse API):**
- Cache full data, apply filtering/pagination client-side
- Include `cached` indicator for frontend freshness awareness
- Use existing service methods instead of duplicating API calls
- Write tests alongside each task (not batched)

### Git Workflow

**Branch:** `story/13-1-server-versions-api`

**Commit Pattern:**
```
feat(story-13.1/task-1): extend VersionsCache for full version lists
feat(story-13.1/task-2): add Pydantic models for versions response
feat(story-13.1/task-3): create /versions router with endpoints
feat(story-13.1/task-4): add cache indicator and staleness handling
feat(story-13.1/task-5): update server_versions job to populate cache
```

### References

- `project-context.md` - Critical implementation rules and patterns
- [Source: api/src/vintagestory_api/services/versions_cache.py] - Existing cache implementation
- [Source: api/src/vintagestory_api/services/server.py] - ServerService with get_available_versions()
- [Source: api/src/vintagestory_api/jobs/server_versions.py] - Background job for version checking
- [Source: api/src/vintagestory_api/models/server.py] - Existing VersionInfo model
- [Source: agentdocs/server-installation.md] - VintageStory version API documentation
- [Source: _bmad-output/planning-artifacts/epics.md#Story-13.1] - Story requirements

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- Task 1: Extended LatestVersionsCache with full version list storage. Added methods: `get_versions(channel)`, `set_versions(channel, versions)`, `get_all_versions()`, `has_cached_versions()`, and `cached_at` property. 11 new unit tests pass.
- Task 2: Created Pydantic models VersionListResponse and VersionDetailResponse in new models/versions.py. Reuses existing VersionInfo model. 6 new unit tests pass.
- Task 3: Created versions router with GET /versions (with channel filter) and GET /versions/{version} endpoints. Registered in main.py. Includes cache fallback on API errors. 14 integration tests pass.
- Task 4: Cache indicator and staleness handling was implemented as part of Task 3 (cached and cached_at fields in responses).
- Task 5: Updated server_versions job to populate full version lists in cache alongside latest version strings. 6 new unit tests pass.

### File List

- Modified: api/src/vintagestory_api/services/versions_cache.py
- Modified: api/tests/test_versions_cache.py
- Created: api/src/vintagestory_api/models/versions.py
- Created: api/tests/test_versions_models.py
- Created: api/src/vintagestory_api/routers/versions.py
- Created: api/tests/test_versions_router.py
- Modified: api/src/vintagestory_api/main.py
- Modified: api/src/vintagestory_api/jobs/server_versions.py
- Created: api/tests/test_server_versions_job.py

## Review Follow-ups (AI)

- [x] [AI-Review][MEDIUM] AC 1 wording mismatch - should say "Admin or Monitor" not just "Admin" [13-1-server-versions-api.md:13]
- [x] [AI-Review][MEDIUM] Remove duplicate version_check_summary log in server_versions.py [api/src/vintagestory_api/jobs/server_versions.py:106]
- [x] [AI-Review][LOW] Add type annotations to pytest fixture parameters in test_versions_router.py [api/tests/test_versions_router.py:326]
- [x] [AI-Review][LOW] Update completion notes to reflect accurate test counts (51 total vs 37 claimed) [13-1-server-versions-api.md:274] - Verified: 37 new tests is correct (11+6+14+6)

