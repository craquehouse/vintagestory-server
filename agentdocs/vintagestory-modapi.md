# VintageStory Mod Database API Documentation

## Base URL

```
https://mods.vintagestory.at/api/
```

The manager's base address is the setting `VS_MOD_DB_URL` (default `https://mods.vintagestory.at`): it calls `<base>/api/...` and downloads from `<base>/download` (Epic 20 ADR-9).

## Authentication

No authentication required. All endpoints are publicly accessible.

---

## Endpoints

### 1. Get Single Mod

Retrieves detailed information about a specific mod.

```
GET /api/mod/{slug}
```

**Parameters:**
| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| `slug` | string | path | URL-friendly mod identifier (e.g., `smithingplus`) |

**Example Request:**
```bash
curl https://mods.vintagestory.at/api/mod/smithingplus
```

**Response:**
```json
{
  "statuscode": "200",
  "mod": {
    "modid": 2655,
    "assetid": 15312,
    "name": "Smithing Plus",
    "text": "<p>HTML-formatted description...</p>",
    "author": "jayu",
    "urlalias": "smithingplus",
    "logofilename": "https://moddbcdn.vintagestory.at/logo_hash.png",
    "logofile": "logo.png",
    "logofiledb": "logo_hash.png",
    "homepageurl": "https://example.com",
    "sourcecodeurl": "https://github.com/user/repo",
    "issuetrackerurl": "https://github.com/user/repo/issues",
    "wikiurl": "https://wiki.example.com",
    "downloads": 204656,
    "follows": 2348,
    "trendingpoints": 1853,
    "comments": 641,
    "side": "both",
    "type": "mod",
    "created": "2024-10-24 01:06:14",
    "lastreleased": "2025-10-09 21:28:57",
    "lastmodified": "2025-12-26 12:00:00",
    "tags": ["Crafting", "QoL", "Utility"],
    "trailervideourl": "",
    "releases": [...],
    "screenshots": [...]
  }
}
```

---

### 2. List All Mods

Retrieves a summary list of all mods in the database.

