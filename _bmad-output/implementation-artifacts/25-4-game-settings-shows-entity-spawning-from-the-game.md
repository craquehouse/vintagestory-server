# Story 25.4: Game Settings Shows Entity Spawning from the Game

Status: review

<!-- Implements FR349, FR350, FR352, Epic 25 ADR-5 decision 3. Bead: VSS-egi (API-080, closes with this story after merge, with the Story 17.6 review note). Branch story/25-4-game-settings-shows-entity-spawning-from-the-game, stacked on story/25-3-entity-spawning-comes-from-the-running-game (PR #225); the PR targets main and merges after 25.3's. Web only. -->

## Story

As an **administrator**,
I want **to see where the Entity Spawning value comes from**,
so that **I know whether I can change it now**.

## Acceptance Criteria

1. **Given** `source: game`
   **When** Game Settings shows Entity Spawning
   **Then** the switch shows the value and is enabled for an Admin key (disabled for Monitor, as every field is)
   *(FR349)*

2. **Given** `source: last_seen`
   **Then** the switch shows the value, is disabled, and the description says "Last reported by the game <relative time>. Changes only while the server runs."
   *(FR350; ADR-5 decision 3)*

3. **Given** `source: unknown`
   **Then** the state reads "Not known yet" (not Story 17.6's "Enabled (default)" or "Not set"), the switch is disabled, and the description says "Not reported by the game yet. Changes only while the server runs." This settles the Story 17.6 review note on `VSS-egi`
   *(FR350)*

4. **Given** a change while the game runs
   **When** the API answers
   **Then** the field keeps the new value; a 409 or 502 shows the error toast and the switch goes back (Story 17.6's `revertOnError`)
   *(FR349)*

5. **Given** `env_managed`
   **Then** the field is locked and its badge names the variable from the API (`VS_CFG_ENTITY_SPAWNING`); every env-managed setting's badge now uses the API's `env_var`
   *(FR352)*

6. **Given** the server starts or stops
   **When** the status changes, and while the server runs until the game has reported the value
   **Then** the settings are fetched again, so the field changes without a reload
   *(FR349, FR350)*

7. **(Quality gates.)** `just check` green; no suppression added.

## Tasks / Subtasks

- [x] Task 1: The field (AC: 1-5)
  - [x] 1.1: `GameSetting.source`, `observedAt`, `envVar`; `SettingField.unsetLabel`
  - [x] 1.2: `GameConfigPanel`: a game-kept setting is disabled unless `source: game`, with the description per source and "Not known yet"; `envVar` passed to every field
  - [x] 1.3: The settings refetch on a server state change, and on each status poll while running and not yet `game`
  - [x] 1.4: Tests: each source, Monitor, the revert on a failed save, the env badge, the refetch
  - [x] 1.5: Commit `fix(story-25.4/task-1): show Entity Spawning as the game reports it, and the last value seen while stopped`

- [x] Task 2: Validate and move the story to review (AC: 7)
  - [x] 2.1: `just check` green; README sentence if needed
  - [x] 2.2: Status `review`; sprint status; Dev Agent Record and File List
  - [x] 2.3: Commit `chore(story-25.4/task-2): validate and move story 25.4 to review`

## Dev Notes

### The code today (verified at 23bcdf5a, the tip of 25.3)

- `GET /config/game` gives EntitySpawning `source` (`game`, `last_seen`, `unknown`), `observed_at` when there is a record, `env_var` when env-managed, and no `default` (Story 25.3).
- `SettingField` (`web/src/components/SettingField.tsx`) labels an unset bool "Not set" or "<state> (default)" (Story 17.6) and reverts a failed bool save (`revertOnError`). It builds the env badge from `envVar` or `VS_CFG_${key.toUpperCase()}`; `GameConfigPanel` never passed `envVar`, so the badge read `VS_CFG_ENTITYSPAWNING`.
- `useGameConfig` polls every 30 s; `useServerStatus` every 5 s (`hooks/use-server-status.ts`). The game reports the value a few seconds after the state becomes `running` (Story 25.3 AC 10: about 25 s after start).
- `relativeTime` (`web/src/lib/relative-time.ts`).

### References

- `epics.md` "Story 25.4"; `architecture/epic-25-server-config-read-correctly.md` ADR-5; Story 17.6; Story 25.3

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5).

### Debug Log References

- `just check` (2026-11-21): exit 0; API 4229 passed, web 3974 passed; Pyright 0/0; lints green.

### Implementation decisions

- **A game-kept setting is recognised by `source` in the response**, not by its key, so the panel needs no list of such settings.
- **The refetch on every status poll (5 s) runs only while the server runs and the game has not reported** (`exact: true` on `['config', 'game']`, so the path check is not refetched with it). If the game never answers, the page keeps asking every 5 s while it is open; the API answers from memory.
- **Story 17.6's default tests are kept**: the `gameDefault` mechanism stays for any bool the API gives a default; no setting has one today.
- **No README change**: Story 25.3's "Entity Spawning" paragraph already describes what Game Settings shows.

### Completion Notes List

- 2026-11-21 (dev-story): Tasks 1 and 2 done. Entity Spawning in Game Settings follows `source` (enabled only from the game; "Not known yet"; when last reported); the env badge names the API's variable; the settings refetch with the server state. 11 new web tests.

- 2026-11-21 (create-story): created from Epic 25's Story 25.4 and ADR-5. Found in creation: the env badge guessed the variable name (`VS_CFG_ENTITYSPAWNING`), so every field now gets the API's `env_var` (AC 5); "Not known yet" applies while running but not yet reported too, so the description names both cases.

### File List

- `web/src/api/types.ts`, `web/src/components/SettingField.tsx`, `web/src/features/game-server/GameConfigPanel.tsx`, `web/src/features/game-server/GameConfigPanel.test.tsx` (Task 1)
- this file; `sprint-status.yaml` (through `just sprint set`)

## Change Log

- 2026-11-21: Story 25.4 created (create-story); status ready-for-dev.
- 2026-11-21: Story 25.4 implemented (dev-story): Tasks 1 and 2; status review.
