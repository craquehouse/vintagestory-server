# Story 9.1: Secure WebSocket Authentication

Status: complete

## Story

As an **administrator**,
I want **WebSocket connections to use secure token-based authentication instead of API keys in URLs**,
So that **credentials are not exposed in server logs, browser history, or network traces**.

## Acceptance Criteria

1. **Given** I have a valid API key, **When** I request a WebSocket token from `POST /api/v1alpha1/auth/ws-token`, **Then** I receive a short-lived token (5 minute expiry) that can be used for WebSocket connections.

2. **Given** I have a valid WebSocket token, **When** I connect to `/api/v1alpha1/console/ws?token={token}`, **Then** the connection is established successfully with my role preserved.

3. **Given** I provide an invalid or expired token, **When** I attempt to connect to a WebSocket endpoint, **Then** the connection is rejected with code 4001 (Unauthorized).

4. **Given** my WebSocket token expires during an active connection, **When** I attempt to send a message, **Then** the connection remains active (tokens only validated at connection time).

5. **Given** the frontend needs to establish a WebSocket connection, **When** it calls the token endpoint, **Then** it receives a token it can use immediately for connection.

6. **Given** a Monitor role API key, **When** I request a WebSocket token, **Then** the token preserves the Monitor role and console access is rejected with code 4003 (Forbidden).

## Tasks / Subtasks

<!--
CRITICAL TASK STRUCTURE RULES:
1. Each functional task MUST include "+ tests" in its name
2. Do NOT create separate "Write tests" tasks at the end
3. A task is NOT complete until its tests pass
4. Tests verify the specific AC listed for that task

✅ CORRECT PATTERN:
- [ ] Task 1: Implement feature + tests (AC: 1, 2)
  - [ ] Subtask 1.1: Implementation detail
  - [ ] Subtask 1.2: Write tests for feature

❌ WRONG PATTERN (tests batched at end):
- [ ] Task 1: Implement feature (AC: 1, 2)
- [ ] Task 2: Write all tests  <- NEVER DO THIS
-->

- [x] Task 1: Create WebSocket token model and generation + tests (AC: 1)
  - [x] Subtask 1.1: Create `api/src/vintagestory_api/models/ws_token.py` with `WebSocketToken` and `WebSocketTokenResponse` Pydantic models
  - [x] Subtask 1.2: Create `api/src/vintagestory_api/services/ws_token_service.py` with token generation using `secrets.token_urlsafe()` and in-memory token store
  - [x] Subtask 1.3: Implement token expiry (5 minute TTL) with cleanup of expired tokens
  - [x] Subtask 1.4: Write unit tests in `api/tests/test_ws_token_service.py` for token generation, validation, and expiry (23 tests)

- [x] Task 2: Create WebSocket token endpoint + tests (AC: 1, 6)
  - [x] Subtask 2.1: Create `api/src/vintagestory_api/routers/ws_token.py` with `POST /api/v1alpha1/auth/ws-token` endpoint
  - [x] Subtask 2.2: Require valid API key (Admin or Monitor) via existing `get_current_user` dependency
  - [x] Subtask 2.3: Return token with role embedded for WebSocket authorization
  - [x] Subtask 2.4: Register router in `api/src/vintagestory_api/main.py`
  - [x] Subtask 2.5: Write integration tests in `api/tests/test_ws_token_router.py` for token request with Admin/Monitor keys (16 tests)

- [x] Task 3: Update WebSocket endpoints to use token auth + tests (AC: 2, 3, 6)
  - [x] Subtask 3.1: Add `token` query parameter to `console_websocket()` in `console.py`
  - [x] Subtask 3.2: Add `token` query parameter to `logs_websocket()` in `console.py`
  - [x] Subtask 3.3: Create `_verify_ws_auth()` helper that validates token and returns role
  - [x] Subtask 3.4: Support both `token` and legacy `api_key` params (token takes precedence) for backwards compatibility during transition
  - [x] Subtask 3.5: Update console test fixtures to include token service (all 18 existing tests pass)
  - [x] Subtask 3.6: Add tests for invalid/expired token rejection (4001) and Monitor role rejection for console (4003) - 14 new tests

