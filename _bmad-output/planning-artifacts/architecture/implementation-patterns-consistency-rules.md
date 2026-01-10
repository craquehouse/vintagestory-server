# Implementation Patterns & Consistency Rules

## Pattern Categories Defined

**Critical Conflict Points Identified:** 12 areas where AI agents could make different choices

These patterns ensure all AI agents write compatible, consistent code.

## Project Structure

**Root Layout (Single Container Strategy):**

```
vintagestory-server/
├── api/                    # FastAPI backend
├── web/                    # React frontend
├── Dockerfile              # Single container (builds both)
├── docker-compose.yaml     # Development/deployment
├── .mise.toml              # Tool versions
└── README.md
```

**Rationale:** Single container serves static files from API, so Dockerfile belongs at root to orchestrate both builds.

## Naming Patterns

**API Naming Conventions:**

| Element      | Convention               | Example                                            |
| ------------ | ------------------------ | -------------------------------------------------- |
| Endpoints    | Plural nouns, kebab-case | `/api/v1alpha1/mods`, `/api/v1alpha1/config-files` |
| Route params | snake_case               | `/mods/{mod_slug}`                                 |
| Query params | snake_case               | `?game_version=1.21.3`                             |
| Headers      | X-Prefix for custom      | `X-API-Key`                                        |

**Python Naming Conventions:**

| Element       | Convention      | Example                              |
| ------------- | --------------- | ------------------------------------ |
| Files/modules | snake_case      | `mod_service.py`, `server_router.py` |
| Classes       | PascalCase      | `ModService`, `StateManager`         |
| Functions     | snake_case      | `get_mod_details()`, `install_mod()` |
| Variables     | snake_case      | `mod_slug`, `game_version`           |
| Constants     | SCREAMING_SNAKE | `DEFAULT_TIMEOUT`, `MAX_RETRIES`     |

**TypeScript Naming Conventions:**

| Element          | Convention                  | Example                                |
| ---------------- | --------------------------- | -------------------------------------- |
| Files            | kebab-case                  | `mod-card.tsx`, `use-server-status.ts` |
| Components       | PascalCase                  | `ModCard`, `ServerStatus`              |
| Hooks            | camelCase with `use` prefix | `useServerStatus`, `useInstallMod`     |
| Functions        | camelCase                   | `formatModVersion()`, `parseSlug()`    |
| Variables        | camelCase                   | `modSlug`, `isLoading`                 |
| Types/Interfaces | PascalCase                  | `Mod`, `ServerState`, `ApiResponse`    |

## JSON Field Naming (API Boundary)

**Convention:** API returns snake_case, frontend transforms to camelCase

```python
# API Response (Python)
{
    "status": "ok",
    "data": {
        "mod_slug": "smithingplus",
        "is_compatible": true,
        "game_version": "1.21.3"
    }
}
```

```typescript
// Frontend (after API client transform)
interface Mod {
  modSlug: string;
  isCompatible: boolean;
  gameVersion: string;
}
```

**API Client Pattern:**

```typescript
// web/src/api/client.ts
const transformKeys = (obj: unknown): unknown => {
  // snake_case → camelCase transformation
};
```

## Structure Patterns

**Backend Structure (`api/`):**

```
api/
├── pyproject.toml
├── uv.lock
├── src/
│   └── vintagestory_api/
│       ├── __init__.py
│       ├── main.py              # FastAPI app entry
│       ├── config.py            # pydantic-settings
│       ├── routers/
│       │   ├── __init__.py
│       │   ├── server.py        # /server/* endpoints
│       │   ├── mods.py          # /mods/* endpoints
│       │   ├── config.py        # /config/* endpoints
│       │   └── health.py        # /healthz, /readyz
│       ├── services/
│       │   ├── __init__.py
│       │   ├── state.py         # StateManager
│       │   ├── server.py        # ServerLifecycle
│       │   ├── mods.py          # ModService
│       │   └── console.py       # ConsoleBuffer
│       ├── models/
│       │   ├── __init__.py
│       │   ├── state.py         # State Pydantic models
│       │   ├── mods.py          # Mod Pydantic models
│       │   └── responses.py     # API response envelopes
│       └── middleware/
│           ├── __init__.py
│           └── auth.py          # API key auth
└── tests/
    ├── conftest.py
    ├── test_server.py
    ├── test_mods.py
    └── test_state.py
```

