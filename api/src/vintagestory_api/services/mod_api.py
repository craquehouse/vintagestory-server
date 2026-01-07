"""Client for VintageStory mod database API.

This module provides an async client for interacting with the VintageStory
mod database at mods.vintagestory.at, handling mod lookups and downloads.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import urlparse

import httpx
import structlog

if TYPE_CHECKING:
    from vintagestory_api.services.cache_eviction import CacheEvictionService

logger = structlog.get_logger()

# Type alias for compatibility status
CompatibilityStatus = Literal["compatible", "not_verified", "incompatible"]

# Type aliases for API response objects
ModDict = dict[str, Any]
ReleaseDict = dict[str, Any]

# Sort options for browse endpoint
SortOption = Literal["downloads", "trending", "recent"]


@dataclass
class DownloadResult:
    """Result of a mod download operation."""

    path: Path
    """Path to the downloaded file in cache."""

    filename: str
    """Original filename of the mod zip."""

    version: str
    """Mod version string."""

    release: ReleaseDict
    """Full release object for compatibility check."""


class ModApiError(Exception):
    """Base exception for mod API errors."""


class ModNotFoundError(ModApiError):
    """Raised when a mod is not found in the mod database."""

    def __init__(self, slug: str) -> None:
        self.slug = slug
        super().__init__(f"Mod '{slug}' not found in mod database")


class ModVersionNotFoundError(ModApiError):
    """Raised when a specific mod version is not found."""

    def __init__(self, slug: str, version: str) -> None:
        self.slug = slug
        self.version = version
        super().__init__(f"Version '{version}' not found for mod '{slug}'")


class ExternalApiError(ModApiError):
    """Raised when the external mod API is unavailable."""

    def __init__(self, message: str = "VintageStory mod API is unavailable") -> None:
        super().__init__(message)


class DownloadError(ModApiError):
    """Raised when a mod download fails."""

    def __init__(self, slug: str, message: str = "Download failed") -> None:
        self.slug = slug
        super().__init__(f"Failed to download mod '{slug}': {message}")


def extract_slug(slug_or_url: str) -> str:
    """Extract mod slug from URL or return as-is if already a slug.

    Args:
        slug_or_url: Either a mod slug (e.g., "smithingplus") or a full URL
                     (e.g., "https://mods.vintagestory.at/smithingplus")

    Returns:
        The extracted slug.
    """
    if slug_or_url.startswith("http"):
        parsed = urlparse(slug_or_url)
        # Path is like /smithingplus or /mod/smithingplus
        path = parsed.path.strip("/")
        # Remove "mod/" prefix if present
        if path.startswith("mod/"):
            path = path[4:]
        return path
    return slug_or_url


def validate_slug(slug: str) -> bool:
    """Validate that a slug contains only safe characters.

    Args:
        slug: The slug to validate.

    Returns:
        True if valid, False otherwise.

    Valid slugs are alphanumeric with dashes/underscores, max 50 chars.
    Rejects Windows reserved names and path traversal patterns.
    """
    if not slug or len(slug) > 50:
        return False

    # Must be alphanumeric with dash/underscore only
    # This already blocks: . / \ and other path traversal chars
    if not re.match(r"^[a-zA-Z0-9_-]+$", slug):
        return False

    # Reject Windows reserved device names (case-insensitive)
    # These cause issues on Windows filesystems
    reserved_names = {
        "con", "prn", "aux", "nul",
        "com1", "com2", "com3", "com4", "com5", "com6", "com7", "com8", "com9",
        "lpt1", "lpt2", "lpt3", "lpt4", "lpt5", "lpt6", "lpt7", "lpt8", "lpt9",
    }
    if slug.lower() in reserved_names:
        return False

    return True


def check_compatibility(release: ReleaseDict, game_version: str) -> CompatibilityStatus:
    """Check if a release is compatible with the installed game version.

    Args:
        release: Release object from mod API response.
        game_version: Installed game version (e.g., "1.21.3").

    Returns:
        - "compatible": Exact version match in release tags
        - "not_verified": Same major.minor version, or version format unrecognized
        - "incompatible": No matching version found
    """
    tags = release.get("tags", [])

    # Handle empty or non-standard game versions defensively
    if not game_version or not tags:
        return "not_verified"

    # Strip common prefixes (v1.2.3 -> 1.2.3)
    normalized_version = game_version.lstrip("vV")

    # Exact match (try both original and normalized)
    if game_version in tags or normalized_version in tags:
        return "compatible"

    # Try to extract major.minor for fuzzy matching
    # Handle non-standard formats like "stable", "latest", etc.
    parts = normalized_version.split(".")
    if len(parts) < 2 or not parts[0].isdigit() or not parts[1].isdigit():
        # Can't parse version - return safe default
        return "not_verified"

    # Major.minor match (e.g., 1.21.x)
    major_minor = f"{parts[0]}.{parts[1]}"
    for tag in tags:
        if tag.startswith(major_minor + ".") or tag == major_minor:
            return "not_verified"

    return "incompatible"


class ModApiClient:
    """Async client for VintageStory mod database API.

    Provides methods for looking up mods and downloading mod files
    from mods.vintagestory.at.

    Attributes:
        BASE_URL: Base URL for the mod API.
        DOWNLOAD_URL: URL for file downloads.
        DEFAULT_TIMEOUT: Default timeout for API calls (30s).
        DOWNLOAD_TIMEOUT: Timeout for file downloads (120s).
        BROWSE_CACHE_TTL: Cache TTL for browse mod list (5 minutes).
    """

    BASE_URL = "https://mods.vintagestory.at/api"
    DOWNLOAD_URL = "https://mods.vintagestory.at/download"
    DEFAULT_TIMEOUT = 30.0
    DOWNLOAD_TIMEOUT = 120.0
    BROWSE_CACHE_TTL = timedelta(minutes=5)

    def __init__(
        self,
        cache_dir: Path,
        cache_eviction_service: CacheEvictionService | None = None,
    ) -> None:
        """Initialize the mod API client.

        Args:
            cache_dir: Directory for caching downloaded mods.
            cache_eviction_service: Optional cache eviction service for managing
                cache size. If provided, eviction is run after each download.
        """
        self._cache_dir = cache_dir
        self._mods_cache = cache_dir / "mods"
        self._mods_cache.mkdir(parents=True, exist_ok=True)
        self._client: httpx.AsyncClient | None = None
        self._cache_eviction = cache_eviction_service

        # In-memory cache for browse mod list
        self._browse_cache: list[ModDict] | None = None
        self._browse_cache_time: datetime | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.DEFAULT_TIMEOUT,
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def get_mod(self, slug: str) -> ModDict | None:
        """Get mod details by slug.

        Args:
            slug: URL-friendly mod identifier (e.g., "smithingplus").

        Returns:
            Mod dictionary if found, None if not found.

        Raises:
            ExternalApiError: If the mod API is unavailable.
        """
        # Extract slug from URL if needed
        slug = extract_slug(slug)

        # Validate slug
        if not validate_slug(slug):
            logger.warning("invalid_slug", slug=slug)
            return None

        client = await self._get_client()
        try:
            response = await client.get(f"{self.BASE_URL}/mod/{slug}")
            data = response.json()

            # CRITICAL: statuscode is STRING, not int!
            if data.get("statuscode") == "200":
                logger.debug("mod_lookup_success", slug=slug)
                return data["mod"]

            if data.get("statuscode") == "404":
                logger.debug("mod_not_found", slug=slug)
                return None

            # Unexpected status
            logger.warning(
                "unexpected_api_status",
                slug=slug,
                statuscode=data.get("statuscode"),
            )
            return None

        except httpx.TimeoutException as e:
            logger.error("mod_api_timeout", slug=slug)
            raise ExternalApiError("VintageStory mod API request timed out") from e

        except httpx.ConnectError as e:
            logger.error("mod_api_connection_error", slug=slug)
            raise ExternalApiError(
                "Could not connect to VintageStory mod API"
            ) from e

        except httpx.HTTPError as e:
            logger.error("mod_api_error", slug=slug, error=str(e))
            raise ExternalApiError(
                f"VintageStory mod API error: {e}"
            ) from e

    async def download_mod(
        self,
        slug: str,
        version: str | None = None,
    ) -> DownloadResult | None:
        """Lookup mod, select release, and download to cache.

        This is the full download flow:
        1. Lookup mod by slug
        2. Select release (latest or specific version)
        3. Download file to cache with atomic write

        Args:
            slug: Mod slug (e.g., "smithingplus").
            version: Specific version to download, or None for latest.

        Returns:
            DownloadResult with path and metadata, or None on failure.

        Raises:
            ModNotFoundError: If the mod doesn't exist.
            ModVersionNotFoundError: If the specific version doesn't exist.
            ExternalApiError: If the mod API is unavailable.
            DownloadError: If the download fails.
        """
        # Extract slug from URL if needed
        slug = extract_slug(slug)

        # 1. Lookup mod
        mod = await self.get_mod(slug)
        if mod is None:
            raise ModNotFoundError(slug)

        releases = mod.get("releases", [])
        if not releases:
            raise ModNotFoundError(slug)

        # 2. Select release
        if version is None:
            release = releases[0]  # Latest (releases are newest-first)
            logger.debug("selected_latest_release", slug=slug, version=release.get("modversion"))
        else:
            release = next(
                (r for r in releases if r.get("modversion") == version),
                None,
            )
            if release is None:
                raise ModVersionNotFoundError(slug, version)
            logger.debug("selected_specific_version", slug=slug, version=version)

        # 3. Download file
        fileid = release["fileid"]
        filename = release["filename"]
        dest_path = self._mods_cache / filename
        temp_path = dest_path.with_suffix(".tmp")

        client = await self._get_client()
        try:
            async with client.stream(
                "GET",
                f"{self.DOWNLOAD_URL}?fileid={fileid}",
                timeout=self.DOWNLOAD_TIMEOUT,
            ) as response:
                response.raise_for_status()

                with open(temp_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)

            # Atomic rename
            temp_path.rename(dest_path)

            logger.info(
                "mod_download_complete",
                slug=slug,
                version=release["modversion"],
                filename=filename,
            )

            # Run cache eviction after successful download
            if self._cache_eviction is not None:
                eviction_result = self._cache_eviction.evict_if_needed()
                if eviction_result.files_evicted > 0:
                    logger.debug(
                        "cache_eviction_after_download",
                        files_evicted=eviction_result.files_evicted,
                        bytes_freed=eviction_result.bytes_freed,
                    )

            return DownloadResult(
                path=dest_path,
                filename=filename,
                version=release["modversion"],
                release=release,
            )

        except httpx.TimeoutException:
            # Cleanup partial download
            if temp_path.exists():
                temp_path.unlink()
            logger.error("mod_download_timeout", slug=slug, fileid=fileid)
            raise DownloadError(slug, "Download timed out")

        except httpx.HTTPError as e:
            # Cleanup partial download
            if temp_path.exists():
                temp_path.unlink()
            logger.error("mod_download_failed", slug=slug, fileid=fileid, error=str(e))
            raise DownloadError(slug, str(e))

        except OSError as e:
            # Cleanup partial download
            if temp_path.exists():
                temp_path.unlink()
            logger.error("mod_download_io_error", slug=slug, error=str(e))
            raise DownloadError(slug, f"IO error: {e}")

    def _is_browse_cache_valid(self) -> bool:
        """Check if the browse cache is still valid.

        Returns:
            True if cache exists and hasn't expired, False otherwise.
        """
        if self._browse_cache is None or self._browse_cache_time is None:
            return False
        return datetime.now() - self._browse_cache_time < self.BROWSE_CACHE_TTL

    async def get_all_mods(self, force_refresh: bool = False) -> list[ModDict]:
        """Get all mods from the VintageStory mod database.

        This method fetches the complete mod list from the API and caches
        it in memory for 5 minutes to avoid hammering the external API.

        Args:
            force_refresh: If True, bypass the cache and fetch fresh data.

        Returns:
            List of mod dictionaries from the API.

        Raises:
            ExternalApiError: If the mod API is unavailable.
        """
        # Return cached data if valid and not forcing refresh
        if not force_refresh and self._is_browse_cache_valid():
            logger.debug("browse_cache_hit", count=len(self._browse_cache or []))
            return self._browse_cache or []

        client = await self._get_client()
        try:
            response = await client.get(f"{self.BASE_URL}/mods")
            data = response.json()

            # CRITICAL: statuscode is STRING, not int!
            if data.get("statuscode") == "200":
                mods = data.get("mods", [])
                self._browse_cache = mods
                self._browse_cache_time = datetime.now()
                logger.debug("browse_cache_refreshed", count=len(mods))
                return mods

            # Unexpected status - log and raise
            logger.warning(
                "unexpected_api_status_browse",
                statuscode=data.get("statuscode"),
            )
            raise ExternalApiError(
                f"VintageStory mod API returned unexpected status: {data.get('statuscode')}"
            )

        except httpx.TimeoutException as e:
            logger.error("mod_api_timeout_browse")
            raise ExternalApiError("VintageStory mod API request timed out") from e

        except httpx.ConnectError as e:
            logger.error("mod_api_connection_error_browse")
            raise ExternalApiError(
                "Could not connect to VintageStory mod API"
            ) from e

        except httpx.HTTPError as e:
            logger.error("mod_api_error_browse", error=str(e))
            raise ExternalApiError(
                f"VintageStory mod API error: {e}"
            ) from e

    def clear_browse_cache(self) -> None:
        """Clear the browse mod list cache.

        This forces the next call to get_all_mods() to fetch fresh data.
        """
        self._browse_cache = None
        self._browse_cache_time = None
        logger.debug("browse_cache_cleared")


def _get_downloads(m: ModDict) -> int:
    """Get downloads count from mod dict."""
    return int(m.get("downloads", 0))


def _get_trending(m: ModDict) -> int:
    """Get trending points from mod dict."""
    return int(m.get("trendingpoints", 0))


def _get_recent(m: ModDict) -> str:
    """Get last released date from mod dict."""
    return str(m.get("lastreleased", ""))


def sort_mods(
    mods: list[ModDict],
    sort_by: SortOption = "recent",
) -> list[ModDict]:
    """Sort a list of mods by the specified criteria.

    Args:
        mods: List of mod dictionaries from the API.
        sort_by: Sort criteria - "downloads", "trending", or "recent".

    Returns:
        Sorted list of mods (descending order).
    """
    if sort_by == "downloads":
        return sorted(mods, key=_get_downloads, reverse=True)
    elif sort_by == "trending":
        return sorted(mods, key=_get_trending, reverse=True)
    else:  # recent
        return sorted(mods, key=_get_recent, reverse=True)
