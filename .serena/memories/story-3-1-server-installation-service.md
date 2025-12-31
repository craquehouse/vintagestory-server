# Story 3.1: Server Installation Service

Status: done

## Summary
Implemented VintageStory server download, extraction, and installation with progress tracking.

## Endpoints
- `POST /api/v1alpha1/server/install` - Start installation (Admin only)
- `GET /api/v1alpha1/server/install/status` - Poll progress

## Installation Flow
```
not_installed → installing (downloading → extracting → configuring) → installed
                     ↓ (on error)
                   error → not_installed (cleanup)
```

## Key Features
- Streaming download for ~40MB server tarball
- MD5 checksum verification
- Progress tracking (stage + percentage)
- Symlink: /data/server/Mods → /data/mods/
- Default config copy if empty
- asyncio.Lock for race condition protection
- Path traversal protection

## Version API
```
https://api.vintagestory.at/stable.json
https://cdn.vintagestory.at/gamefiles/{channel}/vs_server_linux-x64_{version}.tar.gz
```

## File Structure After Install
```
/data/server/
├── VintagestoryServer.dll
├── VintagestoryLib.dll
├── current_version (contains "1.21.6")
└── Mods/ → ../mods/
```

## Error Codes Added
- INVALID_VERSION, VERSION_NOT_FOUND
- SERVER_ALREADY_INSTALLED, INSTALLATION_FAILED
- INSTALLATION_IN_PROGRESS, CHECKSUM_MISMATCH

## Files Created
- api/src/vintagestory_api/models/server.py
- api/src/vintagestory_api/services/server.py (598 lines)
- api/src/vintagestory_api/routers/server.py
- api/tests/test_server.py (1219 lines)
