# Epic 7 & 8: APScheduler Integration & Periodic Tasks

_Added during Epic 5 retrospective (2025-12-30)_
_Updated during Story 7.0 research (2026-01-02)_

## Version Selection

**Use APScheduler v3.11.x (stable), NOT v4.x (alpha)**

| Version | Status | Key Classes | Use? |
|---------|--------|-------------|------|
| **3.11.2** | Stable (Dec 2025) | `AsyncIOScheduler`, `MemoryJobStore`, `AsyncIOExecutor` | **YES** |
| **4.0.0a6** | Alpha (Apr 2025) | `AsyncScheduler`, `MemoryDataStore` | NO |

**Version constraint:** `apscheduler>=3.11.0,<4.0`

**Warning:** AI documentation tools may return v4 patterns (`AsyncScheduler` with `MemoryDataStore`). Always verify you're using v3 patterns with `AsyncIOScheduler`.

## Background Task Scheduling Decision

**Decision:** Use APScheduler with AsyncIOScheduler and MemoryJobStore

**Rationale:**
- Cron syntax support for flexible scheduling
- Built-in job management (pause, resume, remove)
- Async-native with `AsyncIOScheduler`
- No external dependencies (MemoryJobStore is in-memory)
- Good learning opportunity for the team

**Alternatives Considered:**

| Option | Rejected Because |
|--------|------------------|
| Manual asyncio loop | No cron syntax, manual job management |
| Celery Beat | Requires broker, overkill for our needs |
| arq | Requires Redis |
| rocketry | Less proven, smaller community |

## APScheduler Architecture Pattern

**Scheduler Setup:**

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

    def add_interval_job(
        self,
        func,
        seconds: int,
        job_id: str,
        **kwargs
    ):
        """Add an interval-based job."""
        self.scheduler.add_job(
            func,
            trigger="interval",
            seconds=seconds,
            id=job_id,
            replace_existing=True,
            **kwargs
        )

    def add_cron_job(
        self,
        func,
        cron_expression: str,
        job_id: str,
        **kwargs
    ):
        """Add a cron-based job."""
        from apscheduler.triggers.cron import CronTrigger
        self.scheduler.add_job(
            func,
            trigger=CronTrigger.from_crontab(cron_expression),
            id=job_id,
            replace_existing=True,
            **kwargs
        )

    def remove_job(self, job_id: str):
        """Remove a job by ID."""
        self.scheduler.remove_job(job_id)

    def get_jobs(self) -> list:
        """List all scheduled jobs."""
        return self.scheduler.get_jobs()
```

**Lifespan Integration:**

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

## Epic 7: APScheduler Integration (Foundation)

**Scope:** Basic scheduler infrastructure, no jobs yet.

| Story | Title | Scope |
|-------|-------|-------|
| **7.0** | Epic 7 Preparation | Research APScheduler patterns, review async integration |
| **7.1** | SchedulerService | Core service with start/shutdown, lifespan integration |
| **7.2** | Job Management API | GET /jobs (list), DELETE /jobs/{id} (admin only) |
| **7.3** | Scheduler Health | Include scheduler status in /healthz, job count metrics |

## Epic 8: Periodic Task Patterns

**Scope:** Implement initial periodic jobs using the scheduler.

| Story | Title | Scope |
|-------|-------|-------|
| **8.0** | Epic 8 Preparation | Define job patterns, error handling strategy |
| **8.1** | Mod Cache Refresh Job | Periodic mod API cache refresh (uses `mod_list_refresh_interval`) |
| **8.2** | Server Versions Check Job | Check for new VS versions (uses `server_versions_refresh_interval`) |
| **8.3** | Job Configuration UI | Display scheduled jobs in settings, allow interval changes |

## Job Patterns

**Standard Job Template:**

```python
# api/src/vintagestory_api/jobs/mod_cache_refresh.py
import structlog

logger = structlog.get_logger()

