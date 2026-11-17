# Story 19.2: The Web UI No Longer Gets the Admin Key

Status: review

<!-- Implements FR210-FR212, Epic 19 ADR-5 (which changes Epic 15 ADR-5). Beads: VSS-9wv (API-079, size-m). BREAKING CHANGE. Stacked on Story 19.1 (stories run in order 19.1 to 19.7). Line references were verified at b6ae2f2 (epic-19-planning; its api/ and web/ are the code the ADRs cite at 048fea9) and must be re-checked at implementation time: Story 19.1 edits config.py, .env.example, both compose files and scripts/worktree-setup.sh first (it removes VS_GAME_VERSION, so later lines in those files move up). No new dependencies. -->

## Story

As an **operator whose web UI can be reached by people who are not admins**,
I want **the web UI to receive a key only when I name one**,
so that **opening the page does not hand out the Admin key**.

## Acceptance Criteria

1. **Given** `VS_API_KEY` is unset or blank (empty, or whitespace only)
   **When** the API starts
   **Then** it starts, `/healthz` and `/readyz` answer 200 as before, it logs `web_api_key_not_set` at warning level with a hint and without any key, and `GET /config.js` answers 200 with the body `window.__VSM_CONFIG__ = {"apiKey": ""};\n` and the same three headers as before (`Cache-Control: no-store`, `Cross-Origin-Resource-Policy: same-origin`, `X-Content-Type-Options: nosniff`)
   *(Covers FR210, FR211)*

2. **Given** the web UI is loaded and has no key (`window.__VSM_CONFIG__?.apiKey` and `VITE_API_KEY` are both empty)
   **When** the page opens, on any path
   **Then** it shows a full-page "No API key configured" screen instead of the app: it names `VS_API_KEY`, the Monitor key (read-only) and the Admin key (full access), says to restart the server, and says that anyone who can open the page receives that key; it makes no request to `/api/` and opens no WebSocket; it has no field to enter a key
   *(Covers FR210)*

3. **Given** the web UI has a key
   **When** the page opens
   **Then** the screen is not shown and the app renders as before
   *(Covers FR210; the other direction of AC 2)*

4. **Given** `VS_API_KEY` equals the Admin key
   **When** the API starts
   **Then** `/config.js` serves the Admin key and the API logs `web_api_key_is_admin_key` at warning level, with a hint and without the key
   *(Covers FR211)*

5. **Given** `VS_API_KEY` equals the Monitor key (and not the Admin key), or matches neither key
   **When** the API starts
   **Then** with the Monitor key `/config.js` serves it and none of the three web key warnings is logged; with a key that matches no role `/config.js` serves that value and the existing `web_api_key_matches_no_role` warning is logged, as before
   *(Covers FR211)*

6. **Given** the README, `.env.example` and both compose files
   **When** I read how to give the web UI a key
   **Then** they say the web UI needs `VS_API_KEY`, recommend the Monitor key first or an authenticating proxy in front of the web UI, say what setting it to the Admin key means, say that anyone who can load the page receives that key, and `docker-compose.yaml` still passes `${VS_API_KEY:-}` (the production example does not hand out the Admin key by default)
   *(Covers FR212)*

7. **Given** the dev stack started with `just docker start` and no `VS_API_KEY` in the environment or `.env`
   **When** I open the web UI or run the E2E specs
   **Then** the page has the Admin key as before, because `docker-compose.dev.yaml` sets `VS_API_KEY` to the Admin key itself; the stack's log has `web_api_key_is_admin_key`
   *(Covers FR212)*

8. **Given** the API tests
   **When** they need the app in one of the `VS_API_KEY` states (unset, blank, Admin key, Monitor key, a key matching no role)
   **Then** they build the app with those settings through the app factory, and for each state `/config.js` and the start-up log are asserted, each of the three warnings both ways (logged in its state, not logged in the others); `/healthz` and `/readyz` are 200 in every state
   *(Covers FR211)*

9. **Given** the app factory
   **When** the API suite runs
   **Then** the module still exposes `app` (built from the cached `get_settings()`), the lifespan no longer builds a new `Settings()`, and no test outside the ones listed in "Existing tests that change" needs editing
   *(ADR-5 decision 11)*

10. **Given** the commit that removes the fallback
    **When** the release notes are generated with `just changelog`
    **Then** the change is listed under **Breaking Changes** as `**api:** The web UI no longer receives the Admin key by default; set VS_API_KEY to the Monitor or Admin key`
    *(Covers FR212)*

## Tasks / Subtasks

<!-- Each functional task includes its tests in the same commit, red first. Commit per task: type(story-19.2/task-N): ..., EXCEPT Task 2, whose commit subject is fixed by ADR-5 "Release" (see Git Intelligence). -->

- [x] Task 1: App factory in `main.py`, no behaviour change + tests (AC: 8, 9)
  - [x] 1.1: `api/src/vintagestory_api/main.py`: replace the module-level `lifespan` (`:91-162`) with `lifespan_for(settings: Settings) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]`, which returns the same handler closed over `settings`; delete `settings = Settings()` (`:96`). The body is otherwise unchanged (the inner function keeps `global scheduler_service`). Imports: `Callable` from `collections.abc`, `AbstractAsyncContextManager` from `contextlib`
  - [x] 1.2: `main.py`: `register_frontend(target, static_dir, settings: Settings)` (`:246`); `serve_runtime_config` (`:260-272`) takes no dependency and reads `settings.web_api_key` from the closure. Move `_resolve_frontend_file` and `register_frontend` above the factory
  - [x] 1.3: `main.py`: `create_app(settings: Settings, static_dir: Path = STATIC_DIR) -> FastAPI` holds everything from `app = FastAPI(...)` (`:165`) to the WebSocket router (`:227`), with `lifespan=lifespan_for(settings)`, then `if static_dir.exists(): register_frontend(app, static_dir, settings)` (replaces `:281-283`), then `return app`. The module ends with `app = create_app(get_settings())`. The two other `Settings()` calls stay as they are, now inside the factory: CORS (`:177`; rename the local to `cors_settings` so it does not shadow the parameter) and the RBAC test router (`:219`). Story 19.3 moves both (ADR-7 decision 6); see "Not changed". The indented RBAC `logger.warning` line (`:221`) becomes 102 characters: wrap it (ruff E501)
  - [x] 1.4: Update the tests in "Existing tests that change (Task 1)"
  - [x] 1.5: New `api/tests/test_app_factory.py` (Dev Notes "API tests", Task 1 rows)
  - [x] 1.6: `just test-api` passes with no other test edited; `just typecheck-api` at 0 errors

