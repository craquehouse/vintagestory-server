# Story 25.3: Entity Spawning Comes from the Running Game

Status: ready-for-dev

<!-- Implements FR349, FR350, FR351, FR352, FR353, Epic 25 ADR-4, ADR-5, ADR-6. Bead: VSS-egi (API-080, API half; closes in 25.4). Branch story/25-3-entity-spawning-comes-from-the-running-game, stacked on story/25-2-game-settings-warns-about-a-wrong-path (PR #224); the PR targets main and merges after 25.2's. API only. -->

## Story

As an **administrator**,
I want **Entity Spawning to be the value the world uses**,
so that **what I see and change is what the game does**.

## Acceptance Criteria

1. **Given** Task 1's sample (recorded in ADR-4 decision 1)
   **Then** the parser matches only a `[Server Notification]` line (nothing but a timestamp before the tag) ending in `Current Entity spawning mode is on|off` or `Entity spawning mode set to on|off`; a chat line or any other text never matches
   *(ADR-4 decision 1)*

2. **Given** the game logs `Dedicated Server now running` and `VS_CFG_ENTITY_SPAWNING` is not set
   **When** the manager sees the line
   **Then** it sends `/serverconfig entityspawning`, reads the reply within 5 seconds, and records the value, the time and `via: query` in `state/entity_spawning.json`
   *(FR349; ADR-4, ADR-5)*

3. **Given** `VS_CFG_ENTITY_SPAWNING` is set (`true`/`false`, as other `VS_CFG_*` bools)
   **When** the game is ready
   **Then** the manager sends `/serverconfig entityspawning true|false` and records the reply; the setting is `env_managed` and an update answers 400 `SETTING_ENV_MANAGED`
   *(FR352; ADR-6 decisions 3 and 4)*

4. **Given** the game is ready
   **When** `POST /config/game/settings/EntitySpawning` is called by an Admin key with a bool
   **Then** `/serverconfig entityspawning true|false` is sent, and the response (`method: console_command`) and the record carry the value from the reply; with no reply within 5 seconds the answer is 502 `SETTING_UPDATE_FAILED` and the record is unchanged
   *(FR351; ADR-4 decision 4)*

5. **Given** the game is stopped, or started but not yet ready
   **When** the same `POST` is called
   **Then** it answers 409 `SETTING_NEEDS_RUNNING_SERVER`, nothing is sent, and `serverconfig.json` is not touched
   *(FR351; ADR-6 decision 2)*

6. **Given** an `Entity spawning mode set to on|off` line from a command typed in the console
   **When** the watcher sees it
   **Then** the record follows it with `via: console`
   *(FR353; ADR-4 decision 3)*

7. **Given** `GET /config/game`
   **When** it answers
   **Then** EntitySpawning has `value` from the record, `source` (`game` while the game runs and a value was seen since this start, `last_seen` otherwise, `unknown` with `value: null` when there is no record), `observed_at` when there is a record, and no `default`; it is never read from `serverconfig.json`
   *(FR349, FR350; ADR-5 decision 2, ADR-6 decision 1)*

8. **Given** `VS_CFG_ENTITY_SPAWNING`
   **When** config init writes a new `serverconfig.json`
   **Then** it does not write `EntitySpawning`; an existing key in the file is left alone
   *(ADR-6 decision 4)*

9. **Given** a watcher fault, a corrupt `entity_spawning.json`, or a reply timeout
   **When** it happens
   **Then** console capture and the start go on; the record reads as missing; log lines carry no console text
   *(ADR-4 decision 5, ADR-5 decision 1)*

10. **Given** the built image with a game installed in a throwaway container (never the dev stack)
    **When** the game is started through the API
    **Then** `GET /config/game` shows EntitySpawning `source: game`, a change through the API is reported back, and after a stop it is `last_seen`
    *(FR349, FR350, FR351)*

11. **(Quality gates.)** `just check` green; no suppression added.

## Tasks / Subtasks

- [x] Task 1: Record the game's replies (AC: 1)
  - [x] 1.1: Throwaway container `vss-253-spawning` with the dev stack's 1.22.7 install; send the query, sets and `/stop`; record in ADR-4 decision 1
  - [x] 1.2: Goes with Task 2's commit

- [x] Task 2: The watcher and the record (AC: 1, 2, 3, 6, 9)
  - [x] 2.1: `services/entity_spawning.py`: the line patterns, `EntitySpawningRecord`, the atomic store, `EntitySpawningWatcher` (`observe`, `query`, `set`, `reset`, `is_ready`, `seen_since_start`, the ready hook with the env var)
  - [x] 2.2: `ServerService`: one watcher; `_read_stream` feeds it after the player tracker in its own `try` (`console_reply_watcher_error`, type only); reset where the player tracker is reset
  - [x] 2.3: Tests with a fake `send_command` and fed lines: matches, chat spoof, interleaved lines, timeout, fault, ready hook, env var, store load/save/corrupt
  - [x] 2.4: Commit `refactor(story-25.3/task-2): read Entity Spawning replies from the game's console`

- [x] Task 3: Game Settings reads and sets it on the game (AC: 3, 4, 5, 7, 8)
  - [x] 3.1: `ServerSetting.location`; EntitySpawning `location="game"`, no `default`; `SettingInfo` `source`/`observed_at`; `ServerConfigFile` drops `EntitySpawning`
  - [x] 3.2: `update_setting` for a game setting: env check, 409 `SETTING_NEEDS_RUNNING_SERVER` unless ready, the set, 502 on no reply; `ErrorCode.SETTING_NEEDS_RUNNING_SERVER`; router mappings
  - [x] 3.3: `config_init`: skip `EntitySpawning`
  - [x] 3.4: Tests: GET for each source, POST running/stopped/not ready/no reply/env-managed, config init, the file never touched
  - [x] 3.5: Commit `fix(story-25.3/task-3): read and change Entity Spawning on the running game, where the world keeps it`

- [ ] Task 4: End to end and documentation (AC: 10)
  - [ ] 4.1: The AC 10 run on the built image in a throwaway container; record the commands and output in the Debug Log
  - [ ] 4.2: `web/e2e/entity-spawning.spec.ts` tagged `@game-server` (local only)
  - [ ] 4.3: README (Game Settings, `VS_CFG_ENTITY_SPAWNING`), `agentdocs/vs-serverconfig-commands.md`
  - [ ] 4.4: Commit `docs(story-25.3/task-4): explain where Entity Spawning comes from`

- [ ] Task 5: Validate and move the story to review (AC: 11)
  - [ ] 5.1: `just check` green; `just changelog`
  - [ ] 5.2: Status `review`; sprint status; Dev Agent Record and File List
  - [ ] 5.3: Commit `chore(story-25.3/task-5): validate and move story 25.3 to review`

## Dev Notes

### The code today (verified at f6bff716, the tip of 25.2)

- `ServerService._read_stream` (`services/server.py:1510`) feeds `PlayerTracker.observe` in a `try` that logs `player_tracker_error` with the type only. The tracker is reset at `:1230` (start), `:1352`, `:1394`, `:1481` (stop and exit paths).
- `send_command` (`:1550`) writes to stdin and returns whether it could. The state is `RUNNING` from the spawn (`:1253`), before the game is ready; the game logs `[Server Event] Dedicated Server now running on Port <n> and all ips!` when it is.
- `LIVE_SETTINGS["EntitySpawning"]` (`services/game_config.py`) has `default=True` (Story 17.6); `SETTING_ENV_MANAGED` is 400; `SettingUpdateFailedError` is 500.
- `ENV_VAR_MAP` (`services/config_init.py:35`) maps `VS_CFG_ENTITY_SPAWNING`; `ConfigInitService` writes the overrides into the template at first run.
- `PendingConfigEdits` (`services/pending_config_edits.py`) is the state-file pattern (Pydantic file model, atomic write, tolerant load).

### Task 1 result (recorded in ADR-4 decision 1)

The game prints "Entity spawning mode" and `on`/`off` under `[Server Notification]`, answers a query with `Current Entity spawning mode is on`, a set with `Entity spawning mode set to off`, takes any value but true/on/1 as off, and keeps the value in the world across `/stop` (never in `serverconfig.json`).

### Guardrails

- Only `true`/`false` are ever sent. The watcher never stops console capture. No console text in logs.
- Tests never start a game or touch the dev stack; AC 10 runs in a throwaway container from the built image.

### References

- `epics.md` "Story 25.3"; `architecture/epic-25-server-config-read-correctly.md` ADR-4, ADR-5, ADR-6; Epic 22 ADR-1 (the player tracker); Story 22.7 (pending edits)

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5).

