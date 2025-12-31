# Story 6.1: ConfigInitService and Template

**Status:** done

## Summary
Auto-generate initial serverconfig.json from template + VS_CFG_* environment variables on first server start.

## Key Features
- Generates config from template when serverconfig.json doesn't exist
- Applies VS_CFG_* env var overrides with type coercion
- Idempotent: existing config never overwritten
- Invalid env values logged as warning, template default used

## Files Created/Modified
- `api/src/vintagestory_api/services/config_init_service.py` - ConfigInitService class
- `api/src/vintagestory_api/services/server.py` - Integration with start()
- `api/tests/test_config_init_service.py` (31 tests)

## Key Methods
- `needs_initialization()` - Checks if serverconfig.json exists
- `initialize_config()` - Loads template, applies overrides, writes atomically
- `_collect_env_overrides()` - Collects VS_CFG_* from os.environ
- `_apply_overrides()` - Uses parse_env_value() for type coercion
- `_set_nested_value()` - Handles dotted keys

## Integration Point
Called from `ServerService._start_server_locked()` BEFORE launching process:
```python
if self._config_init_service.needs_initialization():
    self._config_init_service.initialize_config()
```

## Config Path
`settings.serverdata_dir / "serverconfig.json"` (NOT data_dir/config/)
