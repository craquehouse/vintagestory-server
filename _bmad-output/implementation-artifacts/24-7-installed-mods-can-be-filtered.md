# Story 24.7: Installed Mods Can Be Filtered

Status: done

<!-- Implements FR341, FR342, Epic 24 ADR-6. Bead: VSS-foq7 (UI-104), closed by this story after merge. Branch story/24-7-installed-mods-can-be-filtered, stacked on story/24-6-rescan-and-unused-files-on-the-installed-tab at 325f7ee0 (24.6 in review); the PR targets main and merges after 24.6's. Web only. -->

## Story

As an **administrator**,
I want **to filter the installed mods by name, compatibility and available update**,
so that **I can find a mod, or the mods that need attention, without scanning the whole list**.

## Acceptance Criteria

1. **Given** installed mods
   **When** I type part of a mod's name or mod ID in the search box, in any letter case
   **Then** only matching mods are shown, on the table and on the cards
   *(FR341; ADR-6 decisions 1 and 6)*

2. **Given** the compatibility select
   **When** I choose Compatible, Not verified or Incompatible
   **Then** only mods with that status are shown; a mod whose status is still loading is shown only under All
   *(FR341; ADR-6 decision 4)*

3. **Given** the "Update available" switch
   **When** I turn it on
   **Then** only mods whose update status is `update_available` are shown; "Update all" and its count are unchanged
   *(FR341; ADR-6 decision 5)*

4. **Given** filters are on
   **When** the list is shown
   **Then** it says "Showing N of M mods" with Clear filters; when nothing matches, the no-match state says so and Clear filters is there
   *(FR342)*

5. **Given** filters are on
   **When** I reload, open the URL directly, or press Back after changing the select or the switch
   **Then** `q`, `compat` and `updates` restore the filters; typing replaces the history entry; an invalid value is ignored; other URL parameters are kept
   *(FR342; ADR-6 decisions 2 and 3)*

6. **(Quality gates.)** `just check` green with 0 skipped unit tests; no suppression added; the E2E passes in the CI set.

## Tasks / Subtasks

- [x] Task 1: The filters (AC: 1 to 5, 6)
  - [x] 1.1: Red first: `web/src/lib/installed-mods-filters.test.ts` (URL parsing and writing, `hasFilters`, `matchesFilters`)
  - [x] 1.2: `installed-mods-filters.ts`; `ModTableRow.compatibilityKnown`; `ModTable` takes `filters` and `onClearFilters`, filters the rows before the table, shows "Showing N of M mods" and the no-match state
  - [x] 1.3: `InstalledModsFilterBar` (search box with clear, compatibility select, "Update available" switch, 44px targets below `lg`); `InstalledTab` reads and writes the URL with `useSearchParams` (typing replaces, the select and switch push), shows the bar when there are mods or filters
  - [x] 1.4: Tests: `InstalledModsFilterBar.test.tsx` (7); `InstalledTab.test.tsx` filters (10), its wrapper now has a `MemoryRouter`; the compatibility mock reads `compat.map` (`vi.hoisted`)
  - [x] 1.5: Commit `feat(story-24.7/task-1): filter installed mods by name, compatibility and available update`

- [x] Task 2: E2E (AC: 5, 6)
  - [x] 2.1: `web/e2e/installed-mods-filters.spec.ts`: the installed list is faked with `page.route`; a filtered URL opened directly; typing and Clear filters
  - [x] 2.2: Commit `test(story-24.7/task-2): check that a filtered Installed tab URL opens filtered`

- [x] Task 3: Validate and move the story to review (AC: all)
  - [x] 3.1: `just check` green; `just changelog` lists Task 1
  - [x] 3.2: Status `review`; sprint status; ADR-6 decision 1 as implemented; Dev Agent Record and File List
  - [x] 3.3: Commit `chore(story-24.7/task-3): validate and move story 24.7 to review`

## Dev Notes

### Decisions made in implementation

- **Rows filtered before the table (ADR-6 decision 1).** The table uses TanStack Table v9 with opt-in features; filtering the rows before `useTable` gives both layouts the same rows without adding the column-filter feature. ADR-6 decision 1 is updated.
- **The URL state lives in `InstalledTab`,** so `ModTable` (and its tests) need no router; `ModTable` only takes `filters` and `onClearFilters`.
- **The filter bar is hidden with no mods installed,** unless a filter is in the URL (so Clear stays reachable).
- **"Showing N of M" is a `role="status"` line,** so a screen reader hears the count change.

### References

- `epics.md` "Story 24.7"; `architecture/epic-24-mod-management-follow-ups.md` ADR-6; `BrowseTab` (URL state), `InstalledModsSortControl` (select pattern)

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5), as the epic's controller.

### Debug Log References

- `just check` (2026-11-20): API 4087 passed, web 3912 passed, 0 skipped; Pyright 0/0; lints green.
- `just changelog`: one entry from this story (Task 1).
- `just test-e2e-ci e2e/installed-mods-filters.spec.ts` (throwaway container): web 2 passed, API E2E 4 passed.

### Completion Notes List

- 2026-11-20 (create-story and dev-story): created from Epic 24's Story 24.7 and ADR-6; Tasks 1 to 3 done.

### File List

- `web/src/lib/installed-mods-filters.ts`, `installed-mods-filters.test.ts` (new)
- `web/src/components/InstalledModsFilterBar.tsx`, `InstalledModsFilterBar.test.tsx` (new)
- `web/src/hooks/use-mods.ts`, `use-mods.test.tsx` (review: a failed lookup reads as not verified)
- `web/src/components/ModTable.tsx`, `InstalledModParts.tsx`, `web/src/features/mods/InstalledTab.tsx`, `InstalledTab.test.tsx` (modified)
- `web/e2e/installed-mods-filters.spec.ts` (new)
- `_bmad-output/planning-artifacts/architecture/epic-24-mod-management-follow-ups.md` (ADR-6 decision 1 as implemented)
- `_bmad-output/implementation-artifacts/24-7-installed-mods-can-be-filtered.md` (this file)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (through `just sprint set` only)

## Review

Reviewer: GLM-5.3-Flash via opencode. Verdict: approve with changes. 0 HIGH, one MEDIUM, six LOW; the MEDIUM and five LOW fixed, one accepted:

1. **MEDIUM: a mod the mod database does not know showed "Not verified" but never matched that filter.** Its lookup answers 404, so it never entered the compatibility map and counted as "loading" forever. `useModsCompatibility` now records a settled failed lookup as `not_verified` (no details), as its badge already showed; only a lookup still in flight counts as loading. The hook test asserts it.
2. **LOW: `type="search"` added a native clear button beside ours.** Now `type="text"`, as `BrowseTab`.
3. **LOW: the clear button was 36px on phones.** 44px; the 44px test covers it.
4. **LOW: a query of only spaces was written to the URL.** Not written; test.
5. **LOW: `setFilters` spread this render's `filters`.** It now applies a partial change to the URL as it is when the update runs.
6. **LOW: no test for the select pushing history.** A test chooses Incompatible, checks the URL, and Back restores the previous filter.
7. **LOW (accepted): a filtered direct URL briefly shows "Showing 0 of M" while lookups load.** The documented result of ADR-6 decision 4; the `role="status"` line announces the correction.

## Change Log

- 2026-11-20: Story 24.7 created and implemented (dev-story): Tasks 1 to 3; status review.
- 2026-11-20: Code review (GLM-5.3-Flash via opencode): approve with changes; 0 HIGH, 1 MEDIUM (fixed), 6 LOW (5 fixed, 1 accepted) (see "Review"). Status done.
