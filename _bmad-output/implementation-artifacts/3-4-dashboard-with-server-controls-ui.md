# Story 3.4: Dashboard with Server Controls UI

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **administrator**,
I want **a dashboard showing server status with control buttons**,
so that **I can monitor and control the server from the web interface**.

---

## Acceptance Criteria

1. **Given** no server is installed, **When** I view the Dashboard, **Then** I see the ServerInstallCard with version input and "Install Server" button **And** server control buttons (Start/Stop/Restart) are not visible

2. **Given** a server installation is in progress, **When** I view the Dashboard, **Then** I see a progress indicator with current stage and percentage **And** the install button is disabled

3. **Given** a server is installed and stopped, **When** I view the Dashboard, **Then** I see the ServerStatusBadge showing "Stopped" (red) **And** server version is displayed **And** "Start" button is enabled **And** "Stop" and "Restart" buttons are disabled

4. **Given** a server is running, **When** I view the Dashboard, **Then** I see the ServerStatusBadge showing "Running" (green) **And** server version and uptime are displayed **And** "Stop" and "Restart" buttons are enabled **And** "Start" button is disabled

5. **Given** I click a server control button, **When** the action is in progress, **Then** the button shows a loading state **And** a toast notification appears on success or failure

6. **Given** the server state changes, **When** the Dashboard is open, **Then** the status updates automatically without page refresh (TanStack Query polling or refetch)

---

## Tasks / Subtasks

<!--
CRITICAL TASK STRUCTURE RULES:
1. Each functional task MUST include "+ tests" in its name
2. Do NOT create separate "Write tests" tasks at the end
3. A task is NOT complete until its tests pass
4. Tests verify the specific AC listed for that task
-->

- [x] Task 1: Create ServerStatusBadge component + tests (AC: 3, 4)
  - [x] 1.1: Create `web/src/components/ServerStatusBadge.tsx` displaying server state with appropriate color/icon
  - [x] 1.2: Support states: Not Installed (gray), Installing (yellow animated), Stopped (red), Starting/Stopping (yellow), Running (green), Error (red)
  - [x] 1.3: Write co-located test file `ServerStatusBadge.test.tsx` verifying all state variants render correctly

- [x] Task 2: Create server API hooks + tests (AC: 5, 6)
  - [x] 2.1: Create `web/src/hooks/use-server-status.ts` hook using TanStack Query with polling
  - [x] 2.2: Create `web/src/api/server.ts` with `fetchServerStatus()`, `startServer()`, `stopServer()`, `restartServer()` functions
  - [x] 2.3: Add server types to `web/src/api/types.ts` (ServerState enum, ServerStatus interface)
  - [x] 2.4: Create mutation hooks for server actions (useStartServer, useStopServer, useRestartServer)
  - [x] 2.5: Write tests for hooks verifying query/mutation behavior

- [x] Task 3: Create ServerControls component + tests (AC: 3, 4, 5)
  - [x] 3.1: Create `web/src/features/dashboard/ServerControls.tsx` with Start/Stop/Restart buttons
  - [x] 3.2: Implement button enable/disable logic based on server state
  - [x] 3.3: Show loading state on buttons during mutations
  - [x] 3.4: Show toast notifications on success/failure using sonner (already installed)
  - [x] 3.5: Write co-located test file verifying button states and mutation calls

- [x] Task 4: Create ServerInstallCard component + tests (AC: 1, 2)
  - [x] 4.1: Create `web/src/components/ServerInstallCard.tsx` for empty/installing state
  - [x] 4.2: Include version input field and "Install Server" button
  - [x] 4.3: Show progress indicator during installation (use existing Progress component)
  - [x] 4.4: Disable install button while installation in progress
  - [x] 4.5: Write co-located tests verifying empty state, installing state, and install action

- [x] Task 5: Implement Dashboard page + tests (AC: 1, 2, 3, 4, 6)
  - [x] 5.1: Update `web/src/features/dashboard/Dashboard.tsx` to integrate all components
  - [x] 5.2: Conditionally render ServerInstallCard OR ServerStatusBadge+ServerControls based on server state
  - [x] 5.3: Display server version and uptime (when running) using Card layout
  - [x] 5.4: Implement TanStack Query polling for auto-refresh (5 second interval)
  - [x] 5.5: Write integration tests verifying conditional rendering and data display

- [x] Task 6: End-to-end validation + polish
  - [x] 6.1: Run `just check` to verify all tests pass and no lint errors
  - [x] 6.2: Manually verify Dashboard appearance and functionality
  - [x] 6.3: Verify toast notifications appear correctly for all actions
  - [x] 6.4: Verify loading states and transitions are smooth

---

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Do not batch tests into a separate "Write tests" task at the end
- Run `just test` to verify all tests pass before marking task complete
- Frontend tests use Vitest with @testing-library/react

### Security Requirements

**Follow patterns in `project-context.md` -> Security Patterns section:**

- API calls use the existing `apiClient` with automatic X-API-Key header injection
- Server control actions (start/stop/restart) require Admin role (handled by backend)
- Status endpoint accessible to both Admin and Monitor roles

