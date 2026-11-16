# Story 18.4: Installed Mods List at Every Width

Status: ready-for-dev

<!-- Implements FR203-FR204. Beads: VSS-bgu (UI-077), VSS-n2u (UI-086). Branch story/18-4-installed-mods-list-at-every-width, stacked on Story 18.3's branch (18.1, 18.2, 18.3 come first, each stacked on the previous). Line references were verified at b9606f1 (epic-18-planning) and must be re-checked on the 18.3 head before editing; 18.1-18.3 are not expected to touch any file this story edits (epics.md, Epic 18 "Dependencies"). Governed by Epic 18 ADR-6 (one sort preference; the Name column wraps; `components/ui/table.tsx` unchanged; `LG_UP_QUERY` unchanged). Changes acceptance criterion 2 of Story 17.8 for rows with long names. Web only: no API change, no new dependency. -->

## Story

As an **administrator**,
I want **to sort my installed mods and reach every control at any window width**,
so that **the list is as usable on a tablet or a small laptop as on a wide screen**.

## Acceptance Criteria

1. **Given** a viewport narrower than 1024px (the cards, `LG_UP_QUERY` false)
   **When** I open Installed mods (`/game-server/mods/installed`) with at least one mod installed
   **Then** a sort control above the cards shows the current sort column (Name, Version or Status) and direction (Ascending or Descending); it offers exactly the three columns the table headers sort by, and nothing else; its column picker has the accessible name "Sort by"; the picker and the direction button are each at least 44px tall
   *(Covers FR203; `VSS-bgu`)*

2. **Given** the sort control
   **When** I choose another column or press the direction button
   **Then** the cards reorder at once; choosing a column keeps the current direction, the button flips only the direction; the choice is written to the existing `installedModsSort` preference (the `vs_ui_prefs` cookie), so it is still there after a reload
   *(Covers FR203)*

3. **Given** I sorted the cards by Version descending
   **When** I widen the window to 1024px or more
   **Then** the table is sorted by Version descending and the Version header shows the descending chevron; and a sort made on a table header is the cards' sort (control and order) when I narrow the window again
   *(Covers FR203)*

4. **Given** a viewport of 1024px or wider, or no mods installed, or the list still loading
   **When** I open Installed mods
   **Then** there is no sort control; the table headers sort as today
   *(Covers FR203)*

5. **Given** a 1024px viewport, sidebar expanded (816px container) or collapsed (912px), and the Story 17.8 fixture (a mod with the 63-character name `An Extraordinarily Long Mod Name That Must Wrap Inside Its Card` and an offered pre-release update, an incompatible mod, a disabled mod)
   **When** I open Installed mods
   **Then** the table does not scroll inside its container, the page does not scroll sideways, the long name wraps, and that mod's enable toggle and remove button are inside the viewport
   *(Covers FR204; `VSS-n2u`)*

6. **Given** the same fixture at 1440px with the sidebar collapsed or at 1920px in either state, or only short-named mods (one of them with an offered pre-release update) at 1280px or wider in either state
   **When** I open Installed mods
   **Then** every mod's name and Available cell are on one line, as today. Below 1280px the Update button of an offered update may sit under the offered version, and at 1440px with the sidebar expanded the 63-character name may wrap (Dev Notes "Epic text against the code": the epic's wording cannot hold there, measured)
   *(Covers FR204)*

7. **Given** the other tables in the app (Scheduled Jobs `JobsTable`, Version `VersionTable`) and the shared `components/ui/table.tsx`
   **When** this story is done
   **Then** `table.tsx` is unchanged and their cells still do not wrap (`whitespace-nowrap` from `TableHead`/`TableCell`)
   *(Covers FR204)*

8. **Given** every existing test
   **When** the suites run
   **Then** they pass, apart from the changes listed in Dev Notes "Existing tests that change"; no test writes into `dev/`, and no E2E test changes real state

## Tasks / Subtasks

<!-- Each functional task includes its tests in the same commit. Commit per task: type(story-18.4/task-N): ... ; feat/fix only for changes an admin can see, subject written for admins. Red first. -->

- [ ] Task 1: Measure the table's columns before any change (AC: 5, 6)
  - [ ] 1.1: New `_bmad-output/implementation-artifacts/18-4-browser/column_widths.mjs` (Dev Notes "Measurement method"). It reads only: the installed mods, update status and lookups are stubbed with `page.route`, every non-GET API request is refused, no screenshot. Do not edit `17-8-browser/layout_widths.mjs` or its JSON files: they are Story 17.8's record and the before numbers the epic asks to keep
  - [ ] 1.2: Rebuild the stack from this branch (`just docker restart`), then `cd web && bun ../_bmad-output/implementation-artifacts/18-4-browser/column_widths.mjs > ../_bmad-output/implementation-artifacts/18-4-browser/column_widths.before.json` with `VS_API_KEY_ADMIN` exported. Check the output holds no key, server name or password
  - [ ] 1.3: Record in the Dev Agent Record a table of the column widths at 1024px (both sidebar states, long-name fixture) and compare with Dev Notes "Planning measurements". Choose the Name column's minimum width by the rule in Dev Notes "Decision: the Name column and the Available cell" and write down the numbers that decided it
  - [ ] 1.4: Commit the script and `column_widths.before.json`: `docs(story-18.4/task-1): measure the installed mods table's columns at 1024px and wider`

