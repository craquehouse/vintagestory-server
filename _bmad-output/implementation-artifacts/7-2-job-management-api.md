# Story 7.2: Job Management API

Status: in-progress

## Story

As an **administrator**,
I want **to view and manage scheduled jobs through the API**,
So that **I can monitor background task status**.

## Acceptance Criteria

1. **Given** I call `GET /api/v1alpha1/jobs` as Admin, **When** jobs are registered, **Then** I receive a list of jobs with: id, next_run_time, trigger type (interval/cron), and trigger details.

2. **Given** I call `DELETE /api/v1alpha1/jobs/{job_id}` as Admin, **When** the job exists, **Then** the job is removed from the scheduler **And** the response confirms deletion.

3. **Given** I call `DELETE /api/v1alpha1/jobs/{job_id}` as Admin, **When** the job does not exist, **Then** I receive a 404 Not Found error with code `JOB_NOT_FOUND`.

4. **Given** I am authenticated as Monitor, **When** I call `GET /api/v1alpha1/jobs`, **Then** I receive a 403 Forbidden (job management is Admin-only).

5. **Given** I am authenticated as Monitor, **When** I call `DELETE /api/v1alpha1/jobs/{job_id}`, **Then** I receive a 403 Forbidden.

## Tasks / Subtasks

<!--
CRITICAL TASK STRUCTURE RULES:
1. Each functional task MUST include "+ tests" in its name
2. Do NOT create separate "Write tests" tasks at the end
3. A task is NOT complete until its tests pass
4. Tests verify the specific AC listed for that task
-->

- [x] Task 1: Create job models and error codes + tests (AC: 1, 3)
  - [x] Subtask 1.1: Add `JOB_NOT_FOUND` error code to `models/errors.py`
  - [x] Subtask 1.2: Create `models/jobs.py` with `JobInfo` Pydantic model
  - [x] Subtask 1.3: Implement `job_to_info()` helper to serialize APScheduler Job to JobInfo
  - [x] Subtask 1.4: Write unit tests for job serialization (interval and cron triggers)

- [x] Task 2: Create /jobs router with list endpoint + tests (AC: 1, 4)
  - [x] Subtask 2.1: Create `routers/jobs.py` with APIRouter (prefix="/jobs", tags=["Jobs"])
  - [x] Subtask 2.2: Implement `GET /` endpoint returning list of JobInfo
  - [x] Subtask 2.3: Add `RequireAdmin` dependency for authorization
  - [x] Subtask 2.4: Register router in `main.py` under api_v1
  - [x] Subtask 2.5: Write tests for list endpoint (Admin allowed, Monitor forbidden)

- [x] Task 3: Add delete endpoint + tests (AC: 2, 3, 5)
  - [x] Subtask 3.1: Implement `DELETE /{job_id}` endpoint
  - [x] Subtask 3.2: Handle `JobLookupError` and return 404 with `JOB_NOT_FOUND`
  - [x] Subtask 3.3: Return success response confirming deletion
  - [x] Subtask 3.4: Write tests for delete endpoint (success, not found, forbidden)

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Do not batch tests into a separate "Write tests" task at the end
- Run `just test-api` to verify all tests pass before marking task complete

**Test Files to Create:**
- `api/tests/test_jobs.py` - Router tests for job API endpoints
- `api/tests/models/test_jobs.py` - Unit tests for job model serialization

### Security Considerations

**Admin-only access:** All job management endpoints require Admin role.

- Use `RequireAdmin` dependency from `middleware.permissions` (same pattern as server router)
- Monitor role should receive 403 Forbidden on all endpoints
- No sensitive data exposed in job info (job IDs and schedules only)

### Development Commands

Use `just` for all development tasks:
- `just test-api` - Run all API tests
- `just test-api -k "jobs"` - Run job tests only
- `just test-api tests/test_jobs.py -xvs` - Run specific file, verbose
- `just check` - Full validation (lint + typecheck + test)
- `just lint-api` - Run API linter

### Architecture & Patterns

**Source tree components to create/modify:**
- `api/src/vintagestory_api/models/jobs.py` (NEW)
- `api/src/vintagestory_api/models/errors.py` (MODIFY - add JOB_NOT_FOUND)
- `api/src/vintagestory_api/routers/jobs.py` (NEW)
- `api/src/vintagestory_api/main.py` (MODIFY - register router)
- `api/tests/test_jobs.py` (NEW)
- `api/tests/models/test_jobs.py` (NEW)

### JobInfo Model Design

```python
# api/src/vintagestory_api/models/jobs.py
from datetime import datetime
from pydantic import BaseModel

class JobInfo(BaseModel):
    """Serialized job information for API responses."""

    id: str
    next_run_time: datetime | None
    trigger_type: str  # "interval" or "cron"
    trigger_details: str  # e.g., "every 3600 seconds" or "0 */6 * * *"
```

### Job Serialization Pattern

APScheduler Job objects need to be serialized to JobInfo. The trigger type and details can be extracted from the job's trigger:

