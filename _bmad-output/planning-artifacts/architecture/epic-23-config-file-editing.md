# Epic 23: Config File Editing - Architecture Decisions

Decisions from the Epic 23 course correction (2026-11-19). Epic 23 has no preparation story. Each fact below was checked by reading the code at commit `fc525885` (`main` after Epic 22 and the `v0.1.0-rc.8` release). The one library fact planning could not settle, how `pyjson5` reports the position of a parse error, is the first task of Story 23.1.

The maintainer named the scope: `VSS-ato4` (the config viewer rejects mod configs with comments), `VSS-glz` (edit config files in the file browser while the game server is stopped) and `VSS-hb4d` (keep a history of config edits and allow restoring one). He approved pulling in `VSS-o8s` (file browser paths that can contain a slash) and `VSS-7z3` (a Monitor key sees editable game settings). On 2026-11-19 he answered eight questions in two rounds; each ADR's status line says which answer it carries.

| Story | ADRs |
|---|---|
| 23.1 Configs with Comments Can Be Viewed | ADR-1, ADR-2, ADR-9 |
| 23.2 File Browser Paths Are Lists of Names | ADR-3 |
| 23.3 Game Settings Are Read-Only for Monitor Keys | ADR-6 |
| 23.4 Config Files Can Be Saved Through the API | ADR-1, ADR-4, ADR-9 |
| 23.5 Config Files Are Edited in the File Browser | ADR-5, ADR-6, ADR-9 |
| 23.6 Config Edits Are Kept as History | ADR-7, ADR-9 |
| 23.7 Config History in the File Browser | ADR-8, ADR-9 |

## Facts Checked in the Code

**The viewer's parser.**

