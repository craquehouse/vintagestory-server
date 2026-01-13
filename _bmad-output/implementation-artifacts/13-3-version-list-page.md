# Story 13.3: Version List Page

Status: done

## Story

As an **administrator**,
I want **a browsable list of server versions**,
So that **I can see all available versions and choose one to install**.

## Acceptance Criteria

1. **Given** I navigate to `/game-server/version`
   **When** a server is installed
   **Then** I see my current version prominently at the top
   **And** below I see "Available Versions" with the version list

2. **Given** I view the version list
   **When** it loads
   **Then** versions are grouped or filterable by channel (All, Stable, Unstable)
   **And** default filter is "All"

3. **Given** I select the "Stable" filter
   **When** the filter is applied
   **Then** only stable versions are displayed

4. **Given** versions are displayed
   **When** I view the list
   **Then** versions are sorted by version number (newest first)

5. **Given** I am viewing on mobile
   **When** the page loads
   **Then** the layout is responsive and cards stack appropriately

## Tasks / Subtasks

- [x] Task 1: Create VersionGrid component + tests (AC: 4, 5)
  - [x] Subtask 1.1: Create `web/src/components/VersionGrid.tsx`
  - [x] Subtask 1.2: Display VersionCards in responsive grid (reuse ModBrowseGrid patterns)
  - [x] Subtask 1.3: Add loading skeleton state
  - [x] Subtask 1.4: Add empty state ("No versions found")
  - [x] Subtask 1.5: Write unit tests for VersionGrid

- [x] Task 2: Create ChannelFilter component + tests (AC: 2, 3)
  - [x] Subtask 2.1: Create `web/src/components/ChannelFilter.tsx` using shadcn/ui Tabs
  - [x] Subtask 2.2: Implement "All", "Stable", "Unstable" tabs
  - [x] Subtask 2.3: Add onChange callback for filter selection
  - [x] Subtask 2.4: Write unit tests for ChannelFilter

- [x] Task 3: Update VersionPage with version list + tests (AC: 1, 2, 3, 4)
  - [x] Subtask 3.1: Modify `web/src/features/game-server/VersionPage.tsx`
  - [x] Subtask 3.2: Add "Available Versions" section below current version display
  - [x] Subtask 3.3: Integrate ChannelFilter for channel selection
  - [x] Subtask 3.4: Integrate VersionGrid to display filtered versions
  - [x] Subtask 3.5: Pass installed version to VersionCards for "Installed" badge
  - [x] Subtask 3.6: Pass onClick handler to VersionCards (prep for Story 13.4)
  - [x] Subtask 3.7: Update existing tests and add new tests for version list

- [x] Task 4: Manual browser verification (AC: all)
  - [x] Subtask 4.1: Start dev servers (`just dev-api` and `just dev-web`)
  - [x] Subtask 4.2: Navigate to `/game-server/version` in browser
  - [x] Subtask 4.3: Verify current version displays at top (if installed)
  - [x] Subtask 4.4: Verify version grid displays available versions
  - [x] Subtask 4.5: Test channel filter functionality (All/Stable/Unstable)
  - [x] Subtask 4.6: Test responsive layout on narrow viewport
  - [x] Subtask 4.7: Check for console errors or warnings

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Do not batch tests into a separate "Write tests" task at the end
- Run `just test-web` to verify all web tests pass before marking task complete

**UI Stories - Manual Browser Verification:**

For stories with UI components, include manual browser verification. Automated tests verify function; manual verification verifies UX and "feel."

### Security Requirements

No special security considerations for this story - version data is public, read-only metadata. Standard API authentication (Admin/Monitor roles) is already in place from Epic 2.

### Development Commands

Use `just` for all development tasks:
- `just test-web` - Run web tests
- `just test-web -- --testPathPattern="VersionGrid"` - Run specific tests
- `just check` - Full validation (lint + typecheck + test)
- `just dev-api` - Start API dev server
- `just dev-web` - Start web dev server

### Architecture & Patterns

**ADR-1 from Epic 13 Architecture: Simpler Than Mod Browser**

The version browser is intentionally simpler than the mod browser due to different characteristics:

| Characteristic | Mod Browser | Version Browser |
|---------------|-------------|-----------------|
| Dataset size | 1000+ mods | <20 versions |
| Search needed | Yes | No (scannable list) |
| Pagination | Required | Not needed |
| Filtering | Complex | Simple (channel only) |

