# Story 11.1: Sub-Navigation Infrastructure

Status: complete

## Story

As a **frontend developer**,
I want **an expandable sub-navigation component in the sidebar**,
So that **Game Server can have nested navigation items**.

## Acceptance Criteria

1. **Given** I view the sidebar **When** I click on "Game Server" **Then** the section expands to show sub-items: Version/Installation, Settings, Mods, Console **And** the expanded/collapsed state is persisted in localStorage

2. **Given** the Game Server section is expanded **When** I click on "Game Server" again **Then** the section collapses to hide sub-items

3. **Given** I am on a Game Server sub-page (e.g., `/game-server/console`) **When** I view the sidebar **Then** the Game Server section is automatically expanded **And** the active sub-item is highlighted

4. **Given** no server is installed **When** I view the sidebar **Then** the first sub-item shows "Installation"

5. **Given** a server is installed **When** I view the sidebar **Then** the first sub-item shows "Version"

6. **Given** the sidebar is in collapsed mode (icons only) **When** I hover over the Game Server icon **Then** a tooltip/flyout shows the sub-navigation items

## Tasks / Subtasks

- [x] Task 1: Create ExpandableNavItem component with expand/collapse behavior + tests (AC: 1, 2)
  - [x] Create `web/src/components/layout/ExpandableNavItem.tsx` component
  - [x] Implement expand/collapse toggle with chevron indicator
  - [x] Add smooth CSS transition for expand/collapse animation
  - [x] Write unit tests for expand/collapse behavior

- [x] Task 2: Add expanded state persistence via PreferencesContext + tests (AC: 1)
  - [x] Extend `UserPreferences` interface with `gameServerNavExpanded: boolean`
  - [x] Add `setGameServerNavExpanded` to PreferencesContext
  - [x] Update `DEFAULT_PREFERENCES` with new field (default: true)
  - [x] Write tests for persistence behavior

- [x] Task 3: Update Sidebar.tsx with expandable Game Server navigation + tests (AC: 1, 2, 3, 4, 5)
  - [x] Replace static Game Server nav item with ExpandableNavItem
  - [x] Add sub-navigation items: Version/Installation, Settings, Mods, Console
  - [x] Implement dynamic label (Installation/Version) based on `useServerStatus`
  - [x] Auto-expand when on any `/game-server/*` route using `useLocation`
  - [x] Highlight active sub-item using `NavLink` active state
  - [x] Update existing Sidebar tests for new navigation structure

- [x] Task 4: Update routes in App.tsx for nested Game Server routing + tests (AC: 3)
  - [x] Add nested routes under `/game-server` path
  - [x] Add placeholder pages for: `/game-server/version`, `/game-server/settings`, `/game-server/mods`, `/game-server/console`
  - [x] Add redirect from `/game-server` to `/game-server/console` (changed from version per route logic)
  - [x] Write integration tests for route structure

- [x] Task 5: Handle collapsed sidebar hover behavior + tests (AC: 6)
  - [x] Create flyout/tooltip component for collapsed state
  - [x] Show sub-navigation items on hover when sidebar is collapsed
  - [x] Ensure flyout items are clickable and navigate correctly
  - [x] Write tests for collapsed sidebar hover interaction

- [x] Task 6: Manual browser verification (AC: all)
  - [x] Start dev servers (`just dev-api` and `just dev-web`)
  - [x] Test expand/collapse in expanded sidebar mode
  - [x] Verify persistence across page refreshes
  - [x] Test dynamic Installation/Version label toggle
  - [x] Test collapsed sidebar hover flyout
  - [x] Check for console errors or warnings

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Do not batch tests into a separate "Write tests" task at the end
- Run `just test` to verify all tests pass before marking task complete

### Architecture & Patterns

**Existing Component Patterns:**
- [Sidebar.tsx](web/src/components/layout/Sidebar.tsx) - Current flat navigation structure
- [SidebarContext.tsx](web/src/contexts/SidebarContext.tsx) - Collapsed/mobile state management
- [PreferencesContext.tsx](web/src/contexts/PreferencesContext.tsx) - Cookie-persisted user preferences

**State Management Pattern:**
- Use `PreferencesContext` for persisting expanded state (cookie-based, same as `sidebarCollapsed`)
- Use `useServerStatus` hook for dynamic label logic (`state === 'not_installed'` → "Installation", else "Version")
- Use React Router's `useLocation` for route-aware auto-expansion

**Sub-Navigation Items:**
```typescript
const gameServerSubItems = [
  { to: "/game-server/version", icon: HardDrive, label: "Version", dynamicLabel: true },
  { to: "/game-server/settings", icon: Settings2, label: "Settings" },
  { to: "/game-server/mods", icon: Package, label: "Mods" },
  { to: "/game-server/console", icon: Terminal, label: "Console" },
];
```

**Dynamic Label Logic:**
```typescript
// In ExpandableNavItem or Sidebar
const { data: statusResponse } = useServerStatus();
const serverState = statusResponse?.data?.state;
const versionLabel = serverState === 'not_installed' ? 'Installation' : 'Version';
```

