# Sprint Change Proposal: Server Operations and Metrics (Epic 22)

**Date:** 2026-11-18
**Author:** BMAD planner (PM and Architect), for Matt
**Workflow:** correct-course (scope named by the maintainer; product decisions asked one at a time)
**Scope classification:** Minor
**Status:** Scope named by Matt before planning (2026-11-18): `VSS-bhw`, `VSS-29p` and `VSS-9jv`, plus any open bead that shares their files. The same day he answered eleven questions (section 5); `VSS-zws` is pulled in and `VSS-hv60`, `VSS-3tb1` and `VSS-7z3` are not. Six stories, four beads. Revised the same day: after Story 22.3's Task 1 confirmed `VSS-zws`, a twelfth answer added Story 22.7 to fix it (seven stories, still four beads). No question is open. Planner decisions not reviewed yet are listed in section 5.

## 1. Issue Summary

**Trigger:** Epic 21 is done and released (`v0.1.0-rc.7`; `main` at `e16a7932` after the dev stack's port moved to 9080). The maintainer named the next epic: server operations and metrics, built from three open beads. `VSS-bhw` (P0) asks for the game server's metrics on `/metrics`; `VSS-29p` (P1, size-l) asks for scheduled restarts, disk cleanup and log rotation; `VSS-9jv` (P3) is the API Settings tab's inability to turn a job off. The backlog rule (2026-11-17) applies: the epic draws the backlog down, related beads that share its files are proposed as pull-ins, and what planning finds goes into a story.

**Problem:** An operator can see the game's CPU and memory on the dashboard, but not how many players are online, and cannot scrape anything into Prometheus, which the PRD promised. The game is restarted only by hand. Its log archives and backups grow without limit. The API accepts 0 to turn a job off, and the UI cannot send it.

**Evidence** (code at `e16a7932`; details and line references in `architecture/epic-22-server-operations-and-metrics.md`, "Facts Checked in the Code"):

- `MetricsSnapshot` already holds the game's memory and CPU (`models/metrics.py:12`, `services/metrics.py:127`); uptime is in the server status and `/healthz` (`services/server.py:912-914`, `routers/health.py:144`). There is no player count and no Prometheus endpoint; the PRD lists one (`prd.md:147`, `:185`, `:283`).
- The game's output is read only by `ServerService._read_stream` (`services/server.py:1234`). `VintagestoryLib.dll` v1.22.7 holds the literals `'{0} {1} joins.'`, `'Player {0} left.'`, `'Client {0} disconnected.'` and `'{0} joined again, killing previous client.'`. No client has joined the dev stack, so the printed prefix is not observed.
- A stop sends SIGTERM and kills after 10 seconds (`services/server.py:1058`, `:1073-1110`); the time a world save needs is not known. No cron job exists; the container is UTC with no `TZ`.
- The game archives each run's logs into `serverdata/Logs/Archive/<YYYY-MM-DD_HH_MM_SS>/` at start and splits files at `LogFileSplitAfterLine` (500000). `Backups/` and `BackupSaves/` exist. The mod cache is already size-limited (`services/cache_eviction.py`). The manager logs to stdout only.
- `ApiSettingsPanel.tsx` caps Mod List Refresh at 1 day and Server Versions Refresh at 7 days (the API allows 365 days), offers no Off and no Metrics Collection field, and two fallbacks differ from the API defaults (`:145`, `:162-174`). `SettingsPage.tsx:51` shows the Admin-only tab to a Monitor key.

**Scope decisions (made by the maintainer, 2026-11-18):**

| Decision | Choice |
|---|---|
| Items in scope | `VSS-bhw`, `VSS-29p`, `VSS-9jv`, and `VSS-zws` pulled in (answer 11) |
| Backlog rule | The epic draws the backlog down; findings go into stories; the net bead change is reported |
| What `/metrics` is | A Prometheus text endpoint at the root, and players added to the JSON metrics and the dashboard (answer 1) |
| Who may read it | Open, like `/healthz` (answer 2) |
| Metric set | The bead's four and a few extras: info, up, state, max players, pending restart, the manager's own process metrics (answer 3) |
| Player count | Parsed from the game's join and leave lines (answer 4) |
| Restart schedule | Daily `HH:MM` times, empty by default, in the container's time zone (answer 5) |
| Warnings | `/announce` at 15, 5 and 1 minutes, fixed text (answer 6) |
| Condition | Restart whenever the game runs, players or not; never start a stopped game (answer 7) |
| Disk cleanup | Log archives older than 14 days, newest 5 kept; backups kept to N only when N is set (default keep all); `BackupSaves` never (answer 8) |
| Log rotation | The game's; the manager only prunes archives (answer 9) |
| Interval fields | An On switch per interval; refresh fields 60 s to 365 days; Metrics Collection 1 s to 1 h (answer 10) |

**Grouping:**

| Story | Beads | Why this grouping |
|---|---|---|
| 22.1 Players Online Are Counted | `VSS-bhw` (first half) | The player count is new data that both the JSON metrics and Prometheus need; it is built and reviewed first, with its dashboard card |
| 22.2 A Prometheus `/metrics` Endpoint | `VSS-bhw` (closes) | A new dependency, a new open route and the metric contract: one pull request to review the names and the exposure |
| 22.3 Scheduled Restarts | `VSS-29p` (first half), `VSS-zws` | The restart job, its warnings and the measurement of the stop it relies on; `VSS-zws` needs the same running-then-stopped game in the same throwaway container |
| 22.4 Log Archive and Backup Cleanup | `VSS-29p` (closes) | Deletion is the riskiest change; it gets its own review. Log rotation is documentation here (answer 9) |
| 22.5 Interval Fields Can Turn Jobs Off | `VSS-9jv` | The bead, with the bounds, fallbacks and Monitor tab found in planning in the same two files |
| 22.6 Restart and Cleanup Settings in the UI | none | The web half of 22.3 and 22.4's settings, after 22.5 because both edit `ApiSettingsPanel.tsx` |
| 22.7 Restart-Required Settings Survive a Live Change | `VSS-zws` (closes) | Added by answer 12 after 22.3 confirmed the bug: a small API fix, run after 22.4 and before 22.5; 22.5 and 22.6 do not depend on it |

## 2. Impact Analysis

**Epic impact:** Epics 1 to 21 are done; none is invalidated. One new epic, Epic 22: Server Operations and Metrics, with 6 stories (7 after answer 12 added Story 22.7). No resequencing.

**Story impact:** No existing story changes. Story 22.2 builds the Prometheus endpoint that Epic 1's PRD listed as post-MVP. Story 22.3 generalises the scheduler callback of Story 17.6 (Epic 17 ADR-5) beyond interval settings, keeping its saved-but-not-applied error.

**Artifact conflicts:**

| Artifact | Change |
|---|---|
| PRD | Add FR287-FR305 (FR306 added in Story 22.2's validation, FR307 with Story 22.7); frontmatter. Story 22.2 updates the post-MVP line on Prometheus |
| Epics | Add Epic 22; FR coverage rows; Story Summary row (134 stories; 135 with Story 22.7); frontmatter |
| Architecture | New `architecture/epic-22-server-operations-and-metrics.md` (facts, ADR-1 to ADR-14; ADR-15 with Story 22.7); index entry |
| UX spec | No text change. The two new settings groups (ADR-13) follow the existing `SettingGroup` pattern |
| CI | No new job. Story 22.2 adds one API E2E test to the existing E2E job |
| Project rules | None |
| Deployment and documentation | README: the metrics section and scrape example (22.2), `TZ` and scheduled restarts (22.3), "Logs and disk use" (22.4). No deployment has to change; an operator who wants local times sets `TZ` |
| Beads | Epic `Epic 22: Server Operations and Metrics` with the four in-scope issues as children |

**Technical impact:**

- One new runtime dependency, `prometheus-client` (approved by answer 1), with a minimum version.
- `ServerService` gains a consumer of every output line (the tracker). A fault in it must not lose console lines (ADR-1 decision 1).
- Two new kinds of background job: one cron job per restart time and a daily cleanup. The scheduler already supports cron.
- The first list-valued API setting; `update_setting` is extended for it.
- The cleanup deletes files on the data volume. ADR-9 limits it to two directories, named entries and no symbolic links, with tests for every refusal.
- `ApiSettingsPanel.tsx` and `DurationSettingField` change in Stories 22.5 and 22.6.

**API contract and configuration changes (for the release notes):**

| Story | Where | Change | Kind |
|---|---|---|---|
| 22.1 | `GET /api/v1alpha1/metrics/current`, `/history` | Each snapshot gains `playersOnline` (number, or null when the game is not running) | Additive field |
| 22.2 | `GET /metrics` | New, at the root, no API key, Prometheus text format | New route |
| 22.3 | API setting `scheduled_restart_times` | New: list of `HH:MM`, default `[]` | New setting |
| 22.3 | Jobs | New `scheduled_restart_HHMM` jobs, listed by `GET /api/v1alpha1/jobs` | New jobs |
| 22.3 | `TZ` | Documented: scheduled restarts and cleanup follow it (UTC when unset) | Documentation |
| 22.4 | API settings `log_archive_retention_days`, `log_archive_keep_min`, `backup_keep_count` | New, defaults 14, 5, 0 | New settings |
| 22.4 | Job `disk_cleanup` | New, daily at 03:00 container time; deletes old log archives by default | New behaviour |
| 22.5 | API Settings tab | Shown to Admin only | Web-only |
| 22.7 | `serverconfig.json`, `vsmanager/state/pending-config-edits.json` | A restart-required game setting saved while the game runs is written again after the game exits and before any start; the new state file keeps it across API restarts | Fix, new state file |

No route is removed, no existing field changes, and nothing is breaking. The cleanup's default deletes log archives older than 14 days (the newest 5 kept); the release note says so, and setting `log_archive_retention_days` to 0 keeps all.

**Draft release-note text** (commit subjects; the story scope is removed by git-cliff):

- Features: `feat(api): count the players online and include them in the metrics`; `feat(web): show the players online on the dashboard`; `feat(api): serve game server metrics for Prometheus at /metrics`; `feat(api): restart the game server at scheduled times, warning players first`; `feat(api): delete old game log archives every day, and old backups when a limit is set`; `feat(web): turn scheduled jobs off and on, and set metrics collection, in API Settings`; `feat(web): set restart times in API Settings`; `feat(web): set disk cleanup limits in API Settings`
- Fixes: `fix(api): show Restart required when a game setting change needs a restart` (Story 22.2, pulled in during its validation); `fix(web): hide the API Settings tab from read-only keys`; `fix(web): allow refresh intervals up to 365 days, as the API does`; and, from Story 22.7, `fix(api): keep a Port or Ip change saved while the server runs when a later live setting change rewrites the config` (Story 22.3 made no code change for `VSS-zws`)
- No note: the dependency (`build`), tests, documentation, the throwaway-container measurements

## 3. Recommended Approach

**Selected:** Option 1, Direct Adjustment: add Epic 22 within the existing structure.

| Option | Assessment |
|---|---|
| 1. Direct Adjustment | Viable. Six stories, each tied to an in-scope bead. Effort medium, risk medium (22.3 and 22.4 act on the game and the disk) |
| 2. Rollback | Not viable. Nothing completed has to be undone |
| 3. MVP Review | Not needed |

**Effort:** Medium. `VSS-29p` is size-l and is two stories; `VSS-bhw` is size-m and is two stories; `VSS-9jv` and the two UI halves are small.

**Risks:**

- Story 22.1: the printed prefix of the join and leave lines is not observed; until the maintainer's sample arrives, the patterns match the literals only. The manual check is a task, and the count can drift if a game update changes the text.
- Story 22.1: a fault in the tracker inside `_read_stream` could stop console capture. The tracker runs after the append and its errors are caught (ADR-1 decision 1).
- Story 22.2: an open endpoint exposes the game version and player count to whoever reaches the API. Answer 2 accepts it; the README says how to keep it off the internet.
- Story 22.3: a restart while players are online loses their progress if the 10-second stop cuts the world save short. The stop is measured first; a slow stop stops the story for the maintainer's decision (ADR-8).
- Story 22.3: time zones. A wrong `TZ` restarts at the wrong hour. The README documents it and the job's next run is visible in Scheduled Jobs.
- Story 22.3: the jobs' next run shown in Scheduled Jobs is the warning time, 15 minutes before the restart. The job id names the restart time (ADR-6 decision 7).
- Story 22.4: deleting files. The rules are narrow (two directories, named entries, no links, a resolve check) and each refusal has a test. The default deletes archives, which no operator asked for before; the release note says so.
- Story 22.4: whether the game prunes its own archives is not observed; the throwaway run checks it before the job ships.
- Stories 22.3, 22.4: tests must not restart the dev stack's game server. Stubs, a fake sleep and throwaway `vss-22-*` containers only (ADR-14).
- Stories 22.5, 22.6: both edit `ApiSettingsPanel.tsx` and run one after the other.
- Story 22.7: it writes `serverconfig.json` while the game is stopped and keeps a state file; a wrong write-back could put back a value the admin changed later. ADR-15 decision 4 drops an edit whenever the same key is changed again, and each path has a test.

## 4. Detailed Change Proposals

### 4.1 PRD (`prd.md`)

**Frontmatter:** update entry "Added FR287-FR305 for Epic 22 (Server Operations and Metrics), with the maintainer's answers of the same day".

**New section after FR286:** "Epic 22: Server Operations and Metrics", FR287 to FR305, in five groups: Players Online (FR287-FR288), Prometheus Metrics (FR289-FR291), Scheduled Restarts (FR292-FR296), Disk Cleanup and Logs (FR297-FR299), API Settings Tab (FR300-FR305). The text is in `prd.md`.

### 4.2 Epics Structure (`epics.md`)

**Frontmatter:** update entry "Added Epic 22 (6 stories) for Server Operations and Metrics; FR287-FR305, with the maintainer's eleven answers of the same day (VSS-zws pulled in)".

**FR Coverage Map:** rows FR287 to FR305 appended after FR286, each mapped to Epic 22.

**Story Summary:** `| Epic 22: Server Operations and Metrics | 22.1, 22.2, 22.3, 22.4, 22.5, 22.6 | 6 |`, and the total from 128 to 134.

### 4.3 Epic 22 Stories (appended to `epics.md`)

The epic's goal, order, dependencies, beads, product changes, current and target state, and Stories 22.1 to 22.6 with their acceptance criteria and tasks, are in `epics.md` under "Epic 22: Server Operations and Metrics".

### 4.4 Architecture (`architecture/epic-22-server-operations-and-metrics.md`, new)

Facts checked at `e16a7932`, and:

- ADR-1 Players are counted from the game's join and leave lines
- ADR-2 The JSON metrics carry `playersOnline`, and the dashboard shows a Players card
- ADR-3 `/metrics` is a Prometheus endpoint at the root, open like `/healthz`, read live
- ADR-4 Metric names and labels
- ADR-5 A restart schedule is a list of daily times in the container's time zone
- ADR-6 One cron job per restart time warns at 15, 5 and 1 minutes, then restarts through the Restart button's path
- ADR-7 A settings change applies its jobs through one function
- ADR-8 The stop timeout is measured, not changed, and `VSS-zws` is checked in the same run
- ADR-9 Disk cleanup deletes old log archives, and backups only when asked
- ADR-10 Log rotation is the game's; the manager only deletes old archives
- ADR-11 Each interval field has an On switch, and Metrics Collection gets a field
- ADR-12 A Monitor key does not see the API Settings tab
- ADR-13 Restart times and cleanup limits are edited in the API Settings tab
- ADR-14 Restarts, cleanup and players are tested with stubs and throwaway containers, never on the dev stack's game server

`architecture/index.md` gains the entry.

### 4.5 Other Artifacts

- `sprint-status.yaml` (through `just sprint`): `epic-22` and its retrospective entry, and the six story keys, all `backlog`; `22-7-restart-required-settings-survive-a-live-change` added with answer 12 (`just sprint add-story 22 ...`).
- Beads: the epic bead with `VSS-bhw`, `VSS-29p`, `VSS-9jv` and `VSS-zws` as children, each with a comment naming its story; `VSS-zws` has a second comment moving it to Story 22.7 with 22.3's evidence.

## 5. Implementation Handoff

**Scope:** Minor. A new epic in the backlog; no replanning of existing work.

| Role | Responsibility |
|---|---|
| Scrum Master (`create-story`) | Create story files 22.1 to 22.7 from `epics.md` and the Epic 22 ADRs |
| Developer (`dev-story`) | Implement each story, one task per commit; each change with a release note is its own commit with the subject written for admins; throwaway containers for anything that restarts a game (ADR-14) |
| Reviewer (`code-review`) | Delegated, read-only review per story, given the commits and this contract |
| Maintainer (Matt) | Provides one anonymised join line and one leave line (22.1); decides the stop timeout if 22.3's measurement asks; confirms the manual checks; reviews the planner decisions below |

**Questions for the maintainer, answered one at a time on 2026-11-18.** Each answer is recorded in the ADR status lines.

1. **What `/metrics` delivers (ADR-2, ADR-3).** Default: a Prometheus text endpoint at `/metrics` with `prometheus-client`, and the player count also in the JSON snapshot and on the dashboard. Alternatives: Prometheus only; JSON only. *Confirmed (Matt, 2026-11-18): Prometheus and JSON.*
2. **Who may read `/metrics` (ADR-3 decision 6).** Default: open, like `/healthz`. Alternatives: a Monitor or Admin key; open behind an opt-in setting. *Confirmed (Matt, 2026-11-18): open, at the root.*
3. **The metric set (ADR-4).** Default: the bead's four plus info (version), up, state, max players, pending restart and the manager's own process metrics. Alternatives: the bead's four only; a wide set with mod counts, disk and job times. *Confirmed (Matt, 2026-11-18): the bead's set and the few extras.*
4. **How players are counted (ADR-1).** Default: parse the join and leave lines; the count resets when the game starts or stops. Alternatives: poll `/list clients`; parse and reconcile with `/list clients`. *Confirmed (Matt, 2026-11-18): parse the lines.* The line format needs one anonymised sample from a real server (Story 22.1 manual check).
5. **The restart schedule (ADR-5).** Default: a list of daily `HH:MM` times, empty by default, in the container's time zone. Alternatives: a cron expression; every N hours. *Confirmed (Matt, 2026-11-18): daily times.*
6. **Warnings before a restart (ADR-6).** Default: `/announce` at 15, 5 and 1 minutes with fixed text, only while the game runs. Alternatives: configurable minutes; configurable minutes and text; no warnings. *Confirmed (Matt, 2026-11-18): 15, 5 and 1 minutes, fixed text.*
7. **When a restart happens (ADR-6).** Default: whenever the game is running, players or not; a restart already in progress makes it skip. Alternatives: only with no player online; only when a restart is pending; a setting to choose. *Confirmed (Matt, 2026-11-18): always, if running.*
8. **What cleanup deletes (ADR-9).** Default: log archives older than 14 days with the newest 5 kept; backups kept to the newest N with N = 0 (keep all) by default; `BackupSaves` and the world never. Alternatives: log archives only; archives and backups (newest 10) by default. *Confirmed (Matt, 2026-11-18): log archives, backups opt-in.*
9. **Who rotates logs (ADR-10).** Default: the game; the manager only prunes archives and documents Docker's log options. Alternatives: the manager also rotates the live game logs; an optional rotating file log for the manager. *Confirmed (Matt, 2026-11-18): the game's; the manager prunes.*
10. **Turning an interval off in the UI (ADR-11).** Default: an On switch per interval; refresh fields 60 s to 365 days; Metrics Collection 1 s to 1 h, default 10 s. Alternatives: typing 0 or "off"; a preset dropdown. *Confirmed (Matt, 2026-11-18): an On switch per interval.* The question also said the bounds and fallbacks would be fixed in the same story.
11. **Pull-ins (table below).** Default: `VSS-zws`. *Answered (Matt, 2026-11-18): `VSS-zws` only.* The question also said the planner would hide the API Settings tab for a Monitor key in the UI story; the maintainer did not object (ADR-12).
12. **How to handle `VSS-zws` once confirmed (ADR-8 decision 3, ADR-15).** Asked after Story 22.3's Task 1 showed that a live `/serverconfig` command makes the game rewrite `serverconfig.json` and lose a pending `Port` edit, with "Restart required" then cleared by the next start. Options: fix inside Story 22.3; a new story; accept and document. *Answered (Matt, 2026-11-18): "New Story 22.7 fix: a small API story after 22.4: keep the restart-required edits made while the game runs and write them to serverconfig.json again after the process exits, before any start (manual, scheduled, auto). Keeps 22.3 at six tasks; handled inside the epic; closes VSS-zws."*

**Planner decisions not reviewed yet:** the job layout (one cron job per time at T-15, ADR-6 decisions 1 and 7); the 16-minute minimum gap between restart times (ADR-6 decision 6); `apply_setting` (ADR-7); the stop-time measurement and the rule that a slow stop is the maintainer's decision (ADR-8); the 03:00 cleanup time and the safety rules (ADR-9 decisions 3 to 6); the hidden tab (ADR-12); the UI of ADR-13, including leaving the next restart time out of the API Settings tab; ADR-15 decisions 1 to 8 (edits recorded only while a game process lives; kept on disk in `vsmanager/state/pending-config-edits.json`; written back after exit, before every spawn and at API start; dropped after a successful start or when the same key is changed again; a failed write-back does not block a start and re-flags the restart; the write-back never reads `VS_CFG_*`).

**Other open beads that share files with this epic** (answered by Matt, 2026-11-18: `VSS-zws` pulled in, the rest not):

| Bead | Shares | Recommendation |
|---|---|---|
| `VSS-zws` (API-073) Check whether VintageStory overwrites `serverconfig.json` edits made while it runs | The stop and restart path of `services/server.py` that scheduled restarts use, and the throwaway container of Story 22.3 | Pulled into Story 22.3 (Matt, 2026-11-18): verified in the same run as the stop-time measurement (ADR-8 decision 3). Confirmed there; fixed and closed by Story 22.7 (answer 12, ADR-15) |
| `VSS-hv60` (UI-103) Leftover `.tmp` and `.bak` files in the mods directory, with a cleanup | The idea of disk cleanup, not its code: the mods directory, the mod service and its own UI decisions (size-m) | Not pulled in. It belongs with the mod files epic it was grouped into |
| `VSS-3tb1` (API-095) Mod file follow-ups from Epic 19 | Only item 3 (cache eviction counts `*.zip` and `*.cs`) is near disk cleanup, and the chosen cleanup does not touch `cache_eviction.py` | Not pulled in |
| `VSS-7z3` (UI-084) Monitor key sees editable game setting fields | The same kind of fault as the hidden API Settings tab, but in `GameConfigPanel.tsx` and `SettingField.tsx`, which this epic does not edit | Not pulled in; it belongs with the game settings epic |

Seen and not proposed, because they share no file with a story: `VSS-2n2` (whitelist), `VSS-7ap` (serverconfig parsing), `VSS-jna` (connection loss), `VSS-glz` and `VSS-o8s` (file browser), `VSS-2bp` (favicon), `VSS-2kdt` (login), `VSS-egi` (EntitySpawning), `VSS-v3be` (hand-added mods), `VSS-koo1` (CSP).

**Found during planning and handled inside the epic (no bead filed):**

1. `/metrics` in the bead was ambiguous: the JSON metrics already hold game CPU and memory, and the PRD's Prometheus endpoint was never built. Answer 1 settles it; Story 22.2 updates the PRD's post-MVP line.
2. The UI's refresh interval maxima (1 day, 7 days) are below the API's 365 days; Story 22.5 aligns them.
3. Two fallbacks in `ApiSettingsPanel.tsx` differ from the API defaults (`serverVersionsRefreshInterval` 3600 for 86400, `enforceEnvOnRestart` true for false); Story 22.5 takes both from one constant.
4. A Monitor key sees the Admin-only API Settings tab and gets "Failed to load settings"; Story 22.5 hides it (ADR-12).
5. With metrics collection off the dashboard charts stop, but `/metrics` must not: ADR-3 decision 4 reads it live, and Story 22.5's help text says so.
6. The stop's 10-second kill was never measured against a world save; Story 22.3 measures it before scheduled restarts ship (ADR-8).
7. Whether the game prunes its own log archives is not observed; Story 22.4 checks it (ADR-9 decision 7).
8. The scheduler callback handles only interval settings; Story 22.3 generalises it with its error path (ADR-7).
9. A restart time saved less than 15 minutes ahead cannot warn on time; ADR-6 decision 6 documents that it first runs the next day.
10. Two `PendingRestartState` singletons: a game setting that needs a restart (`Port`, `Ip`) flags `routers/config.py`'s own, which nothing reads or clears, so `/healthz`, the web's Restart required banner and the new `vintagestory_server_pending_restart` never show it and a restart never clears it. Pulled in by the controller during Story 22.2's validation (backlog drawdown): Story 22.2 makes them one state (its Task 2, a `fix` commit, FR306).
11. `VSS-zws` confirmed by Story 22.3's Task 1: a live `/serverconfig` command makes the game write its in-memory config to `serverconfig.json`, which reverts a pending `Port` edit; the next start uses the old port and clears "Restart required". Answer 12: Story 22.7 fixes it (FR307, ADR-15).

**Seen and left alone, with the reason (no bead filed):**

1. `services/scheduler.py` carries fourteen `# type: ignore` comments for APScheduler, and `models/jobs.py` more. They predate the suppression rule; removing them needs typed wrappers or stubs for APScheduler, which is not this epic's work. New code adds none.
2. The 10-second stop timeout is not changed unless Story 22.3's measurement and the maintainer's decision call for it.
3. No crash auto-restart is added; the bead asks for scheduled restarts only.
4. The mod download cache is already size-limited; the cleanup does not touch it.
5. uvicorn's own access lines are not part of the cleanup or of `/metrics`.
6. The next restart time is not shown in the API Settings tab (ADR-13 decision 3); the Scheduled Jobs tab lists the jobs.

**Planned net bead change** (unchanged by Story 22.7, which closes `VSS-zws` in place of 22.3)**:** closed 4 (`VSS-bhw`, `VSS-29p`, `VSS-9jv`, `VSS-zws`). Opened 1 (the epic bead, which closes with the epic). Filed from planning: none. Net: 4 fewer open beads, from 17 open before the epic to 13 after it.

**Success criteria:**

- A join and a leave line change the count; the count is 0 when the game is stopped; no name is returned or logged above DEBUG; the dashboard shows the count
- `curl http://localhost:9080/metrics` answers without a key with the ADR-4 series; the game process series are absent with the game stopped; it works with metrics collection off
- A restart time saved through the API registers its job at once; the sequence sends three warnings and restarts a running game and never starts a stopped one (tests with a fake sleep)
- The stop time and `VSS-zws` are recorded from a throwaway container
- A `Port` change saved while the game runs survives a live setting change, a stop, a crash and an API restart, and the next start uses it (Story 22.7)
- The cleanup deletes only old named archives (and backups when asked), refuses links and every other directory, and logs what it deleted
- Each interval job can be turned off and on in the UI; Metrics Collection has a field; bounds and fallbacks match the API; a Monitor key does not see the tab
- Restart times and cleanup limits are edited in the UI
- Each of the four in-scope beads is closed with an AAR by its story after merge
- `just check` and CI pass throughout, with 0 Pyright warnings and 0 skipped web tests

## Checklist Record

| Section | Result |
|---|---|
| 1. Trigger and context | [x] 1.1 trigger: the maintainer named the epic and three beads after Epic 21's release. [x] 1.2 type: two new capabilities (metrics, operations) and one UI gap. [x] 1.3 evidence: section 1 and the ADR file |
| 2. Epic impact | [x] 2.1 no current epic is blocked. [x] 2.2 add one epic. [x] 2.3 no remaining epic changes. [x] 2.4 nothing made obsolete; the PRD's post-MVP Prometheus line is built. [x] 2.5 no resequencing; order inside Epic 22 is set |
| 3. Artifact conflicts | [x] 3.1 PRD: FR287-FR305 added, MVP unaffected. [x] 3.2 architecture: new Epic 22 ADRs. [x] 3.3 UX spec: no text change. [!] 3.4 one new runtime dependency, one new open route, and a default that deletes old log archives |
| 4. Path forward | [x] 4.1 Direct Adjustment: viable. [x] 4.2 Rollback: not viable. [x] 4.3 MVP Review: not needed. [x] 4.4 selected Option 1 |
| 5. Proposal components | [x] 5.1 to 5.5: sections 1 to 5 |
| 6. Review and handoff | [x] 6.1 scope named by the maintainer (2026-11-18). [x] 6.2, 6.3 the eleven questions were answered one at a time on 2026-11-18 and are written in, and a twelfth (Story 22.7) after Story 22.3's finding; the planner decisions listed in section 5 are not reviewed yet. [x] 6.4 handoff in section 5 |
