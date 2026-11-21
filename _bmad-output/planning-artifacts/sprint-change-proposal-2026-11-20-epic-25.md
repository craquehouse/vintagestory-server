# Sprint Change Proposal: Server Config Read Correctly (Epic 25)

**Date:** 2026-11-20
**Author:** BMAD planner (PM and Architect), for Matt
**Workflow:** correct-course (scope named by the maintainer; product decisions asked in one round)
**Scope classification:** Minor
**Status:** Scope named by Matt (2026-11-20): the two beads under the epic bead `VSS-m1qc`, `VSS-7ap` and `VSS-egi`. He answered four questions (section 5). Two beads, four stories. Matt approved this proposal the same day; `sprint-status.yaml` has `epic-25` and its four stories (backlog), and the epic bead `VSS-m1qc` has the two beads as children and the story map. Planner decisions not reviewed yet are listed in section 5.

## 1. Issue Summary

**Trigger:** Epic 24 is merged and released as v0.1.0 (`main` at `7224a181`). The maintainer grouped the five open beads into Epics 25 to 27 and started Epic 25. The backlog rule (2026-11-17) applies: the epic draws the backlog down, and what planning finds goes into a story. No other open bead shares the epic's files.

**Problem:** The manager treats `serverconfig.json` as a loose dictionary. Nothing checks that the paths the game depends on, `ModPaths` and `WorldConfig.SaveFileLocation`, point where they should. A wrong path is the known cause of "mods installed but not loaded" and of a world created in the wrong place (`agentdocs/vs-server-troubleshooting.md`, "Double-Path Bug"). Separately, Game Settings shows and edits Entity Spawning as a `serverconfig.json` setting, but game 1.22.7 keeps it in the world save. The value shown is never the game's, and a change made while the server is stopped has no effect.

**Evidence** (code at `7224a181`; API paths under `api/src/vintagestory_api/`; game files from the dev stack, game 1.22.7):

- **No typed read.** `GameConfigService._load_config` (`services/game_config.py:567`) returns `json.load` output. `get_settings`, `get_max_clients` and `_update_config_file` each pick keys from that dict. `config_parse.py` (Epic 23 ADR-1) already has the strict-JSON parser for `serverconfig.json`, with line and column on a parse error, but `GameConfigService` does not use it.
- **No path check.** No code in `api/src` reads `ModPaths` or `SaveFileLocation` (grep at `7224a181`). The template (`templates/serverconfig-template.json:153`) writes `["Mods", "/data/serverdata/Mods"]` and `SaveFileLocation: null`. The manager installs mods into `{serverdata_dir}/Mods` (`services/mods.py:106`). If that folder is not in `ModPaths`, every mod the manager installs is ignored by the game, and nothing tells the administrator.
- **Path rules.** `ModPaths` entries resolve relative to the server install directory (`/data/server`), not the working directory (`agentdocs/vs-server-troubleshooting.md:35`). The game runs with `cwd` set to the data dir (`services/server.py:1245`) and `--dataPath {serverdata_dir}` (`services/server.py:1211`). A null `SaveFileLocation` means `{dataPath}/Saves/default.vcdbs`. The dev stack has `Saves/default.vcdbs`. Story 25.1 confirms both rules on a throwaway container before it relies on them.
- **EntitySpawning is not a serverconfig.json key.** The game-written dev file (`ConfigVersion` 1.10) has every key in `ENV_VAR_MAP` except `EntitySpawning`; it is the only one missing (checked by script). `VintagestoryLib.dll` exposes it as `ISaveGame.EntitySpawning` (the world save). `LIVE_SETTINGS["EntitySpawning"]` (`services/game_config.py:165`) reads `config.get("EntitySpawning")`, which is always null, so Story 17.6 shows `default=True` as "Enabled (default)".
- **The game can be asked.** `VintagestoryLib.dll` 1.22.7 has the `/serverconfig` subcommand `entityspawning` ("Whether to spawn new creatures and monsters over time") and the strings `Current {0} is {1}` and `{0} set to {1}` next to the literal `EntitySpawning`. So `/serverconfig entityspawning` with no value answers `Current EntitySpawning is <value>`, and a set answers `EntitySpawning set to <value>`. How a bool is printed (`True`/`False`) and which tag the line carries on stdout still need a sample from a running server (Story 25.3, task 1).
- **Console plumbing.** `ServerService._read_stream` (`services/server.py:1510`) hands each stdout line to `PlayerTracker.observe` (Epic 22 ADR-1). `send_command` writes to stdin and returns only whether the write happened. No helper waits for a reply. The state goes to `RUNNING` when the process is spawned (`services/server.py:1253`), before the game is ready. The game logs `Dedicated Server now running on Port <n> and all ips!` when it is (`server-main.log` on the dev stack).
- **Env var.** `VS_CFG_ENTITY_SPAWNING` (`services/config_init.py:35`) writes `EntitySpawning` into `serverconfig.json` on first run, which the game ignores.
- **Web.** `GameConfigPanel.tsx:119` lists Entity Spawning with the other world toggles. `SettingField.tsx:165` renders a null bool with a known default as "Enabled (default)". The Story 17.6 review asked for "Not set" until the default is confirmed (comment on `VSS-egi`).

