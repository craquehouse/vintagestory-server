# Story 7.0: Epic 7 Preparation

Status: ready-for-dev

## Story

As a **developer**,
I want **to research APScheduler patterns and async integration**,
So that **subsequent stories have a solid foundation for scheduling**.

## Acceptance Criteria

1. **Given** we need to understand APScheduler async patterns, **When** I research the library, **Then** I document AsyncIOScheduler configuration best practices and verify compatibility with our FastAPI lifespan pattern.

2. **Given** we need to add APScheduler, **When** I add the dependency, **Then** `apscheduler` is added to `api/pyproject.toml` and version is pinned appropriately.

3. **Given** we need documented patterns for job configuration, **When** I complete the research, **Then** job defaults (coalesce, max_instances, misfire_grace_time) are documented in architecture.md.

## Tasks / Subtasks

<!--
CRITICAL TASK STRUCTURE RULES:
1. Each functional task MUST include "+ tests" in its name
2. Do NOT create separate "Write tests" tasks at the end
3. A task is NOT complete until its tests pass
4. Tests verify the specific AC listed for that task
-->

- [x] Task 1: Research APScheduler v3 AsyncIOScheduler patterns + document findings (AC: 1)
  - [x] Subtask 1.1: Verify APScheduler 3.11.x is the latest stable version (v4 is alpha)
  - [x] Subtask 1.2: Document AsyncIOScheduler initialization with MemoryJobStore
  - [x] Subtask 1.3: Document job_defaults configuration (coalesce, max_instances, misfire_grace_time)
  - [x] Subtask 1.4: Research FastAPI lifespan integration pattern (startup/shutdown)
  - [x] Subtask 1.5: Verify async job execution patterns (asyncio executor)

- [x] Task 2: Add APScheduler dependency to pyproject.toml + verify install (AC: 2)
  - [x] Subtask 2.1: Add `apscheduler>=3.11.0,<4.0` to api/pyproject.toml dependencies
  - [x] Subtask 2.2: Run `just build-api` to sync dependencies
  - [x] Subtask 2.3: Verify import works: `from apscheduler.schedulers.asyncio import AsyncIOScheduler`

- [ ] Task 3: Update architecture.md with APScheduler patterns (AC: 1, 3)
  - [ ] Subtask 3.1: Review existing Epic 7 & 8 section in architecture.md
  - [ ] Subtask 3.2: Update SchedulerService code pattern if needed based on research
  - [ ] Subtask 3.3: Document job_defaults rationale (why coalesce=True, max_instances=1, etc.)
  - [ ] Subtask 3.4: Add any additional patterns discovered during research

## Dev Notes

### Testing Requirements

**Note:** This is a research/preparation story with no functional code implementation. Testing requirements are:
- Verify APScheduler dependency installs correctly (`just build-api`)
- Verify imports work without errors
- No unit tests required for documentation-only changes

### APScheduler Version Decision

**Use APScheduler v3.11.x (latest stable)**, NOT v4.x (still in alpha as of Jan 2026).

**Key Differences:**
- **v3.x:** `AsyncIOScheduler` with `MemoryJobStore`, `AsyncIOExecutor`
- **v4.x (alpha):** `AsyncScheduler` with `MemoryDataStore` - different API, not production-ready

**Version constraint:** `apscheduler>=3.11.0,<4.0` - pins to v3 stable line

### Architecture Pattern (from architecture.md)

The architecture.md already contains the recommended pattern:

```python
# api/src/vintagestory_api/services/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor

class SchedulerService:
    """Manages periodic background tasks."""

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

    def start(self):
        """Start the scheduler."""
        self.scheduler.start()

    def shutdown(self, wait: bool = True):
        """Shutdown the scheduler."""
        self.scheduler.shutdown(wait=wait)
```

**Job Defaults Rationale:**
- `coalesce: True` - If the scheduler misses multiple fire times (e.g., system was busy), only run once instead of catching up
- `max_instances: 1` - Prevent overlapping job executions (e.g., if job takes longer than interval)
- `misfire_grace_time: 60` - Allow up to 60 seconds late execution before considering job "misfired"

### FastAPI Lifespan Integration

