"""Base utilities and patterns for periodic jobs.

Story 8.0: Epic 8 Preparation

This module documents the standard job template and provides helper utilities
for implementing periodic background tasks.

Standard Job Template
---------------------
All periodic jobs MUST follow this pattern:

```python
import structlog

logger = structlog.get_logger()


async def example_job():
    '''Example periodic job following standard pattern.'''
    try:
        logger.info("example_job_started")
        # ... job logic ...
        logger.info("example_job_completed", result="success")
    except Exception as e:
        logger.exception("example_job_failed", error=str(e))
        # CRITICAL: Don't re-raise - let scheduler continue
```

Key Requirements:
    1. Jobs are async functions (APScheduler AsyncIOScheduler supports async)
    2. Wrap ENTIRE job in try/except
    3. Use structured logging with event names (snake_case)
    4. NEVER re-raise exceptions - this would kill the scheduler
    5. Job IDs should be descriptive: `mod_cache_refresh`, `server_versions_check`

Error Handling Strategy:
    - Log errors with `logger.exception()` to capture stack trace
    - DO NOT re-raise - the scheduler must continue running
    - Consider adding metrics/alerting for repeated failures (future enhancement)

Logging Conventions:
    - Start event: `{job_name}_started`
    - Success event: `{job_name}_completed` with relevant result data
    - Failure event: `{job_name}_failed` with error details
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any, TypeVar

import structlog

logger = structlog.get_logger()

# Type variable for job functions
T = TypeVar("T")


def safe_job(job_name: str) -> Callable[
    [Callable[..., Coroutine[Any, Any, T]]],
    Callable[..., Coroutine[Any, Any, T | None]],
]:
    """Decorator that wraps an async job function with standard error handling.

    This decorator implements the standard job pattern:
    - Logs job start and completion events
    - Catches and logs exceptions without re-raising
    - Ensures the scheduler continues even if the job fails

    Args:
        job_name: The name used in log events (e.g., "mod_cache_refresh")

    Returns:
        Decorator function that wraps the job.

    Example:
        >>> @safe_job("my_job")
        ... async def my_job():
        ...     # Job logic here
        ...     pass
    """

    def decorator(
        func: Callable[..., Coroutine[Any, Any, T]]
    ) -> Callable[..., Coroutine[Any, Any, T | None]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T | None:
            try:
                logger.info(f"{job_name}_started")
                result = await func(*args, **kwargs)
                logger.info(f"{job_name}_completed")
                return result
            except Exception as e:
                # Log with exception info but DON'T re-raise
                # This is critical - re-raising would kill the scheduler
                logger.exception(f"{job_name}_failed", error=str(e))
                return None

        return wrapper

    return decorator
