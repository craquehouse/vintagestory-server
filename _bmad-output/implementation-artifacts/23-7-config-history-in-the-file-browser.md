# Story 23.7: Config History in the File Browser

Status: review

<!-- Implements FR324, FR325, Epic 23 ADR-8, ADR-9. Bead: VSS-hb4d (API-098), closed by this story after merge (23.6 carried its API half). Branch story/23-7-config-history-in-the-file-browser, stacked on story/23-6-config-edits-are-kept-as-history at 37a8ff38 (23.6 in review); the PR targets main and merges after 23.6's. Web, plus one API test's list of the web's defaults and bounds. Line references verified at 37a8ff38. -->

## Story

As an **administrator**,
I want **to browse a file's earlier versions, compare one with the current text and restore it**,
so that **I can see what an edit changed and undo it from the web UI**.

## Acceptance Criteria

1. **Given** an Admin key and a file with history
   **When** I press History in the viewer's header
   **Then** a panel replaces the viewer and lists the revisions newest first with local time, relative time ("3 hours ago"), saved by and size; a file with none says "No earlier versions. Versions are kept when the file is saved here."; Close returns to the viewer. A Monitor key sees no History button
   *(FR324; ADR-8 decision 1)*

2. **Given** a revision is chosen
   **When** the panel is `md` or wider, and when it is narrower
   **Then** the revision is compared with the current text in a read-only CodeMirror merge view, side by side (revision left, current right) from `md` up and unified below it; "Show this version" switches to the revision's text alone, and back
   *(FR324; ADR-8 decision 2)*

3. **Given** the game server is stopped
   **When** I press Restore on a revision and confirm ("Replace the current file with the version from {time}? The current text is kept in the history.")
   **Then** `POST /config/history/{path}/restore` is sent with the read's version; on 200 a toast says "Restored {path}", the history and the read refresh and the panel closes. A 409/422 refusal is shown with the API's message. While the server is not stopped Restore is disabled with Story 23.5's line; while the editor has unsaved changes History is disabled ("Save or cancel your changes first")
   *(FR324; ADR-8 decision 3)*

4. **Given** the API Settings tab
   **When** an Admin opens it
   **Then** a "Config History" group edits "Versions kept" (`config_history_keep_count`, 1 to 200) and "Maximum age (days)" (`config_history_max_age_days`, 0 to 3650, 0 = any age), with help text saying history is kept only for files saved in the file browser and a lower limit applies at a file's next save; the web defaults and bounds match the API (`TestWebDefaults`)
   *(FR325; ADR-8 decision 4)*

5. **Given** the CodeMirror chunk
   **When** the app is built
   **Then** `@codemirror/merge` is in the lazily loaded code-view chunk, not the main one
   *(ADR-8 decision 5)*

6. **(Quality gates.)** `just check` green, 0 skipped; no suppression added; the E2E that saves runs only in the throwaway container (ADR-9 decision 3).

## Tasks / Subtasks

- [x] Task 1: `@codemirror/merge` and the `RevisionCompare` component + tests (AC: 2, 5, 6)
  - [x] 1.1: `cd web && bun add @codemirror/merge@^6.12.3` (only it and its dependencies)
  - [x] 1.2: Red first: `RevisionCompare.test.tsx` (jsdom, real CodeMirror): side-by-side renders `.cm-mergeView` with both texts, read-only; unified renders one editor whose document is the current text and marks the deleted lines; `split` switching re-renders
  - [x] 1.3: `components/code-view/RevisionCompare.tsx` (props `original`, `current`, `split: boolean`, `wordWrap`; `MergeView` with `a` = original, `b` = current when split; otherwise an `EditorView` with `unifiedMergeView({ original, mergeControls: false })`; both read-only with the JSON5 language and styles, destroyed on unmount); `LazyRevisionCompare.tsx`
  - [x] 1.4: Commit `build(story-23.7/task-1): add CodeMirror's merge view for comparing config file versions`

- [x] Task 2: API calls and hooks + tests (AC: 1, 3, 6)
  - [x] 2.1: Red first: `config.test.ts` (`fetchConfigHistory(path)` -> `{filename, revisions}` mapped to camelCase `savedAt`, `savedBy`; `fetchConfigRevision(path, id)` -> `{revision, text}`; `restoreConfigRevision(path, revision, version)` -> `POST .../restore`; invalid names send nothing); hook tests (`useConfigHistory(path, enabled)`, `useConfigRevision(path, id)`, `useRestoreConfigRevision()` invalidating the history and the read)
  - [x] 2.2: `types.ts` (`ConfigRevision`, `ConfigHistoryData`, `ConfigRevisionData`), `config.ts`, `use-config-files.ts`
  - [x] 2.3: Commit `refactor(story-23.7/task-2): add the web API calls for config file history`

