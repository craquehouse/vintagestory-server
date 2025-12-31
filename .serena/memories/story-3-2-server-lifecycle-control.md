# Story 3.2: Server Lifecycle Control API

Status: done

## Summary
Implemented start/stop/restart server via API with process management and crash detection.

## Endpoints (Admin only)
- `POST /api/v1alpha1/server/start` - Start game server subprocess
- `POST /api/v1alpha1/server/stop` - Graceful shutdown (SIGTERM, then SIGKILL after 10s)
- `POST /api/v1alpha1/server/restart` - Stop then start

## Server State Machine
```
INSTALLED (stopped) → STARTING → RUNNING → STOPPING → INSTALLED
                         ↓ crash                  ↓ force kill
                      INSTALLED               INSTALLED
```

## Key Implementation
- `asyncio.subprocess` for process management
- Background `_monitor_process()` task detects crashes
- `asyncio.Lock` (`_lifecycle_lock`) for thread-safe operations
- Exit code tracking for debugging
- Server command: `dotnet VintagestoryServer.dll --dataPath /data`

## Error Codes Added
- SERVER_START_FAILED, SERVER_STOP_FAILED, SERVER_ALREADY_STOPPED

## Tests
227 tests pass (49 new lifecycle tests)
