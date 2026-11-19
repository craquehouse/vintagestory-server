# Epic 22: Server Operations and Metrics - Architecture Decisions

Decisions from the Epic 22 course correction (2026-11-18). Epic 22 has no preparation story: the facts below were checked in planning, and the unknowns that remain (how long a world save takes on stop, whether the game prunes its own log archives, and `VSS-zws`) are tasks inside Stories 22.3 and 22.4. Each fact was checked by reading or running the code at commit `e16a7932` (`main` after Epic 21 and release `v0.1.0-rc.7`, with the dev stack's port moved to 9080); file and line references are to that commit.

The scope is three open beads the maintainer named: `VSS-bhw` (game server metrics on `/metrics`), `VSS-29p` (scheduled restarts, disk cleanup and log rotation) and `VSS-9jv` (the interval fields cannot turn a job off; metrics collection has no field). On 2026-11-18 the maintainer answered eleven questions, one at a time; the status lines say which answer each ADR carries. `VSS-zws` is pulled in on his answer. ADRs or decisions marked "Planner" had no open question and are not reviewed yet.

| Story | ADRs |
|---|---|
| 22.1 Players Online Are Counted | ADR-1, ADR-2, ADR-14 |
| 22.2 A Prometheus `/metrics` Endpoint | ADR-3, ADR-4, ADR-14 |
| 22.3 Scheduled Restarts | ADR-5, ADR-6, ADR-7, ADR-8, ADR-14 |
| 22.4 Log Archive and Backup Cleanup | ADR-7, ADR-9, ADR-10, ADR-14 |
| 22.5 Interval Fields Can Turn Jobs Off | ADR-11, ADR-12 |
| 22.6 Restart and Cleanup Settings in the UI | ADR-13 |

## Facts Checked in the Code

**Metrics today.**

- `MetricsSnapshot` (`api/src/vintagestory_api/models/metrics.py:12`) already holds `game_memory_mb` and `game_cpu_percent` next to the API's own memory and CPU; `MetricsService.collect()` (`services/metrics.py:127`) fills them with psutil from `ServerService.game_server_pid` and records `None` when the game is not running (`:207`). The snapshots sit in a 360-sample ring buffer and are served as camelCase JSON by `GET /api/v1alpha1/metrics/current` and `/history` (`routers/metrics.py`).
- The collection job `metrics_collection` runs every `metrics_collection_interval` seconds (default 10, 0 = off; `services/api_settings.py`, `jobs/__init__.py:37`).
- Uptime is computed from `_server_start_time` in `ServerService.get_server_status()` (`services/server.py:912-914`) and returned as `uptime_seconds` in the server status and as `game_server_uptime` in `/healthz` (`routers/health.py:144`).
- No Prometheus endpoint exists and `prometheus-client` is not a dependency (`api/pyproject.toml`). The PRD lists one (`prd.md:147`, `:185`, `:283`: "Prometheus `/metrics` endpoint", scraped for a Grafana dashboard) and the architecture deferred it as post-MVP (`architecture/core-architectural-decisions.md:21`).
- `/healthz` and `/readyz` are mounted at the root without an API key (`main.py:386`); every `/api/v1alpha1` route requires `X-API-Key` (`main.py:389`). The routers are registered before `register_frontend` (`main.py:416`), and the web has no `/metrics` route (`web/src/App.tsx:123-142`), so a root `/metrics` route does not clash with the web UI.
- `MaxClients` is a known game setting (`services/game_config.py:123`), read from `serverconfig.json`.

**Players.**

- The manager starts the game with piped stdin, stdout and stderr (`services/server.py:1014-1020`). `_read_stream` (`:1234`) decodes each line and appends it to the console buffer; there is no other reader of the game's output.
- No player count exists anywhere in the API or the web.
- `VintagestoryLib.dll` of v1.22.7 holds these literals (read from its user-string heap in planning): `'{0} {1} joins.'`, `'Player {0} left.'`, `'Client {0} disconnected.'` and `'{0} joined again, killing previous client.'`. Its `assets/game/lang/en.json` holds the chat messages `"{0} joined. Say hi :)"` and `"Player {0} left."`. The dev stack has never had a client, so its logs hold no such line; what the game prints before the literal (timestamp, `[Server Event]` or another tag) and what the second field of the joins line is (an address, probably) are not observed. The maintainer confirms both from one anonymised real line of each (Story 22.1 manual check).

**Restarts.**

- `restart_server()` (`services/server.py:1155`) takes the lifecycle lock, stops the game if it runs and starts it, then clears the pending-restart flag. The Restart button uses it (`routers/server.py:324`).
- A stop sends SIGTERM and kills the process after `timeout` seconds, 10 by default (`services/server.py:1058`, `:1073-1110`). Whether the game finishes saving the world inside 10 seconds is not known.
- `send_command()` (`:1265`) writes a line to the game's stdin and echoes it to the console with a `[CMD]` prefix. The game has `/announce <message>` (`agentdocs/server-commands.md:542`).
- The game is never restarted automatically today: `_monitor_process` (`:1201`) records the exit and does nothing else.
- `SchedulerService.add_cron_job()` (`services/scheduler.py:160`) wraps APScheduler 3's `CronTrigger.from_crontab`; no cron job is registered by the API today. The scheduler uses the process's local time zone.
- The container's clock is UTC; tzdata is installed and no `TZ` is set (`Dockerfile`, `docker-compose*.yaml`).
- `scheduler.py` carries fourteen `# type: ignore` comments for APScheduler, which ships no types, and `models/jobs.py:51-74` more. They predate the project's suppression rule; new code adds none.

**Settings.**

- `ApiSettings` (`services/api_settings.py:34`) holds booleans, three intervals bounded by `MAX_INTERVAL_SECONDS = 31_536_000` (`:26`) and the webhook URL. `update_setting()` (`:246`) coerces booleans and integers, passes anything else to Pydantic, saves atomically and then calls the scheduler callback for the keys in `INTERVAL_SETTINGS` (`:102`, `:328`); a failure there raises `ApiSettingNotAppliedError`, and the web shows "Saved, not applied yet".
- The router builds the service with `scheduler_callback=partial(apply_interval_setting, scheduler)` (`routers/config.py:277`). `GET` and `POST /config/api` are Admin only (`routers/config.py:283`, `:325`).

**Disk and logs.**

- The game writes `server-main.log`, `server-debug.log`, `server-audit.log`, `server-chat.log`, `server-build.log` and `server-worldgen.log` into `serverdata/Logs/`. At start it moves the previous run's files into `serverdata/Logs/Archive/<YYYY-MM-DD_HH_MM_SS>/` (one such directory observed on the dev stack). Whether it ever deletes an archive is not known; with one archive it cannot be seen.
- `serverconfig.json` holds `"LogFileSplitAfterLine": 500000`: the game splits a log file itself.
- `serverdata/Backups/` (written by `/genbackup`) and `serverdata/BackupSaves/` (the game's own backups of the world) exist and were empty on the dev stack.
- The mod download cache is already kept under `VS_MOD_CACHE_MAX_SIZE_MB` by LRU eviction (`services/cache_eviction.py`, `config.py:55`).
- The manager logs to stdout only; `vsmanager/logs/` exists and is empty (`config.py:268-270`). Docker or Kubernetes rotate stdout.

**The API Settings tab.**

- `ApiSettingsPanel.tsx` has duration fields for Mod List Refresh (`min={60}`, `max={86400}`, `:162-163`) and Server Versions Refresh (`max={604800}`, `:173-174`), while the API accepts up to 31,536,000 seconds. Neither can be set to 0 (off). There is no field for `metrics_collection_interval`.
- Two fallbacks differ from the API defaults: `serverVersionsRefreshInterval ?? 3600` (`:172`; the API default is 86400) and `enforceEnvOnRestart ?? true` (`:145`; the API default is false).
- `SettingsPage.tsx:51` shows the API Settings tab to every role, but its data is Admin only, so a Monitor key gets "Failed to load settings". The Scheduled Jobs tab is already hidden for Monitor (`:59`).
- `GET /api/v1alpha1/jobs` (Admin) returns each job's `next_run_time`, `trigger_type` and `trigger_details` (`models/jobs.py:19-32`); the Scheduled Jobs tab lists them.

## ADR-1: Players Are Counted from the Game's Join and Leave Lines

**Status:** Accepted (Matt, 2026-11-18): the count comes from parsing the console's join and leave lines, not from polling `/list clients` (answer 4). Decisions 2 to 6 are the planner's. Implemented by Story 22.1.

**Context:** `VSS-bhw` asks for concurrent players. The manager owns the game's output, and the game prints a line when a player joins or leaves. Polling `/list clients` would put a command and its reply in the console at every interval.

**Decision:**

1. **A `PlayerTracker` service holds the set of names online.** `_read_stream` passes every decoded line to it (after the console append, so a tracker fault never loses a console line; a fault is logged and the line is dropped from counting only).
2. **Three patterns, anchored at the end of the line, after any prefix:** `^(?P<name>.+) \S+ joins\.$` adds the name; `^Player (?P<name>.+) left\.$` removes it; `^(?P<name>.+) joined again, killing previous client\.$` changes nothing (the name stays in the set once). `Client N disconnected.` is not used: it names a client number, not a player, and the leave line follows it. The prefix the game prints (timestamp and tag) is matched by a separate prefix pattern fixed in the story from the maintainer's sample; until the sample arrives the tests pin the literal part only.
3. **The set is emptied when the game starts, when it is stopped and when the process exits** (`_start_server_locked`, `_stop_server_locked`, `_monitor_process`). The count is 0 whenever the game is not running.
4. **Names never leave the tracker.** The API returns the count only. Names are not logged at INFO or above; a DEBUG line says `player_joined` / `player_left` with the new count, not the name.
5. **A leave line for a name not in the set changes nothing and logs at DEBUG.** A join for a name already in the set changes nothing.
6. **Tests:** each pattern with a line built from the literals above and a placeholder name (`ExamplePlayer`, a documentation address such as `203.0.113.5:42420`), names with spaces, a line that only contains "joins." inside chat text (a player typing it is not counted: a chat line has its own prefix, which the prefix pattern rejects), the three resets, and a line from the maintainer's sample once confirmed.

**Consequences:** A format change in a game update makes the count wrong until the patterns are updated; the pinned tests and the manual check make that visible. The count is the manager's view: after an API restart with the game still running (impossible today, since the game is the API's child process) it would start at 0.

**Results (Story 22.1):** The maintainer's sample (game 1.22.7, a real client on the dev stack, 2026-11-19, anonymised) settled the prefix. The manager's console, the game's stdout that the tracker reads, tags the lines `[Server Event]`: `19.11.2026 16:33:41 [Server Event] ExamplePlayer [::ffff:203.0.113.5]:53382 joins.` and `19.11.2026 16:34:28 [Server Event] Player ExamplePlayer left.`. The game's `server-main.log` carries the same messages tagged `[Event]`. The prefix drafted from the log file (`^[^\[]*\[Event\] `) never matched stdout, so the count was always 0; the prefix is now `^[^\[]*\[(?:Server )?Event\] ` and accepts both tags, still with nothing but a timestamp before the tag, so a chat line cannot match. The stdout lines carry no ANSI escape codes. The three message patterns of decision 2 matched the sample unchanged (the address is an IPv4-mapped IPv6 one, `[::ffff:...]:port`, one `\S+` token). One more fact for decision 2: a first connection that dropped while spawning logged only `Client 1 disconnected.`, with no join and no leave line, so ignoring that line is right and the set never held the name. The Players card showing 1 with a real client connected is the maintainer's check (Story 22.1, Task 6.4).

## ADR-2: The JSON Metrics Carry `playersOnline`, and the Dashboard Shows a Players Card

**Status:** Accepted (Matt, 2026-11-18): players are added to the JSON snapshot and the dashboard as well as to Prometheus (answer 1). The field's shape and the card are the planner's. Implemented by Story 22.1.

**Decision:**

1. `MetricsSnapshot` gains `players_online: int | None`: the tracker's count while the game runs, `None` otherwise, like `game_memory_mb`. `MetricsSnapshotResponse` serialises it as `playersOnline`. The field is additive.
2. The web type `MetricsSnapshot` gains `playersOnline: number | null`.
3. The dashboard gains a Players card next to Uptime, built like `UptimeCard`: the count from the current snapshot, "Server stopped" when the game is not running, and `of N` when `MaxClients` is known from the game settings the dashboard can already read; if reading it would need a new request, the card shows the count only (the story decides from the code and says which).
4. The history chart is not changed.

## ADR-3: `/metrics` Is a Prometheus Endpoint at the Root, Open Like `/healthz`, Read Live

**Status:** Accepted (Matt, 2026-11-18): a Prometheus text endpoint at the root, built with `prometheus-client` (answer 1); open without a key like `/healthz` (answer 2). Decisions 3 to 6 are the planner's. Implemented by Story 22.2.

**Decision:**

1. **Dependency:** `prometheus-client` with a minimum version and the next major excluded (`>=0.21,<1`, or the current release's minor as the floor), recorded in `api/uv.lock`.
2. **Route:** `GET /metrics` on the health router's level (root, not versioned, no `get_current_user`), returning `generate_latest(registry)` with `CONTENT_TYPE_LATEST`. Not an ASGI mount, so the request context and CORS middleware apply as for `/healthz`. `HEAD` is not added.
3. **Own registry:** a module-level `CollectorRegistry` (not the global `REGISTRY`), holding the project's custom collector and `ProcessCollector`, `PlatformCollector` and `GCCollector` for the manager itself. Tests build their own registry, so no test leaks series into another.
4. **Read live at scrape time.** A custom collector's `collect()` reads the server status, the tracker, the pending-restart state, the game settings' `MaxClients` and psutil for the game process each time it is scraped. It does not read the ring buffer, so `/metrics` works with `metrics_collection_interval = 0`, and the game's CPU is a counter of seconds (`cpu_times().user + system`), not a sampled percentage.
5. **Failure of one source does not fail the scrape:** a source that raises is logged once per scrape at WARNING and its series are left out; the endpoint answers 200 with the rest.
6. **No authentication, no rate limit.** The data is counts, CPU, memory, uptime and the game version: no names, paths or keys. The README says it is open and how to keep it from the internet (do not publish it through the reverse proxy, or block `/metrics` there).

**Consequences:** One new runtime dependency (approved by the answer). The endpoint exposes the game version to anyone who can reach the API, as `/healthz` already does (`game_server_version`).

## ADR-4: Metric Names and Labels

**Status:** Accepted (Matt, 2026-11-18): the bead's four metrics plus the extras listed here (answer 3). Absence rules (decision 2) are the planner's. Implemented by Story 22.2.

**Decision:**

1. The series, all with the `vintagestory_` prefix and in base units:

   | Name | Type | Labels | Value |
   |---|---|---|---|
   | `vintagestory_server_info` | gauge | `version` | 1; the installed game version |
   | `vintagestory_server_up` | gauge | | 1 while the game is running, else 0 |
   | `vintagestory_server_state` | gauge | `state` | one series per server state (`not_installed`, `installed`, `starting`, `running`, `stopping`, ...), 1 for the current one |
   | `vintagestory_server_uptime_seconds` | gauge | | seconds since the game started |
   | `vintagestory_players_online` | gauge | | the tracker's count; 0 when not running |
   | `vintagestory_players_max` | gauge | | `MaxClients` from `serverconfig.json` |
   | `vintagestory_server_pending_restart` | gauge | | 1 when a change waits for a restart |
   | `vintagestory_server_process_cpu_seconds_total` | counter | | the game process's user and system CPU seconds |
   | `vintagestory_server_process_resident_memory_bytes` | gauge | | the game process's RSS |

   Plus `process_*`, `python_info` and `python_gc_*` for the manager from the default collectors.
2. **Absent, not 0:** `uptime_seconds` and the two `server_process_*` series are absent when the game is not running; `info` is absent when no game is installed; `players_max` is absent when the setting cannot be read. `up`, `state`, `players_online` and `pending_restart` are always present.
3. The state label's values are `ServerState`'s values, so a new state adds a series and needs no change here.
4. Each series has a `# HELP` text in plain English.

## ADR-5: A Restart Schedule Is a List of Daily Times in the Container's Time Zone

**Status:** Accepted (Matt, 2026-11-18): daily `HH:MM` times, empty by default, in the container's time zone (answer 5). The limits in decision 2 are the planner's. Implemented by Story 22.3.

**Decision:**

1. **Setting:** `scheduled_restart_times: list[str]` in `ApiSettings`, default `[]` (no scheduled restart).
2. **Validation (a Pydantic validator):** each entry is `HH:MM`, 24-hour, `00:00` to `23:59`, two digits each; at most 24 entries; duplicates are removed; the list is stored sorted. An invalid list answers 400 `API_SETTING_INVALID` naming the entry, not changing anything.
3. **`update_setting` accepts a list for this key:** a JSON array of strings. It is the first list-valued API setting; the type coercion branch is extended for lists, not bypassed.
4. **Time zone:** the times are read in the container's local time zone, which is `TZ` (UTC when unset). The README documents `TZ` (an example value `Europe/Berlin`) in the configuration table and says scheduled restarts and cleanup follow it. No time zone setting is added.

## ADR-6: One Cron Job per Restart Time Warns at 15, 5 and 1 Minutes, Then Restarts Through the Restart Button's Path

**Status:** Accepted (Matt, 2026-11-18): warnings at 15, 5 and 1 minutes with fixed text, only while the game runs (answer 6); a restart whenever the game is running, players or not, never a start of a stopped game (answer 7). The job layout (decisions 1 to 3 and 6) is the planner's.

**Decision:**

1. **One cron job per time, id `scheduled_restart_HHMM`** (for example `scheduled_restart_0400`), firing 15 minutes before the time. Its function runs the sequence: announce 15 minutes, wait 10 minutes, announce 5 minutes, wait 4 minutes, announce 1 minute, wait 1 minute, restart. The waits use an injectable sleep so tests run without real time.
2. **The texts are fixed:** `Server restarts in 15 minutes`, `Server restarts in 5 minutes`, `Server restarts in 1 minute`, each sent as `/announce <text>` through `send_command`.
3. **At each step the job checks that the game is running.** If it is not, the job ends with `scheduled_restart_skipped reason=not_running`. A stopped game is never started.
4. **The restart calls `ServerService.restart_server()`,** the Restart button's path, which also clears the pending-restart flag. If the lifecycle lock is held when the restart is due (a manual start, stop, restart, install or uninstall in progress), the job does not wait: it logs `scheduled_restart_skipped reason=lifecycle_busy`. A failure of the restart is logged at ERROR with the error code; the job is not retried.
5. **Players online do not matter** (answer 7). The log line of each restart says how many were online.
6. **A time less than 15 minutes ahead when it is saved first runs the next day** (the cron job's first fire time has passed). The README and the setting's help text say so. A job's `max_instances` stays 1, so two times 15 minutes apart or less cannot overlap a sequence; the validator rejects times closer than 16 minutes to each other on the same day, with the reason in the message.
7. **The Scheduled Jobs tab shows the jobs** with their next run time, which is the warning time (15 minutes before the restart); the job id names the restart time. Nothing else is added to the jobs API.

**Consequences:** `max_instances: 1` and `coalesce: True` (`scheduler.py:62-64`) mean a missed fire (the API down at that time) runs within the 60-second grace or not at all; a restart is never made up later.

## ADR-7: A Settings Change Applies Its Jobs Through One Function

**Status:** Planner. Implemented by Story 22.3 and used by Story 22.4.

**Context:** The scheduler callback runs only for `INTERVAL_SETTINGS` and takes `(key, seconds)`. Restart times are a list, and the cleanup settings are read when the job runs.

**Decision:**

1. `jobs/__init__.py` gains `apply_setting(scheduler, key, value)`: for an interval key it calls `apply_interval_setting` as today; for `scheduled_restart_times` it calls `apply_restart_schedule(scheduler, times)`, which removes every `scheduled_restart_*` job not in the list and adds or replaces the others. Other keys do nothing.
2. `INTERVAL_SETTINGS` in `api_settings.py` is replaced by `SCHEDULED_SETTINGS` (the interval keys and `scheduled_restart_times`), and the router passes `partial(apply_setting, scheduler)`. The error path stays: any exception after the save raises `ApiSettingNotAppliedError`, and the web shows "Saved, not applied yet". The test that keeps the service's keys and the jobs module's keys equal is kept for the new name.
3. `register_default_jobs` applies `scheduled_restart_times` at start-up and always registers `disk_cleanup` (ADR-9).
4. Cleanup settings (`log_archive_retention_days`, `log_archive_keep_min`, `backup_keep_count`) are not scheduled settings: the job reads them when it runs, so a change applies at the next run.

## ADR-8: The Stop Timeout Is Measured, Not Changed, and `VSS-zws` Is Checked in the Same Run

**Status:** Planner for decisions 1 to 3; `VSS-zws` is pulled in on the maintainer's answer (Matt, 2026-11-18, answer 11). Implemented by Story 22.3.

**Context:** A scheduled restart runs while players are online, so a world save cut short by the 10-second kill would lose their progress. Nobody has measured how long the game takes to stop. `VSS-zws` asks whether the game overwrites `serverconfig.json` edits made while it runs, which needs a running game to be stopped and restarted.

**Decision:**

1. **One task of Story 22.3 runs a throwaway container** (a `vss-22-3-*` name, built from the branch; never the dev stack, whose game server is not started or stopped). With a fresh world it measures, three times: the time from SIGTERM to exit, whether the exit is within 10 seconds, and whether `server-main.log` shows the world saved before exit.
2. **If the stop takes longer than 10 seconds or the save is cut short,** the story stops and asks the maintainer (raise the timeout, send `/autosavenow` before the stop, or `/stop` instead of SIGTERM). The timeout is not changed without that answer.
3. **`VSS-zws` in the same container:** change `Port` (restart-required) through the API while the game runs, run a live `/serverconfig` command, stop the game, and read `serverconfig.json`; then restart and read it again. The story records the result in the bead and in this ADR's consequences. If the game overwrites the edit and the fix is small (for example re-applying pending file edits after the stop), it is done in the story; otherwise the story asks the maintainer.
4. The results, with the commands used, go into the story file and the pull request. No instance data.

**Results (Story 22.3):** measured on 2026-11-19 in a throwaway `vss-22-3-measure` container (image built from `story/22-3-scheduled-restarts`, `linux/amd64` emulated on an arm64 host), game 1.22.7, fresh world. Three stops after 69 s, 300 s and 125 s of running took 0.83 s, 0.73 s and 0.81 s from `stopping_server` to `server_stopped_gracefully` (an extra stop: 0.85 s), each with exit code 0, no `server_stop_timeout` or `server_killed`, and `server-main.log` showing `World saved! ...` before `Stopped the server!`: the 10-second timeout is not a risk here (decision 2 is not triggered). `VSS-zws` is confirmed: with the game running, `Port` 42420 -> 42421 through the API wrote the file (`pending_restart: true`); a live `ServerName` change (`/serverconfig name ...`) then made the game write its in-memory config to `serverconfig.json` at once, which put `Port` back to 42420; the file still held 42420 after the stop and after the next start, and the game listened on 42420. The edit is lost silently. Under the controller's instruction for Story 22.3 no fix was made; the question went to the maintainer (story file, Task 1.7 and Completion Notes, with the full record and commands).

## ADR-9: Disk Cleanup Deletes Old Log Archives, and Backups Only When Asked

**Status:** Accepted (Matt, 2026-11-18): log archives older than 14 days, the newest 5 always kept; `Backups/` kept to the newest N with N = 0 (keep all) by default; `BackupSaves/` and the world never touched (answer 8). The daily time and the safety rules are the planner's. Implemented by Story 22.4.

**Decision:**

1. **Settings in `ApiSettings`:** `log_archive_retention_days` (default 14, 0 = keep all, at most 3650), `log_archive_keep_min` (default 5, 0 to 1000), `backup_keep_count` (default 0 = keep all, at most 1000).
2. **A `DiskCleanupService`** with one method that returns what it deleted (count and bytes per kind), separate from the job so it can be tested on a temporary directory.
3. **Log archives:** only directories directly inside `serverdata/Logs/Archive/` whose name matches `^\d{4}-\d{2}-\d{2}_\d{2}_\d{2}_\d{2}$`. The age comes from the name (parsed in the container's time zone), not from file times. Sorted newest first, the first `log_archive_keep_min` are kept, and of the rest those older than `log_archive_retention_days` are deleted with `shutil.rmtree`. A name that does not match is left alone and logged at DEBUG.
4. **Backups:** only regular files directly inside `serverdata/Backups/`, newest by modification time first; with `backup_keep_count` above 0, every file after the first N is deleted. Directories in `Backups/` are left alone.
5. **Never:** `BackupSaves/`, `Saves/`, `Mods/`, `Playerdata/`, the live `server-*.log` files, the manager's state and cache. Nothing reached through a symbolic link is deleted: a symlinked `Archive` or `Backups` directory, or a symlinked entry inside one, is skipped and logged at WARNING. Every path is resolved and checked to be inside `serverdata` before deletion.
6. **The job `disk_cleanup`** is a cron job at 03:00 in the container's time zone, always registered, reading the settings when it runs. It runs whether the game is running or not (archives are only the previous runs'; the game writes only the live files). Each deletion is logged at INFO (`disk_cleanup_deleted`, kind, name, bytes); the run ends with `disk_cleanup_finished` and the totals. An error on one entry is logged and the run continues.
7. **A throwaway-container task in Story 22.4** starts and stops a game more than `log_archive_keep_min` times (or as many as the time box allows) to confirm the archive name format and that the game does not prune archives itself, and runs the cleanup against them. Never on the dev stack.

## ADR-10: Log Rotation Is the Game's; the Manager Only Deletes Old Archives

**Status:** Accepted (Matt, 2026-11-18, answer 9). Implemented by Story 22.4.

**Decision:**

1. The manager adds no rotation of its own and does not touch the live `server-*.log` files.
2. The README gains a short "Logs and disk use" section: the game archives its logs at every start and splits a file after `LogFileSplitAfterLine` lines (a game setting); the manager deletes old archives (ADR-9) and, on request, old backups; the manager's own log is stdout, rotated by Docker's log driver (`max-size`, `max-file` in the compose file's `logging` section, an example given) or by Kubernetes.
3. `VSS-29p` closes when Stories 22.3 and 22.4 are done.

## ADR-11: Each Interval Field Has an On Switch, and Metrics Collection Gets a Field

**Status:** Accepted (Matt, 2026-11-18): an On switch per interval; the refresh fields 60 seconds to 365 days; Metrics Collection 1 second to 1 hour, default 10 seconds (answer 10). Decisions 4 and 5 are the planner's. Implemented by Story 22.5.

**Decision:**

1. **The switch:** each of the three interval settings shows a switch labelled "On" beside its label. Turning it off saves 0 and hides the duration input, showing "Off". Turning it on saves the API's default for that setting (14400, 86400, 10) and shows the input. The saved value decides the switch: 0 is off.
2. **Bounds:** Mod List Refresh and Server Versions Refresh accept 60 seconds to 31,536,000 seconds (365 days), matching the API's maximum; Metrics Collection accepts 1 second to 3600 seconds.
3. **Metrics Collection's help text** says that when it is off the dashboard charts stop updating, and that `/metrics` is read live and keeps working.
4. **Fallbacks match the API defaults:** `serverVersionsRefreshInterval ?? 86400`, `enforceEnvOnRestart ?? false`. The defaults live in one web constant next to `INTERVAL_API_SETTINGS` (`web/src/api/config.ts`), used by the fallbacks and by "on".
5. **The switch is built into `DurationSettingField`** as an optional `offValue`/`onValue` pair, so other duration fields are unchanged.
6. A save failure keeps today's behaviour: one toast, and "Saved, not applied yet" for `API_SETTING_NOT_APPLIED` (ADR-7 of Epic 21 for the single toast).

## ADR-12: A Monitor Key Does Not See the API Settings Tab

**Status:** Planner; told to the maintainer with the pull-in question (Matt, 2026-11-18, answer 11) and not objected to. Implemented by Story 22.5.

**Decision:** `SettingsPage` shows the API Settings tab and its content only to Admin, as it already does for Scheduled Jobs. A Monitor key lands on UI Preferences. A deep link or stored tab value of `api-settings` falls back to UI Preferences for Monitor. A unit test for each role and an E2E check with the Monitor key (precondition skip when the key is not configured, as the existing Monitor specs do; base URL default `http://localhost:9080`).

## ADR-13: Restart Times and Cleanup Limits Are Edited in the API Settings Tab

**Status:** Planner. Implemented by Story 22.6.

**Decision:**

1. **A "Scheduled Restarts" group** below Server Behavior: a list of time inputs (`<input type="time">`, 24-hour value) with Remove buttons and an Add time button, saved as one list when an entry changes and is valid. The help text says the times are in the server's time zone (`TZ`, UTC unless set), that players are warned at 15, 5 and 1 minutes, that a stopped server is not started, and that a time less than 15 minutes ahead first runs the next day. A 400 from the API keeps the edited list and shows the message.
2. **A "Disk Cleanup" group** with three number fields (Log archive retention in days, Archives always kept, Backups kept), each with "0 keeps all" in its help text, using `SettingField` with the API's bounds.
3. **The next restart time is not shown** in this group. The Scheduled Jobs tab already lists each `scheduled_restart_HHMM` job with its next run (the warning time); showing a computed restart time here would need either a new API field or a second request for jobs, and is left out.
4. The web type for API settings gains the four fields; the transform at the client boundary is unchanged (camelCase).

## ADR-14: Restarts, Cleanup and Players Are Tested with Stubs and Throwaway Containers, Never on the Dev Stack's Game Server

**Status:** Planner, from the project rule that the dev stack's game server is not started or stopped by tests or manual checks.

**Decision:**

1. Unit tests use a fake `ServerService` (or a real one with a stubbed process), an injectable sleep and clock for the restart sequence, temporary directories for cleanup, and lines built from the literals in the facts section for the tracker.
2. A scheduled restart, a cleanup over real archives, the stop-time measurement and `VSS-zws` are run in throwaway containers named `vss-22-*`, removed after use. `just test-e2e-ci` (port 18080) is the model.
3. Checks on the dev stack (`http://localhost:9080`, rebuilt with `just docker restart`) are read-only: `/metrics` answers without a key, the settings fields save and are restored to their previous values from a snapshot.
4. Manual checks reserved for the maintainer: one anonymised join line and one leave line from a real server (22.1), the Players card and the count with a real client (22.1), a Prometheus scrape of a real deployment (22.2), and a scheduled restart with warnings seen in a game client (22.3). They stay unticked until he confirms them.
