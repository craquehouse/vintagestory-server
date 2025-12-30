# Story 5.6: Mod Management UI

Status: review

## Story

As an **administrator**,
I want **a web interface for managing mods**,
So that **I can install, view, and manage mods visually**.

---

## Background

This is the UI story for Epic 5 (Mod Management). All backend APIs are complete (Stories 5.1-5.5):
- `GET /api/v1alpha1/mods` - List installed mods (Story 5.5)
- `GET /api/v1alpha1/mods/lookup/{slug}` - Lookup mod details (Story 5.3)
- `POST /api/v1alpha1/mods` - Install mod (Story 5.2)
- `POST /api/v1alpha1/mods/{slug}/enable` - Enable mod (Story 5.4)
- `POST /api/v1alpha1/mods/{slug}/disable` - Disable mod (Story 5.4)
- `DELETE /api/v1alpha1/mods/{slug}` - Remove mod (Story 5.4)

The current ModList component at `web/src/features/mods/ModList.tsx` is a placeholder. This story replaces it with a full mod management interface.

**FRs Covered:** FR10 (Admin views mod list), FR14-16 (Enable/Disable/Remove), partial FR11-13 (Install flow)

**Key UX Design Decisions (from UX spec):**
- "Slug to success" loop: Type mod slug → See compatibility → Install with one click
- ModLookupInput accepts slugs OR URLs (smart parsing)
- Compatibility badges: Compatible (green), Not verified (yellow), Incompatible (red)
- Debounced lookup (300ms) with preview card
- Table of installed mods with enable/disable toggle and remove button
- PendingRestartBanner in header when changes require restart
- Toast notifications: subtle for success, prominent for errors

---

## Acceptance Criteria

1. **Given** I navigate to the Mods page **When** the page loads **Then** I see a ModLookupInput field with placeholder "Enter mod slug or paste URL" **And** I see a table of installed mods (or empty state if none)

2. **Given** I type a mod slug in the input **When** I stop typing (300ms debounce) **Then** a lookup request is made **And** mod details appear in a preview card below the input

3. **Given** the mod lookup returns results **When** I view the preview card **Then** I see mod name, author, description, side, and CompatibilityBadge (green/yellow/red) **And** an "Install" button is available

4. **Given** I click "Install" on a compatible mod **When** installation completes **Then** a success toast appears **And** the mod appears in the installed mods table **And** the pending restart banner appears in the header (if server running)

5. **Given** I click "Install" on an incompatible mod **When** I click the button **Then** a warning dialog appears asking for confirmation **And** I can choose to proceed or cancel

6. **Given** the mods table is displayed **When** I view an installed mod row **Then** I see: mod name, version, compatibility badge, enabled/disabled toggle, remove button

7. **Given** I toggle a mod's enabled state **When** the toggle is clicked **Then** the state updates optimistically **And** a toast confirms success or shows error **And** pending restart indicator updates

8. **Given** I click the remove button on a mod **When** the confirmation dialog appears and I confirm **Then** the mod is removed from the list **And** a success toast appears

9. **Given** the pending restart flag is set **When** I view the header **Then** I see the PendingRestartBanner with "Restart required · N pending changes · [Restart Now]"

10. **Given** I have no API key or Monitor role **When** I try to install/enable/disable/remove **Then** I receive appropriate error feedback (401/403)

---

## Tasks / Subtasks

- [x] Task 1: Create API integration hooks + tests (AC: 2-5, 7-8)
  - [x] 1.1: Create `web/src/api/mods.ts` with API functions:
    - `fetchMods()` - GET /mods
    - `lookupMod(slug: string)` - GET /mods/lookup/{slug}
    - `installMod(slug: string, version?: string)` - POST /mods
    - `enableMod(slug: string)` - POST /mods/{slug}/enable
    - `disableMod(slug: string)` - POST /mods/{slug}/disable
    - `removeMod(slug: string)` - DELETE /mods/{slug}
  - [x] 1.2: Create `web/src/hooks/use-mods.ts` with TanStack Query hooks:
    - `useMods()` - Query for installed mods list
    - `useLookupMod(slug: string)` - Query for mod lookup (enabled: !!slug)
    - `useInstallMod()` - Mutation for installation
    - `useEnableMod()` - Mutation for enabling
    - `useDisableMod()` - Mutation for disabling
    - `useRemoveMod()` - Mutation for removal
  - [x] 1.3: Update `web/src/api/query-keys.ts` to add lookup key
  - [x] 1.4: Write tests for API functions and hooks in `web/src/hooks/use-mods.test.tsx`
  - [x] 1.5: Run `just test-web` to verify tests pass

