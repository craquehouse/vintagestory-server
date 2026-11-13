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
   - `BrowseTab` mirrors its full `location.search` (including `page`) to sessionStorage (`browse-last-search`) whenever its URL state changes, so changes to filters, sort or page are remembered as well as the search.
   - The Browse tab (`ModsPage.handleTabChange`) opens `/game-server/mods/browse` with, in order of precedence: `state.browseSearch` when it is clicked on a detail page that was opened from browse; otherwise `browse-last-search`; otherwise nothing (default state). A detail page opened directly (a shared link) has an empty `state.browseSearch` and falls through to `browse-last-search`.
   - Browser back needs nothing extra: the previous entry is the browse URL.

4. **Position is restored to the opened card, only on a return from that card's detail page.** On opening a mod, `BrowseTab` saves `{ search: location.search, slug }` in sessionStorage. On mount it restores only if the current `location.search` matches the saved search and the arrival is a return from the detail page (`location.state.fromModDetail`, set by the three links above, or `useNavigationType() === 'POP'` for browser back); otherwise it clears the saved entry. Every `BrowseTab` mount consumes or clears the entry, and it is written only immediately before leaving for a detail page, so a refresh or initial load of the browse page (also `POP`) never finds one and never scrolls: refresh restores the browse state from the URL, not a position. It restores by calling `scrollIntoView({ block: 'center' })` on `mod-card-<slug>` in an effect that runs once the results containing that slug have rendered, then clears the entry. If the slug is not in the results, the page is left at the top. This replaces the pixel offset and the 100 ms `setTimeout`, and the stale restore after a detour.

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

## ADR-2: Most Recent Supported Game Version

**Status:** Accepted (Story 16.0). Epic 10 ADR-2 (Conservative Compatibility Badge) stays in force for browse cards.

**Context** (probe: `16-0-spike/moddb_probe.py`, output `moddb_probe.out.txt`, installed game 1.22.7):

- Listing items (`/api/mods`, 9,560 items, 4.2 MB) carry only category `tags` (`Building`, `Patch`, ...); none parse as game versions.
- Mod details carry game versions per release in `tags`, oldest first within a release, including pre-releases. `playercorpse` 1.12.0 (its newest release): `1.21.0, 1.21.1-rc.1, 1.21.1-rc.2, 1.21.1`.
- Compatibility (`ModService` lookup, `services/mods.py:477-499`) evaluates `releases[0]` regardless of mod ID, and the incompatible message lists `tags[:3]`: for `playercorpse` it names the three oldest tags, not 1.21.1. For `instruments`, `releases[0]` belongs to `vsinstrumentsbase`, a different mod ID (related: `VSS-jhf`, Story 16.2).
- Per mod ID, the probe's most recent supported versions are: `playercorpse` 1.21.1, `instruments` 1.18.6, `vsinstruments` 1.19.3, `vsinstrumentsbase` 1.21.6; `carryon` supports 1.22.7 exactly. No sampled mod was ahead of the installed version, but nothing prevents a release tagged only for a newer game version.
- `/api/mods?gameversion=<tagid>` returns, in one request (2.5 MB, 1.5 s, 5,582 mods for 1.22.7), the mods with *any* release tagged for that version. `ModApiClient.get_mods_by_version` does **not** cache it (`services/mod_api.py:559`).
- The Installed list gets compatibility from `useModsCompatibility` → `lookupMod(slug)`, which evaluates the newest release, not the installed one, and `ModTable` shows only the status badge.

**Decision:**

1. **Definition.** For a mod ID, the most recent supported game version is the highest tag across that mod ID's releases (`modidstr` equal to it), compared with `parse_base_version` and `is_prerelease` from `services/mod_updates.py`: by base version, then a stable tag above pre-releases of the same base. Stable tags are preferred; a pre-release is used only when the mod ID has no stable tag. Tags that do not parse are ignored. No new version parser.
2. **Which mod ID.** The installed mod's ID when the mod is installed; otherwise the mod ID whose release the install flow would install (today `releases[0].modidstr`; Story 16.2 and `VSS-jhf` keep this consistent).
3. **Which release decides the status.** Detail page and lookup: the newest release of that mod ID (not `releases[0]` of the whole entry). Installed list: the installed release (matching `modidstr` and `modversion`), because the question there is whether what is running supports the game; the lookup endpoint gains an optional `version` parameter for this (Story 16.3; today it takes only the slug).
4. **Message,** replacing the `tags[:3]` list in `_build_compatibility_message`, using the mod ID's lowest and highest supported versions:
   - behind (highest < installed): "Last supported game version: 1.21.1."
   - ahead (lowest > installed): "Requires game version 1.23.0 or newer (installed: 1.22.7)."
   - gap (installed between them but not tagged): "Not tagged for 1.22.7; supports 1.21.0 to 1.23.0."
   - `not_verified` keeps its wording and adds "Last tagged for X." when the highest supported version is older than the installed one.
