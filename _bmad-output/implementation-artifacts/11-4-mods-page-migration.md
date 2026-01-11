# Story 11.4: Mods Page Migration

Status: in-progress

## Story

As an **administrator**,
I want **Mods accessible under Game Server navigation**,
So that **mod management is logically grouped with other server functions**.

## Acceptance Criteria

1. **Given** I navigate to `/game-server/mods` **When** the page loads **Then** I see the existing Mods interface (Installed/Browse tabs) **And** all existing mod functionality works as before

2. **Given** I navigate to the old `/mods` URL **When** the page loads **Then** I am redirected to `/game-server/mods`

3. **Given** I am on the mod detail page **When** I view the URL **Then** it is `/game-server/mods/browse/:slug`

4. **Given** no server is installed **When** I navigate to `/game-server/mods` **Then** I see a message indicating server must be installed first **And** compatibility checking is disabled (no game version to check against)

## Tasks / Subtasks

- [x] Task 1: Move mods routes under `/game-server/mods` + tests (AC: 1, 3)
  - [x] Update App.tsx: Move mods routes from top-level `/mods` to nested under `/game-server`
  - [x] Update ModsPage to work with new route structure (`/game-server/mods/*`)
  - [x] Update ModDetailPage breadcrumb links to use new paths
  - [x] Update handleBack navigation in ModDetailPage to use `/game-server/mods/browse`
  - [x] Add/update route tests to verify new paths render correctly

- [x] Task 2: Add redirects from old `/mods` routes + tests (AC: 2)
  - [x] Add `<Navigate to="/game-server/mods" replace />` for `/mods` route
  - [x] Add redirect for `/mods/installed` → `/game-server/mods/installed`
  - [x] Add redirect for `/mods/browse` → `/game-server/mods/browse`
  - [x] Add redirect for `/mods/browse/:slug` → `/game-server/mods/browse/:slug` (preserve params)
  - [x] Write tests verifying all redirects work correctly

- [x] Task 3: Update internal links throughout codebase + tests (AC: 1, 3)
  - [x] Update ModsPage tab navigation to use new paths (`/game-server/mods/installed`, `/game-server/mods/browse`)
  - [x] Update ModDetailPage breadcrumbs to use new paths
  - [x] Search for any other `/mods` links in components and update them (BrowseTab handleModClick)
  - [x] Write tests to verify internal navigation works

- [x] Task 4: Add empty state for no server installed + tests (AC: 4)
  - [x] In App.tsx GameServerModsPage (or new wrapper), check `serverStatus?.data?.state === 'not_installed'`
  - [x] Display EmptyServerState with message about server installation requirement
  - [x] Include note that compatibility checking is disabled without installed server
  - [x] Add link to `/game-server/version` (Installation page)
  - [x] Write tests for empty state rendering

- [x] Task 5: Remove top-level Mods from sidebar + tests (AC: 1)
  - [x] In Sidebar.tsx, remove "Mods" from `bottomNavItems` array (line 35)
  - [x] Verify Game Server > Mods sub-navigation item still works (already exists, line 56)
  - [x] Write tests verifying sidebar no longer shows top-level Mods

- [ ] Task 6: Manual browser verification (AC: all)
  - [ ] Start dev servers (`just dev-api` and `just dev-web`)
  - [ ] Navigate directly to `/game-server/mods` - verify Installed/Browse tabs work
  - [ ] Navigate to old `/mods` - verify redirect to `/game-server/mods`
  - [ ] Click through to a mod detail page - verify URL is `/game-server/mods/browse/:slug`
  - [ ] Verify breadcrumbs show correct path (Mods > Browse > ModName)
  - [ ] Test "Back to Browse" button navigates correctly
  - [ ] Verify sidebar shows Mods under Game Server, not as top-level item
  - [ ] Test with server not installed - verify empty state
  - [ ] Check for console errors or warnings

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

No security considerations for this story - UI-only route migration using existing authenticated API.

### Development Commands