- [x] Task 3: The history panel + tests (AC: 1, 2, 3, 6)
  - [x] 3.1: Red first: `ConfigHistoryPanel.test.tsx` and `FileManagerPanel.edit.test.tsx` rows (list, empty, choose and compare, show this version, restore with confirm, refusal message, disabled while not stopped; History button for Admin only, disabled while editing with changes) with `LazyRevisionCompare` stubbed
  - [x] 3.2: `features/settings/ConfigHistoryPanel.tsx`; `FileManagerPanel.tsx`: a History button in the viewer's actions (Admin with a read version), `showingHistory` state, the panel in the viewer's place
  - [x] 3.3: Commit `feat(story-23.7/task-3): see, compare and restore earlier versions of config files`

- [x] Task 4: The Config History settings + tests (AC: 4, 6)
  - [x] 4.1: Red first: `ApiSettingsPanel.test.tsx` rows (the two fields, their bounds and help text, saving); `api/tests/test_api_settings.py`: `WEB_DEFAULT_KEYS` and `WEB_BOUNDS` gain the two settings and the two bounds
  - [x] 4.2: `config.ts`: `MAX_CONFIG_HISTORY_KEEP_COUNT = 200`, `MAX_CONFIG_HISTORY_AGE_DAYS = 3650`, two `API_SETTING_DEFAULTS` lines; `types.ts`: `configHistoryKeepCount`, `configHistoryMaxAgeDays`; `ApiSettingsPanel.tsx`: the group after Backup Cleanup
  - [x] 4.3: Commit `feat(story-23.7/task-4): set how many earlier versions of config files are kept`

- [x] Task 5: E2E (AC: 1-3)
  - [x] 5.1: `e2e/config-file-history.spec.ts` (throwaway container only, as `config-file-editor.spec.ts`): create a file, save it twice through the API, open History, choose the oldest, check the compare shows both texts, restore, check the file through the API, remove the file
  - [x] 5.2: `just test-e2e-ci e2e/config-file-history.spec.ts e2e/config-file-editor.spec.ts e2e/content-security-policy.spec.ts`
  - [x] 5.3: Commit `test(story-23.7/task-5): check comparing and restoring a config file version end to end`

- [x] Task 6: Validate and move the story to review (AC: all)
  - [x] 6.1: `just check`; `just build-web` chunk sizes recorded
  - [x] 6.2: `just changelog` lists exactly two entries (Tasks 3 and 4)
  - [x] 6.3: Status `review`; sprint status; Dev Agent Record and File List
  - [x] 6.4: Commit `chore(story-23.7/task-6): validate and move story 23.7 to review`

## Dev Notes

### The code today (verified at 37a8ff38)

- API (Story 23.6): `GET /api/v1alpha1/config/history/{path}` -> `{filename, revisions: [{id, saved_at, saved_by, size, sha256}]}`; `?revision=id` -> `{filename, revision, text}`; `POST .../restore` `{revision, version}` -> `{filename, version}`; errors as the save's plus `CONFIG_REVISION_INVALID` (400), `CONFIG_REVISION_NOT_FOUND` (404), `CONFIG_HISTORY_WRITE_FAILED` (500). The client's default camelCase transform suits these (no file content keys), so no `transformResponse: false`.
- Web (Story 23.5): `components/code-view/` (`CodeView`, `LazyCodeView`, `json5-language`), `features/settings/ConfigFileEditor.tsx` (`ServerNotStoppedNote`, `EditFileButton`), `ConfirmDialog.tsx`, `FileManagerPanel.tsx` (`editBase`, `dirty`, `serverStopped`, `editAction` in the viewer's `actions`), `src/test/mocks/lazy-code-view.tsx`.
- `hooks/use-media-query.ts`: `useMediaQuery(query)`; `md` is `(min-width: 768px)`.
- `ApiSettingsPanel.tsx`: `SettingGroup`/`SettingField` groups; Backup Cleanup at `:149-163` is the model.
- `api/tests/test_api_settings.py`: `WEB_DEFAULT_KEYS` (`:1315`) and `WEB_BOUNDS` (`:1311`) pin the web's copies.

### Relative time

`Intl.RelativeTimeFormat` (`numeric: 'auto'`) over seconds, minutes, hours, days, months and years; local time with `toLocaleString()`. Size in bytes below 1024, else KiB with one decimal.

### Testing

Stub `LazyRevisionCompare` in flow tests (add `src/test/mocks/lazy-revision-compare.tsx`, rendering the two texts in `pre` elements with `data-split`).

### References

- `epics.md` "Story 23.7"; `architecture/epic-23-config-file-editing.md` ADR-8, ADR-9
- Stories 23.5 and 23.6

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5), as the epic's controller.

