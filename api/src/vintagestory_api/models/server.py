"""Pydantic models for server installation and lifecycle."""

from enum import Enum

from pydantic import BaseModel, Field


class InstallationStage(str, Enum):
    """Stages during server installation process."""

    DOWNLOADING = "downloading"
    EXTRACTING = "extracting"
    CONFIGURING = "configuring"


class ServerState(str, Enum):
    """Overall server installation and runtime state."""

    NOT_INSTALLED = "not_installed"
    INSTALLING = "installing"
    INSTALLED = "installed"  # Server installed but stopped
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class InstallRequest(BaseModel):
    """Request body for server installation endpoint."""

    # Matches: 1.21.3, 1.22.0-rc, 1.22.0-pre.1, 1.21.3+build.123
    version: str = Field(
        ..., pattern=r"^\d+\.\d+\.\d+(?:-[a-zA-Z0-9]+(?:\.\d+)?)?(?:\+[a-zA-Z0-9.]+)?$"
    )


class InstallProgress(BaseModel):
    """Current installation progress information."""

    state: ServerState
    stage: InstallationStage | None = None
    percentage: int | None = None
    error: str | None = None
    error_code: str | None = None
    version: str | None = None
    message: str | None = None


class InstallResponse(BaseModel):
    """Response for server installation endpoint."""

    status: str = "ok"
    data: InstallProgress


class VersionInfo(BaseModel):
    """Information about a specific VintageStory version."""

    version: str
    filename: str
    filesize: str
    md5: str
    cdn_url: str
    local_url: str
    is_latest: bool = False
    channel: str = "stable"


class LifecycleAction(str, Enum):
    """Server lifecycle actions."""

    START = "start"
    STOP = "stop"
    RESTART = "restart"


class LifecycleResponse(BaseModel):
    """Response for server lifecycle control endpoints."""

    action: LifecycleAction
    previous_state: ServerState
    new_state: ServerState
    message: str | None = None


class ServerStatus(BaseModel):
    """Current server status information."""

    state: ServerState
    version: str | None = None
    uptime_seconds: int | None = None  # If running
    last_exit_code: int | None = None  # If stopped after running
