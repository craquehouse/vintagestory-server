# Story 2.2: Role-Based Access Control for API Endpoints

Status: done

## Summary
Implemented RBAC permission system with Admin-only restrictions for write operations and console access.

## Role Permissions
| Role | Read | Write | Console |
|------|------|-------|---------|
| Admin | ✓ | ✓ | ✓ |
| Monitor | ✓ | ✗ (403) | ✗ (403) |

## Key Dependencies
```python
# middleware/permissions.py

async def require_admin(current_role: str = Depends(get_current_user)) -> str:
    if current_role != UserRole.ADMIN:
        raise HTTPException(403, {"code": "FORBIDDEN", "message": "Admin role required"})
    return current_role

async def require_console_access(current_role: str = Depends(get_current_user)) -> str:
    if current_role != UserRole.ADMIN:
        raise HTTPException(403, {"code": "FORBIDDEN", "message": "Console access requires Admin role"})
    return current_role
```

## Usage Pattern
```python
@router.get("/data")  # Both roles - uses get_current_user
async def get_data(role: str = Depends(get_current_user)): ...

@router.post("/data")  # Admin only - uses require_admin
async def create_data(role: str = Depends(require_admin)): ...
```

## Files Created
- api/src/vintagestory_api/middleware/permissions.py
- api/src/vintagestory_api/routers/test_rbac.py (DEBUG gated)
- api/tests/test_permissions.py (22 tests)
- api/tests/test_rbac_integration.py (21 tests)
- api/tests/test_debug_gating.py (4 tests)

## Notes
- Test endpoints only available when VS_DEBUG=true
- Literal type constraint prevents role typos at type-check time
