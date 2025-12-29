# Caching Patterns

_Implementation guidance for artifact and API response caching_

## Overview

The vintagestory-server uses a two-tier caching strategy:

1. **Artifact Cache** - Permanent storage for downloaded files (server tarballs, mod files)
2. **API Response Cache** - TTL-based cache for external API responses (mod data, versions)

This caching strategy:
- Respects VintageStory developer resources (fewer API calls)
- Improves reliability (cached data available when API is down)
- Reduces install/reinstall time (no re-downloading)

---

## Cache Directory Structure

```
/data/cache/
├── servers/                       # Server tarballs (permanent)
│   ├── vs_server_1.21.6.tar.gz
│   ├── vs_server_1.21.5.tar.gz
│   └── .metadata.json             # Tracks download dates, sizes
│
├── mods/                          # Downloaded mod files (permanent)
│   ├── smithingplus_1.8.3.zip
│   ├── carrycapacity_0.6.5.zip
│   └── .metadata.json             # Tracks source URLs, checksums
│
└── api/                           # Cached API responses (TTL-based)
    ├── mod_smithingplus.json      # Individual mod lookup
    ├── mod_carrycapacity.json
    ├── modlist.json               # All mods list
    ├── gameversions.json          # Game versions list
    └── .cache_index.json          # TTL tracking
```

---

## Artifact Cache

### Purpose

Store downloaded files permanently to avoid re-downloading:
- Server tarballs (~300MB each)
- Mod files (varies, typically 1-50MB)

### Server Tarball Cache

```python
# api/src/vintagestory_api/services/cache.py
from pathlib import Path
from datetime import datetime
import json

class ArtifactCache:
    """Permanent cache for downloaded artifacts."""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.servers_dir = cache_dir / "servers"
        self.mods_dir = cache_dir / "mods"

        # Create directories
        self.servers_dir.mkdir(parents=True, exist_ok=True)
        self.mods_dir.mkdir(parents=True, exist_ok=True)

    # Server tarballs
    def get_server_path(self, version: str) -> Path:
        """Get path to cached server tarball."""
        return self.servers_dir / f"vs_server_{version}.tar.gz"

    def has_server(self, version: str) -> bool:
        """Check if server version is cached."""
        return self.get_server_path(version).exists()

    async def store_server(self, version: str, data: bytes) -> Path:
        """Store server tarball in cache."""
        path = self.get_server_path(version)

        # Atomic write
        temp = path.with_suffix('.tmp')
        temp.write_bytes(data)
        temp.rename(path)

        await self._update_metadata("servers", version, len(data))
        return path

    # Mod files
    def get_mod_path(self, filename: str) -> Path:
        """Get path to cached mod file."""
        return self.mods_dir / filename

    def has_mod(self, filename: str) -> bool:
        """Check if mod file is cached."""
        return self.get_mod_path(filename).exists()

    async def store_mod(
        self,
        filename: str,
        data: bytes,
        slug: str,
        version: str
    ) -> Path:
        """Store mod file in cache."""
        path = self.get_mod_path(filename)

        # Atomic write
        temp = path.with_suffix('.tmp')
        temp.write_bytes(data)
        temp.rename(path)

        await self._update_metadata("mods", filename, len(data), {
            "slug": slug,
            "version": version
        })
        return path

    async def _update_metadata(
        self,
        category: str,
        key: str,
        size: int,
        extra: dict = None
    ) -> None:
        """Update metadata tracking file."""
        metadata_path = getattr(self, f"{category}_dir") / ".metadata.json"

        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text())
        else:
            metadata = {}

        metadata[key] = {
            "cached_at": datetime.utcnow().isoformat(),
            "size_bytes": size,
            **(extra or {})
        }

        # Atomic write
        temp = metadata_path.with_suffix('.tmp')
        temp.write_text(json.dumps(metadata, indent=2))
        temp.rename(metadata_path)
```

### Usage in Server Service