**Icon Suggestions (from lucide-react):**
- Version/Installation: `HardDrive` or `Download`
- Settings: `Settings2` (to differentiate from top-level VSManager)
- Mods: `Package` (same as current)
- Console: `Terminal` (same as current Game Server icon)
- Game Server parent: `Server` or `Gamepad2`
- Chevron: `ChevronDown` / `ChevronRight` for expand/collapse indicator

**Flyout Pattern (collapsed sidebar):**
- Use Radix UI's `HoverCard` or shadcn's `Popover` with hover trigger
- Position flyout to the right of the sidebar (side="right")
- Ensure flyout content is interactive (not just tooltip text)

### File Structure

**New Files:**
- `web/src/components/layout/ExpandableNavItem.tsx` - Expandable nav component
- `web/src/components/layout/ExpandableNavItem.test.tsx` - Tests

**Modified Files:**
- `web/src/components/layout/Sidebar.tsx` - Add expandable section
- `web/src/components/layout/Sidebar.test.tsx` - Update tests
- `web/src/contexts/PreferencesContext.tsx` - Add expanded state
- `web/src/contexts/PreferencesContext.test.tsx` - Add tests for new preference
- `web/src/App.tsx` - Add nested routes

**Placeholder Pages (minimal, will be implemented in subsequent stories):**
- `web/src/features/game-server/VersionPage.tsx` - Placeholder for Story 11.2
- `web/src/features/game-server/SettingsPage.tsx` - Placeholder for Story 11.3
- `web/src/features/game-server/ConsolePage.tsx` - Placeholder for Story 11.5

### CSS Transition Pattern

Use Tailwind's transition utilities for smooth expand/collapse:
```tsx
<div className={cn(
  "overflow-hidden transition-all duration-200 ease-in-out",
  isExpanded ? "max-h-40 opacity-100" : "max-h-0 opacity-0"
)}>
  {/* Sub-items */}
</div>
```

### Route Structure

Current:
```
/              → Dashboard
/game-server   → GameServerPage (single page)
/mods/*        → ModsPage with nested routes
/config        → SettingsPage
```

Target (after this story + subsequent stories):
```
/                      → Dashboard
/game-server           → Redirect to /game-server/version
/game-server/version   → VersionPage (Story 11.2)
/game-server/settings  → SettingsPage (Story 11.3)
/game-server/mods/*    → ModsPage (Story 11.4)
/game-server/console   → ConsolePage (Story 11.5)
/config                → SettingsPage (renamed to VSManager in sidebar)
```

**For this story:** Create placeholder pages that render minimal content (e.g., "Version page coming soon"). Actual page implementations are in Stories 11.2-11.5.

### Security Requirements

No security considerations for this story - UI-only navigation refactor.

### Development Commands

Use `just` for all development tasks:
- `just test` - Run all tests
- `just test-web` - Run frontend tests only
- `just check` - Full validation (lint + typecheck + test)
- `just lint` - Run all linters
- `just dev-web` - Start web dev server

### References

- `project-context.md` - Critical implementation rules and patterns
- [Sidebar.tsx](web/src/components/layout/Sidebar.tsx) - Current sidebar implementation
- [PreferencesContext.tsx](web/src/contexts/PreferencesContext.tsx) - Preferences persistence pattern
- [SidebarContext.tsx](web/src/contexts/SidebarContext.tsx) - Collapsed state management
- [App.tsx](web/src/App.tsx) - Current route structure
- [Epic 11 in epics.md](_bmad-output/planning-artifacts/epics.md) - Full epic context
- [Lucide Icons](https://lucide.dev/icons/) - Icon reference

### Anti-Patterns to Avoid

| Avoid | Do Instead |
|-------|------------|
| Creating new context for expanded state | Use existing PreferencesContext |
| Using localStorage directly in component | Use PreferencesContext (cookie-based) |
| Hardcoding "Version"/"Installation" labels | Derive from useServerStatus |
| Separate "Write tests" task | Tests included in each task |
| Complex nested routing before needed | Simple placeholders for future pages |

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

None

### Completion Notes List

- Created ExpandableNavItem component with expand/collapse toggle, CSS transitions, and auto-expand on route match
- Extended PreferencesContext with `gameServerNavExpanded` preference (cookie-persisted)
- Updated Sidebar to use ExpandableNavItem with Game Server sub-items (Version, Settings, Mods, Console)
- Added nested routes in App.tsx with placeholder page components
- Implemented collapsed sidebar flyout using Radix UI Tooltip with clickable NavLinks
- All 1133 tests pass, lint and typecheck pass
- Manual browser verification confirmed all functionality works correctly

### File List

**New Files:**
- `web/src/components/layout/ExpandableNavItem.tsx` - Expandable navigation component
- `web/src/components/layout/ExpandableNavItem.test.tsx` - 21 unit tests

**Modified Files:**
- `web/src/contexts/PreferencesContext.tsx` - Added gameServerNavExpanded preference
- `web/src/contexts/PreferencesContext.test.tsx` - Added preference tests
- `web/src/components/layout/Sidebar.tsx` - Integrated ExpandableNavItem
- `web/src/components/layout/Sidebar.test.tsx` - Updated for new navigation structure
- `web/src/App.tsx` - Added nested Game Server routes with placeholder pages
