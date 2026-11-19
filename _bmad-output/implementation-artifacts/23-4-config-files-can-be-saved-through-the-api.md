# Story 23.4: Config Files Can Be Saved Through the API

Status: ready-for-dev

<!-- Implements FR314-FR318, Epic 23 ADR-1 decision 5, ADR-4, ADR-9. Bead: VSS-glz (UI-025), first half (Story 23.5 closes it). Branch story/23-4-config-files-can-be-saved-through-the-api, stacked on story/23-3-game-settings-are-read-only-for-monitor-keys at 02c96240 (23.3 in review); the PR targets main and merges after 23.3's. API only: no web change, no new dependency. Line references verified at 02c96240. -->

## Story

As an **administrator**,
I want **an API that saves a config file's text while the game server is stopped**,
so that **the web editor can change configs safely, keeping comments and formatting**.

## Acceptance Criteria

1. **Given** the game server is stopped, and an Admin key with the `version` from a read
   **When** it sends `PUT /api/v1alpha1/config/files/ModConfig/x.json` with `{text, version}` where the text has comments and odd spacing
   **Then** the file holds exactly that text (with a UTF-8 BOM if the old file had one), its mode is kept, the answer is 200 `{filename, version}` with the new version (SHA-256 of the bytes written), no temporary file is left, and the log has `config_file_saved` without the text
   *(FR314; ADR-4 decisions 1, 2, 6 and 9)*

2. **Given** a Monitor key, a path with `..`, a non-`.json` name, a missing file, a directory, or a text over 2 MiB (UTF-8)
   **When** it is saved
   **Then** the answers are 403, 400 `CONFIG_PATH_INVALID`, 400 `CONFIG_FILE_NOT_SUPPORTED`, 404 `CONFIG_FILE_NOT_FOUND`, 400 `CONFIG_FILE_NOT_SUPPORTED` and 413 `CONFIG_FILE_TOO_LARGE`, and nothing is written
   *(FR314; ADR-4 decision 2)*

3. **Given** a text that does not parse as JSON5, a text with Infinity, or a root `serverconfig.json` text with a comment or a trailing comma
   **When** it is saved
   **Then** the answer is 422 `CONFIG_FILE_INVALID` whose detail has `message` and `parse_error` (`{message, line, column}`), and nothing is written. A `ModConfig/serverconfig.json` is not the root file and is checked as JSON5
   *(FR314; ADR-1 decision 5, ADR-4 decision 3)*

4. **Given** the game server is running, starting or stopping, or a start, stop, restart, install or uninstall holds its lock
   **When** a file is saved
   **Then** the answer is 409 `CONFIG_FILE_SERVER_RUNNING` or 409 `CONFIG_FILE_SERVER_BUSY`, and nothing is written
   *(FR315; ADR-4 decision 4)*

5. **Given** a save in progress (its write blocked in a test)
   **When** a start is requested
   **Then** the start waits until the save has finished
   *(FR315; ADR-4 decision 4, ADR-9 decision 2)*

6. **Given** the file changed after the read
   **When** it is saved with the old `version`
   **Then** the answer is 409 `CONFIG_FILE_CHANGED` and nothing is written
   *(FR316; ADR-4 decision 5)*

7. **Given** the temporary file cannot be written, or the replace fails
   **When** a file is saved
   **Then** the answer is 500 `CONFIG_FILE_WRITE_FAILED` whose message names no absolute path, the original file is unchanged and no temporary file is left
   *(FR314; ADR-4 decision 6)*

8. **Given** pending Story 22.7 edits for `Port` and for `Ip`
   **When** the root `serverconfig.json` is saved with a changed `Port` and an unchanged `Ip`
   **Then** the `Port` edit is dropped (`pending_config_edits_dropped reason=file_edited`) and the `Ip` edit stays; a save of any other file drops nothing
   *(FR318; ADR-4 decision 7)*

9. **Given** an Admin key
   **When** it sends `POST /api/v1alpha1/config/files/validate` with `{filename, text}`, for `ModConfig/x.json` and for `serverconfig.json`, valid and invalid
   **Then** it gets 200 `{valid, parse_error}` under the same parser rule as a save, whether or not the file exists and whatever the server state; nothing is written; a Monitor key gets 403; a bad path gets the save's 400
   *(FR317; ADR-4 decision 10)*

