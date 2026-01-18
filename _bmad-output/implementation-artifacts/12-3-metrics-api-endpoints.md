# Story 12.3: Metrics API Endpoints

Status: review

## Story

As a **frontend developer**,
I want **API endpoints to retrieve current and historical metrics**,
So that **the dashboard can display real-time and chart data**.

## Acceptance Criteria

1. **Given** I call `GET /api/v1alpha1/metrics/current` as Admin
   **When** metrics have been collected
   **Then** I receive the latest MetricsSnapshot
   **And** response includes: timestamp, api_memory_mb, api_cpu_percent, game_memory_mb, game_cpu_percent

2. **Given** I call `GET /api/v1alpha1/metrics/history` as Admin
   **When** I don't specify parameters
   **Then** I receive all available historical metrics (up to buffer size)

3. **Given** I call `GET /api/v1alpha1/metrics/history?minutes=60`
   **When** I specify a time range
   **Then** I receive metrics from the last 60 minutes only

4. **Given** I am authenticated as Monitor
   **When** I call metrics endpoints
   **Then** I receive a 403 Forbidden (metrics are Admin-only)

5. **Given** no metrics have been collected yet
   **When** I call metrics endpoints
   **Then** I receive an empty response (not an error)

## Tasks / Subtasks

- [x] Task 1: Create metrics router with /current endpoint + tests (AC: 1, 5)
  - [x] Subtask 1.1: Create `api/src/vintagestory_api/routers/metrics.py` with router setup
  - [x] Subtask 1.2: Implement `GET /metrics/current` endpoint returning latest snapshot
  - [x] Subtask 1.3: Add Admin-only authorization using `require_admin` dependency
  - [x] Subtask 1.4: Handle empty buffer case (return null for current, empty list for history)
  - [x] Subtask 1.5: Create Pydantic response models in `models/metrics.py`
  - [x] Subtask 1.6: Write tests for /current endpoint (with data, empty, auth)

- [x] Task 2: Implement /history endpoint with time filtering + tests (AC: 2, 3)
  - [x] Subtask 2.1: Implement `GET /metrics/history` endpoint returning all snapshots
  - [x] Subtask 2.2: Add optional `minutes` query parameter for time filtering
  - [x] Subtask 2.3: Implement time filtering logic in MetricsService or router
  - [x] Subtask 2.4: Write tests for /history endpoint (full history, time filtered)

- [x] Task 3: Add authorization tests and register router + tests (AC: 4)
  - [x] Subtask 3.1: Write tests for Monitor role receiving 403 on both endpoints
  - [x] Subtask 3.2: Register metrics router in `main.py`
  - [x] Subtask 3.3: Add OpenAPI documentation (summary, description, response models)
  - [x] Subtask 3.4: Run full test suite to verify integration

## Dev Notes

### Technical Decisions (from Story 12.1)

All technical decisions are documented in [epic-12-dashboard-metrics.md](_bmad-output/planning-artifacts/architecture/epic-12-dashboard-metrics.md).

**Key ADRs:**
- **ADR-E12-001:** Use psutil for process metrics (implemented in 12.2)
- **ADR-E12-002:** Game server PID via ServerService._process (implemented in 12.2)
- **ADR-E12-004:** Ring buffer using collections.deque (implemented in 12.2)

### Existing Infrastructure (from Story 12.2)

**MetricsService** (`api/src/vintagestory_api/services/metrics.py`):
```python
from vintagestory_api.services.metrics import get_metrics_service

# Get singleton service
metrics_service = get_metrics_service()

# Get latest snapshot
latest: MetricsSnapshot | None = metrics_service.buffer.get_latest()

# Get all snapshots (oldest first)
all_snapshots: list[MetricsSnapshot] = metrics_service.buffer.get_all()
```

**MetricsSnapshot** (`api/src/vintagestory_api/models/metrics.py`):
```python
@dataclass(frozen=True)
class MetricsSnapshot:
    timestamp: datetime
    api_memory_mb: float
    api_cpu_percent: float
    game_memory_mb: float | None  # None if game server not running
    game_cpu_percent: float | None
```

### API Response Format

Follow the standard envelope pattern used throughout the codebase:

```python
from vintagestory_api.models.responses import ApiResponse

return ApiResponse(status="ok", data=response_data.model_dump(mode="json"))
```

