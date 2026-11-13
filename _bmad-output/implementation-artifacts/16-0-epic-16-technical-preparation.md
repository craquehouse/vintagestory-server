# Story 16.0: Epic 16 Technical Preparation

Status: in-progress

<!-- Spike story (template-api-spike). Complete before Stories 16.1-16.7: their designs rest on the decisions this story records. No application code changes in this story. -->

## Story

As a **developer**,
I want **the open questions behind the polish stories answered against the running app**,
so that **each story starts from confirmed behavior and data**.

## Acceptance Criteria

1. **Given** the mod browser with Story 10.7's scroll restoration
   **When** it is exercised manually, including on a throttled network and through every way back into the browser
   **Then** findings record whether page and scroll restoration work today, and whether the 100 ms timeout is reliable
   **And** the result is recorded on `VSS-901` as a comment

2. **Given** the browse state that has to survive navigation (search, filters, sort, page, position in the results)
   **When** URL query parameters and sessionStorage are compared
   **Then** findings record the chosen mechanism and why, covering Back to Browse, the breadcrumb, the Browse tab, browser back, refresh and a shared link
   **And** the choice is reconciled with Epic 10 ADR-4 (URL state for filters), which was decided but never implemented
   **And** findings record whether restoration returns to the opened card or to a pixel offset

3. **Given** the mod database API
   **When** its release data is checked for incompatible and unverified mods
   **Then** findings record how the most recent supported game version is computed from the release tags of the evaluated mod ID
   **And** findings record whether that version, or a compatible-with-installed-version flag, can be shown on browse cards without a request per mod (evaluating `?gameversion=<tagid>`)
   **And** a trimmed fixture for an incompatible mod is saved under `api/tests/fixtures/moddb/`

4. **Given** the game server settings page
   **When** it is reviewed at the `lg` (1024px) and wider breakpoints
   **Then** findings record the target layout for the settings cards, including the UX spec's 1280px maximum content width and the collapsible World and Network groups

5. **Given** the findings
   **When** they are written to `architecture/epic-16-ui-polish.md`
   **Then** each decision is an ADR with its evidence, the architecture index links the file and each ADR, and any story whose scope changes is updated in `epics.md` or gets a bead under `VSS-stm`

## Tasks / Subtasks

<!-- Research story: no application code changes. Tasks produce documentation, a fixture, a probe script and spike notes under 16-0-spike/. -->

- [x] Task 1: Verify current browse behavior (AC: 1)
  - [x] 1.1: Start the stack (`just docker restart`); install a game version if none is installed
  - [x] 1.2: Default browse state: go to page 2 or later, scroll down, open a mod, return with Back to Browse; repeat returning with the breadcrumb `Browse` link, the Browse tab and browser back. Record page and scroll results for each
  - [x] 1.3: Repeat 1.2 with Chrome DevTools network throttling ("Slow 4G") to test the 100 ms `setTimeout` in `BrowseTab.tsx`
  - [x] 1.4: Repeat 1.2 with a search term set, to record the current failure Story 16.1 fixes (search resets, so the restored page belongs to a different result set)
  - [x] 1.5: Stale restore: open a mod, leave through the sidebar to another page, come back to Browse later. Saved state is consumed on any mount, so record whether an old position is restored unexpectedly
  - [x] 1.6: Select each sort option (`recent`, `downloads`, `trending`, `name`) and record failures. Name sort requests `pageSize: 1000` (`use-browse-mods.ts:85`) while the API allows `page_size` ≤ 100 (`routers/mods.py:235-237`); the expected 422 is tracked as `VSS-stm.1`, so confirm it there
  - [x] 1.7: Add the results to `VSS-901` with `bd comments add VSS-901 "..."`

