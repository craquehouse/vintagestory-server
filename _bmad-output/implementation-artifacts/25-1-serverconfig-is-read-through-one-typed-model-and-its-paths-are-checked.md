# Story 25.1: serverconfig.json Is Read Through One Typed Model, and Its Paths Are Checked

Status: ready-for-dev

<!-- Implements FR344, FR345, FR346, FR347, Epic 25 ADR-1, ADR-2. Bead: VSS-7ap (API-012, API half; closes in 25.2). Branch story/25-1-serverconfig-is-read-through-one-typed-model-and-its-paths-are-checked from main at 7224a181, carrying the Epic 25 planning commit. API only: `git diff` of `web/` stays empty except the E2E spec. -->

## Story

As an **administrator**,
I want **the manager to check the mod and save paths in `serverconfig.json`**,
so that **I learn about a wrong path before I wonder why my mods do not load**.

## Acceptance Criteria

1. **Given** a `serverconfig.json` written by game 1.22.7
   **When** the API reads it (`GameConfigService.get_settings`, `get_max_clients`, a setting update)
   **Then** the text is parsed with `parse_config_text(text, strict=True)` and validated into `ServerConfigFile`, which names the `LIVE_SETTINGS` keys, `ModPaths`, `WorldConfig.SaveFileLocation`, `OnlyWhitelisted` and `WhitelistMode`, and allows every other key
   *(FR344; ADR-1 decision 1)*

2. **Given** a setting change written to the file
   **When** the file is compared with the sample it started from
   **Then** only the changed key differs, keys the model does not name (`Roles`, `LastLaunchMods`, `ServerIdentifier`, `WorldConfig.WorldConfiguration`, …) included, in the same order
   *(FR344; ADR-1 decision 2)*

3. **Given** a named key with a value of the wrong type (`MaxClients: "sixteen"`, `ModPaths: "Mods"`)
   **When** the file is read
   **Then** the read does not fail; the key is treated as missing for settings and logged once as `serverconfig_field_invalid` with the key only; `ModPaths` that is not a list of strings is one path entry with `status: invalid`
   *(FR344; ADR-1 decision 3, ADR-2 decision 5)*

4. **Given** a `serverconfig.json` that is not valid JSON (or not a JSON object)
   **When** `GET /config/game`, `GET /config/game/paths` or `POST /config/game/settings/{key}` runs
   **Then** it answers 422 `CONFIG_FILE_INVALID` with `parse_error` (`message`, `line`, `column`), `Cache-Control: no-store` on the GETs, and the file is untouched
   *(FR345; ADR-1 decision 4)*

5. **Given** the file
   **When** `GET /config/game/paths` runs with an Admin or a Monitor key
   **Then** it answers `{mod_paths: [...], save_file: {...}, manager_mods_folder_listed: bool}`; each entry has `given`, `resolved`, `status` and `problem`; a missing file answers 404 `CONFIG_NOT_FOUND`; no key answers 401
   *(FR346; ADR-2 decisions 2 and 5)*

6. **Given** mod path entries that are a readable directory, missing, a file, unreadable, under `server_dir` while the game is not installed, and the manager's own mods folder before it exists
   **When** the check runs
   **Then** their statuses are `ok`, `missing`, `not_a_directory`, `not_readable`, `not_installed`, `not_created_yet`; only the first four kinds after `ok` are `problem: true`
   *(FR346; ADR-2 decision 2)*

7. **Given** `SaveFileLocation` null, an existing file, a missing file in a writable folder, a missing folder, a directory, and a read-only file
   **When** the check runs
   **Then** `resolved` is `{serverdata_dir}/Saves/default.vcdbs` for null, and the statuses are `ok` (the default with no `Saves` folder yet is `not_created_yet`), `ok`, `ok`, `missing`, `not_a_file`, `not_writable`
   *(FR346; ADR-2 decisions 1 and 2)*

