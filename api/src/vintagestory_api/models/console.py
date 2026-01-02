"""Console-related Pydantic models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ConsoleCommandRequest(BaseModel):
    """Request body for console command endpoint."""

    command: str = Field(..., min_length=1, max_length=1000)


class LogFileInfo(BaseModel):
    """Information about a log file."""

    name: str = Field(..., description="Log file name (e.g., 'server-main.log')")
    size_bytes: int = Field(..., description="File size in bytes")
    modified_at: str = Field(..., description="Last modification time (ISO 8601)")


class LogFilesResponse(BaseModel):
    """Response for log files listing endpoint."""

    files: list[LogFileInfo] = []
    logs_dir: str