10. **(Quality gates.)** `just check` green, 0 skipped; Pyright 0/0; no suppression, `cast`, skip or `.only` added; tests use `tmp_path` only (ADR-9); `git diff` of `web/` empty.

## Tasks / Subtasks

<!-- Red first. Subjects: type(story-23.4/task-N): ... One user-visible commit: Task 4 (feat(api)). -->

- [x] Task 1: `ServerService.config_write()` + tests (AC: 4, 5, 10)
  - [x] 1.1: Red first: `api/tests/server/test_config_write.py`: free and stopped -> enters; `_process` alive with state RUNNING, and state STARTING / STOPPING -> `GameServerNotStoppedError(reason="running")`; `_lifecycle_lock` held, `_install_lock` held -> `reason="busy"`; inside the context the lifecycle lock is held; a `start_server()` task created inside the context does not take the lock until the context exits (assert with an `asyncio.Event` and the lock state, with a stubbed `_start_server_locked`)
  - [x] 1.2: `services/server.py`: `class GameServerNotStoppedError(Exception)` with `reason: Literal["running", "busy"]`; `@asynccontextmanager async def config_write(self) -> AsyncIterator[None]` (Dev Notes "The lock")
  - [x] 1.3: Commit `refactor(story-23.4/task-1): add a lock for writing config files while the game server is stopped`

- [x] Task 2: `ConfigFilesService.save_file` and `check_text` + tests (AC: 1, 2, 3, 6, 7, 9, 10)
  - [x] 2.1: Red first: `api/tests/test_config_files_save.py` with a row per AC case (Dev Notes "API tests")
  - [x] 2.2: `services/config_files.py`: exceptions `ConfigFileInvalidError(info: ParseErrorInfo)`, `ConfigFileChangedError`, `ConfigFileWriteError`; `is_root_serverconfig(resolved: Path) -> bool`; `check_text(filename, text) -> ParseErrorInfo | None`; `save_file(filename, text, version) -> SavedConfigFile` (Dev Notes "The save"); `_write_atomically(path, data)`
  - [x] 2.3: Commit `refactor(story-23.4/task-2): save a config file's text atomically, with checks`