**Scope decisions (made by the maintainer, 2026-11-20):**

| Decision | Choice |
|---|---|
| Items in scope | `VSS-7ap`, `VSS-egi` |
| Backlog rule | The epic draws the backlog down; findings go into stories; the net bead change is reported |
| Where EntitySpawning comes from | Asked of the running game through the console; changed through the console; never written to `serverconfig.json` again (answer 1) |
| EntitySpawning while stopped | The last value seen, read-only, with a note; "Not known yet" before the first read (answer 2) |
| `VS_CFG_ENTITY_SPAWNING` | Applied through the console after each start; the setting shows as env-managed and locked (answer 3) |
| Path checks | A check endpoint and a warning in Game Settings; the typed model is internal, with no endpoint for the whole typed config (answer 4) |

**Grouping:**

| Story | Beads | Why this grouping |
|---|---|---|
| 25.1 serverconfig.json Is Read Through One Typed Model, and Its Paths Are Checked | `VSS-7ap` (API) | The typed read and the path check share the model and the path rules; one API pull request |
| 25.2 Game Settings Warns About a Wrong Path | `VSS-7ap` (closes) | The web half of 25.1 |
| 25.3 Entity Spawning Comes from the Running Game | `VSS-egi` (API) | The reply parser, the last-seen record, the set through the console and the env var all hang off the same "game is ready" hook |
| 25.4 Game Settings Shows Entity Spawning from the Game | `VSS-egi` (closes) | The web half of 25.3, including the Story 17.6 review note |

## 2. Impact Analysis

**Epic impact:** Epics 1 to 24 are done. None is invalidated. One new epic, Epic 25: Server Config Read Correctly, with 4 stories. Epics 26 and 27 (proposed, unplanned) follow. Epic 27's whitelist mode lives in `serverconfig.json` (`OnlyWhitelisted`, `WhitelistMode`), so it can use 25.1's model.

**Story impact:** No existing story changes. Story 25.3 replaces Story 17.6's `default=True` for EntitySpawning and Story 6.2's file update for it. Story 25.1 changes no API response; it changes how the file is read.

**Artifact conflicts:**

| Artifact | Change |
|---|---|
| PRD | FR344 to FR353 added; frontmatter |
| Epics | Epic 25; FR coverage rows; Story Summary row (155 stories); frontmatter |
| Architecture | New `architecture/epic-25-server-config-read-correctly.md` (facts, ADR-1 to ADR-6); index entry; a note on Story 17.6's defaults table that EntitySpawning no longer uses it |
| UX spec | No text change. The path warning follows the `ModUpdatesNotice` pattern. The Entity Spawning note follows the env-managed setting's helper text |
| CI | No new job. 25.1 and 25.3 add E2E checks to the CI set (throwaway container) |
| Project rules | None |
| Deployment and documentation | README: Game Settings (Entity Spawning comes from the running game; path warnings); `VS_CFG_ENTITY_SPAWNING` applied after each start. `agentdocs/vs-serverconfig-commands.md`: EntitySpawning lives in the world save |
| Beads | Epic bead `VSS-m1qc` exists with both beads as children; its description gets the story map |

