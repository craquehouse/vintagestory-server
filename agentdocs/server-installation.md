# VintageStory Server Installation

_Reference documentation for AI agents implementing server installation (Epic 3, Story 3.1)._

**Source:** Patterns extracted from [quartzar/vintage-story-server](https://github.com/quartzar/vintage-story-server)

---

## Version API

VintageStory provides JSON APIs to discover available versions:

### Endpoints

| Channel | URL |
|---------|-----|
| Stable | `https://api.vintagestory.at/stable.json` |
| Unstable | `https://api.vintagestory.at/unstable.json` |

### Response Structure

```json
{
  "1.21.6": {
    "linuxserver": {
      "filename": "vs_server_linux-x64_1.21.6.tar.gz",
      "filesize": "40.2 MB",
      "md5": "checksum_here",
      "urls": {
        "cdn": "https://cdn.vintagestory.at/gamefiles/stable/vs_server_linux-x64_1.21.6.tar.gz",
        "local": "https://vintagestory.at/api/gamefiles/stable/vs_server_linux-x64_1.21.6.tar.gz"
      },
      "latest": true
    },
    "windowsserver": { ... },
    "windows": { ... },
    "linux": { ... },
    "mac": { ... }
  },
  "1.21.5": { ... }
}
```

### Key Fields

| Field | Description |
|-------|-------------|
| `filename` | Archive filename |
| `filesize` | Human-readable size (e.g., "40.2 MB") |
| `md5` | MD5 checksum for verification |
| `urls.cdn` | Primary CDN download URL |
| `urls.local` | Fallback download URL |
| `latest` | Boolean flag on newest version |

### Getting Latest Version

```python
import httpx

async def get_latest_stable_version() -> str:
    """Fetch latest stable server version."""
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://api.vintagestory.at/stable.json")
        versions = resp.json()
        # Keys are version strings, first key is latest
        return next(iter(versions.keys()))
```

**Note:** Version keys are ordered newest-first, so `keys()[0]` is the latest.

---

## Download URLs

### URL Pattern

```
https://cdn.vintagestory.at/gamefiles/{channel}/vs_server_linux-x64_{version}.tar.gz
```

| Channel | Base URL |
|---------|----------|
| Stable | `https://cdn.vintagestory.at/gamefiles/stable/` |
| Unstable | `https://cdn.vintagestory.at/gamefiles/unstable/` |

### Platform Variants

| Platform | Filename Pattern |
|----------|------------------|
| Linux Server | `vs_server_linux-x64_{version}.tar.gz` |
| Windows Server | `vs_server_win-x64_{version}.zip` |

### Example URLs

```
# Stable server v1.21.6
https://cdn.vintagestory.at/gamefiles/stable/vs_server_linux-x64_1.21.6.tar.gz

# Unstable server v1.22.0-pre.1
https://cdn.vintagestory.at/gamefiles/unstable/vs_server_linux-x64_1.22.0-pre.1.tar.gz
```

---

## Installation Process

### 1. Check URL Availability

Before downloading, verify the version exists in the channel:

```python
async def check_version_available(version: str, channel: str = "stable") -> bool:
    """Check if version exists in channel without downloading."""
    url = f"https://cdn.vintagestory.at/gamefiles/{channel}/vs_server_linux-x64_{version}.tar.gz"
    async with httpx.AsyncClient() as client:
        resp = await client.head(url)
        return resp.status_code == 200
```

### 2. Download with Fallback

Try stable channel first, fall back to unstable:

```python
async def download_server(version: str, dest_dir: Path) -> Path:
    """Download server tarball with channel fallback."""
    channels = ["stable", "unstable"]

    for channel in channels:
        url = f"https://cdn.vintagestory.at/gamefiles/{channel}/vs_server_linux-x64_{version}.tar.gz"
        async with httpx.AsyncClient() as client:
            resp = await client.head(url)
            if resp.status_code == 200:
                # Download the file
                resp = await client.get(url)
                tarball = dest_dir / f"vs_server_linux-x64_{version}.tar.gz"
                tarball.write_bytes(resp.content)
                return tarball

    raise ValueError(f"Version {version} not found in any channel")
```

### 3. Extract Tarball

```python
import tarfile

def extract_server(tarball: Path, dest_dir: Path) -> None:
    """Extract server tarball."""
    with tarfile.open(tarball, "r:gz") as tar:
        tar.extractall(dest_dir)
    tarball.unlink()  # Remove tarball after extraction
```

### 4. Verify Installation

Check for key files after extraction:

```python
def verify_installation(server_dir: Path) -> bool:
    """Verify server files exist."""
    required_files = [
        "VintagestoryServer.dll",
        "VintagestoryLib.dll",
    ]
    return all((server_dir / f).exists() for f in required_files)
```

---

## Server Execution

### Command Line

```bash
dotnet VintagestoryServer.dll --dataPath /path/to/data
```

### Key Arguments

| Argument | Description |
|----------|-------------|
| `--dataPath` | Directory for world data, configs, mods |
| `--port` | Server port (default: 42420) |
| `--ip` | Bind IP address |

### Default Port

- **Game port:** 42420 (UDP/TCP)

---

## Version Tracking

Track installed version for update detection:

```python
def save_installed_version(server_dir: Path, version: str) -> None:
    """Record installed version for future comparison."""
    (server_dir / "current_version").write_text(version)

def get_installed_version(server_dir: Path) -> str | None:
    """Get currently installed version, if any."""
    version_file = server_dir / "current_version"
    if version_file.exists():
        return version_file.read_text().strip()
    return None
```

---

## Implementation Notes for Epic 3

### Story 3.1: Server Installation Service

**Key implementation points:**

1. **Version Discovery**
   - Fetch from `api.vintagestory.at/stable.json`
   - Parse JSON to get version list and metadata
   - Cache version list with reasonable TTL

2. **Download Logic**
   - Try stable channel first, fallback to unstable
   - Verify MD5 checksum after download
   - Use streaming download for large files (~40MB)
   - Report progress during download

3. **Installation State**
   - Track: `not_installed`, `downloading`, `extracting`, `installed`, `error`
   - Persist installed version in `current_version` file
   - Store installation path in config

4. **Error Handling**
   - Network timeouts during download
   - Invalid/corrupted tarball (MD5 mismatch)
   - Disk space issues during extraction
   - Missing .NET runtime

5. **Security Considerations**
   - Verify MD5 checksum matches API metadata
   - Don't expose download URLs in logs (contains version info)
   - Run server as non-root user (per Docker best practices)

---

## Reference Implementation

See [quartzar/vintage-story-server](https://github.com/quartzar/vintage-story-server) for working Docker implementation:

- `scripts/download_server.sh` - Download with channel fallback
- `scripts/check_and_start.sh` - Version check and server launch
- `Dockerfile` - Container configuration with .NET runtime

---

---

## Additional Implementation Notes (Epic 13)

_These notes were added based on learnings from Story 13.1 implementation._

### Metadata Limitations

The VintageStory version API is purely for download discovery. It does **not** provide:

- ❌ **Release date** - No timestamp of when version was released
- ❌ **Changelog/release notes** - No description of changes
- ❌ **Release title/description** - No human-readable summary
- ❌ **Dependencies/requirements** - No .NET version or system requirements

**UI Implication:** The version browser cannot show "Released X days ago" or changelog content. Display should focus on version numbers, channel (stable/unstable), and installed status.

### Version Ordering

> **Important:** Version keys in the JSON response are **not guaranteed** to be in any particular order.

To find the latest version:

1. Look for the version with `"latest": true` flag
2. Do NOT rely on dictionary iteration order

```python
# CORRECT: Use latest flag
def find_latest(versions: dict) -> str:
    for version, data in versions.items():
        if data.get("linuxserver", {}).get("latest"):
            return version
    return next(iter(versions.keys()))  # fallback

# WRONG: Assume first key is latest
latest = next(iter(versions.keys()))  # Order not guaranteed!
```

### Cache Architecture Pattern

From Story 13.1, the recommended caching pattern for version data:

```text
LatestVersionsCache (singleton)
├── _versions: LatestVersions
│   ├── stable_version: str | None (latest only)
│   └── unstable_version: str | None (latest only)
├── _version_lists: dict[channel, list[VersionInfo]]
│   ├── "stable": [...all stable versions...]
│   └── "unstable": [...all unstable versions...]
└── _cached_at: datetime | None
```

**Why dual storage:**

- `_versions` → Quick access for status page ("update available" check)
- `_version_lists` → Full data for version browser UI

**Cache population:** Background job fetches periodically (versions change infrequently).

---

_Last updated: 2026-01-12 (Epic 13 Technical Preparation - Story 13.0)_
