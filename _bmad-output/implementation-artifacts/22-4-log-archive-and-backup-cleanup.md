# Story 22.4: Log Archive and Backup Cleanup

Status: done

<!-- Implements FR297, FR298, FR299, Epic 22 ADR-7 (decisions 3 and 4), ADR-9, ADR-10 and ADR-14. Bead: VSS-29p (API-011), closes here (Story 22.3 carried its first half). Maintainer answers 8 and 9 (Matt, 2026-11-18); four controller decisions during validation (2026-11-18, Dev Notes), for the maintainer to review. Order: 22.1, 22.2, 22.3, 22.4, 22.7, 22.5, 22.6. This branch, story/22-4-log-archive-and-backup-cleanup, is stacked on story/22-3-scheduled-restarts (22.3 in review) at 6fd76056 (the Story 22.7 planning commit; the code is that of 36dd18cf). The PR targets main and merges after 22.3's. Line references were verified at 6fd76056 and must be re-checked at implementation time. API and documentation only; no web source change (the UI for the three settings is Story 22.6). No new dependency, no new route, one new service, one new job module, no change to services/scheduler.py, models/jobs.py, routers/jobs.py, main.py or services/cache_eviction.py. -->

<!-- 2026-11-19: Maintainer decision after Task 3 ("Backups only + docs"): the log-archive cleanup and its two settings are dropped, because the game already keeps at most 5 archives; the opt-in backup cleanup, its setting and the daily disk_cleanup job stay. The ACs and tasks it removes are marked, not deleted. See Dev Notes "Maintainer decision after Task 3". -->

## Story

As an **operator**,
I want **old log archives, and old backups when I ask for it, deleted every day**,
so that **the disk does not fill up over months of restarts, and my world and its own backups are never touched**.

## Acceptance Criteria

1. **Given** `serverdata/Logs/Archive/` holds 20 archive directories named `YYYY-MM-DD_03_00_00` for each of the 20 days before a fixed clock of 2026-11-18 12:00:00 (2026-11-18 back to 2026-10-30), each directory's modification time equal to the time in its name, and the default settings (14 days, 5 kept, backups 0)
   **When** the cleanup runs
   **Then** the 6 archives named 2026-11-04 and earlier (older than 14 days before the clock) are deleted, the 14 newest remain, each deletion is logged as `disk_cleanup_deleted` with `kind=log_archive`, its path relative to `serverdata` (`Logs/Archive/2026-11-04_03_00_00`) and its size in bytes, and one `disk_cleanup_finished` line gives the counts and bytes
   *(Covers FR297, FR299; ADR-9 decisions 1, 3 and 6)*

   **Removed by the maintainer's decision (Matt, 2026-11-19, "Backups only + docs"; Dev Notes "Maintainer decision after Task 3").** The service no longer touches `Logs/`.

2. **Given** 7 archives, all older than 14 days, and `log_archive_keep_min` 5
   **When** the cleanup runs
   **Then** the newest 5 (by the time in their names) remain and the 2 oldest are deleted; with `log_archive_keep_min` 0 the 6 oldest are deleted and the newest remains (the newest archive is never deleted: controller decision 1); with 1000 none is
   *(Covers FR297; ADR-9 decision 3)*

   **Removed by the maintainer's decision (Matt, 2026-11-19, "Backups only + docs"; Dev Notes "Maintainer decision after Task 3").**

3. **Given** `log_archive_retention_days` is 0
   **When** the cleanup runs
   **Then** no archive is deleted, whatever their age and `log_archive_keep_min`
   *(Covers FR297; ADR-9 decision 1)*

   **Removed by the maintainer's decision (Matt, 2026-11-19, "Backups only + docs"; Dev Notes "Maintainer decision after Task 3").** The setting no longer exists; saving it is refused as unknown (AC 10).

4. **Given** (a) an archive whose name is 30 days old but whose directory modification time is 1 hour old (a long run archived at the last start), and (b) an archive whose name is 1 day old but whose directory modification time is 30 days old, with retention 14 and keep 0, among other old archives
   **When** the cleanup runs
   **Then** both (a) and (b) remain: an archive's age is measured from the later of the time in its name and its directory's modification time (`lstat`, links not followed); (c) an archive whose name and modification time are both older than the retention is deleted (unless it is the newest); the order for `log_archive_keep_min` and for "the newest" stays the time in the names
   *(Covers FR297; ADR-9 decision 3, as changed by controller decision 2)*

   **Removed by the maintainer's decision (Matt, 2026-11-19, "Backups only + docs"; Dev Notes "Maintainer decision after Task 3").**

5. **Given** in `Archive/`: an entry whose name does not match `YYYY-MM-DD_HH_MM_SS` (`notes`, `2026-11-01_03_00_00.old`, `2026-11-01_03_00_00\n`, full-width digits, `2026-13-45_00_00_00`), a regular file with an archive name, and an old archive name that is a symbolic link to a directory outside `serverdata`
   **When** the cleanup runs with every limit at its smallest (retention 1, keep 0)
   **Then** none of them is deleted and the link's target and its files are intact; the link is logged at WARNING (`disk_cleanup_skipped reason=symlink`), the others at DEBUG; they are not counted towards `log_archive_keep_min`
   *(Covers FR298; ADR-9 decisions 3 and 5; see "ADR against the code" 1)*

   **Removed by the maintainer's decision (Matt, 2026-11-19, "Backups only + docs"; Dev Notes "Maintainer decision after Task 3").** `Archive/` is never read; its entries are never touched (AC 7).

6. **Given** `serverdata/Backups/` holds 8 regular files with distinct modification times, a directory, and a symbolic link to a file outside `serverdata`, and `backup_keep_count` is 3
   **When** the cleanup runs
   **Then** the 3 newest files (by modification time), the directory and the link (and its target) remain, the 5 others are deleted and each is logged with `kind=backup`; with `backup_keep_count` 0 (the default) all 8 files remain and `Backups/` is not read
   *(Covers FR298; ADR-9 decisions 1 and 4)*

   **Kept.**

7. **Given** files in `BackupSaves/`, `Saves/`, `Mods/`, `Playerdata/`, `ModConfig/`, the live `Logs/server-*.log` files, `serverconfig.json` and the manager's `vsmanager/` state and cache; and separately `Logs/Archive` itself, `Logs` itself or `Backups` itself a symbolic link to a directory outside `serverdata`
   **When** the cleanup runs with every limit at its smallest (retention 1, keep 0, backups 1) and every file older than any limit
   **Then** none of them is deleted (byte-for-byte the same tree before and after, outside the entries the limits select in the two target directories); a symlinked target directory is skipped as a whole with WARNING `disk_cleanup_skipped reason=symlink`
   *(Covers FR298; ADR-9 decision 5; see "ADR against the code" 2)*

   **Amended by the maintainer's decision (2026-11-19):** "every limit at its smallest" is `backup_keep_count` 1, and `Logs/` as a whole (live logs and `Archive/` with old archive names) is among what is never touched; the `Logs` and `Logs/Archive` link cases become "never read". A symlinked `Backups` is still skipped with WARNING `reason=symlink`.

8. **Given** one entry cannot be deleted (permission denied)
   **When** the cleanup runs
   **Then** `disk_cleanup_delete_failed` is logged at WARNING with the path and the error, the other entries are still handled, and `disk_cleanup_finished` counts only what was deleted and gives `errors=1`
   *(Covers FR299; ADR-9 decision 6)*

   **Amended (2026-11-19):** for backups only (`kind=backup`); `disk_cleanup_finished` gives the backup counts and bytes.

9. **Given** the API starts (or `register_default_jobs` runs)
   **When** I list the jobs (`GET /api/v1alpha1/jobs`)
   **Then** `disk_cleanup` is registered whatever the settings, with `trigger_type` `cron` and `trigger_details` `cron[month='*', day='*', day_of_week='*', hour='3', minute='0']`, its next run at 03:00 in the container's time zone (`TZ`, UTC when unset); when it runs it reads the three limits from `api-settings.json` at that moment, so a changed limit applies at the next run, and saving a limit does not touch any job
   *(Covers FR297; ADR-7 decisions 3 and 4, ADR-9 decision 6)*

   **Amended (2026-11-19):** the job reads `backup_keep_count` at each run; with 0 (the default) it deletes nothing and logs `disk_cleanup_finished`.

10. **Given** each cleanup setting
    **When** an Admin key saves a value outside its bounds (`log_archive_retention_days` -1 or 3651; `log_archive_keep_min` -1 or 1001; `backup_keep_count` -1 or 1001), a boolean, or a non-integer string
    **Then** the answer is 400 `API_SETTING_INVALID`, the saved value does not change and the scheduler callback is not called; values inside the bounds (0, the default, the maximum) are saved and returned by `GET /api/v1alpha1/config/api`; a Monitor key gets 403
    *(Covers FR297, FR298; ADR-9 decision 1)*

    **Amended by the maintainer's decision (2026-11-19):** only `backup_keep_count` remains (bounds 0 to 1000). `log_archive_retention_days` and `log_archive_keep_min` are no longer settings: saving either is refused with 400 `API_SETTING_UNKNOWN` and nothing is saved.