8. **Given** `ModPaths` with no entry that resolves to `{serverdata_dir}/Mods` (compared after `normpath`, both `"/data/serverdata/Mods"` and `"../serverdata/Mods"` counting)
   **When** the check runs
   **Then** `manager_mods_folder_listed` is false
   *(FR347; ADR-2 decision 3)*

9. **Given** an entry like `"../../etc"` or `"/proc"`
   **When** the check runs
   **Then** it is reported with its resolved path and status, using only `stat` and `os.access`; nothing is listed, opened or followed
   *(FR346; ADR-2 decision 4)*

10. **Given** the CI E2E container (fixture `serverconfig.json`, no game installed, never started)
    **When** the route is called
    **Then** no entry is a problem: `Mods` is `not_installed`, the manager's folder is listed, the save file is `not_created_yet`
    *(FR346, FR347; ADR-2 decision 2)*

11. **(Quality gates.)** `just check` green; no suppression added; existing config, pending-edit and metrics tests pass unchanged except where a test asserted the old 500.

## Tasks / Subtasks

- [x] Task 1: Confirm the relative `SaveFileLocation` rule (AC: 7)
  - [x] 1.1: On a throwaway container with a game installed (`vss-251-paths`, removed afterwards per the `docker-test-cleanup` memory), set `SaveFileLocation` to a relative path and read the "Savegame … loaded" line. Never on the dev stack
  - [x] 1.2: Record the rule in ADR-2 decision 1. If it cannot be run (no network for the game download), keep the `unverified` status for a relative save path and say so in the ADR and the Dev Agent Record
  - [x] 1.3: No commit on its own; goes with Task 3's ADR update

