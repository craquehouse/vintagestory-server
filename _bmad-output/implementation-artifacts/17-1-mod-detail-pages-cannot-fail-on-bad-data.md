# Story 17.1: Mod Detail Pages Cannot Fail on Bad Data

Status: ready-for-dev

<!-- Implements FR177-FR178 and Epic 17 ADR-1. Beads: VSS-a0r (P1, production bug on v0.1.0-rc.3), VSS-fv7. Epic 17's first story; v0.1.0-rc.4 is expected right after it. Branch from docs/epic-17-mod-data-fixes (1f87ced, the Epic 17 planning commits). Not in scope: Story 17.2 (release selection, refusing a release without a file, "(Latest)", install_mod_id), 17.4 (browse mod_ids), 17.7 (Mods tabs, page clamp). No new dependencies. -->

## Story

As an **administrator**,
I want **every mod in the browser to open, whatever the mod database returns for it**,
so that **one odd release does not hide a mod I want to install**.

## Acceptance Criteria

1. **Given** a mod whose releases include ones with `"fileid": null` (`canjewelry`: releases `0.2.20`, `0.1.26` and `0.2.0`), some with `"changelog": null`, and a top-level `tags` of `["Utility", "Cosmetics", "Crafting", null]`
   **When** I request `GET /api/v1alpha1/mods/lookup/canjewelry`
   **Then** the response is 200, every release of the entry is listed in the mod database's order, those three releases have `file_id: null` and every other release keeps its file ID, the null changelogs are `null`, and `tags` is `["Utility", "Cosmetics", "Crafting"]`
   *(Covers FR177; `VSS-a0r`)*

2. **Given** a mod database entry or listing item with `null` in every field the API reads (entry and release), a `null` element inside `tags` or `modidstrs`, or a listing whose `mods` array holds an element that is not an object
   **When** I look the mod up, browse with each sort (`recent`, `downloads`, `trending`, `name`), search, filter by side, type or tag, list tags, or run an update check
   **Then** each request succeeds; each field has its default (ADR-1 rules, Dev Notes table); null and non-string list elements are dropped; a listing element that is not an object is left out and the rest of the page is returned
   *(Covers FR177)*

3. **Given** mod database data entering the API
   **When** it is read by lookup, browse, search, sort, the tag list, install, version change or the update check
   **Then** it has passed through one normalization step applied by `ModApiClient` at its three entry points (`get_mod`, `get_all_mods`, `get_mods_by_version`); the call sites listed in ADR-1's table read the normalized value instead of `.get(key, default)`; `StoredRelease.from_api` uses the same release normalizer; `ModRelease.file_id` is `int | None` and the web type `fileId` is `number | null`
   *(Covers FR177; Epic 17 ADR-1 decisions 1-4)*

4. **Given** mod database data with no nulls (the existing `mod_carryon.json`, `mod_instruments.json`, `mod_egocaribautomapmarkers.json` and `mod_playercorpse.json` fixtures and the existing browse samples)
   **When** it is looked up, browsed, installed or update-checked
   **Then** the results are unchanged: every existing test passes, apart from the deliberate changes listed in Dev Notes "Existing tests that change"

5. **Given** a mod detail page that fails to load: the lookup fails (API error or unknown mod), the response has no mod ("Mod not found"), or the mod is incomplete ("The server returned incomplete mod details")
   **When** the error is shown
   **Then** a Back to Browse button above the error goes to the same target as the loaded page's button: `BROWSE_PATH` plus `state.browseSearch` when the page was opened from the browser, the default browser otherwise, always with `MOD_DETAIL_RETURN_STATE` (Epic 16 ADR-1)
   *(Covers FR178; `VSS-fv7`)*

## Tasks / Subtasks

<!-- Each functional task includes its tests in the same commit. Commit per task: type(story-17.1/task-N): ... ; feat/fix only for user-visible changes, subject written for users. Red first. -->