### Development Commands

Use `just` for all development tasks:
- `just test` - Run all tests
- `just test-web` - Run frontend tests only
- `just test-web ServerStatusBadge` - Run specific test file
- `just check` - Full validation (lint + typecheck + test)
- `just lint` - Run all linters
- `just dev-web` - Start frontend dev server

### Architecture & Patterns

**This is the FIRST frontend story in Epic 3 - it establishes UI patterns for server management.**

**Existing Frontend Infrastructure (from Epic 1 Story 1.3):**
- React 19.2 + TypeScript + Vite
- TanStack Query v5 configured in `web/src/api/query-client.ts`
- shadcn/ui components in `web/src/components/ui/`
- Catppuccin theming via CSS variables
- Layout components: Sidebar, Header, Layout
- Toast notifications via sonner (`web/src/components/ui/sonner.tsx`)

**Existing API Client (from Epic 2 Story 2.3):**
- `web/src/api/client.ts` - apiClient with X-API-Key header and snake_case/camelCase transforms
- `web/src/api/query-keys.ts` - has `server.status` key already defined
- `web/src/api/types.ts` - ApiResponse and error types

**Backend API Endpoints (from Stories 3.1, 3.2, 3.3):**
```
GET  /api/v1alpha1/server/status          -> ServerStatus (Admin/Monitor)
POST /api/v1alpha1/server/install         -> InstallResponse (Admin only)
GET  /api/v1alpha1/server/install/status  -> InstallStatus (Admin only)
POST /api/v1alpha1/server/start           -> ApiResponse (Admin only)
POST /api/v1alpha1/server/stop            -> ApiResponse (Admin only)
POST /api/v1alpha1/server/restart         -> ApiResponse (Admin only)
```

**ServerState Values (from backend):**
```typescript
type ServerState =
  | 'not_installed'
  | 'installing'
  | 'installed'  // stopped
  | 'starting'
  | 'running'
  | 'stopping'
  | 'error';
```

**ServerStatus Response (from GET /status):**
```json
{
  "status": "ok",
  "data": {
    "state": "running",
    "version": "1.21.3",
    "uptime_seconds": 3600,
    "last_exit_code": null
  }
}
```

**Component Hierarchy:**
```
Dashboard
├── ServerInstallCard (when state === "not_installed" or "installing")
│   ├── Input (version)
│   ├── Button (Install)
│   └── Progress (when installing)
└── ServerStatusDisplay (when server installed)
    ├── Card
    │   ├── ServerStatusBadge
    │   ├── Version display
    │   └── Uptime display (when running)
    └── ServerControls
        ├── Button (Start) - disabled when running/starting/stopping
        ├── Button (Stop) - disabled when not running
        └── Button (Restart) - disabled when not running
```

**Catppuccin Colors (from UX Design Spec):**
```css
--success: #a6e3a1  /* Running state */
--error: #f38ba8    /* Stopped/Error state */
--warning: #f9e2af  /* Starting/Stopping/Installing state */
--muted: #6c7086    /* Not Installed state */
```

### Previous Story Intelligence (3.3)

**Patterns established:**
- `ServerStatus` model with state, version, uptime_seconds, last_exit_code
- GET /status endpoint accessible to both Admin and Monitor
- API response envelope pattern: `{ status: "ok", data: {...} }`

**Test patterns:**
- Use MSW for mocking API responses in frontend tests
- Check loading states and error handling
- Verify TanStack Query cache invalidation

### Git Intelligence

**Recent commits:**
- `284e023` - docs: Add Story 3.3 and update sprint status
- `519fa76` - fix(api): Resolve test code type annotation issues (Story 3.2)
- `7fafb49` - feat(api): Add server lifecycle control API (Story 3.2)

**Files created/modified in Epic 1 Story 1.3 (frontend foundation):**
- `web/src/features/dashboard/Dashboard.tsx` - Placeholder to replace
- `web/src/components/layout/*` - Existing layout components
- `web/src/api/client.ts` - Existing API client

### Project Structure Notes

**Files to create:**
| File | Purpose |
|------|---------|
| `web/src/components/ServerStatusBadge.tsx` | Server state visual indicator |
| `web/src/components/ServerStatusBadge.test.tsx` | Co-located test |
| `web/src/components/ServerInstallCard.tsx` | Empty state install UI |
| `web/src/components/ServerInstallCard.test.tsx` | Co-located test |
| `web/src/features/dashboard/ServerControls.tsx` | Start/Stop/Restart buttons |
| `web/src/features/dashboard/ServerControls.test.tsx` | Co-located test |
| `web/src/api/server.ts` | Server API functions |
| `web/src/hooks/use-server-status.ts` | TanStack Query hook for status |

**Files to modify:**
| File | Change |
|------|--------|
| `web/src/features/dashboard/Dashboard.tsx` | Replace placeholder with full implementation |
| `web/src/api/types.ts` | Add ServerState and ServerStatus types |

### UX Requirements (from UX Design Spec)

