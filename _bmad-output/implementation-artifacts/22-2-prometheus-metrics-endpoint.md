# Story 22.2: A Prometheus `/metrics` Endpoint

Status: ready-for-dev

<!-- Implements FR289-FR291 and FR306, Epic 22 ADR-3, ADR-4 and ADR-14. Bead: VSS-bhw (API-023), closes here (Story 22.1 carried its first half). Maintainer answers 1, 2 and 3 (Matt, 2026-11-18). Stories run in order 22.1 to 22.6; this branch, story/22-2-prometheus-metrics-endpoint, is stacked on story/22-1-players-online-are-counted at 7672fc90 (22.1 in review: it adds ServerService.players_online and the PlayerTracker). The PR targets main and merges after 22.1's. Line references were verified at 7672fc90 (re-checked in validation at e2b55388) and must be re-checked at implementation time. API and documentation only; no web source change. One new runtime dependency (prometheus-client), one new open route, two new modules, one API E2E test, and one fix pulled in by the controller during validation (backlog drawdown, FR306): game settings and mods share one pending-restart state ("ADR against the code" 8). -->

## Story

As an **operator who runs Prometheus and Grafana**,
I want **the manager to serve the game server's metrics in the Prometheus format**,
so that **I can graph players, CPU, memory and uptime, and alert when the server is down, with the tools I already use**.

## Acceptance Criteria

