# Story 2.3: Frontend API Client with Authentication

Status: done

---

## Story

As a **frontend developer**,
I want **an API client that handles authentication and key transformation**,
so that **all API calls are properly authenticated and response data is correctly formatted**.

---

## Acceptance Criteria

1. **Given** the frontend application is configured, **When** API calls are made, **Then** the `X-API-Key` header is automatically included from configuration

2. **Given** the API returns a response with snake_case fields, **When** the API client processes the response, **Then** fields are transformed to camelCase for frontend consumption

3. **Given** the API returns a 401 Unauthorized response, **When** the frontend receives the error, **Then** an appropriate error state is displayed to the user, **And** the user is informed that authentication failed

4. **Given** the API returns a 403 Forbidden response, **When** the frontend receives the error, **Then** an appropriate error state is displayed, **And** the user is informed they lack permission for the operation

5. **Given** TanStack Query is configured, **When** API calls are made, **Then** server state is managed through TanStack Query hooks, **And** client-only state (theme, sidebar) uses React Context

---

## Tasks / Subtasks

- [x] Task 1: Create API client core with fetch wrapper + tests (AC: 1, 2)
  - [x] 1.1: Create `web/src/api/client.ts` with base fetch function that adds `X-API-Key` header
  - [x] 1.2: Implement `transformKeys()` utility for snake_case to camelCase conversion (and reverse for request bodies)
  - [x] 1.3: Create `web/src/api/types.ts` for API response types (ApiResponse, ApiError)
  - [x] 1.4: Write unit tests for key transformation functions
  - [x] 1.5: Write tests for header injection

- [x] Task 2: Configure TanStack Query provider + tests (AC: 5)
  - [x] 2.1: Create `web/src/api/query-client.ts` with QueryClient configuration
  - [x] 2.2: Add QueryClientProvider to `main.tsx` wrapping the app
  - [x] 2.3: Configure default query options (staleTime, retry, refetch on window focus)
  - [x] 2.4: Write test verifying QueryClientProvider is correctly configured

- [x] Task 3: Implement error handling + tests (AC: 3, 4)
  - [x] 3.1: Create `web/src/api/errors.ts` with custom error classes (UnauthorizedError, ForbiddenError)
  - [x] 3.2: Implement error parsing in client that throws appropriate error types
  - [x] 3.3: Create error boundary or global error handler for auth errors
  - [x] 3.4: Integrate with Sonner toast for error notifications
  - [x] 3.5: Write tests for 401 error handling and user notification
  - [x] 3.6: Write tests for 403 error handling and user notification

- [x] Task 4: Create example API hooks for verification + tests (AC: 1-5)
  - [x] 4.1: Create `web/src/api/hooks/use-auth-me.ts` hook using the `/api/v1alpha1/auth/me` endpoint
  - [x] 4.2: Verify hook properly uses TanStack Query with auth headers
  - [x] 4.3: Write integration test demonstrating full flow: fetch → transform → display

## Review Follow-ups (AI)