**ServerStatusBadge states:**
| State | Color | Icon | Description |
|-------|-------|------|-------------|
| Running | Green (`#a6e3a1`) | Filled circle | Server operational |
| Stopped | Red (`#f38ba8`) | Square | Server not running |
| Starting/Stopping | Yellow (`#f9e2af`) | Animated | Transitional state |
| Installing | Yellow (`#f9e2af`) | Animated | Installation in progress |
| Not Installed | Gray (`#6c7086`) | Empty circle | No server present |
| Error | Red (`#f38ba8`) | X icon | Error state |

**Button Behavior:**
- Primary actions (Install, Start): Accent color (Mauve #cba6f7)
- Destructive actions (Stop): Red outline (#f38ba8)
- Secondary actions (Restart): Surface color (#313244)
- Loading state: Spinner replaces icon, button disabled

**Toast Notifications:**
- Success: Green left border, subtle, 3 second auto-dismiss
- Error: Red left border + background tint, 5 seconds, manual dismiss

**TanStack Query Polling:**
- Poll server status every 5 seconds
- Refetch immediately after mutation success
- Show stale indicator if query fails (optional enhancement)

### API Response Formats

```typescript
// GET /api/v1alpha1/server/status
interface ServerStatus {
  state: ServerState;
  version: string | null;
  uptimeSeconds: number | null;  // camelCase after transform
  lastExitCode: number | null;
}

// POST /api/v1alpha1/server/start (success)
{ status: "ok", data: { message: "Server starting" } }

// POST /api/v1alpha1/server/stop (success)
{ status: "ok", data: { message: "Server stopping" } }

// POST /api/v1alpha1/server/restart (success)
{ status: "ok", data: { message: "Server restarting" } }

// POST /api/v1alpha1/server/install (request body)
{ version: "1.21.3" }

// GET /api/v1alpha1/server/install/status
{
  status: "ok",
  data: {
    state: "downloading" | "extracting" | "configuring" | "complete" | "error",
    progress: 45,  // percentage
    message: "Downloading VintageStory 1.21.3..."
  }
}
```

### References

- `project-context.md` - Critical implementation rules and patterns
- [Source: _bmad-output/planning-artifacts/architecture.md#Frontend Architecture]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Server Lifecycle Management]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.4]
- `web/src/api/client.ts` - Existing API client with transforms
- `web/src/api/query-keys.ts` - Query key definitions (server.status exists)
- `api/src/vintagestory_api/routers/server.py` - Backend endpoints

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

- **Task 1 (ServerStatusBadge):** Created component with all 7 server states (not_installed, installing, installed/stopped, starting, running, stopping, error). Each state has appropriate color (green/red/yellow/gray) and animation (spinner for transitional states). 15 tests passing.

- **Task 2 (API hooks):** Created `web/src/api/server.ts` with API functions and `web/src/hooks/use-server-status.ts` with TanStack Query hooks. Added ServerState, ServerStatus, InstallStatus, and ActionMessage types to `web/src/api/types.ts`. Hooks include 5-second polling for status and immediate refetch after mutations. 9 tests passing.

- **Task 3 (ServerControls):** Created component with Start/Stop/Restart buttons. Button enable/disable logic based on server state. Loading spinners during mutations. Toast notifications on success/failure using sonner. 14 tests passing.

- **Task 4 (ServerInstallCard):** Created component with version input and install button. Progress indicator during installation shows stage, percentage, and message. Added shadcn/ui Input and Progress components. Installed @radix-ui/react-progress dependency. 13 tests passing.

- **Task 5 (Dashboard):** Integrated all components into Dashboard page. Conditionally renders ServerInstallCard or status card based on server state. Shows version and formatted uptime. Uses TanStack Query polling. 13 tests passing.

- **Task 6 (Validation):** Ran `just check` - all 239 API tests and 176 web tests passing. No lint or type errors.

### File List

**New Files Created:**
- `web/src/components/ServerStatusBadge.tsx`
- `web/src/components/ServerStatusBadge.test.tsx`
- `web/src/components/ServerInstallCard.tsx`
- `web/src/components/ServerInstallCard.test.tsx`
- `web/src/components/ui/input.tsx`
- `web/src/components/ui/progress.tsx`
- `web/src/features/dashboard/ServerControls.tsx`
- `web/src/features/dashboard/ServerControls.test.tsx`
- `web/src/features/dashboard/Dashboard.test.tsx`
- `web/src/api/server.ts`
- `web/src/hooks/use-server-status.ts`
- `web/src/hooks/use-server-status.test.tsx`

**Modified Files:**
- `web/src/features/dashboard/Dashboard.tsx` - Complete rewrite with full server status UI
- `web/src/api/types.ts` - Added ServerState, ServerStatus, InstallStatus, ActionMessage types
- `web/package.json` - Added @radix-ui/react-progress dependency

### Change Log

- **2025-12-27:** Story 3.4 completed - Dashboard with Server Controls UI
  - Implemented full server status dashboard with conditional rendering
  - Created ServerStatusBadge, ServerControls, and ServerInstallCard components
  - Added server API functions and TanStack Query hooks with 5-second polling
  - All 6 acceptance criteria satisfied with 64 new tests (176 total web tests)
