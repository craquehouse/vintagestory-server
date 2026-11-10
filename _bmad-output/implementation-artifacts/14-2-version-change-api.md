# Story 14.2: Version Change API

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **administrator**,
I want **a mod moved safely to a chosen version**,
so that **a failed update never leaves me without a working mod**.

## Acceptance Criteria

1. **Given** an installed mod and a release listed in the mod database with the installed mod's modid
   **When** I request `PUT /api/v1alpha1/mods/{slug}/version` with `{"version": "<modversion>"}`
   **Then** the release is taken from the download cache if a cached copy validates, otherwise downloaded
   **And** the installed file is replaced only after the new archive is validated
   *(FR135, FR140, FR142)*

2. **Given** a requested version that exists only under a different modid, even within the same mod database entry
   **When** the version change is requested
   **Then** it is rejected as not found and the mod is unchanged

3. **Given** a cached or downloaded archive whose `modinfo.json` modid or version differs from the requested release
   **When** it is validated
   **Then** a cached copy is discarded and downloaded again, and a freshly downloaded copy fails the change with `MOD_VALIDATION_FAILED`
   **And** the original file and state are unchanged

4. **Given** ModDB's `filename` for the release
   **When** it is used to name a file
   **Then** only its final path component is used, and empty, `.` or `..` names are rejected
   *(the same rule now applies to the existing install path; closes `VSS-432`)*

5. **Given** a download or validation failure, or the old file cannot be deleted after the swap
   **When** the change fails
   **Then** the original file and state remain, any new file is removed, and a specific error code is returned
   *(FR137)*

6. **Given** the mod is disabled
   **When** its version changes
   **Then** it remains disabled
   *(FR138)*

7. **Given** the server is running
   **When** a version change succeeds
   **Then** a restart is marked as pending
   *(FR139)*

8. **Given** the target release is not verified, incompatible, a pre-release while the installed version is stable, or older than the installed release (later in the release list)
   **When** the request does not include `"confirm": true`
   **Then** it is rejected with 409 `MOD_CONFIRMATION_REQUIRED` and the reasons, and nothing is downloaded or changed
   *(FR136, FR141)*

9. **Given** a version change is in progress for a mod
   **When** another change is requested for that mod
   **Then** the second request is rejected with 409 `MOD_VERSION_CHANGE_IN_PROGRESS`

10. **Given** the requested version is already installed
    **When** the change is requested
    **Then** it succeeds with `changed: false` and nothing is downloaded or modified

11. **Given** I am a Monitor or unauthenticated
    **When** I request a version change
    **Then** I receive 403 or 401

## Tasks / Subtasks

