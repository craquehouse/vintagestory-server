# Epic 17: Mod Data Correctness and Fixes - Architecture Decisions

Decisions from the Epic 17 course correction (2026-11-15). Epic 17 has no preparation story, so each decision was checked by reading the code at commit `ebca566` (`v0.1.0-rc.3` plus lock file maintenance); file and line references are to that commit. Nothing here was run against a live mod database or server; where a story has to confirm something first, the ADR says so.

Stories 17.7 and 17.8 need no decision: they follow Epic 16 ADR-1 (browse state in the URL) and ADR-3 (1280px settings panel) and the UX spec's tablet rules.

## ADR-1: Mod Database Data Is Normalized Once, Where It Enters

**Status:** Accepted (Epic 17 planning). Implemented by Story 17.1.

**Context:**

- The mod database returns `null` for fields that are usually set. For `canjewelry`, three of 179 releases have `"fileid": null`, and the entry's top-level `tags` contains a `null` element (`VSS-a0r`).
- `dict.get(key, default)` returns the default only when the key is missing. A key that is present with `null` returns `None`.
- `ModService.lookup_mod` builds its response with that pattern (`services/mods.py:589-626`). `file_id=r.get("fileid", 0)` (`:593`) passes `None` to `ModRelease.file_id: int` (`models/mods.py:173`), pydantic rejects it, and the whole lookup returns 500. One such release makes the mod impossible to open.
- The same pattern, or a conversion that fails on `None`, is used wherever raw mod database dictionaries are read:

  | Place | Code | What a null does |
  |---|---|---|
  | `services/mods.py:582` | `sum(r.get("downloads", 0) ...)` | `TypeError`, lookup 500 |
  | `services/mods.py:591-596` | `version`, `filename`, `downloads`, `game_versions`, `created` of each release | `ModRelease` validation error, lookup 500 |
  | `services/mods.py:611-613`, `:617`, `:622` | `int(mod.get("assetid", 0))`, `name`, `author`, `follows`, `tags` | `TypeError` or `ModLookupResponse` validation error (a `null` inside `tags` fails `list[str]`), lookup 500 |
  | `routers/mods.py:212-222` | `_api_mod_to_browse_item`: `int(mod.get("assetid", 0))`, `downloads`, `follows`, `trendingpoints`, `tags` | `TypeError` or validation error; one bad listing item fails the whole browse page |
  | `routers/mods.py:356`, `:527` | `for t in m.get("tags", [])` with `t.lower()` | `TypeError` on null `tags`, `AttributeError` on a null element; tag filter and tag list 500 |
  | `services/mod_api.py:751`, `:756` | sort keys `int(m.get("downloads", 0))`, `trendingpoints` | `TypeError`; the downloads and trending sorts fail |
  | `services/mod_api.py:839` | `for tag in mod.get("tags", [])` in search | `TypeError` on null `tags` |
  | `services/mod_api.py:396`, `:402` | `release["fileid"]`, `int(mod.get("assetid", 0))` in `download_mod` | a null file ID is sent to the download endpoint as `fileid=None` |

  Only the `canjewelry` nulls (release `fileid`, an element of top-level `tags`) are confirmed. The rest are what the code does if the field is null; they have not been seen in mod database data.
- Some code is already null-safe, each in its own way: `StoredRelease.from_api` (`models/mod_updates.py:51-78`, `data.get(k) or default`, used by update checks and version changes), `supported_game_versions` (`services/mod_compatibility.py:62-67`), `_name_sort_key` (`services/mod_api.py:772-775`) and `_compatibility_modid` (`services/mods.py:483-490`).
- Mod database payloads enter the API at three points in `ModApiClient` (`services/mod_api.py`): `get_mod` (returns `data["mod"]`, `:312`), `get_all_mods` (stores `data.get("mods", [])` in the browse cache, `:516-517`) and `get_mods_by_version` (`:602`).

**Decision:**

1. **One normalization boundary.** Two functions, one for a mod entry and one for a release, turn a raw mod database dictionary into one with every known field present and correctly typed. `ModApiClient` applies them at the three entry points above, so the browse cache and every caller hold normalized data.
2. **Rules:**
   - A missing key, a `null`, or a value of the wrong type becomes the field's default: `""` for text, `0` for counts and `assetid`, `[]` for lists, `None` for fields the models already declare optional (`changelog`, `text`, `urlalias`, `logofilename`, `homepageurl`, `sourcecodeurl`, `created` and `lastreleased` of the entry).
   - List fields (`tags`, `modidstrs`, `releases`) drop elements that are `null` or of the wrong type.
   - A release's `fileid` is the exception: `null` stays `None`. It means the release has no downloadable file, and a default of `0` would hide that.
   - A mod entry or listing item that is not an object is dropped from a list, and is an `ExternalApiError` for a single lookup, as today.
