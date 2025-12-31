# Story 6.3: API Settings Service

**Status:** complete

## Summary
API for viewing and updating API operational settings (auto-start, refresh intervals, env handling).

## Endpoints
- `GET /api/v1alpha1/config/api` - Returns API settings (Admin only)
- `POST /api/v1alpha1/config/api/settings/{key}` - Updates setting (Admin only)

## ApiSettings Model
```python
class ApiSettings(BaseModel):
    auto_start_server: bool = False
    block_env_managed_settings: bool = True
    enforce_env_on_restart: bool = False
    mod_list_refresh_interval: int = 3600  # seconds, 0=disabled
    server_versions_refresh_interval: int = 86400
```

## Files Created/Modified
- `api/src/vintagestory_api/services/api_settings.py` - ApiSettingsService
- `api/src/vintagestory_api/routers/config.py` - Added /config/api endpoints
- `api/src/vintagestory_api/models/errors.py` - API_SETTING_UNKNOWN, API_SETTING_INVALID
- `api/tests/test_api_settings.py` (24 tests)
- `api/tests/test_routers_config.py` (15 router tests)

## Key Features
- Settings file: `settings.data_dir / "state" / "api-settings.json"`
- Returns defaults when file missing
- Atomic file writes (temp + rename)
- Scheduler callback stub for Epic 7 integration

## Security
- Admin-only access (Monitor blocked from all endpoints)
- Uses RequireAdmin dependency
