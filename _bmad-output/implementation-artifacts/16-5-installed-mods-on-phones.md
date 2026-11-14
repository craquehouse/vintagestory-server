# Story 16.5: Installed Mods on Phones

Status: review

<!-- Implements FR172. Bead: VSS-rr5 (Story 14.3 review L3). Stacks on Story 16.4 (branch story/16-4-formatted-description-in-mod-lookup-preview, no PR yet), itself on 16.3 (PR #150), 16.2 (PR #149) and 16.1 (PR #148). Do not touch web/src/components/ModLookupInput* or the Story 16.4 docs. No new dependencies. -->

## Story

As an **administrator**,
I want **installed mods to fit a phone screen**,
so that **I can update, enable and remove mods without scrolling sideways**.

## Acceptance Criteria

1. **Given** a viewport narrower than the Tailwind `md` breakpoint (48rem, 768px)
   **When** I open Installed mods
   **Then** each installed mod is a card showing its name (linking to the mod database, with the slug under it when a name exists), its installed version, its side, its update status (the same "Available" content as the table: offered version with an Update action, or "Up to date", "No compatible update", "Unknown"), an enable toggle and a remove action; no table is rendered, and neither the page nor any element inside it scrolls horizontally at 390px wide, also when "Update all" is offered
   *(Covers FR172; `VSS-rr5`)*

2. **Given** a card for a mod that is `not_verified` or `incompatible`
   **When** it is shown
   **Then** it carries the same compatibility information as the table row (Story 16.3): the compatibility badge, "Supports up to X" when the latest supported game version is known, and the compatibility message, shown as visible text because the badge tooltip cannot be reached by touch. A `compatible` card shows only the badge

3. **Given** the cards
   **When** they are listed and their actions are used
   **Then** they appear in the same order as the table under the current sort preference (`installedModsSort`, default name ascending), and the toggle, Update and remove actions go through the same handlers, confirmation dialogs, spinners and toasts as the table (one data source, one set of mutation handlers)

4. **Given** a viewport narrower than `md`
   **When** I use the Installed mods controls
   **Then** the card's enable toggle, Update and remove controls, and the tab's "Update all" and "Check for updates" buttons, are at least 44x44px touch targets, and each control has an accessible name

5. **Given** a viewport at `md` or wider
   **When** I open Installed mods
   **Then** the existing table is unchanged (same columns, sortable headers, test IDs and behavior), and resizing the window across the breakpoint switches between table and cards without a reload

6. **Given** the mod list is loading or empty
   **When** I open Installed mods at either width
   **Then** the existing loading spinner and "No mods installed yet" state are shown, unchanged

## Tasks / Subtasks

<!-- Each functional task includes its tests in the same commit. Commit per task: type(story-16.5/task-N): ... ; feat/fix only for user-visible changes, subject written for users. -->

- [x] Task 1: Media query hook and a viewport helper for tests + tests (AC: 5)
  - [x] 1.1: `web/src/hooks/use-media-query.ts`: `useMediaQuery(query: string): boolean` built on `useSyncExternalStore` (`subscribe` adds and removes a `change` listener on `window.matchMedia(query)`; the snapshot reads `.matches`), and `MD_UP_QUERY = '(min-width: 48rem)'` (Tailwind v4's `md`, 768px at the default root font size). No fallback for a missing `matchMedia`: every supported browser has it
  - [x] 1.2: jsdom has no `matchMedia`. Add `web/tests/viewport.ts`: a `matchMedia` stand-in that evaluates `min-width`/`max-width` in `px` or `rem` (16px) against `window.innerWidth` (other queries never match) and notifies `change` listeners, plus `setViewportWidth(width)` that sets `innerWidth` and notifies listeners whose result changed (inside `act` in tests). `tests/setup.ts` installs it and resets the width to jsdom's default 1024 after each test, so every existing test keeps rendering the desktop layout
  - [x] 1.3: Tests `web/src/hooks/use-media-query.test.tsx`: true at 1024 and at exactly 768, false at 767 and 390, updates when the width crosses the breakpoint, unsubscribes on unmount; a test for the stand-in's `rem`/`px` parsing. Run the full web suite (the stand-in is global; `next-themes` mocks stay as they are)

- [x] Task 2: Share the installed mod cell content between table and cards + tests (AC: 3, 5)
  - [x] 2.1: Move the cell bodies out of the `ModTable` column definitions into `web/src/components/InstalledModParts.tsx`, unchanged in markup, classes and test IDs: `ModNameLink` (link + slug), `ModCompatibility` (badge with message tooltip and "Supports up to X"; new optional `showMessage` that renders the message as text, off for the table), `ModEnableToggle` (switch + spinner, `aria-label` as today) and `ModRemoveButton` (icon button, `aria-label="Remove <name>"`; optional `className` for the card size). Export the `ModTableRow` type from there
  - [x] 2.2: `ModTable` columns render these parts; `ModUpdateCell` stays as is apart from an optional `buttonClassName` passed to its Update button (for the card's touch size; the table passes nothing)
  - [x] 2.3: Tests: the whole existing `ModTable.test.tsx` passes unchanged (proves the table is unchanged); new `InstalledModParts.test.tsx` covers `ModCompatibility` with and without `showMessage` (message shown only for `not_verified`/`incompatible`), `ModEnableToggle` spinner and name, `ModRemoveButton` name; `ModUpdateCell.test.tsx` covers `buttonClassName`

- [x] Task 3: Installed mods as cards below `md` + tests (AC: 1, 2, 3, 4, 5, 6)
  - [x] 3.1: `web/src/components/InstalledModCard.tsx`: one card per mod (`<li>` with `data-testid="installed-mod-card-<slug>"`, `aria-label` = mod name) built from the Task 2 parts and `ModUpdateCell`: name and slug with the enable toggle on the first row; version and side badge; compatibility with `showMessage`; an "Available" row with the update status and Update action; the remove button. Long names, slugs and messages wrap (`min-w-0`, `break-words`), never widen the card. Touch targets: the toggle sits in a `<label>` of at least 44x44px (`min-h-11 min-w-11`) so a tap anywhere in it toggles; the Update and remove buttons are `min-h-11`/`size-11`
  - [x] 3.2: `ModTable` picks the layout with `useMediaQuery(MD_UP_QUERY)`: the table at `md` and up, otherwise `<ul data-testid="installed-mod-cards" aria-label="Installed mods">` with one card per `table.getRowModel().rows` (same sorted row model, so the order always matches the table), passing the existing `handleToggle`, `handleUpdate`, `handleRemoveClick`, `isTogglingMod`, `isChangingVersion` and `gameVersion`. Loading, empty state and both dialogs stay shared and outside the switch. Update the component doc comment
  - [x] 3.3: Tests in `ModTable.test.tsx` ("Story 16.5: cards below md" block, `setViewportWidth(390)`): cards render and `mod-table` does not; each card shows name link, slug, version, side, update status; the Update action opens the same confirmation flow (same request as the table test); toggle calls enable/disable and shows the spinner; remove opens the shared dialog and removes; incompatible card shows badge, "Supports up to X" and the message text, compatible card no message; card order follows the sort preference (name asc default, a stored `version desc` preference); touch-size classes present on toggle label, Update and remove; loading and empty states at 390; crossing the breakpoint with `setViewportWidth` switches table ↔ cards. At the default width the existing table tests are untouched

- [x] Task 4: Installed tab toolbar fits a phone + tests (AC: 1, 4, 5)
  - [x] 4.1: `InstalledTab`: the button group wraps (`flex-wrap`) so "Last checked …", "Update all (N)" and "Check for updates" never push the page wider than the screen (today at 390px with "Update all" shown the document is 413px wide); below `md` the two buttons are 44px tall (`max-md:h-11`). At `md` and up the toolbar looks as today
  - [x] 4.2: Tests in `InstalledTab.test.tsx`: the group has `flex-wrap`; both buttons carry the touch-height class; existing toolbar tests pass

- [x] Task 5: Browser verification against the Docker dev stack + E2E spec (AC: 1-6)
  - [x] 5.1: `web/e2e/installed-mods-phone.spec.ts` (Story 16.5): replaces `GET /api/v1alpha1/mods` and `GET /api/v1alpha1/mods/updates` with `page.route` (like `installed-mod-any-modid.spec.ts`), so it installs nothing: a mod with a long name and an offered update, an incompatible mod, a disabled mod. At 390x844: cards visible, no `mod-table`, `document.documentElement.scrollWidth <= clientWidth`, no element under `main` with `scrollWidth > clientWidth` and `overflow-x` auto/scroll, toggle label, Update, remove, "Update all" and "Check for updates" bounding boxes at least 44x44, clicking Update opens the confirmation dialog or calls the version endpoint (route it, never change data), clicking remove opens the dialog and Cancel closes it. At 1440x900: `mod-table` visible with its columns, no cards. Resize 1440 → 390 switches to cards
  - [x] 5.2: `just docker restart` (rebuild from this branch); run the spec with `cd web && bunx playwright test e2e/installed-mods-phone.spec.ts`. Then a manual pass on the real `./data` mods at 390x844 and 1440x900 (no installs or removals; a toggle, if exercised, is toggled back), browser console clean. Screenshots with the server name (header `span.font-semibold`, `#ServerName`) masked, kept in the session scratchpad unless needed; record the results in the Dev Agent Record

- [x] Task 6: Quality gate and review hand-off (AC: all)
  - [x] 6.1: `just check` passes
  - [x] 6.2: Status review, `just sprint set 16-5-installed-mods-on-phones review`, PR to `story/16-4-formatted-description-in-mod-lookup-preview` (stacks on 16.4, #150, #149, #148), PR link on `VSS-rr5`

## Dev Notes

### Today's behavior (measured on `story/16-4-formatted-description-in-mod-lookup-preview` 10c2706, Docker stack, Chromium)

- `InstalledTab` (`web/src/features/mods/InstalledTab.tsx`) renders a toolbar and `ModTable`. `ModTable` (`web/src/components/ModTable.tsx`) is a TanStack Table v9 (`useTable`, `rowSortingFeature`) with columns Name, Version, Available (`ModUpdateCell`), Side, Compatibility (badge + "Supports up to X", Story 16.3), Status (switch) and a remove button. The shadcn `Table` wraps it in `div[data-slot=table-container].overflow-x-auto`.
- At 390x844 with the five `./data` mods the document is 390px wide but the table container scrolls: 751px of content in 358px. With "Update all" offered (three faked updates) the table is 904px and the toolbar pushes the **document** to 413px, so the whole page scrolls sideways.
- Touch sizes at 390px: switch 32x18, remove 36x36, Update and toolbar buttons 32px tall.
- Sorting is a persisted preference (`PreferencesContext.installedModsSort`, cookie), changed only from the table headers; default name ascending.
- The layout already uses `md` for the sidebar (`Layout.tsx`: hamburger below `md`, `p-4` gutter, so content is 358px at 390).

### Decisions

- **Switch layouts with a media query hook, not CSS hiding.** Rendering both and hiding one with `md:hidden`/`hidden md:block` would mount every switch, button and link twice. In jsdom (no Tailwind CSS is applied in Vitest) both would be "visible", so every existing `getByTestId('mod-toggle-…')`/`getByRole('button', { name: 'Remove …' })` in `ModTable.test.tsx` and `InstalledTab.test.tsx` would find two elements, and tests could not tell the layouts apart. With `useMediaQuery` exactly one layout is mounted, the controls keep their existing test IDs in both layouts (so action tests work on either), tests choose the layout with `setViewportWidth`, and the existing suite keeps running against the table at jsdom's 1024px default. Cost: the layout is chosen in JS; in this client-only SPA `useSyncExternalStore` reads `matchMedia` synchronously on the first render, so there is no flash.
- **Breakpoint `(min-width: 48rem)`**, the same value as Tailwind v4's `md` (`@media (width >= 48rem)`), so the hook and the `md:`/`max-md:` classes switch at the same width.
- **One data source, one set of handlers.** Cards are rendered from `table.getRowModel().rows`, the same TanStack row model as the table, and receive the handlers `ModTable` already has. No second query, no second mutation hook, no second dialog.
- **Shared parts, not shared columns.** The cell bodies move into small components used by both column definitions and the card; the table's markup does not change. `ModUpdateCell` is reused as is (it already renders the label and the Update action), with only an optional class for the card's button size.
- **No sort control on the cards.** The cards follow the current sort preference; changing it on a phone is out of scope (bead, see below). FR172 asks for cards without horizontal scrolling, not sorting.
- **Compatibility message as text on cards** (AC 2): the table shows it as the badge tooltip, which touch screens never show; Story 16.3 made the same choice for the detail page. The table is unchanged.
- **Update status reasons** stay as they are in `ModUpdateCell` (label with a `title` tooltip and screen-reader text). Showing them visibly is not asked for by FR172.
- **Card test IDs:** `installed-mod-cards` and `installed-mod-card-<slug>`; `mod-card-<slug>` is already used by the browse grid (Epic 16 ADR-1 scrolls to it).

### Card layout (390px, 358px content)

```text
┌──────────────────────────────────────────────┐
│ Auto Map Markers ↗                 [Enabled ●]│  name link + slug; toggle in a 44px label
│ egocaribautomapmarkers                        │
│ v5.0.3 · [Both]                               │  version + side
│ [Not verified] Supports up to 1.22.3          │  ModCompatibility showMessage
│ Mod not explicitly verified for 1.22.7. …     │
│ Available  v5.1.0 [ Update ]            [ 🗑 ] │  ModUpdateCell + remove
└──────────────────────────────────────────────┘
```

### Out of scope

- A sort control for the cards, touch sizes of controls outside the Installed tab (sidebar, tabs, header), and the Browse tab (already cards). Any other Epic 16 story. `web/src/components/ModLookupInput*` and Story 16.4 files are not touched (pending decision on 16.4).
- The existing `eslint-disable-next-line react-hooks/exhaustive-deps` above the `ModTable` columns `useMemo` predates this story; do not add another. If the column dependencies change, keep the existing comment untouched and add no suppressions.

### Testing Requirements

**CRITICAL:** Tests are written with each task and committed with it. `just test-web <file>` after each task; `just check` before review.

- Vitest runs jsdom with `css: true` but without the Tailwind plugin, so classes are not applied: assert layout with the viewport helper and class names (`flex-wrap`, `min-h-11`, `size-11`, `max-md:h-11`), and measure real sizes and overflow in Playwright (Task 5).
- `ModTable.test.tsx` mocks `@/hooks/use-mods` partially (compatibility) and `next-themes`/cookies; reuse its `createWrapper` and response fixtures for the card block.
- Reset: `tests/setup.ts` restores `innerWidth` to 1024 after each test; never rely on test order.

**UI Stories - Manual Browser Verification:** Docker stack (`just docker restart`, http://localhost:8080, game 1.22.7, five mods in `./data`). Do not install, remove or update mods in `./data`; the E2E spec fakes the list and updates with `page.route`. Committed screenshots mask the server name (`span.font-semibold` in the header, `#ServerName`) and password. Check the browser console.

### Security Requirements

- UI-only; no API, auth or data changes. Mod names and messages are rendered as text (React escaping), as today.

### Development Commands

- `just test-web src/hooks/use-media-query.test.tsx`, `just test-web src/components/ModTable.test.tsx`, `just test-web src/components/InstalledModParts.test.tsx`, `just test-web src/features/mods/InstalledTab.test.tsx`, `just check`, `just docker restart`, `cd web && bunx playwright test e2e/installed-mods-phone.spec.ts`.

### Previous Story Intelligence

- **16.3:** Added `compatibility` (message, `latestSupportedGameVersion`) to `ModTableRow` via `useModsCompatibility(...).compatibilityDetails`; "Supports up to X" (`mod-latest-supported-<slug>`) only for `not_verified`/`incompatible`. Cards must show the same. Live data: Smithing Plus and Auto Map Markers are Not verified (supports up to 1.22.2 / 1.22.3).
- **16.2 / 16.3 E2E:** specs fake `GET /api/v1alpha1/mods` with `page.route` and set `localStorage.apiKey` in an init script; the admin key is `VS_API_KEY_ADMIN` from `.env` (default `changeme`).
- **14.3:** `useVersionChangeFlow` tracks pending changes per slug (`isPending(slug)`) and owns the confirmation dialog; `ModUpdateCell` hides the action when `onUpdate` is omitted. Review L3 filed this story's bead.
- **16.1:** `just lint-web` is `tsc --noEmit`; React StrictMode double-mounts (the hook must unsubscribe cleanly).

### Git Intelligence

- Branch `story/16-5-installed-mods-on-phones` from `origin/story/16-4-formatted-description-in-mod-lookup-preview` (10c2706); PR base is that branch. 16.4 touched only the description sanitizer, `ModLookupInput` and `ModDetailPage`; no overlap with this story's files. Planned types: Task 1 `refactor` (hook and test helper, nothing visible), Task 2 `refactor`, Task 3 `feat`, Task 4 `fix` (the page scrolled sideways on phones), Task 5 `test`, Task 6 `chore`.

### Latest Technical Information

- No new libraries. React 19 `useSyncExternalStore`; Tailwind v4 `md` = `48rem` and the `max-md:` variant; TanStack Table v9 `table.getRowModel().rows` already sorted by `rowSortingFeature`; Playwright `page.setViewportSize` for the resize check.

### Project Structure Notes

- New: `web/src/hooks/use-media-query.ts` (+ test), `web/tests/viewport.ts`, `web/src/components/InstalledModParts.tsx` (+ test), `web/src/components/InstalledModCard.tsx`, `web/e2e/installed-mods-phone.spec.ts`. Components use PascalCase file names like their neighbors (`ModTable.tsx`), hooks kebab-case.
- Modified: `web/tests/setup.ts`, `web/src/components/ModTable.tsx` (+ test), `web/src/components/ModUpdateCell.tsx` (+ test), `web/src/features/mods/InstalledTab.tsx` (+ test).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 16.5: Installed Mods on Phones]
- [Source: _bmad-output/planning-artifacts/prd.md] FR172
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md] Mobile-Specific Patterns (mod cards show the Update action and status label; 44px touch targets; card layout for mod list), Responsive Strategy (Mobile < 768px: card-based layouts instead of tables), Breakpoint Strategy, Touch Accessibility, "Avoid horizontal scrolling on mobile"
- [Source: _bmad-output/implementation-artifacts/14-3-update-and-version-switching-ui.md] Review L3
- [Source: _bmad-output/implementation-artifacts/16-3-latest-supported-game-version-for-incompatible-mods.md]
- Beads: `VSS-rr5` (this story), parent `VSS-stm`
- `project-context.md` - critical implementation rules and patterns

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5)

### Debug Log References

- Task 1: red run (module missing), then the stand-in's own test failed on a wrong expectation in the test (`49rem` is 784px, not over 800); fixed the test. 9 passed; full web suite 3,167 passed, 4 skipped (pre-existing `it.skip`s) with the stand-in installed globally; `tsc` clean.
### Completion Notes List

- Task 1: `useMediaQuery(query)` on `useSyncExternalStore` and `MD_UP_QUERY = '(min-width: 48rem)'`. `web/tests/viewport.ts` installs a `matchMedia` stand-in (typed `MediaQueryList`/`MediaQueryListEvent` implementations, no casts) evaluating `min-width`/`max-width` in px/rem against `innerWidth`, with `setViewportWidth` and `resetViewport`; `tests/setup.ts` installs it and resets to 1024px after each test.
### File List

- `web/src/hooks/use-media-query.ts` (new)
- `web/src/hooks/use-media-query.test.tsx` (new)
- `web/tests/viewport.ts` (new)
- `web/tests/setup.ts`
- `web/src/components/InstalledModParts.tsx` (new)
- `web/src/components/InstalledModParts.test.tsx` (new)
- `web/src/components/InstalledModCard.tsx` (new)
- `web/src/components/ModTable.tsx`
- `web/src/components/ModTable.test.tsx`
- `web/src/components/ModUpdateCell.tsx`
- `web/src/components/ModUpdateCell.test.tsx`
- `web/e2e/installed-mods-phone.spec.ts` (new)
- `web/src/features/mods/InstalledTab.tsx`
- `web/src/features/mods/InstalledTab.test.tsx`
- `_bmad-output/implementation-artifacts/16-5-installed-mods-on-phones.md`
## Change Log

- 2026-11-13: Story 16.5 created (ready-for-dev).
- 2026-11-13: Implemented: media query hook and test viewport helper; cell content shared by table and cards; installed mods as cards below `md` with 44px controls and the compatibility message as text; toolbar wraps on phones; E2E spec and browser verification at 390x844 and 1440x900; status review.
