# Story 4.0: Epic 4 Technical Preparation

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **development team**,
I want **to complete technical preparation for Epic 4 (Real-Time Console Access)**,
so that **we have the infrastructure, research findings, and patterns in place before implementing console features**.

---

## Background

This preparatory story was created during the Epic 3 retrospective. Epic 4 introduces significant new technical components (WebSockets, xterm.js, ring buffers) that benefit from upfront research and infrastructure setup. Key findings from Epic 3:

- **Lesson 5:** Track prep work as stories - follow the BMAD framework
- **Technical Debt Identified:** Missing Playwright framework, logging inconsistency
- **Epic 4 Dependencies:** All Epic 3 dependencies satisfied (server lifecycle, status API, dashboard)

---

## Acceptance Criteria

1. **Given** the Playwright test framework is set up, **When** I run `just test-e2e`, **Then** a basic end-to-end test executes against the running application in Docker

2. **Given** FastAPI WebSocket research is complete, **When** I review the research document, **Then** it contains patterns for authentication, broadcasting, reconnection, and integration with the console buffer service

3. **Given** xterm.js research is complete, **When** I review the research document, **Then** it contains patterns for React integration, WebSocket attachment, theming with Catppuccin, and resize handling

4. **Given** logging has been audited and standardized, **When** I run the API server, **Then** logs have consistent timestamps and formats **And** frontend console output is clean and actionable

---

## Tasks / Subtasks

<!--
CRITICAL TASK STRUCTURE RULES:
1. Each functional task MUST include "+ tests" in its name where applicable
2. Do NOT create separate "Write tests" tasks at the end
3. A task is NOT complete until its tests pass
4. Tests verify the specific AC listed for that task
-->

- [x] Task 1: Scaffold Playwright test framework + basic test (AC: 1)
  - [x] 1.1: Add `pytest-playwright` to API dev dependencies via `uv add --dev pytest-playwright`
  - [x] 1.2: Install Playwright browsers via `playwright install chromium`
  - [x] 1.3: Create `api/tests/e2e/conftest.py` with base fixtures for browser automation
  - [x] 1.4: Create `api/tests/e2e/test_health.py` - basic test that verifies `/healthz` endpoint via browser
  - [x] 1.5: Add `just test-e2e` recipe to Justfile for running E2E tests
  - [x] 1.6: Document E2E test setup in README or developer docs

- [x] Task 2: Research FastAPI WebSocket patterns (AC: 2)
  - [x] 2.1: Research FastAPI WebSocket endpoint patterns (authentication via query params, connection lifecycle)
  - [x] 2.2: Research broadcasting patterns (multiple connected clients)
  - [x] 2.3: Research integration with async ring buffer / queue patterns
  - [x] 2.4: Create `agentdocs/fastapi-websocket-patterns.md` documenting findings with code examples
  - [x] 2.5: Include error handling and graceful disconnection patterns

- [x] Task 3: Research xterm.js + React integration (AC: 3)
  - [x] 3.1: Research xterm.js npm packages (`@xterm/xterm`, `@xterm/addon-fit`, `@xterm/addon-attach`)
  - [x] 3.2: Research React wrapper patterns (functional component with refs)
  - [x] 3.3: Research WebSocket attachment for bidirectional communication
  - [x] 3.4: Research theming with CSS variables (Catppuccin Mocha/Latte integration)
  - [x] 3.5: Create `agentdocs/xterm-react-patterns.md` documenting findings with code examples
  - [x] 3.6: Include resize handling and accessibility considerations

- [x] Task 4: Audit and standardize logging (AC: 4)
  - [x] 4.1: Review current structlog configuration in `api/src/vintagestory_api/main.py`
  - [x] 4.2: Ensure consistent timestamp format (ISO 8601) across all log entries
  - [x] 4.3: Verify dev mode uses colorful ConsoleRenderer, prod mode uses JSONRenderer
  - [x] 4.4: Review frontend console output for unnecessary noise or missing context
  - [x] 4.5: Add log level configuration via environment variable if not present
  - [x] 4.6: Document logging conventions in `project-context.md`

### Review Follow-ups (AI)

**From code review on 2025-12-28 - 10 issues found (all resolved)**

#### 🔴 CRITICAL (2 issues)
- [x] [AI-Review][CRITICAL] Fix test imports - `expect` from `playwright.sync_api` is NOT deprecated (v0.7.2 uses this pattern correctly)
- [x] [AI-Review][CRITICAL] Add `page` fixture documentation to conftest.py - Added docstring explaining pytest-playwright auto-fixtures

