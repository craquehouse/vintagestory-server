# Story 14.1: Update Detection and Status API

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **administrator**,
I want **to see which installed mods have updates**,
so that **I know what can be updated without checking each mod**.

## Acceptance Criteria

1. **Given** an installed mod has newer releases
   **When** update status is determined
   **Then** release order from the mod database identifies them, without comparing version strings (apart from the base-version check in AC 3)
   **And** the offered update is the newest eligible newer release that is compatible with the installed game version, or if none, the newest eligible newer release that is not verified
   *(FR129, FR130)*

2. **Given** a mod database entry contains releases for several modids
   **When** update status is determined
   **Then** only releases whose `modidstr` equals the installed mod's modid are considered
   **And** the installed release is the one matching both modid and version

3. **Given** the installed version is stable (its version has no `-`)
   **When** a newer release is a pre-release
   **Then** it is not eligible
   **And** a mod already on a pre-release is offered a newer release only if that release's base version is at least the installed base version
   **And** a newer release whose base version cannot be parsed is not eligible, and if the installed base version cannot be parsed, no update is offered
   *(FR130)*

4. **Given** every eligible newer release is incompatible with the installed game version
   **When** update status is determined
   **Then** no update is offered and the status is `blocked`
   *(FR131)*

5. **Given** a mod is not found in the mod database, or its installed release is not listed, or it has never been checked
   **When** update status is determined
   **Then** its status is `unknown` with a reason, never `up_to_date`
   *(FR132)*

6. **Given** I am an Admin or Monitor
   **When** I request `GET /api/v1alpha1/mods/updates`
   **Then** I receive, for each installed mod, its status, offered version, the offered release's compatibility and the last-checked time
   **And** an unauthenticated request receives 401
   *(FR133)*

7. **Given** I am an Admin
   **When** I request `POST /api/v1alpha1/mods/updates/check`
   **Then** release data is refreshed from the mod database and the updated status is returned
   **And** a Monitor receives 403
   **And** a check requested while one is running receives 409
   *(FR134)*

8. **Given** update data has been stored
   **When** the API restarts
   **Then** the last known status is still returned, computed against the current installed game version
   *(FR147)*

9. **Given** the mod database is unavailable for a mod
   **When** a check runs
   **Then** that mod's previously stored data is kept
   **And** the failure is reported in the check result and on that mod's status

## Tasks / Subtasks

- [x] Task 1: Implement update evaluation rules + tests (AC: 1, 2, 3, 4, 5)
  - [x] 1.1: Create `api/src/vintagestory_api/services/mod_updates.py` with pure functions: `is_prerelease(version)`, `parse_base_version(version)`, and `evaluate_update(modid, installed_version, releases, game_version)` returning status, offered release, compatibility and reason
  - [x] 1.2: Reuse `check_compatibility()` from `services/mod_api.py`; do not reimplement it
  - [x] 1.3: Write tests in `api/tests/test_mod_updates.py` using the ModDB fixtures (see Testing Requirements for the required cases)

- [x] Task 2: Add status models and the persistent store + tests (AC: 5, 8)
  - [x] 2.1: Add models in `api/src/vintagestory_api/models/mod_updates.py`: stored per-mod record and the API status item (fields under Dev Notes)
  - [x] 2.2: Implement a store for `{state_dir}/mod-updates.json` with atomic writes (temp file, then rename), a `schema_version` field, and tolerant loading (missing or corrupt file logs a warning and starts empty)
  - [x] 2.3: Tests: round trip, a new store instance reads data written by another (restart), corrupt file, and that status is computed at read time against the game version passed in

- [x] Task 3: Implement the check + tests (AC: 7, 9)
  - [x] 3.1: Add `ModUpdateService` with `get_status()` and `async check()`; fetch each installed mod with `ModService.api_client.get_mod(slug)`, sequentially
  - [x] 3.2: A `None` result (404) stores an empty release list with reason `not_in_database`; an `ExternalApiError` keeps the previous record and sets its error; the check returns counts and the failed slugs
  - [x] 3.3: Guard `check()` with an `asyncio.Lock`; a second concurrent check raises a dedicated error (409 at the API)
  - [x] 3.4: Get the game version from `ServerService.get_installed_version()` via a lazy import; never use `Settings.game_version`
  - [x] 3.5: Tests with `respx` and the fixtures: success, 404, API failure preserving prior data, mixed results, concurrency, and no server installed

