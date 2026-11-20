# Sprint Change Proposal: Mod Management Follow-ups (Epic 24)

**Date:** 2026-11-20
**Author:** BMAD planner (PM and Architect), for Matt
**Workflow:** correct-course (scope named by the maintainer; product decisions asked in two rounds)
**Scope classification:** Minor
**Status:** Scope named by Matt (2026-11-20): the four mods beads `VSS-foq7`, `VSS-v3be`, `VSS-3tb1` and `VSS-hv60`, with `VSS-2bp` and `VSS-uhek` folded in. On the planner's proposal he pulled in `VSS-koo1` the same day. He answered five questions (section 5). Seven beads, eight stories. Matt approved this proposal the same day; `sprint-status.yaml` has `epic-24` and its eight stories (backlog), and the epic bead `VSS-jykl` has the seven beads as children. Planner decisions not reviewed yet are listed in section 5.

## 1. Issue Summary

**Trigger:** Epic 23 is merged (`main` at `804af73f`, PRs #207 to #213; its epic bead `VSS-7f7s` is closed). After it, the maintainer grouped the 12 open beads into proposed epics and chose the mods group first, folding in two small beads that belong to no group. The backlog rule (2026-11-17) applies: the epic draws the backlog down, related beads that share its files are proposed as pull-ins, and what planning finds goes into a story.

**Problem:** With more than a handful of mods installed, the Installed tab cannot be narrowed by name, compatibility or pending update. A mod copied into the mods folder by hand is picked up only when the API restarts, and even then it has no mod database link. Files the manager does not use, such as `.tmp` and `.bak` leftovers or a second archive of an installed mod, are reported only in a start-up log line. Four smaller gaps are left from Epic 19. Outside mods, the browser tab shows Vite's logo, unknown file paths answer with the web page, `/assets` responses lack the security headers, and a fresh clone cannot run the API tests.

**Evidence** (code at `804af73f`; API paths under `api/src/vintagestory_api/`):

- **Installed list.** `ModTable` (`web/src/components/ModTable.tsx`) builds its rows from the mods, compatibility (`useModsCompatibility`) and update (`useModUpdates`) data. It renders a table at `lg` and up and `InstalledModCard`s below. It has sorting (kept in the preferences cookie) but no filtering. `CompatibilityStatus` has three values (`compatible`, `not_verified`, `incompatible`), and a row shows `not_verified` while its status loads. `BrowseTab` already keeps its state in the URL with `useSearchParams` (react-router 8).
- **Hand-added mods.** `sync_state_with_disk` (`services/mod_state.py:512`) adds `.zip` and `.zip.disabled` archives with `asset_id` 0. It is called only from `sync_mod_state_at_startup` (`services/mods.py:157`), whose docstring forbids calling it from a route, because it changes the state without a mod lock.
- **Update check.** `ModUpdateService.check` (`services/mod_updates.py:460`) already calls `get_mod(slug)` for every installed mod, hand-added ones included, and stores the releases. The mod payload carries `assetid` (`services/mod_api.py:609`), but the check never writes it to the mod state. So a hand-added mod already gets update status and Update after a check. What it lacks is the ModDB link (`InstalledModParts.tsx:32` links only when `assetId > 0`). A mod the database does not know already shows "Not found in the mod database" (`ModUpdateCell.tsx:17`).
- **Mod locks.** Installs and version changes hold a per-mod key in `ModService._busy` across their `await`s (`_hold`, `services/mods.py:445`). Enable, disable and remove are synchronous and never interleave with other synchronous code on the event loop.
- **Unused files.** `recover_working_files` (`services/mod_file_recovery.py`) deletes `.vsm-tmp` copies, settles `.vsm-bak` originals, and logs other `.tmp` and `.bak` names as `mod_directory_unknown_leftovers` without deleting them. The sync logs archives it skips (`unreadable`, `duplicate_mod_id`) and keeps no record of them.
- **Epic 19 follow-ups** (`VSS-3tb1`):
  - (1) `change_version` has no `ModFileMissingError` check, unlike enable and disable (Epic 19 ADR-9).
  - (2) An interrupted rename to a new file name leaves two archives of one mod, and the sync skips the second as `duplicate_mod_id`.
  - (3) `CacheEvictionService.CACHE_FILE_PATTERNS = ("*.zip", "*.cs")` (`services/cache_eviction.py:71`).
  - (4) `_cache_modinfo` writes `state/mods/<slug>/<version>/modinfo.json`, and neither `remove_mod` nor the sync removes it.
- **Favicon.** `web/index.html:5` links `/vite.svg`. `web/public/` has `vintagestory-icon.webp` and `@2x`. `_resolve_frontend_file` (`main.py:303`) returns `index.html` for any path that is not a file, `/favicon.ico` included. `/assets` is a `StaticFiles` mount without `frontend_security_headers` (`main.py:328`).
- **Description media.** `web/src/lib/mod-description.ts` replaces an `<img>` the CSP would block with a "not shown" note (Story 19.3) and does nothing for `<video>`, `<audio>`, `<source srcset>`, `poster`, `background`, inline `url()` or SVG `<image href>`.
- **Tests without `.env`.** `Settings` refuses to start without `VS_API_KEY_ADMIN` (`config.py:290`). Locally the key comes from `.env` through `.mise.toml`'s `env_file`, and CI sets it in `ci.yml:25`. `api/tests/conftest.py` already sets `VS_DEBUG` and removes two variables before import, but does not set this one.

**Scope decisions (made by the maintainer, 2026-11-20):**

| Decision | Choice |
|---|---|
| Items in scope | `VSS-foq7`, `VSS-v3be`, `VSS-3tb1`, `VSS-hv60`; `VSS-2bp` and `VSS-uhek` folded in; `VSS-koo1` pulled in |
| Backlog rule | The epic draws the backlog down; findings go into stories; the net bead change is reported |
| Asset ID of hand-added mods | Filled in by the update check (answer 1) |
| Rescan | An Admin Rescan action on the Installed tab (answer 2) |
| Unused files | A list on the Installed tab with a confirmed Delete, covering `.tmp`/`.bak` leftovers and archives the sync skipped (answer 3) |
| Installed filters | Kept in the URL (answer 4) |
| `VSS-koo1` | Pulled in: `/assets` headers with the favicon story; description media as its own story (answer 5) |

**Grouping:**

| Story | Beads | Why this grouping |
|---|---|---|
| 24.1 API Tests Run on a Fresh Clone | `VSS-uhek` | Test tooling first, so every later story's tests run in a worktree without `.env` |
| 24.2 The Web UI Has Its Own Icon, and Missing Files Are 404 | `VSS-2bp`, `VSS-koo1` (item 1) | Both change how `register_frontend` serves files |
| 24.3 Mod File Follow-ups from Epic 19 | `VSS-3tb1` (items 1, 3, 4) | Small fixes in `mods.py`, `cache_eviction.py` and `mod_state.py`; item 2 is closed by 24.5 |
| 24.4 Hand-Added Mods Get Their Mod Database Link | `VSS-v3be` (first half) | The update check stores the asset ID; the "local mod" wording |
| 24.5 Unused Files and Rescan in the API | `VSS-hv60` (API half), `VSS-v3be` (rescan), `VSS-3tb1` (closes, item 2) | One API pull request for the sync's new record, the listing, the delete and the rescan route, all under one busy rule |
| 24.6 Rescan and Unused Files on the Installed Tab | `VSS-hv60` (closes), `VSS-v3be` (closes) | The web half of 24.5 |
| 24.7 Installed Mods Can Be Filtered | `VSS-foq7` | The filters, kept in the URL, on both layouts |
| 24.8 Blocked Media in Mod Descriptions Shows a Note | `VSS-koo1` (closes, item 2) | The description sanitizer only |

## 2. Impact Analysis

**Epic impact:** Epics 1 to 23 are done. None is invalidated. One new epic, Epic 24: Mod Management Follow-ups, with 8 stories. No resequencing. (Housekeeping outside this epic: `sprint-status.yaml` still says `epic-23: in-progress` while its bead is closed. `just sprint set epic-23 done` is the maintainer's call.)

**Story impact:** No existing story changes. Story 24.5 changes Epic 19 ADR-10 decision 1 ("called once, in the API's start-up ... not from a route"): the sync also runs from the Admin rescan route, under the busy rule of section 4.4. Story 24.4 extends Story 14.3's check and Story 18.2's recorder. Story 24.8 extends Story 19.3's image note to other media.

**Artifact conflicts:**

| Artifact | Change |
|---|---|
| PRD | FR327 to FR343 added; frontmatter |
| Epics | Epic 24; FR coverage rows; Story Summary row (151 stories); frontmatter |
| Architecture | New `architecture/epic-24-mod-management-follow-ups.md` (facts, ADR-1 to ADR-8); index entry; a note on Epic 19 ADR-10 decision 1 pointing to the new ADR |
| UX spec | No text change. The filters follow BrowseTab's filter bar. The unused-files notice and its dialog follow the `ModUpdatesNotice` and `AlertDialog` patterns, with 44px targets on phones |
| CI | No new job. Stories 24.6 and 24.7 add E2E checks to the CI set (throwaway container) |
| Project rules | None |
| Deployment and documentation | README: the mods section (hand-added mods, Rescan, unused files, `.cs` and folder mods left alone); the Development section (tests run without `.env`). No deployment change |
| Beads | Epic `Epic 24: Mod Management Follow-ups` with the seven in-scope issues as children |

**Technical impact:**

- No new dependency. The favicon files are generated once from the existing icon and committed. The command used is recorded in the story.
- The first route that runs the mod state sync and the first that deletes a file from the mods directory that no mod entry names. Both are Admin only and share one busy rule (ADR-4).
- No new state file. The sync's skipped archives are kept in memory and recomputed on each listing (ADR-3).
- One new CSP-related change on the API side only: the `/assets` mount gets the security headers (ADR-2). The CSP itself does not change.

**API contract and configuration changes (for the release notes):**

| Story | Where | Change | Kind |
|---|---|---|---|
| 24.2 | `GET /favicon.ico`, `/favicon-32.png`, `/apple-touch-icon.png` | Real files | New files |
| 24.2 | `GET /<path with a file extension>` that is not a file | 404 instead of the web page | Behaviour |
| 24.2 | `GET /assets/*` | Security headers, `nosniff` included | Behaviour |
| 24.3 | `PUT /mods/{slug}/version` | 409 `MOD_FILE_MISSING` when the mod's own file is missing (was 500) | Behaviour |
| 24.4 | Mod state | The update check fills in `asset_id` when it is 0 | Behaviour |
| 24.5 | `GET /mods/unused-files` | New, Admin only | New route |
| 24.5 | `DELETE /mods/unused-files/{name}` | New, Admin only | New route |
| 24.5 | `POST /mods/rescan` | New, Admin only | New route |
| 24.7 | `/game-server/mods/installed?q=&compat=&updates=` | URL parameters | Web-only |

No route is removed, no existing field changes, and nothing is breaking.

**Draft release-note text** (commit subjects; git-cliff removes the story scope):

- Features:
  - `feat(web): filter installed mods by name, compatibility and available update`
  - `feat(api): rescan the mods folder for mods copied in by hand`
  - `feat(web): rescan the mods folder from the Installed tab`
  - `feat(api): list and delete files in the mods folder that the manager does not use`
  - `feat(web): see and delete unused files in the mods folder`
  - `feat(web): show the Vintage Story icon in the browser tab`
- Fixes:
  - `fix(api): link mods added by hand to their mod database page after an update check`
  - `fix(api): answer a version change of a mod whose file is missing with 409, not 500`
  - `fix(api): evict cached mod files of every type, not only .zip and .cs`
  - `fix(api): answer 404 for missing static files instead of the web page`
  - `fix(api): send security headers with the web UI's assets`
  - `fix(web): show a note in place of video, audio and other media a mod description cannot load`
- No note: the test placeholder key (`test`), the stale modinfo cache cleanup (`fix` only if visible; planned as `refactor`), tests and documentation

## 3. Recommended Approach

**Selected:** Option 1, Direct Adjustment: add Epic 24 within the existing structure.

| Option | Assessment |
|---|---|
| 1. Direct Adjustment | Viable. Eight stories, each tied to an in-scope bead. Effort medium, risk low to medium (24.5 deletes files from the mods directory and runs the sync from a route) |
| 2. Rollback | Not viable. Nothing completed has to be undone |
| 3. MVP Review | Not needed |

**Effort:** Medium. `VSS-foq7` and `VSS-hv60` are size-m. `VSS-v3be` is unsized (planned as size-m). The other four are size-s.

**Risks:**

- **Story 24.5: deleting from the mods directory.** A name is deleted only if it is in the listing computed at the time of the request, and only if it is a regular file directly in the mods directory. A name with a path separator or traversal is refused. `.cs` files, folders and every name a mod entry or the manager's own suffixes use are never listed (ADR-3). Each refusal has a test. Tests never touch the dev stack's mods directory.
- **Story 24.5: the sync from a route.** Epic 19 ran it at start-up only because it takes no mod lock. ADR-4 refuses a rescan while any install, version change, update all or update check runs, and refuses those operations while a rescan runs. The sync is synchronous, so enable, disable and remove cannot interleave with it.
- **Story 24.4: the check writing the mod state.** The check runs while mod operations may run. The asset ID is written only under the mod's lock, skipped when the mod is busy (filled in at the next check), and only when the entry's `asset_id` is 0 (ADR-1).
- **Story 24.2: 404 for missing files with an extension.** A client route containing a dot (a mod slug with a dot under `/game-server/mods/browse/...`) must still reach the page. ADR-2 limits the rule to the last segment of paths outside the web UI's own routes, with a test for a dotted mod slug.
- **Story 24.7: filters in the URL.** Typing must not add a history entry per key. ADR-6 replaces the entry while typing, as BrowseTab does.

## 4. Detailed Change Proposals

### 4.1 PRD (`prd.md`)

**Frontmatter:** update entry "Added FR327-FR343 for Epic 24 (Mod Management Follow-ups)".

**New section after FR326:** "Epic 24: Mod Management Follow-ups", FR327 to FR343, in five groups:

- **Development and Static Files (FR327-FR330)**
  - FR327: The API tests run on a fresh clone without a `.env` file; a developer's `.env` value still wins
  - FR328: The browser tab and home-screen icon are the Vintage Story icon, as PNG files and a `favicon.ico`, and `vite.svg` is gone
  - FR329: A request for a path outside the web UI's routes whose last segment has a file extension, and that is not a file, answers 404
  - FR330: Responses under `/assets` carry the web UI's security headers
- **Mod Files (FR331-FR333)**
  - FR331: A version change of a mod whose own file is missing is refused with 409 `MOD_FILE_MISSING`, as enable and disable are
  - FR332: Cache eviction counts and evicts cached release files of every type
  - FR333: When the sync removes a mod's entry, its cached `modinfo.json` directory is removed too
- **Hand-Added Mods (FR334-FR336)**
  - FR334: The update check fills in the mod database asset ID of an installed mod whose asset ID is 0, so a hand-added mod gets its ModDB link
  - FR335: A mod the mod database does not know is shown as a local mod: listed, can be enabled, disabled and removed, no update offers
  - FR336: An Admin key can rescan the mods folder: the start-up sync runs again and the result (added, removed, skipped) is shown; a rescan is refused while a mod operation runs
- **Unused Files (FR337-FR340)**
  - FR337: The API lists the files in the mods folder that the manager does not use: `.tmp` and `.bak` names, archives without a readable `modinfo.json`, and archives whose mod ID is already installed under another file. Each has its size, modified time and reason
  - FR338: An Admin key can delete one listed file after confirming; only a file in the current listing can be deleted
  - FR339: The Installed tab shows a notice when unused files exist, with the list and a Delete per file, for Admin keys
  - FR340: `.cs` files and folders in the mods folder are never listed or deleted; the README says that the manager does not import them
- **Installed Filters and Descriptions (FR341-FR343)**
  - FR341: The Installed tab filters by name or mod ID (part of it, ignoring case), compatibility status and "update available", combined, on both the table and the cards
  - FR342: The filters are kept in the URL and can be cleared; a filter that matches nothing shows how many mods are hidden and a Clear filters button
  - FR343: In a mod description, video, audio, `srcset`, `poster`, `background`, inline `url()` and SVG image media the CSP would block are replaced with a note, as images are

### 4.2 Epics Structure (`epics.md`)

**Frontmatter:** update entry "Added Epic 24 (8 stories) for Mod Management Follow-ups; FR327-FR343".

**FR Coverage Map:** rows FR327 to FR343, each mapped to Epic 24.

**Story Summary:** `| Epic 24: Mod Management Follow-ups | 24.1, ..., 24.8 | 8 |`, and the total from 143 to 151.

### 4.3 Epic 24 Stories (appended to `epics.md`)

**Goal:** An administrator can narrow a long mod list, pick up a mod copied in by hand without restarting, see it linked to the mod database, and clear out files the manager does not use. Smaller gaps left by Epic 19 are closed along the way.

**Order:** 24.1 first (test tooling), then 24.2 to 24.4 in any order. 24.5 needs 24.3 (the missing-file error it reuses). 24.6 needs 24.5. 24.7 and 24.8 are independent.

**Story 24.1: API Tests Run on a Fresh Clone** (`VSS-uhek`, closes)
- `api/tests/conftest.py` sets `VS_API_KEY_ADMIN` to a placeholder with `os.environ.setdefault`, before the app is imported, next to `VS_DEBUG`. A developer's `.env` still wins.
- Criterion: in a worktree without `.env`, `just test-api` passes. A test asserts that the placeholder is used only when the variable is unset.
- Commit type: `test`.

**Story 24.2: The Web UI Has Its Own Icon, and Missing Files Are 404** (`VSS-2bp` closes; `VSS-koo1` item 1)
- `web/public/` gains `favicon.ico` (16, 32 and 48 px), `favicon-32.png` and `apple-touch-icon.png` (180 px), generated from `vintagestory-icon@2x.webp`; `vite.svg` is removed; `index.html` links the icon and the apple-touch icon.
- `_resolve_frontend_file` answers 404 for a path outside the web UI's routes whose last segment has a file extension and that is not a file (ADR-2).
- The `/assets` mount sends `frontend_security_headers(settings.csp_mode)`.
- Criteria: `/favicon.ico` is served with an image type; `/missing.png` is 404; `/game-server/mods/browse/some.mod` and other client routes still get the page; `/assets/*` has `nosniff` and the CSP headers; every file `index.html` references exists in the build.

**Story 24.3: Mod File Follow-ups from Epic 19** (`VSS-3tb1`, items 1, 3, 4)
- `change_version` raises `ModFileMissingError` (409 `MOD_FILE_MISSING`) before any lookup when the mod's own file is not a regular file, using the check enable and disable use.
- `CacheEvictionService` evicts every regular file in a file-ID directory, not only `*.zip` and `*.cs`.
- The sync and `ModService.remove_mod` remove `state/mods/<slug>/` when no entry of that mod ID is left (ADR-5).
- Criteria: one test per item; a cache holding a `.dll` release is evicted by age and size; a stale `modinfo` directory is gone after a sync that removed its entry.

**Story 24.4: Hand-Added Mods Get Their Mod Database Link** (`VSS-v3be`, first half)
- `ModUpdateService._check_one` hands the payload's `assetid` to `ModService`, which writes it to the entry when the entry's `asset_id` is 0, under the mod's lock, skipping a busy mod (ADR-1).
- The update cell's text for `not_in_database` becomes "Local mod: not in the mod database", with no Update button and no ModDB link (FR335).
- Criteria: a hand-added mod with a known mod ID has its asset ID and link after one check; an unknown mod ID stays local; a busy mod is skipped and filled at the next check; a non-zero asset ID is never overwritten; the mod database being unavailable changes nothing.

**Story 24.5: Unused Files and Rescan in the API** (`VSS-hv60` API half; `VSS-v3be` rescan; `VSS-3tb1` closes with item 2)
- `GET /mods/unused-files` (Admin): the listing of FR337, computed on request (ADR-3).
- `DELETE /mods/unused-files/{name}` (Admin): deletes one regular file that is in the listing computed for this request; 404 when it is not; refused under the busy rule (ADR-4). A skipped archive deleted while the game server runs sets "Restart required".
- `POST /mods/rescan` (Admin): runs `sync_state_with_disk` under the busy rule and returns its summary. Added or removed entries while the game server runs set "Restart required". Start-up recovery of working files stays start-up only.
- Criteria: one test per listing reason and per refusal (name not listed, path separator, traversal, a folder, a `.cs` file, a mod's own file, a `.vsm-*` file, busy); the second archive left by an interrupted rename (3tb1 item 2) is listed as a duplicate and can be deleted; a rescan picks up a copied-in archive and refuses while an install runs, and an install refuses while a rescan runs.

**Story 24.6: Rescan and Unused Files on the Installed Tab** (`VSS-hv60` closes; `VSS-v3be` closes)
- A Rescan button beside "Check for updates", Admin only (`useIsAdmin`). A toast gives the summary, and the mods, updates and unused-files queries refresh.
- An unused-files notice above the list when the listing is not empty, Admin only: "N files in the mods folder are not used". It expands to the list (name, size, age, reason), each with a Delete that opens an `AlertDialog` naming the file.
- README mods section: hand-added mods, Rescan, unused files, `.cs` and folder mods left alone.
- Criteria: component tests for each state and role; E2E in the CI set: copy an archive into the throwaway container, Rescan, see it listed; create a `.tmp` file, see it, delete it.

**Story 24.7: Installed Mods Can Be Filtered** (`VSS-foq7`, closes)
- A filter bar above the list on both layouts: a search box (name or mod ID, part of it, ignoring case), a compatibility select (All, Compatible, Not verified, Incompatible) and an "Update available" toggle (ADR-6).
- The state is in the URL as `q`, `compat` and `updates=1`. Typing replaces the history entry. Invalid values are ignored. Sorting stays in preferences.
- With filters on: "Showing N of M mods" and Clear filters. With no match: the empty state names the filters and offers Clear filters. "Update all" and the update count are unaffected by the filters.
- Criteria: one test per filter, the combination, clear, the URL round trip (reload keeps the filter, Back restores the previous one), both layouts; E2E: a filtered URL opened directly shows the filtered list.

**Story 24.8: Blocked Media in Mod Descriptions Shows a Note** (`VSS-koo1`, closes, item 2)
- `mod-description.ts` replaces `<video>`, `<audio>`, `<source>` with `srcset` or `src`, and SVG `<image>` with the "not shown" note pattern of Story 19.3, naming the kind of media. It removes `poster`, `background` and `url()` in inline styles (ADR-7).
- The CSP is not widened (no `media-src`).
- Criteria: one test per element and attribute; a description with an allowed `https:` image is unchanged.

### 4.4 Architecture (`architecture/epic-24-mod-management-follow-ups.md`, new)

Facts checked at `804af73f` (section 1), and:

- **ADR-1: The update check fills in a missing asset ID.** Only when the entry's `asset_id` is 0 and the lookup found the mod. Written through `ModService` under the mod's lock with `_hold`, skipped when the mod is busy, saved with the state's atomic write. Not done at start-up (answer 1). A mod ID found under another asset ID than a non-zero one stored is left alone and logged.
- **ADR-2: Static file serving.** A path outside the web UI's routes (the router's top-level segments, kept in one list next to `register_frontend`) whose last segment has an extension and is not a file answers 404 with the security headers. Client routes always get `index.html`. `/assets` gets `frontend_security_headers` through a small middleware on the mount, not a second CSP.
- **ADR-3: What counts as an unused file.** Computed on each request from one listing of the mods directory:
  - Regular files whose names end in `.tmp` or `.bak`, ignoring case, but not the manager's own `.vsm-tmp` and `.vsm-bak`.
  - `.zip` and `.zip.disabled` archives with no entry whose `modinfo.json` cannot be read.
  - Archives with no entry whose mod ID is installed under another file.

  Never listed: folders, `.cs` files, other names (the game may load them), and any name a mod entry uses. The reason, size and modified time come from the file. `sync_state_with_disk`'s skip rules move into one function both use, so the listing and the sync agree.
- **ADR-4: Rescan and delete share one busy rule.** A rescan or a delete is refused (409 `MODS_BUSY`) while `_busy` is non-empty, update all runs or an update check runs. While a rescan or delete runs, installs, version changes, update all and the check refuse with the same code. Both are synchronous after the check, so enable, disable and remove cannot interleave. This amends Epic 19 ADR-10 decision 1: the sync may run from this route. Start-up recovery (ADR-9) stays start-up only.
- **ADR-5: Mod file follow-ups from Epic 19.** A version change runs the missing-file check before any lookup; eviction covers every cached file type; `state/mods/<slug>/` is removed when the last entry of that mod ID is removed, by the sync or by `remove_mod` (a version change keeps its old version's directory, as before); `VSS-3tb1` item 2 is left to ADR-3.
- **ADR-6: Installed filters.**
  - The filters use TanStack Table's column filters on the existing `ModTable` instance, so the table and the cards share one filtered row model.
  - The URL parameters are `q`, `compat` and `updates`, read and written with `useSearchParams` as `BrowseTab` does, replacing the entry while typing.
  - A row whose compatibility is still loading matches only the "All" option.
- **ADR-7: Description media.** Replaced with a note, not allowed: no `media-src` is added, so the CSP stays as Epic 19 ADR-6 set it. Attributes that only load media (`poster`, `background`, inline `url()`) are removed without a note.
- **ADR-8: Tests never touch the dev stack's mods directory.** API tests use `tmp_path`. The E2E creates and deletes its own files with `docker exec` in the CI set's throwaway container only (as Epic 23 ADR-9).

`architecture/index.md` gains the entry. `epic-19-api-security-and-mod-file-safety.md` ADR-10 decision 1 gains a one-line note pointing to Epic 24 ADR-4.

### 4.5 Other Artifacts

- `sprint-status.yaml` (through `just sprint`): `epic-24` and its retrospective entry, and the eight story keys, all `backlog`:
  - `24-1-api-tests-run-on-a-fresh-clone`
  - `24-2-web-ui-icon-and-missing-files-are-404`
  - `24-3-mod-file-follow-ups-from-epic-19`
  - `24-4-hand-added-mods-get-their-mod-database-link`
  - `24-5-unused-files-and-rescan-in-the-api`
  - `24-6-rescan-and-unused-files-on-the-installed-tab`
  - `24-7-installed-mods-can-be-filtered`
  - `24-8-blocked-media-in-mod-descriptions-shows-a-note`
- Beads: the epic bead `Epic 24: Mod Management Follow-ups` with `VSS-foq7`, `VSS-v3be`, `VSS-3tb1`, `VSS-hv60`, `VSS-2bp`, `VSS-uhek` and `VSS-koo1` as children, each with a comment naming its story or stories.

## 5. Implementation Handoff

**Scope:** Minor. A new epic in the backlog; no replanning of existing work.

| Role | Responsibility |
|---|---|
| Scrum Master (`create-story`) | Create story files 24.1 to 24.8 from `epics.md` and the Epic 24 ADRs |
| Developer (`dev-story`) | Implement each story, one task per commit; each change with a release note is its own commit with the subject written for admins; never touch the dev stack's mods directory in tests (ADR-8) |
| Reviewer (`code-review`) | Delegated, read-only review per story, given the commits and this contract |
| Maintainer (Matt) | Reviews the planner decisions below; confirms the manual check of Story 24.6 (a hand-copied mod is picked up by Rescan on the dev stack) |

**Questions for the maintainer, answered on 2026-11-20 in two rounds.** Each answer is recorded in the ADR it shapes.

1. **When a hand-added mod's asset ID is filled in (ADR-1).** Default: during the update check. Alternatives: at start-up in the background; both. *Confirmed (Matt): during the update check.*
2. **Rescan (ADR-4).** Default: a Rescan button. Alternative: start-up only. *Confirmed (Matt): Rescan button.*
3. **Unused files (ADR-3).** Default: a list with Delete, including archives the sync skipped. Alternatives: `.tmp`/`.bak` only; an automatic age rule. *Confirmed (Matt): list and Delete, skipped archives included.*
4. **Installed filter state (ADR-6).** Default: reset each visit. Alternatives: preferences; the URL. *Answered (Matt): the URL.*
5. **`VSS-koo1` (ADR-2, ADR-7).** Default: pull it in. Alternatives: item 1 only; leave it out. *Confirmed (Matt): pull it in.*

**Planner decisions not reviewed yet:**

- **Hand-added mods:**
  - Only `.zip` and `.zip.disabled` are imported; `.cs` files and folders are left alone and documented (FR340). The bead's first question.
  - "Local mod" is wording on the existing `not_in_database` status, not a new field (FR335).
- **Asset ID:** never overwrites a non-zero asset ID (ADR-1).
- **Rescan:**
  - Start-up recovery of working files is not part of a rescan (ADR-4).
  - A rescan or skipped-archive delete that changes what the game would load sets "Restart required" while the game server runs (Story 24.5).
- **Busy rule:** one new error code, `MODS_BUSY`, for both a rescan or delete refused by busy operations and the reverse (ADR-4).
- **Unused files:**
  - No new state: the listing is recomputed per request (ADR-3).
  - Deleting `.tmp`/`.bak` is allowed while the game server runs (ADR-3, Story 24.5).
- **Favicon:**
  - The 404 rule covers only paths outside the web UI's routes (ADR-2).
  - The favicon files are generated once and committed, with no build step (Story 24.2).
- **Filters:**
  - A loading compatibility matches only "All" (ADR-6).
  - Filters do not change "Update all" or its count (Story 24.7).
- **Description media:** blocked media gets a note; the CSP is not widened (ADR-7).
- **Tests:** a placeholder key in `conftest.py`, not a README step (Story 24.1).

**Other open beads that share files with this epic** (answered by Matt, 2026-11-20: `VSS-koo1` pulled in):

| Bead | Shares | Recommendation |
|---|---|---|
| `VSS-koo1` (API-094) CSP follow-ups | `register_frontend` (item 1); the mod description sanitizer (item 2) | Pulled in: Stories 24.2 and 24.8 |
| `VSS-jna` (UI-006) Lost connection to the API | No file; the Rescan and Delete errors use the existing toast handling | Not pulled in; its own epic (access and connection) |

Seen and not proposed, because they share no file with a story: `VSS-7ap` (serverconfig parsing), `VSS-2n2` (whitelist), `VSS-egi` (EntitySpawning), `VSS-2kdt` (login).

**Found during planning and handled inside the epic (no bead filed):**

1. The update check already looks up hand-added mods and gives them update status. Only the asset ID was missing, so `VSS-v3be` is smaller than written (Story 24.4).
2. `VSS-3tb1` item 2 (the second archive after an interrupted rename) is the same kind of file as `VSS-hv60`'s leftovers. It is closed by the unused-files listing (Story 24.5) instead of its own recovery rule.
3. The sync's skip rules and the listing must agree, or a file could be both skipped and not listed. ADR-3 moves them into one function.
4. A rescan from a route breaks Epic 19 ADR-10 decision 1's "start-up only" premise. ADR-4 gives it a busy rule in both directions, and Epic 19's ADR gains a note.
5. `.cs` files and folders are mods the game loads, so a naive "files without an entry" listing would offer to delete real mods. ADR-3 lists only the named categories (FR340).
6. A 404 for dotted paths could break a client route containing a mod slug with a dot. ADR-2 limits the rule and Story 24.2 tests it.

**Seen and left alone, with the reason (no bead filed):**

1. `.cs` and folder mods are not imported into the mod state. Importing them is a product change (enable/disable has no `.disabled` form for a folder). The README says so. A bead can be filed if wanted.
2. The sync's start-up logs stay as they are. The listing is the visible form; the logs keep their value for headless installs.
3. `sprint-status.yaml` still says `epic-23: in-progress`. That is Epic 23's closure, not this epic's.

**Planned net bead change:** closes 7 (`VSS-foq7`, `VSS-v3be`, `VSS-3tb1`, `VSS-hv60`, `VSS-2bp`, `VSS-uhek`, `VSS-koo1`) and opens 1 (the epic bead, which closes with the epic). None filed from planning. Net: 7 fewer open beads, from 12 open before the epic to 5 after it.

**Success criteria:**

- `just test-api` passes in a worktree without `.env`
- The browser tab shows the Vintage Story icon; a missing file with an extension is 404; `/assets` has the security headers
- A version change of a mod whose file is missing is 409; cache eviction handles every file type; stale modinfo directories are removed
- A hand-added mod gets its ModDB link after a check; an unknown one is labelled a local mod
- Rescan picks up a copied-in mod without an API restart and refuses while a mod operation runs
- Unused files are listed with their reason and can be deleted one at a time after confirming; `.cs` files, folders and mod files are never offered
- The Installed tab filters by name, compatibility and available update on both layouts, kept in the URL
- Blocked description media shows a note
- Each in-scope bead is closed with an AAR by its story after merge
- `just check` and CI pass throughout, with 0 Pyright warnings and 0 skipped web tests

## Checklist Record

| Section | Result |
|---|---|
| 1. Trigger and context | [x] 1.1 trigger: the maintainer named the mods group after Epic 23. [x] 1.2 type: new capabilities and follow-up fixes. [x] 1.3 evidence: section 1 |
| 2. Epic impact | [x] 2.1 no current epic is blocked. [x] 2.2 add one epic. [x] 2.3 no remaining epic changes. [x] 2.4 nothing made obsolete. [x] 2.5 no resequencing; the order inside Epic 24 is set |
| 3. Artifact conflicts | [x] 3.1 PRD: FR327-FR343 added, MVP unaffected. [x] 3.2 architecture: new Epic 24 ADRs, a note on Epic 19 ADR-10. [x] 3.3 UX spec: no text change. [!] 3.4 the first route that runs the sync and the first that deletes unnamed files from the mods directory |
| 4. Path forward | [x] 4.1 Direct Adjustment: viable. [x] 4.2 Rollback: not viable. [x] 4.3 MVP Review: not needed. [x] 4.4 selected Option 1 |
| 5. Proposal components | [x] 5.1 to 5.5: sections 1 to 5 |
| 6. Review and handoff | [x] 6.1 scope named by the maintainer (2026-11-20). [x] 6.2, 6.3 five questions answered in two rounds; planner decisions listed. [x] 6.4 approved by the maintainer (2026-11-20); sprint status and beads updated; handoff in section 5 |
