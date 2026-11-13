# Epic 16: UI Polish - Architecture Decisions

Decisions from Story 16.0 (Epic 16 Technical Preparation). Evidence lives in `_bmad-output/implementation-artifacts/16-0-spike/`.

## ADR-1: Browse State in the URL, Position by Opened Card

**Status:** Accepted (Story 16.0). Implements Epic 10 ADR-4, which was decided but never built.

**Context:**

- `BrowseTab` keeps search, filters and sort in `useState`, so they reset whenever it remounts; `browse` and `browse/:slug` are sibling routes, so opening a mod's detail page always unmounts it.
- Story 10.7's restoration (`use-browse-scroll-restoration.ts`) saves `{ scrollY, page }` in sessionStorage and restores it on the next mount. The Story 16.0 probe (`16-0-spike/browse_probe.out.json`) shows it works for the unfiltered browser on all four return paths, also on Slow 4G (the grid renders from the React Query cache), but:
  - with a search set, the search resets while page and scroll are restored against the unfiltered results, so the opened card is not on screen;
  - saved state survives detours: after leaving for Settings and Installed, returning via the Browse tab still restores the old page and scroll.
- The app uses declarative `<BrowserRouter>` (`App.tsx`), `react-router` 8.5.1. `useSearchParams` and `navigate(to, { replace, state })` work in declarative mode; `<ScrollRestoration>`/`useScrollRestoration` need a data router (they call `useDataRouterContext`) and are unavailable.

**Decision:**

1. **The URL is the source of truth** for search, filters, sort and page on `/game-server/mods/browse`, read and written with `useSearchParams`:

   | Parameter | Value | Default (omitted from URL) |
   |---|---|---|
   | `q` | search text (trimmed) | empty |
   | `sort` | `recent`, `downloads`, `trending`, `name` | `recent` |
   | `side` | `ModFilters.side` | none |
   | `tags` | comma-separated `ModFilters.tags` | none |
   | `type` | `ModFilters.modType` | none |
   | `version` | `ModFilters.gameVersion` | none |
   | `page` | page number | `1` |

   Defaults are omitted, so `/game-server/mods/browse` stays the default state and existing links keep working. Unknown or invalid values fall back to the default. There is no sort direction.

2. **History entries:** typing in the search box keeps local input state for responsiveness and writes the debounced (300 ms) value with `{ replace: true }`, so a search adds no entry per keystroke. Sort, filter and page changes push an entry, so browser back and forward step through them (ADR-4's consequence). Any change to `q`, `sort` or a filter also removes `page`.

3. **Links into browse carry the last browse URL:**
   - Opening a mod (card click, or Enter on a slug) navigates to the detail page with `state: { browseSearch: location.search }`.
   - Back to Browse (`ModDetailPage.handleBack`) and the breadcrumb navigate to `/game-server/mods/browse` plus `state.browseSearch` (empty when the detail page was opened directly).
   - The Browse tab (`ModsPage.handleTabChange`) does the same when it is clicked from a detail page; from another tab it opens browse with the last browse search remembered in sessionStorage (`browse-last-search`), written by `BrowseTab` whenever its search string changes.
   - Browser back needs nothing extra: the previous entry is the browse URL.

4. **Position is restored to the opened card, only on a return from that card's detail page.** On opening a mod, `BrowseTab` saves `{ search: location.search, slug }` in sessionStorage. On mount it restores only if the current `location.search` matches the saved search and the arrival is a return from the detail page (`location.state.fromModDetail`, set by the three links above, or `useNavigationType() === 'POP'`); otherwise it clears the saved entry. It restores by calling `scrollIntoView({ block: 'center' })` on `mod-card-<slug>` in an effect that runs once the results containing that slug have rendered, then clears the entry. If the slug is not in the results, the page is left at the top. This replaces the pixel offset and the 100 ms `setTimeout`, and the stale restore after a detour.

5. **The custom hook stays.** Migrating to a data router for `<ScrollRestoration>` would change the whole app's routing for one page; not proposed.

**Implementation traps (Story 16.1):**

- `useBrowseMods` keeps the page in internal `useState` (`use-browse-mods.ts:70`, initialised once from `params.page`). It must become controlled: the page comes from the URL and `setPage` writes it.
- `BrowseTab` detects filter changes by reference (`prevFiltersRef.current !== filters`, `BrowseTab.tsx:146`). A `filters` object parsed from the URL on every render would look changed every render, reset the page and clear restoration. Derive it with `useMemo` keyed on the parameter strings, or compare by value.
- `setSearchParams` with a function callback does not queue like React `setState`; build the whole next parameter set in one call.
- The Name sort currently fails (`VSS-stm.1`); `page` has no effect for it until that is fixed.

**Consequences:**

- Refresh, shared links and browser back/forward all preserve the browse state.
- Story 10.7's `browse-scroll-position` key and `{ scrollY, page }` shape are retired; its unit tests are rewritten for the slug-based entry.
- Returning lands on the card that was opened even if layout or card heights changed.