- [x] Task 4: Add the endpoints and dependency + tests (AC: 6, 7)
  - [x] 4.1: Add `get_mod_update_service()` singleton and register it as a FastAPI dependency
  - [x] 4.2: Add `GET /mods/updates` (Admin or Monitor) and `POST /mods/updates/check` (Admin) to `routers/mods.py`, declared directly after `list_mods`
  - [x] 4.3: Add `MOD_UPDATE_CHECK_IN_PROGRESS` to `models/errors.py`; map it to 409
  - [x] 4.4: Router tests: response shape and envelope, 401, Monitor 200 on GET and 403 on POST, 409, and that `/mods/updates` is not captured by any `/{slug}` route

- [x] Task 5: Final validation (AC: all)
  - [x] 5.1: Run `just check`
  - [x] 5.2: Update this story's Dev Agent Record and File List

### Review Follow-ups (AI)

- [x] [AI-Review][Medium] Malformed mod database payloads (bad `fileid`, non-list `releases`, non-object `mod`) raise during parsing outside the guarded lookup, aborting the whole check with a 500 and saving nothing [services/mod_updates.py `_check_one`]
- [x] [AI-Review][Medium] AC 9: a failed lookup for a never-checked mod is not reported on that mod's status [services/mod_updates.py `_check_one`, `build_status_items`]
- [x] [AI-Review][Low] Duplicate `modversion` within one modid: first occurrence wins, undocumented [services/mod_updates.py `evaluate_update`]
- [x] [AI-Review][Low] `last_full_check` is stamped even when every lookup failed [services/mod_updates.py `check`]
- [x] [AI-Review][Low] A store save error escapes `check()` as a 500 after successful lookups [services/mod_updates.py `check`]
- [x] [AI-Review][Low] `StoredRelease.from_api` splits a string `tags` value into characters [models/mod_updates.py `from_api`]
- [x] [AI-Review][Low] Concurrency tests reach into the private lock and monkeypatch `check` rather than exercising a real overlapping check [tests/test_mod_updates.py]
- [x] [AI-Review][Low] The `Compatibility` literal duplicates `CompatibilityStatus` with nothing pinning them together [models/mod_updates.py]
- [x] [AI-Review][Low] Records for uninstalled mods are never pruned from `mod-updates.json` [services/mod_updates.py `check`]
- [x] [AI-Review][Medium] `get_mod` raises `AttributeError` (top-level JSON array) or `KeyError` (no `mod` key) before parsing; these escape `check()` and abort it [services/mod_updates.py `_check_one`]
- [x] [AI-Review][Low] A lone surrogate from upstream makes `save()` raise `PydanticSerializationError` (a `ValueError`), which the `OSError` guard misses [services/mod_updates.py `check`]
- [x] [AI-Review][Low] A lone surrogate in a release's `modversion` reaches `offered_version` and makes `GET /mods/updates` and `POST /mods/updates/check` fail during response serialization (500) [models/mod_updates.py `StoredRelease.from_api`]

## Dev Notes

### What this story delivers, and what it does not

Delivers: update detection rules, a persistent update store, a manual check, and two read/check endpoints. **Out of scope:** applying updates (14.2), UI (14.3), update all (14.4), scheduled checks and badges (14.5), webhooks (14.6). Do not modify `jobs/mod_cache_refresh.py` here; Story 14.5 extends it to call `check()`.

### Detection rules (ADR-1, verified in Story 14.0)

Source of truth: `_bmad-output/planning-artifacts/architecture/epic-14-mod-updates.md` ADR-1. In code order:

1. Keep only releases with `release["modidstr"] == installed modid`. ModDB lists newest first.
2. Find the installed release: the first remaining release with `modversion == installed version`. None found → `unknown`, reason `installed_release_not_listed`.
3. Newer releases are those **before** the installed release in the list. Never compare version strings, except step 4.
4. Eligibility:
   - `is_prerelease(v)` is `"-" in v`.
   - Installed stable: only stable newer releases are eligible.
   - Installed pre-release: a newer release is eligible only if `parse_base_version(release) >= parse_base_version(installed)`. The base version is the text before the first `-`, split on `.`, each part an integer; compare as tuples padded with zeros. If the installed base version does not parse → `unknown`, reason `version_unparsable`. If a newer release's base does not parse → that release is not eligible.