5. **API.** `CompatibilityInfo` gains `latest_supported_game_version: str | None` (snake_case in the API, `latestSupportedGameVersion` in the web types, per the JSON field naming rule). The Installed list shows it beside the badge for `not_verified` and `incompatible` mods; the detail page shows it in the compatibility message.
6. **Browse cards are unchanged.** The most recent supported version would need a request per mod. A "has a release for your version" flag is possible from one uncached `?gameversion=` request, but it answers a different question from the detail page (any release, not the one that would be installed), so it is out of Epic 16 and recorded as a backlog bead.

**Consequences:**

- The incompatible and unverified messages name the version an admin can act on, in the right direction.
- Story 16.3 changes the API (`CompatibilityInfo`, lookup `version` parameter, message builder) and the Installed list UI; it does not touch browse cards.
- Fixture `api/tests/fixtures/moddb/mod_playercorpse.json` covers the behind case; `mod_instruments.json` covers mod ID selection; an ahead case needs a synthetic fixture.

## ADR-3: Game Server Settings Layout on Desktop

**Status:** Accepted (Story 16.0).

**Context** (screenshots `16-0-spike/settings-{1024,1440,1920}.png`, measurements `settings_shots.out.json`):

- `GameConfigPanel` stacks four `SettingGroup` cards with `space-y-4` at every width. Panel width: 768px at a 1024px viewport, 1184px at 1440px, 1664px at 1920px; page height 1,984px at every width.
- Cards and their fields: Server Info (4 text fields: name, description, welcome message, password; 486px tall), Player Settings (1 number, 1 toggle; 278px), World Settings (collapsible; 1 number, 4 toggles; 518px), Network (collapsible; 2 text, 2 toggles; 454px).
- At 1440px and wider, inputs stretch to well over 1,000px for values such as a port number, and toggles leave most of each card empty.
- UX spec: `lg` is 1024px+, maximum content width 1280px centered (`ux-design-specification.md:1254-1256`). Nothing in the app applies the maximum today. The sidebar takes 160px (64px collapsed), so at `lg` the content area is too narrow for two useful columns.

**Decision:**

1. **Maximum width.** The settings panel is limited to 1280px and centered (`max-w-[1280px] mx-auto`), per the UX spec. Applying the maximum to every page is a separate, app-wide change and not part of Epic 16.
2. **Two columns from `xl` (1280px viewport; content about 1,072px after the 160px sidebar and padding).** Below `xl` the layout stays a single column, as today.
3. **Placement at `xl`:**

   ```text
   ┌──────────────────── Server Info (spans both columns) ────────────────────┐
   │ Server Name              │ Description                                   │
   │ Welcome Message          │ Password                                      │
   └──────────────────────────────────────────────────────────────────────────┘
   ┌────────── Player Settings ──────────┐ ┌────────── World Settings ▾ ─────┐
   └─────────────────────────────────────┘ │                                 │
   ┌────────── Network ▾ ────────────────┐ │                                 │
   │                                     │ └─────────────────────────────────┘
   └─────────────────────────────────────┘
   ```

   Server Info spans both columns and lays its four text fields out in two columns. The rest is two independent column stacks, not grid rows: Player Settings then Network on the left (column height about 732px), World Settings on the right (about 518px), using the card heights measured at 1440px. Collapsing World Settings or Network then changes only its own column, and no card stretches to match a neighbor's height.
4. **Field width.** Number inputs (Max Players, Max Chunk Radius, Port) keep a fixed narrow width (`max-w-xs`) at every breakpoint; text inputs fill their column.

**Consequences:**

- Page height at 1440px and wider drops from about 1,984px to roughly the left column plus Server Info.
- Story 16.6 changes only `GameConfigPanel` (and `SettingField` sizing for numbers); `SettingGroup` keeps its collapsible behavior.
- Out of scope, recorded separately: empty settings render the text `null` and Password is unmasked (`VSS-7ed`).