**Frontend Structure (`web/`):**

```
web/
├── package.json
├── bun.lock
├── vite.config.ts
├── tsconfig.json
├── index.html
├── src/
│   ├── main.tsx                 # Entry point
│   ├── App.tsx                  # Router setup
│   ├── api/
│   │   ├── client.ts            # API client with transforms
│   │   ├── mods.ts              # Mod API functions
│   │   ├── server.ts            # Server API functions
│   │   └── types.ts             # API response types
│   ├── components/
│   │   ├── ui/                  # shadcn/ui components
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Header.tsx
│   │   │   └── Layout.tsx
│   │   ├── ServerStatusBadge.tsx
│   │   ├── CompatibilityBadge.tsx
│   │   └── ModCard.tsx
│   ├── features/
│   │   ├── dashboard/
│   │   │   ├── Dashboard.tsx
│   │   │   └── ServerControls.tsx
│   │   ├── mods/
│   │   │   ├── ModList.tsx
│   │   │   ├── ModInstall.tsx
│   │   │   └── ModTable.tsx
│   │   ├── config/
│   │   │   └── ConfigEditor.tsx
│   │   └── terminal/
│   │       ├── Terminal.tsx
│   │       └── ConsoleView.tsx
│   ├── hooks/
│   │   ├── use-server-status.ts
│   │   ├── use-websocket.ts
│   │   └── use-theme.ts
│   ├── contexts/
│   │   ├── ThemeContext.tsx
│   │   └── SidebarContext.tsx
│   ├── lib/
│   │   └── utils.ts             # shadcn/ui utilities
│   └── styles/
│       ├── index.css            # Tailwind imports
│       └── themes/
│           ├── mocha.json       # Catppuccin Mocha
│           └── latte.json       # Catppuccin Latte
├── public/
└── tests/
    └── components/
        └── ModCard.test.tsx     # Co-located test example
```

## Test Organization

| Stack    | Pattern                     | Location                       |
| -------- | --------------------------- | ------------------------------ |
| Backend  | Separate `tests/` directory | `api/tests/test_*.py`          |
| Frontend | Co-located with components  | `*.test.tsx` next to component |

**Test Naming:**

- Python: `test_<module>.py` with `test_<function>` methods
- TypeScript: `<Component>.test.tsx` with `describe/it` blocks

## UI Testing Philosophy

**Dual Verification Approach:**

UI stories require both automated tests AND manual browser verification. These are complementary, not redundant:

| Verification Type | Purpose | What It Catches |
|---|---|---|
| **Automated Tests** | Verify function | Logic errors, API integration, state management, edge cases |
| **Manual Browser Testing** | Verify UX and "feel" | Visual layout issues, interaction quirks, animation problems, accessibility gaps |

**Why Both Are Needed:**

- Automated tests verify that code _works correctly_ (functional correctness)
- Manual verification verifies that the UI _feels right_ (user experience quality)
- Tests can pass while the UI looks broken, has awkward spacing, or feels sluggish
- Manual verification catches visual/UX issues that automated tests fundamentally cannot detect

**Example from Story 8.3:**

Story 8.3 (Job Configuration UI) had 31 comprehensive web tests covering all acceptance criteria. Manual browser verification was still required because:
- Tests verified the JobsTable rendered correct data
- Manual verification confirmed the table looked good, columns aligned properly, and status badges were visually clear

**Standard Practice:**

All UI-focused stories MUST include a manual browser verification task as part of acceptance criteria validation. This is not "belt-and-suspenders" overhead—it's defense in depth that catches different categories of issues.

## Format Patterns

**API Response Envelope:**

```python
# Success Response
{
    "status": "ok",
    "data": { ... }
}

# Error Response (FastAPI Standard)
{
    "detail": {
        "code": "MOD_NOT_FOUND",      # Machine-readable
        "message": "Mod 'xyz' not found",  # Human-readable
        "details": {}                  # Optional context
    }
}
```

**Note:** We use FastAPI's standard `detail` pattern for error responses.
This aligns with FastAPI's built-in HTTPException handling and avoids
requiring custom exception handlers. The `detail` field contains the same
structured error data as a custom envelope would, just nested under FastAPI's
standard response key.

