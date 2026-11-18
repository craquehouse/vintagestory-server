# Story 21.3: A Working `VS_LOG_LEVEL` and Config Viewer Edge Cases

Status: review

<!-- Implements FR266-FR270, Epic 21 ADR-4 and ADR-5. Beads: VSS-wv0w (API-096); maintainer decision 3 (VS_LOG_LEVEL, Matt, 2026-11-17). Stories run in order 21.1 to 21.8, each stacked on the previous; this story touches no file under web/ and needs no other story's code (epics.md, Epic 21 "Order"). Line references were verified at 966204f (epic-21-planning; its api/ is identical to 05436da, the commit the ADRs cite) and must be re-checked at implementation time. API change and documentation only; no web source change, no E2E spec. No new dependencies. -->

## Story

As an **operator**,
I want **to set the API's log level with `VS_LOG_LEVEL`, and the config file viewer to behave the same in its edge cases**,
so that **I can have quieter or more detailed logs without debug mode, and read-only keys see neither webhook secrets nor wrong answers**.

## Acceptance Criteria

1. **Given** `VS_LOG_LEVEL=warning` (any letter case, surrounding spaces allowed) and `VS_DEBUG` unset
   **When** the API starts
   **Then** the level set is `WARNING`: DEBUG and INFO lines are not written, WARNING and ERROR lines are, in JSON. The `api_starting` line is an INFO line, so at this level it is not written; at every level that writes it (`DEBUG`, `INFO`) its `log_level` field is the level actually set, not one derived from `VS_DEBUG`
   *(Covers FR266; ADR-4 decisions 2 and 4; see "ADR against the code" 1)*

2. **Given** `VS_LOG_LEVEL` unset, empty or blank
   **When** the API starts
   **Then** the level is DEBUG with `VS_DEBUG=true` and INFO otherwise, as before, with the console renderer in debug mode and JSON otherwise
   *(Covers FR266; Matt, 2026-11-17)*

3. **Given** `VS_DEBUG=true` and `VS_LOG_LEVEL=INFO`
   **When** the API starts
   **Then** the level is INFO, the console renderer is used, `GET /debug` reports `debug_enabled: true`, and `/docs` and the RBAC test routes are served as in any debug mode
   *(Covers FR266; ADR-4 decision 2)*

4. **Given** `VS_LOG_LEVEL=DEBUG` and `VS_DEBUG` unset
   **When** the API starts
   **Then** DEBUG lines are written in JSON, and `/docs` and the RBAC test routes are not served (404)
   *(Covers FR266)*

5. **Given** `VS_LOG_LEVEL=verbose` (or `warn`, `trace`, `CRITICAL`, `10`)
   **When** the settings are read (the API builds them at import, `main.py:420`)
   **Then** start-up stops with a validation error whose text contains `VS_LOG_LEVEL must be one of: DEBUG, INFO, WARNING, ERROR.` and does not contain the value
   *(Covers FR267; Matt, 2026-11-17)*

6. **Given** `VS_LOG_LEVEL=WARNING` and a running API
   **When** an Admin turns debug logging on (`POST /api/v1alpha1/debug/enable`) and then off (`POST /api/v1alpha1/debug/disable`)
   **Then** the level is DEBUG while it is on and WARNING after it is turned off; both responses are `{"status": "ok", "data": {"debug_enabled": <bool>, "changed": true}}` with exactly those keys, and `GET /debug` is `{"debug_enabled": <bool>}` as today. Without `VS_LOG_LEVEL`, off returns to INFO as today
   *(Covers FR267; ADR-4 decision 3)*

7. **Given** `VS_DEBUG=true` and `VS_LOG_LEVEL=WARNING` (debug mode with quiet logs)
   **When** an Admin calls `POST /debug/enable`
   **Then** the level becomes DEBUG and the response is `{"debug_enabled": true, "changed": true}` (the level changed although the debug state did not); a second call answers `changed: false`
   *(Covers FR267; ADR-4 decision 3; Dev Notes "The switch", story decision)*

8. **Given** `VS_DEBUG=on` (or any other value pydantic reads as true: `true`, `1`, `yes`, `y`, `t`, any letter case)
   **When** the API starts
   **Then** logging is in debug mode (DEBUG, console renderer, `debug_enabled: true`), as `/docs` already is: `VS_DEBUG` is parsed once, by the settings
   *(Covers FR267; ADR-4 decision 6)*

9. **Given** the README's configuration table, `.env.example`, the environment table in `architecture/project-structure-boundaries.md` and the Logging section of `project-context.md`
   **When** I read them
   **Then** each describes `VS_LOG_LEVEL`: the four values, that letter case does not matter, the default, what the debug switch does to it, that only the API's own lines follow it (not uvicorn's), and that any other value stops start-up; `project-context.md` no longer describes the old behaviour as the whole story, and `project-structure-boundaries.md` no longer says nothing reads it
   *(Covers FR267; ADR-4 decisions 5 and 7)*

10. **Given** a config file with the value `https://ptb.discord.com/api/webhooks/1/abc` or `https://canary.discord.com/api/webhooks/1/abc` (any letter case in the host)
    **When** a Monitor key reads the file
    **Then** the value is `[redacted]`, as for `discord.com` and `discordapp.com`; an Admin key gets it unchanged; and the API has one definition of the four hosts, used by the redaction rule and by the webhook sender
    *(Covers FR268; `VSS-wv0w`; ADR-5 decision 1)*

11. **Given** a directory symlink, or a `.json` file symlink, inside the server data directory (in the root or in `ModConfig`) that resolves outside it
    **When** an Admin key or a Monitor key lists the directory that holds it (`GET /config/directories`, `GET /config/files`)
    **Then** the entry is not in the listing; what Admin may open does not change (reading through the link is still 400 `CONFIG_PATH_INVALID`)
    *(Covers FR269; `VSS-wv0w`; ADR-5 decision 2)*

12. **Given** the server data directory does not exist
    **When** a Monitor key lists a directory it may not see (for example `Playerdata`) with either listing route
    **Then** the answer is 403 `FORBIDDEN` with the message `This directory needs the Admin role: Playerdata`, as when the data directory exists; a path traversal (`../x`) is 400 for every role; a request for the root or `ModConfig`, and any Admin request inside the data directory, still answers 200 with an empty list
    *(Covers FR270; `VSS-wv0w`; ADR-5 decision 3)*