- [x] Task 4: Frontend WebSocket token integration + tests (AC: 5)
  - [x] Subtask 4.1: Create `web/src/api/ws-token.ts` with `requestWebSocketToken()` function
  - [x] Subtask 4.2: Update `web/src/hooks/use-console-websocket.ts` to request token before connecting
  - [x] Subtask 4.3: Update `web/src/hooks/use-log-stream.ts` to request token before connecting
  - [x] Subtask 4.4: Handle token request errors gracefully with user feedback (added 'token_error' state)
  - [x] Subtask 4.5: Write tests in `web/src/api/ws-token.test.ts` for token request (6 tests)
  - [x] Subtask 4.6: Update hook tests to verify token flow (25 console-websocket tests, 23 Terminal tests)

- [x] Task 5: Documentation and deprecation notices + cleanup (AC: 4)
  - [x] Subtask 5.1: Add deprecation warning log when `api_key` query param is used on WebSocket endpoints (already done in Task 3)
  - [x] Subtask 5.2: Update API documentation/comments to reflect new token auth flow (JSDoc/docstrings in code)
  - [x] Subtask 5.3: Verify all tests pass with `just check` (1035 API + 735 web = 1770 tests pass)
  - [x] Subtask 5.4: Update story file with completion notes

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Do not batch tests into a separate "Write tests" task at the end
- Run `just test-api` to verify API tests pass
- Run `just test-web` to verify web tests pass
- Run `just check` for full validation before marking story complete

**Test Files to Create:**
- `api/tests/services/test_ws_token_service.py` - Token service unit tests
- `api/tests/routers/test_ws_token.py` - Token endpoint integration tests
- `web/src/api/ws-token.test.ts` - Frontend token request tests

**Test Files to Modify:**
- `api/tests/routers/test_console.py` - Update WebSocket tests to use token auth
- `web/src/hooks/use-console.test.ts` - Update hook tests for token flow
- `web/src/hooks/use-log-stream.test.ts` - Update hook tests for token flow

### API Contract

**Token Request Endpoint:** `POST /api/v1alpha1/auth/ws-token`

**Request Headers:**
```
X-API-Key: <admin_or_monitor_api_key>
```

**Response (200 OK):**
```json
{
  "status": "ok",
  "data": {
    "token": "abc123xyz...",
    "expires_at": "2026-01-03T12:05:00Z",
    "expires_in_seconds": 300
  }
}
```

**Response (401 Unauthorized):**
```json
{
  "status": "error",
  "error": {
    "code": "UNAUTHORIZED",
    "message": "API key required"
  }
}
```

**TypeScript Types:**
```typescript
// web/src/api/ws-token.ts
interface WebSocketTokenResponse {
  status: 'ok';
  data: {
    token: string;
    expiresAt: string;  // ISO datetime
    expiresInSeconds: number;
  };
}

async function requestWebSocketToken(): Promise<string> {
  const response = await apiClient.post('/api/v1alpha1/auth/ws-token');
  return response.data.token;
}
```

### Token Storage Design

Use in-memory storage for tokens (not database):

```python
# api/src/vintagestory_api/services/ws_token_service.py
from dataclasses import dataclass
from datetime import datetime, UTC
import secrets

@dataclass
class StoredToken:
    token: str
    role: str  # 'admin' or 'monitor'
    expires_at: datetime
    created_at: datetime

class WebSocketTokenService:
    def __init__(self, token_ttl_seconds: int = 300):
        self._tokens: dict[str, StoredToken] = {}
        self._token_ttl = token_ttl_seconds

    def create_token(self, role: str) -> StoredToken:
        """Create a new WebSocket token for the given role."""
        token = secrets.token_urlsafe(32)
        now = datetime.now(UTC)
        stored = StoredToken(
            token=token,
            role=role,
            expires_at=now + timedelta(seconds=self._token_ttl),
            created_at=now,
        )
        self._tokens[token] = stored
        self._cleanup_expired()
        return stored

    def validate_token(self, token: str) -> str | None:
        """Validate token and return role if valid, None if invalid/expired."""
        stored = self._tokens.get(token)
        if stored is None:
            return None
        if datetime.now(UTC) > stored.expires_at:
            del self._tokens[token]
            return None
        return stored.role

    def _cleanup_expired(self) -> None:
        """Remove expired tokens from storage."""
        now = datetime.now(UTC)
        expired = [t for t, s in self._tokens.items() if now > s.expires_at]
        for t in expired:
            del self._tokens[t]
```