```python
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

def job_to_info(job: Job) -> JobInfo:
    """Convert APScheduler Job to API-friendly JobInfo."""
    trigger = job.trigger

    if isinstance(trigger, IntervalTrigger):
        trigger_type = "interval"
        # IntervalTrigger stores interval as timedelta
        trigger_details = f"every {int(trigger.interval.total_seconds())} seconds"
    elif isinstance(trigger, CronTrigger):
        trigger_type = "cron"
        # CronTrigger can be converted back to cron expression
        trigger_details = str(trigger)
    else:
        trigger_type = "unknown"
        trigger_details = str(trigger)

    return JobInfo(
        id=job.id,
        next_run_time=job.next_run_time,
        trigger_type=trigger_type,
        trigger_details=trigger_details,
    )
```

### Router Pattern (following server.py)

```python
# api/src/vintagestory_api/routers/jobs.py
from fastapi import APIRouter, Depends, HTTPException

from vintagestory_api.main import get_scheduler_service
from vintagestory_api.middleware.permissions import RequireAdmin
from vintagestory_api.models.errors import ErrorCode
from vintagestory_api.models.jobs import JobInfo, job_to_info
from vintagestory_api.models.responses import ApiResponse
from vintagestory_api.services.scheduler import SchedulerService

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("", response_model=ApiResponse)
async def list_jobs(
    _: RequireAdmin,
    scheduler: SchedulerService = Depends(get_scheduler_service),
) -> ApiResponse:
    """List all scheduled jobs.

    Returns job information including ID, next run time, and trigger details.
    Requires Admin role.
    """
    jobs = scheduler.get_jobs()
    job_list = [job_to_info(job).model_dump() for job in jobs]
    return ApiResponse(status="ok", data={"jobs": job_list})


@router.delete("/{job_id}", response_model=ApiResponse)
async def delete_job(
    job_id: str,
    _: RequireAdmin,
    scheduler: SchedulerService = Depends(get_scheduler_service),
) -> ApiResponse:
    """Delete a scheduled job.

    Removes the job from the scheduler. Requires Admin role.
    """
    from apscheduler.jobstores.base import JobLookupError

    try:
        scheduler.remove_job(job_id)
        return ApiResponse(status="ok", data={"message": f"Job '{job_id}' deleted"})
    except JobLookupError:
        raise HTTPException(
            status_code=404,
            detail={
                "code": ErrorCode.JOB_NOT_FOUND,
                "message": f"Job '{job_id}' not found",
            },
        )
```

### Router Registration Pattern

In `main.py`, add the jobs router import and registration:

```python
# Add to imports
from vintagestory_api.routers import auth, config, console, health, jobs, mods, server, test_rbac

# Add to api_v1 router includes (around line 170)
api_v1.include_router(jobs.router)
```

### Error Code Addition

Add to `models/errors.py`:

```python
# Jobs (Epic 7)
JOB_NOT_FOUND = "JOB_NOT_FOUND"
```

### APScheduler JobLookupError

The `remove_job()` method raises `JobLookupError` when the job doesn't exist. Import from:

```python
from apscheduler.jobstores.base import JobLookupError
```

### Test Fixtures and Patterns

Tests should follow the existing patterns in the codebase:

```python
# api/tests/test_jobs.py
import pytest
from fastapi.testclient import TestClient

from vintagestory_api.main import app


@pytest.fixture
def client():
    """Test client with app lifespan (starts scheduler)."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def admin_headers():
    """Admin authentication headers."""
    return {"X-API-Key": "admin-key"}  # Match test config


@pytest.fixture
def monitor_headers():
    """Monitor authentication headers."""
    return {"X-API-Key": "monitor-key"}  # Match test config


def test_list_jobs_admin_success(client, admin_headers):
    """Admin can list scheduled jobs."""
    response = client.get("/api/v1alpha1/jobs", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "jobs" in data["data"]


def test_list_jobs_monitor_forbidden(client, monitor_headers):
    """Monitor cannot list scheduled jobs."""
    response = client.get("/api/v1alpha1/jobs", headers=monitor_headers)
    assert response.status_code == 403
```

### Previous Story Intelligence (7-1)

**From Story 7.1 (SchedulerService):**
- SchedulerService is initialized in `main.py` lifespan
- `get_scheduler_service()` function provides dependency injection
- Methods available: `get_jobs()`, `get_job(job_id)`, `remove_job(job_id)`
- `remove_job()` raises `JobLookupError` if job doesn't exist
- 853 existing API tests pass

**Files from 7-1:**
- `api/src/vintagestory_api/services/scheduler.py` - SchedulerService (195 lines)
- `api/src/vintagestory_api/main.py` - lifespan integration, `get_scheduler_service()`
- `api/tests/test_scheduler.py` - scheduler tests (415 lines)

### Git Workflow for This Story

```bash
# Create feature branch
git checkout -b story/7-2-job-management-api

# Task-level commits
git commit -m "feat(story-7.2/task-1): add job models and error codes"
git commit -m "feat(story-7.2/task-2): create jobs router with list endpoint"
git commit -m "feat(story-7.2/task-3): add delete job endpoint"

# Push and create PR
git push -u origin story/7-2-job-management-api
gh pr create --title "Story 7.2: Job Management API" --body "..."
```

### References

- `project-context.md` - Critical implementation rules and patterns
- `_bmad-output/planning-artifacts/architecture.md` - Epic 7 APScheduler patterns
- `_bmad-output/planning-artifacts/epics.md` - Story requirements [Source: epics.md#Story 7.2]
- `_bmad-output/implementation-artifacts/7-1-scheduler-service.md` - SchedulerService implementation
- [APScheduler 3.x Documentation](https://apscheduler.readthedocs.io/en/3.x/)