- [x] Task 1: Sanitize release filenames and share the download step + tests (AC: 4)
  - [x] 1.1: Add `safe_release_filename(name)` to `services/mod_api.py`: take the part after the last `/` or `\`; raise `DownloadError` for an empty result, `.`, `..`, or a name containing NUL
  - [x] 1.2: Extract `ModApiClient.download_release_file(fileid, filename) -> Path` from step 3 of `download_mod` (stream to `{cache}/mods/{safe name}` through a `.tmp` file, then rename; existing error handling); make `download_mod` call it
  - [x] 1.3: Tests: hostile names (`../x.zip`, `a/b.zip`, `a\\b.zip`, `..`, `""`, NUL) and that `download_mod` uses the safe name; all existing `test_mod_api.py` download tests still pass

- [x] Task 2: Add strict archive validation + tests (AC: 3)
  - [x] 2.1: Add `ModStateManager.read_modinfo(zip_path) -> ModMetadata | None`: parse `modinfo.json` with the existing safe extractor and **no caching or fallback**; `None` when missing or invalid
  - [x] 2.2: Tests: valid archive, missing `modinfo.json`, corrupt zip, invalid JSON, wrong field types

- [x] Task 3: Implement version resolution, confirmation and archive acquisition + tests (AC: 1, 2, 3, 8, 10)
  - [x] 3.1: Add `ModService.change_version(slug, version, confirm)`: installed check (`ModNotFoundError`), no-op when already at the version, fresh `get_mod(slug)`, filter releases to `modidstr == slug`, find `modversion == version` (else `ModVersionNotFoundError`)
  - [x] 3.2: Compute confirmation reasons before any download (see Dev Notes); raise `ModConfirmationRequiredError(reasons, compatibility)` when any apply and `confirm` is false
  - [x] 3.3: Acquire the archive: reuse `{cache}/mods/{safe name}` only if `read_modinfo` matches modid and version, otherwise download with `download_release_file` and validate; a mismatch after download deletes the cached file and raises `ModValidationError`
  - [x] 3.4: Tests using `mod_carryon.json` and `mod_instruments.json` (see Testing Requirements)

- [x] Task 4: Swap files and state safely + tests (AC: 1, 5, 6, 7, 9)
  - [x] 4.1: Per-mod `asyncio.Lock`; a busy mod raises `ModVersionChangeInProgressError`
  - [x] 4.2: Copy into the mods directory as a temp file, rename into place (keep `.disabled` when disabled), update and save state, cache metadata via `import_mod`, then delete the old file when its name differs; on delete failure remove the new file, restore the old state entry and raise `ModVersionChangeFailedError`
  - [x] 4.3: Same-filename case: when old and new names match, the rename replaces the old file atomically and no delete is needed
  - [x] 4.4: Mark a pending restart when the server is running
  - [x] 4.5: Tests for every failure point leaving the original intact, disabled mods, same filename, pending restart, and an overlapping change

- [x] Task 5: Add the endpoint + tests (AC: 8, 9, 11)
  - [x] 5.1: Add error codes `MOD_CONFIRMATION_REQUIRED`, `MOD_VERSION_CHANGE_IN_PROGRESS`, `MOD_VALIDATION_FAILED`, `MOD_VERSION_CHANGE_FAILED` to `models/errors.py`
  - [x] 5.2: Add `PUT /mods/{slug}/version` (Admin) with body `{version: str, confirm: bool = false}`; map errors as listed in Dev Notes
  - [x] 5.3: Router tests: success payload, each error mapping, 401 and 403

- [x] Task 6: Final validation (AC: all)
  - [x] 6.1: Run `just check`
  - [x] 6.2: Update this story's Dev Agent Record and File List; add the AAR to `VSS-432` and close it

### Review Follow-ups (AI)

- [x] [AI-Review][Medium] `VSS-432` closure not visible in the tracker (the review read the stale `.beads/beads.db`; `bd show VSS-432` shows it closed with the AAR)
- [x] [AI-Review][Low] Version change is not serialized against install, enable, disable or remove (filed as `VSS-8wg`)
- [x] [AI-Review][Low] The same-version no-op test does not assert that no request is made [tests/test_mod_version_change.py]
- [x] [AI-Review][Low] No service-level test of a confirmed pre-release change [tests/test_mod_version_change.py]
- [x] [AI-Review][Low] `install_mod` stages its copy with `with_suffix(".tmp")`, which can overwrite an unrelated same-stem `.tmp` file [services/mods.py `install_mod`]
- [x] [AI-Review][Low] An `OSError` from deleting an invalid cache file in `_acquire_release_archive` escapes unmapped [services/mods.py]
- [x] [AI-Review][Low] `read_modinfo` matches keys case-insensitively but `import_mod` does not (filed as `VSS-0jl`, related to `VSS-jhf`)

## Dev Notes

### What this story delivers, and what it does not

Delivers the version change operation (used for updates and rollback) and its endpoint. **Out of scope:** UI (14.3), update all (14.4), scheduled checks (14.5), webhooks (14.6). Do not fix `VSS-jhf` (install ignoring modid), `VSS-tpe` (install compatibility using `VS_GAME_VERSION`) or `VSS-d15` (`get_mod` status handling) here; only `VSS-432` is in scope, because Task 1's shared helper fixes it.

### Rules (ADR-1 and ADR-2; read `architecture/epic-14-mod-updates.md`)

Order of operations in `change_version(slug, version, confirm)`:

1. `state = state_manager.get_mod_by_slug(slug)`; missing → `ModNotFoundError` (404 `MOD_NOT_INSTALLED`).
2. Take the per-mod lock (Task 4.1).
3. `version == state.version` → return `changed=False` with no network call.
4. `mod = await api_client.get_mod(slug)`; `None` → `ApiModNotFoundError` (404 `MOD_NOT_FOUND`). `ExternalApiError` propagates (502).
5. `own = [r for r in mod["releases"] if r["modidstr"] == slug]` (use `StoredRelease.from_api` from `models/mod_updates.py` to parse safely). Target = first `own` release with `modversion == version`; none → `ModVersionNotFoundError` (404). This is how AC 2's other-modid case is rejected.
6. Confirmation reasons (all evaluated; any reason with `confirm` false → 409, before any download):
   - `not_verified` or `incompatible`: from `check_compatibility({"tags": target.tags}, game_version)`.
   - `prerelease`: `is_prerelease(target)` and not `is_prerelease(installed)` (helpers in `services/mod_updates.py`).
   - `older`: the installed release is in `own` and the target's index is **greater** than the installed release's index. If the installed release is not listed, `older` does not apply.
7. Acquire and validate the archive (Task 3.3).
8. Swap and update state (Task 4.2); mark a pending restart if the server is running.

**Game version:** use the installed server version, as Story 14.1 does: `installed_game_version()` in `services/mod_updates.py`. Rename the current private `_installed_game_version` to a public function in this story. **Never** use `ModService._game_version` (`VSS-tpe`).

### Swap details (ADR-2)

- New name: `safe_release_filename(target.filename)`, plus `.disabled` if `state.enabled` is false.
- Copy the validated archive to `{mods_dir}/{new name}.tmp`, then `rename` to `{mods_dir}/{new name}`. If `{new name}` already exists **and is not the old file**, fail with `ModVersionChangeFailedError` rather than overwrite another mod's file.
- State: remove the old filename entry, add `ModState(filename=new name, slug=slug, version=target version, enabled=state.enabled, installed_at=state.installed_at, asset_id=state.asset_id)`, save. Call `state_manager.import_mod(new path)` to cache metadata for the new version (its validated result matches).
- Delete the old file if its name differs. If the delete fails: unlink the new file, restore the old state entry, save, raise `ModVersionChangeFailedError`.
- Story 14.0 showed two copies of one modid make the game load one while the API reports the other. The delete is therefore required, not best effort.
- Replacing a file under a running server is safe; the new version loads at restart (Story 14.0, Task 2).

### API contract

`PUT /api/v1alpha1/mods/{slug}/version` (Admin), body `{"version": "1.14.3", "confirm": false}`.

Success (200):

```json
{"status": "ok", "data": {
  "slug": "carryon", "previous_version": "1.14.1", "version": "1.14.3",
  "filename": "CarryOn-1.22.0_v1.14.3.zip", "compatibility": "compatible",
  "changed": true, "pending_restart": false
}}
```

| Condition | Status | Code |
|---|---|---|
| Mod not installed | 404 | `MOD_NOT_INSTALLED` |
| Mod not in database | 404 | `MOD_NOT_FOUND` |
| Version not listed for this modid | 404 | `MOD_VERSION_NOT_FOUND` |
| Confirmation needed | 409 | `MOD_CONFIRMATION_REQUIRED`, with `details: {"reasons": [...], "compatibility": ...}` |
| Change in progress for this mod | 409 | `MOD_VERSION_CHANGE_IN_PROGRESS` |
| Archive invalid or mismatched | 422 | `MOD_VALIDATION_FAILED` |
| Mod database unavailable | 502 | `EXTERNAL_API_ERROR` |
| Download failed | 502 | `DOWNLOAD_FAILED` |
| Swap or delete failed | 500 | `MOD_VERSION_CHANGE_FAILED` |

Error bodies follow the existing pattern in `routers/mods.py`: `HTTPException(status_code=..., detail={"code": ..., "message": ..., "details": {...}})`.

### Reuse, do not reinvent

| Need | Use |
|---|---|
| Release parsing | `StoredRelease.from_api` (`models/mod_updates.py`) |
| Pre-release test | `is_prerelease` (`services/mod_updates.py`) |
| Compatibility | `check_compatibility` (`services/mod_api.py:153`) |
| Download | `download_release_file` (Task 1) |
| modinfo parsing | `ModStateManager._extract_modinfo_from_zip` via the new `read_modinfo` |
| Pending restart | `self._restart_state.require_restart(reason)` when `self._server_running` |
| Atomic copy pattern | `install_mod` in `services/mods.py:711-737` |

### Testing Requirements

Tests go in `api/tests/test_mod_version_change.py` (service) and `api/tests/test_mod_version_change_router.py` (endpoint). Build archives with a `create_mod_zip_bytes(modinfo)` helper, as in `tests/test_mod_service.py:1122`. Mock `https://mods.vintagestory.at/api/mod/{slug}` with the fixtures and `https://mods.vintagestory.at/download?fileid={fileid}` with archive bytes, using `respx`. Construct `ModService` with temp directories, as `tests/test_mod_service.py` fixtures do. Give the update helpers a game version via `monkeypatch` on `installed_game_version`.