```python
# api/src/vintagestory_api/services/server.py
class ServerService:
    def __init__(self, artifact_cache: ArtifactCache):
        self.cache = artifact_cache

    async def install_server(self, version: str) -> InstallResult:
        # Check cache first
        if self.cache.has_server(version):
            logger.info("server_cache_hit", version=version)
            tarball_path = self.cache.get_server_path(version)
        else:
            # Download and cache
            logger.info("server_downloading", version=version)
            data = await self._download_server(version)
            tarball_path = await self.cache.store_server(version, data)

        # Extract and install
        await self._extract_server(tarball_path)
        return InstallResult(success=True, version=version)
```

---

## API Response Cache

### Purpose

Cache external API responses with TTL to:
- Reduce API calls to mods.vintagestory.at
- Provide stale data when API is unavailable
- Speed up repeated lookups

### TTL Configuration

| Cache Type | TTL | Rationale |
|------------|-----|-----------|
| Individual mod details | 1 hour | Balance freshness vs load |
| All mods list | 15 minutes | List changes frequently |
| Game versions | 24 hours | Rarely changes |
| Tags list | 24 hours | Rarely changes |

### Implementation

```python
# api/src/vintagestory_api/services/api_cache.py
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, TypeVar, Generic
import json

T = TypeVar('T')

class CacheEntry(Generic[T]):
    """Wrapper for cached data with expiry."""
    def __init__(self, data: T, expires: datetime):
        self.data = data
        self.expires = expires

    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires

    @property
    def is_stale(self) -> bool:
        """Stale means expired but might still be usable."""
        return self.is_expired

class ApiResponseCache:
    """TTL-based cache for API responses."""

    # TTL configuration
    TTL_MOD = timedelta(hours=1)
    TTL_MODLIST = timedelta(minutes=15)
    TTL_VERSIONS = timedelta(hours=24)
    TTL_TAGS = timedelta(hours=24)

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir / "api"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.cache_dir / ".cache_index.json"

    def _get_ttl(self, cache_type: str) -> timedelta:
        """Get TTL for cache type."""
        return {
            "mod": self.TTL_MOD,
            "modlist": self.TTL_MODLIST,
            "versions": self.TTL_VERSIONS,
            "tags": self.TTL_TAGS,
        }.get(cache_type, self.TTL_MOD)

    async def get(
        self,
        key: str,
        cache_type: str = "mod",
        stale_ok: bool = False
    ) -> Optional[dict]:
        """
        Get cached data.

        Args:
            key: Cache key (e.g., mod slug)
            cache_type: Type of cache for TTL lookup
            stale_ok: Return expired data if available

        Returns:
            Cached data or None if not found/expired
        """
        path = self.cache_dir / f"{cache_type}_{key}.json"

        if not path.exists():
            return None

        try:
            data = json.loads(path.read_text())
            expires = datetime.fromisoformat(data["_expires"])

            if datetime.utcnow() > expires:
                if stale_ok:
                    return data["_data"]
                return None

            return data["_data"]
        except (json.JSONDecodeError, KeyError):
            # Corrupted cache file
            path.unlink(missing_ok=True)
            return None

    async def set(
        self,
        key: str,
        data: dict,
        cache_type: str = "mod"
    ) -> None:
        """Store data in cache with TTL."""
        path = self.cache_dir / f"{cache_type}_{key}.json"
        ttl = self._get_ttl(cache_type)
        expires = datetime.utcnow() + ttl

        cache_data = {
            "_data": data,
            "_expires": expires.isoformat(),
            "_cached_at": datetime.utcnow().isoformat(),
            "_type": cache_type
        }

        # Atomic write
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(cache_data))
        temp.rename(path)

    async def invalidate(self, key: str, cache_type: str = "mod") -> None:
        """Remove specific entry from cache."""
        path = self.cache_dir / f"{cache_type}_{key}.json"
        path.unlink(missing_ok=True)

    async def clear_expired(self) -> int:
        """Remove all expired entries. Returns count removed."""
        removed = 0
        for path in self.cache_dir.glob("*.json"):
            if path.name.startswith("."):
                continue
            try:
                data = json.loads(path.read_text())
                expires = datetime.fromisoformat(data["_expires"])
                if datetime.utcnow() > expires:
                    path.unlink()
                    removed += 1
            except (json.JSONDecodeError, KeyError):
                path.unlink()
                removed += 1
        return removed

    async def clear_all(self) -> None:
        """Clear entire cache."""
        for path in self.cache_dir.glob("*.json"):
            if not path.name.startswith("."):
                path.unlink()
```