### WebSocket Auth Update Pattern

Update `console.py` to support both token and legacy API key:

```python
# api/src/vintagestory_api/routers/console.py
from vintagestory_api.services.ws_token_service import get_ws_token_service

@ws_router.websocket("/ws")
async def console_websocket(
    websocket: WebSocket,
    token: Annotated[str | None, Query(description="WebSocket auth token")] = None,
    api_key: Annotated[str | None, Query(description="API key (deprecated)")] = None,
    history_lines: Annotated[int | None, Query(...)] = None,
    settings: Settings = Depends(get_settings),
    service: ServerService = Depends(get_server_service),
    token_service: WebSocketTokenService = Depends(get_ws_token_service),
):
    # Prefer token auth over api_key
    role: str | None = None
    if token:
        role = token_service.validate_token(token)
    elif api_key:
        logger.warning("WebSocket connection using deprecated api_key parameter")
        role = _verify_api_key_with_settings(api_key, settings.api_key_admin, settings.api_key_monitor)

    if role is None:
        await websocket.accept()
        await websocket.close(code=4001, reason="Unauthorized: Invalid or expired token")
        return

    # Console requires admin role
    if role != UserRole.ADMIN:
        await websocket.accept()
        await websocket.close(code=4003, reason="Forbidden: Admin role required")
        return

    # ... rest of handler
```

### Frontend Integration Pattern

Update WebSocket hooks to request token first:

```typescript
// web/src/hooks/use-console.ts
import { requestWebSocketToken } from '@/api/ws-token';

export function useConsole() {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [error, setError] = useState<string | null>(null);

  const connect = useCallback(async () => {
    try {
      // Request fresh token before connecting
      const token = await requestWebSocketToken();

      const wsUrl = new URL('/api/v1alpha1/console/ws', window.location.origin);
      wsUrl.protocol = wsUrl.protocol.replace('http', 'ws');
      wsUrl.searchParams.set('token', token);

      const ws = new WebSocket(wsUrl.toString());
      // ... rest of connection logic
    } catch (err) {
      setError('Failed to authenticate WebSocket connection');
    }
  }, []);

  // ...
}
```

### Security Considerations

- Tokens are single-use for connection establishment (not revoked after use to allow reconnection attempts)
- 5-minute TTL limits exposure window if token is intercepted
- Tokens stored only in memory (not persisted to disk/database)
- Role is embedded in token, validated at connection time only (AC: 4)
- Legacy `api_key` param supported for backwards compatibility but logs deprecation warning
- Token endpoint requires valid API key (prevents unauthenticated token requests)

### WebSocket Close Codes

| Code | Meaning | When Used |
|------|---------|-----------|
| 4001 | Unauthorized | Invalid or expired token |
| 4003 | Forbidden | Valid token but insufficient role |
| 4004 | Not Found | Container not found |
| 4005 | Invalid | Invalid message format |

### Development Commands

Use `just` for all development tasks:
- `just test-api` - Run all API tests
- `just test-api -k "ws_token"` - Run token-related tests only
- `just test-web` - Run all web tests
- `just dev-api` - Start API dev server
- `just dev-web` - Start web dev server
- `just check` - Full validation (lint + typecheck + test)

### Git Workflow for This Story

```bash
# Create feature branch from main
git checkout -b story/9-1-secure-websocket-authentication

# Task-level commits
git commit -m "feat(story-9.1/task-1): create WebSocket token service with TTL"
git commit -m "feat(story-9.1/task-2): add POST /auth/ws-token endpoint"
git commit -m "feat(story-9.1/task-3): update WebSocket endpoints to use token auth"
git commit -m "feat(story-9.1/task-4): frontend WebSocket token integration"
git commit -m "docs(story-9.1/task-5): add deprecation notices and cleanup"

# Push and create PR
git push -u origin story/9-1-secure-websocket-authentication
gh pr create --title "Story 9.1: Secure WebSocket Authentication" --body "..."
```