**Expected Response for `/metrics/current`:**
```json
{
  "status": "ok",
  "data": {
    "timestamp": "2026-01-17T10:30:00Z",
    "apiMemoryMb": 128.5,
    "apiCpuPercent": 2.3,
    "gameMemoryMb": 512.0,
    "gameCpuPercent": 15.2
  }
}
```

**Expected Response for `/metrics/history`:**
```json
{
  "status": "ok",
  "data": {
    "metrics": [
      {
        "timestamp": "2026-01-17T09:30:00Z",
        "apiMemoryMb": 125.2,
        "apiCpuPercent": 1.8,
        "gameMemoryMb": 508.3,
        "gameCpuPercent": 12.1
      }
    ],
    "count": 360
  }
}
```

**Empty Buffer Response for `/metrics/current`:**
```json
{
  "status": "ok",
  "data": null
}
```

### Pydantic Response Models

Create in `models/metrics.py` (extend existing file):

```python
from pydantic import BaseModel, Field
from datetime import datetime

class MetricsSnapshotResponse(BaseModel):
    """Single metrics snapshot for API response."""
    timestamp: datetime
    api_memory_mb: float = Field(alias="apiMemoryMb")
    api_cpu_percent: float = Field(alias="apiCpuPercent")
    game_memory_mb: float | None = Field(alias="gameMemoryMb")
    game_cpu_percent: float | None = Field(alias="gameCpuPercent")

    model_config = {"populate_by_name": True}

    @classmethod
    def from_snapshot(cls, snapshot: MetricsSnapshot) -> "MetricsSnapshotResponse":
        return cls(
            timestamp=snapshot.timestamp,
            api_memory_mb=snapshot.api_memory_mb,
            api_cpu_percent=snapshot.api_cpu_percent,
            game_memory_mb=snapshot.game_memory_mb,
            game_cpu_percent=snapshot.game_cpu_percent,
        )

class MetricsHistoryResponse(BaseModel):
    """Historical metrics response."""
    metrics: list[MetricsSnapshotResponse]
    count: int
```

### Time Filtering Logic

For the `minutes` query parameter, filter snapshots by timestamp:

```python
from datetime import datetime, timedelta, UTC

def get_filtered_history(minutes: int | None = None) -> list[MetricsSnapshot]:
    """Get historical metrics, optionally filtered by time range."""
    metrics_service = get_metrics_service()
    all_snapshots = metrics_service.buffer.get_all()

    if minutes is None:
        return all_snapshots

    cutoff = datetime.now(UTC) - timedelta(minutes=minutes)
    return [s for s in all_snapshots if s.timestamp >= cutoff]
```

### Authorization Pattern

Use `require_admin` dependency for Admin-only access (AC: 4):

```python
from vintagestory_api.middleware.permissions import require_admin

@router.get("/current")
async def get_current_metrics(
    _role: str = Depends(require_admin),  # Admin-only
) -> ApiResponse:
    ...
```

### Router Registration

Add to `main.py` following existing pattern:

```python
from vintagestory_api.routers import metrics

# In api_v1 router setup
api_v1.include_router(metrics.router)
```

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

**Test file:** `api/tests/test_metrics_api.py`

**Test patterns to follow:**
```python
import pytest
from datetime import datetime, UTC
from unittest.mock import MagicMock, patch

from vintagestory_api.models.metrics import MetricsSnapshot

class TestMetricsCurrentEndpoint:
    """Tests for GET /metrics/current."""

    @pytest.fixture
    def mock_metrics_service(self):
        """Create a mock metrics service with test data."""
        service = MagicMock()
        service.buffer.get_latest.return_value = MetricsSnapshot(
            timestamp=datetime.now(UTC),
            api_memory_mb=100.0,
            api_cpu_percent=5.0,
            game_memory_mb=200.0,
            game_cpu_percent=10.0,
        )
        return service

    def test_current_returns_latest_snapshot(self, client, mock_metrics_service):
        """AC 1: Returns latest MetricsSnapshot as Admin."""
        with patch("vintagestory_api.routers.metrics.get_metrics_service",
                   return_value=mock_metrics_service):
            response = client.get(
                "/api/v1alpha1/metrics/current",
                headers={"X-API-Key": "test-admin-key"}
            )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["apiMemoryMb"] == 100.0
        assert data["gameCpuPercent"] == 10.0

    def test_current_returns_null_when_empty(self, client, mock_metrics_service):
        """AC 5: Returns null when no metrics collected."""
        mock_metrics_service.buffer.get_latest.return_value = None
        # ... test implementation

    def test_current_requires_admin(self, client):
        """AC 4: Monitor role receives 403."""
        response = client.get(
            "/api/v1alpha1/metrics/current",
            headers={"X-API-Key": "test-monitor-key"}
        )
        assert response.status_code == 403

class TestMetricsHistoryEndpoint:
    """Tests for GET /metrics/history."""

    def test_history_returns_all_metrics(self, client, mock_metrics_service):
        """AC 2: Returns all available metrics."""
        # ... test implementation

    def test_history_filters_by_minutes(self, client, mock_metrics_service):
        """AC 3: Filters by time range when minutes specified."""
        # ... test implementation
```

