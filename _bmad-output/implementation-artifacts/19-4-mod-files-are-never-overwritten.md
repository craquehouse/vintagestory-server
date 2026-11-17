# Story 19.4: Mod Files Are Never Overwritten

Status: review

<!-- Implements FR218-FR223, Epic 19 ADR-8, ADR-9 and ADR-11. Beads: VSS-52fy (API-085), VSS-40ja (API-082, bug), VSS-macf (API-083), VSS-yhmt (API-091, bug), VSS-uoxl (API-092; stays open after this story and is closed with Story 19.5), VSS-n0qv (API-084). Stories run in order 19.1 to 19.7, each stacked on the previous. Line references were verified at b6ae2f2 (epic-19-planning; its api/ and web/ equal the code the ADRs cite at 048fea9, shifted by Story 18.2's lines) and must be re-checked at implementation time: Stories 19.2 and 19.3 rework the start-up in main.py (app factory, one settings object) and the router test fixtures that build the app. API change, web unit test pins and one E2E spec; no web source change. No new dependencies. -->

## Story

As an **administrator**,
I want **no mod operation to replace or lose a mod's file, on any volume and after a crash**,
so that **the mods directory always holds what the Installed list says**.

## Acceptance Criteria

1. **Given** mod A is disabled as `Foo.zip.disabled` and another file `Foo.zip` is in the mods directory
   **When** I enable mod A (`POST /api/v1alpha1/mods/{slug}/enable`)
   **Then** the response is 409 `MOD_FILE_CONFLICT` with the message `Cannot enable '<slug>': a file named Foo.zip already exists in the mods directory.`; both files have the same bytes as before, the mod state is unchanged (in memory and on disk) and no restart is pending
   *(Covers FR218; `VSS-40ja`)*

2. **Given** mod A is enabled as `Foo.zip` and a file `Foo.zip.disabled` is in the mods directory
   **When** I disable mod A
   **Then** the response is 409 `MOD_FILE_CONFLICT` (`Cannot disable '<slug>': a file named Foo.zip.disabled ...`) and nothing is changed
   *(Covers FR218; `VSS-40ja`)*

3. **Given** no file is in the way
   **When** I enable or disable a mod
   **Then** it works as before, and enabling an enabled mod or disabling a disabled one is still a success that changes nothing, also when the mod's own file is missing or a file is in the way (the idempotent return stays first)
   *(Covers FR218, FR222)*

4. **Given** an installed mod and a target release whose file name, or its `.disabled` form, is another file in the mods directory or another entry in the mod state
   **When** I change the mod's version (`PUT /api/v1alpha1/mods/{slug}/version`)
   **Then** the response is 409 `MOD_FILE_CONFLICT` (`Cannot change the version of '<slug>': a file named <name> already exists in the mods directory.`), not 500 `MOD_VERSION_CHANGE_FAILED`, and the mod's file, the other file and the state are unchanged; no stored update record is written
   *(Covers FR219; `VSS-macf`)*

5. **Given** Update All (`POST /api/v1alpha1/mods/updates/apply-all`), and one mod's new file name is taken
   **When** the run reaches it
   **Then** that mod is a `failed` item whose `error` is the conflict message, and the run continues with the other mods
   *(Covers FR219)*

6. **Given** a version change that fails to place the file or save state for another reason
   **When** it is rolled back
   **Then** the response is 500 `MOD_VERSION_CHANGE_FAILED`, as before, and the original file is back under its original name
   *(Covers FR219)*

7. **Given** a mods directory with `Foo.zip` installed, on any volume (the tests run on a case-sensitive directory in CI)
   **When** I install, enable, disable or change to a version of another mod whose file would be `foo.zip` or `FOO.ZIP.disabled`
   **Then** the response is 409 `MOD_FILE_CONFLICT`, the message names the file in the way as it is spelled in the directory (`Foo.zip`), and nothing is placed
   *(Covers FR220; `VSS-52fy`)*

8. **Given** an installed mod `Foo_1.0.zip`
   **When** I change it to a release whose file name differs from its own only in case (`foo_1.0.zip`)
   **Then** the change succeeds, the state names `foo_1.0.zip`, and exactly one file for the mod is in the directory afterwards, on a case-sensitive and on a case-insensitive volume; when that change is rolled back, the original file is back as `Foo_1.0.zip` and no `foo_1.0.zip` is left
   *(Covers FR220)*

9. **Given** a dangling symlink with the target name, or a mod state entry under the target name with no file
   **When** I run any of the four operations (install, enable, disable, version change)
   **Then** the response is 409 `MOD_FILE_CONFLICT`
   *(Covers FR218, FR219, FR220)*

10. **Given** two mods whose releases have the same file name
    **When** I download both, one after the other or at the same time
    **Then** each is cached under its own file ID (`cache/mods/<fileid>/<name>`), neither replaces the other's copy, and each install places the archive of the mod that was asked for
    *(Covers FR221; `VSS-n0qv`)*

11. **Given** two downloads of the same release at the same time
    **When** both finish
    **Then** the cache holds one complete file and no temporary file is left
    *(Covers FR221)*

12. **Given** a cache with files from before this story (directly under `cache/mods`), and a temporary file in the new layout left by a crash more than an hour ago
    **When** the API starts and the next download finishes
    **Then** the old files are removed at start and their number logged; eviction counts and evicts files in the new layout, removes the directories it emptied, and removes the old temporary file (also when eviction is disabled); a temporary file younger than an hour is kept
    *(Covers FR221)*

13. **Given** an installed mod whose own file was removed from the mods directory by hand
    **When** I enable or disable it
    **Then** the response is 409 `MOD_FILE_MISSING` with the message `Cannot enable '<slug>': its file <name> is no longer in the mods directory. Remove the mod and install it again.` (or `Cannot disable`), never a 500, and the mod state is unchanged
    *(Covers FR222; `VSS-yhmt`)*

14. **Given** that mod
    **When** I remove it through the manager
    **Then** the removal succeeds
    *(Covers FR222)*

15. **Given** a mods directory left by an interrupted install or version change: an unplaced working copy (`<name>.vsm-tmp`); a kept-aside original (`<name>.vsm-bak`) whose file is missing; a kept-aside original beside a new file that the mod state does not describe; and one beside a new file that it does
    **When** the API starts
    **Then** the working copy is deleted, the first two originals are put back, the last is deleted, each action is logged, every mod's file matches its state, and this runs once, before the scheduler and the game server auto-start; a failed action is logged and start-up continues
    *(Covers FR223; `VSS-uoxl`)*

16. **Given** files named `something.bak` or `something.tmp` that the manager did not create under its own suffixes
    **When** the API starts
    **Then** they are named in one warning and are neither deleted nor renamed
    *(Covers FR223)*

17. **Given** a leftover working file for a name (`<name>.vsm-tmp`, `<name>.vsm-bak`, or an old-style `<name>.tmp`)
    **When** I install, enable, disable or change the version of a mod with that file name
    **Then** the leftover does not cause a `MOD_FILE_CONFLICT`
    *(Covers FR223)*

18. **Given** enable, disable or a version change is refused with 409 `MOD_FILE_CONFLICT` or `MOD_FILE_MISSING`
    **When** the response arrives in the web UI
    **Then** the Installed page shows the API's message in a toast (enable/disable: "Error"; version change: "Failed to update <name>"), the toggle shows the mod's previous state, and an Update All failed item shows `Failed: <message>`; no web source change is needed for this
    *(Covers FR218, FR219, FR222)*

19. **Given** every existing test
    **When** the suites run
    **Then** they pass, apart from the changes listed in Dev Notes "Existing tests that change"; no test run writes into, renames or deletes anything in the dev data directory (`dev/`)

## Tasks / Subtasks

<!-- Six tasks, the project's limit (Epic 19 "Size"); do not add a seventh. Each functional task includes its tests in the same commit, red first. Commit per task: type(story-19.4/task-N): ...; feat/fix only for changes an admin can see, subject written for admins (Dev Notes "Git Intelligence"). -->

- [x] Task 1: One case-insensitive file-name check, used by install + tests (AC: 7, 9, 19) (`VSS-52fy`)
  - [x] 1.1: `services/mods.py`: `ModFileOperation = Literal["install", "enable", "disable", "change the version of"]` (add `from typing import Literal`). `ModFileConflictError` (`:191-200`) becomes `__init__(self, slug: str, filename: str, *, operation: ModFileOperation)`, keeps `slug` and `filename`, adds `operation`, message `f"Cannot {operation} '{slug}': a file named {filename} already exists in the mods directory."` (Epic 19 ADR-8 decision 6). Docstring: "Raised when a name a mod operation would create is taken (Epic 19 ADR-8)". Keep lines under 100 characters
  - [x] 1.2: `services/mod_state.py`: public `ModStateManager.filenames() -> list[str]` (the state's keys). Use it instead of `list_mods()` so the helper reads exactly the keys, as `get_mod` (`:138-147`) does
  - [x] 1.3: `services/mods.py`: private `ModService._refuse_taken_names(self, slug: str, names: tuple[str, ...], own: str | None, operation: ModFileOperation) -> None` beside `_refuse_if_busy` (`:341-345`), as in Dev Notes "The check". Synchronous; no `await` anywhere near it
  - [x] 1.4: `_place_install` (`:1268`): replace the loop at `:1284-1290` with `self._refuse_taken_names(slug, (name, f"{name}.disabled"), None, "install")`, still the first statement, before `check_compatibility` and outside both `try` blocks. Docstring: names compared ignoring case (Epic 19 ADR-8). `install_mod` docstring (`:1211-1212`): "ignoring case"
  - [x] 1.5: `routers/mods.py` install route docstring (`:745-746`): "...ignoring letter case". The mapping at `:775-782` does not change
  - [x] 1.6: Tests (Dev Notes "API tests", Task 1 rows), red first. The existing `TestInstallRefusesAFileNameInUse` (`tests/test_mod_operation_lock.py:759`) passes unchanged

- [x] Task 2: Enable, disable and version change refuse a taken name with 409 `MOD_FILE_CONFLICT`; Update All records it as failed + tests (AC: 1, 2, 3, 4, 5, 6, 7, 8, 9, 19) (`VSS-40ja`, `VSS-macf`)
  - [x] 2.1: `enable_mod` (`:710-766`): after the idempotent return (`:739-742`) and the computation of `new_filename` (`:746`), before `old_path.rename(new_path)` (`:749`): `self._refuse_taken_names(slug, (new_filename,), state.filename, "enable")`. `disable_mod` (`:768-824`) the same before `:807` with `"disable"`. Docstring Raises: `ModFileConflictError`. Nothing else in either method changes (Task 3 adds the missing-file check in the same places)
  - [x] 2.2: `_apply_version_change` (`:997-1060`): the first statement after `slug = state.slug` is `self._refuse_taken_names(slug, (release_name, f"{release_name}.disabled"), state.filename, "change the version of")` with `release_name = prepared.archive.name`, before `mods_dir.mkdir` (`:1003`). Delete the old `new_path.exists()` refusal (`:1008-1012`). `same_file = new_name.casefold() == state.filename.casefold()` (`:1008`; ADR-8 decision 4)
  - [x] 2.3: `_rollback_version_change` (`:1062-1081`): when a backup exists, restore it under the old state's own name: `old_path = new_path.with_name(old_state.filename)`; if `new_path.name != old_path.name`, `new_path.unlink(missing_ok=True)` first; then `backup_path.replace(old_path)` (Dev Notes "Case-only version change"; "ADR against the code")
  - [x] 2.4: `change_version` docstring (`:942-946`): `ModFileConflictError` under Raises. `_apply_version_change` docstring: refuses before writing anything when a name is taken
  - [x] 2.5: `services/mod_updates.py` `apply_all`: import `ModFileConflictError` in the local import (`:400-406`) and add it to the per-mod `except (...)` tuple (`:425-435`), before `ModOperationInProgressError` (ADR-8 decision 7)
  - [x] 2.6: `routers/mods.py`: `enable_mod` (`:848`) and `disable_mod` (`:924`) each get `except ModFileConflictError as e:` → 409 `{"code": ErrorCode.MOD_FILE_CONFLICT, "message": str(e)}`, after `except ModOperationInProgressError` (`:914`, `:990`); docstring Raises line `HTTPException: 409 if the name the file would be renamed to is taken in the mods directory or the mod state (MOD_FILE_CONFLICT)`. `change_mod_version` (`:1092`): `except ModFileConflictError as e: raise _version_change_error(409, ErrorCode.MOD_FILE_CONFLICT, e) from None` before `except ModVersionChangeFailedError` (`:1137`); add to the docstring: a taken file name is 409 `MOD_FILE_CONFLICT`, and `MOD_VERSION_CHANGE_FAILED` (500) is for a failure to place the file or save state, rolled back
  - [x] 2.7: Tests (Dev Notes "API tests", Task 2 rows) and the two tests in "Existing tests that change", red first

- [x] Task 3: Enable and disable of a mod whose file is gone answer 409 `MOD_FILE_MISSING` + tests (AC: 3, 13, 14, 19) (`VSS-yhmt`)
  - [x] 3.1: `services/mods.py`: `ModFileMissingError(slug, filename, *, operation: ModFileOperation)` after `ModFileConflictError`, attributes `slug`, `filename`, `operation`; message `f"Cannot {operation} '{slug}': its file {filename} is no longer in the mods directory. Remove the mod and install it again."` (ADR-9 decision 2)
  - [x] 3.2: `enable_mod` and `disable_mod`: directly before the Task 2 name check (after the idempotent return, ADR-9 decision 4): `if not (self._state_manager.mods_dir / state.filename).is_file(): raise ModFileMissingError(slug, state.filename, operation=...)`. A dangling symlink or a directory is "missing". Docstring Raises
  - [x] 3.3: `models/errors.py`: `MOD_FILE_MISSING = "MOD_FILE_MISSING"` after `MOD_FILE_CONFLICT` (`:68`)
  - [x] 3.4: `routers/mods.py`: both routes map `ModFileMissingError` to 409 `MOD_FILE_MISSING` with `str(e)`; docstring Raises line `HTTPException: 409 if the mod's own file is no longer in the mods directory (MOD_FILE_MISSING)`. Import it in the `services.mods` block (`:39-50`, alphabetical)
  - [x] 3.5: Tests (Dev Notes "API tests", Task 3 rows), red first. `remove_mod` is not changed: it already skips a missing file (`services/mods.py:857-858`); AC 14 gets a regression test

- [x] Task 4: Working files `.vsm-tmp` / `.vsm-bak` and start-up recovery + tests (AC: 15, 16, 17, 19) (`VSS-uoxl`, stays open for Story 19.5)
  - [x] 4.1: New `api/src/vintagestory_api/services/mod_file_recovery.py` with `WORKING_COPY_SUFFIX = ".vsm-tmp"`, `KEPT_ASIDE_SUFFIX = ".vsm-bak"` and `recover_working_files(state_manager: ModStateManager) -> None` (Dev Notes "Recovery"). Imports only `mod_state` (no cycle with `services/mods.py`)
  - [x] 4.2: `services/mods.py`: `_place_install` temp `dest_path.name + WORKING_COPY_SUFFIX` (`:1296`); `_apply_version_change` temp `new_path.name + WORKING_COPY_SUFFIX` (`:1014`) and backup `old_path.name + KEPT_ASIDE_SUFFIX` (`:1016`). Comments say what each file is
  - [x] 4.3: `services/mods.py`: module function `prepare_mod_files() -> None` after `get_mod_service` (Dev Notes "Start-up order"): step 1 `recover_working_files(service.state_manager)`; step 2 (Task 5) the old cache layout. Its docstring names the slot Story 19.5 fills: "Story 19.5 adds the state sync as step 3, after step 1"
  - [x] 4.4: `main.py`: import `prepare_mod_files` at module level from `services.mods` (beside the other top-level imports, `:15-33`); in `lifespan`, after the `api_starting` log (`:110-115`) and before the auto-start block (`:117`): `try: prepare_mod_files() except OSError as e: logger.error("mod_files_startup_failed", error=str(e))`. Re-check against Stories 19.2/19.3's lifespan; the rule is "after the data directories exist, before auto-start and the scheduler"
  - [x] 4.5: `tests/conftest.py`: an autouse fixture that replaces `vintagestory_api.main.prepare_mod_files` (with `monkeypatch.setattr(main_module, ...)`; conftest already imports `vintagestory_api.main`, `:17`) by a recorder, so no test that runs the lifespan touches `dev/` (Dev Notes "Tests must not touch dev/")
  - [x] 4.6: Tests (Dev Notes "API tests", Task 4 rows) and the `.tmp` tests in "Existing tests that change", red first

- [x] Task 5: Download cache keyed by file ID + tests (AC: 10, 11, 12, 19) (`VSS-n0qv`)
  - [x] 5.1: `services/mod_api.py` `ModApiClient.cache_path(self, fileid: int, filename: str) -> Path` = `self._mods_cache / str(fileid) / safe_release_filename(filename)` (raises `ValueError` like `safe_release_filename`, `:143-155`). `download_release_file` (`:555-630`) uses it (`:578`), `mkdir(parents=True, exist_ok=True)` on its parent, and writes to `parent / f"{uuid4().hex}.tmp"` opened with `"xb"`, renamed into place (ADR-11 decisions 1-3; Dev Notes "Cache"). The cleanup branches keep their `if temp_path.exists(): unlink()` shape
  - [x] 5.2: `services/mods.py` `_acquire_release_archive` (`:1140-1160`): `cached = self.api_client.cache_path(target.fileid, target.filename)` inside the existing `try`/`except ValueError` → `ModValidationError` (`:1142-1145`), replacing `:1147`. `safe_release_filename` stays imported if still used elsewhere in the module (check)
  - [x] 5.3: `ModApiClient.remove_flat_layout(self) -> int`: unlink every regular file directly under `cache/mods` (not directories, `is_file(follow_symlinks=False)`; a symlink there is unlinked too), each failure logged and skipped; returns the count. `prepare_mod_files` step 2 calls it through `service.api_client` and logs `mod_cache_old_layout_removed` with `files=<n>` at info when `n > 0` (ADR-11 decision 5; "ADR against the code")
  - [x] 5.4: `services/cache_eviction.py`: `_get_cache_files` (`:94-130`) globs `f"*/{pattern}"` under `cache/mods`; after a successful `unlink` in `evict_if_needed` and `evict_all`, remove the parent directory if it is now empty (`rmdir`, `OSError` ignored at debug); new `STALE_TEMP_AGE = timedelta(hours=1)` and `_remove_stale_temp_files()` (every `*/*.tmp` whose `st_mtime` is older, unlinked and logged `cache_temp_file_removed`, then its emptied directory), called first in `evict_if_needed` whether or not eviction is enabled (ADR-11 decision 4). Update the class and method docstrings for the layout
  - [x] 5.5: Tests (Dev Notes "API tests", Task 5 rows) and the cache tests in "Existing tests that change", red first

- [ ] Task 6: Web pins, E2E against the Docker dev stack, quality gate and review hand-off (AC: 18, 19, all)
  - [x] 6.1: `web/src/hooks/use-mods.test.tsx` "enable, disable and remove report errors" (`:1660`): for `useEnableMod` and `useDisableMod`, a 409 `MOD_FILE_CONFLICT` and a 409 `MOD_FILE_MISSING` (messages from AC 1 and AC 13) each give exactly one `toast.error('Error', { description: <message> })` and roll back (copy the busy test). `web/src/hooks/use-version-change-flow.test.tsx` (`:180`): a 409 `MOD_FILE_CONFLICT` gives `toast.error('Failed to update Carry On', { description })` and no confirmation. `web/src/components/UpdateAllDialog.test.tsx` (`:129-151`): a `failed` item with the conflict message shows `Failed: Cannot change the version of ...`. All pass against the current source (they pin AC 18); no web source change
  - [x] 6.2: New `web/e2e/mod-file-refusals.spec.ts` (Dev Notes "E2E"): every mod route is stubbed with `page.route`, nothing changes on the server, and the spec needs no mod database. Rebuild the stack from this branch first (`just docker restart`), run `cd web && bunx playwright test e2e/mod-file-refusals.spec.ts` with the admin key from `.env`, and re-run `e2e/install-file-conflict.spec.ts` and `e2e/installed-status.spec.ts`. Record in the Dev Agent Record that `GET /api/v1alpha1/mods` returned the same body before and after. Do not start or stop the game server; no screenshots
  - [x] 6.3: `just check` passes; the diff adds no lint or type suppression and no `cast`; pyright stays at 0 errors and the 3 pre-existing warnings (`VSS-1ar`); after `just test-api`, `git status --short` shows nothing under `dev/` and `dev/vsmanager/cache/mods` and `dev/serverdata/Mods` have the same listing as before the run (Dev Notes "Tests must not touch dev/")
  - [ ] 6.4: Manual check on the Docker stack (needs the maintainer's confirmation before it is ticked, `project-context.md`): see Dev Notes "Manual check"
  - [ ] 6.5: Story status `review`, `just sprint set 19-4-mod-files-are-never-overwritten review`, PR (base: Story 19.3's branch while its PR is open, otherwise `main`), PR link on the six beads. The PR description lists "API contract changes" from this story and says `VSS-uoxl` stays open for Story 19.5

## Dev Notes

### The bugs (verified at b6ae2f2)

- **Enable and disable replace a file (`VSS-40ja`).** `enable_mod` and `disable_mod` (`services/mods.py:710-766`, `:768-824`) call `old_path.rename(new_path)` (`:749`, `:807`) with no check: on POSIX a rename replaces the target, so a stray or another mod's `Foo.zip` is lost when `Foo.zip.disabled` is enabled.
- **Version change answers 500 for a taken name (`VSS-macf`).** `_apply_version_change` refuses when `new_path.exists()` and the name is not its own (`:1008-1012`) with `ModVersionChangeFailedError`, which the route maps to 500 `MOD_VERSION_CHANGE_FAILED` (`routers/mods.py:1137-1138`). It checks one name (not the `.disabled` twin), follows symlinks (a dangling one is "free"), ignores the mod state, and compares exactly (`same_file`, `:1008`). Update All does not catch a new error type (`services/mod_updates.py:425-435`), so a raise outside that tuple aborts the whole run.
- **Install compares exactly (`VSS-52fy`).** `_place_install` (`:1284-1290`, Story 18.2) checks `<name>` and `<name>.disabled` with `exists(follow_symlinks=False)` and `get_mod`; on the Linux volume `foo.zip` is placed beside another mod's `Foo.zip`.
- **Missing own file is a 500 (`VSS-yhmt`).** The renames at `:749` and `:807` raise `FileNotFoundError`; no route catches it.
- **Leftovers (`VSS-uoxl`).** `_place_install` copies to `<name>.tmp` (`:1296`), `_apply_version_change` to `<new>.tmp` (`:1014`) and keeps the original as `<name>.bak` for a same-name change (`:1016`), deleted after the state save (`:1049-1055`). A killed process leaves them; nothing cleans up.
- **Cache keyed by name (`VSS-n0qv`).** `download_release_file` writes `cache/mods/<safe_name>.tmp` and renames to `cache/mods/<safe_name>` (`services/mod_api.py:578-595`); `_acquire_release_archive` builds the same path itself (`services/mods.py:1147`). Two mods with one release file name share the path and, under two different per-mod locks, the temp file.

### The check (Tasks 1 and 2)

```python
def _refuse_taken_names(
    self, slug: str, names: tuple[str, ...], own: str | None, operation: ModFileOperation
) -> None:
    """Raise ModFileConflictError when a name an operation will create is taken (ADR-8).

    Compares with casefold() against the mods directory listing (not probed, so a name that
    differs only in case and a dangling symlink count on every volume) and the state's keys.
    `own` (the mod's current file, None for an install) is never "taken". Working files
    (.vsm-tmp, .vsm-bak, old .tmp/.bak) are never one of `names`, so never conflict (ADR-9 d. 8).
    """
    taken: dict[str, str] = {}
    for key in self._state_manager.filenames():
        taken.setdefault(key.casefold(), key)
    mods_dir = self._state_manager.mods_dir
    if mods_dir.is_dir():
        for path in mods_dir.iterdir():
            taken[path.name.casefold()] = path.name
    own_key = None if own is None else own.casefold()
    for name in names:
        key = name.casefold()
        if key != own_key and key in taken:
            raise ModFileConflictError(slug, taken[key], operation=operation)
```

- **Names per operation (ADR-8 decision 3).** Install: `(name, name + ".disabled")`, own `None`. Enable: `(state.filename.removesuffix(".disabled"),)`, own `state.filename`. Disable: `(state.filename + ".disabled",)`, own `state.filename`. Version change: `(release, release + ".disabled")` with `release = prepared.archive.name` (the cache file's name, which is the release file name), own `state.filename`. For a disabled mod changing to a release of its own name, `release + ".disabled"` is its own file and is skipped; `release` itself is checked (a stray enabled twin is a conflict).
- **The message names the entry in the way, as spelled** (the directory spelling wins over the state's, since the directory is listed last). For an exact match this is the same name Story 18.2's message gave, so `TestInstallRefusesAFileNameInUse` and `test_mods_router.py:444` pass unchanged (prototype: confirmed).
- **Order in enable/disable:** busy check → not installed → idempotent return → missing own file (Task 3) → name check → rename. A refusal changes nothing: no state, no restart flag.
- **Order in the version change:** the check runs in `_apply_version_change`, after the download and validation, under the mod's lock, with no `await` between it and the state save (ADR-8 decision 5). The download is not saved by an earlier check; that is accepted (the cache keeps it). `record_releases` is not called (it runs only after `_apply_version_change` returns, Story 18.2).
- **Concurrency.** All four placements are synchronous and run on the one event loop (`Dockerfile`: one uvicorn worker). Two different mods racing for one name hold different locks; whichever places first wins and the second is refused by the listing or the state. Nothing in this story adds an `await` inside a held section.

### Case-only version change (Task 2, AC 8)

- `same_file` ignoring case sends `Foo_1.0.zip` → `foo_1.0.zip` down the same-file path: the original is moved to `Foo_1.0.zip.vsm-bak`, the copy is renamed to `foo_1.0.zip`, the state key becomes `foo_1.0.zip`, the old file is not unlinked (it is the backup), and the backup is deleted after the save. On a case-insensitive volume the rename lands on the same directory entry; on a case-sensitive one the old name is gone because it was moved aside. Either way one file remains.
- Without the casefold, a case-insensitive volume refuses (today: 500) and, if the check were removed, the step that deletes the old file (`:1044`) would delete the new one (ADR-8 decision 4).
- **Rollback** (`_rollback_version_change`, `:1062-1081`) today does `backup_path.replace(new_path)`, which for a case-only change would put the original back under the new name while the restored state names the old one. Task 2.3 restores the backup to `old_path` (the old state's filename) and first unlinks `new_path` when the names differ. Test it by making `state_manager.save` raise once after placement (shape of `test_state_save_failure_rolls_back`).
- Tests do not need a case-sensitive filesystem to pass: none of them needs `Foo.zip` and `foo.zip` to exist at once. On macOS (case-insensitive) and in CI (`ubuntu-latest`, case-sensitive, `.github/workflows/ci.yml:20`) the same assertions hold. Do not add `pytest.skip` for either.

### Recovery (Task 4)

```python
def recover_working_files(state_manager: ModStateManager) -> None:
    """Put the mods directory right after an interrupted install or version change (ADR-9).

    Runs once at start-up, before any mod operation. The mod state is the source of truth.
    Each action is logged; a failure is logged and the next file is tried.
    """
```

1. Return when `mods_dir` is not a directory.
2. Every entry whose name ends with `.vsm-tmp` → `unlink`, log `mod_working_copy_removed` (info, `filename`).
3. Every `<name>.vsm-bak`: find the entries whose name casefolds to `name.casefold()` (list, so a case-only change is found; normally zero or one):
   - none → `backup.rename(mods_dir / name)`, log `mod_backup_restored` (warning, `filename`);
   - one, `current`: if `state_manager.get_mod(current.name)` exists and `state_manager.read_modinfo(current)` is not `None` and its `version` equals that entry's `version` → the change completed: `backup.unlink()`, log `mod_backup_removed` (info);
   - otherwise the change did not complete and the state still describes the original: if `current.name != name`, `current.unlink()`; then `backup.replace(mods_dir / name)`; log `mod_backup_restored` with `replaced=current.name`.
   - each step in `try`/`except OSError` → `mod_recovery_failed` (error, `filename`, `error`), continue.
4. After that, one warning `mod_directory_unknown_leftovers` with `files=[sorted names]` for entries whose lower-cased name ends with `.tmp` or `.bak` (`.vsm-tmp` and `.vsm-bak` do not end that way); nothing when there are none. Never deleted or renamed (ADR-9 decision 7; Matt confirmed warn-only, follow-up `VSS-hv60`).

Interruption points this covers (ADR-9 consequences; one test each, by building the directory by hand):

| Interrupted | Directory | State | Result |
|---|---|---|---|
| Install, after the copy | `X.zip.vsm-tmp` | no entry | copy deleted |
| Same-name change, after the move aside | `X.zip.vsm-tmp`, `X.zip.vsm-bak` | `X.zip` v1 | copy deleted, `X.zip` (v1) back |
| Same-name change, after the rename | `X.zip` (v2), `X.zip.vsm-bak` (v1) | `X.zip` v1 | `X.zip` is v1 again, no backup |
| Same-name change, after the state save | `X.zip` (v2), `X.zip.vsm-bak` (v1) | `X.zip` v2 | backup deleted, `X.zip` v2 |
| Case-only change, after the rename | `x.zip` (v2), `X.zip.vsm-bak` (v1) | `X.zip` v1 | `x.zip` deleted, `X.zip` v1 |
| Case-only change, after the state save | `x.zip` (v2), `X.zip.vsm-bak` (v1) | `x.zip` v2 | backup deleted |

A disabled mod is the same with `.disabled` in every name. Not covered (pre-existing, reported in "Follow-ups"): a change to a **different** name killed after the rename and before the old file is unlinked leaves two archives of one mod and no working file; Story 19.5's sync warns about the second file and leaves it.

### Start-up order (Task 4; the hook Story 19.5 uses)

```python
def prepare_mod_files() -> None:
    """Start-up work on the mods directory and the download cache (Epic 19 ADR-9, ADR-11).

    Called once by the API's lifespan, before the scheduler and the game server auto-start,
    so it runs before any mod operation. Steps, in order:
    1. recover the manager's working files (ADR-9 decisions 6-7);
    2. remove the download cache's old flat layout (ADR-11 decision 5).
    Story 19.5 adds the state sync (ADR-10) as step 3, after step 1.
    """
    service = get_mod_service()
    recover_working_files(service.state_manager)
    removed = service.api_client.remove_flat_layout()
    if removed:
        logger.info("mod_cache_old_layout_removed", files=removed)
```

- `get_mod_service()` loads the state and runs `repair_fallback_entries` (`services/mods.py:107-108`) first. That repair skips an entry whose file is missing (`services/mod_state.py:436-437`), so it does nothing harmful to a file that is still `.vsm-bak`; it is not reordered.
- `lifespan` (`main.py:92-161`) runs before the server accepts requests, so no route can run before `prepare_mod_files`. The scheduler starts at `:144`, after the auto-start; the call goes before both.
- Creating the singleton at start-up instead of on first request is new; `close_mod_service` at shutdown (`:158-161`) already handles it.

### Cache (Task 5)

- **Layout:** `cache/mods/<fileid>/<safe_name>`. `DownloadResult.filename = path.name` (`services/mod_api.py:549`) and therefore the installed file name are unchanged.
- **Temp file:** `parent / f"{uuid4().hex}.tmp"` opened `"xb"`. Not `tempfile.mkstemp`: that creates the file mode `0600`, and `shutil.copy2` would carry `0600` onto the installed mod file; `open` gives the umask default as today. Not `<name>.<uuid>.tmp`: a long release name plus 37 characters could pass the 255-byte name limit; the directory already names the release.
- **Same release twice at once (AC 11):** each download has its own temp; both `rename` into one path; the second replaces the first atomically with identical bytes. No lock is added (ADR-11 decision 7).
- **Install's archive check is unchanged** (ADR-11 decision 6): the file-ID path can only hold the file it asked for.
- **Eviction:** `CACHE_FILE_PATTERNS` (`*.zip`, `*.cs`) are matched one level down. The stale-temp sweep runs even when `max_size_mb == 0`, so a disabled eviction still tidies crashes; temps younger than an hour (an active download, `DOWNLOAD_TIMEOUT` 120 s per read) are never touched.
- **Old layout removal at start-up, not in `ModApiClient.__init__`:** see "ADR against the code".

### API tests

Helpers: `tests/test_mod_operation_lock.py` (`mock_mod` `:56`, `mock_foo_zip` `:720`, `mod_files` `:117`, `state_of` `:122`, imports `make_service`, `install_existing`, `mod_zip_bytes` from `test_mod_version_change.py`, `:206`, `:216`, `:120`); `tests/test_mod_version_change.py` (`mock_demo` `:481`, `installed_version_on_disk` `:492`); `captured_logs` (`tests/conftest.py:73`). Every refusal test compares, before and after: the other file's bytes, `mod_files(service)`, the mod's state entry, the state file on disk (reload a `ModStateManager`), and `service.restart_state.pending_restart` with the server marked running.

| Task | File | Tests |
|---|---|---|
| 1 | `tests/test_mod_operation_lock.py`, new class `TestFileNamesIgnoreCase` | `moda` installed as `Foo.zip` (and as `Foo.zip.disabled`); `modb`'s release named `foo.zip` and `FOO.ZIP` (parametrize): `install_mod("modb")` raises `ModFileConflictError` with `filename == "Foo.zip"` (or `Foo.zip.disabled`) and `operation == "install"`; nothing placed. A state entry `Foo.zip` without a file and release `foo.zip` → refused. A dangling symlink `Foo.zip` (exists already for exact case, `:813`) with release `foo.zip` → refused. Red first: all fail with the exact comparison on a case-sensitive volume; on macOS the dangling-symlink and state cases are the discriminating ones (the plain file case already fails there through `exists`) |
| 1 | `tests/test_mod_state.py` | `filenames()` returns the keys after `set_mod_state` and `remove_mod` |
| 2 | new `tests/test_mod_file_names.py` (service level) | Enable: `A` disabled as `Foo.zip.disabled` with a stray `Foo.zip` (and, parametrized: another mod's enabled `Foo.zip` with state; `foo.zip`; a state entry `Foo.zip` without a file; a dangling symlink `Foo.zip`) → `ModFileConflictError(operation="enable")`, message as AC 1, nothing changed. Disable: the mirror with `Foo.zip.disabled` in the way. Idempotent: enabling an enabled mod with `Foo.zip.disabled` in the way, and disabling a disabled one with `Foo.zip` in the way, both succeed with `pending_restart` false and nothing changed. No conflict: enable then disable round trip leaves exactly the mod's file |
| 2 | `tests/test_mod_version_change.py` `TestChangeVersion` (`:497`) | `Demo-1.0.0.zip` installed; the release `Demo-1.1.0.zip` taken by: another mod's file and entry; a stray file; a stray `Demo-1.1.0.zip.disabled`; `demo-1.1.0.zip`; a state entry without a file; a dangling symlink (parametrize) → `ModFileConflictError(operation="change the version of")`, files and state unchanged, no `.vsm-tmp` left. A disabled mod whose release name is free but `Demo-1.1.0.zip` (enabled form) is a stray → refused. Case-only change (AC 8): installed `Demo-1.0.0.zip` at 1.0.0, release 1.1.0 named `demo-1.0.0.zip` (`mock_demo("demo-1.0.0.zip", "Demo-1.0.0.zip")`) → succeeds, `mod_files == ["demo-1.0.0.zip"]`, state key `demo-1.0.0.zip` at 1.1.0; same with the save failing once → 500 path, `mod_files == ["Demo-1.0.0.zip"]` with the 1.0.0 bytes and the state back at `Demo-1.0.0.zip`. A save failure on a plain change still raises `ModVersionChangeFailedError` (AC 6, existing `test_state_save_failure_rolls_back` stays) |
| 2 | `tests/test_mod_update_all.py` `TestApplyAll` (`:97`) | A fake `change_version` raising `ModFileConflictError("alpha", "Alpha.zip", operation="change the version of")` for one mod: that item is `failed` with `error == str(exc)`, the next mod is `updated` (copy the `ModVersionChangeFailedError` case at `:154`) |
| 2 | `tests/test_mods_router.py` `TestEnableModEndpoint` (`:1032`), `TestDisableModEndpoint` (`:1205`) | 409, body exactly `{"detail": {"code": "MOD_FILE_CONFLICT", "message": "Cannot enable '<slug>': a file named <name> already exists in the mods directory."}}`; files and `GET /mods` unchanged |
| 2 | `tests/test_mod_version_change_router.py` `TestChangeVersionEndpoint` (`:127`) | A taken name → 409 `MOD_FILE_CONFLICT` with the message; the stored update record is unchanged (the `update_service` fixture from Story 18.2) |
| 2 | `tests/test_mod_update_all_router.py` (`:111`) | carryon's new file name taken by a stray file: `failed` with the conflict message; a second mod in the same run is `updated` |
| 3 | `tests/test_mod_file_names.py` | Enabled and disabled mod with its file deleted: `disable_mod`/`enable_mod` raise `ModFileMissingError` (message as AC 13); state in memory and on disk unchanged; `pending_restart` false. A dangling symlink as the own file → missing. Missing and a name in the way at once → `ModFileMissingError`. Idempotent call on a mod with a missing file succeeds. `remove_mod` of that mod succeeds and the entry is gone (AC 14) |
| 3 | `tests/test_mods_router.py` | Enable and disable of a mod whose file was deleted: 409, body exactly `{"detail": {"code": "MOD_FILE_MISSING", "message": ...}}`; `DELETE /mods/{slug}` then 200 |
| 4 | new `tests/test_mod_file_recovery.py` | One test per row of the "Recovery" table (enabled and disabled), each asserting the listing, the bytes (by `installed_version_on_disk` or raw bytes) and that the state is not changed by recovery (it never saves). An unreadable new file (no `modinfo.json`) beside a backup → backup restored. A failing `rename` (monkeypatch `Path.rename` for one name) → `mod_recovery_failed` logged, the other files still recovered, no exception. No mods directory → nothing, no error. `notes.bak`, `Old.zip.tmp`, `Mod.ZIP.BAK` → one `mod_directory_unknown_leftovers` warning naming all three, bytes unchanged; none of them → no warning. Each action's log line (`captured_logs`) |
| 4 | `tests/test_mod_file_names.py` | AC 17: with `Foo.zip.vsm-tmp`, `Foo.zip.vsm-bak` and `Foo.zip.tmp` present, install of `Foo.zip` (respx, `mock_mod` shape), enable/disable of a mod as `Foo.zip`, and a same-name version change all succeed; the `.tmp` and `.vsm-bak` leftovers keep their bytes (the version change's own backup replaces a leftover `.vsm-bak` and is then deleted: assert no `.vsm-bak` remains in that case) |
| 4 | `tests/test_mod_service.py` and `tests/test_mod_version_change.py` | No working file left after a successful install, a successful same-name change and a failed one (`glob("*.vsm-*") == []`) |
| 4 | `tests/test_main.py` `TestLifespanAutoStart` (`:284`) | The conftest recorder is called once per lifespan, and before `start_server` (record both calls in one list); an `OSError` from it is logged `mod_files_startup_failed` and auto-start still runs |
| 4 | `tests/test_mod_service.py` | `prepare_mod_files()` with `get_mod_service` patched to a tmp service: a `.vsm-tmp` in the mods dir and a flat `cache/mods/Old.zip` are both gone afterwards, `mod_cache_old_layout_removed files=1` logged; with nothing to do, no such line |
| 5 | `tests/test_mod_api.py` | `cache_path(7, "Demo.zip") == cache/mods/7/Demo.zip`; two file IDs with one name → two paths; a hostile name stays inside `cache/mods/<fileid>/`. Two mods (`fileid` 11 and 21) with release file `Same.zip` downloaded one after the other: both files exist with their own bytes. **Concurrency (asyncio):** patch the client's `stream` as `test_download_os_error_with_temp_file_exists` does (`:780-815`), with a side effect that picks the body by the `fileid` in the URL and an async chunk iterator that yields the first half, awaits a shared `asyncio.Event` and then yields the rest; `asyncio.gather` both downloads and set the event once both have written their first chunk (count them), so both are mid-download at once: both paths hold their own complete bytes and no `*.tmp` is left anywhere under `cache/mods` (`rglob`). Red first: with today's shared path and temp, the two files are one. Same file ID twice at once: one file with the expected bytes, no temp. `remove_flat_layout()`: two flat files and a flat `.tmp` removed (returns 3), a `<fileid>/` directory and its file kept |
| 5 | `tests/test_mod_operation_lock.py` | AC 10 end to end, entries built with `entry(modid, "Same-1.1.0.zip", "Same-1.0.0.zip", fileids)` (`:39`) and file IDs `(11, 10)` / `(21, 20)`. In turn: install `moda`, remove it, install `modb`: the placed `Same-1.1.0.zip` names `modb` (`read_modinfo`), and `cache/mods/11/` and `cache/mods/21/` each hold their own mod's archive. At once: gate both installs' downloads (`gate_download`, `:100`, one gate per slug), release both; one install places `Same-1.1.0.zip` and the other is refused with `ModFileConflictError`; the placed file names the mod whose install succeeded; each cached file names its own mod |
| 5 | `tests/test_cache_eviction.py` | Files in `mods/<id>/` are counted and evicted LRU; an emptied `<id>/` directory is removed, a non-empty one kept; a `*/x.tmp` with `mtime` two hours ago is removed by `evict_if_needed` with eviction enabled and with `max_size_mb=0`, one ten minutes old is kept; a flat file directly under `mods/` is not counted |
| 5 | `tests/test_mod_version_change.py` `TestPrepareVersionChange` (`:253`) | A valid cached archive at `cache_path(fileid, name)` is reused (no download); an archive cached under another file ID with the same name is not used |

### Existing tests that change (deliberately)

Found by running the whole API suite (2858 passed at b6ae2f2) against a throwaway prototype of Tasks 1-5 (since discarded): 27 failed, all listed here; pyright 0 errors, 3 warnings. Nothing else failed. Several more tests pass but test nothing after the change and must be updated too.

- **Version change refusal type (Task 2):** `tests/test_mod_version_change.py::TestChangeVersion::test_existing_file_of_another_mod_is_not_overwritten` (`:670`) and `::TestChangeVersionRecordsReleases::test_another_mods_file_in_the_way_records_nothing` (`:804`) expect `ModVersionChangeFailedError`; change to `ModFileConflictError` (ADR-8 decision 6). Their other assertions stay.
- **Working-file suffix (Task 4):** `tests/test_mod_service.py::TestModServiceInstallMod::test_install_mod_cleans_up_temp_file_on_rename_failure` (`:1123`) fails the rename only for names ending `.tmp` (`:1156`) and asserts on `smithingplus_1.8.3.tmp` (`:1167`); switch to `.vsm-tmp` and `smithingplus_1.8.3.zip.vsm-tmp`. Passing but vacuous: `test_install_mod_handles_copy_failure` (`:1084`; its assert at `:1120` checks a name never used) → assert `smithingplus_1.8.3.zip.vsm-tmp`; `test_install_mod_temp_file_does_not_clobber_same_stem_file` (`:873`) docstring says `.tmp` → `.vsm-tmp` (the stray `smithingplus_1.8.3.tmp` stays as the unrelated file).
- **Cache layout (Task 5):**
  - `tests/test_cache_eviction.py`: 17 tests fail (`TestCacheStats` ×2, `TestEvictAll::test_evict_all`, `TestEviction` ×4, `TestFilePatterns` ×2, `TestLogging` ×8) because `create_test_file` (`:20-28`) writes directly under `mods/`. Change the helper to write `mods/<n>/<name>` (a directory per file, e.g. a counter or the name's stem) and the `cache_dir` fixture (`:13-17`) stays. Check `:226` (`mods_dir = cache_dir / "mods"`) in the same way.
  - `tests/test_edge_cases.py::TestCacheEvictionEdgeCases` (`:100-128`): both tests fail; `write_cached_mod` writes `mods/<id>/<name>` and `test_directories_matching_pattern_are_not_counted` makes `mods/<id>/directory.zip` a directory.
  - `tests/test_mod_version_change.py::TestDownloadUsesSafeFilename` (`:76`) both tests and `TestPrepareVersionChange::test_confirmed_change_downloads_and_validates`, `::test_valid_cached_archive_is_reused`, `::test_stale_cache_file_that_cannot_be_deleted_is_replaced` (`:298`, `:313`, `:349`) compare with `cache/mods/<name>`; use `cache/mods/<fileid>/<name>` (or `service.api_client.cache_path(...)`). `:93` (`glob("*.tmp")` directly under `cache/mods`) becomes `rglob`.
  - Passing but vacuous: `tests/test_mod_api.py` `test_download_cleans_up_on_failure` (`:560`, assert at `:594-596`), `test_download_timeout_cleans_up` (`:600`, `:636-637`), `test_download_io_error_cleans_up` (`:641`, `:697-698`), `test_download_timeout_with_temp_file_exists` (`:702`, `:736-737`), `test_download_http_error_with_temp_file_exists` (`:742`, `:774-775`), `test_download_os_error_with_temp_file_exists` (`:780`, `:814-815`): each checks `cache/mods/*.tmp` or `cache/mods/smithingplus_1.8.3.zip.tmp`; make each `list(mods_cache.rglob("*.tmp")) == []` and `not (mods_cache / "59176" / "smithingplus_1.8.3.zip").exists()` where it checks the final file (59176 is `SMITHINGPLUS_MOD`'s file ID; check the fixture).
- **Lifespan (Task 4):** none fail, but without the conftest recorder `TestLifespanAutoStart` (`tests/test_main.py:284-560`), `tests/test_scheduler.py` (`:352-395`), `tests/test_jobs_registration.py` (`:264`, `:279`) and `tests/test_jobs_router.py` (`:42`) would run the real recovery and cache removal against `dev/` (`just test-api` sets `VS_DATA_DIR=../dev`). The prototype showed it: it created `dev/vsmanager/cache/mods`. With the recorder they are unchanged.
- `tests/test_mod_operation_lock.py::TestInstallRefusesAFileNameInUse` and `tests/test_mods_router.py:444` (Story 18.2's message) pass unchanged.
- Environment note: in a fresh worktree without `.env`, `just test-api` reports errors from `VS_API_KEY_ADMIN` being unset (Story 18.2's note). Copy `.env` or set the variable first.
- Anything else that fails is a regression (AC 19): fix the code, not the test.

### Tests must not touch `dev/`

`just test-api` runs with `VS_DATA_DIR=../dev`, the Docker dev stack's data. Recovery renames and deletes files in `dev/serverdata/Mods` and `remove_flat_layout` deletes files in `dev/vsmanager/cache/mods`, so a test that reaches the real `prepare_mod_files` through the lifespan would change the developer's stack. The autouse conftest fixture (Task 4.5) replaces the name `prepare_mod_files` in `vintagestory_api.main`; tests of `prepare_mod_files` itself import it from `services.mods` and patch `get_mod_service` to a tmp service. Gate 6.3 checks the two directory listings before and after `just test-api`.

### Web (Task 6)

- **Enable/disable:** `useEnableMod`/`useDisableMod` (`web/src/hooks/use-mods.ts:117-162`, `:170-212`) roll back the optimistic update and call `handleApiError` (`:156`, `:205`), which shows `toast.error('Error', { description: error.message })` (`web/src/api/error-handler.ts:29-32`). `ModTable`'s `handleToggle` (`web/src/components/ModTable.tsx:193-206`) passes only `onSuccess`, so one toast appears. The message is the API's `detail.message`.
- **Version change:** `useVersionChangeFlow` (`web/src/hooks/use-version-change-flow.ts:67-99`) shows `toast.error('Failed to update <name>', { description: message })` for every error but `MOD_CONFIRMATION_REQUIRED` (`:38-48`).
- **Update All:** `UpdateAllDialog` shows `Failed: <error>` per failed item (`web/src/components/UpdateAllDialog.tsx:50`).
- No web code switches on `MOD_VERSION_CHANGE_FAILED` (`rg` finds it only in `use-mods.test.tsx:1607`), so the code change from 500 to 409 needs nothing. No web source change.

### E2E (`web/e2e/mod-file-refusals.spec.ts`)

Style of `e2e/installed-status.spec.ts` (`installedModJson` `:50-66`, `fakeNotCheckedMod` `:82-131`; copy, do not import across specs) and `e2e/install-file-conflict.spec.ts` (header comment with requirements). Header: Story 19.4, FR218, FR219, FR222; every mod route is stubbed so nothing changes on the server, and no mod database is needed (so Story 19.7's CI can run it untagged). Get the key through Story 19.2's `/config.js` helper in `web/e2e/` (check its name on the base branch); do not add a `localStorage.setItem('apiKey', ...)` init script (FR230).

- One `page.route(/\/api\/v1alpha1\/mods(\/[^?]*)?(\?.*)?$/)` handler: `GET /mods` → `alpha` enabled as `alpha_1.0.0.zip` and `beta` disabled as `beta_1.0.0.zip.disabled`; `GET /mods/updates` → `alpha` `update_available` with `offered_version: "1.1.0"`, `offered_compatibility: "compatible"`; `GET /mods/lookup/*` → 404 as in `fakeNotCheckedMod`; `POST /mods/alpha/disable` → 409 `MOD_FILE_MISSING` ("Cannot disable 'alpha': its file alpha_1.0.0.zip is no longer in the mods directory. Remove the mod and install it again."); `POST /mods/beta/enable` → 409 `MOD_FILE_CONFLICT` ("Cannot enable 'beta': a file named beta_1.0.0.zip already exists in the mods directory."); `PUT /mods/alpha/version` → 409 `MOD_FILE_CONFLICT` ("Cannot change the version of 'alpha': a file named alpha_1.1.0.zip already exists in the mods directory."); anything else → 403 "This test changes nothing". Count the writes.
- Desktop width (1440 × 900), `/game-server/mods/installed`:
  - click `mod-toggle-beta` → a `[data-sonner-toast]` with "Error" containing the enable message; the switch is not checked again (`toBeChecked({ checked: false })`); one POST;
  - click `mod-toggle-alpha` → toast with the missing-file message; the switch is checked again;
  - click `mod-update-button-alpha` → toast "Failed to update alpha" with the conflict message; one PUT.
- No real state changes: compare `GET /api/v1alpha1/mods` (via `request`, admin key) before and after in the Dev Agent Record. Do not start or stop the game server. No screenshots.

### Manual check (Task 6.4)

On the Docker stack built from this branch: the start-up log shows no `mod_recovery_failed` and (first start after the upgrade, if the dev cache had files) one `mod_cache_old_layout_removed`; `ls dev/vsmanager/cache/mods` afterwards shows only `<fileid>/` directories after the next install or version change. Run the E2E spec headed (`bunx playwright test e2e/mod-file-refusals.spec.ts --headed`) and read the three toasts. Do not create conflicts with real mods on the stack, do not start or stop the game server, no screenshots. The maintainer ticks 6.4.

### Not changed (do not "fix" these here)

- `install_mod`'s checks and their order (Story 17.3), the archive mod ID check (ADR-11 decision 6), `record_install`/`record_releases` (Stories 17.4, 18.2).
- `remove_mod` (`services/mods.py:826-879`): it already skips a missing file.
- A version change of a mod whose own file is missing still answers 500 `MOD_VERSION_CHANGE_FAILED` (rename or unlink of the missing file, rolled back); ADR-9 covers enable and disable only. Follow-up.
- `sync_state_with_disk` and `scan_mods_directory` (Story 19.5).
- The state file's own temp (`mods.json` → `.tmp` in the state directory, `services/mod_state.py:118`), which is not in the mods directory.
- No new endpoint, no UI for leftovers (`VSS-hv60`), no cache size or layout setting.

### API contract changes

- `POST /api/v1alpha1/mods/{slug}/enable`, `POST /api/v1alpha1/mods/{slug}/disable`: new error 409 `MOD_FILE_CONFLICT` when the name the file would be renamed to is taken in the mods directory or the mod state, ignoring case. Before, the other file was replaced. Message `Cannot enable|disable '<slug>': a file named <name> already exists in the mods directory.`
- Same two routes: new error code 409 `MOD_FILE_MISSING` when the mod's own file is not in the mods directory. Before: 500. Message `Cannot enable|disable '<slug>': its file <name> is no longer in the mods directory. Remove the mod and install it again.`
- `PUT /api/v1alpha1/mods/{slug}/version`: a taken file name (the release name or its `.disabled` form, in the directory or the state, ignoring case) is 409 `MOD_FILE_CONFLICT`; before 500 `MOD_VERSION_CHANGE_FAILED`, which stays for a failure to place the file or save state. A release whose name differs from the installed file only in case now succeeds.
- `POST /api/v1alpha1/mods`: file names compared ignoring case; the message now names the entry in the way as spelled in the mods directory.
- `POST /api/v1alpha1/mods/updates/apply-all`: response unchanged; a file-name conflict is a `failed` item with the message.
- On disk, not API: download cache `cache/mods/<fileid>/<name>` (old files removed at start); working files `<name>.vsm-tmp` and `<name>.vsm-bak`, recovered at start; new log events `mod_working_copy_removed`, `mod_backup_restored`, `mod_backup_removed`, `mod_recovery_failed`, `mod_directory_unknown_leftovers`, `mod_cache_old_layout_removed`, `mod_files_startup_failed`, `cache_temp_file_removed`.

### ADR against the code

- **ADR-8 decision 4 and the rollback.** Sending a case-only rename down the same-file path is right, but `_rollback_version_change` restores the backup to `new_path` (`:1074`), which for a case-only change is the new spelling while the restored state names the old one. Task 2.3 restores to the old name. The ADR does not mention the rollback.
- **ADR-9 decision 6 and case.** Decision 6 looks for `<name>` exactly. After a case-only change (ADR-8 decision 4) the new file is `x.zip` and the backup `X.zip.vsm-bak`; an exact lookup would "restore" `X.zip` beside `x.zip` (two archives of one mod on a case-sensitive volume). The recovery matches `<name>` ignoring case and, when the change did not complete, removes the differently spelled new file before restoring.
- **ADR-11 decision 5 "when the client is created".** `ModApiClient` is created lazily on first use (`services/mods.py:881-896`), which is not "at start" (AC 12), and tests construct it on many temp directories. The removal is an explicit `remove_flat_layout()` called from `prepare_mod_files` at start-up.
- **ADR-11 decision 3 "uniquely named .tmp file".** Named `<uuid>.tmp` in the file-ID directory, not with `tempfile.mkstemp` (file mode `0600` would reach the installed mod file through `copy2`).
- **ADR-8 decision 6 message.** It names "`<name>`"; the story names the entry in the way as spelled in the directory, so a case conflict says `Foo.zip`, the file the admin can find (as Story 18.2 named the `.disabled` twin).
- Everything else in ADR-8, ADR-9 and ADR-11 matches the code at b6ae2f2 (line numbers re-read; the ADRs cite 048fea9, where `services/mods.py` lines are up to 2 lower in places).

### Testing Requirements

**CRITICAL:** Tests are written with each task and committed with it, red first. `just test-api <file>` / `just test-web <file>` after each task; `just check` before review.

- respx for `https://mods.vintagestory.at/api/mod/{slug}` and `https://mods.vintagestory.at/download`; captured fixtures under `api/tests/fixtures/moddb/` are not changed.
- Every refusal compares bytes, listing, state (memory and disk) and the restart flag before and after.
- No `pytest.skip`/`xfail`, no lint or type suppression, no `cast`. Tests must not read private members (`reportPrivateUsage`): use `service.state_manager`, `service.api_client`, `service.busy_mod_ids`, `service.restart_state`, and the new public `cache_path`, `remove_flat_layout`, `filenames`.

### Security Requirements

- No new endpoint; enable, disable, version change, install and Update All stay Admin-only. The messages contain the requested slug and a file name from the mods directory or state; no path outside it. Recovery touches only names ending in the manager's own suffixes inside the mods directory and never follows a name outside it (`iterdir` of one directory). `cache_path` keeps `safe_release_filename`; the file ID is an `int`, so `str(fileid)` cannot traverse.

### Development Commands

- `just test-api tests/test_mod_operation_lock.py tests/test_mod_file_names.py tests/test_mod_version_change.py tests/test_mod_update_all.py`, `just test-api tests/test_mods_router.py tests/test_mod_version_change_router.py tests/test_mod_update_all_router.py`, `just test-api tests/test_mod_file_recovery.py tests/test_main.py tests/test_mod_service.py`, `just test-api tests/test_mod_api.py tests/test_cache_eviction.py tests/test_edge_cases.py`, `just test-web src/hooks/use-mods.test.tsx src/hooks/use-version-change-flow.test.tsx src/components/UpdateAllDialog.test.tsx`, `just typecheck-api`, `just lint-api`, `just check`.
- Do not run `just format-api` (reformats unrelated files; Story 18.2 debug log).

### Previous Story Intelligence

- **18.2:** the `_place_install` check this story generalizes (Epic 18 ADR-4), `TestInstallRefusesAFileNameInUse` and its helpers; review L1 became `VSS-52fy`, and its "Concurrency" note became `VSS-n0qv`. Router tests must inject `ModUpdateService` on a temp directory (17.4, 18.2). `ruff format --check` already reports unrelated lines in `services/mods.py` and `routers/mods.py`; keep new code `ruff check` clean and do not reformat.
- **17.3:** enable/disable/remove are synchronous on purpose and do not hold the lock (their docstrings); nothing awaited is added. A TanStack Query v5 hook-level `onError` replaces the client default, so such a hook must call `handleApiError` itself; the enable/disable hooks do (`use-mods.ts:155-156`), and this story adds no hook.
- **17.4 / 17.2:** E2E that changes real state needs a snapshot guard and must restore the stack exactly; this story's spec stubs every write. `feat`/`fix` subjects describe what an admin sees. A completion note must be true of the code; manual checks wait for the maintainer.

### Git Intelligence

- Base `b6ae2f2` (`docs(epic-19): fold the maintainer's observation decisions into epic 19`). Stories 19.1-19.3 land first; 19.2 and 19.3 change `main.py` and the app construction in tests. Story 19.5 comes directly after and fills `prepare_mod_files` step 3.
- Planned commits (subjects from the sprint change proposal 2026-11-17, section 2, scope `story-19.4/task-N`; git-cliff drops the scope):
  - Task 1 `fix(story-19.4/task-1): installing a mod refuses a file name another mod uses in other letter case` (the proposal lists no subject for `VSS-52fy`; this one is new; an admin on a Linux volume now sees a 409 where `foo.zip` used to be placed beside `Foo.zip`)
  - Task 2 `fix(story-19.4/task-2): enabling, disabling or changing the version of a mod can no longer replace another mod's file`
  - Task 3 `fix(story-19.4/task-3): enabling or disabling a mod whose file is missing explains what to do instead of failing`
  - Task 4 `fix(story-19.4/task-4): recover mod files left by an interrupted install or version change at start-up`
  - Task 5 `fix(story-19.4/task-5): keep downloaded mod files apart when two mods use the same file name`
  - Task 6 `test(story-19.4/task-6): pin the mod file refusals in the web and an e2e spec`, then `chore(story-19.4/task-6): validate and move story 19.4 to review`
- The epic lists the tasks in another grouping (enable/disable with both checks, then version change, then a closing test task). They are regrouped so each `fix` commit carries exactly one proposal subject, and tests ride with each task; still six tasks.

### Project Structure Notes

- New: `api/src/vintagestory_api/services/mod_file_recovery.py`; `api/tests/test_mod_file_names.py`, `api/tests/test_mod_file_recovery.py`; `web/e2e/mod-file-refusals.spec.ts`.
- Modified: `api/src/vintagestory_api/services/mods.py`, `services/mod_state.py`, `services/mod_api.py`, `services/cache_eviction.py`, `services/mod_updates.py`, `routers/mods.py`, `models/errors.py`, `main.py`; `api/tests/conftest.py`, `test_mod_operation_lock.py`, `test_mod_version_change.py`, `test_mod_service.py`, `test_mod_state.py`, `test_mod_update_all.py`, `test_mods_router.py`, `test_mod_version_change_router.py`, `test_mod_update_all_router.py`, `test_mod_api.py`, `test_cache_eviction.py`, `test_edge_cases.py`, `test_main.py`; `web/src/hooks/use-mods.test.tsx`, `web/src/hooks/use-version-change-flow.test.tsx`, `web/src/components/UpdateAllDialog.test.tsx`. No fixture, no web source file.

### Follow-ups (for the PR, not this story)

- A version change of a mod whose own file is missing answers 500; it could answer `MOD_FILE_MISSING` too.
- A version change to a different file name killed after the rename and before the old file is unlinked leaves two archives of one mod and no working file; Story 19.5's sync warns and keeps the state's entry.
- `CACHE_FILE_PATTERNS` count only `*.zip` and `*.cs`; a release file of another type is never evicted (pre-existing).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 19.4: Mod Files Are Never Overwritten] (and Epic 19 "Size", "Dependencies")
- [Source: _bmad-output/planning-artifacts/prd.md] FR218-FR223
- [Source: _bmad-output/planning-artifacts/architecture/epic-19-api-security-and-mod-file-safety.md#ADR-8, #ADR-9, #ADR-11, "Mod files", "Download cache"; ADR-10 for the order Story 19.5 relies on]
- [Source: _bmad-output/planning-artifacts/architecture/epic-18-mod-media-and-fixes.md#ADR-4] (the install check, decision 6 replaced)
- [Source: _bmad-output/planning-artifacts/architecture/epic-17-mod-data-fixes.md] (ADR-3 per-mod lock)
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-17.md] (API contract table, release-note subjects, answered question 3 on old-style leftovers)
- [Source: _bmad-output/implementation-artifacts/18-2-install-and-version-change-keep-records-right.md], [17-3-mod-operations-are-safe-against-each-other.md], [17-4-installed-status-is-right-everywhere.md]
- Beads: `VSS-52fy`, `VSS-40ja`, `VSS-macf`, `VSS-yhmt`, `VSS-uoxl` (blocks `VSS-hv60`), `VSS-n0qv`; parent `VSS-fl9b`
- `project-context.md` (no suppressions; manual test tasks need the maintainer's confirmation; commit format)

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5), BMAD dev-story, non-interactive.

### Debug Log References

- Line references re-checked at e4c67c2: `services/mods.py`, `services/mod_state.py`, `services/mod_api.py`, `services/cache_eviction.py`, `services/mod_updates.py` and `routers/mods.py` matched the story. `main.py` had changed (Stories 19.2/19.3): the lifespan is now the closure in `lifespan_for(settings)`; `prepare_mod_files()` is called there after `ensure_data_directories()` and the `api_starting` log and before the auto-start block and `SchedulerService().start()`.
- Red runs: Task 1, 7 failing (6 `TestFileNamesIgnoreCase`, `filenames()`); Task 2, 26 failing (incl. the two "Existing tests that change"); Task 3, the enable/disable missing-file tests failed with `FileNotFoundError` (500 path); Task 4, collection failed on the missing `prepare_mod_files`/`mod_file_recovery`; Task 5, 36 failing (17 eviction, 2 edge-case, 5 version-change cache paths, the new `cache_path`/`remove_flat_layout`/concurrency tests).
- The first Task 4 commit raised pyright from 3 to 6 warnings (an untyped test table in `test_mod_file_recovery.py`); fixed in `test(story-19.4/task-4): type the recovery test table`. Pyright is back at 0 errors, 3 warnings (`VSS-1ar`).
- The E2E spec first compared the real `GET /api/v1alpha1/mods` in an `afterEach`; run in parallel with `installed-status.spec.ts` (which installs and removes `playercorpse`) it saw that spec's install and failed. The comparison moved out of the spec (header says why); it was done around the runs instead (below).
- `dev/` (the API tests' `VS_DATA_DIR`): neither `dev/vsmanager/cache/mods` nor `dev/serverdata/Mods` exists, before or after `just test-api`/`just check`; `git status --short dev/` is empty. The Docker dev stack mounts `./data`, not `dev/`.
- Docker dev stack (`just docker restart` from this branch; no game server process before or after): start-up log `mod_cache_old_layout_removed files=9`, no `mod_recovery_failed`, no `mod_files_startup_failed`, no recovery events (the mods directory had no working files). The mods directory listing and `GET /api/v1alpha1/mods` were byte-identical before the restart, after it, after the new spec alone and after the three specs together. The only difference: the 9 flat files in `cache/mods` were removed (by design, ADR-11 decision 5); after the E2E runs the cache holds one `<fileid>/` directory from `installed-status.spec.ts`'s install.

### Completion Notes List

- Story created 2026-11-16 (create-story, non-interactive) and validated against the create-story checklist. A throwaway prototype of Tasks 1-5 (the helper, enable/disable/version change checks, Update All, `.vsm-*` suffixes, recovery and the start-up call, the file-ID cache, eviction one level down) was run against the whole API suite (27 failures, all listed in "Existing tests that change") and pyright (0 errors, 3 warnings), then discarded.
- Task 1: `ModFileOperation`, `ModFileConflictError(slug, filename, *, operation)`, `ModStateManager.filenames()` and `ModService._refuse_taken_names` as in Dev Notes "The check"; `_place_install` calls it first. `TestInstallRefusesAFileNameInUse` and `test_mods_router.py`'s Story 18.2 message pass unchanged.
- Task 2: enable/disable check the one name they rename to; `_apply_version_change` checks `(release, release + ".disabled")` first, before `mkdir`, and the old `new_path.exists()` refusal is gone; `same_file` compares with `casefold()`; `_rollback_version_change` restores the backup under the old state's name and first unlinks a differently spelled new file. Update All records a conflict as a `failed` item; the routes map it to 409 `MOD_FILE_CONFLICT` (version change before `ModVersionChangeFailedError`).
- Task 3: `ModFileMissingError` and `ErrorCode.MOD_FILE_MISSING`; enable/disable check `is_file()` of the own file after the idempotent return and before the name check (a directory or a dangling symlink is missing). `remove_mod` is unchanged; its regression tests pass.
- Task 4: `services/mod_file_recovery.py` (only imports `mod_state`); working files are `<name>.vsm-tmp` / `<name>.vsm-bak`; `prepare_mod_files()` in `services/mods.py`, called from the lifespan inside `try/except OSError` → `mod_files_startup_failed`. The autouse conftest fixture `prepare_mod_files_recorder` replaces `vintagestory_api.main.prepare_mod_files`, so no lifespan test touches the real data directory. Beyond the story's text: when several entries casefold to a backup's name (only possible on a case-sensitive volume), the backup is deleted if the state describes any of them, otherwise every differently spelled one is removed before the restore; `replaced=` names them comma-joined (one name in the normal case).
- Task 5: `ModApiClient.cache_path(fileid, filename)` and `remove_flat_layout()`; `download_release_file` writes `cache/mods/<fileid>/<uuid>.tmp` opened `"xb"` and renames it into place; `_acquire_release_archive` uses `cache_path` (`safe_release_filename` is no longer imported in `services/mods.py`). `prepare_mod_files` step 2 logs `mod_cache_old_layout_removed`. Eviction globs `*/<pattern>`, removes directories it empties and, first in `evict_if_needed` (also with eviction disabled), deletes `*/*.tmp` older than `STALE_TEMP_AGE` (1 hour). Log events beyond the story's list: `mod_cache_old_file_not_removed` (warning, a flat file that cannot be deleted), `cache_temp_file_not_removed` (warning) and `cache_directory_kept` (debug, `rmdir` of a non-empty directory).
- Task 6: web unit tests pin AC 18 against the unchanged source (4 enable/disable refusals, 1 version-change conflict, 1 Update All failed item); no web source change. New `web/e2e/mod-file-refusals.spec.ts` stubs every mod route, gets the key through Story 19.2's `serveConfigKey` and counts the writes.
- Results: `just check` green: API 3181 passed; web 3349 passed, 4 skipped (`VSS-hnl`); pyright 0 errors, 3 warnings (`VSS-1ar`); script tests green. E2E against the rebuilt dev stack: `mod-file-refusals.spec.ts` 3 passed alone; with `install-file-conflict.spec.ts` and `installed-status.spec.ts` 9 passed. No lint or type suppression, no `cast`, no `pytest.skip`/`xfail` in the diff.
- Not done here: Task 6.4 is the maintainer's manual check (unticked). Task 6.5's PR, its "API contract changes" description and the PR link on the six beads were not done (the dev brief forbids push/PR and bead changes); the story status and sprint status are set to review. `VSS-uoxl` stays open for Story 19.5.

### File List

- api/src/vintagestory_api/main.py (modified)
- api/src/vintagestory_api/models/errors.py (modified)
- api/src/vintagestory_api/routers/mods.py (modified)
- api/src/vintagestory_api/services/cache_eviction.py (modified)
- api/src/vintagestory_api/services/mod_api.py (modified)
- api/src/vintagestory_api/services/mod_file_recovery.py (new)
- api/src/vintagestory_api/services/mod_state.py (modified)
- api/src/vintagestory_api/services/mod_updates.py (modified)
- api/src/vintagestory_api/services/mods.py (modified)
- api/tests/conftest.py (modified)
- api/tests/test_cache_eviction.py (modified)
- api/tests/test_edge_cases.py (modified)
- api/tests/test_main.py (modified)
- api/tests/test_mod_api.py (modified)
- api/tests/test_mod_file_names.py (new)
- api/tests/test_mod_file_recovery.py (new)
- api/tests/test_mod_operation_lock.py (modified)
- api/tests/test_mod_service.py (modified)
- api/tests/test_mod_state.py (modified)
- api/tests/test_mod_update_all.py (modified)
- api/tests/test_mod_update_all_router.py (modified)
- api/tests/test_mod_version_change.py (modified)
- api/tests/test_mod_version_change_router.py (modified)
- api/tests/test_mods_router.py (modified)
- web/e2e/mod-file-refusals.spec.ts (new)
- web/src/components/UpdateAllDialog.test.tsx (modified)
- web/src/hooks/use-mods.test.tsx (modified)
- web/src/hooks/use-version-change-flow.test.tsx (modified)
- _bmad-output/implementation-artifacts/19-4-mod-files-are-never-overwritten.md (modified)

## Change Log

- 2026-11-16: Story 19.4 created and validated (ready-for-dev).
- 2026-11-16: Tasks 1-5 and 6.1-6.3 implemented; status review. 6.4 (manual check) waits for the maintainer; 6.5's PR and bead links are left to the maintainer.
