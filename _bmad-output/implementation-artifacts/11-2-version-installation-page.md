# Story 11.2: Version/Installation Page

Status: ready-for-dev

## Story

As an **administrator**,
I want **a dedicated page for server version management**,
So that **I can see and manage which server version is installed**.

## Acceptance Criteria

1. **Given** no server is installed **When** I navigate to `/game-server/version` **Then** I see the installation interface (version input + install button) **And** the page title is "Server Installation"

2. **Given** a server is installed **When** I navigate to `/game-server/version` **Then** I see the current installed version prominently displayed **And** I see server state (running/stopped) **And** the page title is "Server Version"

3. **Given** server installation is in progress **When** I view the page **Then** I see installation progress (stage + percentage) **And** the install button is disabled

4. **Given** a newer version is available **When** I view the page (server installed) **Then** I see an "Update Available" indicator **And** I can see the new version number

5. **Given** I am on the version page **When** the page loads **Then** the ServerInstallCard logic from Dashboard is reused/moved here

## Tasks / Subtasks

- [ ] Task 1: Create VersionPage component with conditional rendering + tests (AC: 1, 2, 5)
  - [ ] Create `web/src/features/game-server/VersionPage.tsx`
  - [ ] Implement conditional rendering based on server state (`not_installed` vs installed)
  - [ ] Extract and reuse ServerInstallCard component (keep in components/)
  - [ ] Add dynamic page title ("Server Installation" vs "Server Version")
  - [ ] Write unit tests for both states

- [ ] Task 2: Add installed version display with server status + tests (AC: 2)
  - [ ] Create InstalledVersionCard component showing current version
  - [ ] Display server state badge (running/stopped) using existing ServerStatusBadge
  - [ ] Add version number prominently displayed
  - [ ] Write tests for version display with different states

- [ ] Task 3: Add installation progress display + tests (AC: 3)
  - [ ] Reuse InstallProgress component from ServerInstallCard
  - [ ] Ensure install button is disabled during installation
  - [ ] Show progress percentage and stage
  - [ ] Write tests for installation progress states

- [ ] Task 4: Add update available indicator + tests (AC: 4)
  - [ ] Compare `version` with `availableStableVersion` from ServerStatus
  - [ ] Create UpdateAvailableBanner component
  - [ ] Show "Update Available: X.X.X" when newer version exists
  - [ ] Write tests for update available detection and display

- [ ] Task 5: Update App.tsx routing and integrate page + tests (AC: all)
  - [ ] Replace placeholder `GameServerVersionPage` with actual VersionPage
  - [ ] Verify route `/game-server/version` works correctly
  - [ ] Write integration tests for routing

- [ ] Task 6: Manual browser verification (AC: all)
  - [ ] Start dev servers (`just dev-api` and `just dev-web`)
  - [ ] Test not_installed state → shows ServerInstallCard, title "Server Installation"
  - [ ] Test installed state → shows version info, title "Server Version"
  - [ ] Test installing state → shows progress, disabled inputs
  - [ ] Test update available indicator (if cached versions differ)
  - [ ] Check for console errors or warnings

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
| ServerInstallCard | `web/src/components/ServerInstallCard.tsx` | Installation interface with version input |
| ServerStatusBadge | `web/src/components/ServerStatusBadge.tsx` | Server state badge (running/stopped) |
| useServerStatus | `web/src/hooks/use-server-status.ts` | Fetches server status with polling |
| useInstallStatus | `web/src/hooks/use-server-status.ts` | Fetches installation progress |

**Data Available from useServerStatus:**
```typescript
interface ServerStatus {
  state: ServerState; // 'not_installed' | 'installing' | 'installed' | 'starting' | 'running' | 'stopping'
  version: string | null; // Current installed version (e.g., "1.21.6")
  uptimeSeconds: number | null;
  lastExitCode: number | null;
  availableStableVersion: string | null; // Latest stable version from cache
  availableUnstableVersion: string | null; // Latest unstable version from cache
  versionLastChecked: string | null;
  diskSpace: DiskSpaceData | null;
}
```

