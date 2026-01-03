# Story 7.3: Scheduler Health

Status: review

## Story

As an **operator**,
I want **scheduler status included in health checks**,
So that **I can monitor the background task system**.

## Acceptance Criteria

1. **Given** I call `GET /healthz`, **When** the scheduler is running, **Then** the response includes `scheduler: { status: "running", job_count: N }`.

2. **Given** the scheduler has failed to start, **When** I call `/healthz`, **Then** the response includes `scheduler: { status: "stopped" }`.

3. **Given** the scheduler is running with registered jobs, **When** I call `/healthz`, **Then** the `job_count` reflects the actual number of scheduled jobs.

## Tasks / Subtasks

<!--
🚨 CRITICAL TASK STRUCTURE RULES:
1. Each functional task MUST include "+ tests" in its name
2. Do NOT create separate "Write tests" tasks at the end
3. A task is NOT complete until its tests pass
4. Tests verify the specific AC listed for that task

✅ CORRECT PATTERN:
- [ ] Task 1: Implement feature + tests (AC: 1, 2)
  - [ ] Subtask 1.1: Implementation detail
  - [ ] Subtask 1.2: Write tests for feature

❌ WRONG PATTERN (tests batched at end):
- [ ] Task 1: Implement feature (AC: 1, 2)
- [ ] Task 2: Write all tests  <- NEVER DO THIS
-->

- [x] Task 1: Add SchedulerHealthData model + tests (AC: 1, 2, 3)
  - [x] Subtask 1.1: Add `SchedulerHealthData` Pydantic model in `models/responses.py`
  - [x] Subtask 1.2: Add `scheduler` field to `HealthData` model (optional field)
  - [x] Subtask 1.3: Write unit tests for model serialization

- [x] Task 2: Update health router to include scheduler status + tests (AC: 1, 2, 3)
  - [x] Subtask 2.1: Import `get_scheduler_service` in health router
  - [x] Subtask 2.2: Add scheduler status retrieval to `/healthz` endpoint
  - [x] Subtask 2.3: Handle case when scheduler service not initialized (status: "stopped")
  - [x] Subtask 2.4: Write tests for scheduler health in `/healthz` response
  - [x] Subtask 2.5: Write tests for scheduler stopped/unavailable scenarios

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Do not batch tests into a separate "Write tests" task at the end
- Run `just test-api` to verify all tests pass before marking task complete

**Test Files to Modify/Create:**
- `api/tests/test_health.py` - Add tests for scheduler status in health endpoints

### Security Considerations

- Health endpoints remain unauthenticated (per K8s convention)
- No sensitive data exposed in scheduler status (only status and job count)
- Follow existing health endpoint patterns

### Development Commands

Use `just` for all development tasks:
- `just test-api` - Run all API tests
- `just test-api -k "health"` - Run health tests only
- `just test-api tests/test_health.py -xvs` - Run specific file, verbose
- `just check` - Full validation (lint + typecheck + test)
- `just lint-api` - Run API linter

### Architecture & Patterns

**Source tree components to modify:**
- `api/src/vintagestory_api/models/responses.py` (MODIFY - add SchedulerHealthData, update HealthData)
- `api/src/vintagestory_api/routers/health.py` (MODIFY - add scheduler status to /healthz)
- `api/tests/test_health.py` (MODIFY - add scheduler health tests)

### SchedulerHealthData Model Design

Add to `models/responses.py`:

```python
class SchedulerHealthData(BaseModel):
    """Scheduler health check data."""

    status: Literal["running", "stopped"] = Field(
        description="Current scheduler status"
    )
    job_count: int = Field(
        default=0,
        description="Number of registered scheduled jobs"
    )
```

Update `HealthData` to include:

```python
class HealthData(BaseModel):
    """Health check response data."""

    api: str = "healthy"
    game_server: GameServerStatus
    game_server_version: str | None = ...
    game_server_uptime: int | None = ...
    game_server_pending_restart: bool = ...
    # Add new field:
    scheduler: SchedulerHealthData | None = Field(
        default=None,
        description="Scheduler service status. None if scheduler not available."
    )
```

### Health Router Integration

Update `/healthz` endpoint in `routers/health.py`:

```python
from vintagestory_api.main import get_scheduler_service
from vintagestory_api.models.responses import SchedulerHealthData

@router.get("/healthz", response_model=ApiResponse)
async def health_check() -> ApiResponse:
    # ... existing server status code ...

    # Get scheduler status - don't fail health checks if this errors
    try:
        scheduler = get_scheduler_service()
        scheduler_data = SchedulerHealthData(
            status="running" if scheduler.is_running else "stopped",
            job_count=len(scheduler.get_jobs())
        )
    except RuntimeError:
        # Scheduler not initialized
        scheduler_data = SchedulerHealthData(status="stopped", job_count=0)
    except Exception:
        # Unexpected error - default to stopped
        scheduler_data = SchedulerHealthData(status="stopped", job_count=0)

    return ApiResponse(
        status="ok",
        data=HealthData(
            api="healthy",
            game_server=game_server_status,
            game_server_version=server_status.version,
            game_server_uptime=server_status.uptime_seconds,
            game_server_pending_restart=pending_restart,
            scheduler=scheduler_data,  # Add scheduler status
        ).model_dump(),
    )
```

