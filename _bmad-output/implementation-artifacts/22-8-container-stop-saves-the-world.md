# Story 22.8: Stopping the Container Saves the World

Status: done

<!-- Implements FR308, Epic 22 ADR-16 and ADR-14. No bead: found inside the epic by Story 22.7's throwaway Run C (its Completion Notes, drawdown item 1) and drawn down there on the maintainer's answer 13 (Matt, 2026-11-19). ADR-16 decisions 1 to 9 are the planner's and not reviewed yet. Order: 22.1, 22.2, 22.3, 22.4, 22.7, 22.8, 22.5, 22.6. This branch, story/22-8-container-stop-saves-the-world, is stacked on story/22-7-restart-required-settings-survive-a-live-change (22.7 in review) at da55999b; Story 22.8 was planned in 4dd719f1 (planning files only). The PR targets main and merges after 22.7's. Line references were verified at da55999b (the code is unchanged in 4dd719f1); re-check them at implementation time. API, one image `CMD` flag and documentation: no new route, no response change, no new setting, no web change, no new dependency, no compose change. The `CMD` flag (`--timeout-graceful-shutdown 1`, Task 3) was added at validation (2026-11-19); see "ADR against the code" 6. -->

## Story

As an **administrator**,
I want **stopping or restarting the manager's container to stop the game server the normal way first**,
so that **the world is saved and players do not lose their progress when I upgrade, restart or stop the container**.

## Acceptance Criteria

1. **Given** the game server is running
   **When** the API shuts down (the container gets SIGTERM)
   **Then** before the scheduler is shut down, the game is stopped through the normal stop path (SIGTERM, a kill only if it has not exited after 8 seconds), and the log shows `api_shutdown_stopping_game`, the stop's own lines (`stopping_server`, `server_stopped_gracefully`), `api_shutdown_game_stopped`, then `scheduler_stopped` and `api_shutting_down`
   *(Covers FR308; ADR-16 decisions 1, 2, 3, 5 and 8)*

2. **Given** no game process lives (never started, stopped, or exited by itself)
   **When** the API shuts down
   **Then** nothing is stopped, no `ServerService` is built for it, and the shutdown is as today
   *(Covers FR308; ADR-16 decisions 1 and 8)*

3. **Given** a game that does not exit on SIGTERM
   **When** the API shuts down
   **Then** it is killed after 8 seconds (`server_stop_timeout`, `server_killed`), `api_shutdown_game_stopped` is still logged, and the shutdown goes on
   *(Covers FR308; ADR-16 decision 5)*

4. **Given** a scheduled restart that holds the lifecycle lock, or a scheduled restart sequence in its warnings
   **When** the API shuts down
   **Then** the game is not started again: the restart's start is refused (`start_server_failed reason=api_shutting_down`, `RuntimeError(SERVER_START_FAILED)`), the sequence ends without a start, and the game is stopped when the shutdown step returns
   *(Covers FR308; ADR-16 decisions 3 and 4)*

5. **Given** the shutdown stop fails (the stop raises, or anything in the step raises)
   **When** the API shuts down
   **Then** `api_shutdown_game_stop_failed` is logged at ERROR, and the scheduler and the mod service are still shut down and `api_shutting_down` is still logged
   *(Covers FR308; ADR-16 decisions 1 and 8)*

6. **Given** a restart-required game setting saved while the game ran, and the game then rewrote `serverconfig.json` after a live change (Story 22.7)
   **When** the API shuts down
   **Then** `serverconfig.json` holds the saved value after the stop (`pending_config_edits_reapplied trigger=exit`), before `api_shutting_down`
   *(Covers FR308; ADR-16 decision 7)*

7. **Given** a throwaway container (never the dev stack) with a running game
   **When** it is stopped with `docker stop`, restarted with `docker restart` while a console WebSocket is open, and stopped with `docker stop -t 30` and `docker stop -t 2`
   **Then** the story records the process tree, the game's save and stop lines in `server-main.log`, the API's lines in order, how long each stop took and the container's exit code; with the default grace (10 s) and with 30 s the game saves and the container exits cleanly well inside the grace
   *(Covers FR308; ADR-16 decision 9, ADR-14)*

8. **Given** the README
   **When** an operator reads how to run the container
   **Then** it says that stopping or restarting the container stops the game server the normal way first so the world is saved, that the manager waits up to 8 seconds for the game, that the stop grace period should stay at Docker's default of 10 seconds or more (`docker stop -t`, compose `stop_grace_period`, Kubernetes `terminationGracePeriodSeconds`), and what can still lose progress
   *(Covers FR308; ADR-16 decision 6)*

9. **(Added: quality gates, as every Epic 22 story.)** **Given** the story's code
   **When** it is validated
   **Then** `just check` is green with 0 skipped tests and Pyright 0 errors and 0 warnings; no added line holds a lint or type suppression, a `cast`, an `as`-style escape or a skip; no test reads or writes `dev/` or `./data`; the maintainer's manual check (Task 6.3) stays unticked until he confirms it
   *(Covers FR308; ADR-14, project-context.md rules 2 and 8)*

## Tasks / Subtasks

<!-- Each code task includes its tests in the same commit, red first (write the new tests, run them, see them fail, then implement). Subjects: type(story-22.8/task-N): ..., the type chosen by what an admin notices. One commit is user-visible: Task 2 (fix), the commit that makes a container stop save the world; its subject is written for admins and its body names Story 22.8 and the task. -->

- [x] Task 1: The shutdown stop in `ServerService` and the refusal of starts + tests (AC: 1, 2, 3, 4, 6, 9)
  - [x] 1.1: Red first: new `api/tests/server/test_api_shutdown_stop.py` with the Task 1 rows of Dev Notes "API tests"; see them fail (an `ImportError` at collection is the expected first red)
  - [x] 1.2: `services/server.py`: the constant `SHUTDOWN_STOP_TIMEOUT_SECONDS = 8.0`; `self._shutting_down = False` in `__init__`; the refusal in `_start_server_locked`; the public `ServerService.stop_for_api_shutdown(timeout)`; the module-level `stop_game_server_for_api_shutdown()` (Dev Notes "The shutdown stop"). Nothing calls them yet
  - [x] 1.3: `cd api && uv run ruff format <changed files>`; `just test-api tests/server tests/test_scheduled_restart.py` green; `just typecheck-api` 0 errors, 0 warnings
  - [x] 1.4: Commit `refactor(story-22.8/task-1): add a game server stop for the API's shutdown`

