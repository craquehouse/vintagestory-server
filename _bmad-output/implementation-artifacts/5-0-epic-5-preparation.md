# Story 5.0: Epic 5 Technical Preparation

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **development team**,
I want **to complete technical preparation for Epic 5 (Mod Management)**,
So that **we have updated architecture docs, caching patterns, and refactored tests before implementing mod features**.

---

## Background

This preparatory story was defined during the Epic 4 retrospective. Epic 5 introduces external API dependencies and new UI patterns that benefit from upfront research and infrastructure improvements.

**Key Learnings from Epic 4 Retrospective:**
- Prep stories (like 4.0) are investments, not overhead - research documents were referenced in every subsequent story
- Manual verification catches integration issues automated tests miss
- Review the manual test list at the end of every task. Ask yourself - Did I implement a change that's testible throug the browser?
- No-silent-failures rule - every failing test should be fixed or tracked
- Clean up at milestones - technical debt should be addressed before the next push

**FRs Covered:** None directly (preparation story)
**NFRs Addressed:**
- NFR11: System gracefully handles VintageStory mod API unavailability (cached data, clear error messages)
- NFR12: Mod installation failures due to network issues are reported clearly to user
- NFR13: System does not require external network access for core functionality

---

## Acceptance Criteria

1. **Given** the architecture documentation is reviewed, **When** I read the architecture.md file, **Then** it reflects current implementation state and any needed updates for Epic 5

2. **Given** a manual test checklist exists, **When** I review `docs/epic-5-manual-test-checklist.md`, **Then** it contains smoke tests for Epics 1-4 functionality and placeholders for Epic 5

3. **Given** the mod API patterns are verified, **When** I review `agentdocs/vintagestory-modapi.md`, **Then** it contains current API patterns with working examples verified against the live API

4. **Given** pending restart pattern research is complete, **When** I review the research findings, **Then** it documents the UI pattern for tracking changes requiring server restart

5. **Given** caching strategy research is complete, **When** I review the caching documentation, **Then** it covers artifact caching (server tarballs) and API response caching (mod data, TTL-based)

6. **Given** large test files are refactored, **When** I examine `api/tests/`, **Then** `test_console.py` and `test_server.py` are split into focused modules

---

## Tasks / Subtasks

<!--
CRITICAL TASK STRUCTURE RULES:
1. Each functional task MUST include "+ tests" in its name
2. Do NOT create separate "Write tests" tasks at the end
3. A task is NOT complete until its tests pass
4. Tests verify the specific AC listed for that task

NOTE: This is a research/documentation story - most tasks produce documentation, not code with tests.
-->

- [x] Task 1: Architecture document review and update (AC: 1)
  - [x] 1.1: Review current `_bmad-output/planning-artifacts/architecture.md` against actual implementation
  - [x] 1.2: Document any deviations between architecture and current codebase
  - [x] 1.3: Add Epic 5 specific patterns (mod service, external API integration, caching layer)
  - [x] 1.4: Update if needed: API patterns, service boundaries, error handling for external APIs

- [x] Task 2: Create manual test checklist + verification (AC: 2)
  - [x] 2.1: Create `docs/epic-5-manual-test-checklist.md` with sections for each epic
  - [x] 2.2: Add Epic 1-4 smoke tests (health endpoints, auth, server lifecycle, console)
  - [x] 2.3: Add Epic 5 placeholder section for mod management tests
  - [x] 2.4: Manually execute Epic 1-4 smoke tests to verify current functionality
  - [x] 2.5: Document any issues found during verification (no issues found)

- [x] Task 3: Verify mod API integration patterns (AC: 3)
  - [x] 3.1: Test live API calls to `https://mods.vintagestory.at/api/mod/{slug}` with real slugs
  - [x] 3.2: Verify download URL construction works (`https://mods.vintagestory.at/download?fileid={id}`)
  - [x] 3.3: Test compatibility tag parsing (releases[].tags contains game version strings)
  - [x] 3.4: Update `agentdocs/vintagestory-modapi.md` with any API changes discovered
  - [x] 3.5: Create httpx-based example code snippets for Story 5.2

- [x] Task 4: Research pending restart pattern (AC: 4)
  - [x] 4.1: Document the pending restart state model (what triggers it, how to clear it)
  - [x] 4.2: Design the PendingRestartBanner component behavior
  - [x] 4.3: Define API changes needed (`pending_restart` field in status/responses)
  - [x] 4.4: Create `agentdocs/pending-restart-patterns.md` with implementation guidance

