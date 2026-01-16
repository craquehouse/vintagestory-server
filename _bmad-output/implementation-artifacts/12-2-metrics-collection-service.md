# Story 12.2: Metrics Collection Service

Status: in-progress

## Story

As a **backend developer**,
I want **a service that collects server metrics periodically**,
So that **current and historical metrics are available via API**.

## Acceptance Criteria

1. **Given** the API server is running
   **When** the metrics collection job executes (default every 10 seconds)
   **Then** it collects: timestamp, api_memory_mb, api_cpu_percent

2. **Given** the game server process is running
   **When** metrics are collected
   **Then** it also collects: game_memory_mb, game_cpu_percent

3. **Given** the game server is not running
   **When** metrics are collected
   **Then** game_memory_mb and game_cpu_percent are null
   **And** collection continues without error

4. **Given** metrics are collected
   **When** the ring buffer is at capacity (default 1 hour at 10s intervals = 360 samples)
   **Then** the oldest samples are evicted (FIFO)

5. **Given** the collection interval is configurable
   **When** `VS_METRICS_INTERVAL` is set
   **Then** metrics are collected at the specified interval

## Tasks / Subtasks

- [x] Task 1: Add psutil dependency + create MetricsSnapshot model + tests (AC: 1, 2, 3)
  - [x] Subtask 1.1: Add `psutil` to pyproject.toml via `uv add psutil`
  - [x] Subtask 1.2: Create `api/src/vintagestory_api/models/metrics.py` with MetricsSnapshot dataclass
  - [x] Subtask 1.3: Write tests for MetricsSnapshot (frozen, nullable game fields)

- [x] Task 2: Implement MetricsBuffer ring buffer + tests (AC: 4)
  - [x] Subtask 2.1: Create MetricsBuffer class in `services/metrics.py` using `collections.deque(maxlen=N)`
  - [x] Subtask 2.2: Implement `append()`, `get_all()`, `get_latest()`, `__len__()` methods
  - [x] Subtask 2.3: Write tests for buffer capacity and FIFO eviction

- [x] Task 3: Implement MetricsService with psutil collection + tests (AC: 1, 2, 3)
  - [x] Subtask 3.1: Create MetricsService class with `collect()` method
  - [x] Subtask 3.2: Implement `_get_api_metrics()` using `psutil.Process()`
  - [x] Subtask 3.3: Implement `_get_game_server_pid()` using ServerService._process
  - [x] Subtask 3.4: Implement graceful degradation when game server not running (return None)
  - [x] Subtask 3.5: Add singleton getter `get_metrics_service()`
  - [x] Subtask 3.6: Write tests with mocked psutil and ServerService

