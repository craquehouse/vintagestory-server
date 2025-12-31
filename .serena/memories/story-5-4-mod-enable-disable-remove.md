# Story 5.4: Mod Enable/Disable and Remove API

Status: done

## Summary
Implemented mod lifecycle management endpoints for enable, disable, and remove operations.

## Endpoints
- `POST /api/v1alpha1/mods/{slug}/enable` - Admin only
- `POST /api/v1alpha1/mods/{slug}/disable` - Admin only
- `DELETE /api/v1alpha1/mods/{slug}` - Admin only

## Enable/Disable Pattern
- File suffix approach: `.zip` ↔ `.zip.disabled`
- Idempotent: Re-enabling enabled mod returns success (no change)
- Sets pending_restart if server running

## Remove Operation
1. Delete mod file from disk (handles both .zip and .disabled)
2. Remove from state index
3. Clean up cached metadata in `state/mods/<slug>/`
4. Set pending_restart if server running

## Response Models
```python
class EnableResult(BaseModel):
    slug: str
    enabled: bool  # always True after enable
    pending_restart: bool

class DisableResult(BaseModel):
    slug: str
    enabled: bool  # always False after disable
    pending_restart: bool

class RemoveResult(BaseModel):
    slug: str
    pending_restart: bool
```

## Error Codes
- MOD_NOT_INSTALLED (404): Mod not found in local installation
- FORBIDDEN (403): Monitor attempting write operation

## Troubleshooting Discovery
VintageStory ignores `--dataPath` after first run in favor of `serverconfig.json` values. Documented in `agentdocs/vs-server-troubleshooting.md`.
