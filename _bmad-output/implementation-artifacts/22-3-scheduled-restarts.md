# Story 22.3: Scheduled Restarts

Status: in-progress

<!-- Implements FR292-FR296, Epic 22 ADR-5, ADR-6, ADR-7, ADR-8 and ADR-14. Beads: VSS-29p (API-011), first half (Story 22.4 closes it); VSS-zws (API-073), checked and closed here. Maintainer answers 5, 6, 7 and 11 (Matt, 2026-11-18). Stories run in order 22.1 to 22.6; this branch, story/22-3-scheduled-restarts, is stacked on story/22-2-prometheus-metrics-endpoint at 0067a09b (22.2 in review: it made game settings and mods share one PendingRestartState and makes every successful start clear it). The PR targets main and merges after 22.2's. Line references were verified at 0067a09b and must be re-checked at implementation time. API and documentation only; no web source change (the UI for the setting is Story 22.6). No new dependency, no new route, one new job module, no change to services/scheduler.py. The stop timeout and game_config.py change only on the maintainer's answer (ADR-8 decision 2). -->

## Story

As an **operator**,
I want **the game server to restart at the times I set, after warning the players**,
so that **it runs fresh every day without me being there, and nobody is surprised**.

## Acceptance Criteria

1. **Given** an Admin key
   **When** it sets `scheduled_restart_times` to `["16:00", "04:00", "04:00"]` (`POST /api/v1alpha1/config/api/settings/scheduled_restart_times`, body `{"value": [...]}`)
   **Then** the answer is 200 with `{"key": "scheduled_restart_times", "value": ["04:00", "16:00"]}`, `api-settings.json` holds `["04:00", "16:00"]`, and `GET /api/v1alpha1/config/api` returns it; the default (no file, or a file without the key) is `[]`
   *(Covers FR292; ADR-5 decisions 1 to 3)*

2. **Given** an Admin key and a saved value
   **When** it sets `scheduled_restart_times` to a list with `4:00`, `24:00`, `04:60`, `04:00\n`, a non-string entry, 25 distinct times, `04:00` and `04:10`, or `23:55` and `00:05`; or to a value that is not a list (`"04:00"`)
   **Then** the answer is 400 `API_SETTING_INVALID` with a message naming the problem (the entry, the count, or the two times and their gap), the saved value does not change, and the scheduler is not called
   *(Covers FR292; ADR-5 decision 2, ADR-6 decision 6; see "ADR against the code" 1 and 2)*

3. **Given** `scheduled_restart_times` is `["04:00"]`
   **When** the API starts, or the setting is saved
   **Then** the job `scheduled_restart_0400` is registered with a next run at 03:45 in the container's time zone (`TZ`, the process's local zone, UTC when unset), and `GET /api/v1alpha1/jobs` lists it with `trigger_type` `cron`; `["00:10"]` gives `scheduled_restart_0010` at 23:55; saving `["16:00"]` removes `scheduled_restart_0400` and adds `scheduled_restart_1600`; saving `[]` removes every `scheduled_restart_*` job at once; no other job changes
   *(Covers FR295; ADR-6 decisions 1 and 7, ADR-7 decisions 1 to 3)*

4. **Given** the scheduler cannot apply the saved times (it raises)
   **When** the setting is saved
   **Then** the value is saved and the answer is 500 `API_SETTING_NOT_APPLIED`, as for an interval, and `api_setting_not_applied` is logged at ERROR
   *(Covers FR295; ADR-7 decision 2)*

5. **Given** the game is running when `scheduled_restart_0400` fires
   **When** the sequence runs (with a fake sleep in tests)
   **Then** `/announce Server restarts in 15 minutes` is sent, then after 600 s `/announce Server restarts in 5 minutes`, then after 240 s `/announce Server restarts in 1 minute`, then after 60 s the restart goes through `ServerService.restart_server()`, which clears the pending-restart flag; the log line before the restart says how many players were online, and one after it says the restart is done
   *(Covers FR293, FR294; ADR-6 decisions 1, 2, 4 and 5)*

6. **Given** the game is stopped when the job fires, or stops during the warnings
   **When** the sequence reaches its next step
   **Then** nothing more is announced, the game is not started, and `scheduled_restart_skipped reason=not_running` is logged
   *(Covers FR293, FR294; ADR-6 decision 3)*

7. **Given** a manual start, stop, restart or uninstall holds the lifecycle lock, or an install holds the install lock, when the restart is due
   **When** the scheduled restart runs
   **Then** it does not wait, does not restart, and logs `scheduled_restart_skipped reason=lifecycle_busy`
   *(Covers FR293; ADR-6 decision 4; see "ADR against the code" 3)*

8. **Given** a sequence is in its warnings
   **When** its time is removed from `scheduled_restart_times` (or its job is deleted with `DELETE /api/v1alpha1/jobs/{job_id}`)
   **Then** at its next step it announces nothing more, does not restart, and logs `scheduled_restart_skipped reason=cancelled`; when the same time stays in a re-saved list, the sequence goes on
   *(Covers FR295; ADR-6 decision 1, ADR-7 decision 1; see "ADR against the code" 4)*

9. **Given** the restart is due and `restart_server()` raises (for example `SERVER_STOP_FAILED`)
   **When** the sequence runs
   **Then** `scheduled_restart_failed` is logged at ERROR with the error code, the job is not retried, and nothing else starts the game
   *(Covers FR293; ADR-6 decision 4)*

10. **Given** a throwaway container with a fresh world (never the dev stack)
    **When** the game is stopped three times
    **Then** the story records each stop's duration, whether it ended within 10 seconds and whether the log shows the world saved; if any stop needs more than 10 seconds or cuts the save short, the story stops for the maintainer's decision before the restart job is merged
    *(Covers FR296; ADR-8 decisions 1 and 2, ADR-14)*

11. **Given** the same throwaway container
    **When** `Port` is changed through the API while the game runs, a live `/serverconfig` command is sent, the game is stopped, and then started again
    **Then** the story records what `serverconfig.json` holds after the live command, after the stop and after the start; if the game overwrote the edit, the story stops for the maintainer's decision (no fix without it)
    *(Covers FR296; ADR-8 decision 3; see "ADR against the code" 6)*

12. **Given** the README
    **When** I read its configuration table and the scheduled restarts section
    **Then** `TZ` is documented (UTC when unset, an example value, set in `.env`), and the section says how to set the times, when the warnings come, that a stopped server is not started, that a time less than 15 minutes ahead (when saved, or when the API starts) first runs the next day, how a restart is skipped or cancelled, the 24-time and 16-minute limits, what the Scheduled Jobs tab shows, and the daylight saving caveat; `.env.example` has a commented `TZ` line
    *(Covers FR292, FR293; ADR-5 decision 4, ADR-6 decision 6)*

13. **Given** every existing test
    **When** the suites run
    **Then** they pass unchanged except the two listed in Dev Notes "Existing tests that change"; Pyright reports 0 errors and 0 warnings; the diff adds no `# type: ignore`, `# pyright: ignore`, `noqa`, `cast` or skipped test; no test starts or stops the dev stack's game server, no unit test restarts a real game process, and no test writes into `dev/`

14. **Given** a scheduled restart on a non-production server
    **When** the maintainer is in the game at the warning times
    **Then** he sees the three warnings and the restart (manual check, reserved for the maintainer, ticked only on his confirmation)
    *(Covers FR294; ADR-14 decision 4)*

## Tasks / Subtasks

<!-- Each functional task includes its tests in the same commit, red first (run the new tests, see them fail, then implement). Subjects: type(story-22.3/task-N): ..., the type chosen by what an admin notices. One commit is user-visible: Task 4 (feat), the commit that makes restarts happen; its subject is written for admins and its body names Story 22.3 and the task. -->

