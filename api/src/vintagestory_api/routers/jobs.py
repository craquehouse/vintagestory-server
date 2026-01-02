"""Job management API endpoints.

Story 7.2: Job Management API

Provides endpoints for viewing and managing scheduled background jobs.
All endpoints require Admin role.
"""

from fastapi import APIRouter, Depends, HTTPException

from vintagestory_api.middleware.permissions import RequireAdmin
from vintagestory_api.models.errors import ErrorCode
from vintagestory_api.models.jobs import job_to_info
from vintagestory_api.models.responses import ApiResponse
from vintagestory_api.services.scheduler import SchedulerService

router = APIRouter(prefix="/jobs", tags=["Jobs"])


def get_scheduler() -> SchedulerService:
    """Get scheduler service from main module.

    Deferred import to avoid circular import with main.py.
    """
    from vintagestory_api.main import get_scheduler_service

    return get_scheduler_service()


@router.get("", response_model=ApiResponse)
async def list_jobs(
    _: RequireAdmin,
    scheduler: SchedulerService = Depends(get_scheduler),
) -> ApiResponse:
    """List all scheduled jobs.

    Returns job information including ID, next run time, and trigger details.
    Requires Admin role.

    Returns:
        ApiResponse with list of jobs, each containing:
        - id: Unique job identifier
        - next_run_time: Next scheduled execution time
        - trigger_type: "interval" or "cron"
        - trigger_details: Human-readable trigger description
    """
    jobs = scheduler.get_jobs()
    job_list = [job_to_info(job).model_dump(mode="json") for job in jobs]
    return ApiResponse(status="ok", data={"jobs": job_list})


@router.delete("/{job_id}", response_model=ApiResponse)
async def delete_job(
    job_id: str,
    _: RequireAdmin,
    scheduler: SchedulerService = Depends(get_scheduler),
) -> ApiResponse:
    """Delete a scheduled job.

    Removes the job from the scheduler. Requires Admin role.

    Args:
        job_id: Unique identifier of the job to delete.

    Returns:
        ApiResponse confirming deletion.

    Raises:
        HTTPException: 404 if job not found.
    """
    # APScheduler v3.x does not ship with type stubs
    from apscheduler.jobstores.base import JobLookupError  # type: ignore[import-untyped]

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
