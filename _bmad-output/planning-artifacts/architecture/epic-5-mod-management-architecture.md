# Epic 5: Mod Management Architecture

_Added during Epic 5 preparation (2025-12-28)_

This section defines architecture patterns specific to Epic 5 (Mod Management).

## External API Integration Pattern

**VintageStory Mod API Client:**

```python
# api/src/vintagestory_api/services/mod_api.py
import httpx
from typing import Optional
from vintagestory_api.config import get_settings

class ModApiClient:
    """Client for VintageStory mod database API."""

    BASE_URL = "https://mods.vintagestory.at/api"
    DOWNLOAD_URL = "https://mods.vintagestory.at/download"
    DEFAULT_TIMEOUT = 30.0

    def __init__(self, cache: Optional["ModCache"] = None):
        self.cache = cache
        self._client = httpx.AsyncClient(
            timeout=self.DEFAULT_TIMEOUT,
            follow_redirects=True
        )

    async def get_mod(self, slug: str) -> Optional[dict]:
        """Get mod details by slug. Returns None if not found."""
        # Check cache first
        if self.cache:
            cached = await self.cache.get_mod(slug)
            if cached:
                return cached

        try:
            response = await self._client.get(f"{self.BASE_URL}/mod/{slug}")
            data = response.json()

            # Note: Status is STRING, not int
            if data.get("statuscode") == "200":
                mod = data["mod"]
                if self.cache:
                    await self.cache.set_mod(slug, mod)
                return mod
            return None
        except httpx.HTTPError:
            # Graceful degradation - return cached if available
            if self.cache:
                return await self.cache.get_mod(slug, stale_ok=True)
            return None

    async def download_file(self, fileid: int, dest_path: Path) -> bool:
        """Download mod file to destination. Returns success status."""
        try:
            async with self._client.stream(
                "GET",
                f"{self.DOWNLOAD_URL}?fileid={fileid}"
            ) as response:
                response.raise_for_status()
                with open(dest_path, "wb") as f:
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)
            return True
        except httpx.HTTPError:
            return False
```

**Key patterns:**
- Async-first with `httpx.AsyncClient`
- Cache integration at client level
- Graceful degradation on API failures
- Status codes are strings (VintageStory API quirk)
- Follow redirects for download CDN

## Mod Service Boundaries

```
ModService
├── lookup(slug) → ModInfo
│   ├── Check local state for cached or installed mod
│   ├── Query API (via ModApiClient) for details
│   └── Return combined local + remote info
│
├── install(slug, version?) → InstallResult
│   ├── Lookup mod details
│   ├── Select appropriate release (version or latest compatible)
│   ├── Download file to /data/cache/mods/
│   ├── Link mod into /data/serverdata/mods
│   ├── Update mod state
│   └── Set pending_restart flag
│
├── enable(slug) → Result
│   ├── Verify mod exists
│   ├── Update mod state to enabled (softlink)
│   └── Set pending_restart flag
│
├── disable(slug) → Result
│   ├── Verify mod exists
│   ├── Update mod state to disabled (unlink)
│   └── Set pending_restart flag
│
├── remove(slug) → Result
│   ├── disable mod file (unlink)
│   ├── Delete mod file from cache
│   ├── Remove from mod state
│   └── Set pending_restart flag
│
├── update(slug) → Result
│   ├── disable outdated mod file (unlink)
│   ├── Remove from mod state
│   ├── Install current version
│   └── Set pending_restart flag
│
└── list() → List[ModInfo]
    ├── Get local mod state
    ├── Enrich with API data (if available)
    └── Return combined list
```

## Mod State Model

