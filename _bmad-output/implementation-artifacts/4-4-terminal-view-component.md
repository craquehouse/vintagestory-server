# Story 4.4: Terminal View Component

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **administrator**,
I want **a terminal component in the web UI that displays real-time console output**,
so that **I can monitor server activity and send commands through the browser**.

---

## Background

This story implements the frontend terminal view component that connects to the WebSocket console endpoint implemented in Story 4.2-4.3. The backend is complete:
- WebSocket endpoint at `/api/v1alpha1/console/ws` with Admin authentication (Story 4.2)
- Real-time console output streaming with history on connect (Story 4.2)
- Command input via WebSocket and REST fallback (Story 4.3)

This story builds the React component that:
1. Connects to the WebSocket endpoint with proper authentication
2. Renders console output using xterm.js with Catppuccin theming
3. Handles reconnection with exponential backoff
4. Provides command input capability

**FRs Covered:** FR6, FR7, FR8
**NFRs Covered:** NFR1 (<1s latency), NFR10 (reconnection fills gap)

---

## Acceptance Criteria

1. **Given** I navigate to the Terminal page as Admin, **When** the page loads, **Then** the terminal component initializes and connects to the WebSocket endpoint **And** I see recent console history (default 100 lines) *(FR7)*

2. **Given** I am viewing the terminal, **When** the game server produces output, **Then** I see the output appear in the terminal within 1 second *(NFR1, FR6)*

3. **Given** I am viewing the terminal, **When** I type a command and press Enter, **Then** the command is sent to the server **And** I see my command echoed with [CMD] prefix *(FR8)*

4. **Given** the WebSocket connection is lost, **When** reconnection succeeds, **Then** I receive recent history to fill the gap **And** I see a "Connected" status indicator *(NFR10)*

5. **Given** the theme is toggled between light and dark mode, **When** the terminal is visible, **Then** the terminal theme updates to match (Catppuccin Mocha for dark, Latte for light)

6. **Given** the terminal container is resized, **When** the resize completes, **Then** the terminal dimensions adjust to fit the container

---

## Tasks / Subtasks

<!--
CRITICAL TASK STRUCTURE RULES:
1. Each functional task MUST include "+ tests" in its name
2. Do NOT create separate "Write tests" tasks at the end
3. A task is NOT complete until its tests pass
4. Tests verify the specific AC listed for that task
-->

- [x] Task 1: Install xterm.js dependencies and create terminal themes + tests (AC: 5)
  - [x] 1.1: Add npm packages: `@xterm/xterm@^5`, `@xterm/addon-fit@^0.10`, `@xterm/addon-attach@^0.11`
  - [x] 1.2: Create `web/src/lib/terminal-themes.ts` with Catppuccin Mocha and Latte ITheme definitions
  - [x] 1.3: Import xterm.css in the component or globally
  - [x] 1.4: Write unit tests for theme object structure and values

- [x] Task 2: Create TerminalView component with xterm.js initialization + tests (AC: 1, 6)
  - [x] 2.1: Create `web/src/components/terminal/TerminalView.tsx` functional component
  - [x] 2.2: Use useRef for terminal instance, container element, and FitAddon
  - [x] 2.3: Initialize Terminal with proper options (cursorBlink, fontSize, fontFamily, convertEol)
  - [x] 2.4: Load FitAddon and call fit() on mount
  - [x] 2.5: Add ResizeObserver with requestAnimationFrame debouncing for resize handling
  - [x] 2.6: Implement cleanup on unmount (terminal.dispose(), observer.disconnect())
  - [x] 2.7: Write tests for component rendering, initialization, cleanup

