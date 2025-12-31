# Story 6.2: Game Settings API

**Status:** done

## Summary
API for viewing and updating game server settings via console commands (live) or file updates (restart required).

## Endpoints
- `GET /api/v1alpha1/config/game` - Returns settings with metadata (Admin/Monitor)
- `POST /api/v1alpha1/config/game/settings/{key}` - Updates setting (Admin only)

## Key Features
- Live update via `/serverconfig` console command when server running
- File update for restart-required settings (sets pending_restart flag)
- Env-managed settings (VS_CFG_*) blocked by default
- 15 settings in LIVE_SETTINGS (13 live, 2 restart-required)

## Files Created/Modified
- `api/src/vintagestory_api/services/game_config.py` - GameConfigService
- `api/src/vintagestory_api/routers/config.py` - Config router
- `api/src/vintagestory_api/models/errors.py` - SETTING_UNKNOWN, SETTING_ENV_MANAGED, SETTING_UPDATE_FAILED
- `api/tests/test_game_config.py`, `api/tests/test_routers_config.py`

## Response Format
```json
{
  "status": "ok",
  "data": {
    "key": "ServerName",
    "value": "New Name",
    "method": "console_command",  // or "file_update"
    "pending_restart": false
  }
}
```

## Security
- Command injection prevented via input sanitization
- Type validation using LIVE_SETTINGS value_type
- Password values redacted in logs
