# Story 23.1: Configs with Comments Can Be Viewed

Status: ready-for-dev

<!-- Implements FR309, FR310, FR311 and FR326 (JSON5 part), Epic 23 ADR-1, ADR-2 and ADR-9. Bead: VSS-ato4 (API-097), closed by this story after merge. Branch story/23-1-configs-with-comments-can-be-viewed from main at fc525885 with the epic's planning commit f759ee24. Line references verified at f759ee24. -->

## Story

As an **administrator**,
I want **the file browser to show mod configs that have comments**,
so that **I can read the configs the game itself accepts instead of a parse error**.

## Acceptance Criteria

1. **Given** a `ModConfig` file with `//` line comments, a `/* */` block comment, a comment after the last property, a trailing comma, `null` in an array and a string value `"http://example.com//path"`
   **When** an Admin key and a Monitor key read it
   **Then** both get the parsed `content` and the string keeps its `//`; Monitor's content is redacted key by key (a `password` key reads `"[redacted]"`, other values unchanged)
   *(FR309; ADR-1 decisions 1 and 3, ADR-2 decision 2)*

2. **Given** a file with single-quoted strings, unquoted keys and a hexadecimal number
   **When** it is read
   **Then** it parses
   *(FR309; ADR-1 decision 1)*

3. **Given** a file nested 201 levels (and 100,000 levels), and a file holding `Infinity`, `-Infinity` or `NaN`
   **When** they are read
   **Then** each answers 200 with the `_raw`/`_parse_error` content and a `parse_error` (`"Nested more than 200 levels deep"`, `"Infinity and NaN cannot be shown"`), never a 500
   *(FR309; ADR-1 decisions 3 and 4)*

4. **Given** a file with a missing comma before line 3's key
   **When** an Admin key reads it
   **Then** `parse_error` is `{message, line: 3, column}` (the column of the unexpected character); `content` keeps `_raw` (the text) and `_parse_error` (the same message); `text` is the text and `version` is the SHA-256 hex digest of the bytes. For a Monitor key `_raw` is `"[redacted]"`, `parse_error` is the same, and there is no `text` or `version`
   *(FR310, FR311; ADR-1 decision 2, ADR-2 decision 1)*

5. **Given** a file that parses (with a leading byte order mark)
   **When** an Admin key reads it
   **Then** `text` is the file's text with its comments and without the BOM, `version` is the SHA-256 of the bytes as read (BOM included), and `parse_error` is null; a Monitor key gets `parse_error: null` and neither `text` nor `version`
   *(FR311; ADR-2 decision 1)*

6. **Given** a config file whose keys contain underscores (`spawn_rate`, `_comment`)
   **When** it is shown in the file browser
   **Then** the keys are shown as in the file (the web client does not rename keys inside `content`)
   *(FR309; ADR-2 decision 5, found in story creation)*

7. **Given** a file that does not parse
   **When** it is opened in the file browser
   **Then** a warning shows "This file could not be parsed: {message} (line L, column C)" (without the position part when it is unknown); Admin sees the text below it in plain monospace, without highlighting; Monitor sees "The text of a file that cannot be parsed is shown only to an Admin key."
   *(FR310; ADR-2 decision 3)*

8. **Given** the README
   **When** an operator reads the file browser section
   **Then** it says that config files are read as JSON5 (comments, trailing commas, single quotes, unquoted keys), that a file the viewer accepts may still be refused by the game or a mod, and that a file that cannot be parsed shows where the error is
   *(FR326; ADR-1 decision 6)*

9. **(Quality gates, as every Epic 22 story.)** `just check` is green with 0 skipped tests and Pyright 0 errors, 0 warnings; no added line holds a lint or type suppression, a `cast`, a skip or `.only`; no test reads or writes `dev/` or `./data`.

## Tasks / Subtasks

<!-- Each code task includes its tests in the same commit, red first. Subjects: type(story-23.1/task-N): ..., the type chosen by what an admin notices. User-visible commits: Task 3 (fix(api)) and Task 4 (fix(web)). -->

- [x] Task 1: Add `pyjson5` + a test pinning its error shape (AC: 4, 9)
  - [x] 1.1: `cd api && uv add "pyjson5>=2.0.1,<3"` (no `just` recipe adds a dependency; precedent Story 22.2 Task 1). `api/pyproject.toml` gains exactly that line in alphabetical order; `api/uv.lock` gains `pyjson5` 2.0.x and no other version changes
  - [x] 1.2: In the new `api/tests/test_config_parse.py`, a test that pins what Dev Notes "pyjson5 facts" records: a `Json5DecoderException` subclass, `.message` ending in `near N` with N the 1-based character position of the offending character, and `Infinity` decoding to `inf` (so the API must refuse it)
  - [x] 1.3: Commit `build(story-23.1/task-1): add the pyjson5 dependency`

