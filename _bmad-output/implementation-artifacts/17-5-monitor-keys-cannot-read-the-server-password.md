# Story 17.5: Monitor Keys Can't Read the Server Password

Status: review

<!-- Implements FR186. Beads: VSS-qed. Security fix. Epic 17 ADR-4 governs this story (redact, do not restrict); the ADR's file viewer rule is widened, see Dev Notes "ADR against the code". Stacks on story/17-4-installed-status-is-right-everywhere. Line references were verified at commit 21457bf (the head of story/17-4 when this story was written) and must be re-checked before use: Stories 17.5-17.8 are implemented in order, each stacked on the previous. No new dependencies. Not in scope: secrets in other files beyond the rule in AC 4, Monitor's editable-looking fields on the settings page, the Monitor role's access to non-JSON files in general (see "Follow-ups"). -->

## Story

As a **server owner**,
I want **a Monitor key never to receive the game server password**,
so that **I can hand out read-only access without handing out the password**.

## Acceptance Criteria

1. **Given** a Monitor key and a server with a password set
   **When** I request `GET /api/v1alpha1/config/game`
   **Then** the `Password` setting has `value: null`, `secret: true` and `configured: true`, and the password appears nowhere in the response body
   *(Covers FR186; `VSS-qed`)*

2. **Given** a Monitor key and a server with no password (`Password` is `null`, is `""`, or is missing from `serverconfig.json`)
   **When** I request `GET /api/v1alpha1/config/game`
   **Then** the `Password` setting has `value: null`, `secret: true` and `configured: false`
   *(Covers FR186)*

3. **Given** a Monitor key
   **When** I read `serverconfig.json` through `GET /api/v1alpha1/config/files/...`, by any path that resolves to that file
   **Then** the `Password` value is `"[redacted]"` when one is set, and is unchanged when it is `null` or `""`; every other key is returned as today
   *(Covers FR186; `VSS-qed`)*

4. **Given** a Monitor key
   **When** I read any other file through `GET /api/v1alpha1/config/files/...`
   **Then** the same rule applies to it: a top-level key that is a secret setting's key in any letter case (`Password`, `password`, `PASSWORD`) with a value is `"[redacted]"`, so a copy of `serverconfig.json` under another name or in another directory does not expose the password; and a file that does not parse as JSON is returned with `_raw: "[redacted]"` and its `_parse_error`, never with its text
   *(Covers FR186; ADR-4 "Known limits", settled here)*

5. **Given** an Admin key
   **When** I request either endpoint
   **Then** the response is as today (the password, `_raw` text of a file that does not parse), except that the `Password` setting in `GET /config/game` also carries `secret: true`. It has no `configured` field
   *(Covers FR186)*

6. **Given** `GameConfigService.get_settings` and `ConfigFilesService.read_file`
   **When** they are called without a role, or with any role other than Admin
   **Then** they return the redacted form; only the Admin role gets secret values
   *(Covers FR186; ADR-4 decision 4)*

7. **Given** a Monitor key
   **When** I use any other endpoint or stream of the API (the list in Dev Notes "Every way the password can reach a Monitor key")
   **Then** none returns the password: each is closed by this story or shown, with a test or a cited existing test, not to carry it. `GET /config/game` and `GET /config/files/...` send `Cache-Control: no-store` for every role
   *(Covers FR186)*

8. **Given** a Monitor key in the web UI
   **When** I open Game Settings
   **Then** Password shows "Set" or "Not set", with no input field and no show/hide control
   *(Covers FR186)*

9. **Given** an Admin key in the web UI
   **When** I open Game Settings
   **Then** Password is the masked field with the show/hide button, editable, as since Story 16.8, including when no password is set (an empty field)
   *(Covers FR186)*

10. **Given** every existing test
    **When** the suites run
    **Then** they pass, apart from the changes listed in Dev Notes "Existing tests that change"; no test run writes into the dev data directory

## Tasks / Subtasks

<!-- Each functional task includes its tests in the same commit. Commit per task: type(story-17.5/task-N): ... ; feat/fix only for user-visible changes, subject written for users. Red first. Commit subjects are in Dev Notes "Git Intelligence": Task 1's is the security fix and is worded for the release notes. -->

- [x] Task 1: Monitor keys receive no secret from game settings or the config file viewer + tests (AC: 1, 2, 3, 4, 5, 6, 7 for the header)
  - [x] 1.1: `api/src/vintagestory_api/services/game_config.py` `ServerSetting` (`:37-83`): add `secret: bool = False` (attribute, constructor argument after `clear_command`, docstring: "the value is a secret: only the Admin role receives it (Story 17.5, FR186)"). Set `secret=True` on `Password` (`:119-126`) and on nothing else (Dev Notes "Which settings are secrets")
  - [x] 1.2: Same file, directly after `LIVE_SETTINGS` (`:192`): the constants and helpers in Dev Notes "The secret list and the helpers" (`REDACTED`, `SECRET_SETTING_KEYS`, `is_secret_key`, `has_secret_value`, `redact_secrets`). `SECRET_SETTING_KEYS` is derived from the `secret` flags, so the flag is the only place a secret is declared
  - [x] 1.3: `SettingInfo` (`:195-240`): add `secret: bool = False` and `configured: bool | None = None` (constructor, attributes, docstring). `to_dict`: `secret` is added as `True` only when set (like `requires_restart`, `:236-237`); `configured` is added only when it is not `None`
  - [x] 1.4: `GameConfigService.get_settings` (`:448-487`) becomes `get_settings(self, role: str | None = None)`. For a setting with `setting_def.secret`: when `role != UserRole.ADMIN`, `value` is `None` and `configured` is whether any key of the loaded config that equals the setting's key without regard to case has a value (`has_secret_value`); for Admin, `value` is read as today and `configured` stays `None`. Every `SettingInfo` gets `secret=setting_def.secret`. Docstring: redacted unless the Admin role is passed (ADR-4 decision 4). Import `UserRole` from `vintagestory_api.middleware.auth` (no cycle: that module imports only `config` and `models.errors`)
  - [x] 1.5: Same file, the two log guards `if key.lower() == "password":` (`:694`, `:759`) become `if setting_def.secret:` (`setting_def` is a parameter of both methods), so the log masking follows the same flag. Behavior is unchanged; `TestPasswordRedaction` (`tests/test_game_config.py:955`) still passes
  - [x] 1.6: `api/src/vintagestory_api/services/config_files.py` `read_file` (`:171-208`) becomes `read_file(self, filename: str, role: str | None = None)` as in Dev Notes "The file viewer". Move `import json` to the module top. Update the module docstring (`:1-12`) and the method docstring: what a role other than Admin receives
  - [x] 1.7: `api/src/vintagestory_api/routers/config.py`: `get_game_settings` (`:99-134`) and `read_config_file` (`:442-499`) name the dependency `role: RequireAuth` (today `_`), pass it to `service.get_settings(role)` / `service.read_file(filename, role)`, and take `response: Response` (import from `fastapi`) to set `response.headers["Cache-Control"] = "no-store"`. Update both docstrings (the "Both Admin and Monitor roles can access" sentences: Monitor receives secrets redacted) and the module docstring's endpoint list
  - [x] 1.8: Tests (Dev Notes "API tests", Task 1 rows), red first, including the raw-body assertions