- [x] Task 2: The lifespan stops the game before the scheduler + tests (AC: 1, 2, 5, 9)
  - [x] 2.1: Red first: the Task 2 rows of Dev Notes "API tests" in `api/tests/test_main.py` (new class `TestLifespanShutdownStopsTheGame`), in `api/tests/server/test_api_shutdown_stop.py` (new class `TestLifespanRunsTheShutdownStop`) and the autouse recorder in `api/tests/conftest.py`; see them fail
  - [x] 2.2: `main.py`: import `stop_game_server_for_api_shutdown` at module level next to `reapply_pending_config_edits_at_api_start` (`:43`); await it after `yield` (`:227`) and before `# Shutdown scheduler first` (`:229-231`), in its own `try`/`except Exception` (Dev Notes "The lifespan"); fix the old comment so it no longer says the scheduler goes first
  - [x] 2.3: `api/tests/conftest.py`: the autouse fixture of Dev Notes "Test safety", next to `reapply_at_api_start_recorder` (`:90-120`)
  - [x] 2.4: `cd api && uv run ruff format <changed files>`; `just test-api tests/test_main.py tests/server tests/test_scheduled_restart.py tests/test_shared_pending_restart.py` green; `just typecheck-api` 0/0; `git status --short dev/ data/` empty
  - [x] 2.5: Commit `fix(story-22.8/task-2): stop the game server, saving the world, when the container stops or restarts` (body: Story 22.8 / task 2; on SIGTERM the manager now stops a running game through the normal stop, waiting up to 8 s, before it shuts down its scheduler and exits; no start is allowed once the shutdown has begun; before, the game died with the container without saving, found by Story 22.7's throwaway run)

- [x] Task 3: Bound uvicorn's wait for open requests in the image, so the shutdown stop runs inside the grace (AC: 1, 7, 9)
  - [x] 3.1: Red first: in `scripts/tests/test-docker-context.sh`, an `assert_contains` that the `Dockerfile`'s `CMD` line holds `"--timeout-graceful-shutdown", "1"`; `just test-scripts test-docker-context.sh` fails
  - [x] 3.2: `Dockerfile:92`: append `"--timeout-graceful-shutdown", "1"` to the `CMD` (nothing else in it changes: still `uv run --no-sync uvicorn ...`, no `exec`, no init; Dev Notes "The code today", "The image"), with a comment above it: on SIGTERM uvicorn waits at most 1 s for open requests and background tasks, then cancels them and runs the lifespan shutdown, which stops the game in up to 8 s, inside Docker's 10 s (Story 22.8, Epic 22 ADR-16 decision 5)
  - [x] 3.3: `just test-scripts test-docker-context.sh` green; `just lint-scripts` green. `just dev-api` (the `Justfile`) is not changed: it is not the container
  - [x] 3.4: Commit `build(story-22.8/task-3): limit uvicorn's wait for open requests at shutdown to 1 second` (body: Story 22.8 / task 3; an install, mod download or Stop/Restart request in flight at SIGTERM no longer holds the lifespan shutdown, and so the game's stop, past Docker's 10 s grace)

- [x] Task 4: Show it in a throwaway container (AC: 7)
  - [x] 4.1: Run Dev Notes "The throwaway-container run" exactly: image `vss-22-8-stop:local` built from this branch after Task 3's commit, container `vss-22-8-stop` on `127.0.0.1:18096`, no game port published, placeholder key, no `-v`/`--mount`/`--env-file`, no compose, not `just test-e2e-ci`. Never the dev stack (`vintagestory-manager-dev`, port 9080), whose game server is not started or stopped, and never `./data` or `dev/`
  - [x] 4.2: The process tree (and PID 1's command line holds `--timeout-graceful-shutdown 1`); Run A (`docker stop`, with a pending `Port` edit the game has overwritten), Run B (`docker restart` with an open console WebSocket), Run C (`docker stop -t 30`), Run D (`docker stop -t 2`), as listed there
  - [x] 4.3: Remove the container and the image (`docker rm -f vss-22-8-stop; docker image rm vss-22-8-stop:local`); `docker ps -a --filter name=vss-22-8` and `docker image ls vss-22-8-stop` are empty; `git status --short dev/ data/` is empty
  - [x] 4.4: Record the results in Dev Agent Record "Throwaway-container results" (host architecture, game version, the process tree, one block per run with the timings, exit codes, the API lines and the game's last lines, the commands) and append a "Results (Story 22.8)" paragraph to ADR-16's section in `_bmad-output/planning-artifacts/architecture/epic-22-server-operations-and-metrics.md`, which also records the `CMD`'s `--timeout-graceful-shutdown 1` (Task 3; "ADR against the code" 6). No instance data, no real key, no address
  - [x] 4.5: **Stop rule:** if in Run A, B or C the lifespan shutdown does not run, the game's `server-main.log` shows no save before the container stops, the API lines are not in AC 1's order, or the container's exit code is 137 (killed by Docker): commit the record (4.6), then stop and report to the controller with the lines. Tasks 5 and 6 wait for the answer; the story does not go to review before it. Run D's outcome is recorded, not judged
  - [x] 4.6: Commit `docs(story-22.8/task-4): record a container stop saving the world in a throwaway container`

- [x] Task 5: The README section (AC: 8)
  - [x] 5.1: `README.md`: the section of Dev Notes "Documentation", `### Stopping and restarting the container`, between `### Upgrading` (`:45-56`) and `### Verifying an image` (`:58`)
  - [x] 5.2: `just lint` green
  - [x] 5.3: Commit `docs(story-22.8/task-5): explain what stopping the container does to the game server`

- [ ] Task 6: Validate and move the story to review (AC: all)
  - [x] 6.1: `just check` green: API tests, pyright 0 errors and 0 warnings, ruff; web tests with 0 skipped, tsc, Prettier; and `just test-scripts`. The added lines in `api/src` and `api/tests` hold no `type: ignore`, `pyright:`, `noqa`, `cast(`, skip, `xfail` or `.only`. `git diff da55999b -- web/ docker-compose.yaml docker-compose.dev.yaml api/src/vintagestory_api/routers/ api/src/vintagestory_api/models/ api/src/vintagestory_api/services/scheduler.py api/src/vintagestory_api/jobs/ api/src/vintagestory_api/services/pending_config_edits.py` is empty, and `git diff da55999b -- Dockerfile` is Task 3's `CMD` line and its comment only. `git status --short dev/ data/` is empty after the runs
  - [x] 6.2: `just changelog` lists exactly one new entry from this story (Task 2's fix subject; Task 3's `build` commit is not a release note); check by this branch's hashes, as Stories 22.2 to 22.7 did
  - [ ] 6.3: Manual check (maintainer only; leave unticked until he confirms, AC 9): on a non-production server he runs, with a client connected, place a few blocks, wait less than the autosave interval, then `docker compose restart` (or `docker compose up -d` after changing the image tag); start the game if auto-start is off, reconnect, and the blocks are there; `server-main.log` of the stopped run (now in `Logs/Archive/`) ends with the save and stop lines. No agent runs this, and never on the dev stack's game server
  - [x] 6.4: Story status `review` in this file; `just sprint set 22-8-container-stop-saves-the-world review`; Dev Agent Record and File List filled in, every statement true of the code
  - [x] 6.5: Commit `chore(story-22.8/task-6): validate and move story 22.8 to review`. No bead to close (none was filed); pushing and the PR wait for the maintainer's go-ahead

## Dev Notes

### The code today (verified at da55999b)

All paths below are under `api/src/vintagestory_api/` unless they say otherwise.

- **The image.** `Dockerfile`: no `ENTRYPOINT` and no entrypoint script (none exists in the repository); `USER vsmanager` (`:79`); `HEALTHCHECK` (`:82-83`); `CMD ["uv", "run", "--no-sync", "uvicorn", "vintagestory_api.main:app", "--host", "0.0.0.0", "--port", "8080"]` (`:92`). No init process: PID 1 is `uv`, uvicorn is its child, and the game (`dotnet VintagestoryServer.dll`) is uvicorn's child (`services/server.py:1158`, `asyncio.create_subprocess_exec`). Docker sends the stop signal (SIGTERM) to PID 1 only. `uv run` does not exec: it spawns the command and, on Unix, forwards every signal it receives except SIGKILL, SIGCHLD, SIGIO and SIGPOLL to that child (SIGINT only when sent twice or when the child's process group differs) and then exits with the child's code (uv docs, "Running commands in projects", "Signal handling"; `crates/uv-command-support/src/child.rs`, `run_to_completion`; the image's uv is 0.13.9, `Dockerfile:52`). It signals the child, not the process group, so the game gets no SIGTERM from Docker or `uv`. So the `CMD` needs no `exec` or init process for the signal to reach uvicorn; 22.7's Run C confirms it (next bullet).
- **The compose files.** `docker-compose.yaml` (`:5-36`) and `docker-compose.dev.yaml` (`:4-28`) set no `init`, no `stop_signal` and no `stop_grace_period`: Docker's defaults apply (SIGTERM, then SIGKILL after 10 s). Both bind-mount `./data:/data` (`:15`, `:15`), which is why the throwaway run never uses compose. Neither is changed by this story (ADR-16 decision 6).
- **What Story 22.7's Run C saw** (`22-7-restart-required-settings-survive-a-live-change.md`, Dev Agent Record "Throwaway-container results", Run C): after `docker restart`, the old API logged `scheduler_stopped` and `api_shutting_down` (13:29:45.88, within a second): SIGTERM reaches uvicorn through `uv`, and uvicorn's lifespan shutdown runs in the image. The game's `server-main.log` ends at the last console command with no SIGTERM, save or shutdown line: it was killed when PID 1 exited. Task 4 checks the process tree and repeats the observation with the fix.
- **The lifespan** (`main.py:153-239`, `lifespan_for`): start-up up to `register_default_jobs` (`:225`), `yield` (`:227`); shutdown: `scheduler_service.shutdown(wait=True)` (`:229-231`), `await close_mod_service()` (`:233-236`), `logger.info("api_shutting_down")` (`:237`). Nothing stops the game. The 22.7 start-up step is the model for the new step: imported at module level (`:43`), called inside a `try`/`except Exception` that logs an ERROR with `error_type` (`:185-190`), replaced in every lifespan test by an autouse conftest recorder.
- **The scheduler shutdown does not wait for running jobs.** `SchedulerService.shutdown(wait)` (`services/scheduler.py:79-91`) calls `AsyncIOScheduler.shutdown(wait)` and logs `scheduler_stopped`. With the `AsyncIOExecutor` (`:58-66`), APScheduler 3.11.3's `AsyncIOExecutor.shutdown` (`api/.venv/lib/python3.14/site-packages/apscheduler/executors/asyncio.py:23-29`) cancels the future of every running job and returns at once ("There is no way to honor wait=True"). A `CancelledError` is a `BaseException`, so `_stop_server_locked`'s `except Exception` (`services/server.py:1282-1285`) and `safe_job`'s `except Exception` (`jobs/base.py`, wrapper) do not catch it: a scheduled restart cancelled during its stop leaves the state `STOPPING`; cancelled while the spawn is awaited (`:1158`) it can lose the new process's handle. Hence ADR-16 decision 3: stop the game first, through the lock, while the scheduler still runs.
- **The normal stop.** `stop_server(timeout=10.0)` (`services/server.py:1205-1218`) takes `_lifecycle_lock` (`:212`) and calls `_stop_server_locked(timeout)` (`:1220-1285`): `SERVER_NOT_INSTALLED` / `SERVER_NOT_RUNNING` checks (`:1227-1233`); `stopping_server pid timeout` (`:1235`); `STOPPING` (`:1237`); SIGTERM (`:1241`); `wait_for(wait(), timeout)` (`:1244`) and `server_stopped_gracefully` (`:1245-1248`), or `server_stop_timeout`, kill, wait, `server_killed` (`:1249-1257`); exit code, `INSTALLED`, start time cleared (`:1259-1261`); Story 22.7's write-back `self._reapply_pending_config_edits("exit")` (`:1264`); `_cancel_background_tasks()`, player reset, mod service told (`:1266-1273`); any `Exception` -> `server_stop_failed`, `_settle_state_after_failed_stop`, `RuntimeError(SERVER_STOP_FAILED)` (`:1282-1285`). Story 22.3 measured SIGTERM to exit at 0.73 s to 0.85 s with `World saved! ...` before `Stopped the server!` (ADR-8, "Results (Story 22.3)").
- **The start.** `start_server()` (`:1070-1086`) takes the lock, calls `_start_server_locked()` (`:1088-1203`), then clears the pending-restart flag and re-flags unapplied edits. `_start_server_locked` checks, in order: not installed (`:1094-1097`), version not supported (`:1099-1106`), `already_running` (`:1108-1110`), `already_starting` (`:1112-1114`); then the template step (`:1117-1119`), the command, `STARTING` (`:1142`), the 22.7 write-back and the spawn inside `try` (`:1149-1199`); `except Exception` -> `INSTALLED`, `server_start_failed`, `RuntimeError(SERVER_START_FAILED)` (`:1200-1203`). Every start (Start button, auto-start, Restart button, scheduled restart) goes through it (ADR-15 context).
- **The restart.** `restart_server(timeout=10.0)` (`:1315-1328`) takes the lock; `_restart_server_locked` (`:1330-1361`) stops if a process lives (`:1342-1345`), then `await self._start_server_locked()` (`:1349`), then clears and re-flags.
- **The scheduled restart** (`jobs/scheduled_restart.py`): `run_restart_sequence` (`:92-144`) checks `still_scheduled()` and `server.game_running` before each warning (`:110-121`) and sleeps between them; at the restart it checks `still_scheduled()`, `server.lifecycle_busy`, `server.game_running` (`:126-131`) and calls `await server.restart_server()` (`:138`) with no `await` in between; a `RuntimeError` -> `scheduled_restart_failed error_code` at ERROR, returns `"failed"` (`:139-142`). The job function (`:147-157`) is wrapped by `safe_job`. `game_running` is `state == RUNNING` (`services/server.py:264-267`); `lifecycle_busy` is either lock held (`:269-272`). A free `asyncio.Lock` is acquired without yielding, so a sequence that passed its checks holds the lock before anything else can run.
- **The disk cleanup and the other jobs** (`jobs/__init__.py`, `jobs/disk_cleanup.py`, the refresh and metrics jobs) never start or stop the game.
- **The monitor** (`_monitor_process`, `:1363-1399`): during a stop (`STOPPING`) it leaves the exit to the stop path (`:1379`); it is cancelled and awaited by `_cancel_background_tasks()`.
- **The singleton.** `_server_service: ServerService | None = None` (`:55`); `get_server_service()` (`:58-67`) builds it on first use with `Settings()`. The game can only run through the singleton (every route and the lifespan use it), so `_server_service is None` means no game process.
- **uvicorn 0.54** (`api/.venv/lib/python3.14/site-packages/uvicorn/server.py:281-311`): on the first SIGTERM it closes the listening sockets, asks every connection to shut down (a WebSocket gets close code 1012), waits for connections and tasks with `timeout_graceful_shutdown` (unset in the `CMD`, so no limit), then runs the lifespan shutdown unless a second signal set `force_exit`. So no HTTP request is in flight and none can arrive while the lifespan shutdown runs. The console WebSocket waits in `receive_text()` (`routers/console.py:371`) and ends on `WebSocketDisconnect` (`:415`); the logs WebSocket polls `receive_text()` every second (`:569`, `:627`). **The wait is for every in-flight request, not only long-lived connections:** `_wait_tasks_to_complete` (`:313-329`) waits for each request's ASGI task, which includes Starlette background tasks run after the response, so a server install (`routers/server.py:122`, `background_tasks.add_task(service.install_server, ...)`; its HTTP client's timeout is 300 s, `services/server.py:382`), a mod download (`services/mod_api.py:367`, `DOWNLOAD_TIMEOUT = 120.0`) or a Stop/Restart request awaiting the lifecycle (`routers/server.py:284`, `:342`) in flight at SIGTERM holds the lifespan shutdown back. With no limit, Docker's SIGKILL at 10 s wins and the game dies without a save while the shutdown stop has not even begun. Hence Task 3: `--timeout-graceful-shutdown 1` in the `CMD` (an `int` option of uvicorn's CLI; on the timeout uvicorn logs `Cancel N running task(s), timeout graceful shutdown exceeded` at ERROR, cancels them, and still runs the lifespan shutdown, `:301-311`).
- **Errors.** `ErrorCode.SERVER_NOT_RUNNING`, `SERVER_START_FAILED`, `SERVER_STOP_FAILED` (`models/errors.py:16`, `:20`, `:21`).

