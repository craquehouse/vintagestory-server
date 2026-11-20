# Epic 24: Mod Management Follow-ups - Architecture Decisions

Decisions from the Epic 24 course correction (2026-11-20). Epic 24 has no preparation story. Each fact below was checked by reading the code at commit `804af73f` (`main` after Epic 23). API paths are under `api/src/vintagestory_api/`.

The maintainer named the scope: `VSS-foq7` (filter the installed mods), `VSS-v3be` (import hand-added mods), `VSS-3tb1` (mod file follow-ups from Epic 19) and `VSS-hv60` (leftover files in the mods directory), with `VSS-2bp` (favicon) and `VSS-uhek` (tests without `.env`) folded in. On the planner's proposal he pulled in `VSS-koo1` (CSP follow-ups). On 2026-11-20 he answered five questions in two rounds; each ADR's status line says which answer it carries.

| Story | ADRs |
|---|---|
| 24.1 API Tests Run on a Fresh Clone | ADR-8 |
| 24.2 The Web UI Has Its Own Icon, and Missing Files Are 404 | ADR-2 |
| 24.3 Mod File Follow-ups from Epic 19 | ADR-5, ADR-8 |
| 24.4 Hand-Added Mods Get Their Mod Database Link | ADR-1, ADR-8 |
| 24.5 Unused Files and Rescan in the API | ADR-3, ADR-4, ADR-8 |
| 24.6 Rescan and Unused Files on the Installed Tab | ADR-3, ADR-4, ADR-8 |
| 24.7 Installed Mods Can Be Filtered | ADR-6 |
| 24.8 Blocked Media in Mod Descriptions Shows a Note | ADR-7 |

## Facts Checked in the Code

**The installed list.**

- `ModTable` (`web/src/components/ModTable.tsx`) builds `ModTableRow`s from the mods, `useModsCompatibility` and `useModUpdates`. It renders a `Table` at `lg` and up and `InstalledModCard`s below, with one layout mounted at a time (`useMediaQuery(LG_UP_QUERY)`).
- TanStack Table is `@tanstack/react-table` 9.3 (`web/package.json:58`). The table has sorting, kept in the preferences cookie (`installedModsSort`), and no filtering.
- `CompatibilityStatus` is `'compatible' | 'not_verified' | 'incompatible'` (`web/src/api/types.ts:100`). A row shows `not_verified` while its status loads (`compatibilityMap.get(mod.slug) ?? 'not_verified'`).
- `BrowseTab` keeps its state in the URL with `useSearchParams` from react-router 8 (`web/src/features/mods/BrowseTab.tsx:67`). The Installed tab is the route `/game-server/mods/installed` (`web/src/App.tsx:134`).

**Hand-added mods and the update check.**

- `ModStateManager.sync_state_with_disk` (`services/mod_state.py:512`) adds `.zip` and `.zip.disabled` archives without an entry, with `asset_id` 0. It skips unreadable archives and archives whose mod ID is already installed (`duplicate_mod_id`), logging each and keeping no record.
- It is called only from `sync_mod_state_at_startup` (`services/mods.py:157`), whose docstring says it "must never be called from a route, a job or a thread", because it changes the state without a mod lock (Epic 19 ADR-10 decision 1).
- `ModUpdateService.check` (`services/mod_updates.py:460`) calls `api_client.get_mod(slug)` for every installed mod, hand-added ones included, and stores the releases. The normalized payload carries `assetid` (`services/mod_api.py:609`). The check never writes it to the mod state.
- A hand-added mod therefore already gets update status and Update after a check. The ModDB link is shown only when `assetId > 0` (`web/src/components/InstalledModParts.tsx:32`). A mod the database does not know has status `unknown` with reason `not_in_database`, shown as "Not found in the mod database." (`web/src/components/ModUpdateCell.tsx:17`).

**Mod locks.**

- Installs and version changes hold a per-mod key in `ModService._busy` across their `await`s, through `_hold` (`services/mods.py:445`), which refuses at once and never waits.
- Enable, disable and remove are synchronous, so on the event loop they never interleave with other synchronous code.
- Update all and the update check have their own locks (`ModUpdateAllInProgressError`, `ModUpdateCheckInProgressError`).

**Files in the mods directory.**

- `recover_working_files` (`services/mod_file_recovery.py`) runs once at start-up. It deletes `.vsm-tmp` copies and settles `.vsm-bak` originals. For other names ending in `.tmp` or `.bak` (ignoring case) it only logs `mod_directory_unknown_leftovers`.
- An interrupted version change to a different file name, stopped after the rename and before the old file is deleted (`_apply_version_change`, `services/mods.py:1119`), leaves two archives of one mod ID. The sync then skips the second as `duplicate_mod_id`.
- The game also loads `.cs` source files and unzipped folders as mods. The manager neither imports nor manages them.

**Epic 19 follow-ups (`VSS-3tb1`).**

