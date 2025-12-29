# Story 5.3: Mod Compatibility Validation

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **administrator**,
I want **to see mod compatibility before installation**,
So that **I can make informed decisions about installing mods**.

---

## Background

This story implements the mod lookup API endpoint that allows administrators to preview mod details and compatibility status before installation. It builds directly on Story 5.2 which established the ModApiClient, compatibility checking via `check_compatibility()`, and the `POST /mods` installation endpoint.

**FRs Covered:** FR12 (System validates mod compatibility against current game version), FR13 (System displays warning when mod is not explicitly compatible)

**NFRs Addressed:** NFR11 (graceful API failures), NFR16 (sufficient error context)

---

## Acceptance Criteria

1. **Given** I call `GET /api/v1alpha1/mods/lookup/{slug}` with a valid mod slug **When** the mod exists on mods.vintagestory.at **Then** I receive mod details including: name, author, description, latest version, download count, and compatibility status *(Covers FR12)*

2. **Given** the installed game server version is "1.21.3" **When** I look up a mod with a release tagged for "1.21.3" **Then** compatibility status is "compatible" and no warning is displayed *(Covers FR12)*

3. **Given** the installed game server version is "1.21.3" **When** I look up a mod with latest release tagged for "1.21.0" (same major.minor but different patch) **Then** compatibility status is "not_verified" **And** a warning message indicates the mod wasn't explicitly tested for this version *(Covers FR13)*

4. **Given** the installed game server version is "1.21.3" **When** I look up a mod with releases tagged only for "1.20.x" (different minor) **Then** compatibility status is "incompatible" **And** a warning message indicates version mismatch

5. **Given** the mod slug does not exist **When** I call the lookup endpoint **Then** I receive a 404 error with message "Mod not found"

6. **Given** the VintageStory mod API is unavailable **When** I call the lookup endpoint **Then** I receive a 502 error with clear message about external API failure *(Covers NFR11)*

7. **Given** I call the lookup endpoint with a full URL like `https://mods.vintagestory.at/smithingplus` **When** processing the request **Then** the slug is extracted from the URL and lookup proceeds normally

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

- [ ] Task 1: Create mod lookup Pydantic models + tests (AC: 1)
  - [ ] 1.1: Create `ModLookupResponse` model in `api/src/vintagestory_api/models/mods.py`:
    - `slug: str` - URL-friendly identifier
    - `name: str` - Display name
    - `author: str` - Mod author
    - `description: str | None` - Mod description
    - `latest_version: str` - Latest release version
    - `downloads: int` - Total download count
    - `side: str` - "Both", "Client", or "Server"
    - `compatibility: CompatibilityInfo` - Nested compatibility details
  - [ ] 1.2: Create `CompatibilityInfo` model:
    - `status: Literal["compatible", "not_verified", "incompatible"]`
    - `game_version: str` - Current server version checked against
    - `mod_version: str` - Version being evaluated
    - `message: str | None` - Warning message if not compatible
  - [ ] 1.3: Write unit tests for model serialization
  - [ ] 1.4: Run `just test-api tests/test_models.py` - verify tests pass

- [ ] Task 2: Extend ModService with lookup_mod method + tests (AC: 1, 2, 3, 4, 5, 6)
  - [ ] 2.1: Add `lookup_mod(slug_or_url: str) -> ModLookupResponse | None` to ModService:
    - Parse slug from URL if provided (reuse `extract_slug` from mod_api.py)
    - Call `ModApiClient.get_mod(slug)` to fetch mod details
    - Get current game version from server state (or None if not installed)
    - Call `check_compatibility()` with latest release tags and game version
    - Build `ModLookupResponse` with all details
  - [ ] 2.2: Handle `None` game version (server not installed):
    - Return compatibility status as "not_verified"
    - Set message to "Game server version unknown - cannot verify compatibility"
  - [ ] 2.3: Generate appropriate warning messages:
    - "compatible": No message (None)
    - "not_verified": "Mod not explicitly verified for version {game_version}. May still work."
    - "incompatible": "Mod version {mod_version} is only compatible with {compatible_versions}. Installation may cause issues."
  - [ ] 2.4: Write tests using respx to mock API calls:
    - Test compatible mod (exact version match)
    - Test not_verified mod (same major.minor)
    - Test incompatible mod (no matching version)
    - Test mod not found
    - Test API unavailable
    - Test with full URL input
    - Test with server not installed (no game version)
  - [ ] 2.5: Run `just test-api tests/test_mod_service.py` - verify tests pass

