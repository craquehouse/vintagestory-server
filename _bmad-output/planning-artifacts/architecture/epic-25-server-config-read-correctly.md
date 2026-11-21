# Epic 25: Server Config Read Correctly - Architecture Decisions

Decisions from the Epic 25 course correction (2026-11-20). Epic 25 has no preparation story. Each fact below was checked by reading the code at commit `7224a181` (`main` after the v0.1.0 release), and the game facts by reading the dev stack's game 1.22.7 files (`serverconfig.json`, `server-main.log`, `VintagestoryLib.dll` strings). Nothing was sent to the dev stack's game. API paths are under `api/src/vintagestory_api/`.

The maintainer named the scope: `VSS-7ap` (parse `serverconfig.json` into a typed model and check its paths) and `VSS-egi` (EntitySpawning lives in the world save), under the epic bead `VSS-m1qc`. On 2026-11-20 he answered four questions in one round; each ADR's status line says which answer it carries.

| Story | ADRs |
|---|---|
| 25.1 serverconfig.json Is Read Through One Typed Model, and Its Paths Are Checked | ADR-1, ADR-2 |
| 25.2 Game Settings Warns About a Wrong Path | ADR-3 |
| 25.3 Entity Spawning Comes from the Running Game | ADR-4, ADR-5, ADR-6 |
| 25.4 Game Settings Shows Entity Spawning from the Game | ADR-5, ADR-6 |

## Facts Checked in the Code

**Reading serverconfig.json.**

- `GameConfigService._load_config` (`services/game_config.py:567`) returns `json.load` output. `get_settings`, `get_max_clients` and `_update_config_file` pick keys from that dict. `_update_config_file` sets one key on the loaded dict and writes the whole dict back (temp file and rename), so every other key survives.
- `config_parse.py` (Epic 23 ADR-1) has a strict mode for `serverconfig.json` (`json.loads`) that raises `ConfigParseError` with a line and column. `GameConfigService` does not use it; a malformed file raises `json.JSONDecodeError`, which `GET /config/game` does not map (500).
- `ErrorCode.CONFIG_FILE_INVALID` exists (`models/errors.py:43`), used by the config file routes.
- `GET /config/game` (`routers/config.py:150`) is Admin and Monitor, `Cache-Control: no-store`, 404 `CONFIG_NOT_FOUND` when the file is missing.

**Paths.**

- No code in `api/src` reads `ModPaths` or `SaveFileLocation`.
- The template (`templates/serverconfig-template.json:153`) writes `"ModPaths": ["Mods", "/data/serverdata/Mods"]` and `WorldConfig.SaveFileLocation: null`. The dev stack's game-written file has the same values.
- The manager installs mods into `{serverdata_dir}/Mods` (`services/mods.py:106`).
- The game runs with `cwd` set to `data_dir` (`services/server.py:1245`) and `--dataPath {serverdata_dir}` (`services/server.py:1211`).
- `agentdocs/vs-server-troubleshooting.md:35` says relative `ModPaths` entries resolve against the server install directory (`/data/server`), not the working directory. The dev stack has `/data/server/Mods` (the game's own mods) and `/data/serverdata/Saves/default.vcdbs` (the default save for a null `SaveFileLocation`). Neither rule was tested by the manager's code before.

**EntitySpawning.**

- The dev stack's game-written `serverconfig.json` (`ConfigVersion` 1.10) has every key in `ENV_VAR_MAP` (`services/config_init.py:13`) except `EntitySpawning`; it is the only one missing.
- `VintagestoryLib.dll` 1.22.7 has `Vintagestory.API.Server.ISaveGame.EntitySpawning` (get and set): the value is in the world save.
- The `/serverconfig` command has the subcommand `entityspawning` ("Whether to spawn new creatures and monsters over time", argument "Entity spawning mode"). Next to the literal `EntitySpawning` the library has `Current {0} is {1}`, `{0} changes server config {1} to {2}.` and `{0} set to {1}`. The bool's spelling and the stdout tag of the reply are not known yet.
- `LIVE_SETTINGS["EntitySpawning"]` (`services/game_config.py:165`) has `console_command="/serverconfig entityspawning {value}"` and Story 17.6's `default=True`. `get_settings` reads `config.get("EntitySpawning")`, which is null, so the web shows "Enabled (default)" (`web/src/components/SettingField.tsx:165`).
- `VS_CFG_ENTITY_SPAWNING` maps to `("EntitySpawning", "bool")` (`services/config_init.py:35`) and is written into the file at first run.

**The console.**

- `ServerService._read_stream` (`services/server.py:1510`) appends each stdout and stderr line to the console buffer, then calls `PlayerTracker.observe(text)` inside a `try` that logs `player_tracker_error` without the text (Epic 22 ADR-1 decision 1).
- `send_command` (`services/server.py:1550`) echoes the command to the buffer with `[CMD]`, writes it to stdin, and returns whether it was written. Nothing waits for a reply.
- The state becomes `RUNNING` right after the process is spawned (`services/server.py:1253`), before the game has loaded. The game logs `Dedicated Server now running on Port <port> and all ips!` when it has (`server-main.log`, tagged `[Event]` there).
- `PendingConfigEdits` (`services/pending_config_edits.py`) is the pattern for a small state file under `state_dir`: a Pydantic file model, atomic save, tolerant load.

## ADR-1: One Typed Model for Reading, the Parsed Dict for Writing

**Status:** Accepted (Matt, 2026-11-20, answer 4: the model is internal)

**Decision:**

1. **The model.** `ServerConfigFile` (in `models/server_config.py`) is a Pydantic model with the game's PascalCase names as aliases and `extra="allow"`. It validates by alias only (Pydantic's default; the file never uses the Python names), so neither `validate_by_name` nor the older `populate_by_name` is set. It names the `LIVE_SETTINGS` keys except EntitySpawning (ADR-6), `ModPaths`, `WorldConfig` (with `SaveFileLocation`, and `extra="allow"`), `OnlyWhitelisted` and `WhitelistMode` (for Epic 27). Every named field is optional, because the game's own file may lack any of them on an older version.
2. **Writes keep the dict.** `GameConfigService` reads with `config_parse`'s strict mode, validates the result with `ServerConfigFile.model_validate`, and keeps the parsed dict. `_update_config_file` still sets one key on that dict and writes it back. The model is never dumped to the file.
3. **A wrong type is not a failure.** A named field with a value of the wrong type is read as missing and logged once per read (`serverconfig_field_invalid`, key only). Game Settings shows it as having no value, as today.
4. **Malformed JSON.** `ConfigParseError` maps to 422 `CONFIG_FILE_INVALID` with `line` and `column` on `GET /config/game` and on a setting update.
5. **No full-config endpoint.** Nothing returns the model as a whole. The raw file stays readable through the file browser (Epic 23), with secrets redacted for Monitor.