13. **Given** every existing test
    **When** the suites run
    **Then** they pass, apart from the changes listed in Dev Notes "Existing tests that change"; no test run writes into `dev/`; a developer's `.env` that sets `VS_LOG_LEVEL` does not change any test's result

## Tasks / Subtasks

<!-- Each functional task includes its tests in the same commit, red first. Commit names: type(story-21.3/task-N): ...; the two fix commits and the feat commit use the release-note subjects of the change proposal (section 2) with the `api` scope, which RELEASING.md:26 shows in the release notes. -->

- [x] Task 1: `VS_LOG_LEVEL` sets the level, `VS_DEBUG` is parsed once, and the debug switch keeps its meaning + tests (AC: 1-8, 13)
  - [x] 1.1: `config.py` `Settings`: a `field_validator("log_level")` after `validate_csp_mode` (`:121-133`), shaped like it (Dev Notes "The validator"). The field stays `log_level: str | None = None` (`:40`); update its comment to point at Epic 21 ADR-4. A module constant `LOG_LEVELS: tuple[str, ...] = ("DEBUG", "INFO", "WARNING", "ERROR")` and the message `"VS_LOG_LEVEL must be one of: DEBUG, INFO, WARNING, ERROR."`
  - [x] 1.2: `config.py` debug state (`:295-368`): delete `_read_debug_from_env` (`:301-309`); add `_configured_log_level: str | None = None` and `_current_log_level: str = "INFO"` beside `_debug_enabled` (`:297-298`); `initialize_debug_state(debug: bool, log_level: str | None) -> None` (`:312-325`) keeps its once-guard, remembers both, applies `log_level or ("DEBUG" if debug else "INFO")`; a new public `current_log_level() -> str`; `set_debug_enabled` (`:337-356`) as in Dev Notes "The switch"; `reconfigure_logging_if_changed` (`:439-475`) passes `log_level=_current_log_level`. `configure_logging` (`:371-432`) keeps its signature and body; fix its docstring's "Runtime Debug Toggle" paragraph (`:386-389`, which says it checks the `VS_DEBUG` environment variable) and the comment at `:295-296`
  - [x] 1.3: `main.py` lifespan (`:157-172`): `initialize_debug_state(settings.debug, settings.log_level)` (`:160`; update the comment at `:158-159`); the `api_starting` line's `log_level=current_log_level()` (`:170`); import `current_log_level` in the `config` import block (`:16-21`, alphabetical)
  - [x] 1.4: `api/tests/conftest.py`: after the `VS_MOD_DB_URL` pop (`:12-14`), `os.environ.pop("VS_LOG_LEVEL", None)` with a one-line comment (a developer's `.env`, loaded by mise, must not change test results; AC 13)
  - [x] 1.5: Tests (Dev Notes "API tests", Task 1 rows) and the rewrites in "Existing tests that change", red first
  - [x] 1.6: Commit `feat(api): VS_LOG_LEVEL sets the log level` (the body names Story 21.3 / task 1 and says that a value other than the four now stops start-up)

- [x] Task 2: Document `VS_LOG_LEVEL` (AC: 9)
  - [x] 2.1: `README.md` Configuration table (`:78-90`): a `VS_LOG_LEVEL` row directly after `VS_DEBUG` (`:83`), text in Dev Notes "Documentation text"
  - [x] 2.2: `.env.example`: a commented block after `VS_DEBUG` (`:25-30`), before `VS_CSP_MODE`, in the style of the `VS_CSP_MODE` block (`:32-39`)
  - [x] 2.3: `_bmad-output/planning-artifacts/architecture/project-structure-boundaries.md`: a `VS_LOG_LEVEL` row after `VS_DEBUG` (`:485`); in `:488` drop the sentence saying nothing reads `Settings.log_level`
  - [x] 2.4: `project-context.md` "Logging Conventions" → "Configuration" (`:396-404`): replace the two bullet lists with the text in Dev Notes "Documentation text" (the `VS_LOG_LEVEL` bullet at `:400` is wrong today: nothing reads it)
  - [x] 2.5: Commit `docs(story-21.3/task-2): document VS_LOG_LEVEL`

- [x] Task 3: One set of Discord hosts for redaction and for the webhook sender + tests (AC: 10, 13) (`VSS-wv0w`)
  - [x] 3.1: `services/game_config.py`: delete `_DISCORD_WEBHOOK_HOSTS` (`:238`); import `DISCORD_HOSTS` from `vintagestory_api.services.mod_update_alerts` (import block `:22-25`) and use it in `is_secret_value` (`:294`); its docstring (`:278-282`) names the four hosts by pointing at `DISCORD_HOSTS`. `mod_update_alerts.DISCORD_HOSTS` (`:20-22`) stays the one definition; give it a docstring saying both the sender and the redaction rule use it (Dev Notes "One set of hosts")
  - [x] 3.2: `services/config_files.py` module docstring (`:20-26`): "a Discord webhook URL" stays; nothing else in that file changes in this task
  - [x] 3.3: Tests (Dev Notes "API tests", Task 3 rows), red first
  - [x] 3.4: Commit `fix(api): hide Discord webhook URLs on ptb and canary hosts from read-only keys`

- [x] Task 4: Listings leave out entries outside the data directory, and the path and role checks run first + tests (AC: 11, 12, 13) (`VSS-wv0w`)
  - [x] 4.1: `services/config_files.py` `_role_may_open` (`:223-240`): move the containment check (`:232-234`) above the Admin return (`:230-231`); docstring: nothing outside the server data directory, for any role (Epic 21 ADR-5 decision 2). `read_file` (`:349`) already refuses such a path earlier, in `_safe_path`, so reads do not change
  - [x] 4.2: `list_files` (`:301-347`): drop the now redundant `f.resolve().is_relative_to(base_resolved)` clause (`:342`) and the `base_resolved` local (`:337`) it used; `list_directories`' filter (`:292-296`) needs no edit (it already calls `_role_may_open`)
  - [x] 4.3: Remove the `serverdata_dir.exists()` shortcuts in `list_directories` (`:282-284`) and `list_files` (`:326-328`) and the then unused `serverdata_dir` locals; `_target_directory` (`:242-258`) checks the root's existence too (Dev Notes "Missing data directory"). Keep the `serverdata_dir_not_found` debug event for a missing root
  - [x] 4.4: Docstrings: `list_directories` and `list_files` (Returns/Raises: an empty list only for an allowed directory that does not exist; entries resolving outside the data directory are never listed); `routers/config.py` module docstring (`:26-28`) and the two listing routes (`:411-438`, `:459-490`): entries resolving outside the server data directory are not listed for any role; 403 holds whether or not the data directory exists. These docstrings are the routes' OpenAPI text
  - [x] 4.5: Tests (Dev Notes "API tests", Task 4 rows), red first
  - [x] 4.6: Commit `fix(api): leave links that point outside the data directory out of the config file listing` (the body also names the 403 correction, which the web UI never meets)

- [ ] Task 5: Quality gate and review hand-off (AC: all)
  - [x] 5.1: `ruff format` on every API file this story changes (not `just format-api` on the tree); `just check` passes; the diff adds no lint or type suppression and no `cast`; pyright stays at 0 errors and the pre-existing warnings (`VSS-1ar`); after `just test-api`, `git status --short` shows nothing under `dev/`
  - [ ] 5.2: Manual check: none required (Dev Notes "Manual check"); if the maintainer wants one, he does it
  - [ ] 5.3: Story status `review`, `just sprint set 21-3-log-level-and-config-viewer review`, PR against `main` (or the previous story's branch while its PR is open); the PR description lists "API contract changes" from this story; PR link on `VSS-wv0w`

## Dev Notes

### The code today (verified at 966204f)

- `Settings.log_level: str | None = None` (`config.py:40`) is read from `VS_LOG_LEVEL` and nothing reads it (`rg log_level api/src` finds only `config.py` and the hard-coded `log_level=` in `main.py:170`).
- `initialize_debug_state()` (`config.py:312-325`) reads `VS_DEBUG` itself (`_read_debug_from_env`, `:301-309`: `true`, `1`, `yes`, after `lower()`) and calls `configure_logging(debug=...)` with no level. It runs once per process (`_debug_initialized`, `:298`, `:322`). The lifespan calls it first (`main.py:160`); `api_starting` (`:167-172`) writes `"DEBUG" if debug_enabled else "INFO"`.
- **`VS_DEBUG` is parsed twice with different rules.** `Settings.debug` (`:39`) is pydantic's bool: `true/1/yes/on/t/y` and `false/0/no/off/f/n`, any case; any other value fails validation and the API does not start. It decides `/docs`, `/redoc`, `/openapi.json` (`main.py:350-352`), the RBAC test routes (`:401`) and a plain-HTTP `VS_MOD_DB_URL` (`config.py:163`). So today `VS_DEBUG=on` serves `/docs` while logging stays INFO in JSON. After this story the settings' parse is the only one (ADR-4 decision 6).
- `configure_logging(debug, log_level)` (`:371-432`) already accepts a level and silently falls back on an unknown one (`:392-397`); `debug` picks the renderer (console `:407-419`, JSON `:420-432`). It stays as it is: the validator guarantees one of four valid names.
- The switch: `routers/debug.py:38-77`, Admin only. `set_debug_enabled` (`:337-356`) calls `configure_logging(debug=enabled)`, which flips both the level and the renderer; the renderer part does not change in this story. The web's API Settings panel (`web/src/features/settings/ApiSettingsPanel.tsx:68-72`) only toasts on `changed`; it is a switch, so it sends `enable` only when it shows "off".
- `reconfigure_logging_if_changed` (`:439-475`) has no caller in `api/src` (only tests). ADR-4 decision 4 asks that it use the configured level; it is kept and updated, and its removal is a follow-up.

### The validator (Task 1.1)

```python
LOG_LEVELS: tuple[str, ...] = ("DEBUG", "INFO", "WARNING", "ERROR")
_LOG_LEVEL_INVALID = "VS_LOG_LEVEL must be one of: DEBUG, INFO, WARNING, ERROR."

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str | None) -> str | None:
        """Normalize VS_LOG_LEVEL; blank means unset, anything but the four levels an error.

        A plain str rather than a Literal, so the error names VS_LOG_LEVEL (Epic 21 ADR-4).
        """
        if v is None:
            return None
        level = v.strip().upper()
        if not level:
            return None
        if level not in LOG_LEVELS:
            raise ValueError(_LOG_LEVEL_INVALID)
        return level
```

- `hide_input_in_errors=True` (`:37`) keeps the value out of the error (prototype: `VS_LOG_LEVEL=verbose` gave `Value error, VS_LOG_LEVEL must be one of: DEBUG, INFO, WARNING, ERROR. [type=value_error]` and no value; `" Warning "` gave `'WARNING'`).
- `CRITICAL` is a Python level but not one of the four (maintainer's list); it is refused, and a test says so.
- pydantic-settings passes an empty `VS_LOG_LEVEL=` as `""` (no `env_ignore_empty`), so the blank branch is reached; test both `""` and `"   "`.

### Start-up and the switch (Task 1.2, 1.3)

```python
_debug_enabled: bool = False
_debug_initialized: bool = False
_configured_log_level: str | None = None  # VS_LOG_LEVEL, validated; None when unset
_current_log_level: str = "INFO"          # the level structlog filters at now


def initialize_debug_state(debug: bool, log_level: str | None) -> None:
    """Apply the settings' debug flag and log level once, at start-up (Epic 21 ADR-4)."""
    global _debug_enabled, _debug_initialized, _configured_log_level, _current_log_level
    if _debug_initialized:
        return
    _debug_enabled = debug
    _configured_log_level = log_level
    _current_log_level = log_level or ("DEBUG" if debug else "INFO")
    _debug_initialized = True
    configure_logging(debug=debug, log_level=_current_log_level)


def current_log_level() -> str:
    """The level the API's log lines are filtered at now."""
    return _current_log_level
```

**The switch.** `set_debug_enabled(enabled)`:

```python
    global _debug_enabled, _current_log_level
    level = "DEBUG" if enabled else (_configured_log_level or "INFO")
    if _debug_enabled == enabled and _current_log_level == level:
        return False
    previous = _debug_enabled
    _debug_enabled = enabled
    _current_log_level = level
    configure_logging(debug=enabled, log_level=level)
    structlog.get_logger().info("debug_logging_toggled", previous=previous, current=enabled)
    return True
```

- On: DEBUG, always (ADR-4 decision 3). Off: `VS_LOG_LEVEL` when set, INFO otherwise.
- **Story decision (AC 7).** ADR-4 does not say what `enable` does when the debug state is already on but the level is not DEBUG (`VS_DEBUG=true` with `VS_LOG_LEVEL=WARNING`). Comparing only the debug state, as today, would answer `changed: false` and leave WARNING: a switch for "debug logging" that gives no debug lines. So `changed` is true when the debug state **or** the level changes. The response keys do not change. The web cannot hit this case from its switch (it shows "on" and offers only "off"), so it only matters to API clients; listed under "API contract changes".
- The `debug_logging_toggled` line is INFO: after `disable` with `VS_LOG_LEVEL=WARNING` it is filtered out. That is the configured level working; the router's own `debug_logging_api_*` lines are INFO too. Not changed.
- `reconfigure_logging_if_changed` (`:439-475`): `configure_logging(debug=current_debug, log_level=_current_log_level)`. Its existing tests keep passing (`test_config.py:937-975`).
- The once-guard stays: every lifespan in the test suite would otherwise reset the debug state. Tests that need a fresh state reset the four module names with `monkeypatch.setattr(config_module, "_debug_initialized", False)` and so on (a string attribute name is not a private-usage report, and monkeypatch restores it). Do not add `# pyright: ignore` comments.

### One set of hosts (Task 3)

- `services/mod_update_alerts.py:20-22` already holds the four hosts (`discord.com`, `discordapp.com`, `ptb.discord.com`, `canary.discord.com`) as public `DISCORD_HOSTS`; `game_config.py` imports it. `mod_update_alerts` imports only `httpx`, `structlog` and `models.mod_updates` (which imports `models.moddb`), none of which imports `game_config`: no cycle (prototype: `python -I -c "import vintagestory_api.services.game_config"` and the whole suite passed). A new module was considered and is not needed (ADR-5 decision 1 leaves the place to the story).
- `is_secret_value` keeps its own shape (`:277-296`: scheme and netloc required, user info, then host in the set and path under `/api/webhooks/`); only the set changes. `is_discord_webhook` (`mod_update_alerts.py:35-39`) does not change.
- `is_secret_value` is used only through `redact_secrets` by the config file viewer (`services/config_files.py:454`), so the change reaches `GET /config/files/{path}` for roles other than Admin and nothing else.

### Listing outside the data directory (Task 4.1, 4.2)

- `_role_may_open` returns `True` for Admin at `:230-231` before the containment check at `:232-234`; `list_directories` filters only through it (`:292-296`). So an Admin listing shows a directory symlink that resolves outside; opening it is 400 from `_safe_path` (`:185-221`). Moving the containment check first makes every role's listing contain only entries inside the data directory, which is what ADR-5 decision 2 asks ("before the Admin shortcut").
- `read_file` (`:349`) calls `_safe_path` first, which already refuses anything resolving outside, so the move changes no read.
- `list_files` already filters every role by `f.resolve().is_relative_to(base_resolved)` (`:342`); see "ADR against the code" 2. With the check inside `_role_may_open` that clause is redundant; drop it so there is one rule.

### Missing data directory (Task 4.3)

```python
    def _target_directory(self, directory: str | None, role: str | None) -> Path | None:
        serverdata_dir = self.settings.serverdata_dir
        if not directory:
            target_dir = serverdata_dir.resolve()
        else:
            target_dir = self._safe_path(serverdata_dir, directory)
            if not self._role_may_open(target_dir, role, file_request=False):
                raise ConfigDirectoryForbiddenError(directory)
        if not target_dir.is_dir():
            logger.debug(... "serverdata_dir_not_found" for the root, "config_subdir_not_found" otherwise ...)
            return None
        return target_dir
```

- `_safe_path` uses `Path.resolve()` (non-strict), so it works when the data directory is missing; the traversal check and the role check then run before any existence check (ADR-5 decision 3).
- Prototype with the data directory missing: Monitor `None` and `ModConfig` → `[]`; Monitor `Playerdata` → `ConfigDirectoryForbiddenError`; Monitor `../x` → `ConfigPathInvalidError`; Admin `Playerdata` → `[]`. With it present, an Admin root listing with `esc -> <outside dir>` gave `['ModConfig']`.

### API tests

| Task | File | Test |
|---|---|---|
| 1 | `tests/test_config.py`, new `TestLogLevel` after `TestCspMode` (`:425-463`, same style with `monkeypatch.setenv`) | unset → `None`; `""` and `"   "` → `None`; `debug`, `Info`, `WARNING`, ` eRRoR ` → the upper-case name; `verbose`, `warn`, `trace`, `CRITICAL`, `10` → `ValidationError` containing the message; a value like `secret-looking-level` does not appear in the error text |
| 1 | `tests/test_runtime_debug_toggle.py`, new `TestConfiguredLogLevel` with an autouse fixture that `monkeypatch.setattr`s `_debug_enabled=False`, `_debug_initialized=False`, `_configured_log_level=None`, `_current_log_level="INFO"` | Parametrized over `(debug, log_level, expected_level, renderer)`: `(False, None, INFO, json)`, `(True, None, DEBUG, console)`, `(False, "WARNING", WARNING, json)`, `(True, "INFO", INFO, console)`, `(False, "DEBUG", DEBUG, json)`, `(True, "ERROR", ERROR, console)`. Call `initialize_debug_state`, then `capsys.readouterr()`, emit one line at each of debug/info/warning/error with `structlog.get_logger()`, and assert exactly the lines at or above the level appear; `current_log_level()` equals the level; for JSON every line parses with `json.loads`, for console none does |
| 1 | same class | Switch round trip (AC 6): `initialize_debug_state(False, "WARNING")`; `set_debug_enabled(True)` is `True`, `current_log_level() == "DEBUG"`, a debug line is written; `set_debug_enabled(False)` is `True`, `current_log_level() == "WARNING"`, an info line is not written and a warning line is. Same with `log_level=None`: off returns to INFO. AC 7: `initialize_debug_state(True, "WARNING")`; `set_debug_enabled(True)` is `True` and gives DEBUG; again → `False`. `initialize_debug_state(False, "WARNING")`; `set_debug_enabled(False)` → `False`, level stays WARNING |
| 1 | `tests/test_debug_api.py` (uses `admin_client`; its autouse `reset_debug_state` fixture, `:53-68`) | New test with `monkeypatch.setattr` of the four names to a fresh state, then `initialize_debug_state(False, "WARNING")`: `POST /debug/enable` → 200, body exactly `{"status": "ok", "data": {"debug_enabled": True, "changed": True}}`, `current_log_level() == "DEBUG"`; `POST /debug/disable` → body exactly `{"status": "ok", "data": {"debug_enabled": False, "changed": True}}`, `current_log_level() == "WARNING"`; `GET /debug` → `data == {"debug_enabled": False}`. Check the exact envelope keys against the existing tests in the file before asserting the whole body |
| 1 | `tests/test_main.py`, new `TestLifespanLogLevel` in the style of `TestLogModDbUrl.test_the_lifespan_logs_it_once_at_start_up` (`:777-791`: `create_app(Settings(...), static_dir=tmp_path / "missing")`, `TestClient(app)` as a context manager, `capsys`) plus the module-state reset fixture | `Settings(api_key_admin=..., data_dir=tmp_path / "data", log_level="info")` (debug false): the `api_starting` line is JSON with `"log_level": "INFO"` and `"debug_mode": false`. `log_level="warning"`: no `api_starting` in the output, `current_log_level() == "WARNING"`. `debug=True, log_level="INFO"`: console output, `api_starting` with `log_level=INFO`, `is_debug_enabled()`. `VS_DEBUG=on` via `monkeypatch.setenv` and `Settings(api_key_admin=..., data_dir=...)`: `is_debug_enabled()` and `current_log_level() == "DEBUG"` after start-up (AC 8). Each test builds its own app, so nothing is shared |
| 1 | `tests/test_debug_gating.py` (`make_app`, `:20-25`) | `make_app` takes an optional `log_level`; `debug=False, log_level="DEBUG"`: `/docs` and `/api/v1alpha1/test/read` are 404 (AC 4); `debug=True, log_level="INFO"`: `/docs` is 200 and the test route 401 without a key (AC 3). Build the app only; no lifespan is needed for the routes |
| 3 | `tests/test_game_config.py` `test_secret_values` (`:301-312`) and `test_other_values_are_not_secret` (`:314-327`) | Add `https://ptb.discord.com/api/webhooks/1/abc`, `https://canary.discord.com/api/webhooks/1/abc`, `https://PTB.Discord.com/api/webhooks/1/abc` as secrets; `https://ptb.discord.com/channels/1` and `https://canary.discord.com/api/other` as not. New test parametrized over `sorted(DISCORD_HOSTS)` (imported from `mod_update_alerts`): `is_secret_value(f"https://{host}/api/webhooks/1/x")` and `is_discord_webhook` of the same URL are both true (one set, AC 10) |
| 3 | `tests/test_routers_config.py` `TestReadConfigFileSecrets` (`:1315`), beside `test_secrets_are_redacted_at_every_depth` (`:1402-1437`) | `ModConfig/mod.json` with `{"Ptb": "https://ptb.discord.com/api/webhooks/1/<SECRET>-ptb", "Canary": "https://canary.discord.com/api/webhooks/1/<SECRET>-canary"}`: Monitor gets both `[redacted]` and `SECRET not in monitor.text`; Admin gets the file unchanged |
| 4 | `tests/test_config_files.py`, new `TestLinksOutsideTheDataDirectory` (fixtures `mock_settings`, `service`, `tmp_path`) | `outside = tmp_path / "outside"` with `x.json` in it; in the root and in `ModConfig`: a directory link `away -> outside` and a file link `away.json -> outside/x.json`. For `role` in `"admin"`, `"monitor"`, `None`: `list_directories()` / `list_directories("ModConfig")` never contain `away`; `list_files()` / `list_files("ModConfig")` never contain `away.json`; a real `ModConfig` and a real `serverconfig.json` are still listed. Admin `read_file("away/x.json", "admin")` and `list_directories("away", "admin")` still raise `ConfigPathInvalidError` (unchanged). Red first: the Admin directory cases fail today |
| 4 | same file, new `TestMissingDataDirectory` (remove the directory with `mock_settings.serverdata_dir.rmdir()`, as `:71-79` does) | For `role` in `"monitor"`, `None`: `list_directories("Playerdata")` and `list_files("Playerdata")` raise `ConfigDirectoryForbiddenError` (red first: today `[]`); `None` and `"ModConfig"` give `[]`. For every role: `"../x"` raises `ConfigPathInvalidError` (red first for the listing: today `[]`). Admin: `"Playerdata"` gives `[]` |
| 4 | `tests/test_routers_config.py` `TestMonitorDirectories` (`:1625`) | Router level for AC 11 and 12: with the data fixture plus a root link `away -> tmp_path / "outside"`, Admin's root listing (`test_root_listing`, `:1642-1660`, shows every directory) does not contain `away`. With `shutil.rmtree(config_file.parent)` (the server data directory): Monitor `?directory=Playerdata` on both listing routes → 403, body exactly as in `test_other_directories_are_403_for_monitor` (`:1662-1682`), `Cache-Control: no-store`; Monitor and Admin `?directory=../x` → 400; Monitor root and `ModConfig` → 200 `[]`; Admin `Playerdata` → 200 `[]` |

Synthetic secrets only (`SECRET` constants already in the files); no real webhook URL.

### Existing tests that change (deliberately)

Found by running the whole API suite against a throwaway prototype of Tasks 1, 3 and 4 (since discarded): 3374 passed, 13 failed, all in Task 1's area:

- `tests/test_config.py::TestDebugStateManagement` (`:803-916`): `test_initialize_debug_state_from_env_true`, `_false`, `_1`, `_yes` and `_idempotent` (`:806-871`) call `initialize_debug_state()` with no argument and patch `VS_DEBUG` in `os.environ`. Rewrite them to build `Settings()` from the patched environment and call `initialize_debug_state(settings.debug, settings.log_level)` (so they test the one parse; add `on`); `_idempotent` passes different arguments to the second call. `test_set_debug_enabled_no_change` (`:895-904`) sets `_debug_enabled = True` only, so the level is still `INFO` and `enable` now reports a change: initialise with `initialize_debug_state(True, None)` after resetting the module state instead.
- `tests/test_runtime_debug_toggle.py::TestInitializeDebugState` (`:21-88`): all five tests, same rewrite (`test_accepts_various_true_values` covers the pydantic spellings, `on` and `y` included). `TestSetDebugEnabled::test_no_change_when_already_enabled` and `test_no_change_when_already_disabled` (`:124-147`): set up through `initialize_debug_state` as above. `setup_method` in both classes writes private names with existing `# pyright: ignore[reportPrivateUsage]` comments; switching them to a `monkeypatch` fixture is welcome, adding new ignore comments is not.
- Not failing, unchanged: `test_main.py` patches `main.initialize_debug_state` with a mock (`:310`, `:511`, `:571`, `:631`, `:687`, `:736`), which accepts the new arguments; `test_debug_api.py`'s and `test_request_context.py`'s fixtures (`:53-68`, `:66-67`) set `_debug_enabled` / `_debug_initialized` directly and still pass; `test_config.py::TestConfigureLoggingWithLogLevel` (`:918-935`) and `TestReconfigureLoggingIfChanged` (`:937-975`).
- Tasks 3 and 4 broke no existing test: `test_config_files.py:71-79` and `:211-220` (missing data directory, root listing, no role) still get `[]`; `test_list_files_uses_the_viewer_file_rule` (`:222-238`) already expects the outside `out.json` link to be left out for Admin.
- Environment note: in a fresh worktree without the repository's `.env`, `just test-api` reports 80 errors and 7 failures from `VS_API_KEY_ADMIN` being unset (lifespan, scheduler, jobs router and console WebSocket tests; 3387 passed with `VS_API_KEY_ADMIN=<any value> just test-api` at the base). Not caused by this story.
- Anything else that fails is a regression (AC 13): fix the code, not the test.

### Documentation text (Task 2)

- **README row:** ``| `VS_LOG_LEVEL` | No | Level of the API's log lines: `DEBUG`, `INFO`, `WARNING` or `ERROR`, any letter case. Unset: `DEBUG` with `VS_DEBUG=true`, `INFO` otherwise. It changes only the level, nothing else that `VS_DEBUG` does. Turning debug logging on in the web UI gives `DEBUG`; turning it off returns to this level. uvicorn's own lines are not affected. Any other value stops start-up |``
- **`.env.example`:** "Level of the API's own log lines: DEBUG, INFO, WARNING or ERROR (any letter case) / Unset: DEBUG with VS_DEBUG=true, INFO otherwise. VS_DEBUG still decides the rest (/docs, the test routes, the console format). / The debug logging switch in the web UI gives DEBUG while it is on and returns to this level when it is turned off. uvicorn's own lines do not follow it. / Any other value stops start-up. / Default: unset / # VS_LOG_LEVEL=INFO"
- **`project-structure-boundaries.md` row:** ``| `VS_LOG_LEVEL` | No | `DEBUG`, `INFO`, `WARNING` or `ERROR`, any case (Epic 21 ADR-4); unset: from `VS_DEBUG`. The debug switch gives `DEBUG` and returns to it; only structlog's level; any other value stops start-up |``
- **`project-context.md` "Configuration":**
  - `VS_DEBUG=true`: debug mode: console renderer, DEBUG unless `VS_LOG_LEVEL` says otherwise, `/docs` and the test routes. Parsed once, by `Settings.debug` (pydantic's bool: `true/1/yes/on` and so on).
  - `VS_LOG_LEVEL`: `DEBUG`, `INFO`, `WARNING` or `ERROR`, any case; validated in `Settings` (an invalid value stops start-up). Sets structlog's level at start-up only; uvicorn's lines do not follow it.
  - Default: DEBUG with `VS_DEBUG=true`, INFO otherwise; JSON outside debug mode.
  - The run-time switch (`POST /debug/enable`, `/disable`) sets DEBUG and returns to the configured level (`current_log_level()` reports it). Initialise logging only through `initialize_debug_state(settings.debug, settings.log_level)`; never read `VS_DEBUG` from `os.environ`.

### No E2E, no web change

Nothing the web shows changes: the debug switch's requests and responses keep their shape, and the config viewer's listings drop only entries that already failed to open (400). The epic's Story 21.3 has no web file (change proposal, section 1, "As suggested: the API's settings and one service, no web file"). So no E2E spec and no web test; the router tests are the user-level check.

### Manual check (Task 5.2)

None required: the lifespan tests start the real app with each combination. Changing `VS_LOG_LEVEL` on the Docker stack means recreating the container, which stops the game server; that is the maintainer's call. If he does it: start with `VS_LOG_LEVEL=warning` and look at `docker compose logs`, never paste server name or password lines anywhere.

### Not changed (do not "fix" these here)

- uvicorn's own log level (`Dockerfile:92` has no `--log-level`); ADR-4 decision 5. The README says so.
- What the switch does to the renderer: as today it follows the switch (console while on, JSON while off), whatever `VS_DEBUG` was at start-up.
- `configure_logging`'s signature and its fallback for unknown names; `get_current_debug_setting` (deprecated) and `is_debug_enabled`.
- `GET /debug` and the response shapes of the three `/debug` routes.
- `is_discord_webhook` and the webhook sender; the redaction by key name.
- What Admin may read: `read_file` and `_safe_path`.
- `reconfigure_logging_if_changed` stays although nothing in `api/src` calls it (follow-up).

### API contract changes

- `VS_LOG_LEVEL` (existing setting, no effect until now): `DEBUG`, `INFO`, `WARNING` or `ERROR`, any case, sets the API's log level at start-up. Unset or blank: as before. **Any other value stops start-up** with `VS_LOG_LEVEL must be one of: DEBUG, INFO, WARNING, ERROR.` Not marked breaking (Matt, 2026-11-17); no file in the repository sets it.
- `VS_DEBUG` values pydantic reads as true but the old logging parse did not (`on`, `t`, `y`): logging is now in debug mode too.
- `POST /api/v1alpha1/debug/enable` and `/disable`: same response keys. Disable returns to the configured level (`VS_LOG_LEVEL`, or INFO). Enable reports `changed: true` when only the level changed (debug already on with `VS_LOG_LEVEL` other than DEBUG).
- Start-up line `api_starting`: `log_level` reports the level actually set.
- `GET /api/v1alpha1/config/files/{path}`, roles other than Admin: Discord webhook URLs on `ptb.discord.com` and `canary.discord.com` are `[redacted]`.
- `GET /api/v1alpha1/config/directories`: entries resolving outside the server data directory are no longer listed for Admin (they never were for other roles, nor in `/config/files` for anyone).
- Both listing routes, roles other than Admin, server data directory missing: a forbidden directory is 403 `FORBIDDEN` (was 200 `[]`); a traversal is 400 for every role (was 200 `[]`).
- No route, response field or error code is added or removed.

### ADR against the code

1. **The `api_starting` line at WARNING.** The epic's AC ("the `api_starting` line reports `WARNING`") cannot hold: `api_starting` is an INFO line (`main.py:167`), so at WARNING it is filtered out. Logging it at WARNING would make a normal start look like a problem. AC 1 is written as: the level set is WARNING (tested through `current_log_level()` and the lines written); the line reports the real level whenever it is written (tested at INFO and DEBUG).
2. **File symlinks.** ADR-5 decision 2 and the epic's AC put a `.json` file symlink pointing outside in the same gap as directories. It is not: `list_files` already leaves out every file resolving outside, for every role (`config_files.py:342`; pinned by `test_config_files.py:222-238`). Only the directory listing has the gap. The story still tests both, for Admin and Monitor, and moves the check into `_role_may_open` so there is one rule.
3. **ADR-4 decision 3 and an already-on switch.** The ADR does not cover `enable` when debug is already on at a non-DEBUG level; see "The switch" (AC 7).
4. **Commit split.** The epic lists validation and application as two tasks with the `feat` commit on the second. Validation alone would make an invalid value stop start-up while a valid one did nothing, and two commits would need two user-facing subjects. Both are one task and one `feat(api)` commit here.
- Line numbers in ADR-4 and ADR-5 match 966204f.

### Testing Requirements

**CRITICAL:** Tests are written with each task and committed with it, red first. `just test-api <file>` after each task; `just check` before review.

- Log output is read with `capsys` (structlog's `PrintLoggerFactory()` writes to `sys.stdout`); the conftest autouse fixture (`conftest.py:27-53`) reconfigures structlog before each test, so a test that reconfigures it does not leak.
- Module state is reset with `monkeypatch.setattr(config_module, "<name>", value)` so it is restored after each test; no new `# pyright: ignore`.
- Lifespan tests use `tmp_path` data directories (`Settings(data_dir=tmp_path / "data")`); nothing under `dev/`.

### Security Requirements

- The `VS_LOG_LEVEL` error never prints the value (`hide_input_in_errors`). No secret is logged at any level by this change.
- The redaction set grows only; Admin output does not change. Listing fewer entries can only hide paths; reads still go through `_safe_path`.

### Development Commands

- `just test-api tests/test_config.py tests/test_runtime_debug_toggle.py tests/test_debug_api.py tests/test_main.py tests/test_debug_gating.py`, `just test-api tests/test_game_config.py tests/test_mod_update_alerts.py tests/test_config_files.py tests/test_routers_config.py`, `just typecheck-api`, `just lint-api`, `just check`.
- `cd api && uv run ruff format <changed files>` (Epic 20 formatted the API; do not format the whole tree).

### Previous Story Intelligence

- **19.1:** built the role rule (`_role_may_open`, `MONITOR_CONFIG_DIRECTORIES`) and the value redaction (`is_secret_value`); its review left the three edge cases now in `VSS-wv0w`. Decisions are made on resolved paths.
- **19.3:** `VS_CSP_MODE` is the model for a validated setting (plain `str`, `field_validator`, message naming the variable); its review: a task is ticked only when done.
- **20.6:** `VS_MOD_DB_URL`: a field validator rather than a model validator (a failing model validator prints every setting); `hide_input_in_errors`; conftest pops a developer's `.env` value (`conftest.py:12-14`), the pattern for `VS_LOG_LEVEL`.
- **20.7:** its review moved the working tuning settings into the README and `.env.example` and left `VS_LOG_LEVEL` out because nothing read it; this story adds it.
- **17.x / 18.x:** a `feat`/`fix` subject must describe what an operator can see; completion notes must be true of the code; tests must not write into `dev/`.

### Git Intelligence

- Base `966204f` (`docs(epic-21): record the maintainer's answers and pull in VSS-q38r`) on `05436da` (`v0.1.0-rc.6`). Stories 21.1 and 21.2 touch only `web/`, Renovate and `RELEASING.md`; they share the README with this story (different sections).
- Planned commits: Task 1 `feat(api): VS_LOG_LEVEL sets the log level`; Task 2 `docs(story-21.3/task-2): document VS_LOG_LEVEL`; Task 3 `fix(api): hide Discord webhook URLs on ptb and canary hosts from read-only keys`; Task 4 `fix(api): leave links that point outside the data directory out of the config file listing`; Task 5 `docs(story-21.3): ...` for the story record. The release-note subjects are the change proposal's (section 2); each commit body names Story 21.3 and the task.

### Project Structure Notes

- Modified: `api/src/vintagestory_api/config.py`, `main.py`, `services/game_config.py`, `services/mod_update_alerts.py` (docstring), `services/config_files.py`, `routers/config.py` (docstrings); `api/tests/conftest.py`, `test_config.py`, `test_runtime_debug_toggle.py`, `test_debug_api.py`, `test_main.py`, `test_debug_gating.py`, `test_game_config.py`, `test_config_files.py`, `test_routers_config.py`; `README.md`, `.env.example`, `project-context.md`, `_bmad-output/planning-artifacts/architecture/project-structure-boundaries.md`.
- No new file, no web file, no compose or Dockerfile change.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 21.3: A Working `VS_LOG_LEVEL` and Config Viewer Edge Cases]
- [Source: _bmad-output/planning-artifacts/prd.md] FR266-FR270
- [Source: _bmad-output/planning-artifacts/architecture/epic-21-maintainer-decisions-and-web-polish.md#ADR-4, #ADR-5, "Logging today", "Config file viewer today"]
- [Source: _bmad-output/planning-artifacts/architecture/epic-19-api-security-and-mod-file-safety.md] ADR-2 (redaction), ADR-3 (role directories)
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-17-epic-21.md] section 2 (API change table, release-note subjects), section 5 (answers 1 and 2)
- [Source: _bmad-output/implementation-artifacts/19-1-secrets-stay-with-admin.md], [20-6-mod-database-tests-in-ci.md], [20-7-reproducible-image-and-conventions.md]
- Bead: `VSS-wv0w`, parent `VSS-syuj`
- `project-context.md` (no suppressions; commit format; manual checks need the maintainer)

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5), BMAD dev-story, non-interactive.

### Debug Log References

- Task 1 red: the new tests failed at collection (`current_log_level`, `LOG_LEVELS` not defined). Task 3 red: 6 failures (ptb/canary values not redacted, the shared-host test). Task 4 red: 9 failures (Admin directory listing showed `away`; with the data directory missing, Monitor `Playerdata` and every `../x` gave `[]`).
- `just check` after the review round: API 3458 passed (3 removed tests, 1 new case), pyright 0 errors 0 warnings; web 3307 passed, 0 skipped.
- `just check` at the end of implementation: API 3460 passed, pyright 0 errors 0 warnings; web 132 files / 3307 tests passed, 0 skipped, tsc 0 errors; script tests passed. `git status --short dev/` empty after the API run.

### Completion Notes List

- Story created 2026-11-17 (create-story, non-interactive) and validated against the create-story checklist. A throwaway prototype of Tasks 1, 3 and 4 (validator, start-up and switch, the shared host set, containment before the Admin return, no missing-directory shortcut) was run against the whole API suite (3374 passed, the 13 failures listed in "Existing tests that change") and by hand against the edge cases, then discarded.
- Task 1: `Settings.validate_log_level` normalises `VS_LOG_LEVEL` (strip, upper; blank is `None`) and refuses anything outside `LOG_LEVELS` with `VS_LOG_LEVEL must be one of: DEBUG, INFO, WARNING, ERROR.`; `hide_input_in_errors` keeps the value out. `_read_debug_from_env` and the `os` import are gone; `initialize_debug_state(debug, log_level)` takes both from the settings (once-guarded) and applies `log_level or DEBUG/INFO`; `current_log_level()` is new; `set_debug_enabled` gives DEBUG on and the configured level (or INFO) off, and reports `changed` when the debug state or the level changes; `reconfigure_logging_if_changed` passes `_current_log_level`. The lifespan passes `settings.debug, settings.log_level` and `api_starting` logs `current_log_level()`. conftest pops `VS_LOG_LEVEL`.
- Task 1 deviation (tests): `test_debug_api.py`'s autouse `reset_debug_state` fixture was rewritten with `monkeypatch` to also reset `_configured_log_level` and `_current_log_level` (the story listed it as unchanged; without the reset the `changed` answers depend on the level a previous test left), and `test_enable_debug_already_enabled` now also sets the level to DEBUG (debug on at INFO is now a change). `test_runtime_debug_toggle.py`'s `TestInitializeDebugState` and `TestSetDebugEnabled` use a `fresh_debug_state` monkeypatch fixture instead of `setup_method` with ignore comments; `TestRuntimeDebugToggleBehavior` is unchanged. No ignore comment was added.
- Task 2: README row, `.env.example` block, `project-structure-boundaries.md` row (and the "nothing reads it" sentence dropped), `project-context.md` Logging "Configuration" replaced, with the story's text.
- Task 3: `game_config._DISCORD_WEBHOOK_HOSTS` removed; `is_secret_value` uses `mod_update_alerts.DISCORD_HOSTS`, which has a docstring naming both users. `config_files.py`'s module docstring needed no change.
- Task 4: `_role_may_open` checks containment before the Admin return; `list_files` lost its own containment clause; the two `serverdata_dir.exists()` shortcuts are gone and `_target_directory` checks existence after the path and role checks (root included, `serverdata_dir_not_found` kept for a missing root). Service and route docstrings updated.
- Task 5: 5.2 left unticked: no manual check is required, and any check on the Docker stack (recreating the container) is the maintainer's. 5.3 left unticked: status and sprint status are `review`; the PR and the PR link on `VSS-wv0w` are for the orchestrator.
- API contract changes as shipped: as listed in Dev Notes "API contract changes", including `/debug/enable` answering `changed: true` when only the level changes (`VS_DEBUG=true` with `VS_LOG_LEVEL` other than DEBUG).
- Code review (APPROVE, one LOW, notes), folded in under the backlog-drawdown rule: L1 `reconfigure_logging_if_changed` and `_last_debug_state` removed with their three tests (no caller outside tests; the docstring described reading `VS_DEBUG` from the environment), which overrides "Not changed" for that function. N2: `TestDebugStateManagement` (fixture now autouse), `TestRuntimeDebugToggleBehavior`, the `request_context_app` fixture and `test_debug_api.py`'s remaining writes set the debug state through `monkeypatch` or `initialize_debug_state` on a fresh state; 8 `pyright: ignore` comments removed in the review round (23 over the story), none added. The touched files pass forward, reversed and shuffled (seeds 1-3), and the whole API suite reversed and shuffled, using a throwaway ordering plugin outside the repository. N1: `api_starting` is checked for `log_level` DEBUG in JSON (`VS_LOG_LEVEL=debug`) and in the console (`VS_DEBUG=on`).

### File List

- `api/src/vintagestory_api/config.py`
- `api/src/vintagestory_api/main.py`
- `api/src/vintagestory_api/services/game_config.py`
- `api/src/vintagestory_api/services/mod_update_alerts.py`
- `api/src/vintagestory_api/services/config_files.py`
- `api/src/vintagestory_api/routers/config.py`
- `api/tests/conftest.py`
- `api/tests/test_config.py`
- `api/tests/test_runtime_debug_toggle.py`
- `api/tests/test_debug_api.py`
- `api/tests/test_main.py`
- `api/tests/test_debug_gating.py`
- `api/tests/test_request_context.py`
- `api/tests/test_game_config.py`
- `api/tests/test_config_files.py`
- `api/tests/test_routers_config.py`
- `README.md`
- `.env.example`
- `project-context.md`
- `_bmad-output/planning-artifacts/architecture/project-structure-boundaries.md`
- `_bmad-output/implementation-artifacts/21-3-log-level-and-config-viewer.md`

## Change Log

- 2026-11-17: Story 21.3 created and validated (ready-for-dev).
- 2026-11-17: Story 21.3 implemented (Tasks 1-4, quality gate); status review.
- 2026-11-17: Code review findings L1, N1, N2 folded in; status stays review.
