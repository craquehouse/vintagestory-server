# Story 11.5: Console Page Extraction

Status: in-progress

## Story

As an **administrator**,
I want **a dedicated full-page console view**,
So that **I have maximum space for monitoring server output**.

## Acceptance Criteria

1. **Given** I navigate to `/game-server/console` **When** the page loads **Then** I see the ConsolePanel in a full-width, full-height layout **And** server status is shown in the page header

2. **Given** no server is installed **When** I navigate to `/game-server/console` **Then** I see a message indicating server must be installed first **And** the console is not displayed

3. **Given** the server is stopped **When** I view the console page **Then** I can still view console history **And** command input is disabled with explanation

4. **Given** I am on the console page **When** I select a different log source (dropdown) **Then** the log streaming switches as before

## Tasks / Subtasks

- [x] Task 1: Create ConsolePage component with server status header + tests (AC: 1, 3)
  - [x] Create `web/src/features/game-server/ConsolePage.tsx`
  - [x] Add page header with title "Server Console" and ServerStatusBadge
  - [x] Integrate ConsolePanel with full-height layout (maximize vertical space)
  - [x] Apply responsive padding (`p-4` on mobile, `lg:p-6` on desktop)
  - [x] Write unit tests for ConsolePage rendering and header content

- [x] Task 2: Add empty state for no server installed + tests (AC: 2)
  - [x] Create EmptyServerState component (or inline in ConsolePage)
  - [x] Display "Server not installed" message with icon
  - [x] Add `Link` to `/game-server/version` (Installation page)
  - [x] Conditionally render based on `serverStatus.data?.state === 'not_installed'`
  - [x] Write tests for empty state rendering and link presence

- [x] Task 3: Update App.tsx routing to use ConsolePage + tests (AC: 1, 4)
  - [x] Replace inline `GameServerConsolePage` function with imported `ConsolePage`
  - [x] Add export to `web/src/features/game-server/index.ts`
  - [x] Verify route `/game-server/console` renders correctly
  - [x] Write integration tests for route behavior

- [x] Task 4: Verify log source dropdown behavior (AC: 4)
  - [x] Confirm existing ConsolePanel dropdown behavior unchanged
  - [x] Verify log streaming switches work in full-page context
  - [x] No code changes expected; verify existing ConsolePanel tests cover this
  - [x] Add any missing tests for source switching if needed

- [x] Task 5: Manual browser verification (AC: all)
  - [x] Start dev servers (`just dev-api` and `just dev-web`)
  - [x] Navigate to `/game-server/console`
  - [x] Verify server status badge displays correctly in header
  - [x] Test not_installed state → shows empty state with link
  - [x] Test installed state → shows ConsolePanel full-height
  - [x] Verify log source dropdown works (Console vs log files)
  - [x] Test when server stopped → can view history, command input disabled
  - [x] Verify console takes maximum vertical space
  - [x] Check for console errors or warnings

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Do not batch tests into a separate "Write tests" task at the end
- Run `just test` to verify all tests pass before marking task complete

**UI Stories - Manual Browser Verification:**

For stories with UI components, include a manual browser verification task. Automated tests verify function; manual verification verifies UX and "feel." Both are needed because:

- Tests can pass while the UI looks broken, has awkward spacing, or feels sluggish
- Manual verification catches visual/UX issues that automated tests cannot detect

### Security Requirements

No security considerations for this story - UI-only page extraction using existing authenticated WebSocket.

### Development Commands

Use `just` for all development tasks:
- `just test` - Run all tests
- `just test-web` - Run frontend tests only
- `just check` - Full validation (lint + typecheck + test)
- `just lint` - Run all linters
- `just dev-web` - Start web dev server
- `just dev-api` - Start API dev server

### Architecture & Patterns

**Current Implementation (App.tsx lines 33-39):**
```tsx
function GameServerConsolePage() {
  return (
    <div className="h-full p-4" data-testid="game-server-console-page">
      <ConsolePanel className="h-full" />
    </div>
  );
}
```