- [ ] Task 3: Create /mods/lookup router endpoint + tests (AC: 1, 5, 6, 7)
  - [ ] 3.1: Add `GET /api/v1alpha1/mods/lookup/{slug}` to `routers/mods.py`:
    - Path parameter: `slug` (accepts slug or URL)
    - Returns `ModLookupResponse` wrapped in API envelope
    - Requires authenticated user (Admin or Monitor - both can lookup)
  - [ ] 3.2: Implement error handling:
    - 404 Not Found if mod doesn't exist (`MOD_NOT_FOUND` error code)
    - 502 Bad Gateway for external API errors (`EXTERNAL_API_ERROR` error code)
    - 400 Bad Request for invalid slug format (`INVALID_SLUG` error code)
  - [ ] 3.3: Write API endpoint tests covering:
    - Successful lookup with all fields populated
    - 404 for non-existent mod
    - 502 for API timeout/unavailable
    - 400 for invalid slug (special characters, too long)
    - Verify Monitor role can access (read-only operation)
  - [ ] 3.4: Run `just test-api tests/test_mods_router.py` - verify tests pass

- [ ] Task 4: Final validation + tests (AC: 1-7)
  - [ ] 4.1: Run `just test-api` - verify full test suite passes
  - [ ] 4.2: Run `just check` - verify lint, typecheck, and all tests pass
  - [ ] 4.3: Manual test: Look up a real mod (smithingplus) with server running
  - [ ] 4.4: Manual test: Look up using full URL format
  - [ ] 4.5: Verify response includes all expected fields with correct compatibility status

---

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Do not batch tests into a separate "Write tests" task at the end
- When it comes time for manual tests, pause, and give the User guidance on how to complete them. Wait until User confirms that they are successful before continuing
- Run `just test-api` to verify tests pass before marking task complete
- Run `just check` for full validation (lint + typecheck + test) before story completion

**Test file locations:**
```
api/tests/
├── test_models.py           # Task 1: ModLookupResponse model tests (extend existing)
├── test_mod_service.py      # Task 2: ModService lookup tests (extend existing)
└── test_mods_router.py      # Task 3: API endpoint tests (extend existing)
```

**Test mocking pattern:**
Use `respx` for mocking httpx async client (established in 5.2):
```python
import respx
from httpx import Response

@respx.mock
async def test_lookup_mod_compatible():
    respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
        return_value=Response(200, json={
            "statuscode": "200",
            "mod": {
                "name": "Smithing Plus",
                "urlalias": "smithingplus",
                "author": "TestAuthor",
                "text": "Mod description",
                "downloads": 12345,
                "side": "Both",
                "releases": [
                    {"modversion": "1.8.3", "tags": ["v1.21.3"]}
                ]
            }
        })
    )
    # Test code...
```

### Security Requirements

**Follow patterns in `project-context.md` → Security Patterns section:**

- Both Admin and Monitor roles can access lookup (read-only operation)
- Use `get_current_user` dependency for authentication (not `require_admin`)
- Validate slug input before passing to external API (reuse `validate_slug()`)
- Never expose internal stack traces in API responses

### Development Commands

Use `just` for all development tasks:
- `just test` - Run all tests
- `just test-api` - Run API tests
- `just test-api tests/test_mod_service.py` - Run specific test file
- `just test-api -k "lookup"` - Run tests matching pattern
- `just check` - Full validation (lint + typecheck + test)
- `just lint` - Run all linters
- `just lint-api --fix` - Lint with auto-fix

### Architecture & Patterns

**From architecture.md → Epic 5: Mod Management Architecture:**

**ModApiClient patterns (established in 5.2 `services/mod_api.py`):**
- `get_mod(slug)` already implemented - returns full mod dict from API
- `check_compatibility(release, game_version)` already implemented - returns status
- `extract_slug()` already implemented - parses URLs to slugs
- `validate_slug()` already implemented - security validation
- Status codes are STRINGS ("200", "404"), not integers - already handled

