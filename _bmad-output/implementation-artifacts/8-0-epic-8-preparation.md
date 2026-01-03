# Story 8.0: Epic 8 Preparation

Status: in-progress

## Story

As a **developer**,
I want **to define job patterns and error handling strategy**,
So that **periodic tasks are implemented consistently across the codebase**.

## Acceptance Criteria

1. **Given** we need a standard job pattern, **When** I define the template, **Then** jobs follow a consistent structure: try/except, structured logging, no re-raise.

2. **Given** we need job registration patterns, **When** I define the approach, **Then** jobs are registered in a central `register_default_jobs()` function.

3. **Given** registration respects API settings, **When** interval settings are 0, **Then** the corresponding job is NOT registered.

4. **Given** the jobs directory structure exists, **When** future stories implement jobs, **Then** they follow the established patterns in `api/src/vintagestory_api/jobs/`.

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

- [x] Task 1: Create jobs directory structure and base pattern + tests (AC: 1, 4)
  - [x] Subtask 1.1: Create `api/src/vintagestory_api/jobs/` directory
  - [x] Subtask 1.2: Create `__init__.py` with `register_default_jobs()` stub function
  - [x] Subtask 1.3: Create `base.py` with job template documentation and helper utilities
  - [x] Subtask 1.4: Write tests for register_default_jobs (empty registration, no jobs registered initially)

- [x] Task 2: Integrate job registration with lifespan + tests (AC: 2, 3)
  - [x] Subtask 2.1: Update `main.py` lifespan to call `register_default_jobs()` after scheduler starts
  - [x] Subtask 2.2: Add structured logging for job registration events
  - [x] Subtask 2.3: Write tests verifying register_default_jobs is called during startup
  - [x] Subtask 2.4: Write tests verifying jobs with interval=0 are not registered