- [x] Task 1: Measure the stop and check `VSS-zws` in a throwaway container (AC: 10, 11)
  - [x] 1.1: Run Dev Notes "The throwaway-container run" exactly: image `vss-22-3-measure:local` built from this branch, container `vss-22-3-measure` on `127.0.0.1:18090`, no game port published, placeholder keys, no volume or bind mount, no compose, not `just test-e2e-ci` (it blocks the game download hosts). Never the dev stack (`vintagestory-manager-dev`, port 9080), whose game server is not started or stopped, and never `./data` or `dev/`
  - [x] 1.2: Install the current stable game through the API, then three start/stop rounds; for each stop record: the time from `stopping_server` to `server_stopped_gracefully` or `server_stop_timeout` (from the API's JSON log timestamps), the HTTP time of `POST /server/stop`, the exit code, and the lines `server-main.log` (and `server-debug.log` if the main log has none) shows between the stop and the exit, verbatim apart from addresses
  - [x] 1.3: `VSS-zws` in the same container (steps in Dev Notes): `Port` 42420 -> 42421 while running, a live `ServerName` change (the API sends `/serverconfig name ...`), then read `serverconfig.json` after the live command, after the stop and after the next start
  - [x] 1.4: The time zone check (Dev Notes): `get_localzone()` in the image is `UTC` without `TZ` and `Europe/Berlin` with `TZ=Europe/Berlin`
  - [x] 1.5: Remove the container and the image (`docker rm -f vss-22-3-measure vss-22-3-tz`, `docker image rm vss-22-3-measure:local`); `docker ps -a --filter name=vss-22-3` is empty
  - [x] 1.6: Record the results in Dev Agent Record "Throwaway-container results" (host architecture, game version, a table of the three stops, the `serverconfig.json` values at each point, the TZ output, the commands) and append a "Results (Story 22.3)" paragraph to ADR-8's section in `_bmad-output/planning-artifacts/architecture/epic-22-server-operations-and-metrics.md`. No instance data, no real key, no address
  - [x] 1.7: **Stop rule:** if any stop took more than 10 s, was killed, or the log does not show the save finished before the exit, or if `serverconfig.json` lost the `Port` edit at any point: commit the record (1.8), then stop and report it to the controller as a maintainer question with the measured numbers and the options of ADR-8 decision 2 (raise the timeout, `/autosavenow` before the stop, `/stop` instead of SIGTERM) or, for `VSS-zws`, the small fix (re-apply pending file edits after the stop). Change neither the 10 s timeout (`services/server.py:1076`, `:1177`) nor `services/game_config.py`. Tasks 2 to 5 go on only if the controller says so; the story does not go to review before the answer
  - [x] 1.8: Commit `docs(story-22.3/task-1): record the game server's stop time and the serverconfig.json check`

- [ ] Task 2: The `scheduled_restart_times` setting, its validator and list handling in `update_setting` + tests (AC: 1, 2, 13)
  - [ ] 2.1: Red first: the Task 2 rows of Dev Notes "API tests" in `api/tests/test_api_settings.py` and `api/tests/test_routers_config.py`; see the new tests fail
  - [ ] 2.2: `services/api_settings.py`: the field, the constants and the validator of Dev Notes "The setting"; the list branch in `update_setting` and the callback changes of Dev Notes "`update_setting` and the callback"; `INTERVAL_SETTINGS` becomes `SCHEDULED_SETTINGS` with the four keys (ADR-7 decision 2). The only other code that names `INTERVAL_SETTINGS` is `tests/test_jobs_registration.py:719-724` (Task 4 updates it; in this task keep it green by updating its import and assertion as "Existing tests that change" says); the comment at `web/src/api/config.ts:79-80` names it too and is left for Story 22.6 (no web source change here). The new `SCHEDULED_SETTINGS` docstring keeps the pointer to the web's `INTERVAL_API_SETTINGS` for the interval keys
  - [ ] 2.3: The router still passes `partial(apply_interval_setting, scheduler)` in this task, so `update_setting` must not call the callback for `scheduled_restart_times` yet and the callback keeps its type `Callable[[str, int], None]` (widening it now would make that partial fail pyright): in this task `SCHEDULED_SETTINGS` holds only the three interval keys. Task 4 adds `RESTART_TIMES_SETTING` to it, widens the callback type and swaps in `apply_setting`, in one commit
  - [ ] 2.4: `cd api && uv run ruff format <changed files>`; `just test-api tests/test_api_settings.py tests/test_routers_config.py tests/test_jobs_registration.py` green; `just typecheck-api` 0 errors, 0 warnings
  - [ ] 2.5: Commit `refactor(story-22.3/task-2): accept and validate scheduled_restart_times in the API settings` (nothing acts on it yet; the release note comes with Task 4; precedent `refactor(story-22.2/task-3)`)

- [ ] Task 3: The warning and restart sequence, with injectable sleep and the skip rules + tests (AC: 5, 6, 7, 8, 9, 13)
  - [ ] 3.1: Red first: new `api/tests/test_scheduled_restart.py` with the Task 3 rows of Dev Notes "API tests", and the `ServerService` rows in `api/tests/server/test_lifecycle.py`; see them fail
  - [ ] 3.2: `services/server.py`: the two read-only properties `game_running` and `lifecycle_busy` of Dev Notes "Two properties on ServerService", after `players_online` (`:217-222`). Nothing else in that file changes
  - [ ] 3.3: New `api/src/vintagestory_api/jobs/scheduled_restart.py` (Dev Notes "The sequence"): the constants, `restart_job_id`, `warning_start`, the `RestartTarget` protocol, `run_restart_sequence` and the job function `scheduled_restart` under `@safe_job("scheduled_restart")`. Logging exactly as Dev Notes "What is logged". Nothing registers it yet
  - [ ] 3.4: `cd api && uv run ruff format <changed files>`; `just test-api tests/test_scheduled_restart.py tests/server` green; `just typecheck-api` 0/0
  - [ ] 3.5: Commit `refactor(story-22.3/task-3): add the scheduled restart sequence with its warnings and skip rules` (not registered yet)

- [ ] Task 4: Apply restart times as cron jobs at start-up and on save + tests (AC: 3, 4, 8, 13)
  - [ ] 4.1: Red first: the Task 4 rows of Dev Notes "API tests" in `api/tests/test_jobs_registration.py`, `api/tests/test_routers_config.py` and `api/tests/test_api_settings.py`; see them fail
  - [ ] 4.2: `jobs/__init__.py`: `apply_restart_schedule`, `apply_setting` and the `register_default_jobs` change of Dev Notes "Registration"; `services/api_settings.py`: add `RESTART_TIMES_SETTING` to `SCHEDULED_SETTINGS`, add `ScheduledSettingValue` and widen the callback type (Dev Notes "`update_setting` and the callback"); `tests/test_api_settings.py:954`: `failing_callback`'s annotation ("Existing tests that change" 1); `routers/config.py`: import `apply_setting` instead of `apply_interval_setting` (`:44`) and pass `partial(apply_setting, scheduler)` (`:275`), with the docstrings of `get_api_settings_service` (`:259-276`) and `update_api_setting` (`:308-382`) naming restart times. `main.py` does not change (the lifespan already calls `register_default_jobs`, `:215-217`)
  - [ ] 4.3: `cd api && uv run ruff format <changed files>`; `just test-api tests/test_jobs_registration.py tests/test_routers_config.py tests/test_api_settings.py tests/test_scheduled_restart.py tests/test_scheduler.py tests/test_main.py` green; `just typecheck-api` 0/0
  - [ ] 4.4: Commit `feat(story-22.3/task-4): restart the game server at scheduled times, warning players first` (body: Story 22.3 / task 4; the API setting `scheduled_restart_times` takes daily `HH:MM` times in the container's time zone; players are warned with `/announce` 15, 5 and 1 minutes before; only a running server is restarted, through the Restart button's path; each time is a `scheduled_restart_HHMM` job in Scheduled Jobs)

- [ ] Task 5: Document `TZ` and scheduled restarts (AC: 12)
  - [ ] 5.1: `README.md`: the `TZ` row in the Configuration table (`:77-90`, after `VS_MOD_CACHE_MAX_SIZE_MB`), a new `### Scheduled restarts` section between Configuration and Metrics (`:92`), and the Features "Scheduled jobs" bullet (`:17`), with the text of Dev Notes "Documentation"
  - [ ] 5.2: `.env.example`: a commented `TZ` block at the end of the OPTIONAL section, in the file's style (Dev Notes "Documentation")
  - [ ] 5.3: `just lint` green (nothing else moved)
  - [ ] 5.4: Commit `docs(story-22.3/task-5): document TZ and scheduled restarts`

- [ ] Task 6: Validate and move the story to review (AC: all)
  - [ ] 6.1: `just check` green: API tests, pyright 0 errors and 0 warnings, ruff; web tests with 0 skipped, tsc, Prettier. The added lines in `api/src` and `api/tests` hold no `type: ignore`, `pyright:`, `noqa`, `cast(`, skip, `xfail` or `.only`; `services/scheduler.py` and `models/jobs.py` are unchanged (`git diff 0067a09b -- api/src/vintagestory_api/services/scheduler.py api/src/vintagestory_api/models/jobs.py` is empty). `git status --short dev/` is empty after the runs
  - [ ] 6.2: `just changelog` lists exactly one new entry from this story (Task 4's feature subject); check by this branch's hashes, as Story 22.2 did
  - [ ] 6.3: Manual check (maintainer only; leave unticked until he confirms, AC 14): on a non-production server he runs, set `scheduled_restart_times` to a time 20 or more minutes ahead (a time less than 15 minutes ahead first runs the next day), be in the game, see `Server restarts in 15 minutes`, `5 minutes`, `1 minute` and the restart, then save `[]`. No agent runs this, and never on the dev stack's game server
  - [ ] 6.4: Story status `review` in this file; `just sprint set 22-3-scheduled-restarts review`; Dev Agent Record and File List filled in, every statement true of the code
  - [ ] 6.5: Commit `chore(story-22.3/task-6): validate and move story 22.3 to review`
  - [ ] 6.6: After merge, with the maintainer's go-ahead only: `VSS-zws` gets an AAR with the Task 1 evidence and is closed; `VSS-29p` gets a comment with this story's commits and stays open for Story 22.4 (`bd comments add`, `bd close`, `bd sync`; CLAUDE.md "Completing Issues"). Pushing, the PR and the beads wait for that go-ahead

## Dev Notes

### The code today (verified at 0067a09b)

- **Settings:** `ApiSettings` (`api/src/vintagestory_api/services/api_settings.py:34-96`) holds booleans, three intervals bounded by `MAX_INTERVAL_SECONDS` (`:26`) and the webhook URL with its `field_validator` (`:78-90`, the pattern for the new validator). `INTERVAL_SETTINGS` (`:102-114`) lists the keys whose saved value goes to the scheduler callback. `ApiSettingsService.__init__` (`:187-203`) types the callback as `Callable[[str, int], None]` (`:190`). `update_setting` (`:246-360`) coerces `bool` (`:281-294`) and `int` (`:295-306`); any other annotation falls to `validated_value = value` (`:307-308`), so a list would reach Pydantic unchecked; it builds `ApiSettings(**current_dict)` (`:311-312`), turns a `ValidationError` into `ApiSettingInvalidError` with the **first** error's `msg` only (`:314-317`), saves atomically (`:320`, `_save_settings` `:362-398`), then calls the callback with `validated_value` (the raw input, not the stored value) for `INTERVAL_SETTINGS` keys (`:322-339`); any exception there is logged `api_setting_not_applied` (ERROR) and re-raised as `ApiSettingNotAppliedError` (`:155-176`). The `api_setting_updated` INFO line logs `value` and `old_value` (`:352-358`).
- **Jobs:** `INTERVAL_JOBS` (`jobs/__init__.py:37-42`), `_job_function` imports job functions lazily (`:48-60`), `apply_interval_setting(scheduler, key, seconds, *, startup=False)` (`:63-106`) adds/replaces or removes one job, `register_default_jobs` (`:109-137`) reads `ApiSettingsService().get_settings()` (default `Settings()` from the environment) and applies each interval. Its docstring already says "A job execution in progress is not cancelled by a replace or a removal" (`:72-73`), and `tests/test_jobs_registration.py` `test_running_execution_finishes_when_interval_changes` pins it.
- **Scheduler:** `SchedulerService` (`services/scheduler.py`) uses `AsyncIOScheduler` with `coalesce: True`, `max_instances: 1`, `misfire_grace_time: 60` (`:58-66`). `add_cron_job(func, cron_expr, job_id, **kwargs)` (`:160-191`) builds `CronTrigger.from_crontab(cron_expr)` with no time zone and passes `id`, `replace_existing=True` and `**kwargs` to `add_job`; it logs `job_added` with `trigger_type="cron"` and `cron_expr`. `remove_job` (`:193-203`, logs `job_removed`, raises `JobLookupError` for an unknown id), `get_jobs` (`:205-211`), `get_job` (`:213-222`). The file carries fourteen `# type: ignore` comments (`:22-27`, `:146`, `:183`, `:185`, `:202`, `:205`, `:211`, `:213`, `:222`); this story adds none and does not edit the file. No cron job is registered today (`add_cron_job` is used only by `tests/test_scheduler.py:157-185`).
- **Router:** `get_api_settings_service` (`routers/config.py:259-276`) builds `ApiSettingsService(settings=server_service.settings, scheduler_callback=partial(apply_interval_setting, scheduler))` (`:275`; import `:44`; `get_scheduler` from `routers/jobs.py:20-27`). `update_api_setting` (`:308-382`) maps `ApiSettingUnknownError` and `ApiSettingInvalidError` to 400 (`:357-373`) and `ApiSettingNotAppliedError` to 500 (`:375-382`) with `ErrorCode.API_SETTING_UNKNOWN`, `API_SETTING_INVALID`, `API_SETTING_NOT_APPLIED` (`models/errors.py:52-55`). The body is `SettingUpdateRequest` with `value: Any` (`:87-90`), so a JSON array arrives as a `list`.
- **Job pattern:** `safe_job(job_name)` (`jobs/base.py:61-105`) logs `{job_name}_started` and `{job_name}_completed` at INFO and catches `Exception` with `logger.exception("{job_name}_failed")`; `asyncio.CancelledError` is not an `Exception` and passes through.
- **Game server:** `get_server_service()` (`services/server.py:52-60`) is the singleton. `_install_lock` (`:166`, held by `install_server`, `:753`) and `_lifecycle_lock` (`:183`, held by `start_server` `:965`, `stop_server` `:1088`, `restart_server` `:1189`, `uninstall_server` `:1346`) are separate. `players_online` (`:217-222`) is the tracker's count while a process lives, else `None`. `_get_runtime_state` (`:939-954`) is the state while the process lives, `STARTING`/`STOPPING` during a transition, else `INSTALLED`; `_start_server_locked` sets `RUNNING` right after the spawn (`:1042`), so the lifecycle lock is held only briefly for a start and up to the timeout for a stop. `restart_server(timeout=10.0)` (`:1177-1190`) takes the lifecycle lock; `_restart_server_locked` (`:1192-1221`) stops the game **if it runs** and then **starts it whatever the state**, then `_clear_pending_restart()` (`:1214`, `:246-258`). A stop sends SIGTERM (`:1112`), waits `timeout` (`:1115`), then kills (`server_stop_timeout`, `server_killed`). `send_command(command)` (`:1298-1327`) returns `False` when no process runs or stdin is missing, echoes `[CMD] <command>` to the console buffer and writes the line to stdin; `/announce <message>` is a game command (`agentdocs/server-commands.md:542-547`). Since Story 22.2 a successful `start_server` also clears the shared pending-restart state (`:965-970`).
- **Jobs API and tab:** `GET /api/v1alpha1/jobs` (`routers/jobs.py:30-49`) serialises each job with `job_to_info` (`models/jobs.py:35-77`): `id`, `next_run_time` (timezone-aware ISO), `trigger_type` (`cron` for a `CronTrigger`), `trigger_details` (`str(trigger)`, for `from_crontab("45 3 * * *")` exactly `cron[month='*', day='*', day_of_week='*', hour='3', minute='45']`, checked on APScheduler 3.11.3). `DELETE /api/v1alpha1/jobs/{job_id}` (`:52-85`) removes any job. The web's `JobsTable` shows the id, the details as they are (`formatSchedule` only rewrites `every N seconds`, `web/src/components/JobsTable.tsx:50-70`), the next run in the browser's local time (`formatNextRunTime`, `:41-44`) and a `cron` badge. So a restart job appears with no web change (ADR-6 decision 7).
- **Start-up:** the lifespan (`main.py:156-229`) auto-starts the game (`:192-208`), then creates and starts the scheduler (`:210-212`) and calls `register_default_jobs` (`:215-217`); at shutdown `scheduler_service.shutdown(wait=True)` (`:221-223`). APScheduler's `AsyncIOExecutor.shutdown` cancels running job coroutines (checked in 3.11.3: the sequence gets `CancelledError` at its sleep; APScheduler logs it as "raised an exception").
- **Time zone:** `CronTrigger.from_crontab` without `timezone` uses `tzlocal.get_localzone()` (`apscheduler/triggers/cron/__init__.py:85-92` in 3.11.3; the docs' "defaults to scheduler timezone" is the same zone here, since the scheduler's own default is also `get_localzone()`). `tzlocal` reads `TZ` first, then `/etc/localtime`; it is a locked dependency of apscheduler (`api/uv.lock`, 5.4.5, ships `py.typed`). Checked locally: with `TZ` unset the zone was the machine's, with `TZ=Europe/Berlin` it was `CET`. The image has no `TZ` (`Dockerfile`, `docker-compose.yaml:16-28`); `.env` reaches the container through `env_file` (`docker-compose.yaml:27-29`). Log timestamps stay UTC (`config.py:428`, `TimeStamper(fmt="iso")`).
- **No list-valued API setting and no cron job exist**; the web types (`web/src/api/types.ts:304`) are plain interfaces, so an extra field in `GET /config/api` changes nothing in the web.

### The setting (Task 2)

In `services/api_settings.py`, after `metrics_collection_interval` (`:66-71`) and before the webhook:

```python
RESTART_TIMES_SETTING = "scheduled_restart_times"
MAX_RESTART_TIMES = 24
MIN_RESTART_GAP_MINUTES = 16
"""Each sequence runs from 15 minutes before its time to the restart (Epic 22 ADR-6 decision 6)."""
_RESTART_TIME = re.compile(r"([01][0-9]|2[0-3]):[0-5][0-9]")

    scheduled_restart_times: list[str] = Field(
        default_factory=list[str],
        description=(
            "Daily restart times, HH:MM (24-hour) in the container's time zone (TZ, UTC when "
            "unset). Players are warned 15, 5 and 1 minutes before; a stopped server is not "
            "started; a time less than 15 minutes ahead first runs the next day. At most 24, "
            "at least 16 minutes apart."
        ),
    )

    @field_validator("scheduled_restart_times")
    @classmethod
    def _validate_restart_times(cls, value: list[str]) -> list[str]: ...
```

(The constants go at module level next to `MAX_INTERVAL_SECONDS`; names are binding.)

- `default_factory=list[str]` (not `list`): with `list` pyright strict infers `list[Unknown]`. Checked in a scratch module under the project's pyright settings: 0/0.
- An **after** validator typed `value: list[str]`: Pydantic first rejects a non-list (`Input should be a valid list`) and a non-string entry (`Input should be a valid string`; lax mode does not turn `400` or `true` into a string). A `mode="before"` validator would narrow an `object` to `list[Unknown]` and warn; do not use one.
- Order of checks, each raising `ValueError` with the message shown (Pydantic prefixes `Value error, `, as for the webhook; tests assert with `in`):
  1. every entry `_RESTART_TIME.fullmatch(entry)`; else `f"{shown!r} is not a time in HH:MM (24-hour, 00:00 to 23:59)"`, `shown` the entry cut to 16 characters plus `...` when longer. `fullmatch` and `[0-9]` (not `match`/`$`/`\d`) so `04:00\n` and full-width digits fail.
  2. `times = sorted(set(value))` (duplicates removed; zero-padded `HH:MM` sorts as text).
  3. `len(times) > MAX_RESTART_TIMES`: `f"at most {MAX_RESTART_TIMES} times, got {len(times)}"` (counted after duplicates are removed).
  4. with two or more times, each time and the next one, the last wrapping to the first (`(minutes(next) - minutes(this)) % 1440`): a gap under `MIN_RESTART_GAP_MINUTES` raises `f"{a!r} and {b!r} are {gap} minutes apart; restart times must be at least {MIN_RESTART_GAP_MINUTES} minutes apart"`. `04:00` + `04:16` passes; `04:00` + `04:10` and `23:55` + `00:05` fail ("ADR against the code" 2).
  5. return `times`.
- Messages name entries and counts; the values are not secret. Prototype run in planning on the epic's examples gave exactly the expected results for each case of AC 1 and 2.
- `get_settings` already falls back to all defaults (WARNING `api_settings_load_failed`) when the file fails validation (`:229-244`); a hand-edited file with a bad time therefore drops every setting to its default. Existing behaviour, not changed.

### `update_setting` and the callback (Task 2)

- **The list branch (ADR-5 decision 3):** a new `elif get_origin(expected_type) is list:` between the `int` branch (`:295-306`) and the `else` (`:307-308`): when the value is not a JSON array, raise `ApiSettingInvalidError(key, "must be a list of times in HH:MM")`; otherwise `validated_value = value` and the model's validator does the rest. Test for the array with a module-level helper `def _is_json_array(value: object) -> bool: return isinstance(value, list)`: an inline `isinstance(value, list)` narrows the `Any` parameter to `list[Unknown]` and pyright strict warns on `validated_value` (checked in planning: inline gives 2 warnings, the helper 0). `from typing import get_origin`.
- **The callback gets the stored value:** `stored = getattr(updated, key)` after the save; call `self._scheduler_callback(key, stored)` (sorted, de-duplicated for the list; the same int for an interval, so existing callback tests still see `(key, 7200)`). Log `api_setting_not_applied` with `value=stored`.
- **The callback type (Task 4, with the router swap):** `ScheduledSettingValue = int | list[str]` (module level, public, exported for `jobs`), `scheduler_callback: Callable[[str, ScheduledSettingValue], None] | None`; docstring: the router passes `apply_setting` bound to the scheduler (Story 17.6, Story 22.3).
- **`SCHEDULED_SETTINGS`** replaces `INTERVAL_SETTINGS` (`:102-114`, same docstring idea: the keys whose saved value goes to the scheduler callback; the interval keys equal `jobs.INTERVAL_JOBS`, a test keeps them equal). Task 2: the three interval keys; Task 4 adds `RESTART_TIMES_SETTING`. The condition at `:326` becomes `key in SCHEDULED_SETTINGS`.
- `api_setting_updated` logs the list as `value`/`old_value` (not secret). `ApiSettingNotAppliedError`'s text ("its job could not be rescheduled ... applies when the API restarts") stays as is for both kinds.

### Two properties on ServerService (Task 3)

```python
    @property
    def game_running(self) -> bool:
        """True while the game process runs and is neither starting nor stopping (Story 22.3)."""
        return self._get_runtime_state() == ServerState.RUNNING

    @property
    def lifecycle_busy(self) -> bool:
        """True while a start, stop, restart, uninstall or install holds its lock (Story 22.3)."""
        return self._lifecycle_lock.locked() or self._install_lock.locked()
```

The job must not read `_lifecycle_lock` from another module (`reportPrivateUsage` is an error in `src`), and `get_server_status()` is too heavy for this (versions cache, `get_disk_space_data()` reading `Settings()` from the environment, `services/server.py:893-937`).

### The sequence (Task 3)

New module `api/src/vintagestory_api/jobs/scheduled_restart.py`. Names are binding, bodies are the developer's:

```python
"""Scheduled restarts: warn the players, then restart a running game (Epic 22 ADR-6)."""

RESTART_JOB_PREFIX = "scheduled_restart_"
WARNING_LEAD_MINUTES = 15
WARNINGS: tuple[tuple[int, str, float], ...] = (
    (15, "Server restarts in 15 minutes", 600.0),
    (5, "Server restarts in 5 minutes", 240.0),
    (1, "Server restarts in 1 minute", 60.0),
)
"""(minutes left, the /announce text, seconds to wait after it); the waits add up to 15 minutes."""

RestartOutcome = Literal["restarted", "not_running", "lifecycle_busy", "cancelled", "failed"]


def restart_job_id(restart_time: str) -> str:  # "04:00" -> "scheduled_restart_0400"
def warning_start(restart_time: str) -> tuple[int, int]:  # "04:00" -> (3, 45); "00:10" -> (23, 55)


class RestartTarget(Protocol):
    """What the sequence needs from ServerService (a test fake satisfies it too)."""

    @property
    def game_running(self) -> bool: ...
    @property
    def lifecycle_busy(self) -> bool: ...
    @property
    def players_online(self) -> int | None: ...
    async def send_command(self, command: str) -> bool: ...
    async def restart_server(self, timeout: float = 10.0) -> object: ...


async def run_restart_sequence(
    restart_time: str,
    *,
    server: RestartTarget,
    still_scheduled: Callable[[], bool],
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> RestartOutcome: ...


@safe_job("scheduled_restart")
async def scheduled_restart(restart_time: str, scheduler: SchedulerService) -> None:
    """The job function: one per restart time, fired WARNING_LEAD_MINUTES before it."""
```

- `scheduled_restart` imports `get_server_service` inside the function (lazily, as `_job_function` does, `jobs/__init__.py:48-60`) and calls `run_restart_sequence(restart_time, server=get_server_service(), still_scheduled=lambda: scheduler.get_job(restart_job_id(restart_time)) is not None)`. `SchedulerService` and `ServerService` are imported under `TYPE_CHECKING` only. `ServerService` satisfies `RestartTarget` structurally (its `restart_server` returns `LifecycleResponse`; checked in planning with pyright strict: 0/0, and a plain test class with attributes for the properties also satisfies it).
- **Steps.** For each `(minutes_left, text, wait)` in `WARNINGS`: (a) `if not still_scheduled()` -> skip `cancelled`; (b) `if not server.game_running` -> skip `not_running`; (c) `sent = await server.send_command(f"/announce {text}")`; `False` -> skip `not_running` (the process ended between (b) and (c)); (d) log `scheduled_restart_warning`; (e) `await sleep(wait)`. Then at the restart time: (a) cancelled, (b) `if server.lifecycle_busy` -> skip `lifecycle_busy` (never wait for the lock), (c) not running, (d) `players = server.players_online`, log `scheduled_restart_restarting`, (e) `await server.restart_server()`; a `RuntimeError` -> log `scheduled_restart_failed` (ERROR, `error_code=str(e)`, the `ErrorCode` the service raises) and return `failed`; success -> log `scheduled_restart_done` and return `restarted`. Any other exception propagates to `safe_job` (`scheduled_restart_failed` with the traceback), no retry. An exception from `send_command` itself (for example `BrokenPipeError` from `drain()` when the process dies between the check and the write) also propagates to `safe_job`: no restart, no retry.
- **Busy before not running, at the restart only (AC 7, FR293):** a manual stop or restart sets `STOPPING` and a start sets `STARTING` while holding the lifecycle lock (`services/server.py:1108`, `:1026`), so `game_running` is already False during them; checking `not_running` first would log `reason=not_running` for every manual operation in progress and AC 7 would hold only for a forced install beside a running game. At the warning steps there is no busy check (ADR-6 decision 4 names it only at the restart): a manual stop or restart in progress at a warning step ends the sequence with `not_running`.
- **No await between the last checks and taking the lock:** (b), (c) and the call to `restart_server()` run with no `await` between them, and `asyncio.Lock.acquire()` on a free lock returns without suspending, so the game cannot be found running and then be started from stopped: `_restart_server_locked` stops only a running process and the check is made in the same event-loop turn. Keep it that way: no `await` (not even a log flush) between the `lifecycle_busy`/`game_running` checks and `restart_server()`. The sequence holds no lock during its warnings (it takes the lifecycle lock only inside `restart_server()`), so manual operations are never blocked by a sequence.
- **Stale sequences ("ADR against the code" 4).** APScheduler does not cancel a running execution when its job is replaced or removed (pinned for intervals by `test_running_execution_finishes_when_interval_changes`; checked for 3.11.3 in planning: after `remove_job` the coroutine kept running and saw `get_job(...) is None`). The rule: **at every step the sequence first checks that its own job id is still registered**; removing the time from the setting (Task 4 removes the job at once) or deleting the job through `DELETE /jobs/{id}` ends the sequence at its next step with `cancelled`, without an announcement. A re-saved list that keeps the time replaces the job under the same id (`replace_existing=True`), so the sequence goes on, which is right: that restart is still wanted. The check is by id only, so a time removed and added back between two steps (save `[]`, then `["04:00"]` again) is not noticed and the sequence goes on too; a removal seen at a step ends it for good, and adding the time back later does not resume it (checked on 3.11.3: after a remove and re-add under the same id the running coroutine sees `get_job(...)` not `None`; a second fire under the same id while one runs is skipped by `max_instances`). `DELETE /jobs/{id}` removes the job itself, so that time has no job (no restart on any later day) until `scheduled_restart_times` is saved again or the API restarts, as for an interval job deleted there. A time changed from `04:00` to `04:05` during the warnings cancels the 04:00 sequence; the 04:05 job's first fire (03:50) may already have passed and then first runs the next day (ADR-6 decision 6).
- **Overlap:** `max_instances: 1` is per job id; two different times cannot overlap because the validator keeps them 16 minutes apart, also across midnight.
- **API shutdown** during the warnings cancels the sequence (`CancelledError` at the sleep); do not catch it. A restart missed while the API is down is not made up: the memory job store is rebuilt at each start and `add_job` computes the first fire from now, so `misfire_grace_time` (60 s) and `coalesce` never see a fire from before the start; they only cover a fire that the running loop wakes up late for. **An API start inside the window** (for example the container restarted at 03:50 for a 04:00 restart) therefore registers the job with its first fire the next day (checked on 3.11.3: a cron time 5 minutes in the past gives a next run about 23 h 55 min ahead): that day's restart does not happen and nothing is logged beyond `job_registered` with its `first_warning`. Documented (README), tested (Task 4 "Startup"), not worked around.

### What is logged

| Event | Level | Fields | When |
|---|---|---|---|
| `scheduled_restart_started`, `scheduled_restart_completed` | INFO | none | `safe_job`, at the fire (T-15) and at the end, whatever the outcome the sequence returns (`_completed` is not logged when an exception reached `safe_job`; it logs `scheduled_restart_failed` instead) |
| `scheduled_restart_warning` | INFO | `restart_time`, `minutes_left` | after each `/announce` was sent |
| `scheduled_restart_skipped` | INFO for `not_running` and `cancelled`; WARNING for `lifecycle_busy` | `restart_time`, `reason`, `minutes_left` (15, 5, 1, or 0 at the restart) | each skip |
| `scheduled_restart_restarting` | INFO | `restart_time`, `players_online` | just before `restart_server()` |
| `scheduled_restart_done` | INFO | `restart_time` | after a successful restart |
| `scheduled_restart_failed` | ERROR | `restart_time`, `error_code` | `restart_server()` raised `RuntimeError`; any other exception: `safe_job`'s line with `error` and the traceback |
| `job_registered` | INFO | `job_id`, `restart_time`, `first_warning` (`HH:MM`) | each restart job added or replaced (Task 4) |
| `restart_schedule_applied` | INFO | `times`, `removed` (job ids) | end of `apply_restart_schedule` |

`add_cron_job` logs `job_added` and `remove_job` logs `job_removed` themselves. No player name or address in any line (only the count). `send_command` logs `command_sent` at DEBUG and the console shows `[CMD] /announce ...`.

### Registration (Task 4)

In `jobs/__init__.py`:

```python
def apply_restart_schedule(scheduler: SchedulerService, times: list[str]) -> None:
    """Make the restart jobs match the saved times (Epic 22 ADR-7 decision 1)."""


def apply_setting(scheduler: SchedulerService, key: str, value: ScheduledSettingValue) -> None:
    """The scheduler callback for every scheduled setting (Epic 22 ADR-7 decisions 1 and 2)."""
```

- `apply_restart_schedule`: import `RESTART_JOB_PREFIX`, `restart_job_id`, `warning_start`, `scheduled_restart` from `jobs.scheduled_restart` inside the function (lazily, so tests can monkeypatch `vintagestory_api.jobs.scheduled_restart.scheduled_restart`). `wanted = {restart_job_id(t): t for t in times}`. Remove every registered job whose id starts with `RESTART_JOB_PREFIX` and is not in `wanted`; read ids as `job_to_info(job).id` for `job in scheduler.get_jobs()` (`job.id` is `Unknown` to pyright and warns; `job_to_info(...).id` is `str`; checked in planning: 0/0). Then for each wanted time `hour, minute = warning_start(t)` and `scheduler.add_cron_job(scheduled_restart, f"{minute} {hour} * * *", job_id=..., kwargs={"restart_time": t, "scheduler": scheduler})` (replaces an existing job). Uses the existing `add_cron_job` unchanged: no time zone argument, so the trigger takes the process's local zone (`TZ`). `CronTrigger(hour=..., minute=..., timezone=...)` would also type-check cleanly in a new module (checked: 0/0 with the import unsuppressed), but it is not needed and would mean a second way to build cron jobs; do not change `scheduler.py`.
- `apply_setting`: a key of `INTERVAL_JOBS` -> `apply_interval_setting(scheduler, key, value)` when `isinstance(value, int)`, else `TypeError`; `RESTART_TIMES_SETTING` -> `apply_restart_schedule(scheduler, value)` when `isinstance(value, list)`, else `TypeError`; any other key: nothing. A `TypeError` is a programming error; through `update_setting` it becomes `API_SETTING_NOT_APPLIED`. Import `RESTART_TIMES_SETTING` and `ScheduledSettingValue` from `services.api_settings` (already imported by this module, `:29`).
- `register_default_jobs`: after the interval loop, `apply_restart_schedule(scheduler, settings.scheduled_restart_times)`; the final log becomes `default_jobs_registered count=<interval jobs> restart_jobs=<len(times)>`. Docstring lists the restart jobs.
- A partial failure (a removal done, an add raising) leaves the scheduler part-way; the value is saved and applies at the next API start, as the not-applied message says. Not made transactional.
- The module docstring (`:1-20`) gains Story 22.3.

### Time zone (ADR-5 decision 4)

The times are wall-clock times in the process's local zone, which is `TZ` (UTC in the image when unset). In a zone with daylight saving, a job whose fire time (T-15) falls in the hour the clocks change runs late or not at all on the spring day and twice on the autumn day (APScheduler 3 documents it; checked on 3.11.3 with `Europe/Berlin`: a 02:25 fire ran at 03:25 CEST on 2027-03-28 and twice on 2027-10-31). Documented in the README, not worked around. The Scheduled Jobs tab shows the next run converted to the browser's local time.

### The throwaway-container run (Task 1)

Run from the repo root; placeholder keys only (never `.env`'s); never the dev stack.

- **Isolation, as `scripts/e2e-ci.sh` does it (ADR-14 decision 2):** plain `docker build`/`docker run`, never `docker compose` (both compose files bind-mount `./data:/data`, and `docker-compose.dev.yaml` is the dev stack, `vintagestory-manager-dev` on 9080 with the game port 42420 published). No `-v`, `--mount` or `--env-file`: the image declares no `VOLUME`, so `/data` lives in the container's writable layer and goes with `docker rm -f`; `.dockerignore` keeps `data/` and every `.env` out of the build context. Own names (`vss-22-3-*`), own port (`127.0.0.1:18090`, not 9080 and not e2e-ci's 18080/18081), own image tag (not `vintagestory-server:e2e`).
- **Do not reuse `just test-e2e-ci`:** it maps `api.vintagestory.at`, `cdn.vintagestory.at` and the mod hosts to loopback (`BLOCKED_HOSTS`), so a game install fails there; it runs the Playwright and API E2E suites and removes its containers when they finish. Reuse its pattern only (placeholder keys, `127.0.0.1` port, `--platform linux/amd64`, cleanup), with the default network so the game download works.

```bash
IMAGE=vss-22-3-measure:local; NAME=vss-22-3-measure; BASE=http://127.0.0.1:18090
KEY=vss-22-3-placeholder-admin-key; H=(-H "X-API-Key: $KEY" -H "Content-Type: application/json")
docker rm -f "$NAME" vss-22-3-tz >/dev/null 2>&1 || true   # leftovers of a killed run
docker build --platform linux/amd64 -t "$IMAGE" .
docker run -d --name "$NAME" --platform linux/amd64 -p 127.0.0.1:18090:8080 \
  -e VS_API_KEY_ADMIN="$KEY" -e VS_DATA_DIR=/data "$IMAGE"
# wait for $BASE/healthz, then:
curl -s "${H[@]}" -X POST "$BASE/api/v1alpha1/server/install" -d '{"version":"stable"}'
# poll GET /api/v1alpha1/server/install/status until installed; record the resolved version
curl -s "${H[@]}" -X POST "$BASE/api/v1alpha1/server/start"
# wait until the game reports it is ready (GET /api/v1alpha1/console/history, or
# docker exec "$NAME" tail /data/serverdata/Logs/server-main.log); record the ready line;
# let it run 60 s so the world has loaded chunks
curl -s -o /dev/null -w '%{time_total}\n' "${H[@]}" -X POST "$BASE/api/v1alpha1/server/stop"
docker logs "$NAME" 2>&1 | grep -E 'stopping_server|server_stopped_gracefully|server_stop_timeout|server_killed'
docker exec "$NAME" tail -n 40 /data/serverdata/Logs/server-main.log
```

- Three rounds of start, ready, 60 s, stop. The stop time is the difference of the `timestamp` fields of `stopping_server` and `server_stopped_gracefully` (or `server_stop_timeout`, which means the 10 s ran out). Record the save lines as the game prints them; a save that "finished" means its completion line comes before the exit. Do not guess the game's wording in advance.
- **Host:** record `uname -m`. The image is `linux/amd64`; on an arm64 Mac it runs emulated and is slower than on a real amd64 host. Record the numbers as measured; a stop near or over 10 s under emulation is still reported (the maintainer can re-run on amd64).
- **VSS-zws**, after round 3's start: read `Port` and `ServerName` from `/data/serverdata/serverconfig.json` (`docker exec "$NAME" cat ...`); `POST /api/v1alpha1/config/game/settings/Port` `{"value": 42421}` (restart-required: the API writes the file and flags a restart); read the file; `POST /api/v1alpha1/config/game/settings/ServerName` `{"value": "vss-22-3 zws check"}` (live: the API sends `/serverconfig name ...`; record the game's console answer); read the file; stop; read the file; start; wait ready; read the file and the port the game says it listens on; stop. Record `Port` and `ServerName` at each of the five reads. The game port is not published, so 42421 clashes with nothing.
- **TZ:** `docker run --rm --name vss-22-3-tz --platform linux/amd64 "$IMAGE" uv run --no-sync python -c "from tzlocal import get_localzone; print(get_localzone())"`, then the same with `-e TZ=Europe/Berlin` before the image name; expect `UTC` and `Europe/Berlin`.
- Clean up even after a failure: `docker rm -f "$NAME" vss-22-3-tz; docker image rm "$IMAGE"`; then `docker ps -a --filter name=vss-22-3` and `docker image ls vss-22-3-measure` are empty (nothing was mounted, so `./data`, which git ignores, and `dev/` were never reachable from the container).

### Documentation (Task 5)

- **Configuration table row**, after `VS_MOD_CACHE_MAX_SIZE_MB`: `| \`TZ\` | No | Time zone of the container, for example \`Europe/Berlin\` (UTC when unset). Scheduled restarts follow it; log timestamps stay in UTC |`.
- **`### Scheduled restarts`**, between Configuration and Metrics, in the README's plain style:
  - The API setting `scheduled_restart_times` holds daily times as `HH:MM` (24-hour) in the container's time zone (`TZ`); empty by default. Example with an Admin key: `curl -X POST http://<host>:8080/api/v1alpha1/config/api/settings/scheduled_restart_times -H "X-API-Key: <admin key>" -H "Content-Type: application/json" -d '{"value": ["04:00", "16:00"]}'`; `{"value": []}` turns them off. Up to 24 times, at least 16 minutes apart; duplicates are dropped and the list is stored sorted.
  - Players are warned with `/announce`: `Server restarts in 15 minutes`, `in 5 minutes`, `in 1 minute`; then the game server restarts the way the Restart button does, whether or not players are online.
  - A stopped server is never started. If it is not running when the warnings start or stops during them, nothing more is announced. If a start, stop, restart, install or uninstall is in progress at the restart time, the restart is skipped. Skips are logged as `scheduled_restart_skipped` with the reason.
  - Removing a time during its warnings cancels that restart; players are not told. Deleting a `scheduled_restart_HHMM` job in Scheduled Jobs also cancels a restart in its warnings, and that time then has no job until the setting is saved again or the API restarts.
  - A time less than 15 minutes ahead when it is saved first runs the next day. The same holds when the API (or the container) starts less than 15 minutes before a time: that day's restart does not happen.
  - Each time is a `scheduled_restart_HHMM` job in **Settings → Scheduled Jobs**; its next run is the first warning, 15 minutes before the restart, shown in your browser's time zone.
  - With a time zone that has daylight saving, a restart whose first warning falls in the hour the clocks change runs late or not at all when they go forward and twice when they go back; choose times outside that hour.
- **Features bullet** (`:17`): "**Scheduled jobs:** background tasks such as mod cache refreshes, and daily scheduled restarts that warn players first, with their status in the UI".
- **`.env.example`**, at the end of the OPTIONAL section:
  ```
  # Time zone of the container (scheduled restarts follow it; log timestamps stay UTC)
  # Default: UTC
  # TZ=Europe/Berlin
  ```

### API tests

| Task | File | Test |
|---|---|---|
| 2 | `api/tests/test_api_settings.py` | **Model:** default `[]`; `["16:00","04:00","04:00"]` -> `["04:00","16:00"]`; `["00:00","23:59"]` accepted; `["04:00","04:16"]` accepted; 24 hourly times accepted; each rejected input of AC 2 raises `ValidationError` whose first `msg` contains the expected text (the entry `'4:00'`, `'24:00'`, `'04:60'`, `'04:00\n'` repr; `valid string`; `at most 24 times, got 25`; `'04:00' and '04:10' are 10 minutes apart`; `'23:55' and '00:05' are 10 minutes apart`; `valid list` for a bare string); a 40-character string entry is shown cut to 16 characters plus `...`; `MAX_RESTART_TIMES == 24`, `MIN_RESTART_GAP_MINUTES == 16` |
| 2 | same | **Service:** `update_setting("scheduled_restart_times", ["16:00","04:00","04:00"])` returns `{"key": ..., "value": ["04:00","16:00"]}` and the file holds that list; a non-list (`"04:00"`, `4`, `{"a": 1}`) raises `ApiSettingInvalidError` with `must be a list of times in HH:MM`; each AC 2 list raises `ApiSettingInvalidError` with the key and the reason, the file bytes unchanged, a `MagicMock` callback not called; `api_setting_updated` logs the list (`capture_logs`). **Callback gets the stored value:** with `SCHEDULED_SETTINGS` patched by `monkeypatch.setattr(api_settings, "SCHEDULED_SETTINGS", frozenset({..., "scheduled_restart_times"}))` (Task 2 only; Task 4 tests the real set), the callback is called once with `("scheduled_restart_times", ["04:00","16:00"])`; existing interval callback tests unchanged |
| 2 | `api/tests/test_routers_config.py` | Through the route with the admin key (the file's `reschedule_client`-style client and `temp_settings`): POST `["16:00","04:00","04:00"]` -> 200 and `GET /api/v1alpha1/config/api` has `scheduled_restart_times == ["04:00","16:00"]`; POST `["04:00","04:10"]` -> 400 `API_SETTING_INVALID`, message contains `10 minutes apart`, the GET value unchanged; a Monitor key -> 403 (as the existing API-settings tests) |
| 3 | `api/tests/server/test_lifecycle.py` | `game_running`: False with no process; True with a live fake process and `RUNNING` (set `_process` and `_server_state` through `monkeypatch.setattr`, as the file's fixtures do); False with a live process in `STOPPING` and `STARTING`. `lifecycle_busy`: False idle; True inside `async with service._lifecycle_lock`; True inside `async with service._install_lock` |
| 3 | `api/tests/test_scheduled_restart.py` (new) | **Helpers:** `restart_job_id("04:00") == "scheduled_restart_0400"`; `warning_start` for `04:00` (3, 45), `00:10` (23, 55), `00:15` (0, 0), `23:59` (23, 44); `WARNINGS` texts exactly as AC 5 and the waits sum to 900 |
| 3 | same | **Fakes:** `FakeServer` (plain class: `game_running`, `lifecycle_busy`, `players_online` attributes; `sent: list[str]`; `send_command` appends and returns `self.accept_commands`; `restart_server` records the call or raises a configured `RuntimeError`) and `FakeSleep` (records each duration in a shared `events` list with the commands, and runs an optional per-call hook to change the fake's state, so a test can stop the game "during" a wait). No `MagicMock` for the server, no real `asyncio.sleep` |
| 3 | same | **Happy path (AC 5):** events are exactly `/announce Server restarts in 15 minutes`, sleep 600, `/announce Server restarts in 5 minutes`, sleep 240, `/announce Server restarts in 1 minute`, sleep 60, restart; outcome `restarted`; `scheduled_restart_restarting` with `players_online=3` and `scheduled_restart_done` logged; three `scheduled_restart_warning` lines with minutes 15, 5, 1 |
| 3 | same | **Not running (AC 6):** stopped at the fire: nothing sent, no restart, `scheduled_restart_skipped reason=not_running minutes_left=15`; stopped during the first wait: one announcement, then skip with `minutes_left=5`; stopped during the last wait: three announcements, no restart, `minutes_left=0`; `send_command` returning False: skip `not_running`. In every case `restart_server` is never called (so a stopped game is never started) |
| 3 | same | **Busy (AC 7):** `lifecycle_busy` True at the restart: no restart, WARNING `scheduled_restart_skipped reason=lifecycle_busy`; the call returns at once (wrap in `asyncio.wait_for(..., timeout=1)`). The order: `lifecycle_busy` True and `game_running` False together at the restart (a manual stop in progress) -> `reason=lifecycle_busy`, not `not_running`; `lifecycle_busy` True during the warnings changes nothing (all three sent) |
| 3 | same | **Cancelled (AC 8):** `still_scheduled` False at the fire: nothing sent; turning False in the second wait: two announcements, then `reason=cancelled minutes_left=1`, no restart; True throughout: restarted |
| 3 | same | **Failure (AC 9):** `restart_server` raising `RuntimeError("SERVER_STOP_FAILED")`: outcome `failed`, ERROR `scheduled_restart_failed error_code=SERVER_STOP_FAILED`, `restart_server` called once. Raising `OSError` through the job function `scheduled_restart` (with `get_server_service` monkeypatched in `vintagestory_api.services.server` to return the fake, and a stub scheduler whose `get_job` returns a non-None value, a small class, not a `MagicMock`): `safe_job` logs `scheduled_restart_failed` and the job returns `None` |
| 3 | same | **Real ServerService (AC 5, pending restart):** a temp-dir `ServerService(settings)` (installed as `tests/server/conftest.py:99-126`), a fake running process with a fake stdin (`write` records, `drain` async no-op) set through `monkeypatch.setattr`, `_stop_server_locked` and `_start_server_locked` replaced with `AsyncMock` through `monkeypatch.setattr`, the shared state reset (`monkeypatch.setattr(vintagestory_api.services.mods, "_restart_state", None)`) and flagged with `require_restart`: after `run_restart_sequence` with `FakeSleep` the three `/announce` lines were written to stdin, the console buffer holds their `[CMD]` echoes, both mocks were awaited once and `get_restart_state().pending_restart` is False. Same with the lock held by the test (`async with service._lifecycle_lock`) at the restart: `lifecycle_busy`, mocks not awaited; and with the lock held and `_server_state` set to `STOPPING` (a manual stop in progress): `lifecycle_busy`, mocks not awaited. The fake process has `pid` and `returncode = None` (`players_online` reads `game_server_pid`) |
| 4 | `api/tests/test_jobs_registration.py` | Fixture: the existing `started_scheduler` plus `monkeypatch.setattr("vintagestory_api.jobs.scheduled_restart.scheduled_restart", _no_op_restart)` (`async def _no_op_restart(**_: object) -> None`), so no registered job can run the real sequence. **Add:** `["04:00"]` -> one job `scheduled_restart_0400`, `trigger_type` `cron`, `trigger_details == "cron[month='*', day='*', day_of_week='*', hour='3', minute='45']"`, `next_run_time.astimezone()` has hour 3 and minute 45 and is within 24 h; `["00:10"]` -> `hour='23', minute='55'`. **Replace:** `["04:00","16:00"]` then `["16:00","20:00"]` -> exactly those two restart ids, interval jobs untouched (register one first and check it is still there). **Remove:** then `[]` -> no `scheduled_restart_*` job. **Less than 15 minutes ahead:** a time 10 minutes ahead of now (in the fixture's UTC zone below) -> next run about 23 h 55 min away (±2 min). **Startup:** `register_default_jobs` with settings `scheduled_restart_times=["04:00"]` (the file's `ApiSettingsService` patch pattern, `:86-88`) registers it and logs `restart_jobs=1`; with a time 10 minutes ahead of now (UTC fixture) the job's next run is about 23 h 55 min away (±2 min): an API start inside the window does not fire that day. **apply_setting:** interval key with an int -> the interval job; `scheduled_restart_times` with a list -> restart jobs; an interval key with a list and the restart key with an int -> `TypeError`; `auto_start_server` -> nothing. **Keys:** `test_settings_service_uses_the_same_keys` renamed for `SCHEDULED_SETTINGS == set(INTERVAL_JOBS) \| {"scheduled_restart_times"}` |
| 4 | same | **Time zone (AC 3):** a fixture `local_tz(name)` that saves `os.environ.get("TZ")`, sets `TZ`, calls `time.tzset()` and `tzlocal.reload_localzone()`, and in its teardown restores the variable (or removes it) and calls both again (do not use `monkeypatch` for `TZ`: its undo runs after this fixture's teardown). With `Europe/Berlin`: the job's `next_run_time` converted with `ZoneInfo("Europe/Berlin")` is 03:45; with `UTC`: its `utcoffset()` is 0 and it is 03:45 |
| 4 | same | **Stale job (AC 8):** a sequence started with the real `still_scheduled` over `started_scheduler` (`lambda: started_scheduler.get_job("scheduled_restart_0400") is not None`) and a `FakeSleep` whose first-wait hook calls `apply_restart_schedule(started_scheduler, [])`: one announcement, then `cancelled`; whose hook re-applies `["04:00"]`: restarted |
| 4 | `api/tests/test_routers_config.py` | Over `reschedule_client` (`:2242-2276`) with the no-op restart job patched: POST `["04:00"]` -> 200, `GET /api/v1alpha1/jobs` lists `scheduled_restart_0400` with `trigger_type` `cron` and a `next_run_time` whose local time is 03:45; POST `[]` -> it is gone and the three interval jobs (if registered) are unchanged; **not applied (AC 4):** `monkeypatch.setattr(reschedule_scheduler, "add_cron_job", raising)` -> 500 `API_SETTING_NOT_APPLIED`, the file holds the new list, `api_setting_not_applied` logged |
| 4 | `api/tests/test_api_settings.py` | `RESTART_TIMES_SETTING in SCHEDULED_SETTINGS`; a callback raising for `scheduled_restart_times` -> `ApiSettingNotAppliedError`, value saved (as `test_failed_callback_raises_after_saving`) |

All player names and keys in tests are placeholders. Tests reach private attributes through `monkeypatch.setattr` only (the `tests` execution environment sets `reportPrivateUsage = false`, `api/pyproject.toml`); add no file-level pyright relaxation. `tzlocal` is imported only in tests (it is apscheduler's locked dependency, typed); `src` does not import it.

### Existing tests that change (deliberately)

1. (Task 4) `tests/test_api_settings.py:954`: `def failing_callback(_key: str, _value: int)` becomes `_value: ScheduledSettingValue` (or `int | list[str]`): with the wider callback type, a callable that accepts only `int` no longer type-checks (parameter contravariance). Behaviour unchanged.
2. `tests/test_jobs_registration.py:719-724` `test_settings_service_uses_the_same_keys` imports `INTERVAL_SETTINGS`, which goes: Task 2 points it at `SCHEDULED_SETTINGS` (still the three interval keys), Task 4 asserts the four keys; the `annotation is int` loop over `INTERVAL_JOBS` stays.

Every other test stays as it is. Tests that patch `ApiSettingsService` in `register_default_jobs` return real `ApiSettings` objects (default `scheduled_restart_times == []`), so they register no restart job. Anything else that fails is a regression (AC 13): fix the code, not the test.

### Not changed (do not "fix" these here)

- The 10 s stop timeout, SIGTERM, `restart_server`, `stop_server` and `services/game_config.py` (ADR-8 decision 2; only on the maintainer's answer to Task 1).
- `services/scheduler.py` (no new method, no time zone argument, its fourteen `# type: ignore` stay), `models/jobs.py`, `routers/jobs.py`, the jobs API shape, the scheduler's `job_defaults`, `main.py`.
- The web (Story 22.6 adds the editor), the Dockerfile and compose files (no `TZ` default is added; operators set it in `.env`).
- No crash auto-restart, no catch-up of a missed restart, no announcement when a restart is cancelled or skipped, no configurable warning text or minutes (answers 6 and 7).
- `ApiSettingNotAppliedError`'s text; `get_settings`' fall-back to defaults on an invalid file.
- `install_server` not taking the lifecycle lock (an existing gap: a forced install can run beside a start or stop); the scheduled restart only treats a held install lock as busy.

### API contract changes

- New API setting `scheduled_restart_times`: list of `HH:MM`, default `[]`, in `GET /api/v1alpha1/config/api` and settable with `POST /api/v1alpha1/config/api/settings/scheduled_restart_times` (`{"value": [...]}`); 400 `API_SETTING_INVALID` for an invalid list, 500 `API_SETTING_NOT_APPLIED` when saved but not scheduled. Additive.
- New jobs `scheduled_restart_HHMM` in `GET /api/v1alpha1/jobs` (`trigger_type` `cron`), deletable with the existing `DELETE /jobs/{id}` (which also cancels a sequence in its warnings; the time then has no job until the setting is saved again or the API restarts).
- Web contract for Story 22.6: `GET /config/api` returns `scheduled_restart_times` in `data.settings`; the web client turns keys to camelCase (`snakeToCamel`, `web/src/api/client.ts:53-66`; it leaves string values as they are), so the UI reads `settings.scheduledRestartTimes: string[]`. The key in the POST path stays `scheduled_restart_times`. `ApiSettingsData` (`web/src/api/types.ts:304-314`) and `updateApiSetting`'s `value: string | number | boolean` (`web/src/api/config.ts:115-118`) gain the list in Story 22.6, not here.
- New log events: see "What is logged".
- `TZ` documented. No route, field or status code changes; nothing breaking.
- Release note (scope stripped by git-cliff): Task 4's "restart the game server at scheduled times, warning players first".

### ADR against the code

1. **Non-string entries are named by Pydantic, not by position.** ADR-5 decision 2 says the 400 names the entry. An after-validator typed `list[str]` (the only shape that type-checks without suppressions, see "The setting") lets Pydantic reject a non-string with `Input should be a valid string`, and `update_setting` reports only the first error's message (`:314-317`). The message names the problem (AC 2 of the epic) but not the index. Changing `update_setting` to include the error location would change every setting's messages; not done.
2. **The 16-minute gap is checked around midnight too.** ADR-6 decision 6 says "on the same day". The jobs are daily, so `23:55` (fire 23:40) and `00:05` (fire 23:50) would overlap exactly like `04:00` and `04:10`; `max_instances` is per job id and cannot stop it. The validator compares the last time with the first across midnight.
3. **`lifecycle_busy` includes the install lock.** ADR-6 decision 4 and FR293 name install among the operations that make a restart skip, but `install_server` holds `_install_lock` (`services/server.py:166`, `:753`), not the lifecycle lock. `lifecycle_busy` is true when either is held; the log reason stays `lifecycle_busy`.
4. **What stops a stale sequence.** ADR-7 decision 1 removes or replaces jobs, and Story 17.6 established that a running execution is not cancelled by either. Without a rule, removing a time during its warnings would still restart the game. The story adds the rule of "The sequence": at every step the sequence checks its own job id is still registered and ends with `reason=cancelled` otherwise (AC 8, a refinement the epic does not state). It also makes `DELETE /jobs/{id}` a way to cancel a restart in its warnings (the job is gone, so the time also has no later restart until the setting is saved again or the API restarts).
5. **The `feat` commit is the wiring task, not the sequence task.** The epic puts the `feat(api)` release note on the sequence task; here the sequence (Task 3) is built and tested first without being registered, and Task 4 is the first commit after which a restart happens. The release note goes with Task 4; the subject uses the project's `feat(story-22.3/task-4)` scope (stripped from release notes; precedent Stories 22.1 and 22.2).
6. **No `VSS-zws` fix without the maintainer.** ADR-8 decision 3 allows a small fix inside the story; the controller's instruction for this story is to stop and ask instead. Task 1.7 stops with the evidence and a proposed fix.
7. **The container run comes first.** The epic lists it fourth. It needs no new code, and a slow stop is the one finding that could change the design (a `/autosavenow` or `/stop` before the restart), so it runs before the code; the epic's condition "before the restart job is merged" is kept by Task 1.7.
8. **Time zone through the existing cron helper.** ADR-5 says the container's local zone; `add_cron_job`'s `from_crontab` without `timezone` gives exactly that (`get_localzone()`, which reads `TZ`), so no scheduler change is needed and no time zone is passed.
9. **At the restart, busy is checked before running.** ADR-6 lists the running check (decision 3) before the busy check (decision 4). A manual stop, restart or start holds the lifecycle lock with the state `STOPPING` or `STARTING`, so with running first every such case would log `not_running` and FR293's "skipped and logged" for an operation in progress would read as a stopped game. The restart step checks cancelled, then busy, then running ("The sequence", Steps); the outcome (no restart, no wait) is the same either way.

### Open questions for the maintainer (none blocks the start)

1. A restart cancelled during its warnings (time removed, job deleted) tells the players nothing, so they may wait for a restart that does not come. Should a cancellation be announced (fixed text)? The story does not, because answer 6 fixed the texts.
2. The 16-minute gap across midnight ("ADR against the code" 2) and the install lock as busy (3): confirm.
3. Daylight saving: documented only (late/missing in spring, twice in autumn when the first warning falls in the changed hour). Acceptable, or should the validator refuse such times for the configured `TZ`?
4. Task 1 may come back with a question about the stop timeout or `VSS-zws` (Task 1.7).
5. An API (or container) start less than 15 minutes before a time skips that day's restart without a log line of its own ("The sequence", API shutdown). Acceptable as documented, or should start-up log `scheduled_restart_skipped reason=api_started_in_window`?
6. A manual stop or restart in progress at a warning step ends the sequence with `not_running`, even when the manual restart brings the game back before the scheduled time. Acceptable (the operator just restarted it), or should warning steps also treat busy as "keep going"?

### Testing Requirements

**CRITICAL:** tests are written with each task and committed with it, red first. `just test-api <files>` after each task; `just check` before review.

- No lint or type suppression (`# type: ignore`, `# pyright: ignore`, `noqa`), no `cast`, no `as`-style escape (`typing.cast`, `Any`-typed stand-ins for typed parameters), no skipped test (`pytest.mark.skip`, `skipif`, `xfail`), no `.only`. Pyright 0 errors and 0 warnings in `src` and `tests`.
- No real sleep in the sequence tests (`FakeSleep`), no real restart: no test spawns `dotnet`; `restart_server` is a fake or has its `_stop_server_locked`/`_start_server_locked` replaced. No test starts or stops the dev stack's game server (ADR-14).
- Every scheduler test registers the no-op restart job, so a registered time that happens to fire during the run cannot reach `get_server_service()`.
- Log assertions with `structlog.testing.capture_logs()`. Private state through `monkeypatch.setattr` only; any test that flags the shared pending-restart state first resets `services.mods._restart_state` to `None` through `monkeypatch`.
- Every `Settings` in a test has `data_dir` under `tmp_path`; nothing writes into `dev/` (`git status --short dev/` stays empty).
- The `TZ` fixture restores the variable and calls `time.tzset()` and `tzlocal.reload_localzone()` after itself, so no other test sees a changed zone.

### Security Requirements

- `POST /config/api/settings/...` and `GET /jobs` stay Admin only (`routers/config.py`, `routers/jobs.py`); a Monitor key cannot set restart times.
- The `/announce` texts are constants; nothing from a request reaches the game's stdin through this job (the times are validated to `HH:MM` and only used in the job id and the log).
- Log lines carry the time, the count of players and error codes; no player name, address or key.
- The throwaway container uses placeholder keys, binds only `127.0.0.1:18090`, and is removed with its image; nothing from it is committed except the measured numbers and game log lines without addresses.

### Development Commands

- `just test-api tests/test_api_settings.py tests/test_routers_config.py tests/test_jobs_registration.py tests/test_scheduled_restart.py tests/server tests/test_scheduler.py tests/test_main.py`, `just typecheck-api`, `just lint-api`.
- `cd api && uv run ruff format <changed files>` (`just format-api` takes no file arguments and formats the whole tree; Story 22.1 drawdown note).
- `just check` (Task 6), `just changelog` (Task 6.2), `just sprint set 22-3-scheduled-restarts review`.
- Docker only for Task 1's `vss-22-3-measure` container; never `just docker ...`, `just test-e2e-api`, `just test-e2e` or `just test-e2e-web` (they target or restart the dev stack). No E2E test is added: a restart job saved by an E2E test would act on whichever stack the run points at, and the route tests cover the API.

### Previous Story Intelligence

- **22.2** (this branch's base, in review): one shared `PendingRestartState` (`routers/config.py:93-105` returns `services.mods.get_restart_state()`), cleared by every successful `start_server` and by `restart_server`; so a scheduled restart clears a pending mod or `Port` change, and the `/healthz`, banner and `/metrics` flag go to false. Its tests built a real temp-dir `ServerService` instead of a bare `MagicMock` (a `MagicMock` leaked into a snapshot in 22.1); do the same. Its "no `with` block" route clients do not run the lifespan; this story's route tests use the existing `reschedule_client` (httpx over ASGI, the scheduler started on the test's loop).
- **22.1:** `players_online` is `None` without a process; the restart log line takes it as it is. User-visible commits use `feat(story-22.x/task-N)`.
- **17.6:** `apply_interval_setting`, `ApiSettingNotAppliedError`, the "Saved, not applied yet" path and the rule that a running execution finishes; this story generalises the callback (ADR-7) without changing that behaviour.
- **21.3:** the depth and the "ADR against the code" record; completion notes must be true of the code.

### Git Intelligence

- Branch `story/22-3-scheduled-restarts` from `story/22-2-prometheus-metrics-endpoint` at `0067a09b` (`chore(story-22.2/task-6): validate and move story 22.2 to review`). 22.2's commits: `d84b02b9` (dependency), `010f93d5` (shared pending restart, `fix`), `c931d014` (collector), `2798a72b` (route, `feat`), `d02ad046` (README).
- Planned commits: Task 1 `docs(story-22.3/task-1): record the game server's stop time and the serverconfig.json check`; Task 2 `refactor(story-22.3/task-2): accept and validate scheduled_restart_times in the API settings`; Task 3 `refactor(story-22.3/task-3): add the scheduled restart sequence with its warnings and skip rules`; Task 4 `feat(story-22.3/task-4): restart the game server at scheduled times, warning players first`; Task 5 `docs(story-22.3/task-5): document TZ and scheduled restarts`; Task 6 `chore(story-22.3/task-6): validate and move story 22.3 to review`.

### Project Structure Notes

- New: `api/src/vintagestory_api/jobs/scheduled_restart.py`, `api/tests/test_scheduled_restart.py`.
- Modified: `api/src/vintagestory_api/services/api_settings.py`, `api/src/vintagestory_api/services/server.py` (two properties), `api/src/vintagestory_api/jobs/__init__.py`, `api/src/vintagestory_api/routers/config.py`, `api/tests/test_api_settings.py`, `api/tests/test_routers_config.py`, `api/tests/test_jobs_registration.py`, `api/tests/server/test_lifecycle.py`, `README.md`, `.env.example`, `_bmad-output/planning-artifacts/architecture/epic-22-server-operations-and-metrics.md` (ADR-8 results, Task 1), this story file, and `sprint-status.yaml` (through `just sprint` only).
- Not touched: `services/scheduler.py`, `models/jobs.py`, `routers/jobs.py`, `main.py`, `services/game_config.py`, the web, the Dockerfile and compose files.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 22.3: Scheduled Restarts] (`:7417-7503`) and the Epic 22 header
- [Source: _bmad-output/planning-artifacts/prd.md] FR292-FR296 (`:904-908`)
- [Source: _bmad-output/planning-artifacts/architecture/epic-22-server-operations-and-metrics.md] "Facts Checked in the Code" (Restarts, Settings), ADR-5, ADR-6, ADR-7, ADR-8, ADR-14
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-18-epic-22.md] sections 1, 2 (contract table, draft release notes, risks), 5 (answers 5-7, 11; planner decisions not reviewed: the job layout, the 16-minute gap, `apply_setting`, the stop measurement)
- [Source: _bmad-output/implementation-artifacts/22-2-prometheus-metrics-endpoint.md], [22-1-players-online-are-counted.md] (previous stories), [21-3-log-level-and-config-viewer.md] (depth)
- Beads: `VSS-zws` (API-073, "change Port through the API, run a live /serverconfig command, stop the server, and check the file"; Story 16.8 comment on live-only values), `VSS-29p` (API-011), parent `VSS-oole`
- APScheduler 3.11.3 (installed): `CronTrigger.from_crontab` time zone default (`get_localzone()`), `str(CronTrigger)`, `AsyncIOExecutor.shutdown` cancelling running coroutines, replace/remove not cancelling a running execution, daylight-saving behaviour (Context7 `/websites/apscheduler_readthedocs_io_en_3_x`, "Daylight saving time behavior"; checked by running 3.11.3 in planning). Pyright strict on the validator, the list branch helper, the protocol and `job_to_info(...).id` checked in a scratch module with the project's settings
- `project-context.md`: tests with each task; no suppressions; "no silent failures"; commit types by user impact; `just` for every task; `RELEASING.md` "Commit messages are release notes"

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5), dev-story workflow, non-interactive.

### Throwaway-container results

<!-- Task 1.6: host architecture, game version, the three stops, the serverconfig.json reads, the TZ output, the commands. -->

Run on 2026-11-19 (UTC) from this branch at bed96d68.

- **Host:** `uname -m` = `arm64` (Apple silicon, Docker 29.9.2). The image is `linux/amd64`, so the game ran emulated; a real amd64 host would be faster, not slower.
- **Game version:** `stable` resolved to **1.22.7** (installed through `POST /api/v1alpha1/server/install`). Fresh world created by the first start.
- **Isolation:** image `vss-22-3-measure:local`, container `vss-22-3-measure`, only `127.0.0.1:18090 -> 8080` published (game port not published), placeholder admin key, no `-v`/`--mount`/`--env-file`, no compose; `docker inspect` showed `Mounts: []`. The dev stack was not running and was not touched.

**The stops** (stop time = `server_stopped_gracefully.timestamp - stopping_server.timestamp` from the API's JSON log; HTTP = curl `time_total` of `POST /api/v1alpha1/server/stop`):

| Stop | Game ready (`now running`) | Ran before stop | `stopping_server` | `server_stopped_gracefully` | Stop time | HTTP | Exit code | Within 10 s | World saved before exit |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 02:13:15 | 69 s | 02:14:24.899 | 02:14:25.731 | 0.83 s | 0.836 s | 0 | yes | yes (`World saved! Saved 8 chunks, 1 mapchunks, 16 mapregions.`) |
| 2 | 02:14:46 | 300 s | 02:19:46.322 | 02:19:47.049 | 0.73 s | 0.730 s | 0 | yes | yes (`World saved! Saved 0 chunks, 0 mapchunks, 4 mapregions.`) |
| 3 | 02:20:15 | 125 s | 02:22:20.755 | 02:22:21.564 | 0.81 s | 0.813 s | 0 | yes | yes (`World saved! Saved 0 chunks, 0 mapchunks, 16 mapregions.`) |
| extra (VSS-zws second start) | 02:22:40 | 6 s | 02:22:46.092 | 02:22:46.938 | 0.85 s | 0.851 s | 0 | yes | yes (`World saved! Saved 0 chunks, 0 mapchunks, 16 mapregions.`) |

No `server_stop_timeout` and no `server_killed` in any round. `server-main.log` between the stop and the exit, round 1 verbatim (rounds 2 and 3 print the same lines in the same order, only the timestamps and the save counts differ; no addresses appear):

```
19.11.2026 02:14:24 [Notification] Server termination event SIGTERM received. Shutting down server
19.11.2026 02:14:24 [Notification] Server: Exit() called
19.11.2026 02:14:24 [Notification] Server stop requested, begin shutdown sequence. Stop reason: External close event SIGTERM received
19.11.2026 02:14:24 [Notification] Server ticking has been suspended
19.11.2026 02:14:25 [Notification] Entering runphase Shutdown
19.11.2026 02:14:25 [Event] Mods and systems notified, now saving everything...
19.11.2026 02:14:25 [Event] It pauses.
19.11.2026 02:14:25 [Event] One last gaze...
19.11.2026 02:14:25 [Event] Saved player world data...
19.11.2026 02:14:25 [Event] Saved map regions...
19.11.2026 02:14:25 [Event] Then all goes quiet...
19.11.2026 02:14:25 [Event] Saved map chunks...
19.11.2026 02:14:25 [Event] The waters recede...
19.11.2026 02:14:25 [Event] Saved loaded chunks...
19.11.2026 02:14:25 [Event] The mountains fade...
19.11.2026 02:14:25 [Event] The dark settles in.
19.11.2026 02:14:25 [Event] Saved generating chunks...
19.11.2026 02:14:25 [Event] Saved savegamedata...2
19.11.2026 02:14:25 [Event] World saved! Saved 8 chunks, 1 mapchunks, 16 mapregions.
19.11.2026 02:14:25 [Event] It sighs...
19.11.2026 02:14:25 [Event] Shutting down 10 server threads... 
19.11.2026 02:14:25 [Event] Killed console thread
19.11.2026 02:14:25 [Event] Alone again...
19.11.2026 02:14:25 [Event] All threads gracefully shut down
19.11.2026 02:14:25 [Event] Time to rest.
19.11.2026 02:14:25 [Event] Doing last tick...
19.11.2026 02:14:25 [Event] Stopped the server!
```

**Stop verdict (AC 10):** every stop ended in under 1 s with exit code 0, and the world save completed (`World saved!`) before `Stopped the server!`. The 10 s timeout is not a risk on this world; no stop-timeout question for the maintainer.

**`VSS-zws` (AC 11)**, after round 3's start (ready 02:20:15, edits at 02:21:11):

| Read | When | `Port` | `ServerName` |
|---|---|---|---|
| 1 | before the edit, game running | 42420 | `Vintage Story Server` |
| 2 | after `POST /config/game/settings/Port {"value": 42421}` (answer `method: file_update`, `pending_restart: true`; API logged `restart_required`) | **42421** | `Vintage Story Server` |
| 3 | after `POST /config/game/settings/ServerName {"value": "vss-22-3 zws check"}` (answer `method: console_command`; console `[CMD] /serverconfig name vss-22-3 zws check`, game answered `Handling Console Command /serverconfig name vss-22-3 zws check` and `Server name set to vss-22-3 zws check`) | **42420** | `vss-22-3 zws check` |
| 4 | after the stop (round 3) | 42420 | `vss-22-3 zws check` |
| 5 | after the next start (game: `Dedicated Server now running on Port 42420 and all ips!`) | 42420 | `vss-22-3 zws check` |
| 6 | after the final stop | 42420 | `vss-22-3 zws check` |

**`VSS-zws` verdict:** the game **does** overwrite `serverconfig.json` edits made while it runs. A live `/serverconfig` command makes it write its in-memory config back to the file at once (read 3, within about 3 s of the command), which put `Port` back to 42420; the next start then listened on 42420, so the restart-required `Port` change was lost silently, although the API had flagged a pending restart (and the start then cleared the flag, Story 22.2). Story 1.7's stop rule applies: see Completion Notes.

**Time zone (1.4):**

```
$ docker run --rm --name vss-22-3-tz --platform linux/amd64 vss-22-3-measure:local uv run --no-sync python -c "from tzlocal import get_localzone; print(get_localzone())"
Etc/UTC
$ docker run --rm --name vss-22-3-tz --platform linux/amd64 -e TZ=Europe/Berlin vss-22-3-measure:local uv run --no-sync python -c "from tzlocal import get_localzone; print(get_localzone())"
Europe/Berlin
```

Without `TZ` the zone is `Etc/UTC` (the story expected the text `UTC`; same zone: the image's `/etc/localtime` links to `/usr/share/zoneinfo/Etc/UTC` and `TZ` is empty). With `TZ=Europe/Berlin` it is `Europe/Berlin`.

**Commands** (repo root; `api.sh METHOD PATH [json]` is a scratch wrapper around `curl -s -H "X-API-Key: vss-22-3-placeholder-admin-key" -H "Content-Type: application/json" -X METHOD http://127.0.0.1:18090PATH -d json`):

```bash
docker rm -f vss-22-3-measure vss-22-3-tz >/dev/null 2>&1 || true
docker build --platform linux/amd64 -t vss-22-3-measure:local .
docker run -d --name vss-22-3-measure --platform linux/amd64 -p 127.0.0.1:18090:8080 \
  -e VS_API_KEY_ADMIN=vss-22-3-placeholder-admin-key -e VS_DATA_DIR=/data vss-22-3-measure:local
api.sh POST /api/v1alpha1/server/install '{"version":"stable"}'      # poll GET .../server/install/status
# each round: start, wait for "now running" in server-main.log, sleep 60, then:
api.sh POST /api/v1alpha1/server/start
docker exec vss-22-3-measure grep 'now running' /data/serverdata/Logs/server-main.log
curl -s -o /dev/null -w '%{time_total}' -H "X-API-Key: ..." -X POST http://127.0.0.1:18090/api/v1alpha1/server/stop
docker logs vss-22-3-measure 2>&1 | grep -E 'stopping_server|server_stopped_gracefully|server_stop_timeout|server_killed'
docker exec vss-22-3-measure sh -c 'tail -n +<lines before the stop + 1> /data/serverdata/Logs/server-main.log'
# VSS-zws (after round 3's start), reading Port and ServerName with docker exec ... python3 json.load:
api.sh POST /api/v1alpha1/config/game/settings/Port '{"value": 42421}'
api.sh POST /api/v1alpha1/config/game/settings/ServerName '{"value": "vss-22-3 zws check"}'
api.sh GET /api/v1alpha1/console/history
# cleanup
docker rm -f vss-22-3-measure vss-22-3-tz; docker image rm vss-22-3-measure:local
docker ps -a --filter name=vss-22-3    # empty
docker image ls vss-22-3-measure       # empty
```

Cleanup done: the container and the image were removed; both listings were empty; `git status --short dev/` was empty.

### Debug Log References

- Round 2 ran 300 s instead of about 60 s before its stop: the wait for the ready line compared line counts of `server-main.log`, but the game moves its logs to `Logs/Archive/<start time>/` at each start, so the count was stale and the wait ran its full 240 s. The game was ready at 02:14:46 (14 s after the start). Round 3 used a plain `grep` after a short pause. A longer run makes the stop's save larger, not smaller, so the round stands.

### Completion Notes List

- 2026-11-18: Story created (create-story, non-interactive) and checked against the create-story checklist: 6 tasks; every code task carries its tests (Task 1 is a measurement, Task 5 documentation, Task 6 validation); every AC is mapped to a task (AC 13 to Task 6 and every task's test run, AC 14 to Task 6.3). Ultimate context engine analysis completed - comprehensive developer guide created.
- 2026-11-19: Task 1 done (dev-story). Stops: 0.83 s, 0.73 s, 0.81 s (and 0.85 s for an extra stop), exit code 0, world saved before exit every time: no stop-timeout question.
- 2026-11-19: **Task 1.7 stop rule triggered by `VSS-zws`.** A live `/serverconfig` command (here `ServerName` through the API) makes the game write its in-memory config to `serverconfig.json` at once, which reverted the API's pending `Port` edit (42421 back to 42420); the next start listened on 42420 and the pending-restart flag was cleared by that start, so the change was lost silently. Neither the 10 s timeout nor `services/game_config.py` was changed. Question for the maintainer: fix `VSS-zws` in this story (the small fix ADR-8 decision 3 names: keep the restart-required edits made while the game runs and re-apply them to `serverconfig.json` after the stop, before the next start; note the overwrite already happens at the live command, not only at shutdown, so a fix must survive both), fix it in its own story, or accept and document it. Tasks 2 to 6 wait for the controller's answer; the story stays `in-progress`.
- 2026-11-19: Deviation (Task 1): `get_localzone()` printed `Etc/UTC` without `TZ` where the story expected `UTC`; the same zone (`/etc/localtime` links to `Etc/UTC`).

### File List

- `_bmad-output/implementation-artifacts/22-3-scheduled-restarts.md` (Task 1 record, status)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (through `just sprint` only: in-progress)
- `_bmad-output/planning-artifacts/architecture/epic-22-server-operations-and-metrics.md` (ADR-8 "Results (Story 22.3)")

## Change Log

- 2026-11-18: Story 22.3 created (ready-for-dev).
- 2026-11-18: Validated against the create-story checklist, the epic, ADR-5 to ADR-8 and ADR-14, and the code at 1e44ab00 (APScheduler 3.11.3 behaviour re-run in a scratch venv): busy checked before running at the restart (AC 7), `DELETE /jobs/{id}` and an API start inside the window documented as they behave, `send_command` exceptions and `safe_job`'s `_completed` line stated, the throwaway container's isolation and why `just test-e2e-ci` cannot be reused, the web's camelCase name for Story 22.6.
- 2026-11-19: Task 1 done: the stop measured (under 1 s, world saved, three rounds) and `VSS-zws` confirmed (a live `/serverconfig` command reverts a pending `Port` edit). Stopped at Task 1.7 for the maintainer.