- [x] Task 5: Research caching strategy (AC: 5)
  - [x] 5.1: Design artifact caching (server tarballs in `/data/cache/`)
  - [x] 5.2: Design API response caching (mod data with TTL)
  - [x] 5.3: Document cache invalidation strategies
  - [x] 5.4: Create `agentdocs/caching-patterns.md` with implementation guidance
  - [x] 5.5: Estimate cache storage requirements and cleanup policies

- [x] Task 6: Prepare test refactoring infrastructure (AC: 6 - prep)
  - [x] 6.1: Created `tests/server/` package structure (migration prep)
  - [x] 6.2: Created shared fixtures in `tests/server/conftest.py` for reusable patterns
  - [x] 6.3: Created `agentdocs/test-refactoring-guide.md` with detailed migration plan
  - [x] 6.4: Documented line-by-line extraction plan for all 28 test classes
  - [x] 6.5: Verified full test suite passes (308 tests, no regressions)

- [x] Task 7: Extract server validation tests (AC: 6)
  - [x] 7.1: Create `tests/server/test_validation.py` with TestVersionValidation (lines 122-187)
  - [x] 7.2: Add TestPathTraversalProtection (lines 188-229)
  - [x] 7.3: Run `just test-api tests/server/test_validation.py` - verify all tests pass (16 passed)

- [x] Task 8: Extract server versions tests (AC: 6)
  - [x] 8.1: Create `tests/server/test_versions.py` with TestGetAvailableVersions (lines 230-284)
  - [x] 8.2: Add TestCheckVersionAvailable (lines 285-340)
  - [x] 8.3: Add TestGetVersionInfo (lines 341-387)
  - [x] 8.4: Run `just test-api tests/server/test_versions.py` - verify all tests pass (12 passed)

- [x] Task 9: Extract server install tests (AC: 6)
  - [x] 9.1: Create `tests/server/test_install.py` with TestInstallProgress (lines 388-416)
  - [x] 9.2: Add TestServerInstallation (lines 417-582)
  - [x] 9.3: Add TestDownloadServer (lines 583-662)
  - [x] 9.4: Add TestChecksumVerification (lines 663-692)
  - [x] 9.5: Add TestExtractServer (lines 693-781)
  - [x] 9.6: Add TestInstallProgressTracking (lines 782-843)
  - [x] 9.7: Add TestCleanupOnFailure (lines 844-877)
  - [x] 9.8: Run `just test-api tests/server/test_install.py` - verify all tests pass (23 passed)

- [x] Task 10: Extract server lifecycle tests (AC: 6)
  - [x] 10.1: Create `tests/server/test_lifecycle.py` with TestServerStateManagement (lines 878-948)
  - [x] 10.2: Add TestPostInstallSetup (lines 949-986)
  - [x] 10.3: Add TestServerLifecycleStateEnum (lines 1356-1371)
  - [x] 10.4: Add TestStartServer (lines 1372-1466)
  - [x] 10.5: Add TestStopServer (lines 1467-1610)
  - [x] 10.6: Add TestRestartServer (lines 1611-1652)
  - [x] 10.7: Add TestProcessMonitoring (lines 1653-1692)
  - [x] 10.8: Add TestServerStatus (lines 1693-1774)
  - [x] 10.9: Add TestConcurrentLifecycleOperations (lines 1775-1813)
  - [x] 10.10: Add TestRestartPartialFailures (lines 2237-2437)
  - [x] 10.11: Run `just test-api tests/server/test_lifecycle.py` - verify all tests pass (43 passed)

- [x] Task 11: Extract server REST endpoint tests (AC: 6)
  - [x] 11.1: Create `tests/server/test_endpoints.py` with TestServerStartEndpoint (lines 1814-1939)
  - [x] 11.2: Add TestServerStopEndpoint (lines 1940-2072)
  - [x] 11.3: Add TestServerRestartEndpoint (lines 2073-2236)
  - [x] 11.4: Add TestRestartEndpointErrorHandling (lines 2438-2532)
  - [x] 11.5: Add TestServerStatusEndpoint (lines 2533-2929)
  - [x] 11.6: Run `just test-api tests/server/test_endpoints.py` - verify all tests pass (29 passed)

- [x] Task 12: Extract server install endpoint tests (AC: 6)
  - [x] 12.1: Create `tests/server/test_install_endpoints.py` with TestServerInstallEndpoint (lines 987-1191)
  - [x] 12.2: Add TestServerInstallStatusEndpoint (lines 1192-1355)
  - [x] 12.3: Run `just test-api tests/server/test_install_endpoints.py` - verify all tests pass (13 passed)