- [x] Task 2: No fallback, the start-up states, the two new warnings + tests; the breaking commit (AC: 1, 4, 5, 8, 10) (`VSS-9wv`)
  - [x] 2.1: `api/src/vintagestory_api/config.py` `web_api_key` (`:31-36`): return `""` instead of `self.api_key_admin`; docstring "VS_API_KEY, or the empty string when it is unset or blank (Epic 19 ADR-5)". Update the field comment at `:22`
  - [x] 2.2: `config.py`: replace `web_api_key_has_a_role()` (`:38-40`) with `web_api_key_state() -> Literal["not_set", "admin", "monitor", "no_role"]` (Dev Notes "The states")
  - [x] 2.3: `main.py`: a module-level `log_web_api_key_state(settings: Settings) -> None` that logs at most one warning from the state, with the hints of Dev Notes "The warnings"; the lifespan calls it where the old `if not settings.web_api_key_has_a_role():` block is (`:103-108`). No key is passed to the logger
  - [x] 2.4: Update the tests in "Existing tests that change (Task 2)"
  - [x] 2.5: Tests (Dev Notes "API tests", Task 2 rows), red first
  - [x] 2.6: Commit with the exact subject and footer of "Git Intelligence"; then run `just changelog` and confirm AC 10

- [x] Task 3: Web: the "No API key configured" screen + tests (AC: 2, 3)
  - [x] 3.1: `web/src/api/client.ts`: export `getApiKey(): string` returning `window.__VSM_CONFIG__?.apiKey || import.meta.env.VITE_API_KEY || ''`; `getConfig` (`:28-33`) uses it. One expression, one place
  - [x] 3.2: New `web/src/components/NoApiKeyScreen.tsx` (Dev Notes "The screen")
  - [x] 3.3: `web/src/App.tsx` `App` (`:104-143`): first statement `if (!getApiKey()) return <ThemeProvider><NoApiKeyScreen /></ThemeProvider>;`. The check runs at render, not at module load. Nothing else in `App` changes
  - [x] 3.4: Tests (Dev Notes "Web tests"), red first

- [x] Task 4: Dev compose default and documentation (AC: 6, 7)
  - [x] 4.1: `docker-compose.dev.yaml` (`:19-20`): `- VS_API_KEY=${VS_API_KEY:-${VS_API_KEY_ADMIN:-changeme}}`, comment: the dev stack gives the web UI the Admin key unless `VS_API_KEY` is set; the API logs `web_api_key_is_admin_key`
  - [x] 4.2: `docker-compose.yaml` (`:19-21`): the variable line stays `- VS_API_KEY=${VS_API_KEY:-}`; new comment (Dev Notes "Documentation")
  - [x] 4.3: `.env.example` (`:40-44`) and `README.md` (`:25`, `:37`, `:75`) (Dev Notes "Documentation")
  - [x] 4.4: Check: `docker compose -f docker-compose.dev.yaml config | grep VS_API_KEY=` shows the Admin key value for `VS_API_KEY` with it unset and with it blank, and the chosen value when set (do not paste a real key into the story; say "matches" or "differs"). `docker compose -f docker-compose.yaml config` shows it empty when unset

- [x] Task 5: E2E against the Docker dev stack: the `/config.js` helper and the no-key spec (AC: 2, 3, 7)
  - [x] 5.1: New `web/e2e/config-js.ts` and `web/e2e/no-api-key.spec.ts` (Dev Notes "E2E")
  - [x] 5.2: Rebuild the stack from this branch (`just docker restart`), run `cd web && bunx playwright test e2e/no-api-key.spec.ts`, then two read-only specs of the twelve that rely on the stack's own key, `e2e/mods-navigation.spec.ts` and `e2e/mod-browse-state.spec.ts` (both need the public mod database), to confirm the page still gets a key from the stack. Do not run the specs that install mods for this. The rebuild restarts the container, as for every story's E2E; do not start or stop the game server yourself; no screenshots
  - [x] 5.3: Record in the Dev Agent Record: the spec's result, and that the stack's log has `web_api_key_is_admin_key` and no key value (`just docker logs | grep -c web_api_key_is_admin_key`; report the count only)