```python
# api/src/vintagestory_api/models/mods.py
from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime

class ModState(BaseModel):
    """State of an installed mod."""
    slug: str
    version: str
    filename: str
    enabled: bool = True
    installed_at: datetime

class ModInfo(BaseModel):
    """Combined local + remote mod information."""
    slug: str
    name: str
    author: str
    description: Optional[str] = None

    # Local state (if installed)
    installed: bool = False
    installed_version: Optional[str] = None
    enabled: Optional[bool] = None

    # Remote info (if available)
    latest_version: Optional[str] = None
    update_available: bool = False
    compatible_versions: list[str] = []
    downloads: Optional[int] = None

class CompatibilityStatus(Literal["compatible", "not_verified", "incompatible"]):
    """Mod compatibility with current game version."""
    pass
```

## Compatibility Check Logic

```python
def check_compatibility(
    releases: list[dict],
    game_version: str
) -> tuple[CompatibilityStatus, Optional[dict]]:
    """
    Check mod compatibility with game version.

    Returns:
        Tuple of (status, matching_release)
        - "compatible": Exact version match in release tags
        - "not_verified": Same major.minor version
        - "incompatible": No matching version
    """
    # Exact match
    for release in releases:
        if game_version in release.get("tags", []):
            return ("compatible", release)

    # Major.minor match (e.g., 1.21.x)
    major_minor = ".".join(game_version.split(".")[:2])
    for release in releases:
        if any(tag.startswith(major_minor) for tag in release.get("tags", [])):
            return ("not_verified", release)

    # No match - return latest anyway
    return ("incompatible", releases[0] if releases else None)
```

## Caching Architecture

**Two-tier caching strategy:**

1. **Artifact Cache** (file-based, permanent)
   - Server tarballs: `/data/cache/servers/`
   - Mod files: `/data/cache/mods/`

2. **API Response Cache** (TTL-based, ephemeral)
   - Mod details: 1 hour TTL
   - Game versions: 24 hour TTL
   - Mod list: 15 minute TTL

```
/data/cache/
├── servers/                    # Server tarballs (permanent)
│   └── vs_server_1.21.6.tar.gz
├── mods/                       # Downloaded mod files (permanent)
│   └── smithingplus_1.8.3.zip
└── api/                        # Cached API responses (TTL-based)
    ├── mod_smithingplus.json   # Individual mod lookup (1h TTL)
    ├── modlist.json            # All mods (15m TTL)
    └── gameversions.json       # Game versions (24h TTL)
```

**Cache implementation pattern:**

```python
# api/src/vintagestory_api/services/cache.py
from pathlib import Path
from datetime import datetime, timedelta
import json

class ModCache:
    """TTL-based cache for mod API responses."""

    TTL_MOD = timedelta(hours=1)
    TTL_VERSIONS = timedelta(hours=24)
    TTL_MODLIST = timedelta(minutes=15)

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir / "api"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    async def get_mod(self, slug: str, stale_ok: bool = False) -> Optional[dict]:
        """Get cached mod data. stale_ok allows expired entries."""
        path = self.cache_dir / f"mod_{slug}.json"
        if not path.exists():
            return None

        data = json.loads(path.read_text())
        expires = datetime.fromisoformat(data["expires"])

        if datetime.utcnow() > expires and not stale_ok:
            return None

        return data["mod"]

    async def set_mod(self, slug: str, mod: dict) -> None:
        """Cache mod data with TTL."""
        path = self.cache_dir / f"mod_{slug}.json"
        expires = datetime.utcnow() + self.TTL_MOD

        data = {
            "mod": mod,
            "expires": expires.isoformat(),
            "cached_at": datetime.utcnow().isoformat()
        }

        # Atomic write
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(data))
        temp.rename(path)
```

## Pending Restart Pattern

**State tracking:**

```python
# In StateManager
class AppState(BaseModel):
    pending_restart: bool = False
    pending_changes: list[str] = []  # Description of changes

    def require_restart(self, reason: str) -> None:
        """Mark that a restart is needed."""
        self.pending_restart = True
        self.pending_changes.append(reason)

    def clear_restart(self) -> None:
        """Clear restart requirement (after successful restart)."""
        self.pending_restart = False
        self.pending_changes = []
```

**API response extension:**

