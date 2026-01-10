# Core Architectural Decisions

## Decision Priority Analysis

**Critical Decisions (Block Implementation):**

- State persistence pattern (in-memory + JSON sync with atomic writes)
- API versioning strategy (v1alpha1)
- WebSocket implementation (built-in Starlette with reconnection pattern)
- Docker deployment strategy (single container)

**Important Decisions (Shape Architecture):**

- HTTP client for external APIs (httpx)
- Frontend state management (TanStack Query + Context with clear boundaries)
- Routing library (React Router v7)
- Logging framework (structlog with env-based configuration)

**Deferred Decisions (Post-MVP):**

- Prometheus metrics implementation
- Backup storage strategy
- Multi-server fleet patterns

## Data Architecture

| Decision           | Choice                     | Rationale                                                             |
| ------------------ | -------------------------- | --------------------------------------------------------------------- |
| **Persistence**    | In-memory + JSON file sync | Fast reads, durable writes, no database overhead                      |
| **State Location** | `data/state.json`          | Single source of truth for server state, mod states, pending restarts |
| **Validation**     | Pydantic v2 models         | Type-safe, automatic serialization                                    |
| **Write Safety**   | Atomic file writes         | Prevents corruption on crash (temp file + rename)                     |

**State Management Pattern:**

```
┌─────────────────┐     ┌──────────────┐
│  In-Memory      │────▶│  JSON File   │
│  StateManager   │◀────│  (on disk)   │
└─────────────────┘     └──────────────┘
        │
        ▼
  Read: Memory (fast)
  Write: Memory + Atomic file sync
  Startup: Load from file
```

**Atomic Write Pattern (prevents corruption):**

```python
async def save_state(self):
    temp = self.state_path.with_suffix('.tmp')
    temp.write_text(json.dumps(self.state, indent=2))
    temp.rename(self.state_path)  # atomic on POSIX
```

## Authentication & Security

| Decision           | Choice                         | Rationale                                       |
| ------------------ | ------------------------------ | ----------------------------------------------- |
| **Auth Method**    | API key via `X-API-Key` header | Simple, stateless, sufficient for single-server |
| **Roles**          | Admin / Monitor / None         | Three-tier access per PRD                       |
| **Key Storage**    | Environment variables          | `VS_API_KEY_ADMIN`, `VS_API_KEY_MONITOR`        |
| **WebSocket Auth** | Query param on connection      | `?api_key=xxx` validated on connect             |

## API & Communication Patterns

| Decision              | Choice                                   | Rationale                                   |
| --------------------- | ---------------------------------------- | ------------------------------------------- |
| **API Style**         | REST + WebSocket                         | REST for CRUD, WebSocket for streaming      |
| **Versioning**        | `/api/v1alpha1`                          | Kubernetes-style, signals API maturity      |
| **HTTP Client**       | httpx                                    | Async-native, modern, mockable with respx   |
| **WebSocket**         | Starlette built-in                       | No additional dependencies, well-integrated |
| **Response Envelope** | `{"status": "ok\|error", "data": {...}}` | Consistent, predictable                     |

**External API Integration:**

```
┌─────────────┐     ┌─────────────┐     ┌──────────────────┐
│  API Route  │────▶│  ModService │────▶│  mods.vintagestory.at  │
└─────────────┘     └─────────────┘     └──────────────────┘
                          │
                    Cache responses
                    Handle failures gracefully
                    Timeout: 30s default
```

**WebSocket Reconnection Pattern (frontend):**

```typescript
// Exponential backoff with jitter
const reconnect = (attempt: number) => {
  const base = Math.min(1000 * 2 ** attempt, 30000); // max 30s
  const jitter = Math.random() * 1000;
  setTimeout(connect, base + jitter);
};
// Max 10 retries, then show "connection lost" UI state
```

## Frontend Architecture

| Decision                | Choice                      | Rationale                                 |
| ----------------------- | --------------------------- | ----------------------------------------- |
| **Server State**        | TanStack Query v5           | Caching, auto-refresh, optimistic updates |
| **Client State**        | React Context               | Theme, sidebar state, simple UI state     |
| **Routing**             | React Router v7             | Standard, well-documented, stable         |
| **Tables**              | TanStack Table v8           | Sorting, filtering, pagination for mods, files, jobs |
| **Field Validation**    | Zod + custom hooks          | Lightweight, no form library overhead     |
| **API Mocking (tests)** | MSW (Mock Service Worker)   | Realistic API mocking for tests           |

**State Management Boundaries:**

```
┌─────────────────────────────────────────────────────────┐
│                    TanStack Query                        │
│  (Server State - anything from API)                     │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│  │  Mods   │ │ Status  │ │ Config  │ │ Console │       │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘       │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                    React Context                         │
│  (Client State - UI only, never from API)               │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐                   │
│  │  Theme  │ │ Sidebar │ │ Toasts  │                   │
│  └─────────┘ └─────────┘ └─────────┘                   │
└─────────────────────────────────────────────────────────┘

⚠️ NEVER mix these. If data comes from API, use TanStack Query.
```

**Field Validation Pattern (Epic 6+):**

For auto-save settings fields, use Zod + custom hook instead of a form library:

```typescript
// Shared Zod schema (can be derived from OpenAPI/Pydantic)
const gameSettingSchema = z.object({
  MaxClients: z.coerce.number().min(1).max(128),
  ServerName: z.string().min(1).max(64),
  Port: z.coerce.number().min(1024).max(65535),
});

// Custom field hook
function useSettingField<T>(key: string, initialValue: T) {
  const [value, setValue] = useState(initialValue);
  const [error, setError] = useState<string | null>(null);
  const mutation = useUpdateGameSetting();

  const validate = (val: unknown): string | null => {
    const fieldSchema = gameSettingSchema.shape[key];
    if (!fieldSchema) return null;
    const result = fieldSchema.safeParse(val);
    return result.success ? null : result.error.errors[0]?.message ?? "Invalid";
  };

  const save = async () => {
    const err = validate(value);
    if (err) {
      setError(err);
      return;
    }
    setError(null);
    await mutation.mutateAsync({ key, value });
  };

  return {
    value,
    setValue,
    error: error ?? (mutation.error ? String(mutation.error) : null),
    save,
    isPending: mutation.isPending,
    isDirty: value !== initialValue,
  };
}
```

**TanStack Table Usage (Epic 6+):**

Use TanStack Table for data lists that benefit from sorting, filtering, or pagination:

| Component | Use TanStack Table? | Rationale |
|-----------|---------------------|-----------|
| Mod List | ✅ Yes | 5+ mods becomes unwieldy as cards, need search/filter |
| File Manager | ✅ Yes | File lists need sorting by name/date |
| Jobs List | ✅ Yes | Consistent pattern, even for small lists |
| Game Settings | ❌ No | Fixed list of fields, not tabular data |
| API Settings | ❌ No | Fixed list of fields, not tabular data |

```typescript
// Example: Mod table with TanStack Table
const columns = [
  columnHelper.accessor("name", { header: "Mod Name" }),
  columnHelper.accessor("version", { header: "Version" }),
  columnHelper.accessor("enabled", {
    header: "Status",
    cell: (info) => <Badge>{info.getValue() ? "Enabled" : "Disabled"}</Badge>,
  }),
  columnHelper.display({
    id: "actions",
    cell: (info) => <ModActions mod={info.row.original} />,
  }),
];
```

## Infrastructure & Deployment

| Decision               | Choice                                                | Rationale                                                                    |
| ---------------------- | ----------------------------------------------------- | ---------------------------------------------------------------------------- |
| **Logging**            | structlog                                             | Structured JSON, beautiful dev output                                        |
| **Container Strategy** | Single container (API + game server)                  | API serves static files, manages game server binary, simplified deployment   |
| **Base Image**         | `mcr.microsoft.com/dotnet/runtime:8.0.22-noble-amd64` | Ubuntu 24.04 Noble with .NET 8 (for game server) + Python 3.12 native to apt |
| **Process Manager**    | Uvicorn (single process) + Subprocess management      | Uvicorn serves API, game server runs as subprocess                           |

**Logging Configuration:**

```python
# Dev mode: colorful, human-readable
# Prod mode: JSON, machine-parseable
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer() if DEV else structlog.processors.JSONRenderer()
    ]
)

# Game server subprocess stdout/stderr captured and logged with context
# Subprocess logs tagged with component="game_server"
```

**Docker Architecture:**

```
┌────────────────────────────────────────────────────┐
│  vintagestory-manager container (Single)         │
│  ┌────────────────────────────────────────┐   │
│  │  FastAPI + Uvicorn (Main Process)   │   │
│  │  - Serves /api/* endpoints           │   │
│  │  - Serves /* static files            │   │
│  │  - WebSocket /ws/console            │   │
│  │  - Manages game server subprocess     │   │
│  └────────────────────────────────────────┘   │
│                  │                          │
│                  ▼                          │
│  ┌────────────────────────────────────────┐   │
│  │  VintageStory Server (Subprocess)    │   │
│  │  - Game binary runs in container    │   │
│  │  - Managed by API lifecycle         │   │
│  └────────────────────────────────────────┘   │
│                  │                          │
│                  ▼                          │
│  ┌────────────────────────────────────────┐   │
│  │  Mounted Volumes                    │   │
│  │  - /data (state, config, mods)      │   │
│  └────────────────────────────────────────┘   │
└────────────────────────────────────────────────────┘
```

**Single Container Strategy Rationale:**

- Simplifies deployment (one compose service instead of two)
- Shared data volume is easier to manage
- Lower infrastructure overhead (no inter-container networking)
- Game server is managed as subprocess, not standalone service

**Tradeoffs:**

- Larger container image (~300MB vs ~150MB with python:3.13-slim)
- Game server crash can affect API (though API should survive crashes per NFR8)
- Cannot scale API and game server independently (not required for MVP)
- Requires careful subprocess management and signal handling

## Testability Considerations

| Component           | Testing Strategy                   | Tools                        |
| ------------------- | ---------------------------------- | ---------------------------- |
| StateManager        | Unit tests with temp files         | pytest                       |
| Mod API integration | Mock external API                  | respx                        |
| WebSocket streaming | Abstract stdout capture as service | pytest-asyncio               |
| Frontend components | Component + integration tests      | @testing-library/react + MSW |

## Decision Impact Analysis

**Implementation Sequence:**

1. Project scaffolding (mise, uv, bun, directory structure)
2. API skeleton with health endpoints
3. State management service (with atomic writes)
4. Authentication middleware
5. Docker deployment configuration (single container with .NET base)
6. Server lifecycle endpoints (subprocess management)
7. WebSocket console streaming (with reconnection)
8. Mod management endpoints
9. Frontend shell with routing
10. Dashboard + server controls
11. Mod management UI
12. Console terminal view

**Cross-Component Dependencies:**

- StateManager → used by all services (atomic writes critical)
- Auth middleware → protects all routes
- WebSocket → depends on StateManager for status updates
- Frontend → depends on all API endpoints
- Reconnection logic → must be implemented in frontend WebSocket hook
