# Story 17.3: Mod Operations Are Safe Against Each Other

Status: ready-for-dev

<!-- Implements FR182-FR183 and Epic 17 ADR-3. Beads: VSS-8wg, VSS-0jl. Branch story/17-3-mod-operations-are-safe-against-each-other, stacked on story/17-2-install-picks-the-right-release (8d7aba2, PR #157 not merged yet). Not in scope: Story 17.4 (installed status on browse cards, update record after install). No new dependencies. No web source change is expected (tests only). -->

## Story

As an **administrator**,
I want **two operations on the same mod never to run at the same time**,
so that **a remove or toggle during an update cannot leave the mod half changed**.

## Acceptance Criteria

1. **Given** an install or a version change is running for a mod (it is waiting for the mod database or the download)
   **When** I install, enable, disable, remove or change the version of the same mod
   **Then** the request is answered at once, without waiting for the running operation, with 409 and the body `{"detail": {"code": "MOD_OPERATION_IN_PROGRESS", "message": "Another operation on mod '<mod ID>' is in progress. Try again when it has finished."}}`; it changes no file and no state; and when the running operation finishes, the mod's file and state are exactly what that operation alone leaves
   *(Covers FR182; `VSS-8wg`)*

2. **Given** two install requests for the same mod arrive together, including two requests whose slugs differ but resolve to the same install mod ID (`automapmarkers` and `egocaribautomapmarkers`, `mod_egocaribautomapmarkers.json`) or differ only in case
   **When** both are processed
   **Then** exactly one installs the mod and the other returns 409 (`MOD_OPERATION_IN_PROGRESS` while the first is still running, `MOD_ALREADY_INSTALLED` if the first has finished); the mods directory holds one file for that mod and the state has one entry
   *(Covers FR182)*

3. **Given** an operation is running for one mod
   **When** I change a different mod, including another mod ID of the same mod database entry (`vsinstrumentsbase` while `instruments` is being installed)
   **Then** it proceeds without waiting and without a 409
   *(Covers FR182)*

4. **Given** Update All reaches a mod that is busy
   **When** its version change is refused
   **Then** that mod is reported as `failed` with the busy message as its `error`, the remaining mods are still processed, and the run's counts include it under `failed`
   *(Covers FR182; ADR-3 decision 5)*

5. **Given** an install whose mod ID is already installed or busy under another name: the requested slug resolves to an installed mod ID (`automapmarkers` while `egocaribautomapmarkers` is installed), or the downloaded archive's `modinfo.json` names a different mod ID that is installed or busy
   **When** the install runs
   **Then** it is refused with 409 (`MOD_ALREADY_INSTALLED` or `MOD_OPERATION_IN_PROGRESS`) before any file is placed in the mods directory, and the installed mod's file, state and cached `modinfo.json` are untouched. In the first case nothing is downloaded
   *(Covers FR182; ADR-3 decision 4; Story 17.2 "Not changed")*

6. **Given** a mod archive whose `modinfo.json` uses `ModID`, `Name`, `Version` or other capitalized top-level keys
   **When** it is installed, or placed by a version change
   **Then** it is imported with its real mod ID and version (not the filename and `unknown`), and its `modinfo.json` is cached and readable through `get_cached_metadata`, the same as an archive with lowercase keys
   *(Covers FR183; `VSS-0jl`)*

7. **Given** a locked operation ends in any way: success, an error before or after the download, a rolled back version change, or cancellation of the request
   **When** the next operation for that mod arrives
   **Then** it is not refused as busy, and the service holds no lock entry for any mod while nothing is running
   *(Covers FR182)*

8. **Given** the web UI
   **When** an install, enable, disable, remove or version change gets 409 `MOD_OPERATION_IN_PROGRESS`
   **Then** an error toast shows the API's message, and an optimistic toggle or removal in the Installed list is rolled back
   *(Covers FR182; behavior exists today, this story adds the tests that pin it)*

9. **Given** every existing mod test
   **When** the suite runs
   **Then** it passes, apart from the changes listed in Dev Notes "Existing tests that change"

## Tasks / Subtasks

<!-- Each functional task includes its tests in the same commit. Commit per task: type(story-17.3/task-N): ... ; feat/fix only for user-visible changes, subject written for users. Red first. -->

- [x] Task 1: One `modinfo.json` key normalization for import and validation + tests (AC: 6, 9)
  - [x] 1.1: `api/src/vintagestory_api/services/mod_state.py`: `_extract_modinfo_from_zip` (`:296-344`) returns the parsed object with its top-level keys lowercased (replace the `return cast(...)` at `:330`; rule in Dev Notes "Key normalization"). Delete the comprehension in `read_modinfo` (`:259`) and validate `data` directly; keep its docstring sentence about case and add the same sentence to `import_mod` (`:194-245`) and to `_extract_modinfo_from_zip`'s Returns. `import_mod` itself needs no other change: it validates and caches what the extractor returns (`:214`, `:217`)
  - [x] 1.2: Tests. `tests/test_mod_state.py` (`TestImportMod`, `:543`): an archive with `{"ModID": "demo", "Name": "Demo", "Version": "1.2.3", "Authors": ["a"], "Side": "Universal"}` imports as `demo` / `1.2.3` / `Both` (not the filename, not `unknown`); `state/mods/demo/1.2.3/modinfo.json` exists with lowercase top-level keys; `get_cached_metadata("demo", "1.2.3")` returns the metadata; a nested object keeps its keys (`{"Dependencies": {"Game": "1.20"}}` is cached as `{"dependencies": {"Game": "1.20"}}`); with both `modid` and `ModID` present the later key wins; `repair_fallback_entries` repairs a state entry stored as filename / `unknown` for such an archive. `tests/test_mod_service.py` (`TestModServiceInstallMod`, `:773`): installing `smithingplus` with a zip whose keys are capitalized gives `InstallResult.slug == "smithingplus"` and a state entry with version `1.8.3`. `tests/test_mod_version_change.py` (`TestChangeVersion`, `:499`): a version change whose new archive has capitalized keys leaves `get_cached_metadata("demo", "1.1.0")` set (pass the modinfo to the download mock as `mock_download` does, `:245-253`)

- [ ] Task 2: One per-mod operation lock for version change, enable, disable and remove + tests (AC: 1, 3, 4, 7, 9)
  - [ ] 2.1: `services/mods.py`: rename `ModVersionChangeInProgressError` (`:179-184`) to `ModOperationInProgressError` with the message in AC 1. Replace `_version_locks` (`:308`) with `self._busy: set[str]` and the helpers in Dev Notes "The lock" (`_lock_key`, `_refuse_if_busy`, `_hold`, and the read-only property `busy_mod_ids`). `import asyncio` (`:9`) is then unused: remove it
  - [ ] 2.2: `change_version` (`:843-900`): replace `:857-860` with `with self._hold(slug):` (a plain `with`; the body is unchanged). `enable_mod` (`:650`), `disable_mod` (`:700`) and `remove_mod` (`:750`): `self._refuse_if_busy(slug)` before the state lookup, so a busy mod answers 409 even when it is not installed yet or the request would be a no-op. They stay plain `def` and do not hold the lock (Dev Notes "Who holds the lock"); say so in each docstring and add `ModOperationInProgressError` to every Raises, replacing the old name in `change_version`'s
  - [ ] 2.3: `models/errors.py:62`: `MOD_OPERATION_IN_PROGRESS` replaces `MOD_VERSION_CHANGE_IN_PROGRESS`. `routers/mods.py`: import (`:45`); `change_mod_version` (`:1014-1015`) returns the new code; `enable_mod` (`:827`), `disable_mod` (`:893`) and `remove_mod` (`:955`) gain `except ModOperationInProgressError` returning 409 with the new code and `str(e)`; add "409 if another operation on this mod is in progress" to the four docstrings' Raises (`:801`, `:867`, `:929`; `change_mod_version` has no Raises section, add the sentence to its description)
  - [ ] 2.4: `services/mod_updates.py` `apply_all`: the lazy import (`:360-366`) and the `except` tuple (`:385-396`) name `ModOperationInProgressError`; nothing else changes (Dev Notes "Update All")
  - [ ] 2.5: Tests: Dev Notes "Concurrency tests" rows V1-V8, "API tests" for the four routes, "Update All" tests; update the tests in "Existing tests that change" that belong to this task

- [ ] Task 3: Install takes the lock for the mod ID it installs and checks the archive's mod ID + tests (AC: 1, 2, 3, 5, 7, 9)
  - [ ] 3.1: `services/mod_api.py`: split `download_mod` (`:375-441`) as in Dev Notes "Install flow": frozen dataclass `ResolvedInstall`, `resolve_install(slug, version=None) -> ResolvedInstall` (everything `download_mod` does before the download at `:434`: the lookup, the selection at `:418` and the debug log, raising the same errors) and `download_resolved(resolved) -> DownloadResult` (`:434-441`). `download_mod` becomes the two calls in sequence, with the same signature, return type, errors and log events, so its 39 uses in `tests/test_mod_api.py` and the others in `tests/` stay as they are
  - [ ] 3.2: `services/mods.py` `install_mod` (`:1084-1219`): implement the seven steps of Dev Notes "Install flow". Move the synchronous part (`:1130-1219`: compatibility, copy, import, state, restart flag, result) unchanged into a private plain `def` (for example `_place_install(slug, download)`) called inside the `with` block, so that no `await` can ever be added between the archive check and the state save without a signature change. Add `ModOperationInProgressError` to the docstring's Raises and say that the lock is on the install mod ID
  - [ ] 3.3: `routers/mods.py` `install_mod` (`:664-768`): `except ModOperationInProgressError` → 409 `MOD_OPERATION_IN_PROGRESS` with `str(e)`; Raises: "409 if another operation on this mod is in progress" (`:687`)
  - [ ] 3.4: Tests: Dev Notes "Concurrency tests" rows I1-I9, "API tests" for install; `tests/test_mod_api.py`: `resolve_install` returns the install mod ID, release, file ID and asset ID for `instruments` (`instruments`, 1.2.2, 12840) and for `automapmarkers` (`egocaribautomapmarkers`) and sends no download request; `download_mod` still downloads the same file. Update the two tests in "Existing tests that change" that belong to this task

- [ ] Task 4: Web tests that pin the busy answer (AC: 8, 9)
  - [ ] 4.1: Add the tests in Dev Notes "Web tests". No source file under `web/src` changes; if one of these tests fails against the current source, stop and record it in the Dev Agent Record before changing any component, because the story assumes the web already shows the message
  - [ ] 4.2: `web/src/hooks/use-version-change-flow.test.tsx:181`, `:188`: the mocked code becomes `MOD_OPERATION_IN_PROGRESS` (the only place the old code appears under `web/`)

- [ ] Task 5: Quality gate and review hand-off (AC: all)
  - [ ] 5.1: `just check` (lint, typecheck, all tests) passes; the diff adds no lint or type suppression and no `cast`; `rg -n "MOD_VERSION_CHANGE_IN_PROGRESS|ModVersionChangeInProgressError|_version_locks" api web` finds nothing
  - [ ] 5.2: Story status `review`, `just sprint set 17-3-mod-operations-are-safe-against-each-other review`, PR (base `story/17-2-install-picks-the-right-release` while PR #157 is open, otherwise `main`), PR link on `VSS-8wg` and `VSS-0jl`. The PR description names the renamed error code as an API change

## Dev Notes

### The bugs (verified on this branch, 8d7aba2)

- `ModService` keeps `_version_locks: dict[str, asyncio.Lock]` (`services/mods.py:308`) and only `change_version` uses it (`:857-860`). `install_mod`, `enable_mod`, `disable_mod` and `remove_mod` never look at it (`VSS-8wg`).
- `change_version` reads the mod's state (`:861`), then awaits the mod database lookup and the download inside `_prepare_version_change` (`:875`; the awaits are `:1009` and `:1040`), then swaps file and state synchronously in `_apply_version_change` (`:876`, `:902-965`). A `remove_mod` that runs during those awaits deletes the file and the state entry; the version change then places the new archive, writes a state entry for the removed mod and fails at `old_path.unlink()` (`:949`), which starts a rollback to a file that no longer exists. An enable or disable in that window is less visible: it mutates the same `ModState` object (`:685-686`, `:735-736`), so the swap follows the new filename, but the admin's toggle and the update still interleave.
- The bead says the window is "between file placement and state save". That window does not exist: `_apply_version_change` has no `await`. The real window is the lookup and the download, before anything is placed.
- `install_mod` checks "already installed" (`:1116-1121`) and then awaits `download_mod` (`:1125`). Two installs of the same mod both pass the check; the second overwrites the first's file and state entry (`temp_path.rename(dest_path)`, `:1149`).
- The already-installed check uses the requested slug (`:1116`), not the mod ID the install resolves to (Story 17.2's install mod ID). Installing `automapmarkers` while `egocaribautomapmarkers` is installed passes the check, downloads, and overwrites that mod's file and state; if anything then fails, the cleanup (`:1184-1195`) deletes the file and the state entry of the mod that was installed before the request.
- The lock table never shrinks: `setdefault(slug, asyncio.Lock())` (`:857`) adds an entry for every slug ever sent to `PUT /mods/{slug}/version`, installed or not, and that route does not validate the slug.
- `ModStateManager.read_modinfo` lowercases top-level keys (`services/mod_state.py:259`); `import_mod` validates the raw dictionary (`:214`). An archive with `ModID`/`Version` passes `_archive_matches` (`services/mods.py:1076-1082`) and is then imported with the filename as its mod ID and version `unknown`, with nothing cached (`VSS-0jl`).

### The lock

```python
self._busy: set[str] = set()   # lock keys of the mods an install or version change is running for

@staticmethod
def _lock_key(mod_id: str) -> str:
    return mod_id.lower()

def _refuse_if_busy(self, mod_id: str) -> None:
    if self._lock_key(mod_id) in self._busy:
        raise ModOperationInProgressError(mod_id)

@contextmanager
def _hold(self, mod_id: str) -> Generator[None]:
    self._refuse_if_busy(mod_id)
    key = self._lock_key(mod_id)
    self._busy.add(key)
    try:
        yield
    finally:
        self._busy.discard(key)

@property
def busy_mod_ids(self) -> frozenset[str]:
    """Lock keys of the mods an install or version change is running for (read-only)."""
    return frozenset(self._busy)
```

- **A set of held keys, not a dictionary of `asyncio.Lock`.** Nothing ever waits for the lock (ADR-3 decision 2), so "check, then take" is all that is needed, and both happen with no `await` between them, which makes them atomic on the event loop. A set is empty whenever nothing is running, so it cannot grow (AC 7). Annotate the generator `Generator[None]` from `collections.abc`: pyright strict reports `Iterator[None]` on a `@contextmanager` as deprecated.
- **Released on every path.** `_hold` is used only as `with self._hold(...):`. The `finally` runs for a return, any exception and `asyncio.CancelledError` (a client that disconnects, shutdown). Never add or discard a key anywhere else.
- **Cancellation leaves nothing half done.** A task can only be cancelled at an `await`. Inside the held section the only awaits are the lookup and the download (`change_version`) or the download (`install_mod`); nothing is in the mods directory or the state at those points. The file swap, rollback and state save are synchronous.
- **Key: the mod ID, lowercased.** `_archive_matches` already compares mod IDs without case (`services/mods.py:1080`), and an archive may spell its mod ID differently from the mod database. Two IDs that differ only in case therefore share a lock. Locking too much costs one 409; locking too little costs a mod.
- **Scope: one process.** `ModService` is a singleton (`services/mods.py:61`, `:75-116`), so one set covers every request. The scheduled job (`jobs/mod_cache_refresh.py:26-35`) runs on the same event loop and only calls `ModUpdateService.check()`, which reads the installed list and writes the update store; it never touches a mod's file or state and needs no lock.

### Who holds the lock (ADR-3 decision 3, checked against the code)

| Operation | Awaits between reading and writing? | Behavior |
|---|---|---|
| `change_version` | Yes (`:875`) | Holds the key of `slug` for the whole call |
| `install_mod` | Yes (`:1125`) | Holds the key of the install mod ID from resolution to return (see "Install flow") |
| `enable_mod`, `disable_mod`, `remove_mod` | No. Plain `def` (`:650`, `:700`, `:750`), so they cannot contain an `await`; called directly from the `async` handlers (`routers/mods.py:817`, `:883`, `:945`), not through a thread pool (the only `run_in_executor` calls are in `routers/console.py` and `services/logs.py`) | Refuse when the key is held; otherwise run without taking it. Nothing else can run until they return |

If one of the three ever becomes `async` or moves to a thread, it must use `_hold`. Put that sentence in their docstrings.

`sync_state_with_disk` and `repair_fallback_entries` also write state. Neither is reachable while an operation is suspended: the first has no caller under `api/src` (tests only), the second runs once in `get_mod_service` (`:106`). They are not changed.

### Install flow (ADR-3 decision 4)

`services/mod_api.py`:

```python
@dataclass(frozen=True)
class ResolvedInstall:
    slug: str          # the requested slug after extract_slug, for logs and errors
    mod_id: str        # the install mod ID (select_install_release, Epic 17 ADR-2)
    release: ReleaseDict
    file_id: int
    asset_id: int
```

`resolve_install` is `download_mod`'s current steps 1 and 2 (including both `ModNotFoundError` cases and the debug log); `download_resolved` is step 3. `download_mod` keeps its `DownloadResult | None` return annotation; changing it is not part of this story.

`ModService.install_mod`, in order:

1. `slug = extract_slug(slug_or_url)`; `self._refuse_if_busy(slug)`. Before the lookup, so installing a mod whose version change is running answers `MOD_OPERATION_IN_PROGRESS` at once, not `MOD_ALREADY_INSTALLED`.
2. The existing already-installed check for `slug` (`:1116-1121`) stays, as a fast path that needs no network.
3. `resolved = await api_client.resolve_install(slug, version)`. No lock is held during this lookup: nothing has been read from the state that is used later, and nothing is written.
4. With no `await` after step 3: `self._refuse_if_busy(resolved.mod_id)`, then the already-installed check for `resolved.mod_id` (`ModAlreadyInstalledError(resolved.mod_id, existing.version)`). This repeats steps 1 and 2 when the IDs are equal; it is needed because the state may have changed during the lookup.
5. `with self._hold(resolved.mod_id):` for everything that follows.
6. `download = await api_client.download_resolved(resolved)`. Then read the archive in the cache: `archive = self._state_manager.read_modinfo(download.path)`. If it is readable and `archive.modid != resolved.mod_id`: when the two lock keys differ, `self._refuse_if_busy(archive.modid)` (when they are equal the key is our own, and refusing would make every install of a mod whose archive says `CarryOn` fail); in both cases, if `get_mod_by_slug(archive.modid)` is installed, raise `ModAlreadyInstalledError(archive.modid, existing.version)`. An unreadable archive (`None`) is not checked and installs with fallback metadata as today (`tests/test_mod_service.py:1141`).
7. The synchronous placement (`_place_install`), unchanged.

Steps 6 and 7 have no `await` between the archive check and the state save, so the archive's mod ID is checked, not held. The check runs before the file is copied into the mods directory: the download's filename can equal the installed mod's filename, and removing "the file" after placing it would remove that mod.

What the admin gets:

| Request | State | Answer |
|---|---|---|
| install `X` | `X` version change or install running | 409 `MOD_OPERATION_IN_PROGRESS` (step 1, no lookup) |
| install `X` | `X` installed, idle | 409 `MOD_ALREADY_INSTALLED` (step 2, no lookup) |
| install `automapmarkers` | `egocaribautomapmarkers` installed | 409 `MOD_ALREADY_INSTALLED` naming `egocaribautomapmarkers` (step 4, no download) |
| install `automapmarkers` | `egocaribautomapmarkers` busy | 409 `MOD_OPERATION_IN_PROGRESS` (step 4, no download) |
| install `demo`, archive says `Demo` | `Demo` installed (state keeps the archive's spelling) | 409 `MOD_ALREADY_INSTALLED` (step 6, after the download, nothing placed) |
| install `instruments` | `vsinstrumentsbase` installed or busy | proceeds: different mod IDs of one entry are different mods |

`ModAlreadyInstalledError` carries the mod ID that is installed, which can differ from the requested slug; the router message (`routers/mods.py:716-723`) already uses `e.slug`.

### Update All (ADR-3 decision 5)

`apply_all` calls `change_version` once per mod (`services/mod_updates.py:382`) and records the listed errors as a `failed` item with `error=str(e)` (`:385-398`). A busy mod raises `ModOperationInProgressError`, which takes the old error's place in that tuple: the mod is `failed`, its error is the busy message, and the loop continues. It is `failed`, not `skipped`: `skipped` means the offer was not applied for a compatibility reason and carries `reasons` the web renders as such; `failed` carries a free-text error (`web/src/components/UpdateAllDialog.tsx:49-50`). The run is not aborted, and the busy mod is not retried; the admin runs Update All again or updates that mod alone.

There is no scheduled apply. The only scheduled mod job is the update check ("The lock", last bullet).

### Key normalization (`VSS-0jl`)

- One place: `_extract_modinfo_from_zip` returns `{key.lower(): value for key, value in parsed.items()}` (keys of a JSON object are always strings). Both callers, `import_mod` and `read_modinfo`, then see the same dictionary. Only top-level keys are lowercased; values, including nested objects, are untouched. When two keys differ only in case, the later one in the file wins.
- The cached `state/mods/<modid>/<version>/modinfo.json` is therefore written with lowercase top-level keys. That is required, not a side effect: `get_cached_metadata` (`:378-407`) validates the cached file as it is, and the installed list and the single-mod read take names and sides from it (`ModService.list_mods` and `get_mod`, `services/mods.py:347`, `:390`). Caching the archive's original spelling would produce a cache that cannot be read.
- Mods that an older build imported with fallback metadata for this reason are repaired at the next start by the existing `repair_fallback_entries` (`:409-453`), which calls `import_mod`. No migration code is needed; one test pins it.
- The mod ID's own spelling is not changed: an archive that says `"ModID": "Demo"` is stored as `Demo`.

### Concurrency tests

New file `api/tests/test_mod_operation_lock.py`. Reuse the helpers of `tests/test_mod_version_change.py` by importing them (`make_service` `:208`, `install_existing` `:218`, `mock_lookup` `:241`, `mock_download` `:245`, `mock_demo` `:483`, `demo_mod` `:469`, `mod_zip_bytes` `:122`, `MOD_URL`, `DOWNLOAD_URL`); `tests/` is on the import path (other test modules import `conftest` by name).

Every test holds the first operation inside its critical section with a gate, then acts while it is suspended:

```python
def gate_download(service: ModService, monkeypatch: pytest.MonkeyPatch) -> tuple[asyncio.Event, asyncio.Event]:
    started, release = asyncio.Event(), asyncio.Event()
    original = service.api_client.download_release_file

    async def held(slug: str, fileid: int, filename: str) -> Path:
        started.set()
        await release.wait()
        return await original(slug, fileid, filename)

    monkeypatch.setattr(service.api_client, "download_release_file", held)
    return started, release
```

`first = asyncio.create_task(...)`, `await started.wait()`, act, `release.set()`, `await first`. Both `change_version` (`_acquire_release_archive`, `:1057`) and install (`download_resolved`) reach `download_release_file` after the lock is taken. No `asyncio.sleep` with a duration and no timing assumptions; where two tasks are started together, `await started.wait()` proves the first is inside. Each test ends by asserting the files in the mods directory, the state entry and that the lock table is empty.

| # | Held operation | Second operation, same mod | Expect |
|---|---|---|---|
| V1 | `change_version("demo", "1.1.0")` | `remove_mod("demo")` | raises `ModOperationInProgressError`; after release the change succeeds: only `Demo-1.1.0.zip`, state `1.1.0` |
| V2 | same | `disable_mod("demo")` | raises; file is not renamed; after release the mod is enabled at `1.1.0` |
| V3 | same, mod installed disabled | `enable_mod("demo")` | raises; after release the file is `Demo-1.1.0.zip.disabled` |
| V4 | same | `change_version("demo", "1.1.0")` | raises (replaces the existing test, see below) |
| V5 | same | `install_mod("demo")` and `install_mod("DEMO")` | both raise `ModOperationInProgressError` (not `ModAlreadyInstalledError`), and the lookup route is called once (by the version change only) |
| V6 | `change_version("demo", ...)` | `disable_mod("other")`, `remove_mod("other")`, `change_version("other", ...)` for a second installed mod | all succeed while `demo` is held (for the version change, gate only `demo`'s download: let `held` pass other slugs through) |
| V7 | `change_version` that fails after the download (archive with the wrong version → `ModValidationError`; and one that fails in the swap: make `service.state_manager.save` raise `OSError`, as `tests/test_mod_version_change.py:636` does → `ModVersionChangeFailedError`, rolled back) | then `disable_mod("demo")` | the toggle succeeds; lock table empty; for the rollback, the original file and state are back first |
| V8 | `change_version` gated, then `first.cancel()` | `await first` raises `asyncio.CancelledError`; then `remove_mod("demo")` | succeeds; lock table empty; before the remove, the mod is as it was (old file, old state, no `.tmp`/`.bak`) |
| I1 | `install_mod("demo")` | `install_mod("demo")` started as a second task before the gate opens | exactly one result is an `InstallResult`, the other `ModOperationInProgressError`; one file, one state entry |
| I2 | `install_mod("demo")` | `remove_mod("demo")`, `enable_mod("demo")`, `disable_mod("demo")`, `change_version("demo", "1.0.0")` | each raises `ModOperationInProgressError` (not `ModNotFoundError`); after release the install succeeds |
| I3 | `install_mod("automapmarkers")` (fixture `egocaribautomapmarkers`; zip modinfo `egocaribautomapmarkers` 5.0.3) | `install_mod("egocaribautomapmarkers")` | the second raises `ModOperationInProgressError` and requests no download; one mod installed |
| I4 | `install_mod("instruments")` (fixture `instruments`) | `install_mod("vsinstrumentsbase")`, its download not gated | the second installs while the first is held; after release both are installed, two files, two state entries |
| I5 | none | `egocaribautomapmarkers` installed, then `install_mod("automapmarkers")` | `ModAlreadyInstalledError` with slug `egocaribautomapmarkers`; the download route is not called; file bytes and state unchanged |
| I6 | none | `other` installed; `install_mod("demo")` whose archive's modinfo says `other` | `ModAlreadyInstalledError("other")`; nothing new in the mods directory; `other`'s file bytes, state and cached modinfo unchanged. Use a download filename equal to `other`'s installed filename, to prove the installed file is not overwritten or deleted |
| I7 | `change_version("other", ...)` gated on `other`'s download only | `install_mod("demo")` whose archive says `other` | `ModOperationInProgressError("other")`; nothing placed; after release the version change succeeds |
| I8 | none | `install_mod("demo")` whose archive says `"ModID": "Demo"` | installs (the differing spelling must not be refused as busy); state slug `Demo`; then `install_mod("demo")` again raises `ModAlreadyInstalledError("Demo")` and the mods directory still has one file |
| I9 | `install_mod("demo")` gated, then cancelled; and an install whose download raises `DownloadError`; and one whose `import_mod` raises | then `install_mod("demo")` | succeeds each time; lock table empty; after the cancelled and failed runs the mods directory is empty |

"Lock table empty" is asserted as `service.busy_mod_ids == frozenset()`, and always together with behavior (the next operation is accepted). Tests do not read `service._busy`: pyright strict reports private access from tests as an error (`reportPrivateUsage`; the one existing case, `tests/test_mod_service.py:126`, carries a suppression), and this story adds no suppression. `pyproject.toml` sets a 10 s test timeout, so a gate that is never released fails the test instead of hanging the run.

### API tests

- **Mapping, all five routes.** `tests/test_mods_router.py`: in `TestInstallModEndpoint` (`:66`), `TestEnableModEndpoint` (`:743`), `TestDisableModEndpoint` (`:901`) and `TestRemoveModEndpoint` (`:1064`), patch the service method to raise `ModOperationInProgressError("smithingplus")` and assert status 409 and the whole body: `response.json() == {"detail": {"code": "MOD_OPERATION_IN_PROGRESS", "message": "Another operation on mod 'smithingplus' is in progress. Try again when it has finished."}}`. `tests/test_mod_version_change_router.py:243-250`: the parametrized case uses the new error and code.
- **A real race through the API.** New `api/tests/test_mod_operation_lock_router.py`, async tests with `httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")` (the `TestClient` is synchronous and cannot hold one request open while sending another). Override `get_mod_service` and `get_settings` as `tests/test_mod_version_change_router.py:80-90` does and clear the overrides in a `finally`. Gate the service as above; replace `service.api_client.get_mod` with an async function returning the fixture's normalized entry (`normalize_mod`, as `tests/test_mod_release_selection.py` loads fixtures) and `download_release_file` with the gate writing a zip into `tmp_path`, so no HTTP mock is needed. Cases: `PUT /mods/carryon/version` held, then `POST /mods/carryon/disable`, `POST /mods/carryon/enable`, `DELETE /mods/carryon`, `PUT /mods/carryon/version` and `POST /mods {"slug": "carryon"}` each return 409 with the exact body; after release the first request returns 200 and `GET /mods` lists the new version, enabled. Second test, with a service that has nothing installed: start two `POST /mods {"slug": "carryon"}` as tasks, `await started.wait()`, release, `asyncio.gather` both: the status codes are `{200, 409}`, the 409 body is the busy body, and `GET /mods` lists `carryon` once. This approach was tried against the current code (a second `PUT` during a gated one returned the 409 body).

### Update All tests

`tests/test_mod_update_all.py`: add `ModOperationInProgressError("alpha")` to the parametrized list at `:148-156` (import it at `:22-26`). One test with the real lock: a `ModService` (`make_service` of `tests/test_mod_version_change.py`) with two installed mods, `alpha` and `delta` at `1.0.0` (`install_existing`); a `ModUpdateService(store=ModUpdateStore(tmp_path / "state"), mod_source=mod_service, game_version_provider=lambda: "1.22.7")` whose store offers both `1.1.0` (`record`, `:50-56`; the store only decides which mods are attempted, `change_version` does its own lookup); respx lookups and downloads for both mods, built like `demo_mod` (`tests/test_mod_version_change.py:469-480`) with each mod's own `modidstr`, file ID and filename. Hold `alpha` with `change_version("alpha", "1.1.0")` started as a task and gated on `alpha`'s download only, then `await update_service.apply_all(mod_service.change_version)`: `alpha` is `failed` with the busy message as `error`, `delta` is `updated`, `(updated, skipped, failed) == (1, 0, 1)`; after release the held change completes and `alpha` is at `1.1.0`.

### Web (AC 8): no source change, verified

- The web never branches on the old code. `rg "IN_PROGRESS" web/src` finds only doc comments about the update check and Update All (`api/mods.ts:227`, `:258`) and the test fixture string at `hooks/use-version-change-flow.test.tsx:181`, `:188`. The only code the mod flows compare is `MOD_CONFIRMATION_REQUIRED` (`hooks/use-version-change-flow.ts:39`, `hooks/use-mods.ts:402`).
- `ApiError.message` is the API's `detail.message` (`api/client.ts:109-115`). Version change: `toast.error('Failed to update <name>', { description: message })` (`hooks/use-version-change-flow.ts:93-94`). Install: `toast.error('Installation failed', { description: error.message })` (`components/InstallConfirmDialog.tsx:118-119`). Enable, disable, remove: the hooks roll back the optimistic change (`hooks/use-mods.ts:149-153`, `:197-200`, `:241-244`) and the query client's default `onError` shows `toast.error('Error', { description: error.message })` (`api/query-client.ts:36-38`, `api/error-handler.ts:29-32`).
- So an admin already reads "Another operation on mod 'x' is in progress. Try again when it has finished." for all five. No E2E task: there is no user-visible change in the web, and a race cannot be produced reliably through a browser. No manual check is required. If the dev runs anything against the Docker dev stack anyway, the installed mods and `data/serverdata/Mods` must end as they started (snapshot before, compare after, as Story 17.2's E2E spec does).

### Web tests

Mock responses as `use-mods.test.tsx:1519-1528` does (`ok: false`, `status: 409`, `json` → `{ detail: { code: 'MOD_OPERATION_IN_PROGRESS', message: BUSY } }`), with `BUSY` the AC 1 message.

- `web/src/components/ModTable.test.tsx`: a new block with `vi.mock('sonner', ...)` as `hooks/use-version-change-flow.test.tsx:6-8` and a query client built like the app's (`defaultOptions.mutations.onError = handleApiError`, `retry: false`; `createTestQueryClient` at `:52` has no global handler). (a) Clicking the switch of an enabled mod (as the toggle tests at `:296-387` do) when `POST .../disable` returns the 409: `toast.error` is called with `'Error', { description: BUSY }` and the switch is checked again. (b) The same for enabling a disabled mod. (c) Confirming a removal when `DELETE` returns the 409: the toast shows `BUSY`, the dialog closes and the row is still listed.
- `web/src/components/InstallConfirmDialog.test.tsx`: when the install mutation fails with `new ApiError('MOD_OPERATION_IN_PROGRESS', BUSY, 409)`, `toast.error` is called with `'Installation failed', { description: BUSY }` and `onOpenChange` is not called with `false` (follow the existing error test at `:418-453` for how the mutation is mocked).
- `web/src/hooks/use-version-change-flow.test.tsx:180-191`: the existing "shows the API message when a change fails" test, with the new code (Task 4.2). Its `conflict` helper builds the message from the code, so the expected description becomes `'MOD_OPERATION_IN_PROGRESS message'`.

### Existing tests that change (deliberately)

Found by running the API suite against a throwaway prototype of Tasks 1-3 (since discarded): 2471 passed, and only these failed.

- `tests/test_mod_version_change.py:31` (import) and `:674-694` `test_overlapping_change_for_same_mod_is_rejected`: the new error name. Move the test to `test_mod_operation_lock.py` as V4 or keep it here; do not keep both. (Task 2)
- `tests/test_mod_version_change_router.py:26` (import), `:246`, `:248`: the new error and code. (Task 2)
- `tests/test_mod_service.py:1177-1194` `test_install_mod_download_returns_none`: it mocks `download_mod` to return `None`; `install_mod` no longer calls `download_mod`, and `resolve_install` raises instead of returning `None`. Delete it together with the `if download_result is None` branch (`services/mods.py:1127-1128`); "mod not in the database" stays covered by `test_install_mod_not_found` (`:957`). (Task 3)
- `tests/test_edge_cases.py:258-284` `test_failed_install_reports_original_error_if_file_is_gone`: its `MagicMock` client provides `download_mod`. Give it `resolve_install` (an `AsyncMock` returning a `ResolvedInstall` for `demo`) and `download_resolved` (returning the same `DownloadResult`); the assertions stay. `cached.zip` there is not a zip, so the archive check reads `None` and is skipped, as intended. (Task 3)
- `web/src/hooks/use-version-change-flow.test.tsx:181`, `:188`. (Task 4)
- `tests/test_mod_version_change.py:152-160` `test_keys_are_case_insensitive` keeps passing unchanged (the normalization moved, the behavior did not).
- Anything else that fails is a regression (AC 9): fix the code, not the test.

### ADR-3 against the code

- ADR-3's line references are to `ebca566`; Stories 17.1 and 17.2 moved them. This story cites 8d7aba2.
- **Decision 1** says "one lock table" replacing `_version_locks`, which reads as a dictionary of `asyncio.Lock`. This story uses a set of held keys. With decision 2 (never wait) a lock object is never awaited, and the dictionary is the leak described in "The bugs".
- **Decision 1** says "keyed by mod ID". This story lowercases the key. The ADR does not mention case.
- **Decision 3** is confirmed: `enable_mod`, `disable_mod` and `remove_mod` are plain synchronous methods called on the event loop. The ADR's context says a remove can run "during the download"; it can also run during the mod database lookup, which the same lock covers.
- **Decision 4** says "Install locks the install mod ID from ADR-2". The install mod ID is only known after the mod database lookup, which `download_mod` did in one call with the download; hence the split into `resolve_install` and `download_resolved`. The requested slug is checked (not held) before the lookup so that a busy mod is refused at once.
- **Decision 4** says the install "fails with the file removed" when the archive names a mod ID that is taken. Removing the placed file is wrong when its filename is the installed mod's filename: the rename at `services/mods.py:1149` has by then replaced that mod's file, and removing it deletes the mod. This story checks the archive in the download cache, before anything is placed, so there is nothing to remove.
- **Decision 4** covers the archive's mod ID but not the simpler case where the install mod ID itself differs from the requested slug and is already installed (the check at `:1116` uses the requested slug). Story 17.2 left that to this story; it is step 4 of "Install flow" and AC 5.
- **Decision 5** ("Update All is unchanged apart from the error type") is confirmed.
- The ADR's "Related" paragraph offers "`_extract_modinfo_from_zip` or a helper beside it". This story normalizes inside `_extract_modinfo_from_zip`, and adds what the ADR does not say: the cached `modinfo.json` must be written normalized, because `get_cached_metadata` validates it as stored.
- The bead `VSS-8wg` describes a window "between file placement and state save" that does not exist (see "The bugs"). The fix is the same.

### Not changed (do not "fix" these here)

- **A filename collision between two different mods on install** (an archive with unreadable metadata, or two mod IDs that ship the same filename): `temp_path.rename(dest_path)` (`:1149`) still replaces an existing file, as today. `_apply_version_change` refuses that case (`:914-917`); install does not. Not part of ADR-3; record a bead if the dev sees it happen.
- An archive whose mod ID differs from the install mod ID and is neither installed nor busy installs under the archive's mod ID, as today.
- `get_mod_by_slug` stays an exact match. An installed `Demo` is found by the archive check (I8), after the download, not by the fast path.
- `PUT /mods/{slug}/version` does not validate its slug (`routers/mods.py:985-989`). With a set of held keys this no longer grows anything.
- `download_mod`'s `| None` return type, `InstallResult.version` coming from the release while the state takes the archive's version, the install toast appearing twice in the web (per-call `onError` plus the global handler): existing behavior, not ADR-3.
- Everything in Story 17.4: browse cards recognizing any installed mod ID, the update record after an install or removal.
- Planning documents and old story files that mention `MOD_VERSION_CHANGE_IN_PROGRESS` (Epic 14 ADRs, Stories 14.2-14.4) are history and stay as written.

### API contract (`v1alpha1`)

- `MOD_VERSION_CHANGE_IN_PROGRESS` is removed; `PUT /mods/{slug}/version` now answers 409 `MOD_OPERATION_IN_PROGRESS` with a new message. No client in this repo depends on the old code.
- `POST /mods`, `POST /mods/{slug}/enable`, `POST /mods/{slug}/disable` and `DELETE /mods/{slug}` can now answer 409 `MOD_OPERATION_IN_PROGRESS`. A busy mod answers 409 on enable, disable and remove even when it is not installed (an install in flight) or the request would be a no-op.
- `POST /mods` can answer 409 `MOD_ALREADY_INSTALLED` naming a mod ID other than the requested slug.
- The API is documented by the router docstrings (OpenAPI); there is no separate reference that lists error codes.

### Testing Requirements

**CRITICAL:** Tests are written with each task and committed with it, red first. `just test-api <file>` / `just test-web <file>` after each task; `just check` before review.

- API tests use respx on `https://mods.vintagestory.at/api/mod/{slug}` and `https://mods.vintagestory.at/download` (match `params={"fileid": ...}` as `tests/test_mod_version_change.py:250` does; assert `route.called` is false where nothing may be downloaded). Async tests carry `@pytest.mark.asyncio` (and `@respx.mock` above it), as `tests/test_mod_version_change.py:674-675`; `asyncio_mode` is `auto`, the marker is kept for consistency with the existing tests.
- Synthetic mod data is built in the tests (`demo_mod`); `fixtures/moddb/` holds only captured data and is not changed.
- After Task 2 and before Task 3 the branch locks four operations and not install. Every commit is green; AC 1 and 2 are complete only after Task 3.
- E2E is not part of `just check` and this story adds none.

### Security Requirements

- No new endpoint; all five routes stay Admin-only. The lock key comes from request input (`PUT /mods/{slug}/version` takes any string): it is only ever compared and stored in a set while an operation runs, never used in a path. The cached `modinfo.json` path still goes through `_cache_modinfo`'s traversal check (`services/mod_state.py:356-363`), now with the normalized `modid` and `version` values.
- The 409 message contains the mod ID from the request. It is JSON-encoded by FastAPI and rendered as text by the toast.

### Development Commands

- `just test-api tests/test_mod_state.py tests/test_mod_version_change.py`, `just test-api tests/test_mod_operation_lock.py tests/test_mod_operation_lock_router.py`, `just test-api tests/test_mod_service.py tests/test_mods_router.py tests/test_mod_api.py tests/test_edge_cases.py tests/test_mod_update_all.py tests/test_mod_version_change_router.py`, `just test-web src/components/ModTable.test.tsx src/components/InstallConfirmDialog.test.tsx src/hooks/use-version-change-flow.test.tsx`, `just check`.
- Do not run `just format-api`: it reformats 72 unrelated files (Story 17.2 process note). Only `ruff check` is part of `just check`.

### Previous Story Intelligence

- **17.2:** `select_install_release` (`services/mod_release_selection.py`) gives the install mod ID; `download_mod` logs it but `DownloadResult` does not carry it, which is why this story adds `ResolvedInstall`. Its "Not changed" list handed this story the already-installed check by requested slug, the archive's mod ID and locking. Its review found an E2E cleanup that could delete a pre-existing install: any check against the dev stack snapshots first. `just format-api` must not be used.
- **17.1:** `get_mod` returns a normalized entry; read `r["modidstr"]`, `mod["assetid"]` directly. pyright is strict: baseline 0 errors and 3 pre-existing warnings in tests (`tests/test_mod_service.py:1589`, `:1668`, `tests/test_mods_router.py:2424`). Keep each commit green and move a test change to the commit that causes it.
- **14.2 (review L2, L7):** the two beads of this story. The existing overlap test (`tests/test_mod_version_change.py:675`) shows the event-gate pattern; it gates the lookup, this story gates the download so that install is inside its lock too.
- **16.2 / 16.3:** mod IDs are compared exactly everywhere else; the lowercase lock key is the one deliberate exception, next to `_archive_matches`.

### Git Intelligence

- Recent commits are Story 17.2's (`ada2b6f`, `26ef27f`, `c046ea6`, `4cbc501`, `8d7aba2`). Release notes are generated from commit subjects (`cliff.toml`). Planned types: Task 1 `fix` (a mod whose modinfo.json uses capitalized keys is imported with its real ID and version), Task 2 `fix` (enabling, disabling or removing a mod while it is being updated is refused instead of corrupting it), Task 3 `fix` (installing a mod twice at once, or under another of its names, no longer overwrites it), Task 4 `test`, Task 5 `docs`.

### Latest Technical Information

- No new libraries. `contextlib.contextmanager` with a synchronous `with` inside an `async def` is fine: the context manager's `finally` runs when the coroutine is cancelled at an `await` inside the block. `httpx.ASGITransport` ships with the installed httpx and needs no lifespan for these routes (the service and settings are dependency overrides). `asyncio.Lock` is not used by `ModService` any more; `ModUpdateService` keeps its own `_check_lock` and `_apply_lock` (`services/mod_updates.py:333-334`), which are unrelated.

### Project Structure Notes

- New: `api/tests/test_mod_operation_lock.py`, `api/tests/test_mod_operation_lock_router.py`.
- Modified: `api/src/vintagestory_api/services/mods.py`, `services/mod_api.py`, `services/mod_state.py`, `services/mod_updates.py`, `routers/mods.py`, `models/errors.py`; `api/tests/test_mod_state.py`, `test_mod_service.py`, `test_mod_version_change.py`, `test_mod_version_change_router.py`, `test_mods_router.py`, `test_mod_api.py`, `test_edge_cases.py`, `test_mod_update_all.py`; `web/src/components/ModTable.test.tsx`, `web/src/components/InstallConfirmDialog.test.tsx`, `web/src/hooks/use-version-change-flow.test.tsx`. No file under `web/src` other than tests; no fixture.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 17.3: Mod Operations Are Safe Against Each Other]
- [Source: _bmad-output/planning-artifacts/prd.md] FR182, FR183
- [Source: _bmad-output/planning-artifacts/architecture/epic-17-mod-data-fixes.md#ADR-3: One Operation Lock per Mod]; ADR-2 (install mod ID)
- [Source: _bmad-output/planning-artifacts/architecture/epic-14-mod-updates.md] ADR-2 (version changes are serialized per mod)
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-15.md]
- [Source: _bmad-output/implementation-artifacts/17-2-install-picks-the-right-release.md] ("Not changed", Completion Notes, Senior Developer Review)
- [Source: _bmad-output/implementation-artifacts/17-1-mod-detail-pages-cannot-fail-on-bad-data.md] (Senior Developer Review)
- Beads: `VSS-8wg`, `VSS-0jl`, parent `VSS-4v5`
- `project-context.md` - critical implementation rules and patterns (no suppressions; manual test tasks need the user's confirmation)

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5)

### Debug Log References

- Baseline before Task 1 (8d7aba2 + story commit 83a99ec): `just test-api` 2473 passed; `just typecheck-api` 0 errors, 3 warnings (the pre-existing three in tests).

### Completion Notes List

- Task 1: `_extract_modinfo_from_zip` returns the object with lowercased top-level keys; `read_modinfo` validates it directly; `import_mod` and the extractor's Returns document the rule. Deviation from 1.1 (no `cast`): the story says to replace the `return cast(...)`, but a plain comprehension over the `isinstance(parsed, dict)`-narrowed value is `dict[Unknown, Unknown]` and adds three pyright `reportUnknown*` warnings. The JSON is now validated with a module-level `TypeAdapter(dict[str, object])` (pydantic, already a dependency): a non-object raises `ValidationError` and logs the same `modinfo_not_object` event as before, so the typed result needs neither `cast` nor `isinstance`. Red first: 6 new tests failed (`modinfo_parse_failed` on every capitalized archive). 6 new tests: capitalized import + lowercase cache + `get_cached_metadata`, nested keys kept and the mod ID's spelling kept (`Demo`), later key wins, `repair_fallback_entries` repairs such an archive, install of `smithingplus` with capitalized keys, version change caching `demo` 1.1.0. `test_keys_are_case_insensitive` passes unchanged. `just test-api` 2479 passed; pyright 0 errors, the same 3 warnings.

- Story created 2026-11-15: context analysis of `ModService` (`_version_locks`, `change_version`, `install_mod`, `enable_mod`, `disable_mod`, `remove_mod`), `ModApiClient.download_mod`, `ModStateManager` (`import_mod`, `read_modinfo`, the modinfo cache), `ModUpdateService.apply_all`, the scheduled check job, the mods router, the web's error handling for the five operations, Stories 17.1 and 17.2 with their reviews, and Epic 17 ADR-3. The API tests that change were found by running the suite against a throwaway prototype of Tasks 1-3; the gate pattern, the cancellation release and the ASGI race test were each tried once before being written into the story.

### File List

- `api/src/vintagestory_api/services/mod_state.py`
- `api/tests/test_mod_state.py`
- `api/tests/test_mod_service.py`
- `api/tests/test_mod_version_change.py`

## Change Log

- 2026-11-15: Story 17.3 created (ready-for-dev).
- 2026-11-15: Validated against the create-story checklist: every cited path and line re-read on 8d7aba2; fixed six wrong line references, made the lock-table assertion a public read-only property (tests may not read private members under pyright strict), made the Update All and API race tests buildable from the existing helpers, and named the existing failure injection for the rollback test.