#### 🟡 MEDIUM (5 issues)
- [x] [AI-Review][MEDIUM] Add `.claude/CLAUDE.md` to File List - N/A: No such file exists, only `.claude/settings.json`
- [x] [AI-Review][MEDIUM] Verify `pytest-playwright` is in `api/pyproject.toml` - Confirmed: `pytest-playwright>=0.7.2`
- [x] [AI-Review][MEDIUM] Verify `just test-e2e` recipe exists and works - Confirmed: 4 tests collected
- [x] [AI-Review][MEDIUM] Verify `playwright install chromium` documented in README.md - Added first-time setup section
- [x] [AI-Review][MEDIUM] Fix XSS vulnerability in conftest.py - Fixed: Now uses `page.evaluate()` with args instead of f-string

#### 🟢 LOW (3 issues)
- [x] [AI-Review][LOW] Pin xterm.js version in documentation - Added version constraints (^5.x, ^0.10.x, ^0.11.x)
- [x] [AI-Review][LOW] Update story Date field - Confirmed: 2025-12-28 is correct
- [x] [AI-Review][LOW] Verify pytest-playwright version - Confirmed: 0.7.2 matches

---

## Dev Notes

### Testing Requirements

**CRITICAL:** Each task should be verified as complete before moving on.

- Task 1: Verified by running `just test-e2e` successfully
- Tasks 2-3: Verified by peer review of research documents
- Task 4: Verified by manual inspection of log output in dev and prod modes

### Security Requirements

**Follow patterns in `project-context.md` → Security Patterns section:**

- WebSocket authentication research must cover secure token validation
- Never log sensitive data in plaintext
- Research documents should include security considerations

### Development Commands

Use `just` for all development tasks:
- `just test` - Run all tests
- `just test-api` - Run API tests
- `just test-e2e` - Run E2E tests (to be created)
- `just check` - Full validation (lint + typecheck + test)

### Architecture & Patterns

**Epic 4 Technology Stack (from architecture.md):**

| Component | Technology | Version |
|-----------|------------|---------|
| WebSocket Server | Starlette built-in (FastAPI) | Latest |
| Console Buffer | In-memory ring buffer | Custom implementation |
| Frontend Terminal | xterm.js | @xterm/xterm@5.x |
| React Integration | Functional component with refs | React 19.2 |
| E2E Testing | pytest-playwright | Latest |

**WebSocket Authentication Pattern (from architecture.md):**
```
ws://host/api/v1alpha1/console?api_key=<admin-key>
```
- Query param validated on connection
- Admin role required for console access (FR9)

**WebSocket Reconnection Pattern (from architecture.md):**
```typescript
// Exponential backoff with jitter
const reconnect = (attempt: number) => {
  const base = Math.min(1000 * 2 ** attempt, 30000); // max 30s
  const jitter = Math.random() * 1000;
  setTimeout(connect, base + jitter);
};
// Max 10 retries, then show "connection lost" UI state
```

**xterm.js Addons Required:**
- `@xterm/addon-fit` - Auto-resize terminal to container
- `@xterm/addon-attach` - Connect to WebSocket for bidirectional I/O

**Console Buffer Requirements (from epics.md - Story 4.1):**
- Ring buffer with configurable size (default 10,000 lines)
- Timestamps added to each line
- In-memory only, no disk persistence (NFR6)
- Preserves content on game server crash

### Previous Story Intelligence (3.5)

**Key Learnings from Story 3.5:**

1. **VintageStory tarball quirks:** Custom tarfile filter needed for extraction (documented in completion notes)
2. **Directory structure refactored:** Now uses `--dataPath` for persistent data
   - `/data/server` - Server installation
   - `/data/serverdata` - Persistent game data
   - `/data/vsmanager` - API manager state
3. **Docker E2E verification critical:** Synthetic tests passed but real-world failed - validates need for Playwright

**Patterns Established:**
- `just clean-data` for resetting dev environment
- Docker compose with build args for VS_API_KEY
- `just docker-*` recipes for container operations

### Git Intelligence

**Recent commits relevant to Epic 4 preparation:**
- `f1fd637` - fix(story-3.5): revert Issue #7 - VS_API_KEY is not a duplicate
- `5a7899d` - docs: add MCP tools guidance for agents
- `c39bc88` - docs: add Epic 3 retrospective and update sprint status

**Files likely to be touched:**
- `api/tests/e2e/` - New E2E test directory
- `agentdocs/` - Research documentation
- `Justfile` - New recipes for E2E testing
- `project-context.md` - Logging conventions
- `api/src/vintagestory_api/main.py` - Logging configuration

### Latest Technology Specifics

**Playwright for Python:**
```bash
# Installation
pip install pytest-playwright
playwright install chromium

# Basic test pattern
from playwright.sync_api import Page, expect

def test_has_title(page: Page):
    page.goto("http://localhost:8080/")
    expect(page).to_have_title(re.compile("VintageStory"))
```

