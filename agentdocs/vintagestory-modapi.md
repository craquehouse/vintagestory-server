# VintageStory Mod Database API Documentation

## Base URL

```
https://mods.vintagestory.at/api/
```

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
- Returns 550+ mods without pagination
- Results ordered by `lastreleased` (newest first)
- `logo` and `urlalias` may be `null`

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

### Screenshot Object

| Field | Type | Description |
|-------|------|-------------|
| `fileid` | integer | Screenshot file ID |
| `mainfile` | string | Full-size image URL |
| `filename` | string | Original filename |
| `thumbnailfilename` | string | Thumbnail URL |
| `created` | string | Upload timestamp |

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
  "statuscode": "404",
  "mod": null
}
```

---

## Rate Limiting

No documented rate limits. However, best practices:
- Cache responses locally
- Avoid rapid repeated requests
- Use CDN URLs (`moddbcdn.vintagestory.at`) for downloads when available

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