- [x] [AI-Review][HIGH] Fix test infrastructure - **RESOLVED: Tests pass correctly with `bun run test` (vitest)**. The reviewer ran `bun test` (Bun's native test runner) instead of `bun run test` which invokes Vitest. Vitest is configured with jsdom environment and proper setup in `vitest.config.ts`. All 112 tests pass. [web/tests/setup.ts:44]
- [x] [AI-Review][HIGH] Correct false claims in Dev Agent Record - **RESOLVED: Claims are accurate**. Running `bun run test` shows "112 passed" as documented. The discrepancy was due to using wrong test command. [_bmad-output/implementation-artifacts/2-3-frontend-api-client-with-authentication.md:548]
- [x] [AI-Review][MEDIUM] Fix all React component test failures - **RESOLVED: No failures exist**. All component tests pass when using the correct test runner (`bun run test`). The vitest.config.ts properly configures jsdom environment. [web/tests/setup.ts]
- [x] [AI-Review][LOW] Add environment variable documentation - **RESOLVED**: Created `web/.env.example` documenting `VITE_API_KEY` and `VITE_API_BASE_URL`. [web/.env.example]
- [x] [AI-Review][LOW] Create local development .env file - **RESOLVED**: `.env` is already in `.gitignore`. Developers should copy `.env.example` to `.env` and fill in their values. Not committing actual `.env` file is the correct practice. [web/.env]

---

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Do not batch tests into a separate "Write tests" task at the end

### Architecture & Patterns

**API Client Architecture:**

```
┌────────────────────────────────────────────────────────────────┐
│                    TanStack Query Hooks                         │
│   useServerStatus(), useMods(), useAuthMe(), etc.               │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                       API Client (client.ts)                    │
│   - Adds X-API-Key header automatically                         │
│   - Transforms snake_case → camelCase on responses              │
│   - Transforms camelCase → snake_case on request bodies         │
│   - Parses errors and throws typed exceptions                   │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                     fetch() (native)                            │
│   Base URL: derived from window.location or env var             │
└────────────────────────────────────────────────────────────────┘
```

**Key Transformation Pattern:**

```typescript
// web/src/api/client.ts

/**
 * Recursively transforms object keys from snake_case to camelCase.
 * Handles nested objects and arrays.
 */
export function snakeToCamel(obj: unknown): unknown {
  if (Array.isArray(obj)) {
    return obj.map(snakeToCamel);
  }
  if (obj !== null && typeof obj === "object") {
    return Object.fromEntries(
      Object.entries(obj).map(([key, value]) => [
        key.replace(/_([a-z])/g, (_, c) => c.toUpperCase()),
        snakeToCamel(value),
      ])
    );
  }
  return obj;
}

/**
 * Recursively transforms object keys from camelCase to snake_case.
 * Used for request bodies sent to the API.
 */
export function camelToSnake(obj: unknown): unknown {
  if (Array.isArray(obj)) {
    return obj.map(camelToSnake);
  }
  if (obj !== null && typeof obj === "object") {
    return Object.fromEntries(
      Object.entries(obj).map(([key, value]) => [
        key.replace(/([A-Z])/g, "_$1").toLowerCase(),
        camelToSnake(value),
      ])
    );
  }
  return obj;
}
```

**API Client Core Pattern:**

```typescript
// web/src/api/client.ts

interface ApiConfig {
  baseUrl: string;
  apiKey: string;
}

function getConfig(): ApiConfig {
  // In development, read from env or use defaults
  // In production, read from runtime config
  return {
    baseUrl: import.meta.env.VITE_API_BASE_URL || "",
    apiKey: import.meta.env.VITE_API_KEY || "",
  };
}

export async function apiClient<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const config = getConfig();
  const url = `${config.baseUrl}${path}`;

  const headers = new Headers(options.headers);
  headers.set("X-API-Key", config.apiKey);
  headers.set("Content-Type", "application/json");

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    await handleApiError(response);
  }

  const data = await response.json();

  // Transform snake_case to camelCase
  return snakeToCamel(data) as T;
}
```

**Error Handling Pattern:**

```typescript
// web/src/api/errors.ts

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number,
    public details?: Record<string, unknown>
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export class UnauthorizedError extends ApiError {
  constructor(message: string = "Authentication required") {
    super("UNAUTHORIZED", message, 401);
    this.name = "UnauthorizedError";
  }
}

export class ForbiddenError extends ApiError {
  constructor(message: string = "Access denied") {
    super("FORBIDDEN", message, 403);
    this.name = "ForbiddenError";
  }
}

// In client.ts
async function handleApiError(response: Response): Promise<never> {
  let errorData: { detail?: { code?: string; message?: string } } = {};

  try {
    errorData = await response.json();
  } catch {
    // Response wasn't JSON
  }

  const code = errorData.detail?.code || "UNKNOWN";
  const message = errorData.detail?.message || response.statusText;

  if (response.status === 401) {
    throw new UnauthorizedError(message);
  }
  if (response.status === 403) {
    throw new ForbiddenError(message);
  }

  throw new ApiError(code, message, response.status);
}
```

**TanStack Query Configuration:**

```typescript
// web/src/api/query-client.ts
import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30 * 1000, // 30 seconds
      retry: (failureCount, error) => {
        // Don't retry on auth errors
        if (error instanceof UnauthorizedError || error instanceof ForbiddenError) {
          return false;
        }
        return failureCount < 3;
      },
      refetchOnWindowFocus: true,
    },
  },
});
```

**Query Keys Pattern (from Architecture):**

```typescript
// web/src/api/query-keys.ts
export const queryKeys = {
  auth: {
    me: ["auth", "me"] as const,
  },
  mods: {
    all: ["mods"] as const,
    detail: (slug: string) => ["mods", slug] as const,
  },
  server: {
    status: ["server", "status"] as const,
  },
  config: {
    files: ["config", "files"] as const,
    file: (name: string) => ["config", "files", name] as const,
  },
};
```

**Example Hook Pattern:**

```typescript
// web/src/api/hooks/use-auth-me.ts
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../client";
import { queryKeys } from "../query-keys";

interface AuthMeResponse {
  status: string;
  data: {
    role: string;
  };
}

export function useAuthMe() {
  return useQuery({
    queryKey: queryKeys.auth.me,
    queryFn: () => apiClient<AuthMeResponse>("/api/v1alpha1/auth/me"),
    // Don't automatically refetch this - role won't change during session
    staleTime: Infinity,
  });
}
```

### Error Display Pattern

```typescript
// Using Sonner toast for error notifications
import { toast } from "sonner";

// Global error handler for TanStack Query
queryClient.setDefaultOptions({
  mutations: {
    onError: (error) => {
      if (error instanceof UnauthorizedError) {
        toast.error("Authentication Failed", {
          description: "Please check your API key configuration.",
        });
      } else if (error instanceof ForbiddenError) {
        toast.error("Access Denied", {
          description: error.message,
        });
      } else if (error instanceof ApiError) {
        toast.error("Error", {
          description: error.message,
        });
      }
    },
  },
});
```

### Project Structure Notes

**Files to create:**

- `web/src/api/client.ts` - Core API client with fetch wrapper and key transformation
- `web/src/api/types.ts` - TypeScript types for API responses
- `web/src/api/errors.ts` - Custom error classes for auth errors
- `web/src/api/query-client.ts` - TanStack Query client configuration
- `web/src/api/query-keys.ts` - Centralized query key definitions
- `web/src/api/hooks/use-auth-me.ts` - Example hook for verification
- `web/src/api/client.test.ts` - Tests for API client
- `web/src/api/hooks/use-auth-me.test.ts` - Tests for hook

**Files to modify:**

- `web/src/main.tsx` - Add QueryClientProvider wrapper
- `web/.env.example` - Document VITE_API_KEY environment variable
- `web/vite.config.ts` - May need proxy configuration for development

**Tests location (co-located per architecture):**

- Tests should be placed next to the files they test (e.g., `client.test.ts` next to `client.ts`)

### API Endpoints Available for Testing

From Stories 2.1 and 2.2, the following endpoints exist:

| Endpoint | Method | Auth Required | Role Required |
|----------|--------|---------------|---------------|
| `/healthz` | GET | No | None |
| `/readyz` | GET | No | None |
| `/api/v1alpha1/auth/me` | GET | Yes | Any (returns role) |
| `/api/v1alpha1/test/read` | GET | Yes | Any (DEBUG only) |
| `/api/v1alpha1/test/write` | POST | Yes | Admin (DEBUG only) |
| `/api/v1alpha1/test/console` | GET | Yes | Admin (DEBUG only) |

**Use `/api/v1alpha1/auth/me` for verification** - it returns the current user's role and is the primary endpoint for testing the API client.

### Previous Story Intelligence

**From Story 2.1:**
- API key header is `X-API-Key` (case-sensitive in practice)
- 401 responses use format: `{"detail": {"code": "UNAUTHORIZED", "message": "..."}}`
- Two roles: "admin" and "monitor"

**From Story 2.2:**
- 403 responses use format: `{"detail": {"code": "FORBIDDEN", "message": "..."}}`
- Console access requires Admin role
- Write operations require Admin role

**From Epic 1 Retrospective:**
- Tests must accompany implementation
- Error envelope uses FastAPI's standard `detail` pattern

### Development Environment Setup

**Environment Variables for Frontend:**

Create `web/.env` with:
```bash
# API Key for development
VITE_API_KEY=your-dev-admin-key

# Base URL (empty for same-origin, or full URL for different server)
VITE_API_BASE_URL=
```

**Vite Proxy Configuration (optional):**

If running frontend separately from backend, add proxy to `vite.config.ts`:
```typescript
export default defineConfig({
  // ... existing config
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/healthz": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/readyz": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
```

### Existing Frontend Patterns to Follow

**From Story 1.3 (Frontend Shell):**

- React 19.2 with TypeScript strict mode
- TanStack Query v5 already installed (`@tanstack/react-query: ^5.90.12`)
- Sonner already installed for toasts (`sonner: ^2.0.7`)
- Vitest for testing (`vitest: ^4.0.16`)
- Testing Library installed (`@testing-library/react: ^16.3.1`)
- ThemeContext and SidebarContext use React Context (UI-only state)
- Components use kebab-case filenames
- Path alias `@/` maps to `src/`

**Import pattern:**
```typescript
import { ThemeProvider } from "@/contexts/ThemeContext";
import { Button } from "@/components/ui/button";
```

### Anti-Patterns to Avoid

| Avoid | Do Instead |
|-------|------------|
| Storing server state in React Context | Use TanStack Query for all API data |
| Manual fetch without error handling | Use apiClient wrapper |
| Forgetting key transformation | Always transform at API boundary |
| Hardcoding API key | Use environment variable |
| Generic error messages | Show specific error code/message from API |
| Testing with real API | Mock with MSW or mock fetch |
| Creating `tests/` directory | Co-locate tests with source files |

### Test Patterns

```typescript
// web/src/api/client.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { snakeToCamel, camelToSnake, apiClient } from "./client";

describe("snakeToCamel", () => {
  it("transforms snake_case keys to camelCase", () => {
    const input = { user_name: "test", is_active: true };
    const expected = { userName: "test", isActive: true };
    expect(snakeToCamel(input)).toEqual(expected);
  });

  it("handles nested objects", () => {
    const input = { outer_key: { inner_key: "value" } };
    const expected = { outerKey: { innerKey: "value" } };
    expect(snakeToCamel(input)).toEqual(expected);
  });

  it("handles arrays", () => {
    const input = [{ user_id: 1 }, { user_id: 2 }];
    const expected = [{ userId: 1 }, { userId: 2 }];
    expect(snakeToCamel(input)).toEqual(expected);
  });
});

describe("apiClient", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("adds X-API-Key header to requests", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ status: "ok", data: {} }),
    });
    globalThis.fetch = mockFetch;

    await apiClient("/test");

    expect(mockFetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.any(Headers),
      })
    );

    const headers = mockFetch.mock.calls[0][1].headers;
    expect(headers.get("X-API-Key")).toBeTruthy();
  });
});
```

### References

- Architecture patterns: [Source: _bmad-output/planning-artifacts/architecture.md#Frontend Architecture]
- API versioning: [Source: _bmad-output/planning-artifacts/architecture.md#API & Communication Patterns]
- Query key pattern: [Source: _bmad-output/planning-artifacts/architecture.md#Communication Patterns]
- State management boundaries: [Source: _bmad-output/planning-artifacts/architecture.md#State Management Boundaries]
- Error response format: [Source: _bmad-output/planning-artifacts/architecture.md#Format Patterns]
- Story 2.1 auth implementation: [Source: _bmad-output/implementation-artifacts/2-1-api-key-authentication-middleware.md]
- Story 2.2 RBAC implementation: [Source: _bmad-output/implementation-artifacts/2-2-role-based-access-control-for-api-endpoints.md]
- Project context rules: [Source: project-context.md]
- TanStack Query docs: https://tanstack.com/query/v5
- Vitest docs: https://vitest.dev/

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- Fixed TypeScript build error: Refactored ApiError class to not use parameter properties due to `erasableSyntaxOnly` tsconfig option
- Fixed test file extension: Renamed `use-auth-me.test.ts` to `use-auth-me.test.tsx` for JSX support

### Completion Notes List

- **Task 1**: Created API client with automatic X-API-Key header injection and bidirectional snake_case/camelCase key transformation. 24 unit tests covering transformation functions, header injection, and response/request handling.
- **Task 2**: Configured TanStack Query with 30s staleTime, custom retry logic (no retry for auth errors), and window focus refetching. Added QueryClientProvider to main.tsx. 6 tests verifying configuration.
- **Task 3**: Implemented error handling with custom error classes (ApiError, UnauthorizedError, ForbiddenError) and global error handler showing Sonner toasts. Added Toaster component to App.tsx. 8 tests for error handling.
- **Task 4**: Created useAuthMe hook demonstrating full integration. 7 tests covering successful requests, caching, and error handling. Full integration test demonstrates fetch → transform → display flow.

**Total: 45 new API tests, 112 total tests passing, build successful**

### File List

**New files:**
- web/src/api/client.ts
- web/src/api/client.test.ts
- web/src/api/types.ts
- web/src/api/errors.ts
- web/src/api/error-handler.ts
- web/src/api/error-handler.test.ts
- web/src/api/query-client.ts
- web/src/api/query-client.test.ts
- web/src/api/query-keys.ts
- web/src/api/hooks/use-auth-me.ts
- web/src/api/hooks/use-auth-me.test.tsx
- web/.env.example

**Modified files:**
- web/src/main.tsx (added QueryClientProvider)
- web/src/App.tsx (added Toaster component)

**Deleted files:**
- web/src/api/.gitkeep

---

## Change Log

- 2025-12-27: Addressed code review findings
  - Created web/.env.example documenting VITE_API_KEY and VITE_API_BASE_URL
  - Clarified that tests use Vitest (`bun run test`), not Bun's native test runner
- 2025-12-27: Implemented frontend API client with authentication (Story 2.3)
  - Added API client with X-API-Key header injection and key transformation
  - Configured TanStack Query provider with custom retry logic
  - Implemented error handling with Sonner toast notifications
  - Created useAuthMe hook as example integration
