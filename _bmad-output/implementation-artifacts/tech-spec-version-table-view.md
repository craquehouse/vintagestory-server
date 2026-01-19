---
title: 'Version Table View'
slug: 'version-table-view'
created: '2026-01-19'
status: 'implementation-complete'
stepsCompleted: [1, 2, 3, 4]
tech_stack:
  - React 19
  - TypeScript
  - Tailwind CSS v4
  - shadcn/ui Table components
  - TanStack React Table v8
files_to_modify:
  - web/src/components/VersionTable.tsx (new)
  - web/src/components/VersionTable.test.tsx (new)
  - web/src/features/game-server/VersionPage.tsx
code_patterns:
  - TanStack Table with columnHelper (see JobsTable.tsx)
  - shadcn/ui Table primitives (Table, TableHeader, TableBody, TableRow, TableHead, TableCell)
  - Tailwind responsive classes for column hiding (hidden sm:table-cell)
test_patterns:
  - vitest + @testing-library/react + userEvent
  - data-testid pattern: {component}-{item}-{id}
  - Co-located tests (*.test.tsx alongside component)
---

# Tech-Spec: Version Table View

**Created:** 2026-01-19
**Bead:** VSS-lvp [UI-033]

## Overview

### Problem Statement

The current card-based grid for displaying VintageStory server versions wastes vertical space and makes it difficult to compare versions at a glance. Users need better information density for version selection.

### Solution

Replace `VersionGrid` (card layout) with a new `VersionTable` component using a sortable, responsive table layout with an action column.

### Scope

**In Scope:**
- New `VersionTable` component with columns: Version, Channel, Size, Status (badges), Actions
- Sortable columns (click header to sort)
- Responsive column hiding on small screens
- Loading skeleton state (table rows)
- Empty state
- Existing click-to-install behavior via action button
- Tests for the new component

**Out of Scope:**
- Adding release date (not available in API)
- Card/table view toggle (replacing entirely)
- Changes to `VersionCard` component (kept for potential future use)
- Changes to install dialog behavior

## Context for Development

### Codebase Patterns

- **Tables:** Two patterns exist - TanStack Table (`JobsTable`) or plain shadcn/ui (`ModTable`). Use TanStack for sortable columns.
- **TanStack Table Setup:** `columnHelper`, `useReactTable`, `getCoreRowModel`, `getSortedRowModel` (for sorting)
- **Tests:** vitest + @testing-library/react, co-located `*.test.tsx` files
- **Test IDs:** Pattern `{component}-{item}-{id}` (e.g., `version-row-1.20.0`)
- **Responsive:** Tailwind classes like `hidden sm:table-cell` for column hiding

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `web/src/components/JobsTable.tsx` | **Primary reference** - TanStack Table with columnHelper |
| `web/src/components/ModTable.tsx` | Table with action buttons pattern |
| `web/src/components/VersionGrid.tsx` | Current implementation (to be replaced in VersionPage) |
| `web/src/components/VersionCard.tsx` | Data display patterns, badge styling |
| `web/src/components/ui/table.tsx` | shadcn/ui Table primitives |
| `web/src/features/game-server/VersionPage.tsx` | Consumer - update to use VersionTable |
| `web/src/api/types.ts` | `VersionInfo` type definition |

### Technical Decisions

- **TanStack Table** for built-in sorting support via `getSortedRowModel`
- **Sortable columns:** Version (default desc), Channel, Size
- **Action column** with "Select" button instead of row click (better accessibility, matches ModTable pattern)
- **Sort state:** Local to component (not persisted across sessions)
- **Responsive column hiding:** Hide Size on mobile (`hidden sm:table-cell`), show all on desktop
- **Status badges:** Keep existing badge styling from VersionCard (Latest, Installed, isNewer ring)

## Implementation Plan

### Tasks