**Technical impact:**

- No new dependency. The model uses Pydantic, already in use.
- The first code that waits for the game's reply to a console command. It is a line watcher with a timeout, fed by `_read_stream` next to the player tracker (ADR-4). A watcher fault never stops console capture (Epic 22 ADR-1 decision 1).
- One new state file, `state/entity_spawning.json` (the last value seen and when), written atomically like `pending_config_edits.json` (ADR-5).
- Writes to `serverconfig.json` stay on the parsed dict, so keys the model does not name are kept exactly (ADR-1).

**API contract and configuration changes (for the release notes):**

| Story | Where | Change | Kind |
|---|---|---|---|
| 25.1 | `GET /config/game/paths` | New, Admin and Monitor | New route |
| 25.1 | `GET /config/game` | A malformed `serverconfig.json` answers 422 `CONFIG_FILE_INVALID` with line and column (was 500) | Behaviour |
| 25.3 | `GET /config/game` | `EntitySpawning` gets `source` (`game`, `last_seen` or `unknown`) and `observed_at`; no `default` | New fields |
| 25.3 | `POST /config/game/settings/EntitySpawning` | Only while the game runs; 409 `SETTING_NEEDS_RUNNING_SERVER` while stopped (was a file write the game ignored) | Behaviour |
| 25.3 | `VS_CFG_ENTITY_SPAWNING` | Applied through the console after each start; no longer written to `serverconfig.json` | Configuration |

No route is removed. The `EntitySpawning` change is a fix, not a break: the old write never reached the game.

**Draft release-note text** (commit subjects; git-cliff removes the story scope):

- Features:
  - `feat(api): check that serverconfig.json's mod and save paths exist`
  - `feat(web): warn in Game Settings when a mod or save path in serverconfig.json is wrong`
- Fixes:
  - `fix(api): read and change Entity Spawning on the running game, where the world keeps it`
  - `fix(api): apply VS_CFG_ENTITY_SPAWNING after each start`
  - `fix(web): show Entity Spawning as the game reports it, and the last value seen while stopped`
  - `fix(api): answer a malformed serverconfig.json with the error's line and column`
- No note: the typed model itself (`refactor`), tests and documentation

## 3. Recommended Approach

**Selected:** Option 1, Direct Adjustment: add Epic 25 within the existing structure.

| Option | Assessment |
|---|---|
| 1. Direct Adjustment | Viable. Four stories, each tied to an in-scope bead. Effort medium, risk low to medium (25.3 waits on console replies) |
| 2. Rollback | Not viable. Nothing completed has to be undone |
| 3. MVP Review | Not needed |

**Effort:** Medium. `VSS-7ap` is P1 size-m with a detailed plan from 2026-01-19. `VSS-egi` is unsized (planned as size-m).

**Risks:**

- **Story 25.1: the model dropping keys.** A model that names some keys and rewrites the file would lose the rest, including keys a newer game adds. ADR-1 keeps the model read-only: it validates and types what the manager reads, `extra="allow"`, and every write still edits the parsed dict. A round-trip test writes the dev stack's 1.22.7 file through a setting change and compares every other key.
- **Story 25.1: the path rule being wrong.** If `ModPaths` resolves against something other than `/data/server`, the check would warn falsely. Task 1 confirms the rule on a throwaway container (a mod in a path given relative to `/data/server` loads) and records it in the ADR before the check is written.
- **Story 25.3: a reply that never comes.** The game may not answer while loading, or another command's output may interleave. ADR-4 sends the query only after `Dedicated Server now running`, matches only `Current EntitySpawning is …` or `EntitySpawning set to …`, waits at most 5 seconds, and on timeout keeps the last value seen and logs `entity_spawning_read_timeout`. Each case has a test with a fake stream.
- **Story 25.3: a value set in the console by hand.** An administrator typing `/serverconfig entityspawning false` in the console changes the world. The watcher sees the `set to` line from any source, so the last value seen follows it.
- **Story 25.3: the env var fighting the UI.** With `VS_CFG_ENTITY_SPAWNING` set, the setting is env-managed: the UI is locked and `POST` answers 400 `SETTING_ENV_MANAGED`, as for every other `VS_CFG_*` setting.

