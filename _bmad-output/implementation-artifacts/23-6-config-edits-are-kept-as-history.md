# Story 23.6: Config Edits Are Kept as History

Status: done

<!-- Implements FR321, FR322, FR323, FR326 (history part), Epic 23 ADR-7, ADR-9. Bead: VSS-hb4d (API-098), first half (Story 23.7 closes it). Branch story/23-6-config-edits-are-kept-as-history, stacked on story/23-5-config-files-are-edited-in-the-file-browser at f55b09c6 (23.5 in review); the PR targets main and merges after 23.5's. API and README only. Line references verified at f55b09c6. -->

## Story

As an **administrator**,
I want **each config save to keep the text it replaced**,
so that **I can see what changed and undo a bad edit**.

## Acceptance Criteria

1. **Given** a file saved through `PUT /config/files/{path}`
   **When** the save succeeds
   **Then** `vsmanager/state/config-history/<path relative to serverdata>/` holds the replaced bytes as `<id>.json` (exactly as they were, BOM included) and `index.json` lists the revision first with `id`, `saved_at` (ISO 8601, UTC), `saved_by` (`"admin"`), `size` and `sha256`
   *(FR321; ADR-7 decisions 1 to 3)*

2. **Given** the history store cannot be written (its directory is not writable)
   **When** a file is saved
   **Then** the answer is 500 `CONFIG_HISTORY_WRITE_FAILED` without an absolute path, and the file is unchanged; and **given** the file replace fails after the revision was written, the revision is removed again (the index lists only revisions whose text exists)
   *(FR321; ADR-7 decision 4)*

3. **Given** `config_history_keep_count` 3, and separately `config_history_max_age_days` 1 with revisions older than a day
   **When** the file is saved again
   **Then** only the newest 3 revisions remain, and none older than a day except the newest; the API settings refuse values outside 1 to 200 and 0 to 3650 like other settings (400 `API_SETTING_INVALID`); defaults are 20 and 0
   *(FR322; ADR-7 decision 5)*

4. **Given** an Admin key
   **When** it calls `GET /api/v1alpha1/config/history/{path}`, `GET /api/v1alpha1/config/history/{path}?revision=<id>`, and `POST /api/v1alpha1/config/history/{path}/restore` with `{revision, version}`
   **Then** the list is newest first (an empty list for a file with no history, existing or not); the read returns `{filename, revision, text}` (the text decoded as UTF-8, a BOM dropped); the restore follows every save rule (stopped server, version, parser rule, size, pending-edit drop) through the same path as `PUT`, keeps the current text as a new revision first, and answers like `PUT`
   *(FR323; ADR-7 decision 6)*

5. **Given** a Monitor key, a malformed revision id (`../x`, `20261119T000000000000Z/../a`, empty), or an unknown well-formed id
   **When** it calls the history routes
   **Then** the answers are 403, 400 `CONFIG_REVISION_INVALID`, and 404 `CONFIG_REVISION_NOT_FOUND`; no path is built from an id that is not listed in the index; a path with `..` is 400 `CONFIG_PATH_INVALID`; every answer has `Cache-Control: no-store`
   *(FR323; ADR-7 decisions 2 and 6)*

6. **Given** the README's Config files section
   **When** an operator reads it
   **Then** it says where history is kept, that only saves through the file browser (or the API) are recorded, not changes by the game, mods, Game Settings or by hand, and how the two settings limit it
   *(FR326)*

7. **(Quality gates.)** `just check` green, 0 skipped; Pyright 0/0; no suppression; tests use `tmp_path` only; `git diff` of `web/` empty.

## Tasks / Subtasks

<!-- Red first. Subjects: type(story-23.6/task-N): ... One user-visible commit: Task 4 (feat(api)). -->