```
GET /api/mods
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `tagids` | string | Filter by tag ID (comma-separated) |
| `gameversion` | integer | Only mods with a release for this game version; the value is the version's `tagid` from `/api/gameversions` (a negative number) |

**Example Request:**
```bash
curl https://mods.vintagestory.at/api/mods
```

**Response:**
```json
{
  "statuscode": "200",
  "mods": [
    {
      "modid": 2655,
      "assetid": 15312,
      "name": "Smithing Plus",
      "summary": "Brief description of the mod",
      "modidstrs": ["smithingplus"],
      "author": "jayu",
      "downloads": 204656,
      "follows": 2348,
      "trendingpoints": 1853,
      "comments": 641,
      "side": "both",
      "type": "mod",
      "logo": "https://moddbcdn.vintagestory.at/logo.png",
      "tags": ["Crafting", "QoL"],
      "lastreleased": "2025-10-09 21:28:57",
      "urlalias": "smithingplus"
    }
  ]
}
```

**Notes:**
- Returns ~5000 mods without pagination (as of January 2026)
- Results ordered by `lastreleased` (newest first)
- `logo` and `urlalias` may be `null`

**Filtering by game version:** `GET /api/mods?gameversion=<tagid>` answers with the same item shape as the full listing (checked against `web/e2e/fixtures/moddb/api-mods-gameversion-1.22.7.json`, recorded 2026-11-17, `tagid` `-281569466515455` = 1.22.7). The API uses only this form (`ModApiClient._fetch_mods_by_version`). The undocumented form `?gameversions[]=<tagid>` gives different results and is not used: checked by hand on 2026-11-17 for 1.22.7, `?gameversion=` returned 5,672 mods and `?gameversions[]=` 2,855.

---

### 3. List Game Versions

Retrieves all supported game versions for mod compatibility tagging.

```
GET /api/gameversions
```

**Example Request:**
```bash
curl https://mods.vintagestory.at/api/gameversions
```

**Response:**
```json
{
  "statuscode": "200",
  "gameversions": [
    {"tagid": -1, "name": "1.21.6", "color": "#CCCCCC"},
    {"tagid": -2, "name": "1.21.5", "color": "#CCCCCC"},
    {"tagid": -283, "name": "1.4.4-dev.2", "color": "#CCCCCC"}
  ]
}
```

**Notes:**
- 283 versions available (1.4.4-dev.2 through 1.21.6)
- `tagid` uses negative integers
- Includes stable, RC, pre-release, and dev versions

---

### 4. List Tags

Retrieves all available mod category tags.

```
GET /api/tags
```

**Example Request:**
```bash
curl https://mods.vintagestory.at/api/tags
```

**Response:**
```json
{
  "statuscode": "200",
  "tags": [
    {"tagid": 1, "name": "Cheat", "color": "#2462673663"},
    {"tagid": 2, "name": "Clothing", "color": "#2462673663"},
    {"tagid": 3, "name": "Cosmetics", "color": "#2462673663"}
  ]
}
```

**Available Tags (20):**
| Category | Tags |
|----------|------|
| Gameplay | Cheat, QoL, Simplification, Tweak |
| Content | Clothing, Cosmetics, Crafting, Creatures, Food, Furniture, Weapons |
| Technical | Graphics, Library, Technology, Texture Pack, Utility |
| World | Magic, Storage, Worldgen |
| Other | Other |

---

### 5. List Authors

Retrieves all registered mod authors.

```
GET /api/authors
```

**Example Request:**
```bash
curl https://mods.vintagestory.at/api/authors
```

**Response:**
```json
{
  "statuscode": "200",
  "authors": [
    {"userid": 1, "name": "Tyron"},
    {"userid": 2, "name": "miclo"},
    {"userid": 3, "name": "DanaCraluminum"}
  ]
}
```

**Notes:**
- 2,946+ registered authors
- Sequential `userid` assignment

---

### 6. Download File

Downloads a mod release file by file ID.

```
GET /download?fileid={fileid}
```

**Parameters:**
| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| `fileid` | integer | query | Unique file identifier from release object |

**Example Request:**
```bash
curl -O https://mods.vintagestory.at/download?fileid=59176
```

**Notes:**
- Redirects to CDN URL at `moddbcdn.vintagestory.at`
- Returns the actual .zip file

---

## Data Structures

### Mod Object (Full)

| Field | Type | Description |
|-------|------|-------------|
| `modid` | integer | Unique mod identifier |
| `assetid` | integer | Asset reference ID |
| `name` | string | Display name |
| `text` | string | HTML-formatted full description |
| `author` | string | Creator's username |
| `urlalias` | string | URL-friendly slug |
| `logofilename` | string | Full CDN URL to logo |
| `logofile` | string | Original logo filename |
| `logofiledb` | string | Database logo reference |
| `homepageurl` | string | External homepage URL |
| `sourcecodeurl` | string | Source code repository URL |
| `issuetrackerurl` | string | Bug tracker URL |
| `wikiurl` | string | Wiki/docs URL |
| `trailervideourl` | string | Trailer video URL, `""` when there is none |
| `downloads` | integer | Total download count |
| `follows` | integer | User follow count |
| `trendingpoints` | integer | Trending score |
| `comments` | integer | Comment count |
| `side` | string | `"client"`, `"server"`, or `"both"` |
| `type` | string | `"mod"`, `"externaltool"`, or `"other"` |
| `created` | string | Creation timestamp (YYYY-MM-DD HH:MM:SS) |
| `lastreleased` | string | Latest release timestamp |
| `lastmodified` | string | Last update timestamp |
| `tags` | array | Category tag names |
| `releases` | array | Release objects (newest first) |
| `screenshots` | array | Screenshot objects |

`issuetrackerurl` and `wikiurl` are not read by this project's API (they are not in the normalized mod, `models/moddb.py`); `""` when unset (`api-mod-carryon.json` has `wikiurl` `""`, `api-mod-canjewelry.json` has `issuetrackerurl` `""`, recorded 2026-11-17).

`trailervideourl` is `""` for most mods (`api-mod-carryon.json`, `api-mod-instruments.json`, `api-mod-canjewelry.json`, recorded 2026-11-17); the API also treats `null` as no trailer. A set value can be a `youtube-nocookie.com/watch?v=<id>` URL (`api-mod-betterruins.json`: `https://www.youtube-nocookie.com/watch?v=mJHZH_sThDM`), which does not load in a frame: the API rebuilds the `/embed/<id>` URL from the video ID and drops anything else (`trailer_link_url`, `services/mod_media.py`).

`tags` can contain `null` elements: `canjewelry`'s entry `tags` was `["Utility", "Cosmetics", "Crafting", null]` on 2026-11-15 (the same mod in the `/api/mods` listing had no `null`). The API normalizes every entry once, where it enters (Epic 17 ADR-1).

### Release Object