## 4. Detailed Change Proposals

### 4.1 PRD (`prd.md`)

**Frontmatter:** update entry "Added FR344-FR353 for Epic 25 (Server Config Read Correctly)".

**New section after FR343:** `### Server Config Read Correctly (Epic 25)`

- FR344: The API reads `serverconfig.json` through one typed model; keys the model does not name are kept when the manager writes the file
- FR345: A `serverconfig.json` that is not valid JSON is reported with the error's line and column, not as a server error
- FR346: The API reports, for each `ModPaths` entry and for the save file, the path as given, the path it resolves to, and whether it exists and is usable
- FR347: The API reports when the folder the manager installs mods into is not in `ModPaths`
- FR348: Game Settings shows a warning when a path is wrong or the manager's mods folder is missing from `ModPaths`, naming the path and how to fix it
- FR349: While the game runs, Entity Spawning shows the value the game reports, read after each start and after each change
- FR350: While the game is stopped, Entity Spawning shows the last value the game reported and when, read-only, with a note that it changes only while the server runs; before any report it shows "Not known yet"
- FR351: Entity Spawning is changed through the game's console and never written to `serverconfig.json`
- FR352: `VS_CFG_ENTITY_SPAWNING` is applied through the console after each start, and the setting shows as managed by it
- FR353: A value set in the console by hand is reflected in Entity Spawning

### 4.2 Epics (`epics.md`)

**Frontmatter:** update entry; Story Summary gains a row "Epic 25 | Server Config Read Correctly | 4" (155 stories). FR coverage rows FR344 to FR353 point to the stories below.

**New epic after Epic 24:**

> ## Epic 25: Server Config Read Correctly
>
> An administrator is told when a mod or save path in `serverconfig.json` is wrong, including when the manager's mods folder is not one the game loads, and sees Entity Spawning as the running game reports it, changed where the game keeps it.
>
> Beads: `VSS-7ap`, `VSS-egi` (epic bead `VSS-m1qc`). Decisions: `architecture/epic-25-server-config-read-correctly.md`. FR344-FR353. Order: 25.1 to 25.4, each branch from the previous story's branch, each PR to `main`.

#### Story 25.1: serverconfig.json Is Read Through One Typed Model, and Its Paths Are Checked

As an administrator, I want the manager to check the mod and save paths in `serverconfig.json`, so that I learn about a wrong path before I wonder why my mods do not load.

**Acceptance criteria:**

1. **Given** a `serverconfig.json` written by game 1.22.7, **when** the API reads it, **then** it is parsed with `config_parse`'s strict mode into a `ServerConfigFile` model that names the keys the manager uses (the `LIVE_SETTINGS` keys, `ModPaths`, `WorldConfig.SaveFileLocation`, `OnlyWhitelisted`, `WhitelistMode`) and allows every other key (FR344).
2. **Given** a setting change, **when** the file is written, **then** every key other than the changed one is unchanged, keys the model does not name included (a round-trip test on the 1.22.7 sample) (FR344).
3. **Given** a `serverconfig.json` that is not valid JSON, **when** `GET /config/game` runs, **then** it answers 422 `CONFIG_FILE_INVALID` with the line and column (FR345).
4. **Given** the file, **when** `GET /config/game/paths` runs (Admin or Monitor), **then** each `ModPaths` entry and the save file come back with `given`, `resolved`, and `status` (`ok`, `missing`, `not_a_directory`, `not_a_file`, `not_readable`, `not_writable`), the save file reporting its parent folder when the file does not exist yet (FR346).
5. **Given** `ModPaths` without the manager's mods folder (by resolved path), **when** the check runs, **then** the response has `manager_mods_folder_listed: false` (FR347).
6. **Given** a path with `..` that resolves outside `/data`, **when** the check runs, **then** it is reported with its resolved path and status, and nothing outside `/data` is listed or read beyond a `stat`.
7. **Given** task 1, **then** the resolution rule for relative `ModPaths` entries and for a null `SaveFileLocation` is confirmed on a throwaway container and recorded in ADR-2.

