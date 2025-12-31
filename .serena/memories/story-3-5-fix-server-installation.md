# Story 3.5: Fix Server Installation in Dev Environment

Status: done

## Summary
Fixed critical installation bug discovered during E2E testing - VintageStory tarballs have malformed USTAR prefixes.

## Root Cause: Malformed USTAR Prefix
VintageStory tarballs contain garbage numeric data (inode numbers like `15070731126`) in the USTAR prefix field. Python's `tarfile` correctly follows USTAR spec and prepends the prefix, causing files to extract to wrong paths like `15070731126/VintagestoryServer.dll`.

## Solution
Custom tarfile filter `_vintagestory_tar_filter()` that:
1. Strips bogus numeric prefixes (8+ digits) from member names
2. Applies standard `data` filter for security

## Data Directory Refactor
Changed from symlink-based approach to VintageStory's native `--dataPath`:

**Old (broken):**
```
/data/server/Mods → /data/mods (symlink broke core mods)
```

**New:**
```
/data/server     - VintageStory installation (with core mods)
/data/serverdata - Persistent game data (--dataPath target)
/data/vsmanager  - API manager state
```

## Files Changed
- api/src/vintagestory_api/config.py - serverdata_dir, vsmanager_dir
- api/src/vintagestory_api/services/server.py - Filter + --dataPath
- Dockerfile, docker-compose.dev.yaml - Build args, directories

## Docker E2E Verified
Server installed, started (PID 66, 15+ seconds uptime), stopped gracefully.
