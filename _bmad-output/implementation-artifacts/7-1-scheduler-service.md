# Story 7.1: SchedulerService

Status: done

## Story

As a **developer**,
I want **a scheduler service that manages periodic background tasks**,
So that **jobs can be added, removed, and monitored**.

## Acceptance Criteria

1. **Given** the API server starts, **When** the lifespan context initializes, **Then** the SchedulerService starts the AsyncIOScheduler and a log entry confirms "scheduler_started".

2. **Given** the API server shuts down, **When** the lifespan context exits, **Then** the SchedulerService stops the scheduler gracefully and running jobs complete before shutdown.

3. **Given** I need to add an interval job, **When** I call `scheduler.add_interval_job(func, seconds, job_id)`, **Then** the job is registered and will execute at the specified interval.

4. **Given** I need to add a cron job, **When** I call `scheduler.add_cron_job(func, cron_expression, job_id)`, **Then** the job is registered with the cron schedule.

## Tasks / Subtasks

<!--
CRITICAL TASK STRUCTURE RULES:
1. Each functional task MUST include "+ tests" in its name
2. Do NOT create separate "Write tests" tasks at the end
3. A task is NOT complete until its tests pass
4. Tests verify the specific AC listed for that task
-->

- [x] Task 1: Create SchedulerService class with core scheduler setup + tests (AC: 1, 2)
  - [x] Subtask 1.1: Create `api/src/vintagestory_api/services/scheduler.py`
  - [x] Subtask 1.2: Implement `SchedulerService.__init__()` with AsyncIOScheduler, MemoryJobStore, AsyncIOExecutor
  - [x] Subtask 1.3: Implement `start()` method with structured logging
  - [x] Subtask 1.4: Implement `shutdown(wait: bool = True)` method with graceful shutdown
  - [x] Subtask 1.5: Write unit tests for scheduler lifecycle (start, shutdown, is_running state)

- [x] Task 2: Implement add_interval_job and add_cron_job methods + tests (AC: 3, 4)
  - [x] Subtask 2.1: Implement `add_interval_job(func, seconds, job_id, **kwargs)` method
  - [x] Subtask 2.2: Implement `add_cron_job(func, cron_expr, job_id, **kwargs)` method
  - [x] Subtask 2.3: Implement `remove_job(job_id)` method
  - [x] Subtask 2.4: Implement `get_jobs()` method to list registered jobs
  - [x] Subtask 2.5: Write tests for job registration, execution, and removal

- [x] Task 3: Integrate SchedulerService with FastAPI lifespan + tests (AC: 1, 2)
  - [x] Subtask 3.1: Add scheduler_service global variable in main.py
  - [x] Subtask 3.2: Initialize and start scheduler in lifespan startup (after auto-start logic)
  - [x] Subtask 3.3: Shutdown scheduler in lifespan cleanup (before mod service close)
  - [x] Subtask 3.4: Add getter function `get_scheduler_service()` for dependency injection
  - [x] Subtask 3.5: Write integration tests verifying lifespan startup/shutdown

### Review Follow-ups (AI)
<!-- Created by adversarial code review workflow -->

- [x] [AI-Review][MEDIUM] Add TODO comment with tracking issue for APScheduler type suppressions (scheduler.py:21-26, 177-194)
- [x] [AI-Review][MEDIUM] Add TODO comment with tracking issue for APScheduler type suppressions in test file (test_scheduler.py:17, 120, 124, 249)
- [x] [AI-Review][LOW] Standardize pyright ignore style: change `# pyright: ignore[reportPrivateUsage]` to `# type: ignore` (test_scheduler.py:109)

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Do not batch tests into a separate "Write tests" task at the end
- Run `just test-api` to verify all tests pass before marking task complete

**Test Files to Create:**
- `api/tests/services/test_scheduler.py` - Unit tests for SchedulerService
- Consider mocking AsyncIOScheduler to avoid timing-dependent tests

### APScheduler Version & Patterns

**CRITICAL:** Use APScheduler v3.11.x patterns, NOT v4.x (v4 is still alpha).

**Correct imports (v3):**
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
```

**Wrong imports (v4 - DO NOT USE):**
```python
# DO NOT USE - v4 alpha patterns
from apscheduler import AsyncScheduler
from apscheduler.datastores.memory import MemoryDataStore
```

### SchedulerService Pattern (from architecture.md)

```python
# api/src/vintagestory_api/services/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
import structlog

logger = structlog.get_logger()

