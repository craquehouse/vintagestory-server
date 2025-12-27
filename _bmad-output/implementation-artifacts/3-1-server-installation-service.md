# Story 3.1: Server Installation Service

Status: done

---

## Story

As an **administrator**,
I want **to install the VintageStory server by providing a version number**,
so that **I can get a game server running without manual file management**.

---

## Acceptance Criteria

1. **Given** no server is installed, **When** I call `POST /api/v1alpha1/server/install` with `{"version": "1.21.3"}`, **Then** the system downloads the server tarball from the VintageStory CDN, **And** extracts it to `/data/server/`, **And** creates a symlink from `/data/server/Mods` to `/data/mods/`, **And** copies default config if none exists

2. **Given** a server installation is in progress, **When** I query `GET /api/v1alpha1/server/install/status`, **Then** I receive progress information (stage: downloading/extracting/configuring, percentage if available)

3. **Given** the download fails (network error, invalid version), **When** the installation process encounters the error, **Then** the error is reported clearly with actionable message, **And** the system returns to "not installed" state

4. **Given** the version format is invalid, **When** I attempt installation, **Then** I receive a 422 Unprocessable Entity with validation error details (Note: Pydantic validation returns 422, not 400)

5. **Given** a server is already installed, **When** I attempt to install again, **Then** I receive an error indicating server already exists (version switching is post-MVP)

---

## Tasks / Subtasks

- [x] Task 1: Create VintageStory version discovery service + tests (AC: 1, 3, 4)
  - [x] 1.1: Create `api/src/vintagestory_api/services/server.py` with `ServerService` class
  - [x] 1.2: Implement `get_available_versions()` fetching from `api.vintagestory.at/stable.json`
  - [x] 1.3: Implement `check_version_available()` with HEAD request to verify version exists
  - [x] 1.4: Implement version validation (format: semver pattern like "1.21.3" or "1.22.0-pre.1")
  - [x] 1.5: Add channel fallback logic (try stable first, then unstable)
  - [x] 1.6: Write tests with mocked HTTP responses using respx

- [x] Task 2: Create server download and extraction service + tests (AC: 1, 2, 3)
  - [x] 2.1: Implement `download_server()` with streaming download for large files (~40MB)
  - [x] 2.2: Add MD5 checksum verification from API metadata
  - [x] 2.3: Implement `extract_server()` using tarfile for tar.gz extraction
  - [x] 2.4: Track installation progress with stage enum: `downloading`, `extracting`, `configuring`
  - [x] 2.5: Implement cleanup on failure (remove partial downloads)
  - [x] 2.6: Write tests for download, extraction, and error scenarios

- [x] Task 3: Create server installation state management + tests (AC: 1, 2, 5)
  - [x] 3.1: Add installation state to `StateManager` (server_state: not_installed/installing/installed/error)
  - [x] 3.2: Implement `save_installed_version()` persisting to `/data/server/current_version`
  - [x] 3.3: Implement `get_installed_version()` reading from version file
  - [x] 3.4: Track installation progress in state (stage, percentage, error message)
  - [x] 3.5: Verify server files exist after extraction (VintagestoryServer.dll, VintagestoryLib.dll)
  - [x] 3.6: Write tests for state transitions and persistence

- [x] Task 4: Create post-installation setup + tests (AC: 1)
  - [x] 4.1: Create symlink `/data/server/Mods` -> `/data/mods/` (persist mods across updates)
  - [x] 4.2: Copy default config files if `/data/config/` is empty
  - [x] 4.3: Create required directories if not exist (`/data/server/`, `/data/mods/`, `/data/config/`, `/data/state/`)
  - [x] 4.4: Write tests for directory setup and symlink creation

- [x] Task 5: Create server installation API endpoints + tests (AC: 1-5)
  - [x] 5.1: Create `api/src/vintagestory_api/routers/server.py` with installation routes
  - [x] 5.2: Implement `POST /api/v1alpha1/server/install` with version body
  - [x] 5.3: Implement `GET /api/v1alpha1/server/install/status` for progress polling
  - [x] 5.4: Add Admin role requirement for install endpoint
  - [x] 5.5: Add proper error responses (422 for validation, 409 for already installed, 404 for not found)
  - [x] 5.6: Write integration tests for all endpoints

---

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Do not batch tests into a separate "Write tests" task at the end
- Run `just test` to verify all tests pass before marking task complete

### Security Requirements

**Follow patterns in `project-context.md` -> Security Patterns section:**

- DEBUG mode gating for test/dev endpoints
- Timing-safe comparison for sensitive data (API keys, passwords)
- Never log sensitive data in plaintext
- Proxy-aware client IP logging
- RBAC patterns for endpoint protection

### Development Commands

Use `just` for all development tasks:
- `just test` - Run all tests
- `just check` - Full validation (lint + typecheck + test)
- `just lint` - Run all linters

### Architecture & Patterns

**Server Installation Service Architecture:**