### Security Requirements

**Follow patterns in `project-context.md` → Security Patterns section:**

- Admin-only access (metrics are operational data, not for Monitor role)
- No sensitive data in metrics (no player names, no API keys)
- Standard API authentication via X-API-Key header

### Development Commands

Use `just` for all development tasks:
- `just test` - Run all tests
- `just test-api` - Run API tests only
- `just test-api -k "metrics"` - Run metrics-related tests
- `just test-api tests/test_metrics_api.py -xvs` - Run specific file, verbose
- `just check` - Full validation (lint + typecheck + test)
- `just lint` - Run all linters

### Previous Story Intelligence (Story 12.2)

From [12-2-metrics-collection-service.md](_bmad-output/implementation-artifacts/12-2-metrics-collection-service.md):

1. **MetricsService fully implemented** - Singleton pattern, collect() method, buffer access
2. **MetricsBuffer tested** - FIFO eviction, get_all(), get_latest() working
3. **MetricsSnapshot dataclass** - frozen=True, nullable game fields
4. **Job registered** - metrics_collection job runs every 10 seconds by default
5. **Test patterns established** - Use pytest-mock, mock psutil and ServerService

**Review follow-ups from 12.2 (all resolved):**
- Lazy-load psutil.Process() - Implemented via `_get_api_process()`
- Integration test for crash during collection - Added
- Thread-safety documented in docstrings

### Architecture & Patterns

**Router pattern** (follow versions.py):
```python
from fastapi import APIRouter, Query
from vintagestory_api.models.responses import ApiResponse

router = APIRouter(prefix="/metrics", tags=["Metrics"])
```

**Response model conversion:**
- Use `.model_dump(mode="json")` for Pydantic → dict
- Apply camelCase aliases for frontend consumption

### Project Structure Notes

Files to create/modify:
- `api/src/vintagestory_api/routers/metrics.py` (NEW)
- `api/src/vintagestory_api/models/metrics.py` (MODIFY - add response models)
- `api/src/vintagestory_api/main.py` (MODIFY - register router)
- `api/tests/test_metrics_api.py` (NEW)

### References

- `project-context.md` - Critical implementation rules and patterns
- [Source: _bmad-output/planning-artifacts/epics.md#Story 12.3] - Epic requirements
- [Source: _bmad-output/planning-artifacts/architecture/epic-12-dashboard-metrics.md] - Technical decisions
- [Source: api/src/vintagestory_api/services/metrics.py] - MetricsService implementation
- [Source: api/src/vintagestory_api/routers/versions.py] - Router pattern example
- [Source: api/src/vintagestory_api/middleware/permissions.py] - require_admin dependency

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- ✅ Task 1, 2, 3: All implemented together - metrics router with /current and /history endpoints
- Created MetricsSnapshotResponse and MetricsHistoryResponse Pydantic models with camelCase aliases
- Used RequireAdmin type alias for cleaner Admin-only authorization
- Time filtering implemented via `_filter_by_minutes()` helper function
- Minutes parameter validated with ge=1, le=1440 (max 24 hours)
- All 15 API tests pass, full suite (1293 tests) passes with no regressions

### File List

- api/src/vintagestory_api/routers/metrics.py (NEW)
- api/src/vintagestory_api/models/metrics.py (MODIFIED - added MetricsSnapshotResponse, MetricsHistoryResponse)
- api/src/vintagestory_api/main.py (MODIFIED - imported and registered metrics router)
- api/tests/test_metrics_api.py (NEW)

### Change Log

- 2026-01-17: Implemented metrics API endpoints (AC 1-5), all tests passing