**Required cases:**

- CarryOn `1.14.1` → `1.14.3` at game `1.22.7`: no confirmation; new file present, old gone; state version `1.14.3`.
- CarryOn `1.14.3` → `1.14.1` (older) and `1.14.3` → `2.0.0-rc.1` (pre-release from stable) without `confirm` → 409 with the reason; with `confirm` → success.
- Target not verified (`2.0.0-pre.7` at game `1.22.7`) → 409 reason `not_verified`.
- Instruments installed `instruments` `1.0.1`, request `2.0.7` (only under `vsinstrumentsbase`) → `ModVersionNotFoundError`.
- Already at version → `changed=False`; the download route is never called.
- Valid cached archive → no download; cached archive with the wrong version → downloaded again.
- Downloaded archive with the wrong modid → `ModValidationError`, original intact, bad cache file removed.
- Download failure → original intact.
- Old file delete fails (monkeypatch `Path.unlink` for that path) → new file removed, state restored, `ModVersionChangeFailedError`.
- Disabled mod stays `.disabled`; same-filename releases replace in place.
- Server running → pending restart set.
- Overlapping change for the same mod → `ModVersionChangeInProgressError`.
- `safe_release_filename` cases from Task 1.

**CRITICAL:** Tests are written with each task, not batched. Commit only when `just lint-api` and the task's tests pass.

