# Story 11.6: Dashboard & Navigation Cleanup

Status: review

## Story

As an **administrator**,
I want **a simplified Dashboard focused on status**,
So that **it serves as a quick overview without duplicate functionality**.

## Acceptance Criteria

1. **Given** I navigate to Dashboard **When** the page loads **Then** ServerInstallCard is NOT displayed (moved to Version page) **And** Server status card remains with basic info

2. **Given** no server is installed **When** I view the Dashboard **Then** I see a card indicating "No server installed" **And** a button/link takes me to `/game-server/version`

3. **Given** the sidebar navigation is updated **When** I view the sidebar **Then** "Settings" is renamed to "VSManager" **And** "Mods" is no longer a top-level item

4. **Given** the default route for `/game-server` **When** I navigate to `/game-server` without a sub-path **Then** I am redirected to `/game-server/version`

## Tasks / Subtasks

- [x] Task 1: Remove ServerInstallCard from Dashboard and add empty state + tests (AC: 1, 2)
  - [x] Remove `ServerInstallCard` import from Dashboard.tsx
  - [x] Remove install status polling logic (no longer needed in Dashboard)
  - [x] Replace not_installed/installing rendering with simplified empty state card
  - [x] Add "No server installed" card with HardDrive icon and link to `/game-server/version`
  - [x] Add "Installation in progress" state with link to version page
  - [x] Update Dashboard tests: remove ServerInstallCard tests, add empty state tests
  - [x] Verify server status card still displays when installed

- [x] Task 2: Update /game-server default redirect to /version + tests (AC: 4)
  - [x] Change `Navigate to="console"` to `Navigate to="version"` in App.tsx
  - [x] Update App.tsx route comment to reflect the change
  - [x] Add/update test for default redirect behavior

- [x] Task 3: Verify sidebar navigation (AC: 3) - No Code Changes Expected
  - [x] Confirm "VSManager" label exists in Sidebar.tsx (line 36)
  - [x] Confirm top-level "Mods" is removed (Story 11.4 completed this)
  - [x] Review existing Sidebar tests verify these behaviors
  - [x] No new code changes needed - just verification

- [x] Task 4: Manual browser verification (AC: all)
  - [x] Start dev servers (`just dev-api` and `just dev-web`)
  - [x] Navigate to Dashboard when server not installed → see empty state with link
  - [x] Click link → goes to `/game-server/version` (Installation page)
  - [x] Navigate to `/game-server` → redirects to `/game-server/version`
  - [x] Verify sidebar shows "VSManager" (not "Settings")
  - [x] Verify "Mods" is only under Game Server sub-nav
  - [x] With server installed → Dashboard shows server status card
  - [x] Check for console errors or warnings

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Do not batch tests into a separate "Write tests" task at the end
- Run `just test` to verify all tests pass before marking task complete

**UI Stories - Manual Browser Verification:**

For stories with UI components, include a manual browser verification task. Automated tests verify function; manual verification verifies UX and "feel."

### Security Requirements

No security considerations for this story - UI-only navigation cleanup using existing authenticated APIs.

### Development Commands

Use `just` for all development tasks:
- `just test` - Run all tests
- `just test-web` - Run frontend tests only
- `just check` - Full validation (lint + typecheck + test)
- `just lint` - Run all linters
- `just dev-web` - Start web dev server
- `just dev-api` - Start API dev server

### Architecture & Patterns

**Current Dashboard Implementation ([Dashboard.tsx](web/src/features/dashboard/Dashboard.tsx)):**

The Dashboard currently shows `ServerInstallCard` for not_installed/installing states (lines 65-74). This needs to be replaced with a simplified empty state card.

```tsx
// CURRENT (to be removed):
if (state === 'not_installed' || state === 'installing') {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>
      <ServerInstallCard
        isInstalling={state === 'installing'}
        installStatus={installStatus}
      />
    </div>
  );
}
```

**New Empty State Pattern:**

Follow the established pattern from [VersionPage.tsx](web/src/features/game-server/VersionPage.tsx), [SettingsPage.tsx](web/src/features/game-server/SettingsPage.tsx), and [ConsolePage.tsx](web/src/features/game-server/ConsolePage.tsx):

```tsx
// NEW simplified empty state:
if (state === 'not_installed' || state === 'installing') {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12 text-center">
          {state === 'installing' ? (
            <>
              <Loader2 className="h-12 w-12 text-muted-foreground mb-4 animate-spin" />
              <p className="text-lg font-medium">Installation in Progress</p>
              <p className="text-muted-foreground mb-4">
                Visit the Installation page to view progress.
              </p>
              <Link to="/game-server/version">
                <Button variant="outline">View Installation Progress</Button>
              </Link>
            </>
          ) : (
            <>
              <HardDrive className="h-12 w-12 text-muted-foreground mb-4" />
              <p className="text-lg font-medium">No Server Installed</p>
              <p className="text-muted-foreground mb-4">
                Install a VintageStory server to get started.
              </p>
              <Link to="/game-server/version">
                <Button variant="default">Go to Installation</Button>
              </Link>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
```

