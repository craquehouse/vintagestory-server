# Story 5.2: Mod Installation API

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **administrator**,
I want **to install a mod by entering its slug**,
So that **I don't need to manually download and copy mod files**.

---

## Background

This story implements the mod installation API endpoint that allows administrators to install mods from the VintageStory mod database by slug. It builds directly on Story 5.1 which established the ModService, ModStateManager, and state persistence patterns.

**FRs Covered:** FR11 (Admin can install a mod by entering its slug)
**NFRs Addressed:** NFR11 (graceful API failures), NFR12 (clear network error messages)

---

## Acceptance Criteria

1. **Given** I call `POST /api/v1alpha1/mods` with `{"slug": "smithingplus"}` **When** the mod exists on mods.vintagestory.at **Then** the latest release is downloaded to `/data/serverdata/Mods/` **And** the mod appears in the installed mods list

2. **Given** I provide a full URL instead of a slug **When** I call the install endpoint with `{"slug": "https://mods.vintagestory.at/smithingplus"}` **Then** the slug is extracted from the URL and installation proceeds

3. **Given** the mod slug does not exist **When** I attempt installation **Then** I receive a 404 error with message "Mod not found"

4. **Given** the VintageStory mod API is unavailable **When** I attempt installation **Then** I receive a 502 error with clear message about external API failure (covers NFR11)

5. **Given** the download fails mid-transfer **When** the error occurs **Then** partial files are cleaned up **And** a clear error message is returned (covers NFR12)

---

## Tasks / Subtasks

<!--
CRITICAL TASK STRUCTURE RULES:
1. Each functional task MUST include "+ tests" in its name
2. Do NOT create separate "Write tests" tasks at the end
3. A task is NOT complete until its tests pass
4. Tests verify the specific AC listed for that task

CORRECT PATTERN:
- [ ] Task 1: Implement feature A + tests (AC: 1, 2)
  - [ ] Create implementation
  - [ ] Write tests for success/failure cases

WRONG PATTERN (tests batched at end):
- [ ] Task 1: Implement feature A (AC: 1, 2)
- [ ] Task 2: Write all tests  <- NEVER DO THIS
-->

- [ ] Task 1: Create ModApiClient service + tests (AC: 1, 3, 4)
  - [ ] 1.1: Create `api/src/vintagestory_api/services/mod_api.py` with:
    - `ModApiClient` class using httpx.AsyncClient
    - `get_mod(slug)` - lookup mod by slug, handle "200"/"404" string status codes
    - Use `follow_redirects=True` for download endpoint
    - Default 30s timeout for API calls, 120s for downloads
  - [ ] 1.2: Implement URL slug extraction (parse "https://mods.vintagestory.at/smithingplus" → "smithingplus")
  - [ ] 1.3: Handle API errors gracefully (timeout, connection error, 404)
  - [ ] 1.4: Write tests using respx to mock httpx calls
  - [ ] 1.5: Run `just test-api tests/test_mod_api.py` - verify tests pass

- [ ] Task 2: Implement mod file download with streaming + tests (AC: 1, 5)
  - [ ] 2.1: Add to ModApiClient:
    - `download_file(fileid, dest_path)` - stream download mod file by fileid
    - Use `client.stream()` for memory-efficient large file handling
    - Write to temp file first, then rename (atomic write pattern)
  - [ ] 2.2: Implement cleanup on download failure (delete partial temp file)
  - [ ] 2.3: Write tests for successful download, partial failure cleanup
  - [ ] 2.4: Run `just test-api tests/test_mod_api.py` - verify tests pass

- [ ] Task 3: Implement compatibility check logic + tests (AC: 1)
  - [ ] 3.1: Add to ModApiClient or separate module:
    - `check_compatibility(releases, game_version)` → (status, release)
    - Status is Literal["compatible", "not_verified", "incompatible"]
    - "compatible" = exact version match in release tags
    - "not_verified" = same major.minor version match
    - "incompatible" = no matching version found
  - [ ] 3.2: Returns best matching release for installation
  - [ ] 3.3: Write tests for all three compatibility scenarios
  - [ ] 3.4: Run `just test-api tests/test_mod_api.py` - verify tests pass

- [ ] Task 4: Extend ModService with install_mod method + tests (AC: 1, 2, 3)
  - [ ] 4.1: Add to ModService in `api/src/vintagestory_api/services/mods.py`:
    - `install_mod(slug_or_url, version=None)` async method
    - Parse slug from URL if provided
    - Lookup mod via ModApiClient
    - Check if mod already installed (return error or update)
    - Download file to mods directory
    - Import mod (extract metadata, update state)
    - Set pending_restart if server running
  - [ ] 4.2: Return structured result with: success, version, compatibility, filename
  - [ ] 4.3: Write integration tests for install flow
  - [ ] 4.4: Run `just test-api tests/test_mod_service.py` - verify tests pass

