# Story 23.5: Config Files Are Edited in the File Browser

Status: ready-for-dev

<!-- Implements FR319, FR320, FR326 (editing part), Epic 23 ADR-5, ADR-6 decision 3, ADR-9. Bead: VSS-glz (UI-025), closed by this story after merge (23.4 carried its API half). Branch story/23-5-config-files-are-edited-in-the-file-browser, stacked on story/23-4-config-files-can-be-saved-through-the-api at 9a6e5e9c (23.4 in review); the PR targets main and merges after 23.4's. Web, README, and one line of the API error handling in the web client. Line references verified at 9a6e5e9c. -->

## Story

As an **administrator**,
I want **to edit a config file in the file browser while the game server is stopped**,
so that **I can change mod and server configs without a shell on the host**.

## Acceptance Criteria

1. **Given** an Admin key and a stopped game server (state `installed`, `not_installed` or `error`)
   **When** I open a file whose read has `text` and press Edit
   **Then** a CodeMirror editor (line numbers, undo history, search, JSON5 highlighting) shows the file's text with its comments; a status line shows "Valid", or the error's message with "line L, column C" from `POST /config/files/validate`, 500 ms after typing stops and once on opening; clicking a positioned error moves the cursor there
   *(FR319; ADR-5 decisions 1, 3 and 4)*

2. **Given** valid, changed text
   **When** I press Save
   **Then** `PUT /config/files/{path}` is sent with the read's `version`; on 200 a toast says "Saved {path}", edit mode ends and the viewer shows the new text (the read is refetched). Save is disabled while the text is unchanged, invalid, or waiting for a check, and while the server is not stopped
   *(FR319; ADR-5 decisions 4 and 5)*