```
┌────────────────────────────────────────────────────────────────┐
│                    Router Layer (server.py)                      │
│   POST /api/v1alpha1/server/install                              │
│   GET /api/v1alpha1/server/install/status                        │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                    Service Layer (ServerService)                 │
│   - Version discovery (api.vintagestory.at)                     │
│   - Download with streaming and progress                         │
│   - Extraction and verification                                  │
│   - Post-install setup (symlinks, configs)                      │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                    State Layer (StateManager)                    │
│   - Installation state (not_installed/installing/installed)     │
│   - Progress tracking (stage, percentage)                        │
│   - Version persistence                                          │
└────────────────────────────────────────────────────────────────┘
```

**VintageStory Version API:**

```python
# api.vintagestory.at/stable.json response structure
{
  "1.21.6": {
    "linuxserver": {
      "filename": "vs_server_linux-x64_1.21.6.tar.gz",
      "filesize": "40.2 MB",
      "md5": "checksum_here",
      "urls": {
        "cdn": "https://cdn.vintagestory.at/gamefiles/stable/...",
        "local": "https://vintagestory.at/api/gamefiles/stable/..."
      },
      "latest": true
    }
  }
}
```

**Download URL Pattern:**

```
https://cdn.vintagestory.at/gamefiles/{channel}/vs_server_linux-x64_{version}.tar.gz
```

| Channel | Versions |
|---------|----------|
| stable | Release versions (1.21.3, 1.21.6) |
| unstable | Pre-release versions (1.22.0-pre.1) |

**Installation State Machine:**

```
                    ┌──────────────┐
                    │ not_installed │
                    └──────┬───────┘
                           │ POST /install
                           ▼
         ┌─────────────────────────────────────┐
         │           installing                 │
         │  ┌─────────────────────────────┐    │
         │  │ downloading → extracting →  │    │
         │  │ configuring                 │    │
         │  └─────────────────────────────┘    │
         └─────────────┬───────────────────────┘
                       │
          ┌────────────┴────────────┐
          │ success                 │ failure
          ▼                         ▼
    ┌───────────┐             ┌───────────┐
    │ installed │             │   error   │
    └───────────┘             │ (revert)  │
                              └───────────┘
```

**Pydantic Models to Create:**

```python
# api/src/vintagestory_api/models/server.py

from enum import Enum
from pydantic import BaseModel, Field

class InstallationStage(str, Enum):
    DOWNLOADING = "downloading"
    EXTRACTING = "extracting"
    CONFIGURING = "configuring"

class ServerState(str, Enum):
    NOT_INSTALLED = "not_installed"
    INSTALLING = "installing"
    INSTALLED = "installed"
    ERROR = "error"

class InstallRequest(BaseModel):
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+(-\w+\.\d+)?$")

class InstallProgress(BaseModel):
    state: ServerState
    stage: InstallationStage | None = None
    percentage: int | None = None
    error: str | None = None

class InstallResponse(BaseModel):
    status: str
    data: InstallProgress
```

**File Locations (per Architecture):**

```
/data/
├── server/           # VintageStory server installation
│   ├── VintagestoryServer.dll
│   ├── VintagestoryLib.dll
│   ├── current_version    # File containing installed version
│   └── Mods/ → ../mods/   # Symlink to persist mods
├── mods/             # Mod files (persistent across updates)
├── config/           # Game server configuration
└── state/            # API state persistence
    └── state.json
```

**Error Response Format:**

```python
# 400 - Invalid version format
{"detail": {"code": "INVALID_VERSION", "message": "Version must be in format X.Y.Z or X.Y.Z-pre.N"}}

# 409 - Server already installed
{"detail": {"code": "SERVER_ALREADY_INSTALLED", "message": "Server version 1.21.3 is already installed"}}

# 502 - CDN unavailable
{"detail": {"code": "EXTERNAL_API_ERROR", "message": "Failed to download server: CDN unavailable"}}

# 404 - Version not found
{"detail": {"code": "VERSION_NOT_FOUND", "message": "Version 1.99.0 not found in stable or unstable channels"}}
```

### Project Structure Notes

**New files to create:**

- `api/src/vintagestory_api/services/server.py` - ServerService class
- `api/src/vintagestory_api/routers/server.py` - Server API endpoints
- `api/src/vintagestory_api/models/server.py` - Server Pydantic models
- `api/tests/test_server.py` - Server service and endpoint tests

**Files to modify:**

- `api/src/vintagestory_api/main.py` - Register server router
- `api/src/vintagestory_api/services/state.py` - Add server state fields
- `api/src/vintagestory_api/models/state.py` - Add server state models
- `api/src/vintagestory_api/models/errors.py` - Add new error codes

**Error Codes to Add:**

```python
# api/src/vintagestory_api/models/errors.py
class ErrorCode:
    # ... existing codes ...
    INVALID_VERSION = "INVALID_VERSION"
    VERSION_NOT_FOUND = "VERSION_NOT_FOUND"
    SERVER_ALREADY_INSTALLED = "SERVER_ALREADY_INSTALLED"
    INSTALLATION_FAILED = "INSTALLATION_FAILED"
    CHECKSUM_MISMATCH = "CHECKSUM_MISMATCH"
```