### The shutdown stop (Task 1)

In `services/server.py`:

- **Constant** next to the other module constants: `SHUTDOWN_STOP_TIMEOUT_SECONDS = 8.0` with a comment: inside Docker's default 10-second stop grace, leaving about 2 s for uvicorn before and the scheduler and mod service after (Epic 22 ADR-16 decision 5). The 10 s defaults of `stop_server` and `restart_server` are not changed.
- **`__init__`:** `self._shutting_down = False`, with a comment (set by `stop_for_api_shutdown`, never cleared; Story 22.8).
- **The refusal** in `_start_server_locked`, after the `already_starting` check (`:1112-1114`) and before the template step (`:1116`), in the style of the other checks:

  ```python
  if self._shutting_down:
      logger.warning("start_server_failed", reason="api_shutting_down")
      raise RuntimeError(ErrorCode.SERVER_START_FAILED)
  ```

  It is before `STARTING`, the template step and the 22.7 write-back, so a refused start changes no state and writes no file. `start_server` then does not clear the pending-restart flag (it raised), and `_restart_server_locked` raises after its stop (the stop has saved the world). The routes cannot reach it during a shutdown (uvicorn has drained requests first); it exists for a scheduled restart that holds the lock and for any path not foreseen (ADR-16 decision 4).
