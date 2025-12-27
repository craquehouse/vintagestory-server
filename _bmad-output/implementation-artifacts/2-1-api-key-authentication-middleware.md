# Story 2.1: API Key Authentication Middleware

Status: review

---

## Story

As an **API consumer**,
I want **to authenticate using an API key in the request header**,
so that **I can access protected endpoints securely**.

---

## Acceptance Criteria

1. **Given** I have a valid Admin API key, **When** I send a request with `X-API-Key: <valid-admin-key>` header, **Then** the request is authenticated successfully and my role is identified as Admin
   *(Covers FR31, FR33)*

2. **Given** I have a valid Monitor API key, **When** I send a request with `X-API-Key: <valid-monitor-key>` header, **Then** the request is authenticated successfully and my role is identified as Monitor
   *(Covers FR31, FR32)*

3. **Given** I send a request without an API key, **When** the endpoint requires authentication, **Then** I receive a 401 Unauthorized response with `{"status": "error", "error": {"code": "UNAUTHORIZED", "message": "..."}}`
   *(Covers FR36)*

4. **Given** I send a request with an invalid API key, **When** the endpoint requires authentication, **Then** I receive a 401 Unauthorized response and the failed attempt is logged with request context (but not the key value)
   *(Covers FR36, NFR7)*

5. **Given** any authentication attempt occurs, **When** the system processes the request, **Then** API keys are never logged in plaintext
   *(Covers NFR4)*

6. **Given** health endpoints (`/healthz`, `/readyz`), **When** I send a request without authentication, **Then** the request succeeds (health endpoints remain unauthenticated)

---

## Tasks / Subtasks

- [x] Task 1: Create authentication middleware with role detection + tests (AC: 1, 2)
  - [x] 1.1: Create `middleware/auth.py` with `APIKeyAuthMiddleware` class
  - [x] 1.2: Implement `get_current_user` dependency for extracting role from `X-API-Key` header
  - [x] 1.3: Use `secrets.compare_digest` for timing-safe key comparison
  - [x] 1.4: Write unit tests for Admin key authentication
  - [x] 1.5: Write unit tests for Monitor key authentication

- [x] Task 2: Implement 401 response handling + tests (AC: 3, 4)
  - [x] 2.1: Return standard error envelope on missing API key
  - [x] 2.2: Return standard error envelope on invalid API key
  - [x] 2.3: Log failed auth attempts with structlog (request path, method, but NEVER the key value)
  - [x] 2.4: Write tests for missing key scenario
  - [x] 2.5: Write tests for invalid key scenario
  - [x] 2.6: Write tests verifying log output (without plaintext keys)

- [x] Task 3: Ensure health endpoints remain public + tests (AC: 6)
  - [x] 3.1: Verify `/healthz` and `/readyz` are not protected by auth
  - [x] 3.2: Write tests confirming health endpoints work without auth headers

- [x] Task 4: Create protected test endpoint for validation + tests (AC: 1-5)
  - [x] 4.1: Create a temporary protected endpoint (e.g., `GET /api/v1alpha1/auth/me`) that returns current role
  - [x] 4.2: Wire up API v1alpha1 router in `main.py` with auth dependency
  - [x] 4.3: Write integration tests exercising the full auth flow

---

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Do not batch tests into a separate "Write tests" task at the end

### Architecture & Patterns

**Authentication Flow:**
```
Request → X-API-Key Header → Middleware → Compare Keys → Role Assignment → Route Handler
              ↓                                               ↓
         Missing/Invalid                              Admin or Monitor
              ↓
        401 Unauthorized
```

**Key Comparison - MUST use timing-safe comparison:**
```python
import secrets

def verify_api_key(provided_key: str, expected_key: str) -> bool:
    """Timing-safe key comparison to prevent timing attacks."""
    return secrets.compare_digest(provided_key, expected_key)
```

**Dependency Pattern (FastAPI best practice):**
```python
from fastapi import Depends, Header, HTTPException
from vintagestory_api.models.errors import ErrorCode

class UserRole:
    ADMIN = "admin"
    MONITOR = "monitor"

async def get_current_user(
    x_api_key: str | None = Header(None),
    settings: Settings = Depends(get_settings),
) -> str:
    """Extract and validate API key, return user role."""
    if x_api_key is None:
        raise HTTPException(
            status_code=401,
            detail={"code": ErrorCode.UNAUTHORIZED, "message": "API key required"}
        )

    if secrets.compare_digest(x_api_key, settings.api_key_admin):
        return UserRole.ADMIN

    if settings.api_key_monitor and secrets.compare_digest(x_api_key, settings.api_key_monitor):
        return UserRole.MONITOR

    # Log failed attempt (without the key value!)
    logger.warning("auth_failed", path=request.url.path, method=request.method)

    raise HTTPException(
        status_code=401,
        detail={"code": ErrorCode.UNAUTHORIZED, "message": "Invalid API key"}
    )
```

**Global Dependency for Protected Routes:**
```python
# In main.py
api_v1 = APIRouter(prefix="/api/v1alpha1", dependencies=[Depends(get_current_user)])
```

### Security Requirements