**What NOT to implement (per ADR-1):**
- No text search (version numbers are easily scannable)
- No pagination (dataset is small enough to display all)
- No URL state for filters (too simple to warrant)
- No scroll restoration (no pagination to restore)

**ADR-5: Channel Filter as Tabs**

Use Tabs component (not FilterControls) for channel filter:

```typescript
<Tabs value={channel} onValueChange={setChannel}>
  <TabsList>
    <TabsTrigger value="all">All</TabsTrigger>
    <TabsTrigger value="stable">Stable</TabsTrigger>
    <TabsTrigger value="unstable">Unstable</TabsTrigger>
  </TabsList>
</Tabs>
```

**Why Tabs over FilterControls:** Only one filter dimension with 3 options - tabs provide better UX than collapsible filter sections.

### Component Patterns to Reuse

**From Story 13.2 (VersionCard):**
- `VersionCard` component - Already created, pass `installedVersion` prop
- `useVersions` hook - Already supports channel filter parameter
- `VersionInfo` type - Already defined in `web/src/api/types.ts`

**From ModBrowseGrid (pattern reference):**
- Responsive grid: `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4`
- Skeleton loading pattern (but simpler - no pagination)
- Empty state pattern

### API Response Structure

**GET /api/v1alpha1/versions?channel={channel}**

```typescript
interface VersionListResponse {
  versions: VersionInfo[];
  total: number;
  cached: boolean;
  cachedAt: string | null;
}
```

**Filtering is server-side:** Pass `channel` parameter to API, don't filter client-side. The `useVersions` hook already supports this:

```typescript
const { data, isLoading } = useVersions({ channel: 'stable' });
```

### VersionGrid Implementation Guide

**Grid Layout (responsive):**

```typescript
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
  {versions.map((version) => (
    <VersionCard
      key={version.version}
      version={version}
      installedVersion={serverStatus?.version}
      onClick={() => handleVersionClick(version.version)}
    />
  ))}
</div>
```

**Loading Skeleton:**

```typescript
// Simplified from ModBrowseGrid - no pagination controls needed
const skeletonCards = Array.from({ length: 8 }, (_, i) => (
  <Card key={i} className="h-[120px] animate-pulse bg-muted" />
));
```

**Empty State:**

```typescript
{versions.length === 0 && !isLoading && (
  <div className="text-center py-8 text-muted-foreground">
    No versions found for this channel.
  </div>
)}
```

### VersionPage Integration

**Existing structure to preserve:**

```
VersionPage
├── Loading state
├── Error state
├── Not installed state → ServerInstallCard (unchanged)
├── Installing state → ServerInstallCard with progress (unchanged)
└── Installed state → InstalledVersionCard (keep) + NEW: VersionList section
```

**New "Available Versions" section (add below InstalledVersionCard):**

```typescript
{isInstalled && (
  <>
    <InstalledVersionCard {...props} />

    {/* New: Available Versions Section */}
    <div className="mt-8">
      <h2 className="text-xl font-semibold mb-4">Available Versions</h2>
      <ChannelFilter value={channel} onChange={setChannel} />
      <VersionGrid
        channel={channel}
        installedVersion={serverStatus?.version}
        onVersionClick={handleVersionClick}
      />
    </div>
  </>
)}
```

### State Management

**Channel filter state:** Local component state (not TanStack Query)

```typescript
const [channel, setChannel] = useState<VersionChannel | undefined>(undefined);
// undefined = "All", 'stable' = Stable only, 'unstable' = Unstable only
```

**Version click handler:** Prepare for Story 13.4 (Install/Upgrade Flow)

```typescript
const handleVersionClick = (version: string) => {
  // Story 13.4 will add dialog/navigation
  console.log('Version clicked:', version);
};
```

### Test Patterns

**VersionGrid.test.tsx pattern:**

```typescript
describe('VersionGrid', () => {
  it('renders version cards in grid', () => { ... });
  it('shows loading skeleton when loading', () => { ... });
  it('shows empty state when no versions', () => { ... });
  it('passes installedVersion to VersionCards', () => { ... });
  it('calls onVersionClick when card clicked', () => { ... });
});
```

**ChannelFilter.test.tsx pattern:**