- [x] Task 2: The typed model and the strict read (AC: 1, 2, 3, 4)
  - [x] 2.1: `models/server_config.py`: `WorldConfigFile` and `ServerConfigFile`, fields optional, aliases in PascalCase, `extra="allow"`; a wrong-typed field becomes `None` (a `field_validator(mode="wrap")` or a per-field `TypeAdapter`, logging `serverconfig_field_invalid` with the key only)
  - [x] 2.2: `GameConfigService`: one `_read_config()` returning `(raw: dict, model: ServerConfigFile)` via `parse_config_text(strict=True)`; `get_settings`, `get_max_clients` and `_update_config_file` use it; writes keep editing `raw`
  - [x] 2.3: `ServerConfigInvalidError` (wrapping `ParseErrorInfo`; also for a top-level value that is not an object); routes map it to 422 `CONFIG_FILE_INVALID` with `parse_error`, like `_config_file_error` (`routers/config.py:747`)
  - [x] 2.4: `get_max_clients` keeps its contract: `None` when the file is missing or the value is not an int; it now also returns `None` (logged) for a malformed file instead of raising, so `/metrics` never fails on it (check `prometheus_metrics.py:115` and its tests)
  - [x] 2.5: Tests: `tests/fixtures/serverconfig-1.22.7.json` (the dev stack's file, `Password` and `StartupCommands` null, `ServerName` and `ServerIdentifier` replaced), round-trip on a setting update, wrong types, malformed text, a JSON array
  - [x] 2.6: Commit `fix(story-25.1/task-2): answer a malformed serverconfig.json with the error's line and column` (planned as `refactor`; the 422 is user-visible and in the epic's release notes as a fix)

- [ ] Task 3: The path check and its route (AC: 5, 6, 7, 8, 9, 10)
  - [ ] 3.1: `services/server_config_paths.py`: `check_paths(model, settings, game_installed) -> PathCheck`; resolution per ADR-2 decision 1; statuses and `problem` per decision 2; only `Path.stat`, `os.access`, `os.path.normpath`
  - [ ] 3.2: Models `PathEntry`, `PathCheck` (`models/server_config.py`); `GET /config/game/paths` in `routers/config.py`, `RequireAuth`, `NO_STORE`, 404 and 422 as `GET /config/game`; `game_installed` from `ServerService.is_installed()`
  - [ ] 3.3: Unit tests for every status, both relative and absolute forms of the manager's folder, a traversal path, `ModPaths` invalid; route tests for Admin, Monitor, no key, missing file, malformed file
  - [ ] 3.4: `web/e2e/server-config-paths.spec.ts` (untagged, CI set): the AC 10 response. Run `just test-e2e-ci e2e/server-config-paths.spec.ts`
  - [ ] 3.5: ADR-2 decision 1 (Task 1's result) and any decision changed in implementation
  - [ ] 3.6: Commit `feat(story-25.1/task-3): check that serverconfig.json's mod and save paths exist`

- [ ] Task 4: Documentation (AC: all)
  - [ ] 4.1: README, Game Settings section: the path check and what each status means; `agentdocs/vs-server-troubleshooting.md`: the confirmed rules with the log lines that prove them
  - [ ] 4.2: Commit `docs(story-25.1/task-4): explain the serverconfig.json path check`

- [ ] Task 5: Validate and move the story to review (AC: 11)
  - [ ] 5.1: `just check` green; `just changelog` lists Task 3's `feat` only
  - [ ] 5.2: Status `review`; `just sprint set 25-1-serverconfig-is-read-through-one-typed-model-and-its-paths-are-checked review`; Dev Agent Record and File List
  - [ ] 5.3: Commit `chore(story-25.1/task-5): validate and move story 25.1 to review`

## Dev Notes

### The code today (verified at 7224a181)

- `GameConfigService._load_config` (`services/game_config.py:567`) is `json.load` on `serverdata_dir / "serverconfig.json"`. Three readers: `get_settings` (`:604`), `get_max_clients` (`:664`, also called by `prometheus_metrics.py:115` with a bare `GameConfigService(settings=...)`), `_update_config_file` (`:930`, sets one key on the loaded dict, writes `json.dumps(config, indent=2)` to a `.tmp` and renames). A `JSONDecodeError` from `get_settings` is unmapped (500); in `_update_config_file` it becomes `SettingUpdateFailedError` (500 `SETTING_UPDATE_FAILED`, `routers/config.py:266`).
- `config_parse.parse_config_text(text, strict=True)` (`services/config_parse.py:153`) raises `ConfigParseError(info: ParseErrorInfo)`; `info.to_dict()` is the `parse_error` object. It also refuses Infinity/NaN and depth over the limit.
- `ConfigFileInvalidError` → 422 with `parse_error` is the existing pattern (`routers/config.py:747`).
- Other `serverconfig.json` readers that stay as they are: `pending_config_edits.reapply_edits` (`:146`, its own `json.loads` and write), `ConfigInitService` (writes the file from the template), `ConfigFilesService` (the file browser, raw text). Do not route them through the model in this story.
- `SETTING_ENV_MANAGED` is 400 (`routers/config.py:249`).
- Paths: the manager starts the game with `cwd=data_dir` and `--dataPath serverdata` (relative, `services/server.py:1207`); the game logged `/data/server/Mods` for `"Mods"` and `Savegame serverdata/Saves/default.vcdbs loaded` (dev stack, 2026-11-19). The manager's mods folder is `serverdata_dir / "Mods"` (`services/mods.py:106`), created on first install (`services/mods.py:1319`). `ServerService.is_installed()` (`services/server.py:707`) reads `vsmanager/current_version`.
- CI E2E containers (`scripts/e2e-ci.sh`) are seeded with `web/e2e/fixtures/serverconfig.json` (`ModPaths: ["Mods", "/data/serverdata/Mods"]`, `SaveFileLocation: null`, ConfigVersion 1.9) and have no game installed. `web/e2e/README.md` describes the two passes; an untagged spec runs in the first.

### Guardrails

- **Never dump the model to the file** (ADR-1 decision 2). A test fails if a key the model does not name changes or moves.
- **Pydantic 2.14.3** (`api/uv.lock`). Validate by alias only; do not set `populate_by_name` (pending deprecation since 2.11) or `validate_by_name`. `extra="allow"` keeps unknown keys in `__pydantic_extra__`; `WorldConfig` is its own model with `extra="allow"`.
- **No file reads in the check** beyond `stat`/`os.access`; no `iterdir`, no `resolve()` that follows symlinks for the comparison (use `os.path.normpath` on the joined path).
- **Logs never carry paths' contents or secrets.** `serverconfig_field_invalid` logs the key; the path check logs nothing per path at info level.
- **Tests never touch the dev stack** (`dev/`, `./data`, `vintagestory-manager-dev`). Use `tmp_path` settings (`tests/test_game_config.py:48` `temp_settings`).
- **Commits** follow `type(story-25.1/task-N): ...` (`project-context.md`, "Commit Message Format"); only Task 3 is user-facing (`feat`).

### Previous story intelligence

- Epic 24's stories ran stacked, one branch per story, PR to `main`; code review delegated per the `code-review-delegation` memory, then the story set to done.
- Story 24.5 found a route test that read `app.routes` and could never fail; route-presence tests read the OpenAPI paths.
- Epic 23 ADR-9: tests never edit the dev stack's files; the fixture approach above follows it.

### References

- `epics.md` "Story 25.1"; `architecture/epic-25-server-config-read-correctly.md` ADR-1, ADR-2; `sprint-change-proposal-2026-11-20-epic-25.md`; `agentdocs/vs-server-troubleshooting.md`; Epic 23 ADR-1 (the parser); Story 22.7 (pending edits, untouched here)

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Implementation decisions

- **Task 1 result (ADR-2 decision 1).** On `vss-251-paths` (the image, the dev stack's 1.22.7 install copied in, the manager's start command `cd /data && dotnet server/VintagestoryServer.dll --dataPath serverdata`): a relative `SaveFileLocation` resolves against `/data`; a missing save folder is fatal ("Unable to open or create savegame"); the game creates `serverdata/Saves` and `serverdata/Mods` itself. So no `unverified` status is needed. The container and the copied files were removed.
- **2.4 changed: `get_max_clients` still raises for a malformed file**, now `ServerConfigInvalidError`, because the metrics collector already logs and skips a failing source (Epic 22 ADR-3 decision 5) and `test_one_failing_source_leaves_the_others` relies on it. Only the expected error type changed in that test.
- **The scrape reads without logging a wrong-typed key** (`read_config(log_invalid=False)`): `test_players_max_absent_when_not_a_whole_number` requires a scrape with a bad `MaxClients` to log no warning. Game Settings reads log it.
- **`from_raw` drops wrong-typed keys from a copy and validates again** (at most four passes), rather than a wildcard wrap validator: it reports the dotted key names for the log and never touches the parsed dict that is written back.
- **New route tests take the keys from the `admin_headers`/`monitor_headers` fixtures** instead of importing `conftest` with a type-ignore, so no suppression is added.

### Completion Notes List

- 2026-11-20 (create-story): created from Epic 25's Story 25.1, ADR-1 and ADR-2. Found in creation and folded in (no bead): the `not_installed` and `not_created_yet` statuses and `problem`, so a fresh install shows no warning (ADR-2 decision 2); the `ModPaths` and null-save rules confirmed from the dev stack's log (ADR-2 decision 1); Pydantic's `populate_by_name` dropped (ADR-1 decision 1); `SETTING_ENV_MANAGED` is 400, not 409 (ADR-6 decision 4, proposal).

### File List

- `api/src/vintagestory_api/models/server_config.py` (new)
- `api/src/vintagestory_api/services/game_config.py`, `api/src/vintagestory_api/routers/config.py` (modified)
- `api/tests/test_server_config_read.py`, `api/tests/fixtures/serverconfig-1.22.7.json` (new)
- `api/tests/test_game_config.py`, `api/tests/test_prometheus_metrics.py` (modified: the expected error type)

## Change Log

- 2026-11-20: Story 25.1 created (create-story); status ready-for-dev.