- `enable_mod` and `disable_mod` raise `ModFileMissingError` (409 `MOD_FILE_MISSING`) when the mod's own file is missing. `change_version` (`services/mods.py:1047`) has no such check.
- `CacheEvictionService.CACHE_FILE_PATTERNS = ("*.zip", "*.cs")` (`services/cache_eviction.py:71`). A release of another file type is never counted or evicted.
- `_cache_modinfo` writes `state/mods/<slug>/<version>/modinfo.json` (`services/mod_state.py:375`). `remove_mod` and the sync remove only the entry.

**Static files.**

- `web/index.html:5` links `/vite.svg`. `web/public/` has `vintagestory-icon.webp` and `vintagestory-icon@2x.webp`; Safari does not take WebP favicons.
- `_resolve_frontend_file` (`main.py:303`) returns `index.html` for any path that is not a file inside the static root, so `/favicon.ico` answers 200 `text/html`.
- `/assets` is a `StaticFiles` mount (`main.py:328`) without `frontend_security_headers`.

**Description media.** `web/src/lib/mod-description.ts` replaces an `<img>` that is not `https:` or `data:image/` with a "not shown" note (Story 19.3). It has no rule for `<video>`, `<audio>`, `<source srcset>`, `poster`, `background`, inline `url()` or SVG `<image href>`. The CSP has no `media-src`, so `default-src 'self'` blocks media from other hosts (Epic 19 ADR-6).

**Tests without `.env`.** `Settings` refuses to start without `VS_API_KEY_ADMIN` (`config.py:290`). Locally the key comes from `.env` through `.mise.toml`'s `env_file`; CI sets it in `.github/workflows/ci.yml:25`. `api/tests/conftest.py` already sets `VS_DEBUG` and removes two variables before the app is imported.

## ADR-1: The Update Check Fills In a Missing Asset ID

**Status:** Accepted (Matt, 2026-11-20, answer 1: during the update check)

**Decision:**

1. **Where.** `ModUpdateService._check_one` passes the payload's `assetid` to `ModService.fill_asset_id(slug, asset_id)` through the `InstalledModSource` protocol, after a successful lookup that found the mod. Nothing is looked up at start-up.
2. **Only when missing.** The entry is written only when its `asset_id` is 0 and the payload's is positive. A non-zero stored asset ID that differs from the payload's is left alone and logged (`mod_asset_id_differs`).
3. **Under the mod's lock.** `fill_asset_id` takes the mod's lock with `_hold`. A busy mod is skipped without an error and filled in at the next check. The state is saved with its atomic write; a failed save is logged and does not fail the check.
4. **Local mods.** No new field. The `not_in_database` reason is shown as "Local mod: not in the mod database", with no Update button and no ModDB link. Enable, disable and remove are unchanged.

## ADR-2: Static File Serving

**Status:** Accepted (planner; `VSS-koo1` item 1 pulled in by Matt, 2026-11-20, answer 5)

**Decision:**

1. **Icons.** `favicon.ico` (16, 32 and 48 px), `favicon-32.png` and `apple-touch-icon.png` (180 px) are generated once from `vintagestory-icon@2x.webp` and committed to `web/public/`. The command is recorded in Story 24.2. `vite.svg` is removed. No build step is added.
2. **404 for missing files.** `serve_spa` answers 404 (with the security headers) when the path is not a file, its last segment has a file extension, and its first segment is not one of the web UI's route prefixes. The prefixes (`game-server`, `config`, `mods` and the others in `App.tsx`) are kept in one list next to `register_frontend`, with a test that each top-level route of `App.tsx` is in it. Every other path still gets `index.html`, so `/game-server/mods/browse/some.mod` loads the page.
3. **`/assets` headers.** The `/assets` mount sends `frontend_security_headers(settings.csp_mode)`, through a small wrapper around `StaticFiles` that adds the headers to its responses. The CSP itself does not change.

## ADR-3: What Counts as an Unused File

**Status:** Accepted (Matt, 2026-11-20, answer 3: list and Delete, skipped archives included)

**Decision:**

1. **Listed.** From one listing of the mods directory, regular files only:
   - names ending in `.tmp` or `.bak`, ignoring case, except the manager's own `.vsm-tmp` and `.vsm-bak` (reason `leftover`);
   - `.zip` and `.zip.disabled` archives with no entry whose `modinfo.json` cannot be read (reason `unreadable`);
   - `.zip` and `.zip.disabled` archives with no entry whose mod ID is installed under another file (reason `duplicate_mod_id`, naming that file).

   Each item has its name, size, modified time and reason.
