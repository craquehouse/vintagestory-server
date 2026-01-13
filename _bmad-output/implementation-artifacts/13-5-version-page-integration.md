# Story 13.5: Version Page Integration

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **administrator**,
I want **the version browser integrated into the Version page**,
So that **version management is a cohesive experience**.

## Acceptance Criteria

1. **Given** no server is installed
   **When** I view `/game-server/version`
   **Then** I see the version browser with "Install" buttons
   **And** page title is "Server Installation"

2. **Given** a server is installed
   **When** I view `/game-server/version`
   **Then** I see current version info at the top
   **And** I see "Change Version" section with the browser below
   **And** page title is "Server Version"

3. **Given** an update is available
   **When** I view the version page
   **Then** the newer version card is highlighted
   **And** an "Update Available" banner is shown

4. **Given** I want to quickly install the latest stable
   **When** I view the page
   **Then** there is a prominent "Install Latest Stable" button (if not installed)
   **Or** "Update to Latest" button (if installed and update available)

## Tasks / Subtasks

- [x] Task 1: Show version browser when not installed + tests (AC: 1)
  - [x] Subtask 1.1: Modify VersionPage to show VersionGrid when state is `not_installed`
  - [x] Subtask 1.2: Enable `useVersions` hook for not_installed state
  - [x] Subtask 1.3: Add InstallVersionDialog integration for not_installed flow
  - [x] Subtask 1.4: Write tests for not_installed version browser display

- [x] Task 2: Add "Install Latest Stable" quick action + tests (AC: 4)
  - [x] Subtask 2.1: Create QuickInstallButton component with loading state
  - [x] Subtask 2.2: Find latest stable version from versions list
  - [x] Subtask 2.3: Wire button to useInstallServer mutation
  - [x] Subtask 2.4: Show "Update to Latest" variant when installed with update available
  - [x] Subtask 2.5: Write tests for quick install button variants

- [x] Task 3: Add newer version highlighting + tests (AC: 3)
  - [x] Subtask 3.1: Add `isNewer` prop to VersionCard for highlight styling
  - [x] Subtask 3.2: Calculate which versions are newer than installed
  - [x] Subtask 3.3: Apply highlight border/glow to newer versions
  - [x] Subtask 3.4: Write tests for version highlighting logic

- [x] Task 4: Manual browser verification (AC: all)
  - [x] Subtask 4.1: Start dev servers (`just dev-api` and `just dev-web`)
  - [x] Subtask 4.2: Uninstall server (if needed) and verify version browser shows
  - [x] Subtask 4.3: Verify "Install Latest Stable" button works
  - [x] Subtask 4.4: Install a version and verify highlighting of newer versions
  - [x] Subtask 4.5: Verify "Update to Latest" button appears when update available

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Run `just test-web` to verify all web tests pass before marking task complete

**UI Stories - Manual Browser Verification:**

For stories with UI components, include manual browser verification. Task 4 covers this.

### Security Requirements

No special security considerations - uses existing authenticated API endpoints with Admin role requirement.

### Development Commands

```bash
just test-web                                    # Run all web tests
just test-web -- --testPathPattern="VersionPage" # Run VersionPage tests
just check                                       # Full validation
just dev-api                                     # Start API dev server
just dev-web                                     # Start web dev server
```

### Architecture & Patterns

**ADR-1 from Epic 13 Architecture: Simpler Than Mod Browser**

This story completes the version browser integration with the simplicity principle:
- No text search (version numbers are scannable)
- No pagination (small dataset)
- Channel filter only (already implemented in Story 13.3)
- Focus on quick actions and clear install flow

**ADR-4 from Epic 13 Architecture: TanStack Query Cache Sync**

After quick install, invalidate related queries (already implemented in useInstallServer hook).

### Current Implementation Status (from Stories 13.2-13.4)

| Feature | Status | Location |
|---------|--------|----------|
| VersionCard component | ✅ Done | `web/src/components/VersionCard.tsx` |
| VersionGrid component | ✅ Done | `web/src/components/VersionGrid.tsx` |
| ChannelFilter component | ✅ Done | `web/src/components/ChannelFilter.tsx` |
| InstallVersionDialog | ✅ Done | `web/src/components/InstallVersionDialog.tsx` |
| useVersions hook | ✅ Done | `web/src/hooks/use-versions.ts` |
| useInstallServer hook | ✅ Done | `web/src/hooks/use-server-status.ts` |
| Update Available banner | ✅ Done | VersionPage `UpdateAvailableBanner` |
| Dynamic page title | ✅ Done | VersionPage `pageTitle` logic |
| Installed state version browser | ✅ Done | VersionPage (Story 13.3) |

**What This Story Adds:**
- Version browser display for `not_installed` state (replacing ServerInstallCard text input)
- "Install Latest Stable" / "Update to Latest" quick action button
- Newer version highlighting on VersionCard

