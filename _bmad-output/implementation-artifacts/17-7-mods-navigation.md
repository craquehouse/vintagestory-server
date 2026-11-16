# Story 17.7: Mods Navigation

Status: ready-for-dev

<!-- Implements FR189-FR190. Beads: VSS-2oz, VSS-nhb. Web only (no API source change; one API test pins the contract the web relies on). Stacked after Stories 17.5 and 17.6 (each stacked on the previous); this story was written and its line references verified at 21457bf (Story 17.4 done, branch story/17-4-installed-status-is-right-everywhere). Re-check every line number on the branch you start from. No Epic 17 ADR governs this story (the Epic 17 ADR file says 17.7 "needs no decision"); Epic 16 ADR-1 (browse state in the URL) does. No new dependencies. Not in scope: Story 17.8 layouts, anything else under Mods. -->

## Story

As an **administrator**,
I want **the Mods tabs and shared browse links to take me where they say**,
so that **I am not stuck on a detail page or looking at a page number that does not exist**.

## Acceptance Criteria

1. **Given** a mod detail page (`/game-server/mods/browse/:slug`), opened from the browser or directly
   **When** I look at the Mods tabs
   **Then** Browse is the active tab (`data-state="active"`, `aria-selected="true"`) and Installed is not. `/game-server/mods/browse` (also with a trailing slash) shows Browse active; `/game-server/mods/installed` shows Installed active, as today
   *(Covers FR189; `VSS-2oz`)*

2. **Given** a mod detail page
   **When** I click the Installed tab (or focus it and press Enter or Space)
   **Then** the Installed list opens at `/game-server/mods/installed`
   *(Covers FR189; `VSS-2oz`)*

3. **Given** a mod detail page
   **When** I click the Browse tab, or focus it and press Enter or Space, although it is the active tab
   **Then** the browser opens with Epic 16 ADR-1's precedence: the detail page's `state.browseSearch` (with `state.fromModDetail: true`, so the opened card is scrolled back into view); otherwise the session's `browse-last-search`; otherwise the default `/game-server/mods/browse`. Exactly one history entry is added
   *(Covers FR189; Epic 16 ADR-1 decision 3)*

4. **Given** the browse list (`/game-server/mods/browse...`)
   **When** I click the already-active Browse tab
   **Then** nothing happens and no history entry is added (unchanged from Story 16.1)
   *(Covers FR189)*

5. **Given** a browse URL whose `page` is beyond the last page of its results (`?q=food&page=9999`)
   **When** the first response arrives
   **Then** the URL is replaced (history `replace`, no new entry) by the same browse state with `page` set to the last page (`page` omitted when that is page 1), the pagination (shown when N > 1) reads "Page N of N" with N marked current, and the last page's mods are shown. The replacement makes no second browse request, and nothing loops
   *(Covers FR190; `VSS-nhb`)*

6. **Given** a browse URL with a `page` beyond the results of a search that has no results (`?q=<nothing matches>&page=3`)
   **When** the first response arrives
   **Then** the URL is replaced by page 1 (`?q=<...>`, no `page`) and the normal empty state shows. A URL already on page 1 with no results stays as it is
   *(Covers FR190; `VSS-nhb`)*

7. **Given** a browse URL with a page within the results
   **When** it loads
   **Then** that page is requested directly, once, and the URL is not touched; returning from a detail page to it still scrolls to the opened card (Story 16.1 behavior unchanged)
   *(Covers FR190)*

8. **Given** every existing test
   **When** the suites run
   **Then** they pass, apart from the changes listed in Dev Notes "Existing tests that change"; no test run writes into the dev data directory

## Tasks / Subtasks

<!-- Each functional task includes its tests in the same commit. Commit per task: type(story-17.7/task-N): ... ; feat/fix only for user-visible changes, subject written for users. Red first. -->

- [x] Task 1: Browse is the active Mods tab on a mod's page, and Installed opens the list + tests (AC: 1, 2, 3, 4, 8)
  - [x] 1.1: `web/src/features/mods/ModsPage.tsx` `getActiveTab` (`:29-34`): return `'browse'` when `pathname === BROWSE_PATH || pathname.startsWith(`${BROWSE_PATH}/`)`, otherwise `'installed'`. Update its doc comment (`:23-28`): add `/game-server/mods/browse/:slug → "browse"`. `BROWSE_PATH` is already imported (`:17`)
  - [x] 1.2: Same file: `const isDetailPage = useMatch(`${BROWSE_PATH}/:slug`) !== null;` (add `useMatch` to the `react-router` import, `:13`). It replaces the `startsWith` test inside `handleTabChange` (`:56`): with a plain `startsWith`, `/game-server/mods/browse/` (trailing slash, the list) would count as a detail page
  - [x] 1.3: Same file: move the Browse branch of `handleTabChange` (`:53-63`, the Story 16.1 precedence) unchanged into `const openBrowse = () => { ... }`; `handleTabChange` keeps its `value === activeTab` guard (`:52`) and calls `openBrowse()` for `'browse'`. Give the Browse trigger (`:88-91`) `onClick={isDetailPage ? openBrowse : undefined}`. Comment why (Dev Notes "Why an onClick"). Add "Story 17.7" to the header comment (`:9-10`)
  - [x] 1.4: Tests in `web/src/features/mods/ModsPage.test.tsx` (Dev Notes "Web tests", Task 1 rows). No existing test changes in this task