async def refresh_mod_cache():
    """Periodic job to refresh mod API cache."""
    try:
        from vintagestory_api.services.mods import get_mod_service
        mod_service = get_mod_service()
        await mod_service.refresh_cache()
        logger.info("mod_cache_refreshed")
    except Exception as e:
        logger.error("mod_cache_refresh_failed", error=str(e))
        # Don't re-raise - let scheduler continue
```

**Job Registration Pattern:**

```python
# api/src/vintagestory_api/jobs/__init__.py
from vintagestory_api.services.scheduler import SchedulerService
from vintagestory_api.services.api_settings import get_api_settings

def register_default_jobs(scheduler: SchedulerService):
    """Register all default periodic jobs."""
    settings = get_api_settings()

    # Mod cache refresh
    if settings.mod_list_refresh_interval > 0:
        from vintagestory_api.jobs.mod_cache_refresh import refresh_mod_cache
        scheduler.add_interval_job(
            refresh_mod_cache,
            seconds=settings.mod_list_refresh_interval,
            job_id="mod_cache_refresh"
        )

    # Server versions check
    if settings.server_versions_refresh_interval > 0:
        from vintagestory_api.jobs.server_versions import check_server_versions
        scheduler.add_interval_job(
            check_server_versions,
            seconds=settings.server_versions_refresh_interval,
            job_id="server_versions_check"
        )
```

**Error Handling Strategy (Critical - Story 8.0):**

1. **Never re-raise exceptions** - This would kill the scheduler
2. **Use structured logging** - Log start, completion, and failure events
3. **Wrap entire job in try/except** - Catch all exceptions
4. **Use `safe_job` decorator** - Helper in `api/src/vintagestory_api/jobs/base.py`

```python
from vintagestory_api.jobs.base import safe_job

@safe_job("my_job")
async def my_job():
    # Job logic - exceptions are caught and logged
    pass
```

**Job Registration Rules:**

- Jobs with `interval = 0` are NOT registered (disabled)
- `register_default_jobs()` is called during lifespan after scheduler starts
- Jobs are registered from `api/src/vintagestory_api/jobs/` module

## Epic Reordering

**Updated Epic Sequence:**

| Epic | Title | Status |
|------|-------|--------|
| 1-5 | (Completed) | Done |
| **6** | Game Configuration Management | Planned |
| **7** | APScheduler Integration | New |
| **8** | Periodic Task Patterns | New |
| **9** | Server Settings & Whitelist | (Former Epic 7) |

**Note:** Original Epic 7 (Server Settings & Whitelist) becomes Epic 9.

## Epic Patterns

**Research-Driven Preparation:**

Preparation epics reduce implementation risk. When facing complex integrations, investing upfront in infrastructure work pays off in faster, smoother implementation.

**Case Study: Epic 7 → Epic 8**

| Epic | Focus | Outcome |
|------|-------|---------|
| **Epic 7** (Preparation) | APScheduler integration, scheduler service, health endpoints | Established patterns for job registration and scheduler integration |
| **Epic 8** (Implementation) | Periodic task implementation using Epic 7's infrastructure | 4 stories completed in 1 day with zero blockers |

Epic 7's research-driven approach meant that when Epic 8 began, the patterns for `@safe_job` decorator, job registration, and settings-based configuration were already established. This eliminated design decisions during implementation, allowing the team to focus purely on building features.

**When to Use Preparation Epics:**

- Complex external library integration (e.g., APScheduler, authentication providers)
- New architectural patterns that will be reused across multiple features
- Integration points with unclear requirements or multiple valid approaches
- Infrastructure work that multiple future features will depend on

**Preparation Epic Characteristics:**

- Focused on establishing patterns, not delivering user-facing features
- Creates reusable infrastructure (services, decorators, base classes)
- Includes comprehensive testing of the new infrastructure
- Documents patterns for future implementation stories to follow

**Planning Consideration:**

When planning sprints, consider whether a complex feature would benefit from being split into:
1. A preparation epic that establishes infrastructure and patterns
2. An implementation epic that uses those patterns to build features

---