3. **Models.** `ModRelease.file_id` becomes `int | None` (`models/mods.py:173`) and `fileId: number | null` in `web/src/api/types.ts:156`. Nothing in the web reads the field today.
4. **Call sites stop defending themselves.** After the boundary exists, the `.get(key, default)` calls in the table read the normalized value directly. `StoredRelease.from_api` uses the same release normalizer, so there is one definition of a clean release. It keeps `fileid: int = 0` for the stored file format; ADR-2 covers what happens to a release without a file.
5. **Rejected: `r.get(key) or default` at each call site.** There are more than forty such reads across three files. Fixing them one by one leaves the next new read unprotected, which is how the existing null-safe code and the unsafe code came to sit side by side.

**Consequences:**

- A null in mod database data can no longer fail a lookup, a browse page, a sort, the tag list or an update check.
- Story 17.1 adds a fixture with a null in every field the normalizers know, plus the `canjewelry` shape (null `fileid` on a release, null inside top-level `tags`), and tests lookup, browse, each sort, the tag list and the update check against it.
- A release with `file_id: null` is listed on the detail page. Whether it can be installed is ADR-2's rule.

## ADR-2: Release Selection for Install

**Status:** Accepted (Epic 17 planning). Implemented by Story 17.2. Extends Epic 14 ADR-1 (release order, pre-release definition) to a first install, and replaces the default in Epic 16 ADR-2 decision 2.

**Context:**

- `ModApiClient.download_mod` picks `releases[0]` when no version is given, and otherwise the first release whose `modversion` matches, across every mod ID in the entry (`services/mod_api.py:383-392`). For the `instruments` entry, `releases[0]` belongs to `vsinstrumentsbase` (`VSS-jhf`; fixture `api/tests/fixtures/moddb/mod_instruments.json`). For `carryon`, `releases[0]` is `2.0.0-rc.1` (`VSS-43b`; fixture `mod_carryon.json`).
- The web UI always names a version, so fixing only the "no version" path would change nothing an admin sees:
  - The detail page's install section preselects `latestVersion` (`ModDetailPage.tsx:186`), which is `releases[0].modversion` (`services/mods.py:536-537`). Its dropdown lists the releases of every mod ID and labels index 0 "(Latest)" (`ModDetailPage.tsx:204-212`).
  - The browse card's install sends `latestVersion` from the mod's details, or the literal string `'latest'` when details have not loaded (`ModCard.tsx:33`, `:234`).
- A version change already restricts itself to the installed mod ID (`services/mods.py:1005`), and Epic 14 ADR-1 defines a pre-release as a `modversion` containing `-` (`is_prerelease`, `services/mod_updates.py:45-47`) and "newer" as earlier in the release list, never by comparing version strings.
- `_compatibility_modid` falls back to `releases[0].modidstr`, documented as "the release the install flow installs" (`services/mods.py:472-492`).

**Decision:**

1. **Install mod ID.** The mod ID being installed is the requested slug (after `extract_slug`), compared exactly with `modidstr`. If no release in the entry carries that mod ID, it is the mod ID of the entry's newest release (today's behavior), so an entry reached by some other key stays installable.
2. **Candidates** are the releases with the install mod ID that have a file ID (ADR-1: `fileid` not null).
3. **No version named:** the first stable candidate in list order (`not is_prerelease(modversion)`). If the mod ID has no stable candidate, the first candidate. List order decides, as in Epic 14 ADR-1; `parse_base_version` is not needed because no versions are compared. Compatibility with the installed game does not change the choice: the install dialog already warns about it.
4. **Version named:** the candidate with that `modversion`, pre-release or not; otherwise 404 `MOD_VERSION_NOT_FOUND`. A named release of the install mod ID that has no file ID is refused with an error that says so, and nothing is requested from the download endpoint.
5. **One function** implements rules 1-4 and is used by both install and lookup, so the UI cannot label one release and install another.
6. **Lookup response.** `latest_version` becomes the version rule 3 selects for the lookup's install mod ID. The response gains `install_mod_id` (`installModId` in the web types). `_compatibility_modid` uses the install mod ID as its default instead of `releases[0].modidstr`.
7. **Web.** The install section lists only the install mod ID's releases, preselects `latestVersion`, and puts "(Latest)" on the release with that version (both dropdowns, `ModDetailPage.tsx:211` and `:380`). An install with no chosen version sends no version; the `'latest'` string is not sent as a version name.