- [x] Task 2: A browse link past the last page opens the last page + tests (AC: 5, 6, 7, 8)
  <!-- The ModsPage.test.tsx fixture change in "Existing tests that change" goes in this task's commit: it fails only once the clamp exists. -->
  - [x] 2.1: `web/src/hooks/use-browse-mods.ts` `UseBrowseModsOptions` (`:25-28`): add `onPageOutOfRange?: (lastPage: number) => void` with a doc comment: called once the response shows `params.page` is beyond the last page, with the last page (1 when there are no results); the caller replaces the page in its URL without a history entry (Story 17.7)
  - [x] 2.2: Same file: build the request parameters once (`const requestParams = { ...apiParams, page: currentPage, sort: apiSort, pageSize: apiPageSize, search: params.search, version: apiVersion, side: apiSide, modType: apiModType, tags: apiTags };`, keeping the `VSS-y7u` comment) and use it for both `queryKey: queryKeys.mods.browse(requestParams)` and `fetchBrowseMods(requestParams)` (today the object is written out twice, `:101-112` and `:114-125`)
  - [x] 2.3: Same file: the `queryFn` becomes `async`: after `fetchBrowseMods(requestParams)`, read `const servedPage = response.data?.pagination?.page;` (optional chaining as at `:130`); if it is defined and lower than `currentPage`, store the response under the served page's key as well: `queryClient.setQueryData(queryKeys.mods.browse({ ...requestParams, page: servedPage }), response)` (`useQueryClient()` from `@tanstack/react-query`). Then return the response. Dev Notes "The clamp" says why
  - [x] 2.4: Same file, after `pagination` (`:130`): `const lastPage = pagination ? Math.max(1, pagination.totalPages) : undefined;` and an effect `useEffect(() => { if (lastPage !== undefined && currentPage > lastPage) onPageOutOfRange?.(lastPage); }, [lastPage, currentPage, onPageOutOfRange]);`. `setPage` (`:134-142`), `goToNextPage` and `goToPrevPage` are unchanged. Add a "Story 17.7" line to the module and hook doc comments
  - [x] 2.5: `web/src/features/mods/BrowseTab.tsx`: next to `handlePageChange` (`:139-142`), `const handlePageOutOfRange = useCallback((lastPage: number) => updateBrowseState({ page: lastPage }, { replace: true }), [updateBrowseState]);` and pass it as `onPageOutOfRange` to `useBrowseMods` (`:162`). Add "Story 17.7" to the header comment (`:16-22`)
  - [x] 2.6: Tests (Dev Notes "Web tests", Task 2 rows; "API test") and the fixture change in "Existing tests that change"

- [x] Task 3: E2E against the Docker dev stack (AC: 1, 2, 3, 5, 6)
  - [x] 3.1: New `web/e2e/mods-navigation.spec.ts` (Dev Notes "E2E"). Rebuild the stack from this branch first (`just docker restart`); run with `cd web && bunx playwright test e2e/mods-navigation.spec.ts e2e/mod-browse-state.spec.ts` and the admin key from `.env` (`just test-e2e-web` stops the stack afterwards)
  - [x] 3.2: `web/e2e/mod-browse-state.spec.ts` "a detour through Installed keeps the state but not the old position" (`:164-175`): leave the detail page through the Installed tab (`page.getByTestId('installed-tab').click()`), not the Mods breadcrumb; delete the `VSS-2oz` comment (`:168`). Its other steps and assertions stay. The `['the Browse tab', ...]` return (`:137`) now exercises the new `onClick` path; it must still pass unchanged
  - [x] 3.3: Read-only: no install, remove or setting change; the game server is not started or stopped; no screenshots

- [ ] Task 4: Quality gate and review hand-off (AC: all)
  - [ ] 4.1: `just check` (lint, typecheck, all tests) passes; the diff adds no lint or type suppression, no `cast` and no new type assertion (`as`); `git status --short` shows nothing under `dev/`
  - [ ] 4.2: Story status `review`, `just sprint set 17-7-mods-navigation review`, PR (base: the Story 17.6 branch while its PR is open, otherwise `main`), PR link on `VSS-2oz` and `VSS-nhb`. Commit `chore(story-17.7/task-4): validate and move story 17.7 to review`

## Dev Notes

### The bugs (verified at 21457bf)

