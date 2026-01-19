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

    asset_id: int = 0
    """Unique asset ID from ModDB for constructing reliable external URLs.

    Defaults to 0 for backwards compatibility with existing state files.
    """


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

    asset_id: int = 0
    """Unique asset ID from ModDB for constructing reliable external URLs.

    Defaults to 0 for backwards compatibility.
    """

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


class ModRelease(BaseModel):
    """Single release/version of a mod.

    Contains information about a specific mod release including
    version, download info, and compatible game versions.
    """

    version: str
    """Semantic version string (e.g., '1.8.3')."""

    filename: str
    """Original filename of the release zip."""

    file_id: int
    """Unique file identifier for download endpoint."""

    downloads: int
    """Download count for this specific release."""

    game_versions: list[str]
    """List of compatible game versions (e.g., ['1.21.0', '1.21.1'])."""

    created: str
    """ISO timestamp when this release was created."""

    changelog: str | None = None
    """HTML-formatted changelog for this release."""


class ModLookupResponse(BaseModel):
    """Response from mod lookup endpoint.

    Contains mod details from the VintageStory mod database
    along with compatibility status for the current server version.
    """

    slug: str
    """URL-friendly mod identifier (urlalias from API)."""

    asset_id: int = 0
    """Unique asset ID for constructing reliable moddb URLs (/show/mod/{asset_id}).

    Defaults to 0 for backwards compatibility with API clients.
    """

    name: str
    """Display name of the mod."""

    author: str
    """Mod author name."""

    description: str | None = None
    """HTML-formatted full description text."""

    latest_version: str
    """Latest release version string."""

    downloads: int
    """Total download count."""

    follows: int = 0
    """Number of users following the mod."""

    side: Literal["Both", "Client", "Server", "Universal"]
    """Mod side: 'Both', 'Client', 'Server', or 'Universal'."""

    compatibility: CompatibilityInfo
    """Compatibility status with current game version."""

    logo_url: str | None = None
    """URL to the mod's logo image from the mod database CDN."""

    releases: list[ModRelease] = []
    """All available releases, newest first."""

    tags: list[str] = []
    """Category tags for the mod."""

    homepage_url: str | None = None
    """External homepage URL if available."""

    source_url: str | None = None
    """Source code repository URL if available."""

    created: str | None = None
    """ISO timestamp when the mod was first created."""

    last_released: str | None = None
    """ISO timestamp of the most recent release."""


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


class ModBrowseItem(BaseModel):
    """Single mod item in the browse list.

    Represents a mod from the VintageStory mod database, containing
    summary information suitable for displaying in a browse/search view.
    """

    slug: str
    """URL-friendly mod identifier (urlalias or modidstrs[0] fallback)."""

    asset_id: int = 0
    """Unique asset ID for constructing reliable moddb URLs (/show/mod/{asset_id}).

    Defaults to 0 for backwards compatibility with API clients.
    """

    name: str
    """Display name of the mod."""

    author: str
    """Primary author of the mod."""

    summary: str | None = None
    """Brief description of the mod."""

    downloads: int
    """Total download count."""

    follows: int
    """Number of users following the mod."""

    trending_points: int
    """Trending score for the mod."""

    side: Literal["client", "server", "both"]
    """Which side the mod runs on: 'client', 'server', or 'both'."""

    mod_type: Literal["mod", "externaltool", "other"]
    """Type of the mod: 'mod', 'externaltool', or 'other'."""

    logo_url: str | None = None
    """URL to the mod's logo image, or None if no logo."""

    tags: list[str] = []
    """List of category tags for the mod."""

    last_released: str | None = None
    """ISO timestamp of the last release, or None if not available."""


class PaginationMeta(BaseModel):
    """Pagination metadata for paginated API responses.

    Provides information about the current page and total results
    to support client-side pagination controls.
    """

    page: int
    """Current page number (1-indexed)."""

    page_size: int
    """Number of items per page."""

    total_items: int
    """Total number of items across all pages."""

    total_pages: int
    """Total number of pages available."""

    has_next: bool
    """Whether there is a next page."""

    has_prev: bool
    """Whether there is a previous page."""


class ModBrowseResponse(BaseModel):
    """Response model for the mod browse endpoint.

    Contains a paginated list of mods from the VintageStory mod database
    along with pagination metadata.
    """

    mods: list[ModBrowseItem]
    """List of mods for the current page."""

    pagination: PaginationMeta
    """Pagination metadata."""