- [ ] Task 2: Choose the browse state mechanism (AC: 2)
  - [ ] 2.1: Read Epic 10 ADR-4 and confirm `useSearchParams` from `react-router` 8.5.1 works with the nested `mods` → `browse` route in `App.tsx`. The app uses declarative `<BrowserRouter>` (`App.tsx:109`), so the router's built-in `<ScrollRestoration>` (data routers only) is unavailable; record whether ADR-1 keeps the custom hook (expected) or proposes a data-router migration as a bead
  - [ ] 2.2: Decide parameter names and defaults, starting from ADR-4's `q` and `side`, for search, each `ModFilters` field, sort and page; default values are omitted so `/game-server/mods/browse` stays the default state. There is no sort direction, only the four `BrowseSortOption` values
  - [ ] 2.3: Record the two implementation traps Story 16.1 must avoid: `page` is internal `useState` in `useBrowseMods` (`use-browse-mods.ts:70`) and must become controlled by the URL; `BrowseTab.tsx:146` detects filter changes by reference (`prevFiltersRef.current !== filters`), so a `filters` object parsed from the URL must be memoized or compared by value, or every render resets the page
  - [ ] 2.4: Decide how the 300 ms debounced search writes to the URL (`replace`, not a history entry per keystroke) and whether page changes add history entries
  - [ ] 2.5: List every link into browse and decide which preserve the last browse URL: Back to Browse (`ModDetailPage.handleBack`, fixed path), the breadcrumb (`ModDetailPage.tsx:522`, fixed path), the Browse tab (`ModsPage.tsx:44`, `navigate('/game-server/mods/${value}')`), and Enter on a slug (`BrowseTab.tsx:174-181`)
  - [ ] 2.6: Decide what restoration targets: the pixel offset (`scrollY`, today) or the opened card (save its slug and `scrollIntoView` once results render, which removes the 100 ms timing dependence). Position is not shareable, so it stays in sessionStorage keyed to the browse URL
  - [ ] 2.7: Record the decisions as ADR-1 in `architecture/epic-16-ui-polish.md`, noting that it implements Epic 10 ADR-4

- [ ] Task 3: Most recent supported game version (AC: 3)
  - [ ] 3.1: Confirm that `https://mods.vintagestory.at/api/mods` listing items carry only category `tags` (e.g. `["Building","Patch"]`), no game versions
  - [ ] 3.2: `https://mods.vintagestory.at/api/mod/{slug}` releases carry game versions in `tags`, oldest first within a release. Already verified for `playercorpse` release 1.12.0: `["1.21.0","1.21.1-rc.1","1.21.1-rc.2","1.21.1"]`; re-check one other mod
  - [ ] 3.3: Define "most recent supported game version": the highest version across the tags of releases whose `modidstr` matches the mod being evaluated (as update checks do at `services/mods.py:933`; see `mod_instruments.json`, where the newest releases belong to `vsinstrumentsbase`), compared as versions, not strings. Decide whether pre-release tags (`-rc.N`) count when a stable tag exists. Reuse `parse_base_version` and `is_prerelease` from `services/mod_updates.py`; no new version parser. This shares its mod ID matching with Story 16.2
  - [ ] 3.4: Decide the message when the mod is ahead rather than behind: compatibility evaluates only the newest release (`services/mods.py:481-499`), and publish order is not version order (Epic 14 ADR-1, `mod_carryon.json`), so an "incompatible" mod may support only a newer game version than the installed one. Also decide whether the Installed list should evaluate the installed release (`ModInfo.version`) instead of the newest; it currently gets compatibility from `useModsCompatibility` → `lookupMod(slug)` (`web/src/hooks/use-mods.ts`), which evaluates the newest release
  - [ ] 3.5: Evaluate browse cards: `ModApiClient.get_mods_by_version(tagid)` fetches `/api/mods?gameversion=<tagid>` in one cached request (`services/mod_api.py:555-575`, used by the browse router at `routers/mods.py:320-328`). Record whether it can flag "compatible with the installed version" on every card, and confirm that "most recent supported" per card would need a request per game version. Browse cards show no compatibility badge today (`ModCard.tsx` does not render `CompatibilityBadge`; compatibility appears only in `InstallConfirmDialog`)
  - [ ] 3.6: Save a trimmed fixture `api/tests/fixtures/moddb/mod_playercorpse.json` (or another mod whose newest release predates the installed game version), trimmed as the folder's `README.md` describes (drop descriptions, changelogs, screenshots, CDN URLs; keep release order), and add its row to that `README.md`
  - [ ] 3.7: Commit the probe script that fetches and summarizes the ModDB data, with its captured output, to `16-0-spike/`
  - [ ] 3.8: Record the definition, the ahead/behind wording, the Installed list choice, the browse card decision and the API change Story 16.3 needs as ADR-2. State whether it supersedes Epic 10 ADR-2 (conservative `not_verified` on browse cards). If browse cards stay out of reach, update Story 16.3's conditional acceptance criterion in `epics.md` to say so