**Consequences:**

- Installing `instruments` installs an `instruments` release; installing `carryon` installs its newest stable release, and `2.0.0-rc.1` is still installable by choosing it.
- "(Latest)" can sit below a newer pre-release in the list. That is intended: it marks what a plain install picks.
- Tests use the existing `mod_instruments.json` and `mod_carryon.json` fixtures; a mod ID with only pre-releases needs a synthetic one.
- Story 17.3 touches the same install path; 17.2 lands first.

## ADR-3: One Operation Lock per Mod

**Status:** Accepted (Epic 17 planning). Implemented by Story 17.3. Extends the last sentence of Epic 14 ADR-2 ("Changes are serialized per mod; a concurrent request for the same mod returns 409") from version changes to every operation that changes a mod.

**Context:**

- `ModService` keeps `_version_locks: dict[str, asyncio.Lock]` (`services/mods.py:308`). Only `change_version` uses it: it raises `ModVersionChangeInProgressError` when the lock is held (`:844-846`), which the router returns as 409 `MOD_VERSION_CHANGE_IN_PROGRESS` (`routers/mods.py:998-999`).
- `enable_mod`, `disable_mod` and `remove_mod` are synchronous methods (`services/mods.py:638`, `:688`, `:738`) called from `async` handlers (`routers/mods.py:758`, `:824`, `:890`). Each runs to completion on the event loop, so they cannot interleave with each other. They can run while another operation is suspended at an `await`.
- `change_version` reads the mod's state (`:848`), then awaits the mod database lookup and the archive download in `_prepare_version_change` (`:994`, `:1027`), then swaps files and state in `_apply_version_change`. A remove that runs during the download deletes the file and the state entry; the version change then places the new archive, writes a new state entry for the removed mod, and fails deleting the old file (`:930-936`), which triggers a rollback to state for a file that no longer exists.
- `install_mod` checks "already installed" (`:1101-1106`) and then awaits the download (`:1110`). Two installs of the same mod both pass the check.
- Update All calls `change_version` once per mod and records `ModVersionChangeInProgressError` as a failed item (`services/mod_updates.py:368`, `:385-393`).
- `ModService` is one in-process singleton (`services/mods.py:61`, `:75-117`), so an `asyncio.Lock` table covers every request.

**Decision:**

1. **One lock table,** keyed by mod ID, replaces `_version_locks`. Install, enable, disable, remove and version change all respect it.
2. **No waiting.** If the lock for that mod is held, the operation raises `ModOperationInProgressError` and changes nothing. The router returns 409 with code `MOD_OPERATION_IN_PROGRESS` for all five operations. `ModVersionChangeInProgressError` and `MOD_VERSION_CHANGE_IN_PROGRESS` are removed; the web does not branch on that code today.
3. **Who holds it.** `change_version` and `install_mod` hold the lock for their whole run, because they await. `enable_mod`, `disable_mod` and `remove_mod` stay synchronous: they refuse when the lock is held and otherwise run without taking it, since nothing can interleave with a synchronous method on the event loop. If one of them ever gains an `await` or is moved to a thread pool, it must hold the lock.
4. **Install key.** Install locks the install mod ID from ADR-2. If the archive's `modinfo.json` names a different mod ID, install also checks that mod's lock and its installed state before saving, and fails with the file removed if either is taken.
5. **Update All** is unchanged apart from the error type: a mod that is busy is reported as failed and the run continues.
6. **Different mods do not block each other.** There is no global lock.

**Consequences:**

- A remove, enable or disable during a version change or install of the same mod gets 409 instead of acting on a file that is about to change.
- Two concurrent installs of the same mod: one proceeds, the other gets 409.
- The 409 code for a busy version change is renamed. The API is `v1alpha1`; the change is noted in the story.
- Tests hold the lock with a blocked download and call each of the other four operations.

**Related, same story:** `ModStateManager.read_modinfo` lowercases top-level `modinfo.json` keys (`services/mod_state.py:259`) and `import_mod` validates the raw dictionary (`:214`), so an archive with `ModID`/`Version` passes version-change validation and then imports with filename fallback metadata (`VSS-0jl`). The key normalization moves into one place, used by both (`_extract_modinfo_from_zip` or a helper beside it). No separate decision is needed.

## ADR-4: Secrets in Config Responses Depend on the Role

