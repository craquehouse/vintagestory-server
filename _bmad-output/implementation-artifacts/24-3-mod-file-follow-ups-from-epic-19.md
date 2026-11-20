# Story 24.3: Mod File Follow-ups from Epic 19

Status: review

<!-- Implements FR331, FR332, FR333, Epic 24 ADR-5. Bead: VSS-3tb1 (API-095) items 1, 3 and 4; item 2 is Story 24.5, which closes the bead after merge. Branch story/24-3-mod-file-follow-ups-from-epic-19, stacked on story/24-2-web-ui-icon-and-missing-files-are-404 at b6a88124 (24.2 in review); the PR targets main and merges after 24.2's. API only. -->

## Story

As an **administrator**,
I want **the mod file edge cases Epic 19 left open to behave like the rest**,
so that **a missing file gives a clear error, the cache stays within its limit and the state directory holds no stale data**.

## Acceptance Criteria

1. **Given** an installed mod whose own file is not in the mods directory (deleted, or a dangling symlink)
   **When** its version is changed (`PUT /mods/{slug}/version`, or Update all)
   **Then** the change is refused with 409 `MOD_FILE_MISSING` before any lookup or download, nothing changes, and Update all records it as failed and goes on; a change to the installed version still returns "unchanged"
   *(FR331; ADR-5 decision 1)*

2. **Given** a cache holding release files of several types (`.zip`, `.cs`, `.dll`, `.txt`, no extension)
   **When** eviction runs by size, or the stats are read
   **Then** every type is counted and evicted, an emptied file-ID directory is removed, and a download in progress (`<uuid>.tmp`) is neither counted nor evicted
   *(FR332; ADR-5 decision 2)*

3. **Given** the last entry of a mod ID is removed, by the start-up sync or by Remove
   **When** the removal completes
   **Then** `state/mods/<slug>/` is removed; a mod renamed by hand (removed and added under the same mod ID in one sync) keeps it; a failure to remove it is logged and never fails the removal
   *(FR333; ADR-5 decision 3)*

4. **(Quality gates.)** `just check` green; no suppression added; `git diff` of `web/` empty.

## Tasks / Subtasks

- [x] Task 1: Version change with a missing file (AC: 1)
  - [x] 1.1: Red: `test_mod_file_names.py` (refused before any request, for deleted and dangling-symlink; same-version still succeeds), `test_mod_version_change_router.py` (409 body), `test_mod_update_all.py` (`ModFileMissingError` is a per-mod failure)
  - [x] 1.2: `ModService.change_version`: the `is_file()` check after the same-version return and before `_prepare_version_change`; router maps to 409 `MOD_FILE_MISSING`; `apply_all` catches it
  - [x] 1.3: Commit `fix(story-24.3/task-1): answer a version change of a mod whose file is missing with 409, not 500`

- [x] Task 2: Every cached file type (AC: 2)
  - [x] 2.1: Red: `test_cache_eviction.py`: five types counted, a `.dll` evicted by size, `.tmp` not counted, a subdirectory not a file
  - [x] 2.2: `CacheEvictionService._get_cache_files`: every regular file at `mods/*/*` except `.tmp` (`CACHE_FILE_PATTERNS` removed)
  - [x] 2.3: Commit `fix(story-24.3/task-2): evict cached mod files of every type, not only .zip and .cs`

- [x] Task 3: The modinfo cache follows the entries (AC: 3)
  - [x] 3.1: Red: `test_mod_state.py` `TestModinfoCacheFollowsTheEntries`; `test_mod_service.py` `TestRemoveModCache`
  - [x] 3.2: `ModStateManager.remove_cached_modinfo(slug)` (unsafe slugs ignored, failures logged as `mod_modinfo_cache_not_removed`); the sync calls it after its additions for each removed mod ID with no entry left; `ModService.remove_mod` uses it instead of its own `rmtree`
  - [x] 3.3: Commit `refactor(story-24.3/task-3): remove a removed mod's cached modinfo, and never fail a removal over it`

- [x] Task 4: Validate and move the story to review (AC: all)
  - [x] 4.1: `just check` green; `just changelog` lists Tasks 1 and 2
  - [x] 4.2: Status `review`; sprint status; Dev Agent Record and File List
  - [x] 4.3: Commit `chore(story-24.3/task-4): validate and move story 24.3 to review`

## Dev Notes

### The code today (verified at 804af73f)

- `enable_mod` and `disable_mod` raise `ModFileMissingError` when `mods_dir / state.filename` is not a regular file (`services/mods.py:854`, `:922`); `change_version` had no such check and failed later with a 500.
- `ModUpdateService.apply_all` caught a fixed tuple of errors per mod; a `ModFileMissingError` from `change_version` would have ended the whole run, so Task 1 adds it to the tuple.
- `CacheEvictionService.CACHE_FILE_PATTERNS = ("*.zip", "*.cs")`; `ModApiClient` writes a download as `<uuid>.tmp` in the file-ID directory and renames it into place (`services/mod_api.py:691`); `_remove_stale_temp_files` removes old ones.
- `ModService.remove_mod` already removed `state/mods/<slug>/`, but with a bare `shutil.rmtree` after the state was saved, so a failure answered 500 for a completed removal. The sync left the directory behind.

### Decisions made in implementation

- **`.tmp` is not a cache file.** ADR-5 decision 2 said "every regular file"; a running download is a `.tmp` file in the same directory, so it is excluded and left to the stale-temp rule. The test that used `notes.txt` to keep a directory non-empty now uses a `.tmp`, since a `.txt` is now a counted release file.
- **The sync removes the cache after its additions,** and only for a mod ID with no entry left (compared ignoring case), so a mod renamed by hand keeps its cache.
- **Item 4 of the bead for Remove** was already done; only the failure handling changed.

### References

- `epics.md` "Story 24.3"; `architecture/epic-24-mod-management-follow-ups.md` ADR-5; Epic 19 ADR-9, ADR-10, ADR-11

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5), as the epic's controller.

### Debug Log References

- `just check` (2026-11-20): API 4040 passed, web 3862 passed, 0 skipped; Pyright 0/0; lints green. `git diff b6a88124 -- web` empty.
- `just changelog`: two entries from this story (Tasks 1 and 2); Task 3 is a `refactor`.

### Completion Notes List

- 2026-11-20 (create-story and dev-story): created from Epic 24's Story 24.3 and ADR-5; Tasks 1 to 4 done.

### File List

- `api/src/vintagestory_api/services/mods.py`, `services/mod_updates.py`, `services/cache_eviction.py`, `services/mod_state.py`, `routers/mods.py` (modified)
- `api/tests/test_mod_file_names.py`, `test_mod_version_change_router.py`, `test_mod_update_all.py`, `test_cache_eviction.py`, `test_mod_state.py`, `test_mod_service.py` (modified)
- `_bmad-output/implementation-artifacts/24-3-mod-file-follow-ups-from-epic-19.md` (this file)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (through `just sprint set` only)

## Change Log

- 2026-11-20: Story 24.3 created and implemented (dev-story): Tasks 1 to 4; status review.
