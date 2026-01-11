# Story 11.3: Settings Page Extraction

Status: complete

## Story

As an **administrator**,
I want **a dedicated full-page view for game server settings**,
So that **I have more space to view and edit configuration**.

## Acceptance Criteria

1. **Given** I navigate to `/game-server/settings` **When** the page loads **Then** I see the GameConfigPanel in a full-width layout **And** server status is shown in the page header

2. **Given** no server is installed **When** I navigate to `/game-server/settings` **Then** I see a message indicating server must be installed first **And** a link to the Installation page is provided

3. **Given** I am on the settings page **When** I edit a setting **Then** the existing auto-save behavior works as before **And** toast notifications appear for success/error

4. **Given** the settings page is displayed **When** I view the layout **Then** setting groups have better horizontal space utilization than the previous split-view

## Tasks / Subtasks

- [x] Task 1: Create SettingsPage component with server status header + tests (AC: 1, 4)
  - [x] Create `web/src/features/game-server/SettingsPage.tsx` (rename from placeholder)
  - [x] Add page header with title "Game Settings" and ServerStatusBadge
  - [x] Integrate GameConfigPanel with full-width layout
  - [x] Apply responsive padding (`p-4` on mobile, `p-6` on desktop)
  - [x] Write unit tests for SettingsPage rendering and header content

- [x] Task 2: Add empty state for no server installed + tests (AC: 2)
  - [x] Create EmptyServerState component (or inline in SettingsPage)
  - [x] Display "Server not installed" message with icon
  - [x] Add `Link` to `/game-server/version` (Installation page)
  - [x] Conditionally render based on `serverStatus.data?.data?.state === 'not_installed'`
  - [x] Write tests for empty state rendering and link presence

- [x] Task 3: Update App.tsx routing to use SettingsPage component + tests (AC: 1)
  - [x] Replace placeholder `GameServerSettingsPage` with imported `SettingsPage`
  - [x] Add export to `web/src/features/game-server/index.ts`
  - [x] Verify route `/game-server/settings` renders correctly
  - [x] Write integration tests for route behavior

- [x] Task 4: Verify auto-save and toast behavior (AC: 3)
  - [x] Confirm existing GameConfigPanel save behavior unchanged
  - [x] Verify toast notifications appear on save success/error
  - [x] No code changes expected; verify existing tests cover this
  - [x] Add any missing tests for save behavior if needed

- [x] Task 5: Manual browser verification (AC: all)
  - [x] Start dev servers (`just dev-api` and `just dev-web`)
  - [x] Navigate to `/game-server/settings`
  - [x] Verify server status badge displays correctly in header
  - [x] Test not_installed state → shows empty state with link
  - [x] Test installed state → shows GameConfigPanel
  - [x] Edit a setting and verify auto-save with toast
  - [x] Verify improved layout width compared to previous split-view
   - [x] Check for console errors or warnings

## Review Follow-ups (AI)

### Code Review by Adversarial Reviewer (2026-01-11)

#### High Priority
- [x] [AI-Review][HIGH] Add route integration test for `/game-server/settings` route (Task 3 subtask "Write integration tests for route behavior" incomplete) [file: web/src/features/game-server/SettingsPage.test.tsx]

#### Medium Priority
- [x] [AI-Review][MEDIUM] Remove extra blank lines in App.tsx (lines 25-26) after placeholder removal [file: web/src/App.tsx:25-26]
- [x] [AI-Review][MEDIUM] Document CSS theme color additions as dependency fix in Dev Notes (scope creep from AC) [file: web/src/styles/index.css]

#### Low Priority
- [x] [AI-Review][LOW] Add test verifying `lg:p-6` responsive padding class [file: web/src/features/game-server/SettingsPage.test.tsx]
- [x] [AI-Review][LOW] Add `aria-label="Game Settings"` to main container for accessibility [file: web/src/features/game-server/SettingsPage.tsx:69]
- [x] [AI-Review][LOW] Add test for "View Installation Progress" link in installing state [file: web/src/features/game-server/SettingsPage.test.tsx]

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Do not batch tests into a separate "Write tests" task at the end
- Run `just test` to verify all tests pass before marking task complete

### Architecture & Patterns

**Existing Components to Reuse:**

| Component | Location | Purpose |
|-----------|----------|---------|
| GameConfigPanel | `web/src/features/game-server/GameConfigPanel.tsx` | Settings groups with auto-save |
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