3. **Given** a save answered 409 `CONFIG_FILE_CHANGED`, 409 `CONFIG_FILE_SERVER_RUNNING` or `CONFIG_FILE_SERVER_BUSY`, or 422 `CONFIG_FILE_INVALID`
   **When** it comes back
   **Then** my text is kept; the message explains it ("The file changed on disk since you opened it.", the API's message for the two others); for a change on disk a Reload action asks for confirmation and then discards my text and loads the file again; for a 422 the status line shows the error with its position
   *(FR319; ADR-5 decision 5)*

4. **Given** unsaved changes
   **When** I press Cancel, select another file or directory, or use the breadcrumb
   **Then** a dialog asks "Discard your changes to {path}?" (Discard / Keep editing); with no changes nothing asks. Closing or reloading the tab triggers the browser's leave-page prompt (`beforeunload`). Switching to another Settings tab and back keeps the editor and its text (the File Manager tab stays mounted). Leaving the Settings page through the app's navigation keeps the draft in memory: when I open the same file again, Edit reads "Resume editing" and restores the draft (while the file's version is unchanged; a changed file drops it)
   *(FR319; ADR-5 decision 6, with the deviation recorded in Dev Notes "Unsaved changes")*

5. **Given** the game server is running, starting or stopping, or installing
   **When** I view a file as Admin
   **Then** Edit is disabled and a line says "Stop the game server to edit files: the game can overwrite changes made while it runs." with a link to the Dashboard (its server controls); if the server starts while I edit, Save is disabled with the same line and my text is kept. A Monitor key sees no Edit button
   *(FR319; ADR-5 decision 3, ADR-6 decision 3)*

6. **Given** an Admin key and a file that parses
   **When** I view it (not editing)
   **Then** it is shown as its text with comments in a read-only highlighted CodeMirror view, and the word-wrap toggle wraps it; a Monitor key sees the highlighted parsed content as before; an unparseable file keeps Story 23.1's warning and plain text, with Edit available to Admin to fix it
   *(FR320; ADR-5 decision 7)*

7. **Given** the production build served with the CSP enforced
   **When** the editor is opened
   **Then** no CSP violation is reported, and the CodeMirror code is in its own lazily loaded chunk (the main chunk does not grow by it)
   *(FR319; ADR-5 decisions 1 and 2)*

8. **Given** the README's Config files section
   **When** an operator reads it
   **Then** it explains editing: Admin only, only while the game server is stopped and why, the text is saved as typed, `serverconfig.json` must stay standard JSON (no comments or trailing commas), the check while typing, and the refusal when the file changed meanwhile
   *(FR326; ADR-4, ADR-5)*

9. **(Quality gates.)** `just check` green, 0 skipped; no suppression, `cast`, `as unknown as`, skip or `.only` added; E2E in the CI set (throwaway container) only for anything that saves (ADR-9 decision 3); `git diff` of `api/` empty.

## Tasks / Subtasks

<!-- Red first. Subjects: type(story-23.5/task-N): ... User-visible: Task 4 (feat(web)) and Task 5 (feat(web)). -->

- [x] Task 1: CodeMirror and the `CodeView` component + tests (AC: 1, 6, 7, 9)
  - [x] 1.1: `cd web && bun add @codemirror/state@^6.7.6 @codemirror/view@^6.43.15 @codemirror/commands@^6.11.1 @codemirror/language@^6.13.1 @codemirror/search@^6.7.2` (check `package.json` and `bun.lock` gain only these and their own dependencies, e.g. `@lezer/*`, `style-mod`, `w3c-keyname`, `crelt`)
  - [x] 1.2: Red first: `web/src/components/code-view/json5-language.test.ts` (the tokenizer: line and block comments, double- and single-quoted strings with escapes, numbers incl. hex, `Infinity`/`NaN`, `true`/`false`/`null`, property names before `:`, punctuation); `CodeView.test.tsx` (renders the text; read-only does not change on typing; `onChange` fires with the new text; `goTo(line, column)` moves the selection; `wordWrap` toggles `cm-lineWrapping`)
  - [x] 1.3: `json5-language.ts` (Dev Notes "JSON5 highlighting") and `CodeView.tsx` (Dev Notes "CodeView"); `LazyCodeView.tsx` (`React.lazy` + `Suspense` with a skeleton)
  - [x] 1.4: Commit `build(story-23.5/task-1): add CodeMirror for viewing and editing config files`

- [x] Task 2: API functions, error details and hooks + tests (AC: 1, 2, 3, 9)
  - [x] 2.1: Red first: `client.test.ts` (an error detail's keys other than `code`/`message`/`details` reach `ApiError.details`); `config.test.ts` (`saveConfigFile(path, text, version)` sends `PUT` with `{text, version}` and returns `{filename, version}`; `checkConfigText(path, text)` sends `POST /files/validate` with `{filename, text}` and maps `{valid, parse_error}`; both refuse an invalid name without a request); hook tests for `useSaveConfigFile` (invalidates the file's read on success) and `useConfigTextCheck` (debounce 500 ms with fake timers; latest text wins; disabled when `path` is null)
  - [x] 2.2: `client.ts` `handleApiError`: `details` = `detail.details` if present, else the detail's other keys (if any); `config.ts`, `use-config-files.ts`, `types.ts` (Dev Notes "API functions")
  - [x] 2.3: Commit `refactor(story-23.5/task-2): add the web API calls for saving and checking config files`

- [ ] Task 3: The Admin read-only text view + tests (AC: 6, 9)
  - [ ] 3.1: Red first: `FileViewer.test.tsx` rows (Admin with `text` and no parse error: `file-viewer-code` with the text, comments included, no `file-viewer-content`; Monitor (no `text`): the highlighted content as before; word wrap passes through); mock `LazyCodeView` with a light stub in component tests (Dev Notes "Testing")
  - [ ] 3.2: `FileViewer.tsx`: when `text` is a string and `parseError` is null, render `LazyCodeView` read-only (`data-testid="file-viewer-code"`); otherwise as today. New optional `actions?: ReactNode` rendered in the header before the word-wrap toggle
  - [ ] 3.3: Commit `feat(story-23.5/task-3): show config files with their comments to Admin keys`

- [ ] Task 4: The editor, Save and the guards + tests (AC: 1-5, 9)
  - [ ] 4.1: Red first: `ConfigFileEditor.test.tsx` and `FileManagerPanel.test.tsx` rows for every AC 1-5 case (Dev Notes "Testing")
  - [ ] 4.2: `web/src/features/settings/config-drafts.ts`, `ConfigFileEditor.tsx`, `EditFileButton` (in the editor's module or its own), `FileManagerPanel.tsx` changes, `SettingsPage.tsx` (`forceMount` on the File Manager tab content, hidden when inactive), the discard `AlertDialog` (Dev Notes "Editor", "Unsaved changes", "Server state")
  - [ ] 4.3: Commit `feat(story-23.5/task-4): edit config files in the file browser while the game server is stopped`

- [ ] Task 5: README + E2E (AC: 7, 8)
  - [ ] 5.1: README `### Config files`: the editing paragraph (Dev Notes "Documentation")
  - [ ] 5.2: `web/e2e/config-file-editor.spec.ts` (Dev Notes "E2E"): runs only when `E2E_CONTAINER` is the throwaway container (as `file-browser-new-directory.spec.ts`); creates `ModConfig/e2e-edit-<random>.json` with `docker exec`, edits, saves, reloads, checks the file's content through the API, removes the file; checks no `securitypolicyviolation` event fired and that Monitor (stubbed role) sees no Edit button. `just test-e2e-ci e2e/config-file-editor.spec.ts e2e/content-security-policy.spec.ts e2e/file-browser-*.spec.ts`
  - [ ] 5.3: Commit `test(story-23.5/task-5): check editing a config file end to end, and document editing`

- [ ] Task 6: Validate and move the story to review (AC: all)
  - [ ] 6.1: `just check` green; `just build-web` and record the chunk sizes (main chunk vs the CodeMirror chunk) in the completion notes; `git diff 9a6e5e9c -- api` empty
  - [ ] 6.2: `just changelog` lists exactly two entries from this story (Tasks 3 and 4)
  - [ ] 6.3: Status `review`; `just sprint set 23-5-config-files-are-edited-in-the-file-browser review`; Dev Agent Record and File List
  - [ ] 6.4: Commit `chore(story-23.5/task-6): validate and move story 23.5 to review`

## Dev Notes

### The code today (verified at 9a6e5e9c)

- `web/src/components/FileViewer.tsx` (Story 23.1): props `filename`, `content`, `isLoading`, `error`, `wordWrap`, `onWordWrapChange`, `parseError`, `text`, `className`; the header has the name and the word-wrap toggle; `parseError` shows the warning and the text (Admin) or a note.
- `web/src/features/settings/FileManagerPanel.tsx` (Stories 23.2, 23.3): `currentDirectory: string[]`, `selectedFile: { directory, name } | null`, `useIsAdmin`, `useConfigFileContent([...directory, name])`; handlers `handleSelectFile`, `handleSelectDirectory`, `handleNavigate`.
- `web/src/features/settings/SettingsPage.tsx`: Radix `Tabs` with `TabsContent value="file-manager"`; Radix unmounts inactive tab content unless `forceMount`.
- `web/src/api/client.ts` `handleApiError` (`:102-134`): `ApiError(code, message, status, details)` with `details = detail.details` only; the API's 422 for a save puts `parse_error` directly in `detail` (Story 23.4), so today it would be dropped.
- `web/src/api/config.ts`: `toConfigPath`, `fetchConfigFileContent(path)` (no key transform). `web/src/hooks/use-config-files.ts`: the three query hooks. `web/src/hooks/use-server-status.ts`: `useServerStatus()` polls `GET /server/status`; `data.data.state` is a `ServerState` (`types.ts:37-44`).
- `App.tsx` uses `BrowserRouter` (not a data router), so React Router's `useBlocker` is not available (it throws outside a data router).
- The CSP (`api/.../main.py:255-268`): `script-src 'self'`, `style-src 'self' 'unsafe-inline'`. CodeMirror injects `<style>` elements (allowed) and uses no `eval` and no workers. `e2e/content-security-policy.spec.ts` checks the policy on the built page.
- API (Story 23.4): `PUT /config/files/{path}` body `{text, version}` -> `{filename, version}`; errors 409 `CONFIG_FILE_SERVER_RUNNING` / `CONFIG_FILE_SERVER_BUSY` / `CONFIG_FILE_CHANGED`, 422 `CONFIG_FILE_INVALID` with `parse_error`, 413, 404, 400, 500 `CONFIG_FILE_WRITE_FAILED`; `POST /config/files/validate` body `{filename, text}` -> `{valid, parse_error}`.

### JSON5 highlighting (Task 1)

`StreamLanguage.define<{ inBlockComment: boolean }>` from `@codemirror/language`, no language package (ADR-5 decision 1 lets the story choose; `@codemirror/lang-json` has no comments and JSON5 is not valid JavaScript at the top level, so a 60-line tokenizer is smaller and right): `//` to end of line -> `comment`; `/* ... */` across lines -> `comment` (state); `"..."` and `'...'` with backslash escapes -> `string`, or `propertyName` when the next non-space character is `:`; numbers (`-`/`+`, decimal, exponent, `0x` hex, leading or trailing dot) -> `number`; `true`/`false` -> `bool`; `null` -> `null`; `Infinity`/`NaN` -> `number`; unquoted identifiers before `:` -> `propertyName`; `{}[],:` -> `punctuation`/`brace`. Highlight with `syntaxHighlighting(defaultHighlightStyle)` plus a small `HighlightStyle` for the dark theme colours used by `json-highlighter.ts` (match its `json-key`/`json-string`/`json-number`/`json-boolean`/`json-null` classes' colours via CSS variables, so both themes read well).

### CodeView (Task 1)

`CodeView` props: `value: string`, `readOnly?: boolean`, `wordWrap?: boolean`, `onChange?: (text: string) => void`, `ariaLabel: string`, `className?`, and a ref handle `{ goTo(line: number, column: number): void; focus(): void }` (`forwardRef` + `useImperativeHandle`). One `EditorView` per mount (`useEffect` creating it into a `div`, destroyed on unmount). Extensions: `lineNumbers()`, `highlightActiveLineGutter()`, `history()`, `drawSelection()`, `keymap.of([...defaultKeymap, ...historyKeymap, ...searchKeymap, indentWithTab])`, `highlightSelectionMatches()`, `json5Language`, the highlight styles, a `Compartment` for `EditorState.readOnly` + `EditorView.editable`, a `Compartment` for `EditorView.lineWrapping`, `EditorView.updateListener` calling `onChange` on `docChanged` (through a ref, so a new callback does not recreate the view), `EditorView.contentAttributes.of({ 'aria-label': ariaLabel })`, and a theme with `height: 100%`, the app's mono font and border colours via CSS variables. A changed `value` prop that differs from the document replaces it (for Reload). `LazyCodeView` = `lazy(() => import('./CodeView'))` in `Suspense` with a `Skeleton`; it forwards the ref.

### API functions (Task 2)

- `saveConfigFile(path: readonly string[], text: string, version: string): Promise<ApiResponse<ConfigFileSaveData>>` -> `PUT ${API_PREFIX}/files/${encodeURIComponent(toConfigPath(path))}` with `body: { text, version }` (the client's camel-to-snake transform leaves these keys alone). `ConfigFileSaveData { filename: string; version: string }`.
- `checkConfigText(path, text): Promise<ConfigTextCheck>` -> `POST ${API_PREFIX}/files/validate` with `{ filename: toConfigPath(path), text }`, `transformResponse: false`, mapped to `{ valid: boolean; parseError: ConfigParseError | null }` (reuse Story 23.1's `toParseError`).
- `parseErrorFromApiError(error: unknown): ConfigParseError | null`: an `ApiError` with code `CONFIG_FILE_INVALID` and `details.parse_error` -> mapped; else null.
- Hooks in `use-config-files.ts`: `useSaveConfigFile()` (`useMutation`; on success `invalidateQueries` for `queryKeys.config.file(joined path)`); `useConfigTextCheck(path: readonly string[] | null, text: string, enabled: boolean)` (a `useDebouncedValue(text, 500)` then `useQuery` keyed `['config', 'files', 'check', joined path, debounced text]`, `staleTime: Infinity`, `retry: false`, `enabled` only when `enabled && path`); returns `{ check, isPending }` where `isPending` is true while the debounced text lags the text or the query fetches.

### Editor (Task 4)

- `ConfigFileEditor` props: `path: string[]`, `displayPath: string`, `initialText: string`, `version: string`, `serverStopped: boolean`, `onDone(saved: boolean)`, `onDirtyChange(dirty: boolean)`, `draft?: string`. State: `text`, `conflict: 'changed' | null`, `saveError: string | null`. Layout: a header row (the path, then Save (primary) and Cancel buttons, `min-h-11 md:min-h-9`), the `LazyCodeView` (editable), a status line (`role="status"`, `aria-live="polite"`): "Checking..." while pending, "Valid" (success colour), or the message with a button "line L, column C" that calls `goTo`; below, the server-not-stopped line (AC 5) or the save error / conflict message with its action.
- Save enabled when `serverStopped && text !== initialText && check is valid && !pending && !mutation.isPending`. On 200: `toast.success(`Saved ${displayPath}`)`, clear the draft, `onDone(true)`. On errors: `CONFIG_FILE_CHANGED` -> conflict with "Reload" (confirm dialog "Discard your changes and load the file as it is now?") which clears the draft and `onDone(false)` after invalidating the read; `CONFIG_FILE_INVALID` -> the status line shows `parseErrorFromApiError`; others -> the API's message.
- `EditFileButton` in the viewer header (`actions`): label "Edit" (or "Resume editing" when a draft exists for this path and version), `Pencil` icon, disabled with `aria-describedby` to the AC 5 line when the server is not stopped.
- Panel: `editing: boolean`, `dirty: boolean`; Edit enters editing; the select-file, select-directory and breadcrumb handlers go through `guard(action)`: when editing and dirty, open the discard dialog and run the action on Discard; when editing and not dirty, leave edit mode and run it. Selecting the same file while editing does nothing.
- The viewer shows the editor instead of its body while editing (the panel renders `ConfigFileEditor` in the viewer's place).

### Unsaved changes (Task 4)

- `beforeunload`: a `useEffect` in `ConfigFileEditor` adds a listener while dirty that calls `event.preventDefault()` (and sets `returnValue = ''` for older browsers).
- Settings tabs: `TabsContent value="file-manager" forceMount` with `className="... data-[state=inactive]:hidden"` so the panel (and the editor) stays mounted.
- Leaving the page through the app's navigation: `useBlocker` is not available with `BrowserRouter` (App.tsx), and moving the app to a data router is out of scope. Instead `config-drafts.ts` keeps `Map<joinedPath, { version, text }>` in memory (module scope, cleared on save, Reload, Discard and Cancel with no changes; never persisted to storage, since a config text can hold secrets). The editor writes the draft on every change; `EditFileButton` shows "Resume editing" and the editor starts from the draft when the stored version equals the read's version; a different version drops the draft. **Deviation from ADR-5 decision 6** ("asks for confirmation ... another route"): the draft is kept instead of asking, recorded for the maintainer in the completion notes.

### Server state (Task 4)

`serverStopped = state === 'installed' || state === 'not_installed' || state === 'error'` from `useServerStatus()`; while the status is loading or failed, treat as not stopped (Save disabled, the API would refuse a running server anyway). The link to the server controls goes to `/` (Dashboard, `ServerControls`).

### Documentation (Task 5)

Append to README `### Config files`: An Admin key can edit a file: open it and press **Edit**. Editing is possible only while the game server is stopped, because the game and mods can write their config files while they run and would overwrite the change. The editor checks the text as you type and shows where an error is; the file is saved exactly as typed, with its comments. `serverconfig.json` is also read by the manager itself, so it must stay standard JSON: comments and trailing commas are refused there. If the file changed on disk after you opened it, the save is refused; reload it and make the change again. Unsaved changes are kept while you switch Settings tabs or visit another page, until the browser tab is closed or reloaded.

### E2E (Task 5)

`web/e2e/config-file-editor.spec.ts`: skip unless `process.env.E2E_CONTAINER === 'vintagestory-manager-e2e'` (reason as in `file-browser-new-directory.spec.ts`). Create `ModConfig` if missing and the file with `execFileSync('docker', ['exec', CONTAINER, 'sh', '-c', ...])` is not allowed (no shell): use `['exec', CONTAINER, 'mkdir', '-p', dir]` and write the file with `['exec', '-i', CONTAINER, 'tee', path]` passing the content as `input`. Steps: `serveConfigKey(admin)`; listen for `securitypolicyviolation` via `page.addInitScript` pushing to `window.__cspViolations`; open the File Manager, `ModConfig`, the file; the read-only code view shows the comment; press Edit; replace the text (`page.keyboard` select-all and type, or `locator.fill` on `.cm-content` is not supported: use `ControlOrMeta+A` then `insertText`); wait for "Valid"; Save; toast; the API read returns the new text; `window.__cspViolations` is empty; remove the file in `finally`. A second test with the stubbed monitor role: no Edit button. The game server in the throwaway container is `not_installed`, which counts as stopped.

### Testing

- Component tests mock `@/components/code-view/LazyCodeView` with a `textarea` stub that implements `value`/`onChange`/`readOnly` and exposes `goTo` through the ref (record calls), so the editor flow tests do not depend on CodeMirror's DOM measuring. `CodeView.test.tsx` tests CodeMirror itself in jsdom (it renders and dispatches there; add a `Range.prototype.getClientRects`/`getBoundingClientRect` stub in that file's `beforeAll` if CodeMirror needs it).
- `ConfigFileEditor.test.tsx`: check pending/valid/invalid status; the position button calls `goTo`; Save disabled cases; 200 path (toast, `onDone(true)`, draft cleared); 409 changed (Reload with confirmation); 409 running/busy; 422 (status shows the position); server not stopped mid-edit; `beforeunload` prevented only while dirty; draft written on change.
- `FileManagerPanel.test.tsx`: Admin sees Edit for a file with text; Monitor does not; Edit disabled + line when running; the guard dialog for file, directory and breadcrumb; Discard runs the action; no dialog when clean; "Resume editing" after unmount/remount with a draft.
- `SettingsPage.test.tsx`: the File Manager content stays mounted when another tab is active.

### References

- `epics.md` "Story 23.5"; `architecture/epic-23-config-file-editing.md` ADR-5, ADR-6, ADR-9
- Story 23.4 (`23-4-config-files-can-be-saved-through-the-api.md`) for the API contract
- `e2e/file-browser-new-directory.spec.ts` for `docker exec` in the throwaway container

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