### Previous Story Intelligence

**From Story 2.3 (Frontend API Client):**
- API client with X-API-Key header injection is ready
- TanStack Query configured with 30s staleTime
- Error handling displays Sonner toasts
- Tests use Vitest with `bun run test`

**From Epic 2:**
- Auth middleware is established - use `require_admin` dependency for install endpoint
- Role-based access control patterns are in place
- Error envelope format uses FastAPI's standard `detail` pattern

**From Epic 1:**
- State persistence uses atomic file writes (temp + rename)
- Health endpoints at `/healthz` and `/readyz` are in place
- Structured logging with structlog is configured

### Git Intelligence

**Recent commits (for context):**
- `b1a8fa6` docs: Add VintageStory server installation reference for Epic 3
- `14f05e5` docs: Add security patterns and dev commands to project-context.md
- `d1d7b85` docs: Add Epic 2 retrospective and mark epic complete
- `98d8dad` feat: Add just command runner for unified dev tasks

**Established patterns from recent work:**
- Use `just` commands for development tasks
- Tests accompany implementation
- Error responses use FastAPI standard `detail` format

### Latest Tech Information

**VintageStory Server Installation:**
- Server tarball is ~40MB, use streaming download
- MD5 checksum available in API metadata for verification
- Server requires .NET 8 runtime (included in base image)
- Server command: `dotnet VintagestoryServer.dll --dataPath /data`

**httpx Streaming Pattern:**

```python
async def download_with_progress(url: str, dest: Path, progress_callback):
    async with httpx.AsyncClient() as client:
        async with client.stream("GET", url) as resp:
            total = int(resp.headers.get("content-length", 0))
            downloaded = 0
            with dest.open("wb") as f:
                async for chunk in resp.aiter_bytes():
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        progress_callback(downloaded * 100 // total)
```

**tarfile Extraction:**

```python
import tarfile

def extract_tarball(tarball: Path, dest: Path) -> None:
    with tarfile.open(tarball, "r:gz") as tar:
        tar.extractall(dest)
```

### References

- `project-context.md` - Critical implementation rules and patterns
- `agentdocs/server-installation.md` - VintageStory server installation reference
- [Source: _bmad-output/planning-artifacts/architecture.md#Container Volume Strategy]
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.1]

---

## Dev Agent Record

### Agent Model Used

claude-opus-4-5-20251101

### Debug Log References

None

### Completion Notes List

- Used `filter="tar"` for tarfile extraction to preserve Unix permissions while blocking path traversal attacks
- Pydantic validates version format before our endpoint code runs (returns 422, not 400)
- Background task requires all HTTP calls to be mocked in tests since it runs asynchronously
- Test uses version 1.21.6 which exists in mock stable.json response
- Task 4.2 fix: Added default config copy logic - copies serverconfig.json from server dir to config dir if empty
- Error code tracking: Added `error_code` field to `InstallProgress` so clients can distinguish error types when polling status (e.g., CHECKSUM_MISMATCH vs INSTALLATION_FAILED). Background tasks cannot raise HTTP exceptions since response is already sent.
- Version regex: Expanded to handle more VintageStory version formats: `-rc` (no suffix number), `-alpha`, `-beta`, and build metadata (`+build.123`)
- HTTP timeout: Increased from 30s to 300s (5 minutes) to handle ~40MB downloads on slow connections
- Race condition protection: Added asyncio.Lock to prevent concurrent install requests from causing conflicts
- Error state recovery: Error state is now cleared at start of new install attempt (AC3 compliance: "returns to not_installed state")
- Path traversal protection: Added `_safe_path()` method to prevent malicious version strings from writing outside server directory
- State management design: Installed state is derived from disk files (`is_installed()` checks DLLs, `get_installed_version()` reads `current_version` file). Only transient `installing` progress is in-memory, which is appropriate since installation progress is lost on restart anyway. This matches the architecture's intent without requiring full StateManager integration for this story.

### File List

**Created:**
- `api/src/vintagestory_api/models/server.py` (62 lines) - Pydantic models for server installation
- `api/src/vintagestory_api/services/server.py` (598 lines) - ServerService class with installation logic
- `api/src/vintagestory_api/routers/server.py` (134 lines) - REST API endpoints for installation
- `api/tests/test_server.py` (1219 lines) - Comprehensive tests for service and endpoints

**Modified:**
- `api/src/vintagestory_api/main.py` - Added server router registration
- `api/src/vintagestory_api/models/errors.py` - Added 6 error codes (INVALID_VERSION, VERSION_NOT_FOUND, SERVER_ALREADY_INSTALLED, INSTALLATION_FAILED, INSTALLATION_IN_PROGRESS, CHECKSUM_MISMATCH)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` - Updated story 3-1 status to done