- [ ] Task 5: Create /mods router with POST endpoint + tests (AC: 1, 2, 3, 4, 5)
  - [ ] 5.1: Create `api/src/vintagestory_api/routers/mods.py` with:
    - `POST /api/v1alpha1/mods` - install mod by slug
    - Request body: `{"slug": "smithingplus"}` or `{"slug": "https://mods.vintagestory.at/..."}`
    - Requires Admin role authentication
  - [ ] 5.2: Implement proper HTTP status codes:
    - 201 Created on success
    - 400 Bad Request for invalid input
    - 404 Not Found if mod doesn't exist
    - 409 Conflict if mod already installed
    - 502 Bad Gateway for external API errors
  - [ ] 5.3: Register router in main.py
  - [ ] 5.4: Write API endpoint tests covering all status codes
  - [ ] 5.5: Run `just test-api tests/test_mods_router.py` - verify tests pass

- [ ] Task 6: Final validation + tests (AC: all)
  - [ ] 6.1: Run `just test-api` - verify full test suite passes
  - [ ] 6.2: Run `just check` - verify lint, typecheck, and all tests pass
  - [ ] 6.3: Manual test: Install a real mod (smithingplus) in dev environment
  - [ ] 6.4: Verify mod appears in state and filesystem

---

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Do not batch tests into a separate "Write tests" task at the end
- Run `just test-api` to verify tests pass before marking task complete
- Run `just check` for full validation (lint + typecheck + test) before story completion

**Test file locations:**
```
api/tests/
├── test_mod_api.py          # Tasks 1, 2, 3: ModApiClient tests
├── test_mod_service.py      # Task 4: ModService install tests (extend existing)
└── test_mods_router.py      # Task 5: API endpoint tests (new file)
```

**Test mocking pattern:**
Use `respx` for mocking httpx async client:
```python
import respx
from httpx import Response

@respx.mock
async def test_get_mod_success():
    respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
        return_value=Response(200, json={
            "statuscode": "200",
            "mod": {"name": "Smithing Plus", "releases": [...]}
        })
    )
    # Test code...
```

### Security Requirements

**Follow patterns in `project-context.md` → Security Patterns section:**

- Validate slug input (alphanumeric + dash only, max 50 chars)
- Use atomic writes for downloaded files (temp + rename)
- Clean up partial downloads on failure
- Admin-only endpoint (require_admin dependency)

### Development Commands

Use `just` for all development tasks:
- `just test` - Run all tests
- `just test-api` - Run API tests
- `just test-api tests/test_mod_api.py` - Run specific test file
- `just check` - Full validation (lint + typecheck + test)
- `just lint` - Run all linters
- `just lint-api --fix` - Lint with auto-fix

### Architecture & Patterns

**From architecture.md → Epic 5: Mod Management Architecture:**

**VintageStory Mod API patterns (from agentdocs/vintagestory-modapi.md):**
- Base URL: `https://mods.vintagestory.at/api/`
- Status codes are STRINGS ("200", "404"), not integers
- `releases[0]` is always the latest release
- Download endpoint: `https://mods.vintagestory.at/download?fileid={fileid}`
- Download redirects to CDN at `moddbcdn.vintagestory.at`

**ModApiClient implementation pattern:**
```python
import httpx
from typing import Optional

class ModApiClient:
    BASE_URL = "https://mods.vintagestory.at/api"
    DOWNLOAD_URL = "https://mods.vintagestory.at/download"
    DEFAULT_TIMEOUT = 30.0
    DOWNLOAD_TIMEOUT = 120.0

    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.DEFAULT_TIMEOUT,
                follow_redirects=True
            )
        return self._client

    async def get_mod(self, slug: str) -> Optional[dict]:
        """Get mod details by slug."""
        client = await self._get_client()
        try:
            response = await client.get(f"{self.BASE_URL}/mod/{slug}")
            data = response.json()
            # CRITICAL: statuscode is STRING, not int!
            if data.get("statuscode") == "200":
                return data["mod"]
            return None
        except httpx.HTTPError:
            return None

    async def download_file(self, fileid: int, dest_path: Path) -> bool:
        """Download mod file by fileid with streaming."""
        client = await self._get_client()
        temp_path = dest_path.with_suffix('.tmp')
        try:
            async with client.stream(
                "GET",
                f"{self.DOWNLOAD_URL}?fileid={fileid}",
                timeout=self.DOWNLOAD_TIMEOUT
            ) as response:
                response.raise_for_status()
                with open(temp_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)
            # Atomic rename
            temp_path.rename(dest_path)
            return True
        except (httpx.HTTPError, IOError):
            # Cleanup partial download
            if temp_path.exists():
                temp_path.unlink()
            return False
```

