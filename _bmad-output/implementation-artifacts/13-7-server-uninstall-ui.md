# Story 13.7: Server Uninstall UI

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **administrator**,
I want **a way to uninstall the server from the UI**,
So that **I can cleanly remove the installation without manual file deletion**.

**Background:** Added from Epic 11 retrospective to support testing workflow. Provides UI for the uninstall API (Story 13.6) with appropriate confirmation.

## Acceptance Criteria

1. **Given** a server is installed
   **When** I view the Version page
   **Then** I see a "Remove Server" button (or similar)
   **And** the button is styled as a destructive action (red/warning)

2. **Given** the server is running
   **When** I click "Remove Server"
   **Then** I see a confirmation dialog explaining the server will be stopped
   **And** the dialog notes that configuration and world data will be preserved

3. **Given** the server is stopped
   **When** I click "Remove Server"
   **Then** I see a confirmation dialog
   **And** the dialog notes that configuration and world data will be preserved

4. **Given** I confirm the uninstall
   **When** the operation completes
   **Then** I see a success toast notification
   **And** the page transitions to the "Server Installation" view
   **And** the Version page header changes to "Server Installation"

5. **Given** I cancel the confirmation dialog
   **When** I close the dialog
   **Then** no action is taken
   **And** the server remains installed

6. **Given** the uninstall API fails
   **When** I attempt to remove the server
   **Then** I see an error toast with the failure message
   **And** the server state remains unchanged

## Tasks / Subtasks

- [x] Task 1: Add `uninstallServer` API function + tests (AC: 4, 6)
  - [x] Subtask 1.1: Add `uninstallServer` function to `web/src/api/server.ts` (DELETE /api/v1alpha1/server)
  - [x] Subtask 1.2: Write tests in existing `web/src/api/server.test.ts` or create if missing

- [x] Task 2: Create `useUninstallServer` mutation hook + tests (AC: 4, 6)
  - [x] Subtask 2.1: Add `useUninstallServer` hook to `web/src/hooks/use-server-status.ts`
  - [x] Subtask 2.2: Invalidate `queryKeys.server.status` and `queryKeys.versions.all` on success
  - [x] Subtask 2.3: Add tests in `web/src/hooks/use-server-status.test.tsx`

- [x] Task 3: Create `UninstallConfirmDialog` component + tests (AC: 2, 3, 5)
  - [x] Subtask 3.1: Create `web/src/components/UninstallConfirmDialog.tsx`
  - [x] Subtask 3.2: Use AlertDialog from shadcn/ui (same pattern as other dialogs)
  - [x] Subtask 3.3: Show server-running warning (yellow) when `serverState === 'running'`
  - [x] Subtask 3.4: Show preservation note in all cases
  - [x] Subtask 3.5: Use destructive button variant for "Remove Server" action
  - [x] Subtask 3.6: Write tests in `web/src/components/UninstallConfirmDialog.test.tsx`

- [x] Task 4: Integrate Remove button into VersionPage + tests (AC: 1, 4, 5, 6)
  - [x] Subtask 4.1: Add "Remove Server" button to `InstalledVersionCard` in `VersionPage.tsx`
  - [x] Subtask 4.2: Wire up dialog state and uninstall mutation
  - [x] Subtask 4.3: Add toast notifications for success/error
  - [x] Subtask 4.4: Button disabled during transitional states (starting, stopping, installing)
  - [x] Subtask 4.5: Update `VersionPage.test.tsx` with integration tests

- [x] Task 5: Manual browser verification (AC: all) - **User confirmed all items work correctly**
  - [x] Subtask 5.1: Start dev servers (`just dev-api` and `just dev-web`)
  - [x] Subtask 5.2: With server installed and stopped, verify Remove button appears
  - [x] Subtask 5.3: Click Remove, verify dialog shows preservation message
  - [x] Subtask 5.4: Confirm uninstall, verify success toast and page transition
  - [x] Subtask 5.5: With server running, verify dialog shows stop warning
  - [x] Subtask 5.6: Verify cancel closes dialog with no changes

### Review Follow-ups (AI-Review)