- [x] Task 2: Every other path checked for both roles + tests (AC: 7)
  - [x] 2.1: Tests only (Dev Notes "API tests", Task 2 rows): the update endpoint, the two listing endpoints, and the default-redacted service calls. No source change is expected; if one of these tests fails, the path it covers is a leak: fix it in this task and add it to Dev Notes
  - [x] 2.2: Re-read Dev Notes "Every way the password can reach a Monitor key" against the code as it is on the branch (Stories 17.5-17.8 stack; an earlier story may have added an endpoint): `rg -n "RequireAuth|get_current_user|RequireAdmin|RequireConsoleAccess|websocket\(" api/src/vintagestory_api/routers`. Record in the Dev Agent Record that the table still holds, or what was added

- [x] Task 3: With a Monitor key, Game Settings shows whether a password is set + tests (AC: 8, 9)
  - [x] 3.1: `web/src/api/types.ts` `GameSetting` (`:244-252`): `secret?: boolean` ("the value is a secret; only an Admin key receives it") and `configured?: boolean` ("present only when the value was withheld: whether the secret is set; `value` is then null"). Extend the `value` comment: null also when withheld
  - [x] 3.2: New `web/src/components/SecretSettingStatus.tsx` (Dev Notes "Web"): label, "Set" or "Not set", one line of help text; no input, no button
  - [x] 3.3: `web/src/features/game-server/GameConfigPanel.tsx` `renderSetting` (`:222-244`): when `setting.configured !== undefined`, render `SecretSettingStatus` instead of `SettingField`. Everything else, including the `masked` Password field for Admin (`:57-62`, `:240`), is unchanged. Add "Story 17.5" to the header comment
  - [x] 3.4: Tests (Dev Notes "Web tests")

- [x] Task 4: E2E against the Docker dev stack (AC: 1, 2, 3, 8, 9)
  - [x] 4.1: New `web/e2e/monitor-password-redaction.spec.ts` (Dev Notes "E2E"). Rebuild the stack from this branch first (`just docker restart`); run with `cd web && bunx playwright test e2e/monitor-password-redaction.spec.ts` with `VS_API_KEY_ADMIN` and, if the stack has one, `VS_API_KEY_MONITOR` exported from `.env` (`just test-e2e-web` stops the stack afterwards). Also re-run `e2e/settings-empty-values.spec.ts`, `e2e/settings-desktop-layout.spec.ts` and `e2e/file-browser-navigation.spec.ts`
  - [x] 4.2: The spec reads only. Confirm in the Dev Agent Record that `data/serverdata/serverconfig.json` has the same SHA-1 before and after the run, and that the game server was not started or stopped. No screenshots; if one is unavoidable, mask `header span.font-semibold`, `#ServerName` and `#Password` (Story 16.8 rule)

- [x] Task 5: Quality gate and review hand-off (AC: all)
  - [x] 5.1: `just check` (lint, typecheck, all tests) passes; the diff adds no lint or type suppression and no `cast`; pyright stays at 0 errors and the 3 pre-existing warnings in tests; after `just test-api`, `git status --short` shows nothing under `dev/`
  - [x] 5.2: Story status `review`, `just sprint set 17-5-monitor-keys-cannot-read-the-server-password review`, PR (base `story/17-4-installed-status-is-right-everywhere` while its PR is open, otherwise `main`), PR link on `VSS-qed`. The PR description states the security fix in its first line, and lists the API contract changes (Dev Notes "API contract") and what a Monitor key loses (password; text of files that are not valid JSON)

## Dev Notes

### The bug (verified at 21457bf)

- **Game settings.** `get_game_settings` takes `_: RequireAuth` (`routers/config.py:99-101`; `RequireAuth = Annotated[str, Depends(get_current_user)]`, `:54`), so the role is known and thrown away. `GameConfigService.get_settings` returns `config.get(key)` for every entry of `LIVE_SETTINGS` (`services/game_config.py:462-463`), `Password` included (`:119-126`).
- **File viewer.** `read_config_file` is `RequireAuth` too (`routers/config.py:442-457`) and returns `ConfigFilesService.read_file(filename)` (`services/config_files.py:171-208`): the parsed JSON of any file under the server data directory, or, when the file does not parse, its whole text as `_raw` (`:205`).
- **The web only hides it.** Story 16.8 made the Password field `type="password"` (`components/SettingField.tsx:193-216`); the value is in the response, and its own Dev Notes record the gap that became `VSS-qed`.
- The role values are `UserRole.ADMIN = "admin"` and `UserRole.MONITOR = "monitor"` (`middleware/auth.py:16-20`); `get_current_user` returns one of them (`:62-107`). `RequireAdmin` (`middleware/permissions.py:14-37`) answers 403 for anything else.

### Decision: redact, do not restrict (recorded before implementation)

Epic 17 left one question open for this story: redact the password for Monitor, or make both endpoints Admin-only. **Redact.** This is ADR-4's decision and the maintainer saw it at story creation and did not object. Both `GET /config/game` and the config file viewer stay open to Monitor (FR21, FR22); what Monitor receives is limited to non-sensitive data (FR32). Admin sees what it sees today.

### Which settings are secrets (checked at story creation)

Epic task "check a server-generated `serverconfig.json` for other secret fields": done against the top-level key names of a `serverconfig.json` written by a 1.22 game server (names and JSON types only; values were not read) and `agentdocs/vs-serverconfig-commands.md:90-170`.

- **Secret: `Password`.** The only credential among the managed settings (`LIVE_SETTINGS`) and in the file.
- **Considered and left visible:** `ServerIdentifier` and `VhIdentifier` (identifiers, not credentials: nothing in `agentdocs/` or the manager authenticates with them; `VhIdentifier` is null outside hosted mode), `WorldConfig.Seed` (not a credential), `Roles` (privilege lists, no passwords), `MasterserverUrl` / `ModDbUrl` (public URLs), `StartupCommands` (free text, null by default; an admin could type a password command into it, which no key list can catch).
- The only managed setting is `Password`, so `SECRET_SETTING_KEYS == frozenset({"Password"})`. A future secret is declared by setting `secret=True` on its `ServerSetting`; a secret key of `serverconfig.json` that is not a managed setting would need the constant to grow a second source, which is not built now.

### The secret list and the helpers (`services/game_config.py`, after `LIVE_SETTINGS`)

```python
REDACTED = "[redacted]"
"""What a role other than Admin receives in place of a secret value in a config file (FR186)."""

SECRET_SETTING_KEYS: frozenset[str] = frozenset(
    key for key, setting in LIVE_SETTINGS.items() if setting.secret
)
"""Keys of serverconfig.json whose values only the Admin role receives (Story 17.5)."""

_SECRET_KEYS_FOLDED = frozenset(key.casefold() for key in SECRET_SETTING_KEYS)


def _is_json_object(value: object) -> TypeGuard[dict[str, Any]]:
    """Whether parsed JSON is an object. `json.loads` only builds dicts with string keys."""
    return isinstance(value, dict)


def is_secret_key(key: str) -> bool:
    """Whether a config key names a secret setting, in any letter case."""
    return key.casefold() in _SECRET_KEYS_FOLDED


def has_secret_value(value: object) -> bool:
    """Whether a secret is set: anything but null and the empty string."""
    return value is not None and value != ""


def redact_secrets(content: object) -> object:
    """Parsed JSON with the value of every top-level secret key replaced by REDACTED.

    Only an object is changed, and only its own keys; null and "" stay, since they
    hold no secret.
    """
    if not _is_json_object(content):
        return content
    return {
        key: REDACTED if is_secret_key(key) and has_secret_value(value) else value
        for key, value in content.items()
    }
```