- [x] Task 3: Implement WebSocket connection with authentication + tests (AC: 1, 4)
  - [x] 3.1: Create `web/src/hooks/use-console-websocket.ts` custom hook
  - [x] 3.2: Build WebSocket URL with API key from localStorage: `${protocol}//${host}/api/v1alpha1/console/ws?api_key=${key}`
  - [x] 3.3: Implement connection state tracking: 'connecting' | 'connected' | 'disconnected' | 'forbidden'
  - [x] 3.4: Handle close codes: 4001 (Unauthorized), 4003 (Forbidden), 1000 (Normal)
  - [x] 3.5: Implement exponential backoff reconnection: base 1s, max 30s, jitter, max 10 retries
  - [x] 3.6: Load AttachAddon on successful connection for bidirectional I/O
  - [x] 3.7: Write tests for connection states, close code handling, reconnection logic

- [x] Task 4: Add connection status indicator + tests (AC: 4)
  - [x] 4.1: Create `web/src/components/terminal/ConnectionStatus.tsx` component
  - [x] 4.2: Display status with colored indicator: green (connected), yellow (connecting), gray (disconnected), red (forbidden)
  - [x] 4.3: Add ARIA live region for screen reader announcements
  - [x] 4.4: Write tests for status display states

- [x] Task 5: Integrate theme switching + tests (AC: 5)
  - [x] 5.1: Use ThemeContext to get current theme (light/dark)
  - [x] 5.2: Initialize terminal with correct theme based on context
  - [x] 5.3: Update terminal.options.theme when theme context changes
  - [x] 5.4: Write tests for theme initialization and dynamic switching

- [x] Task 6: Update Terminal page with TerminalView + tests (AC: 1, 2, 3)
  - [x] 6.1: Replace placeholder in `web/src/features/terminal/Terminal.tsx`
  - [x] 6.2: Add proper layout with header (showing connection status) and terminal container
  - [x] 6.3: Ensure terminal fills available space with proper flex layout
  - [x] 6.4: Add ARIA labels for accessibility
  - [x] 6.5: Write integration tests for full terminal page

### Review Follow-ups (AI)

**From code review on 2025-12-28 - 6 issues found (1 CRITICAL, 2 MEDIUM, 3 LOW)**

#### 🔴 CRITICAL (1 issue)
- [x] [AI-Review][CRITICAL] Fill in Dev Agent Record - Complete empty File List, Completion Notes, and Agent Model Used sections [4-4-terminal-view-component.md:362-364]

#### 🟡 MEDIUM (2 issues)
- [x] [AI-Review][MEDIUM] Verify WebSocket message format - Confirmed: Backend sends plain text console output, expects JSON commands. AttachAddon must use `bidirectional: false` and terminal.onData() must format commands as JSON. Fixed in Terminal.tsx.
- [x] [AI-Review][MEDIUM] Add test for runtime theme switching - Added tests for light theme initialization and runtime theme switching in TerminalView.test.tsx

#### 🟢 LOW (3 issues)
- [x] [AI-Review][LOW] Consider naming consistency - Evaluated: TerminalView name is appropriate, "View" suffix is a common React pattern and consistent with component's purpose
- [x] [AI-Review][LOW] Add optional debug logging for connection lifecycle - Added debugLog helper with DEV mode gating for connect, connected, close, error, and reconnection events
- [x] [AI-Review][LOW] Add E2E test for terminal - Created Playwright E2E test suite with 8 tests covering UI rendering, terminal initialization, connection status, and WebSocket connection attempts. Docker orchestration via `just test-e2e-web`.

---

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Do not batch tests into a separate "Write tests" task at the end
- Run `just test-web` to verify all tests pass before marking task complete

### Security Requirements

**Follow patterns in `project-context.md` -> Security Patterns section:**

- API key is stored in localStorage and passed via WebSocket query parameter
- Never log API key values (only key_prefix if needed)
- Use existing authentication pattern from other features

### Development Commands

Use `just` for all development tasks:
- `just test` - Run all tests
- `just test-web` - Run web tests
- `just check` - Full validation (lint + typecheck + test)
- `just lint` - Run all linters

### Architecture & Patterns

**xterm.js Integration Pattern (from `agentdocs/xterm-react-patterns.md`):**

