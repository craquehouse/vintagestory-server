# Story 19.1: Secrets Stay with Admin

Status: done

<!-- Implements FR205-FR209 and FR233, Epic 19 ADR-1, ADR-2, ADR-3 (decision 9: the Monitor note) and ADR-4. Beads: VSS-633 (API-077, bug, P2), VSS-sg1 (API-078, bug, P3), VSS-3hs2 (API-089, P3), VSS-ms0 (API-070, P3); parent VSS-fl9b. First story of Epic 19 (stories run in order 19.1 to 19.7, each stacked on the previous). Line references were verified at b6ae2f2 (epic-19-planning; its api/ and web/ match 048fea9, the commit the ADRs cite) and must be re-checked at implementation time. API change, one small web change (the note), documentation and configuration files. No new dependencies. -->

## Story

As an **operator who gives other people Monitor access**,
I want **secrets and player data to reach only the Admin role**,
so that **read-only access stays read-only**.

## Acceptance Criteria

1. **Given** a `.json` file in the root of the server data directory or under `ModConfig`
   **When** I request `GET /api/v1alpha1/config/files/{path}` with an Admin or a Monitor key
   **Then** the response is 200 with its content; and `GET /config/files` for a directory lists exactly the files that pass the viewer's file rule for that key's role (a regular file whose requested and resolved names end in `.json`, any letter case, resolving inside the server data directory, in a directory the role may read). A file in that list that is larger than 2 MiB or not UTF-8 text is still listed, and reading it gives the error of AC 4 or AC 3
   *(Covers FR205; `VSS-633`)*

2. **Given** a path whose name does not end in `.json` (`server-main.log`, `x.zip`, `notes.txt`, a name without a suffix), existing or not, in a directory the key's role may read
   **When** I request it with either key
   **Then** the response is 400 `CONFIG_FILE_NOT_SUPPORTED` with `Cache-Control: no-store`, and the file is not opened
   *(Covers FR205, FR206)*

3. **Given** a directory, a directory named `x.json`, a symlink `x.json` to a file of another type, something that is not a regular file, or a `.json` file that is not UTF-8 text (a binary file, Latin-1 text), in a directory the key's role may read
   **When** I request it with either key
   **Then** the response is 400 `CONFIG_FILE_NOT_SUPPORTED`, never a 500
   *(Covers FR206)*

4. **Given** a `.json` file larger than 2 MiB (2,097,152 bytes)
   **When** I request it with either key
   **Then** the response is 413 `CONFIG_FILE_TOO_LARGE` and the file is not read; a file of exactly 2,097,152 bytes is served
   *(Covers FR206)*

5. **Given** a `.json` file that starts with a UTF-8 byte order mark; one that is UTF-8 and not valid JSON; one nested more than 200 levels deep; and one nested so deeply that the parser gives up
   **When** I request them with either key
   **Then** the first is parsed and returned as content; each of the others is 200 with `_raw` and `_parse_error`, where `_raw` is the text for Admin and `"[redacted]"` for Monitor; none is a 500
   *(Covers FR206)*

6. **Given** a config file with `{"Other": {"Password": "x"}}`, a list of objects with `Token` or `ApiKey` keys, and keys such as `bot_token`, `WebhookUrl`, `api-key` or `Private.Key`
   **When** I read it with a Monitor key
   **Then** each of those values is `"[redacted]"` at every depth, whatever its type; a `null` or `""` value stays as it is; keys such as `Seed`, `WorldSeed` and `ServerName` are unchanged; and no secret value is anywhere in the raw response body
   *(Covers FR207; `VSS-sg1`)*

7. **Given** `serverconfig.json` with `StartupCommands` set, and a config file with a string value that is a URL with user info (`https://user:pass@host/`, also `https://user@host/`) or a Discord webhook URL (`https://discord.com/api/webhooks/...`, `https://discordapp.com/api/webhooks/...`) under any key name, at any depth
   **When** I read them with a Monitor key
   **Then** those values are `"[redacted]"`; other URLs (`https://example.com/api/webhooks/1`, `https://discord.com/channels/1`) are unchanged
   *(Covers FR207)*

8. **Given** the files of AC 6 and AC 7
   **When** I read them with the Admin key
   **Then** every value is returned unchanged; and `GET /api/v1alpha1/config/game` is unchanged for both roles
   *(Covers FR207)*

9. **Given** a Monitor key
   **When** I request `GET /api/v1alpha1/config/directories` for the root of the server data directory (no `directory`, or a `directory` that resolves to the root such as `.` or `ModConfig/..`)
   **Then** the response lists `ModConfig` when it exists and no other directory; with the Admin key it lists every directory, hidden ones included, as before. Both listing routes answer with `Cache-Control: no-store`
   *(Covers FR208; `VSS-3hs2`)*

10. **Given** a Monitor key
    **When** I request the directory listing of, the file listing of, or a `.json` file in `Playerdata`, `Saves`, `Backups`, `Logs`, `Mods` or any directory other than `ModConfig`, in any letter case, existing or not
    **Then** the response is 403 `FORBIDDEN` with the message `This directory needs the Admin role: <path>` and `Cache-Control: no-store`; the same requests with the Admin key are answered as for any directory
    *(Covers FR208)*

11. **Given** a Monitor key
    **When** I read a `.json` file in the root or anywhere under `ModConfig` (`ModConfig/a/b/c.json`), and a symlink under `ModConfig` (file or directory) that resolves into another directory such as `Playerdata`
    **Then** the first is 200 with secrets redacted, and the second is 403 `FORBIDDEN` and is not in the listing of `ModConfig`; a path that leaves the server data directory is still 400 `CONFIG_PATH_INVALID` for both keys (containment is checked before the role)
    *(Covers FR208)*

12. **Given** a Monitor key in the web UI
    **When** I open Settings, File Manager
    **Then** the file browser shows the line "Some folders are only shown to Admin keys.", which names no folder and gives no count, and it lists only what the API lists; with the Admin key, or while the role is loading or could not be loaded, the line is not shown
    *(Covers FR233)*

13. **Given** a deployment that still sets `VS_GAME_VERSION`
    **When** the API starts
    **Then** it starts as before; `Settings` has no `game_version` field, and the variable is not in `docker-compose.yaml`, `docker-compose.dev.yaml`, `.env.example`, `scripts/worktree-setup.sh` or the environment table of `architecture/project-structure-boundaries.md`
    *(Covers FR209; `VSS-ms0`)*

14. **Given** every existing test
    **When** the suites run
    **Then** they pass, apart from the changes listed in Dev Notes "Existing tests that change"; no test run writes into the dev data directory (`dev/`)

## Tasks / Subtasks

<!-- Each functional task includes its tests in the same commit, red first. Commit per task: type(story-19.1/task-N): ...; feat/fix only for changes an admin can see, subject written for admins (release-note subjects from sprint-change-proposal-2026-11-17 section 2). -->