- [ ] Task 1: Mod and release normalizers + tests (AC: 2, 3)
  - [ ] 1.1: Create `api/src/vintagestory_api/models/moddb.py` (no imports from `services/`): move the `ModDict` and `ReleaseDict` aliases here (`services/mod_api.py:29-30` re-imports them so existing imports keep working); add the field tables `MOD_FIELDS` and `RELEASE_FIELDS` (Dev Notes "Normalization rules") and `normalize_mod(raw: object) -> ModDict | None`, `normalize_release(raw: object) -> ReleaseDict | None` and `normalize_mod_list(raw: object) -> list[ModDict] | None`. Each returns a new dict (never mutates its input), keeps unknown keys unchanged, and is idempotent
  - [ ] 1.2: Add `api/tests/fixtures/moddb/mod_canjewelry.json` (real data, trimmed; Dev Notes "canjewelry fixture") and its row in `api/tests/fixtures/moddb/README.md`
  - [ ] 1.3: In `agentdocs/vintagestory-modapi.md`, note under the Release Object table that `fileid` can be `null` (with `filename` and `mainfile` `""`) and `changelog` can be `null`, and under the mod object that `tags` can contain `null` (`canjewelry`, 2026-11-15)
  - [ ] 1.4: Tests in `api/tests/test_moddb_normalize.py`: each rule in the table for null, missing and wrong-type values (a `bool` is not an int); `fileid` null, missing or wrong type → `None`, an int kept; a string `tags` → one tag; null and non-string list elements dropped; non-object releases dropped; a non-object entry → `None`; `normalize_mod_list` of a non-list → `None`, non-object items dropped; unknown keys kept; input not mutated; idempotent; every release of `mod_canjewelry.json` and the four existing fixtures normalizes without changing a value that was already valid (compare field by field)

- [ ] Task 2: Lookup lists every release, with `file_id: null` for a release without a file + tests (AC: 1, 2, 3, 4)
  - [ ] 2.1: `ModApiClient.get_mod` (`services/mod_api.py:309-312`): return `normalize_mod(data.get("mod"))`; when it is `None` (the `mod` key missing or not an object) raise `ExternalApiError("VintageStory mod API returned an unexpected response")`, logged like the other unexpected bodies
  - [ ] 2.2: `ModRelease.file_id: int | None` (`models/mods.py:173`, docstring: `None` when the release has no downloadable file); `ModRelease.fileId: number | null` in `web/src/api/types.ts:156`
  - [ ] 2.3: `ModService.lookup_mod` (`services/mods.py:532-626`): read the normalized values directly (Dev Notes "Call sites"); keep the display fallbacks for empty text; `file_id=r["fileid"]`. `ModApiClient.download_mod` (`services/mod_api.py:378-402`): `mod["releases"]`, `release["modversion"]`, `mod["assetid"]`; no change to which release it picks or to a release without a file (Story 17.2)
  - [ ] 2.4: Tests: `tests/test_mod_api.py` (`TestModApiClientGetMod`): canjewelry → normalized dict with `fileid` `None` on the three releases; `{"statuscode": "200"}` and `"mod": [1, 2]` → `ExternalApiError`. `tests/test_mod_service.py` (`TestModServiceLookupMod`) and `tests/test_mods_router.py` (`TestLookupModEndpoint`), respx on `https://mods.vintagestory.at/api/mod/canjewelry` with the fixture: 200, `len(releases)` equals the fixture's, `file_id` `None` for exactly `0.2.20`, `0.1.26`, `0.2.0`, `changelog` `None` for `0.3.7`, `tags` without the null (red first: today 500). The all-null entry (Dev Notes "Synthetic null payloads") looks up with 200 and the documented defaults. `tests/test_mod_models.py`: `ModRelease(file_id=None, ...)` validates and dumps `file_id: null`