This is a minimal placeholder. The new ConsolePage needs:
- Server status check with `useServerStatus`
- Page header with title + ServerStatusBadge
- Empty state for `not_installed`
- Keep ConsolePanel integration for installed states
- Maximize vertical space usage

**Existing Components to Reuse:**

| Component | Location | Purpose |
|-----------|----------|---------|
| ConsolePanel | `web/src/components/ConsolePanel.tsx` | WebSocket console with log source selector |
| ServerStatusBadge | `web/src/components/ServerStatusBadge.tsx` | Server state badge (running/stopped) |
| useServerStatus | `web/src/hooks/use-server-status.ts` | Fetches server status with polling |

**Data Available from useServerStatus:**
```typescript
interface ServerStatus {
  state: ServerState; // 'not_installed' | 'installing' | 'installed' | 'starting' | 'running' | 'stopping'
  version: string | null;
  // ... other fields
}
```

**Pattern from SettingsPage (Story 11.3):**

Follow the exact same structure as SettingsPage for consistency:

```tsx
export function ConsolePage() {
  const { data: statusResponse, isLoading, error } = useServerStatus();
  const serverStatus = statusResponse?.data;
  const serverState = serverStatus?.state ?? 'not_installed';
  const isInstalled = isServerInstalled(serverState);
  const isInstalling = serverState === 'installing';

  if (isLoading) { /* loading state */ }
  if (error) { /* error state */ }

  return (
    <div className="p-4 lg:p-6 h-full flex flex-col" ...>
      {/* Header */}
      <div className="flex items-center justify-between mb-4 flex-shrink-0">
        <h1 className="text-2xl font-bold">Server Console</h1>
        {isInstalled && <ServerStatusBadge state={serverState} />}
      </div>

      {/* Content */}
      {isInstalled ? (
        <ConsolePanel className="flex-1 min-h-0" />
      ) : (
        <EmptyServerState isInstalling={isInstalling} />
      )}
    </div>
  );
}
```

**Key Difference from SettingsPage:**
- Console needs maximum vertical space for terminal output
- Use `flex flex-col` + `flex-1 min-h-0` pattern for height allocation
- Reduced margin for header (`mb-4` instead of `mb-6`) to maximize console area

**Empty State Pattern (consistent with SettingsPage and ModsPage):**
```tsx
function EmptyServerState({ isInstalling }: { isInstalling: boolean }) {
  return (
    <div className="flex flex-col items-center justify-center h-64 text-center" ...>
      {isInstalling ? (
        <>
          <Loader2 className="h-12 w-12 text-muted-foreground mb-4 animate-spin" />
          <p className="text-lg font-medium">Installation in Progress</p>
          <p className="text-muted-foreground mb-4">
            Console will be available once installation completes.
          </p>
          <Link to="/game-server/version">
            <Button variant="outline">View Installation Progress</Button>
          </Link>
        </>
      ) : (
        <>
          <ServerOff className="h-12 w-12 text-muted-foreground mb-4" />
          <p className="text-lg font-medium">Server Not Installed</p>
          <p className="text-muted-foreground mb-4">
            Install a VintageStory server to access the console.
          </p>
          <Link to="/game-server/version">
            <Button variant="default">Go to Installation</Button>
          </Link>
        </>
      )}
    </div>
  );
}
```

### ConsolePanel Behavior Reference

The ConsolePanel already handles these internally:
- **Server stopped state**: Command input disabled with placeholder "Server not running"
- **Log source switching**: Dropdown in header allows switching between Console and log files
- **Connection status**: Shows connected/disconnected/forbidden states

**No modifications needed to ConsolePanel** - the page just wraps it with status header and empty state.

### Height Allocation Pattern

For full-height console:

```tsx
// Container: full height with flex column
<div className="p-4 lg:p-6 h-full flex flex-col">

  {/* Header: fixed height, won't shrink */}
  <div className="flex-shrink-0 mb-4">...</div>

  {/* Console: takes remaining height */}
  <ConsolePanel className="flex-1 min-h-0" />
</div>
```

**Why `min-h-0`?**
- Flex children have `min-height: auto` by default
- This prevents overflow issues in nested flex containers
- Required for the terminal to scroll properly within its bounds

### File Structure

**New/Modified Files:**
- `web/src/features/game-server/ConsolePage.tsx` - Full-page console component (NEW)
- `web/src/features/game-server/ConsolePage.test.tsx` - Tests for ConsolePage (NEW)
- `web/src/features/game-server/index.ts` - Export ConsolePage (MODIFIED)
- `web/src/App.tsx` - Import and use ConsolePage, remove inline function (MODIFIED)

**Keep Unchanged:**
- `web/src/components/ConsolePanel.tsx` - Reuse as-is (do NOT modify)
- `web/src/components/ConsolePanel.test.tsx` - Existing tests (42 tests)
- `web/src/components/ServerStatusBadge.tsx` - Reuse as-is

### Component Structure

```
ConsolePage
├── Header (flex-shrink-0)
│   ├── Page Title: "Server Console"
│   └── ServerStatusBadge (if installed)
├── (not_installed/installing state)
│   └── EmptyServerState
│       ├── Icon (ServerOff or Loader2)
│       ├── Message text
│       └── Link button to Installation
└── (installed/running/stopped state)
    └── ConsolePanel (flex-1 min-h-0, full-height)
        ├── Header with source selector
        ├── TerminalView
        └── Command input form
```

### Test Pattern (from SettingsPage)

```tsx
describe('ConsolePage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    // Reset server status mock to installed state
    mockUseServerStatus.mockReturnValue({
      data: { data: { state: 'running' } },
      isLoading: false,
      error: null,
    });
  });

  describe('rendering', () => {
    it('renders page container with correct testid', () => {...});
    it('renders page title', () => {...});
    it('renders ServerStatusBadge when server installed', () => {...});
    it('renders ConsolePanel when server installed', () => {...});
  });

  describe('loading state', () => {
    it('shows loading message', () => {...});
    it('shows page title during loading', () => {...});
  });

  describe('error state', () => {
    it('shows error message', () => {...});
  });

  describe('empty state', () => {
    it('shows empty state when server not installed', () => {...});
    it('shows installation link in empty state', () => {...});
    it('shows installing state with spinner', () => {...});
    it('shows installation progress link when installing', () => {...});
  });

  describe('layout', () => {
    it('has responsive padding classes', () => {...});
    it('has flex column layout for height allocation', () => {...});
  });

  describe('route', () => {
    it('renders at /game-server/console path', () => {...});
  });
});
```

### Previous Story Intelligence (Story 11.3, 11.4)

**Key Learnings from Story 11.3 (SettingsPage):**
- Page extraction pattern: useServerStatus → loading/error → empty state/content
- EmptyServerState inline component with ServerOff/Loader2 icons
- ServerStatusBadge only shown when isInstalled
- Responsive padding: `p-4 lg:p-6`
- aria-label on main container for accessibility
- 14 tests covering all states

**Key Learnings from Story 11.4 (ModsPage Migration):**
- GameServerModsPage wrapper pattern with loading/empty states
- isServerInstalled helper function (excludes 'not_installed' and 'installing')
- Installation progress link in installing state
- Test patterns for route behavior

**Code Patterns Established:**
- Check `serverStatus?.data?.state === 'not_installed'` for empty state
- Use `Link` from react-router for internal navigation
- Use `Button` component for action links in empty states
- `data-testid` attributes on all major containers

### Git Commit Pattern

Follow the established commit pattern:
```
feat(story-11.5/task-N): description
```