| Field | Type | Description |
|-------|------|-------------|
| `releaseid` | integer | Unique release identifier |
| `mainfile` | string | Full CDN download URL |
| `filename` | string | Original filename |
| `fileid` | integer | File ID for download endpoint |
| `downloads` | integer | Download count for this release |
| `tags` | array | Compatible game versions |
| `modidstr` | string | Mod string identifier |
| `modversion` | string | Semantic version string |
| `created` | string | Release timestamp |
| `changelog` | string | HTML-formatted changelog |

`fileid` can be `null`, with `filename` and `mainfile` `""`: such a release has no downloadable file (`canjewelry` releases `0.2.20`, `0.1.26` and `0.2.0`, 2026-11-15). `changelog` can be `null` (`canjewelry` `0.3.7`).

### Screenshot Object

| Field | Type | Description |
|-------|------|-------------|
| `fileid` | integer | Screenshot file ID |
| `mainfile` | string | Full-size image URL |
| `filename` | string | Original filename |
| `thumbnailfilename` | string | Thumbnail URL |
| `created` | string | Upload timestamp (YYYY-MM-DD HH:MM:SS) |

Checked against `web/e2e/fixtures/moddb/api-mod-betterruins.json` (recorded 2026-11-17, 10 screenshots), in the mod database's key order:

```json
{
  "fileid": 18300,
  "mainfile": "https://moddbcdn.vintagestory.at/9_7078dd7a2f5048080d8ef26c0a763688.jpg",
  "filename": "9.jpg",
  "thumbnailfilename": "https://moddbcdn.vintagestory.at/9_7078dd7a2f5048080d8ef26c0a763688_55_60.jpg",
  "created": "2024-01-28 14:36:08"
}
```

`mainfile` and `thumbnailfilename` are full URLs on `moddbcdn.vintagestory.at`; the thumbnail is the 55x60 version (`_55_60` before the extension). The API passes on only `https` images on that host (`build_screenshots`, `services/mod_media.py`).

---

## Example: "smithingplus" Mod

### API Query

```bash
curl https://mods.vintagestory.at/api/mod/smithingplus
```

### Response (Abbreviated)

```json
{
  "statuscode": "200",
  "mod": {
    "modid": 2655,
    "name": "Smithing Plus",
    "author": "jayu",
    "urlalias": "smithingplus",
    "downloads": 204656,
    "follows": 2348,
    "side": "both",
    "type": "mod",
    "tags": ["Crafting", "QoL", "Utility"],
    "releases": [
      {
        "releaseid": 27001,
        "modversion": "1.8.3",
        "filename": "smithingplus_1.8.3.zip",
        "fileid": 59176,
        "mainfile": "https://moddbcdn.vintagestory.at/smithingplus_1.8.3_bf7bd5e910297357976548542a40fe9a.zip",
        "downloads": 49726,
        "tags": ["1.21.0", "1.21.1", "1.21.2", "1.21.3"],
        "created": "2025-10-09 21:28:57",
        "changelog": "<ul><li>[Fixed] Previous fix caused duplicated descriptions...</li></ul>"
      },
      {
        "releaseid": 26543,
        "modversion": "1.8.2",
        "filename": "smithingplus_1.8.2.zip",
        "fileid": 57894,
        "downloads": 31245,
        "tags": ["1.21.0", "1.21.1"],
        "created": "2025-09-15 14:22:11"
      }
    ],
    "screenshots": [
      {
        "fileid": 54334,
        "filename": "ToolRepair.png",
        "mainfile": "https://moddbcdn.vintagestory.at/ToolRepair_613ab2f037dcd178f1981cf77ae31f86.png",
        "thumbnailfilename": "https://moddbcdn.vintagestory.at/ToolRepair_613ab2f037dcd178f1981cf77ae31f86_55_60.png"
      }
    ]
  }
}
```

### Key Data Points for "smithingplus"

| Property | Value |
|----------|-------|
| Mod ID | 2655 |
| Latest Version | 1.8.3 |
| Latest File ID | 59176 |
| Compatible Game Versions | 1.21.0, 1.21.1, 1.21.2, 1.21.3 |
| Total Downloads | 204,656 |
| Followers | 2,348 |

### Download URL Construction

```
https://mods.vintagestory.at/download?fileid=59176
```

Or direct CDN link:
```
https://moddbcdn.vintagestory.at/smithingplus_1.8.3_bf7bd5e910297357976548542a40fe9a.zip
```

---

## Usage Examples

### Get Latest Version of Any Mod