- [x] Task 13: Create console test infrastructure (AC: 6)
  - [x] 13.1: Create `tests/console/__init__.py` package
  - [x] 13.2: Create `tests/console/conftest.py` with shared console fixtures

- [x] Task 14: Extract console buffer tests (AC: 6)
  - [x] 14.1: Create `tests/console/test_buffer.py` with TestConsoleBuffer (lines 28-337)
  - [x] 14.2: Run `just test-api tests/console/test_buffer.py` - verify all tests pass (20 passed)

- [x] Task 15: Extract console service integration tests (AC: 6)
  - [x] 15.1: Create `tests/console/test_service_integration.py` with TestServerServiceConsoleIntegration (lines 339-603)
  - [x] 15.2: Run `just test-api tests/console/test_service_integration.py` - verify all tests pass (9 passed)

- [x] Task 16: Extract console history endpoint tests (AC: 6)
  - [x] 16.1: Create `tests/console/test_history_endpoint.py` with TestConsoleHistoryEndpoint (lines 605-835)
  - [x] 16.2: Run `just test-api tests/console/test_history_endpoint.py` - verify all tests pass (12 passed)

- [x] Task 17: Extract console command endpoint tests (AC: 6)
  - [x] 17.1: Create `tests/console/test_command_endpoint.py` with TestServerServiceSendCommand (lines 837-1015)
  - [x] 17.2: Add TestConsoleCommandEndpoint (lines 1209-1397)
  - [x] 17.3: Run `just test-api tests/console/test_command_endpoint.py` - verify all tests pass (16 passed)

- [x] Task 18: Extract console websocket tests (AC: 6)
  - [x] 18.1: Create `tests/console/test_websocket.py` with TestConsoleWebSocket (lines 1018-1207)
  - [x] 18.2: Add TestConsoleWebSocketCommands (lines 1399-1656)
  - [x] 18.3: Run `just test-api tests/console/test_websocket.py` - verify all tests pass (18 passed)

- [x] Task 19: Finalize test refactoring (AC: 6)
  - [x] 19.1: Delete `tests/test_server.py` after verifying all server tests extracted (136 tests)
  - [x] 19.2: Delete `tests/test_console.py` after verifying all console tests extracted (75 tests)
  - [x] 19.3: Run `just test-api` - verify full test suite (308 tests) passes
  - [x] 19.4: Run `just check` - verify lint, typecheck, and tests all pass

---

## Review Follow-ups (AI)

- [x] [AI-Review][HIGH] Fix AC #6 - Tasks 7-19 now explicitly cover splitting test files into focused modules
- [x] [AI-Review][HIGH] Fill in manual test checklist placeholders - Replace {{date}} and {{verifier}} in docs/epic-5-manual-test-checklist.md with actual verification date and verifier name
- [x] [AI-Review][HIGH] Mark actual test completion in checklist - Fill checkboxes [x] for Epic 1-4 smoke tests in docs/epic-5-manual-test-checklist.md to match completion notes claim
- [ ] [AI-Review][MEDIUM] Resolve 27 runtime warnings in test suite - Fix AsyncMockMixin._execute_mock_call warnings at api/src/vintagestory_api/services/server.py:1039 (affects tests/server/test_endpoints.py and tests/server/test_lifecycle.py). Note: These are cosmetic warnings in test output; all 308 tests pass correctly. Deferred to future cleanup.
- [x] [AI-Review][MEDIUM] Update test-refactoring-guide.md timeline - Correct lines 176-184 to reflect that test migration was completed in Story 5.0, not "Post-Epic 5"
- [x] [AI-Review][LOW] Sync sprint status with story completion - Update sprint-status.yaml line 72 from "in-progress" to "done"

---

## Dev Notes

### Testing Requirements

**CRITICAL:** This is primarily a research/documentation story. However:

- Task 6 produces code changes - all tests must pass after refactoring
- Use `just test-api` to verify test refactoring
- Use `just check` for full validation before marking complete

### Security Requirements

No new security concerns for this story. Follow existing patterns in `project-context.md`.

### Development Commands

Use `just` for all development tasks:
- `just test` - Run all tests
- `just test-api` - Run API tests (to verify Task 6)
- `just check` - Full validation (lint + typecheck + test)
- `just lint` - Run all linters

### Architecture & Patterns

**Areas to Review in Architecture Doc:**

1. **External API Integration:**
   - httpx client patterns (async, timeouts, error handling)
   - Response caching with TTL
   - Graceful degradation when API unavailable

2. **State Management for Pending Restart:**
   - Server-side tracking in StateManager
   - API response envelope extension (`pending_restart: boolean`)
   - Frontend banner component behavior