- [x] Task 3: Dropping Story 22.7's pending edits a `serverconfig.json` save changes + tests (AC: 8, 10)
  - [x] 3.1: Red first: `changed_keys(old, new)` unit rows; the drop through `ServerService.drop_pending_edits_changed_by_save(old_bytes, new_value)` with a real `PendingConfigEdits` in `tmp_path`
  - [x] 3.2: `services/pending_config_edits.py`: `DropReason` gains `"file_edited"`; `services/config_files.py` (or the new helper's module): `changed_top_level_keys`; `services/server.py`: the method (Dev Notes "Pending edits")
  - [x] 3.3: Commit `refactor(story-23.4/task-3): drop the pending config edits a serverconfig.json save changes`

- [ ] Task 4: The routes + tests (AC: 1-9, 10)
  - [ ] 4.1: Red first: `api/tests/test_routers_config_save.py` over HTTP with a real `ServerService` on `tmp_path` (Dev Notes "Router tests")
  - [ ] 4.2: `models/errors.py`: `CONFIG_FILE_INVALID`, `CONFIG_FILE_SERVER_RUNNING`, `CONFIG_FILE_SERVER_BUSY`, `CONFIG_FILE_CHANGED`, `CONFIG_FILE_WRITE_FAILED`; `routers/config.py`: `POST /files/validate` (declared before the `PUT`), `PUT /files/{filename:path}` with docstrings, `NO_STORE` on every answer, the module docstring's route list
  - [ ] 4.3: Commit `feat(story-23.4/task-4): save config files through the API while the game server is stopped`

- [ ] Task 5: Validate and move the story to review (AC: all)
  - [ ] 5.1: `just check` green; `git diff 02c96240 -- web` empty; no suppression added
  - [ ] 5.2: `just changelog` lists exactly one entry from this story (Task 4)
  - [ ] 5.3: Status `review`; `just sprint set 23-4-config-files-can-be-saved-through-the-api review`; Dev Agent Record and File List
  - [ ] 5.4: Commit `chore(story-23.4/task-5): validate and move story 23.4 to review`

## Dev Notes

### The code today (verified at 02c96240)

Paths under `api/src/vintagestory_api/`.

- `services/server.py`: `_install_lock` (`:212`), `_lifecycle_lock` (`:229`); `lifecycle_busy` (`:291`); `_get_runtime_state()` (`:1074-1089`): the stored state while a process lives, STARTING/STOPPING when transitional, else INSTALLED; `_process`; `pending_config_edits` property (`:274`); `start_server()` takes `_lifecycle_lock` (`:1100`).
- `services/pending_config_edits.py`: `DropReason = Literal["started", "changed_again"]` (`:30`); `PendingConfigEdits.drop(keys, reason)` saves and logs `pending_config_edits_dropped` only when one was removed.
- `services/config_files.py` (Story 23.1): `_safe_path`, `_role_may_open`, `_has_json_suffix`, `CONFIG_FILE_MAX_BYTES`, `content_version`, the read's exceptions; `read_file` order of checks.
- `services/config_parse.py`: `parse_config_text(text, strict=...)`, `ConfigParseError.info: ParseErrorInfo`.
- `routers/config.py`: `RequireAdmin` (`middleware/permissions.py`), `NO_STORE`, `get_config_files_service`, `get_server_service`; the read route `GET /files/{filename:path}` and its error mapping (`:529-640`).

### The lock (Task 1)

```python
class GameServerNotStoppedError(Exception):
    def __init__(self, reason: Literal["running", "busy"]) -> None: ...

@asynccontextmanager
async def config_write(self) -> AsyncIterator[None]:
    """Hold the lifecycle lock while a config file is written (Epic 23 ADR-4 decision 4)."""
    if self._lifecycle_lock.locked() or self._install_lock.locked():
        raise GameServerNotStoppedError("busy")
    async with self._lifecycle_lock:  # free: acquired without yielding to another task
        process_alive = self._process is not None and self._process.returncode is None
        state = self._get_runtime_state()
        if process_alive or state in (ServerState.RUNNING, ServerState.STARTING, ServerState.STOPPING):
            raise GameServerNotStoppedError("running")
        yield
```

A start requested during the save awaits the lock (FIFO), so it begins after the write. The save never waits for a running lifecycle operation.

### The save (Task 2)

`save_file(filename, text, version) -> SavedConfigFile` (`@dataclass(frozen=True)`: `filename`, `version`, `previous_bytes`, `value` (the parsed new text), `is_root_serverconfig`), in this order:

1. `safe_path = self._safe_path(serverdata_dir, filename)`; `_role_may_open(safe_path, UserRole.ADMIN, file_request=True)` (always true inside the data directory; keeps the containment check); `_has_json_suffix(filename)` else `ConfigFileNotSupportedError`; `safe_path.exists()` else `ConfigFileNotFoundError`; regular file with a `.json` resolved name else `ConfigFileNotSupportedError`.
2. `data = text.encode("utf-8")` (a `UnicodeEncodeError` from a lone surrogate -> `ConfigFileInvalidError(ParseErrorInfo("The text is not valid UTF-8", None, None))`); `len(data) > CONFIG_FILE_MAX_BYTES` -> `ConfigFileTooLargeError`.
3. `parse_config_text(text, strict=is_root_serverconfig(safe_path))`; `ConfigParseError` -> `ConfigFileInvalidError(e.info)`.
4. `current = safe_path.read_bytes()` (`OSError` -> `ConfigFileReadError`); `content_version(current) != version` -> `ConfigFileChangedError`.
5. If `current` starts with the UTF-8 BOM and `data` does not, prefix it.
6. `_write_atomically(safe_path, data)`: `st = safe_path.stat()`; temp `safe_path.parent / f".{safe_path.name}.{secrets.token_hex(6)}.tmp"` opened with `os.open(temp, O_WRONLY | O_CREAT | O_EXCL, 0o600)`; write all, `os.fsync`; `os.chmod(temp, stat.S_IMODE(st.st_mode))`; when `os.geteuid() == 0`, `os.chown(temp, st.st_uid, st.st_gid)` (an `OSError` logged as `config_file_owner_not_kept`, not fatal); `os.replace(temp, safe_path)`; open the directory and `os.fsync` it (an `OSError` there is logged, not fatal). Any other `OSError` -> remove the temp if present (ignore errors) and raise `ConfigFileWriteError(filename)` (its message: `Config file could not be written: {filename}`, the relative name only); log `config_file_write_failed` with `error_type`, `errno` and `strerror` (no `str(e)`, it holds the absolute path).
7. Log `config_file_saved` with `filename`, `size=len(data)`, `old_version`, `new_version`; never the text.

`check_text(filename, text) -> ParseErrorInfo | None`: steps 1 (without the existence and regular-file checks) and 2 and 3; returns the info or None. Never reads or writes the file.

`is_root_serverconfig(path)`: `path.parent == serverdata_dir.resolve()` and `path.name.casefold() == "serverconfig.json"`.

### Pending edits (Task 3)

- `changed_top_level_keys(old: object, new: object) -> set[str]`: when both are dicts, the keys whose presence or value differs; otherwise (the old file did not parse, or a side is not an object) every key of the new object (an empty set if the new value is not an object).
- `ServerService.drop_pending_edits_changed_by_save(previous_bytes: bytes, new_value: object) -> None`: parse the previous text leniently (`parse_config_text`; on `ConfigParseError` or `UnicodeDecodeError` the old value is `None`), compute the changed keys, `self._pending_config_edits.drop(keys, reason="file_edited")`. Called by the route inside `config_write()` after a successful save of the root `serverconfig.json` only.

### The routes (Task 4)

- `POST /files/validate` (Admin): body `ConfigTextCheckRequest {filename: str (1..255), text: str}`; answer `{valid: bool, parse_error: {...} | null}`. Errors as the save's for the path (400, 403 cannot happen for Admin) and 413 for size.
- `PUT /files/{filename:path}` (Admin): body `ConfigFileSaveRequest {text: str, version: str (64 hex chars)}`; inside `async with server_service.config_write():` call `service.save_file`, then the pending-edit drop when `saved.is_root_serverconfig`; answer `{filename, version}`.
- Error mapping: `GameServerNotStoppedError("running")` -> 409 `CONFIG_FILE_SERVER_RUNNING` ("Stop the game server to save config files"), `("busy")` -> 409 `CONFIG_FILE_SERVER_BUSY` ("The game server is starting, stopping or being installed; try again when it is stopped"); `ConfigFileInvalidError` -> 422 `CONFIG_FILE_INVALID` with `parse_error`; `ConfigFileChangedError` -> 409 `CONFIG_FILE_CHANGED` ("The file changed on disk since it was read"); `ConfigFileWriteError` -> 500 `CONFIG_FILE_WRITE_FAILED`; the read's errors as the read maps them (`ConfigFileReadError` -> 500 `INTERNAL_ERROR` as there).
- Every answer has `Cache-Control: no-store` (success via `response.headers`, errors via `headers=NO_STORE`).

### API tests

- `test_config_files_save.py` (service, `tmp_path`): AC 1 (exact bytes, BOM kept, mode 0o640 kept, no `.tmp` left, version is the SHA-256 of the file now); AC 2 (each refusal, file unchanged); AC 3 (JSON5 error with a position; `Infinity`; root `serverconfig.json` with a comment and with a trailing comma refused, `ModConfig/serverconfig.json` with a comment accepted); AC 6; AC 7 (monkeypatch `os.replace` to raise: original unchanged, no temp left, message has no `tmp_path` string; monkeypatch `os.open` to raise: same); lone surrogate text; `check_text` rows (valid, invalid, strict rule, missing file allowed, traversal refused, nothing written).
- `test_config_write.py` (Task 1) as in 1.1.
- Pending edits (Task 3): `changed_top_level_keys` rows; the drop with a real store (Port changed and dropped, Ip kept; an unparseable previous text drops every key the new text has).
- `test_routers_config_save.py`: an app fixture like `config_files_app` (`tests/test_routers_config.py:992`) but with a real `ServerService(temp_settings)` overriding `get_server_service` (closed after the test); rows: Admin 200 and file content; Monitor 403 for both routes; 409 running (set `_server_state = ServerState.STARTING` on the service); 409 busy (hold `_lifecycle_lock` from the test's event loop is not possible across the TestClient's loop, so patch `ServerService.config_write` to raise `GameServerNotStoppedError("busy")` with `monkeypatch`); 409 changed; 422 with `parse_error`; 413; the pending-edit drop over HTTP; `no-store` on success and error; validate 200 rows.

### Testing rules

- `tmp_path` / the existing temporary settings only; no test touches `dev/` or `./data`; no game process is started (ADR-9).

### References

- `epics.md` "Story 23.4"; `architecture/epic-23-config-file-editing.md` ADR-1 decision 5, ADR-4, ADR-9
- Story 22.7 (`22-7-restart-required-settings-survive-a-live-change.md`) for the pending-edit store
- Story 23.1 for the parser and `content_version`

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