```python
import requests

def get_latest_version(mod_slug):
    response = requests.get(f"https://mods.vintagestory.at/api/mod/{mod_slug}")
    data = response.json()

    if data['statuscode'] == "200":
        # Releases are ordered newest-first
        latest = data['mod']['releases'][0]
        return {
            'version': latest['modversion'],
            'fileid': latest['fileid'],
            'filename': latest['filename'],
            'download_url': f"https://mods.vintagestory.at/download?fileid={latest['fileid']}",
            'game_versions': latest['tags']
        }
    return None

# Example usage
info = get_latest_version('smithingplus')
print(f"Latest: {info['version']}")
# Output: Latest: 1.8.3
```

### Find Mods Compatible with Game Version

```python
def find_compatible_mods(game_version, mod_list):
    compatible = []
    for mod in mod_list:
        response = requests.get(f"https://mods.vintagestory.at/api/mod/{mod}")
        data = response.json()

        if data['statuscode'] == "200":
            for release in data['mod']['releases']:
                if game_version in release['tags']:
                    compatible.append({
                        'mod': mod,
                        'version': release['modversion'],
                        'fileid': release['fileid']
                    })
                    break
    return compatible
```

### Download Specific Version

```python
def download_mod(mod_slug, version=None):
    response = requests.get(f"https://mods.vintagestory.at/api/mod/{mod_slug}")
    data = response.json()

    if data['statuscode'] != "200":
        return None

    releases = data['mod']['releases']

    # Use latest if no version specified
    if version is None:
        target = releases[0]
    else:
        target = next((r for r in releases if r['modversion'] == version), None)

    if target:
        download_url = f"https://mods.vintagestory.at/download?fileid={target['fileid']}"
        file_response = requests.get(download_url)

        with open(target['filename'], 'wb') as f:
            f.write(file_response.content)

        return target['filename']
    return None

# Download latest
download_mod('smithingplus')

# Download specific version
download_mod('smithingplus', '1.8.2')
```

---

## Error Handling

### Status Codes

| Code | Meaning |
|------|---------|
| `"200"` | Success |
| `"404"` | Mod not found |

**Note:** Status codes are returned as strings, not integers.

### Error Response Example

```json
{
  "statuscode": "404"
}
```

Verified 2026-11-09: a not-found response has no `mod` key at all, so check `statuscode` rather than `mod`.

---

## Rate Limiting

No documented rate limits. However, best practices:
- Cache responses locally
- Avoid rapid repeated requests
- Use CDN URLs (`moddbcdn.vintagestory.at`) for downloads when available

---

## httpx-Based Examples for Epic 5

_Added 2025-12-28 for Story 5.2 implementation_

These examples use `httpx` (the async HTTP client used in the vintagestory-server API).

### Async Mod Lookup

```python
import httpx
from typing import Optional

async def get_mod(slug: str, timeout: float = 30.0) -> Optional[dict]:
    """
    Get mod details by slug using httpx async client.

    Args:
        slug: URL-friendly mod identifier (e.g., "smithingplus")
        timeout: Request timeout in seconds

    Returns:
        Mod dictionary if found, None if not found or error

    Note:
        - statuscode is a STRING ("200", "404"), not an integer
        - releases[0] is always the latest release
        - tags in releases are game version strings
    """
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.get(
                f"https://mods.vintagestory.at/api/mod/{slug}"
            )
            data = response.json()

            # IMPORTANT: statuscode is a string!
            if data.get("statuscode") == "200":
                return data["mod"]
            return None

        except httpx.TimeoutException:
            # Log and return None for graceful degradation
            return None
        except httpx.HTTPError:
            return None
```

### Async File Download with Streaming

```python
from pathlib import Path

async def download_mod_file(
    fileid: int,
    dest_path: Path,
    timeout: float = 120.0
) -> bool:
    """
    Download mod file by fileid using streaming.

    Args:
        fileid: Unique file identifier from release object
        dest_path: Local path to save the file

    Returns:
        True if download successful, False otherwise

    Note:
        - Download endpoint redirects to CDN (moddbcdn.vintagestory.at)
        - follow_redirects=True handles the 302 redirect
    """
    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True
    ) as client:
        try:
            async with client.stream(
                "GET",
                f"https://mods.vintagestory.at/download?fileid={fileid}"
            ) as response:
                response.raise_for_status()

                # Stream to file to handle large mods
                with open(dest_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)

            return True

        except (httpx.HTTPError, IOError):
            # Clean up partial download
            if dest_path.exists():
                dest_path.unlink()
            return False
```

### Compatibility Check

