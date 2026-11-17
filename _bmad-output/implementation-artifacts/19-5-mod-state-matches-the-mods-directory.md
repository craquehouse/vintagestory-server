# Story 19.5: The Mod State Matches the Mods Directory at Start-Up

Status: review

<!-- Implements FR231-FR232, Epic 19 ADR-10 (ADR-9 defines the recovery this runs after). Beads: none of its own; it rides with VSS-uoxl (API-092), which Story 19.4 starts and this story closes. Stacked on Story 19.4 (stories run in order 19.1 to 19.7). Line references were verified at b6ae2f2 (epic-19-planning; its api/ and web/ are identical to 048fea9, the commit the ADRs cite) and must be re-checked at implementation time: Story 19.2 rebuilds main.py around an app factory, and Story 19.4 edits services/mod_state.py, services/mods.py and the start-up first. API only: no web source change, no new route, no new error code, no new dependency. -->

## Story

As an **administrator who sometimes adds or deletes mod files by hand**,
I want **the manager to bring its list of installed mods in line with the mods directory when it starts**,
so that **the Installed list shows what is really there**.

## Acceptance Criteria

1. **Given** a readable mod archive `New.zip` copied into the mods directory by hand, and another as `Off.zip.disabled`
   **When** the API starts
   **Then** both are in `GET /api/v1alpha1/mods` with the mod ID and version from their `modinfo.json` (top-level keys matched without case, as an install does), the first enabled and the second disabled, with `asset_id` 0 and `installed_at` the time of the sync; each addition is logged at info level with its file name and mod ID
   *(Covers FR231)*

2. **Given** a mod state entry whose file is no longer in the mods directory
   **When** the API starts
   **Then** the entry is gone from the Installed list, the removal is logged at info level with its file name and mod ID, and no file in the mods directory was created, renamed or deleted
   *(Covers FR231)*

3. **Given** a state entry whose file exists under a name that does not end in `.zip` or `.zip.disabled`
   **When** the API starts
   **Then** the entry stays, unchanged
   *(Covers FR231)*

4. **Given** a `.zip` in the mods directory that cannot be read or has no usable `modinfo.json` (not a zip, no `modinfo.json`, a `modinfo.json` that is not an object or lacks a mod ID, an archive Python cannot open, a file without read permission)
   **When** the API starts
   **Then** start-up completes, the file gets no state entry (not even one named after the file), its bytes are unchanged, and exactly one `mod_state_sync_skipped` warning names it
   *(Covers FR232)*

5. **Given** a `.zip` added by hand whose mod ID (compared without case, like the mod lock) is already installed under another file
   **When** the API starts
   **Then** the existing entry stays unchanged, no second entry is added, and one warning names both files
   *(Covers FR232)*

6. **Given** `.vsm-tmp`, `.vsm-bak`, `.tmp` and `.bak` files, a directory (also one named `something.zip`) and a text file in the mods directory
   **When** the API starts
   **Then** none of them is added to the state, none is counted as skipped, and the sorted directory listing and every file's bytes are the same after the sync as before it
   *(Covers FR232)*

7. **Given** an interrupted version change left a working file and a kept-aside original
   **When** the API starts
   **Then** Story 19.4's recovery runs first and the sync then sees the recovered file, so the mod is neither removed nor added twice
   *(Covers FR231)*

8. **Given** the mods directory does not exist when the API starts, or it cannot be listed
   **When** the sync runs
   **Then** no state entry is removed, nothing is saved, and a warning says the directory was not found (or could not be read)
   *(Covers FR232; ADR-10 decision 10)*

9. **Given** any start-up
   **When** the sync has run
   **Then** exactly one summary line gives the numbers added, removed and skipped, also when all are zero and also in the cases of AC 8, and the game server's auto-start comes after it
   *(Covers FR231, FR232)*

10. **Given** the API
    **When** I look for a way to run the sync again
    **Then** there is no route and no button for it; it runs only at start-up
    *(Covers FR231)*

11. **Given** a mod that was renamed by hand between `Foo.zip` and `Foo.zip.disabled`, or replaced by hand with another file of the same mod ID (the state names a file that is gone, and a new file carries that mod ID)
    **When** the API starts
    **Then** the Installed list has exactly one entry for the mod, under the file that is there, with the enabled flag its name gives; the mod does not vanish from the list
    *(Covers FR231; derived: removals are applied before additions)*

12. **Given** a sync that added one mod and removed another, with a stored update record for the removed one
    **When** I read `GET /api/v1alpha1/mods/updates`
    **Then** the added mod is `unknown` with reason `not_checked`, the removed mod has no item, and the sync neither looked anything up in the mod database, nor wrote the update store, nor set a pending restart
    *(Covers FR231; ADR-10 decision 7)*

13. **Given** the mod state cannot be saved after the sync, or the sync fails in a way nobody planned for
    **When** the API starts
    **Then** the failure is logged as an error, start-up continues and the game server auto-start still runs
    *(Covers FR232; ADR-10 decision 6)*

14. **Given** the API test suite
    **When** it runs (`just test-api`, which sets `VS_DATA_DIR=../dev`)
    **Then** every test that passed before still passes, and no test runs the start-up sync against `dev/`: `git status --short` shows nothing under `dev/` afterwards
    *(Regression guard; Story 17.4 and 18.2 learning)*

## Tasks / Subtasks

<!-- Each functional task includes its tests in the same commit. Commit per task: type(story-19.5/task-N): ...; feat/fix only for changes an admin can see, subject written for admins. Red first. Only Task 3 changes what an admin sees. -->

- [x] Task 1: Make `sync_state_with_disk` safe + tests (AC: 1, 2, 3, 4, 5, 6, 8, 11, 13)
  - [x] 1.1: `services/mod_state.py`: a small frozen dataclass `ModSyncSummary(added: int, removed: int, skipped: int)` above `ModStateManager` (`:27`). `sync_state_with_disk` (`:492-549`) returns it instead of `None` (every existing caller ignores the result)
  - [x] 1.2: Rewrite the body in the order of Dev Notes "The sync": directory guard, one listing, removals, then additions over the sorted new names, one save. It must not call `import_mod` (Dev Notes "ADR against the code")
  - [x] 1.3: Removal (ADR-10 decision 4): an entry is removed only when its own file name is not among the names of one successful `iterdir()` of the mods directory. Not `state_files - disk_files` (`:530`) and not a per-entry `is_file()` (Dev Notes "Why a listing")
  - [x] 1.4: Addition (decisions 2 and 3): per new file, read and validate `modinfo.json` inside a guard that catches `Exception`; skip an unreadable archive; skip a file whose mod ID, lower-cased, is already in the state or was added earlier in this run; otherwise cache the modinfo and add the entry
  - [x] 1.5: One `save()` after all changes, only when something was added or removed; an `OSError` from it is caught (decision 6). The method never raises for anything the directory or an archive can contain
  - [x] 1.6: Update the method's docstring: what is added, skipped and removed, that it deletes no file, and that it is meant to be called once at start-up
  - [x] 1.7: Tests (Dev Notes "API tests", Task 1 rows), red first

