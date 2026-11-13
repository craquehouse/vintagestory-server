# Story 16.1: Mod Browser State Survives Mod Details

Status: in-progress

<!-- Implements Epic 16 ADR-1 (architecture/epic-16-ui-polish.md), which implements Epic 10 ADR-4. Beads: VSS-dkl (search/sort/filters), VSS-901 (page and scroll restoration). -->

## Story

As an **administrator**,
I want **the mod browser to keep my search, filters (including the game version filter) and sort when I look at a mod and come back**,
so that **I can compare several mods without searching and filtering again each time**.

## Acceptance Criteria

1. **Given** I have entered a search term, chosen a sort, and set filters: side, tags, mod type and **game version**
   **When** I open a mod's detail page and return with **Back to Browse**, the **Browse breadcrumb**, the **Browse tab** or the **browser's back button**
   **Then** the search box, the sort, and every filter including the game version are as I left them, and the results match them (the browse request carries the same `search`, `sort`, `side`, `tags`, `mod_type` and `version`)
   *(Covers FR167; maintainer report: "Back to Browse isn't maintaining a game version filter that was applied")*

2. **Given** I was on a later page of results and scrolled down
   **When** I open a mod and return from its detail page by any of the four ways in AC 1
   **Then** the same page is shown, with the same search, filters and sort, and the card I opened is scrolled into view
   **And** this does not depend on a fixed delay: the scroll happens once the results containing that card have rendered, and if the card is no longer in the results the page is left at the top
   *(Covers FR168; `VSS-901`)*

3. **Given** I change the search, a filter or the sort (after returning or at any time)
   **When** the results change
   **Then** the browser goes back to page 1, as it does today
   **And** typing in the search box does not add a browser history entry per keystroke, while each sort, filter or page change does, so browser back and forward step through them

4. **Given** the browse state is in the URL (`q`, `sort`, `side`, `tags`, `type`, `version`, `page`, defaults omitted)
   **When** I refresh the page or open a copied browse link
   **Then** the search, filters including the game version, sort and page are restored from the URL, without restoring a scroll position
   **And** `/game-server/mods/browse` with no parameters is the default state (no search, Newest, no filters, page 1), and unknown or invalid values fall back to their defaults

5. **Given** I click the **Browse** tab
   **When** I am on a detail page opened from the browser, **then** the browser opens with the state I opened the mod from;
   **when** I am anywhere else in Mods (Installed tab, or a detail page opened directly from a link), **then** it opens with the last browse state of this browser session, including the game version filter;
   **when** there is no saved state, **then** it opens in the default state

6. **Given** I opened a mod and then left through another page (for example Installed or Settings), or I refresh or load the browse page
   **When** the browser mounts
   **Then** no old scroll position is restored: the saved card is consumed on a return from its detail page and cleared on every other mount

## Tasks / Subtasks

<!-- Each functional task includes its tests in the same commit. Commit per task: type(story-16.1/task-N): ... ; feat/fix only for user-visible changes, subject written for users. -->

- [x] Task 1: Browse URL state helpers and a URL-controlled page in `useBrowseMods` + tests (AC: 3, 4)
  - [x] 1.1: Create `web/src/lib/browse-search.ts`: `BROWSE_PATH`, `BrowseUrlState` (`search`, `sort`, `filters: ModFilters`, `page`), `parseBrowseSearch(search: string): BrowseUrlState` and `buildBrowseSearch(state): string` (returns `''` or `?…`, parameters in the order `q, sort, side, tags, type, version, page`, defaults omitted, `tags` comma-separated, `q` trimmed). Invalid `sort`, `side`, `type` and `page` (not a positive integer) fall back to defaults; empty `tags`/`version` are omitted
  - [x] 1.2: Add `readBrowseSearchState(state: unknown): string | undefined` (navigation state `browseSearch`, accepted only when it is `''` or starts with `?`) and `isReturnFromModDetail(state: unknown): boolean` (`fromModDetail === true`); add `getLastBrowseSearch()` / `saveLastBrowseSearch(search)` for sessionStorage key `browse-last-search`, wrapped in try/catch like the existing restoration hook
  - [x] 1.3: Make `useBrowseMods` page controlled: `currentPage` comes from `params.page ?? 1`; `setPage`, `goToNextPage`, `goToPrevPage` validate as today and call an `onPageChange` callback passed in a second `options` argument instead of internal `useState`
  - [x] 1.4: Tests: `web/src/lib/browse-search.test.ts` (round trip for every parameter including `version`, defaults omitted, invalid values, ordering, tags with spaces, `q` trimming, navigation-state guards, sessionStorage failure); rewrite the `use-browse-mods.test.tsx` "pagination state management" and "edge cases" page tests to drive the controlled page through a `useState` wrapper instead of deleting them