### Usage in Mod API Client

```python
# api/src/vintagestory_api/services/mod_api.py
class ModApiClient:
    def __init__(self, cache: Optional[ApiResponseCache] = None):
        self.cache = cache
        self._client = httpx.AsyncClient(timeout=30.0)

    async def get_mod(self, slug: str) -> Optional[dict]:
        """Get mod details with caching."""
        # Check cache first
        if self.cache:
            cached = await self.cache.get(slug, cache_type="mod")
            if cached:
                return cached

        # Fetch from API
        try:
            response = await self._client.get(
                f"https://mods.vintagestory.at/api/mod/{slug}"
            )
            data = response.json()

            if data.get("statuscode") == "200":
                mod = data["mod"]
                # Store in cache
                if self.cache:
                    await self.cache.set(slug, mod, cache_type="mod")
                return mod
            return None

        except httpx.HTTPError:
            # Try stale cache on API failure
            if self.cache:
                return await self.cache.get(slug, cache_type="mod", stale_ok=True)
            return None

    async def get_all_mods(self) -> Optional[list]:
        """Get all mods with caching."""
        if self.cache:
            cached = await self.cache.get("all", cache_type="modlist")
            if cached:
                return cached

        try:
            response = await self._client.get(
                "https://mods.vintagestory.at/api/mods"
            )
            data = response.json()

            if data.get("statuscode") == "200":
                mods = data["mods"]
                if self.cache:
                    await self.cache.set("all", mods, cache_type="modlist")
                return mods
            return None

        except httpx.HTTPError:
            if self.cache:
                return await self.cache.get("all", cache_type="modlist", stale_ok=True)
            return None
```

---

## Cache Invalidation Strategies

### When to Invalidate

| Event | Invalidation Action |
|-------|-------------------|
| Mod installed/updated | Invalidate that mod's cache |
| Mod list refreshed by user | Invalidate modlist cache |
| Server version changed | No invalidation needed |
| Cache cleanup scheduled | Remove expired entries |

### Scheduled Cleanup

Run cleanup on startup and periodically:

```python
# api/src/vintagestory_api/services/cache.py
import asyncio

class CacheManager:
    def __init__(self, api_cache: ApiResponseCache):
        self.api_cache = api_cache
        self._cleanup_task = None

    async def start(self):
        """Start periodic cache cleanup."""
        # Cleanup on startup
        removed = await self.api_cache.clear_expired()
        logger.info("cache_cleanup_startup", removed=removed)

        # Schedule periodic cleanup (every 6 hours)
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())

    async def stop(self):
        """Stop periodic cache cleanup."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

    async def _periodic_cleanup(self):
        """Run cleanup every 6 hours."""
        while True:
            await asyncio.sleep(6 * 60 * 60)  # 6 hours
            removed = await self.api_cache.clear_expired()
            logger.info("cache_cleanup_periodic", removed=removed)
```

---

## Storage Requirements

### Estimated Storage

| Cache Type | Typical Size | Notes |
|------------|-------------|-------|
| Server tarballs | 300MB each | Keep last 2-3 versions |
| Mod files | 1-50MB each | Depends on installed mods |
| API responses | < 1MB total | JSON files, negligible |

### Cleanup Policies