### Debug Log References

### Implementation decisions

- **A watcher for this setting, not a general `ConsoleReplyWatcher`** (ADR-4 decision 2 named one): only Entity Spawning needs a reply, so `EntitySpawningWatcher` owns its patterns, its waiters and its record. A second setting that needs replies would extract the waiter part.
- **A reply is attributed by its waiters**: a `current` reply while a query waits is `via: query`, a `set` reply while a set waits is `via: set`, any other reply was typed in the console (`via: console`). A set ignores an interleaved query reply.
- **`reset()` ends waits with a private exception**, not by cancelling the future, so a real cancellation of the caller is never swallowed.
- **`GAME_KEPT_KEYS` lives in `config_init`**, which both `game_config` and `config_init_service` import; a test asserts it equals the `location="game"` settings, so the two cannot drift.
- **`VS_CFG_ENTITY_SPAWNING` quotes are stripped** as config init strips them (a docker-compose habit).
- **Test doubles get `entity_spawning.record = None`**: the existing `MagicMock` server services in `test_game_config.py` and `test_routers_config.py` otherwise produce an unserialisable value. Story 17.6's default tests now assert no setting has a default and the file's `EntitySpawning` is never read.
- **The game takes any value but true/on/1 as off**, so only `true`/`false` is ever sent (`set_command`).

### Completion Notes List

- 2026-11-21 (create-story): created from Epic 25's Story 25.3 and ADR-4 to ADR-6. Found in creation (Task 1 run first): the reply names the label, not the key, so the planned patterns were wrong (ADR-4 decision 1 and `epics.md` corrected); a set while the game loads would not be answered, so a set is refused until the ready line (AC 5); the E2E check runs on the built image in a throwaway container instead of the dev stack.

### File List

- `api/src/vintagestory_api/services/entity_spawning.py`, `api/tests/test_entity_spawning.py` (new); `api/src/vintagestory_api/services/server.py`, `api/tests/server/test_internal_methods.py` (modified); ADR-4 decision 1 and `epics.md` Story 25.3 (the recorded replies) (Tasks 1 and 2)
- `api/src/vintagestory_api/services/game_config.py`, `services/config_init.py`, `services/config_init_service.py`, `models/server_config.py`, `models/errors.py`, `routers/config.py` (modified); `api/tests/test_entity_spawning_settings.py` (new); `api/tests/test_game_config.py`, `api/tests/test_routers_config.py` (modified: test doubles, Story 17.6 default tests) (Task 3)

## Change Log

- 2026-11-21: Story 25.3 created (create-story); status ready-for-dev.