3. **Mod Service Boundaries:**
   ```
   ModService
   ├── lookup(slug) → ModInfo (from API or cache)
   ├── install(slug) → download, extract, persist state
   ├── enable(slug) → set state, set pending_restart
   ├── disable(slug) → set state, set pending_restart
   └── remove(slug) → delete file, update state, set pending_restart
   ```

### Project Structure Notes

**Files to Create:**
```
docs/
└── manual-test-checklist.md      # NEW - Smoke test checklist

agentdocs/
├── pending-restart-patterns.md   # NEW - Pending restart UI pattern
└── caching-patterns.md           # NEW - Caching strategy guide
```

**Files to Modify:**
```
_bmad-output/planning-artifacts/architecture.md  # Review and update
agentdocs/vintagestory-modapi.md                 # Verify and update
api/tests/test_console.py                        # Split into modules
api/tests/test_server.py                         # Split into modules
```

### Previous Story Intelligence (Epic 4)

**Key patterns established:**

1. **Research documents are valuable** - Story 4.0's `fastapi-websocket-patterns.md` and `xterm-react-patterns.md` were referenced in every subsequent story
2. **E2E tests run separately** - `just test-e2e-api` requires Docker, excluded from regular `just test-api`
3. **Logging conventions** - structlog with `VS_DEBUG` gating, ISO timestamps
4. **WebSocket patterns** - Auth via query param, exponential backoff reconnection

**Code review findings to apply:**
- Manual verification catches issues automated tests miss
- No-silent-failures rule - every failing test must be addressed
- Clean up technical debt at milestones

### Git Intelligence

**Recent commits:**
- `8ea1e20` - docs(retro): add Epic 4 retrospective
- `859c3ca` - fix(story-4.4): post-implementation fixes and improvements
- `0fcd173` - feat(install): add version aliases and improve UX

**Established patterns:**
- Commit message format: `type(scope): description`
- Post-implementation fixes are documented in story files
- Retrospectives capture lessons learned and action items

### VintageStory Mod API Reference

**Base URL:** `https://mods.vintagestory.at/api/`

**Key Endpoints:**
```
GET /api/mod/{slug}          # Get mod details with releases
GET /api/mods                # List all mods
GET /api/gameversions        # List game versions for compatibility
GET /download?fileid={id}    # Download mod file
```

**Important Notes:**
- Status codes are strings (`"200"`), not integers
- Releases are ordered newest-first (`releases[0]` is latest)
- Compatibility is determined by `releases[].tags` array containing game version strings
- Download redirects to CDN at `moddbcdn.vintagestory.at`
- No authentication required
- No documented rate limits (but be respectful)

**Compatibility Logic:**
```python
def check_compatibility(mod_releases, game_version):
    for release in mod_releases:
        if game_version in release['tags']:
            return 'compatible', release
    # Check if close version (same major.minor)
    for release in mod_releases:
        if any(tag.startswith(game_version[:4]) for tag in release['tags']):
            return 'not_verified', release
    return 'incompatible', mod_releases[0] if mod_releases else None
```

### Caching Strategy Context

**From Epic 4 Retrospective:**
- Artifact caching: Server tarballs - file-based, persistent in `/data/cache/`
- API response caching: Mod lists, mod details, server versions - TTL-based
- Goal: Respect VintageStory developer resources, improve reliability (NFR11)

**Proposed Cache Structure:**
```
/data/cache/
├── servers/                    # Server tarballs
│   └── vs_server_1.21.6.tar.gz
├── mods/                       # Downloaded mod files (temporary?)
│   └── smithingplus_1.8.3.zip
└── api/                        # Cached API responses
    ├── mod_smithingplus.json   # Individual mod lookup
    ├── modlist.json            # All mods
    └── gameversions.json       # Game versions list
```

**TTL Recommendations:**
| Cache Type | TTL | Rationale |
|------------|-----|-----------|
| Mod details | 1 hour | Balance freshness vs API load |
| Game versions | 24 hours | Rarely changes |
| Server tarballs | Permanent | File is immutable once downloaded |
| Mod files | Permanent | Specific version is immutable |

### Pending Restart Pattern Context

**From UX Design Specification:**
- Changes requiring restart tracked server-side (`pendingRestart` state)
- Persistent header banner: "⟳ Restart required · N pending changes · [Restart Now]"
- Two workflows: immediate restart or batch changes

**Triggering Events:**
- Mod enabled/disabled
- Mod installed/removed
- Config file saved (future)
- Settings changed (future)

**Clear Conditions:**
- Server successfully restarted
- Manual clear (admin acknowledges without restart)