### Implementation Guide: Not-Installed Version Browser

**Current Flow (to replace):**
```tsx
// VersionPage.tsx - current not_installed behavior
{isInstalled ? (
  <>... version browser ...</>
) : (
  <ServerInstallCard ... />  // <-- REPLACE THIS with version browser
)}
```

**Target Flow:**
```tsx
// VersionPage.tsx - new not_installed behavior
{isInstalled ? (
  <>
    <InstalledVersionCard ... />
    <h2>Available Versions</h2>
    <VersionGrid ... />
  </>
) : (
  <>
    <QuickInstallButton versions={versions} />
    <h2>Available Versions</h2>
    <ChannelFilter ... />
    <VersionGrid versions={versions} onVersionClick={handleVersionClick} />
    <InstallVersionDialog ... installedVersion={null} />
  </>
)}
```

**Key Changes:**
1. Enable `useVersions` for not_installed state (currently `enabled: isInstalled`)
2. Show VersionGrid in both installed and not_installed states
3. Add QuickInstallButton above version list
4. Pass `installedVersion={null}` to dialog for fresh install flow

### Implementation Guide: Quick Install Button

**Component Props:**
```typescript
interface QuickInstallButtonProps {
  versions: VersionInfo[];
  installedVersion: string | null;
  isLoading: boolean;
  onInstallComplete?: () => void;
}
```

**Find Latest Stable:**
```typescript
const latestStable = versions.find(v => v.channel === 'stable' && v.isLatest);
```

**Button Variants:**