**Page Header Pattern (from UX spec):**
```tsx
<div className="flex items-center justify-between mb-6">
  <h1 className="text-2xl font-bold">Game Settings</h1>
  <ServerStatusBadge state={serverStatus?.data?.state ?? 'not_installed'} />
</div>
```

**Empty State Pattern (consistent with other pages):**
```tsx
<div className="flex flex-col items-center justify-center h-64 text-center">
  <ServerOff className="h-12 w-12 text-muted-foreground mb-4" />
  <p className="text-lg font-medium">Server Not Installed</p>
  <p className="text-muted-foreground mb-4">
    Install a VintageStory server to configure settings.
  </p>
  <Link to="/game-server/version">
    <Button variant="default">Go to Installation</Button>
  </Link>
</div>
```

### File Structure

**New/Modified Files:**
- `web/src/features/game-server/SettingsPage.tsx` - Full-page settings component (currently placeholder in App.tsx)
- `web/src/features/game-server/SettingsPage.test.tsx` - Tests for SettingsPage
- `web/src/features/game-server/index.ts` - Export SettingsPage
- `web/src/App.tsx` - Import and use SettingsPage

**Keep Unchanged:**
- `web/src/features/game-server/GameConfigPanel.tsx` - Reuse as-is (do NOT modify)
- `web/src/features/game-server/GameConfigPanel.test.tsx` - Existing tests
- `web/src/components/ServerStatusBadge.tsx` - Reuse as-is

### Component Structure

```
SettingsPage
├── Header
│   ├── Page Title: "Game Settings"
│   └── ServerStatusBadge
├── (not_installed state)
│   └── EmptyServerState
│       ├── Icon (ServerOff)
│       ├── Message text
│       └── Link button to Installation
└── (installed/running state)
    └── GameConfigPanel (full-width)
```

### Current Placeholder vs Target Implementation

**Current (in App.tsx, line 44-50):**
```tsx
function GameServerSettingsPage() {
  return (
    <div className="p-4 h-full overflow-auto" data-testid="game-server-settings-page">
      <GameConfigPanel />
    </div>
  );
}
```

**Target Implementation:**
- Add server status check with `useServerStatus`
- Add page header with title + ServerStatusBadge
- Add empty state for `not_installed`
- Keep GameConfigPanel integration for installed states
- Improve layout with better spacing

### Layout Considerations

**Previous Layout (GameServerPage split-view):**
- GameConfigPanel shared 50% width with ConsolePanel
- Limited horizontal space for setting groups

**New Layout (dedicated SettingsPage):**
- GameConfigPanel gets full content width (minus sidebar)
- Better readability for setting labels and values
- More room for setting group expansion

**Responsive Padding Pattern:**
```tsx
<div className="p-4 lg:p-6 h-full overflow-auto">
```

### Anti-Patterns to Avoid

| Avoid | Do Instead |
|-------|------------|
| Modifying GameConfigPanel | Keep unchanged, compose around it |
| Creating new hooks for status | Use existing useServerStatus |
| Hardcoding server states | Use ServerState type from API types |
| Inline styles | Use Tailwind CSS classes |
| Separate "Write tests" task | Tests included in each task |

### Security Requirements

No security considerations for this story - UI-only page extraction using existing authenticated API.

### Development Commands

Use `just` for all development tasks:
- `just test` - Run all tests
- `just test-web` - Run frontend tests only
- `just check` - Full validation (lint + typecheck + test)
- `just lint` - Run all linters
- `just dev-web` - Start web dev server
- `just dev-api` - Start API dev server

### Previous Story Intelligence (Story 11.1 & 11.2)

**Key Learnings from Story 11.1:**
- Placeholder pages were created in App.tsx - this story replaces the settings placeholder
- Route `/game-server/settings` already exists and works
- Feature pages go in `web/src/features/game-server/`
- Use `data-testid` attributes for testing
- Use existing shadcn/ui Card components for consistent styling
- Follow existing padding patterns (`p-4` for page containers)

**Key Learnings from Story 11.2:**
- ServerStatusBadge reuse pattern established
- useServerStatus hook provides all needed state data
- Empty state pattern with link to other page
- Page title pattern: `<h1 className="text-2xl font-bold">`

**Code Patterns Established:**
- Check `serverStatus?.data?.state === 'not_installed'` for empty state
- Use `Link` from react-router for internal navigation
- Use `Button` component for action links in empty states

### Git Commit Pattern

Follow the established commit pattern:
```
feat(story-11.3/task-N): description
```

