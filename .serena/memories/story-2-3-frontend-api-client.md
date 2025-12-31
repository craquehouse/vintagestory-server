# Story 2.3: Frontend API Client with Authentication

Status: done

## Summary
Created frontend API client with automatic X-API-Key header injection, snake_case/camelCase transformation, and TanStack Query integration.

## Architecture
```
TanStack Query Hooks (useServerStatus, useMods, etc.)
                │
API Client (client.ts) - adds X-API-Key, transforms keys
                │
fetch() with base URL from env
```

## Key Features

### Key Transformation
```typescript
snakeToCamel(obj)  // API response → Frontend
camelToSnake(obj)  // Frontend → API request
```

### Error Classes
- `ApiError` - Base error with code, message, status
- `UnauthorizedError` - 401 errors
- `ForbiddenError` - 403 errors

### TanStack Query Config
- staleTime: 30 seconds
- No retry on auth errors (401, 403)
- refetchOnWindowFocus enabled

### Error Display
Uses Sonner toasts for user-friendly error notifications.

## Files Created
- web/src/api/client.ts, client.test.ts
- web/src/api/types.ts, errors.ts
- web/src/api/error-handler.ts, error-handler.test.ts
- web/src/api/query-client.ts, query-client.test.ts
- web/src/api/query-keys.ts
- web/src/api/hooks/use-auth-me.ts, use-auth-me.test.tsx
- web/.env.example

## Environment Variables
- VITE_API_KEY - API key for authentication
- VITE_API_BASE_URL - Base URL (empty for same-origin)

## Tests
45 new API tests, 112 total tests passing