- This exact code was type-checked in the worktree: pyright strict 0 errors, 0 warnings; ruff clean. A plain `isinstance(content, dict)` narrows to `dict[Unknown, Unknown]` and adds 4-5 `reportUnknown*` warnings; the `TypeGuard` is the cast-free way around it (`TypeGuard` from `typing`). Do not copy the `cast` in `models/moddb.py:120`.
- **Letter case.** The game reads `serverconfig.json` with Json.NET, which matches property names without case by default (general library behavior; not verified against the game). A hand-edited file with `"password": "x"` is therefore treated as holding the password. If both `Password` and `password` are present, both are redacted.
- **`""`.** The manager stores a cleared password as `null` (Story 16.8, `_validate_value`, `:510-515`), and the test fixtures use `""` for "no password". `""` counts as not set and is returned as it is.
- **`configured`** in `get_settings` uses the same two helpers over the loaded config: `any(has_secret_value(v) for k, v in config.items() if k.casefold() == key.casefold())`. For Admin the value is still `config.get(key)` (exact key), as today.

### The file viewer (`ConfigFilesService.read_file`)

```python
reveal_secrets = role == UserRole.ADMIN
content: object
try:
    content = json.loads(text)
except json.JSONDecodeError as e:
    logger.warning("config_file_json_invalid", filename=filename, error=str(e))
    content = {"_raw": text if reveal_secrets else REDACTED, "_parse_error": str(e)}
else:
    if not reveal_secrets:
        content = redact_secrets(content)
```

(`text` is `safe_path.read_text(encoding="utf-8")`, read once; today the file is read twice, `:200` and `:205`.)

Rules, and why each is the smallest safe one:

1. **Redaction works on the parsed JSON, never on the text.** No regular expression touches file content.
2. **Every file, not only `serverconfig.json`.** ADR-4 decision 3 compares the resolved path with the game's `serverconfig.json`. That misses a copy under another name (`serverconfig.backup.json`, a copy inside a backup directory), the temp file of the manager's own atomic write (`serverconfig.tmp`, `services/game_config.py:745-747`; `read_file` has no suffix check), and, on a filesystem that ignores case, the same file requested as `SERVERCONFIG.JSON` (`Path.resolve()` does not normalize case on macOS). Applying the top-level rule by content covers all of them, including every path that resolves to the real file (`./serverconfig.json`, `ModConfig/../serverconfig.json`, a symlink), with less code than the path comparison. The cost: a mod's own config with a top-level `Password` key is redacted for Monitor too, which is what a server owner would want.
3. **Top-level keys only.** `serverconfig.json` holds its password at the top level. Nested keys and other key names (`Token`, `ApiKey`, a mod's webhook URL) are not this story's secret; see "Follow-ups".
4. **A file that does not parse.** Its text cannot be redacted structurally, so a role other than Admin does not receive it: `_raw` is `"[redacted]"`, `_parse_error` is kept (a `JSONDecodeError` message holds a position, never content). This covers a `serverconfig.json` that is not valid JSON (hand-edited with a comment or trailing comma; the game tolerates more than `json.loads`), and it closes a second path at the same time: `GET /config/files/Logs/server-main.log` returns a game log as `_raw` to any authenticated key today, although every log endpoint is Admin-only (`routers/console.py:112-114`, `:426`, `:497`). The manager sends `/serverconfig password <value>` to the game's console (`services/game_config.py:122`, `:699`); whether the game writes that command to its log files was not verified, and after this rule it does not matter. Cost: Monitor loses the text of mod config files that are not strict JSON. That is accepted; Admin is unchanged.
5. **Not JSON at all, not text.** A binary file fails in `read_text` with `UnicodeDecodeError`, which is not caught and becomes a 500 for both roles, today and after this story. It returns no content. Not changed.
6. **Arrays and scalars** (`[1, 2]`, `"text"`, `42`) are returned as they are.

### Every way the password can reach a Monitor key

Checked at 21457bf by reading every router (`rg -n "@router\.|@ws_router\." api/src/vintagestory_api/routers`) and `rg -n -i password api/src`.

| Path | Today | After this story | Evidence / test |
|---|---|---|---|
| `GET /config/game` | value returned | `value: null`, `configured` | Task 1; AC 1, 2 |
| `GET /config/files/{path}`, the real `serverconfig.json` by any path | value returned | `"[redacted]"` | Task 1; AC 3 |
| `GET /config/files/{path}`, copies, `serverconfig.tmp`, other letter case of the key | value returned | `"[redacted]"` | Task 1; AC 4 |
| `GET /config/files/{path}`, a file that does not parse (broken `serverconfig.json`, game logs) | text returned as `_raw` | `_raw: "[redacted]"` | Task 1; AC 4 |
| `POST /config/game/settings/{key}` (the response echoes `value`, `game_config.py:295-302`) | Admin only (`routers/config.py:152`); Monitor gets 403 | unchanged | existing `test_monitor_blocked_from_update` (`tests/test_routers_config.py:501`); Task 2 adds: the 403 body does not contain the submitted value |
| Error messages of the update (`SettingValueInvalidError`, `game_config.py:534-537`, echoes the value) | Admin only; never raised for a string setting (`:519-520`), so never for `Password` | unchanged | reading; the 403 for Monitor is raised by the dependency before the handler runs |
| `GET /config/files`, `GET /config/directories` | names only | unchanged | Task 2: Monitor body does not contain the password |
| `GET /config/api`, `POST /config/api/settings/{key}` | Admin only; API settings, not the game config | unchanged | existing `TestGetApiSettingsRBAC` (`tests/test_routers_config.py:700`) |
| Console: `GET /console/history`, `POST /console/command`, `GET /console/logs` (a password change is sent as a console command and shows in the console buffer) | Admin only (`RequireConsoleAccess`, `routers/console.py:39-41`, `:72-74`, `:112-114`) | unchanged | existing `tests/console/test_history_endpoint.py:26-31`, `tests/console/test_command_endpoint.py:208-217`, `tests/console/test_logs_endpoint.py:31-35` (each: Monitor gets 403) |
| WebSockets `/console/ws`, `/console/logs/ws` | Admin only: a Monitor key or a Monitor `ws-token` is closed with 4003 (`routers/console.py:324-333`, `:497-505`) | unchanged | existing `tests/console/test_websocket.py:43`, `:393`, `tests/console/test_websocket_token_auth.py:126`, `:267`, `tests/console/test_logs_endpoint.py:258` |
| `POST /auth/ws-token` | Monitor can get a token; it carries the Monitor role and the sockets refuse it | unchanged | same tests |
| `GET /server/status`, `/server/install/status`, `/healthz`, `/readyz`, `/auth/me`, `/mods/*`, `/versions/*` | no config values (`models/server.py:97-109`) | unchanged | reading |
| `/debug/*`, `/jobs/*`, `/metrics/*` | Admin only; no config values | unchanged | reading (`routers/debug.py:24`, `:39`, `:60`) |
| API logs (`executing_console_command`, `setting_updated`) | the value is logged as `***` (`game_config.py:693-697`, `:758-774`); `VS_CFG_SERVER_PASSWORD` is masked at startup (`config_init_service.py:174`, `:214`); logs are not served by any endpoint | guard follows the `secret` flag (1.5) | existing `TestPasswordRedaction` (`tests/test_game_config.py:955`) |
| `env_var` in the settings response | the variable's name (`VS_CFG_SERVER_PASSWORD`), never its value | unchanged | reading (`game_config.py:399-411`) |
| Server-side response cache | none: `GameConfigService` and `ConfigFilesService` are built per request (`routers/config.py:79-96`, `:350-361`) and neither caches | unchanged | `rg -n "cache" routers/config.py services/game_config.py services/config_files.py` finds nothing |
| HTTP caches between the API and the browser | both responses now depend on the key and carried no cache header | `Cache-Control: no-store` on both, for every role (as `/config.js` does, `main.py:268`) | Task 1 |
| Web query cache | one browser, one key per page load (`/config.js`, `web/src/api/client.ts:29-32`); not shared between roles | unchanged | reading |

### Web

- **What decides the rendering: `configured`, not the role.** The panel does not ask who is logged in. A setting whose response has `configured` (so its value was withheld) is shown as a status. An Admin response never has it, so Admin keeps the masked field, including for "no password" (`value: null`, no `configured`), which is an empty editable field (AC 9). `secret` alone must not switch the rendering: Admin responses carry it too.
- **`SecretSettingStatus`** (`web/src/components/SecretSettingStatus.tsx`), props `{ settingKey: string; label: string; configured: boolean; className?: string }`:
  - a `div` with `data-testid={`secret-setting-${settingKey}`}`, the label as text (`text-sm font-medium text-foreground`, the classes of `SettingField`'s label; a `span`, not a `label`: there is no control to label), the status `Set` / `Not set` (`text-sm`, `data-testid={`secret-setting-status-${settingKey}`}`), and the help line "Only an Admin key can see or change this value." (`text-xs text-muted-foreground`).
  - No `input`, no `button`, no hook. Nothing in it can hold or reveal a value.
  - The env badge of `SettingField` is not repeated here.
- **Nothing for Monitor may assume `value` is a string.** Checked: `SettingField` uses `value ?? ''` (`:115`); `Header` checks `typeof ... === "string"` (`components/layout/Header.tsx:18`); `GameConfigPanel` passes the value through (`:235`). After Task 3 the withheld setting never reaches `SettingField`.
- **Between Task 1 and Task 3** a Monitor sees Password as an empty masked field (the web already handles `value: null`). Every commit is green; the interim is on the branch only.
- **The file viewer needs no source change:** `FileViewer` prints whatever JSON it is given (`components/FileViewer.tsx:124-132`), so `"[redacted]"` shows as a string value.
- **Unchanged:** a Monitor still sees the other settings as editable fields that answer 403 on save. ADR-4 decision 5 leaves that as it is.

### API tests

Use one distinctive constant in the tests, for example `SECRET = "pw-Zq9-monitor-must-not-see"` (no real value), written into the temp `serverconfig.json`. "Body" means `response.text`, the raw response, not the parsed JSON.

**Task 1**, `tests/test_routers_config.py`, new classes beside `TestGetGameSettings` (`:163`) and `TestReadConfigFile` (`:1188`); fixtures `client` (`:152`), `config_files_client` (`:929`), `config_file` (`:90-96`), keys from `tests/conftest.py:21`, `:61-69`. The fixtures write `"Password": ""` (`:79`); tests that need a password rewrite the file.

| Endpoint | Case | Admin | Monitor |
|---|---|---|---|
| `GET /config/game` | password set | `value == SECRET`, `secret is True`, no `configured` key | `value is None`, `secret is True`, `configured is True`; `SECRET not in response.text` |
| `GET /config/game` | `null`, `""`, key missing (parametrized) | value as today (`None`, `""`, `None`), no `configured` | `value is None`, `configured is False` |
| `GET /config/game` | file has `"password": SECRET` (lower case) and no `Password` | `value is None` (as today) | `configured is True`; `SECRET not in response.text` |
| `GET /config/game` | other settings | only `Password` has `secret`; no setting has `configured` | only `Password` has `secret` and `configured`; every other setting equals the Admin response |
| `GET /config/game`, `GET /config/files/serverconfig.json` | header | `Cache-Control: no-store` | same |
| `GET /config/files/serverconfig.json` | password set | `content["Password"] == SECRET` | `"[redacted]"`; `SECRET not in response.text`; every other key equals the Admin response |
| same | `null` / `""` | unchanged | unchanged (`None` / `""`) |
| `GET /config/files/ModConfig/copy.json`, `/config/files/serverconfig.backup.json`, `/config/files/serverconfig.tmp` (copies of the file) | password set | full | `"[redacted]"`; `SECRET not in response.text` |
| a file with `Password`, `password` and `PASSWORD` keys | values set | full | all three `"[redacted]"` |
| a file with `{"Other": {"Password": "nested"}}` | | full | unchanged (top level only; pins the documented limit) |
| `serverconfig.json` that does not parse (`{"Password": "<SECRET>", }`) | | `_raw` contains `SECRET`, `_parse_error` set | `_raw == "[redacted]"`, `_parse_error` set; `SECRET not in response.text` |
| `Logs/server-main.log` holding a line with `SECRET` | | `_raw` contains it | `_raw == "[redacted]"`; `SECRET not in response.text` |
| a JSON array file, a JSON string file | | unchanged | unchanged |

Service level, `tests/test_config_files.py` `TestReadFile` (`:230`) and `tests/test_game_config.py` `TestGetSettings` (`:232`), `TestServerSettingModel` (`:197`):

- `read_file` for `./serverconfig.json`, `ModConfig/../serverconfig.json` and a symlink to the file: redacted without a role and with `"monitor"`, full with `"admin"` (the alternate paths are tested here because an HTTP client normalizes `..` before the request is sent; see the note in `TestConfigFilePathTraversal`, `tests/test_routers_config.py:1241`).
- AC 6: `read_file(name)` and `get_settings()` with no role, with `"monitor"`, with `""`, and with `"ADMIN"` (wrong case) are all redacted; only `"admin"` (`UserRole.ADMIN`) is not.
- `SECRET_SETTING_KEYS == frozenset({"Password"})`; `ServerSetting.secret` defaults to `False`; `LIVE_SETTINGS["Password"].secret is True`; `SettingInfo.to_dict()` omits `secret` and `configured` by default, includes `secret: True` when set and `configured` when it is `False` (not only when truthy).
- `redact_secrets`: the helper's cases directly (object, array, scalar, `None`, `""`, a non-string secret value such as `123` becomes `"[redacted]"`).

**Task 2**, `tests/test_routers_config.py`:

- `POST /config/game/settings/Password` with `{"value": SECRET}` and the Monitor key: 403, `SECRET not in response.text`, and the file is unchanged. With the Admin key: 200 and the response `value` is `SECRET` (unchanged, pins AC 5 for the update).
- With a password set, `GET /config/files` and `GET /config/directories` with the Monitor key: 200 and `SECRET not in response.text`.
- One sweep: with a password set, for the Monitor key request every `GET` route under `/api/v1alpha1/config` that Monitor may call (`/game`, `/files`, `/directories`, `/files/serverconfig.json`) and assert `SECRET not in response.text` for each; the list is written out in the test so a new route has to be added by hand.

### Web tests

| Task | File | Test |
|---|---|---|
| 3 | `src/components/SecretSettingStatus.test.tsx` (new) | `configured` true shows "Set", false shows "Not set"; the label and the help line are shown; there is no `textbox`, no element with `type="password"`, no `button` |
| 3 | `src/features/game-server/GameConfigPanel.test.tsx` (new `describe('Story 17.5: secret settings')`, style of the Story 16.8 block at `:532`) | Monitor response (Password `{ value: null, secret: true, configured: true }`): `secret-setting-status-Password` reads "Set", `document.getElementById('Password')` is null, no "Show password" button; with `configured: false`: "Not set"; Admin response (`secret: true`, a string value, no `configured`): masked input with the value and the "Show password" button, as today; Admin with no password (`secret: true`, `value: null`, no `configured`): an empty masked input, not "Not set"; the other settings render as fields in every case |
| 3 | `src/api/config.test.ts` `fetchGameConfig` (`:34`) | a response with `secret` and `configured` reaches the caller with those fields |
| 3 | `src/components/FileViewer.test.tsx` "content display" (`:111`) | content `{ Password: '[redacted]' }` shows `"[redacted]"` |

### E2E (`web/e2e/monitor-password-redaction.spec.ts`)

Style of `e2e/settings-empty-values.spec.ts` (reads only) and `e2e/installed-mods-phone.spec.ts` (`page.route` stubs). Header comment with requirements as in those files. The spec changes nothing on the stack.

- **Which key the page uses.** The web reads its key from `/config.js` (`web/index.html:13`, `web/src/api/client.ts:29-32`), which serves the stack's `VS_API_KEY` or the Admin key (`api/src/vintagestory_api/config.py:32-36`). The `localStorage.setItem('apiKey', ...)` in the existing specs has no effect (nothing in `web/src` reads it). So this spec sets the page's key itself: `page.route('**/config.js', route => route.fulfill({ contentType: 'application/javascript', body: `window.__VSM_CONFIG__ = ${JSON.stringify({ apiKey })};` }))` before `page.goto`.
- **Keys.** `VS_API_KEY_ADMIN` as in the other specs (`process.env.VS_API_KEY_ADMIN || 'changeme'`). `docker-compose.dev.yaml:18` passes `VS_API_KEY_MONITOR` to the stack when `.env` sets it; the spec reads `process.env.VS_API_KEY_MONITOR` and the tests that need a real Monitor key `test.skip` with the reason when it is empty. The stubbed tests always run.
- **Never print the password.** Compare with `expect(text.includes(password)).toBe(false)`, not `expect(text).not.toContain(password)`: a failing `toContain` prints both strings into the report.

Tests:

1. **API, real Monitor key** (skipped without one). With the Admin key read whether a password is set (keep only the boolean and, in memory, the value). With the Monitor key: `GET /config/game` gives Password `value === null`, `secret === true`, `configured` equal to that boolean; `GET /config/files/serverconfig.json` gives `content.Password` of `null`, `""` or `"[redacted]"`; when the Admin value is a string of 8 or more characters, neither Monitor body includes it.
2. **UI, real Monitor key** (skipped without one). Page key = Monitor. Open `/game-server/settings`: `secret-setting-status-Password` reads "Set" or "Not set" (matching test 1's boolean), `#Password` does not exist, there is no "Show password" button. Then open the file viewer (`file-manager-tab`, as `e2e/file-browser-navigation.spec.ts:80-82` does), select `file-item-serverconfig.json`: `file-viewer-content` contains `"Password": null`, `"Password": ""` or `"Password": "[redacted]"`.
3. **UI, stubbed, always runs.** Page key = Admin. `page.route` on `GET /api/v1alpha1/config/game`: `route.fetch()` the real response and replace the Password setting with `{ ...setting, value: null, secret: true, configured: true }` (second test: `configured: false`). "Set" / "Not set" as in test 2; at 1440x900 and 390x844 the status stays inside the Server Info card (no horizontal overflow of `game-config-panel`).
4. **UI, Admin unchanged.** Page key = Admin, no stub: `#Password` has `type="password"` and the "Show password" button exists. Do not click it.

### Existing tests that change (deliberately)

Found by running the API suite against a throwaway prototype of Task 1 (since discarded): 2525 passed, 0 failed. No existing API test asserts a password value through either endpoint. The web was not prototyped: the two new `GameSetting` fields are optional, so no existing fixture or type breaks.

- `api/tests/test_config_files.py:253-266` `test_read_file_invalid_json`: still passes (it only checks that `_raw` exists) but now exercises the redacted default. Make it two tests: Admin role gets the text in `_raw`; no role gets `"[redacted]"`. (Task 1)
- `api/tests/test_config_files.py:231-241` `test_read_file_success` and the `get_settings()` calls in `tests/test_game_config.py:232-356`: unchanged and still passing; they now run with the redacted default, which is what AC 6 wants. Do not add a role to them.
- `web/e2e/settings-empty-values.spec.ts:67` ("the password is masked and can be shown and hidden") and `:49` (empty fields, which looks up the Password input by label) rely on the page using the Admin key. On a stack whose `VS_API_KEY` is the Monitor key they fail after this story (no `#Password` field). Give that spec the same `/config.js` route with the Admin key in its `beforeEach` (`:42-47`). (Task 4)
- **Environment, not a regression:** in a worktree without `.env`, `just test-api` fails 6 tests and errors 77 (`ValueError: VS_API_KEY_ADMIN must be set`) before any change. Run `scripts/worktree-setup.sh` (it writes a `.env` with a generated `VS_API_KEY_ADMIN`) or export `VS_API_KEY_ADMIN` first.
- Known load flakes from Story 17.4's notes: `InstallConfirmDialog`, `QuickInstallButton`, `SettingField` and `GameConfigPanel` each failed one test in a full `vitest run` under load and passed alone. If one fails in `just check`, re-run it before suspecting this story (but this story does touch `GameConfigPanel`: read the failure first).
- Anything else that fails is a regression (AC 10): fix the code, not the test.

### ADR against the code

ADR-4 is right about the bug and the decision. Two points are refined and one is added, and the story does the safer thing:

1. **Decision 3 ("when the resolved path is the game's `serverconfig.json`").** The story applies the rule to every file by content instead (Dev Notes "The file viewer", rule 2). A resolved-path comparison misses copies, `serverconfig.tmp` and a different letter case of the file name on a case-insensitive filesystem. The ADR lists copies under "Known limits, not solved here"; the content rule solves that one for the top-level key at no extra cost.
2. **Decision 3 ("a non-null value is replaced").** `""` is left as it is and reported as not configured: it holds no secret and is what "no password" looks like in older files.
3. **Not in the ADR:** a file that does not parse returns its whole text (`config_files.py:205`), for `serverconfig.json` and for game logs. The story withholds that text from roles other than Admin (rule 4).

### Not changed (do not "fix" these here)

- What Admin receives from any endpoint, apart from the added `secret: true`.
- `POST /config/game/settings/{key}` and its response (Admin only).
- Which files the viewer lists or can open, for either role; the 500 for a binary file.
- Monitor's editable-looking settings fields and their 403 on save.
- Secrets in other files beyond the top-level rule (nested keys, other key names).
- The API settings redaction (`ApiSettings.redacted()`, `services/api_settings.py:76-83`): same idea, separate code, already done (FR149).
- `sprint-status.yaml` is changed only by `just sprint set` in Task 5.

### API contract (`v1alpha1`)

- `GET /config/game`: each setting may carry `secret: true` (today: `Password`). For a key that is not Admin, a secret setting has `value: null` and `configured: true|false`. `configured` is absent from Admin responses and from settings that are not secret.
- `GET /config/files/{path}`: for a key that is not Admin, top-level secret keys with a value are `"[redacted]"`, and a file that is not valid JSON has `_raw: "[redacted]"`.
- Both responses send `Cache-Control: no-store`.
- This removes data from Monitor responses. That is the purpose (change proposal, "Risks").

### Testing Requirements

**CRITICAL:** Tests are written with each task and committed with it, red first. `just test-api <file>` / `just test-web <file>` after each task; `just check` before review.

- Every Monitor test for an endpoint asserts on the raw body (`SECRET not in response.text`), not only on the parsed field: a second copy of the value anywhere in the response must fail the test.
- Both roles for every endpoint in the tables; Admin assertions pin "unchanged".
- Tests write only under `tmp_path`; `git status --short` after `just test-api` must show nothing under `dev/`.
- Test passwords are made-up constants. No value from a real `serverconfig.json` goes into a test, a fixture, a log or the Dev Agent Record.

### Security Requirements

- Redacted is the default (AC 6): a new caller of `get_settings` or `read_file` that forgets the role cannot leak.
- The role comparison is `role == UserRole.ADMIN`; anything else, including an unknown string, is treated as not Admin.
- Do not log secret values: the existing `***` masking stays, now driven by `setting_def.secret`. Do not add the file content or `_raw` to any log line.
- No new endpoint, no change to authentication. RBAC patterns as in `project-context.md` "Security Patterns".
- The E2E spec and any manual check must not print, screenshot or record the stack's real password or server name.

### Development Commands

- `just test-api tests/test_routers_config.py tests/test_game_config.py tests/test_config_files.py`, `just test-web src/components/SecretSettingStatus.test.tsx src/features/game-server/GameConfigPanel.test.tsx src/api/config.test.ts src/components/FileViewer.test.tsx`, `just typecheck-api`, `just typecheck-web`, `just check`.
- Do not run `just format-api` (reformats unrelated files; Story 17.2 process note).

### Previous Story Intelligence

- **17.4:** a `feat`/`fix` commit subject must describe something an admin can see (its review L1); tests must not write into `dev/`; an E2E spec that touches real state needs a snapshot guard (this story's spec only reads, so it needs none, and must stay that way).
- **17.3:** tests must not read private members (`reportPrivateUsage`): test `_SECRET_KEYS_FOLDED` and `_is_json_object` through `is_secret_key` and `redact_secrets`. A hook's own `onError` replaces the query client's default (TanStack Query v5); this story adds no query or mutation.
- **17.1:** pyright strict, baseline 0 errors and 3 pre-existing warnings in tests. Keep each commit green.
- **16.8:** `ServerSetting` gained `nullable` and `clear_command` the same way `secret` is added now; the masked field and its tests (`SettingField.test.tsx:534-600`) are the Admin behavior AC 9 keeps. Its manual check restored `serverconfig.json` by SHA-1; this story's E2E only compares the SHA-1.
- **14.6 (FR149):** the webhook URL redaction (`TestModUpdateWebhookRedaction`, `tests/test_routers_config.py:655`) is the model for "report only whether it is configured" and for tests that an error does not echo a secret.

### Git Intelligence

- Recent commits are Story 17.4's (`bb3cf4d`, `2e06182`, `5b037a9`, `23ba067`, `47ae737`, `21457bf`). Release notes come from commit subjects (`cliff.toml`).
- Planned subjects:
  - Task 1: `fix(story-17.5/task-1): Monitor API keys can no longer read the game server password`. This is the security fix and the line release notes will show; keep the wording. Both endpoints are in this one commit so the sentence is true when it lands. The body names the two endpoints and `VSS-qed`.
  - Task 2: `test(story-17.5/task-2): every config endpoint is checked for the server password with a Monitor key`
  - Task 3: `fix(story-17.5/task-3): with a Monitor key, Game Settings shows whether a server password is set instead of a password field`
  - Task 4: `test(story-17.5/task-4): E2E for the server password with a Monitor key`
  - Task 5: `docs(story-17.5/task-5): validate and move story 17.5 to review`
- Do not put a password, a key or a server name in any commit message.

### Latest Technical Information

- No new libraries. FastAPI injects `response: Response` into a handler that returns a model; headers set on it are merged into the final response. `TypeGuard` is in `typing` (Python 3.14 here). TanStack Query needs no change: the settings query key (`queryKeys.config.game`) and its 30 s polling stay.

### Project Structure Notes

- New: `web/src/components/SecretSettingStatus.tsx`, `web/src/components/SecretSettingStatus.test.tsx`, `web/e2e/monitor-password-redaction.spec.ts`.
- Modified: `api/src/vintagestory_api/services/game_config.py`, `services/config_files.py`, `routers/config.py`; `api/tests/test_routers_config.py`, `test_game_config.py`, `test_config_files.py`; `web/src/api/types.ts`, `web/src/features/game-server/GameConfigPanel.tsx`, `GameConfigPanel.test.tsx`, `web/src/api/config.test.ts`, `web/src/components/FileViewer.test.tsx`, `web/e2e/settings-empty-values.spec.ts`.

### Follow-ups (not this story; for the maintainer to file, no bead is created here)

- Through `GET /config/files/{path}` a Monitor key can open any file under the server data directory, not only the `.json` files the listing shows (`read_file` has no suffix check). This story withholds the text of files that are not JSON; whether Monitor should be able to request them at all, and the 500 for binary files, is a separate decision.
- Secrets in other files or under other names: nested `Password` keys, tokens and webhook URLs in mod config files, `StartupCommands`.
- A Monitor sees the other game settings as editable fields that fail with 403 on save.
- `ServerIdentifier` / `VhIdentifier`: treated as identifiers, not secrets; confirm against the game's documentation.
- The existing E2E specs set `localStorage.apiKey`, which the web no longer reads.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 17.5: Monitor Keys Cannot Read the Server Password]
- [Source: _bmad-output/planning-artifacts/prd.md] FR186; FR21, FR22, FR32; FR149
- [Source: _bmad-output/planning-artifacts/architecture/epic-17-mod-data-fixes.md#ADR-4: Secrets in Config Responses Depend on the Role]
- [Source: _bmad-output/planning-artifacts/architecture/epic-16-ui-polish.md#ADR-3] (1280px settings panel; the status line sits in the Server Info card like any field)
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-15.md] (open question for 17.5; API contract changes; "the one change in this epic that removes data from a response")
- [Source: _bmad-output/implementation-artifacts/16-8-name-sort-and-empty-settings.md] (masked Password field; nullable settings)
- [Source: _bmad-output/implementation-artifacts/17-4-installed-status-is-right-everywhere.md] (Completion Notes, Senior Developer Review)
- [Source: agentdocs/vs-serverconfig-commands.md] (key list of `serverconfig.json`, `/serverconfig password`, `nopassword`)
- Beads: `VSS-qed`, parent `VSS-4v5`; found in Story 16.8 (`VSS-7ed`)
- `project-context.md` - critical implementation rules (Security Patterns; no suppressions; manual test tasks need the user's confirmation)

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5)

### Debug Log References

- Started from `story/17-7-mods-navigation` at 314d36d (Story 17.7 done), which stacks on Story 17.4. Story 17.7 changed only web mods navigation files, so every API line reference in the story (written at 21457bf) still matched; the web references (`GameConfigPanel.tsx`, `types.ts`, `SettingField.tsx`, `FileViewer.tsx`) were re-read before Task 3.

### Completion Notes List

- Story created 2026-11-15: context analysis of `routers/config.py`, `services/game_config.py`, `services/config_files.py`, the auth and permission dependencies, every router and WebSocket for a path to the password, `SettingField`, `GameConfigPanel`, the file viewer components, the web key source (`/config.js`), the E2E specs' authentication, Story 16.8 and the reviews of 17.1-17.4. Task 1 was prototyped in the worktree and the API suite run against it (2525 passed, nothing broke); the helper code in Dev Notes was type-checked under pyright strict; the prototype was discarded.
- Task 1: `ServerSetting.secret` (default `False`, `True` on `Password` only); `REDACTED`, `SECRET_SETTING_KEYS`, `is_secret_key`, `has_secret_value`, `redact_secrets` and the `TypeGuard` `_is_json_object` exactly as in Dev Notes; `SettingInfo` gained `secret`/`configured` (`to_dict` adds `secret: true` only when set, `configured` whenever it is not `None`). `get_settings(role=None)`: for a secret setting and any role but `UserRole.ADMIN`, `value` is `None` and `configured` is whether any key equal to `Password` without regard to case has a value; Admin reads `config.get(key)` as before. The two log guards now test `setting_def.secret`. `read_file(filename, role=None)` reads the file once, redacts top-level secret keys for any role but Admin, and returns `_raw: "[redacted]"` (with `_parse_error`) for a file that does not parse; `import json` is at the module top. Both routes take `role: RequireAuth` and `response: Response`, pass the role on and set `Cache-Control: no-store` (successful responses; the 404/400 error bodies carry no content). Tests: `test_game_config.py` (`TestServerSettingModel` 2 new, `TestSecretHelpers`, `TestSettingInfoSecretFields`, `TestGetSettingsSecrets`: roles `None`, `"monitor"`, `""`, `"ADMIN"`, `"Admin"`, `"someone"` redacted, only `"admin"` not; `null`/`""`/missing; lower-case `password`; other settings equal for both roles), `test_config_files.py` (`test_read_file_invalid_json` split into the Admin and no-role cases; `TestReadFileSecrets`: `serverconfig.json`, `./serverconfig.json`, `ModConfig/../serverconfig.json` and a symlink, for the same roles; unset values; a broken file), `test_routers_config.py` (`TestGetGameSettingsSecrets`, `TestReadConfigFileSecrets`: every row of the Task 1 table, raw-body `SECRET not in response.text`, `no-store` for both keys). Red first: the router tests failed (17) and the service test modules did not import. The three files: 270 passed; ruff clean; pyright 0 errors, the 3 pre-existing warnings.
- Task 2: tests only, in `test_routers_config.py` `TestOtherConfigPathsWithAPassword` (password set in `serverconfig.json` and in `ModConfig/copy.json`): a Monitor `POST /config/game/settings/Password` gets 403 `FORBIDDEN`, its body does not contain the password and the file is byte-identical; the Admin update answers 200 with the new `value` (AC 5); `GET /config/files` and `/config/directories`, with and without `?directory=ModConfig`, answer 200 without the password; the sweep requests every Monitor `GET` route under `/config` (`/game`, `/files`, `/directories`, `/files/serverconfig.json`, `/files/ModConfig/copy.json`) and checks `/config/api` is 403, and it compares the hand-written list with the `GET` paths under `/api/v1alpha1/config` in the app's OpenAPI schema, so a new route fails the test until it is added. (FastAPI 0.162 keeps included routers as `_IncludedRouter` objects, so `app.routes` does not list the API routes; the OpenAPI paths do, with `{filename:path}` shown as `{filename}`.) No source change was needed: every test passed against the Task 1 code. 2.2: `rg -n "RequireAuth|get_current_user|RequireAdmin|RequireConsoleAccess|websocket\(" api/src/vintagestory_api/routers` and `rg -n "@router\.|@ws_router\.|include_router" api/src/vintagestory_api` on this branch: the routes are the ones the table lists (Stories 17.4 and 17.7 added none); `/versions` and `/mods` reads are any-role and carry no config values (only `services/mods.py` touches `serverdata_dir`, for `Mods/`); `/test/*` is mounted only with `VS_DEBUG`; there is no custom exception handler, so a 500 (a binary file, a directory requested as a file) carries only "Internal Server Error". `ServerService.send_command` logs only failure reasons, never the command. The table holds. One related observation outside the table: `/config.js` serves the web UI's key (`VS_API_KEY`, or the Admin key when it is unset) to anyone who can reach the web origin, without a key (Epic 15 ADR-5, by design: the origin is expected to be protected). It needs no Monitor key, so it is not a Monitor path, but a deployment that hands out Monitor keys while the web origin is reachable gives the web's key, by default the Admin key, to the same people; recorded for the maintainer, not changed.
- Task 3: `GameSetting` gained `secret?` and `configured?` (comments as in 3.1; the `value` comment says null also when withheld). New `SecretSettingStatus` (label in a `span` inside the same label row as `SettingField`, "Set"/"Not set", the help line; no input, no button, no hook). `GameConfigPanel.renderSetting` renders it when `setting.configured !== undefined`; the masked Admin field is unchanged. The single-word fields need no case transform. Tests: `SecretSettingStatus.test.tsx` (new, 5), `GameConfigPanel.test.tsx` "Story 17.5: secret settings" (Monitor "Set" and "Not set": no `#Password`, no "Show password"; Admin with a value: masked input with the value and "Show password"; Admin with `value: null`: empty masked input, no "Not set"; the other settings are fields in every case), `config.test.ts` (`secret`/`configured` reach the caller), `FileViewer.test.tsx` (`"Password": "[redacted]"` shown as a string). Red first: the two Monitor panel tests failed and `SecretSettingStatus.test.tsx` did not import; the `config.test.ts` case passes at run time but its fixture did not type-check before 3.1; the `FileViewer` case passes against the unchanged viewer, as the story expects. The four files: 122 passed; `just typecheck-web` and `just lint-web` clean.
- Task 4: `web/e2e/monitor-password-redaction.spec.ts` with the four tests of Dev Notes "E2E" (test 3 runs for `configured` true and false, each at 1440x900 and 390x844: the status box lies inside the Server Info card and `game-config-panel` has no horizontal overflow). Every test sets the page's key by answering `/config.js`; the password is compared only through `includes`/`===` booleans, never `toContain`. `settings-empty-values.spec.ts` gets the same `/config.js` route with the Admin key in its `beforeEach`. Deviation: `settings-desktop-layout.spec.ts` gets it too (in `open`), because it measures `#Password` (`:114`), which only exists for an Admin key; the story listed only `settings-empty-values.spec.ts`. On this stack the web's `VS_API_KEY` is the Admin key, so neither spec failed before the change; the route makes them independent of it. Run: `serverconfig.json` SHA-1 recorded and the game server state read (`installed`, not running); `just docker restart` rebuilt the image from this branch (`Cache-Control: no-store` on the live `/config/game` confirmed the new code); `bunx playwright test` with `VS_API_KEY_ADMIN`/`VS_API_KEY_MONITOR` exported from `.env` (values not printed): the new spec, `settings-empty-values`, `settings-desktop-layout` and `file-browser-navigation`: 17 passed, none skipped. Afterwards `serverconfig.json` has the same SHA-1, the game server is still `installed` (not started or stopped), the stack is left running, no screenshot was written and no tracked Playwright file changed. The stack has no server password set, so the E2E's value comparison (password of 8+ characters) did not apply there; the by-hand check below covers a set value.
- By-hand check against the rebuilt stack (keys from `.env` in the environment, no value printed; script in the session scratchpad, not committed). The stack's `Password` is `null`. Monitor key: `GET /config/game` 200, Password `value: null`, `secret: true`, `configured: false`, `no-store`; `GET /config/files/serverconfig.json`, `./serverconfig.json` and `SERVERCONFIG.JSON` (the bind mount ignores case) 200 with `Password: null`, `no-store`; `serverconfig.tmp` 404; `Logs/server-main.log`, `server-audit.log`, `server-debug.log` 200 with `_raw: "[redacted]"`; `/config/files`, `/config/directories`, `/auth/me`, `/auth/ws-token`, `/server/status`, `/server/install/status`, `/mods`, `/mods/updates`, `/versions`, `/healthz`, `/readyz` 200; `/config/api`, `POST /config/game/settings/Password`, `/console/history`, `/console/logs`, `POST /console/command`, `/jobs`, `/debug`, `/metrics/current`, `/metrics/history` 403; no body contained a password. Admin key: `/config/game` Password value equals the file's value (fields `key`, `value`, `type`, `live_update`, `env_managed`, `secret`; no `configured`); `/config/files/serverconfig.json` Password equals the file's; `Logs/server-main.log` `_raw` is the log text. Because no password is set on the stack, a set value was checked with two throwaway files in `data/serverdata` holding a random made-up password (`Password` and `password` keys; and a copy that does not parse), removed right after: Monitor got `"[redacted]"` for both keys and `_raw: "[redacted]"`, the value in neither body; Admin got the value in both. `serverconfig.json` SHA-1 unchanged after all checks.
- Task 5: `just check` passed: ruff clean; pyright 0 errors, 3 warnings (the same pre-existing three in tests); `just test-api` 2624 passed; `just test-web` 129 files, 3219 passed, 4 skipped, no failures (none of the known load flakes appeared); script tests 23/23, 6/6, 12/12, 126/126, 23/23. `dev/` holds no file afterwards and `git status` shows nothing under `dev/`. The diff adds no lint or type suppression, no `cast` and no type assertion. Story status `review`; `just sprint set 17-5-monitor-keys-cannot-read-the-server-password review`.
- Additional leak paths: none found beyond the story's table. The by-hand sweep also covered `/auth/ws-token`, `/mods/updates`, `/versions`, `/jobs`, `/debug`, `/metrics/*`, `/healthz`, `/readyz` and three game logs, and the WebSockets are covered by the cited tests. The one related finding is `/config.js` (Task 2 note): it is unauthenticated and serves the web's key, by default the Admin key, so a deployment must protect the web origin; not a Monitor-key path, not changed here.
- Deviations: (1) Branch and PR base: the branch starts from Story 17.7's branch (`story/17-7-mods-navigation`, which stacks on Story 17.4), and the PR is stacked on Story 17.7's PR (#160), not on `story/17-4-installed-status-is-right-everywhere` as Task 5.2 says; Story 17.7 touched only web mods navigation, so no line reference changed. (2) `settings-desktop-layout.spec.ts` also gets the Admin `/config.js` route (Task 4 note); the story listed only `settings-empty-values.spec.ts`. (3) The Task 2 sweep compares its route list with the app's OpenAPI paths, because FastAPI 0.162 does not expose included routes through `app.routes`. (4) The `Cache-Control: no-store` header is set on the successful responses of both endpoints; their 400/404 error responses carry no file content and are unchanged. No other story instruction was wrong against the code.
- Follow-up beads (the story's "Follow-ups", filed at the maintainer's request, each `discovered-from` `VSS-qed`): `VSS-633` [API-077] the config file viewer opens any file under serverdata, not only JSON, and binary files return 500 (P2); `VSS-sg1` [API-078] secrets under other key names or nested in config files are not redacted for Monitor keys (P3); `VSS-7z3` [UI-084] a Monitor key sees editable game setting fields that fail with 403 on save (P3). Not filed: `ServerIdentifier`/`VhIdentifier` (left visible by the story's analysis) and the E2E specs' unused `localStorage.apiKey` (test hygiene).

### File List

- `api/src/vintagestory_api/services/game_config.py`
- `api/src/vintagestory_api/services/config_files.py`
- `api/src/vintagestory_api/routers/config.py`
- `api/tests/test_game_config.py`
- `api/tests/test_config_files.py`
- `api/tests/test_routers_config.py`
- `web/src/api/types.ts`
- `web/src/api/config.test.ts`
- `web/src/components/SecretSettingStatus.tsx` (new)
- `web/src/components/SecretSettingStatus.test.tsx` (new)
- `web/src/components/FileViewer.test.tsx`
- `web/src/features/game-server/GameConfigPanel.tsx`
- `web/src/features/game-server/GameConfigPanel.test.tsx`
- `web/e2e/monitor-password-redaction.spec.ts` (new)
- `web/e2e/settings-empty-values.spec.ts`
- `web/e2e/settings-desktop-layout.spec.ts`

## Change Log

- 2026-11-15: Story 17.5 created (ready-for-dev).
- 2026-11-15: Validated against the create-story checklist: every cited path and line re-read at 21457bf; the redaction helper rewritten without `cast` after pyright strict reported unknown-type warnings for a plain `isinstance` check; the console rows of the path table re-pointed at the tests of the real console endpoints (the first draft cited tests of the debug-only `/test/console` route); the file viewer rule widened from "the resolved `serverconfig.json`" to every file by content, and unparseable files added, after reading `read_file`; `/config.js` routing added to the E2E plan after finding that the web does not read `localStorage`; the worktree `.env` note added after the baseline run failed for environment reasons.
- 2026-11-15: Story 17.5 implemented (review). A Monitor key no longer receives the game server password: `GET /config/game` returns Password with `value: null`, `secret: true` and `configured`; the config file viewer returns `"[redacted]"` for every top-level Password key (any letter case, every file) and withholds the text of files that are not valid JSON; both send `Cache-Control: no-store`; Admin is unchanged apart from `secret: true`. Game Settings shows "Set"/"Not set" to a Monitor key. New API and web unit tests, a sweep of every Monitor config route, a new E2E spec; follow-ups filed as `VSS-633`, `VSS-sg1`, `VSS-7z3`.
