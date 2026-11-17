# Story 21.5: Version Sort, Sort State for Screen Readers and Close Buttons

Status: ready-for-dev

<!-- Implements FR275-FR277, Epic 21 ADR-8 and ADR-9. Beads: VSS-qxxo (UI-099), VSS-whnb (UI-100), VSS-759m (UI-101), VSS-nuef (UI-095). Stacked on Story 21.4 (stories run in order 21.1 to 21.8, each on the previous one). Line references were verified at 966204f (epic-21-planning, before Story 21.1's Prettier reformat) and must be re-checked at implementation time: Story 21.1 reformats every web file and Story 21.4 edits ModTable.tsx and its test. Each place is also named by symbol so it can be found again. Web only; no API change. No new dependency. -->

## Story

As a **user of the tables and dialogs**,
I want **versions in their real order, the sort order announced, and close buttons I can hit**,
so that **a pre-release is not listed as newer than its release, a screen reader tells me how a table is sorted, and I can close a dialog on a phone**.

## Acceptance Criteria

1. **Given** installed mods with the versions `1.0.0`, `1.0.0-rc.2`, `1.0.0-rc.12`, `1.9.0` and `1.10.0`
   **When** I sort by Version ascending
   **Then** the order is `1.0.0-rc.2`, `1.0.0-rc.12`, `1.0.0`, `1.9.0`, `1.10.0`, and descending is the exact reverse, in the table (1024px and up) and in the cards below 1024px
   *(Covers FR275; `VSS-qxxo`)*

2. **Given** the Version page's table with `1.22.0` and `1.22.0-rc.1`
   **When** I sort by Version ascending
   **Then** `1.22.0-rc.1` comes before `1.22.0`; descending (the default) puts `1.22.0` first
   *(Covers FR275; found in planning)*

3. **Given** an installed game version `1.22.0-rc.2` and a listed version `1.22.0-rc.12`
   **When** the Version page marks newer versions
   **Then** the `1.22.0-rc.12` row is marked as newer and the `1.22.0-rc.1` row is not
   *(Covers FR275; found in planning)*

4. **Given** versions the strict rule cannot read as they are (for example `1.2`, `v1.0.0`, `beta`)
   **When** a table sorts them with others
   **Then** nothing throws; a leading `v` is ignored and a missing numeric part counts as 0, so `1.2` and `v1.0.0` sort as `1.2.0` and `1.0.0`; strings with no version in them (`beta`, an empty string, `1.0.0 hotfix`) come after every version that can be read, ordered among themselves by a numeric-aware comparison; and the order is the same on every render and for every input order (Dev Notes "The comparison")
   *(Covers FR275; ADR-8 decision 3, see "ADR against the code")*

5. **Given** the web's dependencies
   **When** the story is done
   **Then** no package was added for the comparison (`web/package.json` and `web/bun.lock` unchanged), and the two tables, the "newer" mark and the server version dialog's upgrade/downgrade decision use one function, `compareVersions` in `web/src/lib/version-compare.ts`; the private `compareVersions` in `VersionTable.tsx` is gone
   *(Covers FR275)*

6. **Given** the Version page with installed game version `1.21.9`, or `1.21.6-pre.1`
   **When** I select `1.21.10`, or `1.21.6`
   **Then** the dialog is titled "Upgrade Server Version" with an "Upgrade" button and no downgrade warning; selecting `1.21.8` from `1.21.9` still gives "Downgrade Server Version" with the warning and its checkbox
   *(Covers FR275; found in this story, backlog drawdown, see "ADR against the code")*

7. **Given** the installed mods table sorted by Name ascending
   **When** a screen reader reads the header row
   **Then** the Name header (`th`) has `aria-sort="ascending"`, the Version and Status headers have `aria-sort="none"`, and the Available, Side, Compatibility and Actions headers have no `aria-sort`
   *(Covers FR276; `VSS-whnb`)*

8. **Given** either sortable table (installed mods, Version page)
   **When** I change the sort column or its direction
   **Then** `aria-sort` moves with it: `ascending` or `descending` on the sorted column and `none` on the other sortable columns; on the Version page, when a click removes the sort (Dev Notes "Version table sort cycle"), every sortable column reads `none`; columns that cannot be sorted never get the attribute
   *(Covers FR276)*

9. **Given** either table's sort chevrons
   **When** the accessibility tree is read
   **Then** each chevron `svg` has `aria-hidden="true"`, and the column headers' accessible names are the bare labels (`Name`, `Version`, `Status`; `Version`, `Channel`, `Size`)
   *(Covers FR276; ADR-9 decision 2)*

10. **Given** `VersionTable.tsx`
    **When** I read how it uses column meta
    **Then** it reads `meta.className` with no type assertion (no `as` on `columnDef.meta`), and the rendered classes are the same as before (the Size header and cells keep `hidden sm:table-cell`)
    *(`VSS-759m`; a refactor with no requirement of its own)*

11. **Given** any dialog with a close button (`ui/dialog.tsx`), and the phone navigation sheet (`ui/sheet.tsx`)
    **When** I measure the close button at 390px and at 1440px (the sheet at 390px only: it exists only below 768px)
    **Then** it is at least 44 by 44px, its icon is where it was (16px from the top and right edges of the dialog or sheet, within 1px), it does not cover the dialog's title text, and clicking it closes the dialog or sheet
    *(Covers FR277; `VSS-nuef`)*

12. **Given** every existing test
    **When** the suites run
    **Then** they pass, apart from the changes listed in Dev Notes "Existing tests that change"; no test is skipped; no lint or type suppression and no `cast`/`as` assertion is added

## Tasks / Subtasks

<!-- Each functional task includes its tests in the same commit. Commit per task: type(story-21.5/task-N): ...; feat/fix only for changes an admin can see, subject written for admins (the release-note subjects below come from the change proposal, section 2). Red first. Run Prettier (Story 21.1's setup) on every web file this story changes, and only on those. -->

- [ ] Task 1: One `compareVersions`; both tables and the "newer" mark use it + tests (AC: 1, 2, 3, 4, 5) (`VSS-qxxo`)
  - [ ] 1.1: New `web/src/lib/version-compare.ts` exporting `compareVersions(a: string, b: string): number` (returns -1, 0 or 1) as in Dev Notes "The comparison" (ADR-8 decisions 2 to 4). A module doc comment names Semantic Versioning 2.0.0 precedence, the loose-input rules and Epic 21 ADR-8. No package added
  - [ ] 1.2: New `web/src/lib/version-compare.test.ts`, table-driven (`it.each`), every row of Dev Notes "Unit tests: compareVersions"; red first (the module first exports a stub returning 0)
  - [ ] 1.3: `ModTable.tsx`, the `version` accessor column (`columnHelper.accessor('version', ...)`, `:271-282`): add `sortFn: (rowA, rowB) => compareVersions(rowA.original.version, rowB.original.version)` after `cell` (as the `name` column does at `:265-269`); import from `@/lib/version-compare`. The cards (`:408`) use the same sorted rows, so they follow with no change
  - [ ] 1.4: `VersionTable.tsx`: delete the private `compareVersions` and its doc comment (`:70-101`); import the shared one. The Version column's `sortFn: 'alphanumeric'` (`:161`) becomes the same `sortFn` on `rowA.original.version`. The `isNewer` computation (`rowData`, `:309-319`, call at `:314`) keeps `compareVersions(version.version, installedVersion) > 0`, now the shared function. The Channel and Size columns keep `'alphanumeric'` (`:178`, `:190`; see "Not changed")
  - [ ] 1.5: Table tests (Dev Notes "Unit tests: tables", Task 1 rows), red first: run them against the current code and see them fail before 1.3 and 1.4
  - [ ] 1.6: Commit `fix(story-21.5/task-1): sort versions with pre-releases before their release` (ADR-8 Consequences; the function and its users in one commit, since the function alone changes nothing a user sees)

- [ ] Task 2: The server version dialog calls a newer version an upgrade + tests (AC: 5, 6) (backlog drawdown; no bead)
  - [ ] 2.1: `InstallVersionDialog.tsx` `getActionType` (`:61-70`): replace the string comparison and its comment (`:67-69`) with `return compareVersions(targetVersion, installedVersion) > 0 ? 'upgrade' : 'downgrade';`. The `install` and `reinstall` branches (`:65-66`) stay first and unchanged (see "Not changed"). Update the function's doc comment (`:54-60`) to say it uses Semantic Versioning precedence
  - [ ] 2.2: Tests (Dev Notes "Existing tests that change" and "Unit tests: tables", Task 2 rows), red first
  - [ ] 2.3: Commit `fix(story-21.5/task-2): call a move to a newer server version an upgrade, not a downgrade` (a new release note, not in the proposal's list; see "ADR against the code")

- [ ] Task 3: `aria-sort` on every sortable header, chevrons hidden + tests (AC: 7, 8, 9) (`VSS-whnb`)
  - [ ] 3.1: New `web/src/lib/table-aria-sort.ts` exporting `ariaSort(canSort: boolean, sorted: false | 'asc' | 'desc'): 'ascending' | 'descending' | 'none' | undefined` (`undefined` when `!canSort`), with `web/src/lib/table-aria-sort.test.ts` covering the four results. One helper keeps the two tables' mapping identical
  - [ ] 3.2: `ModTable.tsx` header loop (`<TableHead key={header.id} ...>`, `:380`): add `aria-sort={ariaSort(header.column.getCanSort(), header.column.getIsSorted())}` on the `th` (ADR-9 decision 2: set where the `th` is rendered; `SortableHeader` stays a button inside the cell). `SortableHeader` (`:91-112`): `aria-hidden="true"` on both chevrons (`:107-108`); the empty spacer (`:109`) stays
  - [ ] 3.3: `VersionTable.tsx` header loop (`:349-391`): replace the local mapping (`ariaSort`, `:354-359`) with the helper, so unsorted sortable columns get `none`. `SortIndicator` (`:122-129`): `aria-hidden="true"` on both chevrons. Keep `tabIndex`, `role`, `onClick`, `onKeyDown` as they are (see "Not changed")
  - [ ] 3.4: Tests (Dev Notes "Unit tests: tables", Task 3 rows) through the accessibility tree (`getByRole('columnheader', { name })`), red first; update the one existing test listed in "Existing tests that change"
  - [ ] 3.5: Commit `fix(story-21.5/task-3): announce the sort order of table columns to screen readers` (ADR-9 Consequences)

- [ ] Task 4: Column meta without casts in `VersionTable.tsx` + tests (AC: 10) (`VSS-759m`)
  - [ ] 4.1: `:352` becomes `const meta = header.column.columnDef.meta;` and `:407` `const cellMeta = cell.column.columnDef.meta;` (or read `?.className` inline, as `ModTable.tsx:380` and `:393` do). The typed `ColumnMeta` in `web/src/lib/table-column-meta.d.ts` gives `className` (Story 18.4). A prototype at 966204f type-checked clean (`bunx tsc --noEmit`) with both casts removed
  - [ ] 4.2: The existing test "Size column has hidden class for mobile" (`VersionTable.test.tsx:220-227`) pins the header class; add one assertion that a Size body cell (the `td` around `version-table-size-<v>`) has `hidden` and `sm:table-cell`. `rg "columnDef.meta as" web/src` finds nothing afterwards
  - [ ] 4.3: Commit `refactor(story-21.5/task-4): read VersionTable column classes without type assertions` (ADR-9 decision 3)

- [ ] Task 5: 44px close buttons on dialogs and the navigation sheet + tests, and the story's E2E (AC: 1, 2, 3, 6, 7, 8, 11) (`VSS-nuef`)
  - [ ] 5.1: `web/src/components/ui/dialog.tsx` `DialogContent`'s close (`DialogPrimitive.Close`, `:72-78`, classes `:74`): replace `top-4 right-4` with `top-0.5 right-0.5 inline-flex size-11 items-center justify-center`; keep every other class (the icon stays `size-4`). Dev Notes "Close button geometry"
  - [ ] 5.2: `web/src/components/ui/sheet.tsx` `SheetContent`'s close (`SheetPrimitive.Close`, `:73-76`): the same replacement, and add `data-slot="sheet-close"` (the dialog's has `data-slot="dialog-close"`) for the tests
  - [ ] 5.3: Unit tests (Dev Notes "Unit tests: close buttons"); the real size is the E2E's job (jsdom has no layout, ADR-9 decision 5)
  - [ ] 5.4: Commit `fix(story-21.5/task-5): make dialog close buttons easier to tap` (ADR-9 Consequences)
  - [ ] 5.5: New `web/e2e/version-sort-and-close-buttons.spec.ts`, untagged (it needs no mod database and no game server), read-only (Dev Notes "E2E"); it covers this task and Tasks 1 to 3
  - [ ] 5.6: `web/e2e/README.md`: raise the counts of untagged tests and of all tests (`:10`, `:50`) by the number of tests the new spec adds; take the base numbers from the README as it stands after Story 21.4 and confirm with `cd web && bunx playwright test --list`
  - [ ] 5.7: Rebuild the stack from this branch (`just docker restart`, which does not start the game server), run `cd web && bunx playwright test e2e/version-sort-and-close-buttons.spec.ts` with `VS_API_KEY_ADMIN` exported, then `e2e/layout-widths.spec.ts`, `e2e/installed-mods-phone.spec.ts` and `e2e/mod-detail-media.spec.ts` (they use the table headers, the sort control and the screenshot dialog). Then `just test-e2e-ci e2e/version-sort-and-close-buttons.spec.ts` to prove it passes on the CI stack. Do not start or stop the game server; no screenshots
  - [ ] 5.8: Commit `test(story-21.5/task-5): check version order, sort state and close button size in the browser`

- [ ] Task 6: Quality gate and review hand-off (AC: all, 12)
  - [ ] 6.1: `just check` passes (lint including Prettier's check, typecheck including `web/e2e`, all tests); no skipped web test; the diff adds no suppression, no `cast` and no `as` assertion; `web/package.json` and `web/bun.lock` unchanged (`git diff --stat <base>.. -- web/package.json web/bun.lock` is empty)
  - [ ] 6.2: Manual check on the Docker stack (needs the maintainer's confirmation before it is ticked, `project-context.md`): Dev Notes "Manual check"
  - [ ] 6.3: Story status `review`, `just sprint set 21-5-version-sort-aria-sort-close-buttons review`, PR (base: Story 21.4's branch while its PR is open, otherwise `main`); PR link on `VSS-qxxo`, `VSS-whnb`, `VSS-759m`, `VSS-nuef`. The PR description says "API contract changes: none" and lists the four release-note subjects (Tasks 1, 2, 3, 5). Commit `chore(story-21.5/task-6): move story 21.5 to review`

## Dev Notes

### What is wrong today (verified at 966204f)

- **Installed mods (`VSS-qxxo`).** `web/src/components/ModTable.tsx` `version` column (`:271-282`) has no `sortFn`, so TanStack Table 9.3.1 picks one by itself; on version strings it orders numbers as numbers but puts a release before its pre-releases (`1.0.0, 1.0.0-rc.2, 1.0.0-rc.12, 1.9.0, 1.10.0`, Epic 21 facts "Tables and dialogs today"). The cards below 1024px render `table.getRowModel().rows` (`:408`), so they have the same order.
- **Version page.** `web/src/components/VersionTable.tsx:161` asks for `sortFn: 'alphanumeric'`, with the same fault. The private `compareVersions` (`:70-101`), used only for the "newer" row highlight (`isNewer`, `:313-315`, rendered as `bg-primary/5` at `:403`), splits on the first `-` and compares the pre-release with `localeCompare` (`:100`), so `rc.12` sorts before `rc.2`.
- **Server version dialog (found while writing this story).** `web/src/components/InstallVersionDialog.tsx` `getActionType` (`:61-70`) compares with `>` on strings (`:69`). `'1.21.10' > '1.21.9'` is false, so an upgrade from `1.21.9` to `1.21.10` is titled "Downgrade Server Version", shows the downgrade warning and needs its checkbox (`isDowngrade`, `:167`; `isInstallDisabled`, `:185-188`); a move from `1.21.6-pre.1` to `1.21.6` is also a "downgrade". `InstallVersionDialog.test.tsx:102-113` pins the pre-release case as a known limitation of Epic 13 ADR-1. It opens from the same Version page table (`VersionPage.tsx:169-177`).
- **`aria-sort` (`VSS-whnb`).** `ModTable.tsx`'s `th` (`:380`) has none; `SortableHeader` (`:91-112`) is a button with a chevron. `VersionTable.tsx` sets `ascending`/`descending` and leaves the attribute off when a sortable column is not sorted (`:354-359`, `:381`). No other table sorts (`JobsTable` has no sort).
- **Casts (`VSS-759m`).** `VersionTable.tsx:352` and `:407` read `columnDef.meta as { className?: string } | undefined`; `web/src/lib/table-column-meta.d.ts` types `ColumnMeta.className` since Story 18.4.
- **Close buttons (`VSS-nuef`).** `ui/dialog.tsx:72-78`: the close button has no size of its own, so it is the 16px icon at `top-4 right-4`. `ui/sheet.tsx:73-76`: the same. The sheet is the phone navigation menu (`components/layout/Layout.tsx:24-32`, opened by the "Open menu" button, `Header.tsx:27-35`, `md:hidden`). Dialogs with a close button today: `InstallVersionDialog`, `InstallConfirmDialog`, `UpdateAllDialog`, `ModScreenshotGallery` (its own padding `p-3 sm:p-4`). Alert dialogs (`ui/alert-dialog.tsx`) have no close button and are not touched.

### The comparison (Task 1)

`compareVersions(a, b)` returns -1, 0 or 1 and never throws.

1. **Reading a version.** One regular expression, case-insensitive: `^v?(\d+(?:\.\d+)*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+[0-9A-Za-z.-]+)?$`. Group 1 is the numeric core (one or more parts, so `1.2` and `1.0.0.1` are read), group 2 the pre-release identifiers; build metadata after `+` is matched and dropped. No trimming: `' 1.0.0'` is unreadable.
2. **Two readable versions** (Semantic Versioning 2.0.0, section 11): core parts compared as numbers, part by part, a missing part counts as 0. Then a version without a pre-release is greater than one with. Then identifiers one by one: both numeric (`^\d+$`) compare as numbers; a numeric identifier is lower than an alphanumeric one; two alphanumeric ones compare in ASCII order (`<`/`>` on the strings, not `localeCompare`); if all shared identifiers are equal, the shorter list is lower.
3. **Unreadable strings** come after every readable one; two unreadable strings compare with a module-level `new Intl.Collator('en', { numeric: true })` (an explicit locale, so the order does not depend on the browser's).
4. **Tie-break for a total order.** When the steps above give 0 (`1.0.0` vs `v1.0.0` vs `1.0.0+build` vs `1.0`), compare the original strings with `<`/`>`; only identical strings give 0. So sorting any permutation of a list gives one result, and a descending sort is the exact reverse of the ascending one (TanStack negates the result for `desc` and falls back to row index only on 0, `@tanstack/table-core/dist/features/row-sorting/` sorted row model).
5. Numbers are compared with `Number()`; parts beyond 2^53 lose precision and fall to the tie-break. Acceptable: no real version has such parts.

A prototype of exactly these rules (since discarded) sorted `1.10.0, 1.0.0, beta, 1.0.0-rc.12, 1.9.0, 1.0.0-rc.2, v1.0.1, 1.2, 1.0.0+b, 1.0.0-alpha, 1.0.0-alpha.1, 1.0.0-1, 1.0.0.1, alpha` into `1.0.0-1 < 1.0.0-alpha < 1.0.0-alpha.1 < 1.0.0-rc.2 < 1.0.0-rc.12 < 1.0.0 < 1.0.0+b < 1.0.0.1 < v1.0.1 < 1.2 < 1.9.0 < 1.10.0 < alpha < beta`.

### Unit tests: compareVersions (`web/src/lib/version-compare.test.ts`)

Table-driven. A helper `sorted(list)` returns `[...list].sort(compareVersions)`; ordering rows give a shuffled input and the expected output, pair rows give `a`, `b` and the sign.

| Rule | Cases |
|---|---|
| Bead and AC 1 | shuffled `1.0.0, 1.0.0-rc.2, 1.0.0-rc.12, 1.9.0, 1.10.0` → `1.0.0-rc.2, 1.0.0-rc.12, 1.0.0, 1.9.0, 1.10.0` |
| Facts sample (ADR-8 decision 5) | shuffled `1.0.0, 1.0.0-pre.1, 1.0.0-rc.2, 1.0.0-rc.12, 1.0.1, 1.9.0, 1.10.0, 1.22.0, 1.22.0-rc.1` → `1.0.0-pre.1, 1.0.0-rc.2, 1.0.0-rc.12, 1.0.0, 1.0.1, 1.9.0, 1.10.0, 1.22.0-rc.1, 1.22.0` |
| Semantic Versioning's own example | `1.0.0-alpha < 1.0.0-alpha.1 < 1.0.0-alpha.beta < 1.0.0-beta < 1.0.0-beta.2 < 1.0.0-beta.11 < 1.0.0-rc.1 < 1.0.0` |
| Numeric core | `1.9.0 < 1.10.0`, `1.10.0 < 2.0.0`, `0.1.0 < 1.0.0-rc.1` |
| Numeric identifiers | `1.0.0-2 < 1.0.0-10`, `1.0.0-rc.1.2 < 1.0.0-rc.1.10` |
| Numeric before alphanumeric | `1.0.0-1 < 1.0.0-alpha`, `1.0.0-rc.1 < 1.0.0-rc.a` |
| Alphanumeric in ASCII order | `1.0.0-RC.1 < 1.0.0-rc.1`, `1.0.0-alpha < 1.0.0-beta`, `1.0.0-pre.1 < 1.0.0-rc.1` |
| Shorter identifier list first | `1.0.0-alpha < 1.0.0-alpha.1`, `1.0.0-rc < 1.0.0-rc.0` |
| Build metadata ignored | `1.0.0-rc.1+build.9 < 1.0.0`, `1.0.0+zzz < 1.0.1`, `1.0.0-rc.12+a > 1.0.0-rc.2+b` |
| Leading `v` | `v1.10.0 > 1.9.0`, `V2.0.0 > v1.0.0` |
| Missing parts | `1.2 > 1.1.9`, `1.2 < 1.2.1`, `1 < 1.0.1`, `1.0.0.1 > 1.0.0`, `1.2-rc.1 < 1.2` |
| Unreadable after readable | shuffled `beta, 1.0.0, , 1.0.0 hotfix, 0.0.1, build 10, build 9` → `0.0.1, 1.0.0, , 1.0.0 hotfix, beta, build 9, build 10` (checked with `Intl.Collator('en', { numeric: true })` in Node: `'', '1.0.0 hotfix', 'beta', 'build 9', 'build 10'`) |
| Malformed is unreadable, never throws | `1..0`, `.1`, `1.0.0-`, `1.0.0-rc..1`, `1.0.0+`, `-1.0.0`, `1.0.0 `: each sorts after `99.0.0` and `compareVersions` does not throw |
| Equal precedence, total order | `compareVersions(x, x) === 0`; `1.0.0` vs `v1.0.0` vs `1.0.0+b` vs `1.0` all non-zero and ordered by the plain strings |
| Properties | for every pair of a 20-item mixed list: `compareVersions(a, b) === -compareVersions(b, a)`; sorting 5 different permutations of the list (fixed, written out, no randomness) gives one result |

### Unit tests: tables

New tests use `vi.stubGlobal('fetch', ...)` with `vi.unstubAllGlobals()` in their `describe`'s `afterEach` (`project-context.md`, Story 20.2), not `globalThis.fetch =` assignment as the older tests in `ModTable.test.tsx` do; do not convert the older tests.

| Task | File | Test |
|---|---|---|
| 1 | `ModTable.test.tsx`, new `describe('version sort (Story 21.5)')` | Five mods (AC 1's versions, names chosen so name order differs from version order). Sort preference cookie `installedModsSort: { column: 'version', direction: 'asc' }` (pattern: `:1408-1422`): `mod-row-*` order is AC 1's; `direction: 'desc'`: the exact reverse. Same two at phone width (`setViewportWidth(390)`, `cardSlugs()` pattern `:1742-1747`). One test clicks the Version header twice from the default (Name ascending) and checks ascending, then descending |
| 1 | `VersionTable.test.tsx`, `describe('sorting')` | Versions `1.22.0` (stable, latest), `1.22.0-rc.1`, `1.22.0-rc.2`, `1.22.0-rc.12` (unstable), `1.21.10`, `1.21.9`: default (descending) row order `1.22.0, 1.22.0-rc.12, 1.22.0-rc.2, 1.22.0-rc.1, 1.21.10, 1.21.9`; click Version twice (Dev Notes "Version table sort cycle"): ascending, the exact reverse |
| 1 | `VersionTable.test.tsx`, `describe('newer version highlighting')` | `installedVersion="1.22.0-rc.2"`: rows `1.22.0-rc.12` and `1.22.0` have `bg-primary`; `1.22.0-rc.2`, `1.22.0-rc.1`, `1.21.10` do not (AC 3). Fails today on `rc.12` |
| 2 | `InstallVersionDialog.test.tsx`, `describe('getActionType')` | `getActionType('1.21.10', '1.21.9')` is `upgrade`, `('1.21.9', '1.21.10')` `downgrade`, `('1.21.6', '1.21.6-pre.1')` `upgrade`, `('1.21.6-pre.1', '1.21.6')` `downgrade`, `('1.22.0-rc.12', '1.22.0-rc.2')` `upgrade` |
| 2 | `InstallVersionDialog.test.tsx`, rendering | with `installedVersion="1.21.9"` and version `1.21.10`: `dialog-title` is "Upgrade Server Version", `confirm-button` reads "Upgrade", no `downgrade-warning` (pattern of the "shows Downgrade" test, `:223-239`) |
| 3 | `ModTable.test.tsx`, new `describe('aria-sort (Story 21.5)')` | Default sort: `getByRole('columnheader', { name: 'Name' })` has `aria-sort="ascending"`, `Version` and `Status` `none`; `Available`, `Side`, `Compatibility` and the Actions header (`getAllByRole('columnheader')` last) have no `aria-sort`. Click the Version header button: Version `ascending`, Name `none`; again: `descending`. Click the Status header: Status `descending` (TanStack's first direction for a non-string column, Dev Notes "Version table sort cycle"), Name and Version `none`. Every chevron `svg` inside the header row has `aria-hidden="true"` |
| 3 | `VersionTable.test.tsx`, `describe('accessibility')` | Default: Version `descending`, Channel and Size `none`, Status and Actions no attribute. Click Channel: Channel `ascending`, Version `none`. Click Version from the default once: every sortable column `none`; again: Version `ascending`. Chevron `svg` `aria-hidden="true"`. Headers found with `getByRole('columnheader', { name: 'Version' })` (the explicit `role="columnheader"` on sortable `th` keeps them in the tree) |
| 3 | `web/src/lib/table-aria-sort.test.ts` | `(true, 'asc')` → `ascending`, `(true, 'desc')` → `descending`, `(true, false)` → `none`, `(false, false)` → `undefined` |

### Version table sort cycle

TanStack 9.3.1 `column_getNextSortingOrder` (`node_modules/@tanstack/table-core/dist/features/row-sorting/rowSortingFeature.utils.js:231-237`): the first direction is `asc` for string values and `desc` otherwise (`column_getAutoSortDir`, `:121-129`); when the current direction is not the first and sorting removal is enabled, the next click removes the sort. `VersionTable` does not set `enableSortingRemoval` (`:321-327`), so from its default (Version descending) one click on Version removes the sort (rows in API order, every sortable column `none`), the next gives ascending. `ModTable` sets `enableSortingRemoval: false` (`:350`), so it only flips. This story keeps both behaviours; the tests above follow them.

### Close button geometry (Task 5)

Today the button is the bare 16px icon at 16px (`top-4`, `right-4`) from the top and right edges, so the icon's centre is 24px in. A 44px box with the icon centred keeps that centre if its edges are 24 - 22 = 2px in: `top-0.5 right-0.5 size-11` with `inline-flex items-center justify-center`. The icon does not move (ADR-9 decision 4). The `data-[state=open]:bg-accent` / `bg-secondary` classes stay inert: Radix's `Close` renders no `data-state` (`@radix-ui/react-dialog/dist/index.mjs`, the `DialogClose` `Primitive.button`), so the larger box stays invisible except for the focus ring.

Overlap: the box covers 2-46px from the top and right edges; dialog content starts 24px in (`p-6`). At 390px the dialog is 358px wide with centred header text (`text-center sm:text-left`, `DialogHeader`), and the longest title ("Downgrade Server Version", "Reinstall Server Version") is about 240px wide, so it ends about 59px from the right edge; at 1440px titles are left-aligned in a 512px dialog. No title reaches the box, so no header padding is added. The E2E measures it (AC 11); if a title does reach the box, add right padding to `DialogHeader` only while a close button is shown and record it in the Completion Notes. The screenshot dialog's box lies over the image's top-right corner, as the icon does today. The navigation sheet's box lies inside the sidebar's 48px logo row (`Sidebar.tsx:133-154`, logo on the left).

### Unit tests: close buttons

- `ui/dialog.test.tsx` `describe('DialogContent')` (`:180`): the built-in close (`getByRole('button', { name: 'Close' })`) has `data-slot="dialog-close"` and the classes `size-11`, `top-0.5`, `right-0.5`, and its `svg` has no `size-` override (still 16px through `[&_svg:not([class*='size-'])]:size-4`). `showCloseButton={false}` still renders none (`:226-237`, unchanged).
- New `web/src/components/ui/sheet.test.tsx`: an open `Sheet` with `SheetContent` renders a close button named "Close" with `data-slot="sheet-close"` and `size-11`; clicking it closes the sheet (`onOpenChange` called with `false`). `components/layout/Layout.test.tsx` (`:110-147`) already covers opening and closing the navigation sheet and stays unchanged.

### Existing tests that change (deliberately)

Found by running the whole web suite against a throwaway prototype of Tasks 1 to 5 (since discarded): 3,308 tests, 2 failed, both expected:

- `web/src/components/VersionTable.test.tsx:393-403` "has aria-sort on sorted column": `:402` expects Channel to have no `aria-sort`; it becomes `toHaveAttribute('aria-sort', 'none')` (AC 8). Rename the test "marks the sorted column and sets none on the other sortable columns".
- `web/src/components/InstallVersionDialog.test.tsx:102-113` "handles pre-release versions with string comparison": `:108-109` flip (`getActionType('1.21.6', '1.21.6-pre.1')` is now `upgrade`, `('1.21.6-pre.1', '1.21.6')` `downgrade`); drop the comment about string comparison (`:103-107`); rename "orders pre-releases before their release". `:111-112` stay.
- Not failing, still correct under the new order: `VersionTable.test.tsx` "defaults to version descending sort" (`:164-174`: `1.20.1-rc.1 > 1.20.0 > 1.19.8`), "handles prerelease versions correctly" (`:354-390`), "correctly compares versions where string comparison would fail" (`:314-352`); `web/e2e/layout-widths.spec.ts` `BY_VERSION` (`:452`: `0.1.0 < 1.0.0-rc.12 < 2.3.4`) and its chevron check (`:493`, `.lucide-chevron-down`, still rendered).
- Anything else that fails is a regression (AC 12): fix the code, not the test.

### E2E (`web/e2e/version-sort-and-close-buttons.spec.ts`)

Style of `web/e2e/layout-widths.spec.ts` (header comment with the story, FRs and requirements; `readOnly`, `fakeInstalledMods`, `openPage`, `boxOf`, `rowOrder`/`cardOrder`, `expectSortControl` at `:106-117`, `:120-236`, `:263-280`, `:244-248`, `:431-449`) and `installed-status.spec.ts`. Copy the helpers you need; do not import across specs. Use `serveConfigKey(page, API_KEY)` from `e2e/config-js.ts`; every stub that passes a request on uses `fetchOnNewConnection(route)`. Every write to the API is refused (`readOnly`), so nothing changes on the stack; no snapshot guard is needed. Untagged: it needs no mod database (the installed mods, lookups and versions are stubbed) and no game server. No screenshots.

- **Stubs.** Installed mods: `fakeInstalledMods` with five mods: `alphamod` `1.10.0`, `betamod` `1.0.0`, `gammamod` `1.0.0-rc.12`, `deltamod` `1.9.0`, `epsilonmod` `1.0.0-rc.2`, every lookup answering `compatible`. Version page: `page.route(/\/api\/v1alpha1\/versions(\?.*)?$/)` answering `{ status: 'ok', data: { versions: [...], total, cached: false, cached_at: null } }` (shape: `content-security-policy.spec.ts:286-290`; fields of `VersionInfo`, `web/src/api/types.ts:525-534`, in snake_case) with `1.22.0` (stable, `is_latest: true`), `1.22.0-rc.1`, `1.22.0-rc.2`, `1.22.0-rc.12` (unstable), `1.21.10`, `1.21.9`, `1.21.8` (stable); and a local `pretendVersionInstalled(page, version)` modeled on `pretendServerInstalled` (`config-js.ts:44-54`): it passes the status request through `fetchOnNewConnection`, sets `state` to `installed` only when it was `not_installed`, and always replaces `version`. The real server name stays in the header; do not assert it and take no screenshot.
- **Installed mods table (1440px).** Default: Name `aria-sort="ascending"`, Version and Status `none`, Available, Side, Compatibility and Actions without the attribute (`getByRole('columnheader', { name })`). Click the Version header button: rows (`mod-row-*`) `epsilonmod, gammamod, betamod, deltamod, alphamod`, Version `ascending`, Name `none`. Again: the exact reverse, `descending`. (AC 1, 7, 8)
- **Installed mods cards (390px).** Sort control to Version (pattern `layout-widths.spec.ts:470-480`): cards in the same order; direction button: the exact reverse. (AC 1)
- **Version page (1440px), installed `1.22.0-rc.2`.** Default rows (`version-table-row-*`) `1.22.0, 1.22.0-rc.12, 1.22.0-rc.2, 1.22.0-rc.1, 1.21.10, 1.21.9, 1.21.8`; Version `descending`, Channel and Size `none`, Status and Actions without the attribute. Rows `1.22.0-rc.12` and `1.22.0` have class `bg-primary/5`, `1.22.0-rc.1` not. Click Version twice: ascending, the exact reverse, Version `ascending`. (AC 2, 3, 8)
- **Upgrade or downgrade.** Installed `1.21.9`: Select on `1.21.10` (`version-table-select-1.21.10`): `install-version-dialog` titled "Upgrade Server Version", no `downgrade-warning`; close it; Select on `1.21.8`: "Downgrade Server Version" with the warning. Never click the confirm button (a write would be refused anyway). (AC 6)
- **Dialog close button, at 390 and 1440px.** Open the install dialog as above. Wait until it is open and its animations have ended (`await dialog.evaluate((el) => Promise.all(el.getAnimations({ subtree: true }).map((a) => a.finished)))`). `close = dialog.getByRole('button', { name: 'Close', exact: true })`: box width and height `>= 44`; its `svg` box is 16px (within 1px) from the dialog's top and right edges; the title's text box (`page.evaluate` with a `Range` over `dialog-title`'s contents, `getBoundingClientRect()`) does not intersect the close box. Click `close`: the dialog is hidden. (AC 11)
- **Navigation sheet close button, at 390px.** Click "Open menu" (`getByRole('button', { name: 'Open menu' })`); `sheet = page.getByRole('dialog', { name: 'Navigation menu' })`; same wait and measurements (the sheet is on the left, so measure the icon from the sheet's own top and right edges); click the close button: the sheet is hidden. (AC 11)

### Manual check (Task 6.2)

On the Docker stack built from this branch, read-only (stub in the browser's dev tools or run the spec headed, `bunx playwright test e2e/version-sort-and-close-buttons.spec.ts --headed`): with VoiceOver or another screen reader, the installed mods and Version table headers announce "sorted ascending/descending" and the chevrons are not read; the close button of the install dialog and of the navigation sheet is easy to tap on a phone (or 390px in device mode), its icon has not moved, and its focus ring looks right. Do not install, change or remove anything; do not start or stop the game server; no screenshots. The maintainer ticks 8.2.

### Not changed (do not "fix" these here)

- The Channel and Size columns keep `sortFn: 'alphanumeric'` (`VersionTable.tsx:178`, `:190`); Size sorts the human-readable `filesize` strings (`"45.2 MB"`). Not in a bead; a follow-up, not part of this story.
- `VersionTable`'s sort removal on the third state and `ModTable`'s `enableSortingRemoval: false` (Dev Notes "Version table sort cycle").
- `VersionTable`'s `tabIndex`, `role="columnheader"`, `onClick` and `onKeyDown` on the `th` (`:371-382`); `SortableHeader` stays a button inside the cell (ADR-9 decision 2).
- `getActionType`'s `reinstall` test is string equality (`:66`); `isInstalled` in `VersionTable` (`:316`) too. `v1.21.6` and `1.21.6` are different strings from the API, which reports the version it installed.
- `QuickInstallButton` (`:66-69`) and the Version page's update banner (`VersionPage.tsx:219-222`) compare with `!==`, so a newer installed pre-release is offered the latest stable as an "update". Changing that is a product decision; it is listed as a follow-up, not done here.
- Alert dialogs, `DialogHeader`'s padding (unless AC 11's measurement fails), and the `eslint-disable-next-line` comment at `ModTable.tsx:252` (the web has no ESLint; Story 21.1's business).
- No other table: `JobsTable` does not sort.

### API contract changes

None. No route, field, status code or error code changes; the story changes only the web UI.

### ADR against the code

- **ADR-8 decision 3** lists `1.2` among the versions the function "cannot read", while decision 2 and the epic's AC say a missing part counts as 0. The story follows decision 2 and the AC: `1.2` and `v1.0.0` are read (as `1.2.0` and `1.0.0`); only strings with no version shape (`beta`, `1.0.0 hotfix`, empty, malformed) are unreadable and sort last. Either reading satisfies "nothing throws, stable order"; this one keeps a mod's `1.2` next to its `1.2.1`.
- **ADR-8 decision 1** names three users of `compareVersions`. `InstallVersionDialog.getActionType`, on the same Version page, compares strings and calls an upgrade a downgrade (Dev Notes "What is wrong today"). By the backlog drawdown rule it is fixed here (Task 2) with its own commit; its subject is a release note the change proposal's list does not have: `fix(web): call a move to a newer server version an upgrade, not a downgrade`.
- **ADR-9 decision 2** hides the chevrons from screen readers. `lucide-react` 1.72.0 already renders `aria-hidden="true"` on an icon with no accessible prop (`node_modules/lucide-react/dist/esm/Icon.mjs:43`, `shared/src/build/buildLucideIconNode.mjs:47-48`). The story still sets the attribute explicitly, as `ModScreenshotGallery.tsx` does, so the intent is in the code and does not depend on a library default; the rendered output is the same.
- **ADR-9 decision 4/5 and the epic's AC** measure the sheet "at 390px and at 1440px". The navigation sheet exists only below 768px (`Header.tsx:30`, `md:hidden` on its only trigger), so it is measured at 390px; the classes are the same at every width.
- **ADR-9 decision 5** puts the size check in E2E "at 390px"; the epic's AC adds 1440px for dialogs. The E2E does both.
- Everything else in ADR-8 and ADR-9 matches the code at 966204f (line numbers re-read; the facts' `:76-101` for the private function includes its doc comment from `:70`).

### Testing Requirements

**CRITICAL:** Tests are written with each task and committed with it, red first. `just test-web <file>` after each task; `just check` before review.

- Vitest runs in the `vmThreads` pool; follow `project-context.md` "Stubbing browser globals" (Story 20.2); no `it.skip`.
- `just test-web -t "<pattern>"` splits a quoted pattern on spaces (Story 20.3); run a single test by file, or with a pattern without spaces.
- jsdom has no layout: sizes are E2E only; unit tests assert attributes, roles and classes.
- Accessibility assertions go through roles (`getByRole('columnheader', { name })`), not test IDs, so they check what a screen reader gets.

### Security Requirements

- No new endpoint, no API change, no new dependency. The E2E refuses every write and stubs the reads it needs; it takes no screenshot and asserts nothing about the server name or keys.

### Development Commands

- `just test-web src/lib/version-compare.test.ts src/lib/table-aria-sort.test.ts`, `just test-web src/components/ModTable.test.tsx src/components/VersionTable.test.tsx src/components/InstallVersionDialog.test.tsx`, `just test-web src/components/ui/dialog.test.tsx src/components/ui/sheet.test.tsx src/components/layout/Layout.test.tsx`, `just typecheck-web`, `just lint-web`, `just check`.
- Prettier only on the files this story changes (Story 21.1's configuration); never on the whole web.

### Previous Story Intelligence

- **18.4:** added `table-column-meta.d.ts`, the cards' sort control and the `rowOrder`/`cardOrder` E2E helpers; its review found `VSS-qxxo`, `VSS-whnb` and `VSS-759m`.
- **18.1:** the screenshot dialog (`ModScreenshotGallery.tsx`) uses the shared `DialogContent`; its 44px Previous/Next buttons (`size-11`) are the model for the close box; it found `VSS-nuef`.
- **17.2 / 17.x reviews:** `feat`/`fix` subjects describe what an admin can see; a completion note must be true of the code; manual checks wait for the maintainer; E2E that changes real state needs a snapshot guard (this one changes nothing).
- **19.7 / 20.5:** `pretendServerInstalled` and `fetchOnNewConnection` (every pass-through stub uses it, or the API's 5 s keep-alive can reset a reused connection).
- **20.2 / 20.3:** `vmThreads` stubbing rule; `just test-web -t` splits on spaces.
- **21.1:** Prettier formats the web; run it on changed files. **21.4:** edits `ModTable.tsx` (remove dialog) and `ModTable.test.tsx` just before this story; re-read both.

### Git Intelligence

- Base `966204f` (`docs(epic-21): record the maintainer's answers and pull in VSS-q38r`) on `05436da` (`v0.1.0-rc.6`). Stories 21.1 to 21.4 land first.
- Planned commits: Task 1 `fix(story-21.5/task-1): sort versions with pre-releases before their release`; Task 2 `fix(story-21.5/task-2): call a move to a newer server version an upgrade, not a downgrade`; Task 3 `fix(story-21.5/task-3): announce the sort order of table columns to screen readers`; Task 4 `refactor(story-21.5/task-4): read VersionTable column classes without type assertions`; Task 5 `fix(story-21.5/task-5): make dialog close buttons easier to tap`, then `test(story-21.5/task-5): check version order, sort state and close button size in the browser`; Task 6 `chore(story-21.5/task-6): move story 21.5 to review`.

### Project Structure Notes

- New: `web/src/lib/version-compare.ts`, `version-compare.test.ts`, `table-aria-sort.ts`, `table-aria-sort.test.ts`; `web/src/components/ui/sheet.test.tsx`; `web/e2e/version-sort-and-close-buttons.spec.ts`.
- Modified: `web/src/components/ModTable.tsx`, `VersionTable.tsx`, `InstallVersionDialog.tsx`, `ui/dialog.tsx`, `ui/sheet.tsx`; `ModTable.test.tsx`, `VersionTable.test.tsx`, `InstallVersionDialog.test.tsx`, `ui/dialog.test.tsx`; `web/e2e/README.md` (counts). No API file, no dependency file.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 21.5: Version Sort, Sort State for Screen Readers and Close Buttons]
- [Source: _bmad-output/planning-artifacts/prd.md] FR275, FR276, FR277
- [Source: _bmad-output/planning-artifacts/architecture/epic-21-maintainer-decisions-and-web-polish.md] "Tables and dialogs today", ADR-8, ADR-9
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-17-epic-21.md] section 2 (release-note subjects), risks (21.5), order (21.4 before 21.5 before 21.6 and 21.7)
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md] touch targets at least 44 by 44px (`:515`, `:1180`, `:1290`)
- [Source: _bmad-output/implementation-artifacts/18-4-*.md], [18-1-*.md] (where the beads were found)
- Semantic Versioning 2.0.0, section 11 (precedence)
- Beads: `VSS-qxxo`, `VSS-whnb`, `VSS-759m`, `VSS-nuef`, parent `VSS-syuj`
- `project-context.md` (no suppressions; manual test tasks need the maintainer's confirmation; commit format; web unit test stubbing)

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List

## Change Log

- 2026-11-17: Story created and validated (create-story workflow, non-interactive). Status `ready-for-dev`.