- [ ] Task 3: Browse, search, sort, tags and the update check read normalized data + tests (AC: 2, 3, 4)
  - [ ] 3.1: `get_all_mods` (`services/mod_api.py:515-519`) and `get_mods_by_version` (`:601-608`): `normalize_mod_list(data.get("mods"))`; `None` (`mods` missing, null or not a list) raises `ExternalApiError` and is not cached. `_get_downloads`, `_get_trending`, `_get_recent` and `search_mods` (`:749-844`) read normalized values (`mod["summary"] or ""` and `mod["lastreleased"] or ""` stay: those fields are optional)
  - [ ] 3.2: `routers/mods.py`: `_api_mod_to_browse_item` (`:175-224`) reads normalized values; replace the side and type narrowing (`:196-207`, two `# type: ignore[assignment]`) with module-level helpers `_browse_side(mod)` and `_browse_type(mod)` that look the lowercased value up in a `dict[str, Literal[...]]` and fall back to `"both"` / `"mod"`, so both ignores are removed with no `cast`; the side and type filters (`:336-346`) use the same helpers, so a filter and a card always agree (a mod whose side is empty or unknown shows as `both` and now also matches `?side=both`; the same for type and `mod`). The tag filter (`:356`) and the tag list (`:527`) iterate `m["tags"]`
  - [ ] 3.3: `StoredRelease.from_api` (`models/mod_updates.py:51-78`): `normalize_release(release)`, `TypeError` when it is `None`, then `_clean_text` on the text fields and on each tag as today (`created` becomes the normalized string, `""` when missing, instead of `None`); `fileid=0` when the normalized `fileid` is `None` (the stored format keeps `fileid: int = 0`, ADR-1 decision 4). `_record_from_payload` (`services/mod_updates.py:506-522`, parameter typed `ModDict | None` like `get_mod`'s result) and `ModService._prepare_version_change` (`services/mods.py:997-1003`) read `["releases"]` from the normalized mod and drop their now-unreachable `isinstance(..., list)` checks and the `try/except (TypeError, ValueError)` around them; update the comment in `_check_one` (`services/mod_updates.py:490-492`) for what `get_mod` now raises
  - [ ] 3.4: Tests: `tests/test_mods_router.py`: browse with a listing that contains the all-null listing item, an item with `"tags": ["QoL", null]` and `"modidstrs": [null, "qolmod"]`, a `null` element and a string element: 200 for each `sort`, the null item has the defaults (`side` `"both"`, `mod_type` `"mod"`, counts 0, `tags` `[]`), the non-object elements are not counted in `total_items`; `?side=both` and `?mod_type=mod` include the all-null item, matching its card; `?tags=qol` returns that item with `tags` `["QoL"]` and slug `qolmod`; `?search=<term>` over the same listing returns the matching mod and does not fail on the null item; `GET /mods/tags` succeeds without a `null` entry; `"mods": null` → 502. `tests/test_mod_updates.py`: an update check with `mod_canjewelry.json` stores 9 releases with `fileid` 0 for the three null releases and reports no failure, and one with the all-null entry succeeds too; the existing tests in "Existing tests that change" are updated as described; unit tests of `sort_mods`/`search_mods` normalize their inputs

- [ ] Task 4: Back to Browse on the mod detail error state + tests (AC: 5)
  - [ ] 4.1: `web/src/features/mods/ModDetailPage.tsx`: extract the loaded page's Back to Browse button (`:515-524`) into a `BackToBrowseButton({ onClick })` component (same ghost `sm` button, `ArrowLeft` icon, text "Back to Browse", `data-testid="mod-detail-back"`); render it in the loaded page and above the card in `ModDetailError` (`:135-147`, gains an `onBack` prop). The three error branches (`:474-498`) pass `handleBack`, so the error state reuses `browseTarget` and `MOD_DETAIL_RETURN_STATE`; nothing is recomputed. Update the header doc comment (Story 17.1 note)
  - [ ] 4.2: Tests in `ModDetailPage.test.tsx` ("Story 17.1: error states lead back to the browser"), for each of the three states (a failed fetch, `{ status: 'ok' }` with no `data`, `{ status: 'ok', data: {} }`): opened with `state: { browseSearch }` (reuse the Story 16.1 block's search string and `BrowseLanding`), `mod-detail-back` is shown and clicking it lands on `landing-search` = that search with `landing-from-detail` `true`; opened directly, it lands on the default browser (empty search) with `landing-from-detail` `true`. Existing tests pass unchanged

- [ ] Task 5: E2E and browser verification against the Docker dev stack (AC: 1, 5)
  - [ ] 5.1: Add `web/e2e/mod-detail-bad-data.spec.ts` (Playwright, Docker stack, live mod database; set `localStorage.apiKey` with an init script as in `e2e/mod-browse-state.spec.ts`). Test 1: open `/game-server/mods/browse/canjewelry`; wait for the `/mods/lookup/canjewelry` response: status 200, `mod-detail-page` visible, no `mod-detail-error`; for each release in the response whose `file_id` is `null`, `mod-detail-release-<version>` is listed. Test 2: open `/game-server/mods/browse?q=jewelry&sort=downloads`, wait for the grid, read the first card's slug from its `mod-card-<slug>` test ID, then fulfill only that mod's lookup (`/api/v1alpha1/mods/lookup/<slug>`, query string allowed) with a 500 (`page.route`) and open the card; `mod-detail-error` appears (after React Query's retries, about 7 s; allow 30 s); click `mod-detail-back`, record the URL; `page.unroute`, open the same card again, wait for `mod-detail-page`, click `mod-detail-back`: both URLs are `/game-server/mods/browse?q=jewelry&sort=downloads` and the grid shows cards each time
  - [ ] 5.2: `just docker restart` (rebuild from this branch); run the spec (`cd web && bunx playwright test e2e/mod-detail-bad-data.spec.ts`, admin key from `.env`)
  - [ ] 5.3: Manual check: in the mod browser search "jewelry", open C&N Jewelry: the page loads, the releases list includes v0.2.20, v0.1.26 and v0.2.0, the version dropdown opens; Back to Browse returns to the search. Install nothing, so `./data` is unchanged. Browser console clean. Record results in the Dev Agent Record; screenshots stay outside the repo unless the server name (`header span.font-semibold`) is masked

- [ ] Task 6: Quality gate and review hand-off (AC: all)
  - [ ] 6.1: `just check` (lint, typecheck, all tests) passes; the diff adds no suppression and removes the two at `routers/mods.py:199` and `:207`
  - [ ] 6.2: Story status `review`, `just sprint set 17-1-mod-detail-pages-cannot-fail-on-bad-data review`, PR to `main` (it also carries the two Epic 17 planning commits, 88cfd2d and 1f87ced), PR link on `VSS-a0r` and `VSS-fv7`

## Dev Notes

### The bug (verified on `docs/epic-17-mod-data-fixes` 1f87ced; `api/` and `web/` unchanged since `ebca566`, so ADR-1's line references hold)

- Production, v0.1.0-rc.3, 2026-11-15: `GET /api/v1alpha1/mods/lookup/canjewelry` → 500, `pydantic_core.ValidationError: 1 validation error for ModRelease file_id Input should be a valid integer [input_value=None]`. The detail page shows "Failed to load mod details" with no way back to the browser.
- Cause: `services/mods.py:593` builds each release with `file_id=r.get("fileid", 0)`. `dict.get(key, default)` returns the default only for a missing key; `"fileid": null` passes `None` to `ModRelease.file_id: int` (`models/mods.py:173`).
- Live public data, `https://mods.vintagestory.at/api/mod/canjewelry`, 2026-11-15: 179 releases, all `modidstr` `canjewelry`. Releases `0.2.20`, `0.1.26` and `0.2.0` have `"fileid": null`, `"filename": ""`, `"mainfile": ""` and `"downloads": 0`. Seven releases have `"changelog": null` (for example `0.3.7`). The entry's `tags` is `["Utility", "Cosmetics", "Crafting", null]`. In the listing (`/api/mods`) the same mod's `tags` has no null, and across all 9,610 listing items only `urlalias` and `logo` are ever null; every other null in ADR-1's table is what the code would do, not something seen.
- `ModDetailError` (`ModDetailPage.tsx:135-147`) shows only the message. The loaded page's Back to Browse (`:515-524`) calls `handleBack` (`:462-464`), which navigates to `browseTarget` (`:458`, `BROWSE_PATH` + `readBrowseSearchState(location.state)`) with `MOD_DETAIL_RETURN_STATE` (`lib/browse-search.ts:125`). The three error branches are `:474-480` (query error), `:483-489` ("Mod not found") and `:492-498` (incomplete response).

### Normalization rules (ADR-1 decision 2)

`models/moddb.py` defines one table per object; `normalize_mod` and `normalize_release` produce a dict with every field in the table present and correctly typed:

| Object | Fields | Type kept | Default (missing, `null` or wrong type) |
|---|---|---|---|
| Entry | `modid`, `assetid`, `downloads`, `follows`, `trendingpoints` | `int` (not `bool`) | `0` |
| Entry | `name`, `author`, `side`, `type` | `str` | `""` |
| Entry | `text`, `summary`, `urlalias`, `logofilename`, `logo`, `homepageurl`, `sourcecodeurl`, `created`, `lastreleased` | `str` | `None` |
| Entry | `tags`, `modidstrs` | list of `str` | `[]` |
| Entry | `releases` | list of objects, each through `normalize_release` | `[]` |
| Release | `modversion`, `modidstr`, `filename`, `created` | `str` | `""` |
| Release | `downloads` | `int` (not `bool`) | `0` |
| Release | `changelog` | `str` | `None` |
| Release | `tags` | list of `str` | `[]` |
| Release | `fileid` | `int` (not `bool`) | `None`: no downloadable file (ADR-1's exception) |

- **One table for detail entries and listing items.** A field a payload type does not carry simply gets its default (a listing item gets `releases: []`; a detail entry gets `summary: None`). The `None`-default fields are exactly those the response models already declare optional (`ModLookupResponse`, `ModBrowseItem`, `ModRelease.changelog`).
- **Lists:** elements that are `null` or not a `str` (or, for `releases`, not an object) are dropped. A single `str` where a list of strings is expected becomes a one-element list: this keeps `StoredRelease.from_api`'s tested behavior (`test_string_tags_are_one_tag`) as the one definition for every list of strings.
- **Unknown keys** (`releaseid`, `mainfile`, `comments`, `screenshots`, ...) are copied unchanged; nothing reads them.
- **Not objects:** `normalize_mod`/`normalize_release` return `None` for a non-object. `get_mod` turns that into `ExternalApiError` (today a non-object `mod` is returned as is and fails later in the caller, and a missing `mod` key raises `KeyError`); `normalize_mod_list` drops non-object items and returns `None` when `mods` itself is missing, null or not a list (today a missing key gives `[]` and a null fails later with a `TypeError`), which `get_all_mods`/`get_mods_by_version` raise as `ExternalApiError` (caching `[]` for 5 minutes would hide every mod).
- **Unchanged:** no surrogate cleaning, trimming, case changes or value validation. Surrogates stay `StoredRelease.from_api`'s job (`_clean_text`, Story 14 hardening), because only the stored file needs them.
- **Why `models/moddb.py`:** `StoredRelease.from_api` (in `models/`) must call the release normalizer (ADR-1 decision 4), and nothing in `models/` imports from `services/`. The module has no internal imports; `services/mod_api.py` imports from it.
- **Typing:** pyright is strict. Narrow with `isinstance` and use `cast(dict[str, Any], raw)` after an `isinstance(raw, dict)` check, as `get_mod` does today (`mod_api.py:304-307`). `ModDict`/`ReleaseDict` stay `dict[str, Any]` (a `TypedDict` is not needed for this story).

### Call sites (ADR-1 decision 4)

| Place | Today | After |
|---|---|---|
| `mod_api.py:309-312` `get_mod` | `return data["mod"]` | `normalize_mod(data.get("mod"))`, `ExternalApiError` on `None` |
| `mod_api.py:515-519`, `:601-608` | `data.get("mods", [])` | `normalize_mod_list(...)`, `ExternalApiError` on `None` |
| `mod_api.py:378-402` `download_mod` | `mod.get("releases", [])`, `r.get("modversion")`, `int(mod.get("assetid", 0))` | `mod["releases"]`, `r["modversion"]`, `mod["assetid"]`; selection unchanged |
| `mod_api.py:749-761` sort keys | `int(m.get("downloads", 0))`, `int(m.get("trendingpoints", 0))`, `str(m.get("lastreleased", ""))` | `m["downloads"]`, `m["trendingpoints"]`, `m["lastreleased"] or ""` |
| `mod_api.py:821-841` `search_mods` | `str(mod.get("name", ""))`, `author`, `mod.get("tags", [])` | `mod["name"]`, `mod["author"]`, `mod["summary"] or ""`, `mod["tags"]` |
| `mods.py:532-548` lookup | `mod.get("releases", [])`, `.get("modversion", "unknown")` | `mod["releases"]`, `r["modversion"] or "unknown"` |
| `mods.py:582-626` lookup response | `sum(r.get("downloads", 0) ...)`, release fields, `int(mod.get("assetid", 0))`, `name`, `author`, `follows`, `tags`, optional fields | normalized values; display fallbacks below |
| `routers/mods.py:175-224` browse item | `.get` with defaults, `int(...)`, two `# type: ignore` | normalized values, `_browse_side`/`_browse_type`, no ignore |
| `routers/mods.py:336-358` filters | `str(m.get("side", "both"))`, `m.get("tags", [])` with `t.lower()` | `_browse_side(m)`, `_browse_type(m)`, `m["tags"]` |
| `routers/mods.py:527` tag list | `mod.get("tags", [])` with `tag.lower()` | `mod["tags"]` |
| `models/mod_updates.py:51-78` `from_api` | `data.get(k) or default`, its own list handling | `normalize_release`, then `_clean_text`; `fileid` `None` → `0` |
| `mod_updates.py:516-521`, `mods.py:997-1003` | `isinstance` checks on the payload and its releases | `mod["releases"]` |

- **Display fallbacks stay** (they are presentation, not null handling, and change nothing for valid data): `name` → the slug, `author` → `"Unknown"`, a release `modversion` → `"unknown"` (an empty `SelectItem` value would break the web's Radix Select), `side` → `"Both"` (`mod["side"].title() if mod["side"] else "Both"`). Browse cards keep `""` for name and author, as today. The browse slug falls back to `str(mod["modid"])` when `modidstrs` is empty, and to `"unknown"` when `modid` is also 0, as today.
- **Already null-safe; leave as is:** `_compatibility_modid` (`mods.py:472-492`), `supported_game_versions` (`mod_compatibility.py:50-79`), `_name_sort_key` (`mod_api.py:764-775`, Story 16.8) and `check_compatibility` (`mod_api.py:169-207`; it also receives `{"tags": ...}` built from `StoredRelease`, and `not tags` handles a missing list). Do not churn them.
- **Install of a release without a file is Story 17.2.** After this story the canjewelry dropdown lists `0.2.20`; choosing it reaches `download_release_file` with `fileid=None` and `filename=""`, and `safe_release_filename("")` raises, so the install fails with `DownloadError` ("Unusable release filename") before any download request. Do not add a guard here; ADR-2 decision 4 defines that error.

### canjewelry fixture

Captured from the public API and trimmed like the existing fixtures (README: no descriptions, screenshots or CDN URLs), but keeping `tags` and `changelog`, which are the cases:

```bash
curl -s https://mods.vintagestory.at/api/mod/canjewelry | jq '{statuscode, mod: (.mod | {modid, assetid, name, author, urlalias, side, type, lastreleased, tags, releases: [.releases[] | select(.modversion as $v | ["0.8.2","0.8.1","0.3.7","0.2.22","0.2.20","0.2.19","0.1.26","0.2.0","0.0.1"] | index($v)) | {releaseid, modversion, modidstr, filename, fileid, downloads, tags, created, changelog}]})}' > api/tests/fixtures/moddb/mod_canjewelry.json
```

On 2026-11-15 this gives 9 releases, newest first: `0.8.2`, `0.8.1` (normal), `0.3.7` (`changelog` null), `0.2.22`, `0.2.20` (`fileid` null), `0.2.19`, `0.1.26` (`fileid` null), `0.2.0` (`fileid` null), `0.0.1`, and top-level `tags` `["Utility", "Cosmetics", "Crafting", null]`. List order is not version order (`0.1.26` before `0.2.0`); keep it. If the live entry has changed, keep these nine versions and check the three null `fileid`s and the null tag are still there; if not, stop and report rather than editing the data by hand. README row: "`mod_canjewelry.json` | `canjewelry` | 9 of 179 (captured 2026-11-15, Story 17.1) | `fileid` null on three releases (with `filename` `""`); `changelog` null; a `null` in the entry's `tags`".

### Synthetic null payloads (tests only, not in `fixtures/moddb/`)

`fixtures/moddb/` holds only captured data. Build the all-null payloads in the tests from the field tables, so a field added to a table is covered automatically: `{field: None for field in MOD_FIELDS}` with `releases` set to one `{field: None for field in RELEASE_FIELDS}` (a lookup needs at least one release, otherwise it is 404 as today) and `tags` `[None, "Utility"]`. For browse, the same all-null dict is the listing item (`modidstrs` `null` falls back to the slug `"unknown"`).

### Existing tests that change (deliberately)

- `tests/test_mod_updates.py` `MALFORMED_PAYLOADS` (`:433-442`) and `test_malformed_payload_fails_that_mod_only`: under ADR-1 a wrong type becomes the default and a non-object release is dropped, so four cases now succeed: `"fileid": "abc"` (stored `fileid` 0), `"releases": ["oops"]` and `"releases": {"a": 1}` (no releases), `"created": {"x": 1}` (`created` `""`). Keep `"mod": [1, 2]` (and `test_payload_rejected_inside_get_mod_fails_that_mod_only`) as failures; move the four into a new parametrized test that the check succeeds and stores the normalized record.
- `tests/test_mod_api.py` `TestSortMods`/`TestSearchMods` and `tests/test_edge_cases.py:76`, `:81` call `sort_mods`, `search_mods` and `_api_mod_to_browse_item` with partial dicts. These functions now take normalized data (the router always passes it); wrap the inputs in `normalize_mod` and keep every assertion. `test_sort_handles_missing_values` then tests that normalization gives a missing count 0.
- Anything else that fails is a regression (AC 4): fix the code, not the test.

### Out of scope

- Story 17.2: which release install picks, refusing a release without a file, "(Latest)", `install_mod_id`, `latest_version`'s meaning.
- Story 17.4 (`mod_ids` on browse items), Story 17.7 (Mods tabs on a detail page, page clamp).
- Values that are present and of the right type but unexpected (for example a `side` the lookup's `Literal` does not allow); ADR-1 covers nulls and types only.
- The loading skeleton (no back button needed; it resolves to the page or an error).

### Testing Requirements

**CRITICAL:** Tests are written with each task and committed with it, red first. `just test-api <file>` / `just test-web <file>` after each task; `just check` before review.

- API: lookup and browse tests use respx on `https://mods.vintagestory.at/api/mod/{slug}` and `/api/mods`, so they exercise the normalizers end to end; load fixtures like `test_mod_updates.py:27-31` (`FIXTURES / f"mod_{name}.json"`). Update check tests use `make_service`/`installed`/`fixture_response` in `test_mod_updates.py`.
- Web: `ModDetailPage.test.tsx` uses `createTestQueryClient` with `retry: false`, `renderWithProviders` with an `InitialEntry` (pathname + state) and `BrowseLanding`, which prints `landing-search` and `landing-from-detail` (Story 16.1 block, `:1412-1477`).
- E2E: not part of `just check`. Wait for specific responses and DOM markers, never `networkidle` or fixed delays (Story 16.1). The production app retries a failed query three times (`api/query-client.ts`), so the error state takes a few seconds.

**UI Stories - Manual Browser Verification:** Docker stack (`just docker restart`, http://localhost:8080). Read-only: nothing is installed, so `./data` must be unchanged. Check the browser console. `just docker stop` is not required after.

### Security Requirements

- No new endpoint or input. Normalization only reads mod database JSON into defaults; it adds no string interpolation or file path use. `safe_release_filename` still guards every download filename.

### Development Commands

- `just test-api tests/test_moddb_normalize.py`, `just test-api tests/test_mod_api.py tests/test_mod_service.py tests/test_mods_router.py tests/test_mod_models.py`, `just test-api tests/test_mod_updates.py tests/test_mod_updates_router.py tests/test_mod_version_change.py tests/test_edge_cases.py`, `just test-web src/features/mods/ModDetailPage.test.tsx`, `just check`, `just docker restart`, `cd web && bunx playwright test e2e/mod-detail-bad-data.spec.ts`.

### Previous Story Intelligence

- **16.1:** `browseTarget` and `MOD_DETAIL_RETURN_STATE` are the browse return contract; reuse them, do not recompute. Cards open details with `state: { browseSearch: location.search }` (`BrowseTab.tsx:179-184`). `main.tsx` renders under StrictMode; `just lint-web` is `tsc --noEmit`.
- **16.2:** E2E pattern for replacing one API call with `page.route` while the rest stays live (`e2e/installed-mod-any-modid.spec.ts`).
- **16.3:** `_compatibility_modid` and `supported_game_versions` already read releases null-safely; the lookup evaluates `own` releases of one mod ID.
- **16.8:** `_name_sort_key` was made null-safe the per-field way (`m.get("name") or ""`), which ADR-1 decision 5 now replaces as a pattern; it stays as it is. Review found nothing in the sort code; its tests are in `TestSortMods`.
- **14.x hardening:** `StoredRelease.from_api` cleans lone surrogates and accepts a string `tags` (`test_mod_updates.py:571-584`, `test_mod_updates_router.py:142-157`); keep both.

### Git Intelligence

- Branch `story/17-1-mod-detail-pages-cannot-fail-on-bad-data` from `docs/epic-17-mod-data-fixes` (1f87ced). Planned types: Task 1 `refactor` (normalizers not yet used), Task 2 `fix` (mods with missing release files open), Task 3 `fix` (browse, tags and update checks no longer fail on incomplete mod data), Task 4 `fix` (Back to Browse when a mod's details fail to load), Task 5 `test`, Task 6 `chore`.

### Latest Technical Information

- No new libraries. Pydantic v2 validates `int | None` with `None` and dumps it as JSON `null`. Playwright `page.route(url, route => route.fulfill({ status: 500, json }))` and `page.unroute(url)`.

### Project Structure Notes

- New: `api/src/vintagestory_api/models/moddb.py`, `api/tests/test_moddb_normalize.py`, `api/tests/fixtures/moddb/mod_canjewelry.json`, `web/e2e/mod-detail-bad-data.spec.ts`.
- Modified: `api/src/vintagestory_api/services/mod_api.py`, `services/mods.py`, `services/mod_updates.py`, `routers/mods.py`, `models/mods.py`, `models/mod_updates.py`, `api/tests/fixtures/moddb/README.md`, `agentdocs/vintagestory-modapi.md`, `web/src/api/types.ts`, `web/src/features/mods/ModDetailPage.tsx` (+ the tests named in the tasks).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 17.1: Mod Detail Pages Cannot Fail on Bad Data]
- [Source: _bmad-output/planning-artifacts/prd.md] FR177, FR178
- [Source: _bmad-output/planning-artifacts/architecture/epic-17-mod-data-fixes.md#ADR-1: Mod Database Data Is Normalized Once, Where It Enters]; ADR-2 decision 4 (release without a file, Story 17.2)
- [Source: _bmad-output/planning-artifacts/architecture/epic-16-ui-polish.md#ADR-1] (browse state, return target)
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-15.md]
- [Source: _bmad-output/implementation-artifacts/16-1-mod-browser-state-survives-mod-details.md], [16-8-name-sort-and-empty-settings.md]
- [Source: api/tests/fixtures/moddb/README.md], [Source: agentdocs/vintagestory-modapi.md]
- Beads: `VSS-a0r`, `VSS-fv7`, parent `VSS-4v5`
- `project-context.md` - critical implementation rules and patterns

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5)

### Debug Log References

### Completion Notes List

- Story created 2026-11-15: context analysis of `ModApiClient`'s entry points, the lookup, browse, tag and update check readers, `StoredRelease.from_api`, the detail page's error states, the live `canjewelry` entry and listing, Stories 16.1, 16.3 and 16.8, and Epic 17 ADR-1.

### File List

## Change Log

- 2026-11-15: Story 17.1 created (ready-for-dev).