```python
# api/src/vintagestory_api/main.py
from vintagestory_api.services.scheduler import SchedulerService

scheduler_service: SchedulerService | None = None

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global scheduler_service

    # ... existing startup ...

    # Initialize scheduler
    scheduler_service = SchedulerService()
    scheduler_service.start()
    logger.info("scheduler_started")

    yield

    # Shutdown scheduler
    if scheduler_service:
        scheduler_service.shutdown(wait=True)
        logger.info("scheduler_stopped")

    # ... existing shutdown ...
```

### Development Commands

Use `just` for all development tasks:
- `just build-api` - Sync API dependencies after adding apscheduler
- `just test-api` - Run API tests (verify nothing breaks)
- `just check` - Full validation (lint + typecheck + test)
- `just lint` - Run all linters

### Previous Epic Learnings (Epic 6 Retrospective)

**From Epic 6 Retrospective - Key Enforcement Rules:**

1. **Task-Level Commits Are Mandatory** - Every completed task MUST have a corresponding git commit before marking complete
2. **File List Updates Required** - Update "File List" section after each task
3. **Story Sizing: 4-6 Tasks Max** - This story has 3 tasks, well within limits
4. **No Silent Failures** - Any code suppressions require inline justification + tracking issue

**Prep Story Pattern Success:**
- Story 6.0 research became foundation for entire Epic 6
- Upfront research prevents mid-epic pivots and rework
- This story follows the same pattern for Epic 7

### Git Workflow for This Story

```bash
# Create feature branch
git checkout -b story/7-0-epic-7-preparation

# Task-level commits
git commit -m "docs(story-7.0/task-1): research APScheduler async patterns"
git commit -m "feat(story-7.0/task-2): add apscheduler dependency"
git commit -m "docs(story-7.0/task-3): update architecture with scheduler patterns"

# Push and create PR
git push -u origin story/7-0-epic-7-preparation
gh pr create --title "Story 7.0: Epic 7 Preparation" --body "..."
```

### References

- `project-context.md` - Critical implementation rules and patterns
- `_bmad-output/planning-artifacts/architecture.md` - Epic 7 & 8 section with APScheduler patterns
- `_bmad-output/planning-artifacts/epics.md` - Story requirements and acceptance criteria
- [APScheduler 3.x Documentation](https://apscheduler.readthedocs.io/en/3.x/)
- [APScheduler PyPI](https://pypi.org/project/APScheduler/) - v3.11.2 is latest stable

### Research Sources

- **APScheduler PyPI:** Latest stable is v3.11.2 (Dec 2025), v4.0.0a6 is alpha
- **Context7 Docs:** Showed v4 patterns (AsyncScheduler) - NOT for production use
- **Architecture.md:** Contains v3 patterns (AsyncIOScheduler) - correct for our use

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- **Task 1 Complete (2026-01-02):** Research confirmed APScheduler v3.11.2 is latest stable (v4 is alpha). Verified architecture.md patterns are correct: AsyncIOScheduler + MemoryJobStore + AsyncIOExecutor. Job defaults (coalesce=True, max_instances=1, misfire_grace_time=60) properly documented with rationale. FastAPI lifespan pattern verified against real-world implementations (openreplay, letta-ai, rasa). Context7 showed v4 patterns (AsyncScheduler) - confirmed NOT for production use.
- **Task 2 Complete (2026-01-02):** Added `apscheduler>=3.11.0,<4.0` to api/pyproject.toml. Installed apscheduler==3.11.2 + tzlocal==5.3.1. Verified all v3 imports work (AsyncIOScheduler, MemoryJobStore, AsyncIOExecutor). All 827 API tests pass.

### File List

**Files Created:**
- None

**Files Modified:**
- `api/pyproject.toml` - Added `apscheduler>=3.11.0,<4.0` dependency (Task 2)
- `_bmad-output/implementation-artifacts/7-0-epic-7-preparation.md` - Story file updates
- `_bmad-output/implementation-artifacts/sprint-status.yaml` - Updated story status to in-progress

**No Files Deleted**

### Change Log

- **2026-01-02 Task 1:** Completed APScheduler research - confirmed v3.11.2 is latest stable, verified architecture.md patterns are correct
- **2026-01-02 Task 2:** Added apscheduler dependency to pyproject.toml, verified imports and tests pass
