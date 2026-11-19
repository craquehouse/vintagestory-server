# Story 22.1: Players Online Are Counted

Status: ready-for-dev

<!-- Implements FR287-FR288, Epic 22 ADR-1, ADR-2 and ADR-14. Bead: VSS-bhw (API-023), first half; Story 22.2 closes it. Maintainer answers 1 and 4 (Matt, 2026-11-18). Stories run in order 22.1 to 22.6; this is the first, branched from planning/epic-22-server-operations-and-metrics (3b15aa21, main e16a7932 plus the planning commit). The PR targets main. Line references were verified at 3b15aa21 (api/ and web/ identical to e16a7932, the commit the ADRs cite) and must be re-checked at implementation time. API and web change; one new service module, one new web component, one E2E test. No new dependency. -->

## Story

As an **operator**,
I want **to see how many players are on the server**,
so that **I know whether anyone is playing before I restart or change something, and how busy the server is over time**.

## Acceptance Criteria

1. **Given** the game is running and prints a join line for `ExamplePlayer` (the `'{0} {1} joins.'` literal, with a documentation address such as `203.0.113.5:42420`, after the game's line prefix)
   **When** the line is read from the game's output
   **Then** the count of players online is 1, and a second join line for another name (`AnotherPlayer`, `198.51.100.7:42420`) makes it 2
   *(Covers FR287; ADR-1 decision 2; see "ADR against the code" 1)*

2. **Given** `ExamplePlayer` is online
   **When** the game prints `Player ExamplePlayer left.`
   **Then** the count goes down by one; a leave line for a name not online, and a join line for a name already online (including `ExamplePlayer joined again, killing previous client.`), change nothing
   *(Covers FR287; ADR-1 decisions 2 and 5)*

3. **Given** players are counted
   **When** the game is started, stopped (including a stop that fails after the process has exited) or exits by itself
   **Then** the count is 0
   *(Covers FR287; ADR-1 decision 3; see "ADR against the code" 3)*

4. **Given** a chat line whose text ends in "joins." (or in "left.")
   **When** it is read
   **Then** it is not counted
   *(Covers FR287; ADR-1 decision 6; see "ADR against the code" 1)*

5. **Given** players join and leave
   **When** I read the API's log (at any level, DEBUG included) and the API responses
   **Then** no player name and no player address appears in either (the console and log-file routes, which carry the game's own lines to the roles that read them today, are unchanged and out of scope: Dev Notes "Not changed")
   *(Covers FR287; ADR-1 decision 4; see "ADR against the code" 4)*

6. **Given** the game is running with two players online
   **When** an Admin key reads `GET /api/v1alpha1/metrics/current` and `/history` after a collection
   **Then** the snapshots have `playersOnline: 2`; with the game stopped they have `playersOnline: null`; every other field is as before
   *(Covers FR288; ADR-2 decisions 1 and 2; see "ADR against the code" 2)*

7. **Given** a line the tracker cannot handle (it raises)
   **When** `_read_stream` reads it
   **Then** the line is still in the console buffer, the following lines are still captured, and the fault is logged at WARNING without the line's text
   *(Covers FR287; ADR-1 decision 1)*

8. **Given** the dashboard
   **When** the game is running, and when it is stopped
   **Then** a Players card, placed directly after the Uptime card, shows the count, or "Stopped" with the subtitle "Server stopped", at every width the dashboard supports (320px to 2560px, both sidebar states, no sideways scroll)
   *(Covers FR288; ADR-2 decision 3; see "ADR against the code" 5 and 6)*

9. **Given** every existing test
   **When** the suites run
   **Then** they pass, apart from the changes listed in Dev Notes "Existing tests that change"; no test starts or stops the dev stack's game server; no test writes into `dev/`

10. **Given** one anonymised join line and one leave line from a real server, provided by the maintainer
    **When** they are added as test cases
    **Then** they are counted, and the prefix pattern matches them (manual check, reserved for the maintainer, ticked only on his confirmation)
    *(Covers FR287; ADR-1 decision 2, ADR-14 decision 4)*

## Tasks / Subtasks

<!-- Each functional task includes its tests in the same commit, red first (run the new tests, see them fail, then implement). Commit subjects: type(story-22.1/task-N): ... for every commit with no user-visible change; the two user-visible commits use the release-note subjects of the change proposal (section 2) with the component scope (feat(api), feat(web)), which RELEASING.md shows in the notes, and their bodies name Story 22.1 and the task. -->

- [x] Task 1: `PlayerTracker` with the prefix and the three patterns, the name set and the reset + tests (AC: 1, 2, 4, 5)
  - [x] 1.1: Red first: new `api/tests/test_players.py` with the Task 1 rows of Dev Notes "API tests"; run `just test-api tests/test_players.py` and see it fail (module missing)
  - [x] 1.2: New `api/src/vintagestory_api/services/players.py` with `PlayerTracker` (Dev Notes "The tracker"): the provisional `_EVENT_PREFIX`, `_JOIN`, `_LEAVE`, `_REJOIN` compiled patterns, `observe(line: str) -> None`, `reset() -> None`, `count` property. No module singleton: `ServerService` owns the instance (Task 2)
  - [x] 1.3: Logging exactly as Dev Notes "What is logged": DEBUG events with counts only; nothing with a name, an address or the line
  - [x] 1.4: `ruff format` the two files; `just test-api tests/test_players.py` green
  - [x] 1.5: Commit `refactor(story-22.1/task-1): add a player tracker for the game's join and leave lines` (nothing reads it yet; precedent `refactor(story-21.8/task-1): add the sidebar preference rules`)

- [x] Task 2: Wire the tracker into `ServerService`: every output line after the console append, resets on start, stop and exit + tests (AC: 1, 3, 5, 7)
  - [x] 2.1: Red first: the Task 2 rows of Dev Notes "API tests" in `api/tests/server/test_internal_methods.py` (`TestReadStream`) and `api/tests/server/test_lifecycle.py`; see them fail
  - [x] 2.2: `services/server.py` `__init__`: `self._player_tracker = PlayerTracker()` after the console buffer (`:185`); import from `vintagestory_api.services.players` in the import block (`:28-29`, alphabetical)
  - [x] 2.3: A `players_online` property after `game_server_pid` (`:202-211`): `self._player_tracker.count` when `self.game_server_pid is not None`, else `None` (Dev Notes "Wiring")
  - [x] 2.4: `_read_stream` (`:1234-1263`): after `await self._console_buffer.append(text)` (`:1258`), call the tracker inside its own `try`/`except Exception` that logs `player_tracker_error` at WARNING with `error_type=type(e).__name__` only and continues the loop (Dev Notes "Wiring"). The outer `except Exception` (`:1262-1263`) ends the loop, so the tracker must never reach it
  - [x] 2.5: Resets: `_start_server_locked` beside `self._last_exit_code = None` (`:1011`), before the process is spawned; `_stop_server_locked` after the task-cancel loop (`:1116-1123`), before `_update_mod_service_server_state(False)` (`:1126`); `_settle_state_after_failed_stop` in the exited branch (`:1150-1153`); `_monitor_process` right after `returncode = await self._process.wait()` (`:1208`), whatever the state (also during a stop)
  - [x] 2.6: Update the `_read_stream` docstring (`:1239-1246`): each line also goes to the player tracker
  - [x] 2.7: `ruff format` the changed files; `just test-api tests/server tests/test_players.py` green
  - [x] 2.8: Commit `refactor(story-22.1/task-2): count players from the game's output in the server service` (not yet visible in any response)

- [x] Task 3: `players_online` in `MetricsSnapshot` and `playersOnline` in the responses + tests (AC: 5, 6)
  - [x] 3.1: Red first: the Task 3 rows of Dev Notes "API tests" in `api/tests/test_metrics.py` and `api/tests/test_metrics_api.py`; see them fail
  - [x] 3.2: `models/metrics.py`: `MetricsSnapshot` gains `players_online: int | None = None` as its last field (`:25-26` are the game fields; comment: the tracker's count while the game runs, None otherwise, Epic 22 ADR-2); `MetricsSnapshotResponse` gains `players_online: int | None = Field(serialization_alias="playersOnline")` after `game_cpu_percent` (`:40`); `from_snapshot` (`:54-60`) passes it
  - [x] 3.3: `services/metrics.py` `collect()` (`:127-163`): `players_online = self._get_players_online()` and pass it to the snapshot explicitly (`:145-151`); a new `_get_players_online()` after `_get_game_server_pid` (`:193-205`) shaped like it (`None` without a server service, otherwise `server_service.players_online`); add `players_online` to the `metrics_collected` DEBUG line (`:155-161`, a count, no name)
  - [x] 3.4: Docstrings: `collect()` and the `MetricsSnapshotResponse` docstring name the new field; the two routes in `routers/metrics.py` (`:42-48`, `:76-82`) need no change (their text says nothing about fields)
  - [x] 3.5: `ruff format` the changed files; `just test-api tests/test_metrics.py tests/test_metrics_api.py tests/test_metrics_edge_cases.py tests/test_metrics_job.py` green
  - [x] 3.6: Commit `feat(api): count the players online and include them in the metrics` (body: Story 22.1 / task 3; `playersOnline` is a new field of each snapshot from `/metrics/current` and `/metrics/history`, null when the game is not running; counted from the game's join and leave lines)

- [ ] Task 4: `playersOnline` in the web type and the Players card on the dashboard + tests (AC: 8)
  - [ ] 4.1: Red first: new `web/src/features/dashboard/PlayersCard.test.tsx` and the Dashboard rows of Dev Notes "Web tests"; run `just test-web src/features/dashboard` and see them fail
  - [ ] 4.2: `web/src/api/types.ts` `MetricsSnapshot` (`:559-565`): `playersOnline: number | null;` after `gameCpuPercent`, with a comment (count while the game runs, null otherwise); update the interface's doc comment (`:552-558`)
  - [ ] 4.3: Add `playersOnline` to every `MetricsSnapshot` fixture the type now requires (Dev Notes "Existing tests that change"); `just typecheck-web` is the list
  - [ ] 4.4: New `web/src/features/dashboard/PlayersCard.tsx` (Dev Notes "The Players card"): `isRunning` prop, `useCurrentMetrics()` inside (the query MemoryCard already polls; no new request), lucide `Users` icon, `testId="players-card"`, `memo` like `UptimeCard`
  - [ ] 4.5: `Dashboard.tsx`: import it (`:32-37`), render it in a `StatCardErrorBoundary title="Players" testId="players-card"` directly after the Uptime boundary (`:134-137`), `isRunning={isRunning}` (`:87`); update the file comment's card list (`:7-11`). The grid classes (`:118`) do not change
  - [ ] 4.6: `just format-web` (it takes no file arguments; the tree is already formatted, so only this task's files should change: check `git status`, Dev Notes "Development Commands"); `just lint-web`, `just typecheck-web`, `just test-web` green
  - [ ] 4.7: Commit `feat(web): show the players online on the dashboard` (body: Story 22.1 / task 4; the card shows the count from the current metrics, or Stopped)

- [ ] Task 5: The Players card at every dashboard width + E2E test (AC: 8)
  - [ ] 5.1: `web/e2e/layout-widths.spec.ts`: a new `test.describe('Players card at every width (Story 22.1, AC 8)')` (Dev Notes "E2E test"); add Story 22.1 to the file comment (`:4-65`)
  - [ ] 5.2: Run it in a throwaway container only: `just test-e2e-ci e2e/layout-widths.spec.ts` (port 18080, removed after the run). Never against the dev stack, and never rebuild or restart the dev stack for it
  - [ ] 5.3: Commit `test(story-22.1/task-5): check the Players card at every dashboard width`

- [ ] Task 6: Validate and move the story to review (AC: all)
  - [ ] 6.1: `just check` green: API tests, pyright 0 errors and 0 warnings, ruff; web tests with 0 skipped, tsc 0 errors, Prettier. The diff adds no lint or type suppression (`# type: ignore`, `# pyright: ignore`, `eslint-disable`, `@ts-expect-error`), no `cast`, no skipped or `.only` test. `git status --short dev/` is empty after the runs
  - [ ] 6.2: `rg -n "ExamplePlayer|AnotherPlayer|203\.0\.113|198\.51\.100" api/src web/src --glob '!*.test.*'` finds nothing (placeholders live in tests only)
  - [ ] 6.3: Ask the maintainer, in the hand-off and the PR description, for one anonymised join line and one leave line copied from a real server's console (name replaced by `ExamplePlayer`, address by `203.0.113.5:42420`, timestamp kept as printed)
  - [ ] 6.4: Manual check (maintainer only; leave unticked until he confirms): his two sample lines are added to `test_players.py` as test cases and counted; if the provisional `_EVENT_PREFIX` does not match them it is corrected from them in the same commit (Dev Notes "When the sample arrives"); the Players card shows the count with a real client joining and leaving
  - [ ] 6.5: Story status `review` in this file; `just sprint set 22-1-players-online-are-counted review`; Dev Agent Record and File List filled in, every statement true of the code
  - [ ] 6.6: Commit `chore(story-22.1/task-6): validate and move story 22.1 to review`
  - [ ] 6.7: PR against `main` with "API contract changes" from this story; PR link as a comment on `VSS-bhw` (`bd comments add`; the bead stays open: Story 22.2 closes it). Pushing and opening the PR only with the maintainer's or orchestrator's go-ahead

## Dev Notes

### The code today (verified at 3b15aa21)

- **The only reader of the game's output** is `ServerService._read_stream` (`api/src/vintagestory_api/services/server.py:1234-1263`). The game is started with piped stdin, stdout and stderr (`:1014-1020`) and one reader task per stream (`:1029-1034`). Each line is decoded with `errors="replace"` and `rstrip()`ed (`:1257`) and appended to the console buffer (`:1258`). The loop's `except Exception` (`:1262-1263`) logs `stream_read_error` and **ends the loop**: anything new inside the loop that raises would stop console capture for the rest of the run.
- `ConsoleBuffer.append` (`services/console.py:41-70`) stores the line as is and logs `console_append` at DEBUG with `line_length` only. The console buffer and its WebSocket already carry every game line, names and addresses included, to the roles that may read the console today; this story does not change that.
- **Lifecycle** (all in `services/server.py`): `_start_server_locked` (`:956-1056`) sets STARTING and `_last_exit_code = None` (`:1010-1011`), spawns, then sets the start time and RUNNING (`:1023-1024`) and starts the monitor and the readers. `_stop_server_locked` (`:1073-1138`) sends SIGTERM, waits up to `timeout` (10 s, `:1058`), kills on timeout, sets `_server_start_time = None` (`:1114`), cancels the monitor and both readers (`:1116-1123`) and tells the mod service (`:1126`). A stop that raises calls `_settle_state_after_failed_stop` (`:1140-1153`), whose exited branch (`:1150-1153`) is the other stop-time reset point. `_restart_server_locked` (`:1170-1199`) calls stop then start, so it resets twice. `_monitor_process` (`:1201-1232`) waits for the exit (`:1208`) and clears the start time (`:1212`) whatever the state, but changes the state only outside a stop (`:1215`).
- `game_server_pid` (`:202-211`) is the PID while the process lives (`returncode is None`), else `None`; `MetricsService._get_game_metrics` (`services/metrics.py:207-233`) uses it to decide "game running" for `game_memory_mb` and `game_cpu_percent`.
- **Metrics:** `MetricsSnapshot` is a frozen dataclass (`models/metrics.py:11-26`); `MetricsSnapshotResponse` (`:29-60`) serialises it with camelCase aliases. `MetricsService.collect()` (`services/metrics.py:127-163`) builds a snapshot from psutil and appends it to the 360-sample ring buffer; the `metrics_collection` job calls it every `metrics_collection_interval` seconds (`jobs/metrics_collection.py:19-20`, `jobs/__init__.py:40`). `GET /metrics/current` (`routers/metrics.py:42-73`) and `/history` (`:76-127`) are **Admin only** (`RequireAdmin`, `:50`, `:84`) and return `model_dump(mode="json", by_alias=True)`.
- **Web:** `MetricsSnapshot` (`web/src/api/types.ts:559-565`) mirrors the response. `useCurrentMetrics()` (`web/src/hooks/use-metrics.ts:43-57`) polls `/metrics/current` every 10 s under `queryKeys.metrics.current`; `MemoryCard` (`web/src/features/dashboard/MemoryCard.tsx:21-85`) calls it. `Dashboard.tsx` renders four `StatCard`s in `grid gap-4 sm:grid-cols-2` (`:118-138`): Server Status, Memory, Disk Space, Uptime. `UptimeCard` (`UptimeCard.tsx:86-131`) shows "Loading...", "Stopped" / "Server is not running", "N/A" / "Uptime unavailable", or the value. `StatCard` (`web/src/components/StatCard.tsx:50-...`) renders `data-testid={testId}` and `{testId}-value`, with `aria-live="polite"` on the value.
- **No player count exists** anywhere in `api/src` or `web/src` (`rg -i "players_online|playersOnline|PlayerTracker"` finds nothing). `MaxClients` is read only by the Game Settings page (`web/src/features/game-server/GameConfigPanel.tsx:77`), not by the dashboard.

### The tracker (Task 1)

New module `api/src/vintagestory_api/services/players.py`:

```python
"""Players online, counted from the game's join and leave lines (Epic 22 ADR-1)."""

import re

import structlog

logger = structlog.get_logger()

# PROVISIONAL until the maintainer's sample lines (Story 22.1, Task 6.4): the game's
# Logger.Event lines are assumed to carry the "[Event]" tag (seen in v1.22.7 logs), with
# nothing but a timestamp (no "[") before it. A chat line carries its own tag first, so it
# never matches.
_EVENT_PREFIX = re.compile(r"^[^\[]*\[Event\] (?P<message>.+)$")

# The VintagestoryLib.dll v1.22.7 literals, anchored at the end of the message.
_JOIN = re.compile(r"^(?P<name>.+) \S+ joins\.$")  # '{0} {1} joins.'
_LEAVE = re.compile(r"^Player (?P<name>.+) left\.$")  # 'Player {0} left.'
_REJOIN = re.compile(r"^(?P<name>.+) joined again, killing previous client\.$")


class PlayerTracker:
    """The set of player names online. Names never leave this class."""

    def __init__(self) -> None:
        self._online: set[str] = set()

    @property
    def count(self) -> int:
        return len(self._online)

    def observe(self, line: str) -> None:
        """Update the set from one game output line; any other line changes nothing."""
        ...

    def reset(self) -> None:
        """Empty the set: the game started, stopped or exited."""
        ...
```

- **Order of the checks in `observe`:** prefix first (no match: return); then `_REJOIN` before `_JOIN` (a rejoin message does not end in "joins.", but checking it first keeps the intent clear and costs nothing); then `_JOIN` (add the name; already present: nothing); then `_LEAVE` (remove; not present: nothing). `Client {0} disconnected.` is not matched (ADR-1 decision 2: it names a client number, and the leave line follows it).
- **Names with spaces:** `_JOIN`'s greedy `(?P<name>.+)` followed by ` \S+ joins.` takes the last space-separated token as the address, so `Some Name 203.0.113.5:42420 joins.` gives `Some Name`. An IPv6 address in brackets (`[2001:db8::1]:42420`) has no space and is one `\S+` token. `_LEAVE` and `_REJOIN` take the whole remainder.
- `observe` does not strip or lower-case: `_read_stream` already `rstrip()`s (`:1257`), and names are case-sensitive in the game. A `\r` left by the game would already be stripped by `rstrip()`.
- The tracker is synchronous and holds no lock: both reader tasks run on the event loop and `observe` never awaits, so calls never interleave.
- `count` is the set's size, whatever the game state; `ServerService.players_online` (Task 2) decides when it is reported.

### What is logged (Task 1.3, 2.4; security)

**Decision:** no log line at any level carries a player name, a player address or the game line. ADR-1 decision 4 allows nothing above DEBUG; this story keeps DEBUG free of them too, so `VS_LOG_LEVEL=DEBUG` or the debug switch cannot put them into a log shipper.

| Event | Level | Fields |
|---|---|---|
| `player_joined` | DEBUG | `count` (new count) |
| `player_left` | DEBUG | `count` |
| `player_join_ignored` | DEBUG | `reason="already_online"` (a join or a rejoin for a name in the set), `count` |
| `player_leave_ignored` | DEBUG | `reason="not_online"`, `count` |
| `players_reset` | DEBUG | `previous_count` |
| `player_tracker_error` | WARNING | `stream` (`stdout`/`stderr`), `error_type` (`type(e).__name__`) only: `str(e)` could echo the line |
| `metrics_collected` (existing) | DEBUG | gains `players_online` (a count) |

No INFO line is added: the count changes too often to be news at INFO, and the metrics carry it.

### Wiring (Task 2)

```python
    @property
    def players_online(self) -> int | None:
        """Players online while the game process runs (Epic 22 ADR-2); None otherwise."""
        if self.game_server_pid is None:
            return None
        return self._player_tracker.count
```

- Same "running" rule as the game's memory and CPU (`game_server_pid`), so the three game fields of a snapshot are null together. During STOPPING the process still lives: the count is reported until it exits, then the reset makes it 0 before the next start.
- In `_read_stream`, after the append:

```python
                await self._console_buffer.append(text)
                try:
                    self._player_tracker.observe(text)
                except Exception as e:
                    # A tracker fault must never stop console capture (Epic 22 ADR-1 decision 1).
                    logger.warning(
                        "player_tracker_error", stream=stream_name, error_type=type(e).__name__
                    )
```

  `except Exception` here is the "no silent failures" pattern of `project-context.md` (it logs); it is not a suppression. `CancelledError` is a `BaseException` and still reaches the outer handler.
- **Reset placement and why:** at start, before spawning, so no name from an earlier run survives (and a failed spawn leaves 0). At stop, after the readers are cancelled (`:1116-1123`), so no reader can add a name after the reset. In `_settle_state_after_failed_stop` only in the exited branch (a live process keeps its players). In `_monitor_process` right after the wait, unconditionally: an exit during a stop resets too, which is harmless. A reader may still drain a few buffered lines after the monitor's reset (the process has exited); a late leave line changes nothing, and `players_online` is `None` once the PID is gone, so a stale count is never reported; the next start resets again.
- The tracker is not exposed as a property: tests read the count through `players_online`, or `_player_tracker` (the server test files already relax `reportPrivateUsage` at file level, `test_internal_methods.py:16`, `test_lifecycle.py:19`; add no new relaxation or ignore).

### Metrics (Task 3)

- `players_online: int | None = None` is last in the frozen dataclass, so the 21 existing `MetricsSnapshot(...)` constructions in the tests (`test_metrics.py` 7, `test_metrics_edge_cases.py` 13, `test_metrics_api.py` 1) still build; `collect()` always passes it explicitly, and a test pins that it does.
- `MetricsSnapshotResponse.players_online` has no default: `from_snapshot` is the only constructor, and a forgotten field should fail.
- **JSON field name: `playersOnline`** (ADR-2 decision 1; the API contract table of the change proposal). The value is an integer, or `null` when the game is not running. Field order in the JSON: after `gameCpuPercent`.
- History: snapshots taken before the upgrade do not exist after it (the buffer is in memory), so every snapshot served has the field.

### The Players card (Task 4)

```tsx
export interface PlayersCardProps {
  /** Whether the game server is running (from the server status) */
  isRunning: boolean;
}
```

| Case | value | subtitle |
|---|---|---|
| metrics query loading | `Loading...` | none |
| not running (`isRunning` false), whatever the metrics say | `Stopped` | `Server stopped` |
| metrics query error | `Error` | the error's message (as `MemoryCard`, `:33-43`) |
| running, no snapshot yet, or `playersOnline` null, or not a valid number (`isValidNumeric`, `web/src/lib/numeric-utils`) | `N/A` | `Waiting for metrics...` |
| running, `playersOnline` = 0 | `0` | `No players online` |
| running, 1 | `1` | `1 player online` |
| running, n > 1 | `n` | `n players online` |

- Title `Players`, icon `Users` from `lucide-react`, `testId="players-card"`. The "not running" check comes before the error and empty checks: a stopped game always reads Stopped, as in `UptimeCard` (`:96-107`), even though its metrics snapshot may lag the status by up to one poll.
- **`MaxClients` is not shown** (ADR-2 decision 3 leaves it to the story): the dashboard does not read the game settings, so `of N` would need a new request. The card shows the count only.
- No mutation is involved, so the TanStack v5 `onError` rule of `project-context.md` (Frontend, "Mutation errors") does not apply; the card only reads a query.
- A Monitor key gets 403 from the Admin-only metrics routes, so its Players card shows `Error`, as its Memory card does today. Not changed here (see "Not changed").

### Web tests (Task 4)

| File | Test |
|---|---|
| `web/src/features/dashboard/PlayersCard.test.tsx` (new; fetch stub and `QueryClientProvider` wrapper as `MetricCards.test.tsx`, `:1-70`, does for `MemoryCard`) | One test per row of the card's table: `players-card-value` and the subtitle text. Plus: `isRunning=false` with a snapshot of `playersOnline: 3` still shows `Stopped` / `Server stopped`; `playersOnline: NaN` shows `N/A`; the card asks for `/api/v1alpha1/metrics/current` and nothing else (assert the fetch URLs) |
| `web/src/features/dashboard/Dashboard.test.tsx` `stat cards grid (Story 12.4)` (`:406-479`) | `renders stats grid with 4 cards` (`:407-438`) becomes 5 cards and also expects `players-card`. New test: the Players card is the element right after the Uptime card inside `dashboard-stats-grid` (compare `children` order of the grid by test ID). New test: with `state: 'installed'` the Players card shows `Stopped` |
| `web/src/hooks/use-metrics.test.tsx` | Its fixtures gain `playersOnline` (type change only); one assertion that `data.data.playersOnline` comes through from the response |

Vitest rules of `project-context.md` apply (`vi.stubGlobal` for `fetch` with `vi.unstubAllGlobals()` in `afterEach`, or the file's existing `globalThis.fetch` save and restore pattern; do not mix both in one file). No `.skip`, no `.only`.

### E2E test (Task 5)

- In `web/e2e/layout-widths.spec.ts`, a helper `runningWithPlayers(page)` routes `**/api/v1alpha1/server/status` (GET only; fetch the real answer with `fetchOnNewConnection` from `./config-js`, then set `state: 'running'`, `version`, `uptimeSeconds: 3600`, as `installedVersion` does at `:747-758`) and `**/api/v1alpha1/metrics/current` (fulfil `{status: 'ok', data: {timestamp, apiMemoryMb: 100, apiCpuPercent: 1, gameMemoryMb: 500, gameCpuPercent: 5, playersOnline: 2}}`). `readOnly(page)` (`:146`) still refuses every write, so nothing on the server changes and the game is neither started nor stopped.
- **Route order:** register the helper after `readOnly` (whose `pretendServerInstalled` route would otherwise answer the status first; the last-registered route runs first) and before `page.goto`, the way `installedVersion` is: add a `players` option to `PageOptions`/`openPage` (`:309-353`) beside `installed`. Calling the helper after `openPage` returns would stub only after the first status and metrics requests.
- Widths 320, 390, 768, 1024, 1440, 2560, for both `SIDEBAR` states (`:355-358`), through `openPage(..., { players: true })`: `players-card` is visible, `players-card-value` is `2`, the card is inside the viewport (`expectInsideViewport`, `:301`), `documentOverflow(page)` is 0 (`:290`), and the grid's child after `uptime-card` is `players-card`.
- Run with `just test-e2e-ci e2e/layout-widths.spec.ts` only (ADR-14 decision 2). Not against `http://localhost:9080`: the dev stack serves an older build, and rebuilding it would stop its game server.

### API tests

| Task | File | Test |
|---|---|---|
| 1 | `api/tests/test_players.py` (new) | Helpers `event(message)` → `f"18.11.2026 10:15:32 [Event] {message}"` (marked provisional, as the prefix) and the placeholder constants `NAME = "ExamplePlayer"`, `ADDRESS = "203.0.113.5:42420"`, `OTHER = "AnotherPlayer"`, `OTHER_ADDRESS = "198.51.100.7:42420"` |
| 1 | same | **Literal part pinned** (independent of the prefix): parametrised over the three message patterns with `re.fullmatch`-style assertions on the module patterns' `name` group: `ExamplePlayer 203.0.113.5:42420 joins.` → `ExamplePlayer`; `Some Name 203.0.113.5:42420 joins.` → `Some Name`; `ExamplePlayer [2001:db8::1]:42420 joins.` → `ExamplePlayer`; `Player ExamplePlayer left.` and `Player Some Name left.`; `ExamplePlayer joined again, killing previous client.`. Not matched: `Client 3 disconnected.`, `ExamplePlayer joined. Say hi :)` (the chat text from `en.json`), `ExamplePlayer joins.` (no address) |
| 1 | same | Counting (AC 1, 2): join → 1; second name → 2; same name again → 2; rejoin line → 2; leave of a name not online → 2; leave `NAME` → 1; leave `NAME` again → 1; leave `OTHER` → 0; never below 0 |
| 1 | same | Chat and other lines (AC 4): `18.11.2026 10:15:33 [Chat] AnotherPlayer: he joins.`-style lines ending in "joins." and in "left." (`[Chat] 0 | AnotherPlayer: Player ExamplePlayer left.`), a line with `[Event]` after another tag (`... [Chat] x [Event] ExamplePlayer 203.0.113.5:42420 joins.`), the bare literal with no prefix, `[Notification] ...`, an empty line: the count stays 0 |
| 1 | same | `reset()` empties the set; a join after it counts from 0 |
| 1 | same | Logging (AC 5): with `structlog.testing.capture_logs()`, a join, a duplicate, a rejoin, a leave, an unknown leave and a reset produce exactly the events and fields of "What is logged"; `repr` of the captured list contains neither a name nor an address |
| 2 | `api/tests/server/test_internal_methods.py` `TestReadStream` (`:82-172`) | Lines `[event(join NAME), event(join OTHER), b""]` through `_read_stream` (the `AsyncMock(side_effect=[...])` stream of `:113-124`) with a running process mock (`_process` with `returncode = None`, `pid = 4242`): `players_online == 2` and both lines are in the console buffer. With `_process = None`: `players_online is None` and the lines are still buffered. **AC 7:** `monkeypatch.setattr(service._player_tracker, "observe", <raises ValueError>)`, three lines: all three are in the buffer, one `player_tracker_error` per line at WARNING with `error_type="ValueError"`, no `stream_read_error`, and no captured event contains the line text |
| 2 | `api/tests/server/test_lifecycle.py` | **Mind the fixture:** `mock_subprocess` (`:35-66`) makes `wait()` return after 0.01 s and never sets `returncode`, so the monitor's exit reset runs about 10 ms after every start and `game_server_pid` stays non-`None` after a stop. So: **count while running**, as `test_stop_server_records_exit_code` (`:424-456`): a blocking `wait` for the monitor and `process.stdout.readline = AsyncMock(side_effect=[event(join NAME), event(join OTHER), b""])` set after `_configure_stream_mocks`; after start and a short sleep, `players_online == 2`. **Start** resets: put a name in the tracker before `start_server()`; after start the count is 0. **Stop** resets: same setup, then swap `wait` for one that sets `returncode = 0` (`:446-450`); after `stop_server()`, `_player_tracker.count == 0` and `players_online is None`. **Exit** resets: as `test_crash_detected_updates_state` (`:607-624`), adding a name after `start_server()` returns (start itself resets) and before the sleep; after `asyncio.sleep(0.1)` the count is 0. **Failed stop of an exited process** (as `test_failed_stop_of_exited_process_returns_to_installed`, `:485-521`, a name added after start): count 0. **Failed stop of a live process** (as `test_failed_stop_of_live_process_stays_running`, `:459-483`, a name added after start): the count is unchanged. **Restart** (`TestRestartServer`, `:561-591`): count 0 after restart |
| 2 | same or `test_internal_methods.py` | Logging during the lifecycle tests: no captured event contains `ExamplePlayer` or `203.0.113.5` (AC 5) |
| 3 | `api/tests/test_metrics.py` `TestMetricsService` (`:225-409`) | `test_collect_with_game_server_running` (`:273-304`): set `mock_server_service.players_online = 2`, assert `snapshot.players_online == 2`. `server_service=None` tests: `snapshot.players_online is None`. New: a server service whose `players_online` is `None` (game stopped) gives `None`; a snapshot built by `collect()` passes the field explicitly (`dataclasses.fields` order unchanged apart from the new last field) |
| 3 | `api/tests/test_metrics.py` `TestMetricsSnapshot` (`:23-106`) | Default `players_online is None`; explicit `2` kept; still frozen and hashable with the field |
| 3 | `api/tests/test_metrics_api.py` | `_create_snapshot` (`:29-43`) gains `players: int | None = 2`. `/current` as Admin: `data["playersOnline"] == 2` (AC 6); with `players=None`: `null`; every existing key and value unchanged (assert the full key set: `timestamp, apiMemoryMb, apiCpuPercent, gameMemoryMb, gameCpuPercent, playersOnline`). `/history`: each item has `playersOnline`. `test_current_response_uses_camel_case_aliases` (`:303-322`): `"playersOnline" in data`, `"players_online" not in data`. No player name in `response.text` for either route (AC 5) |

All addresses are documentation ranges (RFC 5737 `203.0.113.0/24`, `198.51.100.0/24`; RFC 3849 `2001:db8::/32`); all names are placeholders.

### Existing tests that change (deliberately)

- `api/tests/test_metrics_api.py`: `_create_snapshot` gains a parameter (above); the key-set assertion is new.
- `web`: every object typed `MetricsSnapshot` gains `playersOnline` (tsc requires it; tests are type-checked, `web/tsconfig.json` `include: ["src", "tests"]`). Only two files type their fixtures so: `src/features/dashboard/Dashboard.test.tsx` (`sampleMetrics: MetricsSnapshot[]`, `:101-116`) and `MetricsChart.test.tsx` (`mockDataWithGame`, `mockDataWithNullGame`, ...: `MetricsSnapshot[]`, from `:29`). `src/hooks/use-metrics.test.tsx` (untyped fetch bodies, `:32-83`) gains `playersOnline` in its fixtures for the new assertion. `MemoryCard.test.tsx` (its own `MetricsData` interface, `:41-47`, and a mocked hook) and `MetricCards.test.tsx` (untyped fetch bodies) are not type-checked against `MetricsSnapshot` and need no change. Use `playersOnline: null` where the fixture's game fields are null, a number otherwise. Change nothing else in those tests.
- `Dashboard.test.tsx` "renders stats grid with 4 cards" becomes 5 (above).
- Anything else that fails is a regression (AC 9): fix the code, not the test.

### When the sample arrives (Task 6.4, maintainer)

- Add both lines verbatim (already anonymised) to `test_players.py` as a parametrised "maintainer sample" case: the join gives 1, the leave then 0.
- If `_EVENT_PREFIX` does not match them, change only `_EVENT_PREFIX` (and the `event()` helper) to what they show, keeping the rule that a chat line cannot match; the three message patterns are the DLL's and stay. Remove "PROVISIONAL" from the comment once the sample matches.
- Commit type: `test(story-22.1/user)` when only test cases are added; if the prefix changes before 22.1 is released, `chore(story-22.1/user): match the game's real event line prefix` (a `fix` would put a release note in for a bug no release had). The maintainer may choose otherwise.

### Not changed (do not "fix" these here)

- `MaxClients` on the card (above); the history chart (ADR-2 decision 4); the metrics routes' Admin-only rule, and therefore the Monitor key's `Error` on the Memory and Players cards.
- The console buffer, its WebSocket and history routes, and what they carry (game lines with names and addresses, as today).
- The stop timeout and the restart path (Story 22.3); `/metrics` for Prometheus (Story 22.2, which reads `players_online` and reports 0 when it is `None`).
- `Client {0} disconnected.` lines; polling `/list clients` (answer 4).
- The existing `# type: ignore` comments in `test_metrics.py` (`:71`, `:295`) and `test_metrics_api.py` (`:14`), and the file-level pyright relaxations of the server test files: they predate the rule; add none.
- The dev stack: no task starts, stops, rebuilds or restarts it or its game server. It is at `http://localhost:9080`; any check there is read-only and is the maintainer's.

### API contract changes

- `GET /api/v1alpha1/metrics/current` and `GET /api/v1alpha1/metrics/history`: each snapshot gains `playersOnline` (integer; `null` when the game server is not running). Additive; no field, route or status code changes.
- Log events added at DEBUG (`player_joined`, `player_left`, `player_join_ignored`, `player_leave_ignored`, `players_reset`) and WARNING (`player_tracker_error`); `metrics_collected` gains `players_online`. None carries a name or an address.
- Web: a Players card on the dashboard, after Uptime.

### ADR against the code

1. **The prefix is needed now, not only after the sample.** ADR-1 decision 2 fixes the prefix pattern from the maintainer's sample and pins "the literal part only" until then; its decision 6 and AC 4 ask that a chat line ending in "joins." is not counted, which only a prefix can decide (`AnotherPlayer: he joins.` matches `_JOIN` with the name `AnotherPlayer: he`). So the story ships a provisional prefix, `^[^\[]*\[Event\] ` (the tag the game's `Logger.Event` lines carry: the v1.22.7 logs on the dev stack's data directory have 103 `[Event]` lines, for example `... [Event] Saved player world data...`, and the DLL holds no `Server Event` string; checked by the controller after drafting. Whether stdout repeats the log file's format exactly is what the sample confirms, preceded only by a timestamp, so a line whose first tag is `[Chat]` cannot match), with the literal patterns pinned separately, and Task 6.4 confirms or corrects it from the sample. Until then a wrong guess means a count of 0, never a wrong positive count; the risk is the one the change proposal names (section 2, "Risks", Story 22.1).
2. **"An authenticated client" is an Admin key.** The metrics routes are Admin only (`routers/metrics.py:50`, `:84`); AC 6 says Admin.
3. **A fourth reset point.** ADR-1 decision 3 names start, stop and exit. A stop that raises after the process has exited ends in `_settle_state_after_failed_stop` (`services/server.py:1140-1153`), and the monitor may already have been cancelled; that branch resets too (AC 3).
4. **No names at DEBUG either.** ADR-1 decision 4 forbids names at INFO and above and describes DEBUG lines with counts only; the story makes that the rule for every level and for addresses as well, and AC 5 tests it at DEBUG (see "What is logged").
5. **"Server stopped" on the card.** ADR-2 decision 3 and the epic's AC say the card shows "Server stopped" and is built like `UptimeCard`, whose stopped value is `Stopped` with a subtitle (`UptimeCard.tsx:96-107`). The card shows `Stopped` as the value and `Server stopped` as the subtitle, so the two cards read alike and the text the AC names is shown.
6. **"Next to the Uptime card" in a two-column grid.** The grid is `sm:grid-cols-2` with four cards (`Dashboard.tsx:118`); a fifth card directly after Uptime starts a third row from 640px and sits under Uptime below it. The story keeps the grid and the existing order (no other card moves) and places the card directly after Uptime in the document; AC 8 says so. A three-column grid or a reorder is a layout decision for the maintainer, not needed for the count.
7. **`MaxClients`:** ADR-2 decision 3 lets the story decide; the dashboard does not read the game settings, so the card shows the count only.
- The line numbers in ADR-1 and the facts section (`server.py:1014-1020`, `:1234`, `metrics.py:127`, `:207`, `models/metrics.py:12`) match 3b15aa21.

### Testing Requirements

**CRITICAL:** tests are written with each task and committed with it, red first. `just test-api <files>` / `just test-web <path>` after each task; `just check` before review.

- No lint or type suppression of any kind, no `cast` to silence a type, no skipped test (`pytest.mark.skip`, `it.skip`, `.only`). Pyright stays at 0 errors and 0 warnings; `just check` is green.
- Log assertions use `structlog.testing.capture_logs()` (or `capsys`; the conftest autouse fixture configures structlog at DEBUG to stdout, `api/tests/conftest.py:30-56`).
- Private state in tests: `monkeypatch.setattr(obj, "name", value)` so it is restored; the server test files already allow private access at file level.
- Async tests use `@pytest.mark.asyncio` as the neighbouring tests do; a fake process never runs `dotnet`.
- Never start, stop, rebuild or restart the dev stack or its game server (ADR-14). The only container any task runs is the throwaway one of `just test-e2e-ci`.
- Placeholders only: `ExamplePlayer`, `AnotherPlayer`, documentation addresses. No real player name, address or server line goes into the repository except the maintainer's anonymised sample.

### Security Requirements

- No player name, address or game line in any log line, at any level (table "What is logged"); the WARNING for a tracker fault carries the exception's type only.
- The API returns the count only; names never leave `PlayerTracker` (no getter for the set).
- The metrics stay Admin only. Story 22.2 exposes the count without a key at `/metrics` (answer 2); that is its decision, not this story's.
- The console buffer is unchanged: it carries the same lines to the same roles as before.

### Development Commands

- `just test-api tests/test_players.py`, `just test-api tests/server`, `just test-api tests/test_metrics.py tests/test_metrics_api.py tests/test_metrics_edge_cases.py tests/test_metrics_job.py`, `just typecheck-api`, `just lint-api`.
- `just test-web src/features/dashboard src/hooks/use-metrics.test.tsx`, `just typecheck-web`, `just lint-web`, `just format-web` (formats the whole web tree with the pinned Prettier and takes no arguments; `just lint-web` passes at the base, so it should touch only this story's files; if it touches others, restore them with `git restore` so no reformat mixes into a task commit).
- `cd api && uv run ruff format <changed files>` (do not format the whole tree).
- `just test-e2e-ci e2e/layout-widths.spec.ts` (throwaway container; Task 5 only).
- `just check` (Task 6).

### Previous Story Intelligence

- **12.2-12.5 (Epic 12):** built the metrics buffer, collection job, routes, the stat cards and the chart; the Epic 12 architecture already weighed console parsing for players (`architecture/epic-12-dashboard-metrics.md:335-370`) and deferred it. Its example lines (`[Event] Player <username> joined`) were a guess, not observed; the DLL literals of Epic 22 replace them.
- **21.3:** the model for log assertions and for a story decision recorded under "ADR against the code"; `monkeypatch` instead of ignore comments; completion notes must be true of the code.
- **21.7, 21.8:** `layout-widths.spec.ts` is the place for width checks, read only, with `page.route` stubs; `refactor(story-21.8/task-1)` for a module not yet wired in; run E2E in the throwaway container.
- **17.x, 18.x:** a `feat` or `fix` subject must describe what an operator sees; a task is ticked only when done; manual checks are the maintainer's.

### Git Intelligence

- Branch `story/22-1-players-online-are-counted` from `planning/epic-22-server-operations-and-metrics` at `3b15aa21` (`docs(epic-22): plan server operations and metrics`) on `e16a7932` (`main`, dev stack on port 9080). No other Epic 22 story has code yet.
- Planned commits: Task 1 `refactor(story-22.1/task-1): add a player tracker for the game's join and leave lines`; Task 2 `refactor(story-22.1/task-2): count players from the game's output in the server service`; Task 3 `feat(api): count the players online and include them in the metrics`; Task 4 `feat(web): show the players online on the dashboard`; Task 5 `test(story-22.1/task-5): check the Players card at every dashboard width`; Task 6 `chore(story-22.1/task-6): validate and move story 22.1 to review`. The two `feat` subjects are the change proposal's draft release notes (section 2); `just changelog` should list exactly those two from this story.

### Project Structure Notes

- New: `api/src/vintagestory_api/services/players.py`, `api/tests/test_players.py`, `web/src/features/dashboard/PlayersCard.tsx`, `web/src/features/dashboard/PlayersCard.test.tsx`. The dashboard's component files are PascalCase (`UptimeCard.tsx`), so the new card follows them rather than the kebab-case rule of `project-context.md`.
- Modified: `api/src/vintagestory_api/services/server.py`, `services/metrics.py`, `models/metrics.py`; `api/tests/server/test_internal_methods.py`, `api/tests/server/test_lifecycle.py`, `api/tests/test_metrics.py`, `api/tests/test_metrics_api.py`; `web/src/api/types.ts`, `web/src/features/dashboard/Dashboard.tsx`, `Dashboard.test.tsx`, `MetricsChart.test.tsx`, `web/src/hooks/use-metrics.test.tsx`, `web/e2e/layout-widths.spec.ts`; this story file and `sprint-status.yaml` (through `just sprint`).
- No README change (the README's metrics section is Story 22.2's), no dependency, no compose or Dockerfile change.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 22.1: Players Online Are Counted] and the Epic 22 header
- [Source: _bmad-output/planning-artifacts/prd.md] FR287, FR288 (`:893-894`)
- [Source: _bmad-output/planning-artifacts/architecture/epic-22-server-operations-and-metrics.md] "Facts Checked in the Code" (Metrics today, Players), ADR-1, ADR-2, ADR-14
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-18-epic-22.md] section 1 (evidence), section 2 (API contract table, draft release notes, risks), section 5 (answers 1 and 4, maintainer's sample)
- [Source: _bmad-output/planning-artifacts/architecture/epic-12-dashboard-metrics.md] player count research (`:335-370`)
- [Source: _bmad-output/implementation-artifacts/21-3-log-level-and-config-viewer.md] (layout and depth)
- `project-context.md`: tests with each task; no suppressions; logging conventions and "Never Log Sensitive Data"; commit types by user impact; Frontend "Mutation errors" (not applicable: no mutation); manual verification at `http://localhost:9080`
- `RELEASING.md` "Commit messages are release notes"
- Bead: `VSS-bhw` (API-023), parent `VSS-oole` (Epic 22)

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5), dev-story workflow, non-interactive

### Debug Log References

- Task 1 red: `just test-api tests/test_players.py` failed at collection (`cannot import name 'players'`).
- Task 2 red: the 10 new tests in `tests/server/test_internal_methods.py` and `tests/server/test_lifecycle.py` failed (`ServerService` had no `players_online` or `_player_tracker`).
- Task 3 red: 19 tests failed in `tests/test_metrics.py` and `tests/test_metrics_api.py` (`MetricsSnapshot` had no `players_online`; `_create_snapshot` passed it).

### Completion Notes List

- 2026-11-18: Story created (create-story, non-interactive) and checked against the create-story checklist: 6 tasks; every code task carries its tests; every AC is mapped to a task (AC 9 to Task 6 and every task's test run, AC 10 to Task 6.4). Ultimate context engine analysis completed - comprehensive developer guide created.
- Task 1: `PlayerTracker` in `services/players.py` with the provisional `_EVENT_PREFIX` and the three DLL literals; `observe` checks prefix, then rejoin, join, leave. Logging is DEBUG only, with counts and the `reason` field, never a name, address or line. 26 tests in `tests/test_players.py` (literal patterns, counting, chat and other lines, reset, logging with `capture_logs`). Decision: a rejoin line for a name not in the set adds it (the line says the player is on the server; the story names only the already-online case, which changes nothing); pinned by `test_rejoin_of_a_name_not_online_counts_it`. Formatted with `cd api && uv run ruff format <files>` (as Dev Notes "Development Commands" says; `just format-api` takes no file arguments and formats the whole tree).
- Task 2: `ServerService` owns a `PlayerTracker`; `players_online` reports its count while `game_server_pid` is set, else `None`. `_read_stream` passes each line to the tracker after the console append, inside its own `try`/`except Exception` that logs `player_tracker_error` (WARNING, `stream` and `error_type` only) and continues. Resets in `_start_server_locked` (before the spawn), `_stop_server_locked` (after the readers are cancelled), the exited branch of `_settle_state_after_failed_stop`, and `_monitor_process` right after the wait. Tests: 3 in `TestReadStream` (count while running, `None` without a process, AC 7 tracker fault: lines kept, one WARNING per line, no `stream_read_error`, no line text logged) and 7 in a new `TestPlayersOnline` class in `test_lifecycle.py` (count while running with a no-name log check, start, stop, exit, failed stop of an exited and of a live process, restart). The lifecycle tests use a blocking-`wait` fake process (as `test_stop_server_records_exit_code`) so the start and stop resets are tested on their own, not by the monitor's; the exit and restart tests use `mock_subprocess`.
- Task 3: `MetricsSnapshot.players_online: int | None = None` (last field); `MetricsSnapshotResponse.players_online` (alias `playersOnline`, no default) after `game_cpu_percent`; `MetricsService.collect()` passes `players_online` from the new `_get_players_online()` explicitly and logs it in `metrics_collected`. Tests: 3 new in `TestMetricsSnapshot` (default `None`, explicit value frozen and hashable, field order), `players_online` assertions in the running and no-server-service `collect()` tests, 3 new in `TestMetricsService` (game stopped gives `None`, `collect()` names the field when it builds the snapshot, `_get_players_online()` without a server service), and a new `TestPlayersOnline` class in `test_metrics_api.py` (`/current` 2 and null with the full key set, `/history` items, no name in the response text). Full API suite: 3503 passed.
- Commit subject: `feat(story-22.1/task-3): count the players online and include them in the metrics` instead of the story's `feat(api): ...` (orchestrator's instruction: the project's `type(story-X.Y/task-N)` convention; the scope is stripped from release notes, so the release note reads the same).

### File List

- `api/src/vintagestory_api/services/players.py` (new)
- `api/tests/test_players.py` (new)
- `api/src/vintagestory_api/services/server.py` (modified)
- `api/tests/server/test_internal_methods.py` (modified)
- `api/tests/server/test_lifecycle.py` (modified)
- `api/src/vintagestory_api/models/metrics.py` (modified)
- `api/src/vintagestory_api/services/metrics.py` (modified)
- `api/tests/test_metrics.py` (modified)
- `api/tests/test_metrics_api.py` (modified)

## Change Log

- 2026-11-18: Story 22.1 created (ready-for-dev).
- 2026-11-18: Validated against the create-story checklist: AC 5 scoped to exclude the unchanged console and log-file routes; tracker snippet wrapped to the 100-column ruff limit; lifecycle test rows account for `mock_subprocess` (early monitor reset, `returncode` never set); web fixture list corrected to the files tsc checks; E2E route order (register the stub inside `openPage`); file comment range `:4-65`.