- [x] Task 1: The history store + tests (AC: 1, 2, 3, 5, 7)
  - [x] 1.1: Red first: `api/tests/test_config_history.py` (record and list; ids sortable and unique on a collision; read; remove; prune by count, by age with the newest kept, both; a malformed or unknown id; an index that is missing, unreadable or lists a missing file (skipped, logged); every write atomic; nothing outside the store's root)
  - [x] 1.2: `services/config_history.py` (Dev Notes "The store")
  - [x] 1.3: Commit `refactor(story-23.6/task-1): add a history store for config file saves`

- [x] Task 2: The two API settings + tests (AC: 3, 7)
  - [x] 2.1: Red first: rows in the API settings tests for defaults, bounds and saving (as `backup_keep_count`'s)
  - [x] 2.2: `services/api_settings.py`: `config_history_keep_count: int = Field(default=20, ge=1, le=200, ...)`, `config_history_max_age_days: int = Field(default=0, ge=0, le=3650, ...)` with descriptions; `MAX_CONFIG_HISTORY_KEEP_COUNT = 200`, `MAX_CONFIG_HISTORY_AGE_DAYS = 3650`
  - [x] 2.3: Commit `refactor(story-23.6/task-2): add the config history limits to the API settings`

- [x] Task 3: The save keeps the replaced text + tests (AC: 1, 2, 3, 7)
  - [x] 3.1: Red first: `test_config_files_save.py` rows (a save records the previous bytes; history failure refuses the save and leaves the file; a replace failure removes the revision; pruning after a save uses the settings; a prune failure does not fail the save)
  - [x] 3.2: `ConfigFilesService.__init__(settings, history: ConfigHistory | None = None)` (default `ConfigHistory(settings.state_dir / "config-history")`); `save_file(..., saved_by: str = UserRole.ADMIN)`: after the version check, `history.record(relative, current, saved_by)` (raises `ConfigHistoryWriteError`), then the write; on `ConfigFileWriteError`, `history.remove(relative, revision.id)`; after the write, `history.prune(relative, keep, max_age)` with `ApiSettingsService(self.settings).get_settings()` (an exception there is logged as `config_history_prune_failed`, not raised); `restore_revision(filename, revision_id, version, saved_by)` reads the revision (decoded `utf-8-sig`; undecodable -> `ConfigFileInvalidError`) and calls `save_file`
  - [x] 3.3: Commit `refactor(story-23.6/task-3): keep the text a config save replaces`

- [x] Task 4: The routes + tests (AC: 4, 5, 7)
  - [x] 4.1: Red first: `api/tests/test_routers_config_history.py` over HTTP with a real `ServerService` on `tmp_path` (as `test_routers_config_save.py`)
  - [x] 4.2: `models/errors.py`: `CONFIG_HISTORY_WRITE_FAILED`, `CONFIG_REVISION_INVALID`, `CONFIG_REVISION_NOT_FOUND`; `routers/config.py`: the PUT maps `ConfigHistoryWriteError` to 500; `GET /history/{filename:path}` (list, or `?revision=`), `POST /history/{filename:path}/restore`; module docstring
  - [x] 4.3: Commit `feat(story-23.6/task-4): keep earlier versions of config files saved through the API, and restore them`

- [x] Task 5: README (AC: 6)
  - [x] 5.1: README Config files: the history paragraph (Dev Notes "Documentation")
  - [x] 5.2: Commit `docs(story-23.6/task-5): explain config file history`

- [x] Task 6: Validate and move the story to review (AC: all)
  - [x] 6.1: `just check` green; `git diff f55b09c6 -- web` empty
  - [x] 6.2: `just changelog` lists exactly one entry from this story (Task 4)
  - [x] 6.3: Status `review`; `just sprint set 23-6-config-edits-are-kept-as-history review`; Dev Agent Record and File List
  - [x] 6.4: Commit `chore(story-23.6/task-6): validate and move story 23.6 to review`

## Dev Notes

### The code today (verified at f55b09c6)

- `services/config_files.py` (Story 23.4): `save_file(filename, text, version) -> SavedConfigFile` (path rules, encode, parse, read current, version check, BOM, `_write_atomically`, log `config_file_saved`); `_target_for_write`; `ConfigFileWriteError`; `content_version`.
- `routers/config.py` (Story 23.4): `PUT /files/{filename:path}` inside `server_service.config_write()`, the pending-edit drop for the root `serverconfig.json`, the error mapping, `NO_STORE`, `logger`; `get_config_files_service` builds `ConfigFilesService(settings=server_service.settings)`.
- `services/api_settings.py`: `ApiSettings` fields with `Field(ge=..., le=...)`; `MAX_BACKUP_KEEP_COUNT = 1000` (`:37`); `ApiSettingsService(settings).get_settings()` (as `jobs/disk_cleanup.py:37`).
- `config.py`: `Settings.state_dir` = `data/vsmanager/state` (`:263`).
- `middleware/permissions.py`: `RequireAdmin` returns the role.

### The store (Task 1): `services/config_history.py`

```python
REVISION_ID = re.compile(r"^\d{8}T\d{12}Z(-\d+)?$")

class ConfigHistoryWriteError(Exception)   # message without a path
class RevisionInvalidError(Exception)       # malformed id
class RevisionNotFoundError(Exception)      # well-formed, not listed (or its file is gone)

class Revision(BaseModel):  # the index's entries; serialized snake_case
    id: str; saved_at: datetime; saved_by: str; size: int; sha256: str

class ConfigHistory:
    def __init__(self, root: Path, *, now: Callable[[], datetime] = utc_now) -> None
    def record(self, relative: str, data: bytes, saved_by: str) -> Revision
    def remove(self, relative: str, revision_id: str) -> None
    def list(self, relative: str) -> list[Revision]           # newest first; [] when none
    def read(self, relative: str, revision_id: str) -> tuple[Revision, bytes]
    def prune(self, relative: str, keep_count: int, max_age_days: int) -> list[str]  # removed ids
```

- `relative` is the file's resolved path relative to the server data directory, as POSIX (from `ConfigFilesService`, never from a request directly). Its directory is `root.joinpath(*PurePosixPath(relative).parts)`; a defensive check refuses (`ConfigHistoryWriteError` / empty list) any part that is `..`, empty or absolute, and checks the resolved directory is inside the resolved root.
- `index.json` in that directory: `{"revisions": [Revision, ...]}` newest first. Read with Pydantic; missing -> empty; unreadable or invalid -> logged `config_history_index_unreadable` and treated as empty for listing, but `record` then starts a new index (the revision files stay on disk).
- ids: `now()` formatted `%Y%m%dT%H%M%S%fZ` (UTC); if taken in the index, `-2`, `-3`, ...
- `record`: mkdir the directory (`parents=True`); write `<id>.json` (exclusive create, fsync), then the index (temp + `os.replace`); any `OSError` -> remove what was written of this revision and raise `ConfigHistoryWriteError(relative)`; log `config_history_recorded` (relative, id, size).
- `read`/`remove`: `REVISION_ID.fullmatch(id)` else `RevisionInvalidError`; the id must be in the index else `RevisionNotFoundError`; only then `directory / f"{id}.json"`.
- `prune`: keep the newest `keep_count`; then, when `max_age_days > 0`, remove entries older than `now - max_age_days` except the newest; write the index, then delete the files (a missing file is fine); log `config_history_pruned` (relative, removed count).
- All writes atomic; no log line or message holds an absolute path or file content.

### The routes (Task 4)

- `GET /history/{filename:path}` (Admin; `revision: str | None = Query(default=None, max_length=64)`): path via `_target_for_write` (the file need not exist); no `revision` -> `{filename, revisions: [...]}`; with `revision` -> `{filename, revision: {...}, text}` (`text` is the bytes decoded `utf-8-sig` with `errors="replace"`, since an old revision may not be valid UTF-8 and must still be viewable).
- `POST /history/{filename:path}/restore` (Admin): body `{revision: str, version: str (64 hex)}`; inside `config_write()`: `service.restore_revision(...)`, then the pending-edit drop when `is_root_serverconfig`; the save's error mapping plus `RevisionInvalidError` -> 400 `CONFIG_REVISION_INVALID`, `RevisionNotFoundError` -> 404 `CONFIG_REVISION_NOT_FOUND`, `ConfigHistoryWriteError` -> 500 `CONFIG_HISTORY_WRITE_FAILED`.
- Revisions in responses are snake_case (`saved_at`, `saved_by`); the web maps them (Story 23.7).
- Route order: the `GET /history/...` and `POST /history/.../restore` routes do not overlap with `/files/...`; FastAPI matches `{filename:path}/restore` for POST only.

### Documentation (Task 5)

README Config files, after the editing paragraph: Each save through the file browser keeps the text it replaced, in `vsmanager/state/config-history/` in the data volume (outside `serverdata`, so the game never loads it). Only saves made here are recorded, not changes by the game, mods, the Game Settings page or by hand. Each file keeps its newest 20 versions by default; set `config_history_keep_count` (1 to 200) and `config_history_max_age_days` (0 to 3650, 0 keeps them whatever their age) in API Settings. A lower limit applies when the file is next saved. If a version cannot be kept, the save is refused, so every save can be undone.

### Testing rules

`tmp_path` only; the router tests use the `test_routers_config_save.py` pattern (real `ServerService`, `get_server_service` and `get_config_files_service` overridden); `ApiSettingsService` reads `tmp_path`'s state directory.

### References

- `epics.md` "Story 23.6"; `architecture/epic-23-config-file-editing.md` ADR-7, ADR-9
- Story 23.4 for the save path; Story 22.4 for a bounded API setting (`backup_keep_count`)

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5), as the epic's controller.

### Debug Log References

- `just check` (2026-11-19): API 3991 passed, web 3818 passed, 0 skipped; Pyright 0/0; lints green.

### Completion Notes List

- 2026-11-19 (create-story, dev-story): Tasks 1 to 6 done.
- **What changed.** `services/config_history.py` (new): `ConfigHistory` (`record`, `list`, `read`, `remove`, `prune`), `Revision`, `RevisionIndex`, the three errors; ids checked by form and against the index before any path is built; the relative path refused when a part is empty, `.` or `..`, and checked inside the store's resolved root. `services/api_settings.py`: `config_history_keep_count`, `config_history_max_age_days` and their bounds. `services/config_files.py`: the constructor takes `history` and `history_limits` (defaults: `state_dir/config-history`, the API settings); `save_file` records before writing, removes the revision when the write fails, prunes afterwards (failures logged); `restore_revision`; `relative_path`, `target_for_history`. `models/errors.py`: three codes. `routers/config.py`: `_save_error` maps every refusal of a save or restore (the PUT now uses it too), `GET /history/{filename:path}`, `POST /history/{filename:path}/restore`. README history paragraph.
- **Tests.** 22 store tests (`tests/test_config_history.py`), 8 history rows in `tests/test_config_files_save.py`, 10 settings rows, 14 router tests (`tests/test_routers_config_history.py`). Changed: the two write-failure tests (service and router) now fail only the config file's own `os.replace`/`os.open` (the history's writes go through), and the config route sweep in `tests/test_routers_config.py` names the history route as Admin only.
- **Deviations.** (1) A revision's text is read with `errors="replace"` so an earlier version that is not UTF-8 can still be viewed; restoring it is refused (`ConfigFileInvalidError`). (2) `ConfigHistory.list` shadows the builtin name inside the class; Pyright accepts it and the module uses `from __future__ import annotations`.
- `git diff f55b09c6 -- web` empty. No suppression added. `just changelog`: one entry from this story, 0f0addf (Task 4).

