# Story 28.2: A Mod Can Be Installed by Uploading Its File

Status: review

<!-- Implements FR356 to FR359, Epic 28 ADR-3 and ADR-4. Bead: VSS-cxuu (API-099), closes with this story after merge. Branch story/28-2-a-mod-can-be-installed-by-uploading-its-file, stacked on story/28-1-each-installed-mod-records-where-it-came-from (PR #235); the PR targets main and merges after 28.1's. API only. -->

## Story

As an **administrator**,
I want **to upload a mod's zip file**,
so that **I can install a mod that is not on the mod database or a patched build of one that is**.

## Acceptance Criteria

1. **Given** an Admin key and a zip with a valid `modinfo.json`
   **When** `POST /mods/upload?filename=<name>` sends it as the body
   **Then** the mod is installed with source `upload`, and the response has `slug`, `version`, `filename`, `compatibility` (`not_verified`), `pending_restart`, `source`, `replaced` and `previous_version`
   *(FR356; ADR-3, ADR-4)*

2. **Given** a body over `VS_MOD_UPLOAD_MAX_MB` (by `Content-Length` or while reading)
   **Then** 413 `MOD_FILE_TOO_LARGE`, and nothing is left in the mods folder or the cache
   *(FR357)*

3. **Given** a name that is not a safe `.zip` base name, a body that is not a zip, or a zip without a `modinfo.json` that has a mod ID and a version
   **Then** 422 `MOD_FILE_INVALID` saying which
   *(FR358)*

4. **Given** the mod ID is installed
   **When** `replace` is not set **Then** 409 `MOD_ALREADY_INSTALLED` with the installed version and source
   **When** `replace=true` **Then** the file is swapped keeping the enabled state, the source becomes `upload`, the update record is removed, and a failure restores the original file and state
   *(FR359; ADR-4)*

5. **Given** the mod is busy or the name is taken **Then** 409 `MOD_OPERATION_IN_PROGRESS` or `MOD_FILE_CONFLICT`, as for an install.

6. **Given** a Monitor key **Then** 403. **Given** the server runs **Then** a restart is pending.

7. **Given** a crash during an upload **Then** the leftover working file is deleted at the next start.

8. **(Quality gates.)** `just check` green; README documents the upload and `VS_MOD_UPLOAD_MAX_MB`.

## Tasks / Subtasks

- [x] Task 1: The upload (AC: 1-7)
  - [x] 1.1: `services/mod_upload.py`: `safe_archive_name`, `incoming_file`, `write_limited`, `clear_incoming`, the two errors
  - [x] 1.2: `ModService.install_archive` (new install through `_copy_and_record`, shared with the mod database install; replace through `_apply_version_change` with a `_Replacement`); `ModAlreadyInstalledError.source`
  - [x] 1.3: `POST /mods/upload`; `VS_MOD_UPLOAD_MAX_MB`; `ModUpdateService.forget`; error codes `MOD_FILE_INVALID`, `MOD_FILE_TOO_LARGE`; start-up `clear_incoming`
  - [x] 1.4: Tests (`test_mod_upload.py`)
  - [x] 1.5: Commit `feat(story-28.2/task-1): install a mod by uploading its file`

- [x] Task 2: README (AC: 8)
  - [x] 2.1: Commit `docs(story-28.2/task-2): explain uploading a mod and VS_MOD_UPLOAD_MAX_MB`

- [x] Task 3: Validate and move the story to review (AC: 8)

## Dev Notes

### The code today (verified at the tip of 28.1, cfad2d89)

- `_place_install` (`services/mods.py`) copied, imported and recorded inline; `_apply_version_change` swaps with a backup and rollback and copied the old entry's source.
- No multipart parser is installed; the body is read with `request.stream()`.
- The download cache that eviction scans is `{cache_dir}/mods` (`cache_eviction.py:118`), so `{cache_dir}/incoming` is outside it.

### References

- `epics.md` "Story 28.2"; `architecture/epic-28-mods-from-outside-the-mod-database.md` ADR-3, ADR-4

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5).

### Debug Log References

- `just check` (2026-11-27): exit 0; API 4287 passed, web 3986 passed; Pyright 0/0; lints green.

### Implementation decisions

- **The received file is staged under its final name** (`{cache_dir}/incoming/<random>/<name>`), so the swap of a replace (which takes its file name from the archive path) and a new install use the same file.
- **`install_archive` is synchronous**: the lock is taken and released with no `await` between the check and the state save, as `_place_install` is.
- **A name is refused, never changed** (`safe_archive_name`), so the mod is stored under the name the admin gave.
- **`modinfo.json` must also have a name**: `ModMetadata` requires one, and the game shows it. The error says "a mod ID, a name and a version".
- **A replace with the installed file gone is 409 `MOD_FILE_MISSING`**, as a version change is (Epic 24 ADR-5), checked before the swap.
- **The 409 for an installed mod carries `slug`, `installed_version` and `source`** in the detail, for Story 28.4's replace prompt.
- **A replaced mod's update record is removed** through `ModUpdateService.forget` (Story 28.1 already ignores it for manual mods; this keeps the store clean).
- **Body writes are synchronous file writes** of each received chunk, like the download cache's writes.

### Completion Notes List

- 2026-11-27 (dev-story): Tasks 1 to 3 done. 40 new API tests in `test_mod_upload.py` (names, the limit by length and by stream, the working folder, start-up cleanup, install, every refusal, replace with the enabled state kept, a failed replace restored, a busy mod, the route's answers).
- 2026-11-27 (create-story): created from Epic 28's Story 28.2, ADR-3 and ADR-4.

### File List

- `api/src/vintagestory_api/services/mod_upload.py` (new), `services/mods.py`, `services/mod_updates.py`, `routers/mods.py`, `config.py`, `models/errors.py`; `api/tests/test_mod_upload.py` (new) (Task 1)
- `README.md` (Task 2)
- this file; `sprint-status.yaml` (through `just sprint set`)

## Change Log

- 2026-11-27: Story 28.2 created (create-story).
- 2026-11-27: Story 28.2 implemented (dev-story): Tasks 1 to 3; status review.
