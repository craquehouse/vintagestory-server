# Story 16.5: Installed Mods on Phones

Status: done

<!-- Implements FR172. Bead: VSS-rr5 (Story 14.3 review L3). Stacks on Story 16.4 (branch story/16-4-formatted-description-in-mod-lookup-preview, PR #151), itself on 16.3 (PR #150), 16.2 (PR #149) and 16.1 (PR #148). Do not touch web/src/components/ModLookupInput* or the Story 16.4 docs. No new dependencies. -->

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
  - [x] 3.3: Tests in `ModTable.test.tsx` ("Story 16.5: cards below md" block, `setViewportWidth(390)`): cards render and `mod-table` does not; each card shows name link, slug, version, side, update status; the Update action opens the same confirmation flow (same request as the table test); toggle calls enable/disable and shows the spinner; remove opens the shared dialog and removes; incompatible card shows badge, "Supports up to X" and the message text, compatible card no message; card order follows the sort preference (name asc default, a stored `enabled desc` preference); touch-size classes present on toggle label, Update and remove; loading and empty states at 390; crossing the breakpoint with `setViewportWidth` switches table ↔ cards. At the default width the existing table tests are untouched

- [x] Task 4: Installed tab toolbar fits a phone + tests (AC: 1, 4, 5)
  - [x] 4.1: `InstalledTab`: the button group wraps (`flex-wrap`) so "Last checked …", "Update all (N)" and "Check for updates" never push the page wider than the screen (today at 390px with "Update all" shown the document is 413px wide); below `md` the two buttons are 44px tall (`max-md:h-11`). At `md` and up the toolbar looks as today
  - [x] 4.2: Tests in `InstalledTab.test.tsx`: the group has `flex-wrap`; both buttons carry the touch-height class; existing toolbar tests pass

- [x] Task 5: Browser verification against the Docker dev stack + E2E spec (AC: 1-6)
  - [x] 5.1: `web/e2e/installed-mods-phone.spec.ts` (Story 16.5): replaces `GET /api/v1alpha1/mods` and `GET /api/v1alpha1/mods/updates` with `page.route` (like `installed-mod-any-modid.spec.ts`), so it installs nothing: a mod with a long name and an offered update, an incompatible mod, a disabled mod. At 390x844: cards visible, no `mod-table`, `document.documentElement.scrollWidth <= clientWidth`, no element under `main` with `scrollWidth > clientWidth` and `overflow-x` auto/scroll, toggle label, Update, remove, "Update all" and "Check for updates" bounding boxes at least 44x44, clicking Update opens the confirmation dialog or calls the version endpoint (route it, never change data), clicking remove opens the dialog and Cancel closes it. At 1440x900: `mod-table` visible with its columns, no cards. Resize 1440 → 390 switches to cards
  - [x] 5.2: `just docker restart` (rebuild from this branch); run the spec with `cd web && bunx playwright test e2e/installed-mods-phone.spec.ts`. Then a manual pass on the real `./data` mods at 390x844 and 1440x900 (no installs or removals; a toggle, if exercised, is toggled back), browser console clean. Screenshots with the server name (header `span.font-semibold`, `#ServerName`) masked, kept in the session scratchpad unless needed; record the results in the Dev Agent Record

- [x] Task 6: Quality gate and review hand-off (AC: all)
  - [x] 6.1: `just check` passes
  - [x] 6.2: Status review, `just sprint set 16-5-installed-mods-on-phones review`, PR to `story/16-4-formatted-description-in-mod-lookup-preview` (stacks on 16.4 #151, #150, #149, #148), PR link on `VSS-rr5`

### Review Follow-ups (AI)

- [x] [AI-Review][Medium] M1: Task 3.3 said the order test uses a stored `version desc` preference; the test stores `enabled desc`. Fixed the story wording
- [x] [AI-Review][Medium] M2: PR #152 conflicted after 16.4 gained e5fdbdd and a5675c7 (review fixes, done). Fixed by merging `origin/story/16-4-formatted-description-in-mod-lookup-preview` (b29a0e8, no force-push); `sprint-status.yaml` keeps 16.4 `done` and this story's entry
- [x] [AI-Review][Low] L3: the card's Update button guaranteed only its height; while updating (spinner only) it was about 40px wide. Fixed: `min-h-11 min-w-11`, unit test asserts the class, E2E asserts a computed `min-width` of at least 44px (red on the previous build: `auto`) (084f06e)
- [x] [AI-Review][Low] L4: no test that a confirmation dialog survives a layout switch. Added: at 390 open the remove dialog, switch to 1024, the dialog stays and Confirm sends the DELETE (d3c0ceb). It passed on first run: the dialog state lives in `ModTable` outside the layout switch
- [x] [AI-Review][Low] L5: `useMediaQuery` has no `getServerSnapshot`. Accepted: client-only SPA, no server rendering
- [x] [AI-Review][Low] L6: the `matchMedia` stand-in evaluated comma-separated (OR) queries as AND. Fixed: split on commas and match when any part does; doc comment updated; test added, red first (dd8c1d1)

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
- Task 2: red run: `InstalledModParts.test.tsx` failed to import and the new `ModUpdateCell` test failed; then green. The existing `ModTable.test.tsx` passes without changes. Full web suite 3,179 passed, 4 skipped; `tsc` clean.
- Task 3: red run: 7 of the 13 new card tests failed (the action tests already passed against the table, since both layouts use the same test IDs); then 62 passed (1 pre-existing skip). The label-tap test was checked to fail with the label turned into a `div`. Full web suite 3,192 passed, 4 skipped; `tsc` clean. First look on the rebuilt Docker stack at 390x844 with three faked updates: cards, no table, card controls 44px (toggle label 91x44, remove 44x44, Update 71x44), no console messages; the toolbar still widened the document to 413px (Task 4).
- Task 4: red run, both new toolbar tests failed; then 19 passed. Full web suite 3,194 passed, 4 skipped.
- Task 5: `just docker restart` rebuilt the stack from this branch (game 1.22.7, five mods in `./data`: Auto Map Markers, BetterRuins, Carry On, CarryOnLib, SmithingPlus). `bunx playwright test e2e/installed-mods-phone.spec.ts` (admin key from `.env`): 4 passed. Its document-overflow assertion is the measurement that read 413px on the Task 3 build. Manual pass with a scratchpad Playwright script on the real mods, reads only (no POST/PUT/DELETE sent):
  - 390x844: 5 cards, no table, document overflow 0, no scrolling element under `main`; the Not verified cards (Auto Map Markers, SmithingPlus) show the badge, "Supports up to 1.22.3" / "1.22.2" and the message as text; compatible cards only the badge.
  - 1440x900: the table as before (same columns, sort header, "Supports up to" beside the badge), no cards, no overflow.
  - 767px: cards; 768px: table. The order is the same in both layouts (name ascending).
  - At 768px the unchanged table still scrolls inside its container (751px in 560px; it fits from about 1024px): bead `VSS-dp1`.
  - No console errors or warnings at any width. Screenshots (server name masked) kept in the session scratchpad, not committed. `./data` untouched.
- Task 6: `just check` passed: ruff and `tsc` clean, pyright 0 errors (3 pre-existing warnings in API tests), API 2,108 passed, web 3,194 passed and 4 skipped (pre-existing `it.skip`s), script tests 190 passed. No suppressions added.
- Rebase: Story 16.4's branch moved during development (995e222, de24045, 8ab8b8a: lookup preview removed, story rescoped, PR #151). Rebased this branch onto 8ab8b8a; the only conflicts were the adjacent 16-4/16-5 lines in `sprint-status.yaml`, resolved in each commit by keeping 16.4's `review` and this story's own status, so this branch never changes the 16-4 entry. After the rebase `just check` passed again (API 2,108 passed; web 3,079 passed and 4 skipped, fewer because 16.4 removed the `ModLookupInput` tests; scripts 190 passed; pyright 0 errors, 3 pre-existing warnings), the rebuilt Docker stack passed the E2E spec (4 passed), and the manual pass gave the same results.

- Review fixes: red runs for L3 (unit class assertion; E2E `min-width` on the previous build) and L6 (stand-in OR test); L4's test passed first time (behavior already correct). After the merge and fixes `just check` passed: API 2,108 passed; web 3,084 passed and 4 skipped (pre-existing); scripts 190 passed; pyright 0 errors (3 pre-existing warnings); ruff and `tsc` clean. `just docker restart` then the phone E2E spec: 4 passed (a first run seconds after the restart failed all four while the server was still starting; rerun once ready).

### Completion Notes List

- Task 1: `useMediaQuery(query)` on `useSyncExternalStore` and `MD_UP_QUERY = '(min-width: 48rem)'`. `web/tests/viewport.ts` installs a `matchMedia` stand-in (typed `MediaQueryList`/`MediaQueryListEvent` implementations, no casts) evaluating `min-width`/`max-width` in px/rem against `innerWidth`, with `setViewportWidth` and `resetViewport`; `tests/setup.ts` installs it and resets to 1024px after each test.
- Task 2: `InstalledModParts.tsx` holds `ModTableRow`, `ModNameLink`, `ModCompatibility` (new `showMessage`: message as text for `not_verified`/`incompatible`, `mod-compatibility-message-<slug>`), `ModEnableToggle` and `ModRemoveButton` (optional `className`), with the table's markup, classes, test IDs and names. `ModTable` columns render them; `ModUpdateCell` gained `buttonClassName` for its Update button.
- Task 3: `InstalledModCard` (`<li>` named after the mod): name link and slug with the toggle in a 44px `<label>` (visible Enabled/Disabled text; tapping anywhere in it toggles), version and side, `ModCompatibility showMessage`, an Available row with `ModUpdateCell` (`buttonClassName="min-h-11"`) and a `size-11` remove button. `ModTable` mounts the table at `md` and up, otherwise `<ul aria-label="Installed mods" data-testid="installed-mod-cards">` built from `table.getRowModel().rows` with its existing handlers; loading, empty state and both dialogs are shared.
- Task 4: the toolbar's button group wraps (`flex-wrap`), so "Last checked …", "Update all (N)" and "Check for updates" stack on phones instead of widening the page; both buttons are `max-md:h-11`. Unchanged at `md` and up.
- Task 5: `web/e2e/installed-mods-phone.spec.ts` fakes the mod list, update status, lookups and every write with `page.route` (a version change answers 409 confirmation-required, other writes 500), so it needs no data changes and no mod database. It checks cards, content, compatibility text, no horizontal overflow (document and scroll containers), 44x44px targets, the Update and remove dialogs and the label-tap enable request at 390x844, and the table, its headers and the live switch to cards at 1440x900.
- Task 6: status review; PR targets `story/16-4-formatted-description-in-mod-lookup-preview` (stacks on 16.4 #151, #150, #149, #148).
- Decisions: layouts switch with `useMediaQuery` (one layout mounted, existing test IDs and names reused, tests pick the width with `setViewportWidth`) rather than CSS hiding; cards come from the table's sorted row model and use its handlers and dialogs; the card shows the compatibility message as text; the table is unchanged.
- Beads filed (top-level, not Epic 16): `VSS-dp1` [UI-076] Installed table scrolls sideways at tablet widths, `VSS-bgu` [UI-077] sort control for the cards.

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
- 2026-11-13: Merged the updated Story 16.4 branch (review fixes, 16.4 done) into this branch (b29a0e8) to resolve the PR conflict.
- 2026-11-13: Code review (GLM 5.3 FlashX via OpenCode, Approve). M1, M2, L3, L4, L6 fixed; L5 accepted. Status done.

## Senior Developer Review (AI)

**Date:** 2026-11-13
**Reviewer:** GLM 5.3 FlashX via OpenCode (OpenRouter), delegated read-only review of the PR #152 head
**Outcome:** Approve → resolved

**Summary:** All six acceptance criteria are implemented and the File List matches the diff. The desktop table markup was verified unchanged against 8ab8b8a. On the PR head the web tests passed (3,079 passed, 4 skipped) and the typecheck was clean. Two medium and four low findings; five fixed, one accepted.

### Action Items

- [x] [Medium] M1 story wording of the sort preference test (fixed in the story)
- [x] [Medium] M2 PR conflicting with the updated 16.4 branch (merged, b29a0e8)
- [x] [Low] L3 card Update button width while updating (fixed, 084f06e)
- [x] [Low] L4 dialog across a layout switch untested (test added, d3c0ceb)
- [x] [Low] L5 no `getServerSnapshot` (accepted: client-only SPA)
- [x] [Low] L6 stand-in treated comma-separated queries as AND (fixed, dd8c1d1)