**Current App.tsx Default Redirect ([App.tsx:111](web/src/App.tsx#L111)):**

```tsx
// CURRENT (to be changed):
<Route index element={<Navigate to="console" replace />} />

// NEW:
<Route index element={<Navigate to="version" replace />} />
```

**What's Already Done (Stories 11.1-11.5):**

| Feature | Status | Location |
|---------|--------|----------|
| "VSManager" label in sidebar | DONE | [Sidebar.tsx:36](web/src/components/layout/Sidebar.tsx#L36) |
| Top-level "Mods" removed | DONE | Story 11.4 |
| Sub-navigation infrastructure | DONE | Story 11.1 |
| VersionPage with ServerInstallCard | DONE | [VersionPage.tsx](web/src/features/game-server/VersionPage.tsx) |

**Components to Modify:**

| Component | Action | Details |
|-----------|--------|---------|
| [Dashboard.tsx](web/src/features/dashboard/Dashboard.tsx) | MODIFY | Remove ServerInstallCard, add empty state |
| [Dashboard.test.tsx](web/src/features/dashboard/Dashboard.test.tsx) | MODIFY | Update tests for new empty state |
| [App.tsx](web/src/App.tsx) | MODIFY | Change default redirect from console to version |

**Components to Keep Unchanged:**

| Component | Reason |
|-----------|--------|
| [Sidebar.tsx](web/src/components/layout/Sidebar.tsx) | Already has VSManager label and no top-level Mods |
| [ServerInstallCard.tsx](web/src/components/ServerInstallCard.tsx) | Still used in VersionPage |
| [VersionPage.tsx](web/src/features/game-server/VersionPage.tsx) | ServerInstallCard already moved here |

### Imports to Remove from Dashboard

```tsx
// REMOVE these imports:
import { ServerInstallCard } from '@/components/ServerInstallCard';
import { useInstallStatus } from '@/hooks/use-server-status';

// ADD these imports:
import { Link } from 'react-router';
import { Loader2 } from 'lucide-react';
```

### Dashboard Test Changes

**Tests to Remove:**
- `'shows ServerInstallCard when server is not installed'`
- `'hides server control buttons when not installed'`
- `'shows progress indicator during installation'`
- `'disables install button during installation'`

**Tests to Add:**
- `'shows empty state card when server is not installed'`
- `'shows link to Installation page in empty state'`
- `'shows installing state with spinner and progress link'`
- `'does not show server controls in empty state'`

### Previous Story Intelligence (Stories 11.1-11.5)

**Key Learnings from Story 11.5 (ConsolePage):**
- Empty state pattern: Card with icon, title, description, and link button
- `Link` component from react-router for internal navigation
- `Button` component with `variant="default"` for primary action
- `Loader2` icon with `animate-spin` for installing state
- Consistent padding and spacing in Card components

**Key Learnings from Story 11.4 (ModsPage Migration):**
- Route redirect patterns in App.tsx
- Test patterns for route behavior
- Legacy route redirects work correctly

**Code Patterns Established:**
- Empty state uses `Card` with `CardContent` and centered flex layout
- Icons: `HardDrive` for version/installation, `ServerOff` for not installed, `Loader2` for loading
- Links to Installation page use `/game-server/version` path

### Git Commit Pattern

Follow the established commit pattern:
```
feat(story-11.6/task-N): description
```

**Examples:**
- `feat(story-11.6/task-1): replace ServerInstallCard with empty state in Dashboard`
- `feat(story-11.6/task-2): change default /game-server redirect to /version`

### Scope Boundaries

**In Scope (This Story):**
- Remove ServerInstallCard from Dashboard
- Add simplified empty state to Dashboard
- Change /game-server default redirect to /version
- Update Dashboard tests

**Out of Scope:**
- ServerInstallCard component itself (remains for VersionPage)
- Sidebar navigation changes (already done in previous stories)
- Any API changes
- VersionPage modifications

### FR Coverage

| FR | Description | Task |
|----|-------------|------|
| FR97 | Remove install from Dashboard | Task 1 |
| FR98 | Dashboard link to Version page | Task 1 |
| FR99 | Default redirect /game-server → /game-server/version | Task 2 |
| FR90 | Rename Settings to VSManager | Task 3 (verification only) |

### References

- `project-context.md` - Critical implementation rules and patterns
- [Dashboard.tsx](web/src/features/dashboard/Dashboard.tsx) - Main component to modify
- [Dashboard.test.tsx](web/src/features/dashboard/Dashboard.test.tsx) - Tests to update
- [App.tsx](web/src/App.tsx) - Route configuration
- [VersionPage.tsx](web/src/features/game-server/VersionPage.tsx) - Reference for ServerInstallCard usage
- [ConsolePage.tsx](web/src/features/game-server/ConsolePage.tsx) - Reference for empty state pattern
- [Story 11.5](11-5-console-page-extraction.md) - Previous story patterns
- [Epic 11 in epics.md](_bmad-output/planning-artifacts/epics.md) - Full epic context

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- Task 1: Replaced ServerInstallCard with shared EmptyServerState component in Dashboard. Removed useInstallStatus hook dependency. Updated tests to verify empty state behavior with links to /game-server/version. All 1198 web tests pass.
- Task 2: Changed default /game-server redirect from "console" to "version" in App.tsx. Created App.test.tsx with routing tests. All 1201 web tests pass.
- Task 3: Verification only. Confirmed "VSManager" label in Sidebar.tsx:36 and top-level Mods removed (per Story 11.4). Existing Sidebar tests verify these behaviors. No code changes needed.
- Task 4: Manual browser verification completed. All acceptance criteria verified in Docker container at localhost:8080.

### File List

- web/src/features/dashboard/Dashboard.tsx (modified)
- web/src/features/dashboard/Dashboard.test.tsx (modified)
- web/src/App.tsx (modified)
- web/src/App.test.tsx (created)