```tsx
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { AttachAddon } from '@xterm/addon-attach';
import '@xterm/xterm/css/xterm.css';

// Initialize in useEffect with proper refs
const terminal = new Terminal({
  cursorBlink: true,
  fontSize: 14,
  fontFamily: 'JetBrains Mono, Menlo, Monaco, Consolas, monospace',
  convertEol: true,  // Convert \n to \r\n
  theme: currentTheme,
});
```

**WebSocket Message Protocol (from Story 4.3):**

Incoming messages (from server):
- Plain text lines of console output (streamed via AttachAddon)

Outgoing messages (to server via AttachAddon):
```json
{"type": "command", "content": "/help"}
```

Response messages (from server):
```json
{"type": "error", "content": "Server is not running"}
```

**Catppuccin Theme Definitions (from `agentdocs/xterm-react-patterns.md`):**

```typescript
import type { ITheme } from '@xterm/xterm';

export const catppuccinMocha: ITheme = {
  background: '#1e1e2e',
  foreground: '#cdd6f4',
  cursor: '#f5e0dc',
  cursorAccent: '#1e1e2e',
  selectionBackground: '#585b70',
  selectionForeground: '#cdd6f4',
  black: '#45475a',
  red: '#f38ba8',
  green: '#a6e3a1',
  yellow: '#f9e2af',
  blue: '#89b4fa',
  magenta: '#f5c2e7',
  cyan: '#94e2d5',
  white: '#bac2de',
  brightBlack: '#585b70',
  brightRed: '#f38ba8',
  brightGreen: '#a6e3a1',
  brightYellow: '#f9e2af',
  brightBlue: '#89b4fa',
  brightMagenta: '#f5c2e7',
  brightCyan: '#94e2d5',
  brightWhite: '#a6adc8',
};

export const catppuccinLatte: ITheme = {
  background: '#eff1f5',
  foreground: '#4c4f69',
  cursor: '#dc8a78',
  // ... (see agentdocs/xterm-react-patterns.md for full definition)
};
```

**Exponential Backoff Pattern:**

```typescript
const reconnect = (attempt: number) => {
  const base = Math.min(1000 * Math.pow(2, attempt), 30000); // max 30s
  const jitter = Math.random() * 1000;
  setTimeout(connect, base + jitter);
};
// Max 10 retries, then show "connection lost" UI state
```

### Project Structure Notes

**Files to create:**
```
web/src/
├── components/
│   └── terminal/
│       ├── TerminalView.tsx           # NEW - Main xterm.js wrapper
│       ├── TerminalView.test.tsx      # NEW - Component tests
│       └── ConnectionStatus.tsx       # NEW - Status indicator
├── hooks/
│   └── use-console-websocket.ts       # NEW - WebSocket connection hook
│   └── use-console-websocket.test.ts  # NEW - Hook tests
├── lib/
│   └── terminal-themes.ts             # NEW - Catppuccin theme definitions
```

**Files to modify:**
```
web/src/features/terminal/Terminal.tsx  # MODIFY - Replace placeholder
web/package.json                         # MODIFY - Add xterm.js dependencies
```

### Previous Story Intelligence (4.3)

**Key patterns established:**

1. **WebSocket endpoint:** `/api/v1alpha1/console/ws` with `?api_key=` query param
2. **Authentication:** Admin role required, close code 4003 for forbidden
3. **History on connect:** Configurable via `?history_lines=N` param (default 100)
4. **Command format:** `{"type": "command", "content": "/help"}`
5. **Error format:** `{"type": "error", "content": "..."}`
6. **Command echo:** Commands appear in stream with `[CMD] ` prefix

**Code review findings from previous stories to apply:**
- Test with mock WebSocket for unit tests
- Use Vitest for web tests (matches existing pattern)
- Follow existing component patterns in `web/src/components/`

### Git Intelligence

**Recent commits:**
- `88c3e16` - feat(story-4.3): implement console command input
- `39c8157` - feat(story-4.2): implement WebSocket console streaming

**Established patterns:**
- React components use functional components with hooks
- Tests use Vitest with React Testing Library
- shadcn/ui components are in `web/src/components/ui/`
- Feature-specific components in `web/src/features/<feature>/`
- Shared hooks in `web/src/hooks/`
- Use structlog pattern for any logging

