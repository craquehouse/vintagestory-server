"""Client for VintageStory mod database API.

This module provides an async client for interacting with the VintageStory
mod database at mods.vintagestory.at, handling mod lookups and downloads.
"""

from __future__ import annotations

import asyncio
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Literal, TypeGuard, cast
from urllib.parse import urlparse

import httpx
import structlog

from vintagestory_api.models.moddb import (
    ModDict,
    ReleaseDict,
    normalize_mod,
    normalize_mod_list,
)
from vintagestory_api.services.mod_release_selection import select_install_release

if TYPE_CHECKING:
    from vintagestory_api.services.cache_eviction import CacheEvictionService

logger = structlog.get_logger()

# Type alias for compatibility status
CompatibilityStatus = Literal["compatible", "not_verified", "incompatible"]

# Sort options for browse endpoint
SortOption = Literal["downloads", "trending", "recent", "name"]


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

    asset_id: int
    """Unique asset ID for constructing reliable moddb URLs."""


@dataclass(frozen=True)
class ResolvedInstall:
    """The release an install will download, known before the download (Story 17.3)."""

    slug: str
    """The requested slug after `extract_slug`, for logs and errors."""

    mod_id: str
    """The install mod ID (`select_install_release`, Epic 17 ADR-2)."""

    release: ReleaseDict
    """The selected release."""

    file_id: int
    """The selected release's file ID."""

    asset_id: int
    """The mod database entry's asset ID."""

    releases: list[ReleaseDict]
    """Every release of the mod database entry, newest first, as `get_mod` returned them.

    Story 17.4 stores them as the new mod's update record, so the Installed list shows
    its update status without another lookup.
    """


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


class ModReleaseNotDownloadableError(ModApiError):
    """Raised when the release to install has no downloadable file (Epic 17 ADR-2).

    `version` is the named version, or None when no version was named and no release
    of the mod ID has a file.
    """

    def __init__(self, slug: str, version: str | None = None) -> None:
        self.slug = slug
        self.version = version
        if version is None:
            message = f"Mod '{slug}' has no release with a downloadable file in the mod database"
        else:
            message = (
                f"Version '{version}' of mod '{slug}' has no downloadable file in the mod database"
            )
        super().__init__(message)


class ExternalApiError(ModApiError):
    """Raised when the external mod API is unavailable."""

    def __init__(self, message: str = "VintageStory mod API is unavailable") -> None:
        super().__init__(message)


class DownloadError(ModApiError):
    """Raised when a mod download fails."""

    def __init__(self, slug: str, message: str = "Download failed") -> None:
        self.slug = slug
        super().__init__(f"Failed to download mod '{slug}': {message}")


def safe_release_filename(filename: str) -> str:
    """Return a mod database release filename that is safe to use as a file name.

    Release filenames are chosen by mod authors (Story 14.0), so only the final path
    component is kept, splitting on both "/" and "\\".

    Raises:
        ValueError: If nothing usable remains (empty, ".", "..") or the name contains NUL.
    """
    name = filename.replace("\\", "/").rsplit("/", 1)[-1]
    if name in ("", ".", "..") or "\x00" in name:
        raise ValueError(f"Unusable release filename: {filename!r}")
    return name


class GameVersionNotFoundError(ModApiError):
    """Raised when a game version string is not found in the version list."""

    def __init__(self, version: str) -> None:
        self.version = version
        super().__init__(f"Game version '{version}' not found")


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


def _is_json_object(value: object) -> TypeGuard[dict[str, object]]:
    """Whether parsed JSON is an object. `json.loads` only builds dicts with string keys."""
    return isinstance(value, dict)


def _is_json_array(value: object) -> TypeGuard[list[object]]:
    """Whether parsed JSON is an array."""
    return isinstance(value, list)


@dataclass(frozen=True)
class VersionListing:
    """The mod database listing filtered by one game version tag, as cached (Story 18.3).

    Attributes:
        mods: The normalized listing items.
        mod_ids: The items' numeric mod IDs (an item without one, normalized to 0, is left out).
        fetched_at: When the listing was fetched.
    """

    mods: list[ModDict]
    mod_ids: frozenset[int]
    fetched_at: datetime


