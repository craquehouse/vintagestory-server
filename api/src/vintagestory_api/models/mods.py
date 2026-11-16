"""Pydantic models for mod management.

These models support the mod service layer:
- ModMetadata: Extracted from modinfo.json inside mod zip files
- ModState: State index entry tracking installed mod status
- ModInfo: Combined local + remote mod information for API responses
- CompatibilityInfo: Compatibility status with game version
- ModScreenshot: One screenshot of a mod on the mod lookup response
- ModLookupResponse: Response from mod lookup endpoint
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator

_MODINFO_SIDES: dict[str, str] = {
    "universal": "Both",
    "both": "Both",
    "client": "Client",
    "server": "Server",
}


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

    side: Literal["Both", "Client", "Server"] | None = None
    """Mod side: 'Both', 'Client', or 'Server'. None if not specified or not recognized."""

    @field_validator("side", mode="before")
    @classmethod
    def _normalize_side(cls, value: object) -> str | None:
        """Accept modinfo.json side values as VintageStory does (case-insensitive).

        VintageStory names both sides "Universal"; the mod database says "Both". An
        unrecognized value becomes None rather than discarding the whole modinfo.
        """
        if not isinstance(value, str):
            return None
        return _MODINFO_SIDES.get(value.strip().lower())


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

    side: Literal["Both", "Client", "Server"] | None = None
    """Mod side: 'Both', 'Client', or 'Server'. None if unknown."""


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

    latest_supported_game_version: str | None = None
    """Most recent game version the evaluated mod ID's releases are tagged for
    (Epic 16 ADR-2), or None when none of its tags parse as a version."""


class ModRelease(BaseModel):
    """Single release/version of a mod.

    Contains information about a specific mod release including
    version, download info, and compatible game versions.
    """

    version: str
    """Semantic version string (e.g., '1.8.3')."""

    filename: str
    """Original filename of the release zip."""

    file_id: int | None
    """Unique file identifier for download endpoint; None when the release has no
    downloadable file (Story 17.1)."""

    downloads: int
    """Download count for this specific release."""

    game_versions: list[str]
    """List of compatible game versions (e.g., ['1.21.0', '1.21.1'])."""

    created: str
    """ISO timestamp when this release was created."""

    changelog: str | None = None
    """HTML-formatted changelog for this release."""

    modidstr: str = ""
    """Mod ID inside this release; one database entry can ship several mod IDs."""


class ModScreenshot(BaseModel):
    """One screenshot of a mod database entry (Story 18.1, Epic 18 ADR-1)."""

    image_url: str
    """Full-size image on the mod database CDN."""

    thumbnail_url: str
    """The 55x60 thumbnail, or the image URL when the mod database gave no usable thumbnail."""

    filename: str
    """The uploaded file name; may be ``""``."""


class ModLookupResponse(BaseModel):
    """Response from mod lookup endpoint.

    Contains mod details from the VintageStory mod database
    along with compatibility status for the current server version.
    """

    slug: str
    """Mod identifier from modidstrs[0] - used for API lookups (/api/mod/{slug}).

    VSS-brs: This is always from modidstrs, NOT urlalias, for consistency with
    ModBrowseItem. The VintageStory API only accepts modidstrs for lookups.
    """

    urlalias: str | None = None
    """URL alias for website links (e.g., mods.vintagestory.at/{urlalias}).

    May differ from slug. Use this for constructing website URLs, use slug for API calls.
    """

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

    latest_version: str | None
    """The version an install without a named version picks for `install_mod_id`.

    The newest stable release of that mod ID that has a downloadable file (Epic 17
    ADR-2); None when none of its releases has a file.
    """

    install_mod_id: str
    """The mod ID an install of the looked-up slug installs (Epic 17 ADR-2).

    The looked-up slug when a release carries it as its mod ID, otherwise the mod ID
    of the entry's newest release. May differ from `slug`.
    """

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

    screenshots: list[ModScreenshot] = []
    """The entry's screenshots in mod database order; only `https` URLs on the mod
    database CDN (Epic 18 ADR-1)."""

    trailer_url: str | None = None
    """`https://www.youtube.com/watch?v=<id>` when the entry's trailer field names a
    YouTube video, else None (Epic 18 ADR-2)."""


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
    """Mod identifier from modidstrs[0] - used for API lookups (/api/mod/{slug}).

    VSS-brs: This is always from modidstrs, NOT urlalias, because the VintageStory
    API only accepts modidstrs for lookups. Some mods have different urlalias values.
    """

    mod_ids: list[str] = []
    """Every mod ID of the mod database entry (the listing's modidstrs), in listing order.

    Each appears once; `slug` is the first when the entry has mod IDs (an entry with
    none has `[]`, and `slug` falls back to its numeric ID). The web uses it to
    recognize an installed mod by any of its mod IDs (Story 17.4).
    """

    urlalias: str | None = None
    """URL alias for website links (e.g., mods.vintagestory.at/{urlalias}).

    May differ from slug. Use this for constructing website URLs, use slug for API calls.
    """

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