### Test Patterns

Follow existing patterns in `test_health.py`:

```python
class TestHealthzScheduler:
    """Tests for scheduler status in /healthz endpoint."""

    def test_healthz_includes_scheduler_status(self, client: TestClient) -> None:
        """Test that /healthz includes scheduler status."""
        response = client.get("/healthz")
        data = response.json()
        assert "scheduler" in data["data"]
        assert data["data"]["scheduler"]["status"] in ["running", "stopped"]

    def test_healthz_scheduler_running_status(self, client: TestClient) -> None:
        """Test that scheduler status is 'running' when scheduler is active."""
        # TestClient uses lifespan, so scheduler should be started
        response = client.get("/healthz")
        data = response.json()
        assert data["data"]["scheduler"]["status"] == "running"

    def test_healthz_includes_job_count(self, client: TestClient) -> None:
        """Test that scheduler includes job_count field."""
        response = client.get("/healthz")
        data = response.json()
        assert "job_count" in data["data"]["scheduler"]
        assert isinstance(data["data"]["scheduler"]["job_count"], int)
        assert data["data"]["scheduler"]["job_count"] >= 0

    def test_healthz_scheduler_stopped_when_unavailable(
        self, client: TestClient
    ) -> None:
        """Test that scheduler status is 'stopped' when scheduler unavailable."""
        with patch(
            "vintagestory_api.routers.health.get_scheduler_service",
            side_effect=RuntimeError("Scheduler not initialized"),
        ):
            response = client.get("/healthz")
            data = response.json()
            assert data["data"]["scheduler"]["status"] == "stopped"
            assert data["data"]["scheduler"]["job_count"] == 0
```

### Expected Response Format

After implementation, `/healthz` should return:

```json
{
  "status": "ok",
  "data": {
    "api": "healthy",
    "game_server": "not_installed",
    "game_server_version": null,
    "game_server_uptime": null,
    "game_server_pending_restart": false,
    "scheduler": {
      "status": "running",
      "job_count": 0
    }
  }
}
```

### Previous Story Intelligence (7-1 and 7-2)

**From Story 7.1 (SchedulerService):**
- `SchedulerService` initialized in `main.py` lifespan
- `get_scheduler_service()` returns the service or raises `RuntimeError` if not initialized
- `scheduler.is_running` property indicates if scheduler is active
- `scheduler.get_jobs()` returns list of registered jobs
- 26 scheduler tests in `test_scheduler.py`

**From Story 7.2 (Job Management API):**
- Jobs router at `/api/v1alpha1/jobs` provides job listing and deletion
- `JobInfo` model for serializing job data
- Admin-only access for job management
- 24 tests for job API

**Key files from previous stories:**
- `api/src/vintagestory_api/services/scheduler.py` (195 lines)
- `api/src/vintagestory_api/main.py` - lifespan with scheduler integration
- `api/src/vintagestory_api/routers/jobs.py` (80 lines)
- `api/tests/test_scheduler.py` (415 lines)
- `api/tests/test_jobs_router.py` (300 lines)

### Git Workflow for This Story

```bash
# Create feature branch
git checkout -b story/7-3-scheduler-health

# Task-level commits
git commit -m "feat(story-7.3/task-1): add SchedulerHealthData model"
git commit -m "feat(story-7.3/task-2): add scheduler status to health endpoint"

# Push and create PR
git push -u origin story/7-3-scheduler-health
gh pr create --title "Story 7.3: Scheduler Health" --body "..."
```

### Current Test Stats

From previous stories:
- 877 total API tests pass (as of 7-2 completion)
- All lint and typecheck pass
- Pre-existing typecheck warnings from APScheduler untyped package (tracked with TODO comments)

### Project Structure Notes

- Models in `models/` directory follow Pydantic patterns
- Health router at root level (`/healthz`, `/readyz`) - not versioned
- Follow existing error handling patterns (try/except with defaults)

### References

- `project-context.md` - Critical implementation rules and patterns
- `_bmad-output/planning-artifacts/architecture.md` - Epic 7 patterns
- `_bmad-output/planning-artifacts/epics.md` - Story requirements [Source: epics.md#Story 7.3]
- `_bmad-output/implementation-artifacts/7-1-scheduler-service.md` - SchedulerService patterns
- `_bmad-output/implementation-artifacts/7-2-job-management-api.md` - Job API patterns

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- Task 1 commit: 71317a8 - Add SchedulerHealthData model + tests
- Task 2 commit: e2eb142 - Add scheduler status to health endpoint

### Completion Notes List

- Task 1: Added SchedulerHealthData model with status (Literal["running", "stopped"]) and job_count fields. Added 5 model tests. All 882 tests pass.
- Task 2: Updated /healthz endpoint to include scheduler status. Used deferred import pattern to avoid circular imports. Added 8 tests for scheduler health integration. All 890 tests pass.

### File List

- `api/src/vintagestory_api/models/responses.py` - MODIFIED: Added SchedulerHealthData model, updated HealthData
- `api/src/vintagestory_api/routers/health.py` - MODIFIED: Added scheduler status to /healthz endpoint
- `api/tests/test_health.py` - MODIFIED: Added TestSchedulerHealthDataModel (5 tests) and TestHealthzScheduler (8 tests)