- [x] [AI-Review][HIGH] AC 4: Add test verifying success toast appears after uninstall (VersionPage.test.tsx)
- [x] [AI-Review][HIGH] AC 4: Add test verifying page title changes to "Server Installation" after success (VersionPage.test.tsx)
- [x] [AI-Review][HIGH] AC 6: Add test verifying error toast appears when API call fails (VersionPage.test.tsx)
- [x] [AI-Review][HIGH] Task 4: Mock sonner toast in VersionPage.test.tsx for toast tests
- [x] [AI-Review][MEDIUM] All: Add AC references to pending state tests in UninstallConfirmDialog.test.tsx
- [x] [AI-Review][MEDIUM] All: Add AC references to dialog title tests in UninstallConfirmDialog.test.tsx
- [x] [AI-Review][LOW] Story: Add explicit user confirmation for manual verification in Task 5

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Run `just test-web` to verify all web tests pass before marking task complete
- Manual test task requires **explicit user confirmation** before marking complete

### Security Requirements

Follow patterns in `project-context.md` → Security Patterns section:

- Endpoint already requires Admin role (implemented in Story 13.6)
- No additional security requirements for UI layer

### Development Commands

```bash
just test-web                                # Run all web tests
just test-web --grep "Uninstall"             # Run uninstall-related tests
just check                                   # Full validation
just dev-api                                 # Start API dev server
just dev-web                                 # Start web dev server
```

### Architecture & Patterns

**Component Pattern:** Follow `InstallVersionDialog` (Story 13.4) as the reference pattern.

**Dialog Structure:**
```tsx
<AlertDialog open={open} onOpenChange={onOpenChange}>
  <AlertDialogContent>
    <AlertDialogHeader>
      <AlertDialogTitle>Remove Server Installation</AlertDialogTitle>
      <AlertDialogDescription>
        This will remove the VintageStory server binaries.
      </AlertDialogDescription>
    </AlertDialogHeader>

    {/* Preservation note - always shown */}
    <div className="...preservation-info...">
      Your configuration, mods, and world saves will be preserved.
    </div>

    {/* Server running warning - conditional */}
    {isServerRunning && (
      <div className="...warning-yellow...">
        The server is running and will be stopped first.
      </div>
    )}

    <AlertDialogFooter>
      <AlertDialogCancel>Cancel</AlertDialogCancel>
      <AlertDialogAction variant="destructive">
        Remove Server
      </AlertDialogAction>
    </AlertDialogFooter>
  </AlertDialogContent>
</AlertDialog>
```

**API Function Pattern:**
```typescript
// web/src/api/server.ts
export async function uninstallServer(): Promise<ApiResponse<ActionMessage>> {
  return apiClient<ApiResponse<ActionMessage>>(`${API_PREFIX}`, {
    method: 'DELETE',
  });
}
```

**Hook Pattern:**
```typescript
// web/src/hooks/use-server-status.ts
export function useUninstallServer() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: uninstallServer,
    onSuccess: () => {
      // Invalidate status to show not_installed state
      queryClient.invalidateQueries({ queryKey: queryKeys.server.status });
      // Invalidate versions to refresh "Installed" badges
      queryClient.invalidateQueries({ queryKey: ['versions'] });
    },
  });
}
```

**Button Placement in VersionPage:**

Add to `InstalledVersionCard` component. Button should:
- Use `variant="destructive"` (red styling)
- Use `Trash2` icon from lucide-react
- Be disabled during transitional states

```tsx
// In InstalledVersionCard
const isTransitional = ['starting', 'stopping', 'installing'].includes(state);

<Button
  variant="destructive"
  size="sm"
  disabled={isTransitional}
  onClick={() => setIsUninstallDialogOpen(true)}
>
  <Trash2 className="h-4 w-4 mr-2" />
  Remove Server
</Button>
```

**Toast Notifications:**

Use same pattern as `InstallVersionDialog`:
```typescript
// On success
toast.success('Server removed', {
  description: 'The server installation has been removed.',
});

// On error
toast.error('Failed to remove server', {
  description: error.message,
});
```

### Previous Story Intelligence

**From Story 13.6 (Server Uninstall API):**
- API endpoint: `DELETE /api/v1alpha1/server`
- Returns 409 if server is running (code: `SERVER_RUNNING`)
- Returns 404 if not installed (code: `SERVER_NOT_INSTALLED`)
- Success returns `{ status: "ok", data: { state: "not_installed" } }`
- Preserves `/data/serverdata` (configs, mods, worlds)

**From Story 13.4/13.5 (Install Dialog Patterns):**
- Dialog uses `Dialog` component from shadcn/ui
- Server running warning uses yellow color scheme
- `useInstallStatus` polls during transitional states
- State transitions trigger toast via `useServerStateToasts`