5. Classify each eligible newer release with `check_compatibility(release, game_version)`.
6. Offer the first (newest) `compatible` one; otherwise the first `not_verified` one; otherwise status `blocked` if eligible newer releases exist; `up_to_date` if none exist.

Known limitations (documented in ADR-1; do not "fix" them here): a stable version containing `-` is treated as a pre-release, and stable installs do not get the base-version check.

**Worked example from `mod_carryon.json`** (order: `2.0.0-rc.1`, `1.14.3`, `2.0.0-pre.8`, …):

| Installed | Eligible newer | Offered (if all compatible) |
|---|---|---|
| `2.0.0-pre.8` | `2.0.0-rc.1` (base 2.0.0 ≥ 2.0.0); not `1.14.3` (1.14.3 < 2.0.0) | `2.0.0-rc.1` |
| `1.14.3` | none (`2.0.0-rc.1` is a pre-release) | none: `up_to_date` |

### Game version (pre-existing defect to avoid)

`ModService` checks compatibility against `Settings.game_version` (`VS_GAME_VERSION`, default `"stable"`). That is the server **install channel**, not a version. `check_compatibility()` cannot parse `"stable"`, so it returns `not_verified` for everything. **Do not copy this.** Use the installed server version from `get_server_service().get_installed_version()` (returns `None` when no server is installed). Import `get_server_service` inside the function to avoid an import cycle: `services/server.py` already imports the mods module lazily via `_get_mod_service_module`. With `None`, pass `""` to `check_compatibility()`, which returns `not_verified`. This defect is filed as `VSS-tpe` [API-063]; do not change `ModService` in this story.

### Status computed at read time

Store raw release data, not final statuses. `get_status()` evaluates each installed mod against the stored releases, the **current** installed mods (`ModService.list_mods()`) and the **current** game version. A server upgrade, an install, a removal or a version change then shows up immediately, with no network call. A mod installed after the last check has no record, so it is `unknown`, reason `not_checked`.

### Stored record (`{state_dir}/mod-updates.json`)

`state_dir` is `Settings.state_dir` (`/data/vsmanager/state`).

```json
{
  "schema_version": 1,
  "mods": {
    "<modid>": {
      "checked_at": "<UTC ISO 8601>",
      "found": true,
      "releases": [
        {"modversion": "...", "modidstr": "...", "tags": ["1.22.0"], "fileid": 123, "filename": "...", "created": "..."}
      ],
      "error": null
    }
  }
}
```

Keep `fileid` and `filename`: Story 14.2 needs them. Leave room for Story 14.6, which adds alert tracking under the same file. Write with a temp file then `rename`, as `services/mod_state.py` lines 111-114 do. Note: `Path.with_suffix(".tmp")` on `mod-updates.json` yields `mod-updates.tmp`, which is fine.

### API contract

`GET /api/v1alpha1/mods/updates` (Admin or Monitor):

```json
{"status": "ok", "data": {
  "game_version": "1.22.7",
  "checked_at": "<last full check or null>",
  "update_count": 1,
  "mods": [{
    "slug": "carryon", "name": "Carry On",
    "installed_version": "1.14.2",
    "status": "update_available",
    "offered_version": "1.14.3",
    "offered_compatibility": "compatible",
    "offered_prerelease": false,
    "reason": null,
    "checked_at": "<this mod>",
    "error": null
  }]
}}
```

- `status` is one of `update_available`, `up_to_date`, `blocked`, `unknown`.
- `reason` is set for `unknown`: `not_checked`, `not_in_database`, `installed_release_not_listed`, `version_unparsable`.
- `error` holds the last check failure for that mod, or `null`.
- `update_count` counts `update_available` only.
- JSON stays snake_case; the web client converts to camelCase (`project-context.md` §4).

`POST /api/v1alpha1/mods/updates/check` (Admin) returns the same payload plus `"check": {"checked": n, "failed": n, "failed_slugs": [...]}`. If all lookups fail it still returns 200 with failures reported: data is preserved, not lost.

Errors use the existing `HTTPException(detail={"code": ..., "message": ...})` pattern in `routers/mods.py`. New code: `MOD_UPDATE_CHECK_IN_PROGRESS` (409).

### Reuse, do not reinvent