- [ ] Task 6: Quality gate and review hand-off (AC: all)
  - [x] 6.1: `just check` passes; the diff adds no lint or type suppression and no `cast`; pyright stays at 0 errors and the 3 pre-existing warnings (`VSS-1ar`); after `just test-api`, `git status --short` shows nothing under `dev/`
  - [x] 6.2: `just changelog` lists the Task 2 commit under Breaking Changes with the line of AC 10; no other commit of this story appears under Breaking Changes, and the Task 1 refactor appears nowhere
  - [ ] 6.3: Manual check on the Docker stack (needs the maintainer's confirmation before it is ticked, `project-context.md`): Dev Notes "Manual check"
  - [ ] 6.4: Story status `review`, `just sprint set 19-2-web-ui-no-longer-gets-the-admin-key review`, PR (base: Story 19.1's branch while its PR is open, otherwise `main`), PR link on `VSS-9wv`. The PR description starts with the breaking change and what to set, lists "API contract changes" from this story, and repeats the deployment note below

## Dev Notes

### Deployment note (not done by this story)

Every deployment that does not set `VS_API_KEY` today shows the set-up screen after it upgrades to the release that carries this story. That includes the maintainer's cluster deployment, which is configured in another repository and does not set `VS_API_KEY`. That repository must set `VS_API_KEY` (to the Monitor or the Admin key) in the same release. This story does not touch it and must not try to; say so in the PR description so the maintainer can do it with the release.

### The problem (verified at b6ae2f2)

- `Settings.web_api_key` returns `VS_API_KEY`, or the Admin key when it is unset or blank (`config.py:31-36`). `GET /config.js` serves it without authentication (`main.py:260-272`). Both compose files pass `VS_API_KEY=${VS_API_KEY:-}` (`docker-compose.yaml:21`, `docker-compose.dev.yaml:20`), so by default anyone who can load the page receives the Admin key. The only start-up warning is for a key that matches no role (`main.py:103-108`).
- `main.py` builds `Settings()` three times (`:96` lifespan, `:177` CORS, `:219` RBAC test router) and `app` at import (`:165-170`), so a test cannot build the app with settings of its choice.

### The factory (Task 1)

Shape (prototyped at b6ae2f2 and discarded; pyright strict reported 0 errors in `src`):

```python
def lifespan_for(settings: Settings) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    """Return the lifespan handler of an app that runs with the given settings."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        global scheduler_service
        initialize_debug_state()
        settings.ensure_data_directories()
        ...  # unchanged

    return lifespan


def create_app(settings: Settings, static_dir: Path = STATIC_DIR) -> FastAPI:
    """Build the application for the given settings."""
    app = FastAPI(..., lifespan=lifespan_for(settings))
    ...  # middleware and routers, unchanged
    if static_dir.exists():
        register_frontend(app, static_dir, settings)
    return app


app = create_app(get_settings())
```

- "The lifespan uses the cached `get_settings()`" (epic task 1, ADR-5 decision 11) is met through the factory: the server's `app` is built from `get_settings()`, and its lifespan uses that object. The lifespan does not call `get_settings()` itself, because an app built by a test with other settings must start with those settings (AC 8).
- What the factory's settings govern in this story: the lifespan (data directories, the web key warning, `ApiSettingsService(settings)`) and `/config.js`. Request dependencies still resolve `Depends(get_settings)` (`middleware/auth.py:23-30`), so an app built with other settings authenticates against the cached settings unless a test overrides the dependency, as tests do today. Do not put `dependency_overrides` in `create_app`: many fixtures call `app.dependency_overrides.clear()`. The new tests here call only unauthenticated routes.
- `static_dir` is a parameter so a test can build a whole app that serves `/config.js` from a temp directory. `load_fresh_app` (`api/tests/test_main.py:232-246`) patches `Path.exists` for `/app/static`; the default argument keeps that working (checked with the prototype).
- `uvicorn vintagestory_api.main:app` (`Dockerfile:91`, `Justfile:194`) and `from vintagestory_api.main import app` in the tests keep working. `get_scheduler_service` and the `scheduler_service` global stay module-level (`routers/health.py:83` and `routers/jobs.py:25` import the function).
- Behaviour to keep: middleware order, router order, the RBAC router gate reading a fresh `Settings().debug` (`test_rbac_test_routes_only_exist_in_debug_mode`, `test_main.py:252-260`, sets `VS_DEBUG` and re-runs the module; switching that gate to the cached settings would break the `false` case, which is why it waits for Story 19.3).

### The states (Task 2)

`Settings.web_api_key_state()`, checked in this order:

| `VS_API_KEY` | State | `/config.js` serves | Start-up log |
|---|---|---|---|
| unset, empty or whitespace only | `not_set` | `""` | warning `web_api_key_not_set` |
| equals `api_key_admin` | `admin` | the Admin key | warning `web_api_key_is_admin_key` |
| `api_key_monitor` is set and equals it | `monitor` | the Monitor key | none |
| anything else | `no_role` | that value | warning `web_api_key_matches_no_role` (unchanged) |

- Admin is checked before Monitor, so when both role keys are the same value the state is `admin`.
- The Monitor comparison requires a truthy `api_key_monitor`, as authentication does (`middleware/auth.py:93`). The compose files pass `VS_API_KEY_MONITOR=` as an empty string by default; `not_set` is checked first, so an empty web key never "equals" an empty Monitor key.
- `web_api_key` returns the value as given when it has any non-blank character (no stripping), as today.
- A `Literal` return keeps pyright strict happy without an enum; an `Enum` is also fine. No `cast`.

### The warnings (Task 2)

Event names are the contract; the hints may be reworded but must name the variables and never contain a key:

- `web_api_key_not_set`: `hint="/config.js serves no API key, so the web UI shows a set-up message. Set VS_API_KEY to VS_API_KEY_MONITOR (read-only) or VS_API_KEY_ADMIN (full access); anyone who can load the web UI receives that key"`
- `web_api_key_is_admin_key`: `hint="Anyone who can load the web UI receives the Admin key. Set VS_API_KEY to VS_API_KEY_MONITOR for a read-only web UI, or put the web UI behind an authenticating proxy"`
- `web_api_key_matches_no_role`: the existing call, unchanged (`main.py:105-108`).

Under `just dev-api` with no `VS_API_KEY` in `.env` the API logs `web_api_key_not_set` although `just dev-web` gets its key from `VITE_API_KEY`; that is correct (it describes `/config.js`) and is not special-cased.

They are logged from the lifespan, after `initialize_debug_state()` and `ensure_data_directories()`, where the existing warning is. The API does not refuse to start (ADR-5 decision 3): it supervises the game server, and API-only use is valid.

### The screen (Task 3)

`NoApiKeyScreen({ devServer = import.meta.env.DEV }: { devServer?: boolean })`, a full-page centered block (`min-h-screen`, in the style of `EmptyServerState.tsx:53-64`, with a `lucide-react` icon such as `KeyRound`; no new dependency):

- Root: `<main data-testid="no-api-key-screen">`.
- `<h1>`: `No API key configured`.
- Text: `The web UI was not given an API key, so it cannot talk to the server. Set VS_API_KEY on the server and restart it:` followed by a two-item list: `the Monitor key (VS_API_KEY_MONITOR) for a read-only web UI` and `the Admin key (VS_API_KEY_ADMIN) for full access`; then `Anyone who can open this page receives that key.` Variable names in `<code>`.
- Only when `devServer` is true, `<p data-testid="no-api-key-dev-hint">`: `Running the Vite dev server? Set VITE_API_KEY in web/.env.`
- No input, no button, no link that routes (there is no router), no hook that fetches.

It is rendered inside `ThemeProvider` only (dark mode follows the system as on the other pages). `PreferencesProvider`, `SidebarProvider`, `BrowserRouter`, `Layout` and `Toaster` are not rendered, so nothing can call the API or open a WebSocket: both WebSocket hooks get their token through `apiClient` (`web/src/hooks/use-console-websocket.ts`, `use-log-stream.ts`), and every page chunk is lazy (`App.tsx:15-34`) and never loaded. `main.tsx` keeps wrapping `App` in `QueryClientProvider`; with no query mounted it does nothing.

Where the screen appears: in the image with `VS_API_KEY` unset or blank (the build has no `VITE_API_KEY`, `Dockerfile:26-28`); under `just dev-web` when `web/.env` has no `VITE_API_KEY` (the placeholder `web/public/config.js` defines an empty config). `apiClient` itself is unchanged: it still sends whatever `getApiKey()` returns.

### Documentation (Task 4)

Recommend the Monitor key first (maintainer, 2026-11-17, ADR-5 decisions 6 and 7).

- `docker-compose.yaml:19-20` comment: the web UI gets a key only when `VS_API_KEY` is set; without it the page shows a set-up message. Set it in `.env` to the Monitor key (read-only, recommended) or the Admin key (full access). Anyone who can load the web UI receives this key.
- `.env.example:40-44`: replace "Default: blank - the web UI uses the admin key" with: required for the web UI; unset or blank means the page shows "No API key configured" and the API logs `web_api_key_not_set`; recommended `VS_API_KEY=<your monitor key>` (needs `VS_API_KEY_MONITOR`); the Admin key gives the page full access and logs `web_api_key_is_admin_key` on every start; anyone who can load the web UI receives the key; or put the web UI behind an authenticating reverse proxy. Keep the example line commented out and without a real value.
- `README.md` Installation step 2 (`:25`): also set `VS_API_KEY`, or the web UI shows a set-up message.
- `README.md` Security (`:37`): no fallback any more. The web UI receives `VS_API_KEY` from `/config.js`; with it unset the page shows what to set. Monitor key first (read-only web UI); Admin key means everyone who can load the page has full access, including the game server password, and the API warns at every start; keep port 8080 on a trusted network or behind a reverse proxy that authenticates (the existing sentence), which is the way to use the Admin key in the page safely. Keep "**Anyone who can load the web UI receives that key.**" and "The image itself contains no key."
- `README.md` Configuration table (`:75`): `VS_API_KEY` | "For the web UI" | Key the web UI uses. Unset: the web UI shows a set-up message. Set it to the Monitor key (read-only) or the Admin key (full access); any other value logs a warning at start-up and the UI cannot sign in.
- `README.md` Upgrading (`:39-50`) is not changed: step 1 already says to read the release notes, and the release note carries the instruction.
- `scripts/worktree-setup.sh:55` already writes `VS_API_KEY=$DEV_API_KEY`; no change.
- No real key, host name or instance value in any example.

### API tests

`api/tests/test_app_factory.py` (new). Build `Settings(api_key_admin=..., api_key_monitor=..., api_key=..., data_dir=tmp_path / "data")` with distinctive key values (for example `factory-admin-KEY-1`, `factory-monitor-KEY-2`), a temp `static_dir` holding an `index.html`, and `create_app(settings, static_dir=static_dir)`. Start-up runs inside `with TestClient(app) as client:`. Capture the log with `capsys` (the lifespan calls `initialize_debug_state()`, which reconfigures structlog; the lifespan tests in `tests/test_scheduler.py:355-383` read `capsys` the same way): `capsys.readouterr()` before the `with`, read `.out` inside it. Passing `data_dir` keeps the lifespan's directories out of `dev/`. A prototype of the table below passed (5 cases, about 1 s).

| Task | Test | Expect |
|---|---|---|
| 1 | the app starts with the settings it was given | after start-up `tmp_path / "data" / "vsmanager" / "state"` exists; `/healthz` and `/readyz` are 200 |
| 1 | `/config.js` comes from the given settings, not the environment | `monkeypatch.setenv("VS_API_KEY", "env-key")`, settings built with `api_key="given-key"`: the body has `given-key` and not `env-key` |
| 1 | no frontend without a static directory | `create_app(settings, static_dir=tmp_path / "missing")`: `/config.js` is 404, `/healthz` is 200 |
| 1 | the module's app | `main.app` is a `FastAPI` whose title and version are as before (already in `test_main.py:170-175`; do not duplicate, just keep it passing) |
| 2 | the five inputs, parametrized: `None`, `"  "`, the Admin key, the Monitor key, `"other-key"` | `/config.js` body is exactly `window.__VSM_CONFIG__ = {"apiKey": "<served>"};\n` with `""` for the first two; the three headers are present in every case; `/healthz` and `/readyz` are 200 |
| 2 | the same five inputs, start-up log | for each of the three event names: in the output if and only if it is that state's event (Monitor: none of the three) |
| 2 | no key in the log | neither the Admin nor the Monitor key value nor `other-key` appears in the captured output, in any state |
| 2 | `VS_API_KEY` is read from the environment | `monkeypatch.delenv("VS_API_KEY", raising=False)` then `Settings(api_key_admin="a").web_api_key == ""`; with `setenv("VS_API_KEY", "a")` the state is `admin` (in `test_config.py`) |
| 2 | both role keys equal | `Settings(api_key_admin="k", api_key_monitor="k", api_key="k").web_api_key_state() == "admin"` |
| 2 | empty Monitor key | `Settings(api_key_admin="a", api_key_monitor="", api_key="x").web_api_key_state() == "no_role"`; with `api_key=""` it is `not_set` |

The lifespan starts the scheduler and calls `register_default_jobs`, as the existing lifespan tests do; the game server is not started (`auto_start_server` defaults to false and the temp data directory has no settings file).

### Existing tests that change (deliberately)

Found by running the whole API suite against a throwaway prototype of Tasks 1 and 2 at b6ae2f2 (since discarded). Baseline: 2858 passed. With the prototype: 2826 passed, 18 failed, 14 errors, all in the three files below. Nothing else failed.

**Task 1 (the refactor):**

- `api/tests/test_main.py` `TestLifespanAutoStart` (`:284-571`), five tests: each imports `lifespan` from `main` (`:292`, `:356`, `:418`, `:480`, `:535`) and patches `vintagestory_api.main.Settings` to return `mock_settings` (`:323`, `:385`, `:447`, `:507`, `:556`). Change each to import `lifespan_for`, drop the `Settings` patch, and enter `async with lifespan_for(mock_settings)(test_app):`. Everything else in them stays. `mock_settings` is a `MagicMock`; after Task 2 its `web_api_key_state()` returns a mock that equals none of the states, so no warning is logged, which is fine for these tests.
- `api/tests/test_frontend_routes.py`: `register_frontend` needs the settings. The `client` fixture (`:36-40`) and `test_assets_are_optional` (`:75-83`, call at `:80`) pass `Settings(api_key_admin="admin")`; `TestRuntimeConfig._client` (`:117-121`) passes its `settings` argument and drops the `dependency_overrides` line (`:120`) and the `get_settings` import (`:13`). All 21 tests in the file failed or errored in the prototype for this reason only.

**Task 2 (the breaking change):**

- `api/tests/test_config.py` `TestWebApiKey` (`:148-175`): `test_falls_back_to_admin_key_when_unset` (`:156-159`) and `..._when_blank` (`:161-164`) become "is empty when unset / blank" and expect `""`; `test_web_api_key_has_a_role` (`:166-175`) becomes a parametrized test of `web_api_key_state()` (`None` → `not_set`, `admin-key` → `admin`, `monitor-key` → `monitor`, `other-key` → `no_role`). Update the class docstring to cite Epic 19 ADR-5.
- `api/tests/test_frontend_routes.py` `test_falls_back_to_admin_key` (`:131-134`): becomes "serves an empty key when `VS_API_KEY` is unset" and expects `window.__VSM_CONFIG__ = {"apiKey": ""};\n`. `test_is_a_never_cached_script` (`:145-152`) and `test_other_sites_cannot_include_it` (`:154-160`) build `Settings(api_key_admin="admin")`, which reads `VS_API_KEY` from the environment: pass `api_key=None` so they pin the headers for the empty key (AC 1) whatever the environment holds.

**Tests that construct or import `app` and do not change** (all passed against the prototype; the module still exposes `app`):

`tests/conftest.py:17`, `tests/console/conftest.py:19`, `test_auth.py:339`, `test_debug_api.py:14`, `test_debug_gating.py:17`, `test_jobs_registration.py:259`, `:275`, `test_jobs_router.py:21`, `test_main.py:23-28` (and `load_fresh_app`, `:232-246`, with the four `TestImportTimeWiring` tests, `:249-281`), `test_metrics_api.py:19`, `test_mod_operation_lock_router.py:21`, `test_mod_update_all_router.py:18`, `test_mod_updates_router.py:15`, `test_mod_version_change_router.py:20`, `test_mods_router.py:21`, `test_rbac_integration.py:15`, `test_routers_config.py:48`, `test_scheduler.py:349`, `:363`, `:378`, `:392`, `:406`, `test_static_serving.py:6`, `test_versions_router.py:20`, `server/test_coverage_additions.py:675`, `:735`, `server/test_endpoints.py` (13 local imports, `:40` to `:1217`), `server/test_install_endpoints.py:34`, `:312`, `:429`, `server/test_version_floor.py:14`. The lifespan tests in `test_scheduler.py` and `test_jobs_registration.py` start the module's `app`; its lifespan now uses the settings cached at import instead of a new `Settings()`, which is the same environment in the suite.

- Environment note: in a worktree without `.env`, set `VS_API_KEY_ADMIN` before `just test-api` (CI uses `ci-placeholder-key`, `.github/workflows/ci.yml:23`); without it about 80 lifespan-driven tests error for a reason that is not this story's. `VS_API_KEY` does not need to be set for the suite.
- Anything else that fails is a regression (AC 9): fix the code, not the test.

### Web tests

- `web/src/components/NoApiKeyScreen.test.tsx` (new): renders the heading `No API key configured`; the text contains `VS_API_KEY`, `VS_API_KEY_MONITOR`, `VS_API_KEY_ADMIN`, "restart" and "Anyone who can open this page receives that key"; no `textbox` and no `button` role; `devServer={true}` shows `no-api-key-dev-hint` naming `VITE_API_KEY` and `web/.env`, `devServer={false}` does not.
- `web/src/api/client.test.ts` (extend the "runtime configuration" block, `:202-239`): `getApiKey()` returns the runtime key, falls back to `VITE_API_KEY`, and is `''` when both are empty (`window.__VSM_CONFIG__ = { apiKey: '' }` and `delete import.meta.env.VITE_API_KEY`). The existing tests there stay.
- `web/src/App.no-key.test.tsx` (new; `App.test.tsx` does not render the real `App`, it mirrors the routes, and stays as it is). Renders the real `App` inside a `QueryClientProvider`:
  - No key (`delete import.meta.env.VITE_API_KEY`, `window.__VSM_CONFIG__ = { apiKey: '' }`): `no-api-key-screen` is shown; `globalThis.fetch` (a `vi.fn()`) was not called; a `WebSocket` stub (`vi.stubGlobal`) was not constructed; there is no element with the `navigation` role (the sidebar's `<nav>`, `components/layout/Sidebar.tsx:158`).
  - With a key (`window.__VSM_CONFIG__ = { apiKey: 'k' }`), `fetch` stubbed to a promise that never settles: `no-api-key-screen` is absent and the app shell renders (the sidebar's `navigation` role; the layout has no test id of its own). Restore `import.meta.env` and `delete window.__VSM_CONFIG__` after each test, as `client.test.ts:131-139` does.
  - This file was not prototyped. `Layout.test.tsx:12-23` mocks `@/hooks/use-game-config`, `@/lib/cookies` and `next-themes` to render the layout; if the with-key test needs more than a pending `fetch`, use the same mocks, or mock `@/components/layout/Layout` to a stub that renders a marker and its children and assert on the marker. Do not weaken the no-key test, which must render the real `App` unmocked apart from `fetch` and `WebSocket`.
- No existing web test imports `App` (only `main.tsx:6` does), so none should change. `just test-web` must stay green apart from the 4 pre-existing skips (`VSS-hnl`).

### E2E (`web/e2e/config-js.ts`, `web/e2e/no-api-key.spec.ts`)

**The helper** (`web/e2e/config-js.ts`; Playwright's `testDir` matches `*.spec.ts` only, so it is not collected):

```ts
import type { Page } from '@playwright/test';

/** Answer /config.js with the given key, whatever key the stack hands the web UI. */
export async function serveConfigKey(page: Page, apiKey: string): Promise<void> {
  await page.route('**/config.js', (route) =>
    route.fulfill({
      contentType: 'application/javascript',
      body: `window.__VSM_CONFIG__ = ${JSON.stringify({ apiKey })};`,
    })
  );
}
```

It is the body six specs already repeat (`layout-widths.spec.ts:102-109`, `monitor-password-redaction.spec.ts:44-51`, and four more). This story does not edit those specs or remove the dead `localStorage` init scripts: Story 19.7 moves every spec to the helper (ADR-14 decision 6).

**The spec.** Header comment in the style of `mod-detail-bad-data.spec.ts:3-20` and `layout-widths.spec.ts:21-34`: Story 19.2, FR210, ADR-5; reads only; needs only the stack (no mod database, no game server), so it carries no tag in Story 19.7's CI run. `const API_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';`.

- **No key, three paths** (`/`, `/game-server/mods/browse`, `/config`): `serveConfigKey(page, '')`; collect `page.on('request')` URLs whose path starts with `/api/` and `page.on('websocket')` events before `goto`; open the path; expect `no-api-key-screen` visible with the heading `No API key configured` and the text `VS_API_KEY`; `page.getByRole('navigation')` has count 0; after `page.waitForLoadState('networkidle')` both collections are empty. The mods path proves no lookup reaches the mod database.
- **With a key:** `serveConfigKey(page, API_KEY)`, open `/`: `no-api-key-screen` has count 0 and `page.getByRole('navigation').first()` is visible (the sidebar; the dashboard's own requests need no mod database and no game server).
- **The stack hands out a key (AC 7):** `request.get('/config.js')` without a stub; assert on a boolean (`expect(servesAKey).toBe(true)`, where `servesAKey` is whether the parsed `apiKey` is non-empty), so a failure never prints the key in the report.
- No write, no real state change, nothing to restore. Do not start or stop the game server. No screenshots. No `test.only`.

The image has no `VITE_API_KEY`, so an empty `/config.js` key is the no-key state. Under the Vite dev server the spec is not valid; it is written for the Docker stack on `E2E_BASE_URL` (default `http://localhost:8080`).

### Manual check (Task 6.3)

On the Docker stack built from this branch (the same stack the E2E ran against; no extra restart, no change to `.env`, no screenshots, and the game server is neither started nor stopped):

1. Default dev stack: the UI works as before with the Admin key; the count from Task 5.3 shows `web_api_key_is_admin_key` once per start.
2. Run the spec headed (`bunx playwright test e2e/no-api-key.spec.ts --headed`) or stub `/config.js` in the browser's dev tools: the set-up screen reads well in light and dark mode at phone and desktop widths, and the network panel shows no `/api/` request.
3. Read the new README Security paragraph, the Configuration row and the `.env.example` block as an operator upgrading from `0.1.0-rc.4` would: is it clear what to set?

The other `VS_API_KEY` states (blank, Monitor key, no role) are covered by the API tests; checking them by hand means editing `.env` and restarting the container, which also restarts a running game server, so it is not part of this check. The maintainer ticks 6.3.

### Not changed (do not "fix" these here)

- The CORS `Settings()` and the RBAC test router's `Settings().debug` in `main.py` (`:177`, `:219`), `docs_url` and the Content-Security-Policy: Story 19.3 (ADR-6, ADR-7 decision 6). `Settings()` calls in the services: not in this epic.
- A login or a key field in the browser: `VSS-2kdt`.
- The six E2E specs' own `/config.js` stubs, the fifteen dead `localStorage` init scripts, the CI job: Story 19.7. `api/tests/e2e/conftest.py:89` (reads `VS_API_KEY` for a `localStorage` key the web no longer reads) is the same dead pattern; leave it.
- `apiClient`'s behaviour with an empty key (`client.test.ts:186-200` stays), the `/config.js` headers and JSON encoding, `web/public/config.js`, `web/index.html`.
- `VS_API_KEY_ADMIN` missing still refuses to start (`config.py:178-182`); a key matching no role still starts and warns.
- `scripts/worktree-setup.sh`, the `Dockerfile`, `.github/workflows/ci.yml`.
- The maintainer's cluster deployment (another repository).

### API contract changes

- **Breaking:** `GET /config.js` with `VS_API_KEY` unset or blank serves `window.__VSM_CONFIG__ = {"apiKey": ""};` instead of the Admin key, and the web UI shows a set-up screen. Status, content type and the three headers are unchanged. Setting `VS_API_KEY` to the Monitor key or the Admin key restores a working web UI.
- **`VS_API_KEY`:** no longer optional for the web UI. It has no default.
- **Start-up log, added:** warning `web_api_key_not_set` (no key for the web UI) and warning `web_api_key_is_admin_key` (the web UI's key is the Admin key). `web_api_key_matches_no_role` is unchanged. None carries a key.
- **Dev stack only:** `docker-compose.dev.yaml` sets `VS_API_KEY` to the Admin key when it is unset or empty.
- No REST endpoint under `/api/v1alpha1`, response field or error code changes. `/healthz` and `/readyz` are unchanged.
- Internal (not a contract): `Settings.web_api_key_has_a_role()` is replaced by `web_api_key_state()`; `register_frontend` takes the settings; `main.lifespan` becomes `main.lifespan_for(settings)`; `main.create_app` is new.

### ADR against the code

- **ADR-5 decision 11** says the lifespan "uses the cached `get_settings()`" (`:96`). Calling `get_settings()` inside the lifespan would make an app built with other settings start with the environment's settings, and AC 8 could not be tested. The story passes the settings into the lifespan through the factory, and the server's app is built from `get_settings()`, which gives what the decision asks for.
- **ADR-5 decision 11** does not say how `/config.js` gets the settings. It reads them from the factory (through `register_frontend`), not from `Depends(get_settings)`, for the same reason. For the server's `app` both are the same object.
- **ADR-5 "Release"** fixes the commit subject as `feat(api)!: ...`, which is not `type(story-X.Y/task-N)` (`project-context.md:615-669`). `cliff.toml` prints `**api:**` only for the component scopes and hides story scopes, so the ADR's form is used for that one commit; see "Git Intelligence".
- The proposal says the release note "is the first entry". Checked with `just changelog` on a throwaway commit: Breaking Changes is the first group, and the entry is the last line in it (commits are sorted oldest first; the group already holds dependency upgrades since the last stable tag). Nothing to do in this story.
- Everything else in ADR-5 and in "Facts Checked in the Code" ("The web UI's key", "How the app is built") matches the code at b6ae2f2. Nested defaults in Compose (`${VS_API_KEY:-${VS_API_KEY_ADMIN:-changeme}}`) were checked with `docker compose config`: unset and empty both give the Admin key, a set value wins.

### Testing Requirements

**CRITICAL:** Tests are written with each task and committed with it, red first. `just test-api <file>` / `just test-web <file>` after each task; `just check` before review.

- Each warning is asserted both ways (AC 8). A test that only checks "the warning is logged in its state" is not enough.
- Tests must not write into `dev/` (`just test-api` sets `VS_DATA_DIR=../dev`): pass `data_dir=tmp_path / ...` to every `Settings` whose app is started. `git status --short` after the suite shows nothing under `dev/`.
- Never print or assert on a real key. Test keys are made-up literals; E2E asserts on booleans where the stack's own key is involved.
- No lint or type suppression and no `cast` in the diff.

### Security Requirements

- `/config.js` stays unauthenticated by design (Epic 15 ADR-5) and keeps `Cache-Control: no-store`, `Cross-Origin-Resource-Policy: same-origin` and `X-Content-Type-Options: nosniff`. The key is JSON-encoded (`test_key_is_json_encoded` stays).
- No key is ever logged: the three warnings carry an event name and a fixed hint only.
- Whatever key `VS_API_KEY` names is still handed to anyone who can load the page; the documentation says so. This story removes the default, not the exposure (`VSS-2kdt` is the login).
- The screen renders fixed text only; nothing from the server or the URL is inserted into it.

### Development Commands

- `just test-api tests/test_app_factory.py tests/test_main.py tests/test_frontend_routes.py tests/test_config.py`, `just test-api`, `just typecheck-api`, `just lint-api`
- `just test-web src/components/NoApiKeyScreen.test.tsx src/App.no-key.test.tsx src/api/client.test.ts`, `just typecheck-web`, `just lint-web`
- `just changelog`, `just check`
- `just docker restart`, then `cd web && bunx playwright test e2e/no-api-key.spec.ts`
- Do not run `just format-api` or a whole-repo formatter (reformats unrelated files; Story 17.2 process note). Do not run `just release`.

### Previous Story Intelligence

- **15.2** (Epic 15 ADR-5, the runtime key): its review added `Cross-Origin-Resource-Policy` and the `web_api_key_matches_no_role` warning; both stay. Its review note: a reviewer's transcript once echoed a key from `.env`. Use count-only or boolean output whenever a real key could appear (Tasks 4.4 and 5.3).
- **17.5** (Monitor redaction): the web reads its key only from `/config.js` or `VITE_API_KEY`, never `localStorage`; E2E chooses the page's key by answering `/config.js`.
- **17.3 / 17.4:** a TanStack Query v5 hook-level `onError` replaces the client default, so such a hook must call `handleApiError` itself. This story adds no hook; do not add one for the screen.
- **17.4 / 18.2:** tests must not write into `dev/`; router or lifespan tests that use the real settings do.
- **17.2:** an E2E that changes real state needs a snapshot guard and must restore the stack exactly; this story's E2E changes nothing. A `feat`/`fix` subject must describe something an admin can see.
- **17.x / 18.x reviews:** a completion note must be true of the code; manual checks wait for the maintainer.
- **19.1** (lands first): removes `VS_GAME_VERSION` from `config.py` (`:24`), `.env.example` (`:20-23`), both compose files and `scripts/worktree-setup.sh`. Re-read line numbers in those files before editing; rebase conflicts there are textual only.

### Git Intelligence

- Base `b6ae2f2` (`docs(epic-19): fold the maintainer's observation decisions into epic 19`). Story 19.1's branch lands before this one.
- Planned commits:
  - Task 1: `refactor(story-19.2/task-1): build the app through a factory from its settings` (no release note; nothing an admin can see).
  - Task 2, exactly (ADR-5 "Release"; the scope `api` is what `cliff.toml` prints, and the subject carries the instruction because the template prints the subject, not the footer):

    ```
    feat(api)!: the web UI no longer receives the Admin key by default; set VS_API_KEY to the Monitor or Admin key

    Story 19.2, task 2 (VSS-9wv).

    BREAKING CHANGE: /config.js serves no key when VS_API_KEY is unset or blank, and the web UI shows a set-up message. Set VS_API_KEY to VS_API_KEY_MONITOR for a read-only web UI or to VS_API_KEY_ADMIN for full access; anyone who can load the web UI receives that key.
    ```

    The `!` goes after the scope (`RELEASING.md:24-27`). The `BREAKING CHANGE:` footer is the last paragraph, with nothing after it. This is the one commit of the story whose scope is not `story-19.2/task-N`; the story reference goes in the body. Verified at b6ae2f2 with a throwaway commit: `just changelog` printed `- **api:** The web UI no longer receives the Admin key by default; set VS_API_KEY to the Monitor or Admin key` under `### Breaking Changes`.
  - Task 3: `feat(story-19.2/task-3): the web UI says what to set when it has no API key` (an admin sees the screen).
  - Task 4: `docs(story-19.2/task-4): document VS_API_KEY and give the dev stack the Admin key itself`.
  - Task 5: `test(story-19.2/task-5): e2e config.js helper and the no-key spec`.
  - Task 6: `chore(story-19.2/task-6): validate and move story 19.2 to review`.
- Between the Task 2 and Task 4 commits the dev stack shows the set-up screen when `VS_API_KEY` is not in `.env`; run the E2E only after Task 4.
- While the version is `0.x` a breaking change bumps the minor version (`RELEASING.md:9-15`); nothing to do here.

### Project Structure Notes

- New: `api/tests/test_app_factory.py`, `web/src/components/NoApiKeyScreen.tsx`, `web/src/components/NoApiKeyScreen.test.tsx`, `web/src/App.no-key.test.tsx`, `web/e2e/config-js.ts`, `web/e2e/no-api-key.spec.ts`.
- Modified: `api/src/vintagestory_api/main.py`, `config.py`; `api/tests/test_main.py`, `test_frontend_routes.py`, `test_config.py`; `web/src/api/client.ts`, `client.test.ts`, `web/src/App.tsx`; `docker-compose.yaml`, `docker-compose.dev.yaml`, `.env.example`, `README.md`.
- `web/e2e/` is outside `web/tsconfig.json`'s `include` (`src`, `tests`), so the helper is type-checked by Playwright's own transform only; keep it as small as shown.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 19.2: The Web UI No Longer Gets the Admin Key]
- [Source: _bmad-output/planning-artifacts/prd.md] FR210, FR211, FR212
- [Source: _bmad-output/planning-artifacts/architecture/epic-19-api-security-and-mod-file-safety.md#ADR-5] (and "Facts Checked in the Code": "The web UI's key", "How the app is built"; ADR-7 decision 6 and ADR-14 decisions 5-6 for what Stories 19.3 and 19.7 take over)
- [Source: _bmad-output/planning-artifacts/architecture/epic-15-release-engineering.md#ADR-5: Runtime Web Configuration] (changed by this story: no fallback)
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-17.md] (section 2 API change table and release-note subjects; section 5 answered questions 1, 2 and 8, observation 3)
- [Source: _bmad-output/implementation-artifacts/15-2-runtime-api-key-for-the-web-ui.md], [17-5-monitor-keys-cannot-read-the-server-password.md]
- `RELEASING.md` ("Commit messages are release notes"), `cliff.toml`
- Beads: `VSS-9wv`, parent `VSS-fl9b`; blocks `VSS-2kdt` (login, not in scope)
- `project-context.md` (no suppressions; manual test tasks need the maintainer's confirmation; commit format)

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5), BMAD dev-story workflow, non-interactive.

### Debug Log References

- Line numbers re-checked after Story 19.1: `main.py` was unchanged by 19.1 (the story's `:91-283` held); in `config.py` 19.1 removed `VS_GAME_VERSION` (`:24`) below the field comment, which stays at `:22`, so `web_api_key` is at `:30-35` and `web_api_key_has_a_role` at `:37-39`; in `.env.example` the `VS_API_KEY` block is at `:35-39`, in both compose files the `VS_API_KEY` comment and line at `:19-21` (prod) and `:19-20` (dev); README lines `:25`, `:37`, `:77` (the table row moved from `:75` to `:77`).
- API baseline at the start of the story (after 19.1): 3033 passed with the Task 1 tests added; 3048 after Task 2.
- Task 2 red: 17 failed before the change (the config, factory-state and frontend-route tests); Task 3 red: 4 web tests failed (the new files did not exist, `getApiKey` was not exported).
- `ruff format --check` reports pre-existing drift in `main.py` (one blank line before `STATIC_DIR`), `config.py` and `tests/test_main.py`/`tests/test_config.py` that this story did not introduce; it was left alone (no whole-file reformat). `just lint-api` is clean.
- Task 4.4 (`docker compose ... config`, values compared, never printed): in a scratch directory without `.env`, `docker-compose.dev.yaml` gives `VS_API_KEY` = the Admin key's default when `VS_API_KEY` is unset and when blank, and the chosen value when set; `docker-compose.yaml` gives it empty when unset and blank. In this checkout (whose `.env` defines `VS_API_KEY`) the dev value matches the Admin key.
- Docker dev stack rebuilt with `just docker restart` after Task 4; the game server was not running before or after (`ps` check in the container), and nothing started or stopped it.

### Completion Notes List

- Task 1: `main.py` has `lifespan_for(settings)` (the old lifespan body, closed over `settings`, no `Settings()` inside), `register_frontend(target, static_dir, settings)` whose `/config.js` handler takes no dependency, and `create_app(settings, static_dir=STATIC_DIR)` holding the middleware, routers and frontend registration in the old order. The module ends with `app = create_app(get_settings())`. The CORS `Settings()` (now `cors_settings`) and the RBAC router's `Settings().debug` stay inside the factory for Story 19.3. Only `test_main.py` (five `TestLifespanAutoStart` tests) and `test_frontend_routes.py` changed; `tests/test_app_factory.py` covers start-up with the given settings, `/config.js` from the given settings rather than the environment, and no frontend without a static directory.
- Task 2: `Settings.web_api_key` returns `""` when `VS_API_KEY` is unset or blank; `web_api_key_state()` returns `not_set`/`admin`/`monitor`/`no_role` in that order (Monitor only when `api_key_monitor` is truthy). `main.log_web_api_key_state(settings)` logs `web_api_key_not_set`, `web_api_key_is_admin_key` or the unchanged `web_api_key_matches_no_role`, each with a fixed hint and never a key; the lifespan calls it where the old check was. `test_app_factory.py` asserts, for the five states (unset, blank, Admin, Monitor, other), the exact `/config.js` body, its three headers, `/healthz`/`/readyz` 200, each of the three events both ways and that no key value is in the start-up output. `test_config.py` covers the states, both role keys equal, an empty Monitor key and reading `VS_API_KEY` from the environment. Committed with the story's exact `feat(api)!:` subject and the `BREAKING CHANGE:` footer last; `just changelog` lists `**api:** The web UI no longer receives the Admin key by default; set VS_API_KEY to the Monitor or Admin key` under Breaking Changes (AC 10).
- Task 3: `client.ts` exports `getApiKey()` (the one expression; `getConfig` uses it). `NoApiKeyScreen` renders a `<main data-testid="no-api-key-screen">` with the `KeyRound` icon, the `<h1>`, the text and two-item list of the story with variable names in `<code>`, and `no-api-key-dev-hint` only when `devServer` (default `import.meta.env.DEV`). `App` returns `<ThemeProvider><NoApiKeyScreen /></ThemeProvider>` when `getApiKey()` is empty, checked at render. `App.no-key.test.tsx` renders the real `App` unmocked apart from `fetch` and `WebSocket` in both tests; the with-key test needed no extra mocks (the never-settling `fetch` was enough to render the sidebar).
- Task 4: `docker-compose.dev.yaml` passes `VS_API_KEY=${VS_API_KEY:-${VS_API_KEY_ADMIN:-changeme}}`; `docker-compose.yaml` keeps `${VS_API_KEY:-}` with the new comment; `.env.example` and README (Installation step 2, Security, Configuration table) describe the new behaviour, Monitor key first. README Upgrading is unchanged.
- Task 5: `web/e2e/config-js.ts` exports one function, `serveConfigKey(page: Page, apiKey: string): Promise<void>`, which answers `**/config.js` with `window.__VSM_CONFIG__ = {"apiKey": <apiKey>};` (JSON-encoded), so a spec chooses the page's key (`''` for the no-key state). Stories 19.3-19.7 can import it with `import { serveConfigKey } from './config-js';`. `web/e2e/no-api-key.spec.ts`: 5 tests (no key on `/`, `/game-server/mods/browse`, `/config`: screen, heading, `VS_API_KEY`, no `navigation`, no `/api/` request and no WebSocket after network idle; with a key the sidebar renders; the stack's own `/config.js` serves a non-empty key, asserted as a boolean). Against the rebuilt dev stack with `VS_API_KEY_ADMIN` exported from `.env`: 5 passed. `e2e/mods-navigation.spec.ts` and `e2e/mod-browse-state.spec.ts`: 11 passed. `docker logs vintagestory-manager-dev | grep -c web_api_key_is_admin_key`: 1 (one start); `web_api_key_not_set`/`web_api_key_matches_no_role`: 0; the Admin key value occurs 0 times in the container log. No screenshots; no state changed.
- Task 6: `just check` passes: API 3048 passed, Pyright 0 errors and the 3 known warnings (`VSS-1ar`), web 3325 passed and 4 skipped (`VSS-hnl`), script tests green. No suppression, `cast` or type assertion added. `git status --short` shows nothing under `dev/` after the suites. `just changelog`: the Task 2 commit is the only commit of this story under Breaking Changes; the Task 3 commit is under Features; the Task 1 refactor appears nowhere.
- 6.3 (manual check) is left unticked for the maintainer. 6.4: story status is `review` and sprint status set to `review`; the PR, its description (breaking change first, API contract changes, deployment note) and the PR link on `VSS-9wv` are left to the maintainer/orchestrator (this run was told not to push or open PRs, or to change beads), so 6.4 stays unticked.

### File List

- `api/src/vintagestory_api/main.py` (modified)
- `api/src/vintagestory_api/config.py` (modified)
- `api/tests/test_app_factory.py` (new)
- `api/tests/test_main.py` (modified)
- `api/tests/test_frontend_routes.py` (modified)
- `api/tests/test_config.py` (modified)
- `web/src/api/client.ts` (modified)
- `web/src/api/client.test.ts` (modified)
- `web/src/App.tsx` (modified)
- `web/src/App.no-key.test.tsx` (new)
- `web/src/components/NoApiKeyScreen.tsx` (new)
- `web/src/components/NoApiKeyScreen.test.tsx` (new)
- `web/e2e/config-js.ts` (new)
- `web/e2e/no-api-key.spec.ts` (new)
- `docker-compose.yaml` (modified)
- `docker-compose.dev.yaml` (modified)
- `.env.example` (modified)
- `README.md` (modified)
- `_bmad-output/implementation-artifacts/19-2-web-ui-no-longer-gets-the-admin-key.md` (modified)

## Change Log

- 2026-11-16: Story 19.2 created and validated (ready-for-dev).
- 2026-11-16: Tasks 1-5 and 6.1-6.2 implemented; status review (6.3 manual check and 6.4 PR left for the maintainer).
