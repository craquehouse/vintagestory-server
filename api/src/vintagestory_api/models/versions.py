"""Pydantic models for versions API.

Story 13.1: Server Versions API

Models for the /versions endpoint responses including cache indicators.
"""

from datetime import datetime

from pydantic import BaseModel

from vintagestory_api.models.server import VersionInfo


class VersionListResponse(BaseModel):
    """Response model for GET /versions endpoint.

    Contains a list of available versions with cache metadata.
    """

    versions: list[VersionInfo]
    total: int
    cached: bool = False
    cached_at: datetime | None = None


class VersionDetailResponse(BaseModel):
    """Response model for GET /versions/{version} endpoint.

    Contains details for a single version with cache metadata.
    """

    version: VersionInfo
    cached: bool = False
    cached_at: datetime | None = None