- [ ] Task 4: Settings layout (AC: 4)
  - [ ] 4.1: Screenshot game server settings at 1024px, 1440px and 1920px; list the cards in `GameConfigPanel.tsx` and the kind of field each holds
  - [ ] 4.2: Choose the layout (e.g. a two-column grid at `lg` with wide cards spanning both columns) and record it as ADR-3 with a sketch. ADR-3 must say how it applies the UX spec's 1280px maximum content width and how the collapsible World and Network groups behave in a grid

- [ ] Task 5: Record findings (AC: 5)
  - [ ] 5.1: Write `_bmad-output/planning-artifacts/architecture/epic-16-ui-polish.md` with ADR-1 to ADR-3 and their evidence
  - [ ] 5.2: Add the file to `architecture/index.md` with an anchor link per ADR, as the Epic 14 and 15 entries do
  - [ ] 5.3: Write `_bmad-output/implementation-artifacts/16-0-spike/README.md` with the manual test results, screenshots, and how to rerun the probe script
  - [ ] 5.4: Update affected stories in `epics.md`, or create beads under `VSS-stm` for anything found that is out of scope
  - [ ] 5.5: Run `just check` to confirm nothing broke (the fixture must not affect tests)

## Dev Notes

### Why this story matters

| Question | Used by | If unanswered |
|---|---|---|
| Does Story 10.7 restoration work, and is its timing reliable? | Story 16.1, `VSS-901` | 16.1 rebuilds or keeps restoration code blindly |
| URL parameters or sessionStorage; offset or card? | Story 16.1 | Back, refresh and shared links behave differently from what admins expect |
| Where does "most recent supported game version" come from, and for which release? | Stories 16.2, 16.3, `VSS-udh` | Wrong version shown, or a request per browse card |
| What should the desktop settings layout be? | Story 16.6, `VSS-dfx` | Layout chosen ad hoc in code review |

### Constraints

- **No application code changes.** Stories 16.1-16.7 change code. This story adds documentation, one test fixture, a probe script, and beads comments.
- Use the scratchpad for throwaway files; keep notes, screenshots and the probe script in `_bmad-output/implementation-artifacts/16-0-spike/`.
- Do not use the repo's `./data` volume for anything other than the normal dev stack.
- The live mod database is public and unauthenticated; keep requests to a handful (the listing is about 9,500 items).

### Current state (verified 2026-11-13)

- **Browse state:** `web/src/features/mods/BrowseTab.tsx:56-58` keeps `searchInput`, `filters` (`ModFilters`: `side`, `tags`, `modType`, `gameVersion`) and `sort` (`BrowseSortOption`: `downloads`, `trending`, `recent`, `name`; default `recent`; no direction) in `useState`. No component in `web/src` uses `useSearchParams`, so Epic 10 ADR-4 was never implemented.
- **Restoration:** `web/src/hooks/use-browse-scroll-restoration.ts` stores `{ scrollY, page }` under sessionStorage key `browse-scroll-position`, consumed once on mount; `BrowseTab` scrolls after `setTimeout(..., 100)` and clears the saved state when search, filters or sort change.
- **Navigation:** routes in `web/src/App.tsx`: `mods` → `browse` (`BrowseTab`) and `browse/:slug` (`ModDetailPage`) are siblings, so `BrowseTab` unmounts on the detail page. Back to Browse (`handleBack`) and the breadcrumb both use the fixed path `/game-server/mods/browse` (Story 11.4 replaced `navigate(-1)`); the Browse tab navigates to a fixed path too.
- **ModDB:** `ModApiClient.BASE_URL` is `https://mods.vintagestory.at/api`. Listing items have keys `assetid, author, comments, downloads, follows, lastreleased, logo, modid, modidstrs, name, side, summary, tags, trendingpoints, type, urlalias`. Mod details are a different shape: they drop `modidstrs`, `summary` and `logo`, and add `releases`, `text`, `screenshots`, `homepageurl` and others. Each release has `changelog, created, downloads, fileid, filename, mainfile, modidstr, modversion, releaseid, tags`; releases are newest first by publish date. API reference: `agentdocs/vintagestory-modapi.md`.
- **Compatibility:** `check_compatibility()` in `services/mod_api.py` compares the installed game version with the newest release's `tags`. `_build_compatibility_message()` in `services/mods.py` lists `compatible_tags[:3]`, followed by `...` when there are more, so for `playercorpse` against 1.22.7 it names 1.21.0, 1.21.1-rc.1 and 1.21.1-rc.2 rather than the newest, 1.21.1. The message is shown on the mod detail page (`ModDetailPage.tsx:569,659`) and in `InstallConfirmDialog`; the Installed list (`ModTable.tsx`) shows only the status badge, so Story 16.3 needs a new element there.
- **Settings:** `web/src/features/game-server/GameConfigPanel.tsx:264` stacks its cards with `space-y-4` at every width; World and Network are collapsible groups. The page wrapper is `SettingsPage.tsx:61` (`p-4 lg:p-6`). The sidebar is 160px, or 64px collapsed (`Layout.tsx:19`), so content is about 816px wide at 1024px. The UX spec sets `lg` at 1024px+ and a maximum content width of 1280px, centered (`ux-design-specification.md:1254-1256`); nothing applies the maximum width today.
- **Libraries (resolved in `web/bun.lock`):** `react-router` 8.5.1, `@tanstack/react-query` 5.105.0, Tailwind 4.3.3, Vitest 5.1.0, Playwright 1.64.1, DOMPurify 3.4.17.