class SchedulerService:
    """Manages periodic background tasks using APScheduler."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler(
            jobstores={"default": MemoryJobStore()},
            executors={"default": AsyncIOExecutor()},
            job_defaults={
                "coalesce": True,  # Combine missed runs into one
                "max_instances": 1,  # Only one instance of each job
                "misfire_grace_time": 60,  # Allow 60s grace for misfires
            }
        )
        self._running = False

    def start(self):
        """Start the scheduler."""
        self.scheduler.start()
        self._running = True
        logger.info("scheduler_started")

    def shutdown(self, wait: bool = True):
        """Shutdown the scheduler gracefully."""
        self.scheduler.shutdown(wait=wait)
        self._running = False
        logger.info("scheduler_stopped")

    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running
```

### Job Defaults Rationale

| Setting | Value | Why |
|---------|-------|-----|
| `coalesce` | `True` | If scheduler misses multiple fire times (e.g., system busy), run once instead of catching up |
| `max_instances` | `1` | Prevent overlapping job executions if job takes longer than interval |
| `misfire_grace_time` | `60` | Allow up to 60s late execution before considering job "misfired" |

### FastAPI Lifespan Integration

**Location:** `api/src/vintagestory_api/main.py`

```python
# Add near top of file
from vintagestory_api.services.scheduler import SchedulerService

scheduler_service: SchedulerService | None = None

def get_scheduler_service() -> SchedulerService:
    """Get the scheduler service instance."""
    if scheduler_service is None:
        raise RuntimeError("Scheduler service not initialized")
    return scheduler_service

# In lifespan function, after auto-start logic:
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global scheduler_service

    # ... existing startup code ...

    # Initialize scheduler (after auto-start logic, before yield)
    scheduler_service = SchedulerService()
    scheduler_service.start()

    yield

    # Shutdown scheduler (before existing cleanup)
    if scheduler_service:
        scheduler_service.shutdown(wait=True)

    # ... existing shutdown code (close_mod_service) ...
```

### Service Pattern Reference

Follow the existing service patterns in the codebase:
- `api/src/vintagestory_api/services/api_settings.py` - Good example of service structure
- `api/src/vintagestory_api/services/server.py` - Example with lifecycle methods

**Key patterns:**
- Use `structlog.get_logger()` for logging
- Use structured logging with event names (e.g., `logger.info("scheduler_started")`)
- Include type hints on all public methods
- Docstrings for all public methods

### Previous Story Intelligence (7-0)

**From Story 7.0 (Epic 7 Preparation):**
- APScheduler 3.11.2 is installed and verified working
- All v3 imports tested: `AsyncIOScheduler`, `MemoryJobStore`, `AsyncIOExecutor`
- Architecture.md updated with v3 vs v4 warning
- 827 existing API tests pass - no regressions expected

**Files modified in 7-0:**
- `api/pyproject.toml` - Added `apscheduler>=3.11.0,<4.0`
- `api/uv.lock` - Contains apscheduler + tzlocal dependencies

### Git Workflow for This Story

```bash
# Create feature branch (already exists: story/7-1-scheduler-service)
git checkout story/7-1-scheduler-service

# Task-level commits
git commit -m "feat(story-7.1/task-1): create SchedulerService class with lifecycle"
git commit -m "feat(story-7.1/task-2): add job management methods"
git commit -m "feat(story-7.1/task-3): integrate scheduler with FastAPI lifespan"

# Push and create PR
git push -u origin story/7-1-scheduler-service
gh pr create --title "Story 7.1: SchedulerService" --body "..."
```

### Development Commands

Use `just` for all development tasks:
- `just test-api` - Run all API tests
- `just test-api -k "scheduler"` - Run scheduler tests only
- `just test-api tests/services/test_scheduler.py -xvs` - Run specific file, verbose
- `just check` - Full validation (lint + typecheck + test)
- `just lint-api` - Run API linter

### Security Considerations

- Scheduler runs with same permissions as API process
- Jobs should not log sensitive data (follow existing logging patterns)
- No external API keys or credentials in scheduler configuration

### Architecture & Patterns

**Source tree components to touch:**
- `api/src/vintagestory_api/services/scheduler.py` (NEW)
- `api/src/vintagestory_api/main.py` (MODIFY - lifespan integration)
- `api/tests/services/test_scheduler.py` (NEW)

**Alignment with unified project structure:**
- Services in `services/` directory
- Tests mirror source structure in `tests/`
- No routers in this story (API endpoints in Story 7.2)

### References

- `project-context.md` - Critical implementation rules and patterns
- `_bmad-output/planning-artifacts/architecture.md` - Epic 7 & 8 APScheduler patterns
- `_bmad-output/planning-artifacts/epics.md` - Story requirements [Source: epics.md#Story 7.1]
- `_bmad-output/implementation-artifacts/7-0-epic-7-preparation.md` - Research findings from prep story
- [APScheduler 3.x Documentation](https://apscheduler.readthedocs.io/en/3.x/)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- Task 1+2 commit: b642615 - SchedulerService class with job management
- Task 3 commit: 6ef0ecc - FastAPI lifespan integration

### Completion Notes List

- APScheduler v3.11.x patterns used (v4.x is alpha, not recommended)
- Added `# type: ignore[import-untyped]` comments for APScheduler imports (no type stubs available)
- structlog writes to stdout, so tests use `capsys` instead of `caplog` for log assertions
- Integration tests use `with TestClient(app):` pattern for proper lifespan handling
- 26 new tests covering lifecycle, job management, execution, and lifespan integration
- All 853 API tests pass, all 686 web tests pass

### File List

- `api/src/vintagestory_api/services/scheduler.py` - NEW: SchedulerService implementation (195 lines)
- `api/src/vintagestory_api/main.py` - MODIFIED: lifespan integration (+29 lines)
- `api/tests/test_scheduler.py` - NEW: comprehensive test suite (415 lines)