### Debug Log References

- `just check` (2026-11-19, with Stories 23.1 to 23.6 merged in): API 3995 passed, web 3851 passed, 0 skipped; Pyright 0/0; lints green.
- `just test-e2e-ci e2e/config-file-history.spec.ts e2e/config-file-editor.spec.ts e2e/content-security-policy.spec.ts e2e/file-browser-navigation.spec.ts`: 14 passed; API E2E 4 passed.
- `just build-web`: CodeMirror is split across lazily loaded chunks (`CodeView-*.js` 45.07 kB, `RevisionCompare-*.js` 28.85 kB, and the shared CodeMirror chunk); `index-*.js` 369.59 kB (118.99 kB gzip), as before the epic's editor.

### Completion Notes List

- 2026-11-19 (create-story, dev-story): Tasks 1 to 6 done.
- **What changed.** `@codemirror/merge`. `components/code-view/RevisionCompare.tsx` (`MergeView` side by side, or `unifiedMergeView` with `mergeControls: false`, read-only, JSON5 highlighting) and `LazyRevisionCompare.tsx`. `api/config.ts`: `fetchConfigHistory`, `fetchConfigRevision`, `restoreConfigRevision`, `MAX_CONFIG_HISTORY_KEEP_COUNT`, `MAX_CONFIG_HISTORY_AGE_DAYS`, two defaults; `types.ts`: `ConfigRevision`, `ConfigHistoryData`, `ConfigRevisionData`, two settings fields. Hooks `useConfigHistory`, `useConfigRevision`, `useRestoreConfigRevision`. `features/settings/ConfigHistoryPanel.tsx` (list, compare, show alone, restore with confirmation, `relativeTime`, `formatSize`); `FileManagerPanel.tsx` (History button beside Edit, the panel in the viewer's place, closed by any navigation). `ApiSettingsPanel.tsx`: the Config History group. `api/tests/test_api_settings.py`: `WEB_DEFAULT_KEYS` and `WEB_BOUNDS` gain the new keys and bounds.
- **Tests.** 3 RevisionCompare (real CodeMirror), 4 config API, 3 hooks, 11 history panel, 3 panel (History button, closed by navigation, Monitor), 7 API Settings rows; existing typed settings fixtures gained the two fields, and the "eight settings" test is now ten. E2E `e2e/config-file-history.spec.ts`.
- **Deviation.** AC 3's "History disabled while the editor has unsaved changes" holds by construction: while editing, the editor replaces the viewer and its header, so the History button is not shown; there is no separate disabled state.
- No suppression added; `git diff 37a8ff38 -- api/src` empty (only the web-defaults test changed in `api/tests`). `just changelog`: two entries from this story, 303a00f (Task 3) and 025fc97 (Task 4).

### File List

- `web/package.json`, `web/bun.lock` (modified)
- `web/src/components/code-view/RevisionCompare.tsx`, `RevisionCompare.test.tsx`, `LazyRevisionCompare.tsx` (new)
- `web/src/test/mocks/lazy-revision-compare.tsx` (new)
- `web/src/api/config.ts`, `config.test.ts`, `types.ts` (modified)
- `web/src/hooks/use-config-files.ts`, `use-config-files.test.tsx`, `use-api-settings.test.tsx` (modified)
- `web/src/features/settings/ConfigHistoryPanel.tsx`, `ConfigHistoryPanel.test.tsx` (new)
- `web/src/features/settings/FileManagerPanel.tsx`, `FileManagerPanel.edit.test.tsx`, `ApiSettingsPanel.tsx`, `ApiSettingsPanel.test.tsx` (modified)
- `web/e2e/config-file-history.spec.ts` (new)
- `api/tests/test_api_settings.py` (modified)
- `_bmad-output/implementation-artifacts/23-7-config-history-in-the-file-browser.md` (this file)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (through `just sprint set` only)

## Change Log

- 2026-11-19: Story 23.7 created (ready-for-dev).
- 2026-11-19: Implemented (dev-story): Tasks 1 to 6; status review.