class ModApiClient:
    """Async client for VintageStory mod database API.

    Provides methods for looking up mods and downloading mod files
    from mods.vintagestory.at.

    Attributes:
        BASE_URL: Base URL for the mod API.
        DOWNLOAD_URL: URL for file downloads.
        DEFAULT_TIMEOUT: Default timeout for API calls (30s).
        DOWNLOAD_TIMEOUT: Timeout for file downloads (120s).
        BROWSE_CACHE_TTL: Cache TTL for browse mod list and for each listing filtered by
            game version (5 minutes).
        GAMEVERSIONS_CACHE_TTL: Cache TTL for the game version list (1 hour).
        VERSION_LISTING_MAX_ENTRIES: Filtered listings kept in memory at most (3); the one
            fetched longest ago is evicted first (Story 18.3).
        VERSION_FLAGS_WAIT: Seconds a browse request waits at most for the game version
            flags (5); a fetch still running then finishes in the background (Story 18.3).
        VERSION_FLAGS_RETRY_AFTER: How long the flag lookup is not retried after a failure
            or a timeout (60 seconds; Story 18.3).
    """

    BASE_URL = "https://mods.vintagestory.at/api"
    DOWNLOAD_URL = "https://mods.vintagestory.at/download"
    DEFAULT_TIMEOUT = 30.0
    DOWNLOAD_TIMEOUT = 120.0
    BROWSE_CACHE_TTL = timedelta(minutes=5)
    GAMEVERSIONS_CACHE_TTL = timedelta(hours=1)
    VERSION_LISTING_MAX_ENTRIES = 3
    VERSION_FLAGS_WAIT = 5.0
    VERSION_FLAGS_RETRY_AFTER = timedelta(seconds=60)

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

        # In-memory cache for game versions list
        self._gameversions_cache: dict[str, int] | None = None
        self._gameversions_cache_time: datetime | None = None

        # Story 18.3: listings filtered by game version tag ID (expired copies stay until
        # replaced or evicted), the fetch running for each tag ID, and when the flag
        # lookup last failed
        self._version_listings: dict[int, VersionListing] = {}
        self._version_fetches: dict[int, asyncio.Task[VersionListing]] = {}
        self._version_flags_failed_at: datetime | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.DEFAULT_TIMEOUT,
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        """Cancel any filtered listing fetch still running, then close the HTTP client."""
        fetches = list(self._version_fetches.values())
        for task in fetches:
            task.cancel()
        if fetches:
            await asyncio.gather(*fetches, return_exceptions=True)
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
            ExternalApiError: If the mod API is unavailable, or answers with a body that is
                not a JSON object or an unexpected status (VSS-d15).
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
            try:
                payload: object = response.json()
            except ValueError as e:
                logger.error("mod_api_invalid_body", slug=slug, http_status=response.status_code)
                raise ExternalApiError(
                    f"VintageStory mod API returned an unreadable response "
                    f"(HTTP {response.status_code})"
                ) from e
            if not isinstance(payload, dict):
                logger.error("mod_api_invalid_body", slug=slug, http_status=response.status_code)
                raise ExternalApiError("VintageStory mod API returned an unexpected response")
            data = cast(ModDict, payload)

            # CRITICAL: statuscode is STRING, not int!
            if data.get("statuscode") == "200":
                # Story 17.1 (Epic 17 ADR-1): every entry is normalized where it enters
                mod = normalize_mod(data.get("mod"))
                if mod is None:
                    logger.error(
                        "mod_api_invalid_body", slug=slug, http_status=response.status_code
                    )
                    raise ExternalApiError("VintageStory mod API returned an unexpected response")
                logger.debug("mod_lookup_success", slug=slug)
                return mod

            if data.get("statuscode") == "404":
                logger.debug("mod_not_found", slug=slug)
                return None

            # Unexpected status: raise, as the other fetchers do. Returning None would
            # read as "not found" to callers (VSS-d15).
            logger.warning(
                "unexpected_api_status",
                slug=slug,
                statuscode=data.get("statuscode"),
            )
            raise ExternalApiError(
                f"VintageStory mod API returned unexpected status: {data.get('statuscode')}"
            )

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

        This is the full download flow: `resolve_install`, then `download_resolved`.
        1. Lookup mod by slug
        2. Select release with `select_install_release` (Epic 17 ADR-2): only releases
           of the install mod ID with a downloadable file; "latest" is the newest
           stable one
        3. Download file to cache with atomic write

        Args:
            slug: Mod slug (e.g., "smithingplus").
            version: Specific version to download, or None for the newest stable
                release of the mod ID that has a downloadable file.

        Returns:
            DownloadResult with path and metadata, or None on failure.

        Raises:
            ModNotFoundError: If the mod doesn't exist.
            ModVersionNotFoundError: If no release of the mod ID has that version.
            ModReleaseNotDownloadableError: If the named release has no file, or no
                version was named and no release of the mod ID has a file.
            ExternalApiError: If the mod API is unavailable.
            DownloadError: If the download fails.
        """
        resolved = await self.resolve_install(slug, version)
        return await self.download_resolved(resolved)

    async def resolve_install(self, slug: str, version: str | None = None) -> ResolvedInstall:
        """Lookup mod and select the release an install downloads, without downloading.

        Steps 1 and 2 of `download_mod`. Install calls this first so that it knows the
        install mod ID, and can refuse a mod that is busy or installed, before the download.

        Args:
            slug: Mod slug or URL (e.g., "smithingplus").
            version: Specific version, or None for the newest stable release of the
                mod ID that has a downloadable file.

        Raises:
            ModNotFoundError: If the mod doesn't exist or has no releases.
            ModVersionNotFoundError: If no release of the mod ID has that version.
            ModReleaseNotDownloadableError: If the named release has no file, or no
                version was named and no release of the mod ID has a file.
            ExternalApiError: If the mod API is unavailable.
        """
        # Extract slug from URL if needed
        slug = extract_slug(slug)

        # 1. Lookup mod
        mod = await self.get_mod(slug)
        if mod is None:
            raise ModNotFoundError(slug)

        releases: list[ReleaseDict] = mod["releases"]
        if not releases:
            raise ModNotFoundError(slug)

        # 2. Select release (Epic 17 ADR-2)
        selection = select_install_release(slug, releases, version)
        if selection.refusal == "version_not_found" and version is not None:
            raise ModVersionNotFoundError(slug, version)
        release = selection.release
        file_id = selection.file_id
        if release is None or file_id is None:
            raise ModReleaseNotDownloadableError(slug, version)
        logger.debug(
            "selected_install_release",
            slug=slug,
            mod_id=selection.mod_id,
            version=release["modversion"],
            requested_version=version,
        )
        return ResolvedInstall(
            slug=slug,
            mod_id=selection.mod_id,
            release=release,
            file_id=file_id,
            asset_id=mod["assetid"],
            releases=releases,
        )

    async def download_resolved(self, resolved: ResolvedInstall) -> DownloadResult:
        """Download a resolved release into the cache (step 3 of `download_mod`).

        Raises:
            DownloadError: If the download fails.
        """
        path = await self.download_release_file(
            resolved.slug, resolved.file_id, resolved.release["filename"]
        )
        return DownloadResult(
            path=path,
            filename=path.name,
            version=resolved.release["modversion"],
            release=resolved.release,
            asset_id=resolved.asset_id,
        )

    async def download_release_file(self, slug: str, fileid: int, filename: str) -> Path:
        """Download one release file into the mod cache, atomically.

        Args:
            slug: Mod slug, for logging and errors.
            fileid: The release's file ID.
            filename: The release's filename from the mod database (sanitized here).

        Returns:
            Path of the downloaded file in the cache.

        Raises:
            ModReleaseNotDownloadableError: If `fileid` is not a positive file ID.
            DownloadError: If the filename is unusable or the download fails.
        """
        if fileid <= 0:
            raise ModReleaseNotDownloadableError(slug)
        try:
            safe_name = safe_release_filename(filename)
        except ValueError as e:
            logger.error("mod_download_unsafe_filename", slug=slug, filename=filename)
            raise DownloadError(slug, str(e)) from e

        dest_path = self._mods_cache / safe_name
        temp_path = dest_path.with_name(dest_path.name + ".tmp")

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

            logger.info("mod_download_complete", slug=slug, fileid=fileid, filename=safe_name)

            # Run cache eviction after successful download
            if self._cache_eviction is not None:
                eviction_result = self._cache_eviction.evict_if_needed()
                if eviction_result.files_evicted > 0:
                    logger.debug(
                        "cache_eviction_after_download",
                        files_evicted=eviction_result.files_evicted,
                        bytes_freed=eviction_result.bytes_freed,
                    )

            return dest_path

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
            List of normalized mod dictionaries from the API.

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
                # Story 17.1 (Epic 17 ADR-1): normalized before it is cached. A missing
                # or non-list `mods` is an error, not an empty (and cached) list.
                mods = normalize_mod_list(data.get("mods"))
                if mods is None:
                    logger.error("mod_api_invalid_body_browse")
                    raise ExternalApiError("VintageStory mod API returned an unexpected response")
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
        """Clear the browse mod list cache and the filtered listings.

        This forces the next call to get_all_mods() or get_mods_by_version() to fetch
        fresh data and resets the flag lookup's retry pause. A filtered listing fetch
        that is running is left to finish.
        """
        self._browse_cache = None
        self._browse_cache_time = None
        self._version_listings.clear()
        self._version_flags_failed_at = None
        logger.debug("browse_cache_cleared")

    def _fresh_version_listing(self, version_tagid: int) -> VersionListing | None:
        """The cached listing for a tag if it has not expired."""
        listing = self._version_listings.get(version_tagid)
        if listing is None or datetime.now() - listing.fetched_at >= self.BROWSE_CACHE_TTL:
            return None
        return listing

    async def _refresh_version_listing(self, version_tagid: int) -> VersionListing:
        """Fetch the listing for a tag and cache it, evicting the oldest beyond the limit."""
        mods = await self._fetch_mods_by_version(version_tagid)
        listing = VersionListing(
            mods=mods,
            mod_ids=frozenset(m["modid"] for m in mods if m["modid"]),
            fetched_at=datetime.now(),
        )
        self._version_listings[version_tagid] = listing
        while len(self._version_listings) > self.VERSION_LISTING_MAX_ENTRIES:
            oldest = min(
                self._version_listings, key=lambda t: self._version_listings[t].fetched_at
            )
            del self._version_listings[oldest]
        return listing

    def _version_fetch(self, version_tagid: int) -> asyncio.Task[VersionListing]:
        """The running fetch for a tag, started if there is none. Callers share it."""
        task = self._version_fetches.get(version_tagid)
        if task is None:
            task = asyncio.create_task(self._refresh_version_listing(version_tagid))
            self._version_fetches[version_tagid] = task

            def finished(done: asyncio.Task[VersionListing]) -> None:
                self._version_fetches.pop(version_tagid, None)
                if not done.cancelled():
                    # Retrieved, so a failure nobody awaited is not reported as lost
                    done.exception()

            task.add_done_callback(finished)
        return task

    async def get_mods_by_version(self, version_tagid: int) -> list[ModDict]:
        """Get mods filtered by game version from the VintageStory mod database.

        Results are cached per tag ID for BROWSE_CACHE_TTL, at most
        VERSION_LISTING_MAX_ENTRIES of them (Story 18.3). Concurrent callers for one
        tag share one request. An expired copy is never served: a failed refresh
        raises, as get_all_mods() does.

        Args:
            version_tagid: The game version tagid to filter by.

        Returns:
            List of normalized mod dictionaries with a release tagged for the version.

        Raises:
            ExternalApiError: If the mod API is unavailable.
        """
        listing = self._fresh_version_listing(version_tagid)
        if listing is None:
            # Shielded: one caller's cancellation does not cancel the shared fetch
            listing = await asyncio.shield(self._version_fetch(version_tagid))
        return listing.mods

    async def get_version_mod_ids(self, game_version: str) -> frozenset[int] | None:
        """The mod IDs of the entries with a release tagged for a game version (Story 18.3).

        Used for the browse cards' flags; never raises ExternalApiError. Waits at most
        VERSION_FLAGS_WAIT for the game version list and the filtered listing; a fetch
        still running then finishes in the background and fills the cache. After a
        failure or a timeout, no new attempt is made for VERSION_FLAGS_RETRY_AFTER.

        Args:
            game_version: A game version name without a "v" prefix (e.g. "1.22.7").

        Returns:
            The set from an unexpired copy or a fresh fetch; the last (expired) copy when
            the refresh fails, is slow or is paused; None when the version has no tag in
            the mod database or nothing is known.
        """
        tagid: int | None = None
        if self._is_gameversions_cache_valid():
            tagid = (self._gameversions_cache or {}).get(game_version)
            if tagid is None:
                return None
            listing = self._fresh_version_listing(tagid)
            if listing is not None:
                return listing.mod_ids
        failed_at = self._version_flags_failed_at
        if failed_at is None or datetime.now() - failed_at >= self.VERSION_FLAGS_RETRY_AFTER:
            try:
                async with asyncio.timeout(self.VERSION_FLAGS_WAIT):
                    tagid = (await self.get_game_versions()).get(game_version)
                    if tagid is None:
                        return None
                    return (await asyncio.shield(self._version_fetch(tagid))).mod_ids
            except (TimeoutError, ExternalApiError) as e:
                self._version_flags_failed_at = datetime.now()
                logger.warning(
                    "version_flags_unavailable",
                    game_version=game_version,
                    tagid=tagid,
                    error=str(e) or type(e).__name__,
                )
        if tagid is None:
            # An expired map is still a map
            tagid = (self._gameversions_cache or {}).get(game_version)
        stale = self._version_listings.get(tagid) if tagid is not None else None
        return stale.mod_ids if stale is not None else None

    async def _fetch_mods_by_version(self, version_tagid: int) -> list[ModDict]:
        """Fetch the listing filtered by a game version tag from the mod database.

        Uncached; get_mods_by_version() and get_version_mod_ids() cache the result.

        Args:
            version_tagid: The game version tagid to filter by.

        Returns:
            List of normalized mod dictionaries compatible with the specified version.

        Raises:
            ExternalApiError: If the mod API is unavailable.
        """
        client = await self._get_client()
        try:
            response = await client.get(
                f"{self.BASE_URL}/mods",
                params={"gameversion": version_tagid},
            )

            # Check HTTP status before parsing JSON
            if response.status_code != 200:
                logger.warning(
                    "mod_api_http_error_mods_by_version",
                    status_code=response.status_code,
                    version_tagid=version_tagid,
                )
                raise ExternalApiError(
                    f"VintageStory mod API returned HTTP {response.status_code}"
                )

            try:
                data = response.json()
            except ValueError as e:
                logger.error(
                    "mod_api_json_error_mods_by_version", version_tagid=version_tagid
                )
                raise ExternalApiError(
                    "VintageStory mod API returned invalid JSON"
                ) from e

            # CRITICAL: statuscode is STRING, not int!
            if data.get("statuscode") == "200":
                # Story 17.1 (Epic 17 ADR-1): normalized where it enters
                mods = normalize_mod_list(data.get("mods"))
                if mods is None:
                    logger.error(
                        "mod_api_invalid_body_mods_by_version", version_tagid=version_tagid
                    )
                    raise ExternalApiError("VintageStory mod API returned an unexpected response")
                logger.debug(
                    "mods_by_version_fetched",
                    version_tagid=version_tagid,
                    count=len(mods),
                )
                return mods

            # Unexpected status - log and raise
            logger.warning(
                "unexpected_api_status_mods_by_version",
                statuscode=data.get("statuscode"),
                version_tagid=version_tagid,
            )
            raise ExternalApiError(
                f"VintageStory mod API returned unexpected status: {data.get('statuscode')}"
            )

        except httpx.TimeoutException as e:
            logger.error("mod_api_timeout_mods_by_version", version_tagid=version_tagid)
            raise ExternalApiError("VintageStory mod API request timed out") from e

        except httpx.ConnectError as e:
            logger.error(
                "mod_api_connection_error_mods_by_version", version_tagid=version_tagid
            )
            raise ExternalApiError(
                "Could not connect to VintageStory mod API"
            ) from e

        except httpx.HTTPError as e:
            logger.error(
                "mod_api_error_mods_by_version",
                version_tagid=version_tagid,
                error=str(e),
            )
            raise ExternalApiError(
                f"VintageStory mod API error: {e}"
            ) from e

    def _is_gameversions_cache_valid(self) -> bool:
        """Check if the game versions cache is still valid.

        Returns:
            True if cache exists and hasn't expired, False otherwise.
        """
        if self._gameversions_cache is None or self._gameversions_cache_time is None:
            return False
        return datetime.now() - self._gameversions_cache_time < self.GAMEVERSIONS_CACHE_TTL

    async def get_game_versions(
        self, force_refresh: bool = False
    ) -> dict[str, int]:
        """Get game versions mapping from version string to tagid.

        This method fetches the game versions list from the VintageStory API
        and caches it in memory for 1 hour (game versions change infrequently).

        Args:
            force_refresh: If True, bypass the cache and fetch fresh data.

        Returns:
            Dictionary mapping version strings (e.g., "1.21.3") to tagids.

        Raises:
            ExternalApiError: If the mod API is unavailable.
        """
        # Return cached data if valid and not forcing refresh
        if not force_refresh and self._is_gameversions_cache_valid():
            logger.debug(
                "gameversions_cache_hit", count=len(self._gameversions_cache or {})
            )
            return self._gameversions_cache or {}

        client = await self._get_client()
        try:
            response = await client.get(f"{self.BASE_URL}/gameversions")

            # Check HTTP status before parsing JSON
            if response.status_code != 200:
                logger.warning(
                    "mod_api_http_error_gameversions",
                    status_code=response.status_code,
                )
                raise ExternalApiError(
                    f"VintageStory mod API returned HTTP {response.status_code}"
                )

            try:
                data = response.json()
            except ValueError as e:
                logger.error("mod_api_json_error_gameversions")
                raise ExternalApiError(
                    "VintageStory mod API returned invalid JSON"
                ) from e

            # CRITICAL: statuscode is STRING, not int!
            # Story 18.3: browse reads this list on every request, so a malformed body
            # is an ExternalApiError and a malformed entry is skipped, never a 500
            body: object = data
            if not _is_json_object(body):
                logger.error("mod_api_invalid_body_gameversions")
                raise ExternalApiError("VintageStory mod API returned an unexpected response")
            if body.get("statuscode") == "200":
                versions = body.get("gameversions", [])
                if not _is_json_array(versions):
                    logger.error("mod_api_invalid_body_gameversions")
                    raise ExternalApiError("VintageStory mod API returned an unexpected response")
                # Build mapping from version name to tagid; skip malformed entries
                version_map: dict[str, int] = {}
                for entry in versions:
                    if not _is_json_object(entry):
                        continue
                    name = entry.get("name")
                    tagid = entry.get("tagid")
                    if (
                        isinstance(name, str)
                        and isinstance(tagid, int)
                        and not isinstance(tagid, bool)
                    ):
                        version_map[name] = tagid
                self._gameversions_cache = version_map
                self._gameversions_cache_time = datetime.now()
                logger.debug("gameversions_cache_refreshed", count=len(version_map))
                return version_map

            # Unexpected status - log and raise
            logger.warning(
                "unexpected_api_status_gameversions",
                statuscode=body.get("statuscode"),
            )
            raise ExternalApiError(
                f"VintageStory mod API returned unexpected status: {body.get('statuscode')}"
            )

        except httpx.TimeoutException as e:
            logger.error("mod_api_timeout_gameversions")
            raise ExternalApiError("VintageStory mod API request timed out") from e

        except httpx.ConnectError as e:
            logger.error("mod_api_connection_error_gameversions")
            raise ExternalApiError(
                "Could not connect to VintageStory mod API"
            ) from e

        except httpx.HTTPError as e:
            logger.error("mod_api_error_gameversions", error=str(e))
            raise ExternalApiError(
                f"VintageStory mod API error: {e}"
            ) from e

    def clear_gameversions_cache(self) -> None:
        """Clear the game versions cache.

        This forces the next call to get_game_versions() to fetch fresh data.
        """
        self._gameversions_cache = None
        self._gameversions_cache_time = None
        logger.debug("gameversions_cache_cleared")


def _get_downloads(m: ModDict) -> int:
    """Get downloads count from a normalized mod dict."""
    return m["downloads"]


def _get_trending(m: ModDict) -> int:
    """Get trending points from a normalized mod dict."""
    return m["trendingpoints"]


def _get_recent(m: ModDict) -> str:
    """Get last released date from a normalized mod dict (optional, so "" when unset)."""
    return m["lastreleased"] or ""


def _name_sort_key(m: ModDict) -> tuple[str, str, int]:
    """Get the Name (A-Z) sort key from a mod dict (Story 16.8).

    Ignores surrounding spaces, letter case and accents (combining marks after NFKD
    normalization). Equal names are ordered by the stripped name, then by asset ID,
    so the order is the same whatever order the mod database lists them in.
    A null or missing name sorts as empty.
    """
    name = str(m.get("name") or "").strip()
    decomposed = unicodedata.normalize("NFKD", name)
    base = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return (base.casefold(), name, int(m.get("assetid") or 0))


def sort_mods(
    mods: list[ModDict],
    sort_by: SortOption = "recent",
) -> list[ModDict]:
    """Sort a list of mods by the specified criteria.

    Args:
        mods: List of normalized mod dictionaries (`ModApiClient.get_all_mods`).
        sort_by: Sort criteria - "downloads", "trending", "recent", or "name".

    Returns:
        Sorted list of mods (descending order, except name which is ascending and
        ignores surrounding spaces, letter case and accents).
    """
    if sort_by == "downloads":
        return sorted(mods, key=_get_downloads, reverse=True)
    elif sort_by == "trending":
        return sorted(mods, key=_get_trending, reverse=True)
    elif sort_by == "name":
        return sorted(mods, key=_name_sort_key)
    else:  # recent
        return sorted(mods, key=_get_recent, reverse=True)


def search_mods(mods: list[ModDict], search: str) -> list[ModDict]:
    """Filter mods by search term.

    Searches across name, author, summary, and tags (case-insensitive).

    Args:
        mods: List of normalized mod dictionaries (`ModApiClient.get_all_mods`).
        search: Search term to filter by. Empty string returns all mods.

    Returns:
        Filtered list of mods matching the search term.
    """
    search = search.strip().lower()
    if not search:
        return mods

    results: list[ModDict] = []
    for mod in mods:
        # Check name
        name: str = mod["name"].lower()
        if search in name:
            results.append(mod)
            continue

        # Check author
        author: str = mod["author"].lower()
        if search in author:
            results.append(mod)
            continue

        # Check summary
        summary: str = (mod["summary"] or "").lower()
        if search in summary:
            results.append(mod)
            continue

        # Check tags
        tags: list[str] = mod["tags"]
        if any(search in tag.lower() for tag in tags):
            results.append(mod)
            continue

    return results
