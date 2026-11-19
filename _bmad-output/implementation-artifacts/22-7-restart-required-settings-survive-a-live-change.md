# Story 22.7: Restart-Required Settings Survive a Live Change

Status: ready-for-dev

<!-- Implements FR307, Epic 22 ADR-15 and ADR-14. Bead: VSS-zws (API-073), closes here (Story 22.3 confirmed it in its Task 1; maintainer answer 12, Matt, 2026-11-18). ADR-15 decisions 1 to 8 are the planner's and not reviewed yet. Order: 22.1, 22.2, 22.3, 22.4, 22.7, 22.5, 22.6. This branch, story/22-7-restart-required-settings-survive-a-live-change, is stacked on story/22-4-log-archive-and-backup-cleanup (22.4 in review) at 5c35b7e7 (22.3's review merged in). The PR targets main and merges after 22.4's. Line references were verified at 5c35b7e7; services/game_config.py, services/server.py, main.py, routers/config.py, config.py and services/pending_restart.py are unchanged since 36dd18cf, where ADR-15's facts were checked. Re-check them at implementation time. API and documentation only: one new service module, no new route, no response change, no web change, no new dependency. -->

## Story

As an **administrator**,
I want **a `Port` or `Ip` change I save while the game server runs to be the one the next start uses**,
so that **a later live setting change cannot quietly undo it while "Restart required" goes away as if it had worked**.

## Acceptance Criteria

1. **Given** the game is running and `serverconfig.json` holds `Port` 42420
   **When** an Admin key sets `Port` to 42421, and the game then writes its own config with 42420 (as it does after a live `/serverconfig` command), and the game is stopped
   **Then** after the exit `serverconfig.json` holds 42421 again, `pending_config_edits_reapplied trigger=exit` is logged, and the next start runs with 42421; after that start the pending edit is gone (`pending_config_edits_dropped reason=started`)
   *(Covers FR307; ADR-15 decisions 1, 3 and 4)*

2. **Given** the same pending edit and the game exits by itself (a crash or `/stop`)
   **When** the exit is seen
   **Then** the file holds 42421 again before anything starts the game; a Start, a Restart, a scheduled restart and auto-start each start with 42421
   **And** (refined, "ADR against the code" 2) a stop that fails after the process has exited (`_settle_state_after_failed_stop`) writes it back too
   *(Covers FR307; ADR-15 decision 3)*

3. **Given** a pending edit and the API restarts while the game is not running (the container was restarted)
   **When** the API starts
   **Then** the edit is read from `vsmanager/state/pending-config-edits.json`, written to `serverconfig.json` before auto-start (`trigger=api_start`), and with auto-start off the file holds 42421 while the game stays stopped
   *(Covers FR307; ADR-15 decisions 2 and 3)*

4. **Given** a pending `Port` edit of 42421
   **When** `Port` is set again (to 42422 while the game runs, or to 42423 while it is stopped)
   **Then** the pending edit holds 42422 in the first case and is dropped in the second, and an older value is never written over a newer one; a pending `ServerDescription` clear followed by a live `ServerDescription` change is dropped
   **And** (refined, "ADR against the code" 1 and 3) any successful update of a key that is not itself recorded drops that key's edit, and the drop after a start removes only the edit that start wrote, never one recorded or dropped while the process was being spawned
   *(Covers FR307; ADR-15 decision 4)*

5. **Given** a restart-required change saved while no game process lives
   **When** it is saved
   **Then** nothing is recorded (the game reads the file at its next start), and behaviour is as today
   *(Covers FR307; ADR-15 decision 1)*

6. **Given** a pending edit and `serverconfig.json` cannot be read or written at a start
   **When** the start runs
   **Then** `pending_config_edits_reapply_failed` is logged at ERROR, the start goes on, the edit is kept, and the pending-restart flag is set again after the start so "Restart required" stays
   *(Covers FR307; ADR-15 decision 5)*

7. **Given** the state file is missing, empty, not JSON, or names an unknown setting
   **When** the API starts
   **Then** it starts normally; a bad file or unknown key is logged at WARNING and ignored
   *(Covers FR307; ADR-15 decision 2)*

8. **Given** a setting managed by a `VS_CFG_*` variable
   **When** an Admin key tries to change it
   **Then** it is refused as today and nothing is recorded; the write-back never reads `VS_CFG_*`
   *(Covers FR307; ADR-15 decision 6)*

9. **Given** a throwaway container (never the dev stack)
   **When** the steps of Story 22.3's `VSS-zws` check are repeated with the fix: `Port` 42420 -> 42421 while running, a live `ServerName` change, stop, start
   **Then** the story records `serverconfig.json` after each step, the file holds 42421 after the stop, and the game listens on 42421 after the start; the same after `docker restart` of the container between the live change and the start
   *(Covers FR307; ADR-15, ADR-14)*