```python
# Success responses include pending_restart status
{
    "status": "ok",
    "data": {...},
    "pending_restart": true  # Added when pending_restart is true
}
```

**Frontend banner component:**

```typescript
// web/src/components/PendingRestartBanner.tsx
function PendingRestartBanner() {
  const { data: status } = useServerStatus();

  if (!status?.pending_restart) return null;

  return (
    <div className="bg-warning p-2 flex justify-between items-center">
      <span>
        ⟳ Restart required · {status.pending_changes?.length || 0} pending changes
      </span>
      <Button onClick={handleRestart}>Restart Now</Button>
    </div>
  );
}
```

**Triggering events:**
- Mod enabled/disabled
- Mod installed/removed
- Config file saved (future)
- Server settings changed (future)

**Clear conditions:**
- Server successfully restarted
- Manual acknowledgment without restart

## Error Handling for External APIs

**Error codes for mod operations:**

```python
# api/src/vintagestory_api/models/errors.py
class ErrorCode:
    # Existing codes...

    # Epic 5 additions
    MOD_NOT_FOUND = "MOD_NOT_FOUND"
    MOD_ALREADY_INSTALLED = "MOD_ALREADY_INSTALLED"
    MOD_NOT_INSTALLED = "MOD_NOT_INSTALLED"
    MOD_INCOMPATIBLE = "MOD_INCOMPATIBLE"
    MOD_DOWNLOAD_FAILED = "MOD_DOWNLOAD_FAILED"
    MOD_API_UNAVAILABLE = "MOD_API_UNAVAILABLE"
    MOD_API_TIMEOUT = "MOD_API_TIMEOUT"
```

**Graceful degradation pattern:**

```python
async def get_mod_info(slug: str) -> ModInfo:
    """Get mod info, gracefully handling API failures."""

    # Always get local state
    local = state_manager.get_mod(slug)

    try:
        remote = await mod_api.get_mod(slug)
    except httpx.TimeoutException:
        # Log but don't fail
        logger.warning("mod_api_timeout", slug=slug)
        remote = None
    except httpx.HTTPError as e:
        logger.warning("mod_api_error", slug=slug, error=str(e))
        remote = None

    # Return combined info
    return ModInfo(
        slug=slug,
        installed=local is not None,
        installed_version=local.version if local else None,
        latest_version=remote["releases"][0]["modversion"] if remote else None,
        # ... etc
    )
```

## Testing Patterns for External APIs

**Use `respx` for httpx mocking:**

```python
# tests/test_mod_api.py
import respx
from httpx import Response

@respx.mock
async def test_get_mod_success():
    respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
        return_value=Response(
            200,
            json={
                "statuscode": "200",
                "mod": {
                    "name": "Smithing Plus",
                    "urlalias": "smithingplus",
                    "releases": [{"modversion": "1.8.3", "tags": ["1.21.3"]}]
                }
            }
        )
    )

    client = ModApiClient()
    mod = await client.get_mod("smithingplus")

    assert mod is not None
    assert mod["name"] == "Smithing Plus"

@respx.mock
async def test_get_mod_api_unavailable():
    respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
        side_effect=httpx.TimeoutException("Connection timeout")
    )

    client = ModApiClient()
    mod = await client.get_mod("smithingplus")

    assert mod is None  # Graceful failure

@respx.mock
async def test_get_mod_with_cache_fallback():
    # First request succeeds and populates cache
    respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
        return_value=Response(200, json={"statuscode": "200", "mod": {...}})
    )

    cache = ModCache(tmp_path)
    client = ModApiClient(cache=cache)

    # First call - populates cache
    mod1 = await client.get_mod("smithingplus")

    # Simulate API failure
    respx.reset()
    respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
        side_effect=httpx.HTTPError("API unavailable")
    )

    # Second call - should return stale cache
    mod2 = await client.get_mod("smithingplus")
    assert mod2 is not None  # From stale cache
```

---
