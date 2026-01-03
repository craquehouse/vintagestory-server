# Story 9.1: Secure WebSocket Authentication

Status: ready-for-dev

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

- [ ] Task 1: Create WebSocket token model and generation + tests (AC: 1)
  - [ ] Subtask 1.1: Create `api/src/vintagestory_api/models/ws_token.py` with `WebSocketToken` and `WebSocketTokenResponse` Pydantic models
  - [ ] Subtask 1.2: Create `api/src/vintagestory_api/services/ws_token_service.py` with token generation using `secrets.token_urlsafe()` and in-memory token store
  - [ ] Subtask 1.3: Implement token expiry (5 minute TTL) with cleanup of expired tokens
  - [ ] Subtask 1.4: Write unit tests in `api/tests/services/test_ws_token_service.py` for token generation, validation, and expiry

- [ ] Task 2: Create WebSocket token endpoint + tests (AC: 1, 6)
  - [ ] Subtask 2.1: Create `api/src/vintagestory_api/routers/ws_token.py` with `POST /api/v1alpha1/auth/ws-token` endpoint
  - [ ] Subtask 2.2: Require valid API key (Admin or Monitor) via existing `get_current_user` dependency
  - [ ] Subtask 2.3: Return token with role embedded for WebSocket authorization
  - [ ] Subtask 2.4: Register router in `api/src/vintagestory_api/main.py`
  - [ ] Subtask 2.5: Write integration tests in `api/tests/routers/test_ws_token.py` for token request with Admin/Monitor keys

- [ ] Task 3: Update WebSocket endpoints to use token auth + tests (AC: 2, 3, 6)
  - [ ] Subtask 3.1: Add `token` query parameter to `console_websocket()` in `console.py`
  - [ ] Subtask 3.2: Add `token` query parameter to `logs_websocket()` in `console.py`
  - [ ] Subtask 3.3: Create `_verify_ws_token()` helper that validates token and returns role
  - [ ] Subtask 3.4: Support both `token` and legacy `api_key` params (token takes precedence) for backwards compatibility during transition
  - [ ] Subtask 3.5: Update existing WebSocket tests to use token auth
  - [ ] Subtask 3.6: Add tests for invalid token rejection (4001) and Monitor role rejection for console (4003)

- [ ] Task 4: Frontend WebSocket token integration + tests (AC: 5)
  - [ ] Subtask 4.1: Create `web/src/api/ws-token.ts` with `requestWebSocketToken()` function
  - [ ] Subtask 4.2: Update `web/src/hooks/use-console.ts` to request token before connecting
  - [ ] Subtask 4.3: Update `web/src/hooks/use-log-stream.ts` to request token before connecting
  - [ ] Subtask 4.4: Handle token request errors gracefully with user feedback
  - [ ] Subtask 4.5: Write tests in `web/src/api/ws-token.test.ts` for token request
  - [ ] Subtask 4.6: Update hook tests to verify token flow

- [ ] Task 5: Documentation and deprecation notices + cleanup (AC: 4)
  - [ ] Subtask 5.1: Add deprecation warning log when `api_key` query param is used on WebSocket endpoints
  - [ ] Subtask 5.2: Update API documentation/comments to reflect new token auth flow
  - [ ] Subtask 5.3: Verify all tests pass with `just check`
  - [ ] Subtask 5.4: Update story file with completion notes

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

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

### File List