**xterm.js with WebSocket Attachment:**
```typescript
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { AttachAddon } from '@xterm/addon-attach';

const terminal = new Terminal({ cursorBlink: true });
const fitAddon = new FitAddon();
terminal.loadAddon(fitAddon);
terminal.open(containerElement);
fitAddon.fit();

// Connect to WebSocket
const socket = new WebSocket('ws://localhost:8080/api/v1alpha1/console?api_key=xxx');
socket.onopen = () => {
  const attachAddon = new AttachAddon(socket);
  terminal.loadAddon(attachAddon);
};
```

**FastAPI WebSocket Pattern:**
```python
from fastapi import WebSocket, WebSocketDisconnect

@app.websocket("/api/v1alpha1/console")
async def console_websocket(websocket: WebSocket, api_key: str = Query(...)):
    # Validate API key
    if not verify_admin_key(api_key):
        await websocket.close(code=4003)  # Custom close code for forbidden
        return

    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            # Process command
    except WebSocketDisconnect:
        # Clean up connection
        pass
```

### Project Structure Notes

**New directories/files to create:**
```
api/tests/e2e/
├── conftest.py          # Playwright fixtures
└── test_health.py       # Basic health check test

agentdocs/
├── fastapi-websocket-patterns.md   # Task 2 output
└── xterm-react-patterns.md         # Task 3 output
```

**Justfile additions:**
```just
# E2E testing with Playwright
test-e2e *ARGS:
    mise exec -- uv run --directory api pytest tests/e2e {{ ARGS }}
```

### References

- `project-context.md` - Critical implementation rules and patterns
- [Source: _bmad-output/planning-artifacts/architecture.md#WebSocket Reconnection Pattern]
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 4: Real-Time Console Access]
- [Source: epic-3-retro-2025-12-28.md#Action Items] - Story 4.0 tasks origin

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A - Research and scaffolding story, no complex debugging required.

### Completion Notes List

**Task 1: Playwright E2E Test Framework**
- Added `pytest-playwright` to dev dependencies
- Installed Chromium browser for headless testing
- Created `api/tests/e2e/conftest.py` with fixtures for `base_url`, `api_base_url`, and `authenticated_page`
- Created `api/tests/e2e/test_e2e_health.py` with 4 tests (health endpoints, web UI, API root)
- Added `just test-e2e` recipe to Justfile
- Documented E2E testing setup in README.md

**Task 2: FastAPI WebSocket Patterns Research**
- Documented authentication via query parameters pattern (WebSocket can't use HTTP headers in browser)
- Documented ConnectionManager pattern for broadcasting to multiple clients
- Documented integration patterns with async ring buffer for console streaming
- Documented error handling, graceful disconnection, and custom close codes (4003 for forbidden)
- Created comprehensive `agentdocs/fastapi-websocket-patterns.md`

**Task 3: xterm.js + React Integration Research**
- Documented npm packages: `@xterm/xterm`, `@xterm/addon-fit`, `@xterm/addon-attach`
- Documented React functional component pattern with refs and useEffect
- Documented WebSocket attachment for bidirectional communication
- Documented Catppuccin Mocha/Latte theme definitions for terminal
- Documented ResizeObserver pattern with requestAnimationFrame debouncing
- Documented reconnection with exponential backoff and jitter
- Documented accessibility considerations (ARIA, screen reader announcements)
- Created comprehensive `agentdocs/xterm-react-patterns.md`

**Task 4: Logging Standardization**
- Fixed: Added ISO 8601 timestamps to dev mode (was only in prod)
- Added: `VS_LOG_LEVEL` environment variable for log level override
- Verified: Dev mode uses colorful ConsoleRenderer, prod mode uses JSONRenderer
- Verified: Frontend console output is clean (no noise)
- Documented: Logging conventions in `project-context.md`

### File List

**New Files:**
- `api/tests/e2e/conftest.py` - Playwright fixtures for E2E testing
- `api/tests/e2e/test_e2e_health.py` - Basic E2E health endpoint tests
- `agentdocs/fastapi-websocket-patterns.md` - WebSocket research documentation
- `agentdocs/xterm-react-patterns.md` - xterm.js React integration documentation

**Modified Files:**
- `api/pyproject.toml` - Added pytest-playwright dev dependency
- `Justfile` - Added test-e2e recipe
- `README.md` - Added development commands and E2E testing documentation
- `api/src/vintagestory_api/config.py` - Added log_level setting and improved configure_logging
- `api/src/vintagestory_api/main.py` - Pass log_level to configure_logging
- `project-context.md` - Added logging conventions section

---

## Change Log

- 2025-12-28: Initial implementation of story 4.0 - Epic 4 technical preparation complete
- 2025-12-28: Code review completed - 10 issues found (2 CRITICAL, 5 MEDIUM, 3 LOW) - Status changed to in-progress for follow-up fixes
- 2025-12-28: All 10 code review issues resolved - XSS fix, documentation updates, version pinning
- 2025-12-28: Story marked **done** - Ready for Epic 4 implementation

---

## Status

Status: done