| Need | Use |
|---|---|
| Mod database lookup | `ModService.api_client.get_mod(slug)` (`services/mod_api.py:256`): returns `None` on 404, raises `ExternalApiError` on failure |
| Compatibility | `check_compatibility(release, game_version)` (`services/mod_api.py:153`) |
| Installed mods | `ModService.list_mods()` → `ModInfo` (`slug` = modid, `version`, `name`) |
| Roles | `RequireAuth` (defined in `routers/mods.py:43`) for Admin or Monitor; `RequireAdmin` from `middleware/permissions.py` |
| Envelope | `ApiResponse(status="ok", data=...)` |
| Atomic write | Pattern in `services/mod_state.py:111-114` |

### Testing Requirements

Tests go in `api/tests/test_mod_updates.py` (rules, store, service) and `api/tests/test_mod_updates_router.py` (endpoints). Load fixtures with `json.loads((Path(__file__).parent / "fixtures" / "moddb" / name).read_text())`. Use `respx` for HTTP, as `tests/test_mod_api.py` does. Override dependencies through `app.dependency_overrides`, as `tests/test_mods_router.py:90-93` does, and clear them afterwards.

**Required rule cases:**

- CarryOn: `2.0.0-pre.8` is offered `2.0.0-rc.1`, never `1.14.3`; `1.14.3` is never offered a pre-release.
- Instruments: an installed `instruments` `1.0.1` ignores the `vsinstrumentsbase` `1.0.1` release and other modids.
- Auto Map Markers: releases under `egocaribresinmapmarkers` are ignored for an `egocaribautomapmarkers` install.
- Not found (`mod_not_found.json`) → `unknown`, `not_in_database`.
- Installed version not listed → `unknown`, `installed_release_not_listed`.
- Unparsable installed base on a pre-release install → `unknown`, `version_unparsable`. A newer release with an unparsable base is skipped, not fatal.
- Only incompatible eligible newer releases → `blocked`.
- Compatible preferred over not-verified, even if older in the list.
- No server installed: everything classifies `not_verified`, and an update is still offered.

Fixture tags are 1.22-era. Use a game version such as `"1.22.0"` for compatible cases, and build small inline release lists where the fixtures do not cover a case.

**CRITICAL:** Tests are written with each task, not batched at the end. A task is complete only when its tests pass. Run `just test-api -k mod_updates` while iterating and `just check` at the end.

### Security Requirements

- Update status is read-only for Monitor; the check is Admin-only (it triggers outbound requests).
- No user input reaches a file path: the store path is fixed, and modids come from installed state.
- Log events: `mod_update_check_started`, `mod_update_check_complete` (counts), `mod_update_lookup_failed` (slug, error). No secrets are involved.

### Development Commands

- `just test-api -k mod_updates`
- `just check`

### Project Structure Notes

- New: `api/src/vintagestory_api/services/mod_updates.py`, `api/src/vintagestory_api/models/mod_updates.py`, `api/tests/test_mod_updates.py`, `api/tests/test_mod_updates_router.py`
- Modified: `api/src/vintagestory_api/routers/mods.py`, `api/src/vintagestory_api/models/errors.py`
- No web changes. No changes to `ModService`, `ModApiClient` or jobs.

### Previous Story Intelligence (14.0)

- ModDB facts: `agentdocs/vintagestory-modapi.md` § Release Behavior. A not-found response is `{"statuscode": "404"}` with no `mod` key.
- Fixtures and their cases: `api/tests/fixtures/moddb/README.md`.
- Two existing install-path bugs are filed and **out of scope** here: `VSS-432` (unsanitized filenames) and `VSS-jhf` (install ignores modid). Do not touch install code.
- Reviews of 14.0 tightened wording three times; follow ADR-1 exactly rather than paraphrasing it.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 14.1]
- [Source: _bmad-output/planning-artifacts/architecture/epic-14-mod-updates.md] ADR-1, ADR-4, API Additions
- [Source: _bmad-output/planning-artifacts/prd.md] FR129-FR134, FR147
- [Source: _bmad-output/implementation-artifacts/14-0-epic-14-technical-preparation.md] findings
- [Source: project-context.md] §3 API Response Envelope, §4 JSON Field Naming Boundary, §6 Atomic File Writes, Security Patterns §5 RBAC

## Senior Developer Review (AI)

**Date:** 2026-11-09
**Reviewer:** GLM-5.3-Flash via OpenCode (Z.ai coding plan), delegated read-only review of `dd12072`..`105b093`
**Outcome:** Changes Requested

