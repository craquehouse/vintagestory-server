# Story 3.5: Fix Server Installation in Dev Environment

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **administrator**,
I want **the server installation to work correctly in the real dev environment**,
so that **I can actually install and run VintageStory server using the web UI**.

---

## Background

This story was created during the Epic 3 retrospective after discovering that server installation fails in the real development environment despite all 239 synthetic tests passing. This validates the concern about needing manual end-to-end verification and highlights the gap between mocked tests and real-world behavior.

**Discovery Context:**
- All unit tests pass (239 backend, 176 frontend)
- CORS issues were fixed (commit `5eb47a5`)
- Server installation still fails when attempted through the Dashboard UI
- Error symptoms and root cause need investigation

---

## Acceptance Criteria

1. **Given** the API and web servers are running in dev mode, **When** I attempt to install server version "1.21.3" via the Dashboard UI, **Then** the installation completes successfully **And** server files exist in `/data/server/`

2. **Given** the server is installed, **When** I check the installation status, **Then** state is "installed" **And** version file contains "1.21.3"

3. **Given** the server is installed, **When** I start the server via the Dashboard, **Then** the server process starts **And** status shows "running"

4. **Given** an installation failure occurs, **When** the root cause is identified, **Then** the fix is implemented **And** the root cause is documented in completion notes

---

## Tasks / Subtasks

<!--
CRITICAL TASK STRUCTURE RULES:
1. Each functional task MUST include "+ tests" in its name
2. Do NOT create separate "Write tests" tasks at the end
3. A task is NOT complete until its tests pass
4. Tests verify the specific AC listed for that task
-->

- [ ] Task 1: Investigate installation failure (AC: 4)
  - [ ] 1.1: Start API and web dev servers using `just dev-api` and `just dev-web`
  - [ ] 1.2: Attempt server installation via Dashboard UI (version 1.21.3)
  - [ ] 1.3: Capture error logs from browser console, API server logs, and network requests
  - [ ] 1.4: Identify root cause of failure (document findings in completion notes)

- [ ] Task 2: Fix identified issues + tests (AC: 1, 2, 4)
  - [ ] 2.1: Implement fix based on root cause analysis
  - [ ] 2.2: Add test(s) to prevent regression if applicable
  - [ ] 2.3: Run `just test` to verify fix doesn't break existing tests

- [ ] Task 3: Manual verification in dev environment (AC: 1, 2, 3)
  - [ ] 3.1: Start fresh dev environment (delete any existing `/data` content)
  - [ ] 3.2: Install server via Dashboard UI - verify success
  - [ ] 3.3: Check server files exist in expected location
  - [ ] 3.4: Start server via Dashboard - verify status changes to "running"
  - [ ] 3.5: Stop server - verify status returns to "installed"

- [ ] Task 4: Document root cause and solution (AC: 4)
  - [ ] 4.1: Document root cause in Dev Agent Record > Completion Notes
  - [ ] 4.2: Update project-context.md if new patterns discovered
  - [ ] 4.3: Run `just check` for final validation

---

## Dev Notes

### Testing Requirements

**CRITICAL:** This story focuses on fixing a real-world integration issue that synthetic tests did not catch.

- Manual end-to-end verification is the PRIMARY validation for this story
- New automated tests should be added ONLY if they can actually catch the issue
- Don't write tests that would pass even with the bug present
- Run `just test` to ensure fix doesn't introduce regressions

### Security Requirements

**Follow patterns in `project-context.md` -> Security Patterns section:**

- DEBUG mode gating for test/dev endpoints
- Never log sensitive data in plaintext
- Proxy-aware client IP logging

### Development Commands

Use `just` for all development tasks:
- `just dev-api` - Start API dev server (default port 8000)
- `just dev-web` - Start web dev server (default port 5173)
- `just test` - Run all tests
- `just check` - Full validation (lint + typecheck + test)

### Architecture & Patterns

**Server Installation Flow:**
```
Dashboard (web) -> POST /api/v1alpha1/server/install -> ServerService.install_server()
                                                              |
                                                              v
                                                      1. Validate version
                                                      2. Check availability
                                                      3. Download tarball (CDN)
                                                      4. Verify checksum (MD5)
                                                      5. Extract to /data/server/
                                                      6. Setup symlinks
                                                      7. Save version file
```