**Server version retrieval:**
```python
# Get current game version from server status
from vintagestory_api.services.server import get_server_service

server_service = get_server_service()
status = await server_service.get_status()
game_version = status.version  # May be None if not installed
```

**Response envelope pattern:**
```python
# Success response
{"status": "ok", "data": {...}}

# Error response (FastAPI standard)
{"detail": {"code": "MOD_NOT_FOUND", "message": "Mod 'xyz' not found"}}
```

**API versioning:**
- All endpoints under `/api/v1alpha1/`
- Current endpoint: `GET /api/v1alpha1/mods/lookup/{slug}`

### Project Structure Notes

**Files to modify:**
```
api/src/vintagestory_api/
├── models/mods.py           # Add ModLookupResponse, CompatibilityInfo
├── services/mods.py         # Add lookup_mod method
├── routers/mods.py          # Add GET /mods/lookup/{slug} endpoint
```

**Files to extend (tests):**
```
api/tests/
├── test_models.py           # Add ModLookupResponse serialization tests
├── test_mod_service.py      # Add lookup_mod tests in new test class
└── test_mods_router.py      # Add lookup endpoint tests
```

### Previous Story Intelligence (5.2)

**Key patterns established in 5.2:**
- ModApiClient with httpx.AsyncClient in `services/mod_api.py`
- `check_compatibility()` function already validates releases against game version
- `extract_slug()` and `validate_slug()` for input handling
- Exception classes: `ModNotFoundError`, `ExternalApiError`, `DownloadError`
- Router patterns in `routers/mods.py` with Admin-only POST endpoint
- respx for mocking HTTP calls in tests

**Code review findings from 5.2 (applied):**
- HTTP client resource management via `close_mod_service()` in lifespan
- Atomic file operations with temp + rename
- Defensive `check_compatibility()` for non-standard version formats
- Slug validation with Windows reserved name rejection

**Key integration point:**
The `lookup_mod()` method in ModService should:
1. Call `ModApiClient.get_mod(slug)` - already handles URL extraction and validation
2. Get server version from `ServerService.get_status()`
3. Use `check_compatibility()` from `mod_api.py` with the latest release
4. Build and return `ModLookupResponse`

### Git Intelligence

**Recent commits establishing patterns:**
- `c3acc15` - fix(story-5.2): address code review findings and mark complete
- `c79522d` - feat(story-5.2): implement mod installation API endpoint

**Commit message format:** `type(scope): description`
- `feat(mods)`: for new functionality
- `fix(mods)`: for bug fixes
- `test(mods)`: for test-only changes

### Error Handling

**Use error codes from models/errors.py:**
```python
# Existing codes used
from vintagestory_api.models.errors import ErrorCode

ErrorCode.MOD_NOT_FOUND        # Mod doesn't exist
ErrorCode.EXTERNAL_API_ERROR   # VintageStory API unavailable

# May need to add (if not exists)
ErrorCode.INVALID_SLUG = "INVALID_SLUG"  # Invalid slug format
```

**HTTP exception pattern:**
```python
from fastapi import HTTPException

# 404 Not Found
raise HTTPException(
    status_code=404,
    detail={
        "code": ErrorCode.MOD_NOT_FOUND,
        "message": f"Mod '{slug}' not found",
    }
)

# 502 Bad Gateway
raise HTTPException(
    status_code=502,
    detail={
        "code": ErrorCode.EXTERNAL_API_ERROR,
        "message": "VintageStory mod API is unavailable",
    }
)

# 400 Bad Request
raise HTTPException(
    status_code=400,
    detail={
        "code": ErrorCode.INVALID_SLUG,
        "message": "Invalid mod slug format",
    }
)
```

### References

- `project-context.md` - Critical implementation rules and patterns
- `_bmad-output/planning-artifacts/architecture.md` - Full architecture (Epic 5 section)
- `agentdocs/vintagestory-modapi.md` - Complete mod API documentation
- `_bmad-output/implementation-artifacts/5-2-mod-installation-api.md` - Previous story patterns
- `api/src/vintagestory_api/services/mod_api.py` - ModApiClient implementation
- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.3: Mod Compatibility Validation]

---

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

---

## Change Log