**Summary:** ADR-1 rules are implemented in exact order and well tested (probes covered `1.0`, `1.0.0.1`, `01.2`, unicode digits, cross-modid versions); persistence is atomic and tolerant; the API matches the contract; no suppressions; `just check` passed. AC 1-8 pass, AC 9 partial.

### Action Items

- [x] [Medium] Malformed mod database payloads (bad `fileid`, non-list `releases`, non-object `mod`) raise during parsing outside the guarded lookup, aborting the whole check with a 500 and saving nothing [services/mod_updates.py `_check_one`]
- [x] [Medium] AC 9: a failed lookup for a never-checked mod is not reported on that mod's status [services/mod_updates.py `_check_one`, `build_status_items`]
- [x] [Low] Duplicate `modversion` within one modid: first occurrence wins, undocumented [services/mod_updates.py `evaluate_update`]
- [x] [Low] `last_full_check` is stamped even when every lookup failed [services/mod_updates.py `check`]
- [x] [Low] A store save error escapes `check()` as a 500 after successful lookups [services/mod_updates.py `check`]
- [x] [Low] `StoredRelease.from_api` splits a string `tags` value into characters [models/mod_updates.py `from_api`]
- [x] [Low] Concurrency tests reach into the private lock and monkeypatch `check` rather than exercising a real overlapping check [tests/test_mod_updates.py]
- [x] [Low] The `Compatibility` literal duplicates `CompatibilityStatus` with nothing pinning them together [models/mod_updates.py]
- [x] [Low] Records for uninstalled mods are never pruned from `mod-updates.json` [services/mod_updates.py `check`]

## Senior Developer Review (AI): Follow-up

**Date:** 2026-11-09
**Reviewer:** GLM-5.3-Flash via OpenCode (Z.ai coding plan), delegated read-only review of `105b093`..`006b6f8`
**Outcome:** Changes Requested

**Summary:** All nine earlier findings verified resolved (original probes re-run, 12 further malformed shapes contained), backward compatibility of pre-`lookup_errors` files confirmed, no suppressions, bookkeeping complete, `just check` passed. Two residual escape paths remain.

### Action Items

- [x] [Medium] `get_mod` raises `AttributeError` (top-level JSON array) or `KeyError` (no `mod` key) before parsing; these escape `check()` and abort it [services/mod_updates.py `_check_one`]
- [x] [Low] A lone surrogate from upstream makes `save()` raise `PydanticSerializationError` (a `ValueError`), which the `OSError` guard misses [services/mod_updates.py `check`]

## Senior Developer Review (AI): Second Follow-up

**Date:** 2026-11-09
**Reviewer:** GLM-5.3-Flash via OpenCode (Z.ai coding plan), delegated read-only review of `006b6f8`..`9f1d42f`
**Outcome:** Changes Requested

**Summary:** Both earlier findings verified resolved with real-client probes; every probed upstream payload shape is contained per mod; no AC regressions; no suppressions; `just check` passed. One new Low finding.

### Action Items

- [x] [Low] A lone surrogate in a release's `modversion` reaches `offered_version` and makes `GET /mods/updates` and `POST /mods/updates/check` fail during response serialization (500) [models/mod_updates.py `StoredRelease.from_api`]

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5)

### Debug Log References

### Completion Notes List

- Task 1: Added `evaluate_update`, `is_prerelease` and `parse_base_version` implementing ADR-1, and the `StoredRelease` model. 26 tests cover every required rule case using the ModDB fixtures and inline release lists.
- Task 2: Added `StoredModRecord`, `ModUpdatesFile` and `ModUpdateStatusItem` models, the atomic `ModUpdateStore` (`{state_dir}/mod-updates.json`, schema version 1, tolerant of missing or corrupt files) and `build_status_items`, which computes status at read time. 8 tests cover restart persistence, atomic writes, corrupt files and read-time game version.

- Task 3: Added `ModUpdateService` (`get_status`, `check`, `game_version`) behind an `InstalledModSource` protocol, with an `asyncio.Lock` guard (`ModUpdateCheckInProgressError`). Lookups that raise `ExternalApiError`, or `ValueError` for a non-JSON reply (which `get_mod` does not catch), keep previous data and record the error; a successful lookup clears it. A failed lookup for a never-checked mod is reported in the check result only, since there is no stored record to attach it to; the mod stays `unknown` / `not_checked`. 6 tests.