**Examples:**
- `feat(story-11.3/task-1): create SettingsPage with server status header`
- `feat(story-11.3/task-2): add empty state for no server installed`
- `feat(story-11.3/task-3): integrate SettingsPage into App.tsx routes`

### References

- `project-context.md` - Critical implementation rules and patterns
- [GameConfigPanel.tsx](web/src/features/game-server/GameConfigPanel.tsx) - Settings panel to reuse
- [ServerStatusBadge.tsx](web/src/components/ServerStatusBadge.tsx) - Status badge component
- [use-server-status.ts](web/src/hooks/use-server-status.ts) - Server status hook
- [App.tsx](web/src/App.tsx) - Current routing with placeholder (lines 44-50)
- [Story 11.1](11-1-sub-navigation-infrastructure.md) - Previous story patterns
- [Story 11.2](11-2-version-installation-page.md) - Version page patterns
- [Epic 11 in epics.md](_bmad-output/planning-artifacts/epics.md) - Full epic context
- [UX Design Specification](_bmad-output/planning-artifacts/ux-design-specification.md) - Layout patterns

### Scope Boundaries

**In Scope (This Story):**
- Dedicated settings page at `/game-server/settings`
- Server status in page header
- Empty state for not_installed
- Full-width GameConfigPanel layout
- Existing auto-save and toast behavior preserved

**Out of Scope (Future Stories):**
- Story 11.4 will move Mods under Game Server
- Story 11.5 will extract Console to full page
- Story 11.6 will clean up Dashboard
- No new settings or setting groups in this story
- No modifications to GameConfigPanel behavior

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- ✅ Task 1: Created SettingsPage component with page header ("Game Settings" title + ServerStatusBadge), full-width GameConfigPanel integration, loading/error states, and EmptyServerState for not_installed/installing states. 14 unit tests covering all behaviors.
- ✅ Task 2: Empty state already implemented as part of Task 1 (EmptyServerState inline component with ServerOff icon, message, and Link to /game-server/version). Tests already cover empty state rendering and link presence.
- ✅ Task 3: Integrated SettingsPage into App.tsx routing. Added export to game-server index.ts. Removed placeholder GameServerSettingsPage function and unused GameConfigPanel import. Existing Sidebar tests already verify route paths.
- ✅ Task 4: Verified auto-save and toast behavior unchanged. GameConfigPanel was NOT modified - SettingsPage simply wraps it. Existing GameConfigPanel tests (11 tests) verify API calls on blur and toast.success/toast.error are already implemented in the component (lines 163, 172).
- ✅ Task 5: Manual browser verification completed. All ACs verified. Ad-hoc fix: Added missing --success and --warning CSS theme colors (Catppuccin green/yellow) to fix ServerStatusBadge background coloring.

### File List

- web/src/features/game-server/SettingsPage.tsx (created)
- web/src/features/game-server/SettingsPage.test.tsx (created)
- web/src/features/game-server/index.ts (modified)
- web/src/App.tsx (modified)
- web/src/styles/index.css (modified - added success/warning theme colors)

### Change Log

- 2026-01-11: Story implementation complete. Created SettingsPage with full-width GameConfigPanel, server status header, and empty state for not_installed. Fixed pre-existing bug with missing success/warning CSS colors.
- 2026-01-11: Code review follow-ups addressed. Added route integration test, responsive padding test, installing state link test, aria-label for accessibility, and removed extra blank lines in App.tsx.

### CSS Theme Color Dependency Fix (Ad-hoc)

During manual browser verification, ServerStatusBadge background colors (success/warning states) were not rendering correctly. Investigation revealed that `--success` and `--warning` CSS custom properties were missing from the theme configuration.

**Root Cause:** The base CSS variables `--success`, `--success-foreground`, `--warning`, and `--warning-foreground` were not defined in the `:root` and `.dark` selectors, nor mapped in the `@theme inline` block.

**Fix Applied (web/src/styles/index.css):**
- Added Catppuccin Latte colors for light mode: `--success: #40a02b` (green), `--warning: #df8e1d` (yellow)
- Added Catppuccin Mocha colors for dark mode: `--success: #a6e3a1`, `--warning: #f9e2af`
- Added theme mappings: `--color-success`, `--color-success-foreground`, `--color-warning`, `--color-warning-foreground`

This was a pre-existing infrastructure gap that only became visible when ServerStatusBadge was rendered in a context requiring these colors. The fix is consistent with the existing Catppuccin theme palette.