**Key Files:**
- [server.py](api/src/vintagestory_api/services/server.py) - ServerService with install_server() method
- [server.py](api/src/vintagestory_api/routers/server.py) - API endpoints
- [Dashboard.tsx](web/src/features/dashboard/Dashboard.tsx) - UI triggering install
- [use-server-status.ts](web/src/hooks/use-server-status.ts) - useInstallServer mutation

**API Endpoints:**
```
POST /api/v1alpha1/server/install         -> Start installation
GET  /api/v1alpha1/server/install/status  -> Poll installation progress
GET  /api/v1alpha1/server/status          -> Get server status
```

**Installation States:**
- `not_installed` - No server files present
- `installing` - Installation in progress (with stage/percentage)
- `installed` - Server ready but stopped
- `running` - Server process active
- `error` - Installation failed (with error_code)

**Data Directories (from Settings):**
```python
data_dir:    /data               # Root data directory
server_dir:  /data/server        # Server binary location
mods_dir:    /data/mods          # Mod files
config_dir:  /data/config        # Game configuration
```

### Previous Story Intelligence (3.4)

**Patterns established:**
- Dashboard conditionally renders ServerInstallCard or ServerStatusBadge based on state
- Installation initiated via useInstallServer mutation
- Progress tracked via useInstallStatus query (refetch every second during install)
- Toast notifications on success/failure using sonner

**Known working components:**
- ServerStatusBadge (all states render correctly in tests)
- ServerInstallCard (version input, progress indicator work in tests)
- API client with X-API-Key header and snake_case/camelCase transforms
- TanStack Query polling (5 second interval for status)

### Git Intelligence

**Recent relevant commits:**
- `5eb47a5` - fix(api): add CORS middleware for cross-origin requests (fixed one issue)
- `c706618` - chore: Add mise env file support and dev-api documentation
- `3f59d32` - feat(web): Add Dashboard with server controls UI (Story 3.4)

**CORS was already fixed** - so the remaining issue is likely:
1. Environment configuration (VS_DATA_DIR, paths)
2. Network/download issues from the API server
3. File permissions in dev environment
4. Process execution (dotnet runtime availability)
5. Frontend-to-API communication issues not related to CORS

### Likely Root Causes to Investigate

Based on code analysis, potential failure points:

1. **VS_DATA_DIR not set in dev environment**
   - Settings.data_dir defaults to `/data` which may not exist outside Docker
   - Check `api/src/vintagestory_api/config.py` for default values

2. **Missing data directories**
   - `server_dir`, `mods_dir`, `config_dir` may not be created
   - Check if `mkdir -p` equivalent happens before installation

3. **HTTP client timeout/network issues**
   - ServerService uses 300s timeout for downloads
   - Check if VintageStory CDN is accessible from dev machine

4. **Async/background task issues**
   - install_server() runs async but UI may not be polling correctly
   - Check useInstallStatus query behavior

5. **Frontend API base URL**
   - API client may not be configured for dev environment
   - Check `web/src/api/client.ts` for baseURL handling

### Investigation Checklist

When investigating, capture:
- [ ] Browser Network tab (all requests to /api/v1alpha1/server/*)
- [ ] Browser Console (any JavaScript errors)
- [ ] API server logs (structlog output)
- [ ] What state the installation gets stuck in
- [ ] What error message appears (if any)
- [ ] What files exist in data directory after failure

### Project Structure Notes

**Files likely to need changes:**
| File | Potential Issue |
|------|----------------|
| `api/src/vintagestory_api/config.py` | Default data_dir path |
| `api/src/vintagestory_api/services/server.py` | Directory creation |
| `web/src/api/client.ts` | API base URL for dev |
| `.env.example` | Missing env var documentation |

**Dev environment setup:**
```bash
# Terminal 1: API server
cd api && just dev-api

# Terminal 2: Web server
cd web && just dev-web
```

### References

- `project-context.md` - Critical implementation rules and patterns
- [Source: _bmad-output/planning-artifacts/architecture.md#Container Volume Strategy]
- [Source: agentdocs/server-installation.md] - VintageStory installation API docs
- [Source: epic-3-retro-2025-12-28.md#Challenges] - Discovery context
- `api/src/vintagestory_api/services/server.py` - ServerService implementation

---

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

<!-- Document root cause and fix here -->

### File List

