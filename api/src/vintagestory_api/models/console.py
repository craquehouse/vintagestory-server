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


class ConsoleHistoryData(BaseModel):
    """Data payload for console history response."""

    lines: list[str] = Field(
        default_factory=list, description="Console output lines (oldest first)"
    )
    total: int = Field(..., description="Total number of lines in the buffer")
    limit: int | None = Field(None, description="Requested line limit (if provided)")


class ConsoleCommandData(BaseModel):
    """Data payload for console command response."""

    command: str = Field(..., description="The command that was sent")
    sent: bool = Field(True, description="Whether the command was successfully sent")
