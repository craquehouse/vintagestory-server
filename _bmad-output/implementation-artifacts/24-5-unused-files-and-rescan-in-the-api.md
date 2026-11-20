# Story 24.5: Unused Files and Rescan in the API

Status: review

<!-- Implements FR336, FR337, FR338, FR340, Epic 24 ADR-3, ADR-4. Beads: VSS-hv60 (UI-103, API half; closes in 24.6), VSS-v3be (API-093, rescan; closes in 24.6), VSS-3tb1 (API-095, item 2; closes with this story after merge). Branch story/24-5-unused-files-and-rescan-in-the-api, stacked on story/24-4-hand-added-mods-get-their-mod-database-link at 6289058c (24.4 in review); the PR targets main and merges after 24.4's. API only. -->

## Story

As an **administrator**,
I want **to list and delete files in the mods folder that the manager does not use, and to rescan the folder**,
so that **I can clean up leftovers and pick up a mod I copied in without restarting the API**.

## Acceptance Criteria

1. **Given** the mods folder holds `old.zip.bak`, `x.TMP`, an archive with no readable `modinfo.json`, a second archive of an installed mod ID, a `.cs` file, a folder, `.vsm-*` files, a symlink, a new archive the sync would add, and installed mods
   **When** an Admin key calls `GET /mods/unused-files`
   **Then** the first four are listed with size, modified time and reason (`leftover`, `unreadable`, `duplicate_mod_id` with `installed_as`), and none of the others; a Monitor key gets 403
   *(FR337, FR340; ADR-3)*

2. **Given** a listed file
   **When** an Admin key calls `DELETE /mods/unused-files/{name}`
   **Then** it is deleted; deleting a skipped archive while the game server runs sets "Restart required", a leftover does not
   *(FR338; ADR-3 decision 5, ADR-4 decision 5)*