- [x] Task 2: BrowseTab reads and writes its state through the URL + tests (AC: 1, 3, 4)
  - [x] 2.1: Replace `useState` for `filters` and `sort` with `useSearchParams`; derive `BrowseUrlState` with `useMemo` keyed on `searchParams.toString()` (trap: reference-compared filters reset the page every render)
  - [x] 2.2: Keep `searchInput` local for responsiveness, initialised from `q`; write the debounced (300 ms), trimmed value with `{ replace: true }` only when the debounced value itself changes; resync the input when `q` changes from outside (browser back/forward) by adjusting state during render, not in an effect
  - [x] 2.3: Sort, filter and page changes build the whole next parameter set in one `setSearchParams` call (push). Any change to `q`, `sort` or a filter removes `page`; delete the `prev*Ref` page-reset effect it replaces
  - [x] 2.4: Mirror `location.search` to `browse-last-search` whenever it changes
  - [x] 2.5: Tests in `BrowseTab.test.tsx` with a `MemoryRouter` harness that exposes the current location: initial state from URL for every parameter including `version` (asserted on the request URL and the filter UI), writes for search (replace), sort/side/version (push), page change, page reset on search/sort/filter change, invalid values, `browse-last-search` mirroring; adapt existing tests to the router harness

- [ ] Task 3: Links into browse carry the browse state + tests (AC: 1, 5)
  - [ ] 3.1: Card click and Enter-on-slug navigate to the detail page with `state: { browseSearch: location.search }`
  - [ ] 3.2: `ModDetailPage`: Back to Browse and the Browse breadcrumb go to `BROWSE_PATH + browseSearch` (empty when opened directly) with `state: { fromModDetail: true }`
  - [ ] 3.3: `ModsPage.handleTabChange('browse')`: precedence `state.browseSearch` (detail page opened from browse, with `fromModDetail`), then `browse-last-search`, then default. The Installed tab is unchanged
  - [ ] 3.4: Tests: `ModDetailPage.test.tsx` (back button and breadcrumb targets with a search, side, tags, type, `version` and sort; direct open → default), `ModsPage.test.tsx` (all three precedence branches, game version kept), `BrowseTab.test.tsx` (card and Enter pass `browseSearch`)

- [ ] Task 4: Restore position to the opened card, only on a return from its detail page + tests (AC: 2, 6)
  - [ ] 4.1: Rewrite `use-browse-scroll-restoration.ts` for the slug entry: sessionStorage `{ search, slug }` saved immediately before opening a mod; retire `browse-scroll-position` and `{ scrollY, page }`; pure `shouldRestoreOpenedCard(saved, currentSearch, isReturn)`
  - [ ] 4.2: `BrowseTab`: read the entry without side effects on first render; restore only if `saved.search === location.search` and the arrival is a return (`fromModDetail` state or `useNavigationType() === 'POP'`); clear the entry on every mount. Once results have rendered, `scrollIntoView({ block: 'center' })` the `mod-card-<slug>` element if that slug is in the results, then stop; remove the 100 ms `setTimeout`
  - [ ] 4.3: Rewrite `use-browse-scroll-restoration.test.ts` and the BrowseTab "Scroll Position Restoration" tests for the slug entry: save on card click and Enter, restore on `fromModDetail` and on `POP`, no restore on `PUSH` without state (detour), on a search mismatch, or when the slug is absent; entry cleared on every mount; no `setTimeout`