Use `just` for all development tasks:
- `just test` - Run all tests
- `just test-web` - Run frontend tests only
- `just check` - Full validation (lint + typecheck + test)
- `just lint` - Run all linters
- `just dev-web` - Start web dev server
- `just dev-api` - Start API dev server

### Architecture & Patterns

**Current Route Structure (Before):**
```
/                         → Dashboard
/game-server/             → GameServerLayout
/game-server/version      → VersionPage
/game-server/settings     → SettingsPage
/game-server/mods         → Placeholder (GameServerModsPage)
/game-server/console      → ConsolePage
/mods                     → ModsPage (TOP-LEVEL)
/mods/installed           → InstalledTab
/mods/browse              → BrowseTab
/mods/browse/:slug        → ModDetailPage
/config                   → SettingsPage (VSManager)
```

**Target Route Structure (After):**
```
/                                → Dashboard
/game-server/                    → GameServerLayout
/game-server/version             → VersionPage
/game-server/settings            → SettingsPage
/game-server/mods                → ModsPage (MOVED HERE)
/game-server/mods/installed      → InstalledTab
/game-server/mods/browse         → BrowseTab
/game-server/mods/browse/:slug   → ModDetailPage
/game-server/console             → ConsolePage
/mods                            → REDIRECT → /game-server/mods
/mods/*                          → REDIRECT preserving path
/config                          → SettingsPage (VSManager)
```

**Existing Components to Reuse:**

| Component | Location | Purpose |
|-----------|----------|---------|
| ModsPage | `web/src/features/mods/ModsPage.tsx` | Tab container with Installed/Browse tabs |
| InstalledTab | `web/src/features/mods/InstalledTab.tsx` | Mod management with ModTable |
| BrowseTab | `web/src/features/mods/BrowseTab.tsx` | Mod discovery interface |
| ModDetailPage | `web/src/features/mods/ModDetailPage.tsx` | Full mod detail view with install |
| useServerStatus | `web/src/hooks/use-server-status.ts` | Server status hook for empty state |
| EmptyServerState pattern | `web/src/features/game-server/SettingsPage.tsx` | Template for server-not-installed state |

**Files That Need URL Updates:**

1. **ModsPage.tsx** (line 44): Updates tab navigation paths
   ```typescript
   // BEFORE
   navigate(`/mods/${value}`);
   // AFTER
   navigate(`/game-server/mods/${value}`);
   ```

2. **ModsPage.tsx** (line 22-27): Updates getActiveTab() path parsing
   ```typescript
   // Need to handle /game-server/mods/installed vs /game-server/mods/browse
   ```

3. **ModDetailPage.tsx** (line 334): Updates fallback navigation
   ```typescript
   // BEFORE
   navigate('/mods/browse');
   // AFTER
   navigate('/game-server/mods/browse');
   ```

4. **ModDetailPage.tsx** (lines 389-404): Updates breadcrumb links
   ```typescript
   // BEFORE
   <Link to="/mods">Mods</Link>
   <Link to="/mods/browse">Browse</Link>
   // AFTER
   <Link to="/game-server/mods">Mods</Link>
   <Link to="/game-server/mods/browse">Browse</Link>
   ```

5. **Sidebar.tsx** (line 35): Remove top-level Mods
   ```typescript
   // BEFORE
   const bottomNavItems = [
     { to: "/mods", icon: Package, label: "Mods" },
     { to: "/config", icon: Settings, label: "VSManager" },
   ];
   // AFTER
   const bottomNavItems = [
     { to: "/config", icon: Settings, label: "VSManager" },
   ];
   ```

### Redirect Pattern for Preserving Params

For redirecting `/mods/browse/:slug` to `/game-server/mods/browse/:slug`, use React Router's Navigate with path matching:

```tsx
// Option 1: Use splat route for all /mods/* paths
<Route path="/mods/*" element={<ModsRedirect />} />

// ModsRedirect component:
function ModsRedirect() {
  const location = useLocation();
  // Extract the path after /mods and append to new base
  const newPath = location.pathname.replace(/^\/mods/, '/game-server/mods');
  return <Navigate to={newPath} replace />;
}
```