### Output artifacts

- `_bmad-output/planning-artifacts/architecture/epic-16-ui-polish.md` (ADR-1 browse state, ADR-2 supported game version, ADR-3 settings layout) and its `index.md` entry.
- `_bmad-output/implementation-artifacts/16-0-spike/`: `README.md` with manual test results and screenshots, the ModDB probe script and its output.
- `api/tests/fixtures/moddb/mod_<slug>.json` for an incompatible mod, documented in the fixtures `README.md`.
- A comment on `VSS-901` with the restoration results.

### Testing Requirements

- Research story with no application code; no new tests required.
- `just check` must still pass.

### Project Structure Notes

- Story numbering: `project-context.md` (Story Conventions) says preparation stories are Story 1, and even says "Epic 12 onwards uses Story 1", but Epics 13-15 used Story 0 and the Epic 16 proposal approved 16.0. Kept as 16.0; the rule itself is tracked in `VSS-as6`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 16.0]
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-13.md]
- [Source: _bmad-output/planning-artifacts/architecture/epic-10-architecture-decisions.md#ADR-2: Conservative Compatibility Badge]
- [Source: _bmad-output/planning-artifacts/architecture/epic-10-architecture-decisions.md#ADR-4: URL State for Filters]
- [Source: _bmad-output/planning-artifacts/architecture/epic-14-mod-updates.md#ADR-1: Detect Updates by Release Order] release order is not version order
- [Source: _bmad-output/implementation-artifacts/10-7-pagination.md] scroll restoration design
- [Source: _bmad-output/implementation-artifacts/14-0-epic-14-technical-preparation.md] ModDB fixtures and modid matching
- [Source: _bmad-output/implementation-artifacts/15-0-epic-15-technical-preparation.md] spike structure and evidence scripts
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md] breakpoints and content width
- `agentdocs/vintagestory-modapi.md` - ModDB API reference
- `project-context.md` - critical implementation rules and patterns

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5)

### Debug Log References

- Task 1: Playwright probe `16-0-spike/browse_probe.mjs` against the dev stack (`just docker restart`, game 1.22.7, 1440x900 Chromium); output `16-0-spike/browse_probe.out.json`. Required `bunx playwright install chromium` (the lockfile's Playwright 1.64.1 needs headless shell build 1248).

### Findings Summary

### Architecture Decisions Made

### Backlog Items Created

### Completion Notes List

- Task 1: Unfiltered restoration works on all four return paths (Back to Browse, breadcrumb, Browse tab, browser back), also on Slow 4G, because the grid renders from the React Query cache. With a search set, the search resets while page and scroll are restored against the unfiltered results. Saved state survives detours (stale restore confirmed). Name (A-Z) sort gets three 422 responses (`page_size=1000`) and shows no cards and no error message; added to `VSS-stm.1`. Results recorded on `VSS-901`.

### File List

- `_bmad-output/implementation-artifacts/16-0-spike/browse_probe.mjs` (new)
- `_bmad-output/implementation-artifacts/16-0-spike/browse_probe.out.json` (new)
- `_bmad-output/implementation-artifacts/16-0-epic-16-technical-preparation.md`

## Change Log