- [ ] Task 5: End-to-end round trip and browser verification against the Docker dev stack + tests (AC: all)
  - [ ] 5.1: Add `web/e2e/mod-browse-state.spec.ts` (Playwright, Docker stack, live mod database): set a search, a side filter, the **game version filter** and a sort, go to page 2, scroll, open a card; return by Back to Browse, the breadcrumb, the Browse tab and browser back; assert URL parameters, the search box, the version filter label, the sort label, the page, and that the opened card is in the viewport; plus refresh (state kept, no scroll) and detour (Installed → Browse tab keeps state, no scroll)
  - [ ] 5.2: `just docker restart`, run the spec (`cd web && bunx playwright test e2e/mod-browse-state.spec.ts`), and check the flow by hand in a browser at http://localhost:8080, including Slow 4G throttling and the browser console. Screenshots, if committed, mask the server name (`span.font-semibold` in the header, `#ServerName`) and password
  - [ ] 5.3: Record results in the Dev Agent Record; manual confirmation by the maintainer is still required before this task is treated as user-accepted

- [ ] Task 6: Quality gate and review hand-off (AC: all)
  - [ ] 6.1: `just check` (lint, typecheck, all tests) passes
  - [ ] 6.2: Story status `review`, `just sprint set 16-1-mod-browser-state-survives-mod-details review`, PR to `main`, PR link on `VSS-dkl` and `VSS-901`

## Dev Notes

### Current state (verified 2026-11-13 on `main` 8477096)

- `web/src/features/mods/BrowseTab.tsx:56-58`: `searchInput`, `filters` (`ModFilters`: `side`, `tags`, `modType`, `gameVersion`) and `sort` (`BrowseSortOption`, default `recent`) are `useState`. `browse` and `browse/:slug` are sibling routes in `web/src/App.tsx`, so opening a mod unmounts `BrowseTab` and all of it resets. This is why the **game version filter** is lost on Back to Browse (maintainer report).
- `BrowseTab.tsx:87-105`: restoration reads `{ scrollY, page }` (key `browse-scroll-position`) and scrolls after `setTimeout(…, 100)`. `BrowseTab.tsx:139-160` resets the page and clears the saved position when `prevFiltersRef.current !== filters` (reference comparison).
- `web/src/hooks/use-browse-mods.ts:70`: `const [currentPage, setCurrentPage] = useState(params.page ?? 1)`, initialised once. `goToNextPage`/`goToPrevPage` are used only by tests.
- `web/src/features/mods/ModDetailPage.tsx:450-452` (`handleBack`) and `:522-528` (breadcrumb) use the fixed path `/game-server/mods/browse`. The "Mods" breadcrumb (`/game-server/mods`) is not a browse link and stays as is.
- `web/src/features/mods/ModsPage.tsx:43-45`: `handleTabChange` navigates to `/game-server/mods/${value}`.
- No component uses `useSearchParams` yet. `react-router` 8.5.1, declarative `<BrowserRouter>`; `useSearchParams`, `useLocation`, `useNavigationType` and `navigate(to, { replace, state })` work; `<ScrollRestoration>` does not (data routers only).
- Story 16.0 probe (`16-0-spike/browse_probe.out.json`): unfiltered restoration works on all four return paths, also on Slow 4G (grid renders from the React Query cache); with a search the search resets and the restored page belongs to the unfiltered results; a detour restores a stale position.
- `web/src/main.tsx` renders under `<StrictMode>`: `useState` initialisers and mount effects run twice in development, so reading the saved card must be side-effect free and clearing must be idempotent.
- `just lint-web` is `tsc --noEmit`; there is no ESLint in the web package, but hooks must still follow the rules of hooks.

### Design (binding: Epic 16 ADR-1)

| Parameter | `BrowseUrlState` field | Default (omitted) | Validation |
|---|---|---|---|
| `q` | `search` | `''` | trimmed |
| `sort` | `sort` | `recent` | one of `recent`, `downloads`, `trending`, `name` |
| `side` | `filters.side` | none | one of `client`, `server`, `both` |
| `tags` | `filters.tags` | none | comma-separated, empty items dropped |
| `type` | `filters.modType` | none | one of `mod`, `externaltool`, `other` |
| `version` | `filters.gameVersion` | none | any non-empty string (the list loads asynchronously) |
| `page` | `page` | `1` | positive integer |

