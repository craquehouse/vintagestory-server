# Story 2.1: API Key Authentication Middleware

Status: done

## Summary
Implemented API key authentication with Admin/Monitor roles using FastAPI dependency injection.

## Key Patterns

### Authentication Flow
```
Request → X-API-Key Header → get_current_user dependency → Role (admin/monitor) → Route Handler
                                      ↓
                                401 Unauthorized (if invalid/missing)
```

### Roles
- **Admin** (VS_API_KEY_ADMIN): Full access to all operations
- **Monitor** (VS_API_KEY_MONITOR, optional): Read-only access

### Security
- `secrets.compare_digest` for timing-safe comparison
- Never log API keys in plaintext
- Proxy-aware IP logging (X-Forwarded-For, X-Real-IP)
- Thread-safe settings with `@lru_cache`

### Error Responses
```python
# 401 Unauthorized
{"detail": {"code": "UNAUTHORIZED", "message": "API key required"}}
```

## Files Created
- api/src/vintagestory_api/middleware/auth.py
- api/src/vintagestory_api/routers/auth.py (/api/v1alpha1/auth/me endpoint)
- api/tests/test_auth.py (17 tests)

## Key Code
```python
# Dependency pattern
async def get_current_user(x_api_key: str | None = Header(None)) -> str:
    if not x_api_key:
        raise HTTPException(401, {"code": "UNAUTHORIZED", "message": "API key required"})
    if secrets.compare_digest(x_api_key, settings.api_key_admin):
        return UserRole.ADMIN
    # ... check monitor key
    raise HTTPException(401, {"code": "UNAUTHORIZED", "message": "Invalid API key"})
```
