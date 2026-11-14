# Story 16.3: Latest Supported Game Version for Incompatible Mods

Status: review

<!-- Implements FR170 and Epic 16 ADR-2 decisions 1-5 (decision 6: browse cards unchanged). Bead: VSS-udh. Related, NOT in scope: VSS-jhf (install can pick a release from a different mod ID), VSS-4f3 (browse-card "has a release for your version" flag). Stacks on Story 16.2 (PR #149), itself on 16.1 (PR #148). -->

## Story

As an **administrator**,
I want **to see which game version an unverified or incompatible mod last supported**,
so that **I can judge how far behind it is before installing it**.

## Acceptance Criteria

1. **Given** a mod that is not verified or is incompatible with my installed game version
   **When** I view it on its detail page or in the Installed mods list
   **Then** the compatibility message names the most recent game version the mod supports, and the Installed list shows that version beside the badge
   *(Covers FR170; `VSS-udh`)*

2. **Given** a mod database entry
   **When** the API computes the most recent supported game version
   **Then** it is the highest release tag across the releases whose `modidstr` is the evaluated mod ID, compared with `parse_base_version` and `is_prerelease` (by base version, then a stable tag above pre-releases of the same base); stable tags are preferred and a pre-release is used only when the mod ID has no stable tag; tags that do not parse are ignored; it is returned as `latest_supported_game_version` on `CompatibilityInfo` (`latestSupportedGameVersion` in the web types), `null` when no tag parses
   *(ADR-2 decisions 1 and 5)*

3. **Given** a lookup of a mod database entry
   **When** the API picks the mod ID and the release whose compatibility it reports
   **Then** the mod ID is the installed mod's ID when one of the entry's mod IDs is installed (the same rule as Story 16.2's `findInstalledModForEntry`: the looked-up slug first, then the entry's mod IDs in release order, exact comparison), otherwise the mod ID of `releases[0]` (the release the install flow installs); without a `version` the reported release is the newest release of that mod ID, not `releases[0]` of the whole entry; with the new optional `version` query parameter it is that mod ID's release with that `modversion`
   *(ADR-2 decisions 2 and 3)*

4. **Given** a mod is installed
   **When** I view it in the Installed mods list
   **Then** its compatibility reflects the installed release, not the newest one

5. **Given** a release that is not compatible with the installed game version
   **When** the compatibility message is built
   **Then** it uses the mod ID's lowest and highest supported versions: behind (highest < installed) "Last supported game version: 1.21.1."; ahead (lowest > installed) "Requires game version 1.23.0 or newer (installed: 1.22.7)."; gap (installed between them but not tagged) "Not tagged for 1.22.7; supports 1.21.0 to 1.23.0."; `not_verified` keeps its wording and adds "Last tagged for X." when the highest supported version is older than the installed one
   *(ADR-2 decision 4)*

6. **Given** I browse mods
   **When** the cards are shown
   **Then** they are unchanged: the version needs mod details, which browse cards do not fetch (Epic 16 ADR-2 decision 6)

## Tasks / Subtasks

<!-- Each functional task includes its tests in the same commit. Commit per task: type(story-16.3/task-N): ... ; feat/fix only for user-visible changes, subject written for users. Adding an API field or an optional parameter is not a breaking change. -->

- [x] Task 1: Supported game version range per mod ID + tests (AC: 2)
  - [x] 1.1: New module `api/src/vintagestory_api/services/mod_compatibility.py` with `supported_game_versions(releases, modid) -> SupportedRange | None` (frozen dataclass `lowest`, `highest`, both tag strings) over the releases whose `modidstr` equals `modid`. Sort key: `parse_base_version` with trailing zero parts dropped (so `1.21` equals `1.21.0`), then stable above pre-release. Stable tags preferred for both ends; pre-releases only when the mod ID has no stable tag; unparsable tags ignored; `None` when nothing parses. Ties keep the first tag seen
  - [x] 1.2: `compare_game_versions(left, right) -> int | None` with the same key, used by the message builder
  - [x] 1.3: Tests in `api/tests/test_mod_compatibility.py`: `mod_playercorpse.json` (highest `1.21.1`, not `1.21.1-rc.2`; lowest `1.14.0`), `mod_instruments.json` per mod ID (`instruments` 1.18.6, `vsinstruments` 1.19.3, `vsinstrumentsbase` 1.21.6), `mod_carryon.json` (release order is not version order; highest `1.22.7`), pre-release-only mod ID, unparsable tags (`"stable"`, `"1.x"`), `1.21` vs `1.21.0`, unknown mod ID → `None`

- [x] Task 2: Lookup reports the evaluated mod ID's release, its latest supported version and the ADR-2 messages + tests (AC: 1, 2, 3, 4, 5)
  - [x] 2.1: `CompatibilityInfo.latest_supported_game_version: str | None = None` (`models/mods.py`)
  - [x] 2.2: `ModService.lookup_mod(slug_or_url, version: str | None = None)`: choose the mod ID (AC 3; installed IDs from `self._state_manager.list_mods()`), its releases (fall back to all releases when no release carries that mod ID, as for old entries without `modidstr`), and the evaluated release (newest of the mod ID, or the one matching `version`). When `version` is given but not listed for that mod ID: `not_verified`, `mod_version` = the requested version, message "Version X is not listed in the mod database; cannot verify compatibility." `latest_version`, `releases` and the rest of the response are unchanged
  - [x] 2.3: Rewrite `_build_compatibility_message` to take the range and produce the AC 5 wording. When the installed version is tagged by another release of the mod ID but not by the evaluated one (possible for an older installed release), say so ("Version X is not tagged for G; another release of this mod is.") instead of the gap wording. Without a parsable range keep today's fallback ("Mod version X is not compatible with G. Installation may cause issues."). The unknown-game-version message is unchanged
  - [x] 2.4: Router `GET /mods/lookup/{slug}` gains `version: str | None = Query(None, min_length=1, max_length=100)` and passes it through; docstring lists the new field
  - [x] 2.5: Tests: service (playercorpse behind; synthetic ahead entry; synthetic gap entry; not_verified with and without "Last tagged for"; instruments not installed → `vsinstrumentsbase` 2.0.7; instruments with `vsinstruments` installed → its newest release 1.2.7 and 1.19.3; URL slug wins; `version` picks the installed release; unlisted `version`; old entries without `modidstr`), router (`?version=` passed through, field serialized), model. Update existing tests that pinned the `tags[:3]` wording

- [x] Task 3: Installed list evaluates the installed release and shows the latest supported version + tests (AC: 1, 4)
  - [x] 3.1: `web/src/api/types.ts`: `ModCompatibility.latestSupportedGameVersion: string | null`; `lookupMod(slugOrUrl, version?)` adds `?version=` (encoded); `queryKeys.mods.lookup(slug, version?)` appends the version only when given, so the detail page key is unchanged
  - [x] 3.2: `useModsCompatibility(mods: { slug: string; version: string }[])` looks up each installed mod with its installed version and returns `compatibilityMap: Map<slug, ModCompatibility>` (status, message, latest supported version) plus `sideMap`
  - [x] 3.3: `ModTable`: the Compatibility cell shows the badge with the message as its tooltip and, for `not_verified` and `incompatible` with a known version, "Supports up to X" beside it (`data-testid="mod-latest-supported-<slug>"`)
  - [x] 3.4: Tests: `api/mods.test.ts` (version query string), `use-mods.test.tsx` (installed version in the request and key; map contents), `ModTable.test.tsx` (version beside incompatible/not_verified, absent for compatible and unknown), `InstalledTab.test.tsx` if its doubles change

- [x] Task 4: Detail page shows the evaluated mod ID's version and the compatibility message + tests (AC: 1, 3)
  - [x] 4.1: `ModDetailPage` header: "Version:" shows `compatibility.modVersion` (the release that decides the badge), falling back to `latestVersion`; the compatibility message is shown as text under the badge row for `not_verified` and `incompatible` (`data-testid="mod-detail-compatibility-message"`), not only as a tooltip. The install flow (`InstallSection latestVersion`) is unchanged (`VSS-jhf`)
  - [x] 4.2: Tests in `ModDetailPage.test.tsx` ("Story 16.3" block): message visible for incompatible and not_verified, absent for compatible; header version follows `compatibility.modVersion`. Browse card tests unchanged (AC 6)

- [x] Task 5: Browser verification against the Docker dev stack (AC: 1, 4, 6)
  - [x] 5.1: `just docker restart` (rebuild from this branch). Note the installed mod set. Open `/game-server/mods/browse/playercorpse`: Incompatible badge, message "Last supported game version: 1.21.1." (or the live equivalent), header version = newest playercorpse release
  - [x] 5.2: Install `playercorpse` through the UI; Installed list shows Incompatible and "Supports up to 1.21.1"; open `/game-server/mods/browse/instruments` (not installed) and check the header names the `vsinstrumentsbase` release. Browse cards look as before. Browser console clean
  - [x] 5.3: Screenshot with the server name masked (header `span.font-semibold`, `#ServerName`), kept outside the repo unless needed; remove `playercorpse` and its cached zip so `./data` returns to its prior mod set; record results in the Dev Agent Record

- [x] Task 6: Quality gate and review hand-off (AC: all)
  - [x] 6.1: `just check` passes
  - [x] 6.2: Status review, `just sprint set 16-3-latest-supported-game-version-for-incompatible-mods review`, PR to `story/16-2-installed-mods-recognized-by-any-mod-id` (stacks on #149 and #148), PR link on `VSS-udh`

## Dev Notes

### Today's behavior (verified on `story/16-2-installed-mods-recognized-by-any-mod-id` 9842138)

- `ModService.lookup_mod` (`api/src/vintagestory_api/services/mods.py:441-560`) evaluates `releases[0]` of the whole entry with `check_compatibility` (`services/mod_api.py:168`) and builds the message from `latest_release.tags`; the incompatible message lists `tags[:3]`, which for `playercorpse` 1.12.0 are its three *oldest* tags (`1.21.0, 1.21.1-rc.1, 1.21.1-rc.2`).
- `CompatibilityInfo` (`models/mods.py:132`) has `status`, `game_version`, `mod_version`, `message`. It is used only by the lookup.
- The router (`routers/mods.py:550`) takes only the path slug.
- Web: `useModsCompatibility(slugs)` (`web/src/hooks/use-mods.ts:314`) looks up each installed slug with the detail-page query key and keeps only the status; `ModTable` (`components/ModTable.tsx:315`) renders the badge with no message. `ModDetailPage` shows the badge with the message only as a `title` tooltip and "Version: {latestVersion}" (`releases[0]` of the entry).
- Story 16.2 saw it live: with `vsinstrumentsbase` installed, the instruments page header still says "Version: 2.0.7" and "Incompatible" from the entry's newest release, whatever mod ID is installed.

### Decisions

- **Where the mod ID is chosen: the API.** The detail page needs the compatibility of the installed mod ID's newest release, and the installed mod is only known after the lookup returns its releases; passing the mod ID from the client would need a second lookup. The API knows the installed mods (`ModStateManager.list_mods()`), and mirrors `findInstalledModForEntry` exactly (looked-up slug first, then distinct non-empty `modidstr` in release order, exact comparison), as Story 16.2's Dev Notes require. Caching is safe: every lookup key starts with `['mods']` and install, remove, enable/disable and version change all invalidate `queryKeys.mods.all`, so lookups refetch after the installed set changes.
- **The Installed list passes `version`.** Its lookup slug is the installed mod's own ID, so the API's rule picks that mod ID, and `version` selects the installed release (`modidstr` and `modversion`, like `evaluate_update`). Its query key includes the version, so the detail page (no version) and the Installed list never share a cache entry.
- **Range comparisons.** Drop trailing zero parts from `parse_base_version` so `1.21` and `1.21.0` compare equal; a stable tag sorts above pre-releases of the same base; pre-releases of the same base are not ordered among themselves (no new parser; first seen wins). The installed game version is compared with the same key; if it does not parse, messages fall back to today's wording (no direction can be named).
- **Gap vs. tagged elsewhere.** ADR-2's gap wording ("Not tagged for G") is wrong when another release of the same mod ID *is* tagged for G, which happens when the evaluated release is an older installed release. That case gets "Version X is not tagged for G; another release of this mod is." The Installed list's Available column already offers the update. This is an addition to ADR-2, not a change.
- **Unlisted `version`.** If the requested release is not in the mod database (removed upload), report `not_verified` for that version with a message saying so, mirroring `evaluate_update`'s `installed_release_not_listed`, rather than silently evaluating another release.
- **`latest_supported_game_version` is always filled** when a tag parses, for every status; the UI only shows it for `not_verified` and `incompatible`.
- **Detail page shows the message as text.** ADR-2 decision 5 puts the version in the detail page's compatibility message; today that message is only a tooltip, which touch screens never show. It is rendered as a short line under the header for `not_verified` and `incompatible`.
- **Header version.** "Version:" shows the release the badge describes (`compatibility.mod_version`), so badge and version agree. `latest_version` in the API keeps its meaning (`releases[0]`), so no API field changes meaning.

### Out of scope

- `VSS-jhf` (install from a multi-mod-ID entry picks `releases[0]`), `VSS-4f3` (browse-card flag), browse cards in general (AC 6), the install dialog's version list, any other Epic 16 story. Adjacent problems become beads.

### Testing Requirements

**CRITICAL:** Tests are written with each task and committed with it. `just test-api ...` / `just test-web ...` after each task; `just check` before review.

- Fixtures: `api/tests/fixtures/moddb/mod_playercorpse.json` (behind), `mod_instruments.json` (mod ID choice), `mod_carryon.json` (release order is not version order). The ahead and gap cases use synthetic entries in the tests (ADR-2 consequence); no new fixture file is needed.
- Installed state in service tests: write mods through the existing `ModStateManager` helpers used in `test_mod_service.py`, or construct the service with state, following the existing lookup tests (`TestModServiceLookupMod`).
- Web: `ModTable.test.tsx` and `use-mods.test.tsx` mock `fetch`; the lookup URL now carries `?version=`.

**UI Stories - Manual Browser Verification:** Docker stack (`just docker restart`, http://localhost:8080, game 1.22.7 in `./data`). Task 5 installs and removes `playercorpse`; `./data` must end with its prior mod set (mods and `cache/mods`). Screenshots committed to this public repo mask the server name (`span.font-semibold` in the header, `#ServerName`) and password. Check the browser console.

### Security Requirements

- The new `version` query parameter is length-limited and only compared for equality with release data; it is never used in a path or a file name. Lookup stays read-only for Admin and Monitor.

### Development Commands

- `just test-api tests/test_mod_compatibility.py`, `just test-api tests/test_mod_service.py -k lookup`, `just test-api tests/test_mods_router.py -k lookup`, `just test-web src/components/ModTable.test.tsx`, `just test-web src/features/mods/ModDetailPage.test.tsx`, `just check`, `just docker restart`.

### Previous Story Intelligence

- **16.2:** `web/src/lib/mod-ids.ts` `findInstalledModForEntry` is the single matching rule on the web; the API mirror must use the same order and exact comparison. `ModDetailPage` computes `installedMod` after the response guards; `InstalledVersionSection` is unaffected here. E2E lesson: read live ModDB data at run time; the API key for scripts comes from `.env` (`VS_API_KEY_ADMIN`). Real-install verification removed the mod with `DELETE /api/v1alpha1/mods/<id>` and deleted the cached zip in `cache/mods`.
- **16.1:** `just lint-web` is `tsc --noEmit`; StrictMode double-mounts.
- **14.1:** `parse_base_version`, `is_prerelease` and `evaluate_update` (installed release = matching `modidstr` and `modversion`, first occurrence).

### Git Intelligence

- Branch `story/16-3-latest-supported-game-version-for-incompatible-mods` from `origin/story/16-2-installed-mods-recognized-by-any-mod-id` (9842138); PR base is that branch. Planned types: Task 1 `refactor` (helper only), Task 2 `fix` (the message named the wrong versions), Task 3 `feat`, Task 4 `fix`, Task 5 `docs`/`test`, Task 6 `chore`.

### Latest Technical Information

- No new libraries. FastAPI `Query(None, min_length=..., max_length=...)` with `Annotated` as used elsewhere in `routers/mods.py`. TanStack Query `useQueries` keys are compared structurally.

### Project Structure Notes

- New: `api/src/vintagestory_api/services/mod_compatibility.py`, `api/tests/test_mod_compatibility.py`.
- Modified: `models/mods.py`, `services/mods.py`, `routers/mods.py`, API tests; web `api/types.ts`, `api/mods.ts`, `api/query-keys.ts`, `hooks/use-mods.ts`, `components/ModTable.tsx`, `features/mods/ModDetailPage.tsx` and their tests.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 16.3: Latest Supported Game Version for Incompatible Mods]
- [Source: _bmad-output/planning-artifacts/prd.md] FR170
- [Source: _bmad-output/planning-artifacts/architecture/epic-16-ui-polish.md#ADR-2: Most Recent Supported Game Version]
- [Source: _bmad-output/implementation-artifacts/16-0-spike/moddb_probe.py] and `moddb_probe.out.txt`
- [Source: _bmad-output/implementation-artifacts/16-2-installed-mods-recognized-by-any-mod-id.md] "For Story 16.3"
- [Source: api/tests/fixtures/moddb/README.md]
- Beads: `VSS-udh` (this story), `VSS-jhf`, `VSS-4f3` (related, out of scope)
- `project-context.md` - critical implementation rules and patterns

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5)

### Debug Log References

- Task 1: red run of `test_mod_compatibility.py` (module missing, collection error), then 21 passed; ruff and pyright clean (pyright 0 errors, 3 pre-existing warnings in API tests).
- Task 2: new tests written after a first cut of the service change; red verified by stashing `api/src`: 15 of the 16 new `TestLookupLatestSupportedGameVersion` tests failed (the one that passed pins the unchanged fallback wording), then 16 passed with the change. Six existing tests failed on the change as expected (two model serializations gained the field; four pinned the `tags[:3]` wording or the old builder signature) and were updated. API 2,104 passed; ruff clean; pyright 0 errors, 3 pre-existing warnings.
- Task 3: red run with the four source files stashed: 8 tests failed (the new lookup query-string test, two new ModTable tests, the new hook test, and four existing hook tests that now pass installed mods), then green. Web 3,115 passed, 4 skipped (pre-existing `it.skip`s); `tsc` clean.
- Task 4: red run, 3 of the 4 new detail page tests failing (the compatible case already showed no message), then 71 passed. Web 3,119 passed, 4 skipped; `tsc` clean.
- Task 5: `just docker restart` rebuilt the stack from this branch at 2a8d0c5 (game 1.22.7, server stopped). `./data` had `betterruins`, `smithingplus` 1.9.0-rc.1, `carryon`, `carryonlib`, `egocaribautomapmarkers`; Mods folder, `cache/mods` and the state file list snapshotted before. Scratchpad Playwright script (Chromium 1440x900, API key from `.env`):
  - Detail pages: `playercorpse` Incompatible, message "Last supported game version: 1.21.1.", Version 1.12.0; `instruments` (not installed) Incompatible, "Last supported game version: 1.21.6.", Version 2.0.7 (`vsinstrumentsbase`); `smithingplus` Not verified, "Mod not explicitly verified for version 1.22.7. May still work. Last tagged for 1.22.2." (live data: its newest release is tagged up to 1.22.2 including pre-releases of 1.22.0).
  - Installed `playercorpse` 1.11.1 (an older release, chosen in the version select) through the detail page's Install flow. Installed list lookups were `.../lookup/<slug>?version=<installed version>` for all six mods; Player Corpse showed Incompatible with "Supports up to 1.21.1" and the message as its tooltip, Smithing Plus and Auto Map Markers Not verified with "Supports up to 1.22.2" / "1.22.3", the compatible mods no version. The detail page afterwards (no `version`) evaluated 1.12.0, the mod ID's newest release.
  - Browse grid rendered 8 cards with no lookup requests; browse components have no diff on this branch (AC 6).
  - No console errors or warnings on any page. Screenshots (server name masked) kept in the session scratchpad, not committed.
  - Removed with `DELETE /api/v1alpha1/mods/playercorpse` and deleted `cache/mods/PlayerCorpse_VS1.20.7_net7_v1.11.1.zip`; the Mods folder, `cache/mods` and the state file list match the snapshot (only directory mtimes differ).
- Task 6: `just check` passed: ruff and `tsc` clean, pyright 0 errors (3 pre-existing warnings in API tests), API 2,104 passed, web 3,119 passed and 4 skipped (pre-existing `it.skip`s), script tests 190 passed. No suppressions added.

### Completion Notes List

- Task 1: `services/mod_compatibility.py` exports `SupportedRange`, `supported_game_versions(releases, modid)` and `compare_game_versions(left, right)`. Sort key is `parse_base_version` with trailing zero parts dropped, then stable above pre-release; stable tags preferred for both ends; unparsable and non-string tags ignored; ties keep the first tag seen. Not used yet; Task 2 wires it into the lookup.
- Task 2: `CompatibilityInfo.latest_supported_game_version`. `lookup_mod(slug_or_url, version=None)` picks the mod ID with `_compatibility_modid` (installed looked-up slug, then installed entry mod IDs in release order, exact comparison; else `releases[0].modidstr`; a match with no releases in the entry falls back to the default), evaluates that mod ID's newest release or its `version` release, and reports an unlisted `version` as `not_verified` with "Version X is not listed in the mod database; cannot verify compatibility." `_build_compatibility_message` now takes the `SupportedRange` and produces the ADR-2 behind/ahead/gap wording, "Last tagged for X." on `not_verified`, "Version X is not tagged for G; another release of this mod is." when an older evaluated release misses a version another release has, and today's fallback when there is no range or the game version does not parse. `latest_version` and `releases` are unchanged. Router: optional `version` query parameter (1-100 chars).
- Task 3: `ModCompatibility.latestSupportedGameVersion`; `lookupMod(slugOrUrl, version?)` adds `?version=` (encoded); `queryKeys.mods.lookup(slug, version?)` appends `{ version }` only when given. `useModsCompatibility` now takes the installed mods (`{ slug, version }`) and returns, besides the unchanged `compatibilityMap` (status) and `sideMap`, a `compatibilityDetails` map with the full compatibility. Deviation from subtask 3.2's wording: the status map was kept and the details added as a second map, so existing callers and tests keep their shape. `ModTable`'s Compatibility cell shows the badge with the message as its tooltip and "Supports up to X" for `not_verified`/`incompatible` when the version is known.
- Task 4: `ModDetailPage` shows the compatibility message as text under the name and badge for `not_verified` and `incompatible`, and "Version:" shows `compatibility.modVersion` (the evaluated release), falling back to `latestVersion`. The install flow still uses `latestVersion` (`VSS-jhf`). Browse cards and their tests are untouched (AC 6).
- Task 6: status review; PR targets `story/16-2-installed-mods-recognized-by-any-mod-id` (stacks on #149 and #148).
- Decisions beyond ADR-2 (recorded in Dev Notes): the API chooses the mod ID by mirroring `findInstalledModForEntry`; an evaluated older release that misses a game version another release of the mod ID has gets "Version X is not tagged for G; another release of this mod is." instead of the gap wording; an unlisted `version` is `not_verified` with its own message; the detail page shows the message as text and its header version follows `compatibility.modVersion`. `latest_version` keeps its meaning, so no API field is removed or changes meaning.
- Bead filed: `VSS-br2` [UI-074] newly installed mod shows Available: Unknown until the next update check (top-level, not Epic 16).

### File List

- `api/src/vintagestory_api/services/mod_compatibility.py` (new)
- `api/tests/test_mod_compatibility.py` (new)
- `api/src/vintagestory_api/models/mods.py`
- `api/src/vintagestory_api/services/mods.py`
- `api/src/vintagestory_api/routers/mods.py`
- `api/tests/test_mod_service.py`
- `api/tests/test_mods_router.py`
- `api/tests/test_mod_models.py`
- `web/src/api/types.ts`
- `web/src/api/mods.ts`
- `web/src/api/mods.test.ts`
- `web/src/api/query-keys.ts`
- `web/src/hooks/use-mods.ts`
- `web/src/hooks/use-mods.test.tsx`
- `web/src/components/ModTable.tsx`
- `web/src/components/ModTable.test.tsx`
- `web/src/features/mods/InstalledTab.test.tsx`
- `web/src/features/mods/ModDetailPage.tsx`
- `web/src/features/mods/ModDetailPage.test.tsx`
- `_bmad-output/implementation-artifacts/16-3-latest-supported-game-version-for-incompatible-mods.md`

## Change Log

- 2026-11-13: Story 16.3 created (ready-for-dev).
- 2026-11-13: Implemented: supported game version range per mod ID; lookup reports the installed (or install-flow) mod ID's release, `latest_supported_game_version`, the ADR-2 messages and an optional `version`; Installed list evaluates the installed release and shows "Supports up to X"; detail page shows the message and the evaluated release's version; browser verification; status review.