```python
from typing import Literal, Tuple

CompatibilityStatus = Literal["compatible", "not_verified", "incompatible"]

def check_compatibility(
    releases: list[dict],
    game_version: str
) -> Tuple[CompatibilityStatus, Optional[dict]]:
    """
    Check mod compatibility with installed game version.

    Args:
        releases: List of release objects from mod API (newest first)
        game_version: Installed game version (e.g., "1.21.3")

    Returns:
        Tuple of (status, matching_release):
        - "compatible": Exact version match in release tags
        - "not_verified": Same major.minor, different patch
        - "incompatible": No matching version found

    Example:
        >>> releases = [{"modversion": "1.8.3", "tags": ["1.21.0", "1.21.1"]}]
        >>> check_compatibility(releases, "1.21.0")
        ("compatible", {"modversion": "1.8.3", ...})
        >>> check_compatibility(releases, "1.21.3")
        ("not_verified", {"modversion": "1.8.3", ...})
    """
    # Exact match - best case
    for release in releases:
        if game_version in release.get("tags", []):
            return ("compatible", release)

    # Major.minor match (e.g., 1.21.x matches any 1.21.*)
    major_minor = ".".join(game_version.split(".")[:2])
    for release in releases:
        for tag in release.get("tags", []):
            if tag.startswith(major_minor + ".") or tag == major_minor:
                return ("not_verified", release)

    # No match - return latest anyway for user decision
    if releases:
        return ("incompatible", releases[0])
    return ("incompatible", None)
```

### Full Example: Install Latest Compatible Mod

```python
async def install_mod(
    slug: str,
    game_version: str,
    mods_dir: Path
) -> dict:
    """
    Install the latest compatible version of a mod.

    Returns dict with:
        - success: bool
        - version: str (installed version)
        - compatibility: str (compatible/not_verified/incompatible)
        - error: Optional[str]
    """
    # 1. Lookup mod
    mod = await get_mod(slug)
    if not mod:
        return {"success": False, "error": "Mod not found"}

    releases = mod.get("releases", [])
    if not releases:
        return {"success": False, "error": "No releases available"}

    # 2. Check compatibility
    compat_status, release = check_compatibility(releases, game_version)

    if release is None:
        return {"success": False, "error": "No compatible release found"}

    # 3. Download
    filename = release["filename"]
    dest_path = mods_dir / filename

    success = await download_mod_file(release["fileid"], dest_path)
    if not success:
        return {"success": False, "error": "Download failed"}

    return {
        "success": True,
        "version": release["modversion"],
        "compatibility": compat_status,
        "filename": filename
    }
```

---

## CDN Structure

Download files are hosted on:
```
https://moddbcdn.vintagestory.at/
```

File naming pattern:
```
{modname}_{version}_{hash}.zip
```

Example:
```
smithingplus_1.8.3_bf7bd5e910297357976548542a40fe9a.zip
```

---

## Release Behavior

_Verified against the live API on 2026-11-09 for Story 14.0 (10 mods, 464 releases, 10 archives parsed). Fixtures: `api/tests/fixtures/moddb/`._

| Behavior | Detail |
|---|---|
| Order | `releases` are newest first by both `created` and `releaseid` |
| History | Old releases stay listed (up to 89 per mod, back to 1.15-era versions) |
| Publish order is not version order | CarryOn lists `2.0.0-rc.1`, then `1.14.3`, then `2.0.0-pre.8`: maintenance releases on an older line can follow a pre-release |
| Pre-release mod versions | Common; they carry a `-` suffix such as `-rc.1`, `-pre.8` or `-dev.17` |
| Several modids per entry | 225 of 4,852 entries; release `modidstr` varies (`instruments` spans `instruments`, `vsinstruments`, `vsinstrumentsbase`) |
| `modversion` uniqueness | Not unique within an entry; can repeat under different modids |
| `filename` uniqueness | Not unique within an entry (`Auto Map Markers.zip` repeats); names often contain spaces |
| Archive contents | Release `modidstr` and `modversion` matched the archive's `modinfo.json` `modid` and `version` in 10 of 10 archives |
| Lookup keys | `/api/mod/{key}` resolves any release `modidstr` or the numeric ModDB `modid`; `urlalias` does not resolve |
| Removed mods | Return `{"statuscode": "404"}` under every key |
| Game version tags | No empty `tags` seen; pre-release game tags such as `1.22.0-rc.1` are common |

**Implications:** filter releases to the installed modid; identify the installed release by `modidstr` and `modversion`; never key a downloaded file by `filename` alone; treat `filename` as untrusted input.
