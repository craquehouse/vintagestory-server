# Story 25.2: Game Settings Warns About a Wrong Path

Status: ready-for-dev

<!-- Implements FR348, Epic 25 ADR-3. Bead: VSS-7ap (API-012, closes with this story after merge). Branch story/25-2-game-settings-warns-about-a-wrong-path, stacked on story/25-1-serverconfig-is-read-through-one-typed-model-and-its-paths-are-checked (PR #223); the PR targets main and merges after 25.1's. Web, plus one API field (`manager_mods_folder`). -->

## Story

As an **administrator**,
I want **Game Settings to tell me when a mod or save path is wrong**,
so that **I can fix it**.

## Acceptance Criteria

1. **Given** a path entry with `problem: true`, or `manager_mods_folder_listed: false`
   **When** Game Settings opens
   **Then** a warning above the settings groups names each problem: the path as given and as resolved and what is wrong, and for the mods folder the folder the manager installs into (`manager_mods_folder`, new in the response)
   *(FR348; ADR-3 decision 3)*

2. **Given** an Admin key
   **When** the warning shows
   **Then** it says how to fix it: absolute paths such as `/data/serverdata/Mods`, edited in **Settings → File Manager → serverconfig.json** while the game server is stopped; a Monitor key gets "Ask an administrator to correct serverconfig.json." instead
   *(FR348)*

3. **Given** every entry has `problem: false` and the mods folder is listed
   **When** Game Settings opens
   **Then** no warning shows
   *(FR348)*

4. **Given** the check fails (404, 422, network) or its response has another shape
   **When** Game Settings opens
   **Then** the settings show as before, with no warning and no error from the check
   *(FR348; ADR-3 decision 2)*

5. **Given** a `serverconfig.json` saved or restored in the file browser
   **When** the save succeeds
   **Then** the settings and the path check are fetched again; otherwise the check refreshes with the settings' 30-second polling
   *(ADR-3 decision 1)*

6. The warning is a `role="alert"` region (announced once when it appears); it has no controls, so it adds no touch targets.

7. **(Quality gates.)** `just check` green; no suppression added.

## Tasks / Subtasks

- [ ] Task 1: `manager_mods_folder` in the path check (AC: 1)
  - [ ] 1.1: `PathCheck.manager_mods_folder` (the resolved `{serverdata}/Mods`); tests; README sentence
  - [ ] 1.2: Commit `refactor(story-25.2/task-1): name the manager's mods folder in the path check`

- [ ] Task 2: The warning (AC: 1-6)
  - [ ] 2.1: Types `ServerConfigPathEntry`, `ServerConfigPathCheck`; `fetchServerConfigPaths`; `queryKeys.config.gamePaths` (under `['config', 'game']`); `useServerConfigPaths` (30 s polling, no retry)
  - [ ] 2.2: `ServerConfigPathsWarning` (problem list, Admin fix text, Monitor text, renders nothing on error or another shape); placed in `GameConfigPanel` after the read-only note
  - [ ] 2.3: `useSaveConfigFile` and `useRestoreConfigRevision` invalidate `['config', 'game']` when the root `serverconfig.json` changes
  - [ ] 2.4: Tests: each status's text, the mods-folder line, the save line, no problem, failed check, other shape, Monitor, the invalidation
  - [ ] 2.5: README sentence (Game Settings shows the warning)
  - [ ] 2.6: Commit `feat(story-25.2/task-2): warn in Game Settings when a mod or save path in serverconfig.json is wrong`

- [ ] Task 3: Validate and move the story to review (AC: 7)
  - [ ] 3.1: `just check` green
  - [ ] 3.2: Status `review`; sprint status; Dev Agent Record and File List
  - [ ] 3.3: Commit `chore(story-25.2/task-3): validate and move story 25.2 to review`

## Dev Notes

### The code today (verified at 3f734626, the tip of 25.1)

- `GET /config/game/paths` returns `{mod_paths, save_file, manager_mods_folder_listed}`; entries `{given, resolved, status, problem}` (`models/server_config.py`). The web client turns snake_case into camelCase (`web/src/api/client.ts`).
- `GameConfigPanel` (`web/src/features/game-server/GameConfigPanel.tsx`) renders the read-only note then the groups; `useIsAdmin` gives the role. `useGameConfig` polls every 30 s (`hooks/use-game-config.ts`).
- The file browser has no URL that opens a given file (Settings tabs and the selected file are component state), so the warning names where to go instead of linking (ADR-3 decision 3 as implemented).
- `GameConfigPanel.test.tsx` mocks `fetch` to answer every URL with the settings response, so the warning must treat an unexpected shape as "no data".
- `UnusedFilesNotice` (Story 24.6) is the nearest notice-with-a-list pattern; `ModUpdatesNotice` is a one-line link.

### References

- `epics.md` "Story 25.2"; `architecture/epic-25-server-config-read-correctly.md` ADR-2, ADR-3; Story 25.1

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5).

### Debug Log References

### Completion Notes List

- 2026-11-21 (create-story): created from Epic 25's Story 25.2 and ADR-3. Found in creation: the file browser cannot be linked to a file, so the warning names the place (ADR-3 decision 3); the response needs the manager's folder to name it (`manager_mods_folder`); the check refreshes with the settings' polling rather than on a server status change.

### File List

## Change Log

- 2026-11-21: Story 25.2 created (create-story); status ready-for-dev.