- [x] Task 2: Log every change and one summary + tests (AC: 1, 2, 4, 5, 8, 9)
  - [x] 2.1: Events and keys exactly as in Dev Notes "Logging": `mod_state_sync_added`, `mod_state_sync_removed`, `mod_state_sync_skipped`, `mod_state_sync_mods_directory_not_found`, `mod_state_sync_mods_directory_unreadable`, `mod_state_sync_save_failed`, and always one `mod_state_synced`. The old events `mod_state_added` and `mod_state_removed_deleted_file` (`:523`, `:536`) go; nothing else uses them
  - [x] 2.2: Tests (Dev Notes "API tests", Task 2 rows), red first

- [x] Task 3: Call the sync once at start-up, before the game server auto-start + tests (AC: 7, 9, 10, 13, 14)
  - [x] 3.1: `services/mods.py`: a module-level `sync_mod_state_at_startup() -> None` beside `close_mod_service` (`:121-130`): `get_mod_service().state_manager.sync_state_with_disk()` inside `try`/`except Exception`, logging `mod_state_sync_failed` at error level. It never raises. `get_mod_service` (`:77-118`) is not changed by this story (Dev Notes "Where it is called")
  - [x] 3.2: The lifespan in `main.py` (`:91-162` at b6ae2f2; reached through Story 19.2's app factory by then): call `sync_mod_state_at_startup()` after Story 19.4's recovery and before the auto-start block (`:117-141`), imported inside the lifespan as the block's other services are (`:118-120`). No route, no job, no timer, no call from `get_mod_service`
  - [x] 3.3: `api/tests/conftest.py`: an autouse fixture that replaces `vintagestory_api.services.mods.sync_mod_state_at_startup` with a no-op for every test (Dev Notes "Tests must not sync `dev/`"). If Story 19.4 added such a guard for its recovery, extend that one instead of adding a second
  - [x] 3.4: `README.md`: one sentence under Features, after the Mods bullet (`:13`), or in Installation after "Game data, mods and manager state live in `./data`" (`:33`): mod archives (`.zip`, or `.zip.disabled` for a disabled mod) copied into or deleted from `data/serverdata/Mods` by hand are picked up the next time the manager container starts
  - [x] 3.5: Tests (Dev Notes "API tests", Task 3 rows), red first

- [x] Task 4: API tests of start-up through the routes and of update status, and the Docker stack regression run (AC: 1, 2, 12, 14)
  - [x] 4.1: API integration tests (Dev Notes "API tests", Task 4 rows): the real lifespan over a hand-built directory and state, then `GET /api/v1alpha1/mods` and `GET /api/v1alpha1/mods/updates`
  - [x] 4.2: Docker dev stack (Dev Notes "E2E"): no new spec. With the guard conditions met, snapshot `GET /api/v1alpha1/mods`, rebuild the stack from this branch, compare, read the one `mod_state_synced` line from the container log, and re-run `web/e2e/installed-status.spec.ts`. Record the before and after bodies' equality (or the explained difference) and the summary line's numbers in the Dev Agent Record

- [ ] Task 5: Quality gate and review hand-off (AC: all)
  - [x] 5.1: `just check` passes; the diff adds no lint or type suppression and no `cast`; pyright stays at 0 errors and the 3 pre-existing warnings (`VSS-1ar`); after `just test-api`, `git status --short` shows nothing under `dev/`
  - [ ] 5.2: Manual check on the Docker stack (needs the maintainer's confirmation before it is ticked, `project-context.md`): see Dev Notes "Manual check"
  - [ ] 5.3: Story status `review`, `just sprint set 19-5-mod-state-matches-the-mods-directory review`, PR (base: Story 19.4's branch while its PR is open, otherwise `main`), PR link on `VSS-uoxl`. The PR description carries "API contract changes" from this story. `VSS-uoxl` is closed with its AAR (covering Story 19.4's recovery and this story's sync) when this story is done, not before

## Dev Notes

### What is wrong today (verified at b6ae2f2)

- `ModStateManager.sync_state_with_disk` (`services/mod_state.py:492-549`) is called by nothing in `api/src`. Only tests call it, as a way to get a mod into the state (`tests/test_mod_service.py`, 21 calls from `:168`; `tests/test_mods_router.py`, 17 calls from `:394`; `tests/test_mod_state.py:1205-1328`).
- The mod state is loaded lazily, by the first `get_mod_service()` (`services/mods.py:107-108`: `load()`, then `repair_fallback_entries()`). The lifespan (`main.py:91-162`) does not touch the mod service before the auto-start block (`:117-141`); the first call usually comes from `ServerService._update_mod_service_server_state` (`services/server.py:211-231`) or from the first request.
- As written the sync is not safe at start-up; see "ADR against the code" for what exactly goes wrong, which differs from the ADR's wording in one point.

### The sync (Tasks 1 and 2)

`sync_state_with_disk(self) -> ModSyncSummary`, all synchronous, in this order:

1. **Directory guard (decision 10).** `if not self._mods_dir.is_dir():` warn `mod_state_sync_mods_directory_not_found`, log the summary with zeros, return. Nothing is removed and nothing is saved.
2. **One listing.** Inside `try`/`except OSError`: `names = {p.name for p in self._mods_dir.iterdir()}` and `candidates = sorted(self.scan_mods_directory())` (`:465-490`, unchanged: regular files ending in `.zip` or `.zip.disabled`). On `OSError`: warn `mod_state_sync_mods_directory_unreadable`, summary with zeros, return; nothing removed, nothing saved.
3. **Removals first.** For each state key not in `names`: delete the entry, log `mod_state_sync_removed`. Removals come before additions so that a hand rename or a hand replacement (AC 11) is one removal plus one addition; done the other way round, the new file would be skipped as a duplicate of the entry that is about to be removed, and the mod would vanish from the list until the next start.
4. **Additions.** Build `by_mod_id = {entry.slug.lower(): filename}` from the entries that remain. For each name in `candidates` that is not a state key:
   - read it inside `try`/`except Exception`: `data = self._extract_modinfo_from_zip(path)` (`:301-353`), then `ModMetadata.model_validate(data)` when `data` is not `None`. `None`, a `ValueError` from validation, or any other exception: skip with reason `unreadable`;
   - `existing = by_mod_id.get(metadata.modid.lower())`: if set, skip with reason `duplicate_mod_id`, naming both files. The comparison is `ModService._lock_key`'s (`services/mods.py:336-339`, `mod_id.lower()`); do not import from `services/mods.py` (it imports this module), write `.lower()` here with a comment naming `_lock_key`;
   - otherwise `self._cache_modinfo(metadata.modid, metadata.version, data)` (`:355-385`; an `OSError` from it is logged as a warning and the entry is still added: `list_mods` falls back to the mod ID as the name without a cached modinfo, `services/mods.py:419`), then `self._state[filename] = ModState(filename=..., slug=metadata.modid, version=metadata.version, enabled=not filename.endswith(".disabled"), installed_at=datetime.now(UTC))` (`asset_id` keeps its default 0), add it to `by_mod_id`, log `mod_state_sync_added`.
   - `candidates` is sorted so that, of two new files with one mod ID, the same one wins on every start (the other is skipped, AC 5).
5. **One save,** only if something was added or removed: `self.save()` (`:101-136`) inside `try`/`except OSError`, logging `mod_state_sync_save_failed` at error level. The in-memory state keeps the changes; the next start tries again (decision 6).
6. **Summary,** always: `mod_state_synced` with `added`, `removed`, `skipped` and `total=len(self._state)`.

The sync creates, renames and deletes nothing in the mods directory. It does not delete the cached modinfo of a removed entry (`state/mods/<slug>/`); see "Not changed".

`except Exception` in step 4 is deliberate and is not a suppression: the guard is the boundary that keeps one bad file from stopping the API (FR232), and the set of exceptions `zipfile` and `json` raise for hostile input is open (see the table in "ADR against the code"). The lifespan already does the same for the auto-start (`main.py:138`). Ruff's selected rules (`E`, `F`, `I`, `UP`, `api/pyproject.toml:39`) do not flag it.

### Why a listing, not `is_file()` per entry (Task 1.3)

ADR-10 decision 4 says "checked per entry by its own file name and not by membership in the scan". Membership in a plain listing of the directory satisfies that (an entry for `odd.cs` stays, AC 3) and is safe where a per-entry probe is not: on Python 3.14 `Path.is_file()` returns `False` for any `OSError`, so a mods directory the process may not search (wrong ownership after a volume change, a stale network mount) would report every file as gone and the sync would remove every entry. `iterdir()` raises in that case, and the sync then changes nothing (AC 8). Checked on this machine: a directory with mode `000` gives `is_dir() == True`, `is_file() == False` for its files, and `iterdir()` raises `PermissionError`; with mode `400` the names are listed and `is_file()` is `False`, so nothing is added and nothing is removed.

Consequences of the listing rule, all intended:

- An entry whose name is in the listing stays whatever is there (a regular file, a dangling symlink, a directory). Enabling or disabling a mod whose file is not a regular file is still `MOD_FILE_MISSING` (ADR-9; ADR-10 decision 8).
- Names are compared exactly. A file renamed by hand only in case (`Foo.zip` to `foo.zip`) is one removal and one addition, so the entry ends up under the name that is on disk, on every filesystem.

### Logging (Task 2)

| Event | Level | Keys | When |
|---|---|---|---|
| `mod_state_sync_added` | info | `filename`, `slug`, `version`, `enabled` | per entry added |
| `mod_state_sync_removed` | info | `filename`, `slug` | per entry removed |
| `mod_state_sync_skipped` | warning | `filename`, `reason` (`unreadable` or `duplicate_mod_id`); for `unreadable` also `error` when an exception was caught; for `duplicate_mod_id` also `slug` and `existing` (the file the state already has) | per file skipped |
| `mod_state_sync_mods_directory_not_found` | warning | `path` | the directory does not exist |
| `mod_state_sync_mods_directory_unreadable` | warning | `path`, `error` | listing it raised `OSError` |
| `mod_state_sync_save_failed` | error | `error`, `path` | `save()` raised |
| `mod_state_synced` | info | `added`, `removed`, `skipped`, `total` | always, exactly once per call |
| `mod_state_sync_failed` (in `sync_mod_state_at_startup`) | error | `error` | anything else |

The mod ID is logged under the key `slug`, as this file's other events do (`mod_state_removed`, `:195`; `mod_state_repair_skipped_duplicate`, `:443-448`). Paths and file names are not secrets; no key or password is near this code.

"One warning" in AC 4 and AC 5 means exactly one `mod_state_sync_skipped` line per skipped file. The reader's own line about why an archive is unusable (`modinfo_extraction_failed` at warning, `:348`; `modinfo_not_object`, `:337`; `modinfo_not_found_in_zip` at debug, `:341`) may come before it and is not changed: installs and the fallback repair use the same reader and tests assert those events.

### Where it is called (Task 3)

- `sync_mod_state_at_startup()` lives in `services/mods.py` because it needs the singleton; the lifespan calls it. It is **not** called from `get_mod_service()`: that function is also reached by every request of a test client that never entered the lifespan, and by `ServerService`, so a sync there would run in hundreds of tests against `dev/` and at times nobody chose. `tests/test_mod_service.py:716-742` pins `get_mod_service` to `load` then `repair`; with this design it stays as Story 19.4 leaves it.
- **Order inside start-up:** state `load()` → Story 19.4's recovery (ADR-9 decision 6) → `repair_fallback_entries()` (either side of the recovery, as 19.4 left it) → the sync → the auto-start block → the scheduler (`main.py:143-150`). Find where Story 19.4 calls its recovery. If it is in the lifespan, call `sync_mod_state_at_startup()` directly after it. If it is inside `get_mod_service()`, the sync function's own `get_mod_service()` call runs it first. Either way the order test of Task 3 must show recovery, then sync, then `start_server`.
- The sync runs before `yield`, synchronously, with no `await`: no request is being served, no scheduled job has been registered, and `ModService.busy_mod_ids` is empty. It takes no per-mod lock and needs none. This is the only reason it may change the state without `_hold`; it must never be called from a route, a job or a thread (AC 10).
- **Story 19.4's name check** (ADR-8) is not involved: the sync puts no file name into the directory. Its results feed the check afterwards in the right way: a removed ghost entry frees its file name (before, a state entry without a file answered 409 `MOD_FILE_CONFLICT` to an install of that name, Story 18.2 AC 3), and a skipped file is still in the directory listing, so its name stays taken.
- **Story 19.4's working files:** `<name>.vsm-tmp` and `<name>.vsm-bak` (ADR-9 decision 5) and old-style `.tmp` and `.bak` files do not end in `.zip` or `.zip.disabled`, so `scan_mods_directory` never returns them. After the recovery, a mod whose file was put back from `.vsm-bak` is in the listing under its state key: not removed, not added (AC 7). Without the recovery first, that entry would be removed and the mod lost from the list, which is why the order is tested.
- A fresh install has no `serverdata/Mods` yet: `ensure_data_directories` (`config.py:162-203`) creates `serverdata` but not `Mods`, which the game server or the first install creates (`_place_install`). Such a start logs the not-found warning and the zero summary. That is AC 8 as written; see "Not changed".

### Tests must not sync `dev/` (Task 3.3, AC 14)

`just test-api` runs with `VS_DATA_DIR=../dev` (`justfile:35`), and these tests enter the real lifespan with the real `Settings()`: `tests/test_scheduler.py:342-400` (4), `tests/test_jobs_registration.py:250-280` (2), the `lifespan_client` fixture of `tests/test_jobs_router.py:40-42`, the client fixture of `tests/console/conftest.py:103`. `tests/test_main.py:284-572` (5) patch `main.Settings` but `get_mod_service` builds its own `Settings()` (`services/mods.py:90`), and Story 19.2's factory does not change the services (ADR-5 decision 11).

Measured with a throwaway prototype (since discarded): with a mod archive in `dev/serverdata/Mods`, one run of the suite wrote `dev/vsmanager/state/mods.json` and `dev/vsmanager/state/mods/<modid>/`. `dev/` is not git-ignored, and on a developer's machine it is the data of `just dev-api`.

So `api/tests/conftest.py` gets an autouse fixture, for example:

```python
@pytest.fixture(autouse=True)
def no_startup_mod_sync(monkeypatch: pytest.MonkeyPatch) -> None:
    """The lifespan's mod state sync must never run against VS_DATA_DIR in tests."""
    monkeypatch.setattr(mods_module, "sync_mod_state_at_startup", lambda: None)
```

The lifespan imports the name inside the function, so it gets the replacement. Tests of the real function import it at module top (`from vintagestory_api.services.mods import sync_mod_state_at_startup`), which binds the real object before any fixture runs; a test that needs the real function inside the lifespan puts it back with `monkeypatch.setattr` and points the singleton at a service on `tmp_path` (`monkeypatch.setattr(mods_module, "_mod_service", service)`, as `tests/test_mod_service.py:731` does; do not copy the `# pyright: ignore` assignments at `:684` and `:699`).

### API tests

Hand-built directories and states on `tmp_path`; never `dev/`. Helpers: `create_mod_zip` (`tests/test_mod_state.py:524`), the `state_manager`, `temp_mods_dir`, `temp_state_dir` fixtures (`:16-38`), `captured_logs` (`tests/conftest.py`). For every case that must not touch files, compare the sorted listing of the mods directory and each file's bytes before and after.

| Task | File | Test |
|---|---|---|
| 1 | `tests/test_mod_state.py`, new class `TestSyncAtStartUp` after `TestSyncStateWithDisk` (`:1205`) | AC 1: `New.zip` (`{"modid": "newmod", "name": "New", "version": "1.2.3"}`) and `Off.zip.disabled` (keys `ModID`, `Name`, `Version` capitalized) → two entries with slug, version, `enabled` True/False, `asset_id == 0`, `installed_at` within the test's time window; the summary is `(2, 0, 0)`; `mods.json` on disk has both; the cached modinfo exists for both |
| 1 | same | AC 2: an entry `ghost.zip` with no file → removed, summary `(0, 1, 0)`, saved. AC 3: an entry `odd.cs` whose file exists → stays, equal to before, nothing saved (assert `mods.json` is not written when it did not exist) |
| 1 | same, parametrized | AC 4, each case a file `bad.zip`: bytes that are not a zip; a zip without `modinfo.json`; `modinfo.json` that is a JSON array; `modinfo.json` without `modid` (`ModMetadata` requires `modid`, `name` and `version`, `models/mods.py:32-38`, as an install does); a zip whose entry has an unsupported compression method (patch the method field to 99 in the local and central headers: `zipfile` raises `NotImplementedError`); a zip with the encryption flag set (`RuntimeError`); a `modinfo.json` of 200000 `[` characters (`RecursionError`); `_extract_modinfo_from_zip` monkeypatched to raise `PermissionError` (portable, no `chmod`). Each: no exception, no entry under any name (in particular none with slug `bad` and version `unknown`), bytes unchanged, summary `(0, 0, 1)`, and a good `New.zip` beside it is still added. Red first against the current code: the first two cases add a fallback entry, the next ones raise |
| 1 | same | AC 5: `Foo.zip` installed (entry, slug `foo`); `Foo-copy.zip` with `modid` `FOO` → entry for `Foo.zip` equal to before, no entry for the copy, summary `(0, 0, 1)`. Two new files with one mod ID and no entry: the one that sorts first is added, the other skipped, and a second sync changes nothing |
| 1 | same | AC 6: `a.zip.vsm-tmp`, `a.zip.vsm-bak`, `b.zip.tmp`, `b.zip.bak`, `notes.txt`, a directory `dir.zip`, a directory `plain` → summary `(0, 0, 0)`, listing and bytes unchanged |
| 1 | same | AC 8: mods directory absent, with two entries in the state → both stay, summary zeros, `mods.json` not written. Same with `Path.iterdir` monkeypatched to raise `PermissionError` for the mods directory. Same with the mods path being a regular file |
| 1 | same | An empty mods directory with two entries → both removed (ADR-10 "an empty directory"); this is the difference from AC 8 and both tests say so in their names |
| 1 | same | AC 11: entry `Ren.zip.disabled` (slug `ren`, disabled), file `Ren.zip` on disk → exactly one entry for `ren`, key `Ren.zip`, enabled; summary `(1, 1, 0)`. Entry `Up_1.0.zip`, file `Up_1.1.zip` (same mod ID, version `1.1.0`) → one entry, version `1.1.0`. Red first if additions run before removals |
| 1 | same | AC 13: `save` monkeypatched to raise `OSError` → no exception, the in-memory state has the changes, summary counts them. `_cache_modinfo` raising `OSError` → the entry is still added |
| 1 | same | A dangling symlink under an entry's name → the entry stays (listing rule). An entry `Foo.zip` with only `foo.zip` on disk: one entry, key `foo.zip`; the result is the same whether `tmp_path` is case-sensitive or not, so the test needs no skip |
| 2 | same | Log lines: AC 1 has two `mod_state_sync_added` lines each with file name and mod ID; AC 2 one `mod_state_sync_removed` with both; AC 4 exactly one `mod_state_sync_skipped` line containing `bad.zip` and `unreadable`; AC 5 exactly one containing both file names and `duplicate_mod_id`; AC 8 the not-found (or unreadable) warning. Every case: exactly one `mod_state_synced` line with the three numbers, also `added=0 removed=0 skipped=0`. The old events `mod_state_added` and `mod_state_removed_deleted_file` do not appear |
| 3 | new `tests/test_mod_state_sync_startup.py` | `sync_mod_state_at_startup` (the real function, imported at module top) with the singleton on `tmp_path`: syncs that service's state once. With `sync_state_with_disk` monkeypatched to raise `RuntimeError`, and with `get_mod_service` raising: no exception, one `mod_state_sync_failed` error line (AC 13) |
| 3 | same, or `tests/test_main.py` `TestLifespanAutoStart` (`:284`) | Order (AC 9): the lifespan with auto-start on and a mock server service in state `INSTALLED` (the pattern of `:288-349`, built the way Story 19.2's tests build the app), Story 19.4's recovery and `sync_mod_state_at_startup` replaced by recorders, `start_server` recording too: the recorded order is recovery, sync, start. With the real `sync_mod_state_at_startup` put back and `sync_state_with_disk` raising, `start_server` is still awaited (AC 13). With auto-start off, the sync is still called once |
| 3 | same | AC 7 with the real functions on `tmp_path`: state entry `Foo.zip` at version `1.0.0`, the directory holds only `Foo.zip.vsm-bak` (the original) and `Foo.zip.vsm-tmp` → after the lifespan's start-up the directory holds `Foo.zip` only and the state has exactly the one entry, unchanged. Names per ADR-9 decision 5; use the constants Story 19.4 defines |
| 3 | same | AC 10: no route of the app has a path containing `sync` (`[r.path for r in app.routes]`). That `sync_state_with_disk` has exactly one caller in `api/src` (`sync_mod_state_at_startup`) is a review check, not a test: record the output of `grep -rn sync_state_with_disk api/src` in the Dev Agent Record |
| 3 | same | AC 14 guard: with the autouse fixture in place, entering `TestClient(app)` as a context manager does not call `ModStateManager.sync_state_with_disk` (spy with `monkeypatch`) |
| 4 | new class in `tests/test_mods_router.py` or the new file | Through the API: singleton on `tmp_path` with entries `Kept.zip` (file present) and `Gone.zip` (no file), `New.zip` and `Off.zip.disabled` added by hand; the real sync put back; enter the lifespan; `GET /api/v1alpha1/mods` lists `Kept`, `New` (enabled) and `Off` (disabled) and not `Gone`; `POST /api/v1alpha1/mods/<gone slug>/disable` is 404 `MOD_NOT_INSTALLED` (`routers/mods.py:925`); `pending_restart` in the list's `data` is false |
| 4 | `tests/test_mod_updates.py` (`make_service` `:324`) or the same class | AC 12: an update store on `tmp_path` holding a record for the removed mod's ID; after the sync `get_status()` has an item for the added mod with `status == "unknown"`, `reason == "not_checked"`, and none for the removed mod; the store file's bytes are unchanged; respx with no routes registered proves no mod database request was made |

### Existing tests that change (deliberately)

Found by running the whole API suite against a throwaway prototype of Tasks 1 to 3 (the rewritten sync, `sync_mod_state_at_startup`, the lifespan call, without the conftest guard; since discarded): **2858 passed, none failed**, the same number as at b6ae2f2 without the prototype. Pyright: 0 errors, the 3 pre-existing warnings. Ruff clean.

- **No existing test fails.** All 46 existing calls of `sync_state_with_disk` (`tests/test_mod_service.py:168-661` and `:979`, `tests/test_mods_router.py:394-1807`, `tests/test_mod_state.py:1217-1318`) sync archives with a readable `modinfo.json` and ignore the return value; none relies on the fallback entry for an unreadable archive, on the old event names, or on a ghost entry surviving.
- **Not failing, but the reason this story has Task 3.3:** the eleven real-lifespan tests and two fixtures listed in "Tests must not sync `dev/`" ran the sync against `dev/` in the prototype. With the autouse guard they do not.
- `tests/test_mod_service.py:716-742` (`get_mod_service` calls `load` then `repair`) stays as Story 19.4 leaves it; this story does not add a call there.
- `tests/test_mod_state.py` `TestScanModsDirectory` (`:1123-1202`), `tests/test_mod_state_coverage.py:226-255` and `tests/test_edge_cases.py:234`: `scan_mods_directory` is unchanged.
- Environment note: in a fresh worktree without `.env`, `just test-api` fails many lifespan, scheduler and jobs tests because `VS_API_KEY_ADMIN` is unset. Set it (or work where `.env` exists) before reading results.
- Anything else that fails is a regression: fix the code, not the test.

### E2E (Task 4.2)

No new Playwright spec, and the reason is part of the story: the web does not change, and the effect appears only after the manager restarts, which an E2E run must not do to the dev stack (a restart of the container stops a running game server, and with auto-start on it starts one). What an E2E spec would have shown is covered instead by the Task 4 API tests, which drive the real lifespan and read `GET /api/v1alpha1/mods` and `GET /api/v1alpha1/mods/updates`.

What is run against the Docker dev stack (port 8080), with the Admin key from `.env`, no screenshots:

1. **Guard.** `GET /api/v1alpha1/server/status`: the game server must not be running. `GET /api/v1alpha1/config/api/settings`: `auto_start_server` must be false. If either fails, stop here, change nothing, and leave the run to the maintainer (record that in the Dev Agent Record).
2. **Snapshot.** Save the body of `GET /api/v1alpha1/mods` (outside the repository).
3. `just docker restart` from this branch. This is the one restart; it runs the sync once on the stack's own mods directory.
4. **Compare.** `GET /api/v1alpha1/mods` again. On a stack whose state already matched its directory the bodies are identical. If they differ, every difference must be one the container log explains with a `mod_state_sync_added`, `mod_state_sync_removed` line; record the lines (mod IDs and file names only). That is the feature working on drift that was already there; do not undo it and do not edit files in `data/` to make the bodies match. Tell the maintainer.
5. `docker compose -f docker-compose.dev.yaml logs` shows exactly one `mod_state_synced` line since the start, before any `auto_start` line.
6. Regression: `cd web && bunx playwright test e2e/installed-status.spec.ts` (it stubs the list for two tests and installs and removes one mod under its own snapshot guard). Compare `GET /api/v1alpha1/mods` with step 4's body afterwards.

Do not start or stop the game server. Do not copy files into `data/serverdata/Mods` in this task; that is the manual check.

### Manual check (Task 5.2, maintainer)

On the Docker dev stack built from this branch, game server stopped and `auto_start_server` off (so no restart starts it):

1. Snapshot: save `GET /api/v1alpha1/mods` and the listing of `data/serverdata/Mods`.
2. Make an archive that holds only a `modinfo.json` with a mod ID nothing uses, for example `{"type": "content", "modid": "vsmhandcheck", "name": "Hand check", "version": "0.0.1"}`, and copy it into `data/serverdata/Mods` as `vsmhandcheck.zip`.
3. `just docker restart`. The Installed page lists "Hand check" 0.0.1, enabled, with "Not checked yet"; the log has one `mod_state_sync_added` line for it and the summary `added=1`.
4. Rename the file by hand to `vsmhandcheck.zip.disabled`, restart: the mod is listed once, disabled.
5. Delete the file by hand, restart: the mod is gone from the list; the log has one `mod_state_sync_removed` line and `removed=1`.
6. Restore check: `GET /api/v1alpha1/mods` and the directory listing equal the snapshot. (`data/vsmanager/state/mods/vsmhandcheck/` is left behind, see "Not changed"; delete that directory by hand.)

Never start the game server with the check archive in place.

### Not changed (do not "fix" these here)

- `scan_mods_directory` still matches only `.zip` and `.zip.disabled`; a mod file of another form added by hand is not picked up (`VSS-v3be`).
- A mod added by the sync has `asset_id` 0 and no update record until the next check; a mod renamed or replaced by hand gets a new entry, so its former `asset_id` and `installed_at` are not carried over (ADR-10 decision 2 gives the new entry's values). Looking hand-added mods up in the mod database is `VSS-v3be`.
- The update store is not written by the sync. A removed mod's record, lookup error and alert record stay in `mod-updates.json` until the next check prunes them (`services/mod_updates.py:479`, `prune` `:170-174`); they are not shown, because the status is built from the installed mods only (`build_status_items`, `:217-241`).
- The cached modinfo directory of a removed entry (`state/mods/<slug>/`) is left; `remove_mod` deletes it for a removal through the manager (`services/mods.py:866-869`). It is small, and a later install or sync of the mod rewrites it.
- `import_mod` and its filename fallback (`services/mod_state.py:197-251`), `read_modinfo`, `_extract_modinfo_from_zip` and their log events; `repair_fallback_entries`; `get_mod_service`.
- No pending-restart flag, no update check, no webhook alert from the sync (decision 7).
- `MOD_FILE_MISSING` (Story 19.4) stays for a file removed between restarts (decision 8).
- Old-style `.tmp` and `.bak` files: Story 19.4 warns about them; the sync ignores them (`VSS-hv60` is the follow-up).
- The not-found warning on a fresh install that has no `Mods` directory yet (AC 8 asks for a warning whenever the directory is missing).
- No web change: the Installed page has no "rescan" control and gets none (AC 10).

### API contract changes

- No route, field or error code is added or changed.
- **Behavior change at start-up** (`GET /api/v1alpha1/mods`, and every route that looks an installed mod up): after a restart of the manager the installed mods are those in the mods directory. A `.zip` or `.zip.disabled` archive with a readable `modinfo.json` that was added by hand is listed (`asset_id` 0, `installed_at` the start time, update status `unknown` / `not_checked` until the next check). An entry whose file is gone is no longer listed, so its routes answer 404 `MOD_NOT_INSTALLED` where, since Story 19.4, enable and disable answered 409 `MOD_FILE_MISSING`.
- Release note (Task 3's commit subject): `feat(api): pick up mods added or removed by hand when the manager starts`.

### ADR against the code

- **ADR-10 context, "`import_mod` is not guarded. One archive that cannot be read raises":** half right. For bytes that are not a zip, or a zip without `modinfo.json`, `import_mod` does not raise: `_extract_modinfo_from_zip` catches `BadZipFile`, `KeyError`, `JSONDecodeError` and `UnicodeDecodeError` (`:347`) and `import_mod` then returns **fallback metadata** (`:239-251`), so the current sync would add an entry with the file's stem as mod ID and version `unknown`. That contradicts decision 3 (such a file is skipped). It does raise for other inputs, checked at b6ae2f2:

  | Archive | `import_mod` |
  |---|---|
  | not a zip; no `modinfo.json` | returns fallback metadata (entry would be added) |
  | unsupported compression method | raises `NotImplementedError` |
  | encryption flag set | raises `RuntimeError` |
  | no read permission | raises `PermissionError` |
  | `modinfo.json` nested 200000 deep | raises `RecursionError` |

  So the story does not "guard each import": the sync does not call `import_mod` at all. It reads with `_extract_modinfo_from_zip`, validates, and caches with `_cache_modinfo`, inside a guard that catches `Exception`.
- **Decision 4, "checked per entry by its own file name":** implemented as membership in one directory listing, not as a per-entry `is_file()`, for the reason in "Why a listing". Same result for every case the ADR names; safer when the directory cannot be searched.
- **Decision 10** names only a directory that does not exist. The story gives a directory that cannot be listed the same treatment (AC 8).
- **Order of removals and additions** is not in the ADR; the story fixes it (removals first, AC 11) because the other order loses a hand-renamed mod for one start.
- **"One warning"** (decision 3, AC 4): one `mod_state_sync_skipped` line per file; the archive reader's own existing line may precede it (see "Logging").
- **Decision 1, "called once in the API's start-up":** the mod state is not loaded in the lifespan today (`get_mod_service` is lazy), so the start-up call also becomes the place where the mod service is first built. A failure to build it is logged by `sync_mod_state_at_startup` and does not stop start-up; it surfaces at the first mod request as before.
- Everything else in ADR-10 matches the code at b6ae2f2 (line numbers re-read: the sync is `:492-549`, the ADR says `:492-547`).

### Testing Requirements

**CRITICAL:** Tests are written with each task and committed with it, red first. `just test-api <file>` after each task; `just check` before review.

- Every removal path has a test, and so has every way of *not* removing: file gone (AC 2), empty directory, hand rename and hand replacement (AC 11), case-only rename; and kept: non-zip name (AC 3), dangling symlink, missing directory, unlistable directory, mods path that is a file (AC 8).
- Compare directory listing and file bytes before and after wherever the AC says nothing is changed.
- Log assertions use `captured_logs` and count lines per event; "exactly one" means `== 1`.
- No test writes under `dev/`: singletons and stores are on `tmp_path`; `git status --short` after `just test-api` shows nothing under `dev/`.
- No `chmod`-based test (it behaves differently for root); raise from a monkeypatched method instead.
- Tests of application code must not need a new `# pyright: ignore`; use `monkeypatch.setattr` for the module singleton and the public `state_manager`, `busy_mod_ids`, `store` properties.

### Security Requirements

- No new endpoint; nothing a request can trigger. The sync reads only `modinfo.json` from archives in the mods directory, through the existing reader with its member-path check (`_is_safe_zip_path`, `:271-299`) and the cache writer's path check (`_cache_modinfo`, `:366`); it extracts nothing else and never executes mod content.
- A hostile archive in the mods directory can at worst be skipped; the guard covers deep JSON and broken or encrypted zips (tests above). Whoever can write to the mods directory can already give the game server any mod.
- Log lines carry file names, mod IDs and the mods directory path; no key, password or server name.
- No instance data in tests, fixtures, the README sentence or the PR.

### Development Commands

- `just test-api tests/test_mod_state.py tests/test_mod_state_sync_startup.py tests/test_main.py`, `just test-api tests/test_mods_router.py tests/test_mod_updates.py tests/test_mod_service.py`, `just typecheck-api`, `just lint-api`, `just check`.
- Do not run `just format-api` (it reformats unrelated files; Story 17.2 process note).
- Do not edit `sprint-status.yaml` by hand (`just sprint set ...`) or `.beads/` (`bd`).

### Previous Story Intelligence

- **19.4 (directly before):** the working-file suffixes `.vsm-tmp` and `.vsm-bak`, the start-up recovery and its warning for old-style leftovers, `ModFileMissingError` / `MOD_FILE_MISSING`, the casefold name helper. Read its Dev Agent Record first: where the recovery is called decides where this story's call goes, and whether a conftest guard already exists.
- **19.2 / 19.3:** the app factory and the single settings object in `main.py`. The lifespan tests of Task 3 build the app as those stories' tests do; the services still construct their own `Settings()`.
- **18.2 and 17.4:** router and lifespan tests that reach a real singleton write into `dev/`; inject on `tmp_path` and check `git status`. A `feat`/`fix` subject must describe something an admin can see: only Task 3 does.
- **17.2:** anything that changes the dev stack's real state needs a snapshot and an exact restore; here the stack's state is only read, except for the one rebuild (see "E2E" step 4 for what a difference means).
- **17.3:** mod IDs that differ only in case are one mod (`_lock_key`); `modinfo.json` keys are matched without case.
- **17.x and 18.x reviews:** a completion note must be true of the code; manual checks wait for the maintainer.

### Git Intelligence

- Base `b6ae2f2` (`docs(epic-19): fold the maintainer's observation decisions into epic 19`) on `048fea9` (Epic 18 merged, `v0.1.0-rc.4`). Stories 19.1 to 19.4 land first.
- Planned commits: Task 1 `refactor(story-19.5/task-1): make the mod state sync safe to run at start-up`. Task 2 `refactor(story-19.5/task-2): log each change and a summary from the mod state sync`. Task 3 `feat(story-19.5/task-3): pick up mods added or removed by hand when the manager starts` (the release note; includes the README sentence and the conftest guard). Task 4 `test(story-19.5/task-4): start-up sync through the api and update status`. Task 5 `chore(story-19.5/task-5): validate and move story 19.5 to review`.

### Project Structure Notes

- New: `api/tests/test_mod_state_sync_startup.py`.
- Modified: `api/src/vintagestory_api/services/mod_state.py`, `services/mods.py`, `main.py`; `api/tests/conftest.py`, `tests/test_mod_state.py`, `tests/test_mods_router.py` and/or `tests/test_mod_updates.py`, possibly `tests/test_main.py`; `README.md`. No web file, no model, no router, no error code.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 19.5: The Mod State Matches the Mods Directory at Start-Up]
- [Source: _bmad-output/planning-artifacts/prd.md] FR231, FR232
- [Source: _bmad-output/planning-artifacts/architecture/epic-19-api-security-and-mod-file-safety.md#ADR-10] (and ADR-9 for the recovery and suffixes, ADR-8 for the name check, ADR-5 decision 11 for the app factory)
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-17.md] (API change table row 19.5; release-note subject; risk note on removals; observations 1 and 2 of the second revision)
- [Source: _bmad-output/implementation-artifacts/18-2-install-and-version-change-keep-records-right.md], [17-4-installed-status-is-right-everywhere.md]
- Beads: `VSS-uoxl` (closed with this story), parent `VSS-fl9b`; follow-ups `VSS-v3be`, `VSS-hv60`
- `project-context.md` (no suppressions; manual test tasks need the maintainer's confirmation; commit format)

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5), BMAD dev-story, non-interactive.

### Debug Log References

- Line references re-checked at b5e78d2 (Stories 19.1 to 19.4 merged into this branch's base): the sync was `services/mod_state.py:500-557`, `scan_mods_directory` `:473-498`, `_extract_modinfo_from_zip` `:309-361`, `_cache_modinfo` `:363-393`, `save` `:101-136`. `main.py`'s lifespan is the closure in `lifespan_for(settings)` (`:124-200`); it calls Story 19.4's `prepare_mod_files()` (`services/mods.py:126-145`) inside `try`/`except Exception` (`mod_files_startup_failed`) before the auto-start block (`:155-179`). Story 19.4's autouse conftest fixture `prepare_mod_files_recorder` replaces `vintagestory_api.main.prepare_mod_files` in every test.
- Red runs: Task 1, 23 of the new `TestSyncAtStartUp` tests failed against the old sync (with only a `ModSyncSummary` stub added so the module imports). Task 2, the 8 `TestSyncLogging` tests failed against the old sync. Task 3, collection failed without `sync_mod_state_at_startup`; with the function but no call from `prepare_mod_files`, 4 failed (the AC 7 test and the three lifespan order tests). Task 4's API tests are test-only and passed on first run against Task 3.
- `grep -rn sync_state_with_disk api/src`: the definition (`services/mod_state.py:510`), a docstring mention (`:30`) and exactly one caller, `services/mods.py:158` in `sync_mod_state_at_startup`.
- `dev/`: `dev/vsmanager/state` is empty and `dev/serverdata` has no `Mods`, before and after `just check`; `git status --short dev/` is empty.
- Docker dev stack (Task 4.2): before the rebuild no game server process (`ps` in the container found none), server state `installed`, `auto_start_server` false. Snapshot: `GET /api/v1alpha1/mods` (5 mods, `pending_restart` false), `ls -la` and SHA-256 of each file in `data/serverdata/Mods` (5 files), SHA-256 of `data/vsmanager/state/mods.json`. `just docker restart` from this branch. After: the `GET /api/v1alpha1/mods` body is byte-identical, the listing and every file's bytes are the same, `mods.json` has the same checksum. The container log has exactly one `mod_state_synced added=0 removed=0 skipped=0 total=5`, followed by `auto_start_server_disabled`; no `mod_state_sync_*` change, skip or warning line, no `mod_files_startup_failed`. `web/e2e/installed-status.spec.ts`: 4 passed; afterwards `GET /api/v1alpha1/mods`, the directory's bytes and the `mods.json` checksum still equal the snapshot. No game server process after the runs.

### Completion Notes List

- Story created 2026-11-17 (create-story, non-interactive) and validated against the create-story checklist. A throwaway prototype of Tasks 1 to 3 (the rewritten sync returning a summary, `sync_mod_state_at_startup`, the lifespan call) was run against the whole API suite (2858 passed, as without it), pyright (0 errors, 3 warnings) and ruff, and against a hand-built directory with every case of AC 1 to 6, 8 and 11; it showed the write into `dev/` that Task 3.3 prevents. It was then discarded.
- Task 1: `ModSyncSummary(added, removed, skipped)` (frozen dataclass) above `ModStateManager`; `sync_state_with_disk()` returns it and runs as in Dev Notes "The sync": `is_dir()` guard, one `iterdir()` listing plus `scan_mods_directory()` inside `except OSError`, removals of entries whose own name is not in the listing (sorted), then additions over the sorted candidates, one `save()` in `except OSError`. It does not call `import_mod`: `_read_new_archive()` reads with `_extract_modinfo_from_zip` and validates with `ModMetadata.model_validate` inside `except Exception`; mod IDs are compared lower-cased (comment names `ModService._lock_key`), against the remaining entries and the ones added earlier in the run. An `OSError` from `_cache_modinfo` is a warning and the entry is still added. The new log events (Task 2's table) landed in this commit, because the rewrite replaced the old ones.
- Task 2: tests for every event in Dev Notes "Logging"; exactly one `mod_state_synced` per call, also with zeros and in both AC 8 cases; the old `mod_state_added` / `mod_state_removed_deleted_file` are gone. Beyond the table: `mod_state_sync_modinfo_not_cached` (warning, `filename`, `slug`, `error`) for the cache-write failure the story asks to log without naming an event, and an `error_type` key on an `unreadable` skip that caught an exception and on `mod_state_sync_failed`.
- Task 3 (deviation from 3.2's wording, same order): `sync_mod_state_at_startup()` in `services/mods.py` (never raises; `mod_state_sync_failed` at error level) is called by Story 19.4's `prepare_mod_files()` as its step 2, right after the recovery and before the cache's old-layout removal, not by a second call in the lifespan. Story 19.4 left that slot for it (its docstring, Dev Notes "Start-up order"). Effects: the order recovery, sync, auto-start, scheduler holds; a failure of the cache step cannot skip the sync; if the recovery itself raises (unplanned; it logs and continues on `OSError` per file), the sync does not run and `mod_files_startup_failed` is logged, so an entry whose file is still `.vsm-bak` is not removed. In that one case there is no `mod_state_synced` line (AC 9 otherwise holds). Task 3.3: Story 19.4's autouse guard already replaces `main.prepare_mod_files`, which now holds the sync, so no second fixture was added; its docstring says it covers the sync, and `TestStartUpOnly` pins that entering `TestClient(app)` never calls `sync_state_with_disk`. README: one sentence in Installation step 5.
- Task 3 tests: `tests/test_mod_state_sync_startup.py` (the real function on a singleton on `tmp_path`; failing sync and failing `get_mod_service`; AC 7 through the real `prepare_mod_files`; AC 10 no route with `sync`; AC 14 guard) and three tests in `tests/test_main.py` `TestLifespanAutoStart` (order recovery, sync, `start_server`, scheduler with one summary line before `auto_starting_game_server`; a raising sync still auto-starts; auto-start off still syncs once). `run_auto_start_lifespan` got an `auto_start` keyword (default on).
- Task 4: `TestStartUpSyncThroughTheApi` drives the real lifespan with the real `prepare_mod_files` over `Kept.zip`/`Gone.zip` entries and hand-added `New.zip`/`Off.zip.disabled`, under respx with no routes (zero calls asserted): the list, 404 `MOD_NOT_INSTALLED` for the removed mod, `pending_restart` false, and update status (`unknown`/`not_checked` for both added mods, no item for the removed one, store bytes unchanged).
- Results: `just check` green: API 3229 passed (3185 before, +44); web 3349 passed, 4 skipped (`VSS-hnl`); pyright 0 errors, 3 warnings (`VSS-1ar`); lint and script tests green. E2E: `installed-status.spec.ts` 4 passed on the rebuilt stack. No lint or type suppression and no `cast` in the diff. Only new and changed lines were formatted (`test_mod_state_sync_startup.py` is new and fully `ruff format`ted); `mods.py`, `test_main.py` and `test_mod_state.py` have older lines `ruff format` would change, left alone.
- Not done here: Task 5.2 is the maintainer's manual check (unticked). Task 5.3's PR, its "API contract changes" description, the PR link on `VSS-uoxl` and closing `VSS-uoxl` were not done (the dev brief forbids push, PR and bead changes); story status and sprint status are `review`.

### File List

- README.md (modified)
- api/src/vintagestory_api/services/mod_state.py (modified)
- api/src/vintagestory_api/services/mods.py (modified)
- api/tests/conftest.py (modified)
- api/tests/test_main.py (modified)
- api/tests/test_mod_state.py (modified)
- api/tests/test_mod_state_sync_startup.py (new)
- _bmad-output/implementation-artifacts/19-5-mod-state-matches-the-mods-directory.md (modified)

## Change Log

- 2026-11-17: Story 19.5 created and validated (ready-for-dev).
- 2026-11-17: Tasks 1-4 and 5.1 implemented; status review. 5.2 (manual check) waits for the maintainer; 5.3's PR, bead link and `VSS-uoxl` closing are left to the maintainer.