- History: debounced search → `replace`; sort, filter, page → push. Build the full next set in one `setSearchParams` call (`setSearchParams(fn)` does not queue like `setState`).
- Navigation state: `{ browseSearch: string }` on links into a detail page; `{ fromModDetail: true }` on the three links back (Back to Browse, breadcrumb, Browse tab on a detail page).
- sessionStorage: `browse-last-search` (full `location.search`, mirrored on change); opened-card entry `{ search, slug }` written only immediately before opening a mod, consumed or cleared on every `BrowseTab` mount.
- Restore: `document.querySelector('[data-testid="mod-card-<slug>"]')?.scrollIntoView({ block: 'center' })` after the results containing the slug render (`ModCard.tsx:88` sets the test id). Use `CSS.escape` on the slug if it is interpolated into a selector, or look it up by iterating the grid's children.

### Implementation traps

- **Controlled page:** do not keep a second copy of `page` in `useBrowseMods`. The URL is the only page state.
- **Memoized filters:** derive `filters` from the parameter string, not `searchParams` identity; never compare filters by reference.
- **Search echo:** after browser back changes `q`, the debounced value still holds the old text for 300 ms. Write `q` only when the debounced value changes, or back would rewrite the old search into the URL.
- **POP on refresh:** a refresh is also `POP`. It never restores because every mount consumes or clears the entry and the entry is written only when opening a mod.
- **Name sort (`VSS-stm.1`)** fails today with a 422; out of scope. `page` has no effect for it. Do not fix it here.

### Out of scope

- The Name (A-Z) sort failure (`VSS-stm.1`) and any other Epic 16 story.
- A data-router migration for `<ScrollRestoration>` (ADR-1 decision 5).
- Restoring the scroll offset inside the detail page.

### Testing Requirements

**CRITICAL:** Tests are written with each task and committed with it. `just test-web` after each task; `just check` before review.

- Unit: `web/src/lib/browse-search.test.ts`, rewritten `web/src/hooks/use-browse-scroll-restoration.test.ts`, updated `web/src/hooks/use-browse-mods.test.tsx`.
- Component: `BrowseTab.test.tsx`, `ModDetailPage.test.tsx`, `ModsPage.test.tsx`. Render BrowseTab inside `MemoryRouter` with `Routes` so `useSearchParams` works, and expose the location (a small `LocationProbe` component) to assert the URL and history behavior. The game version filter is asserted explicitly in every round-trip test, alongside search, side, tags, type and sort.
- Tests that encode the old `{ scrollY, page }` behavior are rewritten for the slug entry, not deleted.
- E2E: `web/e2e/mod-browse-state.spec.ts` runs against the Docker stack (`just test-e2e-web` or `bunx playwright test` with the stack up). It depends on the live mod database, so it picks cards from the rendered grid rather than hard-coding slugs. E2E tests are not part of `just check`.