**Update Available Logic:**
```typescript
// Story 8.2 added version cache fields
const hasUpdate = serverStatus.version &&
  serverStatus.availableStableVersion &&
  serverStatus.version !== serverStatus.availableStableVersion;
```

**Page Title Pattern (matches existing pages):**
```tsx
<h1 className="text-2xl font-bold">
  {serverState === 'not_installed' ? 'Server Installation' : 'Server Version'}
</h1>
```

### File Structure

**New Files:**
- `web/src/features/game-server/VersionPage.tsx` - Main page component
- `web/src/features/game-server/VersionPage.test.tsx` - Tests
- `web/src/features/game-server/InstalledVersionCard.tsx` - Version display component (optional - can inline if simple)
- `web/src/features/game-server/UpdateAvailableBanner.tsx` - Update notification component

**Modified Files:**
- `web/src/App.tsx` - Replace placeholder with VersionPage import
- `web/src/features/game-server/index.ts` - Export new component

**Keep Unchanged:**
- `web/src/components/ServerInstallCard.tsx` - Reuse as-is (do NOT move or modify)
- Dashboard.tsx continues to render ServerInstallCard when appropriate

### Component Structure

```
VersionPage
├── (not_installed) → ServerInstallCard
├── (installing) → ServerInstallCard with progress
└── (installed)
    ├── InstalledVersionCard
    │   ├── Version number
    │   ├── ServerStatusBadge
    │   └── UpdateAvailableBanner (if newer version)
    └── (future: Change Version section for Epic 13)
```

### Anti-Patterns to Avoid

| Avoid | Do Instead |
|-------|------------|
| Moving ServerInstallCard to features/game-server | Keep in components/, import from there |
| Duplicating ServerInstallCard code | Import and reuse the existing component |
| Creating new hooks for status | Use existing useServerStatus, useInstallStatus |
| Hardcoding version comparison logic | Use availableStableVersion from API response |
| Adding complex upgrade/downgrade logic | That's Epic 13 - keep this story simple |

### Security Requirements

No security considerations for this story - UI-only page refactor using existing authenticated API.

### Development Commands

Use `just` for all development tasks:
- `just test` - Run all tests
- `just test-web` - Run frontend tests only
- `just check` - Full validation (lint + typecheck + test)
- `just lint` - Run all linters
- `just dev-web` - Start web dev server
- `just dev-api` - Start API dev server

### Previous Story Intelligence (Story 11.1)

**Key Learnings:**
- Placeholder pages were created in App.tsx - now replace with actual implementations
- Route structure established: `/game-server/version` already exists
- ExpandableNavItem with dynamic label ("Installation"/"Version") is controlled by useServerStatus

**Code Patterns Established:**
- Feature pages go in `web/src/features/game-server/`
- Use `data-testid` attributes for testing
- Use existing shadcn/ui Card components for consistent styling
- Follow existing padding patterns (`p-4` for page containers)

**Files Created in 11.1 Relevant to This Story:**
- Route `/game-server/version` with placeholder `GameServerVersionPage`
- Dynamic sidebar label logic using `useServerStatus`

### References

- `project-context.md` - Critical implementation rules and patterns
- [ServerInstallCard.tsx](web/src/components/ServerInstallCard.tsx) - Existing installation component
- [Dashboard.tsx](web/src/features/dashboard/Dashboard.tsx) - Current usage of ServerInstallCard
- [use-server-status.ts](web/src/hooks/use-server-status.ts) - Server status hooks
- [App.tsx](web/src/App.tsx) - Current routing with placeholder
- [Epic 11 in epics.md](_bmad-output/planning-artifacts/epics.md) - Full epic context
- [Story 11.1](11-1-sub-navigation-infrastructure.md) - Previous story in epic

### Scope Boundaries

**In Scope (This Story):**
- Display installed version with status badge
- Show ServerInstallCard for not_installed/installing states
- Display "Update Available" indicator when newer version cached
- Basic version page layout

**Out of Scope (Future Stories):**
- Epic 13 will add version browser with install/upgrade/downgrade
- Story 11.6 will clean up Dashboard (remove install from there)
- Version history or changelog display
- Multiple version installation support

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
