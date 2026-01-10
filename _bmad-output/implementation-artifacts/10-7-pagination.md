# Story 10.7: Pagination

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **administrator**,
I want **pagination for large result sets**,
So that **I can browse through hundreds of mods efficiently without overwhelming the UI**.

## Acceptance Criteria

1. **Given** browse results exceed one page
   **When** results are displayed
   **Then** pagination controls are visible (page numbers or "Load more" button)
   *(Covers FR80)*

2. **Given** the UI implements pagination controls
   **When** I click page 2 or "Load more"
   **Then** page 2 results are displayed (or appended for infinite scroll)
   *(Covers FR81)*

3. **Given** I am on page 3 of results
   **When** I click a mod card, view details, then go back
   **Then** I return to page 3 at approximately the same scroll position
   *(Covers FR82)*

## Tasks / Subtasks

<!--
🚨 CRITICAL TASK STRUCTURE RULES:
1. Each functional task MUST include "+ tests" in its name
2. Do NOT create separate "Write tests" tasks at the end
3. A task is NOT complete until its tests pass
4. Tests verify the specific AC listed for that task

✅ CORRECT PATTERN:
- [ ] Task 1: Implement user login endpoint + tests (AC: 1, 2)
  - [ ] Create login route handler
  - [ ] Add input validation
  - [ ] Write tests for success/failure cases

❌ WRONG PATTERN (tests batched at end):
- [ ] Task 1: Implement user login endpoint (AC: 1, 2)
- [ ] Task 2: Implement logout endpoint (AC: 3)
- [ ] Task 3: Write all tests  <- NEVER DO THIS
-->

- [x] Task 1: Extend useBrowseMods hook with pagination state + tests (AC: 1, 2)
  - [x] Subtask 1.1: Add page and pageSize parameters to hook
  - [x] Subtask 1.2: Expose fetchNextPage/fetchPrevPage functions
  - [x] Subtask 1.3: Include pagination metadata (hasNext, hasPrev, totalPages) in return
  - [x] Subtask 1.4: Update query key to include page for proper caching
  - [x] Subtask 1.5: Write tests for pagination state changes

- [x] Task 2: Create Pagination component + tests (AC: 1)
  - [x] Subtask 2.1: Create Pagination.tsx with page numbers and prev/next buttons
  - [x] Subtask 2.2: Handle edge cases (first page, last page, single page)
  - [x] Subtask 2.3: Add loading state styling for page transitions
  - [x] Subtask 2.4: Apply Catppuccin theming consistent with other controls
  - [x] Subtask 2.5: Write tests for all pagination states and interactions

- [x] Task 3: Integrate pagination into BrowseTab + tests (AC: 1, 2)
  - [x] Subtask 3.1: Add Pagination component below ModBrowseGrid
  - [x] Subtask 3.2: Connect pagination controls to useBrowseMods hook
  - [x] Subtask 3.3: Update results count to show "Page X of Y"
  - [x] Subtask 3.4: Reset to page 1 when filters/search/sort change
  - [x] Subtask 3.5: Write integration tests for pagination with filter interactions

- [x] Task 4: Implement scroll position restoration + tests (AC: 3)
  - [x] Subtask 4.1: Store scroll position and page in sessionStorage before navigation
  - [x] Subtask 4.2: Restore scroll position and page on back navigation
  - [x] Subtask 4.3: Clear stored position when filters/search change
  - [x] Subtask 4.4: Write tests for position restoration after detail view navigation

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Do not batch tests into a separate "Write tests" task at the end
- Run `just test` to verify all tests pass before marking task complete

### Security Requirements

**Follow patterns in `project-context.md` → Security Patterns section:**

- Both Admin and Monitor roles can access browse endpoint (read-only)
- No sensitive data in pagination implementation
- Use existing API client with auth headers

### Development Commands

Use `just` for all development tasks:
- `just test` - Run all tests
- `just test-web` - Run web tests only
- `just test-web Pagination` - Run specific test file
- `just check` - Full validation (lint + typecheck + test)
- `just lint` - Run all linters

### Architecture & Patterns

**Backend API Already Supports Pagination:**

The browse endpoint `GET /api/v1alpha1/mods/browse` already returns pagination metadata:

```typescript
interface PaginationInfo {
  page: number;         // Current page (1-indexed)
  pageSize: number;     // Items per page
  totalItems: number;   // Total items across all pages
  totalPages: number;   // Total pages available
  hasNext: boolean;     // Whether next page exists
  hasPrev: boolean;     // Whether previous page exists
}

// Response structure
interface BrowseResponse {
  status: 'ok';
  data: {
    mods: ModBrowseItem[];
    pagination: PaginationInfo;
  }
}
```

Query parameters:
- `page`: Page number (1-indexed, default 1)
- `page_size`: Items per page (1-100, default 20)

**Current Hook State:**

`useBrowseMods` currently fetches data but doesn't expose page navigation. The pagination data is available in `query.data?.data?.pagination` but not used.

**Client-Side vs Server-Side Filtering:**

Important: The current implementation does client-side filtering for search and filters because:
1. VintageStory API returns all 550+ mods without search support
2. Our API caches and paginates this data
3. Search/filter happens client-side on the current page

This means pagination works on the FULL dataset, but filtering narrows within that:
- Without filters: Server pagination of all ~550 mods
- With filters: Client-side filtering of paginated results

**Design Decision: Page Numbers vs Infinite Scroll:**

Choose **page numbers** over infinite scroll because:
1. Matches established patterns (Portainer, TrueNAS)
2. Better for "find that mod I saw on page 5" use case
3. Clear "X of Y" feedback per UX spec
4. Simpler implementation with existing backend

**Pagination Component Pattern:**

```tsx
// Simple pagination with prev/next and page numbers
<Pagination
  currentPage={pagination.page}
  totalPages={pagination.totalPages}
  onPageChange={(page) => setPage(page)}
  isLoading={isFetching}
/>
```

Show:
- Previous button (disabled on page 1)
- Page numbers: 1 ... 4 5 [6] 7 8 ... 20 (truncated for many pages)
- Next button (disabled on last page)
- "Page X of Y" text

### Previous Story Intelligence (Story 10.6)

**Key Learnings:**

- Navigation uses `navigate()` from react-router
- Query keys defined in `web/src/api/query-keys.ts`
- CompatibilityBadge and ModCard patterns established
- DOMPurify used for HTML sanitization
- Test count: ~972 web tests

**Files Modified in 10.6:**
- `web/src/App.tsx` - Added `/mods/browse/:slug` route
- `web/src/features/mods/ModDetailPage.tsx` - Detail view with back navigation
- `web/src/hooks/use-mod-detail.ts` - TanStack Query hook pattern

**Deferred from 10.6:** Scroll position restoration was added to polish backlog. This story implements it as AC 3.

### Git Intelligence (Recent Commits)

Recent story 10.6 commits show the pattern:
```
feat(story-10.6/task-1): add mod detail API types and fetch function
feat(story-10.6/task-2): create ModDetailPage with description and releases
feat(story-10.6/task-3): implement install/update section with version dropdown
feat(story-10.6/task-4): add navigation and route integration
```

### Scroll Position Restoration Strategy

Two approaches to consider:

**Option A - sessionStorage (Recommended):**
```typescript
// Before navigation to detail
sessionStorage.setItem('browse-state', JSON.stringify({
  page: currentPage,
  scrollY: window.scrollY,
}));

// On mount/back navigation
const saved = sessionStorage.getItem('browse-state');
if (saved && wasBackNavigation()) {
  const { page, scrollY } = JSON.parse(saved);
  setPage(page);
  requestAnimationFrame(() => window.scrollTo(0, scrollY));
}
```

**Option B - URL State:**
Store page in URL: `/mods/browse?page=3`
- Pros: Bookmarkable, shareable
- Cons: More complex state management

**Recommendation:** Use sessionStorage for scroll position, consider URL for page number (cleaner UX).

### Pagination Controls UI Layout

```
┌──────────────────────────────────────────────────────────────┐
│  [< Prev] [1] ... [4] [5] [6] [7] [8] ... [20] [Next >]     │
│                                                              │
│  Showing page 6 of 20 (541 mods total)                      │
└──────────────────────────────────────────────────────────────┘
```

Use shadcn/ui Button components with consistent styling:
- Current page: Primary variant (accent color)
- Other pages: Ghost variant
- Prev/Next: Outline variant
- Ellipsis: Text span (not clickable)

### Files to Create

- `web/src/components/Pagination.tsx` - Pagination controls component
- `web/src/components/Pagination.test.tsx` - Component tests

### Files to Modify