- [ ] Task 2: Sort control above the installed mod cards + tests (AC: 1, 2, 3, 4, 8)
  - [ ] 2.1: New `web/src/components/InstalledModsSortControl.tsx` (Dev Notes "The sort control"): exports `SORT_COLUMN_LABELS: Record<InstalledModsSortColumn, string>` (`name: 'Name'`, `version: 'Version'`, `enabled: 'Status'`) and `InstalledModsSortControl({ value, onChange }: { value: InstalledModsSort; onChange: (sort: InstalledModsSort) => void })`. Uses `Select`/`SelectTrigger`/`SelectValue`/`SelectContent`/`SelectItem` (`components/ui/select.tsx`) and `Button` (`components/ui/button.tsx`); no new component in `components/ui/`, no new dependency
  - [ ] 2.2: `web/src/components/ModTable.tsx`: the three `SortableHeader` labels (`:254`, `:269`, `:309`) use `SORT_COLUMN_LABELS.name`, `.version`, `.enabled`, so the control and the headers cannot drift. In the cards branch (`:401-418`) render `<div className="space-y-3">` holding `<InstalledModsSortControl value={preferences.installedModsSort} onChange={setInstalledModsSort} />` and the existing `<ul ...>` unchanged (`preferences` and `setInstalledModsSort` are already read at `:128`). Nothing in the table branch changes for this task. Header comment (`:1-14`): add "Story 18.4: below `lg`, a sort control above the cards writes the same preference as the headers"
  - [ ] 2.3: `onSortingChange` (`:155-175`), the `sorting` memo (`:149-153`) and `PreferencesContext.tsx` do not change: the control calls `setInstalledModsSort` (`PreferencesContext.tsx:195-197`), which the cookie effect (`:168-171`) persists, and the table reads the same `preferences.installedModsSort`
  - [ ] 2.4: Tests (Dev Notes "Web tests", Task 2 rows), red first

- [ ] Task 3: The Name column wraps so the table fits at 1024px + tests (AC: 5, 6, 7, 8)
  - [ ] 3.1: New `web/src/lib/table-column-meta.d.ts`: module augmentation of TanStack Table's `ColumnMeta` with `className?: string` (Dev Notes "Typed column meta"). In `ModTable.tsx` the header's `(header.column.columnDef.meta as { className?: string } | undefined)?.className` (`:377-379`) becomes `header.column.columnDef.meta?.className`; no type assertion is added anywhere
  - [ ] 3.2: `ModTable.tsx` Name column (`:251-265`): add `meta: { className: 'min-w-36 whitespace-normal wrap-anywhere' }` (`min-w-36` is the planning value; use the value Task 1.3 chose). Body cells (`:392-396`): `<TableCell key={cell.id} className={cell.column.columnDef.meta?.className}>`, so the Name cells get the same classes as the Name header. The Actions column's `meta` (`w-[80px]`, `:334`) now also reaches its body cells; that is intended and changes nothing measurable (it is a width hint on the same column)
  - [ ] 3.3: `web/src/components/ModUpdateCell.tsx:60`: the `update_available` container becomes `flex flex-wrap items-center gap-x-2 gap-y-1`, so the Update button can drop under the offered version when the column is narrow (Dev Notes "Decision"). It is shared with the cards (`InstalledModCard.tsx:73-79`), where it only wraps if the card is narrower than the line. Header comment: add "Story 18.4: the Update button wraps under the version when the column is narrow"
  - [ ] 3.4: `web/src/components/ui/table.tsx` is not edited (ADR-6 decision 1); `JobsTable.tsx` and `VersionTable.tsx` are not edited
  - [ ] 3.5: Tests (Dev Notes "Web tests", Task 3 rows), red first