10. **(Added: the epic's README task.)** **Given** the README
    **When** an operator reads the Configuration section
    **Then** a short paragraph after the Configuration table says that a restart-required game setting (`Port`, `Ip`, a cleared description) changed while the server runs is kept until the next start, and that the Game Settings page shows the game's own value until the server stops
    *(Covers FR307; ADR-15 consequences)*

11. **(Added: quality gates, as every Epic 22 story.)** **Given** the story's code
    **When** it is validated
    **Then** `just check` is green with 0 skipped tests and Pyright 0 errors and 0 warnings; no added line holds a lint or type suppression, a `cast`, or a skip; no test reads or writes `dev/` or `./data`; the new log lines never carry a setting's value; the maintainer's manual check (Task 6.3) stays unticked until he confirms it
    *(Covers FR307; ADR-14, project-context.md rules 2, 8 and "Never Log Sensitive Data")*

## Tasks / Subtasks

<!-- Each code task includes its tests in the same commit, red first (write the new tests, run them, see them fail, then implement). Subjects: type(story-22.7/task-N): ..., the type chosen by what an admin notices. One commit is user-visible: Task 3 (fix), the commit that makes the edit survive; its subject is written for admins and its body names Story 22.7 and the task. -->

- [ ] Task 1: The `PendingConfigEdits` store + tests (AC: 7, 11)
  - [ ] 1.1: Red first: new `api/tests/test_pending_config_edits.py` with the Task 1 rows of Dev Notes "API tests"; see them fail (an `ImportError` at collection is the expected first red)
  - [ ] 1.2: New `api/src/vintagestory_api/services/pending_config_edits.py` (Dev Notes "The store"): the Pydantic file model, `PendingConfigEdits` with `edits`, `record`, `drop`, `drop_if_unchanged`, the load rules and the atomic save, and the pure function `reapply_edits(config_path, edits)` that does the read-set-write of ADR-15 decision 3 and returns what it changed. Nothing calls it yet
  - [ ] 1.3: `cd api && uv run ruff format <changed files>`; `just test-api tests/test_pending_config_edits.py` green; `just typecheck-api` 0 errors, 0 warnings
  - [ ] 1.4: Commit `refactor(story-22.7/task-1): add a store for restart-required game settings saved while the server runs`

- [ ] Task 2: Record and drop edits in `GameConfigService.update_setting` + tests (AC: 4, 5, 8, 11)
  - [ ] 2.1: Red first: the Task 2 rows of Dev Notes "API tests" in `api/tests/test_game_config.py` (new class `TestPendingConfigEditTracking`) and `api/tests/test_shared_pending_restart.py`; see them fail
  - [ ] 2.2: `services/server.py`: `ServerService.__init__` builds the one store, `PendingConfigEdits(self._settings.state_dir)`, and exposes it as the read-only property `pending_config_edits` (after `game_server_pid`, `:206-215`). No other change to `server.py` in this task
  - [ ] 2.3: `services/game_config.py`: the tracking step of Dev Notes "Recording and dropping" at the end of `update_setting` (`:768-822`), after the console or file call has returned without raising; nothing in `_update_config_file`'s write, flag or log lines (`:924-958`) or in `_execute_console_command` (`:838-900`) changes
  - [ ] 2.4: The guard test of Dev Notes "Secrets": no secret setting in `LIVE_SETTINGS` can be recorded
  - [ ] 2.5: `cd api && uv run ruff format <changed files>`; `just test-api tests/test_game_config.py tests/test_shared_pending_restart.py tests/test_routers_config.py tests/test_pending_config_edits.py` green; `just typecheck-api` 0/0
  - [ ] 2.6: Commit `refactor(story-22.7/task-2): record restart-required game settings saved while the server runs` (nothing writes them back yet)

- [ ] Task 3: Write back after exit, before every spawn and at API start; drop after a successful start; the failure rule + tests (AC: 1, 2, 3, 6, 11)
  - [ ] 3.1: Red first: the Task 3 rows of Dev Notes "API tests" in new `api/tests/server/test_pending_config_edits_lifecycle.py`, `api/tests/test_main.py` and `api/tests/test_shared_pending_restart.py`, including the scheduled restart and auto-start rows; see them fail
  - [ ] 3.2: `services/server.py`: the write-back of Dev Notes "Writing back" at the four points (`_stop_server_locked` after the wait, `_settle_state_after_failed_stop` when the process has exited, `_monitor_process` on an exit by itself, `_start_server_locked` after the template step and before the spawn); the drop after the spawn; the re-flag after the two `_clear_pending_restart()` calls (`:979`, `:1231`); the module-level `reapply_pending_config_edits_at_api_start()`
  - [ ] 3.3: `main.py`: import that function at module level next to `prepare_mod_files` (`:41`) and call it in the lifespan after `prepare_mod_files()` (`:176-182`) and before the auto-start block (`:184-208`), in its own `try`/`except Exception` that logs `pending_config_edits_startup_failed` at ERROR and goes on (Dev Notes "API start")
  - [ ] 3.4: `api/tests/conftest.py`: the autouse fixture of Dev Notes "Test safety", next to `prepare_mod_files_recorder` (`:76-87`)
  - [ ] 3.5: `cd api && uv run ruff format <changed files>`; `just test-api tests/server tests/test_main.py tests/test_shared_pending_restart.py tests/test_game_config.py tests/test_pending_config_edits.py tests/test_scheduled_restart.py tests/test_routers_config.py` green; `just typecheck-api` 0/0; `git status --short dev/ data/` empty
  - [ ] 3.6: Commit `fix(story-22.7/task-3): keep a Port or Ip change saved while the server runs when a later live setting change rewrites the config` (body: Story 22.7 / task 3; the change is kept in `vsmanager/state/pending-config-edits.json` and written to `serverconfig.json` again after the game exits, before every start and when the API starts; "Restart required" stays if it could not be written; closes the gap Story 22.3 found, `VSS-zws`)

- [ ] Task 4: Repeat Story 22.3's `VSS-zws` check with the fix in a throwaway container (AC: 9)
  - [ ] 4.1: Run Dev Notes "The throwaway-container run" exactly: image `vss-22-7-zws:local` built from this branch after Task 3's commit, container `vss-22-7-zws` on `127.0.0.1:18094`, no game port published, placeholder key, no `-v`/`--mount`/`--env-file`, no compose, not `just test-e2e-ci`. Never the dev stack (`vintagestory-manager-dev`, port 9080), whose game server is not started or stopped, and never `./data` or `dev/`
  - [ ] 4.2: Run A (stop path), run B (exit by itself through `/stop`) and run C (`docker restart` between the live change and the start), reading `Port` and `ServerName` from `serverconfig.json` and the state file at each step, as listed there
  - [ ] 4.3: Remove the container and the image (`docker rm -f vss-22-7-zws; docker image rm vss-22-7-zws:local`); `docker ps -a --filter name=vss-22-7` and `docker image ls vss-22-7-zws` are empty; `git status --short dev/ data/` is empty
  - [ ] 4.4: Record the results in Dev Agent Record "Throwaway-container results" (host architecture, game version, one table per run, the log lines, the commands) and append a "Results (Story 22.7)" paragraph to ADR-15's section in `_bmad-output/planning-artifacts/architecture/epic-22-server-operations-and-metrics.md`. No instance data, no real key, no address
  - [ ] 4.5: **Stop rule:** if any read after an exit or an API start does not hold the expected value, or the game does not listen on it after the start: commit the record (4.6), then stop and report it to the controller with the reads and the log lines. Tasks 5 and 6 wait for the answer; the story does not go to review before it
  - [ ] 4.6: Commit `docs(story-22.7/task-4): record a Port change surviving a live setting change in a throwaway container`

- [ ] Task 5: The README paragraph (AC: 10)
  - [ ] 5.1: `README.md`: the paragraph of Dev Notes "Documentation" between the Configuration table (ends `:91`) and `### Scheduled restarts` (`:93`)
  - [ ] 5.2: `just lint` green (nothing else moved)
  - [ ] 5.3: Commit `docs(story-22.7/task-5): explain when a restart-required game setting takes effect`

- [ ] Task 6: Validate and move the story to review (AC: all)
  - [ ] 6.1: `just check` green: API tests, pyright 0 errors and 0 warnings, ruff; web tests with 0 skipped, tsc, Prettier. The added lines in `api/src` and `api/tests` hold no `type: ignore`, `pyright:`, `noqa`, `cast(`, skip, `xfail` or `.only`. `git diff 5c35b7e7 -- web/ api/src/vintagestory_api/routers/ api/src/vintagestory_api/models/ api/src/vintagestory_api/services/pending_restart.py api/src/vintagestory_api/services/config_init_service.py api/src/vintagestory_api/jobs/` is empty. `git status --short dev/ data/` is empty after the runs
  - [ ] 6.2: `just changelog` lists exactly one new entry from this story (Task 3's fix subject); check by this branch's hashes, as Stories 22.2 to 22.4 did
  - [ ] 6.3: Manual check (maintainer only; leave unticked until he confirms, AC 11): on a non-production server he runs, change `Port` in Game Settings while the server runs, then change the server name, then press Restart; the game says it is running on the new port and a client can connect to it; then set the old port back the same way. No agent runs this, and never on the dev stack's game server
  - [ ] 6.4: Story status `review` in this file; `just sprint set 22-7-restart-required-settings-survive-a-live-change review`; Dev Agent Record and File List filled in, every statement true of the code
  - [ ] 6.5: Commit `chore(story-22.7/task-6): validate and move story 22.7 to review`
  - [ ] 6.6: After merge, with the maintainer's go-ahead only: `VSS-zws` (size-s) gets an abbreviated AAR comment with this story's commits and Task 4's evidence, then `bd close VSS-zws --reason "..."` and `bd sync` (CLAUDE.md "Completing Issues"). Pushing, the PR and the bead wait for that go-ahead

## Dev Notes

### The code today (verified at 5c35b7e7)

All paths below are under `api/src/vintagestory_api/` unless they say otherwise.

- **Which settings need a restart.** `LIVE_SETTINGS` (`services/game_config.py:103-212`). `Port` (`:197-203`) and `Ip` (`:204-211`, nullable) have `requires_restart=True`, `live_update=False`, no console command. Every other key is live (`/serverconfig ...`). `Password` (`:135-143`) is the only `secret=True` setting; it has a `clear_command` (`/serverconfig nopassword`). `ServerDescription` (`:110-116`) is nullable with no clear command.
- **How a change is written.** `update_setting` (`:768-822`): unknown key -> `SettingUnknownError` (`:788-789`); value validated (`:794-800`); env-managed key refused when `_block_env_managed` (`:802-806`, `SettingEnvManagedError`, before any write); `server_running = self.is_server_running()` (`:809`, which is `get_server_status().state == RUNNING`, `:569-578`); `use_console = server_running and setting_def.live_update` (`:810`). A `None` value while `use_console`: the setting's clear command (`Password`) or, without one (`ServerDescription`), `_update_config_file(..., requires_restart=True)` (`:812-817`). Otherwise the console (`:819-820`) or the file (`:821-822`).
- **`_update_config_file`** (`:902-969`): `_load_config()`, set the key, write `serverconfig.tmp` and rename (`:924-931`); `pending_restart` is the override or `setting_def.requires_restart` (`:934-936`) and, when true, `self._pending_restart_state.require_restart(f"Setting '{key}' changed - requires server restart")` (`:937-940`); `setting_updated` logs the value, or `"***"` for a secret (`:942-958`); any exception -> `config_file_update_failed` ERROR and `SettingUpdateFailedError` (`:967-969`). So a file write flags a restart for `Port`/`Ip` in any state, and for a cleared `ServerDescription` while running; while the game is `STARTING` or `STOPPING` (not `RUNNING`) every key goes to the file, with `pending_restart` false for the live keys.
- **`_execute_console_command`** (`:838-900`): sends the command through `ServerService.send_command`, logs `"***"` for a secret, returns `method="console_command"`, `pending_restart=False`.
- **The router** builds a fresh `GameConfigService` per request with `settings=server_service.settings`, the `ServerService` singleton and the shared flag, and the default `block_env_managed_settings=True` (`routers/config.py:106-123`; `get_pending_restart_state` returns `services/mods.py`'s `get_restart_state()`, `:93-103`, Story 22.2). `update_game_setting` calls `service.update_setting(key, request.value)` (`:214`). The API setting `block_env_managed_settings` (`services/api_settings.py:68-71`) is not read there, and `enforce_env_on_restart` (`:72-75`) says "(backlog)": not built.
- **`ServerService`** (`services/server.py`): one singleton (`get_server_service`, `:49-61`). `game_server_pid` (`:206-215`) is the pid while `_process.returncode is None`, so it covers `STARTING` (after the spawn), `RUNNING` and `STOPPING`. `_clear_pending_restart` (`:256-269`) reaches the shared flag through the lazy `_get_mod_service_module().get_restart_state()` and swallows any exception at DEBUG.
- **Every start** goes through `_start_server_locked` (`:982-1087`): checks (`:988-1008`), the template step `if needs_initialization(): initialize_config()` (`:1010-1013`, `serverconfig.json` created from the template with `VS_CFG_*` only when it does not exist), the command, `STARTING` (`:1036`), `await self._cancel_background_tasks()` (`:1040`), the player reset, then `await asyncio.create_subprocess_exec(...)` (`:1044-1051`), `RUNNING`, the monitor and readers; a spawn failure -> `INSTALLED`, `server_start_failed`, `RuntimeError(SERVER_START_FAILED)` (`:1084-1087`). `start_server` (`:966-980`, the Start button through `routers/server.py:214` and auto-start through `main.py:200`) calls `_clear_pending_restart()` after it (`:979`). `_restart_server_locked` (`:1209-1238`; the Restart button, `routers/server.py:342`, and scheduled restarts, `jobs/scheduled_restart.py` calling `restart_server()`) stops if running (`:1220-1224`), starts (`:1228`) and clears (`:1231`).
- **The exits.** `_stop_server_locked` (`:1104-1166`): `STOPPING`, SIGTERM, `wait_for(wait(), timeout)` or kill and `wait()` (`:1123-1141`), then exit code, `INSTALLED` (`:1143-1145`), `await self._cancel_background_tasks()` (`:1148`). A failure -> `_settle_state_after_failed_stop` (`:1178-1192`), which sets `INSTALLED` when the process has exited (`:1188-1192`). `_monitor_process` (`:1240-1273`): after `wait()` it handles an exit by itself only when the state is not `STOPPING` (`:1256-1267`); during a stop the stop path owns the exit.
- **The lifespan** (`main.py:152-231`): `ensure_data_directories()` (`:165`), `prepare_mod_files()` in a try/except (`:176-182`), auto-start (`:184-208`: `get_server_service()`, `start_server()` only from `INSTALLED`), then the scheduler (`:210-217`). ADR-15 cites `:182-208`; the auto-start block is `:184-208` (the try/except of `prepare_mod_files` ends at `:182`). The API's shutdown does not stop the game.
- **The state directory.** `Settings.state_dir` = `data_dir/vsmanager/state` (`config.py:262-265`), created by `ensure_data_directories` (`:272-301`). Files there today: `api-settings.json` (`services/api_settings.py:279`), `mods.json` (`services/mod_state.py:78`), the mod update store (`services/mod_updates.py:131-190`). The model for a small store: `ModUpdateStore` (Pydantic file model, `_load` returns an empty model and logs WARNING on `OSError`/`ValidationError`, `:183-190`; `save` writes `.tmp` and renames, `:176-181`).
- **The atomic-write rule** (`project-context.md` "Critical Implementation Rules" 6): temp file, then rename. Both new writes follow it.
- **The env map**: `VS_CFG_SERVER_PORT` -> `Port`, `VS_CFG_SERVER_IP` -> `Ip`, `VS_CFG_SERVER_DESCRIPTION` -> `ServerDescription`, `VS_CFG_SERVER_PASSWORD` -> `Password` (`services/config_init.py:17-29`).
- **What 22.3 measured** (`22-3-scheduled-restarts.md`, "Throwaway-container results"; ADR-8 "Results (Story 22.3)"): the game writes its in-memory config to `serverconfig.json` within about 3 s of a live `/serverconfig` command, so the overwrite happens while it runs, not only at shutdown; stops take under 1 s.

### The store (Task 1)

New module `services/pending_config_edits.py`. One owner: the `ServerService` singleton (Task 2.2). No second instance anywhere in `src`.

- **File:** `state_dir / "pending-config-edits.json"`, constant `PENDING_CONFIG_EDITS_FILENAME`. Shape (ADR-15 decision 2): `{"edits": {"Port": {"value": 42421, "recorded_at": "2026-11-19T12:00:00Z"}}}`.
- **Models** (Pydantic, as `ModUpdatesFile`): `PendingConfigEdit(value: str | int | float | bool | None, recorded_at: datetime)` and `PendingConfigEditsFile(edits: dict[str, PendingConfigEdit] = {})` (use `Field(default_factory=dict)`). Pydantic's smart union keeps `42421` an `int` and `true` a `bool`; a test pins that a saved `int` loads as `int`.
- **`PendingConfigEdits(state_dir: Path, *, now: Callable[[], datetime] = <UTC now>)`**, loaded at construction:
  - missing file -> no edits, no log;
  - unreadable (`OSError`), empty, not JSON or not the shape (`ValidationError`) -> WARNING `pending_config_edits_unreadable` with `error_type` and no edits; the bad file is left where it is (the next save replaces it);
  - a key not in `LIVE_SETTINGS` (import it from `services/game_config.py`; no import cycle: `game_config` imports `ServerService` only under `TYPE_CHECKING`, `:28-30`) -> WARNING `pending_config_edit_unknown_key` with `key` and dropped from memory (the file is rewritten at the next save).
- **API:** `edits` (a copy, `dict[str, PendingConfigEdit]`); `record(key, value)` (replace, `recorded_at = now()`, save, INFO `pending_config_edit_recorded key=...`); `drop(keys, reason)` (remove those present, save once, INFO `pending_config_edits_dropped keys=[...] reason=...` only when something was removed); `drop_if_unchanged(written: dict[str, PendingConfigEdit], reason)` (drop each key whose current edit equals the written one, value and `recorded_at`; see "Writing back"). `reason` is `Literal["started", "changed_again"]`.
- **Save:** `state_dir.mkdir(parents=True, exist_ok=True)`, write `pending-config-edits.tmp`, rename. With no edits left, save `{"edits": {}}` (do not delete the file: one code path, and "missing" and "empty" mean the same). A save that raises `OSError` is logged at ERROR `pending_config_edits_save_failed` (`error_type`, `errno`, `strerror`, never `str(e)`, whose text holds the absolute path; Story 22.4's rule) and does not raise: the in-memory edit stays, so the write-back still works until the API restarts ("ADR against the code" 5).
- **`reapply_edits(config_path: Path, edits: Mapping[str, PendingConfigEdit]) -> list[str]`** (module function, synchronous, no `await`; ADR-15 decision 3): returns `[]` without touching anything when `edits` is empty or `config_path` does not exist (decision 3: a missing file is not created). Otherwise `json.loads(config_path.read_text())`; a result that is not a JSON object raises `ValueError`; set each key whose current value differs from the edit's value (`config.get(key) != edit.value`, also when the key is absent); if none differs return `[]` with no write (the file's mtime does not change); else write `serverconfig.tmp` with `json.dumps(config, indent=2)` (the format `_update_config_file` writes, `:930`) and rename, and return the changed keys. It lets `OSError` and `ValueError` (`json.JSONDecodeError` is one) propagate: the caller logs them. It never reads `os.environ` or `VS_CFG_*` (decision 6).

### Recording and dropping (Task 2)

In `GameConfigService.update_setting`, keep the existing calls and put their result in `result`; after the call returns (an exception skips this step, so a refused or failed update changes nothing), call one private method, `_track_pending_edit(key, result)`:

- If `self._server_service is None`: do nothing (no process is known; `prometheus_metrics.py:115` builds a service without one).
- `store = self._server_service.pending_config_edits`.
- **Record** when `result.method == "file_update"` and `result.pending_restart` and `self._server_service.game_server_pid is not None`: `store.record(key, result.value)` (ADR-15 decision 1). This covers `Port`/`Ip` while `STARTING`, `RUNNING` or `STOPPING`, and a cleared `ServerDescription` while `RUNNING`.
- **Otherwise drop** `key` if the store holds it: `store.drop([key], reason="changed_again")` (decision 4). This covers a live console command, a file write while no process lives, and a file write while a process lives that does not flag a restart (a live key while `STARTING`/`STOPPING`) ("ADR against the code" 1).
- There is no `await` between the write and this step (`_update_config_file`'s body has none), so nothing interleaves.
- `update_setting`'s return value, the router's response and every existing log line are unchanged.

### Writing back (Task 3)

Add to `ServerService` one synchronous private method, `_reapply_pending_config_edits(trigger: Literal["exit", "start", "api_start"]) -> ReapplyOutcome` (a small frozen dataclass: `written: dict[str, PendingConfigEdit]`, `failed: bool`):

- `edits = self._pending_config_edits.edits`; none -> `ReapplyOutcome({}, False)`.
- `changed = reapply_edits(self._settings.serverdata_dir / "serverconfig.json", edits)`; `changed` non-empty -> INFO `pending_config_edits_reapplied keys=changed trigger=trigger`. Return `ReapplyOutcome(edits, False)` (`written` is every edit the file now holds, changed or already equal, so all of them are dropped after a start).
- `OSError` or `ValueError` -> ERROR `pending_config_edits_reapply_failed keys=sorted(edits) trigger=trigger error_type=...` (plus `errno`/`strerror` for an `OSError`; no `str(e)` of an `OSError`, no value), return `ReapplyOutcome({}, True)`. Nothing is raised: no exit or start path is blocked (decision 5).

Where it is called (ADR-15 decision 3):

1. **`_stop_server_locked`** right after the `try: wait_for ... except TimeoutError: kill; wait` block and the three state lines (`:1143-1145`), before `await self._cancel_background_tasks()` (`:1148`): `self._reapply_pending_config_edits("exit")`.
2. **`_settle_state_after_failed_stop`**, in the branch where the process has exited (`:1188-1192`): the same call, `"exit"` ("ADR against the code" 2). Not in the still-alive branch.
3. **`_monitor_process`**, inside `if self._server_state != ServerState.STOPPING:` (`:1256-1267`), after `INSTALLED` is set: `"exit"`. During a stop the stop path does it (one write-back per exit).
4. **`_start_server_locked`**, after the template step (`:1010-1013`) and before the spawn: `outcome = self._reapply_pending_config_edits("start")`. Put it after `await self._cancel_background_tasks()` (`:1040`) and the player reset, immediately before `create_subprocess_exec` (`:1045`), so no `await` of this method separates the write from the spawn. Keep `outcome` in `self._last_start_reapply_failed_keys: list[str]` (set to the edit keys when `outcome.failed`, `[]` otherwise) so the callers can re-flag.
   - **After a successful spawn** (after `self._process = await ...` returns, before `RUNNING`/the monitor or right after; inside the `try`): `self._pending_config_edits.drop_if_unchanged(outcome.written, reason="started")` (decision 4). It drops only an edit that is still the one written: an edit recorded again during the spawn's `await` (a newer value) stays for the next exit, and one dropped during it stays dropped ("ADR against the code" 3). A failed spawn (the `except` at `:1084`) drops nothing.
5. **Re-flag on failure** (decision 5): in `start_server` after `self._clear_pending_restart()` (`:979`) and in `_restart_server_locked` after its `self._clear_pending_restart()` (`:1231`), call a new private `_reflag_unapplied_edits()`: when `_last_start_reapply_failed_keys` is non-empty, `get_restart_state().require_restart(f"Settings {', '.join(keys)} could not be written to serverconfig.json - requires server restart")` through `_get_mod_service_module()` as `_clear_pending_restart` does; no value in the reason. A start that raised never gets here, and its flag was never cleared.
6. **API start:** a public method `ServerService.reapply_pending_config_edits_at_api_start() -> None` that returns at once when `game_server_pid is not None` (a guard; at API start no process lives) and otherwise calls `self._reapply_pending_config_edits("api_start")`; and a module-level function in `services/server.py`, `reapply_pending_config_edits_at_api_start() -> None`, that calls it on `get_server_service()`. No module reaches into a private name of another.

### API start (Task 3)

- `main.py` imports `reapply_pending_config_edits_at_api_start` at module level (`from vintagestory_api.services.server import ...`, next to `prepare_mod_files`, `:41`), so `tests/conftest.py` can replace it on `main_module` as it replaces `prepare_mod_files`.
- The lifespan calls it after the `prepare_mod_files` try/except (`:176-182`) and before `# Auto-start game server if enabled` (`:184`), whatever `auto_start_server` is, in:

```python
try:
    reapply_pending_config_edits_at_api_start()
except Exception as e:
    logger.error("pending_config_edits_startup_failed", error_type=type(e).__name__)
```

  (the function itself never raises for a file problem; this guard is for anything else, such as constructing the singleton). The API always starts.
- With auto-start on, `start_server` writes back again before the spawn; the values are equal, so nothing is written the second time.
- The API start does not set "Restart required" (the in-memory flag starts empty after an API restart while the edits are kept; the game is stopped, and the next start loads the file). Open question 1.

### What is logged

| Event | Level | Fields | When |
|---|---|---|---|
| `pending_config_edit_recorded` | INFO | `key` | a restart-required file write while a process lives |
| `pending_config_edits_dropped` | INFO | `keys`, `reason` (`started`, `changed_again`) | something was removed |
| `pending_config_edits_reapplied` | INFO | `keys`, `trigger` (`exit`, `start`, `api_start`) | the write-back changed the file |
| `pending_config_edits_reapply_failed` | ERROR | `keys`, `trigger`, `error_type` (+ `errno`, `strerror` for `OSError`) | the file could not be read or written |
| `pending_config_edits_unreadable` | WARNING | `error_type` | bad state file at load |
| `pending_config_edit_unknown_key` | WARNING | `key` | a key not in `LIVE_SETTINGS` at load |
| `pending_config_edits_save_failed` | ERROR | `error_type`, `errno`, `strerror` | the state file could not be written |
| `pending_config_edits_startup_failed` | ERROR | `error_type` | anything unexpected in the lifespan step |

**No new line carries a setting's value**, secret or not (stricter than ADR-15 decision 7, which only redacts secret values: "ADR against the code" 4). `setting_updated` keeps logging the value as today (`:942-958`). No absolute path in these lines.

### Secrets

- Can a restart-required key be secret? Not today. Recording needs a file write with `pending_restart` true while a process lives. `pending_restart` is true only for a setting with `requires_restart=True` (`Port`, `Ip`, neither secret) or for the `requires_restart=True` override, used only when a value is cleared while running and the setting has no `clear_command` (`:812-817`). `Password`, the only secret, has `requires_restart=False` and a `clear_command`, so it is set and cleared by console command while running, and while `STARTING`/`STOPPING` it is written to the file with `pending_restart` false: never recorded. `ServerDescription` is recorded only when cleared (value `None`).
- Guard test (Task 2.4): for every `setting` in `LIVE_SETTINGS` with `setting.secret`, `not setting.requires_restart and setting.clear_command is not None`. If a later change makes a secret recordable, the test fails and that story must decide (the state file would then hold the secret in plaintext, as `serverconfig.json` already does, under the same `/data` volume).
- The state file therefore holds only `Port`, `Ip` and `null` descriptions today. Its values are not secrets; it sits next to `api-settings.json`.

### Test safety (Task 3)

- `just test-api` runs with `VS_DATA_DIR=../dev` (`Justfile:36`), so `Settings()` in a test points at `dev/`. The new lifespan step calls `get_server_service()`, whose singleton is built with `Settings()` and would read `dev/vsmanager/state/pending-config-edits.json` and could write `dev/serverdata/serverconfig.json`.
- `api/tests/conftest.py` gains an autouse fixture next to `prepare_mod_files_recorder` (`:76-87`), in the same style: a small recorder class `ReapplyAtApiStartRecorder` (`calls: list[str]`, `error: Exception | None`) set with `monkeypatch.setattr(main_module, "reapply_pending_config_edits_at_api_start", recorder)`, with a docstring saying why. The lifespan order tests use it (and `prepare_mod_files_recorder`) to check the order.
- Every new test builds `Settings(data_dir=tmp_path / "data", api_key_admin=...)` or uses `installed_settings`/`temp_settings`; no new test calls `Settings()` without `data_dir` or `get_server_service()` unpatched. `git status --short dev/ data/` stays empty (Task 3.5, Task 6.1).
- `mock_subprocess` in `tests/server/test_lifecycle.py:36-66` returns from `wait()` after 0.01 s, so its monitor "sees an exit" almost at once. The new lifecycle tests need a process that stays alive until the test ends it: build their own fake in the new file (an `asyncio.Event` that `wait()` awaits with no timeout and that `send_signal`/`kill` or the test sets, `returncode` set when it fires). Use typed small classes or `AsyncMock`/`MagicMock` as the existing tests do; no `cast`.

### API tests

Red first in each task. Log assertions with `structlog.testing.capture_logs()`. Private module functions only through `monkeypatch.setattr`.

**Task 1, `tests/test_pending_config_edits.py`** (all on `tmp_path`, fixed `now`):

- missing file -> no edits, no log line; empty file, `not json`, `[]`, `{"edits": 5}` -> no edits, one WARNING `pending_config_edits_unreadable` each, construction does not raise;
- `{"edits": {"Port": {...}, "NotASetting": {...}}}` -> only `Port`, WARNING `pending_config_edit_unknown_key key=NotASetting`;
- `record("Port", 42421)` writes the file (read it back raw: shape, ISO `recorded_at`), a new instance loads it, the value is `int`; `record` again replaces; `record("Ip", None)` round-trips `None`;
- the save is atomic: no `.tmp` left, and a monkeypatched `Path.rename` that raises `OSError` -> ERROR `pending_config_edits_save_failed` without `str(e)`, no raise, the edit still in memory;
- `drop(["Port"], "changed_again")` removes and logs once; dropping an absent key logs nothing and does not write;
- `drop_if_unchanged`: same edit -> dropped; an edit replaced after the snapshot (new `recorded_at`) -> kept; a key dropped after the snapshot -> stays dropped, nothing re-added;
- `reapply_edits`: empty edits -> `[]`, file untouched (`st_mtime_ns` same); missing config -> `[]`, not created; differing value -> written, other keys kept as they were, `[ "Port" ]` returned, no `.tmp` left; equal values -> `[]`, mtime unchanged; absent key -> added; config that is `[]` or invalid JSON -> `ValueError`; config path that is a directory -> `OSError`; it reads no environment (set `VS_CFG_SERVER_PORT` with `monkeypatch.setenv` and see the edit's value written).

**Task 2, `tests/test_game_config.py` class `TestPendingConfigEditTracking`** (a real `ServerService(temp_settings)` with `_process` set to a fake live process through `monkeypatch.setattr`, or a small typed fake server with `get_server_status`, `game_server_pid`, `pending_config_edits` and `send_command`; not the existing `MagicMock`, whose attributes are never `None`):

- `Port` 42421 while running -> recorded (`edits["Port"].value == 42421`), `pending_config_edit_recorded key=Port`, response unchanged;
- `Port` 42421 then 42422 while running -> 42422;
- `Port` 42421 while running, then 42423 with no process (`_process` `None`) -> dropped, `reason=changed_again`, file holds 42423;
- `Port` while no process lives -> nothing recorded, no state file written (AC 5);
- `Port` while `STOPPING` with the process alive -> recorded;
- `ServerDescription` cleared while `RUNNING` -> recorded with `None`; then set while `RUNNING` (console command) -> dropped, `reason=changed_again` (AC 4);
- `ServerDescription` cleared while `RUNNING` -> recorded; then set while `STARTING` with the process alive (file write, `pending_restart` false) -> not recorded, the edit dropped ("ADR against the code" 1);
- env-managed `Port` (`monkeypatch.setenv("VS_CFG_SERVER_PORT", "42420")`) -> `SettingEnvManagedError`, nothing recorded, no state file (AC 8);
- a failing file write (`SettingUpdateFailedError`) and an invalid value (`SettingValueInvalidError`) -> nothing recorded or dropped;
- `server_service=None` -> no error, nothing recorded;
- the guard test of "Secrets";
- no recorded or dropped log line contains the value (`42421` absent from every new event's fields).

**Task 2, `tests/test_shared_pending_restart.py`** (its real temp-dir `service` and `client`): with a live fake process on `service`, `POST .../Port {"value": 42421}` -> `service.pending_config_edits.edits["Port"].value == 42421` and `settings.state_dir / "pending-config-edits.json"` holds it.

**Task 3, `tests/server/test_pending_config_edits_lifecycle.py`** (new; `installed_settings` with a `serverconfig.json` holding `{"Port": 42420, "ServerName": "x"}`, a pending edit `Port` 42421 recorded through the store, the long-lived fake process):

- stop: start, simulate the game's write (write 42420 to the file), `stop_server()` -> file 42421 right after the stop, `pending_config_edits_reapplied trigger=exit`; the edit is still pending until the next start (AC 1);
- stop then start -> after the start the edit is gone, `pending_config_edits_dropped reason=started`, the state file has `{"edits": {}}`; the spawn saw 42421 (read the file inside a `create_subprocess_exec` side effect) (AC 1);
- kill path: a `wait()` that times out with `timeout=0.01` -> killed -> file 42421;
- exit by itself: end the fake process (returncode 1) -> after the monitor runs the file holds 42421, `trigger=exit` (AC 2);
- failed stop of an exited process (as `test_failed_stop_of_exited_process_returns_to_installed`, `tests/server/test_lifecycle.py:486`) -> file 42421 ("ADR against the code" 2);
- before the spawn: the file says 42420 and no exit was seen (fresh `ServerService` loading the state file, as after a container stop) -> `start_server()` writes 42421 before `create_subprocess_exec` is called, `trigger=start`; `restart_server()` the same;
- scheduled restart: `run_restart_sequence("04:00", server=<the real ServerService, running>, still_scheduled=lambda: True, sleep=<no-op>)` with the game's write simulated -> after it the spawn saw 42421 and the edit is dropped (AC 2);
- equal values -> no write (mtime unchanged), no `reapplied` line;
- a spawn that raises `OSError` -> the edit is kept, no `dropped` line, the flag stays set (Story 22.2's rule: a failed start keeps it);
- an edit recorded again during the spawn (`create_subprocess_exec` side effect that calls `store.record("Port", 42424)`) -> after the start the edit is 42424, not dropped;
- failure rule: `serverconfig.json` replaced by a directory (or invalid JSON) -> `start_server()` succeeds, ERROR `pending_config_edits_reapply_failed trigger=start`, the edit is kept, and after the start `get_restart_state().pending_restart` is true with a reason naming `Port` (the autouse `fresh_restart_state` style: monkeypatch `services.mods._restart_state` to `None` first); the same through `restart_server()` (AC 6);
- a missing `serverconfig.json` at exit -> nothing created, the edit kept;
- `reapply_pending_config_edits_at_api_start()` with `get_server_service` monkeypatched to a temp-dir service -> file 42421, `trigger=api_start`, no process started (AC 3).

**Task 3, `tests/test_main.py` `TestLifespanAutoStart`:** with `reapply_at_api_start_recorder` and `prepare_mod_files_recorder` writing into one list (or comparing the two recorders' call order through a shared list in the test), the order is `prepare_mod_files`, the write-back, `start_server`, `scheduler_start` with auto-start on; with auto-start off the write-back still runs once; a write-back that raises -> ERROR `pending_config_edits_startup_failed`, auto-start and the scheduler still run (AC 3, 7). AC 7's bad-file cases are covered at the store level (Task 1); one lifespan test with a real temp-dir `ServerService` and a `not json` state file shows the API starts (`async with lifespan_for(...)`, with `get_server_service` patched to it).

**Task 3, `tests/test_shared_pending_restart.py`:** through the router with the temp-dir `service`: `Port` 42421 while running (fake live process), the game's write simulated, `POST /server/stop`, file 42421; `POST /server/start` (spawn patched) -> `/healthz` `game_server_pending_restart` false and the edit gone. The existing four tests stay as they are (they mock `_start_server_locked`, which is fine: nothing is recorded in them).

### Existing tests that change (deliberately)

- None is expected to change. `tests/test_game_config.py`'s `mock_server_service` (`:83-91`) is a `MagicMock`: `_track_pending_edit` calls `record`/`drop` on a `MagicMock` store and nothing is written; leave those tests alone. The existing `TestLifespanAutoStart` tests keep passing because the conftest fixture replaces the new step. If any existing test must change, record which and why in Completion Notes.

### The throwaway-container run (Task 4)

Run from the repo root after Task 3's commit; placeholder keys only (never `.env`'s); never the dev stack. The isolation is Story 22.3's (Dev Notes "The throwaway-container run" of `22-3-scheduled-restarts.md`): plain `docker build`/`docker run`, never `docker compose` (both compose files bind-mount `./data:/data`; `docker-compose.dev.yaml` is the dev stack on 9080 with game port 42420); no `-v`, `--mount` or `--env-file`, so `/data` lives in the container's writable layer, survives `docker restart` of the same container and goes with `docker rm -f`; own names (`vss-22-7-*`), own port `127.0.0.1:18094` (not 9080, not e2e-ci's 18080/18081, not 22.3's 18090, not 22.4's 18092), own image tag; not `just test-e2e-ci` (it blocks the game download hosts).

```bash
IMAGE=vss-22-7-zws:local; NAME=vss-22-7-zws; BASE=http://127.0.0.1:18094
KEY=vss-22-7-placeholder-admin-key; H=(-H "X-API-Key: $KEY" -H "Content-Type: application/json")
docker rm -f "$NAME" >/dev/null 2>&1 || true   # leftovers of a killed run
docker build --platform linux/amd64 -t "$IMAGE" .
docker run -d --name "$NAME" --platform linux/amd64 -p 127.0.0.1:18094:8080 \
  -e VS_API_KEY_ADMIN="$KEY" -e VS_DATA_DIR=/data "$IMAGE"
# wait for $BASE/healthz, then:
curl -s "${H[@]}" -X POST "$BASE/api/v1alpha1/server/install" -d '{"version":"stable"}'
# poll GET /api/v1alpha1/server/install/status until installed; record the resolved version
read_cfg() { docker exec "$NAME" python3 -c "import json; c=json.load(open('/data/serverdata/serverconfig.json')); print(c.get('Port'), c.get('ServerName'))"; }
read_state() { docker exec "$NAME" sh -c 'cat /data/vsmanager/state/pending-config-edits.json 2>/dev/null || echo missing'; }
```

- **Waiting for ready:** the game moves `server-main.log` into `Logs/Archive/` at each start (22.3's Debug Log) and keeps at most 5 archives (22.4), so wait for the start's own ready line, not an old one: before each start record the line count of `docker logs "$NAME"`, then wait for a new `now running on Port` line in `docker exec "$NAME" cat /data/serverdata/Logs/server-main.log` after the archive move (or poll `GET /api/v1alpha1/console/history` for `now running`). Record the port the line names.
- **Run A (stop path, AC 1):** start, ready, wait 30 s. Reads: (1) `read_cfg`, `read_state`; `POST /config/game/settings/Port {"value": 42421}` (expect `file_update`, `pending_restart: true`); (2) reads; `POST /config/game/settings/ServerName {"value": "vss-22-7 live change"}` (expect `console_command`); wait 5 s; (3) reads (expect `Port` 42420: the game wrote, as in 22.3; state file still holds 42421); `POST /server/stop`; (4) reads (expect 42421) and `docker logs "$NAME" 2>&1 | grep pending_config_edits`; `POST /server/start`, ready; (5) reads (expect 42421, state file `{"edits": {}}`), the ready line's port (expect 42421), `GET /healthz` `game_server_pending_restart` (expect false).
- **Run B (exit by itself, AC 2):** game running on 42421. `Port` 42422; `ServerName` `"vss-22-7 run b"`; wait 5 s; (1) reads (expect 42421); `POST /api/v1alpha1/console/command {"command": "/stop"}`; wait until `GET /api/v1alpha1/server/status` is `installed`; (2) reads (expect 42422; log `trigger=exit`); start, ready; (3) reads and the ready line's port (expect 42422).
- **Run C (`docker restart`, AC 3 and 9):** game running on 42422. `Port` 42420; `ServerName` `"vss-22-7 run c"`; wait 5 s; (1) reads (expect 42422 in the file, 42420 in the state file); `docker restart "$NAME"`; wait for `/healthz`; (2) reads (expect 42420) and the API's start log lines (`docker logs --since <restart time>`: `pending_config_edits_reapplied trigger=api_start` and no auto-start, since auto-start is off by default) and `GET /api/v1alpha1/server/status` (expect `installed`); start, ready; (3) reads and the ready line's port (expect 42420); stop.
- Record for every read: `Port`, `ServerName`, the state file, and the time. Record what the game printed at the `docker restart` (whether it saved and exited before the API, from `server-main.log` in the newest archive), without guessing it in advance.
- **Clean up even after a failure:** `docker rm -f "$NAME"; docker image rm "$IMAGE"`; then `docker ps -a --filter name=vss-22-7` and `docker image ls vss-22-7-zws` are empty; record `uname -m` (an arm64 host runs the image emulated).
- The game port is not published, so 42421 and 42422 clash with nothing.

### Documentation (Task 5)

`README.md`, between the Configuration table (ends `:91`) and `### Scheduled restarts` (`:93`), in the README's plain style:

> **Game settings that need a restart.** `Port`, `Ip` and a cleared server description take effect only when the game server starts. If you change one while the server runs, the manager keeps the change in `vsmanager/state/pending-config-edits.json` and writes it to `serverconfig.json` again after the server stops and before every start (the Start and Restart buttons, scheduled restarts and auto-start), because the game rewrites `serverconfig.json` with its own values when another setting is changed live. Until the server stops, the Game Settings page shows the game's value; "Restart required" stays until a start has loaded the change.

Adjust the wording if Task 3's code says otherwise; every sentence must be true of the code.

### Not changed (do not "fix" these here)

- The live command path and its logging; the game's own write of its config (it cannot be prevented); `PendingRestartState` (`services/pending_restart.py`) and the flag's meaning; `_clear_pending_restart`; the 10 s stop timeout; `ConfigInitService`; `routers/config.py`, `routers/server.py` and every route, response and status code; `models/`; `jobs/` (`scheduled_restart.py` is covered because it calls `restart_server()`); `services/scheduler.py`; the web (ADR-15 decision 8).
- `is_server_running` stays `state == RUNNING`; the recording rule uses `game_server_pid` instead, on purpose (decision 1).
- `block_env_managed_settings` and `enforce_env_on_restart` stay unread (decision 6).
- The non-restart file writes made while `STARTING`/`STOPPING` (open question 2) and a hand edit of `serverconfig.json` while the game runs are not recorded (ADR-15 consequences).
- `ServerService._clear_pending_restart` and `_update_mod_service_server_state` logging at DEBUG only (noted in 22.2's review; out of scope).

### API contract changes

None. No route, field, status code or setting changes. One new state file, `vsmanager/state/pending-config-edits.json`, owned by the manager.

### ADR against the code

1. **The drop rule is the general form of decision 4.** Decision 4 names a live console command and a file write while no process lives. While `STARTING` or `STOPPING`, `update_setting` writes a live key to the file with `pending_restart` false while a process lives (`:809-822`); that write is newer than any edit of the key and is not recorded (decision 1), so it must drop the edit too. The rule here: any successful update that is not itself recorded drops the key's edit. Only `ServerDescription` can be both recorded and live, so this matters for it alone today.
2. **A failed stop of an exited process writes back.** Decision 3 names the stop after `wait()` and the monitor. When `_stop_server_locked` raises after the process exited, `_settle_state_after_failed_stop` (`:1188-1192`) takes the exit and the monitor has left it to the stop (`:1256`), so neither named point runs. It writes back there too (`trigger=exit`); the before-spawn write-back would cover it anyway.
3. **Dropping after a start is by identity.** Decision 4 drops "every edit that was written". Between the write-back and the end of the spawn there are `await`s (`create_subprocess_exec`), and an update can land there (state `STARTING`, no live pid yet, so it drops the edit; or, after the pid exists, records a newer one). `drop_if_unchanged` removes only an edit that is still the one written, so a newer edit is kept for the next exit and a dropped one is not revived.
4. **No value in the new log lines.** Decision 7 logs values unless the setting is secret; the new lines carry keys only, which is simpler and never leaks. `setting_updated` still logs the value as before.
5. **A failed state-file save does not fail the update.** ADR-15 does not say. The `serverconfig.json` write has already succeeded and the response says so; the edit is kept in memory (lost only if the API restarts before the next exit) and the failure is an ERROR.
6. **Line references.** ADR-15 cites `main.py:182-208` for auto-start; it is `:184-208` (the `prepare_mod_files` guard ends at `:182`). The other ADR-15 references hold at 5c35b7e7.
7. **Where the write-back sits in `_start_server_locked`.** Decision 3 says after the template step and before `create_subprocess_exec`. It is placed immediately before the spawn, after `_cancel_background_tasks()` (`:1040`): still after the template step, and it leaves no `await` of this code between the write and the spawn.

### Open questions for the maintainer (none blocks the start)

1. **"Restart required" after an API restart.** The flag lives in memory, so after `docker restart` it is off while an edit is kept and written at `api_start`. The game is stopped then, and the next start loads the file, so nothing is lost. Default: no flag at API start. Should the API start set it when edits are kept, so the banner shows until the next start?
2. **Live settings saved while the game is starting or stopping.** `update_setting` writes them to the file with no restart flag (`:809-822`); the game may already have read the file, or may rewrite it, and ADR-15 decision 1 does not record them. The same loss as `VSS-zws` is possible in that window (a few seconds per start or stop). Default: unchanged here. File a bead?
3. **A `VS_CFG_*` variable set after an edit is recorded.** Decision 6: the write-back never reads `VS_CFG_*`, and env values apply only when the file is created, so a recorded `Port` wins over a `VS_CFG_SERVER_PORT` added later (the key is then refused for new changes). Confirm.

### Testing Requirements

**CRITICAL:** tests are written with each task and committed with it, red first. `just test-api <files>` after each task; `just check` before review.

- No lint or type suppression (`# type: ignore`, `# pyright: ignore`, `noqa`), no `cast`, no `as`-style escape (`typing.cast`, `Any`-typed stand-ins for typed parameters), no skipped test (`pytest.mark.skip`, `skipif`, `xfail`, `pytest.skip`), no `.only`. Pyright 0 errors and 0 warnings in `src` and `tests`. The existing file-level `# pyright:` lines in `tests/server/conftest.py` are not copied into the new test file.
- Every test on `tmp_path`; no test reads or writes `dev/` or `./data` (`git status --short dev/ data/` empty); the conftest fixture of "Test safety" is in place before any lifespan test runs the new step.
- Never run `just test-e2e-api`, `just test-e2e` or `just test-e2e-web` (they target the dev stack); never `just docker ...`. No E2E test is added: the write-back needs a game process, and Task 4's container covers the real game. Docker only for Task 4's `vss-22-7-zws` container.

### Security Requirements

- `POST /config/game/settings/{key}` stays Admin only; env-managed keys stay refused before any write (AC 8).
- No new log line carries a value or an absolute path; `OSError`s are logged by `errno`/`strerror`, not `str(e)`.
- The state file is written atomically under `state_dir`; its name is a constant, never built from a request.
- The throwaway container uses a placeholder key, binds only `127.0.0.1:18094`, and is removed with its image; nothing from it is committed except setting values, log event names and game lines without addresses.

### Development Commands

- `just test-api tests/test_pending_config_edits.py tests/test_game_config.py tests/test_shared_pending_restart.py tests/server tests/test_main.py tests/test_scheduled_restart.py tests/test_routers_config.py`, `just typecheck-api`, `just lint-api`.
- `cd api && uv run ruff format <changed files>` (`just format-api` takes no file arguments and formats the whole tree).
- `just check` (Task 6), `just changelog` (Task 6.2), `just sprint set 22-7-restart-required-settings-survive-a-live-change review`.

### Previous Story Intelligence

- **22.4** (this branch's base, in review): the conftest autouse no-op pattern for anything that would touch `dev/` (`no_real_disk_cleanup`); `OSError` logged without `str(e)`; the throwaway-container recipe on 18092 and its stop rule; the game keeps at most 5 log archives itself and moves `server-main.log` at each start, so a ready-line wait must not read the previous run's line.
- **22.3:** found `VSS-zws` (Task 1): the overwrite happens within about 3 s of a live `/serverconfig` command; stops take under 1 s, so the exit write-back adds nothing noticeable to a restart. `ServerService.game_running`/`lifecycle_busy`; `run_restart_sequence` takes a `RestartTarget`, which a real `ServerService` satisfies. Its "API tests" rows were checked against the rules before writing them; do the same here.
- **22.2:** one shared pending-restart state; any successful start (`start_server`) and a restart clear it; a failed start keeps it (`tests/test_shared_pending_restart.py`). Route tests over a real temp-dir service rather than a bare `MagicMock`.
- **21.3:** the depth model; completion notes must be true of the code.

### Git Intelligence

- Branch `story/22-7-restart-required-settings-survive-a-live-change` from `story/22-4-log-archive-and-backup-cleanup` at `5c35b7e7` (`Merge branch 'story/22-3-scheduled-restarts' into story/22-4-log-archive-and-backup-cleanup`). 22.4's commits: `c77f9074`, `8cf51967`, `a5c7c1ca`, `6d5aff2d`, `7a568dcb`, `a14103e1` (`feat`), `e52d5239`, `55f040c5`. Story 22.7 was planned in `6fd76056`.
- Planned commits: Task 1 `refactor(story-22.7/task-1): add a store for restart-required game settings saved while the server runs`; Task 2 `refactor(story-22.7/task-2): record restart-required game settings saved while the server runs`; Task 3 `fix(story-22.7/task-3): keep a Port or Ip change saved while the server runs when a later live setting change rewrites the config`; Task 4 `docs(story-22.7/task-4): record a Port change surviving a live setting change in a throwaway container`; Task 5 `docs(story-22.7/task-5): explain when a restart-required game setting takes effect`; Task 6 `chore(story-22.7/task-6): validate and move story 22.7 to review`.

### Project Structure Notes

- New: `api/src/vintagestory_api/services/pending_config_edits.py`, `api/tests/test_pending_config_edits.py`, `api/tests/server/test_pending_config_edits_lifecycle.py`.
- Modified: `services/game_config.py` (`update_setting` and one private method), `services/server.py` (the store, the write-back points, the drop, the re-flag, the API-start function), `main.py` (one import, one call), `api/tests/conftest.py`, `api/tests/test_game_config.py`, `api/tests/test_shared_pending_restart.py`, `api/tests/test_main.py`, `README.md`, ADR-15 (Task 4).
- Naming follows the codebase: snake_case modules, a `*File` Pydantic model for the file shape (as `ModUpdatesFile`), event names in lower snake case.

### References

- [Source: _bmad-output/planning-artifacts/epics.md] Story 22.7 (`:7713`), Epic 22 order and dependencies (`:7238-7246`)
- [Source: _bmad-output/planning-artifacts/prd.md] FR307 (`:931`)
- [Source: _bmad-output/planning-artifacts/architecture/epic-22-server-operations-and-metrics.md] ADR-8 and "Results (Story 22.3)", ADR-14, ADR-15
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-18-epic-22.md] answer 12, section 5 planner decisions
- [Source: _bmad-output/implementation-artifacts/22-3-scheduled-restarts.md] Task 1, "Throwaway-container results"
- [Source: _bmad-output/implementation-artifacts/22-2-prometheus-metrics-endpoint.md] Task 2, "ADR against the code" 8
- [Source: _bmad-output/implementation-artifacts/22-4-log-archive-and-backup-cleanup.md] "Test safety", "The throwaway-container run"
- [Source: project-context.md] Critical Implementation Rules 1, 2, 6, 8; Security Patterns 3; Logging Conventions; Commit Message Format
- `bd show VSS-zws` (comments of 2026-11-14 and 2026-11-19)

## Dev Agent Record

### Agent Model Used

### Throwaway-container results

<!-- Task 4.4: host architecture, game version, a table per run (Port, ServerName, state file at each read), the log lines, the commands. -->

### Debug Log References

### Completion Notes List

- 2026-11-19: Story created (create-story, non-interactive) and checked against the create-story checklist: 6 tasks; every code task carries its tests (Task 4 is a container check, Task 5 documentation, Task 6 validation); every AC is mapped to a task (AC 11 to every code task and Task 6, the maintainer check to Task 6.3). Line references verified at 5c35b7e7. Ultimate context engine analysis completed - comprehensive developer guide created.

### File List

## Change Log

- 2026-11-19: Story 22.7 created (ready-for-dev).