### Source Tree Components

**Files to CREATE:**
- `api/src/vintagestory_api/models/ws_token.py` - Token Pydantic models
- `api/src/vintagestory_api/services/ws_token_service.py` - Token generation/validation service
- `api/src/vintagestory_api/routers/ws_token.py` - Token endpoint router
- `api/tests/services/test_ws_token_service.py` - Service unit tests
- `api/tests/routers/test_ws_token.py` - Endpoint integration tests
- `web/src/api/ws-token.ts` - Frontend token request function
- `web/src/api/ws-token.test.ts` - Frontend token tests

**Files to MODIFY:**
- `api/src/vintagestory_api/main.py` - Register ws_token router
- `api/src/vintagestory_api/routers/console.py` - Add token auth to WebSocket endpoints
- `api/tests/routers/test_console.py` - Update tests for token auth
- `web/src/hooks/use-console.ts` - Request token before connecting
- `web/src/hooks/use-log-stream.ts` - Request token before connecting
- `web/src/hooks/use-console.test.ts` - Update for token flow
- `web/src/hooks/use-log-stream.test.ts` - Update for token flow

### Previous Story Intelligence

**From Story 8.3 (Job Configuration UI):**
- Frontend hooks pattern: `useQuery` with query keys, polling support
- Test patterns: MSW for API mocking, Testing Library for component tests
- 1683 total tests (966 API + 717 web) as baseline

**From Architecture Document:**
- WebSocket close codes: 4001 (Unauthorized), 4003 (Forbidden), 4004 (Not Found), 4005 (Invalid)
- API response envelope: `{"status": "ok/error", "data": {...}}`
- RBAC: Admin and Monitor roles with different access levels

**From Current Implementation (console.py):**
- `_verify_api_key_with_settings()` uses `secrets.compare_digest()` for timing-safe comparison
- WebSocket endpoints accept connection before auth check, then close with appropriate code
- Both `/ws` (console) and `/logs/ws` (log stream) need updating

### References

- `project-context.md` - Critical implementation rules and patterns
- `_bmad-output/planning-artifacts/architecture.md` - WebSocket patterns, close codes
- `_bmad-output/planning-artifacts/epics.md#Story 9.1` - Story requirements and BDD
- `api/src/vintagestory_api/routers/console.py` - Current WebSocket implementation
- `api/src/vintagestory_api/middleware/auth.py` - API key validation patterns
- `web/src/hooks/use-console.ts` - Current frontend WebSocket hook

## Review Follow-ups (AI)

