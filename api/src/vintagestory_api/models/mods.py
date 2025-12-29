"""Pydantic models for mod management.

These models support the mod service layer:
- ModMetadata: Extracted from modinfo.json inside mod zip files
- ModState: State index entry tracking installed mod status
- ModInfo: Combined local + remote mod information for API responses
"""

from datetime import datetime

from pydantic import BaseModel


class ModMetadata(BaseModel):
    """Metadata extracted from modinfo.json inside a mod zip file.

    This represents the static information about a mod that doesn't change
    unless the mod itself is updated.
    """

    modid: str
    """Unique identifier for the mod (usually matches slug)."""

    name: str
    """Display name of the mod."""

    version: str
    """Mod version string."""

    authors: list[str] = []
    """List of mod authors."""

    description: str | None = None
    """Optional description of the mod."""


class ModState(BaseModel):
    """State index entry for an installed mod.

    Maps a mod filename to its slug/version for fast lookup without
    re-extracting from the zip file. Stored in the state index file.
    """

    filename: str
    """Original filename of the mod zip (key for download cache)."""

    slug: str
    """modid from modinfo.json (key for metadata cache)."""

    version: str
    """Version string from modinfo.json."""

    enabled: bool = True
    """Whether the mod is enabled (False = .disabled suffix)."""

    installed_at: datetime
    """When the mod was first installed."""


class ModInfo(BaseModel):
    """Combined local and remote mod information for API responses.

    This model is used when returning mod details to the frontend,
    combining state information with extracted metadata.
    """

    filename: str
    """Mod zip filename."""

    slug: str
    """Unique mod identifier (modid)."""

    version: str
    """Installed version."""

    enabled: bool
    """Whether the mod is currently enabled."""

    installed_at: datetime
    """Installation timestamp."""

    name: str
    """Display name of the mod."""

    authors: list[str] = []
    """List of mod authors."""

    description: str | None = None
    """Optional description."""