### References

- `project-context.md` - Critical implementation rules and patterns
- `_bmad-output/planning-artifacts/architecture.md` - Full architecture doc
- `_bmad-output/implementation-artifacts/epic-4-retro-2025-12-28.md` - Epic 4 lessons learned
- `agentdocs/vintagestory-modapi.md` - Mod API documentation
- `docs/epic-5-manual-test-checklist.md` - Epic 5 living manual test list
- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.0: Epic 5 Technical Preparation]

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

None - documentation/research story with no implementation bugs

### Completion Notes List

**Task 1 - Architecture Update:**
- Added "Architecture Deviations & Evolutions" section documenting intentional changes from original spec
- Added "Epic 5: Mod Management Architecture" section with detailed patterns for:
  - External API integration (ModApiClient with httpx)
  - Mod service boundaries
  - Mod state model
  - Compatibility check logic
  - Caching architecture
  - Pending restart pattern
  - Error handling for external APIs
  - Testing patterns with respx

**Task 2 - Manual Test Checklist:**
- Created comprehensive `docs/epic-5-manual-test-checklist.md` with 30+ test cases
- Verified Epic 1-4 functionality via curl and Playwright
- All smoke tests pass:
  - Health endpoints: ✅
  - Auth (admin/monitor keys): ✅
  - Server lifecycle controls: ✅
  - Console WebSocket streaming: ✅
  - Terminal UI rendering: ✅

**Task 3 - Mod API Verification:**
- Verified live API calls work correctly
- Confirmed download URL redirects to CDN (302 → moddbcdn.vintagestory.at)
- Added httpx-based examples to `agentdocs/vintagestory-modapi.md`
- API quirks documented (statuscode is string, releases ordered newest-first)

**Task 4 - Pending Restart Pattern:**
- Created `agentdocs/pending-restart-patterns.md` with:
  - State model (PendingRestartState with changes list)
  - Triggering events and clear conditions
  - API response extension
  - Frontend PendingRestartBanner component design
  - Testing considerations

**Task 5 - Caching Strategy:**
- Created `agentdocs/caching-patterns.md` with:
  - Two-tier caching (artifact cache + API response cache)
  - TTL configuration (mod: 1h, modlist: 15m, versions: 24h)
  - Cache invalidation strategies
  - Storage requirements and cleanup policies
  - Full implementation examples

**Task 6 - Test Refactoring:**
- Created `tests/server/` package with shared conftest.py
- Created `agentdocs/test-refactoring-guide.md` with migration plan
- Documented line-by-line extraction for all 28 test classes in test_server.py
- All 308 tests pass

### File List

**Created:**
- `docs/epic-5-manual-test-checklist.md` - Manual test checklist (180 lines)
- `agentdocs/pending-restart-patterns.md` - Pending restart pattern docs (280 lines)
- `agentdocs/caching-patterns.md` - Caching strategy docs (350 lines)
- `agentdocs/test-refactoring-guide.md` - Test migration guide (180 lines)
- `api/tests/server/__init__.py` - Server test package init
- `api/tests/server/conftest.py` - Shared server test fixtures (180 lines)
- `api/tests/server/test_validation.py` - Version validation tests (16 tests)
- `api/tests/server/test_versions.py` - Version fetching tests (12 tests)
- `api/tests/server/test_install.py` - Installation tests (23 tests)
- `api/tests/server/test_lifecycle.py` - Lifecycle management tests (43 tests)
- `api/tests/server/test_endpoints.py` - REST endpoint tests (29 tests)
- `api/tests/server/test_install_endpoints.py` - Install endpoint tests (13 tests)
- `api/tests/console/__init__.py` - Console test package init
- `api/tests/console/conftest.py` - Shared console test fixtures
- `api/tests/console/test_buffer.py` - ConsoleBuffer unit tests (20 tests)
- `api/tests/console/test_service_integration.py` - Service integration tests (9 tests)
- `api/tests/console/test_history_endpoint.py` - History endpoint tests (12 tests)
- `api/tests/console/test_command_endpoint.py` - Command endpoint tests (16 tests)
- `api/tests/console/test_websocket.py` - WebSocket tests (18 tests)

**Modified:**
- `_bmad-output/planning-artifacts/architecture.md` - Added Epic 5 sections (~500 lines added)
- `agentdocs/vintagestory-modapi.md` - Added httpx examples (~200 lines added)

**Deleted:**
- `api/tests/test_server.py` - Replaced by `tests/server/` package (136 tests migrated)
- `api/tests/test_console.py` - Replaced by `tests/console/` package (75 tests migrated)