### File List

- `api/src/vintagestory_api/services/config_history.py` (new)
- `api/src/vintagestory_api/services/config_files.py`, `services/api_settings.py`, `models/errors.py`, `routers/config.py` (modified)
- `api/tests/test_config_history.py`, `api/tests/test_routers_config_history.py` (new)
- `api/tests/test_config_files_save.py`, `api/tests/test_routers_config_save.py`, `api/tests/test_api_settings.py`, `api/tests/test_routers_config.py` (modified)
- `README.md` (modified)
- `_bmad-output/implementation-artifacts/23-6-config-edits-are-kept-as-history.md` (this file)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (through `just sprint set` only)

## Review

Reviewer: GLM-5.3-Flash via opencode. First verdict: changes requested (0 HIGH, three MEDIUM, four LOW); all addressed in b23ea09d; re-check verdict: approve.

1. **MEDIUM M1: an empty or overlong revision id got FastAPI's 422, and the Admin 403 had no `Cache-Control: no-store`.** Fixed: no length rule on the id (the service's form check answers 400 `CONFIG_REVISION_INVALID`); `require_admin`'s 403 is `no-store` for every Admin-only route.
2. **MEDIUM M2: history files did not follow the save's write recipe** (default mode, no directory fsync), so a revision of a 0600 `serverconfig.json` could be world-readable. Fixed: files 0600 (exclusive create, fsync), leaf directories 0700, directory fsync after each create, replace and prune.
3. **MEDIUM M3: entries whose file is gone were listed** (Task 1.1 said skipped and logged). Fixed: skipped, `config_history_entries_missing`.
4. **LOW L1: a failing cleanup inside `record` escaped as a raw `OSError`.** Fixed.
5. **LOW L2: an orphan `<id>.json` from an interrupted record could block later saves.** Fixed: such a file makes the id taken.
6. **LOW L3: the PUT docstring missed `CONFIG_HISTORY_WRITE_FAILED`.** Fixed.
7. **LOW L4: a restore drops a BOM when the file has none now.** Documented in the README (the save's rule).

Re-check observations, no change: only the leaf history directory is 0700 (its parents keep the default; the files are 0600); and a fresh clone needs `api/.env` with `VS_API_KEY_ADMIN` for the lifespan tests (outside this epic: filed as a bead).

## Change Log

- 2026-11-19: Story 23.6 created (ready-for-dev).
- 2026-11-19: Implemented (dev-story): Tasks 1 to 6; status review.
- 2026-11-19: Code review (GLM-5.3-Flash via opencode): changes requested (three MEDIUM, four LOW); fixed in b23ea09d; re-check approve (see "Review"). Status done.
