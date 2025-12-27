# Story 2.2: Role-Based Access Control for API Endpoints

Status: review

---

## Story

As a **system administrator**,
I want **different API keys to have different permission levels**,
so that **I can grant read-only access to monitoring systems while reserving write access for admins**.

---

## Acceptance Criteria

1. **Given** I am authenticated as Admin, **When** I attempt any API operation (read or write), **Then** the operation is permitted
   *(Covers FR33)*

2. **Given** I am authenticated as Monitor, **When** I attempt a read operation on non-sensitive endpoints, **Then** the operation is permitted
   *(Covers FR32)*

3. **Given** I am authenticated as Monitor, **When** I attempt a write operation (POST, PUT, DELETE on protected resources), **Then** I receive a 403 Forbidden response with `{"status": "error", "error": {"code": "FORBIDDEN", "message": "..."}}`
   *(Covers FR35, FR37)*

4. **Given** I am authenticated as Monitor, **When** I attempt to access console endpoints (stream or history), **Then** I receive a 403 Forbidden response with error message indicating console access requires Admin role
   *(Covers FR34)*

5. **Given** role permissions are checked, **When** a 403 response is returned, **Then** the response clearly indicates the required role for the operation

---

## Tasks / Subtasks

- [x] Task 1: Create role permission utilities + tests (AC: 1, 2, 3, 5)
  - [x] 1.1: Create `middleware/permissions.py` with `require_admin` and `require_role` dependencies
  - [x] 1.2: Implement role-checking helper that compares current role to required role
  - [x] 1.3: Add `FORBIDDEN` error response helper in `models/responses.py`
  - [x] 1.4: Write unit tests for Admin role allowing all operations
  - [x] 1.5: Write unit tests for Monitor role allowing reads, blocking writes

- [x] Task 2: Create console access guard + tests (AC: 4)
  - [x] 2.1: Create `require_console_access` dependency that only allows Admin
  - [x] 2.2: Return 403 with clear message: "Console access requires Admin role"
  - [x] 2.3: Write tests verifying console access blocked for Monitor role
  - [x] 2.4: Write tests verifying console access allowed for Admin role

- [x] Task 3: Create protected test endpoints for validation + tests (AC: 1-5)
  - [x] 3.1: Create `GET /api/v1alpha1/test/read` endpoint (allows Admin and Monitor)
  - [x] 3.2: Create `POST /api/v1alpha1/test/write` endpoint (allows Admin only)
  - [x] 3.3: Create `GET /api/v1alpha1/test/console` endpoint simulating console access (Admin only)
  - [x] 3.4: Write integration tests for all role/endpoint combinations
  - [x] 3.5: Verify 403 response includes required role in error message

- [x] Task 4: Verify existing endpoints work with RBAC + tests (AC: 1, 2)
  - [x] 4.1: Ensure `/api/v1alpha1/auth/me` works for both Admin and Monitor
  - [x] 4.2: Write integration tests confirming health endpoints remain public
  - [x] 4.3: Verify error responses use standard envelope format

---

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Do not batch tests into a separate "Write tests" task at the end

### Architecture & Patterns

**Role Hierarchy:**
```
Admin → Full access (read + write + console)
Monitor → Read-only access (no writes, no console)
```

**Permission Check Flow:**
```
Request → Auth Middleware → Role Extracted → Permission Check → Route Handler
                            (from Story 2.1)        ↓
                                              Monitor + Write?
                                                    ↓
                                              403 Forbidden
```

**CRITICAL - Extend Existing Auth:**
Story 2.1 created `middleware/auth.py` with `get_current_user` dependency that returns the user role. Build on top of this - DO NOT recreate authentication logic.