| Condition | Button Text | Style |
|-----------|-------------|-------|
| Not installed | "Install Latest Stable ({version})" | Primary/Default |
| Installed, update available | "Update to {version}" | Primary/Default |
| Installed, up to date | (don't show button) | - |
| Loading | "Installing..." with spinner | Disabled |

**Implementation:**
```tsx
function QuickInstallButton({ versions, installedVersion, isLoading }: QuickInstallButtonProps) {
  const latestStable = versions.find(v => v.channel === 'stable' && v.isLatest);
  const installMutation = useInstallServer();

  if (!latestStable) return null; // No versions available yet

  const hasUpdate = installedVersion && installedVersion !== latestStable.version;
  const showButton = !installedVersion || hasUpdate;

  if (!showButton) return null;

  const buttonText = installedVersion
    ? `Update to ${latestStable.version}`
    : `Install Latest Stable (${latestStable.version})`;

  const handleClick = () => {
    installMutation.mutate(latestStable.version, { force: !!installedVersion });
  };

  return (
    <Button
      size="lg"
      onClick={handleClick}
      disabled={isLoading || installMutation.isPending}
    >
      {installMutation.isPending ? (
        <>
          <Loader2 className="animate-spin" />
          Installing...
        </>
      ) : (
        <>
          <Download />
          {buttonText}
        </>
      )}
    </Button>
  );
}
```

### Implementation Guide: Version Highlighting

**VersionCard Enhancement:**

Add `isNewer` prop to show highlight when version is newer than installed:

```typescript
interface VersionCardProps {
  version: VersionInfo;
  installedVersion?: string | null;
  isNewer?: boolean;  // NEW: highlight this version
  onClick?: () => void;
}
```

**Highlighting Style:**
```tsx
<Card
  className={cn(
    'h-full',
    onClick && 'cursor-pointer hover:shadow-lg transition-shadow',
    isNewer && 'ring-2 ring-primary ring-offset-2'  // Highlight newer versions
  )}
  ...
>
```

**Calculate Newer Versions:**

In VersionPage or VersionGrid, determine which versions are newer:

```typescript
const isVersionNewer = (version: string, installedVersion: string | null): boolean => {
  if (!installedVersion) return false;
  // Simple string comparison works for semver-like versions (see Story 13.4 Dev Notes)
  return version > installedVersion;
};
```

**Pass to VersionGrid:**

Modify VersionGrid to accept and pass `isNewer` to each card:

```tsx
<VersionCard
  key={version.version}
  version={version}
  installedVersion={installedVersion}
  isNewer={installedVersion ? version.version > installedVersion : false}
  onClick={() => onVersionClick?.(version.version)}
/>
```

### Test Patterns

**VersionPage.test.tsx additions:**

```typescript
describe('not installed state', () => {
  it('shows version browser instead of ServerInstallCard', () => { ... });
  it('shows "Install Latest Stable" button', () => { ... });
  it('enables version selection from grid', () => { ... });
  it('opens InstallVersionDialog on card click', () => { ... });
});

describe('quick install button', () => {
  it('shows "Install Latest Stable" when not installed', () => { ... });
  it('shows "Update to {version}" when update available', () => { ... });
  it('hides button when up to date', () => { ... });
  it('disables button during installation', () => { ... });
});

describe('version highlighting', () => {
  it('highlights versions newer than installed', () => { ... });
  it('does not highlight installed version', () => { ... });
  it('does not highlight older versions', () => { ... });
  it('does not highlight any versions when not installed', () => { ... });
});
```

### Previous Story Intelligence

**From Story 13.4 (Install/Upgrade Flow):**
- InstallVersionDialog fully implemented with action type logic
- Force flag support for reinstall/upgrade/downgrade
- Auto-close dialog on successful install
- 1299 web tests passing as baseline
- Dialog integrates with VersionPage via selectedVersion state

**From Story 13.3 (Version List Page):**
- ChannelFilter component for channel selection
- VersionGrid displays versions in responsive grid
- useVersions hook with channel filter support
- InstalledVersionCard with UpdateAvailableBanner

**From Story 13.4 Completion Notes:**
- Force flag implementation: API accepts `force` param to overwrite existing
- Version comparison uses simple string comparison (acceptable per Dev Notes)
- Test count: 1299 web tests

### File Structure

**Files to modify:**
- `web/src/features/game-server/VersionPage.tsx` - Add not-installed browser, quick install button
- `web/src/features/game-server/VersionPage.test.tsx` - Add tests for new functionality
- `web/src/components/VersionCard.tsx` - Add isNewer highlighting prop
- `web/src/components/VersionCard.test.tsx` - Add tests for highlighting
- `web/src/components/VersionGrid.tsx` - Pass isNewer prop to cards
- `web/src/components/VersionGrid.test.tsx` - Add tests for highlighting pass-through

**Files to create:**
- `web/src/components/QuickInstallButton.tsx` - Quick action button component
- `web/src/components/QuickInstallButton.test.tsx` - Tests for quick install

**Files to reference (DO NOT modify):**
- `web/src/components/InstallVersionDialog.tsx` - Use existing dialog
- `web/src/components/ChannelFilter.tsx` - Use existing filter
- `web/src/hooks/use-server-status.ts` - useInstallServer hook
- `web/src/hooks/use-versions.ts` - useVersions hook

### Git Workflow

**Branch:** `story/13-5-version-page-integration`

**Commit Pattern:**
```
feat(story-13.5/task-1): show version browser when not installed
feat(story-13.5/task-2): add quick install button component
feat(story-13.5/task-3): add newer version highlighting
```

### References

- `project-context.md` - Critical implementation rules and patterns
- [Source: _bmad-output/planning-artifacts/architecture/epic-13-server-version-browser.md] - ADRs for Epic 13
- [Source: _bmad-output/planning-artifacts/epics.md#Story 13.5] - Story requirements
- [Source: web/src/features/game-server/VersionPage.tsx] - Current implementation
- [Source: _bmad-output/implementation-artifacts/13-4-install-upgrade-flow.md] - Previous story

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- **Task 1 Complete (2026-01-13):** Replaced ServerInstallCard with full version browser for not_installed state. Changes: enabled useVersions hook for not_installed state, added ChannelFilter + VersionGrid + InstallVersionDialog for fresh install flow. Tests: 27 VersionPage tests pass (5 new tests added for not_installed state).
- **Task 2 Complete (2026-01-13):** Added QuickInstallButton component for one-click install/update. Shows "Install Latest Stable" when not installed, "Update to {version}" when update available. Integrated into VersionPage. Tests: 9 QuickInstallButton tests + 3 VersionPage integration tests.
- **Task 3 Complete (2026-01-13):** Added newer version highlighting with ring styling. Added isNewer prop to VersionCard, VersionGrid calculates and passes isNewer based on version comparison. Tests: 4 VersionCard tests + 4 VersionGrid tests.
- **Task 4 Fix (2026-01-13):** Added confirmation dialog to QuickInstallButton when server is running. Shows warning that server will be stopped before proceeding with update. Tests: 5 new tests for confirmation behavior.

### File List

**Task 1:**

- `web/src/features/game-server/VersionPage.tsx` (modified) - Added version browser for not_installed state
- `web/src/features/game-server/VersionPage.test.tsx` (modified) - Added 5 tests for not_installed version browser

**Task 2:**

- `web/src/components/QuickInstallButton.tsx` (created) - Quick install/update button component
- `web/src/components/QuickInstallButton.test.tsx` (created) - 9 tests for button variants
- `web/src/features/game-server/VersionPage.tsx` (modified) - Integrated QuickInstallButton
- `web/src/features/game-server/VersionPage.test.tsx` (modified) - Added 3 integration tests

**Task 3:**

- `web/src/components/VersionCard.tsx` (modified) - Added isNewer prop with ring highlight styling
- `web/src/components/VersionCard.test.tsx` (modified) - Added 4 tests for highlighting
- `web/src/components/VersionGrid.tsx` (modified) - Calculate and pass isNewer to VersionCard
- `web/src/components/VersionGrid.test.tsx` (modified) - Added 4 tests for highlighting pass-through