**Status:** Accepted (Epic 17 planning). Implemented by Story 17.5.

**Context:**

- `GET /config/game` needs only an authenticated key (`RequireAuth`, `routers/config.py:99-101`) and returns the value of every managed setting, including `Password` (`services/game_config.py:119-126`, values read at `:463`).
- `GET /config/files/{filename}` is also `RequireAuth` (`routers/config.py:442-457`) and returns the parsed JSON of any JSON file under the server data directory (`services/config_files.py:171`), including `serverconfig.json` with its `Password`.
- The PRD gives Monitor read access to configuration (FR21, FR22) and limits Monitor to non-sensitive data (FR32). Both handlers receive the role from `get_current_user` and discard it.
- The API already has a redaction pattern: `ApiSettings.redacted()` replaces the webhook URL with `mod_update_webhook_configured` (`services/api_settings.py:76-83`, FR149).
- Story 16.8 masked the Password field in the web UI; the value is still in the response.

**Decision:** Redact; do not restrict.

1. **Secret settings are declared, not special-cased.** `ServerSetting` gains a `secret` flag, set on `Password`. Each setting in the `GET /config/game` response carries `secret: true` when it applies.
2. **`GET /config/game` for a non-Admin role:** a secret setting has `value: null` and `configured: true` or `false`. Admin responses are unchanged apart from the `secret` flag.
3. **`GET /config/files/...` for a non-Admin role:** when the resolved path is the game's `serverconfig.json` (compared as resolved paths, not as the requested string), each secret setting's top-level key with a non-null value is replaced by the string `"[redacted]"`. A null stays null.
4. **Redacted is the default.** The service methods return the redacted form unless the caller passes the Admin role, so a new caller cannot leak by omission.
5. **Web.** For a secret setting without a value in the response, the settings page shows "Set" or "Not set" instead of a masked field. Monitor cannot edit settings today; that is unchanged.
6. **Rejected: making both endpoints Admin-only.** It removes FR21 and FR22 from Monitor to protect one field.

**Consequences:**

- A Monitor key can no longer read the game server password from either endpoint.
- Tests cover both endpoints for both roles, including `./serverconfig.json` and a subdirectory path that resolves to the same file.
- **Known limits, not solved here:** other files the viewer can open may hold secrets (for example a mod's own config file, or a copy of `serverconfig.json` under another name). Story 17.5 checks a server-generated `serverconfig.json` for secret fields other than `Password` and adds any to the list; anything beyond that is a follow-up.

## ADR-5: Interval Settings Drive Their Jobs

**Status:** Accepted (Epic 17 planning). Implemented by Story 17.6. Completes the Epic 7 TODO.

**Context:**

- `ApiSettingsService.update_setting` calls `scheduler_callback(key, value)` for `mod_list_refresh_interval`, `server_versions_refresh_interval` and `metrics_collection_interval` (`services/api_settings.py:273-280`), but `get_api_settings_service` never passes a callback (`routers/config.py:226-249`). Its TODO names `scheduler.reschedule_job`, which `SchedulerService` does not have.
- `SchedulerService` has `add_interval_job`, which replaces a job with the same ID (`replace_existing: True`, `services/scheduler.py:102-138`), and `remove_job`, which raises `JobLookupError` when the job does not exist (`:193-202`).
- Which job belongs to which setting, and that an interval of 0 means "not registered", is written inline in `register_default_jobs` (`jobs/__init__.py:35-106`): `mod_cache_refresh`, `server_versions_check` (registered with `run_immediately=True`) and `metrics_collection`.

**Decision:**

1. **One function per rule.** `jobs/__init__.py` gets a function that applies one interval setting to the scheduler: a value above 0 calls `add_interval_job` for that setting's job (adding it or replacing its interval); 0 removes the job if it is registered and does nothing otherwise.
2. `register_default_jobs` uses it at startup, and `get_api_settings_service` passes it as `scheduler_callback`, so startup and a settings change cannot disagree.
3. **A changed interval restarts the countdown** from the time of the change. A settings change does not run the job immediately; `run_immediately` stays a startup-only behavior of `server_versions_check`.
4. All three interval settings are covered, since they share the callback. `VSS-8bl` names two; `metrics_collection_interval` has the same defect.
5. The setting is saved before the callback runs (`services/api_settings.py:267`). If the callback fails, the request reports the failure and the saved value still applies at the next start.

**Consequences:**

- Changing a refresh interval takes effect without restarting the API, including to and from 0.
- Tests cover each transition for each setting: changed, to 0, from 0, and 0 to 0.