**Dependency Pattern (FastAPI best practice):**
```python
from fastapi import Depends, HTTPException
from vintagestory_api.middleware.auth import get_current_user, UserRole
from vintagestory_api.models.errors import ErrorCode

async def require_admin(
    current_role: str = Depends(get_current_user),
) -> str:
    """Require Admin role for the endpoint."""
    if current_role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail={
                "code": ErrorCode.FORBIDDEN,
                "message": "Admin role required for this operation"
            }
        )
    return current_role

async def require_console_access(
    current_role: str = Depends(get_current_user),
) -> str:
    """Require Admin role for console access (sensitive data)."""
    if current_role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail={
                "code": ErrorCode.FORBIDDEN,
                "message": "Console access requires Admin role"
            }
        )
    return current_role
```

**Route Protection Patterns:**

```python
# Read endpoint - accessible by both Admin and Monitor
@router.get("/data")
async def get_data(role: str = Depends(get_current_user)):
    # Both Admin and Monitor can access
    pass

# Write endpoint - Admin only
@router.post("/data")
async def create_data(role: str = Depends(require_admin)):
    # Only Admin can access
    pass

# Console endpoint - Admin only with specific message
@router.get("/console/history")
async def get_console_history(role: str = Depends(require_console_access)):
    # Only Admin can access, with console-specific error message
    pass
```

### Error Response Format

All 403 responses MUST use the standard envelope:

```python
# 403 Forbidden - Write operation
{
    "status": "error",
    "error": {
        "code": "FORBIDDEN",
        "message": "Admin role required for this operation"
    }
}

# 403 Forbidden - Console access
{
    "status": "error",
    "error": {
        "code": "FORBIDDEN",
        "message": "Console access requires Admin role"
    }
}
```

### Project Structure Notes

**Files to create:**
- `api/src/vintagestory_api/middleware/permissions.py` - Role-based permission dependencies
- `api/src/vintagestory_api/routers/test_rbac.py` - Temporary test endpoints for RBAC validation

**Files to modify:**
- `api/src/vintagestory_api/middleware/__init__.py` - Export permission dependencies
- `api/src/vintagestory_api/routers/__init__.py` - Export test_rbac router (temporary)
- `api/src/vintagestory_api/main.py` - Wire up test_rbac router

**Tests to create:**
- `api/tests/test_permissions.py` - Permission dependency unit tests
- `api/tests/test_rbac_integration.py` - Full RBAC integration tests

### Existing Code to Reuse

**From Story 2.1 - DO NOT DUPLICATE:**

| Component | Location | Purpose |
|-----------|----------|---------|
| `get_current_user` | `middleware/auth.py` | Returns user role from API key |
| `UserRole` | `middleware/auth.py` | Role constants (ADMIN, MONITOR) |
| `ErrorCode.FORBIDDEN` | `models/errors.py` | Error code constant |
| `get_settings` | `config.py` | Settings dependency |

**Import pattern:**
```python
from vintagestory_api.middleware.auth import get_current_user, UserRole
from vintagestory_api.models.errors import ErrorCode
```

### Security Requirements

| Requirement | Implementation |
|-------------|----------------|
| FR32: Monitor read-only | `get_current_user` dependency allows, no extra check for reads |
| FR33: Admin full access | `get_current_user` dependency allows all operations |
| FR34: Console Admin-only | `require_console_access` dependency with specific error |
| FR35: Writes Admin-only | `require_admin` dependency for POST/PUT/DELETE |
| FR37: 403 for insufficient role | HTTPException with FORBIDDEN code and clear message |

### Previous Story Intelligence

**From Story 2.1 implementation:**

1. **Authentication is already done** - `get_current_user` returns "admin" or "monitor" role
2. **Router-level auth** - API v1alpha1 router already has `dependencies=[Depends(get_current_user)]` protecting all routes
3. **Thread-safe settings** - Uses `@lru_cache` for settings dependency
4. **Error envelope pattern** - 401 responses use `{"status": "error", "error": {...}}` format
5. **Test patterns** - See `api/tests/test_auth.py` for test organization examples
6. **16+ auth tests exist** - Verify no regressions in existing tests

**Key insight from Story 2.1:**
The router already has authentication at the router level. RBAC adds a second layer - permission checking after authentication succeeds. The flow is:
1. Router auth dependency verifies API key is valid
2. Endpoint-level permission dependency (require_admin, etc.) checks role permissions

### Git History Intelligence