| Requirement | Implementation |
|-------------|----------------|
| NFR4: Keys never logged in plaintext | Use masked value like `***` or just don't log key at all |
| NFR7: Failed auth attempts logged | Log with structlog: path, method, timestamp (no key value) |
| Timing attack prevention | Use `secrets.compare_digest` for all key comparisons |
| Header name | `X-API-Key` (case-insensitive in HTTP but use this exact casing) |

### Error Response Format

All error responses MUST use the standard envelope from `models/responses.py`:

```python
# 401 Unauthorized
{
    "status": "error",
    "error": {
        "code": "UNAUTHORIZED",
        "message": "API key required"  # or "Invalid API key"
    }
}

# 403 Forbidden (for Story 2.2 - role-based access)
{
    "status": "error",
    "error": {
        "code": "FORBIDDEN",
        "message": "Admin role required for this operation"
    }
}
```

### Project Structure Notes

**Files to create:**
- `api/src/vintagestory_api/middleware/auth.py` - Authentication logic
- `api/src/vintagestory_api/routers/auth.py` - Temporary test endpoint (can be removed after Epic 2)

**Files to modify:**
- `api/src/vintagestory_api/main.py` - Wire up API v1alpha1 router with auth dependency
- `api/src/vintagestory_api/config.py` - Add `get_settings` dependency function

**Tests to create:**
- `api/tests/test_auth.py` - Authentication middleware tests
- `api/tests/test_health_no_auth.py` - Verify health endpoints stay public

### Existing Code Patterns

**Error codes are already defined in `models/errors.py`:**
```python
class ErrorCode:
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    # ... other codes
```

**Settings already has API key fields in `config.py`:**
```python
class Settings(BaseSettings):
    api_key_admin: str = ""
    api_key_monitor: str | None = None
```

**Logging is already configured with structlog in `config.py`**

### Latest Security Best Practices (2025)

From current FastAPI security research:

1. **Use `secrets.compare_digest`** - Prevents timing attacks by ensuring constant-time comparison
2. **Header-based auth preferred** - `X-API-Key` header is more secure than query params (won't appear in logs)
3. **Log failed attempts** - Essential for security monitoring (but never log the key value)
4. **Keep health endpoints public** - Standard practice for Kubernetes/load balancer probes
5. **Environment-based configuration** - Keys from `VS_API_KEY_ADMIN` and `VS_API_KEY_MONITOR`

### References

- Architecture authentication section: [Source: _bmad-output/planning-artifacts/architecture.md#Authentication & Security]
- Error codes definition: [Source: api/src/vintagestory_api/models/errors.py]
- Settings configuration: [Source: api/src/vintagestory_api/config.py]
- Response envelope pattern: [Source: api/src/vintagestory_api/models/responses.py]
- FR31-37 requirements: [Source: _bmad-output/planning-artifacts/epics.md#Epic 2]
- NFR4, NFR7: [Source: _bmad-output/planning-artifacts/epics.md#NonFunctional Requirements]
- FastAPI Security Docs: https://fastapi.tiangolo.com/tutorial/security/
- TestDriven.io API Key Auth: https://testdriven.io/tips/6840e037-4b8f-4354-a9af-6863fb1c69eb/

### Previous Story Intelligence

From Epic 1 retrospective learnings:

1. **Tests must accompany implementation** - Don't batch tests at the end
2. **Error envelope already established** - Use the pattern from Story 1.2
3. **structlog configured** - Use existing logging setup

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

No blocking issues encountered during implementation.

### Completion Notes List

1. **Authentication middleware implemented** using FastAPI's dependency injection pattern with `get_current_user` dependency
2. **Timing-safe comparison** using `secrets.compare_digest` for all API key comparisons to prevent timing attacks
3. **Two roles supported**: Admin (from `VS_API_KEY_ADMIN`) and Monitor (from `VS_API_KEY_MONITOR`, optional)
4. **Error responses** use standard envelope format with `UNAUTHORIZED` error code
5. **Security logging** logs failed auth attempts with path/method but NEVER logs the API key value
6. **Health endpoints remain public** - `/healthz` and `/readyz` do not require authentication
7. **Test endpoint created** at `GET /api/v1alpha1/auth/me` returns current user role
8. **16 new auth tests** covering unit tests and integration tests for all acceptance criteria
9. **All 54 tests pass** with no regressions

### File List

**New Files:**
- `api/src/vintagestory_api/middleware/auth.py` - Authentication dependency and role detection
- `api/src/vintagestory_api/routers/auth.py` - Auth router with `/auth/me` endpoint
- `api/tests/test_auth.py` - 16 authentication tests

**Modified Files:**
- `api/src/vintagestory_api/middleware/__init__.py` - Export auth components
- `api/src/vintagestory_api/routers/__init__.py` - Export auth router
- `api/src/vintagestory_api/main.py` - Wire up API v1alpha1 router with auth endpoint

### Change Log

| Date | Change | Author |
|------|--------|--------|
| 2025-12-27 | Implemented API key authentication middleware with Admin/Monitor roles, 401 error handling, and protected `/api/v1alpha1/auth/me` endpoint. Added 16 tests covering all acceptance criteria. | Claude Opus 4.5 |