```python
class ArtifactCache:
    MAX_SERVER_VERSIONS = 3  # Keep at most 3 server versions
    MAX_CACHE_AGE_DAYS = 30  # Remove unused mods after 30 days

    async def cleanup_servers(self) -> int:
        """Remove old server versions, keeping most recent."""
        servers = sorted(
            self.servers_dir.glob("vs_server_*.tar.gz"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        removed = 0
        for server in servers[self.MAX_SERVER_VERSIONS:]:
            server.unlink()
            removed += 1

        return removed

    async def cleanup_unused_mods(self, installed_mods: set[str]) -> int:
        """Remove mod files not currently installed and older than threshold."""
        threshold = datetime.utcnow() - timedelta(days=self.MAX_CACHE_AGE_DAYS)
        metadata_path = self.mods_dir / ".metadata.json"

        if not metadata_path.exists():
            return 0

        metadata = json.loads(metadata_path.read_text())
        removed = 0

        for filename, info in list(metadata.items()):
            slug = info.get("slug", "")

            # Skip if currently installed
            if slug in installed_mods:
                continue

            # Check age
            cached_at = datetime.fromisoformat(info["cached_at"])
            if cached_at < threshold:
                path = self.mods_dir / filename
                if path.exists():
                    path.unlink()
                    removed += 1
                del metadata[filename]

        # Update metadata
        temp = metadata_path.with_suffix('.tmp')
        temp.write_text(json.dumps(metadata, indent=2))
        temp.rename(metadata_path)

        return removed
```

---

## Testing Considerations

### Unit Tests

```python
import pytest
from pathlib import Path

@pytest.fixture
def cache_dir(tmp_path):
    return tmp_path / "cache"

@pytest.fixture
def api_cache(cache_dir):
    return ApiResponseCache(cache_dir)

async def test_cache_set_and_get(api_cache):
    data = {"name": "Test Mod", "version": "1.0.0"}

    await api_cache.set("testmod", data, cache_type="mod")
    result = await api_cache.get("testmod", cache_type="mod")

    assert result == data

async def test_cache_expiry(api_cache):
    # Set with very short TTL for testing
    api_cache.TTL_MOD = timedelta(seconds=1)

    await api_cache.set("testmod", {"data": "test"}, cache_type="mod")

    # Should return data immediately
    assert await api_cache.get("testmod") is not None

    # Wait for expiry
    await asyncio.sleep(1.5)

    # Should return None (expired)
    assert await api_cache.get("testmod") is None

    # Should return stale data if requested
    assert await api_cache.get("testmod", stale_ok=True) is not None

async def test_artifact_cache_server(cache_dir):
    cache = ArtifactCache(cache_dir)

    # Initially not cached
    assert not cache.has_server("1.21.6")

    # Store server
    await cache.store_server("1.21.6", b"fake tarball data")

    # Now cached
    assert cache.has_server("1.21.6")
    assert cache.get_server_path("1.21.6").exists()
```

---

## Configuration

### Environment Variables

```bash
# Cache directory (default: /data/cache)
VS_CACHE_DIR=/data/cache

# TTL overrides (optional, in seconds)
VS_CACHE_TTL_MOD=3600          # 1 hour
VS_CACHE_TTL_MODLIST=900       # 15 minutes
VS_CACHE_TTL_VERSIONS=86400    # 24 hours

# Storage limits
VS_CACHE_MAX_SERVERS=3
VS_CACHE_MAX_AGE_DAYS=30
```

### Settings Integration

```python
# api/src/vintagestory_api/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    cache_dir: Path = Path("/data/cache")
    cache_ttl_mod: int = 3600
    cache_ttl_modlist: int = 900
    cache_ttl_versions: int = 86400
    cache_max_servers: int = 3
    cache_max_age_days: int = 30

    class Config:
        env_prefix = "VS_"
```

---

## Implementation Order

1. **Story 5.1**: Implement `ArtifactCache` for mod files
2. **Story 5.1**: Implement `ApiResponseCache` for mod API
3. **Story 5.2**: Use caches in `ModApiClient`
4. **Future**: Add server tarball caching to `ServerService`

---

_Last updated: 2025-12-28_