**Recent commit patterns:**
- `fix(auth):` prefix for auth fixes
- `feat(auth):` prefix for auth features
- Commit messages include story reference
- All tests must pass before marking complete

**Files recently touched in auth work:**
- `api/src/vintagestory_api/middleware/auth.py`
- `api/src/vintagestory_api/routers/auth.py`
- `api/tests/test_auth.py`

### Latest Best Practices (2025)

**FastAPI Dependency Injection:**
- Use `Depends()` for composable permission checks
- Layer permissions: auth → role check → route
- Keep permission dependencies small and focused

**Role-Based Access Control:**
- Two-tier is sufficient for MVP (Admin/Monitor)
- Check at endpoint level, not middleware (allows flexibility)
- Clear error messages help debugging

**Test Organization:**
- Unit tests for permission logic
- Integration tests for full request flow
- Test both allowed and denied scenarios

### Anti-Patterns to Avoid

| Avoid | Do Instead |
|-------|------------|
| Creating new auth middleware | Use existing `get_current_user` |
| Checking role in route handler body | Use dependency injection |
| Generic "Access denied" message | Specific message with required role |
| Testing only happy path | Test all role/endpoint combinations |
| Duplicating UserRole constants | Import from `middleware/auth.py` |

### Test Scenarios Checklist

| Role | Endpoint Type | Expected Result |
|------|---------------|-----------------|
| Admin | Read (GET) | 200 OK |
| Admin | Write (POST/PUT/DELETE) | 200/201/204 |
| Admin | Console | 200 OK |
| Monitor | Read (GET) | 200 OK |
| Monitor | Write (POST/PUT/DELETE) | 403 Forbidden |
| Monitor | Console | 403 Forbidden |
| None | Any protected | 401 Unauthorized (from Story 2.1) |

### References

- Architecture authentication section: [Source: _bmad-output/planning-artifacts/architecture.md#Authentication & Security]
- Error codes definition: [Source: api/src/vintagestory_api/models/errors.py]
- Existing auth middleware: [Source: api/src/vintagestory_api/middleware/auth.py]
- Response envelope pattern: [Source: api/src/vintagestory_api/models/responses.py]
- FR31-37 requirements: [Source: _bmad-output/planning-artifacts/epics.md#Epic 2]
- Previous story implementation: [Source: _bmad-output/implementation-artifacts/2-1-api-key-authentication-middleware.md]
- Project context rules: [Source: project-context.md]

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

None - implementation proceeded without issues

### Completion Notes List

- Implemented `require_admin`, `require_console_access`, and `require_role` permission dependencies in `middleware/permissions.py`
- Created type aliases `RequireAdmin` and `RequireConsoleAccess` for cleaner dependency injection
- Extended `middleware/__init__.py` to export all new permission utilities
- Created test RBAC router with `/test/read`, `/test/write`, and `/test/console` endpoints
- Wired test_rbac router into the v1alpha1 API
- Wrote 17 unit tests for permission dependencies covering all role/endpoint combinations
- Wrote 21 integration tests for full RBAC flow including health endpoints and error format
- All 93 tests pass (no regressions from Story 2.1's 17 auth tests)
- All acceptance criteria satisfied through test coverage

### Change Log

- 2025-12-27: Implemented RBAC permission system with Admin/Monitor role enforcement

### File List

**New files:**
- `api/src/vintagestory_api/middleware/permissions.py` - Role-based permission dependencies
- `api/src/vintagestory_api/routers/test_rbac.py` - Test endpoints for RBAC validation
- `api/tests/test_permissions.py` - Permission dependency unit tests (17 tests)
- `api/tests/test_rbac_integration.py` - RBAC integration tests (21 tests)

**Modified files:**
- `api/src/vintagestory_api/middleware/__init__.py` - Export permission dependencies
- `api/src/vintagestory_api/routers/__init__.py` - Export test_rbac router
- `api/src/vintagestory_api/main.py` - Wire up test_rbac router
- `_bmad-output/implementation-artifacts/sprint-status.yaml` - Updated story status