**Error Codes (constants):**

```python
# api/src/vintagestory_api/models/errors.py
class ErrorCode:
    MOD_NOT_FOUND = "MOD_NOT_FOUND"
    MOD_INCOMPATIBLE = "MOD_INCOMPATIBLE"
    SERVER_NOT_RUNNING = "SERVER_NOT_RUNNING"
    INVALID_CONFIG = "INVALID_CONFIG"
    EXTERNAL_API_ERROR = "EXTERNAL_API_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
```

**HTTP Status Code Usage:**

| Status | Usage                              |
| ------ | ---------------------------------- |
| 200    | Success (GET, PUT)                 |
| 201    | Created (POST that creates)        |
| 204    | No content (DELETE)                |
| 400    | Bad request (validation error)     |
| 401    | Unauthorized (missing/invalid key) |
| 403    | Forbidden (insufficient role)      |
| 404    | Not found                          |
| 500    | Server error                       |
| 502    | External API error                 |

## Communication Patterns

**TanStack Query Keys:**

```typescript
// Hierarchical array format
const queryKeys = {
  mods: {
    all: ["mods"] as const,
    detail: (slug: string) => ["mods", slug] as const,
    updates: ["mods", "updates"] as const,
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

**Mutation Naming:**

```typescript
// Verb-first, matches API action
useInstallMod()
useRemoveMod()
useEnableMod()
useRestartServer()
useSaveConfig()
```

**Boolean State Naming:**

```typescript
// Always use 'is' prefix
isLoading
isConnected
isCompatible
isEnabled
isPending
```

## Process Patterns

**Loading States:**

```typescript
// TanStack Query provides these automatically
const { data, isLoading, isError, error } = useQuery(...);

// For mutations
const { mutate, isPending } = useMutation(...);
```

**Error Handling (Frontend):**

```typescript
// Global error boundary for unexpected errors
// Toast notifications for operation errors
// Inline error messages for form validation
```

**Error Handling (Backend):**

```python
# Use FastAPI HTTPException with standard envelope
raise HTTPException(
    status_code=404,
    detail={
        "code": ErrorCode.MOD_NOT_FOUND,
        "message": f"Mod '{slug}' not found",
        "details": {"slug": slug}
    }
)
```

## Enforcement Guidelines

**All AI Agents MUST:**

1. Follow naming conventions exactly as specified above
2. Place files in the defined directory structure
3. Use the standard API response envelope for all endpoints
4. Transform JSON keys at the API client boundary (snake_case ↔ camelCase)
5. Use TanStack Query for all server state, React Context for UI state only
6. Write tests using the specified patterns and locations
7. Use error codes from the defined constants

**Pattern Enforcement:**

- Ruff (Python) configured to enforce naming conventions
- ESLint (TypeScript) configured for naming rules
- PR reviews should check pattern compliance
- Architecture doc is the source of truth for patterns

## Anti-Patterns to Avoid

| Avoid                                      | Do Instead                              |
| ------------------------------------------ | --------------------------------------- |
| `getUserData()` in Python                  | `get_user_data()`                       |
| `mod-service.py` filename                  | `mod_service.py`                        |
| `ModCard.tsx` filename with default export | Keep PascalCase, it's correct for React |
| Mixing snake_case in frontend code         | Transform at API boundary               |
| Storing API data in React Context          | Use TanStack Query                      |
| `tests/` folder in web/                    | Co-locate tests with components         |
| Custom loading state variables             | Use TanStack Query's isLoading          |
| Generic error messages                     | Use error codes + descriptive messages  |

## Code Comment Patterns

**Placeholder Code for Future Stories:**

When writing placeholder code that will be implemented in a future story, use TODO comments with the story number to make the forward reference explicit and discoverable:

```python
# ✅ CORRECT - Explicit story reference
# TODO: Story 8.3 - Register server_versions_check job
pass

# ❌ INCORRECT - Ambiguous placeholder
# Placeholder for server versions job
pass
```

**Benefits:**
- Future story work is discoverable via TODO search
- Code reviewers understand the placeholder is intentional, not dead code
- Clear traceability between placeholder and planned implementation

**TODO Format:**
```
# TODO: Story X.Y - Brief description of what will be implemented
```