### Empty State Pattern (from Story 11.3)

```tsx
// Check server status for empty state
const { data: statusResponse } = useServerStatus();
const serverState = statusResponse?.data?.state;

if (serverState === 'not_installed') {
  return (
    <div className="flex flex-col items-center justify-center h-64 text-center">
      <ServerOff className="h-12 w-12 text-muted-foreground mb-4" />
      <p className="text-lg font-medium">Server Not Installed</p>
      <p className="text-muted-foreground mb-4">
        Install a VintageStory server to manage mods. Compatibility checking requires
        a server version to compare against.
      </p>
      <Link to="/game-server/version">
        <Button variant="default">Go to Installation</Button>
      </Link>
    </div>
  );
}
```

### Project Structure Notes

**No new files needed** - this story moves existing routes and updates paths.

**Modified Files:**
- `web/src/App.tsx` - Route restructure + redirects + placeholder removal
- `web/src/features/mods/ModsPage.tsx` - Update navigation paths
- `web/src/features/mods/ModDetailPage.tsx` - Update breadcrumbs and back navigation
- `web/src/components/layout/Sidebar.tsx` - Remove top-level Mods nav item
- `web/src/features/mods/ModsPage.test.tsx` - Update route expectations
- `web/src/features/mods/ModDetailPage.test.tsx` - Update route expectations
- `web/src/components/layout/Sidebar.test.tsx` - Update nav item expectations

### Previous Story Intelligence (Story 11.1, 11.2, 11.3)

**Key Learnings from Story 11.1:**
- Sub-navigation under Game Server already exists and works
- `/game-server/mods` route already exists with placeholder (GameServerModsPage)
- ExpandableNavItem component handles sub-navigation rendering

**Key Learnings from Story 11.2:**
- Empty state pattern for `not_installed` server state
- Link to `/game-server/version` for installation redirect

**Key Learnings from Story 11.3:**
- Page wrapper pattern with useServerStatus for empty state check
- EmptyServerState inline component pattern
- Pattern for replacing placeholder pages with actual implementations

**Code Patterns Established:**
- Check `serverStatus?.data?.state === 'not_installed'` for empty state
- Use `<Navigate to="..." replace />` for redirects
- Use `Link` from react-router for internal navigation
- Page containers use `data-testid` attributes for testing

### Git Commit Pattern

Follow the established commit pattern:
```
feat(story-11.4/task-N): description
```

**Examples:**
- `feat(story-11.4/task-1): move mods routes under /game-server/mods`
- `feat(story-11.4/task-2): add redirects from old /mods routes`
- `feat(story-11.4/task-3): update internal mods links to new paths`
- `feat(story-11.4/task-4): add empty state for no server installed`
- `feat(story-11.4/task-5): remove top-level Mods from sidebar`

### References

- `project-context.md` - Critical implementation rules and patterns
- [App.tsx](web/src/App.tsx) - Current routing structure (lines 58-74)
- [ModsPage.tsx](web/src/features/mods/ModsPage.tsx) - Tab navigation to update
- [ModDetailPage.tsx](web/src/features/mods/ModDetailPage.tsx) - Breadcrumbs and back nav to update
- [Sidebar.tsx](web/src/components/layout/Sidebar.tsx) - Remove top-level Mods (line 35)
- [Story 11.3](11-3-settings-page-extraction.md) - Empty state pattern reference
- [Epic 11 in epics.md](_bmad-output/planning-artifacts/epics.md) - Full epic context

### Scope Boundaries

**In Scope (This Story):**
- Move mods routes under `/game-server/mods`
- Add redirects from old `/mods` routes
- Update all internal links to mods pages
- Update breadcrumbs in mod detail page
- Add empty state for no server installed
- Remove top-level Mods from sidebar

**Out of Scope (Future Stories):**
- Story 11.5 will extract Console to full page
- Story 11.6 will clean up Dashboard
- No changes to mod functionality itself
- No changes to mod API endpoints
- No modifications to ModTable, InstalledTab, or BrowseTab behavior

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