2. **Never listed.** Folders, `.cs` files, any other name (the game may load it), any name a mod entry uses, and the manager's `.vsm-*` files.
3. **One set of rules.** The sync's skip rules move into one function that `sync_state_with_disk` and the listing both use, so a file the sync skips is always listed, and the reverse. The sync's behaviour and log events do not change.
4. **Only `.zip` mods are imported.** `.cs` files and folders are left alone and documented in the README (`VSS-v3be`'s first question).
5. **Deleting.** `DELETE /mods/unused-files/{name}` recomputes the listing for the request and deletes only a name in it. Anything else is 404, including names with a path separator or `..`. Each delete is logged with the name and reason.
6. **No new state.** The listing is computed on request. Nothing is stored.

## ADR-4: Rescan and Delete Share One Busy Rule

**Status:** Accepted (Matt, 2026-11-20, answer 2: a Rescan button). Amends Epic 19 ADR-10 decision 1.

**Decision:**

1. **The rescan.** `POST /mods/rescan` (Admin) runs `sync_state_with_disk` and returns its summary (added, removed, skipped). Start-up recovery of the manager's working files (Epic 19 ADR-9) stays start-up only.
2. **Refused while busy.** A rescan or a delete is refused with 409 `MODS_BUSY` while `ModService._busy` is not empty, update all runs or an update check runs.
3. **And the reverse.** While a rescan or delete runs, an install, a version change, update all and the check refuse with 409 `MODS_BUSY`. A flag on `ModService` is set for the rescan or delete, which is synchronous after the check, so enable, disable and remove cannot interleave with it.
4. **Epic 19 ADR-10 decision 1** ("called once, in the API's start-up ... not from a route") gains a note pointing here. `sync_mod_state_at_startup`'s docstring is amended to name the rescan as the one other caller.
5. **Restart required.** While the game server runs, a rescan that added or removed an entry, or the delete of a skipped archive, sets "Restart required". Deleting a `leftover` file does not.

## ADR-5: Mod File Follow-ups from Epic 19

**Status:** Accepted (planner)

**Decision:**

1. **Missing file on a version change.** `change_version` runs the missing-file check enable and disable use, after `ModNotFoundError` and before `_prepare_version_change`, so no lookup or download happens. The router maps it to 409 `MOD_FILE_MISSING`.
2. **Every cached file type.** `CacheEvictionService` counts and evicts every regular file in a file-ID directory under `mods/`, not only `*.zip` and `*.cs`. An emptied directory is removed, as now.
3. **The modinfo cache follows the entries.** When the last entry of a mod ID is removed, by the sync or by `ModService.remove_mod`, `state/mods/<slug>/` is removed. A failure is logged and never fails the removal. A version change keeps the old version's directory, as now.
4. **`VSS-3tb1` item 2** (the second archive left by an interrupted rename) is not given its own recovery rule. ADR-3 lists it as `duplicate_mod_id`, and the admin deletes it.

## ADR-6: Installed Filters

**Status:** Accepted (Matt, 2026-11-20, answer 4: in the URL)

**Decision:**

1. **One filtered row model.** The filters are TanStack Table column filters on `ModTable`'s existing table instance. The cards render the same filtered, sorted rows, so both layouts agree.
2. **URL parameters.** `q` (text), `compat` (`compatible`, `not_verified` or `incompatible`) and `updates=1`, read and written with `useSearchParams` as `BrowseTab` does. Sorting stays in preferences.
3. **History.** Typing in the search box replaces the history entry. Changing the select or the toggle pushes one. Invalid values are ignored and dropped from the URL on the next change.
4. **Loading compatibility.** A row whose compatibility has not loaded matches only "All", so it never appears under "Not verified" by mistake.
5. **Update all is not filtered.** "Update all" and its count cover every installed mod, whatever the filters show.
6. **Name match.** The search matches the mod's name or mod ID, any part of it, ignoring case.

## ADR-7: Description Media Gets a Note

**Status:** Accepted (planner; `VSS-koo1` item 2 pulled in by Matt, 2026-11-20, answer 5)

**Decision:**

1. **Replaced with a note.** `<video>`, `<audio>`, a `<picture>` whose `<source>` has a `srcset` from another host, and SVG `<image>` with an `href` from another host are replaced with Story 19.3's "not shown" note, naming the kind of media.
2. **Removed without a note.** The `poster` and `background` attributes, and `url()` declarations in inline styles, which only load media.
3. **The CSP is not widened.** No `media-src` is added. Epic 19 ADR-6's policy stays as it is.

## ADR-8: Tests Never Touch the Dev Stack's Mods Directory

**Status:** Accepted (planner, as Epic 23 ADR-9)

**Decision:**

1. API tests use `tmp_path` for the mods, state and cache directories.
2. `api/tests/conftest.py` sets a placeholder `VS_API_KEY_ADMIN` with `os.environ.setdefault` before the app is imported, so the tests run without `.env`, and a value from `.env` or CI still wins (Story 24.1).
3. The E2E checks of Stories 24.6 and 24.7 create and delete their own files with `docker exec`, only in the CI set's throwaway container, never on the dev stack.
