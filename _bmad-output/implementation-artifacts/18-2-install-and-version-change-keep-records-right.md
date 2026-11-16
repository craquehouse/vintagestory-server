# Story 18.2: Install and Version Change Keep Files and Records Right

Status: ready-for-dev

<!-- Implements FR199-FR200, Epic 18 ADR-4 and ADR-5. Beads: VSS-z7e (API-075, bug, P2), VSS-do7 (API-076). Stacked on Story 18.1 (stories run in order 18.1, 18.2, 18.3, 18.4). Line references were verified at b9606f1 (epic-18-planning; its api/ and web/ are identical to 574e125, the commit the ADRs cite) and must be re-checked at implementation time: Story 18.1 edits routers/mods.py and models/mods.py first. API change only, plus web tests and an E2E spec; no web source change. No new dependencies. -->

## Story

As an **administrator**,
I want **installing or changing one mod never to damage another mod or leave a wrong status behind**,
so that **I can trust the Installed list after every operation**.

## Acceptance Criteria

1. **Given** mod A is installed as `Foo.zip`
   **When** I install mod B, whose release file is also named `Foo.zip`
   **Then** `POST /api/v1alpha1/mods` returns 409 `MOD_FILE_CONFLICT` with the message `Cannot install '<slug>': a file named Foo.zip already exists in the mods directory.`; A's file has the same bytes as before, A's state entry is unchanged, the mods directory holds exactly the files it held before (no `Foo.zip.tmp`), B has no state entry, and no mod's lock is left held
   *(Covers FR199; `VSS-z7e`)*

2. **Given** mod A is disabled, so its file is `Foo.zip.disabled`
   **When** I install mod B, whose release file is named `Foo.zip`
   **Then** the response is 409 `MOD_FILE_CONFLICT`, the message names `Foo.zip.disabled`, and nothing is placed
   *(Covers FR199)*