```typescript
describe('ChannelFilter', () => {
  it('renders All, Stable, Unstable tabs', () => { ... });
  it('calls onChange with channel on tab click', () => { ... });
  it('highlights selected tab', () => { ... });
});
```

**VersionPage.test.tsx additions:**

```typescript
describe('version list section (AC: 1, 2, 3, 4)', () => {
  it('shows Available Versions section when installed', () => { ... });
  it('renders ChannelFilter', () => { ... });
  it('renders VersionGrid with versions', () => { ... });
  it('filters by channel when tab clicked', () => { ... });
});
```

### Previous Story Intelligence

**From Story 13.2 (VersionCard):**
- VersionCard accepts `installedVersion` prop for "Installed" badge comparison
- Uses `onClick` prop for card click handling
- Test patterns established with `data-testid` conventions
- 37 tests added (12 hook, 22 component, 3 type transformation)

**From Story 13.1 (API):**
- `/api/v1alpha1/versions?channel={channel}` endpoint is ready
- `useVersions({ channel })` hook supports filtering
- Versions pre-sorted newest first by API

### File Structure

**Files to create:**
- `web/src/components/VersionGrid.tsx`
- `web/src/components/VersionGrid.test.tsx`
- `web/src/components/ChannelFilter.tsx`
- `web/src/components/ChannelFilter.test.tsx`

**Files to modify:**
- `web/src/features/game-server/VersionPage.tsx` - Add version list section
- `web/src/features/game-server/VersionPage.test.tsx` - Add version list tests

**Files to reference (DO NOT modify):**
- `web/src/components/VersionCard.tsx` - Reuse as-is
- `web/src/hooks/use-versions.ts` - Reuse as-is
- `web/src/components/ModBrowseGrid.tsx` - Pattern reference only

### Git Workflow

**Branch:** `story/13-3-version-list-page`

**Commit Pattern:**
```
feat(story-13.3/task-1): create VersionGrid component
feat(story-13.3/task-2): create ChannelFilter component
feat(story-13.3/task-3): add version list to VersionPage
```

### References

- `project-context.md` - Critical implementation rules and patterns
- [Source: _bmad-output/planning-artifacts/architecture/epic-13-server-version-browser.md] - ADRs for Epic 13
- [Source: web/src/components/VersionCard.tsx] - Card component to reuse
- [Source: web/src/hooks/use-versions.ts] - Hook to reuse
- [Source: web/src/features/mods/BrowseTab.tsx] - Complex browse pattern (reference only)
- [Source: _bmad-output/implementation-artifacts/13-2-version-card-component.md] - Previous story

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5

### Debug Log References

### Completion Notes List

- Task 1: Created VersionGrid component with responsive grid layout (1-4 columns), loading skeleton (8 cards), empty state, installedVersion prop for highlighting, and onVersionClick handler. 10 tests added covering all scenarios.
- Task 2: Created ChannelFilter component using shadcn/ui Tabs with All/Stable/Unstable options. Maps undefined to "all" for display, converts back on selection. 8 tests added.
- Task 3: Updated VersionPage to add "Available Versions" section below InstalledVersionCard when server is installed. Integrated ChannelFilter and VersionGrid components. 7 new tests added for version list functionality.
- Task 4: Manual browser verification completed by user. Stable channel filtering works correctly. Responsive layout verified. UX feedback captured to polish backlog (UI-033) suggesting table view may be better than cards for this small dataset.

### File List

- `web/src/components/VersionGrid.tsx` (created)
- `web/src/components/VersionGrid.test.tsx` (created)
- `web/src/components/ChannelFilter.tsx` (created)
- `web/src/components/ChannelFilter.test.tsx` (created)
- `web/src/features/game-server/VersionPage.tsx` (modified)
- `web/src/features/game-server/VersionPage.test.tsx` (modified)

### Change Log

- 2026-01-13: Task 1 complete - Created VersionGrid component with 10 tests
- 2026-01-13: Task 2 complete - Created ChannelFilter component with 8 tests
- 2026-01-13: Task 3 complete - Integrated version list into VersionPage with 7 new tests
- 2026-01-13: Task 4 complete - Manual verification done, UX feedback added to polish backlog (UI-033)
- 2026-01-13: Story 13.3 complete - All acceptance criteria met, all 1263 web tests passing