**UI Stories - Manual Browser Verification:** Docker stack (`just docker restart`, http://localhost:8080, game 1.22.7 installed in `./data`). Verify the four return paths with a search, side, tags, type, **game version** and sort set, on page 2 or later, scrolled down; refresh; a copied link in a new tab; detour through Installed; Slow 4G throttling; browser console free of errors. `just docker stop` when done.

### Security Requirements

- No API changes. Navigation state and sessionStorage values are validated before use (`readBrowseSearchState`, JSON parse in try/catch); URL values are parsed into typed state and invalid values fall back to defaults.

### Development Commands

- `just test-web`, `just test-web src/lib/browse-search.test.ts`, `just check`, `just docker restart`, `just test-e2e-web`.

### Previous Story Intelligence

- **10.3 / 10.4:** search debounce is 300 ms (`useDebounce`); `SortControl` validates its value; `FilterControls` calls `onChange` with the whole next `ModFilters` object (removing a key, not setting `undefined`, for side/type/version).
- **10.7:** introduced pagination and `{ scrollY, page }` restoration; its tests (`BrowseTab.test.tsx` "Story 10.7" blocks, `use-browse-scroll-restoration.test.ts`) are the ones to rewrite.
- **11.4:** replaced `navigate(-1)` with the fixed browse path for predictable Back; keep an explicit path, now with the saved search.
- **16.0:** evidence and ADR-1; `16-0-spike/browse_probe.mjs` shows how to drive the browser and sample the opened card's visibility.

### Git Intelligence

- Recent `main` commits are release and dependency chores; the last story was 16.0 (spike, PR #144). Story branches merge without squash; commit per task with `type(story-16.1/task-N)`.

### Latest Technical Information

- react-router 8.5.1 (declarative mode): `useSearchParams()` returns `[URLSearchParams, setSearchParams(next, navigateOptions)]`; `navigateOptions` accepts `replace` and `state`. `useNavigationType()` returns `'POP' | 'PUSH' | 'REPLACE'`. Confirmed in Story 16.0 via Context7.

### Project Structure Notes

- New: `web/src/lib/browse-search.ts` (+ test), `web/e2e/mod-browse-state.spec.ts`.
- Modified: `BrowseTab.tsx`, `ModDetailPage.tsx`, `ModsPage.tsx`, `use-browse-mods.ts`, `use-browse-scroll-restoration.ts` and their tests.
- File naming kebab-case for new modules (`project-context.md`); co-located tests.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 16.1]
- [Source: _bmad-output/planning-artifacts/architecture/epic-16-ui-polish.md#ADR-1: Browse State in the URL, Position by Opened Card]
- [Source: _bmad-output/planning-artifacts/architecture/epic-10-architecture-decisions.md#ADR-4: URL State for Filters]
- [Source: _bmad-output/implementation-artifacts/16-0-epic-16-technical-preparation.md]
- [Source: _bmad-output/implementation-artifacts/16-0-spike/README.md] and `browse_probe.mjs`
- [Source: _bmad-output/implementation-artifacts/10-7-pagination.md]
- [Source: _bmad-output/implementation-artifacts/11-4-mods-page-migration.md]
- Beads: `VSS-dkl`, `VSS-901`, `VSS-stm.1`
- `project-context.md` - critical implementation rules and patterns

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5)

### Debug Log References

- Task 1: red run of `browse-search.test.ts` (module missing) and of the three new controlled-page tests in `use-browse-mods.test.tsx` before implementing. `use-browse-mods.test.tsx` has 2 pre-existing `it.skip` tests (game version client-side filter, disabled since VSS-y7u); not touched.
- Task 2: red run, 8 new URL-state tests failing; after implementation only the old 10.7 "restores page from saved position" test failed, as expected (the page now comes from the URL), and was rewritten for the URL.

### Completion Notes List

- Task 1: `web/src/lib/browse-search.ts` parses and builds the ADR-1 parameters (`q, sort, side, tags, type, version, page`, defaults omitted, invalid values to defaults), guards navigation state (`browseSearch`, `fromModDetail`) and wraps `browse-last-search` in sessionStorage. `useBrowseMods` no longer keeps the page: `params.page` is the current page and `setPage`/`goToNextPage`/`goToPrevPage` report through `options.onPageChange`. The hook's page tests now drive the page through a `useState` wrapper (`useControlledBrowseMods`) instead of being deleted; four new tests cover the controlled contract. BrowseTab keeps a local page state for this commit only (replaced by the URL in Task 2). Web: 3,051 passed, 4 skipped (pre-existing).
- Task 2: `BrowseTab` reads `q, sort, side, tags, type, version, page` with `useSearchParams` (memoized on the query string), keeps the search box local and writes the debounced, trimmed search with `replace` only when the debounced value changes; sort, filter and page changes push one complete parameter set, dropping `page` on search/sort/filter changes, and are skipped when they would not change the URL. The search box follows browser back/forward by adjusting state during render. `location.search` is mirrored to `browse-last-search`. The `prev*Ref` page-reset effect is gone. Tests use a `MemoryRouter` harness with a `LocationProbe` that logs every location and navigation type; ten new tests (every parameter including `version`, defaults, invalid values, replace vs push, page reset, no-op writes, back/forward resync with the debounce, sessionStorage mirroring) and the 10.7 page tests rewritten to assert the URL. Web: 3,061 passed.

### File List

- `web/src/lib/browse-search.ts` (new)
- `web/src/lib/browse-search.test.ts` (new)
- `web/src/hooks/use-browse-mods.ts`
- `web/src/hooks/use-browse-mods.test.tsx`
- `web/src/features/mods/BrowseTab.tsx`
- `web/src/features/mods/BrowseTab.test.tsx`
- `_bmad-output/implementation-artifacts/16-1-mod-browser-state-survives-mod-details.md`