**Tasks:** (1) confirm the path rules on a throwaway container; (2) the model and the strict read in `GameConfigService`; (3) the round-trip test; (4) the path check and the route; (5) the 422 mapping; (6) README and `agentdocs/vs-server-troubleshooting.md`.

#### Story 25.2: Game Settings Warns About a Wrong Path

As an administrator, I want Game Settings to tell me when a mod or save path is wrong, so that I can fix it.

**Acceptance criteria:**

1. **Given** a path whose status is not `ok`, or `manager_mods_folder_listed: false`, **when** Game Settings opens, **then** a warning names each problem, the path as given and as resolved, and the fix (an absolute path such as `/data/serverdata/Mods`, or the file browser link to `serverconfig.json`) (FR348).
2. **Given** every path `ok`, **then** no warning shows.
3. **Given** the check fails or `serverconfig.json` is missing, **then** Game Settings shows as today, with no warning and no error from the check.
4. **Given** a Monitor key, **then** the warning shows without the edit link.
5. The warning is announced to screen readers once, and its targets are 44px on phones.

#### Story 25.3: Entity Spawning Comes from the Running Game

As an administrator, I want Entity Spawning to be the value the world uses, so that what I see and change is what the game does.

**Acceptance criteria:**

1. **Given** task 1, **then** a sample of the game's replies to `/serverconfig entityspawning` and `/serverconfig entityspawning false` on 1.22.7 is recorded in ADR-4 (tag, bool spelling), and the parser is written against it.
2. **Given** the game logs `Dedicated Server now running`, **when** no `VS_CFG_ENTITY_SPAWNING` is set, **then** the manager sends `/serverconfig entityspawning`, reads `Current EntitySpawning is <value>` within 5 seconds, and records the value and the time (FR349).
3. **Given** `VS_CFG_ENTITY_SPAWNING` is set, **when** the game is ready, **then** the manager sends `/serverconfig entityspawning <value>` and records the reply; the setting is `env_managed` (FR352).
4. **Given** the game runs, **when** `POST /config/game/settings/EntitySpawning` is called, **then** the command is sent, and the response and the record carry the value from `EntitySpawning set to <value>`; on no reply within 5 seconds, 502 `SETTING_UPDATE_FAILED` and the record is unchanged (FR351).
5. **Given** the game is stopped, **when** the same `POST` is called, **then** 409 `SETTING_NEEDS_RUNNING_SERVER`, and `serverconfig.json` is not touched (FR351).
6. **Given** any `EntitySpawning set to <value>` line on stdout, from the UI or typed in the console, **then** the record follows it (FR353).
7. **Given** `GET /config/game`, **then** EntitySpawning has `value` from the record, `source` (`game` while running and read since start, `last_seen` otherwise, `unknown` with `value: null` before any read), `observed_at`, and no `default` (FR349, FR350).
8. `VS_CFG_ENTITY_SPAWNING` is no longer written to `serverconfig.json` by config init. An existing `EntitySpawning` key in the file is left alone and never read.
9. A watcher fault or a timeout never stops console capture or the start; it is logged without the line's text.

**Tasks:** (1) the reply sample; (2) the reply watcher in `_read_stream`; (3) the record (`state/entity_spawning.json`); (4) the ready hook, the query and the env var; (5) the set through the console and the 409; (6) the `GET` fields; (7) config init; (8) README, `agentdocs/vs-serverconfig-commands.md`.

#### Story 25.4: Game Settings Shows Entity Spawning from the Game

As an administrator, I want to see where the Entity Spawning value comes from, so that I know whether I can change it now.

**Acceptance criteria:**

1. **Given** `source: game`, **then** the toggle shows the value and is enabled for Admin (FR349).
2. **Given** `source: last_seen`, **then** the toggle shows the value, is disabled, and the note says "Last reported by the game <relative time>. Changes only while the server runs." (FR350).
3. **Given** `source: unknown`, **then** the field shows "Not known yet" and is disabled while stopped; this replaces Story 17.6's "Enabled (default)" for this setting (the Story 17.6 review note) (FR350).
4. **Given** a change while running, **then** the field shows the value from the response; a 502 shows the error and keeps the previous value.
5. **Given** `env_managed`, **then** the field is locked with the env var's name, as other env-managed settings are (FR352).
6. **Given** the server starts or stops, **then** the field updates without a reload (the server status query invalidates the settings query).