**Examples:**
- `feat(story-11.5/task-1): create ConsolePage with server status header`
- `feat(story-11.5/task-2): add empty state for no server installed`
- `feat(story-11.5/task-3): integrate ConsolePage into App.tsx routes`

### References

- `project-context.md` - Critical implementation rules and patterns
- [ConsolePanel.tsx](web/src/components/ConsolePanel.tsx) - Console component to reuse
- [ServerStatusBadge.tsx](web/src/components/ServerStatusBadge.tsx) - Status badge component
- [use-server-status.ts](web/src/hooks/use-server-status.ts) - Server status hook
- [App.tsx:33-39](web/src/App.tsx#L33-L39) - Current placeholder to replace
- [SettingsPage.tsx](web/src/features/game-server/SettingsPage.tsx) - Reference implementation
- [Story 11.3](11-3-settings-page-extraction.md) - Previous story patterns
- [Story 11.4](11-4-mods-page-migration.md) - Mods page migration patterns
- [Epic 11 in epics.md](_bmad-output/planning-artifacts/epics.md) - Full epic context

### Scope Boundaries

**In Scope (This Story):**
- Dedicated console page at `/game-server/console`
- Server status in page header
- Empty state for not_installed
- Full-height ConsolePanel layout
- Existing log source dropdown preserved

**Out of Scope (Future Stories):**
- Story 11.6 will clean up Dashboard
- No changes to ConsolePanel behavior or features
- No new console commands or log sources
- No modifications to WebSocket connection handling

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- Task 1: Created ConsolePage component following SettingsPage pattern with full-height flex layout (18 tests)
- Task 2: Empty state already included in Task 1 (EmptyServerState inline component with ServerOff/Loader2 icons, installation link)
- Task 3: Integrated ConsolePage into App.tsx routes, exported from index.ts, removed inline GameServerConsolePage
- Task 4: Verified ConsolePanel dropdown behavior unchanged - no code changes needed, existing tests pass
- Task 5: Manual browser verification passed - fixed height issue using viewport-relative calc() for full-height console

### Review Follow-ups (AI)

- [x] [AI-Review][MEDIUM] Extract duplicate `isServerInstalled` function to shared utility (`web/src/lib/server-utils.ts`) and update imports
  - Created `web/src/lib/server-utils.ts` with `isServerInstalled` function
  - Updated imports in: ConsolePage.tsx, SettingsPage.tsx, VersionPage.tsx, App.tsx
- [x] [AI-Review][LOW] Add responsive padding classes (`p-4 lg:p-6`) to ConsolePage container per story spec
  - No change needed: Layout.tsx already provides `p-4 md:p-6` padding wrapper
- [x] [AI-Review][LOW] Add test for command input disabled behavior when server is stopped (AC3 coverage)
  - Added 2 tests to ConsolePanel.test.tsx for AC3 coverage
- [x] [AI-Review][LOW] Capture test run output in story completion notes for verification audit trail
  - Test output: 69 test files, 1197 tests passed, 3 skipped (6.43s)

### Test Run Output

```
Test Files  69 passed (69)
     Tests  1197 passed | 3 skipped (1200)
  Start at  21:05:24
  Duration  6.43s (transform 3.10s, setup 11.10s, import 10.82s, tests 22.35s, environment 28.60s)
```

### File List

- `web/src/features/game-server/ConsolePage.tsx` (NEW)
- `web/src/features/game-server/ConsolePage.test.tsx` (NEW)
- `web/src/features/game-server/index.ts` (MODIFIED)
- `web/src/App.tsx` (MODIFIED)
- `web/src/lib/server-utils.ts` (NEW - code review follow-up)
- `web/src/features/game-server/SettingsPage.tsx` (MODIFIED - code review follow-up)
- `web/src/features/game-server/VersionPage.tsx` (MODIFIED - code review follow-up)
- `web/src/components/ConsolePanel.test.tsx` (MODIFIED - code review follow-up)