11. **Given** a throwaway container (never the dev stack), run with `TZ=Europe/Berlin`
    **When** the game is started and stopped 7 times, and `/genbackup` is run twice
    **Then** the story records the archive directory names the game writes (one per start after the first, each the start time of the archived run in the container's time zone), that the game deletes none of them, what `/genbackup` writes into `Backups/`, and that the cleanup, run against that data, deletes exactly the expected entries; a different finding stops the story before the job is registered
    *(Covers FR297; ADR-9 decision 7, ADR-14)*

    **Done (Task 3); its finding led to the maintainer's decision:** the game keeps at most 5 log archives itself, and `/genbackup` wrote no file in that run.

12. **Given** the README
    **When** I read "Logs and disk use"
    **Then** it says who rotates what (the game: a new set of log files and an archive per start, and `LogFileSplitAfterLine`; the manager: deletes old archives and, when asked, old backups; the manager's stdout: Docker's or Kubernetes' log options, with a compose `logging` example), what the cleanup deletes and when (03:00 in `TZ`), the three settings with their defaults, bounds and how to set them, and what it never touches
    *(Covers FR299; ADR-10)*

    **Amended (2026-11-19):** the README says the game keeps at most 5 log archives itself, who rotates what (the game: archives and `LogFileSplitAfterLine`; the manager's stdout: Docker's or Kubernetes' log options; `Backups/`: the manager, only when `backup_keep_count` > 0), what the cleanup deletes and when (03:00 in `TZ`), the setting with its default, bounds and how to set it, and what it never touches.

13. **Given** every existing test
    **When** the suites run
    **Then** they pass unchanged except those listed in Dev Notes "Existing tests that change"; Pyright reports 0 errors and 0 warnings; the diff adds no `# type: ignore`, `# pyright: ignore`, `noqa`, `cast`, `as`-style escape or skipped test; no test deletes, creates or renames anything outside its `tmp_path` (in particular nothing in `dev/` or `./data`), and no registered cleanup job can run the real cleanup during a test

14. **Given** a deployment with real archives
    **When** the maintainer reads the API log the morning after an upgrade
    **Then** he sees `disk_cleanup_finished` at 03:00 local time and only old archives deleted (manual check, reserved for the maintainer, ticked only on his confirmation)
    *(Covers FR297, FR299; ADR-14 decision 4)*

    **Amended (2026-11-19):** a deployment with `backup_keep_count` set: he sees `disk_cleanup_finished` at 03:00 local time and only backups beyond the newest N deleted; with the default 0 the line shows nothing deleted.

## Tasks / Subtasks

<!-- Each functional task includes its tests in the same commit, red first (run the new tests, see them fail, then implement). Subjects: type(story-22.4/task-N): ..., the type chosen by what an admin notices. One commit is user-visible: Task 4 (feat), the commit that makes the cleanup run; its subject is written for admins and its body names Story 22.4, the task, and that archives older than 14 days are now deleted by default. -->

- [x] Task 1: The three cleanup settings with their bounds + tests (AC: 10, 13)
  - [x] 1.1: Red first: the Task 1 rows of Dev Notes "API tests" in `api/tests/test_api_settings.py` and `api/tests/test_routers_config.py`; see the new tests fail
  - [x] 1.2: `services/api_settings.py`: the three constants and fields of Dev Notes "The settings", after `scheduled_restart_times` and before the webhook. They are plain `int` fields, so `update_setting`'s existing `int` branch (`:357-368`) coerces them and Pydantic's `ge`/`le` enforce the bounds; no change to `update_setting`. They are **not** added to `SCHEDULED_SETTINGS` (`:162-175`; ADR-7 decision 4): the router's callback is not called for them
  - [x] 1.3: `cd api && uv run ruff format <changed files>`; `just test-api tests/test_api_settings.py tests/test_routers_config.py tests/test_jobs_registration.py` green; `just typecheck-api` 0 errors, 0 warnings
  - [x] 1.4: Commit `refactor(story-22.4/task-1): accept the disk cleanup limits in the API settings` (nothing acts on them yet; precedent `refactor(story-22.3/task-2)`)

- [x] Task 2: `DiskCleanupService` with the archive and backup rules and the path and link checks + tests (AC: 1, 2, 3, 4, 5, 6, 7, 8, 13)
  - [x] 2.1: Red first: new `api/tests/test_disk_cleanup.py` with every Task 2 row of Dev Notes "API tests" (temporary directories, a fixed clock, no real `serverdata`); see them fail
  - [x] 2.2: New `api/src/vintagestory_api/services/disk_cleanup.py` as Dev Notes "The service": `CleanupLimits`, `CleanupResult`, `DiskCleanupService.run`, the rules of "What is deleted" and "What is never deleted", the log lines of "What is logged". Nothing calls it yet
  - [x] 2.3: `cd api && uv run ruff format <changed files>`; `just test-api tests/test_disk_cleanup.py` green; `just typecheck-api` 0/0
  - [x] 2.4: Commit `refactor(story-22.4/task-2): add the disk cleanup service for log archives and backups` (not registered yet)

- [x] Task 3: Check the game's archives and backups, and run the service on them, in a throwaway container (AC: 11)
  - [x] 3.1: Run Dev Notes "The throwaway-container run" exactly: image `vss-22-4-cleanup:local` built from this branch (with Tasks 1 and 2), container `vss-22-4-cleanup` on `127.0.0.1:18092` with `TZ=Europe/Berlin`, no game port published, placeholder keys, no volume or bind mount, no `--env-file`, no compose, not `just test-e2e-ci`. Never the dev stack (`vintagestory-manager-dev`, `http://localhost:9080`), whose game server is not started or stopped, and never `./data` or `dev/`
  - [x] 3.2: Install the current stable game through the API; 7 rounds of start, ready, stop; after each start record `ls Logs/Archive`, `stat -c '%y %n' Logs/Archive/*` (each archive directory's modification time), `date` and `date -u` in the container and the new archive's first `server-main.log` line ("Server logger started")
  - [x] 3.3: In round 7, while the game runs: `/genbackup` twice through `POST /api/v1alpha1/console/command`; record `ls -la` of `Backups/` and `BackupSaves/` (type, size, name of each entry)
  - [x] 3.4: Run the service in the container (`docker exec ... uv run --no-sync python -c ...`, Dev Notes) four times: defaults (expect nothing deleted: every archive is from today); after adding three old copies of an archive, each with its directory modification time set back to its name's age (`touch -m -d`; a copy keeps today's modification time otherwise and would not be deleted, controller decision 2), and an old-named symbolic link to `/etc` (expect exactly the three copies deleted, the link skipped with WARNING, `/etc` intact); `backup_keep_count` 1 (expect the older backup deleted, the newer kept); `log_archive_retention_days` 0 and `backup_keep_count` 0 (expect nothing deleted)
  - [x] 3.5: Remove the container and the image (`docker rm -f vss-22-4-cleanup; docker image rm vss-22-4-cleanup:local`); `docker ps -a --filter name=vss-22-4` and `docker image ls vss-22-4-cleanup` are empty; `git status --short dev/ data/` is empty
  - [x] 3.6: Record the results in Dev Agent Record "Throwaway-container results" (host architecture, game version, the archive listing after each start with the logger-start line and the clock, the `Backups/` listing, the four service runs' results and log lines, the commands) and append a "Results (Story 22.4)" paragraph to ADR-9's section in `_bmad-output/planning-artifacts/architecture/epic-22-server-operations-and-metrics.md`. No instance data, no real key, no address
  - [x] 3.7: **Stop rule:** if the game deleted or renamed any archive across the rounds, if an archive name does not match the pattern or is not the archived run's start time in `TZ` (for example UTC while `TZ=Europe/Berlin`), if `/genbackup` writes anything other than one regular file directly in `Backups/`, or if any service run deleted anything other than the expected entries: commit the record (3.8), then stop and report it to the controller as a maintainer question with the evidence. Task 4 goes on only if the controller says so; the story does not go to review before the answer
  - [x] 3.8: Commit `docs(story-22.4/task-3): record the game's log archives and backups and a cleanup run on them`

- [x] Task 3a (`/user`, maintainer decision 2026-11-19): Drop the log-archive cleanup the game already does + tests (AC: 6, 7, 8, 10, 13)
  - [x] 3a.1: Record the decision in this story (Completion Notes, "ADR against the code" 11, the ACs and tasks it removes marked, not deleted) and amend ADR-9 and ADR-10, FR297 in `prd.md`, the Story 22.4 entry and FR297 coverage row in `epics.md` and the change proposal's decisions; commit `docs(story-22.4/user): record the maintainer's decision to clean up backups only`
  - [x] 3a.2: Red first: the settings tests assert that `log_archive_retention_days` and `log_archive_keep_min` are refused as unknown (service and route) and that the model has no such fields; the service tests assert that nothing under `Logs/` is read or deleted, with every backup, link, containment and per-entry error case kept
  - [x] 3a.3: Remove the two settings and constants from `services/api_settings.py`, and the archive pass from `services/disk_cleanup.py` (`CleanupLimits` holds `backup_keep_count` only; `CleanupResult` the backup counts and `errors`)
  - [x] 3a.4: Commit `refactor(story-22.4/user): drop the log archive cleanup the game already does`

- [x] Task 4: The `disk_cleanup` cron job, always registered, with its log lines + tests (AC: 8, 9, 13; AC 1 removed)
  - [x] 4.1: Red first: new `api/tests/jobs/test_disk_cleanup_job.py` and the Task 4 rows in `api/tests/test_jobs_registration.py` and `api/tests/test_routers_config.py`; see them fail
  - [x] 4.2: `api/tests/conftest.py`: the autouse no-op for the cleanup job (Dev Notes "Test safety"), in the same commit as the registration and in place before the first test run with `register_disk_cleanup` called from `register_default_jobs`, so no test run can delete under `dev/`. Its string target imports `vintagestory_api.jobs.disk_cleanup`, so add it once that module exists (before, every test errors at set-up)
  - [x] 4.3: New `api/src/vintagestory_api/jobs/disk_cleanup.py` (Dev Notes "The job"): the constants, `run_disk_cleanup(settings, *, now=...)` and the job function `disk_cleanup` under `@safe_job("disk_cleanup")`; `jobs/__init__.py`: `register_disk_cleanup(scheduler)` and its call at the end of `register_default_jobs` (Dev Notes "Registration"); the module docstrings name Story 22.4
  - [x] 4.4: The existing tests listed in Dev Notes "Existing tests that change", and nothing else
  - [x] 4.5: `cd api && uv run ruff format <changed files>`; `just test-api tests/jobs tests/test_jobs_registration.py tests/test_routers_config.py tests/test_jobs_router.py tests/test_main.py tests/test_disk_cleanup.py tests/test_scheduler.py` green; `just typecheck-api` 0/0
  - [x] 4.6: Commit `feat(story-22.4/task-4): delete old backups every day when a limit is set` (body: Story 22.4 / task 4; a daily `disk_cleanup` job at 03:00 in the container's time zone keeps only the newest `backup_keep_count` files in `Backups` when it is above 0 (default 0 keeps all, so nothing is deleted by default); log archives are left to the game, which keeps 5; `BackupSaves`, the world, mods and the logs are never touched). **Amended (2026-11-19); the original subject and body were:** `feat(story-22.4/task-4): delete old game log archives every day, and old backups when a limit is set` (body: Story 22.4 / task 4; a daily `disk_cleanup` job at 03:00 in the container's time zone deletes the game's log archives older than `log_archive_retention_days` (default 14, 0 keeps all), always keeping the newest `log_archive_keep_min` (default 5), and keeps only the newest `backup_keep_count` files in `Backups` when it is above 0 (default 0 keeps all); **archives older than 14 days are now deleted by default**; `BackupSaves`, the world, mods and the live logs are never touched)

- [x] Task 5: Document who rotates which logs and the cleanup (AC: 12; text as amended in Dev Notes "Maintainer decision after Task 3")
  - [x] 5.1: `README.md`: a new `### Logs and disk use` section between "Scheduled restarts" and "Metrics" (`:93-112`), and the Features "Scheduled jobs" bullet (`:17`), with the text of Dev Notes "Documentation". The compose files are not changed
  - [x] 5.2: `just lint` green (nothing else moved)
  - [x] 5.3: Commit `docs(story-22.4/task-5): document who rotates which logs and the disk cleanup`

- [ ] Task 6: Validate and move the story to review (AC: all)
  - [x] 6.1: `just check` green: API tests, pyright 0 errors and 0 warnings, ruff; web tests with 0 skipped, tsc, Prettier. The added lines in `api/src` and `api/tests` hold no `type: ignore`, `pyright:`, `noqa`, `cast(`, skip, `xfail` or `.only`; `services/scheduler.py`, `models/jobs.py`, `routers/jobs.py`, `main.py` and `services/cache_eviction.py` are unchanged (`git diff 6fd76056 -- <those files>` is empty). `git status --short dev/ data/` is empty after the runs
  - [x] 6.2: `just changelog` lists exactly one new entry from this story (Task 4's feature subject); check by this branch's hashes, as Stories 22.2 and 22.3 did
  - [ ] 6.3: Manual check (maintainer only; leave unticked until he confirms, AC 14): on a deployment he runs, the morning after the upgrade, `disk_cleanup_finished` at 03:00 local time in the API log, and with `backup_keep_count` set only backups beyond the newest N gone (amended 2026-11-19; was: only archives older than the retention, beyond the newest 5, gone). No agent runs this, and never on the dev stack's data
  - [x] 6.4: Story status `review` in this file; `just sprint set 22-4-log-archive-and-backup-cleanup review`; Dev Agent Record and File List filled in, every statement true of the code
  - [x] 6.5: Commit `chore(story-22.4/task-6): validate and move story 22.4 to review`
  - [ ] 6.6: After merge, with the maintainer's go-ahead only: `VSS-29p` gets an AAR comment naming Stories 22.3 and 22.4 and their commits, then `bd close VSS-29p` (CLAUDE.md "Completing Issues"). Pushing, the PR, `bd sync` and the bead wait for that go-ahead

## Dev Notes

### Maintainer decision after Task 3 (Matt, 2026-11-19): "Backups only + docs"

Task 3 found that the game keeps at most 5 log archives itself (it deleted the oldest at the start that made a sixth) and that `/genbackup` wrote no file in that run. The maintainer's answer:

- **Dropped:** the log-archive cleanup and its two settings, `log_archive_retention_days` and `log_archive_keep_min`, because the game already keeps at most 5 archives. The service does not read or delete anything under `Logs/`. Saving either key is refused as unknown (400 `API_SETTING_UNKNOWN`).
- **Kept:** the opt-in `backup_keep_count` (default 0 = keep all, 0 to 1000) and the daily `disk_cleanup` job for it at 03:00 container time, always registered, reading the setting at each run; the link, containment and per-entry error rules for `Backups/`; the log lines (`disk_cleanup_deleted kind=backup`, `disk_cleanup_finished` with the backup counts and bytes and `errors`).
- **Docs:** the README says the game keeps 5 log archives itself and who rotates what: the game (archives at each start, at most 5, and `LogFileSplitAfterLine`); the manager's stdout (Docker's or Kubernetes' log options, the compose `logging` example in the README only); `Backups/` (the manager, only when `backup_keep_count` > 0). The "Documentation" notes below are read with these changes: the Features bullet says "a daily cleanup of old backups when you ask"; the table's archive row says the game keeps at most 5 and the manager does not touch them; the cleanup paragraph and the settings describe `backup_keep_count` only; "What it never touches" includes `Logs/` as a whole.
- The sections below ("The settings", "The service", "What is deleted", "API tests", "The throwaway-container run", "Documentation", "API contract changes") keep their original text as history; where they name the archive rules or the two dropped settings, this decision overrides them.

### The code today (verified at 6fd76056)

- **Settings:** `ApiSettings` (`api/src/vintagestory_api/services/api_settings.py:57-156`) holds booleans, three intervals bounded by `MAX_INTERVAL_SECONDS` (`:28-33`), `scheduled_restart_times` (`:95-103`) and the webhook (`:104-108`). `update_setting` (`:308-427`): unknown key -> `ApiSettingUnknownError` (`:328-329`); for an `int` annotation it refuses a `bool` (`must be an integer, not boolean`), accepts an `int`, converts a numeric string and refuses anything else (`:357-368`); then `ApiSettings(**current_dict)` and a `ValidationError` becomes `ApiSettingInvalidError` with the first error's `msg` (`:378-385`, for `le=3650` Pydantic says `Input should be less than or equal to 3650`); saves atomically (`:388`, `_save_settings` `:429-465`); calls the scheduler callback only for `SCHEDULED_SETTINGS` keys (`:390-406`, set at `:162-175`). The router maps `ApiSettingInvalidError` to 400 `API_SETTING_INVALID` and is Admin only (`routers/config.py`, `update_api_setting`; Story 22.3 tests use the `reschedule_client` fixture, `api/tests/test_routers_config.py:2248-2285`).
- **Jobs:** `INTERVAL_JOBS` (`jobs/__init__.py:47-52`), `apply_interval_setting` (`:73-116`), `apply_restart_schedule` (`:119-161`, imports its job function lazily so tests can monkeypatch it), `apply_setting` (`:164-182`; any key that is neither an interval nor `scheduled_restart_times` does nothing), `register_default_jobs` (`:185-221`: reads `ApiSettingsService().get_settings()`, applies the intervals and the restart times, logs `default_jobs_registered count=<interval jobs> restart_jobs=<n>`). `safe_job(job_name)` (`jobs/base.py:61-105`) logs `{job_name}_started` / `_completed` at INFO and turns any `Exception` into `logger.exception("{job_name}_failed")`. A job module pattern with a lazily fetched singleton: `jobs/metrics_collection.py:19-41`; with an injectable seam and a protocol: `jobs/scheduled_restart.py` (Story 22.3).
- **Scheduler:** `SchedulerService` (`services/scheduler.py:50-67`: `AsyncIOScheduler`, memory job store, `coalesce: True`, `max_instances: 1`, `misfire_grace_time: 60`). `add_cron_job(func, cron_expr, job_id, **kwargs)` (`:160-191`) builds `CronTrigger.from_crontab(cron_expr)` with no time zone, so the trigger uses `tzlocal.get_localzone()`, which reads `TZ` (Story 22.3 checked it in the image: `Etc/UTC` without `TZ`, `Europe/Berlin` with it); it passes `id`, `replace_existing=True` and `**kwargs` to `add_job` and logs `job_added trigger_type=cron cron_expr=...`. Its docstring example is a daily cleanup (`:178-181`). The file has fourteen `# type: ignore` comments; this story adds none and does not edit it.
- **Jobs API and tab:** `GET /api/v1alpha1/jobs` (`routers/jobs.py:30-49`, Admin) serialises each job with `job_to_info` (`models/jobs.py:35-77`); for `from_crontab("0 3 * * *")` the `trigger_details` is `cron[month='*', day='*', day_of_week='*', hour='3', minute='0']` (format checked on APScheduler 3.11.3 in Story 22.3). `DELETE /api/v1alpha1/jobs/{job_id}` (`:52-85`) removes any job, so deleting `disk_cleanup` stops it until the API restarts. The web's Scheduled Jobs tab shows the id, the details as they are, the next run in the browser's local time and a `cron` badge: `disk_cleanup` appears with no web change.
- **Start-up:** the lifespan (`main.py:156-229`) auto-starts the game, then creates and starts the scheduler (`:211-212`) and calls `register_default_jobs` (`:215-217`). `main.py` does not change.
- **Data directories:** `Settings.serverdata_dir` is `data_dir / "serverdata"` (`config.py:243-250`, the game's `--dataPath`), `state_dir` `vsmanager/state` (`:262-265`), `cache_dir` `vsmanager/cache` (`:257-260`), `logs_dir` `vsmanager/logs` (`:267-270`, empty: the manager logs to stdout). `ensure_data_directories` (`:272-...`) creates them. `ServerService.settings` is the app's `Settings` (`services/server.py:191-194`; `get_server_service()` `:52-60` builds `ServerService()` from the environment), the same one the routers pass to `ApiSettingsService` (`routers/config.py:259-276`, `get_api_settings_service`).
- **Existing deletion code:** `services/cache_eviction.py` deletes mod cache files only under `cache_dir/mods/*/`, matching named patterns with `glob` (`:122-139`), unlinks one file at a time and logs `cache_evicted` with the file name and size (`:247-258`), logs a per-file `OSError` at WARNING and goes on (`:259-265`), removes a directory only with `rmdir` when empty (`:169-176`), and returns counts and bytes in a dataclass (`EvictionResult`, `:37-51`). The cleanup follows the same shape (named entries, one at a time, per-entry errors logged and skipped, a result dataclass). It does not reuse or change `cache_eviction.py` (different directories and rules; ADR-9 decision 2).
- **The game's layout** (read-only listing of the dev stack's `./data/serverdata` on the host, 2026-11-18; nothing there was changed): `BackupSaves/` (empty), `Backups/` (empty), `Cache/`, `Logs/` (`server-audit.log`, `server-build.log`, `server-chat.log`, `server-debug.log`, `server-main.log`, `server-worldgen.log` and `Archive/`), `Macros/`, `ModConfig/`, `Mods/`, `Playerdata/`, `Saves/`, `WorldEdit/`, `serverconfig.json` (`"LogFileSplitAfterLine": 500000`), `servermagicnumbers.json`. `Logs/Archive/` holds one directory, `2026-11-09_19_53_31`, with the six `server-*.log` files of the previous run; its `server-main.log` begins `9.11.2026 19:53:31 [Notification] Server logger started.` So **the name is the archived run's start time** (the game's local clock, UTC in that container), not the time it was archived (the next start, 2026-11-10 03:07). The dev stack's two runs give one archive: the first start archives nothing.
- **Tests run against `dev/`:** `just test-api` sets `VS_DATA_DIR=../dev` (`Justfile:36`), and `dev/` holds a `serverdata/`. `api/tests/conftest.py:76-87` already keeps lifespans away from the real mods directory with an autouse fixture. Any test that registers the real `disk_cleanup` on a started scheduler (for example `TestRegisterDefaultJobs.scheduler`, `api/tests/test_jobs_registration.py:52-58`, which does not patch the job functions; `lifespan_client` in `tests/test_jobs_router.py`) could run it at 03:00 against `dev/serverdata`. Dev Notes "Test safety" closes that.
- **Python 3.14.10** (`api/pyproject.toml`, `requires-python = ">=3.14"`): `shutil.rmtree.avoids_symlink_attacks` is `True` (checked on the host; Linux has it too); `shutil.rmtree` on a symbolic link raises `OSError` (with `onexc`, the handler is called with `os.path.islink`), and a link inside a tree is unlinked, not followed (checked: the link's target and its files stayed). `re` with `\d` and `$` accepts `2026-11-09_19_53_31\n` and full-width digits; `[0-9]` with `fullmatch` refuses both. `datetime.strptime("2026-13-45_00_00_00", "%Y-%m-%d_%H_%M_%S")` raises `ValueError`.

### The settings (Task 1)

In `services/api_settings.py`, module constants next to `MAX_INTERVAL_SECONDS` (names are binding):

```python
MAX_LOG_ARCHIVE_RETENTION_DAYS = 3650
MAX_LOG_ARCHIVE_KEEP_MIN = 1000
MAX_BACKUP_KEEP_COUNT = 1000
"""Upper bounds of the disk cleanup limits (Epic 22 ADR-9 decision 1)."""
```

Fields after `scheduled_restart_times`, before `mod_update_webhook_url`:

```python
    log_archive_retention_days: int = Field(
        default=14,
        ge=0,
        le=MAX_LOG_ARCHIVE_RETENTION_DAYS,
        description=(
            "Days the game's log archives (serverdata/Logs/Archive) are kept by the daily "
            "cleanup, from the later of the start time in their names and their folder's "
            "modification time (0 = keep all, at most 3650)"
        ),
    )
    log_archive_keep_min: int = Field(
        default=5,
        ge=0,
        le=MAX_LOG_ARCHIVE_KEEP_MIN,
        description=(
            "Newest log archives always kept, whatever their age (0 to 1000). "
            "The newest archive is always kept, also with 0"
        ),
    )
    backup_keep_count: int = Field(
        default=0,
        ge=0,
        le=MAX_BACKUP_KEEP_COUNT,
        description=(
            "Newest files kept in serverdata/Backups by the daily cleanup "
            "(0 = keep all, at most 1000). BackupSaves is never touched"
        ),
    )
```

- Not in `SCHEDULED_SETTINGS`: the job reads them when it runs (ADR-7 decision 4). `apply_setting` already ignores unknown keys, so even a wrong callback call would do nothing; the tests assert the callback is not called.
- `GET /api/v1alpha1/config/api` returns them in `data.settings` (the model is dumped whole); the web's camelCase transform gives `logArchiveRetentionDays`, `logArchiveKeepMin`, `backupKeepCount` for Story 22.6. No web change here.
- A hand-edited `api-settings.json` with an out-of-bounds value makes `get_settings` fall back to all defaults with WARNING `api_settings_load_failed` (`:272-306`); the cleanup then runs with the defaults. Existing behaviour, not changed.

### The service (Task 2)

New module `api/src/vintagestory_api/services/disk_cleanup.py`. Names are binding, bodies are the developer's:

```python
"""Daily disk cleanup of the game's log archives and, when asked, its backups (Epic 22 ADR-9)."""

ARCHIVE_DIR = Path("Logs") / "Archive"
BACKUP_DIR = Path("Backups")
_ARCHIVE_NAME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{2}_[0-9]{2}_[0-9]{2}")
_ARCHIVE_TIME_FORMAT = "%Y-%m-%d_%H_%M_%S"

CleanupKind = Literal["log_archive", "backup"]


@dataclass(frozen=True)
class CleanupLimits:
    log_archive_retention_days: int
    log_archive_keep_min: int
    backup_keep_count: int


@dataclass
class CleanupResult:
    archives_deleted: int = 0
    archive_bytes: int = 0
    backups_deleted: int = 0
    backup_bytes: int = 0
    errors: int = 0


class DiskCleanupService:
    def __init__(self, serverdata_dir: Path, *, now: Callable[[], datetime] = datetime.now) -> None: ...
    def run(self, limits: CleanupLimits) -> CleanupResult: ...
```

- `now` returns the **naive local** wall-clock time (`datetime.now()`), the same clock as the names, which the game writes in its local time (the container's `TZ`; Task 3 confirms it with `TZ=Europe/Berlin`). Archive names are parsed naive with `_ARCHIVE_TIME_FORMAT`; a directory's modification time is converted with `datetime.fromtimestamp(st_mtime)` (naive local, the same clock). Tests pass `now=lambda: datetime(2026, 11, 18, 12, 0, 0)`. A daylight-saving change shifts an age by at most an hour; not handled.
- `run` is synchronous (the job runs it in a worker thread, "The job"). It does the archive pass, then the backup pass, logs `disk_cleanup_finished` and returns the result. One pass failing as a whole (for example `PermissionError` listing the directory) is logged (`disk_cleanup_delete_failed` with the directory, WARNING), counted in `errors`, and the other pass still runs.
- Sizes: an archive's bytes are the sum of `lstat().st_size` of the regular files under it, walked with `os.walk(..., followlinks=False)` and computed before deletion; a backup's are its `lstat().st_size`. A size read that fails counts as 0 for that entry (no error by itself).
- Listing and deletion go through three small module-level functions, `_scan(directory: Path) -> list[os.DirEntry[str]]` (`list(os.scandir(directory))`), `_delete_tree(path: Path) -> None` (`shutil.rmtree(path)`) and `_delete_file(path: Path) -> None` (`path.unlink()`), so a test can make one listing or one entry fail, or change the tree between the listing and the deletion, with `monkeypatch.setattr` (root ignores `chmod`, and CI may run as root; "ADR against the code" 7).

### What is deleted (ADR-9 decisions 3 and 4)

**Log archives**, only when `log_archive_retention_days > 0`:

1. The target is `serverdata_dir / ARCHIVE_DIR`. If `serverdata_dir`, `Logs` or `Logs/Archive` is missing, the pass does nothing (DEBUG `disk_cleanup_dir_missing`). If `Logs` or `Logs/Archive` is a symbolic link (`Path.is_symlink()`), the pass is skipped: WARNING `disk_cleanup_skipped reason=symlink path=<relative>`.
2. Candidates: entries of `_scan(target)` that are directories without following links (`entry.is_dir(follow_symlinks=False)`), whose name `_ARCHIVE_NAME.fullmatch`es and parses with `strptime`. The link check comes first: an entry that is a symbolic link (`entry.is_symlink()`) is skipped with WARNING `disk_cleanup_skipped reason=symlink`; then a name that does not match or does not parse, or a regular file, is skipped with DEBUG `disk_cleanup_skipped reason=not_an_archive`. Skipped entries are not counted towards the keep minimum.
3. Each candidate's **name time** is the parsed name; its **age time** is the later of the name time and its directory's modification time, `datetime.fromtimestamp(entry.stat(follow_symlinks=False).st_mtime)` (naive local, the clock of `now()`; `lstat`, a link is never followed) (controller decision 2: the name is the archived run's start time, and the directory is made when the run is archived, at the next start, so a long run would otherwise give a fresh archive an old age). An `OSError` reading the modification time keeps that entry (it is not deleted) and is logged as `disk_cleanup_delete_failed` and counted in `errors`.
4. Sorted newest first by the name time (ties by name, descending). The first `max(log_archive_keep_min, 1)` are kept: **the newest archive is never deleted, whatever `log_archive_keep_min` is, 0 included** (controller decision 1), so a cleanup during a game start cannot remove the archive just written. Of the rest, those whose age time is **strictly before** `now() - timedelta(days=log_archive_retention_days)` are deleted, one at a time, each after the path check below. The setting's bounds stay 0 to 1000; 0 behaves as 1.

**Backups**, only when `backup_keep_count > 0` (with 0 `Backups/` is not even listed):

1. The target is `serverdata_dir / BACKUP_DIR`; missing -> nothing (DEBUG); a symbolic link -> skipped with WARNING, as above.
2. Candidates: entries that are regular files without following links (`entry.is_file(follow_symlinks=False)`). A symbolic link: WARNING `disk_cleanup_skipped reason=symlink`; a directory or anything else: DEBUG `disk_cleanup_skipped reason=not_a_file`.
3. Sorted newest first by `entry.stat(follow_symlinks=False).st_mtime` (ties by name, descending); every file after the first `backup_keep_count` is deleted, each after the path check.

**The path check before every deletion:** `resolved = path.resolve()`; the deletion goes ahead only when `resolved.parent == target.resolve()` and `target.resolve()` is inside `serverdata_dir.resolve()` (`is_relative_to`) and `path.is_symlink()` is still false; otherwise WARNING `disk_cleanup_skipped reason=outside` and nothing is deleted. `shutil.rmtree` itself refuses a link and does not follow links inside the tree. `_delete_tree` calls `shutil.rmtree(path)` with no `onexc`, `onerror` or `ignore_errors`: with `onexc` a link at the top is passed to the handler (`os.path.islink`) instead of raising, and `ignore_errors` hides a partial deletion; the first error must raise and be logged as `disk_cleanup_delete_failed` (an archive can then be partly deleted; it is retried at the next run).

### What is never deleted (ADR-9 decision 5)

Anything not selected above: `BackupSaves/`, `Saves/`, `Mods/`, `ModConfig/`, `Playerdata/`, `Cache/`, `Macros/`, `WorldEdit/`, `serverconfig.json`, `servermagicnumbers.json`, the live `Logs/server-*.log` files (they are in `Logs/`, not in `Archive/`), the `Archive` and `Backups` directories themselves, entries reached through a link, and everything under `vsmanager/` (state, cache, logs). The service never builds a path from anything but `serverdata_dir`, the two constants and names it listed itself.

### What is logged

| Event | Level | Fields | When |
|---|---|---|---|
| `disk_cleanup_started`, `disk_cleanup_completed` | INFO | none | `safe_job`, around each run of the job (`_completed` is not logged when an exception reached `safe_job`; it logs `disk_cleanup_failed` with the traceback instead) |
| `disk_cleanup_deleted` | INFO | `kind` (`log_archive` or `backup`), `path` (relative to `serverdata`, for example `Logs/Archive/2026-11-04_03_00_00` or `Backups/<name>`), `bytes` | after each deletion |
| `disk_cleanup_delete_failed` | WARNING | `kind`, `path` (relative), `error` (`e.strerror`, or the exception's class name when it has none) and `errno` | a deletion, a directory listing or an archive's modification-time read raised `OSError`. Never `str(e)`: an `OSError`'s text holds the absolute file name (for example `[Errno 13] Permission denied: '/data/serverdata/...'`) |
| `disk_cleanup_skipped` | WARNING for `symlink` and `outside`; DEBUG for `not_an_archive` and `not_a_file` | `path` (relative), `reason` | each skipped entry or directory |
| `disk_cleanup_dir_missing` | DEBUG | `path` (relative) | a target directory does not exist |
| `disk_cleanup_finished` | INFO | `archives_deleted`, `archive_bytes`, `archives_kept`, `backups_deleted`, `backup_bytes`, `backups_kept`, `errors`, `log_archive_retention_days`, `log_archive_keep_min`, `backup_keep_count` | end of every `run`, also when nothing was deleted (`archives_kept`/`backups_kept` count the candidates left; 0 for a pass that did not run) |
| `job_registered` | INFO | `job_id=disk_cleanup`, `cron="0 3 * * *"` | registration (Task 4) |

No absolute path, no file content (the tests assert that no logged value contains `str(tmp_path)`). An exception that is not an `OSError` reaches `safe_job`, whose `disk_cleanup_failed` traceback can hold paths; that is the existing job pattern and only happens on a bug. Archive and backup names are the game's date stamps or an admin-given `/genbackup` file name; neither is secret.

### The job (Task 4)

New module `api/src/vintagestory_api/jobs/disk_cleanup.py`:

```python
"""Daily disk cleanup job (Epic 22 ADR-9 decision 6)."""

DISK_CLEANUP_JOB_ID = "disk_cleanup"
DISK_CLEANUP_CRON = "0 3 * * *"
"""03:00 every day in the process's local time zone (TZ, UTC when unset)."""


async def run_disk_cleanup(
    settings: Settings, *, now: Callable[[], datetime] = datetime.now
) -> CleanupResult:
    """Read the limits now and run the cleanup in a worker thread."""


@safe_job("disk_cleanup")
async def disk_cleanup() -> None:
    """The job function: get_server_service().settings, then run_disk_cleanup."""
```

- `run_disk_cleanup` reads `ApiSettingsService(settings).get_settings()` **at each run** (so a saved limit applies at the next run; ADR-7 decision 4), builds `CleanupLimits` from the three fields and awaits `asyncio.to_thread(DiskCleanupService(settings.serverdata_dir, now=now).run, limits)`. A worker thread keeps a large `rmtree` from blocking the event loop (console, WebSocket, requests); the service touches no shared state.
- `disk_cleanup` imports `get_server_service` inside the function (as `jobs/scheduled_restart.py` does) and uses `get_server_service().settings`, the `Settings` the routers use. It runs whether the game is running or not (ADR-9 decision 6: archives are previous runs'; the game writes only the live files).
- **Registration:** `jobs/__init__.py` gains `register_disk_cleanup(scheduler: SchedulerService) -> None`, which imports `DISK_CLEANUP_CRON`, `DISK_CLEANUP_JOB_ID` and `disk_cleanup` from `jobs.disk_cleanup` inside the function (so `monkeypatch.setattr("vintagestory_api.jobs.disk_cleanup.disk_cleanup", ...)` takes effect), calls `scheduler.add_cron_job(disk_cleanup, DISK_CLEANUP_CRON, job_id=DISK_CLEANUP_JOB_ID)` and logs `job_registered`. `register_default_jobs` calls it after `apply_restart_schedule`, whatever the settings (ADR-7 decision 3); its `default_jobs_registered` line and its `count` (interval jobs) stay as they are; its docstring lists `disk_cleanup`. Uses the existing `add_cron_job` unchanged (no time zone argument: `TZ` decides, like the restart jobs).
- **Missed runs:** the memory job store is rebuilt at each API start and `add_job` computes the first fire from now, so an API that is down at 03:00 (or starts at 03:00:30) skips that day's cleanup; it runs the next day. A run that the loop wakes late for runs within `misfire_grace_time` (60 s). Not worked around; the README says the cleanup is daily.
- **Turning it off:** set `log_archive_retention_days` to 0 and leave `backup_keep_count` at 0: the job still runs at 03:00, deletes nothing and logs `disk_cleanup_finished` with zeros. `DELETE /jobs/disk_cleanup` removes it until the API restarts, like any job. No on/off setting is added (ADR-9 has none).

### Test safety (Task 4)

- `api/tests/conftest.py` gains an autouse fixture next to `prepare_mod_files_recorder` (`:76-87`): `monkeypatch.setattr("vintagestory_api.jobs.disk_cleanup.disk_cleanup", _no_op_disk_cleanup)` with `async def _no_op_disk_cleanup() -> None`, and a docstring saying why (`just test-api` runs with `VS_DATA_DIR=../dev`; a registered cleanup that fires at 03:00 during a run would delete in `dev/serverdata`). Because `register_disk_cleanup` imports the job lazily, every registration in every test (lifespan clients, `TestRegisterDefaultJobs`, `reschedule_client`) gets the no-op.
- The job's own tests import the real function object at module import time (`from vintagestory_api.jobs.disk_cleanup import disk_cleanup, run_disk_cleanup`), before the autouse fixture patches the module attribute, so they test the real code; they pass `Settings(data_dir=tmp_path / "data", ...)` and monkeypatch `vintagestory_api.services.server.get_server_service` to return an object whose `settings` is that `Settings` (a small class, not a `MagicMock`, as Story 22.3 did).
- Every `Settings` in a test has `data_dir` under `tmp_path`; no test reads or writes `dev/` or `./data`. `git status --short dev/ data/` stays empty.

### API tests

| Task | File | Test |
|---|---|---|
| 1 | `api/tests/test_api_settings.py` | **Model:** defaults 14, 5, 0 (extend `test_default_values`, `:58-66`, by three asserts: an addition, not a change); the constants 3650, 1000, 1000; each field accepts 0 and its maximum and rejects -1 and maximum + 1 (`ValidationError`, parametrised over the three keys). **Service:** `update_setting(key, value)` for 0, the default and the maximum returns `{"key": key, "value": value}` and the file holds it; `"7"` is saved as 7; -1, max + 1, `True`, `"seven"` and `[1]` raise `ApiSettingInvalidError` with the file bytes unchanged; a `MagicMock` callback is never called for any of the three keys (also on success); the three keys are not in `SCHEDULED_SETTINGS` |
| 1 | `api/tests/test_routers_config.py` | Over `reschedule_client` with the admin key: POST `log_archive_retention_days` 30 -> 200 and `GET /api/v1alpha1/config/api` has 30; POST 3651 -> 400 `API_SETTING_INVALID`, the GET value unchanged; POST `backup_keep_count` 3 -> 200; the scheduler's job ids are the same before and after both saves; a Monitor key -> 403 (as the existing API-settings tests) |
| 2 | `api/tests/test_disk_cleanup.py` (new) | **Fixtures:** a `serverdata` tree under `tmp_path` built by small helpers (`make_archive(name, files={...}, mtime=None)` writing a few bytes per log file and then setting the directory's modification time with `os.utime`, by default to the time in its name (set last: writing the files changes it; left at the wall clock every archive would look new under controller decision 2); `make_backup(name, mtime)` with `os.utime`); `NOW = datetime(2026, 11, 18, 12, 0, 0)`; `service = DiskCleanupService(serverdata, now=lambda: NOW)`. Logs with `structlog.testing.capture_logs()` |
| 2 | same | **AC 1:** the 20 daily archives: exactly the 6 named 2026-11-04 and earlier are gone, 14 remain; 6 `disk_cleanup_deleted` lines with `kind="log_archive"`, the relative `path` and the right `bytes`; `disk_cleanup_finished` with `archives_deleted=6`, `archive_bytes` the sum, `archives_kept=14`, `errors=0`; the result dataclass matches. **Boundary:** an archive named exactly `now - 14 days` (`2026-11-04_12_00_00`) is kept, one second older is deleted. **Logs:** no logged value (in any test of this file that logs a path or an error) contains `str(tmp_path)` |
| 2 | same | **AC 2:** 7 archives older than 14 days: keep 5 -> the 5 newest remain; keep 0 -> only the newest remains (controller decision 1); keep 1000 -> all remain. **Decision 1:** a single archive 30 days old (name and mtime), keep 0, retention 1 -> it remains. **AC 3:** retention 0 with keep 0 and 20 old archives -> none deleted, no `disk_cleanup_deleted`, and `_scan` (monkeypatched to record its calls) is never called for `Archive/` |
| 2 | same | **AC 4 (controller decision 2):** retention 14, keep 0, NOW fixed: (a) name 30 days old, mtime 1 hour old -> kept; (b) name 1 day old, mtime 30 days old -> kept; (c) name and mtime 30 days old -> deleted; plus a newer archive so none of the three is the newest. **Boundary on mtime:** name 30 days old with mtime exactly `now - 14 days` -> kept, one second older -> deleted. **Order:** the keep-min order follows the names, not the mtimes: with keep 1, the archive with the newest name is the one kept even when another has a newer mtime (that other is then kept or deleted by its own age time) |
| 2 | same | **AC 5:** each non-matching name of the AC (including `"2026-11-01_03_00_00\n"` and full-width digits, if the file system accepts the name; skip that one case only by building it conditionally, never `pytest.skip`), a regular file named `2026-11-01_03_00_00`, a link `2026-11-01_03_00_00` -> a directory outside `serverdata` with a file in it: all remain, the target file remains, one WARNING `reason=symlink`; the link and the others are not counted as kept: with keep 1 and one real old archive plus these entries, the real one is kept and nothing else is deleted |
| 2 | same | **AC 6:** 8 files with mtimes 1..8 days old, a directory, a link to an outside file; keep 3 -> the 3 newest files, the directory, the link and its target remain; 5 `disk_cleanup_deleted kind="backup"`; keep 0 -> all remain and nothing is listed |
| 2 | same | **AC 7:** a full tree (`BackupSaves/x`, `Saves/default.vcdbs`, `Mods/m.zip`, `ModConfig/c.json`, `Playerdata/p.json`, `Logs/server-main.log` and the other five live logs, `serverconfig.json`, and `vsmanager/state/api-settings.json` beside `serverdata`), all files' mtimes 100 days old, limits retention 1, keep 0, backups 1, no archive and no backup: a snapshot (relative path -> bytes) of the whole `tmp_path` tree before equals the one after. **Links:** `Logs/Archive` a link to an outside directory holding old archive names; `Logs` a link to an outside directory; `Backups` a link to an outside directory with 5 files and keep 1: nothing outside is deleted, WARNING `reason=symlink` for each |
| 2 | same | **AC 8:** `_delete_tree` monkeypatched to raise `PermissionError` for one of three old archives: the other two are deleted, `disk_cleanup_delete_failed` (WARNING, with the path), `archives_deleted=2`, `errors=1`; the same for `_delete_file` with backups. **Listing fails:** `_scan` monkeypatched to raise `PermissionError` for `Archive/`: `errors=1`, the backup pass still deletes. **Missing:** no `serverdata`, no `Logs/Archive`, no `Backups`: zeros, no error |
| 2 | same | **Path check (a change between listing and deletion):** `_scan` monkeypatched to call the real one and then replace one old archive by a link of the same name to an outside directory (rename the directory away, `symlink_to`, then `os.utime(link, (t, t), follow_symlinks=False)` with the old archive's time: the modification time and the backup order are read with `lstat` after the scan, so a link left at the wall clock's time would be kept as new and never reach the path check): that entry is not deleted, its outside target and files remain, WARNING `reason=outside`; the other old archives are deleted. Likewise a backup file replaced by a link to an outside file after the scan (the link's own mtime set old the same way): not deleted, the target remains |
| 4 | `api/tests/jobs/test_disk_cleanup_job.py` (new) | `run_disk_cleanup(settings, now=...)` with `api-settings.json` holding retention 1, keep 0, backups 1 in the temp `state_dir` and two old archives (directory mtimes set to their names' times) and two backups: the older archive and the older backup deleted, the newest archive kept (controller decision 1); with no settings file the defaults apply (a 20-day-old archive among 6 is deleted only beyond the newest 5); **read at each run:** save retention 0 between two runs -> the second deletes nothing. `disk_cleanup()` (the `safe_job` wrapper) with `get_server_service` monkeypatched to the small fake: `disk_cleanup_started`, `disk_cleanup_finished`, `disk_cleanup_completed`; with the service's `run` raising `OSError` through a monkeypatch: `disk_cleanup_failed` and the wrapper returns `None` |
| 4 | `api/tests/test_jobs_registration.py` | **Registration:** `register_default_jobs` over `started_scheduler` with default settings, with all intervals 0, and with restart times: `disk_cleanup` is listed each time; `job_to_info` gives `trigger_type` `cron` and `trigger_details == "cron[month='*', day='*', day_of_week='*', hour='3', minute='0']"`; `next_run_time.astimezone()` has hour 3 and minute 0 and is within 24 h; with the Story 22.3 `local_tz` fixture set to `Europe/Berlin` the next run converted with `ZoneInfo("Europe/Berlin")` is 03:00. `register_disk_cleanup` twice -> one job (replaced). `apply_setting(scheduler, "log_archive_retention_days", 30)` changes no job |
| 4 | `api/tests/test_routers_config.py` | Over `reschedule_client`: POST each cleanup key -> 200 and `GET /api/v1alpha1/jobs` unchanged (same ids and next runs) |

All names in tests are placeholders. Tests reach private attributes and module functions through `monkeypatch.setattr` only (the `tests` execution environment sets `reportPrivateUsage = false`, `api/pyproject.toml`); add no file-level pyright relaxation.

### Existing tests that change (deliberately, Task 4)

1. `tests/test_jobs_registration.py:300-322` `test_jobs_not_registered_when_interval_zero` asserts `len(jobs) == 0` after `register_default_jobs` with every interval 0. From Task 4 `disk_cleanup` is always registered: assert that the registered ids are exactly `["disk_cleanup"]` (no interval job). The docstring says so.
2. `tests/test_jobs_registration.py:694-700` `no_real_jobs` and `tests/test_routers_config.py:2248-2262` `reschedule_scheduler`: no change needed (the conftest autouse no-op covers the cleanup job); do not duplicate it there.

Every other test stays as it is: `default_jobs_registered`'s `count` is unchanged (`:1051-1053` asserts `count == 3`), `tests/test_jobs_router.py:130-148` removes every job before asserting `[]`, `tests/test_main.py` patches `register_default_jobs`. Anything else that fails is a regression (AC 13): fix the code, not the test.

### The throwaway-container run (Task 3)

Run from the repo root after Task 2's commit; placeholder keys only (never `.env`'s); never the dev stack. The isolation is Story 22.3's (Dev Notes "The throwaway-container run" of `22-3-scheduled-restarts.md`): plain `docker build`/`docker run`, never `docker compose` (both compose files bind-mount `./data:/data`; `docker-compose.dev.yaml` is the dev stack on 9080 with game port 42420); no `-v`, `--mount` or `--env-file`, so `/data` lives in the container's writable layer and goes with `docker rm -f`; own names (`vss-22-4-*`), own port `127.0.0.1:18092` (not 9080, not e2e-ci's 18080/18081, not 22.3's 18090), own image tag; not `just test-e2e-ci` (it blocks the game download hosts).

```bash
IMAGE=vss-22-4-cleanup:local; NAME=vss-22-4-cleanup; BASE=http://127.0.0.1:18092
KEY=vss-22-4-placeholder-admin-key; H=(-H "X-API-Key: $KEY" -H "Content-Type: application/json")
docker rm -f "$NAME" >/dev/null 2>&1 || true   # leftovers of a killed run
docker build --platform linux/amd64 -t "$IMAGE" .
docker run -d --name "$NAME" --platform linux/amd64 -p 127.0.0.1:18092:8080 \
  -e VS_API_KEY_ADMIN="$KEY" -e VS_DATA_DIR=/data -e TZ=Europe/Berlin "$IMAGE"
# wait for $BASE/healthz, then:
curl -s "${H[@]}" -X POST "$BASE/api/v1alpha1/server/install" -d '{"version":"stable"}'
# poll GET /api/v1alpha1/server/install/status until installed; record the resolved version
```

- **Seven rounds:** before each start record `A=$(docker exec "$NAME" sh -c 'ls /data/serverdata/Logs/Archive 2>/dev/null | wc -l')`; `POST /server/start`; from round 2 wait until the archive count is `A+1` (the game moves the previous run's logs at start, so `server-main.log` still holds the previous run's ready line until then; Story 22.3's Debug Log), then until `grep -q 'now running' /data/serverdata/Logs/server-main.log`; record `docker exec "$NAME" sh -c 'date; date -u; ls /data/serverdata/Logs/Archive; stat -c "%y %n" /data/serverdata/Logs/Archive/*'` and, for the newest archive, `head -1 .../Archive/<name>/server-main.log`; wait 10 s; `POST /server/stop`. Expect 6 archives after round 7, each name equal to the logger-start line's time of the run it holds, in Berlin time (one hour ahead of `date -u` in November), each directory's modification time at or after its name's time (the start that archived it), and no name ever gone.
- **Backups**, in round 7 before its stop: `curl -s "${H[@]}" -X POST "$BASE/api/v1alpha1/console/command" -d '{"command":"/genbackup"}'`, wait until the console history shows the game's answer (`GET /api/v1alpha1/console/history`), 70 s, again; then `docker exec "$NAME" sh -c 'ls -la --time-style=full-iso /data/serverdata/Backups /data/serverdata/BackupSaves'`. Expect two regular files in `Backups/`.
- **Four service runs** after round 7's stop, each with `docker exec "$NAME" uv run --no-sync python -c "from vintagestory_api.config import Settings; from vintagestory_api.services.disk_cleanup import CleanupLimits, DiskCleanupService; print(DiskCleanupService(Settings().serverdata_dir).run(CleanupLimits(<days>, <keep>, <backups>)))"` (the log lines go to stdout as JSON):
  1. `(14, 5, 0)`: nothing deleted (all archives are from today).
  2. Then `docker exec "$NAME" sh -c 'cd /data/serverdata/Logs/Archive && for d in 30 31 32; do n="$(date -d "-$d days" +%Y-%m-%d_%H_%M_%S)"; cp -a "$(ls | head -1)" "$n"; touch -m -d "-$d days" "$n"; done; ln -s /etc "$(date -d "-40 days" +%Y-%m-%d_%H_%M_%S)"'` (the `touch` sets each copy's directory modification time to its name's age; without it the copies would be kept by controller decision 2); run `(14, 5, 0)`: exactly the three copies deleted, the link skipped with WARNING `reason=symlink`, `ls /etc | wc -l` the same before and after, the 6 real archives remain.
  3. `(14, 5, 1)`: the older of the two backups deleted, the newer kept.
  4. `(0, 5, 0)`: nothing deleted.
- **Clean up even after a failure:** `docker rm -f "$NAME"; docker image rm "$IMAGE"`; then `docker ps -a --filter name=vss-22-4` and `docker image ls vss-22-4-cleanup` are empty; record `uname -m` (an arm64 host runs the image emulated; Story 22.3 measured starts of about 14 s there).
- The game port is not published; the game's own network use (download) goes through Docker's default network.

### Documentation (Task 5)

- **Features bullet** (`README.md:17`): "**Scheduled jobs:** background tasks such as mod cache refreshes, daily scheduled restarts that warn players first, and a daily cleanup of old log archives (and old backups when you ask), with their status in the UI".
- **`### Logs and disk use`**, between "Scheduled restarts" and "Metrics", in the README's plain style:
  - A "who rotates what" table:

    | What | Who | How |
    |---|---|---|
    | The game's logs, `serverdata/Logs/server-*.log` | The game | At every start it moves the previous run's logs into `serverdata/Logs/Archive/<start time of that run>/` and begins new files; it also splits a file after `LogFileSplitAfterLine` lines (a game setting in `serverconfig.json`, 500000 by default). The manager does not touch these files |
    | The archives, `serverdata/Logs/Archive/` | The manager | Daily cleanup (below) |
    | `/genbackup` files, `serverdata/Backups/` | The manager, only when you set a limit | Daily cleanup (below) |
    | The world, `serverdata/BackupSaves/`, mods, player data | Nobody | Never deleted by the manager |
    | The manager's own log (standard output) | Docker or Kubernetes | Docker's `json-file` log driver options, or your Kubernetes log rotation |

  - The cleanup: every day at 03:00 in the container's time zone (`TZ`), the `disk_cleanup` job deletes archive directories older than `log_archive_retention_days` days (default 14; the age counts from the later of the start time in the folder's name and the folder's modification time, so the archive of a long run is not deleted the day it is made), always keeping the newest `log_archive_keep_min` (default 5) and never deleting the newest archive, even with 0; and, when `backup_keep_count` is above 0, keeps only that many newest files in `Backups/` (default 0 keeps all). It runs whether or not the game server is running, logs each deletion (`disk_cleanup_deleted`) and a summary (`disk_cleanup_finished`), and is listed in **Settings → Scheduled Jobs**. If the API is not running at 03:00 that day's cleanup is skipped.
  - The three settings with their bounds (retention 0 to 3650 days, 0 keeps all; kept 0 to 1000; backups 0 to 1000, 0 keeps all), and a `curl` example in the style of the scheduled restarts section: `curl -X POST http://<host>:8080/api/v1alpha1/config/api/settings/log_archive_retention_days -H "X-API-Key: <admin key>" -H "Content-Type: application/json" -d '{"value": 30}'`. A change applies at the next run. To keep every archive, set `log_archive_retention_days` to 0.
  - What it never touches: `BackupSaves/` (the game's own world backups), the world in `Saves/`, mods, player data, the live log files, anything reached through a symbolic link, and anything outside those two directories; names it does not recognise in `Archive/` are left alone.
  - The manager's stdout, with a compose example (not added to the shipped compose files; controller decision 4):

    ```yaml
    services:
      manager:
        logging:
          driver: json-file
          options:
            max-size: "10m"
            max-file: "5"
    ```

  - One release-note sentence is not needed here (the changelog has it); the section only describes the behaviour.
- No `.env.example` change (the settings are API settings, not environment variables).

### Not changed (do not "fix" these here)

- `services/scheduler.py` (no new method, no time zone argument, its `# type: ignore` comments stay), `models/jobs.py`, `routers/jobs.py`, `main.py`, the jobs API shape, the scheduler's `job_defaults`.
- `services/cache_eviction.py` and the mod cache (`VS_MOD_CACHE_MAX_SIZE_MB`); the mods directory's leftover `.tmp`/`.bak` files (`VSS-hv60`, not pulled in).
- `SCHEDULED_SETTINGS`, `apply_setting`, `update_setting`, `ApiSettingNotAppliedError`, `get_settings`' fall-back to defaults.
- The game's own log handling: no rotation, splitting or compression by the manager, and the live `server-*.log` files are never opened (ADR-10 decision 1). `LogFileSplitAfterLine` is not set or changed.
- The web (Story 22.6 adds the three fields), the Dockerfile and the compose files (the logging example is README text only), `.env.example`.
- `services/game_config.py`, `services/server.py` (Story 22.7 changes them; this story must not, so the two branches do not conflict).
- No on/off setting for the job, no configurable time, no catch-up of a missed run, no cleanup of `vsmanager/logs` (empty; the manager logs to stdout).

### API contract changes

- New API settings `log_archive_retention_days` (int, default 14, 0 to 3650), `log_archive_keep_min` (int, default 5, 0 to 1000), `backup_keep_count` (int, default 0, 0 to 1000): in `GET /api/v1alpha1/config/api` and settable with `POST /api/v1alpha1/config/api/settings/<key>` (`{"value": n}`); 400 `API_SETTING_INVALID` out of bounds. Additive.
- New job `disk_cleanup` in `GET /api/v1alpha1/jobs` (`trigger_type` `cron`), deletable with the existing `DELETE /jobs/{id}` (until the API restarts).
- New behaviour: archives older than 14 days (beyond the newest 5) are deleted every day by default. The release note says so.
- New log events: see "What is logged". No route, field or status code changes; nothing breaking.
- Web contract for Story 22.6: the three keys arrive camelCased (`logArchiveRetentionDays`, `logArchiveKeepMin`, `backupKeepCount`); the POST path keeps the snake_case key.
- Release note (scope stripped by git-cliff): Task 4's "delete old game log archives every day, and old backups when a limit is set".

### ADR against the code

1. **The name pattern is strict.** ADR-9 decision 3 writes `^\d{4}-\d{2}-\d{2}_\d{2}_\d{2}_\d{2}$`. In Python `\d` matches any Unicode digit and `$` matches before a trailing newline (checked on 3.14.10), so the story uses `[0-9]{4}-...` with `fullmatch`, and also requires `strptime` to parse the name (a name like `2026-13-45_00_00_00` is not an archive). Same lesson as Story 22.3's time validator.
2. **`Logs` itself is checked for a link too.** ADR-9 decision 5 names a symlinked `Archive` or `Backups` directory; a symlinked `Logs` would reach `Archive` through a link as well, so it is skipped the same way (AC 7).
3. **The name is the archived run's start time, so the age also reads the directory's modification time.** The ADR said "the age comes from the name, not from file times"; the dev stack's only archive shows the name is the time the archived run started (its first log line), not the time it was archived. A run that lasted longer than the retention would be archived with an already-old name and could be deleted at the next 03:00. Controller decision 2 (below) changes the rule: the age counts from the later of the name's time and the directory's modification time (`lstat`); the order for the keep minimum stays the names'. ADR-9 decision 3 is updated to say so.
4. **The container run comes after the service, before the job.** The epic lists it fourth (after the job). It runs the real service on the game's real archives, which needs Task 2's code, and a finding that would change the design (the game pruning its own archives, a different name format or zone, `/genbackup` writing a directory) must stop the story before the job is registered (Task 3.7). The epic's condition is kept.
5. **The job runs in a worker thread** (`asyncio.to_thread`). ADR-9 does not say; an `rmtree` of large debug logs on a slow disk would otherwise stall the event loop.
6. **The job's settings come from `get_server_service().settings`**, the `Settings` the routers use, not a fresh `Settings()`; both come from the environment.
7. **The permission-denied test uses a seam, not `chmod`.** AC 7 of the epic says "permission denied"; a test that removes write permission passes or fails depending on whether it runs as root. `_delete_tree`/`_delete_file` are monkeypatched to raise `PermissionError` for one entry.
8. **A conftest autouse no-op for the job.** Not in the ADR. `just test-api` runs with `VS_DATA_DIR=../dev`, so a registered cleanup that fired during a test run would delete in `dev/serverdata`; ADR-14 decision 1 (temporary directories for cleanup) requires that no test can reach real data.
9. **`disk_cleanup_finished` is logged by the service**, so the container run (which calls the service directly) logs it too; `safe_job` adds `disk_cleanup_started`/`_completed` around the job. ADR-9 decision 6 names the events, not the layer. Each deletion's `path` is relative to `serverdata` (the controller's wording) where the ADR says "name".
10. **The README section is "Logs and disk use" with the settings in it.** The epic's task says "the settings rows"; the README has no API settings table (the restart times are documented in their own section, Story 22.3), so the three settings are described in the new section with a `curl` example.

11. **The archive half is dropped (maintainer's decision, 2026-11-19).** ADR-9 decisions 1, 3 and 7 assumed the game never prunes its archives; Task 3 showed it keeps at most 5. The settings `log_archive_retention_days` and `log_archive_keep_min`, the archive pass, the name pattern and the age rule (and with them controller decisions 1 and 2 above) are removed; ADR-9 and ADR-10 are amended to say so. The job, the backup rules and the safety rules stay. Points 1 to 3 above now describe code that no longer exists.

### Controller decisions during validation (2026-11-18), for the maintainer to review

The story's open questions 1, 2, 3 and 5 were settled by the controller during validation. They are planner decisions, not the maintainer's answers; ADR-9 (and ADR-10 for decision 4) and the change proposal's list of planner decisions not reviewed yet carry them too.

1. **The newest log archive is never deleted, whatever `log_archive_keep_min` is (0 included),** so a cleanup during a game start (for example at a 03:00 scheduled restart) can never remove the archive just written. The setting keeps its bounds (0 to 1000); 0 behaves as 1. (Was open question 1.)
2. **An archive's age is measured from the later of the time in its directory's name and the directory's modification time** (`lstat`, links not followed), because the name is the archived run's start time and a long run would otherwise make a fresh archive look old. The keep-minimum order stays the names'. Tests for both cases (old name with a new modification time is kept; new name with an old modification time is kept). (Was open question 2.)
3. **03:00 container time stays** (ADR-9 decision 6; no setting, not tied to the restart times). (Was open question 3.)
4. **The Docker `logging` example is in the README only;** the shipped `docker-compose.yaml` (and `docker-compose.dev.yaml`) is not changed. (Was open question 5.)

### Open questions for the maintainer (none blocks the start)

1. Task 3 may come back with a question (Task 3.7): the game pruning archives, names in UTC under `TZ`, or `/genbackup` writing directories.

### Testing Requirements

**CRITICAL:** tests are written with each task and committed with it, red first. `just test-api <files>` after each task; `just check` before review.

- No lint or type suppression (`# type: ignore`, `# pyright: ignore`, `noqa`), no `cast`, no `as`-style escape (`typing.cast`, `Any`-typed stand-ins for typed parameters), no skipped test (`pytest.mark.skip`, `skipif`, `xfail`, `pytest.skip`), no `.only`. Pyright 0 errors and 0 warnings in `src` and `tests`.
- Deletion tests run only under `tmp_path`, with a fixed clock (`now=lambda: NOW`) and explicit `os.utime` times on every archive directory and backup file (an archive left at the wall clock's mtime is never old under controller decision 2); no test depends on the wall clock or the host's time zone, except the registration tests that use Story 22.3's `local_tz` fixture (it restores `TZ`, `time.tzset()` and `tzlocal.reload_localzone()`).
- Every test that builds a link points it at a directory inside `tmp_path` but outside the test's `serverdata`, and asserts the target and its files still exist afterwards. No test links to `/`, `/etc` or the home directory.
- Log assertions with `structlog.testing.capture_logs()`. Private module functions through `monkeypatch.setattr` only.
- Never run `just test-e2e-api`, `just test-e2e` or `just test-e2e-web` (they target the dev stack); never `just docker ...`. No E2E test is added: the cleanup deletes on the stack a run points at, and the unit tests cover the rules. Docker only for Task 3's `vss-22-4-cleanup` container.

### Security Requirements

- `POST /config/api/settings/...` and `GET`/`DELETE /jobs` stay Admin only; a Monitor key cannot change a limit or the job.
- The cleanup deletes only entries it listed itself in two fixed directories under `serverdata`, refuses links at every level, resolves and checks each path before deleting, and never builds a path from a request or a setting (the settings are integers).
- Log lines carry relative paths, sizes and counts; no absolute path, no file content, no key.
- The throwaway container uses placeholder keys, binds only `127.0.0.1:18092`, and is removed with its image; nothing from it is committed except names, sizes, counts and log lines without addresses.

### Development Commands

- `just test-api tests/test_api_settings.py tests/test_routers_config.py tests/test_disk_cleanup.py tests/jobs tests/test_jobs_registration.py tests/test_jobs_router.py tests/test_main.py tests/test_scheduler.py`, `just typecheck-api`, `just lint-api`.
- `cd api && uv run ruff format <changed files>` (`just format-api` takes no file arguments and formats the whole tree).
- `just check` (Task 6), `just changelog` (Task 6.2), `just sprint set 22-4-log-archive-and-backup-cleanup review`.

### Previous Story Intelligence

- **22.3** (this branch's base, in review): `SCHEDULED_SETTINGS` and `apply_setting` (keys outside it do nothing), `apply_restart_schedule`'s lazy import for monkeypatching, the `local_tz` fixture in `tests/test_jobs_registration.py:881`, the throwaway-container recipe and its clean-up check, the `trigger_details` format for a cron job, and the deviation it hit with "accepted" test rows that contradicted a rule (check each row of "API tests" against the rules before writing it). Its README sections are the style model. Its Debug Log: the game moves `server-main.log` into the archive at each start, so a wait on the ready line must first wait for the new archive.
- **22.2:** route tests over a real temp-dir service rather than a bare `MagicMock`; `reschedule_client` runs on the test's loop.
- **22.1:** user-visible commits use `feat(story-22.x/task-N)`; drawdowns are written in the Completion Notes.
- **21.3:** the depth and the "ADR against the code" record; completion notes must be true of the code.
- **19.4 / cache eviction (`services/cache_eviction.py`):** the existing deletion style (named entries, per-entry `OSError` logged at WARNING and skipped, a result dataclass with counts and bytes).

### Git Intelligence

- Branch `story/22-4-log-archive-and-backup-cleanup` from `story/22-3-scheduled-restarts` at `6fd76056` (`docs(epic-22): add story 22.7 for settings lost to a live change`; the code is that of `36dd18cf`). 22.3's commits: `6d7c8879` (container run), `d96b97ac` (setting), `7e537cd8` (sequence), `8ed3ede1` (cron jobs, `feat`), `a6dba65b` (README), `2f0a1cdd` (review).
- Planned commits: Task 1 `refactor(story-22.4/task-1): accept the disk cleanup limits in the API settings`; Task 2 `refactor(story-22.4/task-2): add the disk cleanup service for log archives and backups`; Task 3 `docs(story-22.4/task-3): record the game's log archives and backups and a cleanup run on them`; Task 4 `feat(story-22.4/task-4): delete old game log archives every day, and old backups when a limit is set`; Task 5 `docs(story-22.4/task-5): document who rotates which logs and the disk cleanup`; Task 6 `chore(story-22.4/task-6): validate and move story 22.4 to review`.

### Project Structure Notes

- New: `api/src/vintagestory_api/services/disk_cleanup.py`, `api/src/vintagestory_api/jobs/disk_cleanup.py`, `api/tests/test_disk_cleanup.py`, `api/tests/jobs/test_disk_cleanup_job.py`.
- Modified: `api/src/vintagestory_api/services/api_settings.py`, `api/src/vintagestory_api/jobs/__init__.py`, `api/tests/conftest.py`, `api/tests/test_api_settings.py`, `api/tests/test_routers_config.py`, `api/tests/test_jobs_registration.py`, `README.md`, `_bmad-output/planning-artifacts/architecture/epic-22-server-operations-and-metrics.md` (ADR-9 results, Task 3), this story file, and `sprint-status.yaml` (through `just sprint` only).
- Not touched: `services/scheduler.py`, `models/jobs.py`, `routers/jobs.py`, `main.py`, `services/cache_eviction.py`, `services/game_config.py`, `services/server.py`, the web, the Dockerfile, the compose files, `.env.example`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 22.4: Log Archive and Backup Cleanup] (`:7508-7594`) and the Epic 22 header (order, dependencies, product changes)
- [Source: _bmad-output/planning-artifacts/prd.md] FR297-FR299 (`:912-914`)
- [Source: _bmad-output/planning-artifacts/architecture/epic-22-server-operations-and-metrics.md] "Facts Checked in the Code" (Disk and logs, `:49-54`), ADR-7 (`:159-170`), ADR-9 (`:187-201`), ADR-10 (`:203-211`), ADR-14 (`:243-...`)
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-18-epic-22.md] sections 1 (answers 8, 9), 2 (contract table, draft release notes, risks: deletion, the default, the game's own pruning), 5 (planner decisions not reviewed: the 03:00 time and the safety rules; `VSS-hv60` and `VSS-3tb1` not pulled in)
- [Source: _bmad-output/implementation-artifacts/22-3-scheduled-restarts.md] (previous story: the container recipe, `local_tz`, the README style), [21-3-log-level-and-config-viewer.md] (depth)
- Beads: `VSS-29p` (API-011, scheduled restarts, disk cleanup and log rotation), parent `VSS-oole`
- Python 3.14.10 `shutil.rmtree` (`avoids_symlink_attacks`, refusal of a link, links inside not followed) and `re` (`\d`, `$` vs `[0-9]`, `fullmatch`), checked on the host in planning; APScheduler 3.11.3 `CronTrigger.from_crontab` time zone and `str(trigger)` (Story 22.3)
- `project-context.md`: tests with each task; no suppressions; "no silent failures"; commit types by user impact; `just` for every task; `RELEASING.md` "Commit messages are release notes"

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5), BMAD dev-story workflow, non-interactive

### Throwaway-container results

<!-- Task 3.6: host architecture, game version, the archive listing after each start (with the logger-start line and date/date -u), the Backups listing, the four service runs, the commands. -->

Run on 2026-11-19 from this branch at `8cf51967` (Tasks 1 and 2; no cleanup job is registered in that image).

- **Host:** `uname -m` = `arm64` (Docker 29.9.2); the `linux/amd64` image ran emulated.
- **Game version:** `stable` resolved to **1.22.7** (`POST /api/v1alpha1/server/install`). Fresh world created by the first start.
- **Isolation:** image `vss-22-4-cleanup:local`, container `vss-22-4-cleanup`, only `127.0.0.1:18092 -> 8080` published (game port not published), `TZ=Europe/Berlin`, placeholder admin key, no `-v`/`--mount`/`--env-file`, no compose; `docker inspect` showed `Mounts: []`. The dev stack was not touched.

**The archives after each start** (`date` / `date -u` in the container at the record; "first line" is the newest archive's `server-main.log` first line; "dir mtime" from `stat -c '%y'`):

| Round | Ready (`now running`) | `date` / `date -u` | `Logs/Archive` after the start | Newest archive's first line | Newest archive's dir mtime | Live `server-main.log` first line |
|---|---|---|---|---|---|---|
| 1 | 04:25:38 | 04:25:38 CET / 03:25:39 UTC | (none: the first start archives nothing) | - | - | `19.11.2026 04:25:16 [Notification] Server logger started.` |
| 2 | 04:26:05 | 04:26:06 CET / 03:26:06 UTC | `2026-11-19_04_25_16` | `19.11.2026 04:25:16 ... Server logger started.` | 04:25:50.688 +0100 | `19.11.2026 04:25:50 ...` |
| 3 | 04:26:32 | 04:26:32 CET / 03:26:32 UTC | `..._04_25_16`, `..._04_25_50` | `19.11.2026 04:25:50 ...` | 04:26:18.127 +0100 | `19.11.2026 04:26:18 ...` |
| 4 | 04:26:58 | 04:26:59 CET / 03:26:59 UTC | `..._04_25_16`, `..._04_25_50`, `..._04_26_18` | `19.11.2026 04:26:18 ...` | 04:26:44.531 +0100 | `19.11.2026 04:26:44 ...` |
| 5 | 04:27:24 | 04:27:25 CET / 03:27:25 UTC | the 3 above + `..._04_26_44` | `19.11.2026 04:26:44 ...` | 04:27:11.016 +0100 | `19.11.2026 04:27:11 ...` |
| 6 | 04:27:50 | 04:27:51 CET / 03:27:51 UTC | the 4 above + `..._04_27_11` (5 archives) | `19.11.2026 04:27:11 ...` | 04:27:37.393 +0100 | `19.11.2026 04:27:37 ...` |
| 7 | 04:28:16 | 04:30:14 CET / 03:30:14 UTC | **`..._04_25_50`, `..._04_26_18`, `..._04_26_44`, `..._04_27_11`, `..._04_27_37`: `2026-11-19_04_25_16` is gone** (still 5) | `19.11.2026 04:27:37 ...` | 04:28:02.762 +0100 | `19.11.2026 04:28:02 ...` |

(All archive names are `2026-11-19_HH_MM_SS`; "`..._`" abbreviates `2026-11-19_`.) Round 7's record came 2 minutes after the ready line because the wait for "archive count + 1" timed out (the count stayed at 5).

- **Names:** every name matches `[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{2}_[0-9]{2}_[0-9]{2}` and is the archived run's "Server logger started" time **in Berlin time** (one hour ahead of `date -u`), not UTC. Each directory's modification time is at or after its name's time (the start that archived it). As expected.
- **Pruning (stop rule):** the game deleted `2026-11-19_04_25_16` at round 7's start. Nothing in the manager can have done it: the image has no cleanup job (`docker logs` holds no `disk_cleanup` line and no line naming an archive). `serverconfig.json` has no archive setting (`grep -i archive` finds nothing; the only log settings are `LogBlockBreakPlace` and `LogFileSplitAfterLine: 500000`). So **the game keeps at most 5 log archives itself**, deleting the oldest at a start.

**`/genbackup`** (round 7, through `POST /api/v1alpha1/console/command`, game running):

```
19.11.2026 04:30:15 [Notification] Handling Console Command /genbackup
19.11.2026 04:30:15 [Error] Exception: Object reference not set to an instance of an object.
   at Vintagestory.Server.ServerSystemSupplyChunkCommands.GenBackup(IServerPlayer logToPlayer) in VintagestoryLib\Server\Systems\World\LoadThread\SupplyChunkCommands.cs:line 306
   at Vintagestory.Server.ServerSystemSupplyChunkCommands.onCmdGenBackup(TextCommandCallingArgs args) in VintagestoryLib\Server\Systems\World\LoadThread\SupplyChunkCommands.cs:line 290
   ... (ChatCommandImpl, ServerMain.ReceiveServerConsole, ServerConsole, ServerMain.ProcessMain frames)
19.11.2026 04:31:27 [Notification] Handling Console Command /genbackup
19.11.2026 04:31:27 [Notification] Can't run backup. A backup is already in progress
19.11.2026 04:31:27 [Notification] Ok, generating backup, this might take a while
19.11.2026 04:35:44 [Notification] Server termination event SIGTERM received. Shutting down server
```

`ls -la --time-style=full-iso` right after the second call, and again after the stop: `Backups/` and `BackupSaves/` both empty (only `.` and `..`, created 04:25:16 by the first start). **No backup file was written** in over 4 minutes: the first call failed with a `NullReferenceException` inside the game, which apparently left its "backup in progress" flag set, and the second refused yet also said it was generating. What `/genbackup` writes into `Backups/` is therefore still unknown (stop rule: not "one regular file directly in `Backups/`").

**The four service runs** (after round 7's stop; `docker exec vss-22-4-cleanup uv run --no-sync python -c "... DiskCleanupService(Settings().serverdata_dir).run(CleanupLimits(<days>, <keep>, <backups>))"`; the container logged in console format):

1. `(14, 5, 0)`: `disk_cleanup_finished archive_bytes=0 archives_deleted=0 archives_kept=5 backup_bytes=0 backup_keep_count=0 backups_deleted=0 backups_kept=0 errors=0 log_archive_keep_min=5 log_archive_retention_days=14`. Nothing deleted, as expected.
2. After three copies of `2026-11-19_04_25_50` named and `touch -m`-dated 30, 31 and 32 days back (`2026-10-20_04_36_08`, `2026-10-19_04_36_08`, `2026-10-18_04_36_08`; `stat` showed their mtimes at those times, +0200) and a link `2026-10-10_04_36_08 -> /etc`; `ls /etc | wc -l` = 84 before and after. `(14, 5, 0)`:
   ```
   [warning] disk_cleanup_skipped path=Logs/Archive/2026-10-10_04_36_08 reason=symlink
   [info] disk_cleanup_deleted bytes=233676 kind=log_archive path=Logs/Archive/2026-10-20_04_36_08
   [info] disk_cleanup_deleted bytes=233676 kind=log_archive path=Logs/Archive/2026-10-19_04_36_08
   [info] disk_cleanup_deleted bytes=233676 kind=log_archive path=Logs/Archive/2026-10-18_04_36_08
   [info] disk_cleanup_finished archive_bytes=701028 archives_deleted=3 archives_kept=5 ... errors=0
   ```
   Exactly the three copies deleted, the link skipped with WARNING, `/etc` intact, the 5 real archives (and the link) remain. As expected.
3. `(14, 5, 1)`: the link skipped again (WARNING), `archives_deleted=0 backups_deleted=0 backups_kept=0 errors=0`. **Not the expected result** ("the older of two backups deleted"): there was no backup to delete, because `/genbackup` wrote none.
4. `(0, 5, 0)`: `archives_deleted=0 archives_kept=0 ... errors=0`; nothing deleted, as expected.

**Commands** (repo root; `api.sh METHOD PATH [json]` is a scratch wrapper around `curl -s -H "X-API-Key: vss-22-4-placeholder-admin-key" -H "Content-Type: application/json" -X METHOD http://127.0.0.1:18092PATH -d json`):

```bash
docker rm -f vss-22-4-cleanup >/dev/null 2>&1 || true
docker build --platform linux/amd64 -t vss-22-4-cleanup:local .
docker run -d --name vss-22-4-cleanup --platform linux/amd64 -p 127.0.0.1:18092:8080 \
  -e VS_API_KEY_ADMIN=vss-22-4-placeholder-admin-key -e VS_DATA_DIR=/data -e TZ=Europe/Berlin vss-22-4-cleanup:local
api.sh POST /api/v1alpha1/server/install '{"version":"stable"}'   # polled GET .../server/install/status
# each of 7 rounds: count archives; start; from round 2 wait (<= 120 s) for count + 1; wait for 'now running'; record; sleep 10; stop
api.sh POST /api/v1alpha1/server/start
docker exec vss-22-4-cleanup sh -c 'date; date -u; ls /data/serverdata/Logs/Archive; stat -c "%y %n" /data/serverdata/Logs/Archive/*'
docker exec vss-22-4-cleanup head -1 /data/serverdata/Logs/Archive/<newest>/server-main.log
api.sh POST /api/v1alpha1/server/stop
# round 7, game running:
api.sh POST /api/v1alpha1/console/command '{"command":"/genbackup"}'   # twice, 70 s apart; GET .../console/history
docker exec vss-22-4-cleanup sh -c 'ls -la --time-style=full-iso /data/serverdata/Backups /data/serverdata/BackupSaves'
# the four service runs and the old copies: as in Dev Notes "The throwaway-container run"
docker rm -f vss-22-4-cleanup; docker image rm vss-22-4-cleanup:local
docker ps -a --filter name=vss-22-4      # empty
docker image ls vss-22-4-cleanup         # empty
git status --short dev/ data/            # empty
```

Cleanup done: the container and the image were removed; both listings and `git status --short dev/ data/` were empty.

### Debug Log References

- Task 1: red first (`ImportError` for `MAX_BACKUP_KEEP_COUNT`; the router's defaults and save tests failed), then green: `just test-api tests/test_api_settings.py tests/test_routers_config.py tests/test_jobs_registration.py` 410 passed; pyright 0/0.
- Task 4: drafted while Task 3's container ran (red: the module and `register_disk_cleanup` did not exist; then green), stashed at the stop rule, restored after Task 3a and adapted to backups only (red again: the draft read `log_archive_retention_days` from the settings; then green). `run_disk_cleanup(settings)` lost its `now` argument with the service's. `just test-api tests/jobs tests/test_jobs_registration.py tests/test_routers_config.py tests/test_jobs_router.py tests/test_main.py tests/test_disk_cleanup.py tests/test_scheduler.py tests/test_api_settings.py`: 523 passed; pyright 0/0; ruff clean.
- Task 3a (maintainer decision): red first (14 failures and 1 failing assertion: `CleanupLimits` still required the two archive limits, `ApiSettings` still had the fields), then green: the four affected test files 408 passed; pyright 0/0, ruff clean. `DiskCleanupService` lost its `now` argument too: with no archive pass nothing reads the clock (backups are ordered by modification time).
- Task 3: the 7-round script waited up to 120 s for the archive count to reach the count before the start + 1; in round 7 it never did (the game deleted one archive as it added one), which is how the pruning showed.
- Task 2: red first was an `ImportError` at collection (the service module did not exist), not 28 individual failures; then 28 passed; pyright 0/0, ruff clean. The newline and full-width archive names are created on the host's APFS, so those cases run (built conditionally, never skipped).

### Completion Notes List

- 2026-11-18: Story created (create-story, non-interactive) and checked against the create-story checklist: 6 tasks; every code task carries its tests (Task 3 is a container check, Task 5 documentation, Task 6 validation); every AC is mapped to a task (AC 13 to every code task and Task 6, AC 14 to Task 6.3).
- 2026-11-18: Validated (create-story checklist, fresh context) against the epic, ADR-7/9/10/14, project-context.md, CLAUDE.md and the code at `4bc01ea1` (every line reference re-checked; the Python 3.14.10 `shutil.rmtree`, `re` and `strptime` claims re-run). Applied the four controller decisions (Dev Notes "Controller decisions during validation"; ADR-9, ADR-10 and the change proposal updated). Fixed: AC 2 and AC 4 for decisions 1 and 2, the archive rules ("What is deleted"), the settings' descriptions, the test rows (explicit directory mtimes in `make_archive`, decision 1 and 2 cases, mtime boundary, keep order), Task 3's old copies (`touch -m` so decision 2 does not keep them) and the mtime record; `disk_cleanup_delete_failed` logs `e.strerror` and `errno`, not `str(e)` (an `OSError`'s text holds the absolute path); `_delete_tree` must not pass `onexc`/`ignore_errors`; the link check comes before the directory check; the conftest fixture lands once `jobs/disk_cleanup.py` exists (its string target imports it).
- 2026-11-19: Tasks 1 and 2 done (dev-story). Task 1: the three settings with their bounds, not in `SCHEDULED_SETTINGS`. Task 2: `DiskCleanupService` with the archive and backup rules, the link and path checks and the log lines of Dev Notes; 28 tests in `tests/test_disk_cleanup.py`.
- 2026-11-19: Task 3 done (throwaway container, game 1.22.7, `TZ=Europe/Berlin`). Archive names and their zone are as expected (the archived run's start time in Berlin time; the directory's mtime is the archiving start), and the service deleted exactly the expected entries in the archive runs. **Task 3.7 stop rule fired, twice:**
  1. **The game prunes its own log archives.** At round 7's start it deleted the oldest archive (`2026-11-19_04_25_16`) as it added a new one, keeping 5. No manager code ran a deletion (no cleanup job in that image, no such log line), and `serverconfig.json` has no archive setting. ADR-9 decision 7's premise ("the game does not prune archives itself") does not hold.
  2. **`/genbackup` wrote nothing.** The first call failed inside the game (`NullReferenceException` in `ServerSystemSupplyChunkCommands.GenBackup`); the second answered "Can't run backup. A backup is already in progress" and "Ok, generating backup, this might take a while"; `Backups/` and `BackupSaves/` stayed empty until the stop more than 4 minutes later. What `/genbackup` writes is still unconfirmed, and the backup service run (3) had nothing to delete.
  
  **Question for the maintainer (through the controller), with the evidence in "Throwaway-container results":** (a) the game already keeps at most 5 archives, the same number as `log_archive_keep_min`'s default: should the manager's archive cleanup still ship (it then only matters when the game's own limit is larger or changes, or for archives left by other versions), ship with other defaults, or be dropped in favour of documenting the game's own limit? Note that with the game's 5 and the default 14 days, the manager would never delete an archive the game keeps. (b) Is the backup half kept as designed without a confirmed `/genbackup` output (one more container run on a world that has played longer, or a different command, could confirm it), or deferred? Task 4 (the job, the only `feat` commit) and Tasks 5 and 6 wait for the answer; the story stays `in-progress`.
  
  Deviation: Task 4's code and tests were drafted in the working tree while the container ran (tests red first, then green: 396 passed in the Task 4.5 set, pyright 0/0) but are **not committed**; they were set aside with `git stash push -u -m "story-22.4 task-4 draft (uncommitted, awaiting the Task 3.7 answer)"` so the Task 3 commit holds only the record. Nothing was registered in any committed code.
- 2026-11-19: **Maintainer decision (Matt, through the controller): "Backups only + docs".** The log-archive cleanup and its two settings (`log_archive_retention_days`, `log_archive_keep_min`) are dropped, since the game already keeps at most 5 archives; the opt-in `backup_keep_count` (default 0 = keep all) and the daily `disk_cleanup` job for it (03:00 container time) stay; the README says the game keeps 5 log archives itself and who rotates what. Recorded in Dev Notes "Maintainer decision after Task 3" and "ADR against the code" 11; ACs 1 to 5 marked removed, ACs 7 to 10, 12 and 14 amended, Task 3a added, Tasks 4.6, 5 and 6.3 amended (history kept). ADR-9 and ADR-10, FR297 (`prd.md`), the Story 22.4 entry and FR297 coverage row (`epics.md`) and the change proposal's decisions amended to match.

- 2026-11-19: Tasks 3a to 6 done. Task 3a: the two archive settings removed (saving them is now 400 `API_SETTING_UNKNOWN`), the service handles `Backups/` only and never reads `Logs/`. Task 4: `disk_cleanup` registered at 03:00 whatever the settings, reading `backup_keep_count` at each run, in a worker thread; conftest autouse no-op keeps every registered job in tests away from `dev/`. Task 5: README "Logs and disk use" and the Features bullet. Task 6: `just check` green (API 3697 passed, web 3567 passed in 137 files with 0 skipped, script suites green, pyright 0 errors 0 warnings in `src`/`tests` and in `scripts`, ruff and Prettier clean); no suppression, cast, skip or `.only` in the added lines; `scheduler.py`, `models/jobs.py`, `routers/jobs.py`, `main.py`, `cache_eviction.py`, `game_config.py`, `server.py`, the web, the Dockerfile, the compose files and `.env.example` unchanged since `6fd76056`; `git status --short dev/ data/` empty. `just changelog` lists one new entry from this story: "Delete old backups every day when a limit is set" (`a14103e1`). Manual check 6.3 and the bead (6.6) are left for the maintainer.
- Deviations: the archive half was built (Tasks 1 and 2) and then removed (Task 3a) by the maintainer's decision; the `/user` commits are outside the planned task list. `DiskCleanupService` and `run_disk_cleanup` have no `now` argument (nothing reads the clock with backups only). The Task 4 draft was stashed during the stop rule and restored after it.
- Drawdown items (not done here, for the maintainer): (1) ADR-13 decision 2 and Story 22.6's acceptance criterion in `epics.md` (the "Disk Cleanup" group with three number fields) and the Epic 22 header's "Product changes" line (four new settings; archives deleted by default) and change-proposal section 2 (contract table, draft release notes) still name the two dropped settings; Story 22.6 should show `backup_keep_count` only. (2) What `/genbackup` writes is unconfirmed: in Task 3 its first call failed inside the game (`NullReferenceException`) and no file appeared; a run on a world that has played longer could confirm it and whether the game's failure is a bug worth reporting upstream. (3) `VSS-29p`'s AAR and close wait for merge and the maintainer's go-ahead (6.6).
### File List

- `api/src/vintagestory_api/services/api_settings.py` (Task 1: three constants and fields; Task 3a: two of them removed, `backup_keep_count` and `MAX_BACKUP_KEEP_COUNT` remain)
- `api/tests/test_api_settings.py` (Tasks 1 and 3a)
- `api/tests/test_routers_config.py` (Tasks 1, 3a and 4)
- `api/src/vintagestory_api/services/disk_cleanup.py` (Task 2, new; Task 3a: backups only; review: deletes relative to the opened `Backups/`)
- `api/tests/test_disk_cleanup.py` (Task 2, new; Task 3a: rewritten for backups only; review: seams take the open directory, two swap tests)
- `_bmad-output/planning-artifacts/architecture/epic-22-server-operations-and-metrics.md` (Task 3: ADR-9 "Results (Story 22.4)"; Task 3a: ADR-9 and ADR-10 amended)
- `_bmad-output/planning-artifacts/prd.md` (Task 3a: FR297, FR299)
- `_bmad-output/planning-artifacts/epics.md` (Task 3a: Story 22.4 entry, FR297 coverage row)
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-11-18-epic-22.md` (Task 3a: answers 8 and 9, the controller decisions)
- `README.md` (Task 5: Features bullet, "Logs and disk use")
- `api/src/vintagestory_api/jobs/disk_cleanup.py` (Task 4, new)
- `api/src/vintagestory_api/jobs/__init__.py` (Task 4: `register_disk_cleanup`, called from `register_default_jobs`)
- `api/tests/conftest.py` (Task 4: autouse no-op for the job)
- `api/tests/jobs/test_disk_cleanup_job.py` (Task 4, new)
- `api/tests/test_jobs_registration.py` (Task 4)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (through `just sprint` only: in-progress, then review)
- `_bmad-output/implementation-artifacts/22-4-log-archive-and-backup-cleanup.md` (this file)

## Review

Reviewer: GLM-5.3-Flash via opencode. Verdict: approve. 0 HIGH, 0 MEDIUM, one LOW finding, fixed; two notes, accepted without a change.

1. **LOW: a `Backups/` swapped for a link between the path check and the deletion could send the deletion elsewhere.** `_delete` resolved and re-checked each path, then called `path.unlink()`, which walks the path again: a `Backups/` replaced by a symbolic link in that window would have the file of the same name deleted in the link's target. Fixed: `Backups/` is opened once per run with `os.open(target, O_RDONLY | O_DIRECTORY | O_NOFOLLOW)`; the entries are listed with `os.scandir(fd)`, each modification time and the check before each deletion use `os.stat(name, dir_fd=fd, follow_symlinks=False)`, and the deletion is `os.unlink(name, dir_fd=fd)`; the descriptor is closed in a `finally`. The check before each deletion is now "still a regular file" (`stat.S_ISREG`); a link or a directory found there is skipped with the same WARNING `disk_cleanup_skipped reason=outside` (the old resolve check is gone: the Dev Notes paragraph "The path check before every deletion" describes the code as first built). A link put in place between `_target`'s look and the open is refused by the open (`ELOOP` on macOS, `ENOTDIR` on Linux) and logged as `reason=symlink` like a link found by `_target`; any other open error is `disk_cleanup_delete_failed path=Backups`, as a failed listing was. Every log line and field is unchanged. The seams changed with it: `_scan(directory_fd)` and `_delete_file(name, directory_fd)`; the tests that replace them were adapted (the "logs are never read" test compares the scanned directory's device and inode with `Backups/`'s). New tests: `test_backup_dir_replaced_by_a_link_after_it_is_opened` (the real `Backups/` renamed and a link to a directory holding older files of the same names put in its place right after the listing: the two old backups are deleted from the renamed directory, the link's target is unchanged; on the old code it failed) and `test_backup_dir_replaced_by_a_link_before_it_is_opened` (nothing deleted, one `reason=symlink` WARNING).
2. **Notes (two):** recorded by the reviewer for information and accepted as they stand; no change.

Fix commit: `refactor(story-22.4/review): delete backups relative to the opened Backups directory`. `just check` green after it (API 3703 passed, web 3567 passed, pyright 0 errors and 0 warnings).

## Change Log

- 2026-11-18: Story 22.4 created (ready-for-dev).
- 2026-11-18: Validated; four controller decisions applied (newest archive always kept; age from the later of name and directory mtime; 03:00 stays; logging example in the README only); fixes listed in Completion Notes.
- 2026-11-19: Tasks 1 to 3 done; Task 3.7 stop rule fired (the game keeps at most 5 log archives itself; `/genbackup` wrote no file). Waiting for the maintainer's answer before Task 4.
- 2026-11-19: Maintainer decision "Backups only + docs": log-archive cleanup and its two settings dropped; backups opt-in and the daily job kept. ACs and tasks amended (history kept); Task 3a added.
- 2026-11-19: Tasks 3a to 6 done; `just check` green; status review.
- 2026-11-19: Code review (GLM-5.3-Flash via opencode): approve; 0 HIGH, 0 MEDIUM, one LOW fixed (backups are listed, checked and deleted relative to `Backups/` opened once without following a link), two notes accepted (see "Review"). Status done.