- [x] **Task 1: Create VersionTable component**
  - File: `web/src/components/VersionTable.tsx` (new)
  - Action: Create sortable table component using TanStack Table
  - Details:
    - Import TanStack Table: `createColumnHelper`, `useReactTable`, `getCoreRowModel`, `getSortedRowModel`, `flexRender`, `SortingState`
    - Import shadcn/ui: `Table`, `TableHeader`, `TableBody`, `TableRow`, `TableHead`, `TableCell`
    - Import `Badge`, `Button` from shadcn/ui
    - Props interface: `versions: VersionInfo[]`, `isLoading?: boolean`, `installedVersion?: string | null`, `onVersionSelect?: (version: string) => void`
    - Columns: Version (with changelog link), Channel (badge), Size (hidden on mobile), Status (Latest/Installed badges), Actions (Select button)
    - Sorting: `useState<SortingState>` with default `[{ id: 'version', desc: true }]`
    - Sortable header cells with click handler and sort indicator (arrow up/down)
    - Row highlighting for `isNewer` versions (use ring styling like VersionCard)
    - Loading state: Skeleton table rows (8 rows)
    - Empty state: "No versions found for this channel."

- [x] **Task 2: Create VersionTable tests**
  - File: `web/src/components/VersionTable.test.tsx` (new)
  - Action: Write comprehensive tests following VersionGrid.test.tsx patterns
  - Tests to include:
    - Renders table with version data (all columns)
    - Shows loading skeleton when `isLoading={true}`
    - Shows empty state when versions array is empty
    - Passes `installedVersion` - shows "Installed" badge on matching row
    - Calls `onVersionSelect` when Select button clicked
    - Sorting: clicking column header changes sort order
    - Sorting: default sort is version descending
    - Responsive: Size column has hidden class on mobile
    - Newer version highlighting (ring styling when `version > installedVersion`)

- [x] **Task 3: Update VersionPage to use VersionTable**
  - File: `web/src/features/game-server/VersionPage.tsx`
  - Action: Replace `VersionGrid` import and usage with `VersionTable`
  - Changes:
    - Replace import: `VersionGrid` → `VersionTable`
    - Update JSX: `<VersionGrid ... />` → `<VersionTable ... />`
    - Rename prop: `onVersionClick` → `onVersionSelect` (if different)
    - Remove `VersionGrid` import (no longer used in this file)

- [x] **Task 4: Run tests and verify**
  - Action: Run `just test-web` and fix any failures
  - Verify: All new tests pass, existing VersionPage tests still pass

### Acceptance Criteria

- [x] **AC 1:** Given the VersionPage is loaded, when versions are fetched, then they display in a table format with columns: Version, Channel, Size, Status, Actions
- [x] **AC 2:** Given the table is displayed, when clicking a sortable column header, then the table sorts by that column (toggle asc/desc)
- [x] **AC 3:** Given the table is displayed, when on mobile viewport (<640px), then the Size column is hidden
- [x] **AC 4:** Given versions are loading, when `isLoading` is true, then skeleton rows are displayed
- [x] **AC 5:** Given no versions match the filter, when versions array is empty, then "No versions found" message is displayed
- [x] **AC 6:** Given a version row, when clicking the "Select" button, then `onVersionSelect` is called with the version string
- [x] **AC 7:** Given `installedVersion` matches a row, when that row renders, then it shows an "Installed" indicator
- [x] **AC 8:** Given `installedVersion` is set, when a version is newer, then that row has ring highlighting
- [x] **AC 9:** Given all changes are complete, when running `just test-web`, then all tests pass

## Additional Context

### Dependencies

- **Already installed:**
  - `@tanstack/react-table` v8.21.3
  - shadcn/ui Table component (`web/src/components/ui/table.tsx`)
  - shadcn/ui Badge, Button components
- **No new dependencies required**

### Testing Strategy

**Unit Tests (VersionTable.test.tsx):**
- Render tests for each column
- Sorting behavior (click header, verify order change)
- Loading skeleton state
- Empty state
- Installed version indicator
- Newer version highlighting
- Select button callback

**Integration (existing tests):**
- `VersionPage.test.tsx` should continue to pass (if it tests the page, not specific grid behavior)

**Manual Verification:**
- Visual inspection in browser at different viewport widths
- Verify sorting feels responsive
- Verify Select button opens install dialog

### Notes

- `VersionCard` and `VersionGrid` components preserved for potential future use (not deleted)
- Sorting uses string comparison for versions - this works for VintageStory versions (e.g., "1.19.8" < "1.20.0")
- The changelog external link pattern from VersionCard should be replicated in the Version column
- Consider: TanStack Table's `getSortedRowModel` handles the sorting logic; we just need to manage `SortingState`