**Compatibility check pattern:**
```python
from typing import Literal, Tuple, Optional

CompatibilityStatus = Literal["compatible", "not_verified", "incompatible"]

def check_compatibility(
    releases: list[dict],
    game_version: str
) -> Tuple[CompatibilityStatus, Optional[dict]]:
    """Check mod compatibility with installed game version."""
    # Exact match
    for release in releases:
        if game_version in release.get("tags", []):
            return ("compatible", release)

    # Major.minor match
    major_minor = ".".join(game_version.split(".")[:2])
    for release in releases:
        for tag in release.get("tags", []):
            if tag.startswith(major_minor + ".") or tag == major_minor:
                return ("not_verified", release)

    # No match - return latest
    if releases:
        return ("incompatible", releases[0])
    return ("incompatible", None)
```

**URL slug extraction pattern:**
```python
import re
from urllib.parse import urlparse

def extract_slug(slug_or_url: str) -> str:
    """Extract mod slug from URL or return as-is if already a slug."""
    if slug_or_url.startswith("http"):
        parsed = urlparse(slug_or_url)
        # Path is like /smithingplus or /mod/smithingplus
        path = parsed.path.strip("/")
        # Remove "mod/" prefix if present
        if path.startswith("mod/"):
            path = path[4:]
        return path
    return slug_or_url
```

### Project Structure Notes

**Files to create:**
```
api/src/vintagestory_api/
├── services/
│   └── mod_api.py           # NEW - ModApiClient for external API
├── routers/
│   └── mods.py              # NEW - /mods/* endpoints
```

**Files to modify:**
```
api/src/vintagestory_api/
├── main.py                  # Add mods router
├── services/mods.py         # Add install_mod method
├── models/mods.py           # Add request/response models if needed
```

**Test files to create:**
```
api/tests/
├── test_mod_api.py          # ModApiClient tests
└── test_mods_router.py      # Mods router tests
```

### Previous Story Intelligence (5.1)

**Key patterns established in 5.1:**
- ModService singleton via `get_mod_service()`
- ModStateManager for state persistence with atomic writes
- PendingRestartState for restart tracking
- `import_mod()` extracts modinfo.json and caches metadata
- `sync_state_with_disk()` reconciles state with filesystem
- File suffix approach (`.disabled`) for enable/disable
- Server integration: `set_server_running()` method

**Code review findings from 5.1:**
- Zip slip protection using Path.resolve() validation
- Server-mod integration via lazy import pattern to avoid circular deps
- Story 5.5 (Mod List API) will add the API endpoints - this story focuses on installation

**Integration point:**
After downloading a mod file, use `import_mod(zip_path)` from ModStateManager to:
1. Extract modinfo.json
2. Parse slug/version
3. Cache metadata
4. Update state index

### Git Intelligence

**Recent commits establishing patterns:**
- `682135d` - feat(story-5.1): complete mod service with review follow-up fixes
- `b6d6097` - review(story-5.1): add code review action items and update status

**Commit message format:** `type(scope): description`
- `feat(mods)`: for new functionality
- `fix(mods)`: for bug fixes
- `test(mods)`: for test-only changes

### Error Handling

**Use error codes from architecture.md:**
```python
# api/src/vintagestory_api/models/errors.py
class ErrorCode:
    MOD_NOT_FOUND = "MOD_NOT_FOUND"
    MOD_ALREADY_INSTALLED = "MOD_ALREADY_INSTALLED"
    EXTERNAL_API_ERROR = "EXTERNAL_API_ERROR"
    DOWNLOAD_FAILED = "DOWNLOAD_FAILED"
```

**HTTP exception pattern:**
```python
from fastapi import HTTPException

raise HTTPException(
    status_code=502,
    detail={
        "code": ErrorCode.EXTERNAL_API_ERROR,
        "message": "VintageStory mod API is unavailable",
    }
)
```

### References

- `project-context.md` - Critical implementation rules and patterns
- `_bmad-output/planning-artifacts/architecture.md` - Full architecture (Epic 5 section)
- `agentdocs/vintagestory-modapi.md` - Complete mod API documentation with httpx examples
- `_bmad-output/implementation-artifacts/5-1-mod-service-and-state-management.md` - Previous story patterns
- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.2: Mod Installation API]

---

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