- [x] Task 4: Add metrics_collection_interval to ApiSettingsService + tests (AC: 5)
  - [x] Subtask 4.1: Add `metrics_collection_interval: int = 10` to ApiSettings model
  - [x] Subtask 4.2: Update api-settings.json.example with new field (N/A - file doesn't exist)
  - [x] Subtask 4.3: Write test for default value and custom override

- [x] Task 5: Create metrics_collection job + register in jobs/__init__.py + tests (AC: 1, 5)
  - [x] Subtask 5.1: Create `api/src/vintagestory_api/jobs/metrics_collection.py`
  - [x] Subtask 5.2: Implement `collect_metrics()` async function with `@safe_job` decorator
  - [x] Subtask 5.3: Register job in `register_default_jobs()` when interval > 0
  - [x] Subtask 5.4: Write tests for job execution and interval configuration

## Dev Notes

### Technical Decisions (from Story 12.1)

All technical decisions are documented in [epic-12-dashboard-metrics.md](_bmad-output/planning-artifacts/architecture/epic-12-dashboard-metrics.md).

**ADR-E12-001: Use psutil for process metrics**
- Well-maintained library (10K+ stars, regular releases)
- Cross-platform (Linux, macOS, Windows)
- Fast operations (~1ms) - no async wrapper needed

**ADR-E12-002: Game server PID discovery via ServerService._process**
- Direct access: `server_service._process.pid` when server is running
- Check: `_process is not None and _process.returncode is None`
- Graceful degradation: Return `None` for game metrics when not running

**ADR-E12-004: Ring buffer using collections.deque**
- Same pattern as ConsoleBuffer (proven in codebase)
- Default capacity: 360 samples (1 hour at 10s intervals)
- Thread-safe for single writer (APScheduler job) + multiple readers (API)

### psutil Usage Patterns

```python
import psutil

# Current process (API server)
process = psutil.Process()  # No PID = current process
memory = process.memory_info()
memory_rss_mb = memory.rss / (1024 * 1024)  # Resident Set Size
cpu_percent = process.cpu_percent(interval=None)  # Non-blocking

# External process (game server by PID)
try:
    game_process = psutil.Process(pid)
    game_memory = game_process.memory_info()
    # ... same pattern
except psutil.NoSuchProcess:
    # Process not running - return None
    pass
```

**CPU Percent Note:** First call returns `0.0` (baseline). Subsequent calls return delta since last call. Initialize at service startup for accurate readings.

### MetricsSnapshot Data Model

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class MetricsSnapshot:
    """Immutable metrics sample point."""
    timestamp: datetime
    # API server metrics
    api_memory_mb: float
    api_cpu_percent: float
    # Game server metrics (None if not running)
    game_memory_mb: float | None
    game_cpu_percent: float | None
```

### MetricsBuffer Pattern

Follow the existing ConsoleBuffer pattern in [console.py](api/src/vintagestory_api/services/console.py):

```python
from collections import deque

class MetricsBuffer:
    DEFAULT_CAPACITY = 360  # 1 hour at 10s intervals

    def __init__(self, capacity: int = DEFAULT_CAPACITY):
        self._buffer: deque[MetricsSnapshot] = deque(maxlen=capacity)

    def append(self, snapshot: MetricsSnapshot) -> None:
        self._buffer.append(snapshot)

    def get_all(self) -> list[MetricsSnapshot]:
        return list(self._buffer)

    def get_latest(self) -> MetricsSnapshot | None:
        return self._buffer[-1] if self._buffer else None
```

### Job Registration Pattern

Follow the existing pattern in [jobs/__init__.py](api/src/vintagestory_api/jobs/__init__.py):

```python
# In jobs/__init__.py - add to register_default_jobs()
if settings.metrics_collection_interval > 0:
    from vintagestory_api.jobs.metrics_collection import collect_metrics

    scheduler.add_interval_job(
        collect_metrics,
        seconds=settings.metrics_collection_interval,
        job_id="metrics_collection",
    )
```

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

**Test patterns to follow:**
- Use `pytest-mock` for mocking psutil and ServerService
- Test graceful degradation when game server not running
- Test ring buffer eviction with small capacity
- Test job decorator with simulated exceptions

**Example test structure:**
```python
# tests/test_metrics.py
class TestMetricsSnapshot:
    def test_frozen_dataclass(self): ...
    def test_nullable_game_fields(self): ...

class TestMetricsBuffer:
    def test_append_and_get_all(self): ...
    def test_fifo_eviction_at_capacity(self): ...
    def test_get_latest_empty_buffer(self): ...

class TestMetricsService:
    def test_collect_with_game_server_running(self, mocker): ...
    def test_collect_without_game_server(self, mocker): ...
    def test_graceful_degradation_on_psutil_error(self, mocker): ...
```

### File Structure

Files to create/modify:
- `api/src/vintagestory_api/models/metrics.py` (NEW)
- `api/src/vintagestory_api/services/metrics.py` (NEW)
- `api/src/vintagestory_api/jobs/metrics_collection.py` (NEW)
- `api/src/vintagestory_api/jobs/__init__.py` (MODIFY - add job registration)
- `api/src/vintagestory_api/models/api_settings.py` (MODIFY - add interval setting)
- `api/tests/test_metrics.py` (NEW)
- `api/tests/test_metrics_job.py` (NEW)
- `api/example-config/api-settings.json.example` (MODIFY - add interval)

### Security Requirements

**Follow patterns in `project-context.md` → Security Patterns section:**

- No sensitive data in metrics (no player names, no API keys)
- Metrics are operational data - no DEBUG mode gating needed
- Admin-only access will be enforced in Story 12.3 (API layer)

### Development Commands

Use `just` for all development tasks:
- `just test` - Run all tests
- `just test-api` - Run API tests only
- `just test-api -k "metrics"` - Run metrics-related tests
- `just check` - Full validation (lint + typecheck + test)
- `just lint` - Run all linters

### Existing Service Patterns to Follow

**Service singleton pattern** (see [scheduler.py](api/src/vintagestory_api/services/scheduler.py:224)):
```python
_metrics_service: MetricsService | None = None

def get_metrics_service() -> MetricsService:
    global _metrics_service
    if _metrics_service is None:
        _metrics_service = MetricsService()
    return _metrics_service
```

**Job decorator** (see [base.py](api/src/vintagestory_api/jobs/base.py)):
```python
@safe_job("metrics_collection")
async def collect_metrics() -> None:
    metrics_service = get_metrics_service()
    metrics_service.collect()
```

### Accessing ServerService for PID

```python
from vintagestory_api.services.server import get_server_service

def _get_game_server_pid(self) -> int | None:
    server_service = get_server_service()

    # Check if process exists and is running
    if (server_service._process is not None and
        server_service._process.returncode is None):
        return server_service._process.pid

    return None
```

### Previous Story Intelligence (Story 12.1)

From [12-1-epic-12-technical-preparation.md](_bmad-output/implementation-artifacts/12-1-epic-12-technical-preparation.md):

1. **psutil research completed** - Use `psutil.Process()` for current process, `psutil.Process(pid)` for game server
2. **Charting library selected** - Recharts (for Story 12.5)
3. **Ring buffer design approved** - `collections.deque` with `maxlen=360`
4. **Player count deferred** - Too complex for Epic 12

### References

- `project-context.md` - Critical implementation rules and patterns
- [Source: _bmad-output/planning-artifacts/epics.md#Story 12.2] - Epic requirements
- [Source: _bmad-output/planning-artifacts/architecture/epic-12-dashboard-metrics.md] - Technical decisions
- [Source: api/src/vintagestory_api/services/console.py] - Ring buffer pattern
- [Source: api/src/vintagestory_api/jobs/base.py] - Job decorator pattern
- [Source: api/src/vintagestory_api/jobs/__init__.py] - Job registration pattern

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- Task 1: Added psutil 7.2.1 dependency, created MetricsSnapshot frozen dataclass with nullable game server fields, wrote 5 unit tests
- Task 2: Implemented MetricsBuffer ring buffer with deque(maxlen=360), FIFO eviction, added 8 unit tests
- Task 3: Implemented MetricsService with collect(), _get_api_metrics(), _get_game_server_pid(), graceful degradation, singleton pattern, added 11 unit tests
- Task 4: Added metrics_collection_interval to ApiSettings (default 10s), scheduler callback support, 3 new tests
- Task 5: Created metrics_collection job with @safe_job, registered in jobs/__init__.py, wrote 4 registration tests + 8 execution tests

### File List

- api/pyproject.toml (MODIFIED - added psutil dependency)
- api/uv.lock (MODIFIED - updated lockfile)
- api/src/vintagestory_api/models/metrics.py (NEW - MetricsSnapshot dataclass)
- api/src/vintagestory_api/services/metrics.py (NEW - MetricsBuffer, MetricsService classes)
- api/src/vintagestory_api/services/api_settings.py (MODIFIED - added metrics_collection_interval)
- api/src/vintagestory_api/jobs/metrics_collection.py (NEW - collect_metrics job)
- api/src/vintagestory_api/jobs/__init__.py (MODIFIED - register metrics_collection job)
- api/tests/test_metrics.py (NEW/MODIFIED - model, buffer, service tests)
- api/tests/test_metrics_job.py (NEW - job execution tests)
- api/tests/test_api_settings.py (MODIFIED - added metrics interval tests)
- api/tests/test_jobs_registration.py (MODIFIED - added metrics job registration tests)

## Review Follow-ups (AI)

- [x] [AI-Review][HIGH] Create api/example-config/api-settings.json.example with metrics_collection_interval [story:203-204]
  - **Resolution:** N/A - This project doesn't use example config files for api-settings. Settings are runtime-configurable via API and stored in state directory. Subtask 4.2 was already marked N/A during implementation.
- [x] [AI-Review][HIGH] File tracking issue for pyright private API suppressions or add public accessor to ServerService [services/metrics.py:192-195]
  - **Resolution:** Added to polish backlog as API-032. ADR-E12-002 documents the current pattern as intentional.
- [x] [AI-Review][HIGH] Lazy-load psutil.Process() in MetricsService to defer initialization [services/metrics.py:117-120]
  - **Resolution:** Implemented lazy initialization via `_get_api_process()` method. Process handle and CPU baseline are now created on first `collect()` call.
- [x] [AI-Review][MEDIUM] Add integration test for game server crash during metrics collection [test_metrics_job.py]
  - **Resolution:** Added `test_game_server_crash_during_collection()` test that simulates NoSuchProcess and verifies graceful degradation.
- [x] [AI-Review][LOW] Add single-writer thread-safety guarantee note to MetricsBuffer docstring [services/metrics.py:19-23]
  - **Resolution:** Already documented at lines 26-27: "Thread-safe for single writer (APScheduler job) + multiple readers (API)."