3. **Given** a name not in the listing computed for the request (a mod's own file, a `.cs` file, a folder, a `.vsm-*` file, `..`, a traversal, a name that is gone, another letter case)
   **When** it is deleted
   **Then** the answer is 404 `UNUSED_FILE_NOT_FOUND` (or no route matches) and nothing is deleted
   *(FR338, FR340; ADR-3 decision 5)*

4. **Given** an archive copied into the mods folder while the API runs
   **When** an Admin key calls `POST /mods/rescan`
   **Then** it is added, the answer has `added`, `removed`, `skipped` and `pending_restart`, and while the game server runs a change sets "Restart required"
   *(FR336; ADR-4 decisions 1 and 5)*

5. **Given** an install or version change holds a mod's lock, or an update check or update all runs
   **When** a rescan or a delete is requested
   **Then** it is refused with 409 `MODS_BUSY`, and nothing is changed
   *(FR336, FR338; ADR-4 decisions 2 and 3)*

6. **Given** a version change to a new file name interrupted after the rename (`VSS-3tb1` item 2)
   **When** the listing is read
   **Then** the old archive is listed as `duplicate_mod_id` and can be deleted
   *(FR337; ADR-5 decision 4)*

7. **(Quality gates.)** `just check` green; no suppression added; `git diff` of `web/` empty.

## Tasks / Subtasks

- [x] Task 1: Unused files (AC: 1, 2, 3, 5, 6)
  - [x] 1.1: `mod_state.py`: `UnusedFile`, `LEFTOVER_SUFFIXES`, `_classify_new_archive` (the sync's skip rules, now used by the sync and the listing), `_mod_id_index`, `is_archive_name`, `list_unused_files`; `_read_new_archive(log=...)`
  - [x] 1.2: `mods.py`: `ModsBusyError`, `UnusedFileNotFoundError`, `UnusedFileDeleteFailedError`, `list_unused_files`, `delete_unused_file`, `_refuse_while_mods_busy`; `ModUpdateService.is_running`; models `UnusedFileInfo`, `UnusedFileDeleteResult`; error codes `MODS_BUSY`, `UNUSED_FILE_NOT_FOUND`, `UNUSED_FILE_DELETE_FAILED`
  - [x] 1.3: Routes `GET /mods/unused-files`, `DELETE /mods/unused-files/{name}`; `tests/test_mod_unused_files.py`
  - [x] 1.4: Commit `feat(story-24.5/task-1): list and delete files in the mods folder that the manager does not use`

- [x] Task 2: Rescan (AC: 4, 5)
  - [x] 2.1: `ModService.rescan`, `RescanResult`, `POST /mods/rescan`; the sync's and `sync_mod_state_at_startup`'s docstrings name the rescan
  - [x] 2.2: Tests: `TestRescan`, the rescan rows of `TestBusyRule` and `TestRoutes`; `test_mod_state_sync_startup.py` `test_only_the_rescan_route_runs_the_sync`
  - [x] 2.3: Commit `feat(story-24.5/task-2): rescan the mods folder for mods copied in by hand`

- [x] Task 3: Validate and move the story to review (AC: all)
  - [x] 3.1: `just check` green; `just changelog` lists Tasks 1 and 2
  - [x] 3.2: Status `review`; sprint status; ADR-4 decision 3 as implemented; Dev Agent Record and File List
  - [x] 3.3: Commit `chore(story-24.5/task-3): validate and move story 24.5 to review`

## Dev Notes

### The code today (verified at 804af73f)

- `sync_state_with_disk` (`services/mod_state.py:512`) skipped unreadable archives and archives whose mod ID is installed (`duplicate_mod_id`), with log lines only; it was called only from `sync_mod_state_at_startup`.
- `recover_working_files` logs other `.tmp`/`.bak` names as `mod_directory_unknown_leftovers` and never deletes them.

### Decisions made in implementation

- **No flag for the reverse busy rule (ADR-4 decision 3).** The routes are `async` handlers with no `await` and the service calls are synchronous, so from the busy check to the end nothing else runs on the event loop. ADR-4 decision 3 is updated.
- **Symlinks are never listed.** Deleting a link is harmless, but a link is something an admin made on purpose.
- **An archive the sync would add is not listed.** It is a mod waiting for a rescan, not an unused file.
- **Names are matched exactly.** The delete compares the name with the listing computed for the request; an encoded slash is decoded by the router and matches no route.
- **Tests written with the code, not before it.** The listing's rules came out of the refactor of the sync's skip rules, whose existing 282 tests were the red/green guard for that step.
- **Pre-existing gap fixed.** Story 19.5's `test_no_route_runs_the_sync` read `app.routes`, which (with the included routers) has no paths, so it could never fail. It now reads the OpenAPI paths and asserts the rescan is the only such route.

### References

- `epics.md` "Story 24.5"; `architecture/epic-24-mod-management-follow-ups.md` ADR-3, ADR-4, ADR-5 decision 4; Epic 19 ADR-9, ADR-10

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5), as the epic's controller.

### Debug Log References

- `just check` (2026-11-20): API 4087 passed, web 3863 passed, 0 skipped; Pyright 0/0; lints green. `git diff 6289058c -- web` empty.
- `just changelog`: two entries from this story (Tasks 1 and 2).

### Completion Notes List

- 2026-11-20 (create-story and dev-story): created from Epic 24's Story 24.5, ADR-3 and ADR-4; Tasks 1 to 3 done.

### File List

- `api/src/vintagestory_api/services/mod_state.py`, `services/mods.py`, `services/mod_updates.py`, `routers/mods.py`, `models/mods.py`, `models/errors.py` (modified)
- `api/tests/test_mod_unused_files.py` (new); `api/tests/test_mod_state_sync_startup.py` (modified)
- `_bmad-output/planning-artifacts/architecture/epic-24-mod-management-follow-ups.md` (ADR-4 decision 3 as implemented)
- `_bmad-output/implementation-artifacts/24-5-unused-files-and-rescan-in-the-api.md` (this file)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (through `just sprint set` only)

## Change Log

- 2026-11-20: Story 24.5 created and implemented (dev-story): Tasks 1 to 3; status review.