## ADR-2: Path Rules and the Check

**Status:** Accepted (Matt, 2026-11-20, answer 4). Decision 1 checked while creating Story 25.1 from the dev stack's `server-main.log` (game 1.22.7, 2026-11-19 start): "Will search the following paths for mods:" lists `/data/server/Mods` for the relative `"Mods"`, and "Savegame serverdata/Saves/default.vcdbs loaded" for a null `SaveFileLocation` (the manager passes `--dataPath serverdata` with `cwd` `/data`, `services/server.py:1207`). Story 25.1 Task 1 (2026-11-21, throwaway container `vss-251-paths` with the dev stack's 1.22.7 install, the manager's start command): `SaveFileLocation: "relsaves/rel.vcdbs"` loaded `/data/relsaves/rel.vcdbs` ("Savegame relsaves/rel.vcdbs loaded"); with `/data/relsaves` absent the game stopped with "[Fatal] Unable to open or create savegame" (`SQLiteDBConnection.HaveWriteAccessFolder`); with `SaveFileLocation: null` and no `serverdata/Saves` the game created the folder and loaded `serverdata/Saves/default.vcdbs`. The game also creates `serverdata/Mods` at start.

**Decision:**

1. **Resolution.** A relative `ModPaths` entry resolves against `server_dir` (confirmed). A null or empty `SaveFileLocation` means `{serverdata_dir}/Saves/default.vcdbs` (confirmed). A relative `SaveFileLocation` resolves against the game's working directory, `data_dir` (confirmed). A save file whose folder is missing is fatal to the game, so `missing` is a problem, except for the default `Saves` folder, which the game creates (`not_created_yet`). Paths are normalised with `os.path.normpath`, without following symlinks for the comparison in decision 3.
2. **Statuses.** For a mod path: `ok` (a readable directory), `missing`, `not_a_directory`, `not_readable`. For the save file: `ok` (a readable, writable file, or a missing file whose parent folder is a writable directory), `missing` (the parent folder does not exist), `not_a_file`, `not_writable`. Each entry has `given`, `resolved` and `status`.
   Two statuses are not problems, so a fresh install shows no warning (found while creating Story 25.1: the CI E2E container has no game installed and has never started one): `not_installed`, for an entry that resolves under `server_dir` while the game is not installed (the relative `"Mods"`, the game's own mods); and `not_created_yet`, for the manager's mods folder before the first install and for the default save file whose `Saves` folder the game has not created yet. Each entry carries `problem: bool`; the warning (ADR-3) shows only problems.
3. **The manager's mods folder.** `manager_mods_folder_listed` is true when one `ModPaths` entry resolves to `{serverdata_dir}/Mods`.
4. **Paths outside `/data`.** Reported like any other, with `stat` and `os.access` only. Nothing is listed, opened or followed.
5. **Route.** `GET /config/game/paths`, Admin and Monitor, `Cache-Control: no-store`; 404 `CONFIG_NOT_FOUND` when the file is missing; 422 `CONFIG_FILE_INVALID` when it is malformed. `ModPaths` that is not a list of strings is reported as one entry with `status: invalid`. *(As implemented in Story 25.1: a `SaveFileLocation` (or `WorldConfig`) of the wrong type is `status: invalid` too; a file with no `ModPaths` key lists no entries and `manager_mods_folder_listed: false`. A parent folder that cannot be searched counts as `not_readable` for a mod path and `not_writable` for the save file.)*

## ADR-3: The Path Warning Has Its Own Query

**Status:** Accepted (Matt, 2026-11-20, answer 4: a warning in Game Settings)

**Decision:**

1. **Query.** `useServerConfigPaths` calls `GET /config/game/paths`, separate from the settings query, and refetches when the server status changes and when a config file is saved.
2. **Failure is silent.** An error from the check (including 404) shows no warning and no error; Game Settings is unchanged.
3. **Placement.** Above the settings groups in `GameConfigPanel`, following `ModUpdatesNotice` (an alert with a list). Each problem names the path as given and as resolved and suggests an absolute path. An Admin key gets a link to `serverconfig.json` in the file browser.

## ADR-4: Reading a Reply from the Console

**Status:** Accepted (Matt, 2026-11-20, answer 1: ask the running game). Decision 1 is confirmed by Story 25.3's first task.

**Decision:**

1. **Patterns.** Written against a recorded 1.22.7 sample, anchored at the end of the line, ignoring the timestamp and tag: `Current EntitySpawning is (?P<value>\S+)` and `EntitySpawning set to (?P<value>\S+)`. The value is parsed case-insensitively from `true`/`false`/`on`/`off`/`1`/`0`; anything else is not a match.
2. **Watcher.** `ConsoleReplyWatcher` is fed by `_read_stream` after the player tracker, inside its own `try`. It also sees `Dedicated Server now running`, which fires the ready hook (ADR-6 decision 3). It is reset when the process starts and stops.
3. **Every set line counts.** A `set to` line updates the record (ADR-5) whether the manager sent the command or an administrator typed it.
4. **Waiting.** `expect(pattern, timeout=5.0)` is registered before the command is sent and resolves on the first matching line after it. On timeout the caller gets `None`. A set that times out answers 502 `SETTING_UPDATE_FAILED`; a query that times out logs `entity_spawning_read_timeout` and keeps the record.
5. **Faults.** A watcher exception is logged (`console_reply_watcher_error`, type only) and never stops console capture or a start.

## ADR-5: The Last Value Seen

**Status:** Accepted (Matt, 2026-11-20, answer 2: the last value seen, read-only)

**Decision:**

1. **File.** `state/entity_spawning.json`: `value` (bool), `observed_at` (UTC), `via` (`query`, `set`, `console`). Saved atomically like `pending_config_edits.json`. A missing or unreadable file is no record. One world per data dir, so no world key.
2. **Source in the response.** `game` when the game runs and a value was observed since this start; `last_seen` when a record exists otherwise; `unknown` (with `value: null`) when there is no record. `observed_at` is included when a record exists.
3. **Web.** `game`: the toggle is enabled for Admin. `last_seen`: disabled, with "Last reported by the game <relative time>. Changes only while the server runs." `unknown`: "Not known yet", disabled while stopped. This replaces Story 17.6's "Enabled (default)" for this setting only.

## ADR-6: EntitySpawning Leaves serverconfig.json

**Status:** Accepted (Matt, 2026-11-20, answers 1 and 3)

**Decision:**

1. **Marker.** `ServerSetting` gains `location: Literal["file", "game"] = "file"`. EntitySpawning is `location="game"` and loses `default`. `get_settings` takes a `game` setting's value from ADR-5's record, never from the file. An `EntitySpawning` key already in the file is left there and never read.
2. **Updates.** A `game` setting is set only through the console, and only while the game runs. While it is stopped the update answers 409 `SETTING_NEEDS_RUNNING_SERVER` (new) and the file is not touched. The response's `value` is the one the game reported.
3. **Ready hook.** On `Dedicated Server now running`, the manager sends `/serverconfig entityspawning <value>` when `VS_CFG_ENTITY_SPAWNING` is set, or `/serverconfig entityspawning` otherwise, and records the reply.
4. **Env var.** `VS_CFG_ENTITY_SPAWNING` keeps its name. `config_init` no longer writes it to the file. The setting is `env_managed` when it is set, and updates answer 400 `SETTING_ENV_MANAGED` as for other settings (`routers/config.py:249`).
5. **Epic 6.** The Epic 6 table row for EntitySpawning ("Immediate") still holds for the command; the value's home is the world save.