- [x] [AI-Review][HIGH] Add asyncio.Lock to WebSocketTokenService for thread-safe dict operations in token validation and cleanup [ws_token_service.py] - **FIXED**: All public methods are now async with asyncio.Lock protection
- [x] [AI-Review][MEDIUM] Add test explicitly verifying token expiry during active connection (AC: 4) [test_websocket_token_auth.py] - **FIXED**: Added `TestTokenExpiryDuringConnection` class
- [x] [AI-Review][MEDIUM] Add concurrency test using asyncio.gather to simulate concurrent token creation/validation [test_ws_token_service.py] - **FIXED**: Added `TestConcurrency` class with 3 concurrent tests
- [x] [AI-Review][MEDIUM] Implement periodic token cleanup or LRU eviction with size limit [ws_token_service.py] - **FIXED**: Added MAX_TOKEN_COUNT=10000 with oldest-first eviction
- [x] [AI-Review][MEDIUM] Fix Justfile duplicate --run flag in test-web recipe [Justfile:39] - **NOT A BUG**: `--run` is required for vitest to run once (not watch mode)
- [x] [AI-Review][MEDIUM] Clarify whether Monitor role should access logs WebSocket endpoint [console.py:497] - **DOCUMENTED**: Added note to test that this is current behavior, product decision to be made
- [x] [AI-Review][LOW] Fix typo in log event name - **NOT A BUG**: "ws_token_validated" is spelled correctly
- [x] [AI-Review][LOW] Standardize logging event names - **VERIFIED**: All use consistent past tense (created, validated, expired, evicted)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- Task 1: Created WebSocketTokenService with in-memory token storage, 5-minute TTL, secure token generation using `secrets.token_urlsafe(32)`, and automatic cleanup of expired tokens. Includes singleton pattern for FastAPI dependency injection. 23 unit tests pass.
- Task 2: Created POST /auth/ws-token endpoint that requires valid API key and returns short-lived token with role, expires_at, and expires_in_seconds. 16 integration tests pass.
- Task 3: Updated WebSocket endpoints (console/ws and console/logs/ws) to support token authentication. Token takes precedence over legacy api_key. Deprecation warning logged when api_key used. All 112 console tests pass (18 existing + 14 new token auth tests).
- Task 4: Created frontend WebSocket token integration. Added web/src/api/ws-token.ts with requestWebSocketToken() function, WebSocketTokenError class. Updated use-console-websocket.ts and use-log-stream.ts hooks to request token before connecting. Added 'token_error' connection state for failed token requests. Updated ConnectionStatus component and ConsolePanel to handle token_error state. All 735 web tests pass.
- Task 5: Verified all lint/type checks pass. Fixed import formatting in main.py, shortened deprecation message, and added pyright directives for test files. Total test count: 1035 API + 735 web = 1770 tests.

### Review Follow-up Fixes

- Made WebSocketTokenService methods async with asyncio.Lock for thread-safety in concurrent environments
- Added MAX_TOKEN_COUNT (10000) limit with oldest-first eviction to prevent memory exhaustion
- Added concurrency tests (TestConcurrency class with 3 tests using asyncio.gather)
- Added token expiry during active connection test (TestTokenExpiryDuringConnection class)
- Updated all test files to use async token service methods
- Total test count after review fixes: 1041 API + 735 web = 1776 tests

### File List

**Task 1:**
- `api/src/vintagestory_api/models/ws_token.py` (created) - Pydantic models for token response
- `api/src/vintagestory_api/services/ws_token_service.py` (created) - Token service with TTL
- `api/tests/test_ws_token_service.py` (created) - 23 unit tests

**Task 2:**
- `api/src/vintagestory_api/routers/ws_token.py` (created) - Token request endpoint
- `api/src/vintagestory_api/main.py` (modified) - Registered ws_token router
- `api/tests/test_ws_token_router.py` (created) - 16 integration tests

**Task 3:**
- `api/src/vintagestory_api/routers/console.py` (modified) - Added token param and _verify_ws_auth helper
- `api/tests/console/conftest.py` (modified) - Added token service fixture
- `api/tests/console/test_websocket_token_auth.py` (created) - 14 token auth tests

**Task 4:**
- `web/src/api/ws-token.ts` (created) - Token request function with WebSocketTokenError class
- `web/src/api/ws-token.test.ts` (created) - 6 tests for token API
- `web/src/hooks/use-console-websocket.ts` (modified) - Added token request before connect, token_error state
- `web/src/hooks/use-console-websocket.test.ts` (modified) - Updated for async token flow, 25 tests
- `web/src/hooks/use-log-stream.ts` (modified) - Added token request before connect, token_error state
- `web/src/components/terminal/ConnectionStatus.tsx` (modified) - Added token_error state handling
- `web/src/components/ConsolePanel.tsx` (modified) - Updated state type for token_error
- `web/src/features/terminal/Terminal.test.tsx` (modified) - Added ws-token mock, 23 tests

**Task 5:**
- `api/src/vintagestory_api/main.py` (modified) - Fixed import formatting
- `api/src/vintagestory_api/routers/console.py` (modified) - Shortened deprecation message
- `api/tests/console/test_websocket_token_auth.py` (modified) - Removed unused import
- `api/tests/test_ws_token_service.py` (modified) - Added pyright directive with justification