- [x] Task 3: Update architecture docs with job patterns (AC: 1, 2, 3)
  - [x] Subtask 3.1: Document standard job template in architecture.md (already present, verify)
  - [x] Subtask 3.2: Document error handling strategy (log, don't re-raise)
  - [x] Subtask 3.3: Add any Epic 8 preparation notes to architecture

## Review Follow-ups (AI)

- [x] [AI-Review][MEDIUM] Add sprint-status.yaml to File List - modified but not documented (sprint-status.yaml)
- [x] [AI-Review][MEDIUM] Correct test filename in Dev Notes - lists `test_jobs.py` but actual file is `test_jobs_registration.py` (line 69)
- [x] [AI-Review][MEDIUM] Remove unnecessary `pass` statements in stub code (api/src/vintagestory_api/jobs/__init__.py:63,75)
- [x] [AI-Review][LOW] Remove unused `jobs_registered` counter or uncomment increment logic (api/src/vintagestory_api/jobs/__init__.py:51)
  - Note: Counter kept for logging output, will be incremented when jobs are added in 8.1/8.2

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Do not batch tests into a separate "Write tests" task at the end
- Run `just test-api` to verify all tests pass before marking task complete

**Test Files to Create:**
- `api/tests/test_jobs_registration.py` - Tests for job registration and patterns

### Security Considerations

- Jobs run in the API server context with full access
- Job errors should NOT crash the scheduler or API server
- Logging should NOT include sensitive data (API keys, passwords)

### Development Commands

Use `just` for all development tasks:
- `just test-api` - Run all API tests
- `just test-api -k "jobs"` - Run jobs tests only
- `just test-api tests/test_jobs.py -xvs` - Run specific file, verbose
- `just check` - Full validation (lint + typecheck + test)
- `just lint-api` - Run API linter

### Architecture & Patterns

**Standard Job Template (from architecture.md):**

```python
# api/src/vintagestory_api/jobs/example_job.py
import structlog

logger = structlog.get_logger()

async def example_job():
    """Example periodic job following standard pattern."""
    try:
        logger.info("example_job_started")
        # ... job logic ...
        logger.info("example_job_completed", result="success")
    except Exception as e:
        logger.exception("example_job_failed", error=str(e))
        # Don't re-raise - let scheduler continue
```

**Key Patterns:**
- Jobs are async functions (APScheduler AsyncIOScheduler supports async)
- Wrap entire job in try/except
- Use structured logging with event names
- NEVER re-raise exceptions - this would kill the scheduler
- Job IDs should be descriptive: `mod_cache_refresh`, `server_versions_check`

**Job Registration Pattern:**

```python
# api/src/vintagestory_api/jobs/__init__.py
from vintagestory_api.services.scheduler import SchedulerService
from vintagestory_api.services.api_settings import get_api_settings

def register_default_jobs(scheduler: SchedulerService):
    """Register all default periodic jobs."""
    settings = get_api_settings()

    # Mod cache refresh (Story 8.1)
    if settings.mod_list_refresh_interval > 0:
        from vintagestory_api.jobs.mod_cache_refresh import refresh_mod_cache
        scheduler.add_interval_job(
            refresh_mod_cache,
            seconds=settings.mod_list_refresh_interval,
            job_id="mod_cache_refresh"
        )

    # Server versions check (Story 8.2)
    if settings.server_versions_refresh_interval > 0:
        from vintagestory_api.jobs.server_versions import check_server_versions
        scheduler.add_interval_job(
            check_server_versions,
            seconds=settings.server_versions_refresh_interval,
            job_id="server_versions_check"
        )
```

**Note:** Story 8.0 creates the infrastructure. Stories 8.1 and 8.2 implement the actual jobs.

### Lifespan Integration

Update `main.py` lifespan to register jobs:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... existing startup code ...

    # Start scheduler
    scheduler.start()
    logger.info("scheduler_started")

    # Register default jobs
    from vintagestory_api.jobs import register_default_jobs
    register_default_jobs(scheduler)
    logger.info("default_jobs_registered")

    yield

    # ... existing shutdown code ...
```

### Source Tree Components

**Files to CREATE:**
- `api/src/vintagestory_api/jobs/__init__.py` (register_default_jobs stub)
- `api/src/vintagestory_api/jobs/base.py` (job template documentation/helpers)
- `api/tests/test_jobs.py` (job registration tests)

**Files to MODIFY:**
- `api/src/vintagestory_api/main.py` (add job registration to lifespan)

### Previous Story Intelligence (7-3)

**From Story 7.3 (Scheduler Health):**
- SchedulerService is fully integrated with lifespan
- `get_scheduler_service()` available for dependency injection
- Health endpoint reports scheduler status and job count
- 890 tests passing as of Epic 7 completion

**Scheduler Service API (from 7-1):**
- `scheduler.add_interval_job(func, seconds, job_id)` - Add interval job
- `scheduler.add_cron_job(func, cron_expression, job_id)` - Add cron job
- `scheduler.remove_job(job_id)` - Remove job
- `scheduler.get_jobs()` - List all jobs
- `scheduler.is_running` - Check if scheduler is running

**API Settings (from 6-3):**
- `get_api_settings()` returns ApiSettings with:
  - `mod_list_refresh_interval: int` (default 3600 = 1 hour)
  - `server_versions_refresh_interval: int` (default 86400 = 24 hours)

### Git Workflow for This Story

```bash
# Create feature branch
git checkout -b story/8-0-epic-8-preparation

# Task-level commits
git commit -m "feat(story-8.0/task-1): create jobs directory and base pattern"
git commit -m "feat(story-8.0/task-2): integrate job registration with lifespan"
git commit -m "docs(story-8.0/task-3): update architecture with job patterns"

# Push and create PR
git push -u origin story/8-0-epic-8-preparation
gh pr create --title "Story 8.0: Epic 8 Preparation" --body "..."
```

### Project Structure Notes

After this story, the jobs structure will be:

```
api/src/vintagestory_api/
├── jobs/
│   ├── __init__.py        # register_default_jobs()
│   ├── base.py            # Job template documentation/helpers
│   ├── mod_cache_refresh.py   # (Story 8.1)
│   └── server_versions.py     # (Story 8.2)
├── services/
│   └── scheduler.py       # SchedulerService (from 7-1)
└── ...
```

### References

- `project-context.md` - Critical implementation rules and patterns
- `_bmad-output/planning-artifacts/architecture.md#Job Patterns` - Standard job template
- `_bmad-output/planning-artifacts/epics.md#Story 8.0` - Story requirements
- `_bmad-output/implementation-artifacts/7-1-scheduler-service.md` - SchedulerService patterns
- `_bmad-output/implementation-artifacts/7-3-scheduler-health.md` - Health integration patterns

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- Created jobs module infrastructure for Epic 8 periodic tasks
- Implemented `register_default_jobs()` function with settings-based job registration
- Created `safe_job` decorator for standardized error handling (catch + log, no re-raise)
- Integrated job registration into FastAPI lifespan (after scheduler starts)
- Added 19 tests covering job registration, safe_job decorator, and lifespan integration
- Updated architecture.md with error handling strategy and job registration rules

### File List

**Task 1:**
- `api/src/vintagestory_api/jobs/__init__.py` (created)
- `api/src/vintagestory_api/jobs/base.py` (created)
- `api/tests/test_jobs_registration.py` (created)

**Task 2:**
- `api/src/vintagestory_api/main.py` (modified - added register_default_jobs call)
- `api/tests/test_jobs_registration.py` (modified - added lifespan integration tests)

**Task 3:**
- `_bmad-output/planning-artifacts/architecture.md` (modified - added error handling strategy and safe_job docs)

**Story Completion:**
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modified - updated story status)
- `_bmad-output/implementation-artifacts/8-0-epic-8-preparation.md` (created - story file)

