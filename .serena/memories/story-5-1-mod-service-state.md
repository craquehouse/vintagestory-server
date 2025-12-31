# Story 5.1: Mod Service and State Management

Status: done

## Summary
Created foundational mod service layer with state persistence and pending restart tracking.

## Services Created

### ModStateManager
- `load()` / `save()` - State persistence with atomic writes
- `get_mod()` / `list_mods()` - Query mod state
- `import_mod(zip_path)` - Extract modinfo.json, cache metadata
- `sync_state_with_disk()` - Reconcile state with filesystem
- Zip slip protection with Path.resolve()

### PendingRestartState
- `require_restart(reason)` - Set pending restart flag
- `clear_restart()` - Clear on successful restart
- Integrated with ServerService lifecycle

### ModService
- `list_mods()` / `get_mod(slug)` - Query mods with metadata
- `enable_mod()` / `disable_mod()` - File suffix approach (.disabled)
- `get_mod_service()` - Singleton DI factory

## State Structure
```
/data/vsmanager/
├── state/
│   ├── mods.json           # State index: filename → {slug, version, enabled}
│   └── mods/<slug>/<ver>/  # Cached modinfo.json
```

## State Index Format
```json
{
  "modfile.zip": {
    "slug": "smithingplus",
    "version": "1.8.3",
    "enabled": true,
    "installed_at": "2025-12-29T10:30:00Z"
  }
}
```

## Tests
76 new tests (models: 11, state: 47, service: 18)