3. **Given** a file named like the download exists in the mods directory but has no state entry, or the mod state has an entry under that file name with no file
   **When** I install the mod
   **Then** the response is 409 `MOD_FILE_CONFLICT`, and nothing is placed or removed (the stray file's bytes and the state entry are unchanged)
   *(Covers FR199)*

4. **Given** a download whose `modinfo.json` cannot be read, with a file name another mod uses
   **When** I install it
   **Then** the response is 409 `MOD_FILE_CONFLICT`, with the same "nothing touched" outcome as AC 1
   *(Covers FR199)*

5. **Given** no file-name collision, and the import or state save fails after the file is placed
   **When** the install cleans up
   **Then** only the newly placed file and its own state entry are removed, as today, and another installed mod's file and entry are untouched
   *(Covers FR199)*

6. **Given** the mod being installed is itself already installed (same mod ID, any case), under the same file name
   **When** I install it again
   **Then** the response is still 409 `MOD_ALREADY_INSTALLED` from the existing check (Story 17.3), not `MOD_FILE_CONFLICT`: the order of checks in `install_mod` is unchanged
   *(Covers FR199; regression guard)*

7. **Given** an install from a browse card or a mod detail page is refused with 409 `MOD_FILE_CONFLICT`
   **When** the response arrives
   **Then** the install dialog shows the "Installation failed" toast with the API's message (naming the file) and stays open; no web source change is needed for this
   *(Covers FR199)*

8. **Given** an installed mod whose stored update record does not list a release the mod database now has
   **When** I change the mod to that release from its detail page (`PUT /api/v1alpha1/mods/{slug}/version`)
   **Then** `GET /api/v1alpha1/mods/updates` reports a real status for it (`up_to_date` or `update_available`), not `unknown` with reason `installed_release_not_listed`, without an update check and with exactly one mod database lookup for the change
   *(Covers FR200; `VSS-do7`)*

9. **Given** a version change through `PUT /api/v1alpha1/mods/{slug}/version`
   **When** it succeeds
   **Then** the response `data` has exactly the keys `slug`, `previous_version`, `version`, `filename`, `compatibility`, `changed` and `pending_restart`, as before
   *(Covers FR200)*

10. **Given** Update All (`POST /api/v1alpha1/mods/updates/apply-all`) changes several mods
    **When** it finishes
    **Then** each changed mod's stored record comes from its own change's lookup, and a mod that failed or was skipped keeps its previous record
    *(Covers FR200)*

11. **Given** storing the record fails, or the version change fails, is refused for confirmation, or is rolled back, or the requested version is already installed
    **When** the request ends
    **Then** a storing failure does not fail the version change (200, same body, a warning is logged), and in the other cases the stored record is untouched
    *(Covers FR200)*

12. **Given** every existing test
    **When** the suites run
    **Then** they pass, apart from the changes listed in Dev Notes "Existing tests that change"; no test run writes into the dev data directory (`dev/`)

## Tasks / Subtasks

<!-- Each functional task includes its tests in the same commit. Commit per task: type(story-18.2/task-N): ...; feat/fix only for changes an admin can see, subject written for admins. Red first. -->

- [ ] Task 1: Install refuses a file name another mod uses + tests (AC: 1, 2, 3, 4, 5, 6, 12) (`VSS-z7e`)
  - [ ] 1.1: `services/mods.py`: new `ModFileConflictError(slug, filename)` after `ModOperationInProgressError` (`:180-187`), before `ModVersionChangeFailedError` (`:190`). Attributes `slug`, `filename`; message exactly `f"Cannot install '{slug}': a file named {filename} already exists in the mods directory."` (Epic 18 ADR-4 decision 4). Keep the line under 100 characters (ruff E501; the prototype's one-line f-string was 101)
  - [ ] 1.2: `services/mods.py` `_place_install` (`:1234`): the collision check is the first statement of the method, before `check_compatibility` (`:1243`), the `mkdir` and the copy (`:1259-1261`, `shutil.copy2` at `:1260`), and outside both `try` blocks (Dev Notes "The check"). Update the docstring: it refuses a file name in use before writing anything
  - [ ] 1.3: `install_mod` docstring (`:1154-1184`): add `ModFileConflictError` to Raises. Do not move, add or remove any other check: steps 1-7 (`:1185-1212`) stay as they are (AC 6)
  - [ ] 1.4: `models/errors.py`: `MOD_FILE_CONFLICT = "MOD_FILE_CONFLICT"` under "# Mod Installation", after `MOD_VERSION_CHANGE_FAILED` (`:67`)
  - [ ] 1.5: `routers/mods.py`: import `ModFileConflictError` in the `services.mods` import block (`:37-47`, alphabetical, after `ModAlreadyInstalledError` `:39`). `install_mod` (`:666`): a new `except ModFileConflictError as e:` before `except ModAlreadyInstalledError` (`:723`), status 409, `detail={"code": ErrorCode.MOD_FILE_CONFLICT, "message": str(e)}`. Docstring Raises (`:691-698`): `HTTPException: 409 if a file with the download's name (or its .disabled form) is already in the mods directory or the mod state`. That docstring is the route's API documentation (OpenAPI); there is no other API document that lists install errors (`rg MOD_ALREADY_INSTALLED` finds only code and tests)
  - [ ] 1.6: Tests (Dev Notes "API tests", Task 1 rows), red first

- [ ] Task 2: A version change stores the mod's update record from its own lookup + tests (AC: 8, 9, 10, 11, 12) (`VSS-do7`)
  - [ ] 2.1: `services/mods.py` `PreparedVersionChange` (`:212-218`): add `releases: list[StoredRelease]` with a docstring ("every release of the mod database entry, newest first, from the change's lookup; internal, never serialized (Epic 18 ADR-5)"). `_prepare_version_change` passes its `releases` local (`:1078`) in the return (`:1106`). `VersionChangeResult` (`:198-209`) does not change
  - [ ] 2.2: `services/mods.py` `change_version` (`:908-965`): new keyword-only parameter `record_releases: Callable[[str, list[StoredRelease]], None] | None = None` after `confirm` (`Callable` and `StoredRelease` are already imported, `:10`, `:19`). Directly after `filename = self._apply_version_change(state, prepared)` (`:941`), still inside `with self._hold(slug):` (`:925`): `if record_releases is not None: record_releases(slug, prepared.releases)`. Docstring: a completed change hands the lookup's releases to `record_releases`, under the mod's lock; the same-version return (`:929-938`) and every raise path never call it; the recorder must not raise
  - [ ] 2.3: `services/mod_updates.py` `ModUpdateService` (Dev Notes "Recording"): a private `_store_record(modid, releases: list[StoredRelease])` that builds the `StoredModRecord`, sets it, clears the lookup error and saves (may raise); `record_releases(modid, releases: list[StoredRelease]) -> None` (public, never raises, logs `mod_update_record_after_version_change_failed`); `record_install` (`:348-366`) keeps its signature, behavior and log event, and now converts the raw releases and calls `_store_record` inside its existing `try`
  - [ ] 2.4: `routers/mods.py` `change_mod_version` (`:1031`): add `update_service: ModUpdateService = Depends(get_mod_update_service)` (already imported, `:31-36`) and call `service.change_version(slug, request.version, confirm=request.confirm, record_releases=update_service.record_releases)` (`:1044`). The response stays `ApiResponse(status="ok", data=asdict(result))` (`:1071`). Docstring: one sentence that a completed change stores the mod's update record from its own lookup
  - [ ] 2.5: `routers/mods.py` `apply_all_mod_updates` (`:150-173`): `update_service.apply_all(partial(mod_service.change_version, record_releases=update_service.record_releases))` (`:164`), with `from functools import partial` (stdlib import block, `:3-5`). `ChangeVersion` (`services/mod_updates.py:263-264`) and `apply_all` (`:368`) do not change; extend `ChangeVersion`'s docstring: the route binds the recorder. Pyright strict accepts the `partial` against `ChangeVersion` (checked with a prototype: 0 errors)
  - [ ] 2.6: Tests (Dev Notes "API tests", Task 2 rows) and the fixture change in "Existing tests that change", red first

- [ ] Task 3: Web shows the refusal: unit test pin + E2E tests against the Docker dev stack (AC: 7)
  - [ ] 3.1: `web/src/components/InstallConfirmDialog.test.tsx` "error callback" block (`:418-480`): a mutation failing with `new ApiError('MOD_FILE_CONFLICT', CONFLICT, 409)` (CONFLICT = `"Cannot install 'carrycapacity': a file named Foo.zip already exists in the mods directory."`) calls `toast.error('Installation failed', { description: CONFLICT })` and `onOpenChange` is not called with `false` (copy the busy test at `:455-479`). It passes against the current source; it pins AC 7. No web source change (Dev Notes "Web")
  - [ ] 3.2: New `web/e2e/install-file-conflict.spec.ts` (Dev Notes "E2E"): the install POST is stubbed with `page.route`; nothing is installed. Rebuild the stack from this branch first (`just docker restart`), run `cd web && bunx playwright test e2e/install-file-conflict.spec.ts` with the admin key from `.env`; also re-run `e2e/mod-install-release.spec.ts` and `e2e/installed-status.spec.ts`. Do not start or stop the game server; no screenshots
  - [ ] 3.3: Record in the Dev Agent Record that `GET /api/v1alpha1/mods` returned the same body before and after the run

- [ ] Task 4: Quality gate and review hand-off (AC: all)
  - [ ] 4.1: `just check` passes; the diff adds no lint or type suppression and no `cast`; pyright stays at 0 errors and the 3 pre-existing warnings (`VSS-1ar`); after `just test-api`, `git status --short` shows nothing under `dev/`
  - [ ] 4.2: Manual check on the Docker stack (needs the maintainer's confirmation before it is ticked, `project-context.md`): see Dev Notes "Manual check"
  - [ ] 4.3: Story status `review`, `just sprint set 18-2-install-and-version-change-keep-records-right review`, PR (base: Story 18.1's branch while its PR is open, otherwise `main`), PR link on `VSS-z7e` and `VSS-do7`. The PR description lists "API contract changes" from this story

## Dev Notes

### The bugs (verified at b9606f1)

- **File-name collision on install (`VSS-z7e`).** `install_mod` (`services/mods.py:1149-1212`) holds the lock of the install mod ID (`:1202`), downloads, checks the archive's own mod ID (`:1206-1210`) and calls `_place_install` (`:1212`). `_place_install` copies the cached archive to `<name>.tmp` and renames it over `mods_dir/<name>` (`:1246-1261`); a rename replaces an existing file. If the import or state save then fails, the cleanup unlinks `dest_path` (`:1299`) and removes the state entry under `<name>` (`:1301`), both of which then belong to the other mod. Story 17.3's checks (`_refuse_if_installed`, `:1214-1232`) compare mod IDs, so they miss two different mod IDs whose release files share a name, and they skip an archive whose `modinfo.json` cannot be read (`archive is None`, `:1207`).
- **Stale update record after a version change (`VSS-do7`).** `_prepare_version_change` fetches the entry and builds `releases = [StoredRelease.from_api(r) ...]` (`:1078`), then drops them. Only installs store a record (`routers/mods.py:704`, `record_install`). A change from the detail page to a release published after the last check leaves the stored list without the installed version, so `build_status_items` (`services/mod_updates.py:217-241`) gives `unknown` / `installed_release_not_listed` until the next check. Confirmed with a prototype router test: stored record holding only carryon `1.14.1`, change to `1.14.3`; with the recorder the status is `up_to_date` and the lookup ran once.

### The check (Task 1)

```python
def _place_install(self, slug: str, download_result: DownloadResult, releases: list[ReleaseDict]) -> InstallResult:
    """...Refuses before writing anything when the file name is in use (Epic 18 ADR-4)..."""
    name = download_result.filename
    mods_dir = self._state_manager.mods_dir
    for candidate in (name, f"{name}.disabled"):
        if (
            (mods_dir / candidate).exists(follow_symlinks=False)
            or self._state_manager.get_mod(candidate) is not None
        ):
            raise ModFileConflictError(slug, candidate)
    # ...existing body unchanged...
```

- **Order: `<name>` first, then `<name>.disabled`.** The error names the first name in use, so AC 1 names `Foo.zip` and AC 2 names `Foo.zip.disabled`; the admin sees which file to remove or rename. This deviates slightly from ADR-4 decision 4, which says "names the file" without saying which; see "ADR against the code".
- **`exists(follow_symlinks=False)`** is true for a dangling symlink (ADR-4 decision 1). Python is 3.14 (`api/pyproject.toml:5`), so the argument is available. `get_mod` (`services/mod_state.py:138-147`) is an exact key lookup; state is keyed by file name.
- **`slug`** is the requested slug after `extract_slug` (the one `_place_install` already logs), as in ADR-4's message. The error does not need the other mod's ID: the file name is what the admin acts on.
- **Nothing to clean up.** The check runs before the `.tmp` copy (`:1260`) and outside both `try` blocks, so no `.tmp` file is created and the cleanup at `:1296-1307` never runs for a refusal. The downloaded archive stays in the download cache (`cache/mods/<name>`), as it does for every other refusal after the download (Story 17.3's step 6); it is a cache, not a temp file, and a later version change validates a cached archive before use (`_acquire_release_archive`, `:1108-1128`).
- **Order of checks (AC 6).** Re-installing the same mod is refused earlier, by `_refuse_if_installed` at steps 2, 4 and 6 (`:1191`, `:1199`, `:1210`, case-insensitive since Story 17.3's review M1). Those run before `_place_install`, so `MOD_ALREADY_INSTALLED` still wins for a mod that is already installed; the new check only sees different mods or unreadable archives. A prototype test (`install_mod("modb")` with `modb` installed as `Foo.zip`) confirmed `ModAlreadyInstalledError`.
- **Unreadable `modinfo.json` (AC 4).** `read_modinfo` returns `None` (`services/mod_state.py:253-269`), step 6 is skipped (`:1207`), and the new check refuses. Prototype: the enabled and `.disabled` cases with a readable and an unreadable archive (4 cases) all raised `ModFileConflictError`, left the other mod's file bytes and state unchanged, left exactly one file in the mods directory, and released the lock.

### Concurrency (Task 1)

- **The check runs under the install lock.** `_place_install` is called inside `with self._hold(resolved.mod_id):` (`:1202-1212`) and is synchronous: there is no `await` between the check and the state save (`:1295`). Every route is `async def` on one event loop and `enable_mod`, `disable_mod` and `remove_mod` are synchronous too (their docstrings, `:699-701`, `:757-759`, `:815-817`), so nothing can rename or create a file in the mods directory between the check and the rename. The API runs one uvicorn worker (`Dockerfile:91`).
- **Two different mods racing for the same name.** They hold different locks (`mod-a`, `mod-b`), so their lookups and downloads can overlap. Each `_place_install` runs to completion without yielding. The first one places its file and saves its state; the second one's check then sees the file and the state entry and is refused with 409 `MOD_FILE_CONFLICT`. No in-process race remains for the mods directory or the state.
- **Residual race, out of scope (follow-up).** Both downloads of that race write the same cache path, `cache/mods/<name>` via `<name>.tmp` (`services/mod_api.py:529-546`, opened `"wb"` by each), so the cached archive one install copies may be the other mod's, or a mix. Step 6 refuses a readable foreign archive while its mod is busy (`_refuse_if_busy(archive.modid)`, `:1208-1209`); a mixed, unreadable archive would be placed. This is pre-existing (it does not depend on this story) and needs two different mods with the same release file name installed within the same seconds. Not fixed here; listed for the maintainer under follow-ups in the PR.

### Recording (Task 2)

```python
def record_install(self, modid: str, releases: list[ReleaseDict]) -> None:
    """(docstring unchanged)"""
    try:
        self._store_record(modid, [StoredRelease.from_api(r) for r in releases])
    except (OSError, ValueError, TypeError) as e:
        logger.warning("mod_update_record_after_install_failed", slug=modid, error=str(e))

def record_releases(self, modid: str, releases: list[StoredRelease]) -> None:
    """Store a mod's releases from a completed version change's lookup (Story 18.2, ADR-5).

    Never raises: a failure is logged and the mod keeps its previous record until the
    next check (or, if only the save failed, the record lives in memory until restart).
    """
    try:
        self._store_record(modid, releases)
    except (OSError, ValueError, TypeError) as e:
        logger.warning("mod_update_record_after_version_change_failed", slug=modid, error=str(e))

def _store_record(self, modid: str, releases: list[StoredRelease]) -> None:
    record = StoredModRecord(checked_at=datetime.now(UTC), found=True, releases=releases)
    self._store.set(modid, record)
    self._store.clear_lookup_error(modid)
    self._store.save()
```

- **Same record as a check and an install.** `_check_one` stores `_record_from_payload(get_mod(slug))` (`services/mod_updates.py:503-539`): `found=True`, every release through `StoredRelease.from_api`. `_prepare_version_change` builds exactly that list from the same normalized `get_mod` (`services/mods.py:1074-1078`). No extra lookup.
- **Key.** `change_version`'s `slug` is the installed mod ID exactly (`get_mod_by_slug` is an exact match, `services/mod_state.py:149-161`), which is what `build_status_items` looks up (`store.get(mod.slug)`).
- **Only a completed change records (ADR-5 decision 6).** The same-version return (`:929-938`) makes no lookup. `ModConfirmationRequiredError`, `ModValidationError`, `ModVersionNotFoundError`, `ModReleaseNotDownloadableError`, `ExternalApiError`/`DownloadError` raise in `_prepare_version_change` before the recorder; `ModVersionChangeFailedError` (including after `_rollback_version_change`) raises out of `_apply_version_change` before it. Nothing to add for these: placing the call after `_apply_version_change` returns is the whole rule.
- **A recorder failure never fails the change (ADR-5 decision 7).** `record_releases` catches what `record_install` catches. `change_version` does not wrap the call: a recorder that raises anything else is a bug and must surface, as for `record_install`.
- **Under the lock.** The call is inside `with self._hold(slug):`, so the record cannot be written by a change that another operation on the same mod has already superseded. `record_releases` is synchronous; a running `check()` cannot interleave between its `set` and `save` (same reasoning as Story 17.4, "Check and install at the same time"). If a check's own lookup of that mod finished before the change and the check then saves, it may store its older list over the new one; the next check corrects it. Not changed.
- **`checked_at`.** The record's `checked_at` becomes the time of the change; `last_full_check` and the `notified` versions are untouched, so webhook alerts behave as before (ADR-5 consequences).
- **Update All.** `apply_all` iterates `self.get_status()` computed once before the loop (`services/mod_updates.py:393`), a list, so recording during the loop does not change what it iterates. Each `change_version` call records its own mod under its own lock. A skipped or failed mod records nothing.

### Web (Task 3)

- `InstallConfirmDialog` is the only install UI for mods: `ModDetailPage.tsx:265` and `ModCard.tsx:231` render it. Its call-level `onError` shows `toast.error('Installation failed', { description: error.message })` and keeps the dialog open (`components/InstallConfirmDialog.tsx:117-122`). `error.message` is the API's `detail.message` (`api/client.ts:95-123`), so the 409 message naming the file reaches the admin without a code mapping. No web code switches on `MOD_ALREADY_INSTALLED` or other install codes (`rg` finds them only in tests), so an unknown code needs nothing.
- Pre-existing, not changed: `useInstallMod` (`hooks/use-mods.ts:88-99`) has no hook-level `onError`, so the query client's default (`api/query-client.ts:34-39`, `handleApiError` → `toast.error('Error', { description })`, `api/error-handler.ts:29-32`) also runs. A failed install therefore shows two toasts with the same message ("Error" and "Installation failed"). This applies to every install error, not only this one. The E2E asserts the "Installation failed" toast and does not count toasts; record what the browser showed in the Dev Agent Record. Follow-up for the maintainer (not this story's scope: the epic says "no other web change").

### API tests

| Task | File | Test |
|---|---|---|
| 1 | `tests/test_mod_operation_lock.py` (has `make_service`, `mock_mod`, `mod_files`, `state_of`, and the imported `mod_zip_bytes`; `:37-123`) or a new class in `tests/test_mod_service.py` | New class `TestInstallRefusesAFileNameInUse`: mod A (`moda`) placed as `Foo.zip`, then as `Foo.zip.disabled` (parametrize), with a state entry; mod B's lookup has one release `modidstr: "modb"`, `filename: "Foo.zip"`; its archive's `modinfo.json` readable (`modb`) and unreadable (zip without `modinfo.json`) (parametrize). `install_mod("modb")` raises `ModFileConflictError` with `filename` the name in use; A's bytes and `state_of(service, "moda")` equal their values before; `mod_files(service)` equals its value before (no `.tmp`); `get_mod_by_slug("modb") is None`; `service.busy_mod_ids == frozenset()`; the state file on disk (reload a `ModStateManager`) has only A. The 4-case prototype of this test passed |
| 1 | same | A stray file `Foo.zip` with no state entry → refused, bytes unchanged, still no state entry. A state entry `Foo.zip` (slug `moda`) with no file → refused, entry unchanged, no file created |
| 1 | same | AC 6: `modb` installed as `Foo.zip`; `install_mod("modb")` raises `ModAlreadyInstalledError` (not `ModFileConflictError`); also with the installed spelling `ModB` |
| 1 | same | AC 5: no collision, `import_mod` fails (follow `TestInstallReleasesTheLock::test_i9_after_a_failed_import`, `:690-714`) while another mod `moda` is installed as `Other.zip`: B's file and entry are gone, `Other.zip` bytes and A's entry unchanged |
| 1 | `tests/test_mods_router.py` `TestInstallModEndpoint` (`:91`) | `POST /mods {"slug": "smithingplus"}` with another mod (`othermod`) already placed as `smithingplus_1.8.3.zip` (the release file name in `SMITHINGPLUS_MOD`, `:73-88`) and synced into state (as `test_install_mod_already_installed`, `:377-400`, does): 409, body exactly `{"detail": {"code": "MOD_FILE_CONFLICT", "message": "Cannot install 'smithingplus': a file named smithingplus_1.8.3.zip already exists in the mods directory."}}`; the file's bytes unchanged; `GET /mods` lists only `othermod`; nothing in `GET /mods/updates` for `smithingplus` (no record stored: `record_install` runs only after a successful install) |
| 2 | `tests/test_mod_version_change.py` `TestChangeVersion` (`:496`) | With `record_releases` collecting `(slug, releases)` calls: a completed update calls it once with `"carryon"` and releases equal to `[StoredRelease.from_api(r) for r in fixture_json("carryon")["mod"]["releases"]]`; inside the call `"carryon" in service.busy_mod_ids` (record it in the callback). Not called: same version (`test_same_version_is_a_no_op` shape), confirmation required (`test_confirmed_prerelease_change` first call), archive validation failure (`ModValidationError`), state save failure with rollback (`test_state_save_failure_rolls_back` shape), another mod's file in the way (`test_existing_file_of_another_mod_is_not_overwritten` shape). Without `record_releases` every existing test passes unchanged |
| 2 | `tests/test_mod_updates.py` (`make_service` `:324`, `installed` `:198`, `fixture_releases` `:32`) | New `TestRecordReleases`: `record_releases("carryon", fixture_releases("carryon"))` with `carryon` at `1.14.3` stores the record (persisted, `checked_at` set, lookup error cleared) and the status is not `unknown`; a failing `store.save` logs `mod_update_record_after_version_change_failed` at warning level and does not raise. `TestRecordInstall` (`:647-708`) passes unchanged (same log event) |
| 2 | `tests/test_mod_version_change_router.py` | AC 8: seed the update service's store with a carryon record holding only release `1.14.1` (installed version, so the status before is `up_to_date`); `PUT` to `1.14.3` returns 200; then `GET /mods/updates` for carryon has `status` `up_to_date`, `reason` null, `installed_version` `1.14.3`, and the lookup route's `call_count == 1`. Red first: without the recorder it is `unknown` / `installed_release_not_listed` (prototype confirmed both). AC 9: `set(response.json()["data"]) == {"slug", "previous_version", "version", "filename", "compatibility", "changed", "pending_restart"}`. AC 11: `store.save` monkeypatched to raise `OSError` gives 200 with the same body as `test_successful_update` (`:109-128`), the state at `1.14.3`, and the `mod_update_record_after_version_change_failed` warning (`captured_logs`, `conftest.py:73`); a request for `2.0.0-rc.1` without `confirm` (409) and a request for the installed `1.14.1` (`changed: false`) leave the stored record equal to the seeded one |
| 2 | `tests/test_mod_update_all_router.py` | AC 10: install a second mod `demo` at `1.0.0` beside carryon (entry shape of `test_mod_operation_lock.entry`, `:37-51`, built inline). Seed both stored records so they still offer an update but differ from the lookups: carryon with only `1.14.3` and `1.14.1`; demo with `1.1.0` and `1.0.0`, while demo's lookup also lists a newer `1.2.0-rc.1` (a stable install is never offered a pre-release, `evaluate_update`, `services/mod_updates.py:101-108`, so the offer stays `1.1.0`). After the run both are `updated`; `store.get("carryon").releases` equals carryon's full fixture list and `store.get("demo").releases` equals demo's three releases, each through `StoredRelease.from_api`; both `checked_at` are later than the seeded `2026-11-09`. Second test: demo's download returns 500, so demo is `failed` and its record equals the seeded one, while carryon's is refreshed |

### Existing tests that change (deliberately)

Found by running the whole API suite against a throwaway prototype of Tasks 1 and 2 (since discarded): 2682 passed, none failed. One fixture must change anyway:

- **Not failing, but must change:** `api/tests/test_mod_version_change_router.py:80-89` (`client`) must also override `get_mod_update_service` with `ModUpdateService(store=ModUpdateStore(tmp_path / "state"), mod_source=service, game_version_provider=lambda: "1.22.7")` (expose it as a fixture so the new tests can seed and read its store). Without it the prototype passed but wrote `dev/vsmanager/state/mod-updates.json` (`just test-api` sets `VS_DATA_DIR=../dev`) through the real singleton, as Story 17.4 found for the install route. `test_mod_update_all_router.py` (`:95-107`), `test_mods_router.py` (`TestInstallModEndpoint.test_app`, `:134-143`) and `test_mod_operation_lock_router.py` (`:114-133`) already override it; the prototype left `dev/` empty for them.
- `test_mod_version_change_router.py::test_service_errors_map_to_responses` (`:257-274`) replaces `change_version` with `fail(*args, **kwargs)`, so the new keyword is absorbed; unchanged.
- `test_mod_update_all.py` passes a fake `change_version(slug, version)` straight to `apply_all`; unchanged, since the binding is in the route.
- Environment note: in a fresh worktree without `.env`, `just test-api` reports 77 errors and 6 failures from `VS_API_KEY_ADMIN` being unset (lifespan, scheduler, jobs router, console WebSocket tests). They are not caused by this story; set the variable (or work where `.env` exists) before reading results.
- Anything else that fails is a regression (AC 12): fix the code, not the test.

### E2E (`web/e2e/install-file-conflict.spec.ts`)

Style of `e2e/mod-install-release.spec.ts` (helpers `fakeNoInstalledMods` `:77-85` and `stubInstall` `:88-112`; copy them, do not import across specs) and `e2e/mod-detail-bad-data.spec.ts` (header comment with requirements, `firstCardSlug`). Header: Story 18.2, FR199, the install POST is stubbed so nothing is installed.

- `stubConflict(page)`: `page.route(/\/api\/v1alpha1\/mods(\?.*)?$/)`, `route.fallback()` unless the method is `POST`; fulfill status 409, JSON `{"detail": {"code": "MOD_FILE_CONFLICT", "message": "Cannot install '<slug from the request body>': a file named Stub-1.0.0.zip already exists in the mods directory."}}`; count the POSTs.
- **Detail page.** `fakeNoInstalledMods(page)`, `stubConflict(page)`, open `/game-server/mods/browse/carryon` (live lookup; wait for `mod-detail-install-button`, timeout 60 s), click it, click `install-dialog-confirm`. Expect a toast (`page.locator('[data-sonner-toast]').filter({ hasText: 'Installation failed' })`) containing `a file named Stub-1.0.0.zip already exists in the mods directory`; `install-confirm-dialog` still visible; exactly one POST.
- **Browse card.** Same stubs; open `/game-server/mods/browse?q=carry&sort=downloads`, read the first card's slug (`firstCardSlug`), click `mod-card-install-<slug>`, confirm, same assertions with that slug in the message.
- No real state changes: compare `GET /api/v1alpha1/mods` (via `request`, admin key) before and after in the Dev Agent Record. Do not start or stop the game server. No screenshots.

### Manual check (Task 4.2)

On the Docker stack built from this branch, with the same stubs as the E2E (run the spec headed, `bunx playwright test e2e/install-file-conflict.spec.ts --headed`, or stub in the browser's dev tools): the refusal reads well in the toast, the dialog stays open and can be cancelled, and note whether the duplicate "Error" toast appears (see "Web"). Do not change a real mod's version for this check: a change cannot be undone exactly (the stored record's `checked_at` and the release list change), and AC 8 is covered by the router test. Do not start or stop the game server; no screenshots. The maintainer ticks 4.2.

### Not changed (do not "fix" these here)

- The version change's own refusal stays 500 `MOD_VERSION_CHANGE_FAILED` (`services/mods.py:979-982`); `enable_mod` and `disable_mod` still rename without checking the target name (`:730`, `:788`). Both are follow-ups (ADR-4 decision 6; change proposal open items 1-2).
- `VersionChangeResult`, `asdict(result)` and the response of `PUT /mods/{slug}/version` (ADR-5 decision 1); `ChangeVersion` and `apply_all`'s signature.
- The download cache sharing one path per release file name across mods (see "Concurrency").
- The duplicate "Error" toast on a failed install (see "Web").
- The install flow's checks and their order (Story 17.3), and `record_install`'s behavior and log event (Story 17.4).

### API contract changes

- `POST /api/v1alpha1/mods`: new error 409 `MOD_FILE_CONFLICT` when the download's file name, or its `.disabled` form, is already in the mods directory or the mod state. Message: `Cannot install '<slug>': a file named <name> already exists in the mods directory.` Before, the install succeeded and replaced the other file. New error code; behavior change.
- `PUT /api/v1alpha1/mods/{slug}/version` and `POST /api/v1alpha1/mods/updates/apply-all`: responses unchanged. A completed change now stores that mod's update record, so `GET /api/v1alpha1/mods/updates` reports its status at once (side effect only).

### ADR against the code

- **ADR-5 decision 4** says `record_install` "becomes a thin wrapper" around `record_releases`. Done literally, a failed save after an install would log the version change's event, and three Story 17.4 tests assert `mod_update_record_after_install_failed` (`tests/test_mod_updates.py:690`, `:708`, and the router test from 17.4's review L3, `tests/test_mods_router.py:254`). So both public methods share a private `_store_record` and keep their own log event; the behavior ADR-5 asks for is unchanged.
- **ADR-4 decision 4** gives one message naming "the file". The story names the name actually in use, so the `.disabled` case says `Foo.zip.disabled` (AC 2). For a state entry without a file (AC 3) the message still says the file "already exists in the mods directory": the state is the API's record of the mods directory, and one message keeps the contract simple.
- Everything else in ADR-4 and ADR-5 matches the code at b9606f1 (line numbers re-read).

### Testing Requirements

**CRITICAL:** Tests are written with each task and committed with it, red first. `just test-api <file>` / `just test-web <file>` after each task; `just check` before review.

- API tests use respx on `https://mods.vintagestory.at/api/mod/{slug}` and `https://mods.vintagestory.at/download`. Fixtures under `api/tests/fixtures/moddb/` are captured data and are not changed; synthetic entries are built in the tests.
- Compare file bytes and state before and after for every refusal; "nothing placed" means the sorted list of the mods directory is unchanged.
- Router tests must inject a `ModUpdateService` on a temp directory; `git status --short` after `just test-api` must show nothing under `dev/`.
- Tests must not read private members (`reportPrivateUsage`); use `ModUpdateService.store`, `ModService.busy_mod_ids`, `ModService.state_manager`.

### Security Requirements

- No new endpoint; `POST /mods`, `PUT /mods/{slug}/version` and `POST /mods/updates/apply-all` stay Admin-only. The 409 message contains the requested slug and a release file name already sanitized by `safe_release_filename` (`services/mod_api.py:142-154`); both are mod database data, not paths outside the mods directory. The web renders the message as toast text. The stored record holds mod database data only, as after a check.

### Development Commands

- `just test-api tests/test_mod_operation_lock.py tests/test_mod_service.py tests/test_mods_router.py tests/test_edge_cases.py`, `just test-api tests/test_mod_version_change.py tests/test_mod_version_change_router.py tests/test_mod_update_all_router.py tests/test_mod_updates.py`, `just test-web src/components/InstallConfirmDialog.test.tsx`, `just typecheck-api`, `just lint-api`, `just check`.
- Do not run `just format-api` (reformats unrelated files; Story 17.2 process note).

### Previous Story Intelligence

- **17.3:** `install_mod` order (resolve, checks, `_hold`, download, archive check, `_place_install`) stays; nothing awaited is added inside the held section. Its review L1 created `VSS-z7e`. Its Task 4 finding: a hook-level `onError` replaces the query client's default, so such a hook must call `handleApiError` itself; this story adds no hook (and see "Web" for the opposite effect on install).
- **17.4:** `record_install` and the router override pattern for `get_mod_update_service`; its Dev Notes "Remove and version change" describe `VSS-do7`. Router tests without the override write into `dev/`.
- **17.2:** E2E that changes real state needs a snapshot guard and must restore the stack exactly; this story's E2E changes nothing. `feat`/`fix` subjects must describe what an admin can see.
- **17.x reviews:** a completion note must be true of the code; manual checks wait for the maintainer.

### Git Intelligence

- Base `b9606f1` (`docs(epic-18): plan epic 18 mod media and fixes`) on `574e125` (Epic 17 merged). Story 18.1 lands first and touches `routers/mods.py` and `models/mods.py` in other places.
- Planned commits: Task 1 `fix(story-18.2/task-1): installing a mod no longer replaces another mod's file with the same name` (VSS-z7e; an admin sees a 409 naming the file instead of a silently overwritten mod). Task 2 `fix(story-18.2/task-2): the Installed list shows the right update status right after a version change` (VSS-do7; an admin no longer sees "Unknown" after changing to a newly published release). Task 3 `test(story-18.2/task-3): ...`. Task 4 `docs(story-18.2): ...`.

### Project Structure Notes

- New: `web/e2e/install-file-conflict.spec.ts`.
- Modified: `api/src/vintagestory_api/services/mods.py`, `services/mod_updates.py`, `routers/mods.py`, `models/errors.py`; `api/tests/test_mod_operation_lock.py` (or `test_mod_service.py`), `test_mods_router.py`, `test_mod_version_change.py`, `test_mod_version_change_router.py`, `test_mod_update_all_router.py`, `test_mod_updates.py`; `web/src/components/InstallConfirmDialog.test.tsx`. No fixture, no web source file.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 18.2: Install and Version Change Keep Files and Records Right]
- [Source: _bmad-output/planning-artifacts/prd.md] FR199, FR200
- [Source: _bmad-output/planning-artifacts/architecture/epic-18-mod-media-and-fixes.md#ADR-4, #ADR-5]
- [Source: _bmad-output/planning-artifacts/architecture/epic-17-mod-data-fixes.md] (ADR-1 normalized releases; ADR-3 install lock)
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-16.md] (API change table; open items 1-3)
- [Source: _bmad-output/implementation-artifacts/17-3-mod-operations-are-safe-against-each-other.md], [17-4-installed-status-is-right-everywhere.md]
- Beads: `VSS-z7e`, `VSS-do7`, parent `VSS-5w8`
- `project-context.md` (no suppressions; manual test tasks need the maintainer's confirmation; commit format)

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

- Story created 2026-11-16 (create-story, non-interactive) and validated against the create-story checklist. A throwaway prototype of Tasks 1 and 2 (the check, the error and route mapping, `PreparedVersionChange.releases`, the `record_releases` parameter, `ModUpdateService.record_releases`, both routes) was run against the whole API suite (2682 passed), pyright (0 errors, 3 warnings) and four collision cases plus the re-install case, then discarded.

### File List

## Change Log

- 2026-11-16: Story 18.2 created and validated (ready-for-dev).