**Query Invalidation (ADR-4):**
After uninstall, invalidate:
- `queryKeys.server.status` - Refresh to show `not_installed`
- `queryKeys.versions.all` - Refresh "Installed" badges

### File Structure

**Files to create:**
- `web/src/components/UninstallConfirmDialog.tsx`
- `web/src/components/UninstallConfirmDialog.test.tsx`

**Files to modify:**
- `web/src/api/server.ts` - Add `uninstallServer` function
- `web/src/hooks/use-server-status.ts` - Add `useUninstallServer` hook
- `web/src/hooks/use-server-status.test.tsx` - Add hook tests
- `web/src/features/game-server/VersionPage.tsx` - Add Remove button and dialog
- `web/src/features/game-server/VersionPage.test.tsx` - Add integration tests

**Files to reference (DO NOT modify):**
- `web/src/components/ui/alert-dialog.tsx` - AlertDialog primitives
- `web/src/components/InstallVersionDialog.tsx` - Reference pattern
- `web/src/api/query-keys.ts` - Query key definitions
- `web/src/api/types.ts` - API types

### Git Workflow

**Branch:** `story/13-7-server-uninstall-ui`

**Commit Pattern:**
```
feat(story-13.7/task-1): add uninstallServer API function
feat(story-13.7/task-2): create useUninstallServer mutation hook
feat(story-13.7/task-3): create UninstallConfirmDialog component
feat(story-13.7/task-4): integrate uninstall UI into VersionPage
```

### Test Patterns

**Component Tests (UninstallConfirmDialog.test.tsx):**
```typescript
describe('UninstallConfirmDialog', () => {
  it('shows preservation message in all cases');
  it('shows server running warning when server is running');
  it('hides server running warning when server is stopped');
  it('calls onConfirm when Remove Server button clicked');
  it('calls onOpenChange(false) when Cancel clicked');
  it('disables Remove button when isPending is true');
});
```

**Integration Tests (VersionPage.test.tsx additions):**
```typescript
describe('VersionPage uninstall', () => {
  it('shows Remove Server button when server is installed');
  it('hides Remove Server button when not installed');
  it('disables Remove Server button during transitional states');
  it('opens dialog when Remove Server clicked');
  it('shows success toast after successful uninstall');
  it('shows error toast on uninstall failure');
});
```

**Hook Tests (use-server-status.test.tsx additions):**
```typescript
describe('useUninstallServer', () => {
  it('calls DELETE /api/v1alpha1/server');
  it('invalidates server.status on success');
  it('invalidates versions on success');
});
```

### References

- `project-context.md` - Critical implementation rules and patterns
- [Source: _bmad-output/planning-artifacts/epics.md#Story 13.7] - Story requirements
- [Source: _bmad-output/implementation-artifacts/13-6-server-uninstall-api.md] - API implementation
- [Source: web/src/components/InstallVersionDialog.tsx] - Dialog pattern reference
- [Source: web/src/hooks/use-server-status.ts] - Mutation hook patterns
- [Source: _bmad-output/planning-artifacts/architecture/epic-13-server-version-browser.md] - ADR-4 cache sync

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- Task 1: Added `uninstallServer()` function to server.ts, created server.test.ts with 4 tests covering success/error cases.
- Task 2: Added `useUninstallServer` hook with query invalidation for server.status and versions queries. Added 3 tests.
- Task 3: Created `UninstallConfirmDialog` component with AlertDialog, preservation message, server-running warning, destructive styling. Added 17 tests.
- Task 4: Integrated Remove Server button into VersionPage with dialog, toast notifications, and transitional state handling. Added 6 integration tests.
- Task 5: Manual browser verification completed - all acceptance criteria verified by user.

### File List

- `web/src/api/server.ts` (modified) - Added uninstallServer function
- `web/src/api/server.test.ts` (created) - Tests for uninstallServer
- `web/src/hooks/use-server-status.ts` (modified) - Added useUninstallServer hook
- `web/src/hooks/use-server-status.test.tsx` (modified) - Added hook tests
- `web/src/components/UninstallConfirmDialog.tsx` (created) - Confirmation dialog component
- `web/src/components/UninstallConfirmDialog.test.tsx` (created) - Dialog tests
- `web/src/features/game-server/VersionPage.tsx` (modified) - Added Remove button and dialog integration
- `web/src/features/game-server/VersionPage.test.tsx` (modified) - Added uninstall integration tests