1. **Given** a running API
   **When** a client without an API key (or with a wrong one) requests `GET /metrics`
   **Then** the answer is 200 with `Content-Type: text/plain; version=0.0.4; charset=utf-8` (prometheus-client's `CONTENT_TYPE_PLAIN_0_0_4`) and a body in the Prometheus text format
   *(Covers FR289; ADR-3 decisions 2 and 6; see "ADR against the code" 1)*

2. **Given** the game is running, version 1.22.7, with two players, `MaxClients` 16 and no pending restart
   **When** `/metrics` is scraped
   **Then** it has `vintagestory_server_info{version="1.22.7"} 1`, `vintagestory_server_up 1`, `vintagestory_server_state{state="running"} 1` and a 0 series for each of the other six `ServerState` values, `vintagestory_server_uptime_seconds`, `vintagestory_players_online 2`, `vintagestory_players_max 16`, `vintagestory_server_pending_restart 0`, `vintagestory_server_process_cpu_seconds_total` (type counter) and `vintagestory_server_process_resident_memory_bytes`, each with the `# HELP` and `# TYPE` of Dev Notes "The metric contract", and the manager's `python_info` and `python_gc_*` series, plus `process_*` where `/proc` exists (Linux, so in the image and in CI). The text format writes the values as `1.0`, `0.0`, `16.0`; tests parse the body, they do not compare strings
   *(Covers FR289; ADR-4 decisions 1, 3 and 4; see "ADR against the code" 3)*

3. **Given** the game is installed and stopped
   **When** `/metrics` is scraped
   **Then** `vintagestory_server_up` is 0, `vintagestory_server_state{state="installed"}` is 1, `vintagestory_players_online` is 0, `vintagestory_server_info` is present, and the uptime and both `vintagestory_server_process_*` series are absent
   *(Covers FR290; ADR-4 decision 2)*

4. **Given** no game is installed
   **When** `/metrics` is scraped
   **Then** `vintagestory_server_info` is absent, `vintagestory_server_state{state="not_installed"}` is 1, `up`, `players_online` and `pending_restart` are present with 0; `vintagestory_players_max` is present when `serverconfig.json` exists and has a whole-number `MaxClients`, and absent otherwise, without a WARNING for a missing file
   *(Covers FR290; ADR-4 decision 2; see "ADR against the code" 5)*

5. **Given** `metrics_collection_interval` is 0 (the collection job is off)
   **When** `/metrics` is scraped twice while the game runs and the player count changes between the scrapes
   **Then** each answer carries the values current at its scrape, the CPU counter does not go down, and nothing reads the metrics ring buffer
   *(Covers FR290; ADR-3 decision 4)*

6. **Given** one source raises (the server status, the player count, the pending-restart state, reading `MaxClients`, or the game process's psutil read other than "the process just exited")
   **When** `/metrics` is scraped
   **Then** the answer is 200 with every other series, that source's series are absent, and exactly one WARNING `prometheus_source_failed` with `source` and `error_type` is logged for it in that scrape
   *(Covers FR290; ADR-3 decision 5; see "ADR against the code" 6)*

7. **Given** the web UI is served by the API
   **When** `/metrics` is requested
   **Then** the metrics answer it, not the web UI's page, and the answer carries no `Content-Security-Policy`, `Content-Security-Policy-Report-Only` or `X-Frame-Options` header, as `/healthz`; every other path still reaches the web UI
   *(Covers FR289; ADR-3 decision 2)*

8. **Given** players are online and the series are scraped
   **When** I read the body and the API's log
   **Then** the only labels on `vintagestory_*` series are `version` and `state`, the body holds no player name, address, path or key, and a scrape that succeeds logs nothing at INFO or above from the API (uvicorn's own access line is unchanged, as for `/healthz`)
   *(Covers FR289; ADR-3 decision 6; ADR-1 decision 4)*

9. **Given** the README
   **When** I read its metrics section
   **Then** it lists each series with its meaning and when it is absent, says that the endpoint is open and how to keep it off the internet, and gives a Prometheus `scrape_configs` example with `metrics_path: /metrics` and a placeholder target; the Features list names `/metrics`; the PRD's two post-MVP Prometheus lines say Epic 22
   *(Covers FR291; ADR-3 decision 6)*

10. **Given** the API in a container (the CI E2E stack)
    **When** the API E2E tests run
    **Then** one test scrapes `/metrics` without a key and finds `vintagestory_server_up`, exactly one `vintagestory_server_state` series at 1, `python_info` and `process_resident_memory_bytes`
    *(Covers FR289)*

11. **Given** every existing test
    **When** the suites run
    **Then** they pass unchanged, except `test_get_pending_restart_state_singleton_initialization` (`api/tests/test_routers_config.py:2129-2146`), rewritten for the shared state (AC 13); Pyright reports 0 errors and 0 warnings; no test starts or stops the dev stack's game server and no test writes into `dev/`

12. **Given** a real Prometheus (or `curl`) and the dev stack at `http://localhost:9080`
    **When** the maintainer scrapes `/metrics`, read-only
    **Then** the series of AC 2 to 4 appear for the stack's state (manual check, reserved for the maintainer, ticked only on his confirmation)
    *(Covers FR289; ADR-14 decision 4)*

13. **Given** an admin saves a game setting that needs a restart (`Port` or `Ip`; or `ServerDescription` cleared while the game runs)
    **When** `/healthz`, `GET /api/v1alpha1/mods` and `/metrics` are read
    **Then** `/healthz` has `game_server_pending_restart: true`, the mods list has `pending_restart: true` (what the web's "Restart required" banner reads) and `vintagestory_server_pending_restart` is 1; after a restart through `ServerService.restart_server` (game start mocked) all three are false / 0 again. Game settings and mods share one `PendingRestartState`
    *(Covers FR306; pulled in by the controller during validation, backlog drawdown; see "ADR against the code" 8)*

## Tasks / Subtasks

<!-- Each functional task includes its tests in the same commit, red first (run the new tests, see them fail, then implement). Subjects: type(story-22.2/task-N): ..., the type chosen by what an admin notices. Two commits are user-visible: Task 2 (fix) and Task 4 (feat), each with a subject written for admins; their bodies name Story 22.2 and the task. -->

- [ ] Task 1: Add `prometheus-client` + tests (AC: 1, 11)
  - [ ] 1.1: Red first: new `api/tests/test_prometheus_metrics.py` with one test, `test_plain_text_content_type_is_version_0_0_4`: `from prometheus_client import CONTENT_TYPE_PLAIN_0_0_4` equals `"text/plain; version=0.0.4; charset=utf-8"` (it pins the constant the route uses, so a Renovate bump that changes it fails here). Run `just test-api tests/test_prometheus_metrics.py`; it fails at import
  - [ ] 1.2: `cd api && uv add "prometheus-client>=0.26.0,<1"` (no `just` recipe adds a dependency; precedent: Stories 7.0 and 12.2). Check `api/pyproject.toml` `dependencies` (`:6-13`) gains exactly that line in alphabetical order and `api/uv.lock` gains `prometheus-client` 0.26.x and nothing else changes version (`git diff --stat`; the Dockerfile installs with `uv sync --frozen`, `Dockerfile:59`, `:63`, so the lock must be committed with it)
  - [ ] 1.3: `just test-api tests/test_prometheus_metrics.py` green; `just typecheck-api` 0 errors, 0 warnings (the package ships `py.typed`; checked in planning and again in validation with pyright strict)
  - [ ] 1.4: Commit `build(story-22.2/task-1): add the prometheus-client dependency`

- [ ] Task 2: One pending-restart state for game settings and mods + tests (AC: 11, 13)
  - [ ] 2.1: Red first: new `api/tests/test_shared_pending_restart.py` with the Task 2 rows of Dev Notes "API tests"; rewrite `test_get_pending_restart_state_singleton_initialization` (`api/tests/test_routers_config.py:2129-2146`, it resets `config_module._pending_restart_state`, which goes away) to assert `get_pending_restart_state() is get_restart_state()`. See them fail
  - [ ] 2.2: `routers/config.py:92-105`: delete the module's own `_pending_restart_state` singleton; `get_pending_restart_state()` keeps its name (it is the dependency of `get_game_config_service`, `:108-125`, and `test_routers_config.py:161` overrides it) and returns `get_restart_state()` from `services/mods.py:80-85`; its comment and docstring say it is the one state `/healthz`, the mods list and `ServerService._clear_pending_restart` use. Nothing else changes: `GameConfigService`, `services/mods.py`, `services/server.py` and the web stay as they are (Dev Notes "One pending-restart state")
  - [ ] 2.3: `cd api && uv run ruff format <changed files>`; `just test-api tests/test_shared_pending_restart.py tests/test_routers_config.py tests/test_game_config.py tests/test_health.py tests/test_pending_restart.py tests/test_mods_router.py tests/server` green; `just typecheck-api` 0/0
  - [ ] 2.4: Commit `fix(story-22.2/task-2): show Restart required when a game setting change needs a restart` (body: Story 22.2 / task 2; a change to the port or IP address set a restart flag that nothing read, so the header's Restart required banner, `/healthz` and a restart ignored it; game settings and mods now share one flag, which a restart clears)

- [ ] Task 3: The game server collector and the project registry + tests (AC: 2, 3, 4, 5, 6, 8, 13)
  - [ ] 3.1: Red first: the Task 3 rows of Dev Notes "API tests" in `api/tests/test_prometheus_metrics.py` and `api/tests/test_game_config.py`; see them fail
  - [ ] 3.2: `services/game_config.py`: a public `GameConfigService.get_max_clients() -> int | None` after `get_settings` (`:604-662`), as Dev Notes "MaxClients" says. No other change in that file
  - [ ] 3.3: New `api/src/vintagestory_api/services/prometheus_metrics.py` (Dev Notes "The collector"): `GameServerCollector` with injectable providers, the five guarded sources, `build_registry(collector)` with `ProcessCollector`, `PlatformCollector`, `GCCollector` on a new `CollectorRegistry`, and the lazy `get_metrics_registry()` singleton. Nothing imports it yet
  - [ ] 3.4: Logging exactly as Dev Notes "What is logged"
  - [ ] 3.5: `cd api && uv run ruff format <changed files>`; `just test-api tests/test_prometheus_metrics.py tests/test_game_config.py` green; `just typecheck-api` 0/0
  - [ ] 3.6: Commit `refactor(story-22.2/task-3): collect the game server's Prometheus metrics at scrape time` (not served yet; precedent `refactor(story-22.1/task-1)`)

- [ ] Task 4: The root `GET /metrics` route without authentication, scraped in the API E2E tests + tests (AC: 1, 7, 8, 10)
  - [ ] 4.1: Red first: new `api/tests/test_prometheus_router.py` with the Task 4 rows of Dev Notes "API tests"; see them fail (404 or the SPA page)
  - [ ] 4.2: New `api/src/vintagestory_api/routers/prometheus.py` (Dev Notes "The route")
  - [ ] 4.3: `main.py`: add `prometheus` to the router import (`:26-39`, alphabetical, after `mods`) and `app.include_router(prometheus.router)` directly after `app.include_router(health.router)` (`:386`), under the same "at root" comment (`:385`), extended to name `/metrics`. Nothing else in `main.py` changes: the middlewares (`:369-383`) apply to it as to `/healthz`, and it is registered before `register_frontend` (`:415-416`), whose `/{full_path:path}` fallback (`:334-339`) would otherwise answer it
  - [ ] 4.4: `cd api && uv run ruff format <changed files>`; `just test-api tests/test_prometheus_router.py tests/test_prometheus_metrics.py tests/test_security_headers_scope.py tests/test_frontend_routes.py tests/test_app_factory.py tests/test_health.py tests/test_static_serving.py` green
  - [ ] 4.5: New `api/tests/e2e/test_e2e_metrics.py` (Dev Notes "E2E test"). Run it only through `just test-e2e-ci` (it builds the image from the branch, runs it on port 18080 and removes it; `scripts/e2e-ci.sh:150-158` runs `pytest tests/e2e` against it). Never `just test-e2e-api`, `just test-e2e` or `just test-e2e-web` (they target or restart the dev stack), and never rebuild or restart the dev stack for it
  - [ ] 4.6: Commit `feat(story-22.2/task-4): serve game server metrics for Prometheus at /metrics` (body: Story 22.2 / task 4; `GET /metrics` at the root, without an API key, in the Prometheus text format: the game server's version, up, state, uptime, players online and maximum, pending restart, the game process's CPU and memory, and the manager's own process metrics; read live, so it works with metrics collection off; scraped by the API E2E tests)

- [ ] Task 5: Document `/metrics` (AC: 9)
  - [ ] 5.1: `README.md`: the Features "API" bullet (`:18`) names `/metrics` beside the health endpoints; a new `### Metrics` section after `### Configuration` (`:73-90`), before `## Development` (`:92`), with the content of Dev Notes "Documentation"
  - [ ] 5.2: `_bmad-output/planning-artifacts/prd.md:149` and `:285`: append ` (Epic 22)` as the other built items on those lists do (`(Epic 14)`, `(Epic 15)`); `_bmad-output/planning-artifacts/architecture/core-architectural-decisions.md:21`: `Prometheus metrics implementation` gains ` (decided in Epic 22: architecture/epic-22-server-operations-and-metrics.md, ADR-3 and ADR-4)`
  - [ ] 5.3: `just lint` green (the README is not linted; this checks nothing else moved)
  - [ ] 5.4: Commit `docs(story-22.2/task-5): document /metrics with a Prometheus scrape example`

- [ ] Task 6: Validate and move the story to review (AC: all)
  - [ ] 6.1: `just check` green: API tests, pyright 0 errors and 0 warnings, ruff; web tests with 0 skipped, tsc, Prettier. The diff adds no lint or type suppression (`# type: ignore`, `# pyright: ignore`, `noqa`), no `cast`, no skipped or `.only` test. `git status --short dev/` is empty after the runs
  - [ ] 6.2: `rg -n "ExamplePlayer|AnotherPlayer|203\.0\.113|198\.51\.100" api/src` finds nothing; `just changelog` lists exactly two new entries from this story (Task 2's fix and Task 4's feature subjects)
  - [ ] 6.3: Manual check (maintainer only; leave unticked until he confirms): scrape `http://localhost:9080/metrics` with a real Prometheus or `curl -s http://localhost:9080/metrics`, read-only, and see the series of AC 2 to 4 for the stack's state. Nobody starts, stops or rebuilds the dev stack for it; if the dev stack runs an older image, the check waits until the maintainer has rebuilt it himself
  - [ ] 6.4: Story status `review` in this file; `just sprint set 22-2-prometheus-metrics-endpoint review`; Dev Agent Record and File List filled in, every statement true of the code
  - [ ] 6.5: Commit `chore(story-22.2/task-6): validate and move story 22.2 to review`
  - [ ] 6.6: After merge, with the maintainer's go-ahead only: AAR comment on `VSS-bhw` and close it (`bd comments add`, `bd close`, `bd sync`; CLAUDE.md "Completing Issues"). Pushing, the PR and the bead wait for that go-ahead

## Dev Notes

### The code today (verified at 7672fc90; re-checked at e2b55388)

- **Open routes:** `health.router` (`api/src/vintagestory_api/routers/health.py:24`, `/healthz` `:88-149`, `/readyz` `:152-180`) is included at the root without a key (`main.py:385-386`); every `/api/v1alpha1` route requires `X-API-Key` (`:389`). `register_frontend` (`:299-339`) adds `/config.js` and a GET-only `/{full_path:path}` fallback that serves `index.html` with the CSP headers (`:330-339`); it is called last (`:415-416`), so any root route registered before it wins. The web app has no `/metrics` route (`web/src/App.tsx:124-142`).
- **Middlewares** (`main.py:369-383`): CORS, `CORSLoggingMiddleware` (DEBUG lines only, and only with an `Origin` header), `RequestContextMiddleware` (`middleware/request_context.py:42-64`: binds a `request_id`, logs nothing). **The API logs no line per request**; uvicorn's default access log (`Dockerfile:92` starts uvicorn without `--no-access-log`) writes one line per request for every route, `/healthz` included. `/metrics` is treated the same: no line of its own.
- **Server status:** `get_server_service()` (`services/server.py:52-60`) is the singleton. `get_server_status()` (`:892-936`) returns `NOT_INSTALLED` (no version) when the two DLLs are missing (`REQUIRED_SERVER_FILES`, `:82`; `is_installed`, `:515-522`); otherwise the runtime state (`_get_runtime_state`, `:938-953`: `INSTALLED`, `STARTING`, `RUNNING` or `STOPPING`), `version` from `vsmanager/current_version` (`get_installed_version`, `:524-533`; `None` if the file is missing) and `uptime_seconds` only while `RUNNING` with a start time (`:923-925`). It also calls `get_disk_space_data()` (`routers/health.py:30-72`, imported at call time at `:900`: it reads `Settings()` from the environment through `get_settings()`, runs `shutil.disk_usage` on `data_dir` and logs `disk_space_check_failed` at WARNING when that fails) and the in-memory versions cache; `/healthz` pays the same, and a disk-check WARNING is the only line a scrape can log outside "What is logged" (it is `/healthz`'s too, not a `/metrics` failure). `INSTALLING` and `ERROR` are install states (`get_install_progress`, `:478-513`) and never come out of `get_server_status`.
- **Game process:** `game_server_pid` (`:206-215`) is the PID while the process lives (`returncode is None`), so also during `STARTING` and `STOPPING`. `players_online` (`:217-222`, Story 22.1) is the tracker's count while `game_server_pid` is set, else `None`. `MetricsService._get_game_metrics` (`services/metrics.py:228-254`) reads the same PID with psutil and treats `NoSuchProcess` as "gone" (DEBUG) and `AccessDenied` as WARNING.
- **Pending restart (before Task 2):** two singletons. `services/mods.py:77-85` (`get_restart_state`): `/healthz` reads it (`routers/health.py:113-118`), the mods list returns it as `pending_restart` (`routers/mods.py:85`, through `ModService.restart_state`, given at `services/mods.py:110`), the mod operations set it, and `ServerService._clear_pending_restart` (`services/server.py:246-258`, called only at the end of `_restart_server_locked`, `:1209`) clears it. `routers/config.py:92-105` (`get_pending_restart_state`) is a second one, the dependency of `get_game_config_service` (`:108-125`), so `GameConfigService._update_config_file` (`services/game_config.py:921-927`) flags a restart-required game setting on an object nothing reads or clears. `PendingRestartState` is `services/pending_restart.py:12-67`. Task 2 makes them one ("ADR against the code" 8).
- **`MaxClients`** is a known setting (`services/game_config.py:123-128`) of `serverdata/serverconfig.json` (`config_path`, `:550-553`). `_load_config` (`:580-593`) raises `FileNotFoundError` when the file is missing; the file is created at the game's first start (`ConfigInitService`, `services/server.py` `_start_server_locked`), so it is missing on a fresh install and normally present after. `get_settings` (`:604-662`) builds every setting with env lookups and logs `settings_retrieved` at DEBUG; it is too much for one key at every scrape.
- **No Prometheus code exists:** no `prometheus` import in `api/src`, no dependency in `api/pyproject.toml` (`:6-13`).

### The metric contract (ADR-4)

| Name | Type | Labels | Value | Present |
|---|---|---|---|---|
| `vintagestory_server_info` | gauge | `version` | 1 | when `status.version` is not `None` (a game is installed and its version file exists) |
| `vintagestory_server_up` | gauge | | 1 when `status.state == RUNNING`, else 0 | always |
| `vintagestory_server_state` | gauge | `state` | one sample per `ServerState` member in enum order (7: `not_installed`, `installing`, `installed`, `starting`, `running`, `stopping`, `error`), 1 for `status.state`, 0 otherwise | always |
| `vintagestory_server_uptime_seconds` | gauge | | `status.uptime_seconds` | when it is not `None` (RUNNING only) |
| `vintagestory_players_online` | gauge | | `server.players_online`, 0 when it is `None` | always |
| `vintagestory_players_max` | gauge | | `GameConfigService.get_max_clients()` | when it returns an int |
| `vintagestory_server_pending_restart` | gauge | | 1 when `get_restart_state().pending_restart`, else 0 (after Task 2 the one state for mods and restart-required game settings, as `/healthz`) | always |
| `vintagestory_server_process_cpu_seconds_total` | counter | | `cpu_times().user + cpu_times().system` of the game process | while `game_server_pid` is not `None` |
| `vintagestory_server_process_resident_memory_bytes` | gauge | | `memory_info().rss` of the game process | while `game_server_pid` is not `None` |

"Always" means: unless its own source failed (AC 6). HELP texts, verbatim:

| Name | `# HELP` |
|---|---|
| `vintagestory_server_info` | `The installed VintageStory server version; always 1.` |
| `vintagestory_server_up` | `1 while the VintageStory server is running, else 0.` |
| `vintagestory_server_state` | `1 for the VintageStory server's current state, 0 for the others.` |
| `vintagestory_server_uptime_seconds` | `Seconds since the VintageStory server was started.` |
| `vintagestory_players_online` | `Players on the VintageStory server, counted from its join and leave lines; 0 when it is not running.` |
| `vintagestory_players_max` | `MaxClients from the VintageStory server's serverconfig.json.` |
| `vintagestory_server_pending_restart` | `1 when a change waits for a VintageStory server restart, else 0.` |
| `vintagestory_server_process_cpu_seconds_total` | `User and system CPU time of the VintageStory server process, in seconds.` |
| `vintagestory_server_process_resident_memory_bytes` | `Resident memory of the VintageStory server process, in bytes.` |

- **Definitions:** `up` follows the state (like `/readyz`'s `game_server`, `routers/health.py:169`), so `STARTING` and `STOPPING` are 0; the process series follow the PID (like the JSON metrics), so they are present during `STARTING` and `STOPPING`; uptime follows `uptime_seconds` (RUNNING only). The state set comes from `ServerState` itself (`models/server.py:19-28`), so a new state adds a sample without a change here (ADR-4 decision 3); `installing` and `error` are always 0 because `get_server_status` never reports them.
- The CPU counter resets to 0 when the game restarts (a new process); Prometheus' `rate()` and `increase()` handle counter resets. Do not add `_created` samples (the 0.0.4 text format has none for a `CounterMetricFamily` built with `value=`).
- **Manager metrics** come from the default collectors on the project registry: `python_info` (`PlatformCollector`), `python_gc_objects_collected_total`, `python_gc_objects_uncollectable_total`, `python_gc_collections_total` (`GCCollector`), and `process_cpu_seconds_total`, `process_virtual_memory_bytes`, `process_resident_memory_bytes`, `process_start_time_seconds`, `process_open_fds`, `process_max_fds` (`ProcessCollector`, which reads `/proc` and yields nothing on macOS: the dev machine's unit tests cannot see them; CI's Linux runner and the E2E container can).

### The collector (Task 3)

New module `api/src/vintagestory_api/services/prometheus_metrics.py`. Shape (names are binding, bodies are the developer's):

```python
"""The game server's metrics for Prometheus, read at scrape time (Epic 22 ADR-3, ADR-4)."""

from collections.abc import Callable, Iterable

import psutil
import structlog
from prometheus_client import CollectorRegistry, GCCollector, PlatformCollector, ProcessCollector
from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily
from prometheus_client.metrics_core import Metric

from vintagestory_api.models.server import ServerState
from vintagestory_api.services.game_config import GameConfigService
from vintagestory_api.services.mods import get_restart_state
from vintagestory_api.services.pending_restart import PendingRestartState
from vintagestory_api.services.server import ServerService, get_server_service

logger = structlog.get_logger()


class GameServerCollector:
    """Builds the vintagestory_* series from live state at every collect()."""

    def __init__(
        self,
        server: Callable[[], ServerService] = get_server_service,
        restart_state: Callable[[], PendingRestartState] = get_restart_state,
    ) -> None: ...

    def collect(self) -> Iterable[Metric]: ...


def build_registry(collector: GameServerCollector) -> CollectorRegistry: ...


def get_metrics_registry() -> CollectorRegistry:
    """The process-wide registry, built on first use (the route's dependency)."""
    ...
```

- **Sources and isolation.** `collect()` runs five sources, each through one helper that calls a builder returning a `list[Metric]` (built eagerly, so a raise happens inside the helper), catches `Exception`, logs `prometheus_source_failed` and returns `[]`:

  | `source` | Series | Reads |
  |---|---|---|
  | `server_status` | info, up, state, uptime | `server().get_server_status()` once |
  | `players` | players_online | `server().players_online` |
  | `pending_restart` | pending_restart | `restart_state().pending_restart` |
  | `max_clients` | players_max | `GameConfigService(settings=server().settings).get_max_clients()` |
  | `game_process` | both `server_process_*` | `server().game_server_pid`, then `psutil.Process(pid)` `.cpu_times()` and `.memory_info()` |

  The `except Exception` logs, so it is the "no silent failures" pattern of `project-context.md`, not a suppression. `psutil.NoSuchProcess` inside `game_process` is not a failure (the process exited between the PID read and psutil, as `metrics.py:247-250`): catch it inside the builder, log `prometheus_game_process_gone` at DEBUG and return `[]`. `AccessDenied` and anything else go to the helper (WARNING).
- **Why the route cannot rely on prometheus-client for isolation:** `generate_latest` lets a collector's exception propagate (checked against 0.26.0 in planning and validation: the exception a custom `collect()` raises comes out of `generate_latest` unchanged, a `RuntimeError` as a `RuntimeError`), which would be a 500. The isolation is inside `GameServerCollector`; the three default collectors handle their own I/O errors.
- **Families:** `GaugeMetricFamily(name, help, value=...)` for unlabelled gauges; `GaugeMetricFamily(name, help, labels=["version"])` + `add_metric([version], 1)` for info; `GaugeMetricFamily(name, help, labels=["state"])` + one `add_metric([member.value], 1 or 0)` per member for state; `CounterMetricFamily("vintagestory_server_process_cpu_seconds_total", help, value=...)` (the library strips `_total` from the family name and writes it back on the sample: the parser reports the family as `vintagestory_server_process_cpu_seconds` with sample `..._total`; the 0.0.4 text, as 0.26.0 writes it, still carries `_total` on the comment lines: `# HELP vintagestory_server_process_cpu_seconds_total User and ...` and `# TYPE vintagestory_server_process_cpu_seconds_total counter`, which is what the raw-text assertion of AC 2 must expect). Not `InfoMetricFamily` or `StateSetMetricFamily`: see "ADR against the code" 3.
- **No `describe()`** and `CollectorRegistry()` with its default `auto_describe=False`: registering then never calls `collect()`, so building the registry reads nothing. Do not pass `auto_describe=True`.
- `build_registry(collector)`: `registry = CollectorRegistry()`, `registry.register(collector)`, then `ProcessCollector(registry=registry)`, `PlatformCollector(registry=registry)`, `GCCollector(registry=registry)`. Never the global `REGISTRY` (ADR-3 decision 3), so tests that build their own registry share nothing.
- `get_metrics_registry()`: a module-level `_registry: CollectorRegistry | None = None`, built with `build_registry(GameServerCollector())` on first call, as `get_server_service` does (`services/server.py:52-60`). Not built at import.
- The collector runs on the event loop (the route is `async def`), like `/healthz`: no thread touches `ServerService` or the tracker from outside the loop. Its I/O is two small file reads and two psutil calls.
- `GameServerCollector` satisfies prometheus-client's `Collector` protocol (`prometheus_client.registry.Collector` is a `Protocol` with `collect(self) -> Iterable[Metric]`); no base class is needed. Planning ran pyright strict on this shape against 0.26.0: 0 errors, 0 warnings.

### MaxClients (Task 3.2)

```python
    def get_max_clients(self) -> int | None:
        """MaxClients from serverconfig.json (Epic 22 ADR-4).

        None when the file does not exist yet or the value is not a whole number.
        Raises when the file exists but cannot be read or is not valid JSON.
        """
```

- Missing file: return `None` (check `self.config_path.exists()` first; a fresh install has none until the first start). Present: `self._load_config().get("MaxClients")`; `None` unless `isinstance(value, int) and not isinstance(value, bool)`. `OSError` and `json.JSONDecodeError` propagate, and the collector logs them (AC 6).
- It reads the file the game writes, so a live `/serverconfig maxclients` change shows once the game has saved the file; that is the same source the Game Settings page shows.
- No env lookup and no log line here: it runs at every scrape.

### The route (Task 4)

New module `api/src/vintagestory_api/routers/prometheus.py`:

```python
"""Prometheus metrics at the root, open like /healthz (Epic 22 ADR-3)."""

from fastapi import APIRouter, Depends, Response
from prometheus_client import CONTENT_TYPE_PLAIN_0_0_4, CollectorRegistry, generate_latest

from vintagestory_api.services.prometheus_metrics import get_metrics_registry

router = APIRouter(tags=["Metrics"])


@router.get("/metrics", response_class=Response)
async def prometheus_metrics(
    registry: CollectorRegistry = Depends(get_metrics_registry),
) -> Response:
    """The game server's and the manager's metrics in the Prometheus text format.

    No authentication (Epic 22 ADR-3 decision 6). Values are read at each scrape.
    """
    return Response(content=generate_latest(registry), media_type=CONTENT_TYPE_PLAIN_0_0_4)
```

- `generate_latest(registry)` with its default escaping (underscores); every name and label here is a legacy-valid Prometheus name, so the body is the classic text format any Prometheus 2.x or 3.x parses.
- Starlette adds a charset only when the media type has none, so the header is exactly `text/plain; version=0.0.4; charset=utf-8`.
- GET only: `HEAD` and `POST` are not added (ADR-3 decision 2); the SPA fallback is GET only, so they answer 405. No `Cache-Control`, no rate limit, no `Accept` negotiation (no OpenMetrics): Prometheus accepts this format.
- `Depends(get_metrics_registry)` is the test seam: tests set `app.dependency_overrides[get_metrics_registry]` to a registry built over a fake server, so no route test reads `dev/` through the singleton.
- The route is in the schema like `/healthz` (the schema is served only in debug mode, `main.py:349-354`).

### What is logged

| Event | Level | Fields | When |
|---|---|---|---|
| `prometheus_source_failed` | WARNING | `source` (table above), `error_type` (`type(e).__name__`), `error` (`str(e)`) | once per failing source per scrape |
| `prometheus_game_process_gone` | DEBUG | `pid` | psutil `NoSuchProcess` |

Nothing else: no line for a successful scrape at any level, no line for a missing `serverconfig.json` or a non-integer `MaxClients` (absent is the answer). A persistent failure (for example an unreadable `serverconfig.json`) logs one WARNING at every scrape; that is what ADR-3 decision 5 asks for, and it stops when the cause is fixed. No log line carries a player name or address (the collector only reads a count).

### API tests

| Task | File | Test |
|---|---|---|
| 1 | `api/tests/test_prometheus_metrics.py` (new) | `CONTENT_TYPE_PLAIN_0_0_4 == "text/plain; version=0.0.4; charset=utf-8"` |
| 2 | `api/tests/test_shared_pending_restart.py` (new) | **Fixtures:** an autouse fixture resets the shared singleton with `monkeypatch.setattr(vintagestory_api.services.mods, "_restart_state", None)` (restored after, so no flag leaks into another test) and patches `vintagestory_api.routers.health.get_disk_space_data` to return `None`; `settings` under `tmp_path` with an admin key; an installed, stopped temp-dir `ServerService(settings)` (`install` as `tests/server/conftest.py:98-117`) with a `serverconfig.json` holding `Port` 42420 |
| 2 | same | **Identity:** `routers.config.get_pending_restart_state() is services.mods.get_restart_state()` |
| 2 | same | **Through the routes (AC 13):** client as `tests/test_security_headers_scope.py:16-26` (no `with` block), `dependency_overrides[get_settings]`, `dependency_overrides[get_server_service]` (the temp service; `get_game_config_service` and `POST /server/restart` take it from there), `dependency_overrides[get_mod_service]` = `ModService(state_dir=..., mods_dir=..., cache_dir=..., restart_state=get_restart_state())` under `tmp_path` (as `services/mods.py:106-110`), and `monkeypatch.setattr("vintagestory_api.routers.health.get_server_service", lambda: service)` (`/healthz` calls it directly, `routers/health.py:98`). Before: `/healthz` `game_server_pending_restart` false. `POST /api/v1alpha1/config/game/settings/Port` `{"value": 42421}` with the admin key → 200; then `/healthz` true and `GET /api/v1alpha1/mods` `pending_restart` true. `POST /api/v1alpha1/server/restart` with `_start_server_locked` replaced by `monkeypatch.setattr(service, "_start_server_locked", AsyncMock(...))` (no `dotnet`; the game is stopped, so nothing is stopped) → 200; then both false again |
| 2 | `api/tests/test_routers_config.py` | `test_get_pending_restart_state_singleton_initialization` (`:2129-2146`) rewritten: with `services.mods._restart_state` reset through `monkeypatch`, `get_pending_restart_state()` returns `get_restart_state()`, the same object twice |
| 3 | `api/tests/test_prometheus_metrics.py` | **Fixtures:** `settings` = `Settings(data_dir=tmp_path / "data", api_key_admin=...)` (never `dev/`); helpers `install(settings, version="1.22.7")` (the two DLLs under `server_dir`, `vsmanager/current_version`, as `tests/server/conftest.py:98-117`), `write_serverconfig(settings, **values)` (JSON into `serverdata/serverconfig.json`), `run(service, monkeypatch, state=ServerState.RUNNING, started=time.time() - 120)` setting `_process` to a small `FakeProcess` (`pid = os.getpid()`, `returncode: int | None = None`) with `monkeypatch.setattr`, `_server_state` and `_server_start_time`; players through `monkeypatch.setattr(service._player_tracker, "_online", {"ExamplePlayer", "AnotherPlayer"})`. An autouse fixture monkeypatches `vintagestory_api.routers.health.get_disk_space_data` to return `None` (`get_server_status` imports it at call time; this keeps `shutil.disk_usage` off `dev/`). `scrape(registry) -> dict[str, list[Sample]]` parses `generate_latest(registry).decode()` with `prometheus_client.parser.text_string_to_metric_families`, keyed by sample name |
| 3 | same | **Running (AC 2):** every series and value of the contract table for version 1.22.7, two players, `MaxClients` 16, no pending restart; seven `vintagestory_server_state` samples, `running` 1, the six others 0; uptime ≥ 120; CPU ≥ 0 and type counter; RSS > 0; the raw text has the exact `# HELP` and `# TYPE` line of each of the nine families |
| 3 | same | **Installed, stopped (AC 3):** up 0, `state="installed"` 1, players 0, info present, uptime and both process series absent. **Not installed (AC 4):** info absent, `state="not_installed"` 1, up, players, pending 0; players_max absent without `serverconfig.json` and present with one. **Stopping with a live process:** up 0, `state="stopping"` 1, process series present, uptime absent. **Pending:** after `restart_state.require_restart("test")` the series is 1. **Pending from a game setting (AC 13):** with `services.mods._restart_state` reset through `monkeypatch` and the collector's default `restart_state`, `await GameConfigService(settings=..., server_service=service, pending_restart_state=routers.config.get_pending_restart_state()).update_setting("Port", 42421)` makes the series 1, and `await service.restart_server()` with `_start_server_locked` mocked (`AsyncMock`) makes it 0 |
| 3 | same | **players_max:** absent for a missing key, `"16"`, `16.5`, `true`, `null`; no WARNING for any of them nor for a missing file (`structlog.testing.capture_logs()`) |
| 3 | same | **Failure isolation (AC 6), parametrised per source:** `get_server_status` raising `RuntimeError` (via `monkeypatch.setattr(service, "get_server_status", ...)`); the `players_online` read raising (`monkeypatch.setattr(PlayerTracker, "count", property(raising))` with a `def raising(self: PlayerTracker) -> int` that raises; not a stand-in object, which would not type-check as the `Callable[[], ServerService]` provider); a `restart_state` provider that raises; `serverconfig.json` with invalid JSON; `psutil.Process` monkeypatched in `vintagestory_api.services.prometheus_metrics` to raise `psutil.AccessDenied`. Each: `generate_latest` does not raise, the source's series are absent, every other source's series are present, exactly one `prometheus_source_failed` with that `source` and `error_type`. **NoSuchProcess:** process series absent, no WARNING, one `prometheus_game_process_gone` at DEBUG |
| 3 | same | **Live (AC 5):** scrape, change the player set and burn a little CPU (a short arithmetic loop), scrape again: players changed, CPU counter ≥ the first value, with no `MetricsService.collect()` call in between (the collector module does not import `services.metrics`; the ring buffer is never read) |
| 3 | same | **Labels and names (AC 8):** across all `vintagestory_*` samples the label names are a subset of `{"version", "state"}`; the body contains neither `ExamplePlayer` nor `AnotherPlayer` nor `str(tmp_path)`; a successful scrape logs nothing at INFO or above |
| 3 | same | **Registry:** `build_registry` output has `python_info` and `python_gc_objects_collected_total`; `process_resident_memory_bytes` is present when `sys.platform == "linux"` and absent otherwise (one assertion on the platform, not a skip). Two registries built in one test do not share series (building the second does not raise `Duplicated timeseries`). `get_metrics_registry()` returns the same object twice (reset the module's `_registry` with `monkeypatch.setattr` first and do not scrape it: scraping the singleton would read `Settings()` from the environment) |
| 3 | `api/tests/test_game_config.py` | `get_max_clients`: missing file → `None`; `{"MaxClients": 16}` → 16; missing key, string, float, bool, null → `None`; invalid JSON raises `json.JSONDecodeError`. Use the file's existing `temp_settings` / `config_file` fixtures (`:45`, `:75`) |
| 4 | `api/tests/test_prometheus_router.py` (new) | **Client:** as `tests/test_security_headers_scope.py:16-26`: `create_app(settings, static_dir=tmp)` with an `index.html`, `dependency_overrides[get_settings]` and `dependency_overrides[get_metrics_registry]` (a `build_registry(GameServerCollector(server=lambda: service, restart_state=lambda: state))` over a temp-dir `ServerService`), and **no `with` block**, so the lifespan does not run and nothing is written under `dev/`. Patch `vintagestory_api.routers.health.get_disk_space_data` to return `None` here too: `get_server_status` calls it, and it reads `Settings()` from the environment, not the override |
| 4 | same | No key → 200; wrong `X-API-Key` → 200 (the key is not read); `content-type` header exactly `text/plain; version=0.0.4; charset=utf-8` (AC 1); the body parses and has `vintagestory_server_up` and `python_info`; the body is not the `index.html` text (AC 7); no `content-security-policy`, `content-security-policy-report-only` or `x-frame-options` header; `/` still answers the SPA page with its CSP (AC 7); `POST /metrics` → 405; a scrape logs nothing at INFO or above (`capture_logs`, AC 8) |

All names are placeholders. Tests reach private attributes through `monkeypatch.setattr` only; the `tests` execution environment already sets `reportPrivateUsage = false` (`api/pyproject.toml:61-64`). Add no file-level pyright relaxation.

### E2E test (Task 4.5)

`api/tests/e2e/test_e2e_metrics.py`, in the style of `test_e2e_health.py:16-24` (Playwright `page.request.get(f"{base_url}/metrics")`, no headers):

- `response.ok`; `response.headers["content-type"]` starts with `text/plain; version=0.0.4`.
- Parse `response.text()` with `text_string_to_metric_families`: `vintagestory_server_up` present with 0 or 1; exactly one `vintagestory_server_state` sample is 1; `python_info` and `process_resident_memory_bytes` present (the container is Linux).
- State-independent on purpose: `just test-e2e-ci` runs it on a container with no game installed (`scripts/e2e-ci.sh`; `serverconfig.json` seeded from `web/e2e/fixtures/serverconfig.json`, `MaxClients` 16 at `:13`), while the file's `base_url` default is the dev stack (`tests/e2e/conftest.py:64-71`). Do not assert `not_installed` or `players_max`.
- The session fixture already skips when the address does not answer (`tests/e2e/conftest.py:48-61`); `scripts/e2e-ci.sh:150-158` fails the run if the container died first. Add no skip of your own.

### Documentation (Task 5)

`### Metrics` in `README.md`, after Configuration, in the README's plain style:

- One paragraph: `GET /metrics` serves the game server's metrics and the manager's own in the Prometheus text format; values are read at each scrape, so it works with metrics collection turned off in API Settings.
- A table of the nine `vintagestory_*` series: name, meaning, when absent (from "The metric contract"; `vintagestory_server_pending_restart` is 1 after a mod change or a game setting that needs a restart, until the next restart), and one line naming the manager's `process_*`, `python_info` and `python_gc_*` series.
- **Open, like `/healthz`:** no API key; it shows the game version, the state, player counts and resource use, never names. To keep it off the internet, do not publish `/metrics` through the reverse proxy (or block the path there) and let Prometheus reach port 8080 on the internal network.
- The example:

  ```yaml
  scrape_configs:
    - job_name: vintagestory
      metrics_path: /metrics
      static_configs:
        - targets: ["vintagestory-manager.example.internal:8080"]
  ```

- Do not document an alert rule or a Grafana dashboard; one sentence may say `vintagestory_server_up == 0` is the series to alert on.

### Existing tests that change

One: `test_get_pending_restart_state_singleton_initialization` (`api/tests/test_routers_config.py:2129-2146`) resets `config_module._pending_restart_state`, which Task 2 removes (Pyright would report the attribute); Task 2.1 rewrites it for the shared state. The other users of the two getters keep working unchanged: `test_routers_config.py:161` and `test_game_config.py:114` inject their own state, `test_health.py:159-176` patches `routers.health.get_restart_state`, and `tests/server/test_lifecycle.py:1017-1026`, `:1205` and `tests/server/test_internal_methods.py:328-337` patch `_get_mod_service_module`. `test_security_headers_scope.py` and `test_frontend_routes.py` are run in Task 4.4 as regression checks only; the `/metrics` header checks live in the new router test file (its client needs the registry override). Anything existing that fails is a regression (AC 11): fix the code, not the test.

### Not changed (do not "fix" these here)

- `/healthz`, `/readyz`, the JSON metrics (`/api/v1alpha1/metrics/*`, `MetricsService`, the ring buffer, the `metrics_collection` job and its interval), the dashboard and the web (no web file changes; the "Restart required" banner becomes correct without one, "ADR against the code" 8).
- Beyond Task 2's one shared state: when a restart is flagged (`GameConfigService` flags `Port`/`Ip` whether or not the game runs; mods only while it runs, `services/mods.py:870-873`), and what clears it (only `restart_server`, `services/server.py:1209`; a plain start does not). See "ADR against the code" 8 for the consequence.
- The uvicorn access log (one line per request, as for `/healthz`); the CORS settings; the CSP and the SPA fallback.
- No authentication, rate limit, HEAD, OpenMetrics or `Cache-Control` on `/metrics` (ADR-3).
- `architecture/epic-22-server-operations-and-metrics.md`: its ADR-3 decision 2 still says `CONTENT_TYPE_LATEST`; this story records the deviation here ("ADR against the code" 1) and leaves the ADR text alone.
- The existing `# type: ignore` comments in `services/scheduler.py`, `models/jobs.py` and older tests: they predate the rule; add none.
- The dev stack: no task starts, stops, rebuilds or restarts it or its game server. Any check at `http://localhost:9080` is read-only and the maintainer's.

### API contract changes

- New: `GET /metrics` at the root, no API key, `text/plain; version=0.0.4; charset=utf-8`, the series of "The metric contract" plus the manager's `process_*`, `python_info`, `python_gc_*`. Additive; no route, field or status code changes.
- New log events: `prometheus_source_failed` (WARNING), `prometheus_game_process_gone` (DEBUG).
- New runtime dependency: `prometheus-client>=0.26.0,<1`.
- Fixed (Task 2): a restart-required game setting change now shows in `/healthz` `game_server_pending_restart`, the mods list's `pending_restart` (the web's banner) and `vintagestory_server_pending_restart`, and a restart clears it. No field or route changes.
- Release notes (scope stripped by git-cliff): Task 2's fix "show Restart required when a game setting change needs a restart" and Task 4's feature "serve game server metrics for Prometheus at /metrics".

### ADR against the code

1. **Content type.** ADR-3 decision 2 says `CONTENT_TYPE_LATEST`, and the epic's AC 1 gives its value as `text/plain; version=0.0.4; charset=utf-8`. In prometheus-client 0.26.0 (checked in planning, installed in a scratch environment) `CONTENT_TYPE_LATEST` is `CONTENT_TYPE_PLAIN_1_0_0` = `text/plain; version=1.0.0; charset=utf-8`; the library's own exposition handlers answer a request without content negotiation with `generate_latest` and `CONTENT_TYPE_PLAIN_0_0_4` (`exposition.py`, `choose_encoder`'s fallback). The story uses `CONTENT_TYPE_PLAIN_0_0_4`: it is the AC's literal value, it matches the body `generate_latest` writes, and every Prometheus version parses it. Task 1's test pins the constant.
2. **Version floor.** ADR-3 decision 1 allows `>=0.21,<1` "or the current release's minor as the floor"; the current release is 0.26.0 (2026-07-24, PyPI), and the content-type constants of point 1 exist in it, so the floor is `>=0.26.0,<1`.
3. **No `InfoMetricFamily` or `StateSetMetricFamily`.** Planning ran both against 0.26.0: `StateSetMetricFamily("vintagestory_server_state", ...)` writes the label as `vintagestory_server_state="running"`, not ADR-4's `state="running"`. `InfoMetricFamily` would write the right line, but a plain labelled gauge does the same with one family type for every gauge here. Both are `GaugeMetricFamily` with `labels=["version"]` and `labels=["state"]`; the exposed text matches ADR-4 exactly (`# TYPE ... gauge`).
4. **"Running" has three meanings, each from an existing rule.** ADR-4 says `up` is 1 "while the game is running" and the process and uptime series are absent "when the game is not running". The story takes `up` from the state (as `/readyz`), the process series from the PID (as the JSON metrics, Story 12.2, and `players_online`), and uptime from `uptime_seconds` (RUNNING only, as `/healthz`). During STARTING and STOPPING, `up` is 0 while the process series are present; the contract table says so.
5. **`players_max` without a file is absent, not a failure.** ADR-4 decision 2 says absent "when the setting cannot be read"; ADR-3 decision 5 says a source that raises is logged at WARNING. A missing `serverconfig.json` is normal before the first start, so `get_max_clients` returns `None` for it without logging; an unreadable or invalid file raises and is logged (AC 4, AC 6).
6. **"One WARNING" is per failing source per scrape.** The epic's AC names one source; with two failing sources a scrape logs two lines. AC 6 says so.
7. **`up`, `state`, `players_online` and `pending_restart` are "always present" unless their own source fails** (AC 6 takes precedence over ADR-4 decision 2's "always"; a series cannot be reported from a source that raised).
8. **One pending-restart state (pulled in by the controller during validation, backlog drawdown; FR306).** Not in ADR-3 or ADR-4; it is in this story because `vintagestory_server_pending_restart` would otherwise inherit the bug. Before Task 2 there are two `PendingRestartState` singletons ("The code today"): game settings flag `routers/config.py`'s, which nothing reads or clears, so a `Port` or `Ip` change (or a `ServerDescription` cleared while running) never shows in `/healthz`, the web's banner or the new series, and a restart never clears it. The smallest correct change: `routers/config.py`'s `get_pending_restart_state()` returns `services/mods.py`'s `get_restart_state()`, and its own singleton goes. The name stays because it is the FastAPI dependency (`:110`) the config router tests override; the reverse (mods delegating to config) would make a service import a router. **The web:** the "Restart required" banner (`web/src/components/PendingRestartBanner.tsx`, in the header on every page, `components/layout/Header.tsx:41`) reads `pendingRestart` from `GET /api/v1alpha1/mods` (`useModsPendingRestart`, `web/src/hooks/use-mods.ts:256-259`; `useMods` polls every 10 s, `:36`, `:60-66`), which `routers/mods.py:85` takes from the `services/mods.py` singleton. Saving a game setting already invalidates that query (`web/src/hooks/use-game-config.ts:126`), and `useConfigPendingRestart` (`:133-146`, used only by its own tests) already assumes the two are shared. So after Task 2 the banner appears right after a restart-required save, and after a restart it goes at the next mods poll, within 10 s (`useRestartServer` invalidates only the server status, `web/src/hooks/use-server-status.ts:159-170`), as it does for mods today. No web change; the banner's doc comment still says "mod changes", left as is. **Known consequence, not changed here:** `GameConfigService` flags `Port`/`Ip` even while the game is stopped (mods flag only while it runs), and only `restart_server` clears the flag; so after Task 2 a `Port` change on a stopped server shows "Restart required", "Restart Now" (which starts a stopped game) clears it, but a plain Start leaves it set until the next restart. Before Task 2 the same flag was set and never visible.
- The facts of ADR-3 and ADR-4 otherwise match 7672fc90: `/healthz` at the root (`main.py:386`), routers before `register_frontend` (`:415-416`), no web `/metrics` route, `MaxClients` known (`game_config.py:123`).

### Testing Requirements

**CRITICAL:** tests are written with each task and committed with it, red first. `just test-api <files>` after each task; `just check` before review.

- No lint or type suppression of any kind (`# type: ignore`, `# pyright: ignore`, `noqa`), no `cast` or `typing.cast`, no skipped test (`pytest.mark.skip`, `skipif`, `xfail`), no `.only`. Pyright stays at 0 errors and 0 warnings in `src` and `tests`; `just check` is green.
- Log assertions with `structlog.testing.capture_logs()`.
- Private state only through `monkeypatch.setattr`, so it is restored. Any test that flags the real shared state (`get_restart_state()`) first resets `services.mods._restart_state` to `None` with `monkeypatch.setattr`, so a pending flag never leaks into another test.
- Every `Settings` in a test has `data_dir` under `tmp_path`; nothing scrapes the `get_metrics_registry()` singleton (it would read `Settings()` from the environment, which `just test-api` points at `dev/`); route tests override it.
- No fake process runs `dotnet`; the fake game process is the test process's own PID, read with real psutil.
- Never start, stop, rebuild or restart the dev stack or its game server (ADR-14). The only container any task runs is the throwaway one of `just test-e2e-ci`.

### Security Requirements

- Labels: `version` (from `vsmanager/current_version`, written by the installer from a validated version) and `state` (enum values) only. No player name, address, path, key or setting other than `MaxClients` in any series.
- No authentication by decision (answer 2, ADR-3 decision 6); the README says it is open and how to keep it off the internet. `/healthz` already exposes the version and state the same way.
- The WARNING carries the exception's type and message; neither the collector nor its sources ever hold a player name (the tracker gives a count only, Story 22.1).
- `GameConfigService.get_max_clients()` returns one integer; secret settings in the same file are never read into the collector.

### Development Commands

- `just test-api tests/test_shared_pending_restart.py tests/test_routers_config.py tests/test_prometheus_metrics.py tests/test_game_config.py tests/test_prometheus_router.py`, `just typecheck-api`, `just lint-api`.
- `cd api && uv add "prometheus-client>=0.26.0,<1"` (Task 1 only).
- `cd api && uv run ruff format <changed files>` (`just format-api` takes no file arguments and formats the whole tree; Story 22.1 drawdown note).
- `just test-e2e-ci` (throwaway container; Task 4.5; never `just test-e2e-api`/`just test-e2e`, which target the dev stack at `http://localhost:9080`, nor `just test-e2e-web`, which restarts it). It also runs the web E2E suite; a web failure unrelated to this story is reported, not fixed here.
- `just check` (Task 6). `just changelog` (Task 6.2).

### Previous Story Intelligence

- **22.1** (in review, this branch's base): `ServerService.players_online` is `None` when no process lives and the tracker's count otherwise; use it, do not reach into `_player_tracker` from `src`. Its drawdown notes: a bare `MagicMock` server service leaked a `MagicMock` into a snapshot; this story's tests use a real `ServerService` on a temp dir instead. The orchestrator's convention for user-visible commits is `feat(story-22.x/task-N)` (the scope is stripped from release notes). `just format-api` and `just format-web` take no file arguments.
- **12.2:** `MetricsService` and the psutil handling of `NoSuchProcess` / `AccessDenied`; the Epic 12 architecture deferred Prometheus.
- **19.3:** the CSP is on web UI pages only; `test_security_headers_scope.py`'s "no `with` block" client is the model for route tests that must not run the lifespan.
- **21.3:** the depth and the "ADR against the code" record; completion notes must be true of the code.

### Git Intelligence

- Branch `story/22-2-prometheus-metrics-endpoint` from `story/22-1-players-online-are-counted` at `7672fc90` (`chore(story-22.1/task-6): validate and move story 22.1 to review`). 22.1's commits: `8a52c44b` (tracker wired into `ServerService`), `68b66035` (`players_online` in the JSON metrics), `964576da` (Players card), `13438fdc` (E2E widths).
- Planned commits: Task 1 `build(story-22.2/task-1): add the prometheus-client dependency`; Task 2 `fix(story-22.2/task-2): show Restart required when a game setting change needs a restart`; Task 3 `refactor(story-22.2/task-3): collect the game server's Prometheus metrics at scrape time`; Task 4 `feat(story-22.2/task-4): serve game server metrics for Prometheus at /metrics` (with the E2E test); Task 5 `docs(story-22.2/task-5): document /metrics with a Prometheus scrape example`; Task 6 `chore(story-22.2/task-6): validate and move story 22.2 to review`. Previous dependency additions: `4f1c31e3` (apscheduler), `a3b2a840` (psutil).

### Project Structure Notes

- New: `api/src/vintagestory_api/services/prometheus_metrics.py`, `api/src/vintagestory_api/routers/prometheus.py`, `api/tests/test_shared_pending_restart.py`, `api/tests/test_prometheus_metrics.py`, `api/tests/test_prometheus_router.py`, `api/tests/e2e/test_e2e_metrics.py`. Not `routers/metrics.py` or `services/metrics.py`: those are the JSON metrics and stay as they are.
- Modified: `api/pyproject.toml`, `api/uv.lock`, `api/src/vintagestory_api/main.py`, `api/src/vintagestory_api/routers/config.py`, `api/src/vintagestory_api/services/game_config.py`, `api/tests/test_routers_config.py`, `api/tests/test_game_config.py`, `README.md`, `_bmad-output/planning-artifacts/prd.md`, `_bmad-output/planning-artifacts/architecture/core-architectural-decisions.md`, this story file, and `sprint-status.yaml` (through `just sprint` only).
- No web, Dockerfile, compose, `.env.example` or Renovate change (Renovate's preset already follows `pyproject.toml`).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 22.2: A Prometheus `/metrics` Endpoint] and the Epic 22 header
- [Source: _bmad-output/planning-artifacts/prd.md] FR289-FR291 (`:898-900`), FR306 (Epic 22 "Pulled In"); post-MVP lines `:149`, `:285`
- [Source: _bmad-output/planning-artifacts/architecture/epic-22-server-operations-and-metrics.md] "Facts Checked in the Code" (Metrics today), ADR-3, ADR-4, ADR-14
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-18-epic-22.md] section 1 (scope decisions), section 2 (API contract table, draft release notes, the open-endpoint risk), section 5 (answers 1-3)
- [Source: _bmad-output/implementation-artifacts/22-1-players-online-are-counted.md] (previous story), [21-3-log-level-and-config-viewer.md] (depth)
- prometheus-client 0.26.0: custom collectors, `CounterMetricFamily` `_total` handling, `ProcessCollector` (Linux `/proc` only), `PlatformCollector`, `GCCollector` with `registry=` (Context7 `/prometheus/client_python`; behaviour of the content types, `StateSetMetricFamily` and a raising collector checked by running 0.26.0 in planning; the content types, `choose_encoder`'s fallback, the counter's `# HELP`/`# TYPE` lines, a raising collector, two registries side by side, `ProcessCollector` yielding nothing on macOS, FastAPI answering `HEAD`/`POST /metrics` with 405, and pyright strict on the collector, registry and parser shapes re-checked on Python 3.14 in validation)
- `project-context.md`: tests with each task; no suppressions; "no silent failures"; commit types by user impact; `just` for every task
- `RELEASING.md` "Commit messages are release notes"
- Bead: `VSS-bhw` (API-023), parent `VSS-oole` (Epic 22)

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

- 2026-11-18: Story created (create-story, non-interactive) and checked against the create-story checklist: 6 tasks; every code task carries its tests (Task 5 is documentation only, Task 6 validation); every AC is mapped to a task (AC 11 to Task 6 and every task's test run, AC 12 to Task 6.3). Ultimate context engine analysis completed - comprehensive developer guide created.
- 2026-11-18: Validated against the create-story checklist, the epic, ADR-3, ADR-4, ADR-14, project-context.md, CLAUDE.md and the code at e2b55388; prometheus-client 0.26.0 re-checked on Python 3.14 in a scratch environment (pyright strict 0/0 on the collector shape). Pulled in by the controller during validation (backlog drawdown): one pending-restart state for game settings and mods (new Task 2, AC 13, FR306, "ADR against the code" 8); the route and the E2E test merged into Task 4 to stay at 6 tasks. Corrected: the exception `generate_latest` lets through, the counter's `# HELP`/`# TYPE` lines, the README Features line, `register_frontend`'s call lines, the disk-space patch in the router tests, a players-failure seam that type-checks.

### File List

## Change Log

- 2026-11-18: Story 22.2 created (ready-for-dev).
- 2026-11-18: Validated; the shared pending-restart fix pulled in by the controller (backlog drawdown), tasks restructured to 6.