- [ ] Task 4: E2E, after measurements and browser check (AC: 1-7)
  - [ ] 4.1: `web/e2e/layout-widths.spec.ts` (Dev Notes "E2E"): the 1024px table tests expect no scrolling element; new long-name and short-name assertions at 1024/1280/1440/1920; new sort control tests. Update its header comment (`:6-9`). `web/e2e/installed-mods-phone.spec.ts`: add the two sort controls to the 44px touch target test (`:231-256`)
  - [ ] 4.2: Rebuild the stack from this branch (`just docker restart`); run `cd web && bunx playwright test e2e/layout-widths.spec.ts e2e/installed-mods-phone.spec.ts` with `VS_API_KEY_ADMIN` exported. Both specs read only (every write refused; sort preference only in the test browser's cookie); the game server is not started or stopped
  - [ ] 4.3: Run the measurement script again into `18-4-browser/column_widths.after.json`; record a before/after table in the Dev Agent Record (per width and sidebar state: table scroll width / container width, each column's width, row heights of the three fixture mods, toggle and remove inside the viewport)
  - [ ] 4.4: Browser check on the stack (Admin key, every write refused or nothing clicked that writes, no screenshot kept): at 900px and 390px choose Version, flip to Descending, reload, widen to 1024px and see the table sorted the same way; at 1024px with the sidebar expanded and collapsed the table does not scroll sideways. This is a manual check: per `project-context.md` it is ticked only after the maintainer confirms it; record the agent's scripted check separately, as Story 17.8 did
  - [ ] 4.5: Commit the specs and `column_widths.after.json`: `test(story-18.4/task-4): check the installed mods list and its sort at every width`

- [ ] Task 5: Quality gate and review hand-off (AC: all)
  - [ ] 5.1: `just check` passes (lint, typecheck, all tests); the diff adds no lint or type suppression, no `cast`, no `as` type assertion and no non-null assertion in source (the existing `!` in test helpers such as `ModTable.test.tsx:1723` is not new); `git status --short` shows nothing under `dev/`
  - [ ] 5.2: Story status `review`, `just sprint set 18-4-installed-mods-list-at-every-width review`, PR (base: Story 18.3's branch while its PR is open, otherwise `main`), PR link on `VSS-bgu` and `VSS-n2u`. The PR description lists the follow-ups in Dev Notes "Follow-ups" and the two AC 6 exceptions

## Dev Notes

### The problems (verified at b9606f1)

- **No sort below `lg` (`VSS-bgu`).** `ModTable` renders the table only when `useMediaQuery(LG_UP_QUERY)` is true (`ModTable.tsx:131`; `LG_UP_QUERY = '(min-width: 64rem)'`, `hooks/use-media-query.ts:17`) and the cards otherwise (`:401-418`). Both render `table.getRowModel().rows`, sorted by `preferences.installedModsSort` (`:149-153`), a `{ column: 'name' | 'version' | 'enabled', direction: 'asc' | 'desc' }` kept in the `vs_ui_prefs` cookie (`contexts/PreferencesContext.tsx:27-34`, default `name`/`asc` `:51`, setter `:195-197`, cookie write `:168-171`). Only the `SortableHeader` buttons in the table (`:88-109`, used at `:251-327`) can change it, so since Story 17.8 put the cards up to 1023px, phones and tablets cannot re-sort.
- **The table scrolls at 1024px (`VSS-n2u`).** `TableHead` and `TableCell` are `whitespace-nowrap` (`components/ui/table.tsx:71`, `:84`), the container is `overflow-x-auto` (`:5-18`). The Name cell renders `ModNameLink` (`InstalledModParts.tsx:37-55`: the name as an `inline-flex` link with an icon, and the slug on a second line), so the column is as wide as the longest name. Story 17.8 measured 1183px needed vs 816/912px available (`17-8-browser/layout_widths.after.json`). Only the header cells get `meta.className` today (`ModTable.tsx:375-379`); body cells get none (`:393`).

### Planning measurements (2026-11-16, read-only, the running Docker dev stack)

Taken while writing this story with a throwaway script in the session scratchpad (the Story 17.8 stubs, every write refused, no screenshot). The stack's web build had the Story 17.8 table (1183px needed at 1024px, the same as `layout_widths.after.json`). Columns are the `th` widths (padding included). "Simulated" rows inject the planned CSS into the page with `page.addStyleTag`, which approximates Task 3 without a rebuild; Task 1 and Task 4 replace these with real numbers.

Story 17.8 fixture (63-character name, offered `1.0.0-rc.13` pre-release), today:

| Viewport | Sidebar | Table / container | Name | Version | Available | Side | Compatibility | Status | Actions |
|---|---|---|---|---|---|---|---|---|---|
| 1024 | expanded | 1183 / 816 | 447 | 90 | 234 | 154 | 131 | 76 | 52 |
| 1024 | collapsed | 1183 / 912 | 447 | 90 | 234 | 154 | 131 | 76 | 52 |
| 1280 | expanded | 1183 / 1072 | 447 | 90 | 234 | 154 | 131 | 76 | 52 |
| 1440 | expanded | 1232 / 1232 | 447 | 90 | 234 | 154 | 152 | 76 | 80 |
| 1440 | collapsed | 1328 / 1328 | 449 | 90 | 235 | 155 | 242 | 76 | 80 |

- At 1024px the six other columns need 737px together (their minimum: they are squeezed already), so with the sidebar expanded the Name column could have at most 816 − 737 = 79px, less than the widest word of the name (about 89px of text plus 16px padding). **Wrapping the Name column alone is not enough with the sidebar expanded**; simulated, Name-only wrapping with a 128/144/160/192px minimum still scrolls (864, 880, 896, 928 / 816). With the sidebar collapsed it fits up to a 160px minimum.
- The Available cell (offered version, "pre-release", Update button on one line) is 234px. Letting it wrap brings its minimum to about 155px. Simulated, Name wrapping plus a wrapping Available cell fits at 1024px in both states with a 128px or 144px minimum (816/816, 912/912; at 144px the other minimums plus the Name minimum add up to about 802px, 14px under 816); a 160px minimum overflows by 1px (817/816), 192px by 33px.
- Side is 154px because a mod with side `Both` shows two badges (`SideBadge.tsx:52-80`). Compatibility already wraps its "Supports up to" text under the badge when squeezed (`InstalledModParts.tsx:76-86`, `flex flex-wrap`), which is why the incompatible mod's row is 63px instead of 57px at 1024 and 1440 expanded today.
- Short names only (the fixture with the long name replaced by `Short Mod`, still with the offered pre-release update): today the table needs **841px at 1024px with the sidebar expanded, so it scrolls (841/816) even without a long name**; collapsed it fits. Simulated with the planned CSS it fits in both states; the Short Mod row's Update button drops under its version at 1024px (row 73px instead of 57px), and from 1280px every row is 57px as today.
- Simulated with the planned CSS, the long-name fixture at 1440px expanded gives Name 381-393px, so the name wraps (row 77px), while at 1440 collapsed and 1920 in both states every row is as today. See "Epic text against the code".

### Decision: the Name column and the Available cell (ADR-6 "long names")

- **Name column:** `meta: { className: 'min-w-36 whitespace-normal wrap-anywhere' }`, applied to the header and the body cells. `cn()` (tailwind-merge) in `TableHead`/`TableCell` drops the base `whitespace-nowrap` when `whitespace-normal` is passed, so only the Name cells change.
- **Why `wrap-anywhere`, not `break-words`:** the Name cell's second line is the slug (`InstalledModParts.tsx:52`), which has no spaces; mod IDs of 20+ characters are common (for example a mod ID like `egocaribautomapmarkers` is about 170px at `text-sm`). `overflow-wrap: break-word` (Tailwind `break-words` / `wrap-break-word`) does not lower a cell's min-content width, so such a slug would set the column's minimum and the table would scroll again. `overflow-wrap: anywhere` (Tailwind v4.1 `wrap-anywhere`, available in the installed `tailwindcss` 4.1.18) does count those break opportunities, and the min width keeps the column readable. The browser still breaks between words first.
- **Minimum width rule (Task 1.3):** take the largest of `min-w-32` (128px), `min-w-36` (144px) and `min-w-40` (160px) for which the measured minimum widths of the other six columns at 1024px with the sidebar expanded, after the Available cell can wrap (about 155px), plus the Name minimum, are at most 808px (816 minus an 8px margin for a slightly longer version string). The planning numbers give `min-w-36` (about 802px). If no candidate passes, stop and report: that means something other than this story changed the columns.
- **Available cell wraps instead of always stacking:** ADR-6 decision 3 allows stacking the offered version above the Update button "if the numbers require it". They do (above). `flex-wrap` on the cell's container stacks only when the column is narrower than the line, so wide windows keep one line; an always-stacked cell would make every row with an offered update two lines at every width.
- **Not chosen:** a percentage width on the Name column (simulated at 30/40/50%: it keeps the long name on one line at 1440 expanded only by squeezing the Available and Compatibility columns, and at 50% squeezes them at 1920 too); wrapping the Side badges (outside ADR-6); a wider breakpoint (ADR-6 decision 2).

### The sort control (ADR-6 "sort")

```tsx
// web/src/components/InstalledModsSortControl.tsx (shape; names and test IDs are binding)
export const SORT_COLUMN_LABELS: Record<InstalledModsSortColumn, string> = {
  name: 'Name',
  version: 'Version',
  enabled: 'Status',
};
const SORT_COLUMNS: InstalledModsSortColumn[] = ['name', 'version', 'enabled'];

function isSortColumn(value: string): value is InstalledModsSortColumn {
  return value === 'name' || value === 'version' || value === 'enabled';
}

export function InstalledModsSortControl({ value, onChange }: InstalledModsSortControlProps) {
  const labelId = useId();
  const isAscending = value.direction === 'asc';
  return (
    <div className="flex flex-wrap items-center gap-2" data-testid="installed-mods-sort">
      <span id={labelId} className="text-sm text-muted-foreground">Sort by</span>
      <Select
        value={value.column}
        onValueChange={(column) => {
          if (isSortColumn(column)) onChange({ column, direction: value.direction });
        }}
      >
        <SelectTrigger aria-labelledby={labelId} className="min-h-11" data-testid="installed-mods-sort-column">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {SORT_COLUMNS.map((column) => (
            <SelectItem key={column} value={column} data-testid={`installed-mods-sort-option-${column}`}>
              {SORT_COLUMN_LABELS[column]}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="min-h-11"
        onClick={() => onChange({ column: value.column, direction: isAscending ? 'desc' : 'asc' })}
        data-testid="installed-mods-sort-direction"
      >
        {isAscending ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        {isAscending ? 'Ascending' : 'Descending'}
      </Button>
    </div>
  );
}
```

- **Height:** `min-h-11`, not `h-11`. `SelectTrigger` sets its height with `data-[size=default]:h-9` (`select.tsx:38`), which outranks a plain `h-11` in specificity, and `Button size="sm"` is `h-8`; a 44px `min-height` wins over both. The control is only rendered below `lg`, so no `max-lg:` prefix is needed.
- **Direction button:** shows and names the direction in effect (chevron as in the table headers, plus "Ascending"/"Descending"), and a press flips it. Its accessible name is its visible text (no `aria-label`, so the name matches what is seen). See "ADR against the code" for the wording.
- **Choosing a column keeps the direction.** The table headers keep their own TanStack behavior (`column.toggleSorting()`), which is not changed.
- **`isSortColumn`** is a type guard, so `onValueChange`'s `string` needs no assertion. Radix only emits values of the rendered items.
- **Not reused:** `components/SortControl.tsx` is the mod browser's `DropdownMenu` for its own `BrowseSortOption` values (`:28-36`) with no direction; ADR-6 decision 3 names `Select`.
- **Placement:** inside the cards branch only, in a `space-y-3` wrapper with the `<ul>`. The loading and empty states return early (`ModTable.tsx:348-365`), so the control is absent there (AC 4). `InstalledTab.tsx` (toolbar, `:83-123`) does not change.

### Typed column meta (no type assertion)

`ModTable.tsx:378` (and `VersionTable.tsx:352`, `:407`) read `columnDef.meta` through `as { className?: string } | undefined`, because TanStack Table's `ColumnMeta` is an empty interface meant for module augmentation (`node_modules/@tanstack/table-core/dist/types/ColumnDef.d.ts:17`, `export interface ColumnMeta<in out TFeatures extends TableFeatures, in out TData extends RowData, TValue extends CellData = CellData> {}`). Task 3.1 adds:

```ts
// web/src/lib/table-column-meta.d.ts
import '@tanstack/react-table';
import type { CellData, RowData, TableFeatures } from '@tanstack/react-table';

declare module '@tanstack/react-table' {
  interface ColumnMeta<TFeatures extends TableFeatures, TData extends RowData, TValue extends CellData = CellData> {
    /** Classes for the column's header and body cells */
    className?: string;
  }
}
```

Checked in a throwaway prototype on b9606f1: `tsc -b` passes, `meta?.className` is typed (a misspelt `meta?.classNam` is a type error), and without the file `meta?.className` is an error. The `VersionTable` assertions stay valid and are not touched (follow-up 3). If the type parameters' names trip a lint rule, keep the augmentation and fix the rule's complaint, not with a suppression.

### Web tests

The web test setup has no CSS: jsdom does no layout, so class assertions are the unit-level check and the E2E is the real one. The jsdom viewport stand-in is `tests/viewport.ts` (`setViewportWidth`, default 1024). Radix `Select` needs `Element.prototype.hasPointerCapture`, `releasePointerCapture` and `scrollIntoView` stubs in jsdom (as `features/mods/ModDetailPage.test.tsx:794-799`); add the same `beforeAll` to the new describe. `@testing-library/user-event` is already a dev dependency. `@/lib/cookies` is mocked in `ModTable.test.tsx:23-26` (`getCookie`, `setCookie`); read the persisted value from `setCookie`'s last call.

| Task | File | Test |
|---|---|---|
| 2 | `src/components/ModTable.test.tsx`, new describe "sort control below lg (Story 18.4)" inside `describe('ModTable')`, reusing `mockApi`/`cardSlugs` from "cards below lg" (`:1662-1724`) or nesting inside it | at 390 and 900 (`it.each`): `installed-mods-sort` shown; `getByRole('combobox', { name: 'Sort by' })` reads "Name"; the direction button reads "Ascending"; both have `min-h-11`. Opening the picker lists exactly the options Name, Version, Status (`findAllByRole('option')`), the same labels as the table's sortable headers (render at 1024 and read the three header buttons) |
| 2 | same | a stored preference `{ column: 'enabled', direction: 'desc' }` (cookie mock, as `:1895-1911`) shows "Status" and "Descending" |
| 2 | same | choosing Version: cards reorder to version ascending (`mockModsResponse`: `smithingplus` 1.5.0, `carrycapacity` 2.0.0, so `['smithingplus', 'carrycapacity']`, whereas the default name order is the reverse) and `setCookie`'s last call holds `installedModsSort: { column: 'version', direction: 'asc' }` (direction kept) |
| 2 | same | the direction button flips: order reversed, button reads "Descending", cookie direction `desc`; pressing again goes back |
| 2 | same | shared preference both ways: on the cards choose Version and Descending, `act(() => setViewportWidth(1024))`, the table rows (`mod-row-*`) are in version descending order and the control is gone; click the table's Name header, `act(() => setViewportWidth(900))`, the control reads "Name"/"Ascending" and the cards are in name order |
| 2 | same | no control at 1024 and 1440 (`queryByTestId('installed-mods-sort')` null), in the empty state at 390 and in the loading state at 390 |
| 3 | `src/components/ModTable.test.tsx`, "table rendering" or a new "long names (Story 18.4)" describe | at the default 1024: the Name `columnheader` and every Name cell (first `td` of each `mod-row-*`) have `whitespace-normal`, `wrap-anywhere` and the chosen `min-w-*`, and do not have `whitespace-nowrap`; the Version cell of a row still has `whitespace-nowrap` (the other columns are untouched) |
| 3 | `src/components/ModUpdateCell.test.tsx` | `update_available`: `mod-update-<slug>` has `flex-wrap` |
| 3 | `src/components/ui/table.test.tsx` | unchanged: `:400` and `:469` already assert `whitespace-nowrap` on `TableHead`/`TableCell`, which is AC 7's guard for `JobsTable` and `VersionTable` |

### E2E (`web/e2e/layout-widths.spec.ts`, extended)

Keep the spec's style and rules: `readOnly` refuses every non-GET request (`:71-86`), `fakeInstalledMods` serves the list, updates and lookups (`:89-194`), the sidebar state is the `vs_ui_prefs` cookie of a fresh context (`openPage`, `:233-245`), no screenshot. Update the header comment (`:6-9`): Story 18.4 (FR203-FR204; `VSS-bgu`, `VSS-n2u`): the table fits from 1024px with a long name, and the cards have a sort control.

1. **Fixtures.** Let `fakeInstalledMods(page, mods = MODS)` take the list, and give each entry an optional `offered` version that `updateStatus` reads instead of testing `slug === 'longnamemod'` (`:54-68`): `longnamemod` offers `1.0.0-rc.13` pre-release as today. Add `SHORT_MODS`: `oldmod`, `offmod` and `shortmod` (`Short Mod`, version `1.4.0`, offers `1.5.0-rc.1` pre-release, compatible). Add `shortmod` to `COMPATIBILITY`.
2. **Table at 1024 (AC 5).** Replace the exception at `:286-287` (`if (width > 1024)`) so `scrolling` is `[]` at every table width, in both sidebar states. At 1024 in both states also: `mod-toggle-longnamemod` and `mod-remove-longnamemod` inside `[0, width]` (`expectInsideViewport`), and the name wraps: the box of `mod-link-longnamemod` is taller than that of `mod-link-offmod`.
3. **One line where it fits (AC 6).** Long-name fixture at 1440 collapsed and 1920 in both states, and `SHORT_MODS` at 1280, 1440 and 1920 in both states: for every mod, the `mod-link-<slug>` box is as tall as `mod-link-offmod`'s (within 1px), and where an update is offered the `mod-update-button-<slug>` box's vertical center is within 2px of the `mod-update-<slug>` box's (one line). `SHORT_MODS` at 1024 in both states: `scrolling` is `[]` and the document does not scroll (today it scrolls with the sidebar expanded). No one-line assertion at 1024-1279 or at 1440 expanded with the long name (AC 6 exceptions).
4. **Sort control (AC 1-4).** At 900 with the sidebar expanded and at 390: `installed-mods-sort` visible and inside the viewport, reads Name / Ascending, cards in name order (`longnamemod`, `offmod`, `oldmod`); click `installed-mods-sort-column`, then the Version option: cards `offmod` (0.1.0), `longnamemod` (1.0.0-rc.12), `oldmod` (2.3.4); click `installed-mods-sort-direction`: reversed, reads Descending. `page.reload()`: still Version / Descending in the same order. `page.setViewportSize({ width: 1024, height: HEIGHT })`: the table's rows are `oldmod`, `longnamemod`, `offmod`, the Version `columnheader` contains the `lucide-chevron-down` icon, and `installed-mods-sort` has count 0. Click the Name header (`getByRole('button', { name: 'Name' })` inside the header), narrow to 900: the control reads Name / Ascending and the cards are in name order. At 320 the control wraps without document overflow (covered by the existing 320-1023 card tests once the control exists: they already assert `{ document: 0, scrolling: [] }`).
5. `web/e2e/installed-mods-phone.spec.ts` (`:231-256`): add `installed-mods-sort-column` and `installed-mods-sort-direction` to the `expectTouchTarget` list.

Nothing here changes real state: the installed mods are stubbed, writes are refused, the sort preference lives in the test context's cookie. Do not start or stop the game server.

### Measurement method (`18-4-browser/column_widths.mjs`)

Copy the stubs and helpers of `17-8-browser/layout_widths.mjs` (`:26-179`: Playwright from `../../../web/node_modules/@playwright/test/index.mjs`, `/config.js` answered with `VS_API_KEY_ADMIN`, `readOnly`, `fakeInstalledMods`, `overflow`, `rect`, `open`). Measure only Installed mods, at 1024, 1280, 1440 and 1920, sidebar expanded and collapsed, with both fixtures (the 17.8 long-name fixture and the `SHORT_MODS` of the E2E). Per page: `documentOverflowX`, `scrolling`, `[data-slot="table-container"]` rect, the width of each `thead th` labelled by its text (`(actions)` for the last), each fixture row's height, whether `mod-toggle-<long>` and `mod-remove-<long>` end inside the viewport. Output JSON only, numbers and test IDs. If the installed Playwright has no browser binary for its version, run the script with `bunx playwright install chromium` first (it downloads into the user cache, not the repo).

### Epic text against the code

- **AC 6 (epic: "a viewport of 1440px or wider, or only mods with short names: each row is on one line, as today").** Two parts cannot hold with any wrapping table, measured above: (1) today the long-name table fits at 1440 expanded only because the Compatibility column absorbs the shortfall (1232px container, about 1327px preferred); once the Name column can wrap, the browser shares the shortfall between Name and Compatibility, so the long name wraps there. (2) With short names and an offered update, the table already scrolls at 1024 expanded today (841/816); fitting it means the Available cell wraps at 1024-1279px. AC 6 is written to what is achievable; the exceptions are listed in the PR for the maintainer. FR204 ("fits its container", "on screen") is fully met.
- **Epic task "Extend `layout_widths.mjs`"** becomes a new script in `18-4-browser/`, so Story 17.8's script and its before/after record stay as they are ("keep the before numbers").

### ADR against the code

- **ADR-6 long names, decision 1 ("`whitespace-normal` and `break-words`")**: `wrap-anywhere` instead of `break-words` (see "Decision": `break-word` does not lower the min-content width, so a long slug would keep the table wide). Same intent, the class that achieves it.
- **ADR-6 long names, decision 3 ("the Available cell may also stack")**: the numbers require it; it is done with `flex-wrap` (stacks only when narrow) rather than a fixed stack, to keep wide rows on one line.
- **ADR-6 sort, decision 3 ("a button that flips the direction and names the result in its label ('Sort ascending' or 'Sort descending')")**: the button names the direction in effect after the last press, as visible text "Ascending"/"Descending" with the header chevron. Naming the opposite of what is shown would contradict AC 1 ("shows the current ... direction"). Both are 44px tall as the ADR says, via `min-h-11` (see "The sort control").
- ADR-6's line references (`ModTable.tsx:131`, `:150-153`, `:369-418`, `:372-376`; `PreferencesContext.tsx:28-34`, `:51`, `:196`; `table.tsx:71`, `:84`; `use-media-query.ts:17`) match b9606f1.

### Version sort (planning finding not reproduced)

The planning note said the Version column sorts as text (1.10.0 before 1.9.0). On b9606f1 it does not: the column has no `sortFn` (`ModTable.tsx:266-277`), so TanStack picks one from the first rows' values (`rowSortingFeature.utils.js:77-96` in `@tanstack/table-core`): any value with digits gets `alphanumeric`, which compares digit runs as numbers. A prototype test sorted `1.9.0` before `1.10.0` ascending. What it does get wrong is semver pre-release order (`1.0.0` before `1.0.0-rc.12`, the reverse of semver) and a value without digits would switch the column to `text`. Out of scope: follow-up 1. Do not change the Version sort here.

### Existing tests that change (deliberately)

Found by running the whole web suite against a throwaway prototype of Tasks 2 and 3 (sort control, Name meta on body cells, typed meta, `flex-wrap` in `ModUpdateCell`; since discarded): 130 files, 3260 passed, 4 skipped, **no failure**, and `tsc -b` clean. A prototype test also confirmed in jsdom that the Radix `Select` can be driven with `user-event` (with the stubs above), that the persisted cookie holds the new sort, and that the table follows it at 1024.

- `web/e2e/layout-widths.spec.ts:286-287`: the 1024px exception goes (Task 4). Header `:6-9`.
- `web/e2e/installed-mods-phone.spec.ts:231-256`: two more touch targets (Task 4). Its 390px overflow test (`:208-229`) now also covers the control and must still pass.
- Known load flakes (Story 17.4: `InstallConfirmDialog`, `QuickInstallButton`, `SettingField`, `GameConfigPanel`, one test each, pass alone): re-run before suspecting this story. Anything else that fails is a regression: fix the code, not the test.

### Not changed (do not "fix" these here)

- `components/ui/table.tsx`, `components/ui/select.tsx`, `JobsTable.tsx`, `VersionTable.tsx` (including its `meta` assertions), `LG_UP_QUERY`, `InstalledModCard.tsx`, `InstalledTab.tsx`, `PreferencesContext.tsx` (no new preference, no URL state), `SortControl.tsx`.
- The table's columns, header sort behavior (`enableSortingRemoval: false`, `:345`; the Status column's `sortFn`, `:322-326`) and the Version sort.
- The Side badges and the Compatibility cell layout.
- No API change; no new npm dependency.

### Follow-ups (not in this story; for the maintainer to file)

1. Version column ordering: semver pre-releases sort after their release (`1.0.0` before `1.0.0-rc.12`) and a list whose first ten versions have no digit would sort as text. A `sortFn` using the semver comparison the update check already uses on the API side would fix it. (Not the "1.10.0 before 1.9.0" of the planning note, which does not reproduce.)
2. Even short-named mods with an offered pre-release update made the table scroll at 1024 expanded before this story (841/816); fixed here, but it means `VSS-n2u`'s "long name" title understated the case. No action beyond noting it on the bead.
3. `VersionTable.tsx:352`, `:407` can drop their `as { className?: string }` assertions once the `ColumnMeta` augmentation exists.
4. Sortable headers have no `aria-sort`; the sort direction is shown only by a chevron icon.

### Testing Requirements

**CRITICAL:** tests are written with each task and committed with it, red first. `just test-web <file>` after each task; `just check` before review.

- Web tests use the existing `ModTable.test.tsx` helpers (`createWrapper` with `PreferencesProvider`, `mockApi`, `setViewportWidth`); no new test utility module.
- E2E reads only; every write is refused; no screenshot.
- No test writes into `dev/` (this story has no API test).

### Security Requirements

- No new endpoint, no data change. The sort preference is a UI cookie already in use. The measurement script and the E2E read the admin key from the environment and never print it; committed JSON holds numbers and test IDs only.

### Development Commands

- `just test-web src/components/ModTable.test.tsx src/components/ModUpdateCell.test.tsx src/components/ui/table.test.tsx`, `just typecheck-web`, `just lint-web`, `just check`.
- E2E: `just docker restart`, then `cd web && bunx playwright test e2e/layout-widths.spec.ts e2e/installed-mods-phone.spec.ts` (`just test-e2e-web` stops the stack afterwards).
- Do not run `just format` (whole-repo formatter).

### Previous Story Intelligence

- **17.8:** put the cards up to `lg`, measured the 1183px table, wrote `layout-widths.spec.ts` with the 1024 exception this story removes, and filed `VSS-n2u`; its completion notes already flagged that `VSS-bgu` now covers 768-1023px. Its review: the maintainer's hand check is separate from the agent's scripted check (M1); measurement scope must be stated (L2); no type assertion in new tests (L3).
- **17.4 / 17.3:** a feat/fix subject must describe something an admin can see; a completion note must be true of the code; E2E cleanup must be snapshot-guarded (not needed here: nothing real is changed). TanStack Query v5 hook-level `onError` replaces the client default (no new mutation here).
- **16.5:** introduced the cards from the same sorted rows, the jsdom `matchMedia` stand-in and the 44px card targets; "keeps an open remove dialog when the layout switches" (`ModTable.test.tsx:1927`) must still pass with the control in the cards branch.
- **VSS-g54 / UI-062:** the preference always names a column (`enableSortingRemoval: false`); the control keeps that (it always sends a column).

### Git Intelligence

- Base b9606f1 (`docs(epic-18): plan epic 18 mod media and fixes`). Release notes come from commit subjects (`cliff.toml`). Planned: Task 1 `docs`, Task 2 `feat(story-18.4/task-2): sort installed mods on phones and tablets`, Task 3 `fix(story-18.4/task-3): long mod names wrap so the installed mods table fits at 1024px`, Task 4 `test`, Task 5 `docs`.

### Latest Technical Information

- No new libraries. Tailwind CSS 4.1.18: `wrap-anywhere` = `overflow-wrap: anywhere`; `min-w-36` = 9rem. `@tanstack/react-table` 9.3: `ColumnMeta` is declared for augmentation; `getAutoSortFn` picks `alphanumeric` for strings with digits. `@radix-ui/react-select` 2.2: `SelectTrigger` is a `combobox` whose name comes from `aria-labelledby`.

### Project Structure Notes

- New: `web/src/components/InstalledModsSortControl.tsx`, `web/src/lib/table-column-meta.d.ts`, `_bmad-output/implementation-artifacts/18-4-browser/column_widths.mjs`, `column_widths.before.json`, `column_widths.after.json`.
- Modified: `web/src/components/ModTable.tsx`, `web/src/components/ModUpdateCell.tsx`, `web/src/components/ModTable.test.tsx`, `web/src/components/ModUpdateCell.test.tsx`, `web/e2e/layout-widths.spec.ts`, `web/e2e/installed-mods-phone.spec.ts`.
- Component files are PascalCase like their neighbors (`InstalledModCard.tsx`), not the kebab-case of `project-context.md`'s naming table.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 18.4: Installed Mods List at Every Width]
- [Source: _bmad-output/planning-artifacts/prd.md] FR203, FR204 (`:721-722`)
- [Source: _bmad-output/planning-artifacts/architecture/epic-18-mod-media-and-fixes.md#ADR-6] (ADR-1 to ADR-5 do not touch this story)
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-16.md] (18.4 is web only; measures before choosing the width)
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md] 44px touch targets (`:515`, `:1180`, `:1290`), Responsive Strategy (`:1194-1215`)
- [Source: _bmad-output/implementation-artifacts/17-8-layout-at-tablet-and-phone-widths.md] and `17-8-browser/layout_widths.after.json`
- Beads: `VSS-bgu`, `VSS-n2u` (discovered from `VSS-dp1`), parent `VSS-5w8`
- `project-context.md` - no suppressions; manual checks need the maintainer's confirmation; story size at most 6 tasks

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

- Story created 2026-11-16 at b9606f1: context analysis of `ModTable`, `InstalledModParts`, `InstalledModCard`, `ModUpdateCell`, `SideBadge`, `PreferencesContext`, `use-media-query`, the shadcn `Table` and `Select`, the browse `SortControl`, `VersionTable`'s meta use, TanStack Table's `ColumnMeta` and auto sort, the 17.8 measurement script, specs and story, and ADR-6. Read-only column measurements and CSS simulations on the running dev stack (Dev Notes "Planning measurements"). A throwaway prototype of Tasks 2-3 run against the whole web suite (no failure) and a prototype test of the control in jsdom; both discarded.

### File List

## Change Log

- 2026-11-16: Story 18.4 created and validated (ready-for-dev). Validation against the create-story checklist, every cited path and line re-read at b9606f1: measured the columns instead of assuming them (Name wrapping alone does not fit at 1024 expanded, so the Available cell wraps too); `wrap-anywhere` instead of ADR-6's `break-words` (long slugs); `min-h-11` instead of `h-11` (the `SelectTrigger` data-size height outranks it); typed `ColumnMeta` so the body-cell change adds no type assertion; AC 6 narrowed to what any wrapping table can do, with the two exceptions measured; the planning note on Version sorting checked and not reproduced (follow-up 1 states the real defect); the 17.8 script kept unchanged and a new one added; the jsdom stubs Radix `Select` needs; the 44px E2E list extended.