- `ConfigFilesService.read_file` (`api/src/vintagestory_api/services/config_files.py:331`) parses with strict `json.loads` (`:429`). Content that does not parse is returned as `{"_raw": text, "_parse_error": message}`; for any role but Admin, `_raw` is `"[redacted]"` (`:432-447`). A `ValueError` that is not a `JSONDecodeError` (Python's long-integer limit) gets a fixed message (`:438-447`).
- Nesting deeper than `CONFIG_FILE_MAX_DEPTH = 200` is checked after parsing by `_nesting_depth_exceeds` (`:52`, `:136`) and also returned as `_raw`.
- For any role but Admin, parsed content goes through `game_config.redact_secrets` (`:453`). Because a file with comments does not parse today, it is hidden entirely (`_raw: "[redacted]"`) instead of being redacted key by key.
- The read returns `{filename, content}` only. The response has no raw text and no version tag (hash or mtime) for the parsed file.
- The game reads its configs with Newtonsoft.Json, which accepts `//` and `/* */` comments, trailing commas, single-quoted strings and unquoted keys (the bead's evidence, `ModConfig/seasonalflowers.json` on the live server).
- `pyjson5` 2.0.1 (MIT OR Apache-2.0) ships CPython 3.14 wheels for `manylinux` x86_64 and aarch64 (PyPI, checked in planning); the API requires Python 3.14 (`api/pyproject.toml:5`) and the image is built for `linux/amd64` (`.github/workflows/release.yml:90`). Its decoder takes a `maxdepth` argument and raises `Json5NestingTooDeep`. Its errors carry a message ending in `near N` (a character offset) and a `result` with the partial value. Whether the offset is also an attribute is not documented (Story 23.1 Task 1).
- JSON5 accepts `Infinity` and `NaN`. Starlette's `JSONResponse` serializes with `allow_nan=False`, so a non-finite number in the parsed content would fail the response with a 500.

**Other readers and writers of `serverconfig.json`.** All of them use strict JSON and write the object back re-serialized:

- `GameConfigService._load_config` (`services/game_config.py:580`, `json.load`) and `_update_config_file` (`:927`, `json.dumps(config, indent=2)` to a `.tmp` file, then `rename`).
- `reapply_edits` (`services/pending_config_edits.py:155`, Story 22.7), run after the game exits, before every start and at API start (`services/server.py:351`).
- `ConfigInitService` creates the file from the template only when it is missing (`services/config_init_service.py`).

A comment or trailing comma saved into `serverconfig.json` would make each of these fail, and each rewrite would drop the formatting.

**Server state and locks.** `ServerService.game_running` (`services/server.py:286`) is true only in `RUNNING`; `lifecycle_busy` (`:291`) is true while `_lifecycle_lock` or `_install_lock` is held. `start_server` takes `_lifecycle_lock` (`:1100`), as do stop, restart, uninstall and the Story 22.8 shutdown stop. `GameConfigService.is_server_running` (`services/game_config.py:569`) checks `RUNNING` only, so `STARTING` and `STOPPING` count as stopped there.

**State directory.** `Settings.state_dir` is `data/vsmanager/state` (`config.py:263`), outside `serverdata`; Story 22.7's `pending-config-edits.json` lives there.

**The web file browser.**

- `FileManagerPanel` (`web/src/features/settings/FileManagerPanel.tsx`) keeps `currentDirectory` and `selectedFile` as slash-joined strings (`:51-54`, `:105-116`). `PathBreadcrumb` (`web/src/components/PathBreadcrumb.tsx`) takes `path: string | null` and splits it on `/` (`:44`). `fetchConfigFileContent` sends `encodeURIComponent(filename)` (`web/src/api/config.ts:228-233`), so a `/` is sent as `%2F`, which the `{filename:path}` route decodes.
- `FileViewer` (`web/src/components/FileViewer.tsx`) gets the parsed `content` and pretty-prints it through `highlightJson` (`:121`). It has no case for the `_raw`/`_parse_error` shape, so such a file shows as an escaped string under two keys.
- The panel reads the role through `useAuthMe` (`:58-60`) and shows a note for roles other than Admin (Story 19.1).
- The web has no code editor and no diff library (`web/package.json`). The CSP (`api/src/vintagestory_api/main.py:255-268`) is `script-src 'self'`, `style-src 'self' 'unsafe-inline'`, with no `worker-src` (so workers fall back to `default-src 'self'`). The API tests compare the whole string.

**Game Settings.** `GameConfigPanel` (`web/src/features/game-server/GameConfigPanel.tsx`) renders every setting through `SettingField` (`web/src/components/SettingField.tsx`), which already has a `disabled` state for env-managed settings (`:132`, `:160`, `:201`, `:232`). Saving is Admin-only (`RequireAdmin`, `routers/config.py`), so a Monitor key gets a 403 after editing. Story 17.5 changed only the Password field (`SecretSettingStatus`).

## ADR-1: Config Files Are Parsed as JSON5 with `pyjson5`

**Status:** Maintainer, answer 1 (Matt, 2026-11-19: "JSON5 library"). Implemented by Story 23.1; the strict rule for `serverconfig.json` (decision 5) by Story 23.4.

**Decision:**

1. One parser, `parse_config_text(text: str, *, strict: bool = False) -> ParsedConfig`, in a new module `services/config_parse.py`. With `strict=False` it parses with `pyjson5.decode(text, maxdepth=CONFIG_FILE_MAX_DEPTH)`, which accepts comments, trailing commas, single-quoted strings, unquoted keys, hexadecimal numbers and leading `+`. With `strict=True` it uses `json.loads`. The viewer, the write path, the check endpoint and the restore all call it, and nothing else in the API parses config files.
2. A failed parse gives a `ConfigParseError` with a message and, when it can be found, a 1-based `line` and `column`, computed from the character offset. Story 23.1 Task 1 finds out how `pyjson5` exposes the offset: an attribute, `args`, or only the `near N` text. A test pins it. If the offset can only be read from the message, the regular expression lives in one function, and if it does not match, the error is returned without a position rather than failing.
3. `maxdepth=CONFIG_FILE_MAX_DEPTH` replaces the depth walk after parsing (`_nesting_depth_exceeds` is removed, along with its tests, in the same commit). Too deep a file still gives the message "Nested more than 200 levels deep". `strict=True` keeps the walk, because `json.loads` has no depth limit of its own.
4. A parsed value holding `Infinity`, `-Infinity` or `NaN` is a parse failure with the message "Infinity and NaN cannot be shown" (no position). The API never builds a response that fails to serialize. Python's long-integer `ValueError` keeps its fixed message.
5. `serverconfig.json` in the server data root (the resolved path equals `serverdata_dir / "serverconfig.json"`, compared with `casefold()` on the name) is checked with `strict=True` when it is saved (ADR-4) or restored (ADR-7). Other services read it with strict JSON (Facts). The viewer still reads it leniently, so a hand-edited copy with comments can at least be seen.
6. The leniency is the viewer's, not a promise about the game. JSON5 and Newtonsoft differ in a few places. For example, Newtonsoft accepts `undefined`, and JSON5 accepts multi-line strings with escaped newlines. The README's file browser section says that a file the editor accepts may still be refused by the game or a mod.
7. `pyjson5` is a new runtime dependency (answer 1), with a lower bound of `>=2.0.1,<3`. It is a `build(api)` commit with no release note.

## ADR-2: The Read Returns the Text for Admin, and the Viewer Shows Unparseable Files as Text

**Status:** Planner, from `VSS-ato4`'s proposal. Implemented by Story 23.1.

**Decision:**

1. `GET /config/files/{filename}` keeps `filename` and `content` unchanged (parsed and redacted for Monitor; `_raw`/`_parse_error` when it does not parse). Additive fields:
   - `parseError`: `null`, or `{message, line, column}` (`line` and `column` null when unknown). It repeats `_parse_error` with a position, so the web does not have to read the content's keys.
   - For Admin only: `text`, the file as stored after UTF-8 decoding with a leading byte order mark dropped, and `version`, the SHA-256 hex digest of the file's bytes as read, BOM included. Monitor gets neither field. The text may hold secrets in comments or in unparseable content, and the hash is of no use without the right to save.
2. A file that parses goes through `redact_secrets` for roles other than Admin, as it does today. A commented file is therefore redacted key by key instead of hidden entirely. Its comments never reach Monitor, because Monitor gets only the parsed `content`.
3. The web's `FileViewer` handles `parseError`. It shows a warning, "This file could not be parsed: {message} (line L, column C)". Below the warning, Admin sees the text as plain monospace with no highlighting, and Monitor sees "The text of a file that cannot be parsed is shown only to an Admin key." The web type `ConfigFileContentData` gains the new fields.
4. Until Story 23.5, a file that parses is still shown as the highlighted parsed content for every role, as today. Story 23.5 shows Admin the text with its comments (ADR-5 decision 7).
5. **Found in Story 23.1's creation:** the web client's `apiClient` renames every key of every response from snake_case to camelCase (`web/src/api/client.ts:53-66`), so keys inside a config file's `content` are renamed in the viewer (`spawn_rate` shows as `spawnRate`; the fallback arrives as `Raw` and `ParseError`, the bead's "escaped blob"). The read is fetched without that transform (`transformResponse: false`), and `fetchConfigFileContent` maps the envelope's own keys (`parse_error` to `parseError`). The response keys stay snake_case like every other API response.

**Results (Story 23.1 creation, `pyjson5` 2.0.1 on CPython 3.14):** the position of an error is only in the message, as `near N`, where N is the 1-based character position of the offending character (for extra data, of the last character consumed). `Infinity` and `NaN` decode to floats, so decision 4 of ADR-1 is needed. `1e400` and a 5,000-digit integer are refused as unclosed numbers. Depth over `maxdepth` raises `Json5NestingTooDeep` for 201 and 100,000 levels without a `RecursionError`. A 2 MB file parses in about 20 ms.

## ADR-3: The File Browser Carries Paths as Lists of Names

**Status:** Planner, from `VSS-o8s`'s suggestion (pulled in by the maintainer, 2026-11-19). Implemented by Story 23.2.

**Decision:**

1. `FileManagerPanel` holds the current directory as `string[]` (`[]` is the root) and the selected file as `{ directory: string[]; name: string } | null`. `PathBreadcrumb` takes `segments: string[]` and calls `onNavigate(segments.slice(0, n))`. Nothing in the panel or the breadcrumb splits or joins on `/`.
2. One helper, `toConfigPath(segments: string[]): string` in `web/src/api/config.ts`, joins the names with `/` for the API. It is the only place a path string is built. It throws on a name that is empty, `.` or `..`, or that contains `/` or a NUL character. Such a name cannot come from a POSIX directory listing, and if one ever did, it is never sent. The fetch functions keep `encodeURIComponent` of the joined path (the route's `{filename:path}` decodes `%2F`) and take `string[]`.
3. The TanStack Query keys for directories, files and file content use the names joined with `/` (`segments.join('/')`), so cached entries stay comparable. **Amended in Story 23.2 (review LOW-3):** the keys do not call `toConfigPath`, because a key is computed during render and must not throw; the fetch refuses an invalid name, and the query shows the error. Two lists that join to the same string (`['a/b']` and `['a', 'b']`) share a key; only the refused names can produce that, and the refetch on mount corrects it (review LOW-2, accepted).
4. A `refactor(web)` commit: there is no user-visible change, so no release note.

## ADR-4: Saving a Config File Through the API

**Status:** Planner, from `VSS-glz`. The files that can be saved are the maintainer's answer 4 ("Every file Admin can read"); the strict rule for `serverconfig.json` is answer 2. Implemented by Story 23.4.

**Decision:**

1. `PUT /api/v1alpha1/config/files/{filename:path}`, Admin only (`RequireAdmin`), with the body `{ "text": string, "version": string }`. The answer is `200` with `{ filename, version }`, the new version being the hash of the bytes written. Every response, errors included, carries `Cache-Control: no-store`, as the reads do.
2. The path rules are the read's, in the read's order: `_safe_path`, the role (Admin may open every directory), a `.json` requested name, an existing regular file whose resolved name ends in `.json`. Only existing files can be saved; creating, renaming and deleting files are out of scope (404 `CONFIG_FILE_NOT_FOUND` for a missing file). The encoded body text must be at most `CONFIG_FILE_MAX_BYTES` (413 `CONFIG_FILE_TOO_LARGE`). FastAPI's body size is not otherwise limited, so the check runs on the decoded string's UTF-8 length before parsing.
3. The text must parse with `parse_config_text` (strict for the root `serverconfig.json`, ADR-1 decision 5). If it does not, the answer is 422 `CONFIG_FILE_INVALID` with `{message, line, column}` in the error detail, and nothing is written.
4. **Server state.** The save holds `ServerService._lifecycle_lock` for the whole check-and-write, through a new `ServerService.config_write()` async context manager. The lock is taken with a zero wait: if it or `_install_lock` is already held (a start, stop, restart, install or uninstall is running), the answer is 409 `CONFIG_FILE_SERVER_BUSY`. With the lock held, if `_get_runtime_state()` is `RUNNING`, `STARTING` or `STOPPING`, the answer is 409 `CONFIG_FILE_SERVER_RUNNING`. Every other state (not installed, installed, error) allows the save. A start requested during a save waits for the lock, so the game never starts on a half-written file.
5. **Version check.** The current file's bytes are hashed under the lock. If the hash differs from `version`, the answer is 409 `CONFIG_FILE_CHANGED` and nothing is written.
6. **The write.** The text is encoded as UTF-8 exactly as sent, with no normalisation of line endings or whitespace and no re-serialization. If the file on disk started with a UTF-8 byte order mark, it is written with one. The bytes go to a temporary file in the same directory (`.<name>.<random>.tmp`, opened `O_EXCL`), are flushed and `fsync`ed, get the old file's mode (`chmod`) and, when the API runs as root, its owner and group (`chown`; a failure is logged, not fatal), and are moved over the resolved path with `os.replace`. The directory is then `fsync`ed. On any failure the temporary file is removed and the original is untouched (500 `CONFIG_FILE_WRITE_FAILED`, with no path or `str(e)` in the response).
7. **Story 22.7's pending edits** (answer 2). A save of the root `serverconfig.json` drops each pending edit whose key the saved text sets to a different value from the file it replaces. The admin changed that key on purpose, so the write-back must not undo it. Keys the save leaves alone stay pending. This uses Story 22.7's existing drop path, with a new reason `"file_edited"` added to `DropReason`.
8. A save does not set "Restart required": the game is stopped, and the next start reads the file.
9. Logging: `config_file_saved` with the relative path, the byte size and both versions, and never the text. Refusals log their reason at INFO.
10. **The check endpoint** (maintainer, answer 5: "API check endpoint"). `POST /api/v1alpha1/config/files/validate`, Admin only, body `{ "filename": string, "text": string }`. It answers `200` with `{ valid: bool, error: {message, line, column} | null }`. It applies the path rules of decision 2, minus the existence check, the size limit and the parser rule of decision 3 (strict for `serverconfig.json`). It writes nothing, takes no lock and ignores the server state. A path the save would refuse gives the same 400 or 403 as the save. Static and greedy routes are matched in order, so the route is declared before `PUT /files/{filename:path}`. The methods differ anyway, but the order is kept explicit.

## ADR-5: The Editor Is CodeMirror 6, in the File Viewer

**Status:** Maintainer, answer 3 ("CodeMirror 6"); the check-as-you-type is answer 5 ("API check endpoint"). The layout and flow are the planner's. Implemented by Story 23.5.

**Decision:**

1. **Packages:** `@codemirror/state`, `@codemirror/view`, `@codemirror/commands`, `@codemirror/language`, `@codemirror/search` and one language package for highlighting. Story 23.5 Task 1 picks between `@codemirror/lang-json` and `@codemirror/lang-javascript` (JSON5 is a JavaScript subset). It keeps whichever highlights `seasonalflowers.json`'s comments and trailing commas without error marks. No package outside the `@codemirror` scope and no `codemirror` bundle (`basicSetup`): the extensions are listed one by one, so the bundle stays small and auditable. The editor code is loaded with a dynamic `import()`, so it does not grow the main bundle. The build's chunk report in the story's completion notes shows the size.
2. **CSP:** CodeMirror injects `<style>` elements, which `style-src 'unsafe-inline'` allows. It needs no worker and no `eval`. The CSP string does not change. An E2E check opens the editor with the CSP enforced and asserts that no CSP violation was reported.
3. **Edit button:** In the `FileViewer` header, next to the word-wrap toggle, shown only when the role is Admin (`useAuthMe`, ADR-6 decision 3) and the file parsed or was read with `text` present. While the game server state is not stopped (`useServerStatus`: running, starting or stopping, or a lifecycle operation in progress), the button is disabled. A line below it says "Stop the game server to edit files: the game can overwrite changes made while it runs." and links to the page with the server controls.
4. **Edit mode:** The viewer is replaced by the editor, holding the `text` from the read. Save and Cancel buttons sit in the header. A status line below the editor shows the latest check from `POST /config/files/validate`: "Valid", or the message with line and column, and a click moves the cursor there. The check runs 500 ms after typing stops and once on opening. Save is disabled while the text is unchanged, invalid or waiting for a check, and while the server is not stopped. Buttons are at least 44px tall on phones.
5. **Save:** `PUT` with the read's `version`. A 200 shows a toast ("Saved serverconfig.json"), leaves edit mode and refetches the file. A 409 `CONFIG_FILE_CHANGED` keeps the text and shows "The file changed on disk since you opened it." with a Reload action, which discards the edits after a confirmation. There is no merge. A 409 `CONFIG_FILE_SERVER_RUNNING` or `CONFIG_FILE_SERVER_BUSY` keeps the text and explains. A 422 shows the error in the status line.
6. **Unsaved changes:** Leaving edit mode with changes (Cancel, choosing another file or directory, the breadcrumb, another settings tab or another route) asks for confirmation in an `AlertDialog`. React Router's `useBlocker` covers route changes and a `beforeunload` listener covers closing the tab. With no changes, nothing asks.
7. **View mode for Admin:** A file whose read has `text` and that parsed is shown as the text, with its comments, in a read-only CodeMirror view using the same highlighting. The word-wrap toggle maps to `EditorView.lineWrapping`. Monitor keeps the highlighted parsed content (`highlightJson`), because Monitor never receives the text. An unparseable file keeps ADR-2 decision 3's plain view.

## ADR-6: Role-Gated Controls Use One Hook, and Game Settings Are Read-Only for Monitor

**Status:** Maintainer, answer 8 ("Disabled fields + note"). The hook is the planner's. Implemented by Story 23.3; Story 23.5 uses the hook.

**Decision:**

1. `GameConfigPanel` passes `disabled` to every `SettingField` unless the role is Admin. One note at the top of the panel, "Only an Admin key can change settings.", is shown when the role is known and is not Admin. `SecretSettingStatus` for Password (Story 17.5) is unchanged. Switches and inputs keep their values and their labels, and a disabled field never sends a request.
2. While the role is loading, fields are disabled and no note is shown. If `GET /auth/me` fails, fields stay disabled and the note reads "Could not check this key's role; settings cannot be changed until it loads." The API enforces the role either way; this rule only stops the 403 after typing.
3. A hook `useIsAdmin(): { isAdmin: boolean; isKnown: boolean; isError: boolean }` in `web/src/api/hooks/use-auth-me.ts` wraps `useAuthMe`. Game Settings, the file browser's note (Story 19.1) and the Edit button (ADR-5 decision 3) use it. `SettingsPage`'s tab hiding (Epic 22 ADR-12) moves to it too, in the same commit, with behaviour unchanged.
4. A `fix(web)` commit (users notice it): "show game settings read-only to Monitor keys".

## ADR-7: Saved Config Files Keep Their Earlier Versions

**Status:** Planner, from `VSS-hb4d`. Retention settings are the maintainer's answer 6 ("API settings"). Implemented by Story 23.6.

**Decision:**

1. **Store:** `vsmanager/state/config-history/`, outside `serverdata`, so neither the game nor mods load it. Each file has its own directory, named by the file's resolved path relative to the server data directory with each part kept as is, for example `config-history/ModConfig/seasonalflowers.json/`. Symlinked names share one history. In it, each revision is `<id>.json`, the replaced bytes exactly as they were on disk, plus one `index.json`: `{ "revisions": [ { "id", "savedAt", "savedBy", "size", "sha256" } ] }`, newest first. `index.json` is written atomically, the same way as ADR-4 decision 6.
2. **Revision id:** the UTC time of the save that replaced the text, `YYYYMMDDTHHMMSSffffffZ`, with `-2`, `-3` and so on appended on a collision. The routes accept an id only if it matches `^\d{8}T\d{12}Z(-\d+)?$` and is listed in `index.json` (no path is built from an unchecked id).
3. **What is recorded:** every successful save through `PUT` (ADR-4) or a restore (decision 6) first stores the text it replaces, then writes. `savedBy` is the caller's role (`"admin"`). The API has no user identity: keys are shared secrets, and a login is `VSS-2kdt`. Files changed by the game, mods, the Game Settings page or by hand are not recorded (the bead's scope).
4. **Failure:** if the revision or index cannot be written, the save is refused with 500 `CONFIG_HISTORY_WRITE_FAILED` and the config file is untouched, so every accepted edit can be undone. The revision is written before the config file is replaced. If the replace then fails, the orphan revision is removed again.
5. **Retention:** two API settings, `config_history_keep_count` (default 20, 1 to 200) and `config_history_max_age_days` (default 0, no age limit, 0 to 3650), saved and validated like Epic 22's settings and taking effect at the next save. After each save, that file's revisions beyond the newest `keep_count`, and those older than `max_age_days` when it is above 0, are deleted. The newest revision is never deleted by age. Lowering a setting prunes nothing until the file is next saved; there is no job. Pruning failures are logged and do not fail the save.
6. **Routes** (Admin only, `Cache-Control: no-store`; the path rules of ADR-4 decision 2, except that the file need not exist for the two reads):
   - `GET /api/v1alpha1/config/history/{filename:path}` returns `{ filename, revisions: [...] }`, newest first. A file with no history gives an empty list.
   - `GET /api/v1alpha1/config/history/{filename:path}?revision=<id>` returns `{ filename, revision: {...}, text }`. An unknown id is 404 `CONFIG_REVISION_NOT_FOUND`.
   - `POST /api/v1alpha1/config/history/{filename:path}/restore`, body `{ revision, version }`, goes through the save path with the revision's text. It has the same server-state lock, version check, parser rule and pending-edit handling as a save. It records the current text as a new revision first and answers like `PUT`. A revision that does not parse under the save's rule cannot be restored (422 `CONFIG_FILE_INVALID`); it can still be read and copied.
7. A `feat(api)` commit: "keep earlier versions of config files saved through the API, and restore them".

## ADR-8: History, Comparison and Restore in the File Browser

**Status:** Maintainer, answer 7 ("CodeMirror merge view"); the layout is the planner's. Implemented by Story 23.7.

**Decision:**

1. A History button in the `FileViewer` header (Admin only) opens a panel listing the file's revisions: local time, relative time ("3 hours ago"), saved by and size. An empty history says "No earlier versions. Versions are kept when the file is saved here."
2. Choosing a revision shows it compared with the current text using `@codemirror/merge`: side by side (`MergeView`) from the `md` breakpoint up, and unified (`unifiedMergeView`) below it. Both are read-only. A "Show this version" toggle shows the revision's text alone.
3. **Restore:** with the server stopped (ADR-5 decision 3's rule and message), a Restore button asks for confirmation ("Replace the current file with the version from {time}? The current text is kept in the history.") and calls the restore route with the current version. The outcomes and 409s are handled as for a save (ADR-5 decision 5). While the editor has unsaved changes, History is disabled with the reason "Save or cancel your changes first".
4. **API Settings:** a "Config History" group in the API Settings tab with the two fields of ADR-7 decision 5 (`SettingField`, the API's bounds). The help text says that history is kept only for files saved in the file browser, and that a lower limit applies at a file's next save.
5. `@codemirror/merge` loads with the editor's dynamic import.
6. A `feat(web)` commit: "see, compare and restore earlier versions of config files".

## ADR-9: Tests Never Edit the Dev Stack's Files

**Status:** Planner, from the project rule that tests and manual checks do not change the dev stack's game server (Epic 22 ADR-14).

**Decision:**

1. API tests use `tmp_path` server data and a stubbed `ServerService` state, and cover each refusal of ADR-4 and ADR-7 with its own test: role, path traversal, a non-`.json` name, a missing file, size, an invalid body, strict `serverconfig.json`, running, starting, stopping, a busy lock, a stale version, a write failure, a history write failure, an unknown revision id and a malformed revision id.
2. A concurrency test shows that a start requested during a save waits until the save ends (a stub start awaiting the lock).
3. Web unit tests mock the API. The E2E checks that save or restore a file run only against the CI set's throwaway container (`just test-e2e-ci`, game not started). The check creates its own `ModConfig/e2e-<random>.json` with `docker exec`, before the run, and removes it afterwards. It never touches a file it did not create, and it never runs against the dev stack on port 9080. Read-only E2E checks (viewer, a disabled Edit button, Monitor's read-only Game Settings) may run against either.
4. Fixtures: a copy of `ModConfig/seasonalflowers.json`'s shape (line comments, a comment after the last property, `null` in arrays) and a `//` inside a string value, written by the test, not taken from a live server.