### Security Requirements

- Admin only; the endpoint downloads and writes files.
- `filename` from ModDB is untrusted (Story 14.0): always pass it through `safe_release_filename` before joining a path.
- The `slug` path parameter must name an installed mod; it never builds a path directly.

### Development Commands

- `just test-api -k version_change`
- `just test-api tests/test_mod_api.py`
- `just check`

### Project Structure Notes

- New: `api/tests/test_mod_version_change.py`, `api/tests/test_mod_version_change_router.py`
- Modified: `services/mod_api.py` (helpers, `download_mod` refactor), `services/mod_state.py` (`read_modinfo`), `services/mods.py` (`change_version`, errors), `services/mod_updates.py` (public `installed_game_version`), `routers/mods.py`, `models/errors.py`

### Previous Story Intelligence (14.1)

- Upstream data is untrusted and oddly shaped: Story 14.1's reviews found crashes from malformed payloads, `KeyError` and `AttributeError` inside `get_mod`, and lone surrogates. Parse releases with `StoredRelease.from_api`, which handles all of these, rather than indexing raw dicts.
- `get_mod` returns `None` for any unexpected status (`VSS-d15`); treat `None` as not found here, as 14.1 does.
- 14.1 committed once with lint failing; gate every commit on `just lint-api` and the task's tests.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 14.2]
- [Source: _bmad-output/planning-artifacts/architecture/epic-14-mod-updates.md] ADR-1, ADR-2, ADR-3, API Additions
- [Source: _bmad-output/planning-artifacts/prd.md] FR135-FR142
- [Source: _bmad-output/implementation-artifacts/14-0-epic-14-technical-preparation.md] swap test, filename findings
- [Source: _bmad-output/implementation-artifacts/14-1-update-detection-and-status-api.md] update service, review learnings
- [Source: project-context.md] §6 Atomic File Writes, §8 No Silent Failures, Security Patterns

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5)

### Debug Log References

### Completion Notes List

- Task 1: Added `safe_release_filename` (raises `ValueError`; `download_release_file` converts it to `DownloadError`) and extracted `ModApiClient.download_release_file`, which `download_mod` now uses, so the install path also gets sanitized names (`VSS-432`). The temp file is now `<name>.tmp` rather than a swapped suffix, so a release named `x.tmp` cannot collide with its own temp file. 15 tests; existing `test_mod_api.py`, `test_mod_service.py` and `test_mods_router.py` pass unchanged.
- Task 2: Added `ModStateManager.read_modinfo` (no caching, no fallback, case-insensitive top-level keys as VintageStory reads them). The shared extractor now accepts a UTF-8 byte-order mark, returns `None` for undecodable bytes (previously an uncaught `UnicodeDecodeError`) and for JSON that is not an object; this also benefits `import_mod`. 10 tests; existing mod state and service suites pass.