- [x] Task 1: The config file viewer serves `.json` files only + tests (AC: 1, 2, 3, 4, 5, 14) (`VSS-633`)
  - [x] 1.1: `models/errors.py`: `CONFIG_FILE_NOT_SUPPORTED` and `CONFIG_FILE_TOO_LARGE` under "# Config", after `CONFIG_PATH_INVALID` (`:37`)
  - [x] 1.2: `services/config_files.py`: constants `CONFIG_FILE_MAX_BYTES = 2 * 1024 * 1024` and `CONFIG_FILE_MAX_DEPTH = 200` (module level, after `logger`, `:28`); errors `ConfigFileNotSupportedError(filename)` and `ConfigFileTooLargeError(filename)` beside `ConfigPathInvalidError` (`:40-46`), with `filename` and `message` like the existing two (messages in Dev Notes "Messages"); `ConfigFileReadError(filename)` for any other `OSError` (Dev Notes "Read")
  - [x] 1.3: One file rule (Dev Notes "The file rule"): `_has_json_suffix(name)` and `_is_viewable_file(path)`; `list_files` (`:141-177`) uses it instead of `f.is_file() and f.suffix == ".json"` (`:172-174`) and drops entries that resolve outside the server data directory
  - [x] 1.4: `read_file` (`:179-227`): the order of Dev Notes "Read": containment, (Task 3's role check goes here), suffix of the requested name, exists, type and resolved suffix, size by `stat`, `read_bytes()` and `decode("utf-8-sig")`, `json.loads`, depth, redaction. `RecursionError` from `json.loads` and a depth over `CONFIG_FILE_MAX_DEPTH` give the `_raw` form (Dev Notes "Depth"). Update the module (`:1-17`) and method docstrings
  - [x] 1.5: `routers/config.py` `read_config_file` (`:471-538`): map `ConfigFileNotSupportedError` to 400, `ConfigFileTooLargeError` to 413, `ConfigFileReadError` to 500 `INTERNAL_ERROR`, each `headers=NO_STORE` (Dev Notes "Router"); imports (`:46-50`); docstring Raises and the module docstring (`:19-25`) say what the viewer serves
  - [x] 1.6: Tests (Dev Notes "API tests", Task 1 rows) and the changes in "Existing tests that change", red first

- [x] Task 2: Recursive redaction by key name and value + tests (AC: 6, 7, 8, 14) (`VSS-sg1`)
  - [x] 2.1: `services/game_config.py` (`:212-248`): `UNMANAGED_SECRET_KEYS = frozenset({"StartupCommands"})`, `SECRET_KEY_FRAGMENTS` (the ten of ADR-2 decision 2), a key normaliser, `is_secret_key` broadened to the three rules, `is_secret_value` for the two value rules, and `redact_secrets` recursive over objects and arrays, failing closed on `RecursionError` (Dev Notes "Redaction"). `has_secret_value` and `REDACTED` are unchanged
  - [x] 2.2: Update the docstrings of `redact_secrets`, `services/config_files.py` (module, `read_file`) and `routers/config.py` `read_config_file` (`:494-499`): "top-level" becomes "at every depth", naming the key and value rules
  - [x] 2.3: Tests (Dev Notes "API tests", Task 2 rows); replace `test_nested_password_is_unchanged` (`tests/test_routers_config.py:1474`) and `test_nested_secret_is_unchanged` (`tests/test_game_config.py:302`), red first

- [x] Task 3: Roles other than Admin see the root and `ModConfig` only + tests (AC: 1, 9, 10, 11, 14) (`VSS-3hs2`)
  - [x] 3.1: `services/config_files.py`: `MONITOR_CONFIG_DIRECTORIES = frozenset({"ModConfig"})`, `ConfigDirectoryForbiddenError(path)` and `_role_may_open(resolved, role, *, file_request)` (Dev Notes "The role's directories")
  - [x] 3.2: `list_directories(directory=None, role=None)` and `list_files(directory=None, role=None)`: role check on the resolved target directory after `_safe_path`; each listed entry is kept only when `_role_may_open` accepts its resolved path. `read_file`: role check right after `_safe_path`, before the suffix check (ADR-3 decision 5). Redacted stays the default: `None` and every role but `UserRole.ADMIN` are restricted (ADR-3 decision 6)
  - [x] 3.3: `routers/config.py` `list_config_directories` (`:393-429`) and `list_config_files` (`:432-468`): `role: RequireAuth` instead of `_`, `response: Response`, pass the role, `response.headers.update(NO_STORE)`, map `ConfigDirectoryForbiddenError` to 403 `FORBIDDEN` with `headers=NO_STORE` (also on the existing 400); `read_config_file` maps it the same way. Docstrings: which directories each role may list and read
  - [x] 3.4: `README.md` "Security" (`:35-37`): one paragraph "What a Monitor key can read" (Dev Notes "README")
  - [x] 3.5: Tests (Dev Notes "API tests", Task 3 rows) and the service-test changes in "Existing tests that change", red first

- [x] Task 4: Remove `VS_GAME_VERSION` + test (AC: 13, 14) (`VSS-ms0`)
  - [x] 4.1: `api/src/vintagestory_api/config.py:24`: remove `game_version: str = "stable"`
  - [x] 4.2: Remove `- VS_GAME_VERSION=${VS_GAME_VERSION:-stable}` from `docker-compose.yaml:22` and `docker-compose.dev.yaml:21`; the four-line block `.env.example:20-23` and the blank line after it; `VS_GAME_VERSION=stable` at `scripts/worktree-setup.sh:61`; the compose lines `_bmad-output/planning-artifacts/architecture/project-structure-boundaries.md:225`, `:259` and the table row `:470`. `README.md` needs no change: it does not mention the variable (`rg VS_GAME_VERSION README.md` is empty at b6ae2f2)
  - [x] 4.3: Comments that name the variable as if it existed: `services/mods.py:100-101` and `:302-303`, and the class docstring `tests/test_mod_service.py:2073-2074` (ADR-4 decision 3): say compatibility follows the installed server version; `VS_GAME_VERSION` may be named only as a former setting. Remove the stale mock line `tests/test_mod_service.py:709` (`mock_settings.return_value.game_version = "1.21.3"`)
  - [x] 4.4: `tests/test_config.py`: new class `TestRemovedSettings` (Dev Notes "API tests", Task 4 row)
  - [x] 4.5: `rg -n "VS_GAME_VERSION|game_version: str = \"stable\"|settings\.game_version"` outside `_bmad-output/implementation-artifacts/`, `archive/` and the Epic 6 and Epic 19 architecture files lists only the test of 4.4 and `test_mod_service.py:2141` (which sets the variable on purpose)

- [x] Task 5: Web: the note in the file browser for roles other than Admin + tests (AC: 12)
  - [x] 5.1: `web/src/features/settings/FileManagerPanel.tsx`: `const { data: auth } = useAuthMe();` (`@/api/hooks/use-auth-me`, as `SettingsPage.tsx:23`, `:35-36`); `showAdminNote = role !== undefined && role !== 'admin'`; render `<p data-testid="file-manager-admin-note" className="border-b px-3 py-1.5 text-xs text-muted-foreground">Some folders are only shown to Admin keys.</p>` directly after the breadcrumb bar (`:153-156`), inside `file-manager-panel`. Not in the error state (`:130-146`). No new hook, no API change, no change to what the list shows. Header comment: Story 19.1 (FR233)
  - [x] 5.2: `FileManagerPanel.test.tsx`: new `describe('Story 19.1: note for roles other than Admin')` (Dev Notes "Web tests")

- [x] Task 6: E2E against the Docker dev stack (AC: 9, 10, 11, 12)
  - [x] 6.1: New `web/e2e/file-browser-monitor-note.spec.ts` (Dev Notes "E2E")
  - [x] 6.2: Rebuild the stack from this branch (`just docker restart`), run `cd web && bunx playwright test e2e/file-browser-monitor-note.spec.ts` with `VS_API_KEY_ADMIN` and `VS_API_KEY_MONITOR` exported from `.env` (values not printed); also re-run `e2e/monitor-password-redaction.spec.ts`, `e2e/file-browser-navigation.spec.ts` and `e2e/settings-desktop-layout.spec.ts`. Do not start or stop the game server; no screenshots
  - [x] 6.3: Record in the Dev Agent Record that `GET /api/v1alpha1/config/directories` and `GET /api/v1alpha1/config/files` (Admin key) returned the same bodies before and after the run, and the SHA-1 of `data/serverdata/serverconfig.json` is unchanged

- [ ] Task 7: Quality gate and review hand-off (AC: all)
  - [x] 7.1: `just check` passes; the diff adds no lint or type suppression, no `cast` and no type assertion; pyright stays at 0 errors and the 3 pre-existing warnings (`VSS-1ar`); web 4 skipped (`VSS-hnl`); after `just test-api`, `git status --short` shows nothing under `dev/`
  - [ ] 7.2: Manual check on the Docker stack (needs the maintainer's confirmation before it is ticked, `project-context.md`): Dev Notes "Manual check"
  - [ ] 7.3: Story status `review`, `just sprint set 19-1-secrets-stay-with-admin review`, PR to `main`, PR link on `VSS-633`, `VSS-sg1`, `VSS-3hs2` and `VSS-ms0`. The PR description lists "API contract changes" from this story

## Dev Notes

### The problems (verified at b6ae2f2)

- **Any file under the server data directory (`VSS-633`).** `GET /config/files/{filename:path}` (`routers/config.py:471-538`) needs only an authenticated key (`role: RequireAuth`, `:485`). `read_file` (`services/config_files.py:179-227`) checks containment (`_safe_path`, `:67-102`, resolves symlinks) and existence (`:207`) only. `read_text(encoding="utf-8")` (`:213`) is outside the `try`, so a binary file (`UnicodeDecodeError`) or a directory (`IsADirectoryError`) is an unhandled 500 for both roles. `list_files` lists only `*.json` (`:172-174`, `f.suffix == ".json"`, case-sensitive), so listing and read disagree. A file with a byte order mark does not parse (`json.loads` rejects `\ufeff`) and comes back as `_raw`.
- **Nesting (found by this story's prototype, not in the ADR).** A JSON text nested 255 levels (arrays) or 254 levels (objects) parses but the response cannot be serialized: the route answers a plain 500 even for Admin (measured through `TestClient` at b6ae2f2: 250 levels 200, 254/255 levels 500, 100,000 levels 500 from `RecursionError` in `json.loads`). See "Depth".
- **Top-level redaction only (`VSS-sg1`).** `redact_secrets` (`services/game_config.py:238-248`) changes only an object's own keys and only keys in `SECRET_SETTING_KEYS` (`Password`, `:215-217`), so nested passwords, mod tokens and webhook URLs, and `StartupCommands` (free text) reach Monitor. Pinned as a limit by `test_nested_password_is_unchanged` (`tests/test_routers_config.py:1474`) and `test_nested_secret_is_unchanged` (`tests/test_game_config.py:302`).
- **Every directory (`VSS-3hs2`).** `GET /config/directories` (`:393-429`) and `GET /config/files` (`:432-468`) ignore the role (`_: RequireAuth`) and set no `Cache-Control`; `list_directories` (`services/config_files.py:104-139`) returns every subdirectory. A Monitor key lists `Saves`, `Backups`, `Playerdata` and reads `Playerdata/*.json`.
- **`VS_GAME_VERSION` (`VSS-ms0`).** `Settings.game_version` (`config.py:24`) is read by nothing in `api/src` (only the comments `services/mods.py:100-101`, `:302-303` name it). Set in `docker-compose.yaml:22`, `docker-compose.dev.yaml:21`, `scripts/worktree-setup.sh:61`; described falsely in `.env.example:20-23`. `Settings` (`model_config = SettingsConfigDict(env_prefix="VS_")`, `:16`) has no `env_file`; pydantic-settings reads declared fields only, so an undeclared `VS_GAME_VERSION` is ignored. Checked with a prototype: with `VS_GAME_VERSION=1.21.6` in the environment and the field removed, `Settings()` constructs and has no `game_version` attribute.

### Messages

| Error | Status | Code | `message` |
|---|---|---|---|
| `ConfigPathInvalidError` (unchanged) | 400 | `CONFIG_PATH_INVALID` | `Invalid file path: {filename}` |
| `ConfigDirectoryForbiddenError` (Task 3) | 403 | `FORBIDDEN` | `This directory needs the Admin role: {path}` |
| `ConfigFileNotSupportedError` | 400 | `CONFIG_FILE_NOT_SUPPORTED` | `Only .json files that are UTF-8 text can be viewed: {filename}` |
| `ConfigFileNotFoundError` (unchanged) | 404 | `CONFIG_FILE_NOT_FOUND` | `Config file not found: {filename}` |
| `ConfigFileTooLargeError` | 413 | `CONFIG_FILE_TOO_LARGE` | `Config file is larger than 2 MiB and cannot be viewed: {filename}` |
| `ConfigFileReadError` | 500 | `INTERNAL_ERROR` (exists, `models/errors.py:85`) | `Config file could not be read: {filename}` |

`{filename}` / `{path}` is the requested string, as today; it is the caller's own input. The 403 message is the same whether or not the directory or file exists (ADR-3 decision 4). The 2 MiB in the message is written from the constant (`CONFIG_FILE_MAX_BYTES // (1024 * 1024)`), not a second literal.

### The file rule (Task 1, ADR-1 decision 1)

```python
def _has_json_suffix(name: str) -> bool:
    """Whether a file name ends in .json, in any letter case (Epic 19 ADR-1)."""
    return name.casefold().endswith(".json")


def _is_viewable_file(path: Path) -> bool:
    """The viewer's file rule, shared by the listing and the read (Epic 19 ADR-1).

    A regular file (symlinks followed) whose own name and resolved name end in .json.
    Size and encoding are content checks made when the file is read.
    """
    return path.is_file() and _has_json_suffix(path.name) and _has_json_suffix(path.resolve().name)
```

- `list_files` keeps an entry `f` of `target_dir.iterdir()` when `_is_viewable_file(f)` and `f.resolve()` is inside the server data directory (`resolved.is_relative_to(base)`; a symlink out of the data directory is never listed, because its read is 400 `CONFIG_PATH_INVALID`), and, from Task 3, `_role_may_open(f.resolve(), role, file_request=True)`. The result is still the sorted entry names (`f.name`), unchanged shape.
- Letter case: `X.JSON` is now listed and read (ADR-1 decision 1 "compared without case"). The listing used to compare case-sensitively; an addition, listed under API contract changes.
- Size and encoding are not part of the listing rule (see "ADR against the code" 3): checking UTF-8 would read every file on every listing.

### Read (Task 1 and Task 3)

Order of checks in `read_file(filename, role=None)`; each raises before the next runs:

1. `safe_path = self._safe_path(serverdata_dir, filename)`: 400 `CONFIG_PATH_INVALID` (unchanged).
2. Task 3: `if not _role_may_open(safe_path, role, file_request=True): raise ConfigDirectoryForbiddenError(filename)`: 403.
3. `if not _has_json_suffix(filename)`: 400 `CONFIG_FILE_NOT_SUPPORTED`. The requested name, before the disk is touched (ADR-1 decision 3): same answer whether the file exists.
4. `if not safe_path.exists()`: 404 (unchanged; `safe_path` is resolved, so a dangling symlink is "not found").
5. `if not (safe_path.is_file() and _has_json_suffix(safe_path.name))`: 400 `CONFIG_FILE_NOT_SUPPORTED` (a directory, `x.json` that is a directory, a FIFO, a symlink `x.json` whose target is `notes.txt`; `safe_path` is already resolved, so `.name` is the target's name).
6. In one `try`: `size = safe_path.stat().st_size`; `if size > CONFIG_FILE_MAX_BYTES`: 413 (before any read, ADR-1 decision 5); `data = safe_path.read_bytes()`. `except FileNotFoundError` → `ConfigFileNotFoundError` (removed between the checks); `except OSError as e` → log `config_file_read_failed` (`filename`, `error=str(e)`) at error level and raise `ConfigFileReadError` (ADR-1 decision 8). `FileNotFoundError` is an `OSError`: catch it first.
7. `text = data.decode("utf-8-sig")`; `UnicodeDecodeError` → 400 `CONFIG_FILE_NOT_SUPPORTED` (ADR-1 decision 6). `utf-8-sig` strips one leading byte order mark and is otherwise UTF-8.
8. `json.loads(text)`; `except (json.JSONDecodeError, RecursionError) as e` → the `_raw` form as today (`{"_raw": text if reveal_secrets else REDACTED, "_parse_error": str(e)}`, warning `config_file_json_invalid` as today). Then the depth check ("Depth"), then `redact_secrets` unless Admin.

`reveal_secrets = role == UserRole.ADMIN` exactly as today (`"ADMIN"`, `"Admin"`, `""` and `None` are not Admin; `TestReadFileSecrets` pins this, `tests/test_config_files.py:301`).

### Depth (Task 1; ADR against the code 1)

```python
def _nesting_depth_exceeds(value: object, limit: int) -> bool:
    """Whether parsed JSON nests objects and arrays more than `limit` levels deep.

    Iterative, so it cannot hit the recursion limit itself.
    """
```

Walk with an explicit stack of `(value, depth)`; use the `TypeGuard` helpers (`_is_json_object` exists in `services/game_config.py:223-225`; add `_is_json_array` beside it and import both, or define local ones in `config_files.py`) so pyright strict sees no `Unknown` (a plain `isinstance(value, dict)` loop gave 9 `reportUnknown*` warnings in the prototype). When it exceeds `CONFIG_FILE_MAX_DEPTH` (200), return the `_raw` form with `_parse_error = f"Nested more than {CONFIG_FILE_MAX_DEPTH} levels deep"`. 200 leaves room for the response envelope (`data` → `content`) under the serializer's limit (~254 levels measured) and keeps `redact_secrets`' recursion far below Python's limit (1000), so its fail-closed branch is defensive only.

### Redaction (Task 2, ADR-2)

```python
UNMANAGED_SECRET_KEYS: frozenset[str] = frozenset({"StartupCommands"})
"""serverconfig.json keys that are not managed settings and hold secrets (Epic 19 ADR-2)."""

SECRET_KEY_FRAGMENTS: tuple[str, ...] = (
    "password", "passwd", "secret", "token", "apikey",
    "privatekey", "accesskey", "credential", "webhook", "authorization",
)
"""A key that contains one of these, after normalising, is a secret (Epic 19 ADR-2)."""

def _normalise_key(key: str) -> str:
    """casefold() and remove "_", "-", "." and spaces."""

_SECRET_KEYS_NORMALISED = frozenset(_normalise_key(k) for k in SECRET_SETTING_KEYS | UNMANAGED_SECRET_KEYS)

def is_secret_key(key: str) -> bool:
    """Whether a config key names a secret: a secret setting, an unmanaged secret key, or a key
    containing a secret fragment, compared after _normalise_key (Epic 19 ADR-2)."""

def is_secret_value(value: str) -> bool:
    """Whether a string is a URL with user info or a Discord webhook URL (Epic 19 ADR-2 decision 4)."""

def redact_secrets(content: object) -> object:
    """Parsed JSON with every secret replaced by REDACTED, at every depth (Epic 19 ADR-2).

    A secret key's whole value (any type) is replaced unless it is null or "" (has_secret_value);
    any other string is replaced when is_secret_value. Fails closed: if the walk hits the
    recursion limit the whole content is REDACTED. The argument is not changed.
    """
```

- Replace `_SECRET_KEYS_FOLDED` (`:220`) with `_SECRET_KEYS_NORMALISED`; `is_secret_key` keeps its name (ADR-2 decision 9: one function), so `TestSecretHelpers` keeps testing it. `is_secret_key` is used only by `redact_secrets` (`rg is_secret_key api/src`); `GET /config/game` decides `configured` with its own comparison (`services/game_config.py:549-553`) and does not change (ADR-2 decision 8).
- The walk is a private recursive `_redact(value)`: for an object, each `key: REDACTED if is_secret_key(key) and has_secret_value(v) else _redact(v)`; for an array, `[_redact(v) for v in value]`; for a string, `REDACTED if is_secret_value(value) else value`; anything else unchanged. Use the `TypeGuard` helpers (see "Depth") so pyright strict has no `Unknown`.
- `is_secret_value`: `urllib.parse.urlsplit` inside `try` (`ValueError` → not a secret). Secret when the URL has a scheme and a netloc and `parts.username is not None` (user info, with or without a password; the stricter reading of ADR-2 decision 4, an accepted direction of error), or when `parts.hostname` (lower-case) is `discord.com` or `discordapp.com` and `parts.path.startswith("/api/webhooks/")`. Subdomains (`ptb.discord.com`, `canary.discord.com`) are not in ADR-2; not added here (follow-up).
- Prototype results (`is_secret_key`): `bot_token`, `WebhookUrl`, `ApiKey`, `api-key`, `StartupCommands`, `startup_commands`, `Password`, `TokenBucketSize` → secret; `Key1`, `Seed`, `WorldSeed` → not (ADR-2 consequences). `Passwords` is now secret (it contains `password`).

### The role's directories (Task 3, ADR-3)

```python
MONITOR_CONFIG_DIRECTORIES: frozenset[str] = frozenset({"ModConfig"})
"""Directories, besides the root, that roles other than Admin may list and read (Epic 19 ADR-3)."""

def _role_may_open(self, resolved: Path, role: str | None, *, file_request: bool) -> bool:
    """Whether `role` may list (file_request=False) or read (True) the resolved path.

    Admin: always. Any other role: the root itself, a file directly in the root (for a read),
    or anything whose first path part relative to the server data directory is in
    MONITOR_CONFIG_DIRECTORIES, compared with casefold() (Epic 19 ADR-3 decision 3).
    """
```

- `resolved` is what `_safe_path` returns (resolved, inside the data directory), or a listing entry's `resolve()`. For a role other than Admin a path outside the data directory is refused (`resolved.is_relative_to(base_resolved)` first, so `relative_to` cannot raise for a listing entry that is a symlink out of the tree). `parts = resolved.relative_to(base_resolved).parts`; `()` is the root; `len(parts) == 1 and file_request` is a file in the root. The early `return []` when the server data directory itself does not exist (`:121-123`, `:157-159`) stays.
- **Listing a directory** (`list_directories`, `list_files` with `directory` set): `_safe_path` first (400), then `if not self._role_may_open(target_dir, role, file_request=False): raise ConfigDirectoryForbiddenError(directory)` before `is_dir()`, so a missing forbidden directory is 403, not `[]`. A missing allowed directory stays `[]` (unchanged).
- **Entries** in both listings are filtered for a role other than Admin by `_role_may_open(entry.resolve(), role, file_request=...)` (`False` for directories, `True` for files). That one rule gives AC 9 (the root listing of directories is `ModConfig` only, whatever `directory` string resolves to the root), AC 11 (a symlink in `ModConfig` that resolves into `Playerdata` is not listed) and a root symlink named `ModConfig` that points into `Saves` (not listed; reading through it is 403). Hidden directories in the root are not listed for Monitor (they are not in the allow-list); Admin's listing is unchanged, hidden ones included.
- Letter case: `playerdata`, `PLAYERDATA` are compared with `casefold()`. On a case-insensitive volume (macOS bind mount, Story 17.5's by-hand check) `resolve()` keeps the requested spelling, so the `casefold()` comparison is what makes `modconfig/x.json` allowed and `playerdata/x.json` forbidden there too.
- **Order** (ADR-3 decision 5): containment 400 → role 403 → ADR-1's checks. So `../x` is 400 for both keys, and `Logs/server-main.log` is 403 for Monitor and 400 `CONFIG_FILE_NOT_SUPPORTED` for Admin.
- **Router**: three routes map `ConfigDirectoryForbiddenError` to `HTTPException(403, {"code": ErrorCode.FORBIDDEN, "message": e.message}, headers=NO_STORE)`. Headers set on the injected `Response` are dropped when an exception produces the response, so every `HTTPException` of the three routes passes `headers=NO_STORE` (Story 17.5 review L1).

### Router (Tasks 1 and 3)

- `read_config_file`: new `except` blocks in the order of the service checks: `ConfigPathInvalidError` (400, exists), `ConfigDirectoryForbiddenError` (403), `ConfigFileNotSupportedError` (400), `ConfigFileNotFoundError` (404, exists), `ConfigFileTooLargeError` (413), `ConfigFileReadError` (500 `INTERNAL_ERROR`). All with `headers=NO_STORE`. The order of `except` clauses does not change behaviour (the classes are unrelated); it keeps the code readable.
- Both listing routes: `role: RequireAuth`, `response: Response` (already imported, `:31`), `response.headers.update(NO_STORE)` first, pass `role`; the existing 400 gains `headers=NO_STORE`. The listings now depend on the role, which is the reason Story 17.5 gave the read route `no-store` (`:66-68`).
- Docstrings are the route's API documentation (OpenAPI; there is no separate API document): `read_config_file` lists the 400/403/404/413/500 cases and the redaction rule; the listing routes say Monitor sees the root and `ModConfig` only and gets 403 for other directories.

### README (Task 3)

After the paragraph at `README.md:37`, add one paragraph (keep it short; Story 19.2 rewrites `:37` itself):

> **What a Monitor key can read.** In the file manager, a Monitor key sees the configuration files in the root of the server data directory and under `ModConfig` only; saves, backups, logs and player data are for the Admin key. Values under key names that look like secrets (password, token, secret, API key, webhook and similar), `StartupCommands`, URLs that contain a user name or password, and Discord webhook URLs are shown as `[redacted]`, and a file that is not valid JSON is not shown at all. A secret stored under another key name (for example `Key1`) is not recognised, so give Monitor keys only to people you would show your mod configuration to.

### Web (Task 5)

- `useAuthMe()` (`web/src/api/hooks/use-auth-me.ts:41-48`) caches `/api/v1alpha1/auth/me` with `staleTime: Infinity` under `queryKeys.auth.me`; `SettingsPage` already calls it (`:35`), so the panel's call shares the cached query and adds no request after the first. `role` is `auth?.data?.role` (a `string`; the API returns `"admin"` or `"monitor"`). `undefined` while loading or after an error, so the note is hidden then.
- The note is a static line, `text-xs text-muted-foreground` like other secondary text, `border-b` like the breadcrumb bar above it. It takes about 28 px from the 500 px panel (`:150`); the list and viewer keep `min-h-0 flex-1`.
- The panel lists what the API returns (minus names starting with `.`, `:79-81`); it needs no rule of its own (ADR-3 decision 7).
- Prototype: the note added as above, the six `src/features/settings/*.test.tsx` files passed unchanged (135 tests): their `fetch` mocks answer `/auth/me` with a files or settings body, so `role` is `undefined` and the note is hidden. No existing web test changes.

### API tests

All API tests: secret values are made-up constants (`SECRET` in both test modules); assert `SECRET not in response.text` on the raw body for Monitor. Files are written under `temp_settings.serverdata_dir` / `mock_settings.serverdata_dir` (`tmp_path`), never `dev/`.

| Task | File | Tests |
|---|---|---|
| 1 | `tests/test_config_files.py` new `TestViewableFiles` | For roles `"admin"` and `"monitor"` (parametrize), files in the root: `notes.txt`, `server-main.log`, `x.zip`, `noext` (existing and missing) → `ConfigFileNotSupportedError`, and `Path.read_bytes` monkeypatched to fail is never called; a directory `Logs` requested as `Logs`; a directory `dir.json`; `link.json` → `notes.txt` symlink; a FIFO `pipe.json` (`os.mkfifo`) → `ConfigFileNotSupportedError`; `bin.json` with `bytes(range(256))` and `latin.json` with `'{"a": "é"}'.encode("latin-1")` → `ConfigFileNotSupportedError`; `big.json` of `CONFIG_FILE_MAX_BYTES + 1` bytes → `ConfigFileTooLargeError` with `read_bytes` patched to raise (proves "not read"); `exact.json` of exactly `CONFIG_FILE_MAX_BYTES` bytes of valid JSON (`'"' + "a" * (N - 2) + '"'`) → served; `bom.json` = `b"\xef\xbb\xbf" + b'{"a": 1}'` → content `{"a": 1}`; `X.JSON` → served and listed; depth 200 (`"[" * 200 + "]" * 200`) → parsed content; depth 201 and an object nesting of 201 → `_raw` (Admin text, Monitor `REDACTED`) with `_parse_error` naming the limit; depth 100,000 → `_raw` (`RecursionError` path). `read_bytes` patched to raise `PermissionError` → `ConfigFileReadError` and an error log `config_file_read_failed`; patched to raise `FileNotFoundError` → `ConfigFileNotFoundError` |
| 1 | same, `TestListFiles` | `list_files(role="admin")` with `a.json`, `B.JSON`, `notes.txt`, a directory `dir.json`, `link.json` → `notes.txt`, `out.json` → a file outside the data directory: exactly `["B.JSON", "a.json"]`; and every listed name reads without `ConfigFileNotSupportedError` or `ConfigPathInvalidError` (AC 1, one rule) |
| 1 | `tests/test_routers_config.py` new `TestConfigFileTypes` | Both keys: `notes.txt` (exists), `missing.log` (missing), a directory, `bin.json` → 400 `CONFIG_FILE_NOT_SUPPORTED`, body `detail.code` and `Cache-Control: no-store`; `big.json` → 413 `CONFIG_FILE_TOO_LARGE` with `no-store`; depth 300 → 200 with `_raw` (Admin) — red first: 500 at b6ae2f2; `PermissionError` from `read_bytes` → 500 body `{"detail": {"code": "INTERNAL_ERROR", ...}}` with `no-store` |
| 2 | `tests/test_game_config.py` `TestSecretHelpers` | `is_secret_key` true for one key per fragment (`MyPassword`, `db_passwd`, `clientSecret`, `bot_token`, `ApiKey`, `Private.Key`, `AWS Access Key`, `credentials`, `WebhookUrl`, `Authorization`), for `StartupCommands`/`startup_commands`, for `api_key`/`api-key`/`api.key`/`API Key`, and for `Passwords`; false for `ServerName`, `Pass`, `""`, `ServerIdentifier`, `Seed`, `WorldSeed`, `Key1`, `Port`. `is_secret_value`: true for `https://user:pass@host/x`, `https://user@host/`, `https://discord.com/api/webhooks/1/abc`, `https://DiscordApp.com/api/webhooks/1/abc`; false for `https://example.com/api/webhooks/1`, `https://discord.com/channels/1`, `not a url`, `""`, `http://[`, `C:\\path`. `redact_secrets`: `{"Other": {"Password": "x"}}` → nested redacted; `[{"Token": "t"}, {"ApiKey": "k"}]`; a secret key with an object, an array, a number and `true` as value → `REDACTED`; `null`/`""` under a secret key at depth stay; a URL value at depth 3 inside an array; `{"StartupCommands": "/op x"}`; non-secret keys unchanged; the argument is not changed (deep copy compare); a 5,000-level list built in a loop → `REDACTED` (fail closed) |
| 2 | `tests/test_routers_config.py` `TestReadConfigFileSecrets` | One fixture file `ModConfig/mod.json` with every AC 6/7 case (nested `Password`, list with `Token`/`ApiKey`, `bot_token`, `WebhookUrl`, a user-info URL under `Endpoint`, a Discord webhook under `Url`, `Seed`, `null` and `""` under `Password`) and `serverconfig.json` with `StartupCommands` set: Monitor → each value `"[redacted]"`, `Seed` and the empty values unchanged, and none of the secret strings in `response.text`; Admin → content equals the file exactly (AC 8). `GET /config/game` for both roles equals its response before the change (`TestGetGameSettingsSecrets` passes unchanged) |
| 3 | `tests/test_config_files.py` new `TestRoleDirectories` | Data dir with `ModConfig/a/b/c.json`, `Playerdata/p.json`, `Saves/`, `.hidden/`, `serverconfig.json`. Role `"monitor"` and `None`: `list_directories()` == `["ModConfig"]`; `list_directories(".")` and `list_directories("ModConfig/..")` == `["ModConfig"]`; `list_directories("ModConfig")` == `["a"]`; `list_directories(d)` and `list_files(d)` for `Playerdata`, `playerdata`, `PLAYERDATA`, `Saves`, `NoSuchDir` raise `ConfigDirectoryForbiddenError`; `read_file("Playerdata/p.json")`, `read_file("NoSuchDir/x.json")`, `read_file("Playerdata/x.log")` raise `ConfigDirectoryForbiddenError` (role before suffix); `read_file("ModConfig/a/b/c.json")` and `read_file("serverconfig.json")` served; `ModConfig/link.json` → `Playerdata/p.json` and a directory symlink `ModConfig/pd` → `Playerdata`: read → forbidden, not in `list_files("ModConfig")` / `list_directories("ModConfig")`; in a second data dir whose `ModConfig` is a symlink to its `Saves`: `list_directories()` == `[]` and `read_file("ModConfig/x.json")` is forbidden (a root symlink with another name that resolves to `ModConfig` is allowed, because the rule is on the resolved path); `read_file("../x.json")` → `ConfigPathInvalidError` (containment first). Role `"admin"`: every listing unchanged (hidden included), every read allowed |
| 3 | `tests/test_routers_config.py` new `TestMonitorDirectories` | Through the routes with both keys: AC 9 (root listing, `?directory=.`), AC 10 (`/config/directories?directory=X`, `/config/files?directory=X`, `/config/files/X/p.json` for `Playerdata`, `playerdata`, `Saves`, `Backups`, `Logs`, `Mods`, a missing directory → 403 `{"code": "FORBIDDEN", "message": "This directory needs the Admin role: X..."}` for Monitor; Admin 200 or 400/404 as for any directory), AC 11 (nested `ModConfig` read, symlink out of `ModConfig` 403); `Cache-Control: no-store` on all three routes for 200, 400 and 403, both keys |
| 4 | `tests/test_config.py` new `TestRemovedSettings` | `monkeypatch.setenv("VS_GAME_VERSION", "1.21.6")`; `Settings(api_key_admin="admin-key")` constructs; `"game_version" not in Settings.model_fields`; `not hasattr(settings, "game_version")`. Docstring: ADR-4 decision 2, why the removal is not breaking |

### Existing tests that change (deliberately)

Found by running the whole API suite (`VS_API_KEY_ADMIN` set, `--ignore=tests/e2e`) against a throwaway prototype of Tasks 1 to 4 at b6ae2f2 (since discarded): 2843 passed, 15 failed, all listed here. The web settings suites passed unchanged against a prototype of Task 5.

- `tests/test_config_files.py`, because the service methods now restrict roles other than Admin by default (ADR-3 decision 6) and these tests call them without a role and with directories outside the allow-list (`ModConfigs`, `Cache`, `subdir`, `NonexistentDir`): pass `role="admin"` to keep their meaning in `test_list_directories_returns_subdirectory_names` (`:44`), `test_list_directories_includes_hidden_directories` (`:76`), `test_list_directories_excludes_files` (`:88`), `test_list_directories_with_subdirectory` (`:101`), `test_list_directories_nested_subdirectory` (`:116`), `test_list_directories_nonexistent_subdirectory` (`:140`), `test_list_files_in_subdirectory` (`:166`), `test_list_files_subdirectory_not_exists` (`:183`), `test_double_dot_variations` (`:406`, still 404 for Admin) and `test_subdirectory_within_serverdata_allowed` (`:448`).
- `tests/test_game_config.py`: `test_other_keys_are_not_secret` (`:262`) drops `"Passwords"` from its list (now secret; added to the secret cases); `test_nested_secret_is_unchanged` (`:302`) is replaced by the nested-redaction test.
- `tests/test_routers_config.py`: `test_copies_are_redacted` (`:1434`) drops `serverconfig.tmp` from its parameters (now 400; covered by `TestConfigFileTypes`); `test_nested_password_is_unchanged` (`:1474`) is replaced (Task 2); `test_game_log_is_withheld` (`:1501`) becomes "a game log is refused": `Logs/server-main.log` is 403 `FORBIDDEN` for Monitor and 400 `CONFIG_FILE_NOT_SUPPORTED` for Admin, and the log text is in neither body.
- `tests/test_mod_service.py`: `:709` stale mock line removed and `:2073-2074` docstring reworded (Task 4.3); not failing.
- Not changing and still passing (checked): `TestOtherConfigPathsWithAPassword` (`:1549`), including the route sweep `test_every_config_route_a_monitor_may_read` (`:1612`, reads `ModConfig/copy.json`; no route added), `test_errors_are_not_cached` (`:1539`, `/etc/passwd` stays 400 `CONFIG_PATH_INVALID` for both keys), `TestConfigFilePathTraversal` (`:1674`), `TestReadFileSecrets` (`tests/test_config_files.py:287`, including `ModConfig/../serverconfig.json` and the symlink in `ModConfig` to the root file: allowed, because the resolved file is in the root).
- Environment note: in a fresh worktree without `.env`, set `VS_API_KEY_ADMIN` before `just test-api` (Story 18.2 note: otherwise 77 errors and 6 failures unrelated to the story).
- Anything else that fails is a regression (AC 14): fix the code, not the test.

### Web tests (Task 5)

`FileManagerPanel.test.tsx` (pattern: `fetch` mocked per URL, as at `:503-520`): `/auth/me` answers `{status: 'ok', data: {role: 'monitor'}}` → `file-manager-admin-note` has exactly the text "Some folders are only shown to Admin keys."; `role: 'admin'` → no note; `/auth/me` never resolves (pending promise) while the list has rendered → no note; `/auth/me` answers 500 → no note; Monitor with `/config/directories` answering `['ModConfig']` → the list shows `file-item-ModConfig` and the files, nothing else. Red first: the Monitor case fails before 5.1.

### E2E (`web/e2e/file-browser-monitor-note.spec.ts`)

Style of `e2e/monitor-password-redaction.spec.ts` (copy `usePageKey`, `:46-54`; do not import across specs) and `e2e/mod-detail-bad-data.spec.ts` (header comment with story, FRs and requirements). Header: Story 19.1, FR208, FR233; read-only; the stubbed tests answer `/config.js` and `/api/v1alpha1/auth/me` with `page.route`; the real-Monitor tests skip, with the reason, when `VS_API_KEY_MONITOR` is not exported. Open the file manager as `file-browser-navigation.spec.ts:74-83` does, without its `localStorage` init script (it does nothing since Story 17.5).

- **Stubbed Monitor role.** `usePageKey(page, ADMIN_KEY)`; `page.route('**/api/v1alpha1/auth/me', ...)` fulfils `{status: 'ok', data: {role: 'monitor'}}`. Open `/config`, click `file-manager-tab`: `file-manager-admin-note` has the exact text; it contains no directory name from the Admin listing (compare against `GET /config/directories` with the Admin key). At 390x844 the note is inside `file-manager-panel` and the page has no horizontal overflow (`layout-widths.spec.ts` measure).
- **Admin.** `usePageKey(page, ADMIN_KEY)`, no stub: panel visible, note count 0.
- **Role loading.** `auth/me` stubbed with a handler that never fulfils until the end of the test: `file-list` visible, note count 0; then `page.unroute`.
- **Real Monitor key (API).** With `request`: `GET /config/directories` (Monitor) lists only `ModConfig` or nothing, and every entry is in the Admin listing; `?directory=Playerdata`, `?directory=playerdata`, `?directory=Saves` and a random missing name → 403 `FORBIDDEN`; `/config/files/Logs/server-main.log` → 403 (Monitor), 400 `CONFIG_FILE_NOT_SUPPORTED` (Admin); `/config/files/serverconfig.json` → 200 (Monitor); `Cache-Control: no-store` on the listings.
- **Real Monitor key (UI).** `usePageKey(page, MONITOR_KEY)`: the note is visible and the directory items in `file-list` equal the Monitor API listing (minus names starting with `.`).
- No real state changes; compare the listings before and after (Task 6.3). Do not start or stop the game server. No screenshots; the stack's server name never appears in an assertion message.

### Manual check (Task 7.2)

On the Docker stack built from this branch, with the page key set to the Monitor key (run the spec headed, or answer `/config.js` in the browser's dev tools): Settings, File Manager shows the note under the breadcrumb, reads well in light and dark themes and at phone width; only `ModConfig` and the root files are listed; opening a `ModConfig` file shows redacted values where expected. With the Admin key there is no note and every directory is listed. Do not start or stop the game server; no screenshots. The maintainer ticks 7.2.

### Not changed (do not "fix" these here)

- `GET /config/game` and how it decides `configured` (ADR-2 decision 8).
- The web's key handling and `/config.js` (Story 19.2), the CSP (Story 19.3), `main.py`'s `Settings()` construction (Stories 19.2 and 19.3).
- `FileViewer` and `useConfigFileContent`: a 400/403/413 shows the API's message in the viewer's existing error state (`FileManagerPanel.tsx:177`); no new UI for the new codes.
- The `localStorage` init scripts in other specs (Story 19.7).
- `.env.example`'s and the README's `VS_API_KEY` text (Story 19.2 edits the same files; keep this story's edits to the lines named in Task 4.2 and the new README paragraph).

### API contract changes

- `GET /api/v1alpha1/config/files/{path}`: new 400 `CONFIG_FILE_NOT_SUPPORTED` for a name that does not end in `.json`, a directory, a file that is not a regular file or does not resolve to a `.json` name, or a file that is not UTF-8 text. Before: 200 (text files, as `_raw`), 404 or an unhandled 500. New error code; behavior change.
- `GET /api/v1alpha1/config/files/{path}`: new 413 `CONFIG_FILE_TOO_LARGE` above 2 MiB. New error code.
- `GET /api/v1alpha1/config/files/{path}`: an `OSError` while reading is 500 `INTERNAL_ERROR` with the standard error body (before: a plain "Internal Server Error").
- `GET /api/v1alpha1/config/files/{path}`: a file with a byte order mark now parses instead of returning `_raw`; JSON nested more than 200 levels returns `_raw` and `_parse_error` (before: 500 from about 254 levels). Behavior change.
- `GET /api/v1alpha1/config/files/{path}`: for roles other than Admin, more values are `"[redacted]"`: secret key names at any depth, `StartupCommands`, URLs with user info, Discord webhook URLs; the whole value is replaced whatever its type. Behavior change (Monitor only).
- `GET /api/v1alpha1/config/directories`, `GET /api/v1alpha1/config/files`, `GET /api/v1alpha1/config/files/{path}`: for roles other than Admin, the root listing of directories holds `ModConfig` only and files that resolve elsewhere are not listed; any directory other than the root and `ModConfig` is 403 `FORBIDDEN` (existing code) for listing and reading. Before: 200. Behavior change (Monitor only).
- `GET /api/v1alpha1/config/directories`, `GET /api/v1alpha1/config/files`: responses (and their errors) now carry `Cache-Control: no-store`. File listing: `.json` is compared without case (`X.JSON` is listed and readable), and files that resolve outside the data directory are no longer listed (their read was already 400).
- `VS_GAME_VERSION`: removed from the settings, compose files and `.env.example`. Still accepted and ignored. Not breaking.
- Web UI: a note in the file browser for roles other than Admin. No API change.

### ADR against the code

1. **ADR-1 decision 7** treats `RecursionError` from `json.loads` as the `_raw` form. At b6ae2f2 the parser accepts nesting far deeper than the response can be serialized: 254 levels of objects or 255 of arrays already give a plain 500 for Admin, because the serializer stops there (measured with a prototype route test). The story adds `CONFIG_FILE_MAX_DEPTH = 200`: deeper content is also given as `_raw` (AC 5). This also keeps ADR-2's recursive redaction well under Python's recursion limit.
2. **ADR-3 decision 4** says the root listing for a role other than Admin returns only the allowed directories. Decided on the `directory` parameter, a request for `?directory=.` or `?directory=ModConfig/..` would list the whole root, and a root symlink named `ModConfig` that points into `Saves` would be listed. The story decides on resolved paths: the target and each entry (Dev Notes "The role's directories").
3. **ADR-1 decision 1** ("one predicate for the listing and the read") and the epic's AC "lists exactly the files that can be read this way". Size and UTF-8 are content checks: putting UTF-8 in the listing would read every file on every listing. The shared rule covers name, type, location and role; a too-large or non-UTF-8 `.json` file is listed and its read explains why it cannot be shown (AC 1 states this).
4. **ADR-1 decision 8** ("a logged 500 with the standard error envelope"): the app has no exception handler, so the route raises `HTTPException(500, {"code": "INTERNAL_ERROR", ...})` itself, the pattern of `routers/server.py:383`.
5. **ADR-4 decision 4** names the commit `fix(docker): ...`. The project's task commits are `type(story-X.Y/task-N): ...` (`project-context.md`, Commit Message Format); `cliff.toml` hides story scopes (`:5`, `:38`) and prints only the `api`/`web`/`docker` component scopes, so the story's subject gives the same release-note text without the `docker:` prefix. Kept as the project format; the maintainer may reword at merge.
6. **ADR-4 decision 1** lists README among the files to change: `README.md` does not mention `VS_GAME_VERSION` at b6ae2f2 (Story 15.6 dropped it). Nothing to remove there.
7. Not in the ADRs: `tests/test_game_config.py:302` (`test_nested_secret_is_unchanged`) pins the top-level limit too, beside the router test ADR-2 names.
8. Everything else in ADR-1 to ADR-4 matches the code at b6ae2f2 (line numbers re-read; ADR facts cite 048fea9, which has the same `api/` and `web/`).

### Testing Requirements

**CRITICAL:** Tests are written with each task and committed with it, red first. `just test-api <file>` / `just test-web <file>` after each task; `just check` before review.

- Raw-body checks: every Monitor test that holds a secret asserts `SECRET not in response.text` (Story 17.5 pattern).
- Both roles in every rejection and redaction test; Admin gets files unchanged.
- Router tests use `config_files_app` / `config_files_client` (`tests/test_routers_config.py:1046-1075`), which override `get_settings`, `get_server_service` and `get_config_files_service`; nothing is written outside `tmp_path`.
- Symlink and FIFO tests run on the CI runner (Linux) and macOS; no Windows support is needed.
- Tests must not read private members (`reportPrivateUsage`); the service's checks are tested through `read_file`, `list_files` and `list_directories`.

### Security Requirements

- No new endpoint and no new role. Containment stays first; the role check runs on resolved paths, so `..` segments and symlinks cannot reach a forbidden directory.
- The error messages echo only the requested path (the caller's input), never file content; the 403 answer does not reveal whether a forbidden directory or file exists.
- Never log a file's content or a redacted value; `config_file_read_failed` logs the file name and the error string only.
- A redacted value is replaced whole; the fail-closed branch replaces the whole content.

### Development Commands

- `just test-api tests/test_config_files.py tests/test_routers_config.py tests/test_game_config.py tests/test_config.py tests/test_mod_service.py`, `just test-web src/features/settings/`, `just typecheck-api`, `just lint-api`, `just lint-scripts` (Task 4 edits `scripts/worktree-setup.sh`), `just check`.
- Do not run `just format-api` (reformats unrelated files; Story 17.2 and 18.2 process notes); keep new code `ruff check` clean.

### Previous Story Intelligence

- **17.5:** the redaction default (`role == UserRole.ADMIN` only), `NO_STORE` on every `HTTPException` (review L1), the route sweep (review L2), the Monitor E2E with `page.route` on `/config.js`; its follow-ups became `VSS-633` and `VSS-sg1`.
- **17.3/17.4:** a TanStack Query v5 hook-level `onError` replaces the client default, so such a hook must call `handleApiError` itself; this story adds no hook and no `onError`. Router tests that write state must use `tmp_path`, never `dev/`.
- **17.2/18.2:** E2E that changes real state needs a snapshot guard and must restore the stack exactly; this story's E2E changes nothing. `feat`/`fix` subjects must describe what an admin can see; a completion note must be true of the code; manual checks wait for the maintainer.

### Git Intelligence

- Base `b6ae2f2` (`docs(epic-19): fold the maintainer's observation decisions into epic 19`) on `epic-19-planning`; the code is that of `048fea9` (Epic 18 on `main`).
- Planned commits (release-note subjects from the proposal, section 2):
  - Task 1 `fix(story-19.1/task-1): the config file viewer serves only .json files and no longer fails on binary files`
  - Task 2 `fix(story-19.1/task-2): hide nested and other-named secrets in config files from Monitor keys`
  - Task 3 `fix(story-19.1/task-3): Monitor keys can no longer list or read saves, backups and player data`
  - Task 4 `fix(story-19.1/task-4): VS_GAME_VERSION is no longer set or documented; it had no effect`
  - Task 5 `feat(story-19.1/task-5): tell Monitor users that some folders are only shown to Admin keys`
  - Task 6 `test(story-19.1/task-6): e2e for the file browser with a Monitor key`
  - Task 7 `chore(story-19.1/task-7): move story 19.1 to review`
- Story 19.2 edits `config.py`, `.env.example`, the compose files and `README.md:37` next; keep Task 4's edits to the named lines so its rebase is clean.

### Project Structure Notes

- New: `web/e2e/file-browser-monitor-note.spec.ts`.
- Modified: `api/src/vintagestory_api/services/config_files.py`, `services/game_config.py`, `routers/config.py`, `models/errors.py`, `config.py`, `services/mods.py` (comments); `api/tests/test_config_files.py`, `test_routers_config.py`, `test_game_config.py`, `test_config.py`, `test_mod_service.py`; `web/src/features/settings/FileManagerPanel.tsx`, `FileManagerPanel.test.tsx`; `README.md`, `.env.example`, `docker-compose.yaml`, `docker-compose.dev.yaml`, `scripts/worktree-setup.sh`, `_bmad-output/planning-artifacts/architecture/project-structure-boundaries.md`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 19.1: Secrets Stay with Admin]
- [Source: _bmad-output/planning-artifacts/prd.md] FR205-FR209, FR233
- [Source: _bmad-output/planning-artifacts/architecture/epic-19-api-security-and-mod-file-safety.md#Facts Checked in the Code, #ADR-1, #ADR-2, #ADR-3, #ADR-4]
- [Source: _bmad-output/planning-artifacts/architecture/epic-17-mod-data-fixes.md] (ADR-4: redaction by role, decisions 1, 2, 4-6 stand)
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-17.md] (section 2 API contract table and release-note subjects; section 5 answered questions 4 and 5, revision question 2)
- [Source: _bmad-output/implementation-artifacts/17-5-monitor-keys-cannot-read-the-server-password.md] (Completion Notes, Senior Developer Review)
- [Source: _bmad-output/implementation-artifacts/18-2-install-and-version-change-keep-records-right.md], [17-4-installed-status-is-right-everywhere.md]
- Beads: `VSS-633`, `VSS-sg1`, `VSS-3hs2`, `VSS-ms0`, parent `VSS-fl9b`
- `project-context.md` (no suppressions; manual test tasks need the maintainer's confirmation; commit format)

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5), BMAD dev-story, non-interactive.

### Debug Log References

- Red runs: Tasks 1 and 3 failed at collection (new names imported from `services/config_files.py`); Task 2 failed at collection (`is_secret_value`); Task 4's `TestRemovedSettings` failed on `game_version`; Task 5's three role cases failed before the panel called `useAuthMe`.
- Task 1 `typecheck-api`: a return annotation `-> httpx.Response` on a test helper was rejected (TestClient returns the `httpx2` type); the helper is left unannotated like the existing `_get`.
- Task 2 `typecheck-api`: a dict literal passed to `_write_config(dict[str, object])` was invariant; the variable is annotated `dict[str, object]`.
- `ruff format --check` on the touched test modules and `services/game_config.py` reports pre-existing formatting elsewhere in those files; they were not reformatted (only new code was kept in the format). The changed source modules `config_files.py` and `routers/config.py` are formatted.
- Docker dev stack rebuilt with `just docker restart` before the E2E runs; the game server was not running before or after (`ps` check in the container), and nothing started or stopped it.

### Completion Notes List

- Story created 2026-11-17 (create-story, non-interactive) and validated against the create-story checklist. A throwaway prototype of Tasks 1 to 4 (file rule, read order, role allow-list on resolved paths, recursive redaction, `game_version` removed) was run against the whole API suite (2843 passed, the 15 failures listed in "Existing tests that change"); a route test measured the serialization limit (254/255 levels → 500 at b6ae2f2); `Settings()` was constructed with `VS_GAME_VERSION` set and no field; a prototype of Task 5 passed the six settings web suites unchanged (135 tests). Everything was discarded.
- Task 1: `services/config_files.py` has `CONFIG_FILE_MAX_BYTES` (2 MiB), `CONFIG_FILE_MAX_DEPTH` (200), `ConfigFileNotSupportedError`, `ConfigFileTooLargeError`, `ConfigFileReadError`, `_has_json_suffix`, `_is_viewable_file` and an iterative `_nesting_depth_exceeds` (with local `TypeGuard` helpers). `read_file` checks in the order of Dev Notes "Read"; `RecursionError` from `json.loads` and nesting over 200 levels give the `_raw` form. `list_files` uses the shared file rule and drops entries that resolve outside the data directory. The router maps the new errors to 400 `CONFIG_FILE_NOT_SUPPORTED`, 413 `CONFIG_FILE_TOO_LARGE` and 500 `INTERNAL_ERROR`, each with `no-store`. Besides the story's tests, a router test checks that 200 levels of arrays and of objects still serialize (200) for both keys.
- Task 2: `services/game_config.py` has `UNMANAGED_SECRET_KEYS`, `SECRET_KEY_FRAGMENTS`, `_normalise_key`, `_SECRET_KEYS_NORMALISED` (replacing `_SECRET_KEYS_FOLDED`), `_is_json_array`, the broadened `is_secret_key`, `is_secret_value` (`urlsplit`, user info or a Discord webhook path on `discord.com`/`discordapp.com`) and a recursive `redact_secrets` that returns `REDACTED` on `RecursionError`. `GET /config/game` is unchanged (`TestGetGameSettingsSecrets` passes unchanged).
- Task 3: `MONITOR_CONFIG_DIRECTORIES`, `ConfigDirectoryForbiddenError` and `_role_may_open` decide on resolved paths; a small private `_target_directory` helper holds the listing target logic shared by `list_directories` and `list_files` (containment 400, then role 403 before `is_dir()`, then a missing allowed directory is `[]`). Each listed entry is kept only when `_role_may_open(entry.resolve(), ...)` accepts it. `read_file` checks the role right after `_safe_path`. The three routes take `role`, set `Cache-Control: no-store`, and map the 403 with `headers=NO_STORE` (the listings' existing 400 gained it too). README "Security" has the "What a Monitor key can read" paragraph.
- Task 4: `Settings.game_version` and every `VS_GAME_VERSION` line named in 4.2 are removed; the `mods.py` comments and the `test_mod_service.py` docstring name it only as a former setting; the stale mock line is gone. The 4.5 search outside the excluded paths also lists those two `mods.py` comments (allowed by ADR-4 decision 3) and planning documents that describe the removal (`prd.md`, `epics.md`, `sprint-change-proposal-2026-11-17.md`, `architecture/index.md`); no code or configuration sets or reads the variable.
- Task 5: `FileManagerPanel` reads the role with `useAuthMe()` and shows `file-manager-admin-note` under the breadcrumb bar when the role is known and not `admin`; not in the error state. Four new web tests (Monitor note and list, Admin, role pending, `/auth/me` 500).
- Task 6: `web/e2e/file-browser-monitor-note.spec.ts`, 5 tests, all passed against the rebuilt dev stack with `VS_API_KEY_ADMIN` and `VS_API_KEY_MONITOR` exported from `.env` (the real-Monitor tests ran, none skipped). `monitor-password-redaction.spec.ts`, `file-browser-navigation.spec.ts` and `settings-desktop-layout.spec.ts`: 15 passed. No screenshots. Task 6.3: the Admin-key bodies of `GET /api/v1alpha1/config/directories` and `GET /api/v1alpha1/config/files` and the SHA-1 of `data/serverdata/serverconfig.json` were byte-identical before and after both E2E runs.
- Task 7.1: `just check` passed: API 3015 passed; pyright 0 errors, 3 warnings (`VSS-1ar`); web 3316 passed, 4 skipped (`VSS-hnl`); script tests passed. The diff adds no lint or type suppression, no `cast` and no type assertion. `git status --short` shows nothing under `dev/` after the API suite.
- Task 7.2 (manual check on the Docker stack) is left for the maintainer and stays unticked.
- Task 7.3: story status `review` and sprint status `review` are set; the PR to `main` and the PR links on `VSS-633`, `VSS-sg1`, `VSS-3hs2` and `VSS-ms0` are not done (no push, PR or beads change in this run) and stay unticked.

### File List

- `README.md` (modified)
- `.env.example` (modified)
- `docker-compose.yaml` (modified)
- `docker-compose.dev.yaml` (modified)
- `scripts/worktree-setup.sh` (modified)
- `_bmad-output/planning-artifacts/architecture/project-structure-boundaries.md` (modified)
- `_bmad-output/implementation-artifacts/19-1-secrets-stay-with-admin.md` (modified)
- `api/src/vintagestory_api/config.py` (modified)
- `api/src/vintagestory_api/models/errors.py` (modified)
- `api/src/vintagestory_api/routers/config.py` (modified)
- `api/src/vintagestory_api/services/config_files.py` (modified)
- `api/src/vintagestory_api/services/game_config.py` (modified)
- `api/src/vintagestory_api/services/mods.py` (modified, comments)
- `api/tests/test_config.py` (modified)
- `api/tests/test_config_files.py` (modified)
- `api/tests/test_game_config.py` (modified)
- `api/tests/test_mod_service.py` (modified)
- `api/tests/test_routers_config.py` (modified)
- `web/src/features/settings/FileManagerPanel.tsx` (modified)
- `web/src/features/settings/FileManagerPanel.test.tsx` (modified)
- `web/e2e/file-browser-monitor-note.spec.ts` (new)
- 2026-11-17: Code review (GLM-5.3-Flash): changes requested (two medium, one low), fixed in 7e2d78b, re-review approved. Status done.
