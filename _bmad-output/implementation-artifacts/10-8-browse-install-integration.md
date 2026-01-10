# Story 10.8: Browse Install Integration

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **administrator**,
I want **to install mods directly from the browse results or detail view**,
So that **discovery and installation is a seamless experience without switching tabs**.

## Acceptance Criteria

1. **Given** I am viewing a mod card or detail view
   **When** I click "Install"
   **Then** an install confirmation dialog appears
   *(Covers FR83)*

2. **Given** the install dialog is open
   **When** I view the dialog
   **Then** I see the compatibility check result (Compatible/Not verified/Incompatible)
   **And** a warning is shown if not verified or incompatible
   *(Covers FR84)*

3. **Given** I confirm installation
   **When** the install completes successfully
   **Then** a success toast appears
   **And** the mod card/detail updates to show "Installed"
   **And** the mod appears in the Installed tab
   *(Covers FR85)*

4. **Given** installation fails
   **When** the error occurs
   **Then** a clear error message is displayed
   **And** the install button returns to its original state

## Tasks / Subtasks

<!--
CRITICAL TASK STRUCTURE RULES:
1. Each functional task MUST include "+ tests" in its name
2. Do NOT create separate "Write tests" tasks at the end
3. A task is NOT complete until its tests pass
4. Tests verify the specific AC listed for that task
-->

- [x] Task 1: Create InstallConfirmDialog component + tests (AC: 1, 2)
  - [x] Subtask 1.1: Create dialog structure with shadcn Dialog component
  - [x] Subtask 1.2: Display mod name, version, and CompatibilityBadge
  - [x] Subtask 1.3: Add warning message for not_verified/incompatible mods
  - [x] Subtask 1.4: Implement Install/Cancel buttons with loading state
  - [x] Subtask 1.5: Write tests for dialog rendering, states, and interactions

- [x] Task 2: Add Install button to ModCard + tests (AC: 1, 3, 4)
  - [x] Subtask 2.1: Add Install button to ModCard component
  - [x] Subtask 2.2: Show "Installed" indicator when mod already installed
  - [x] Subtask 2.3: Integrate InstallConfirmDialog trigger
  - [x] Subtask 2.4: Handle install success/error with toast notifications
  - [x] Subtask 2.5: Write tests for card install button states and interactions

- [x] Task 3: Enhance ModDetailPage install section + tests (AC: 1, 3, 4)
  - [x] Subtask 3.1: Replace direct install with InstallConfirmDialog
  - [x] Subtask 3.2: Show confirmation before install/update actions
  - [x] Subtask 3.3: Update UI state after successful install
  - [x] Subtask 3.4: Write tests for detail page install flow

- [x] Task 4: Implement cross-tab state synchronization + tests (AC: 3)
  - [x] Subtask 4.1: Verify TanStack Query cache invalidation propagates to Installed tab
  - [x] Subtask 4.2: Test mod appears in Installed tab after browse install
  - [x] Subtask 4.3: Write integration tests for cross-tab synchronization

### Review Follow-ups (AI-Review)

- [ ] [AI-Review][HIGH] Add tracking issue comment to eslint-disable in TerminalView.tsx:123 or properly list dependencies
- [ ] [AI-Review][MEDIUM] Refactor BrowseTab.tsx installedSlugs Set construction to use Set constructor with map
- [ ] [AI-Review][MEDIUM] Propagate onModInstalled callback in BrowseTab.tsx or remove unused prop from ModBrowseGrid
- [ ] [AI-Review][LOW] Update test count documentation from ~750 to 1105 tests
- [ ] [AI-Review][LOW] Extract 'latest' string constant in ModCard.tsx for version handling

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Do not batch tests into a separate "Write tests" task at the end
- Run `just test` to verify all tests pass before marking task complete

### Security Requirements

**Follow patterns in `project-context.md` -> Security Patterns section:**

- Both Admin and Monitor roles can view browse content (read-only)
- Install action requires Admin role (existing `useInstallMod` enforces this)
- No sensitive data exposure in confirmation dialog
- Use existing API client with auth headers

### Development Commands

Use `just` for all development tasks:
- `just test` - Run all tests
- `just test-web` - Run web tests only
- `just test-web InstallConfirmDialog` - Run specific test file
- `just check` - Full validation (lint + typecheck + test)
- `just lint` - Run all linters

### Architecture & Patterns

**Existing Install Infrastructure:**

The install mutation hook already exists and handles all API communication:

```typescript
// From web/src/hooks/use-mods.ts
export function useInstallMod() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ slug, version }: { slug: string; version?: string }) =>
      installMod(slug, version),
    onSuccess: () => {
      // Refetch mods list to include the new mod
      queryClient.invalidateQueries({ queryKey: queryKeys.mods.all });
    },
  });
}
```

The `queryClient.invalidateQueries` call automatically updates all components using `useMods()`, including the Installed tab's ModTable.

**Existing Components to Reuse:**

1. **CompatibilityBadge** - Already renders compatibility status with correct styling
   - Located: `web/src/components/CompatibilityBadge.tsx`
   - Props: `status: CompatibilityStatus, message?: string`

2. **Dialog** - shadcn/ui dialog component
   - Located: `web/src/components/ui/dialog.tsx`
   - Pattern: `<Dialog><DialogTrigger><DialogContent>...</DialogContent></DialogTrigger></Dialog>`

3. **useInstallMod** - TanStack Query mutation for installation
   - Located: `web/src/hooks/use-mods.ts`
   - Returns: `{ mutate, isPending, isError, error }`

4. **useMods** - Check if mod already installed
   - Located: `web/src/hooks/use-mods.ts`
   - Access installed list: `data?.data?.mods`

5. **Toast notifications** - Use sonner (already configured)
   - Pattern: `toast.success("message")`, `toast.error("message")`

**ModDetailPage Install Section Pattern:**

The ModDetailPage already has an InstallSection component (lines 160-246) that:
- Shows version dropdown via Select component
- Manages install state with useInstallMod
- Shows "Installed: vX.Y.Z" indicator
- Differentiates between Install and Update buttons

This story adds confirmation dialog BEFORE the actual install call.

**ModCard Current Structure:**

```tsx
// Current ModCard (web/src/components/ModCard.tsx) - No install button
<Card onClick={onClick}>
  <div>Thumbnail</div>
  <CardHeader>Name, CompatibilityBadge, Author</CardHeader>
  <CardContent>Summary, Stats</CardContent>
</Card>
```

Add Install button to CardContent, positioned after stats row.

### InstallConfirmDialog Component Design

```tsx
interface InstallConfirmDialogProps {
  /** Mod to install */
  mod: {
    slug: string;
    name: string;
    version: string;
  };
  /** Compatibility status for warning display */
  compatibility: {
    status: CompatibilityStatus;
    message?: string;
  };
  /** Whether dialog is open */
  open: boolean;
  /** Callback when dialog open state changes */
  onOpenChange: (open: boolean) => void;
  /** Callback when install succeeds */
  onSuccess?: () => void;
  /** Callback when install fails */
  onError?: (error: Error) => void;
}
```

**Dialog Content Layout:**

```
+-----------------------------------------------+
|  Install Mod                                  |
+-----------------------------------------------+
|                                               |
|  [Mod Logo]  ModName                          |
|              by Author                        |
|              Version: v1.2.3                  |
|                                               |
|  [CompatibilityBadge]                        |
|                                               |
|  Warning (if not_verified/incompatible):     |
|  "This mod has not been verified for your    |
|   game server version. Installation may      |
|   cause issues."                             |
|                                               |
|  [ Cancel ]                [ Install ]       |
|                                               |
+-----------------------------------------------+
```

### Previous Story Intelligence (Story 10.7)

**Key Patterns Established:**

- `useBrowseScrollRestoration` hook pattern for state management
- Pagination component using shadcn Button variants
- Integration tests use `vi.mock` for TanStack Query hooks
- Test data fixtures in individual test files

**Files Modified in 10.7:**
- `web/src/features/mods/BrowseTab.tsx` - Added pagination integration
- `web/src/hooks/use-browse-mods.ts` - Added pagination state
- `web/src/components/Pagination.tsx` - Created pagination controls

**Current Test Count:** ~750 web tests

### Git Intelligence (Recent Commits)

Recent story 10.7 commits follow the pattern:
```
feat(story-10.7/task-1): extend useBrowseMods hook with pagination state
feat(story-10.7/task-2): create pagination component with page controls
feat(story-10.7/task-3): integrate pagination into BrowseTab
feat(story-10.7/task-4): implement scroll position restoration
```

### Files to Create

- `web/src/components/InstallConfirmDialog.tsx` - Confirmation dialog component
- `web/src/components/InstallConfirmDialog.test.tsx` - Component tests

### Files to Modify

- `web/src/components/ModCard.tsx` - Add Install button
- `web/src/components/ModCard.test.tsx` - Add install button tests
- `web/src/features/mods/ModDetailPage.tsx` - Integrate confirmation dialog
- `web/src/features/mods/ModDetailPage.test.tsx` - Add dialog integration tests

### Compatibility Status from Browse API

