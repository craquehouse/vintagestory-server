# Story 16.2: Installed Mods Recognized by Any Mod ID

Status: ready-for-dev

<!-- Implements FR169 and Epic 16 ADR-2 decision 2 ("which mod ID"), detail-page side. Bead: VSS-ywb. Related, NOT in scope: VSS-jhf (install can pick a release from a different mod ID). Stacks on Story 16.1 (PR #148). -->

## Story

As an **administrator**,
I want **a mod's detail page to know when I already have it installed**,
so that **I am not offered an install for a mod I have**.

## Acceptance Criteria

1. **Given** a mod database entry that ships several mod IDs (for example `instruments`, `vsinstruments`, `vsinstrumentsbase`), and I have installed one that is not the entry's browse slug (for example `vsinstrumentsbase`, while the browse card opens `/game-server/mods/browse/instruments`)
   **When** I open the entry's detail page
   **Then** it shows the installed state ("Installed: v<installed version>") and the version section, not the Install button or the install dialog
   *(Covers FR169; `VSS-ywb`)*

2. **Given** the detail page recognized an installed mod through a mod ID other than the URL slug
   **When** I look at its version list and actions
   **Then** the version list holds only releases whose `modidstr` is the installed mod's ID, the Update button offers that mod ID's update from the update status, and Update or Switch changes the version of that mod ID (`PUT /mods/<installed mod ID>/version`), never another mod ID's release

3. **Given** several of the entry's mod IDs are installed
   **When** I open the detail page
   **Then** the installed mod whose ID is the URL slug is shown when there is one; otherwise the installed mod whose ID has the entry's newest release (the first match in release order, newest first)

4. **Given** any other case
   **When** I open a detail page
   **Then** behavior is unchanged: a mod installed under the URL slug is recognized as before (also when the entry's releases carry no `modidstr`); a mod that is not installed shows the install flow; an installed mod whose ID does not appear in the entry is not matched; mod IDs are compared exactly, as the update check and the version change API compare them

5. **Given** Story 16.3 needs the same answer to "which installed mod ID is this entry" (ADR-2 decision 2)
   **When** the matching is implemented
   **Then** it lives in one exported, unit-tested helper in `web/src/lib/`, and `ModDetailPage` uses it instead of an inline `slug ===` comparison

## Tasks / Subtasks

<!-- Each functional task includes its tests in the same commit. Commit per task: type(story-16.2/task-N): ... ; feat/fix only for user-visible changes, subject written for users. -->

- [ ] Task 1: Mod ID matching helper + tests (AC: 3, 4, 5)
  - [ ] 1.1: Create `web/src/lib/mod-ids.ts` with `entryModIds(releases: Pick<ModRelease, 'modidstr'>[]): string[]` (distinct, non-empty `modidstr` values in release order, newest first) and `findInstalledModForEntry<T extends { slug: string }>(installedMods: readonly T[] | undefined, entry: { slug: string; releases: Pick<ModRelease, 'modidstr'>[] }): T | undefined` implementing AC 3 and AC 4 (URL slug first, then `entryModIds` order; exact comparison; `undefined` for no list)
  - [ ] 1.2: Tests in `web/src/lib/mod-ids.test.ts`: the instruments shape (three mod IDs, installed one last or middle), URL slug wins over an earlier-release mod ID, newest-release mod ID wins when the URL slug is not installed, no `modidstr` on releases (URL slug still matches), installed mod from another entry not matched, case differs → no match, empty and `undefined` installed lists, duplicates and empty strings dropped from `entryModIds`

- [ ] Task 2: Detail page recognizes the installed mod by any of the entry's mod IDs + tests (AC: 1, 2, 3, 4)
  - [ ] 2.1: `ModDetailPage`: replace `modsData?.data?.mods?.find((m) => m.slug === slug)` with `findInstalledModForEntry(modsData?.data?.mods, { slug, releases: mod.releases })`, computed after the `mod` guards (the releases are needed); `InstalledVersionSection` keeps receiving `installedMod.slug`, so its version list, update status lookup and version change already use the installed mod ID
  - [ ] 2.2: Update the header doc comment (Story 16.2 note)
  - [ ] 2.3: Tests in `ModDetailPage.test.tsx` ("Story 16.2" block) with an instruments-shaped lookup response (releases for `vsinstrumentsbase`, `vsinstruments`, `instruments`) opened at `/game-server/mods/browse/instruments`: installed `vsinstrumentsbase` → installed indicator, no Install button; version options only `vsinstrumentsbase` releases; Update button uses the `vsinstrumentsbase` offered update and the `PUT` goes to `/mods/vsinstrumentsbase/version`; installed `vsinstruments` (middle) also recognized; two installed → AC 3 choice; unrelated installed mod → install flow. Existing tests keep passing unchanged

- [ ] Task 3: Browser verification against the Docker dev stack + E2E (AC: 1, 2)
  - [ ] 3.1: Add `web/e2e/installed-mod-any-modid.spec.ts` (Playwright, Docker stack, live mod database): open `/game-server/mods/browse/instruments` with the installed mods list (`GET /api/v1alpha1/mods`) fulfilled by `page.route`, so nothing is installed on the stack. Test 1: the list holds `vsinstrumentsbase` at its newest live version (read from the real lookup response, which the spec does not mock) → installed indicator, no Install button, and version options that are exactly the live `vsinstrumentsbase` releases. Test 2: the list holds `vsinstruments` (a middle mod ID) → recognized too. Test 3: the list is empty → the install flow
  - [ ] 3.2: `just docker restart` (rebuild from this branch), run the spec (`cd web && bunx playwright test e2e/installed-mod-any-modid.spec.ts`)
  - [ ] 3.3: Real-install check in the dev stack: note the installed mod set, install `instruments` through the UI (today this installs `vsinstrumentsbase`, `VSS-jhf`), confirm the detail page at `/game-server/mods/browse/instruments` shows the installed section for `vsinstrumentsbase` and the browser console is clean, take a screenshot with the server name (`span.font-semibold` in the header) masked, then remove the mod so `./data` returns to its prior mod set. Record results in the Dev Agent Record

- [ ] Task 4: Quality gate and review hand-off (AC: all)
  - [ ] 4.1: `just check` (lint, typecheck, all tests) passes
  - [ ] 4.2: Story status `review`, `just sprint set 16-2-installed-mods-recognized-by-any-mod-id review`, PR to `story/16-1-mod-browser-state-survives-mod-details` (stacks on #148), PR link on `VSS-ywb`

## Dev Notes

### Decision: web-only

The fix needs no API change. Everything required is already on the client:

- The lookup response (`GET /api/v1alpha1/mods/lookup/{slug}`, `useModDetail`) carries every release with its `modidstr` (`ModRelease.modidstr`, added in Story 14.3 Task 1; `api/src/vintagestory_api/services/mods.py:517-529`).
- The installed list (`GET /api/v1alpha1/mods`, `useMods`) carries each installed mod's ID as `slug` (the modinfo `modid`, `services/mod_state.py`).
- `InstalledVersionSection` (`web/src/features/mods/ModDetailPage.tsx:261-391`) already filters releases by `release.modidstr === slug`, finds the update status by `item.slug === slug` and changes versions through `useVersionChangeFlow` with that slug, all with the slug it is given. It is given `installedMod.slug`, so once the right installed mod is found, the version list and the update/switch actions refer to the installed mod ID's releases (AC 2) with no further change.

Putting the match in the API (for example an `installed_mod_id` on the lookup response) was rejected: the lookup is ModDB data with a 5-minute client `staleTime`, and tying it to local install state would need its query invalidated on every install, remove and version change. The installed list is already invalidated by those mutations.

### The bug (verified on `story/16-1-mod-browser-state-survives-mod-details` 4c5deff)

- `ModDetailPage.tsx:447`: `const installedMod = modsData?.data?.mods?.find((m) => m.slug === slug);` where `slug` is the URL parameter.
- Browse cards link with `ModBrowseItem.slug`, which is `modidstrs[0]` of the listing (`VSS-brs`). Live ModDB listing (2026-11-13): 367 entries have more than one mod ID; the Instruments entry (asset 463) has `modidstrs` `['instruments', 'vsinstruments', 'vsinstrumentsbase']` and its newest release is `vsinstrumentsbase` 2.0.7.
- So with `vsinstrumentsbase` installed, the Instruments card opens `/browse/instruments`, nothing matches, and the page offers Install. Today installing from that page installs `vsinstrumentsbase` (`VSS-jhf`), so the bug is reachable from the UI with one click.
- The detail endpoint (`/api/mod/{key}`) has no `modidstrs`; `lookup_mod` falls back to the URL slug for `slug` (`services/mods.py:533-534`). Use the releases' `modidstr` values, not `mod.slug`, for the entry's mod IDs.

### Matching rule (AC 3, AC 4)

```text
candidates = [urlSlug, ...entryModIds(releases)]   // entryModIds: distinct non-empty modidstr, newest release first
return first installed mod whose slug === a candidate, in candidate order
```

- URL slug first: links from the Installed list (`ModTable`) and typed slugs use the installed mod's own ID, so the mod the admin asked for wins when several of the entry's mod IDs are installed (common: `vsinstruments` needs `vsinstrumentsbase`).
- Then release order: the installed mod ID with the newest release, matching ADR-2's "newest release of that mod ID" orientation.
- **Exact comparison.** The update check (`services/mod_updates.py:97`) and the version change API (`services/mods.py:933`) compare `modidstr == slug` exactly; a case-insensitive match would recognize a mod whose version list is then empty. Case handling of mod IDs is `VSS-0jl`'s concern, not this story's.
- Keep the helper generic over `{ slug: string }` so it serves `ModInfo` and test doubles; do not import React.

### For Story 16.3 (same mod-ID question)

ADR-2 decision 2: the mod ID is "the installed mod's ID when the mod is installed; otherwise the mod ID whose release the install flow would install (today `releases[0].modidstr`)". `findInstalledModForEntry` answers the first half for the web. If 16.3 needs the answer server-side for the lookup's compatibility, it should either pass the mod ID found here to the API or mirror this rule exactly (URL slug first, then release order, exact comparison); do not invent a second rule.

### Out of scope

- `VSS-jhf`: install picking `releases[0]` across mod IDs (API). The install flow's version list for a not-installed entry is unchanged.
- The header "Version: {latestVersion}", the compatibility badge and the full Releases list stay entry-wide (`releases[0]`); per-mod-ID compatibility is Story 16.3.
- Browse cards' "Installed" badge (`ModCard`, `BrowseTab.installedSlugs`) also compares only the browse slug. Browse items carry only `modidstrs[0]`, so fixing it needs API data; file a top-level bead, do not fix here.
- Any other Epic 16 story.

### Testing Requirements

**CRITICAL:** Tests are written with each task and committed with it. `just test-web` after each task; `just check` before review.

- Unit: `web/src/lib/mod-ids.test.ts`.
- Component: `ModDetailPage.test.tsx` with the existing `mockInstalled` fetch double in the "installed state (Story 14.3)" block (it already serves lookup, updates, installed list and `PUT .../version`). Radix Select needs the `hasPointerCapture`/`releasePointerCapture`/`scrollIntoView` stubs from that block's `beforeAll`.
- E2E: `web/e2e/installed-mod-any-modid.spec.ts` against the Docker stack, following `web/e2e/mod-browse-state.spec.ts` (API key `VS_API_KEY_ADMIN` or `changeme`, live mod database). Use `page.route` for the installed list so the spec never installs anything. E2E tests are not part of `just check`.

**UI Stories - Manual Browser Verification:** Docker stack (`just docker restart`, http://localhost:8080, game 1.22.7 installed in `./data`). The real-install check in Task 3.3 installs and then removes `instruments`/`vsinstrumentsbase`; `./data` must end with its prior mod set. Screenshots committed to this public repo mask the server name (header `span.font-semibold`, `#ServerName`) and password. Check the browser console for errors. `just docker stop` is not required after (the stack may stay up for review).

### Security Requirements

- No API change and no new input. The helper reads typed data from two existing queries.

### Development Commands

- `just test-web src/lib/mod-ids.test.ts`, `just test-web src/features/mods/ModDetailPage.test.tsx`, `just check`, `just docker restart`, `cd web && bunx playwright test e2e/installed-mod-any-modid.spec.ts`.

### Previous Story Intelligence

- **16.1 (same epic, just finished):** `ModDetailPage` now reads `location.state` for the browse return path; do not disturb `browseTarget`/`MOD_DETAIL_RETURN_STATE`. E2E lessons: wait for specific responses and DOM markers, never `networkidle` or fixed delays; pick live data at run time because ModDB changes daily. `main.tsx` renders under StrictMode. `just lint-web` is `tsc --noEmit` (no ESLint). 16.1 filed `VSS-2oz` (Installed tab inert on detail pages); unrelated here.
- **14.3:** introduced `InstalledVersionSection`, the `modidstr` filter and the version change flow; its review (L6) found this bug and filed `VSS-ywb`. Its tests (`withOtherModid`, `mockInstalled`) show how to build multi-mod-ID responses.
- **10.6:** the detail page and its test harness (`renderWithProviders`, routes under `/game-server/mods/browse/:slug`).

### Git Intelligence

- Branch `story/16-2-installed-mods-recognized-by-any-mod-id` from `origin/story/16-1-mod-browser-state-survives-mod-details` (4c5deff); PR base is that branch. Commits per task with `type(story-16.2/task-N)`; the user-visible fix is `fix(...)`, the helper alone is `refactor(...)`, E2E is `test(...)`, hand-off is `chore(...)`.

### Latest Technical Information

- No new libraries. Playwright `page.route(url, route => route.fulfill({ json }))` intercepts the browser's API call; match `**/api/v1alpha1/mods` exactly (not `mods/lookup/**` or `mods/updates`) so only the installed list is replaced.

### Project Structure Notes

- New: `web/src/lib/mod-ids.ts` (+ test), `web/e2e/installed-mod-any-modid.spec.ts`.
- Modified: `web/src/features/mods/ModDetailPage.tsx`, `ModDetailPage.test.tsx`.
- File naming kebab-case for new modules; co-located tests (`project-context.md`).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 16.2: Installed Mods Recognized by Any Mod ID]
- [Source: _bmad-output/planning-artifacts/prd.md] FR169
- [Source: _bmad-output/planning-artifacts/architecture/epic-16-ui-polish.md#ADR-2: Most Recent Supported Game Version] decision 2
- [Source: _bmad-output/implementation-artifacts/14-3-update-and-version-switching-ui.md] Task 1 (`modidstr`), Task 5 (`InstalledVersionSection`)
- [Source: _bmad-output/implementation-artifacts/16-1-mod-browser-state-survives-mod-details.md]
- [Source: _bmad-output/implementation-artifacts/10-6-mod-detail-view.md]
- [Source: api/tests/fixtures/moddb/README.md] and `mod_instruments.json` (one entry, three mod IDs)
- Beads: `VSS-ywb` (this story), `VSS-jhf` (related, out of scope), `VSS-brs`, `VSS-0jl`
- `project-context.md` - critical implementation rules and patterns

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List

## Change Log

- 2026-11-13: Story 16.2 created (ready-for-dev).