- [x] Task 2: `services/config_parse.py` + tests (AC: 1, 2, 3, 4, 9)
  - [x] 2.1: Red first: the parser rows of Dev Notes "API tests" in `api/tests/test_config_parse.py`; see them fail
  - [x] 2.2: The module of Dev Notes "The parser"
  - [x] 2.3: `just test-api tests/test_config_parse.py`; `just typecheck-api` 0/0; `just lint-api`
  - [x] 2.4: Commit `refactor(story-23.1/task-2): add a JSON5 parser for config files`

- [x] Task 3: `read_file` uses it and returns `parse_error`, `text`, `version` + tests (AC: 1-5, 9)
  - [x] 3.1: Red first: the service and router rows of Dev Notes "API tests"; update the tests whose expectations change (Dev Notes "Existing tests that change"); see them fail
  - [x] 3.2: `services/config_files.py` as in Dev Notes "The read"; remove `_nesting_depth_exceeds`, `_is_json_object`/`_is_json_array` if no longer used, and `import json` if unused; update the module and method docstrings and the router docstring (`routers/config.py`, `read_config_file`)
  - [x] 3.3: `just test-api`; `just typecheck-api` 0/0; `just lint-api`
  - [x] 3.4: Commit `fix(story-23.1/task-3): show mod configs that contain comments` (body: Story 23.1 / task 3; config files are read as JSON5, like the game's own reader accepts comments and trailing commas; an Admin read also returns the text and a version; unparseable files report the line and column)

- [ ] Task 4: The web: untransformed content, the new fields, the parse-error view + tests (AC: 6, 7, 9)
  - [ ] 4.1: Red first: the rows of Dev Notes "Web tests"; see them fail
  - [ ] 4.2: `web/src/api/client.ts`, `web/src/api/config.ts`, `web/src/api/types.ts`, `web/src/components/FileViewer.tsx`, `web/src/features/settings/FileManagerPanel.tsx` as in Dev Notes "The web"
  - [ ] 4.3: `just test-web`; `just typecheck-web`; `just format-web` then `just lint-web`
  - [ ] 4.4: Commit `fix(story-23.1/task-4): show a config file that cannot be parsed as text, with where the error is` (body: Story 23.1 / task 4; also stops the viewer renaming keys with underscores inside a config file)

- [ ] Task 5: README (AC: 8)
  - [ ] 5.1: A `### Config files` section after `### Logs and disk use` (`README.md:118`) and before `### Metrics` (`:155`), text in Dev Notes "Documentation"
  - [ ] 5.2: Commit `docs(story-23.1/task-5): explain how the file browser reads config files`

- [ ] Task 6: Validate and move the story to review (AC: all)
  - [ ] 6.1: `just check` green (API, web with 0 skipped, scripts, Pyright 0/0). Added lines hold no `type: ignore`, `pyright:`, `noqa`, `cast(`, `eslint-disable`, skip, `xfail` or `.only`. `git status --short dev/ data/` empty
  - [ ] 6.2: `just changelog` shows exactly this story's two fix entries (Tasks 3 and 4)
  - [ ] 6.3: Manual check (maintainer only; leave unticked until he confirms): after this story is deployed, `ModConfig/seasonalflowers.json` opens in the file browser on his server as parsed content (Admin and Monitor), not a parse error. No agent writes to the dev stack or a live server for this story
  - [ ] 6.4: Status `review` here; `just sprint set 23-1-configs-with-comments-can-be-viewed review`; Dev Agent Record and File List filled in
  - [ ] 6.5: Commit `chore(story-23.1/task-6): validate and move story 23.1 to review`

## Dev Notes

### The code today (verified at f759ee24)

Paths under `api/src/vintagestory_api/` unless stated.

- `services/config_files.py`: `CONFIG_FILE_MAX_BYTES` (`:45`), `CONFIG_FILE_MAX_DEPTH = 200` (`:52`), `_is_json_object`/`_is_json_array` (`:126-133`, used only by `_nesting_depth_exceeds`), `_nesting_depth_exceeds` (`:136-155`), `read_file` (`:331-454`): path, role, suffix, existence, regular file, size, read bytes, `decode("utf-8-sig")` (`:422-425`), then `json.loads` (`:429`) with three fallbacks (`JSONDecodeError`/`RecursionError`, other `ValueError`, depth) building `{"_raw": text if admin else REDACTED, "_parse_error": msg}`; otherwise `redact_secrets` for non-Admin (`:452-453`). Returns `{"filename", "content"}`.
- `routers/config.py`: `read_config_file` (`:529-620`) returns `ApiResponse(status="ok", data=result)`. The docstring lists the `_raw`/`_parse_error` behaviour.
- `services/game_config.py`: `REDACTED`, `redact_secrets` (`:318`).
- The web client (`web/src/api/client.ts:53-66`, `:166-199`): `apiClient` runs `snakeToCamel` over the whole response, so **keys inside a config file's `content` are renamed** (`spawn_rate` shows as `spawnRate`; `_raw` and `_parse_error` arrive as `Raw` and `ParseError`, which is the "escaped blob under Raw/ParseError keys" in the bead). Found in story creation; fixed here (AC 6).
- `web/src/api/config.ts:228-234` `fetchConfigFileContent`; `web/src/api/types.ts:364-367` `ConfigFileContentData { filename; content: unknown }`.
- `web/src/components/FileViewer.tsx` (157 lines): props `filename`, `content`, `isLoading`, `error`, `wordWrap`, `onWordWrapChange`, `className`; renders `highlightJson(content)` for `.json` names.
- `web/src/features/settings/FileManagerPanel.tsx:186-195` passes `fileContent?.data.content` to `FileViewer`, and has the role from `useAuthMe` (`:58-60`).

### pyjson5 facts (checked in story creation with 2.0.1 on CPython 3.14)

- `pyjson5.decode(text, maxdepth=200)` accepts `//` and `/* */` comments, trailing commas, single-quoted strings, unquoted keys, hex (`0x1F`), `+1`, `.5`, multi-line strings with an escaped newline, a leading BOM; duplicate keys: last wins (as `json.loads`). Arbitrary-size integers (30 digits) parse. A 2 MB document parses in about 20 ms.
- `Infinity`, `-Infinity`, `NaN` decode to `float` inf/nan. `1e400` is refused (`Json5EOF`, "Unclosed b'NumericLiteral'..."). A 5,000-digit integer is refused the same way. Lone surrogate escapes (`"\ud800"`) are refused.
- Errors: all subclasses of `pyjson5.Json5DecoderException` (`Json5NestingTooDeep`, `Json5EOF`, `Json5IllegalCharacter`, `Json5ExtraData`, `Json5IllegalType`). `.message` is the text; the position is only inside it as `near N`. N is the **1-based character (code point) position** of the offending character: for `'{"a": 1\n "b": 2}'` the `"` of `"b"` is at index 9 and the message says `near 10`; the same with non-ASCII before it and with `\r\n`. For `Json5ExtraData` N is the position of the last character consumed (so the error points at the end of the value before the junk), and for `Json5EOF` "starting near N" is where the unclosed token began. Messages hold Python byte reprs: `Expected b'comma' or U+007d near 12, found U+0022`.
- Depth over `maxdepth`: `Json5NestingTooDeep` with `Maximum nesting level exceeded near N`, for 201 and for 100,000 levels (no `RecursionError`).
- Typed: the wheel ships `__init__.pyi`; check Pyright accepts it (Task 1).

### The parser (Task 2): `services/config_parse.py`

```python
@dataclass(frozen=True)
class ParseErrorInfo:
    message: str
    line: int | None   # 1-based
    column: int | None # 1-based, in characters

    def to_dict(self) -> dict[str, object]  # {"message", "line", "column"}

class ConfigParseError(Exception):  # .info: ParseErrorInfo; str() is the message

def parse_config_text(text: str, *, strict: bool = False) -> object
def line_and_column(text: str, index: int) -> tuple[int, int]
```

- **Lenient** (`strict=False`): `pyjson5.decode(text, maxdepth=CONFIG_FILE_MAX_DEPTH)`. On `Json5NestingTooDeep`: message `f"Nested more than {CONFIG_FILE_MAX_DEPTH} levels deep"`, no position. On any other `Json5DecoderException`: the position from `near (\d+)` (one function, `_offset_from_message`; when it does not match, `line`/`column` are None) as index `N - 1` clamped to `[0, len(text)]`; the message cleaned by one function: remove ` near \d+` / ` starting near \d+` and turn `b'word'` into `word` (so `Expected comma or U+007d, found U+0022`). Never put file text into the message beyond what pyjson5 puts there (it names single characters only).
- **Strict** (`strict=True`, used from Story 23.4): `json.loads(text)`; `JSONDecodeError` -> message `e.msg`, `line=e.lineno`, `column=e.colno`; `RecursionError` -> the depth message; other `ValueError` (the long-integer limit) -> the fixed message from `config_files.py:443-446` ("A value in the file could not be converted (for example, a number with too many digits)"), no position; then the depth walk (`_nesting_depth_exceeds`, moved here from `config_files.py`).
- **Both modes**, after a successful parse: one iterative walk (no recursion) that raises `ConfigParseError("Infinity and NaN cannot be shown")` for any non-finite `float` (`math.isfinite`), and in strict mode also the depth error. Keep the walk in this module; `CONFIG_FILE_MAX_DEPTH` moves here and `config_files.py` imports it (keep its name importable from `config_files` too, tests import it from there).
- `line_and_column(text, index)`: line = `text.count("\n", 0, index) + 1`; column = `index - (text.rfind("\n", 0, index) + 1) + 1`. A `\r` before `\n` is counted as part of the previous line's text (column stays right for the next line).
- `ParseErrorInfo` is what the read, and later the save and the check endpoint, return.

### The read (Task 3)

In `read_file`, after decoding the text:

```python
reveal = role == UserRole.ADMIN
parse_error: ParseErrorInfo | None = None
try:
    content = parse_config_text(text)
except ConfigParseError as e:
    parse_error = e.info
    logger.warning("config_file_json_invalid", filename=filename, error=e.info.message)
    content = {"_raw": text if reveal else REDACTED, "_parse_error": e.info.message}
else:
    if not reveal:
        content = redact_secrets(content)
result: dict[str, object] = {
    "filename": filename,
    "content": content,
    "parse_error": parse_error.to_dict() if parse_error else None,
}
if reveal:
    result["text"] = text
    result["version"] = hashlib.sha256(data).hexdigest()
```

- The `version` hashes `data` (the bytes read, BOM included), not the text. The same function will be used by Story 23.4: put it in `config_files.py` as `content_version(data: bytes) -> str`.
- Keys are snake_case like every other API response (`parse_error`); the web maps them (Task 4).
- The response's existing `_raw`/`_parse_error` stay for compatibility.

### Existing tests that change (Task 3)

- `api/tests/test_config_files.py::TestReadFile::test_read_file_success` asserts the exact dict: now `{"filename", "content", "parse_error": None}` with no role (None is not Admin).
- `test_deeper_nesting_is_raw` (`:441`): for 100,000 levels the message is now also "Nested more than 200 levels deep" (pyjson5 raises `Json5NestingTooDeep`); the assertion only pins it for 201, keep it and add the 100,000 case to the pin.
- `TestReviewFixes::test_integer_too_long_is_raw` (`:739`): the 5,000-digit integer is still the `_raw` form, now through pyjson5's `Json5EOF`; the assertion that no 50-digit run is in the message still holds. Keep it.
- `api/tests/test_routers_config.py` rows that compare whole `data` objects for reads (search `"content"` with `==` on `data`): add the new keys. The deep-nesting (`:1586`) and long-integer (`:1837`) router tests keep passing.

### API tests (new)

`api/tests/test_config_parse.py`:
- Task 1: the pinned pyjson5 facts above (exception class, `near N` for `'{"a": 1\n "b": 2}'` is 10, `Infinity` -> inf).
- Lenient: the AC 1 fixture (ADR-9 decision 4: line comments, a block comment, a comment after the last property, a trailing comma, `null` in an array, `"http://example.com//path"`) parses to the expected dict; single quotes, unquoted keys, hex (AC 2); `ConfigParseError` for the missing comma with line 3 and the column of `"`; the same with `\r\n` line ends and with non-ASCII text before the error; empty text -> an error with a position; extra data -> an error; 201 levels and 100,000 levels -> the depth message, no position; `Infinity`, `-Infinity`, `NaN` at depth 1 and nested in an array -> "Infinity and NaN cannot be shown"; the cleaned message has no `near` and no `b'`.
- Strict: comments refused with line and column from `json.loads`; valid JSON parses; 201 levels -> depth message; the long-integer `ValueError` -> the fixed message; `NaN` (which `json.loads` accepts) -> the Infinity/NaN message.
- `line_and_column` unit rows: index 0, after `\n`, after `\r\n`, at the end.

`api/tests/test_config_files.py` (new class `TestJson5Read`, parametrised over Admin and Monitor where it matters): AC 1 (with a `password` key and a `"[redacted]"` check for Monitor), AC 2, AC 3 (`Infinity`), AC 4 (Admin and Monitor shapes), AC 5 (BOM, text without BOM, version of the bytes with BOM via `hashlib.sha256`).

`api/tests/test_routers_config.py`: one router test per role for AC 4 and AC 5 over HTTP (the response JSON has `parse_error`, and `text`/`version` only for Admin), and one for AC 3 (`Infinity` answers 200, not 500).

### The web (Task 4)

- **`apiClient` option.** Add `transformResponse?: boolean` (default true) to `ApiClientOptions`; when false, the parsed JSON is returned as is. Strip it from the options passed to `fetch` (it is not a `RequestInit` field). Test in `client.test.ts`.
- **`fetchConfigFileContent`** calls `apiClient` with `{ transformResponse: false }` and maps the raw response to `ApiResponse<ConfigFileContentData>`: `status`, and `data: { filename, content, parseError: raw.parse_error ?? null, text?: raw.text, version?: raw.version }` (`content` untouched). Validate shapes defensively: a missing `parse_error` is `null`, a non-string `text` is dropped. Tests in `config.test.ts`: keys with underscores in `content` are kept; `parse_error` maps; `text`/`version` present or absent.
- **`types.ts`:** `export interface ConfigParseError { message: string; line: number | null; column: number | null }`; `ConfigFileContentData` gains `parseError: ConfigParseError | null; text?: string; version?: string`.
- **`FileViewer`:** new optional props `parseError?: ConfigParseError | null` and `text?: string`. When `parseError` is set: a warning block (`role="alert"`, the amber/warning style used elsewhere in the app for warnings, `AlertTriangle` icon), text `This file could not be parsed: {message}` plus ` (line {line}, column {column})` when both are numbers; below it, when `text` is a string, `<pre data-testid="file-viewer-raw">` with the text, honouring word wrap; otherwise the sentence "The text of a file that cannot be parsed is shown only to an Admin key." The header (filename, word-wrap toggle) is unchanged. With `parseError` null or undefined, behaviour is exactly as today.
- **`FileManagerPanel`:** pass `parseError={fileContent?.data.parseError}` and `text={fileContent?.data.text}`.

### Web tests (Task 4)

- `client.test.ts`: `transformResponse: false` returns keys untouched and does not pass the option to `fetch`.
- `config.test.ts`: the mapping rows above (update the existing `fetchConfigFileContent` rows, which expect `apiClient` called with one argument).
- `FileViewer.test.tsx`: warning with position; warning without position; Admin text shown in `file-viewer-raw`, no highlighting classes; Monitor sentence when `text` is undefined; word wrap applies to the raw view; without `parseError` the existing rows pass unchanged.
- `FileManagerPanel.test.tsx`: the panel passes `parseError` and `text` through (one row).

### Documentation (Task 5)

`### Config files` in README.md: The Settings page's file browser shows the `.json` files in the server's data directory (Admin keys see every folder; Monitor keys the top level and `ModConfig`, with secrets hidden). Files are read as JSON5, the relaxed JSON the game's own reader accepts: comments (`//`, `/* */`), trailing commas, single-quoted strings and unquoted keys. JSON5 and the game's reader differ in small ways, so a file the viewer reads may still be refused by the game or a mod; check the server log after a change. A file that cannot be read shows the parser's message with the line and column; an Admin key also sees its text. Keep it short; Stories 23.5 and 23.6 add editing and history to this section.

### Testing rules

- `tmp_path` server data only (the existing fixtures); no test touches `dev/` or `./data` (ADR-9).
- Red first for each task; run the narrow tests, then `just check` in Task 6.

### Project Structure Notes

- New: `api/src/vintagestory_api/services/config_parse.py`, `api/tests/test_config_parse.py`.
- Changed: `api/pyproject.toml`, `api/uv.lock`, `services/config_files.py`, `routers/config.py` (docstring), API tests; `web/src/api/client.ts`, `config.ts`, `types.ts`, `components/FileViewer.tsx`, `features/settings/FileManagerPanel.tsx` and their tests; `README.md`.

### References

- `_bmad-output/planning-artifacts/epics.md` "Story 23.1"; `architecture/epic-23-config-file-editing.md` ADR-1, ADR-2, ADR-9
- `_bmad-output/project-context.md` (commit format, testing rules, no suppressions)
- Story 19.1 (`19-1-secrets-stay-with-admin.md`) for the read's rules and redaction

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