- Task 4: Added `get_mod_update_service()` (game version from `ServerService.get_installed_version()` via a lazy import), `MOD_UPDATE_CHECK_IN_PROGRESS`, and `GET /mods/updates` (Admin or Monitor) and `POST /mods/updates/check` (Admin, 409 when busy) directly after `list_mods`. Timestamps serialize with a `Z` suffix. 6 router tests cover the payload shape, roles, 401, 403 and 409; the GET and POST tests also show neither path is captured by a `/{slug}` route.

- Task 5: `just check` passes: Ruff and Pyright clean (0 errors), 1879 API tests (46 new), 2911 web tests.
- Lint failed after the Task 1 commit (two long lines in the new tests); fixed in `eebeb97`, and later commits were gated on lint and tests passing.
- ✅ Resolved review finding [Medium]: Parsing now runs inside the guarded lookup via `_record_from_payload`; `ValueError` (including pydantic validation) and `TypeError` become a per-mod failure. 5 parametrized payload shapes tested; the good mod is still stored and saved.
- ✅ Resolved review finding [Medium]: The store keeps `lookup_errors` for mods with no record; status shows the error with reason `not_checked`; a later successful lookup clears it. Tested, including persistence.
- ✅ Resolved review finding [Low]: `evaluate_update` docstring states the first (newest) occurrence is the installed release.
- ✅ Resolved review finding [Low]: `last_full_check` now means the last check in which every lookup succeeded; tested for partial failure then success.
- ✅ Resolved review finding [Low]: `OSError` on save is logged (`mod_update_store_save_failed`) and the check returns its results, which stay available in memory until restart. Tested.
- ✅ Resolved review finding [Low]: A string `tags` value becomes a one-element list; non-object releases raise `TypeError`. Tested.
- ✅ Resolved review finding [Low]: Replaced with a behavioral test that blocks a real check on a pending lookup and asserts a second check is rejected.
- ✅ Resolved review finding [Low]: Test pins `Compatibility` to `mod_api.CompatibilityStatus`.
- ✅ Resolved review finding [Low]: `check()` prunes records and lookup errors for mods no longer installed. Tested.
- ✅ Resolved review finding [Medium]: `_check_one` also catches `KeyError` and `AttributeError` raised inside `get_mod()`; `mod_api` unchanged. Tested with a top-level JSON array and a body with no `mod` key.
- ✅ Resolved review finding [Low]: The save guard catches `ValueError` as well as `OSError`. Tested with a lone surrogate in a release filename.
- ✅ Resolved review finding [Low]: `StoredRelease.from_api` replaces each lone surrogate with U+FFFD in every stored text field, so neither the store nor responses can carry one. Tested at the model and end to end through `POST /mods/updates/check` and `GET /mods/updates`.

### File List

- Created: `api/src/vintagestory_api/models/mod_updates.py`
- Created: `api/src/vintagestory_api/services/mod_updates.py`
- Created: `api/tests/test_mod_updates.py`
- Created: `api/tests/test_mod_updates_router.py`
- Modified: `api/src/vintagestory_api/routers/mods.py`
- Modified: `api/src/vintagestory_api/models/errors.py`

## Change Log

- 2026-11-09: Implemented update detection (ADR-1 rules), the persistent update store (`mod-updates.json`), the update check service, and `GET /mods/updates` and `POST /mods/updates/check`. 46 tests.
- 2026-11-09: Addressed code review findings - 9 items resolved (2 Medium, 7 Low). Malformed payloads are per-mod failures; never-checked failures appear on status; `last_full_check` only after a fully successful check; save errors no longer fail the check; stale records pruned. 57 tests in the two update test files; `just check` passes with 1890 API tests.
- 2026-11-09: Addressed follow-up review findings - 2 items resolved (1 Medium, 1 Low). Payload errors raised inside `get_mod()` and save serialization errors no longer abort a check. 60 tests in the two update test files.
- 2026-11-09: Addressed second follow-up review finding - lone surrogates in mod database text are replaced at ingestion. 62 tests in the two update test files.
- 2026-11-09: Third follow-up review approved; story marked done. Non-blocking note from the review: error strings stored from exceptions are not passed through `_clean_text`; no current exception embeds raw upstream text, so this is left as is.