- **`async def stop_for_api_shutdown(self, timeout: float = SHUTDOWN_STOP_TIMEOUT_SECONDS) -> None`** (public, after `restart_server`):
  1. `self._shutting_down = True` (before taking the lock, so a restart holding it is refused at its start).
  2. `async with self._lifecycle_lock:` (waits for a restart, stop or start in progress; asyncio's lock is FIFO).
  3. If `self.game_server_pid is None`: `logger.debug("api_shutdown_game_not_running")`; return.
  4. `logger.info("api_shutdown_stopping_game", timeout=timeout)`; `started = time.monotonic()`.
  5. `await self._stop_server_locked(timeout)` in `try`; `except RuntimeError as e:` -> `logger.error("api_shutdown_game_stop_failed", error_code=str(e))` and return (`_stop_server_locked` has already logged `server_stop_failed` and settled the state). Only `RuntimeError` is caught here: `_stop_server_locked` turns every `Exception` into one; anything else propagates to the lifespan's guard.
  6. `logger.info("api_shutdown_game_stopped", seconds=round(time.monotonic() - started, 2))`.
  It never raises for a failed stop and never starts anything. `time` is already imported (`time.time()` at the start).
- **Module-level `async def stop_game_server_for_api_shutdown() -> None`** next to `reapply_pending_config_edits_at_api_start` (`:70-75`): `if _server_service is None: return` (no game can be running, and nothing is built at shutdown: no `Settings()` read, no state file); otherwise `await _server_service.stop_for_api_shutdown()`. Docstring: Story 22.8, Epic 22 ADR-16 decisions 1 to 4. It reads the module global; it does not call `get_server_service()`.

### The lifespan (Task 2)

`main.py`, after `yield` (`:227`), replacing the comment at `:229`:

```python
yield

# Stop a running game through its normal stop first, so its world is saved, while the
# scheduler still runs: its shutdown cancels running jobs without waiting (Story 22.8,
# Epic 22 ADR-16 decisions 1 and 3). The API always finishes shutting down
try:
    await stop_game_server_for_api_shutdown()
except Exception as e:
    logger.error("api_shutdown_game_stop_failed", error_type=type(e).__name__)

# Then the scheduler (before other cleanup)
if scheduler_service:
    scheduler_service.shutdown(wait=True)
```

- Import `stop_game_server_for_api_shutdown` in the existing `from vintagestory_api.services.server import ...` line (`:43`), so `tests/conftest.py` can replace it on `main_module`.
- Nothing else in the lifespan changes: `close_mod_service()` and `api_shutting_down` stay after the scheduler.
- `except Exception` does not catch `CancelledError`; if the lifespan task itself is cancelled the shutdown is being torn down anyway (not a case uvicorn produces on SIGTERM).

### What is logged

| Event | Level | Fields | When |
|---|---|---|---|
| `api_shutdown_stopping_game` | INFO | `timeout` | a game process lives at shutdown, before its stop |
| `stopping_server`, `server_stopped_gracefully` or `server_stop_timeout` + `server_killed` | as today | as today (`timeout` is 8.0) | the normal stop's own lines |
| `pending_config_edits_reapplied` | INFO | `keys`, `trigger=exit` | Story 22.7, when the stop's write-back changed the file |
| `api_shutdown_game_stopped` | INFO | `seconds` (2 decimals) | after the stop, graceful or killed |
| `api_shutdown_game_not_running` | DEBUG | none | no game process at shutdown |
| `api_shutdown_game_stop_failed` | ERROR | `error_code` (from `stop_for_api_shutdown`) or `error_type` (from the lifespan's guard) | the stop failed |
| `start_server_failed` | WARNING | `reason=api_shutting_down` | a start after the shutdown began |
| `scheduler_stopped`, `api_shutting_down` | INFO | as today | after the above |

No path, key, address or value is logged. `stopping_server` keeps its `pid` field as today.

### Test safety (Task 2)

- `just test-api` runs with `VS_DATA_DIR=../dev` (`Justfile:36`). The new step reads only the module global `_server_service`; in a test run that global can hold a singleton another test built with `Settings()` (`dev/`), possibly with a stubbed or real process. A lifespan test must never stop it, write its `serverconfig.json` or its state file.
- `api/tests/conftest.py` gains an autouse fixture after `reapply_at_api_start_recorder` (`:90-120`), in the same style: a small recorder class `StopGameAtShutdownRecorder` (`calls: list[str]`, `error: Exception | None`; `async def __call__(self) -> None` appends `"stop_game_server_for_api_shutdown"` and raises `error` when set) installed with `monkeypatch.setattr(main_module, "stop_game_server_for_api_shutdown", recorder)`, with a docstring saying why. Tests of the real step put the real function back on `main_module` with `monkeypatch.setattr` and set `server_module._server_service` with `monkeypatch.setattr(server_module, "_server_service", service)` to a temp-dir service.
- Every new `ServerService` is built on `installed_settings` (`tests/server/conftest.py:99`) or `Settings(data_dir=tmp_path / ...)`; no new test calls `Settings()` without `data_dir` or `get_server_service()` unpatched. `git status --short dev/ data/` stays empty (Tasks 2.4, 6.1).
- The existing lifespan tests (`tests/test_main.py`, `TestLifespanAutoStart` `:295-857` and the others) keep passing unchanged: the recorder replaces the new step, and their `MagicMock` scheduler's `shutdown` is still called.

### API tests

Red first in each task. Log assertions with `structlog.testing.capture_logs()` (it records every level, so the DEBUG line can be asserted). Private module names only through `monkeypatch.setattr`; no `cast`, no `# pyright:` line in the new file.

**Task 1, `api/tests/server/test_api_shutdown_stop.py`** (new; `installed_settings` with a `serverconfig.json` holding `{"Port": 42420, "ServerName": "x"}`; reuse Story 22.7's typed fakes and helpers by relative import, as `tests/server/test_install_endpoints.py:25` imports from `test_install`: `from .test_pending_config_edits_lifecycle import FakeGameProcess, Spawner, events, game_writes, port_in, run_until`; define this file's own autouse fixture with the three lines of 22.7's `no_real_mod_service` (`test_pending_config_edits_lifecycle.py`, fixture of that name): a fresh `services.mods._restart_state`, a `MagicMock` `services.mods._mod_service`, `routers.health.get_disk_space_data` returning `None`; and its own `config_path` and `spawner` fixtures, copied from 22.7's file (a few lines each): pytest fixtures are found by module attribute, and importing them by name would leave Pyright-unused imports and parameters that shadow them, so do not import them; the game is started with `service.start_server()` and the `spawner` fixture's fake, so no private state is set by hand):

- running game -> `await service.stop_for_api_shutdown()`: the fake got SIGTERM and exited, the state is `INSTALLED` (`get_server_status().state`), and the log events in order are `api_shutdown_stopping_game` (`timeout == 8.0`), `stopping_server` (`timeout == 8.0`), `server_stopped_gracefully`, `api_shutdown_game_stopped` (a `float` `seconds`) (AC 1);
- `SHUTDOWN_STOP_TIMEOUT_SECONDS == 8.0`, and the method's default uses it (the `stopping_server` line above);
- a game that ignores SIGTERM (`spawner.ignore_sigterm = True`) with `stop_for_api_shutdown(timeout=0.01)` -> killed: `server_stop_timeout`, `server_killed`, then `api_shutdown_game_stopped`; no raise; `INSTALLED` (AC 3);
- no game started -> no `api_shutdown_stopping_game`, no `stopping_server`, one `api_shutdown_game_not_running`; no raise (AC 2);
- a game that exited by itself before the shutdown (`process.exit(1)`, then `run_until` the state is `INSTALLED`) -> the same as no game; the process got no signal (AC 2);
- after `stop_for_api_shutdown()`, with a pending `Port` edit (`record("Port", 42421)`) and the file put back to 42420 (`game_writes(config_path, 42420)`) so that a start's write-back would change it: `start_server()` raises `RuntimeError` whose message is `ErrorCode.SERVER_START_FAILED`, logs `start_server_failed reason=api_shutting_down`, logs no `server_start_failed` (the refusal is before the `try`) and no `pending_config_edits_reapplied trigger=start`, spawns nothing (`len(spawner.processes)` unchanged), the state stays `INSTALLED`, and `port_in(config_path) == 42420` (the refusal is before the 22.7 write-back) (AC 4);
- a restart holding the lock: the running fake's `on_signal` records the signal and does not exit; start `restart = asyncio.create_task(service.restart_server())`, `run_until(lambda: service.lifecycle_busy and <SIGTERM recorded>)`; start `shutdown = asyncio.create_task(service.stop_for_api_shutdown())`; let the loop run; then `process.exit(0)`; await both with `asyncio.gather(..., return_exceptions=True)`: the restart's result is a `RuntimeError` (`SERVER_START_FAILED`), `start_server_failed reason=api_shutting_down` was logged, one process was ever spawned, the shutdown logged `api_shutdown_game_not_running` (the restart's stop had ended the game), the state is `INSTALLED` (AC 4);
- a sequence in its warnings: the real running service, `run_restart_sequence("04:00", server=service, still_scheduled=lambda: True, sleep=<a sleep that awaits an asyncio.Event>)` as a task; `run_until` one `/announce` has been written to the fake's stdin; `await service.stop_for_api_shutdown()`; set the event: the sequence returns `"not_running"`, no second process was spawned, `scheduled_restart_skipped reason=not_running` was logged (AC 4);
- Story 22.7's write-back: `service.pending_config_edits.record("Port", 42421)` while running, `game_writes(config_path, 42420)`, `stop_for_api_shutdown()` -> `port_in(config_path) == 42421`, `pending_config_edits_reapplied trigger=exit` before `api_shutdown_game_stopped`; the edit is still pending (only a start drops it) (AC 6);
- a stop that fails: `monkeypatch.setattr(service, "_stop_server_locked", <async fn raising RuntimeError(ErrorCode.SERVER_STOP_FAILED)>)` -> `api_shutdown_game_stop_failed error_code=SERVER_STOP_FAILED` at ERROR, no `api_shutdown_game_stopped`, no raise (AC 5). (If Pyright objects to replacing a method on an instance, use a small `ServerService` subclass in the test that overrides `_stop_server_locked`; `reportPrivateUsage` does not flag a subclass override.)
- module function: with `monkeypatch.setattr(server_module, "_server_service", None)` and `monkeypatch.setattr(server_module, "ServerService", <a callable that fails the test>)`, `await stop_game_server_for_api_shutdown()` returns and builds nothing (AC 2); with `_server_service` set to the running temp-dir service, it stops the game (`INSTALLED`, `api_shutdown_stopping_game` logged with `timeout == 8.0`, so the shutdown uses the 8 s default) (AC 1, 3).

**Task 2, `api/tests/test_main.py` new class `TestLifespanShutdownStopsTheGame`** (the same patches as `run_auto_start_lifespan`, `:298-337`, with auto-start off; one shared `calls` list: the autouse `stop_game_at_shutdown_recorder` appends its name, `scheduler.shutdown.side_effect` appends `"scheduler_shutdown"`, the `close_mod_service` `AsyncMock`'s `side_effect` appends `"close_mod_service"`):

- the order on leaving the lifespan is `stop_game_server_for_api_shutdown`, `scheduler_shutdown`, `close_mod_service`, and the step runs once (AC 1);
- with `recorder.error = RuntimeError("boom")`: ERROR `api_shutdown_game_stop_failed error_type=RuntimeError`, then `scheduler_shutdown` and `close_mod_service` still run, and `api_shutting_down` is logged (AC 5);

**Task 2, `api/tests/server/test_api_shutdown_stop.py` new class `TestLifespanRunsTheShutdownStop`** (in Task 1's file, where the fakes are already imported, as Story 22.7 put its auto-start-through-the-lifespan row in its lifecycle file; `lifespan_for(installed_settings)` with the patches of `run_auto_start_lifespan` for the scheduler, `register_default_jobs` and `close_mod_service`, auto-start off, and the real `stop_game_server_for_api_shutdown` put back on `main_module` with `monkeypatch.setattr` over the autouse recorder):

- `monkeypatch.setattr(server_module, "_server_service", service)` with a running temp-dir `ServerService`: after `async with lifespan_for(...)(FastAPI())` exits, the game got SIGTERM, the state is `INSTALLED`, and in the captured events `api_shutdown_stopping_game` and `api_shutdown_game_stopped` come before `api_shutting_down`, and the scheduler mock's `shutdown` was called after the stop (record both in one list) (AC 1);
- `_server_service` `None` and `ServerService` replaced by a callable that fails the test -> nothing is built and the shutdown completes with `api_shutting_down` (AC 2).

### The throwaway-container run (Task 4)

Run from the repo root after Task 3's commit; placeholder keys only (never `.env`'s); never the dev stack. The isolation is Story 22.7's (Dev Notes "The throwaway-container run" of `22-7-restart-required-settings-survive-a-live-change.md`): plain `docker build`/`docker run`, never `docker compose` (both compose files bind-mount `./data:/data`; `docker-compose.dev.yaml` is the dev stack on 9080 with game port 42420); no `-v`, `--mount` or `--env-file`, so `/data` lives in the container's writable layer, survives `docker stop`/`docker start` and `docker restart` of the same container and goes with `docker rm -f`; own names (`vss-22-8-*`), own port `127.0.0.1:18096` (not 9080, not e2e-ci's 18080/18081, not 22.3's 18090, 22.4's 18092 or 22.7's 18094), own image tag; not `just test-e2e-ci` (it blocks the game download hosts). Helper scripts and copied logs go in the session scratchpad, never in the repository.

```bash
IMAGE=vss-22-8-stop:local; NAME=vss-22-8-stop; BASE=http://127.0.0.1:18096
KEY=vss-22-8-placeholder-admin-key; H=(-H "X-API-Key: $KEY" -H "Content-Type: application/json")
docker rm -f "$NAME" >/dev/null 2>&1 || true   # leftovers of a killed run
docker build --platform linux/amd64 -t "$IMAGE" .
docker run -d --name "$NAME" --platform linux/amd64 -p 127.0.0.1:18096:8080 \
  -e VS_API_KEY_ADMIN="$KEY" -e VS_DATA_DIR=/data "$IMAGE"
# wait for $BASE/healthz, then:
curl -s "${H[@]}" -X POST "$BASE/api/v1alpha1/server/install" -d '{"version":"stable"}'
# poll GET /api/v1alpha1/server/install/status until installed; record the resolved version
read_cfg() { docker exec "$NAME" python3 -c "import json; c=json.load(open('/data/serverdata/serverconfig.json')); print(c.get('Port'), c.get('ServerName'))"; }
game_log_tail() { mkdir -p "$SCRATCH/logs" && docker cp "$NAME:/data/serverdata/Logs/server-main.log" "$SCRATCH/logs/$1.log" && tail -n 8 "$SCRATCH/logs/$1.log"; }   # works on a stopped container
ps_tree() { docker exec "$NAME" sh -c 'for p in /proc/[0-9]*; do n=${p#/proc/}; printf "%s ppid=%s %s\n" "$n" "$(awk "/^PPid/{print \$2}" $p/status)" "$(tr "\0" " " < $p/cmdline | cut -c1-90)"; done'; }
```

- **Starting and waiting for ready:** auto-start is off (default), so after each `docker start`/`docker restart` the game is started with `POST /api/v1alpha1/server/start`. Wait for a new `now running on Port` line in `docker exec "$NAME" cat /data/serverdata/Logs/server-main.log` that differs from the last one before the start (the game archives the old log at each start; 22.4, 22.7), then wait at least 60 s so the world is loaded and a save has something to do.
- **Timing a stop:** `t0=$(date +%s.%N)`; the Docker command; `t1=...`; record `t1 - t0`, `docker inspect -f '{{.State.ExitCode}}' "$NAME"` (0 = the API exited by itself; 137 = Docker killed it), and `docker logs --since <t0 as RFC 3339> "$NAME" 2>&1 | grep -E 'api_shutdown_|stopping_server|server_stopped_gracefully|server_stop_timeout|server_killed|pending_config_edits_reapplied|scheduler_stopped|api_shutting_down'` with the timestamps. Then `game_log_tail <run>` for the game's last lines (expect `World saved! ...` before `Stopped the server!`, as 22.3 measured; record them as they are, without addresses).
- **Process tree (once, game running, before Run A):** `ps_tree`. Expect PID 1 `uv run --no-sync uvicorn ... --timeout-graceful-shutdown 1`, a python uvicorn process whose ppid is 1, and `dotnet .../VintagestoryServer.dll` whose ppid is the uvicorn process. Record what is there.
- **Run A (`docker stop`, AC 1, 6, 7):** game running (ready, 60 s). `POST /config/game/settings/Port {"value": 42421}` (expect `file_update`, `pending_restart: true`); `POST /config/game/settings/ServerName {"value": "vss-22-8 run a"}` (`console_command`); wait 5 s; `read_cfg` (expect `42420`: the game wrote, as in 22.3 and 22.7). `docker stop "$NAME"` timed. Record the API lines (expect AC 1's order with `pending_config_edits_reapplied trigger=exit` before `api_shutdown_game_stopped`), the exit code (expect 0), the game's last lines, the stop's duration (expect a few seconds, well under 10). `docker start "$NAME"`; `read_cfg` (expect 42421, and no `trigger=api_start` line, since the file already holds it).
- **Run B (`docker restart` with an open console WebSocket, AC 7):** start the game (it runs on 42421), ready, 60 s. Open a console WebSocket from inside the container with the image's own Python (the `websockets` package is installed with uvicorn's standard extras; `/app/.venv/bin/python`): write a short client in the scratchpad that connects to `ws://127.0.0.1:8080/api/v1alpha1/console/ws?api_key=<KEY>` (`routers/console.py:262-300`; the legacy key parameter is fine for a placeholder key), appends each message and the close code, with a timestamp, to a file under `/tmp` in the container, and stays open until the server closes it; `docker cp` it to `/tmp` in the container and run it with `docker exec -d "$NAME" /app/.venv/bin/python /tmp/<client>.py`. Check `websocket_connected` in `docker logs`. `docker restart "$NAME"` timed. Record uvicorn's own lines (`Shutting down`, `Waiting for connections to close`, `Cancel N running task(s), timeout graceful shutdown exceeded`, if any; the console WebSocket is expected to close at once, so no cancel line), `websocket_disconnected`, the API lines and their order, the game's last lines, the duration (expect a few seconds), the restart's success (`/healthz` up again).
- **Run C (`docker stop -t 30`, AC 7):** start, ready, 60 s; `docker stop -t 30 "$NAME"` timed. Expect the same lines and a duration close to Run A's, not 30 s: the manager exits as soon as the game has stopped. Exit code 0. `docker start "$NAME"`.
- **Run D (`docker stop -t 2`, AC 7, recorded only):** start, ready, 60 s; `docker stop -t 2 "$NAME"` timed. Record the duration, the exit code, which API lines appear and whether the game's log shows the save. Docker kills everything 2 s after SIGTERM; the save is measured at under 1 s, so it may still complete. Do not guess the outcome in advance; the README's advice (Task 5) does not depend on it.
- **Clean up even after a failure:** `docker rm -f "$NAME"; docker image rm "$IMAGE"`; then `docker ps -a --filter name=vss-22-8` and `docker image ls vss-22-8-stop` are empty; record `uname -m` (an arm64 host runs the image emulated) and `docker version --format '{{.Server.Version}}'`.
- The game port is not published, so nothing clashes with the dev stack's 42420.

### Documentation (Task 5)

`README.md`, a new section between `### Upgrading` (ends `:56`) and `### Verifying an image` (`:58`), in the README's plain style:

> ### Stopping and restarting the container
>
> When the container is stopped or restarted (`docker stop`, `docker restart`, `docker compose down`, or `docker compose up -d` with a new image), the manager first stops a running game server the normal way, so the game saves the world, and then exits. It gives open requests up to 1 second to finish, then waits up to 8 seconds for the game to stop (a save usually takes about a second) and then ends it. Docker gives a container 10 seconds by default before it kills it, which is enough: do not make it shorter (`docker stop -t`, `stop_grace_period` in a compose file). On Kubernetes, keep `terminationGracePeriodSeconds` at 10 or more (the default is 30). A shorter grace period, `docker kill`, or a crash or power loss of the host can still lose what changed since the game's last autosave. Whether the game server starts again with the container depends on the auto-start setting.

Adjust the wording if Task 2's code or Task 4's run says otherwise (for example, if Run A's stop took longer than a few seconds); every sentence must be true. The auto-start setting is the API setting `auto_start_server` (`services/api_settings.py`); name it so only if the README names API settings that way elsewhere.

### Not changed (do not "fix" these here)

- The `Dockerfile` beyond Task 3's one `CMD` flag (still `uv run`, no `exec`, no `ENTRYPOINT`, no init process, the same `USER`), `docker-compose.yaml` and `docker-compose.dev.yaml` (ADR-16 decision 6; no `stop_grace_period`, no `init`). If Task 4 shows the lifespan shutdown does not run or the game cannot save inside the default grace, that is the stop rule (4.5), not a change made here.
- `just dev-api` (`Justfile:245`): no `--timeout-graceful-shutdown`; it is not the container and its Ctrl-C path is not Docker's.
- The 10 s defaults of `stop_server` and `restart_server` and the Stop and Restart buttons; the stop path itself (`_stop_server_locked`); `services/scheduler.py` (its `shutdown(wait=True)` is still called and still does not wait); `jobs/` (a scheduled restart refused at its start logs `scheduled_restart_failed error_code=SERVER_START_FAILED` at ERROR, as any failed restart does; see "ADR against the code" 3); Story 22.7's store and write-back; every route, model, response and status code; the web.
- `ServerService.close()` (the HTTP client) is still not called at shutdown; the process exits.
- Crash auto-restart: none exists, none is added.

### API contract changes

None. No route, field, status code or setting changes. The visible change is in the logs (the new lines above) and in what a container stop does to the game.

### ADR against the code

1. **The "no start" flag is set before the lock is taken** (ADR-16 decision 4 says "first"): otherwise a restart that holds the lock would complete its start while the shutdown waits for the lock, and the shutdown would then stop a game it had just let start (two saves and a start for nothing, inside the 8 s budget). Set first, the restart's stop saves the world and its start is refused.
2. **The shutdown's lock wait is not bounded.** A restart holding the lock at shutdown finishes its own stop (10 s timeout, measured under 1 s) before the shutdown step runs; with the start refused it adds about a second. Bounding the wait would mean cancelling a stop inside the lock, which decision 3 avoids. Accepted; Task 4 does not exercise it (the unit test does).
3. **A refused scheduled restart logs at ERROR.** `run_restart_sequence` reports a `RuntimeError` from `restart_server()` as `scheduled_restart_failed` (`jobs/scheduled_restart.py:139-142`). At a shutdown that coincides with a restart this gives one ERROR line with `error_code=SERVER_START_FAILED` after the WARNING `start_server_failed reason=api_shutting_down`. Changing `jobs/` to tell the two apart is not worth it for a moment that rare; recorded here.
4. **`api_shutdown_game_stop_failed` has two field sets.** From `stop_for_api_shutdown` it carries `error_code` (the stop's `RuntimeError`); from the lifespan's guard it carries `error_type` (anything else). Same event, so one log query finds both.
5. **Line references.** Every file:line reference in ADR-16 holds at da55999b; the APScheduler and uvicorn references are to the installed packages (`api/uv.lock`: APScheduler 3.11.3, uvicorn 0.54.0) and move with an upgrade.
6. **`--timeout-graceful-shutdown 1` in the `CMD` (Task 3, added at validation).** ADR-16 decision 9 kept it back as a fallback for a failed throwaway run, and its Consequences named only long-lived connections as the risk. But uvicorn waits, with no limit, for every in-flight request and its background tasks before the lifespan shutdown (Dev Notes "The code today", uvicorn bullet): a server install, a mod download (120 s timeout) or a Stop/Restart request at SIGTERM would let Docker's SIGKILL win before the game's stop starts, which no throwaway run here would catch. 1 s (uvicorn takes whole seconds) plus its 0.1 s pause, the 8 s stop and the scheduler and mod service close fits Docker's 10 s. The cost: a request still running after 1 s is cancelled. A cancelled Stop or Restart request can leave the state `STOPPING` with the game already sent SIGTERM (it saves on its own; the shutdown stop then signals it again and waits, or finds it gone), or lose a just-spawned process's handle (a game that had not loaded its world). The `_shutting_down` flag is not set yet at that point (the lifespan shutdown has not begun). The `CMD` keeps `uv run` (it forwards SIGTERM; Dev Notes "The image"), so no `exec` or init is needed. Task 4.4's ADR-16 paragraph records the change.

### Open questions for the maintainer (none blocks the start)

1. **Should a longer grace be recommended or shipped?** ADR-16 decisions 5 and 6 keep Docker's 10 s and the 8 s stop, README only. If Task 4's Run A takes longer than about 5 s under emulation, or a large world is expected to save slower, the maintainer may prefer `stop_grace_period: 30s` in the shipped compose file and a longer shutdown timeout; that is a user-facing compose change and is not made here.
2. **Run D (`docker stop -t 2`)** is recorded, not judged; if it shows the save completing, the README still recommends 10 s or more.
3. **The 1-second drain limit (Task 3).** uvicorn takes whole seconds, and 0 would cancel every open request at once; longer eats into the 8 s stop's room in the 10 s grace. If the maintainer prefers 2 s, the stop timeout would drop to 7 s to keep the budget; neither is changed without his word.

### Testing Requirements

**CRITICAL:** tests are written with each task and committed with it, red first. `just test-api <files>` after each task; `just check` before review.

- No lint or type suppression (`# type: ignore`, `# pyright: ignore`, `noqa`), no `cast`, no `as`-style escape (`typing.cast`, `Any`-typed stand-ins for typed parameters), no skipped test (`pytest.mark.skip`, `skipif`, `xfail`, `pytest.skip`), no `.only`. Pyright 0 errors and 0 warnings in `src` and `tests`. The file-level `# pyright:` lines in `tests/server/conftest.py` are not copied into the new test file.
- Every test on `tmp_path`/`installed_settings`; no test reads or writes `dev/` or `./data` (`git status --short dev/ data/` empty); the conftest recorder is in place before any lifespan test runs the new step.
- Never run `just test-e2e-api`, `just test-e2e` or `just test-e2e-web` (they target the dev stack); never `just docker ...`. No E2E test is added: the behaviour needs a game process and a container stop, which Task 4 covers. Docker only for Task 4's `vss-22-8-stop` container.

### Security Requirements

- No new route; nothing new is reachable from outside. The new log lines carry no path, key, address or value.
- The throwaway container uses a placeholder key, binds only `127.0.0.1:18096`, and is removed with its image; nothing from it is committed except log event names, timings, exit codes and game lines without addresses. The WebSocket client passes the placeholder key only.

### Development Commands

- `just test-api tests/server/test_api_shutdown_stop.py tests/server tests/test_main.py tests/test_scheduled_restart.py tests/test_shared_pending_restart.py`, `just typecheck-api`, `just lint-api`.
- `cd api && uv run ruff format <changed files>` (`just format-api` takes no file arguments and formats the whole tree).
- `just check` (Task 6), `just changelog` (Task 6.2), `just test-scripts test-docker-context.sh` and `just lint-scripts` (Task 3), `just sprint set 22-8-container-stop-saves-the-world review`.

### Previous Story Intelligence

- **22.7** (this branch's base, in review): found this gap (Run C, drawdown item 1); the conftest autouse recorder pattern for a lifespan step (`ReapplyAtApiStartRecorder`); the typed long-lived `FakeGameProcess` and `Spawner` in `tests/server/test_pending_config_edits_lifecycle.py`; the throwaway-container recipe on 18094, its ready-line wait and its stop rule; its write-back after the exit (`trigger=exit`), which this story's stop runs. Its drawdown item 3 (a shared fake-process helper) is not done here; importing the fakes from 22.7's test module keeps a fourth copy from appearing.
- **22.3:** measured the stop (0.73 s to 0.85 s, save before exit) and built `run_restart_sequence` with an injectable sleep and the `RestartTarget` protocol; the real `ServerService` satisfies it.
- **22.4:** the game moves `server-main.log` into `Logs/Archive/` at each start and keeps at most 5 archives, so a stopped run's log is the live `server-main.log` until the next start (read it before starting again, or from the newest archive after).
- **21.3:** the depth model; completion notes must be true of the code.

### Git Intelligence

- Branch `story/22-8-container-stop-saves-the-world` from `story/22-7-restart-required-settings-survive-a-live-change` at `da55999b` (`chore(story-22.7/task-6): validate and move story 22.7 to review`). 22.7's commits: `a12eb477`, `658631fc` (`refactor`), `c886d3fe` (`fix`), `8ad964f9`, `63bee557`, `da55999b`. Story 22.8 was planned in `4dd719f1` (`docs(epic-22): add story 22.8 for a world save when the container stops`).
- Planned commits: Task 1 `refactor(story-22.8/task-1): add a game server stop for the API's shutdown`; Task 2 `fix(story-22.8/task-2): stop the game server, saving the world, when the container stops or restarts`; Task 3 `build(story-22.8/task-3): limit uvicorn's wait for open requests at shutdown to 1 second`; Task 4 `docs(story-22.8/task-4): record a container stop saving the world in a throwaway container`; Task 5 `docs(story-22.8/task-5): explain what stopping the container does to the game server`; Task 6 `chore(story-22.8/task-6): validate and move story 22.8 to review`. Exactly one release-note commit: Task 2's `fix`.

### Project Structure Notes

- New: `api/tests/server/test_api_shutdown_stop.py`.
- Modified: `api/src/vintagestory_api/services/server.py` (the constant, the flag, the refusal, the method, the module function), `api/src/vintagestory_api/main.py` (one import, one call, one comment), `api/tests/conftest.py`, `api/tests/test_main.py`, `Dockerfile` (the `CMD` flag, Task 3), `scripts/tests/test-docker-context.sh` (Task 3), `README.md`, ADR-16 (Task 4). `api/tests/server/test_api_shutdown_stop.py` gains a second class in Task 2.
- Naming follows the codebase: snake_case, event names in lower snake case, a module constant in SCREAMING_SNAKE.

### References

- [Source: _bmad-output/planning-artifacts/epics.md] Story 22.8 (`:7794`), Epic 22 order and dependencies
- [Source: _bmad-output/planning-artifacts/prd.md] FR308
- [Source: _bmad-output/planning-artifacts/architecture/epic-22-server-operations-and-metrics.md] ADR-16, ADR-8 "Results (Story 22.3)", ADR-14, ADR-15 "Results (Story 22.7)"
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-18-epic-22.md] answer 13, found-in-epic item 12, section 5 planner decisions
- [Source: _bmad-output/implementation-artifacts/22-7-restart-required-settings-survive-a-live-change.md] Dev Agent Record "Throwaway-container results" (Run C), Completion Notes drawdown item 1, Dev Notes "Test safety" and "The throwaway-container run"
- [Source: _bmad-output/implementation-artifacts/22-3-scheduled-restarts.md] Task 1, the stop measurement
- [Source: project-context.md] Critical Implementation Rules 1, 2, 8; Security Patterns 3; Logging Conventions; Commit Message Format
- uvicorn 0.54 `Server.shutdown`; APScheduler 3.11.3 `AsyncIOExecutor.shutdown` (installed sources under `api/.venv`)

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5), dev-story workflow, non-interactive

### Throwaway-container results

<!-- Task 4.4: host architecture, Docker version, game version, the process tree, a block per run (duration, exit code, API lines with timestamps, the game's last lines), the commands. -->

Run on 2026-11-19 from this branch at `e22886d9` (after Tasks 1 to 3). Host `arm64` (macOS), Docker server 29.9.2; image `vss-22-8-stop:local` built with `docker build --platform linux/amd64` (emulated); container `vss-22-8-stop` from `docker run -d --name vss-22-8-stop --platform linux/amd64 -p 127.0.0.1:18096:8080 -e VS_API_KEY_ADMIN=<placeholder> -e VS_DATA_DIR=/data vss-22-8-stop:local` (no `-v`, `--mount`, `--env-file` or compose; no game port published); `POST /server/install {"version":"stable"}` resolved to game **1.22.7**, fresh world. Helper functions as in Dev Notes "The throwaway-container run" (`read_cfg`, `game_log_tail`, `ps_tree`), plus a wait for a new `now running on Port` line and 60 s before each stop. Durations are `docker stop`/`docker restart`'s wall time on the host.

**Process tree** (game running, before Run A):

```
1  ppid=0  uv run --no-sync uvicorn vintagestory_api.main:app --host 0.0.0.0 --port 8080 --timeout-graceful-shutdown 1
10 ppid=1  /app/.venv/bin/python /app/.venv/bin/uvicorn vintagestory_api.main:app --host 0.0.0.0 --po...
31 ppid=10 dotnet /data/server/VintagestoryServer.dll --dataPath serverdata
```

PID 1's full command line ends in `--timeout-graceful-shutdown 1`. As expected: `uv` PID 1, uvicorn its child, the game uvicorn's child.

**Run A (`docker stop`, default grace 10 s; AC 1, 6, 7).** `POST /config/game/settings/Port {"value": 42421}` -> `file_update`, `pending_restart: true`; `POST .../ServerName {"value": "vss-22-8 run a"}` -> `console_command`; 5 s later `read_cfg` -> `42420 vss-22-8 run a` (the game wrote its own Port back). `docker stop vss-22-8-stop`: **1.29 s**, exit code **143**, `OOMKilled=false`.

```
INFO:     Shutting down
INFO:     Waiting for application shutdown.
14:20:56.702336Z api_shutdown_stopping_game timeout=8.0
14:20:56.703076Z stopping_server pid=31 timeout=8.0
14:20:57.625658Z server_stopped_gracefully returncode=0
14:20:57.626420Z pending_config_edits_reapplied keys=["Port"] trigger=exit
14:20:57.626900Z api_shutdown_game_stopped seconds=0.92
14:20:57.627011Z scheduler_stopped
14:20:57.627166Z api_shutting_down
INFO:     Finished server process [10]
```

Game (`server-main.log`): `14:20:56 [Notification] Server termination event SIGTERM received. Shutting down server`, `... Entering runphase Shutdown`, `Mods and systems notified, now saving everything...`, `Saved player world data...`, `Saved map regions...`, `Saved map chunks...`, `Saved loaded chunks...`, `Saved generating chunks...`, `Saved savegamedata...`, `14:20:56 [Event] World saved! Saved 8 chunks, 1 mapchunks, 16 mapregions.`, then `14:20:57 ... All threads gracefully shut down`, `Doing last tick...`, `Stopped the server!`. After `docker start`: `read_cfg` -> `42421 vss-22-8 run a`; no `pending_config_edits_reapplied` line at the API start (the file already held 42421).

**Run B (`docker restart` with an open console WebSocket; AC 7).** Game started (ready on Port 42421), 60 s. A WebSocket client (scratchpad script, run with the image's `/app/.venv/bin/python` via `docker exec -d`) connected to `ws://127.0.0.1:8080/api/v1alpha1/console/ws?api_key=<placeholder>` (`websocket_connected` at 14:22:43). `docker restart vss-22-8-stop`: **1.27 s**; `/healthz` up again.

```
INFO:     Shutting down
14:22:51.199458Z websocket_disconnected code=1012
INFO:     Waiting for application shutdown.
14:22:51.302672Z api_shutdown_stopping_game timeout=8.0
14:22:51.303640Z stopping_server pid=37 timeout=8.0
14:22:52.147221Z server_stopped_gracefully returncode=0
14:22:52.147893Z api_shutdown_game_stopped seconds=0.84
14:22:52.148468Z scheduler_stopped
14:22:52.148665Z api_shutting_down
INFO:     Finished server process [9]
INFO:     Waiting for application startup.
```

No `Waiting for connections to close` and no `Cancel N running task(s), timeout graceful shutdown exceeded` line: the WebSocket closed at once. The client's file: `14:22:51.203 closed code=1012`. Game: `14:22:51 ... SIGTERM received. Shutting down server`, `14:22:51 [Event] World saved! Saved 0 chunks, 0 mapchunks, 16 mapregions.`, `14:22:52 [Event] Stopped the server!`. The old run's exit code cannot be read after a restart (`docker inspect` shows the new run's state).

**Run C (`docker stop -t 30`; AC 7).** Game started, ready, 60 s. **1.33 s** (not 30 s), exit code **143**.

```
14:24:21.734865Z api_shutdown_stopping_game timeout=8.0
14:24:21.736465Z stopping_server pid=36 timeout=8.0
14:24:22.630853Z server_stopped_gracefully returncode=0
14:24:22.631680Z api_shutdown_game_stopped seconds=0.9
14:24:22.632241Z scheduler_stopped
14:24:22.632507Z api_shutting_down
```

(preceded by uvicorn's `Shutting down`, `Waiting for application shutdown.` and followed by `Finished server process [9]`). Game: `14:24:21 ... SIGTERM received`, `14:24:21 [Event] World saved! Saved 0 chunks, 0 mapchunks, 16 mapregions.`, `14:24:22 [Event] Stopped the server!`.

**Run D (`docker stop -t 2`; recorded, not judged).** `docker start`, game started, ready, 60 s. **1.32 s**, exit code **143**; every line of AC 1's order: `api_shutdown_stopping_game` 14:25:54.167100Z, `stopping_server` .170947Z, `server_stopped_gracefully` 14:25:55.075637Z, `api_shutdown_game_stopped seconds=0.91` .076378Z, `scheduler_stopped` .076939Z, `api_shutting_down` .077242Z. Game: `14:25:54 ... SIGTERM received`, `World saved! Saved 0 chunks, 0 mapchunks, 16 mapregions.`, `Stopped the server!`. The save completed inside the 2 s on this small, fresh world.

**Exit code 143, not the expected 0.** uvicorn 0.54 records the signal it caught (`Server.handle_exit`, `_captured_signals`) and, once its shutdown, including the lifespan shutdown, has finished, re-raises it (`signal.raise_signal`, `uvicorn/server.py:348-349`), so the uvicorn process ends by SIGTERM and `uv` exits with 128 + 15 = 143. Docker did not kill the container (that would be 137; `OOMKilled=false`), every stop ended within 1.33 s of the grace, and `api_shutting_down` and `Finished server process` were logged first. The stop rule (4.5) names 137, so it did not fire; recorded as a difference from the story's expectation (Completion Notes, deviations).

**Stop rule (4.5):** not fired. In Runs A, B and C the lifespan shutdown ran, the game saved before it stopped, the API lines are in AC 1's order, and no exit code was 137.

**Cleanup:** `docker rm -f vss-22-8-stop; docker image rm vss-22-8-stop:local`; afterwards `docker ps -a --filter name=vss-22-8` and `docker image ls vss-22-8-stop` list nothing; `git status --short dev/ data/` is empty. The dev stack was not touched. Copied logs and the WebSocket client stayed in the session scratchpad.

### Debug Log References

- Task 1 red: `just test-api tests/server/test_api_shutdown_stop.py` -> `ImportError: cannot import name 'SHUTDOWN_STOP_TIMEOUT_SECONDS'` at collection (the expected first red); green after 1.2 (12 passed). Pyright then flagged `list[dict[str, object]]` against structlog's `list[EventDict]` in a helper; fixed with `Sequence[Mapping[str, object]]`.
- Task 2 red: every test in `tests/test_main.py` and the new file errored at the autouse fixture (`monkeypatch.setattr(main_module, "stop_game_server_for_api_shutdown", ...)`: no such attribute); green after 2.2. Pyright `reportUnknownLambdaType` on `lambda wait: ...` scheduler side effects; replaced with typed local functions.
- Task 3 red: `just test-scripts test-docker-context.sh` 10/11 (the new `assert_contains` on the `CMD` line); green 11/11 after 3.2.
- Task 4: see "Throwaway-container results"; uvicorn's signal re-raise checked in `api/.venv/lib/python3.14/site-packages/uvicorn/server.py:348-352`.

### Completion Notes List

- 2026-11-19 (dev-story): Tasks 1 to 6 done; 6.3 (the maintainer's manual check) left unticked for him.
- **What changed.** `services/server.py`: `SHUTDOWN_STOP_TIMEOUT_SECONDS = 8.0`; `self._shutting_down` (set by `stop_for_api_shutdown`, never cleared); the refusal in `_start_server_locked` after `already_starting` and before the template step (`start_server_failed reason=api_shutting_down`, `RuntimeError(SERVER_START_FAILED)`); `ServerService.stop_for_api_shutdown(timeout=8.0)` (flag before the lock, then under the lock: `api_shutdown_game_not_running` at DEBUG when no process lives, else `api_shutdown_stopping_game`, `_stop_server_locked`, `api_shutdown_game_stopped seconds`; a `RuntimeError` from the stop -> `api_shutdown_game_stop_failed error_code` at ERROR, no raise); module-level `stop_game_server_for_api_shutdown()` that reads `_server_service` and builds nothing. `main.py`: imported at module level, awaited after `yield` and before the scheduler shutdown in its own `try`/`except Exception` (`api_shutdown_game_stop_failed error_type`); the old "scheduler first" comment now says "Then the scheduler". `tests/conftest.py`: autouse `StopGameAtShutdownRecorder`. `Dockerfile`: `"--timeout-graceful-shutdown", "1"` on the `CMD` with its comment; `scripts/tests/test-docker-context.sh` asserts it. README: "Stopping and restarting the container" between "Upgrading" and "Verifying an image", the Dev Notes wording unchanged (every sentence held in Task 4: stops took 1.27 s to 1.33 s, the game's stop 0.84 s to 0.92 s). ADR-16: decisions 6 and 9 amended for the `CMD` flag ("controller decision during validation (2026-11-19), for the maintainer to review") and a "Results (Story 22.8)" paragraph.
- **Tests.** 16 new API tests: 14 in `tests/server/test_api_shutdown_stop.py` (12 in `TestStopForApiShutdown` and `TestStopGameServerForApiShutdown` for Task 1; 2 in `TestLifespanRunsTheShutdownStop` for Task 2) and 2 in `tests/test_main.py` `TestLifespanShutdownStopsTheGame`; one new script assertion in `test-docker-context.sh`. `just check` green: API 3787 passed, web 3567 passed (137 files), 0 skipped; Pyright 0 errors, 0 warnings; ruff, Prettier, ShellCheck, actionlint green; `just test-scripts` all green. No added line in `api/src` or `api/tests` holds a suppression, `cast(`, skip, `xfail` or `.only`. `git diff da55999b` is empty for `web/`, both compose files, `routers/`, `models/`, `services/scheduler.py`, `jobs/` and `services/pending_config_edits.py`; the `Dockerfile` diff is the `CMD` line and its comment. `git status --short dev/ data/` empty after every run. `just changelog` lists exactly one entry from this story's hashes: `ff3a8ce` (Task 2's fix).
- **Throwaway container (Task 4).** The fix works in the image: every run (A, B, C, D) logged AC 1's lines in order and the game's `World saved! ...` before `Stopped the server!`; each stop took about 1.3 s; the console WebSocket closed with 1012 at once; the stop rule did not fire.
- **Deviations.** (1) **Exit code 143, not the expected 0** (Runs A, C, D): uvicorn 0.54 re-raises the caught SIGTERM after its shutdown, including the lifespan shutdown, has finished, so `uv` exits with 128 + 15. Docker did not kill the container (not 137, the stop rule's trigger); recorded, nothing changed. (2) The `Dockerfile`'s existing comment line gained a final full stop so the new comment reads as a second sentence; no other change. (3) In the new test file `fail_if_built` and the "no service" test assert that nothing was logged (`logs == []`) as the visible sign that nothing was built or stopped, since reading the private `_server_service` back would need a private-usage escape.
- **Drawdown items (not done here, for the maintainer):** (1) The exit code 143 on every clean stop may confuse an operator or a monitor that treats non-zero as a crash; if wanted, a later story could make the API exit 0 after a completed shutdown (for example by running uvicorn programmatically, or a small wrapper), which changes the `CMD` beyond this story's one flag. (2) Task 4 did not exercise `--timeout-graceful-shutdown 1` with a request in flight (an install or a mod download at SIGTERM); a later throwaway run could show the `Cancel N running task(s)` line and the stop still inside the grace. (3) The runs used a fresh, small world (saves of 0 to 8 chunks); a large world's save time inside the 8 s is unmeasured (open question 1).
- 2026-11-19: Story created (create-story, non-interactive) from Epic 22's Story 22.8 entry, ADR-16 and FR308, and checked against the create-story checklist: 5 tasks; every code task carries its tests (Task 3 is a container check, Task 4 documentation, Task 5 validation); every AC is mapped to a task (AC 9 to every code task and Task 5, the maintainer check to Task 5.3). Line references verified at da55999b.

### File List

- `api/src/vintagestory_api/services/server.py` (modified)
- `api/src/vintagestory_api/main.py` (modified)
- `api/tests/server/test_api_shutdown_stop.py` (new)
- `api/tests/conftest.py` (modified)
- `api/tests/test_main.py` (modified)
- `Dockerfile` (modified)
- `scripts/tests/test-docker-context.sh` (modified)
- `README.md` (modified)
- `_bmad-output/planning-artifacts/architecture/epic-22-server-operations-and-metrics.md` (modified: ADR-16 decisions 6 and 9, "Results (Story 22.8)")
- `_bmad-output/implementation-artifacts/22-8-container-stop-saves-the-world.md` (this file)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (through `just sprint set` only)

## Review

Reviewer: GLM-5.3-Flash via opencode. Verdict: approve. 0 HIGH, 0 MEDIUM, three LOW findings, all accepted without a code change:

1. **LOW: an in-flight Stop or Restart can push the shutdown's stop past Docker's 10 s grace.** A Stop or Restart that holds the lifecycle lock when SIGTERM arrives finishes its own stop (10 s timeout) before `stop_for_api_shutdown` gets the lock; with a game that ignores SIGTERM, that stop plus the shutdown's 8 s can run past 10 s and Docker's SIGKILL wins. Accepted: ADR-16 decision 3 keeps the stop inside the lock uncancelled, and "ADR against the code" 2 records the unbounded lock wait. The measured stop is under 1 s (Task 4), so the window needs both an in-flight lifecycle request and a game that does not stop.
2. **LOW: a clean stop exits with code 143, not 0.** uvicorn 0.54 re-raises the SIGTERM it caught once its shutdown, including the lifespan shutdown, has finished, so `uv` exits with 128 + 15 (Dev Agent Record, "Exit code 143"; Completion Notes deviation 1). Accepted: the shipped compose file's `restart: unless-stopped` honours a manual stop, so a 143 does not start a restart loop. Drawdown item 1 (exit 0 after a completed shutdown) stays for the maintainer.
3. **LOW: Task 3's `build` commit has a side effect a user could notice.** `build(story-22.8/task-3): limit uvicorn's wait for open requests at shutdown to 1 second` (e22886d9) means a request still running 1 s after SIGTERM is cancelled ("ADR against the code" 6). `build` is not a release-note type, so the release notes will not mention it. Accepted: the README's "Stopping and restarting the container" says the manager "gives open requests up to 1 second to finish", and no history is rewritten.

No fix commits. `just check` green with Stories 22.4 and 22.7's reviews merged in (API 3790 passed, web 3567 passed, pyright 0 errors and 0 warnings). Task 6.3 (the maintainer's check) stays open.

## Change Log

- 2026-11-19: Story 22.8 created (ready-for-dev).
- 2026-11-19: Validated against the create-story checklist, ADR-16, FR308 and the code at dd781b5c. Added Task 3 (`--timeout-graceful-shutdown 1` in the image `CMD`, a `build` commit; uvicorn otherwise waits without limit for in-flight requests and background tasks before the lifespan shutdown) and renumbered the later tasks (now 6); recorded that `uv run` forwards SIGTERM to uvicorn (uv docs); the new test file defines its own `config_path`/`spawner` fixtures; the refused-start test now proves the refusal comes before the 22.7 write-back; the module-function test checks the 8 s default.
- 2026-11-19: Implemented (dev-story): Tasks 1 to 6; throwaway-container run recorded (exit code 143, not 0; stop rule not fired); status review. Task 6.3 waits for the maintainer.
- 2026-11-19: Code review (GLM-5.3-Flash via opencode): approve; 0 HIGH, 0 MEDIUM, three LOW accepted without a code change (an in-flight Stop/Restart can push the stop past the grace; clean stops exit 143; Task 3's `build` commit's 1 s request cut-off is in the README, not the release notes) (see "Review"). Status done.
