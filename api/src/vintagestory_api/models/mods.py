"""Pydantic models for mod management.

These models support the mod service layer:
- ModMetadata: Extracted from modinfo.json inside mod zip files
- ModState: State index entry tracking installed mod status
- ModInfo: Combined local + remote mod information for API responses
- CompatibilityInfo: Compatibility status with game version
- ModLookupResponse: Response from mod lookup endpoint
"""

from datetime import datetime
from typing import Literal

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


class CompatibilityInfo(BaseModel):
    """Compatibility status information for a mod version.

    Contains the result of checking a mod release against the
    current game version installed on the server.
    """

    status: Literal["compatible", "not_verified", "incompatible"]
    """Compatibility status:
    - compatible: Exact version match in release tags
    - not_verified: Same major.minor version, or version unknown
    - incompatible: No matching version found
    """

    game_version: str
    """Current server game version checked against."""

    mod_version: str
    """Mod version being evaluated."""

    message: str | None = None
    """Warning message if not compatible. None for compatible status."""


class ModLookupResponse(BaseModel):
    """Response from mod lookup endpoint.

    Contains mod details from the VintageStory mod database
    along with compatibility status for the current server version.
    """

    slug: str
    """URL-friendly mod identifier (urlalias from API)."""

    name: str
    """Display name of the mod."""

    author: str
    """Mod author name."""

    description: str | None = None
    """Mod description text."""

    latest_version: str
    """Latest release version string."""

    downloads: int
    """Total download count."""

    side: Literal["Both", "Client", "Server", "Universal"]
    """Mod side: 'Both', 'Client', 'Server', or 'Universal'."""

    compatibility: CompatibilityInfo
    """Compatibility status with current game version."""


class EnableResult(BaseModel):
    """Result of enabling a mod."""

    slug: str
    """The mod slug that was enabled."""

    enabled: bool
    """Whether the mod is now enabled (always True for successful enable)."""

    pending_restart: bool
    """Whether a server restart is required for changes to take effect."""


class DisableResult(BaseModel):
    """Result of disabling a mod."""

    slug: str
    """The mod slug that was disabled."""

    enabled: bool
    """Whether the mod is now enabled (always False for successful disable)."""

    pending_restart: bool
    """Whether a server restart is required for changes to take effect."""


class RemoveResult(BaseModel):
    """Result of removing a mod."""

    slug: str
    """The mod slug that was removed."""

    pending_restart: bool
    """Whether a server restart is required for changes to take effect."""