- **Tabs on a detail page (`VSS-2oz`).** Routes: `mods` → `installed`, `browse`, `browse/:slug` (`web/src/App.tsx:122-127`); `browse/:slug` (`ModDetailPage`) is the only route nested below a tab, and the legacy `/mods/browse/:slug` redirect (`App.tsx:62-66`, `:132`) lands on it too. `getActiveTab` (`ModsPage.tsx:29-34`) returns `browse` only when the last path segment is `browse`, so a detail page (last segment = slug) and `/game-server/mods/browse/` (last segment `''`) both get `installed`. Radix Tabs (`@radix-ui/react-tabs` 1.2.1) calls `onValueChange` from the trigger's `onMouseDown`, `onKeyDown` (Enter/Space) and `onFocus` (`node_modules/@radix-ui/react-tabs/dist/index.mjs:127-147`), and the controlled state only reports a value that differs from the current one (`node_modules/@radix-ui/react-use-controllable-state/dist/index.mjs:40`). So on a detail page the Installed click is swallowed. The Mods breadcrumb (`ModDetailPage.tsx:578-584`, to `/game-server/mods`, which redirects to Installed) is the only way out today; Story 16.1's E2E uses it (`e2e/mod-browse-state.spec.ts:168-170`).
- **Out-of-range page (`VSS-nhb`).** `parsePage` (`web/src/lib/browse-search.ts:52-56`; the bead's `:65-70` is stale) accepts any positive integer, and `useBrowseMods` sends it as is (`hooks/use-browse-mods.ts:83`, `:113-125`). **The bead and the epic's "Current State" say the browser shows an empty page; it does not.** The API already clamps: `browse_mods` computes `total_pages = max(1, ceil(total_items / page_size))` and serves `actual_page = min(page, total_pages)` (`api/src/vintagestory_api/routers/mods.py:364-386`), returning that page's mods and `pagination.page = actual_page` (pinned only loosely by `tests/test_mods_router.py:2125-2143`, which checks `page == 1` with one page). What the admin sees at `?page=9999`: the last page's mods under "Page 9999 of N" (`components/Pagination.tsx:139`, from the URL's page); no page button is marked current; Next is disabled; Previous is enabled but does nothing, because `setPage(9998)` is rejected as beyond `totalPages` (`use-browse-mods.ts:138`); and `browse-last-search` remembers `page=9999` (`BrowseTab.tsx:135-137`), so the Browse tab returns to it. The fix is the same as the bead asks (replace the URL with the last page); the description of the symptom is what was wrong.

### Why an `onClick` on the Browse trigger (Task 1)

With Browse active on a detail page, Radix never calls `onValueChange('browse')` there, so Story 16.1's precedence in `handleTabChange` would become unreachable from the place it was written for. The trigger is a native `<button type="button">`, so `onClick` fires for a mouse click and for Enter and Space; Radix's `onMouseDown`/`onKeyDown` call `onValueChange('browse')` first, which the controlled state drops (same value), so exactly one navigation happens. The handler is attached only on a detail page; on the browse list the active Browse tab stays inert (AC 4; existing test "does not add a history entry when the active Browse tab is clicked", `ModsPage.test.tsx:368-397`). Rejected alternatives: making the tabs uncontrolled or giving the detail page a third tab value (Browse would not be highlighted, which is the bug); navigating from `onMouseDown` (fires before `click`, misses Enter/Space).

`isDetailPage` uses `useMatch(`${BROWSE_PATH}/:slug`)` (declarative mode supports it; `react-router` 8.5.1): `/browse/` does not match (empty slug), `/browse/x/` does. The prototype confirmed the trailing-slash case and Enter/Space.

### The clamp (Task 2)

- **Where it is detected: the hook; where the URL is written: `BrowseTab`.** The hook has the response and the query key; `BrowseTab` owns the URL (Epic 16 ADR-1) and already writes every change through `updateBrowseState` (`BrowseTab.tsx:115-122`), which keeps `q`, `sort` and every filter and writes them in the canonical order of `buildBrowseSearch` (`browse-search.ts:89-104`). Unknown parameters are dropped, as by every browse URL write since Story 16.1; that is deliberate (the URL is rebuilt from parsed state) and not changed here. `{ replace: true }` gives AC 5's "no new entry" (the debounced search write is the precedent, `:131`).
- **Target: `max(1, totalPages)`.** The API never reports `totalPages` 0 (`max(1, ...)`), but the web type allows it (`BrowsePaginationMeta`, `api/types.ts:407-414`), and the existing "empty results" test mocks `totalPages: 0` (`BrowseTab.test.tsx:674`), so the guard is cheap. A page at or below the last page is never touched (AC 7), and `currentPage > lastPage` can only move the page down, so the effect cannot loop: after the replace, `currentPage === lastPage`. If the result set shrinks again between requests, it moves down again, at most once per response. In development, `StrictMode` (`web/src/main.tsx:12`) runs a mount's effects twice; when the out-of-range data is already cached at mount, both runs replace with the same URL, which adds no entry and no request.
- **No second request (AC 5).** The API answered `?page=9999` with the last page's mods and `pagination.page = N`. Without help, the replace changes the query key to page N and React Query fetches it again (and shows the loading skeleton in between, `ModBrowseGrid` with `isLoading`). Storing the response under page N's key in the `queryFn` (Task 2.3) makes the replace render from cache with `staleTime` 5 minutes (`use-browse-mods.ts:22`): one request, no flicker. It is stored only when the API says it served a lower page (`servedPage < currentPage`), which is exactly the API's clamp, so the cached data is what a page-N request returns. If an API ever answered with an empty out-of-range page instead, nothing is stored and the replace simply fetches page N.
- **Why not clamp in `parsePage` or before the first request.** The page count is unknown until a response arrives, and the bead requires that a valid deep link does not wait for an extra request (AC 7).
- **API: no change (decision).** The API already clamps and returns the last page (above), so the web cannot see an empty page for an out-of-range request; a 404 or 422 would only add an error path to a shared link. One API test (below) pins the behavior the web's cache step relies on (`pagination.page` and items are the last page's).
- **Scroll restoration and "return to the opened card" (AC 7).** `useBrowseScrollRestoration` decides once per mount from the saved `{ search, slug }` and the arrival (`hooks/use-browse-scroll-restoration.ts:121-124`) and scrolls once the results render (`:133-140`). For a valid page nothing changes: the effect never fires. A card cannot be opened from an out-of-range URL any more (the replace happens on the first response, before any card renders), so a saved entry always holds an in-range search, unless the results shrank while the detail page was open. In that case the mount still decides against the saved search, and because page N's data is already cached, the grid keeps the same cards through the replace and the scroll to the card (or to the top) is final. The replace does not carry `location.state` (`fromModDetail`); nothing reads it after mount. The prototype test for this case passed (Dev Notes "Web tests", last Task 2 row).
- **`browse-last-search`.** It is written on every `location.search` change (`BrowseTab.tsx:135-137`), so after the replace it holds the clamped search.

### Web tests

| Task | File | Test |
|---|---|---|
| 1 | `src/features/mods/ModsPage.test.tsx` (new describe "Story 17.7: Mods tabs on a mod detail page"; use `createTestRouterWithRedirects`, `:149-173`, which has the `browse/:slug` route, and `LocationProbe`, `:44-54`) | On `/game-server/mods/browse/testmod`: the Browse tab has `data-state="active"` and Installed `inactive`; on `/game-server/mods/browse/` (trailing slash) Browse is active (fails today) |
| 1 | same | On a detail page, clicking Installed shows `installed-tab-content` and `probe-path` `/game-server/mods/installed` (fails today). Same with focus + `user.keyboard('{Enter}')` |
| 1 | same | On a detail page opened with `state: { browseSearch: '?q=food' }`, clicking the active Browse tab navigates to `/game-server/mods/browse?q=food` with `probe-from-detail` `true`, adding exactly one location key (reuse the `KeyProbe` pattern of `:368-397`); with `' '` (Space) from focus the same. The two existing Story 16.1 detail-page tests (`:335-348` opened from browse, `:360-366` opened directly) stay and now run through the `onClick` |
| 2 | `src/hooks/use-browse-mods.test.tsx` (new describe "Story 17.7: page beyond the results"; wrapper `createWrapper`, `:23-37`) | `useBrowseMods({ page: 9999 }, { onPageOutOfRange })` with a response `pagination: { page: 5, totalPages: 5, ... }`: called once with `5`; after `rerender` with `page: 5` there is still only one fetch (served from the stored page-5 data) and no further call. `totalPages: 0` or `1` with `page: 3` → called with `1`. `page: 3` of 5 → never called. While loading or after an error → never called |
| 2 | `src/features/mods/BrowseTab.test.tsx` (new describe "Story 17.7: a page beyond the results"; a fetch mock that answers like the API: `page = min(requested, max(1, ceil(totalItems / 20)))`, reading `page` from the request URL) | `${BROWSE_PATH}?q=food&version=1.21.2&page=9999` with 100 items: `currentSearch()` becomes `?q=food&version=1.21.2&page=5`, `locationLog.at(-1)?.navigationType` is `REPLACE`, `locationLog` searches are exactly `['?q=food&version=1.21.2&page=9999', '?q=food&version=1.21.2&page=5']`, "Page 5 of 5" shows, the browse fetch ran once (advance the fake timers ~1 s first), `sessionStorage[BROWSE_LAST_SEARCH_KEY]` is the clamped search |
| 2 | same | `?q=zzz&page=3` with 0 items: URL becomes `?q=zzz` by `REPLACE`, `mod-browse-grid-empty` shows, one fetch. `?q=zzz` with 0 items: `locationLog` has one entry |
| 2 | same | `?page=3` with 100 items: "Page 3 of 5", one fetch with `page=3`, `locationLog` has one entry (AC 7) |
| 2 | same, in "Story 10.7 / 16.1: returning to the opened card" (`:1345`) | A return (`createMemoryRouter` with `{ pathname: BROWSE_PATH, search: '?page=9', state: { fromModDetail: true } }`, saved entry `{ search: '?page=9', slug: 'primitivesurvival' }`, response page 5 of 5 holding that card): URL becomes `?page=5`, `scrollIntoView` was called once on `mod-card-primitivesurvival`, one fetch. Pattern: the test at `:1392-1419`; add `LocationProbe` next to `<BrowseTab />` in the route element |

The key new tests were run against a throwaway prototype at 21457bf: the detail-page Installed test, the trailing-slash test and the BrowseTab out-of-range and empty tests failed against the unchanged source and passed with the change; the one-history-entry and Space tests and the out-of-range return-to-card test passed with the change. The full web suite with the prototype had exactly the one failure listed in "Existing tests that change".

### API test

`api/tests/test_mods_router.py` `TestBrowseModsEndpoint` (`:1744`), next to `test_browse_mods_page_beyond_total` (`:2125-2143`): with `BROWSE_MODS_API_RESPONSE` (3 mods), `?page=100&page_size=1&sort=downloads` returns exactly the same `data` as `?page=3&page_size=1&sort=downloads`, with `pagination.page == 3`, `has_prev` true, `has_next` false and one mod. Name it for what it pins: the browse API serves the last page for a page beyond the results (the web stores that response as the last page, Story 17.7). It passes today (prototype); it is a contract test, not red-first. Commit it with Task 2.

### E2E (`web/e2e/mods-navigation.spec.ts`)

Style of `e2e/mod-browse-state.spec.ts` (live mod database through the dev stack's API, cards picked from the grid, `addInitScript` for the API key, 1440x900). Header comment with requirements as there. Read-only.

1. **Tabs on a detail page.** Open `/game-server/mods/browse?q=food&sort=downloads`, wait for the grid, open the first card by its name (`mod-card-name-<slug>`, as `openCardBelowTheFold` does). On the detail page (`mod-detail-back` visible): `browse-tab` has `aria-selected="true"`, `installed-tab` `aria-selected="false"`. Click `installed-tab` → URL ends with `/game-server/mods/installed`, `installed-tab-content` visible. `page.goBack()` → the detail page again; click `browse-tab` → URL is `/game-server/mods/browse?q=food&sort=downloads`, grid visible.
2. **Detail page opened directly, no session state.** In a new page (`context.newPage()`, so sessionStorage is empty), `goto` the detail URL from test 1 (or the first card's slug), click `browse-tab` → URL is exactly `/game-server/mods/browse` (default state).
3. **Page beyond the results.** `goto('/game-server/mods/installed')`, record `history.length`; collect requests whose URL contains `/api/v1alpha1/mods/browse?`; `goto('/game-server/mods/browse?q=food&sort=downloads&page=9999')`, wait for the first browse response and read `data.pagination.total_pages` (snake_case: the API's raw JSON). Expect the URL to become the same search with `page=<total_pages>` (no `page` when it is 1); `history.length` is one more than before the `goto` (the replace added none); the pagination's `[aria-current="page"]` is `<total_pages>` when there is more than one page; exactly one browse request was made. `page.goBack()` lands on `/game-server/mods/installed`.
4. **Empty results.** `goto('/game-server/mods/browse?q=zzqqxxnomodmatches&page=3')` → URL becomes `?q=zzqqxxnomodmatches`, `mod-browse-grid-empty` visible, one browse request.

### Existing tests that change (deliberately)

Found by running the web suite (128 files) and `tests/test_mods_router.py` against a throwaway prototype of Tasks 1 and 2 (since discarded): web 1 failed, 3187 passed, 4 skipped.

- `web/src/features/mods/ModsPage.test.tsx:335-348` "on a detail page opened from browse, opens the state the mod was opened from": its `openedSearch` has `page=2`, but the file's browse mock (`mockBrowseModsResponse`, `:80-106`) says `totalPages: 1` (`:104`), so the new clamp replaces the URL and `probe-search` no longer equals `openedSearch`. The test's intent is the Browse tab, not the clamp: make the mock describe enough pages (`totalItems: 41, totalPages: 3`, `:103-104`). Verified: with that change the file passes. (Task 2)
- `web/e2e/mod-browse-state.spec.ts:164-175` detour (Task 3.2).
- Nothing else failed. The prototype also passed `BrowseTab.test.tsx` and `use-browse-mods.test.tsx` unchanged, although many of their mocks answer `page: 1` for any requested page (they only store an extra cache entry, which no existing test reads). Anything else that fails is a regression (AC 8): fix the code, not the test.
- Known load flakes from Story 17.4 (`InstallConfirmDialog`, `QuickInstallButton`, `SettingField`, `GameConfigPanel`): if one fails in `just check`, re-run before suspecting this story.

### Not changed (do not "fix" these here)

- The API (`routers/mods.py` browse), `parsePage`, `buildBrowseSearch`, `setPage`/`goToNextPage`/`goToPrevPage`, `Pagination`, `useBrowseScrollRestoration`, `ModDetailPage` (Back to Browse and the breadcrumbs keep their targets: a directly opened detail page's Back to Browse goes to the default browser, while the Browse tab uses `browse-last-search`, exactly as ADR-1 decision 3 says).
- The Mods breadcrumb (`/game-server/mods` → Installed) and the legacy `/mods/*` redirects.
- Arrow-key behavior of the tab list (Radix automatic activation: focusing Installed with an arrow key opens it, as on the other Mods pages).
- Story 17.8 (layouts) and everything outside Mods.

### ADR against the code

- **Epic 16 ADR-1 decision 3** places the Browse tab precedence in `ModsPage.handleTabChange`. Once Browse is the active tab on a detail page (FR189), Radix never calls `handleTabChange('browse')` there, so the precedence moves to the Browse trigger's `onClick` (shared with `handleTabChange` through `openBrowse`). The behavior ADR-1 defines is unchanged; only its location in the code moves.
- **Bead `VSS-nhb` and the epic's "Current State"** say an out-of-range page shows an empty page. The API clamps (`routers/mods.py:364-386`), so the browser shows the last page's mods under a wrong page number with an inert Previous button. The AC (replace with the last page) stands; FR190's wording is correct.

### Security Requirements

- Web only; no new endpoint, request or stored data. Navigation targets are built from parsed browse state (`buildBrowseSearch`) or the existing `readBrowseSearchState` / `getLastBrowseSearch` validation (`browse-search.ts:106-141`), which only accept `''` or a string starting with `?`; no path from user input is navigated to.

### Development Commands

- `just test-web src/features/mods/ModsPage.test.tsx src/features/mods/BrowseTab.test.tsx src/hooks/use-browse-mods.test.tsx`, `just test-api tests/test_mods_router.py`, `just typecheck-web` (`bun run lint` is `tsc --noEmit` as well), `just check`.
- Do not run `just format-api` (reformats unrelated files; Story 17.2 process note).

### Testing Requirements

**CRITICAL:** Tests are written with each task and committed with it, red first (the API test in Task 2 is a contract test and passes today). `just test-web <files>` after each task; `just check` before review. Each commit is green: Task 1 does not depend on Task 2.

- `BrowseTab.test.tsx` uses fake timers (`vi.useFakeTimers({ shouldAdvanceTime: true })`, `:225`): advance them before asserting "one fetch", so a second request would have had time to start.
- Count browse fetches by URL (`/mods/browse`): `BrowseTab` also mounts hooks that the file mocks (`react-router`'s `useNavigate`, `useMods`, `useGameVersions`, `useServerStatus`, `useModTags`, `:39-117`; `setSearchParams` still writes the real `MemoryRouter` location), so today every fetch there is a browse fetch, but filter anyway.
- No type assertion on hand-built query results (Story 17.4 Task 2 note); stub `fetch` instead.

### Previous Story Intelligence

- **17.4:** E2E specs run in parallel (`fullyParallel: true`); a spec must not depend on or change another spec's state. This story's E2E is read-only, so it is safe at any worker count. Its review (L1): a `feat`/`fix` subject must describe what an admin sees.
- **17.3:** a hook's own `onError` replaces the query client's default error handling (TanStack Query v5). Not touched here (no new mutation; the browse query's error path is unchanged).
- **17.2:** E2E that changes real state needs a snapshot guard; not needed here (read-only).
- **17.1:** browse data is normalized at the API boundary; unchanged.
- **16.1:** introduced the URL state, `browse-last-search`, the opened-card restoration and the E2E this story edits; its review finding L3 is `VSS-nhb`, and its E2E detour found `VSS-2oz`. Its traps still apply: build the whole next search in one `setSearchParams` call (`updateBrowseState` does), and `filters` keeps its identity per query string (`BrowseTab.tsx:66-69`).

### Git Intelligence

- Recent commits are Story 17.4's (`47ae737`, `23ba067`, `21457bf`). Release notes come from commit subjects (`cliff.toml`). Planned: Task 1 `fix(story-17.7/task-1): on a mod's page the Mods tabs show Browse, and Installed opens the installed list`; Task 2 `fix(story-17.7/task-2): a browse link past the last page opens the last page`; Task 3 `test(story-17.7/task-3): ...`; Task 4 `chore(story-17.7/task-4): validate and move story 17.7 to review`.

### Latest Technical Information

- No new libraries. `react-router` 8.5.1 declarative mode: `useMatch(pattern)` returns `null` when the pattern does not match. `@radix-ui/react-tabs` 1.2.1 (behavior cited above). TanStack Query v5: `queryClient.setQueryData(key, data)` inside a `queryFn` is allowed; a later `useQuery` with that key and a `staleTime` of 5 minutes renders it without fetching.

### Project Structure Notes

- New: `web/e2e/mods-navigation.spec.ts`.
- Modified: `web/src/features/mods/ModsPage.tsx`, `web/src/hooks/use-browse-mods.ts`, `web/src/features/mods/BrowseTab.tsx`; tests `web/src/features/mods/ModsPage.test.tsx`, `web/src/features/mods/BrowseTab.test.tsx`, `web/src/hooks/use-browse-mods.test.tsx`, `api/tests/test_mods_router.py`, `web/e2e/mod-browse-state.spec.ts`. No API source, no fixture.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 17.7: Mods Navigation]
- [Source: _bmad-output/planning-artifacts/prd.md] FR189, FR190
- [Source: _bmad-output/planning-artifacts/architecture/epic-16-ui-polish.md#ADR-1: Browse State in the URL, Position by Opened Card] (decisions 2-4)
- [Source: _bmad-output/planning-artifacts/architecture/epic-17-mod-data-fixes.md] (17.7 needs no decision)
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-15.md] (17.7 keeps ADR-1's Browse tab precedence; web only)
- [Source: _bmad-output/implementation-artifacts/16-1-mod-browser-state-survives-mod-details.md]
- [Source: _bmad-output/implementation-artifacts/17-4-installed-status-is-right-everywhere.md] (structure, E2E and review learnings)
- Beads: `VSS-2oz`, `VSS-nhb`, parent `VSS-4v5`
- `project-context.md` - no suppressions; commit format and release-note rules

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5)

### Debug Log References

- Started from `story/17-4-installed-status-is-right-everywhere` at 21457bf (Story 17.4 done), not from a Story 17.6 branch: every line reference in the story was re-checked there and matches.

### Completion Notes List

- Story created 2026-11-15: context analysis of the Mods routes, `ModsPage` (`getActiveTab`, `handleTabChange`), Radix Tabs' trigger and controlled-state code, `browse-search.ts`, `useBrowseMods`, `BrowseTab`, `Pagination`, `useBrowseScrollRestoration`, `ModDetailPage`'s links, the browse API's page handling and its tests, the existing ModsPage/BrowseTab/hook tests and `e2e/mod-browse-state.spec.ts`, and the reviews of 17.1-17.4. Tasks 1 and 2 and their key tests were prototyped and discarded (see "Existing tests that change").

- Task 1: `getActiveTab` returns `browse` for `BROWSE_PATH` and anything below it; `isDetailPage = useMatch(`${BROWSE_PATH}/:slug`) !== null`; the Story 16.1 precedence moved unchanged into `openBrowse`, called by `handleTabChange` (its `value === activeTab` guard kept) and by the Browse trigger's `onClick` on a detail page only (comment on why). Tests (new describe "Story 17.7: Mods tabs on a mod detail page"): Browse active (`data-state`, `aria-selected`) on a detail page and on `/browse/`; Installed opens `/game-server/mods/installed` by click and by focus + Enter; the active Browse tab on a detail page opened with `browseSearch: '?q=food'` (and `?q=farming` saved for the session) opens `?q=food` with `fromModDetail`, adding exactly one location key, by click, Space and Enter. Red first: the four tab/Installed tests failed against the old source. With the new `getActiveTab` but no `onClick`, the three new Browse tests and both Story 16.1 detail-page tests failed, so they run through the `onClick`. Focusing Installed already opens it (Radix automatic activation, unchanged); the Enter that follows is then a no-op. `ModsPage.test.tsx` 24 passed; `just typecheck-web` clean.
- Task 2: `UseBrowseModsOptions.onPageOutOfRange` (doc comment as in 2.1); the request parameters are built once (`requestParams`) for the query key and the request; the `queryFn` stores the response under the served page's key when the API served a lower page than asked; `lastPage = pagination ? Math.max(1, pagination.totalPages) : undefined` and an effect reports `lastPage` when `currentPage > lastPage`. `BrowseTab.handlePageOutOfRange` replaces the page with `updateBrowseState({ page }, { replace: true })`. Tests: hook (new describe "Story 17.7: page beyond the results"): `page: 9999` with page 5 of 5 reports 5 once, and after `rerender` with page 5 the data is there without fetching (one request, no second report); `totalPages` 0 and 1 with page 3 report 1; page 3 of 5, loading and error never report. `BrowseTab` (new describe "Story 17.7: a page beyond the results", with a fetch mock that clamps like the API): `?q=food&version=1.21.2&page=9999` with 100 items becomes `...&page=5` by `REPLACE` (exactly two locations logged), "Page 5 of 5", one browse request after advancing the timers 1 s, `browse-last-search` clamped; `?q=zzz&page=3` with no results becomes `?q=zzz` by `REPLACE`, empty state, one request; `?q=zzz` stays a single entry; `?page=3` of 5 shows "Page 3 of 5" with one `page=3` request and no URL change. In "returning to the opened card": a return to `?page=9` (saved `{ search: '?page=9', slug: 'primitivesurvival' }`) becomes `?page=5`, scrolls `mod-card-primitivesurvival` into view once, one request. API: `test_browse_mods_serves_the_last_page_for_a_page_beyond_the_results` (`?page=100&page_size=1&sort=downloads` returns the same `data` as `?page=3`, page 3, `has_prev`, not `has_next`, one mod); passes against the unchanged API (contract test). Red first: the hook's three reporting tests and BrowseTab's three URL tests failed against the old source; the within-range, page-1-empty and no-report tests passed there, as expected. `ModsPage.test.tsx` browse mock now says `totalItems: 41, totalPages: 3` (the one existing test that the clamp changed, as the story listed). The three web files: 166 passed, 2 skipped; `tests/test_mods_router.py` 129 passed; ruff clean; pyright 0 errors, the 3 pre-existing warnings; `just typecheck-web` clean.
- Task 3: `web/e2e/mods-navigation.spec.ts` with the four tests of Dev Notes "E2E"; `mod-browse-state.spec.ts`'s detour now leaves the detail page through the Installed tab (the `VSS-2oz` comment is gone). Deviation in test 1: the story's order (Installed, then browser back to the detail page, then Browse) fails, because a mouse click on an inactive Mods tab adds **two** history entries, so back lands on the Installed list again. Cause (pre-existing, not introduced here, on every Mods page): Radix calls `onValueChange` from the trigger's `onMouseDown` and again from its `onFocus`; react-router applies the navigation in a transition, so the focus call still sees the old `activeTab` and navigates a second time. Measured on the stack: Browse list → Installed tab click, and Installed list → Browse tab click, each grow `history.length` by 2. The Browse tab on a detail page is not affected (it is already active, so neither Radix call fires; only the `onClick` navigates: +1). Smallest correct choice: the test checks Browse first (with `history.length` +1, AC 3), goes back to the detail page, then clicks Installed (AC 2); the double entry is left as it is and reported as a follow-up (not in this story's scope or ACs). Run: before anything, `GET /mods` saved (five mods) and the game server state read (`installed`, not running); `just docker restart` rebuilt the image from this branch; the new spec with `mod-browse-state.spec.ts`: 11 passed; then the new spec with every mod spec (`mod-browse-state`, `installed-mod-any-modid`, `installed-mods-phone`, `installed-status`, `mod-browse-name-sort`, `mod-detail-bad-data`, `mod-install-release`): 32 passed, 1 skipped (the real Carry On install, Carry On being installed). Afterwards `GET /mods` is byte-identical to before; the game server stayed `installed` and was not started or stopped; stack left running. The tracked `web/playwright-report/index.html` and `web/test-results/.last-run.json` that Playwright rewrites were restored with `git checkout`.
- Manual browser check (Docker stack, this branch, no screenshots kept): `?q=food&sort=downloads`, opened the first card by its name: on the detail page Browse is `aria-selected="true"`/active and Installed `false`/inactive. Clicking the Browse tab opened `?q=food&sort=downloads` with the opened card in view, one history entry. Back to the detail page, Browse focused + Enter, and Browse focused + Space, each opened the same browse URL. Focusing Installed on the detail page opened `/game-server/mods/installed` (automatic activation); a mouse click on Installed did too. `?q=food&sort=downloads&page=9999`: one browse request (`page=9999`), URL replaced by `&page=29`, "Page 29 of 29 (575 mods total)", page 29 marked current, 15 cards, `browse-last-search` holds `page=29`, and Previous now goes to page 28. `?q=zzqqxxnomodmatches&page=3`: URL replaced by `?q=zzqqxxnomodmatches`, empty state, no pagination, one browse request.

### File List

- `web/src/features/mods/ModsPage.tsx`
- `web/src/features/mods/ModsPage.test.tsx`
- `web/src/hooks/use-browse-mods.ts`
- `web/src/hooks/use-browse-mods.test.tsx`
- `web/src/features/mods/BrowseTab.tsx`
- `web/src/features/mods/BrowseTab.test.tsx`
- `api/tests/test_mods_router.py`
- `web/e2e/mods-navigation.spec.ts` (new)
- `web/e2e/mod-browse-state.spec.ts`

## Change Log

- 2026-11-15: Story 17.7 created (ready-for-dev).
- 2026-11-15: Validated against the create-story checklist: every cited path and line re-read at 21457bf. Found that the API already clamps the page (the bead's "empty page" is wrong), so the story keeps the API unchanged, adds a contract test, and stores the served page in the cache so the replace costs no request; replaced the `startsWith` detail-page test (it would treat `/browse/` as a detail page) with `useMatch`; added the trailing-slash case, keyboard activation, the one-history-entry check and the out-of-range return-to-card case; listed the one test the prototype broke (`ModsPage.test.tsx` browse mock with `totalPages: 1`).