### 4.3 Architecture (`architecture/epic-25-server-config-read-correctly.md`)

Facts checked at `7224a181` (section 1's evidence), then:

- **ADR-1: One typed model for reading, the parsed dict for writing.** `ServerConfigFile` (Pydantic, aliases for the game's PascalCase, `extra="allow"`) validates what the manager reads. Writes keep editing the dict from `config_parse`'s strict parse, so nothing the model does not name is lost. No endpoint returns the whole model.
- **ADR-2: Path rules.** Relative `ModPaths` entries resolve against `server_dir`; a null `SaveFileLocation` means `{serverdata_dir}/Saves/default.vcdbs`; a relative `SaveFileLocation` resolves against the same base as `ModPaths` (confirmed in 25.1 task 1, rule recorded here). Statuses and the `manager_mods_folder_listed` comparison by resolved path. Only `stat` and `os.access`; nothing is listed or read.
- **ADR-3: The path warning.** Its own query (`/config/game/paths`), separate from the settings query, so a failing check never breaks Game Settings.
- **ADR-4: Reading a reply from the console.** A `ConsoleReplyWatcher` fed by `_read_stream` next to the player tracker. `expect(pattern, timeout)` resolves on the first matching line after the command is sent. Only the two EntitySpawning patterns. Readiness is the `Dedicated Server now running` line, seen by the same watcher. Faults are logged without line text.
- **ADR-5: The last value seen.** `state/entity_spawning.json` (`value`, `observed_at`, `source` of the observation: `query`, `set`, `console`), written atomically. Kept across API restarts and game restarts; one world per data dir, so no world key.
- **ADR-6: EntitySpawning leaves `serverconfig.json`.** Removed from the file reads and writes; `LIVE_SETTINGS` gains a `location="game"` marker instead of `default`; env var applied by ADR-4's ready hook; config init skips it.

### 4.4 Beads

`VSS-m1qc` description gains the story map: `VSS-7ap` → 25.1 and 25.2 (closes in 25.2); `VSS-egi` → 25.3 and 25.4 (closes in 25.4). Close each with an AAR after its story merges.

## 5. Implementation Handoff

**Maintainer answers (Matt, 2026-11-20, four questions in one round):**

1. EntitySpawning: ask the running game; change through the console; stop writing it to the file.
2. While stopped: the last value seen, read-only, with a note; "Not known yet" before the first read.
3. `VS_CFG_ENTITY_SPAWNING`: applied after each start; shows as env-managed.
4. `VSS-7ap`: a check endpoint and a warning in Game Settings; no endpoint for the full typed config.

**Planner decisions not reviewed yet:**

- Four stories (API then web for each bead) rather than two or six.
- A 5-second reply timeout, and 502 `SETTING_UPDATE_FAILED` when a set gets no reply.
- A new error code `SETTING_NEEDS_RUNNING_SERVER` (409) rather than reusing `CONFIG_FILE_SERVER_RUNNING`'s opposite.
- The path check reports paths outside `/data` (by `stat` only) rather than refusing them.
- The model also names `OnlyWhitelisted` and `WhitelistMode`, for Epic 27.
- An existing `EntitySpawning` key in `serverconfig.json` is left in the file, not removed.

**Scope:** Minor. Direct implementation by the dev workflow (`create-story`, `dev-story`), one story at a time; code review delegated per the `code-review-delegation` memory.

**On approval:** add the FRs to `prd.md`, Epic 25 to `epics.md`, the architecture file and its index entry, the four stories to `sprint-status.yaml` (`just sprint add-story 25 …`), and the story map to `VSS-m1qc`; then create Story 25.1.

**Success criteria:** both beads closed with AARs; `just check` and the CI E2E set pass on each PR; on the dev stack, Game Settings shows Entity Spawning as the game reports it, and a deliberately wrong `ModPaths` entry in a throwaway container shows the warning.

**Backlog change (projected):** closes 2 (`VSS-7ap`, `VSS-egi`), plus the epic bead; opens 0 so far.