### UX Design Requirements (from `ux-design-specification.md`)

**Terminal Component Strategy:**
- Component: xterm.js - industry standard terminal emulator (used by VS Code, Hyper)
- Dual-mode terminal view: Console (stdout/stdin) + Shell (future PTY) tabs
- For MVP: Console mode only (Shell deferred to Phase 2)

**Catppuccin Theming:**
- Dark mode: Mocha palette (base #1e1e2e, text #cdd6f4)
- Light mode: Latte palette (complementary values)
- Theme toggle reads from ThemeContext

**Layout Requirements:**
- Terminal fills available space
- Connection status indicator in terminal header
- Responsive resize handling

**Accessibility:**
- ARIA label on terminal container: `aria-label="Server console terminal"`
- ARIA live region for connection status announcements
- Focus management for keyboard users

### Configuration

No new configuration needed. Uses existing:
- `VS_API_KEY_ADMIN` - Stored in localStorage as `apiKey` by auth flow
- WebSocket URL derived from current location host

### Testing Patterns

**Component Testing with Vitest:**

```typescript
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { TerminalView } from './TerminalView';

// Mock xterm.js
vi.mock('@xterm/xterm', () => ({
  Terminal: vi.fn().mockImplementation(() => ({
    loadAddon: vi.fn(),
    open: vi.fn(),
    dispose: vi.fn(),
    options: {},
    writeln: vi.fn(),
  })),
}));

describe('TerminalView', () => {
  it('renders terminal container', () => {
    render(<TerminalView />);
    expect(screen.getByRole('application')).toBeInTheDocument();
  });
});
```

**WebSocket Hook Testing:**

```typescript
import { renderHook, waitFor } from '@testing-library/react';
import { useConsoleWebSocket } from './use-console-websocket';

// Mock WebSocket
global.WebSocket = vi.fn().mockImplementation(() => ({
  onopen: null,
  onclose: null,
  onerror: null,
  close: vi.fn(),
  send: vi.fn(),
}));
```

### References

- `project-context.md` - Critical implementation rules and patterns
- `agentdocs/xterm-react-patterns.md` - Complete xterm.js React integration patterns
- `agentdocs/fastapi-websocket-patterns.md` - WebSocket protocol details
- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.4: Terminal View Component]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Terminal Component Strategy]
- [Source: 4-2-websocket-console-streaming.md] - WebSocket endpoint patterns
- [Source: 4-3-console-command-input.md] - Command input protocol

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

None - implementation proceeded without significant blockers.

### Completion Notes List

- Implemented xterm.js terminal component with Catppuccin theming (Mocha dark, Latte light)
- Created WebSocket connection hook with exponential backoff reconnection (base 1s, max 30s, 10 retries max)
- Used AttachAddon for bidirectional WebSocket I/O instead of manual message handling
- Connection status indicator with ARIA live region for accessibility
- ResizeObserver with requestAnimationFrame debouncing for responsive terminal sizing
- All 75 new tests pass across 7 test files

### File List

**Created:**
- `web/src/lib/terminal-themes.ts` - Catppuccin theme definitions
- `web/src/lib/terminal-themes.test.ts` - Theme tests
- `web/src/components/terminal/TerminalView.tsx` - Main xterm.js wrapper component
- `web/src/components/terminal/TerminalView.test.tsx` - Component tests
- `web/src/components/terminal/ConnectionStatus.tsx` - Connection status indicator
- `web/src/components/terminal/ConnectionStatus.test.tsx` - Status indicator tests
- `web/src/hooks/use-console-websocket.ts` - WebSocket connection hook
- `web/src/hooks/use-console-websocket.test.ts` - Hook tests

**Modified:**
- `web/src/features/terminal/Terminal.tsx` - Replaced placeholder with full implementation
- `web/src/features/terminal/Terminal.test.tsx` - Updated tests for new implementation
- `web/package.json` - Added xterm.js dependencies