- [x] Task 2: Create CompatibilityBadge component + tests (AC: 3, 6)
  - [x] 2.1: Create `web/src/components/CompatibilityBadge.tsx`:
    - Props: `status: "compatible" | "not_verified" | "incompatible"`, optional `message`
    - Renders badge with appropriate color and icon
    - Green (#a6e3a1) + checkmark for compatible
    - Yellow (#f9e2af) + warning for not_verified
    - Red (#f38ba8) + X for incompatible
  - [x] 2.2: Write tests in `web/src/components/CompatibilityBadge.test.tsx`
  - [x] 2.3: Run `just test-web` to verify tests pass

- [x] Task 3: Create ModLookupInput component + tests (AC: 1-5)
  - [x] 3.1: Create `web/src/components/ModLookupInput.tsx`:
    - Input field with placeholder "Enter mod slug or paste URL"
    - Debounced (300ms) lookup trigger using useDeferredValue or custom debounce
    - Loading state with spinner in input
    - Preview card below input when mod found
    - Preview shows: name, author, description (truncated), side, CompatibilityBadge
    - Install button with loading state
    - Error state for mod not found
  - [x] 3.2: Smart URL parsing: extract slug from `https://mods.vintagestory.at/smithingplus` or `mods.vintagestory.at/smithingplus`
  - [x] 3.3: Confirmation dialog for incompatible mods before install
  - [x] 3.4: Write tests in `web/src/components/ModLookupInput.test.tsx`
  - [x] 3.5: Run `just test-web` to verify tests pass

- [x] Task 4: Create ModTable component + tests (AC: 6-8)
  - [x] 4.1: Create `web/src/components/ModTable.tsx`:
    - Table with columns: Name, Version, Compatibility, Status, Actions
    - Name column shows mod name with slug as subtitle
    - Version shows installed version
    - Compatibility shows CompatibilityBadge
    - Status shows enabled/disabled toggle (Switch component)
    - Actions shows Remove button (trash icon)
  - [x] 4.2: Implement optimistic updates for enable/disable toggle
  - [x] 4.3: Implement remove confirmation dialog
  - [x] 4.4: Empty state when no mods installed: "No mods installed yet"
  - [x] 4.5: Write tests in `web/src/components/ModTable.test.tsx`
  - [x] 4.6: Run `just test-web` to verify tests pass

- [x] Task 5: Create PendingRestartBanner component + tests (AC: 9)
  - [x] 5.1: Create `web/src/components/PendingRestartBanner.tsx`:
    - Shows when `pending_restart` is true from mods or server status
    - Displays: "⟳ Restart required · [Restart Now]" with mauve accent button
    - Restart Now triggers server restart mutation
    - Loading state during restart
  - [x] 5.2: Integrate into Header component (conditionally rendered)
  - [x] 5.3: Write tests in `web/src/components/PendingRestartBanner.test.tsx`
  - [x] 5.4: Run `just test-web` to verify tests pass

- [x] Task 6: Update ModList feature page + tests (AC: 1, 4)
  - [x] 6.1: Update `web/src/features/mods/ModList.tsx`:
    - Page heading "Mods"
    - ModLookupInput at top
    - ModTable below showing installed mods
    - Toast notifications for install/enable/disable/remove results
  - [x] 6.2: Use Sonner toast from shadcn/ui for notifications
  - [x] 6.3: Write/update tests in `web/src/features/mods/ModList.test.tsx`
  - [x] 6.4: Run `just test-web` to verify tests pass

- [x] Task 7: Final validation (AC: 1-10)
  - [x] 7.1: Run `just test-web` - verify full test suite passes (347 tests pass)
  - [x] 7.2: Run `just check` - verify lint, typecheck, and all tests pass (511 API + 347 web)
  - [x] 7.3: Manual test: Navigate to Mods page, verify UI renders
  - [x] 7.4: Manual test: Search for mod "smithingplus", verify preview appears
  - [x] 7.5: Manual test: Install mod, verify toast and table update
  - [x] 7.6: Manual test: Toggle enable/disable, verify optimistic update
  - [x] 7.7: Manual test: Remove mod, verify confirmation and removal
  - [x] 7.8: Manual test: Verify PendingRestartBanner appears after mod operations

---

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Run `just test-web` to verify tests pass before marking task complete
- Run `just check` for full validation (lint + typecheck + test) before story completion

**Test patterns to follow:**
- Use MSW (Mock Service Worker) for API mocking in tests
- Use @testing-library/react for component testing
- Use vitest for test runner

### Security Requirements

**Follow patterns in `project-context.md` → Security Patterns section:**

- All mod operations except list require Admin role
- List endpoint works for both Admin and Monitor
- Handle 401/403 errors gracefully with user feedback
- Never log API keys

### Development Commands

Use `just` for all development tasks:
- `just test-web` - Run all web tests
- `just dev-web` - Start frontend dev server
- `just check` - Full validation (lint + typecheck + test)

### Architecture & Patterns

**State Management (from architecture.md):**
- Use TanStack Query for ALL server state (mods data)
- Use React Context ONLY for UI state (theme, sidebar)
- NEVER mix these

**Query Keys Pattern (from query-keys.ts):**
```typescript
export const queryKeys = {
  mods: {
    all: ['mods'] as const,
    detail: (slug: string) => ['mods', slug] as const,
    lookup: (slug: string) => ['mods', 'lookup', slug] as const,  // Add this
  },
  // ...
};
```

**Mutation Pattern with Optimistic Updates:**
```typescript
const enableMod = useMutation({
  mutationFn: (slug: string) => enableModApi(slug),
  onMutate: async (slug) => {
    await queryClient.cancelQueries({ queryKey: queryKeys.mods.all });
    const previous = queryClient.getQueryData(queryKeys.mods.all);
    // Optimistically update
    queryClient.setQueryData(queryKeys.mods.all, (old) => ({
      ...old,
      mods: old.mods.map(m => m.slug === slug ? {...m, enabled: true} : m)
    }));
    return { previous };
  },
  onError: (err, slug, context) => {
    queryClient.setQueryData(queryKeys.mods.all, context?.previous);
    toast.error(`Failed to enable mod: ${err.message}`);
  },
  onSettled: () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.mods.all });
  },
  onSuccess: () => {
    toast.success('Mod enabled');
  },
});
```

**API Response Types:**
```typescript
// From GET /api/v1alpha1/mods
interface ModsListResponse {
  mods: ModInfo[];
  pending_restart: boolean;
}

interface ModInfo {
  filename: string;
  slug: string;
  version: string;
  enabled: boolean;
  installed_at: string;  // ISO 8601
  name: string | null;
  authors: string[] | null;
  description: string | null;
}

// From GET /api/v1alpha1/mods/lookup/{slug}
interface ModLookupResponse {
  slug: string;
  name: string;
  author: string;
  description: string | null;
  latest_version: string;
  downloads: number;
  side: "Both" | "Client" | "Server";
  compatibility: {
    status: "compatible" | "not_verified" | "incompatible";
    game_version: string | null;
    mod_version: string | null;
    message: string;
  };
}

// From POST /api/v1alpha1/mods (install)
interface ModInstallResponse {
  slug: string;
  version: string;
  filename: string;
  compatibility: "compatible" | "not_verified" | "incompatible";
  pending_restart: boolean;
}
```

**JSON Field Transform at API Boundary:**
- API returns snake_case (e.g., `pending_restart`)
- Transform to camelCase in API client (e.g., `pendingRestart`)
- See `web/src/api/client.ts` for transform pattern

### UX Patterns (from ux-design-specification.md)

**Toast Notifications:**
- Success: Green left border, subtle, 3 seconds auto-dismiss
- Error: Red left border + background tint, prominent, 5 seconds + manual dismiss
- Use `sonner` via shadcn/ui

**Confirmation Dialogs:**
- Remove mod: "Remove {mod name}? This cannot be undone."
- Install incompatible: Warning with compatibility message + "Install Anyway" / "Cancel"

**Debounce Pattern:**
```typescript
// Use useDeferredValue for lookup
const [inputValue, setInputValue] = useState('');
const deferredSlug = useDeferredValue(inputValue);

// Or custom debounce hook
const debouncedSlug = useDebounce(inputValue, 300);
```

**Smart URL Parsing:**
```typescript
function extractSlug(input: string): string {
  // Handle full URLs
  const urlMatch = input.match(/mods\.vintagestory\.at\/([a-zA-Z0-9_-]+)/);
  if (urlMatch) return urlMatch[1];
  // Handle protocol-less URLs
  if (input.includes('/')) {
    const parts = input.split('/');
    return parts[parts.length - 1];
  }
  // Already a slug
  return input.toLowerCase().trim();
}
```

### Existing Components to Use

**shadcn/ui components available:**
- `Button` - for actions (install, restart)
- `Card` - for mod preview
- `Input` - for slug input
- `Switch` - for enable/disable toggle
- `Table` (if available) or custom div-based table
- `Dialog` - for confirmation modals
- `Skeleton` - for loading states
- `Badge` - base for CompatibilityBadge
- `Sonner` (toast) - for notifications

**Check which shadcn components are installed:**
```bash
ls web/src/components/ui/
```

**To add missing components:**
```bash
cd web && bunx shadcn@latest add table dialog alert-dialog
```

### Project Structure Notes

**Files to create:**
```
web/src/
├── api/
│   └── mods.ts                    # API functions
├── hooks/
│   ├── use-mods.ts                # TanStack Query hooks
│   └── use-mods.test.ts           # Hook tests
├── components/
│   ├── CompatibilityBadge.tsx     # Compatibility status badge
│   ├── CompatibilityBadge.test.tsx
│   ├── ModLookupInput.tsx         # Search input with preview
│   ├── ModLookupInput.test.tsx
│   ├── ModTable.tsx               # Installed mods table
│   ├── ModTable.test.tsx
│   ├── PendingRestartBanner.tsx   # Header banner for restart
│   └── PendingRestartBanner.test.tsx
└── features/mods/
    ├── ModList.tsx                # Page component (update existing)
    └── ModList.test.tsx           # Page tests (create)
```

**Files to update:**
```
web/src/
├── api/query-keys.ts              # Add lookup key
└── components/layout/Header.tsx   # Add PendingRestartBanner
```

### Previous Story Intelligence (5.5)

**Key patterns from Story 5.5:**
- `GET /api/v1alpha1/mods` returns `{ mods: [...], pending_restart: boolean }`
- Use `model_dump(mode="json")` for Pydantic models in responses
- `RequireAuth` type alias for read-only endpoints (both Admin and Monitor)
- Restart state tracked via `ModService.restart_state.pending_restart`

**Commit message format:**
- `feat(story-5.6): implement mod management UI components`
- `test(story-5.6): add mod table and lookup input tests`

### Git Intelligence

**Recent commits:**
- `47f2483` - feat(story-5.5): mark story as done after code-review
- `417e97c` - feat(story-5.5): implement mod list API endpoint
- `1fa27ed` - fix(story-5.4): add slug validation to enable/disable/remove endpoints
- `46110b3` - feat(story-5.4): implement mod enable/disable and remove API

### References

- `project-context.md` - Critical implementation rules and patterns
- `_bmad-output/planning-artifacts/architecture.md` - Frontend architecture patterns
- `_bmad-output/planning-artifacts/ux-design-specification.md` - UX patterns and components
- `_bmad-output/planning-artifacts/epics.md#Story 5.6: Mod Management UI` - Story source
- `api/src/vintagestory_api/routers/mods.py` - All API endpoints
- `api/src/vintagestory_api/models/mods.py` - Response models

---

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2025-12-30 | Story created with comprehensive context for UI implementation | Claude Opus 4.5 |