- Task 3: Added `ModService._prepare_version_change` (installed check, fresh lookup, releases parsed with `StoredRelease.from_api` and filtered to the installed modid, confirmation reasons `not_verified`/`incompatible`/`prerelease`/`older` evaluated before any download) and `_acquire_release_archive` (valid cached copy reused, otherwise downloaded; a mismatched download is deleted and raises `ModValidationError`; an unusable filename raises `ModValidationError`). `ModService` takes an optional `game_version_provider`, defaulting to the installed server version; `installed_game_version` is now public in `mod_updates.py`. A malformed release list raises `ExternalApiError`. 13 tests.

- Task 4: Added `ModService.change_version` (per-mod `asyncio.Lock`, no-op when already at the version, pending restart when the server runs) and `_apply_version_change`: copy to a temp file, rename into place keeping `.disabled`, update and save state, then delete the old file. A failure restores the original file and state. When the release reuses the old filename, the old file is first moved to `<name>.bak` (ignored by the game and the mods scan) so it can be restored; ADR-2 did not cover this case. An existing file of another mod at the new name is never overwritten. 10 tests.

- Task 5: Added `MOD_CONFIRMATION_REQUIRED`, `MOD_VERSION_CHANGE_IN_PROGRESS`, `MOD_VALIDATION_FAILED` and `MOD_VERSION_CHANGE_FAILED`, and `PUT /mods/{slug}/version` (Admin) mapping each service error to the status in Dev Notes; confirmation errors carry `details.reasons` and `details.compatibility`. 14 router tests. The test helper reads responses as `Any` because the TestClient response type comes from a different httpx package than `httpx.Response`.

- Task 6: `just check` passes (see Change Log for counts). ADR-2 updated with the same-filename `.bak` step. `VSS-432` closed with an AAR: the shared `download_release_file` sanitizes filenames for installs too.

- Review: verdict Approve with follow-ups. M1 was a tracker read of the stale SQLite file. Fixed: the no-op test asserts no requests; a confirmed pre-release change is tested at service level; `install_mod` stages under `<name>.tmp`; a failed delete of an invalid cache file is logged, not raised (the download replaces the file by rename and every later use validates it again). L2 and L7 filed as `VSS-8wg` and `VSS-0jl`. 4 tests added.

### File List

- Created: `api/tests/test_mod_version_change.py`
- Created: `api/tests/test_mod_version_change_router.py`
- Modified: `api/src/vintagestory_api/routers/mods.py`
- Modified: `api/src/vintagestory_api/models/errors.py`
- Modified: `_bmad-output/planning-artifacts/architecture/epic-14-mod-updates.md` (ADR-2)
- Modified: `api/src/vintagestory_api/services/mod_api.py`
- Modified: `api/src/vintagestory_api/services/mod_state.py`
- Modified: `api/src/vintagestory_api/services/mods.py`
- Modified: `api/tests/test_mod_service.py` (review follow-up)
- Modified: `api/src/vintagestory_api/services/mod_updates.py`

## Change Log

- 2026-11-09: Implemented filename sanitizing in a shared download step (fixes the install path too), strict archive validation, version change resolution with confirmation, the atomic swap with rollback, and `PUT /mods/{slug}/version`. 61 new tests; `just check` passes with 1956 API tests and 2911 web tests.
- 2026-11-09: Code review (GLM-5.3-Flash, Approve). Applied the small follow-ups, filed `VSS-8wg` and `VSS-0jl`, status done.

## Senior Developer Review (AI)

**Date:** 2026-11-09
**Reviewer:** GLM-5.3-Flash via OpenCode (Z.ai coding plan), delegated read-only review of `f4394e8`^..`cccc4fa`
**Outcome:** Approve

**Summary:** All 11 acceptance criteria pass. Failure injection at five points in the swap restored the original file and state each time with no stray `.tmp` or `.bak`; hostile filenames stayed in the cache; the install path did not regress.

### Action Items

- [x] [Medium] `VSS-432` closure not verifiable in the tracker (stale database read; verified closed)
- [x] [Low] No shared per-mod lock across mutating operations (`VSS-8wg`)
- [x] [Low] No-op test lacks a no-request assertion
- [x] [Low] Confirmed pre-release change untested at service level
- [x] [Low] `install_mod` temp name collision
- [x] [Low] Unmapped `OSError` on cache discard
- [x] [Low] Case-sensitive keys in `import_mod` (`VSS-0jl`)
