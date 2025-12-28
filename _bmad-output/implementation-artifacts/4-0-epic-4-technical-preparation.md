# Story 4.0: Epic 4 Technical Preparation

Status: ready-for-dev

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

- [ ] Task 1: Scaffold Playwright test framework + basic test (AC: 1)
  - [ ] 1.1: Add `pytest-playwright` to API dev dependencies via `uv add --dev pytest-playwright`
  - [ ] 1.2: Install Playwright browsers via `playwright install chromium`
  - [ ] 1.3: Create `api/tests/e2e/conftest.py` with base fixtures for browser automation
  - [ ] 1.4: Create `api/tests/e2e/test_health.py` - basic test that verifies `/healthz` endpoint via browser
  - [ ] 1.5: Add `just test-e2e` recipe to Justfile for running E2E tests
  - [ ] 1.6: Document E2E test setup in README or developer docs

- [ ] Task 2: Research FastAPI WebSocket patterns (AC: 2)
  - [ ] 2.1: Research FastAPI WebSocket endpoint patterns (authentication via query params, connection lifecycle)
  - [ ] 2.2: Research broadcasting patterns (multiple connected clients)
  - [ ] 2.3: Research integration with async ring buffer / queue patterns
  - [ ] 2.4: Create `agentdocs/fastapi-websocket-patterns.md` documenting findings with code examples
  - [ ] 2.5: Include error handling and graceful disconnection patterns

- [ ] Task 3: Research xterm.js + React integration (AC: 3)
  - [ ] 3.1: Research xterm.js npm packages (`@xterm/xterm`, `@xterm/addon-fit`, `@xterm/addon-attach`)
  - [ ] 3.2: Research React wrapper patterns (functional component with refs)
  - [ ] 3.3: Research WebSocket attachment for bidirectional communication
  - [ ] 3.4: Research theming with CSS variables (Catppuccin Mocha/Latte integration)
  - [ ] 3.5: Create `agentdocs/xterm-react-patterns.md` documenting findings with code examples
  - [ ] 3.6: Include resize handling and accessibility considerations

- [ ] Task 4: Audit and standardize logging (AC: 4)
  - [ ] 4.1: Review current structlog configuration in `api/src/vintagestory_api/main.py`
  - [ ] 4.2: Ensure consistent timestamp format (ISO 8601) across all log entries
  - [ ] 4.3: Verify dev mode uses colorful ConsoleRenderer, prod mode uses JSONRenderer
  - [ ] 4.4: Review frontend console output for unnecessary noise or missing context
  - [ ] 4.5: Add log level configuration via environment variable if not present
  - [ ] 4.6: Document logging conventions in `project-context.md`

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

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

