# Story 4.0: Epic 4 Technical Preparation

Status: done

## Summary
Technical preparation for Epic 4 (Real-Time Console Access) - research, Playwright setup, logging standardization.

## Deliverables

### 1. Playwright E2E Tests
- Added `pytest-playwright` dev dependency
- Created `api/tests/e2e/` with conftest.py and test_e2e_health.py
- Added `just test-e2e` recipe

### 2. FastAPI WebSocket Research
Created `agentdocs/fastapi-websocket-patterns.md`:
- Query param authentication (`?api_key=`)
- ConnectionManager for broadcasting
- Close codes: 4001 (Unauthorized), 4003 (Forbidden)
- Ring buffer integration for console streaming

### 3. xterm.js React Research
Created `agentdocs/xterm-react-patterns.md`:
- NPM packages: @xterm/xterm, @xterm/addon-fit, @xterm/addon-attach
- React functional component with refs
- Catppuccin theming definitions
- ResizeObserver with debouncing
- Exponential backoff reconnection

### 4. Logging Standardization
- Added ISO 8601 timestamps to dev mode
- Added `VS_LOG_LEVEL` environment variable
- Documented conventions in project-context.md