- `web/src/hooks/use-browse-mods.ts` - Add page state management
- `web/src/hooks/use-browse-mods.test.tsx` - Update tests for pagination
- `web/src/features/mods/BrowseTab.tsx` - Integrate pagination component
- `web/src/features/mods/BrowseTab.test.tsx` - Integration tests
- `web/src/api/query-keys.ts` - Update browse key to include page

### Reset Behavior

When these change, reset to page 1:
- Search query changes
- Any filter changes (side, tags, modType, gameVersion)
- Sort option changes

This prevents showing "Page 5 of 2" when filters narrow results.

### Test Scenarios

**Pagination Component:**
1. Renders correct page numbers
2. Highlights current page
3. Disables prev on page 1
4. Disables next on last page
5. Shows ellipsis for many pages
6. Fires onPageChange callback
7. Shows loading state

**BrowseTab Integration:**
1. Shows pagination when results exceed page size
2. Hides pagination for single page
3. Page change updates grid content
4. Filters reset page to 1
5. Search resets page to 1
6. Sort change resets page to 1

**Scroll Restoration:**
1. Position saved on detail navigation
2. Position restored on back
3. Position cleared on filter change
4. Works across page changes

### Git Commit Pattern

```bash
git commit -m "feat(story-10.7/task-1): extend useBrowseMods hook with pagination state"
git commit -m "feat(story-10.7/task-2): create pagination component with page controls"
git commit -m "feat(story-10.7/task-3): integrate pagination into BrowseTab"
git commit -m "feat(story-10.7/task-4): implement scroll position restoration"
```

### References

- `project-context.md` - Critical implementation rules and patterns
- [Source: web/src/hooks/use-browse-mods.ts] - Existing browse hook
- [Source: web/src/features/mods/BrowseTab.tsx] - Browse tab component
- [Source: api/src/vintagestory_api/routers/mods.py:126-204] - Backend pagination implementation
- [Source: api/src/vintagestory_api/models/mods.py:287-318] - Pagination model definitions
- [Source: epics.md#Story-10.7] - Epic requirements (FR80-FR82)
- [Source: 10-6-mod-detail-view.md] - Previous story learnings

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- **Task 1 (2026-01-10):** Extended useBrowseMods hook with internal page state management. Added setPage, goToNextPage, goToPrevPage functions. Page is included in query key for proper caching. Navigation functions respect hasNext/hasPrev from API response. Added 8 new tests for pagination state changes.

- **Task 2 (2026-01-10):** Created Pagination component with prev/next buttons and page number buttons. Implements ellipsis algorithm for large page counts (shows 1, ..., current-1, current, current+1, ..., last). Supports loading state, hides for single page. Added 18 test cases covering rendering, disabled states, interactions, and edge cases.

- **Task 3 (2026-01-10):** Integrated Pagination component into BrowseTab. Connected to useBrowseMods hook pagination state. Added useEffect to reset page to 1 when search/filters/sort change. Pagination controls show loading state during fetch. Added 4 integration tests.

- **Task 4 (2026-01-10):** Implemented scroll position restoration using sessionStorage. Created `useBrowseScrollRestoration` hook with savePosition, restorePosition, clearPosition, and scrollToPosition functions. Added `getSavedScrollState` for synchronous initial page restoration. BrowseTab saves position before navigating to mod detail, restores on mount, and clears when search/filters/sort change. Added 12 hook tests and 3 integration tests.

### File List

**Task 1:**
- Modified: `web/src/hooks/use-browse-mods.ts` - Added pagination state management
- Modified: `web/src/hooks/use-browse-mods.test.tsx` - Added pagination tests

**Task 2:**
- Created: `web/src/components/Pagination.tsx` - Pagination controls component
- Created: `web/src/components/Pagination.test.tsx` - Component tests (18 tests)

**Task 3:**
- Modified: `web/src/features/mods/BrowseTab.tsx` - Integrated Pagination component
- Modified: `web/src/features/mods/BrowseTab.test.tsx` - Added pagination integration tests

**Task 4:**
- Created: `web/src/hooks/use-browse-scroll-restoration.ts` - Scroll position save/restore hook
- Created: `web/src/hooks/use-browse-scroll-restoration.test.ts` - Hook tests (12 tests)
- Modified: `web/src/features/mods/BrowseTab.tsx` - Integrated scroll restoration
- Modified: `web/src/features/mods/BrowseTab.test.tsx` - Added scroll restoration integration tests (3 tests)