The browse API returns mods without full compatibility info. For browse cards:
- Use `getBrowseCardCompatibility()` from `web/src/lib/mod-compatibility.ts`
- Returns `'not_verified'` as conservative default
- Full compatibility check happens in mod detail view

For detail page install:
- Use `mod.compatibility` from `useModDetail` response
- This has actual status based on server game version

### Install Button States (ModCard)

1. **Not Installed**: Show "Install" button
2. **Installing**: Show spinner with "Installing..."
3. **Installed**: Show "Installed" indicator (green checkmark)
4. **Error**: Toast notification, return to "Install" state

**Important:** The ModCard needs access to installed mods list to show "Installed" indicator. Use `useMods()` hook at card or grid level.

### Test Scenarios

**InstallConfirmDialog:**
1. Renders with mod info and CompatibilityBadge
2. Shows warning for not_verified status
3. Shows warning for incompatible status
4. No warning for compatible status
5. Cancel button closes dialog
6. Install button triggers mutation
7. Shows loading state during install
8. Calls onSuccess after successful install
9. Calls onError on failure

**ModCard Install Button:**
1. Shows Install button when not installed
2. Opens confirmation dialog on click
3. Shows Installed indicator when mod in installed list
4. Successful install updates card to show Installed
5. Install button is not shown when onClick handler exists (detail navigation mode)

**ModDetailPage Integration:**
1. Install button opens confirmation dialog
2. Update button opens confirmation dialog
3. Successful install updates "Installed" indicator
4. Dialog closes after successful install

**Cross-Tab Synchronization:**
1. Installing from Browse tab adds mod to Installed tab list
2. TanStack Query cache invalidation propagates correctly

### Error Handling

Use existing error patterns from `useInstallMod`:
- Network errors: "Failed to connect to server"
- API errors: Show error message from response
- Mod not found: "Mod not found on ModDB"

Toast error pattern:
```typescript
toast.error('Installation failed', {
  description: error.message,
});
```

### Git Commit Pattern

```bash
git commit -m "feat(story-10.8/task-1): create InstallConfirmDialog component"
git commit -m "feat(story-10.8/task-2): add install button to ModCard"
git commit -m "feat(story-10.8/task-3): integrate confirmation dialog in ModDetailPage"
git commit -m "feat(story-10.8/task-4): verify cross-tab state synchronization"
```

### References

- `project-context.md` - Critical implementation rules and patterns
- [Source: web/src/hooks/use-mods.ts:108-119] - useInstallMod hook
- [Source: web/src/components/CompatibilityBadge.tsx] - CompatibilityBadge component
- [Source: web/src/components/ModCard.tsx] - ModCard component
- [Source: web/src/features/mods/ModDetailPage.tsx:160-246] - InstallSection component
- [Source: web/src/features/mods/InstalledTab.tsx:32-38] - handleInstalled toast pattern
- [Source: epics.md#Story-10.8] - Epic requirements (FR83-FR85)
- [Source: 10-7-pagination.md] - Previous story learnings

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- Task 1: Created InstallConfirmDialog component with comprehensive test coverage (15 tests). Component displays mod info, CompatibilityBadge, warnings for not_verified/incompatible mods, and handles install mutation with success/error callbacks.
- Task 2: Added Install button to ModCard with dialog integration. Shows "Installed" indicator for already-installed mods. Updated ModBrowseGrid and BrowseTab to pass installed slugs from useMods(). Added 6 new tests for install button functionality.
- Task 3: Replaced direct install in ModDetailPage InstallSection with InstallConfirmDialog integration. Install/Update buttons now open dialog with mod info and compatibility status. Added 4 new tests for dialog integration.
- Task 4: Verified cross-tab state synchronization. The existing useInstallMod hook already implements cache invalidation via queryClient.invalidateQueries(). Added explicit integration test that proves useMods() subscribers receive updated data after install.

### File List

- `web/src/components/InstallConfirmDialog.tsx` (created)
- `web/src/components/InstallConfirmDialog.test.tsx` (created)
- `web/src/components/ModCard.tsx` (modified)
- `web/src/components/ModCard.test.tsx` (modified)
- `web/src/components/ModBrowseGrid.tsx` (modified)
- `web/src/components/ModBrowseGrid.test.tsx` (modified)
- `web/src/features/mods/BrowseTab.tsx` (modified)
- `web/src/features/mods/BrowseTab.test.tsx` (modified)
- `web/src/features/mods/ModDetailPage.tsx` (modified)
- `web/src/features/mods/ModDetailPage.test.tsx` (modified)
- `web/src/hooks/use-mods.test.tsx` (modified)
