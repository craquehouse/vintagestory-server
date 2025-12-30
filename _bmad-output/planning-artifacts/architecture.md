---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
status: 'complete'
completedAt: '2025-12-26'
lastUpdated: '2025-12-30'
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/ux-design-specification.md'
  - 'agentdocs/vintagestory-modapi.md'
workflowType: 'architecture'
project_name: 'vintagestory-server'
user_name: 'Matt'
date: '2025-12-26'
updates:
  - date: '2025-12-28'
    section: 'Epic 5 Mod Management'
    description: 'Added mod management architecture patterns'
  - date: '2025-12-30'
    section: 'Epic 6 Configuration Management'
    description: 'Architectural pivot from file editing to console commands'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**

37 functional requirements spanning 8 capability areas:

| Category               | FRs     | Architectural Implication                                         |
| ---------------------- | ------- | ----------------------------------------------------------------- |
| Server Lifecycle       | FR1-5   | Process manager component, state machine for server status        |
| Console Access         | FR6-9   | WebSocket server, ring buffer implementation, Admin-only access   |
| Mod Management         | FR10-17 | External HTTP client, file system operations, compatibility logic |
| Game Configuration     | FR18-22 | JSON file I/O, validation layer                                   |
| Settings Management    | FR23-26 | Lightweight persistence (JSON files)                              |
| Health & Observability | FR27-30 | Kubernetes-compatible endpoints, process health checks            |
| Authentication         | FR31-37 | Middleware for API key validation, role-based access control      |
| Deployment             | FR38-39 | Docker Compose, environment variable configuration                |

**Non-Functional Requirements:**

| Category      | Key Requirements                                | Architectural Impact                                       |
| ------------- | ----------------------------------------------- | ---------------------------------------------------------- |
| Performance   | <1s console latency, <500ms API response        | In-memory operations, efficient WebSocket handling         |
| Security      | API keys never logged, in-memory console buffer | Logging configuration, no persistence for sensitive data   |
| Reliability   | API survives game crashes, auto-reconnect       | Decoupled process management, WebSocket reconnection logic |
| Integration   | Graceful mod API failures, clear error messages | Circuit breaker pattern, response caching                  |
| Observability | Structured JSON logs, contextual errors         | Logging framework configuration, error envelope design     |

**Scale & Complexity:**

- Primary domain: Full-stack web application (API + SPA + Docker)
- Complexity level: Low-Medium
- Estimated architectural components: 6-8 major components

### Technical Constraints & Dependencies

**External Dependencies:**

- VintageStory Mod Database API (`mods.vintagestory.at`) - mod lookup and downloads
- Existing Docker image (`quartzar/vintage-story-server`) or custom from `mcr.microsoft.com/dotnet/runtime:8.0`
- Game server binary downloaded at runtime

**Infrastructure Constraints:**

- No database required - JSON file persistence only
- TLS termination via external reverse proxy (Traefik, Caddy, nginx)
- Single server management (not multi-server fleet)

**Technology Decisions (from PRD/UX):**

- Backend: Python + FastAPI + uv + Ruff + pytest
- Frontend: React + Vite + TypeScript + Bun
- Components: shadcn/ui + Radix UI
- Terminal: xterm.js
- Theming: Catppuccin Mocha/Latte

### Cross-Cutting Concerns Identified

1. **Authentication & Authorization**
   - API key middleware for all protected routes
   - Role differentiation (Admin vs Monitor)
   - WebSocket authentication for console access

2. **Error Handling & Response Envelope**
   - Consistent `{"status": "ok|error", "data": {...}}` format
   - Graceful degradation for external API failures
   - Contextual error messages without exposing internals

3. **State Management**
   - Server status tracking (running/stopped/starting/stopping)
   - Pending restart queue for batched changes
   - Mod enable/disable state

4. **Real-Time Communication**
   - WebSocket for console streaming
   - Status updates pushed to connected clients
   - Reconnection handling

5. **File System Operations**
   - Config file read/write with validation
   - Mod file downloads and management
   - Game server binary installation

## Starter Template Evaluation

### Primary Technology Domains

**Backend API:** Python 3.12 + FastAPI + uv (API server with WebSocket support)
**Frontend SPA:** React 19.2 + Vite + TypeScript + Bun + shadcn/ui (Admin web interface)

### Development Environment: mise

All runtime versions managed via mise for consistent development environments.

**.mise.toml (project root):**

```toml
[tools]
python = "3.12"      # Minimum version, compatible with .NET 8 Noble base image
uv = "0.9.18"        # Pinned for reproducibility
bun = "1.3.5"        # Pinned for reproducibility

[env]
VIRTUAL_ENV = "{{config_root}}/api/.venv"
```

**Version Specification Guidelines:**

- **Development tools (uv, bun):** Pin specific versions for reproducible builds
- **Runtime (Python):** Use minimum version compatible with deployment target
- **Dependencies:** Use version ranges in pyproject.toml/package.json unless specific pin needed

**Setup commands:**

```bash
# Install mise (if not already installed)
curl https://mise.run | sh

# Trust and install project tools
mise trust
mise install
```

### Starter Options Considered

#### Backend (FastAPI)

| Option                        | Evaluation                                                       |
| ----------------------------- | ---------------------------------------------------------------- |
| uv-fastapi-example (Official) | ✅ Selected - Official Astral pattern, minimal, production-ready |
| py-fastapi-starter            | Modular but includes PostgreSQL/Alembic we don't need            |
| Full starter templates        | Over-engineered for our no-database requirement                  |

#### Frontend (React + shadcn/ui)

| Option                    | Evaluation                                          |
| ------------------------- | --------------------------------------------------- |
| Official shadcn/ui + Vite | ✅ Selected - Documented, Tailwind v4, full control |
| react-ts-shadcn-starter   | Good but third-party maintenance                    |
| vite-react-ts-shadcn-ui   | Includes extras (Husky, etc.) we may not need       |

### Selected Approach: Official Patterns

**Rationale:**

- Official documentation ensures long-term maintenance and compatibility
- Minimal starting point avoids removing unwanted dependencies
- Full control over project structure from day one
- Both patterns are actively maintained by their ecosystems
- mise ensures all developers use identical tool versions

### Backend Initialization

```bash
# From project root (with mise activated)
mkdir api && cd api
uv init --name vintagestory-api --python 3.12
uv add "fastapi[standard]" httpx pydantic-settings
uv add --dev pytest pytest-asyncio ruff

# Project structure will follow FastAPI best practices:
# api/
#   pyproject.toml
#   uv.lock
#   src/
#     vintagestory_api/
#       __init__.py
#       main.py
#       routers/
#       services/
#       models/
```

### Frontend Initialization

```bash
# From project root (with mise activated)
bun create vite web -- --template react-ts
cd web

# Pin React 19.2 specifically (security fix)
bun add react@19.2 react-dom@19.2
bun add -D @types/react@19 @types/react-dom@19

# Install Tailwind CSS v4
bun add -D tailwindcss @tailwindcss/vite

# Initialize shadcn/ui (canary required for React 19 + Tailwind v4)
bunx shadcn@canary init

# Add required components
bunx shadcn@canary add button card table dialog toast tabs input badge switch skeleton progress alert
```

### Architectural Decisions Provided by Starters

**Development Environment (mise):**

- Python 3.12 (stable, required for .NET 8 Noble base image compatibility)
- uv for Python package/venv management
- Bun for frontend runtime and package management
- All versions pinned in `.mise.toml`

**Backend (uv + FastAPI):**

- Python 3.12 with uv package management
- FastAPI with Uvicorn ASGI server
- Pydantic v2 for data validation
- Built-in OpenAPI documentation
- Async-first architecture

**Frontend (Vite + shadcn/ui):**

- React 19.2 with TypeScript (security-patched version)
- Vite 7 with SWC for fast builds
- Tailwind CSS v4 with CSS variables
- Radix UI primitives via shadcn/ui
- Path aliases (@/ → src/)

**Development Experience:**

- Backend: `fastapi dev` with hot reload
- Frontend: `bun run dev` with HMR
- Both support VS Code debugging
- mise ensures consistent tooling across machines

**Note:** Project initialization using these commands should be the first implementation story.

## Core Architectural Decisions

### Decision Priority Analysis

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

### Data Architecture

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

### Authentication & Security

| Decision           | Choice                         | Rationale                                       |
| ------------------ | ------------------------------ | ----------------------------------------------- |
| **Auth Method**    | API key via `X-API-Key` header | Simple, stateless, sufficient for single-server |
| **Roles**          | Admin / Monitor / None         | Three-tier access per PRD                       |
| **Key Storage**    | Environment variables          | `VS_API_KEY_ADMIN`, `VS_API_KEY_MONITOR`        |
| **WebSocket Auth** | Query param on connection      | `?api_key=xxx` validated on connect             |

### API & Communication Patterns

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

### Frontend Architecture

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

### Infrastructure & Deployment

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

### Testability Considerations

| Component           | Testing Strategy                   | Tools                        |
| ------------------- | ---------------------------------- | ---------------------------- |
| StateManager        | Unit tests with temp files         | pytest                       |
| Mod API integration | Mock external API                  | respx                        |
| WebSocket streaming | Abstract stdout capture as service | pytest-asyncio               |
| Frontend components | Component + integration tests      | @testing-library/react + MSW |

### Decision Impact Analysis

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

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Critical Conflict Points Identified:** 12 areas where AI agents could make different choices

These patterns ensure all AI agents write compatible, consistent code.

### Project Structure

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

### Naming Patterns

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

### JSON Field Naming (API Boundary)

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

### Structure Patterns

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

### Test Organization

| Stack    | Pattern                     | Location                       |
| -------- | --------------------------- | ------------------------------ |
| Backend  | Separate `tests/` directory | `api/tests/test_*.py`          |
| Frontend | Co-located with components  | `*.test.tsx` next to component |

**Test Naming:**

- Python: `test_<module>.py` with `test_<function>` methods
- TypeScript: `<Component>.test.tsx` with `describe/it` blocks

### Format Patterns

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

### Communication Patterns

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

### Process Patterns

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

### Enforcement Guidelines

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

### Anti-Patterns to Avoid

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

## Project Structure & Boundaries

### Complete Project Directory Structure

```
vintagestory-server/
├── .mise.toml                          # Tool version management
├── .gitignore
├── README.md
├── LICENSE
│
├── docker-compose.yaml                 # Production - pulls from registry
├── docker-compose.dev.yaml             # Development - builds locally
├── Dockerfile                          # Multi-stage: builds API + Web
│
├── api/                                # FastAPI backend
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── src/
│   │   └── vintagestory_api/
│   │       ├── __init__.py
│   │       ├── main.py
│   │       ├── config.py
│   │       ├── routers/
│   │       │   ├── __init__.py
│   │       │   ├── server.py
│   │       │   ├── mods.py
│   │       │   ├── config.py
│   │       │   └── health.py
│   │       ├── services/
│   │       │   ├── __init__.py
│   │       │   ├── state.py
│   │       │   ├── server.py
│   │       │   ├── mods.py
│   │       │   └── console.py
│   │       ├── models/
│   │       │   ├── __init__.py
│   │       │   ├── state.py
│   │       │   ├── mods.py
│   │       │   ├── responses.py
│   │       │   └── errors.py
│   │       └── middleware/
│   │           ├── __init__.py
│   │           └── auth.py
│   └── tests/
│       ├── conftest.py
│       ├── test_server.py
│       ├── test_mods.py
│       ├── test_state.py
│       └── test_auth.py
│
├── web/                                # React frontend
│   ├── package.json
│   ├── bun.lock
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── api/
│   │   │   ├── client.ts
│   │   │   ├── mods.ts
│   │   │   ├── server.ts
│   │   │   ├── config.ts
│   │   │   └── types.ts
│   │   ├── components/
│   │   │   ├── ui/                     # shadcn/ui components
│   │   │   ├── layout/
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   ├── Header.tsx
│   │   │   │   └── Layout.tsx
│   │   │   ├── ServerStatusBadge.tsx
│   │   │   ├── CompatibilityBadge.tsx
│   │   │   └── ModCard.tsx
│   │   ├── features/
│   │   │   ├── dashboard/
│   │   │   │   ├── Dashboard.tsx
│   │   │   │   └── ServerControls.tsx
│   │   │   ├── mods/
│   │   │   │   ├── ModList.tsx
│   │   │   │   ├── ModInstall.tsx
│   │   │   │   └── ModTable.tsx
│   │   │   ├── config/
│   │   │   │   └── ConfigEditor.tsx
│   │   │   └── terminal/
│   │   │       ├── Terminal.tsx
│   │   │       └── ConsoleView.tsx
│   │   ├── hooks/
│   │   │   ├── use-server-status.ts
│   │   │   ├── use-websocket.ts
│   │   │   └── use-theme.ts
│   │   ├── contexts/
│   │   │   ├── ThemeContext.tsx
│   │   │   └── SidebarContext.tsx
│   │   ├── lib/
│   │   │   └── utils.ts
│   │   └── styles/
│   │       ├── index.css
│   │       └── themes/
│   │           ├── mocha.json
│   │           └── latte.json
│   └── public/
│       └── favicon.ico
│
├── data/                               # Git-ignored, volume mount point
│   └── .gitkeep
│
└── agentdocs/                          # AI agent reference documentation
    └── vintagestory-modapi.md
```

### Container Strategy Decision

**Chosen Pattern:** Single Container (API + Game Server in Same Container)

**Architecture Decision Date:** 2025-12-26 (during Story 1.4 implementation)

**Alternatives Considered:**

| Pattern                       | Description                               | Pros                                                                                                                                       | Cons                                                                                                                                   |
| ----------------------------- | ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------- |
| **Single Container** (CHOSEN) | API and game server run in same container | ✓ Simpler deployment (one service) <br> ✓ Shared data volume <br> ✓ No inter-container networking <br> ✓ Lower infrastructure overhead | ✗ Larger image (~300MB) <br> ✗ Cannot scale independently <br> ✗ Game server crash impacts API (mitigated by subprocess management) |
| **Two Containers**            | Separate API and game server containers   | ✓ Smaller API image (~150MB) <br> ✓ Independent scaling <br> ✓ Isolated failures                                                        | ✗ More complex deployment <br> ✗ Inter-container networking <br> ✗ Shared volume management <br> ✗ Higher infrastructure overhead  |

**Rationale for Single Container:**

1. **Simplicity First:** MVP scope is single-server management, not multi-server fleet
2. **Lower Complexity:** One docker-compose service instead of two means:
   - Simpler deployment for users
   - Less networking configuration
   - Easier troubleshooting
   - Fewer points of failure
3. **Shared Resources:** Game server and API both need `/data` volume - single container is cleaner
4. **Future Flexibility:** Can migrate to two-container pattern if/when scaling becomes a requirement
5. **Subprocess Management:** Python's subprocess module is well-suited for managing game server lifecycle
6. **NFR8 Compliance:** API designed to survive game server crashes (decoupled process management)

**Tradeoffs Acknowledged:**

- **Image Size:** ~300MB vs ~150MB (acceptable for MVP, can optimize later)
- **Independent Scaling:** Not needed for single-server use case
- **Failure Isolation:** Mitigated by subprocess management and health checks
- **Runtime Dependencies:** .NET runtime included (required for game server anyway)

**Migration Path (if needed):**

If multi-server fleet becomes requirement (Phase 3/Vision):

1. Extract game server to separate container
2. Add inter-container networking (docker network)
3. Update API to manage remote game server (SSH/process API)
4. Keep single-container option for simple deployments

**Base Image Decision:**

`mcr.microsoft.com/dotnet/runtime:8.0.22-noble-amd64`

**Why This Base Image:**

- Ubuntu 24.04 Noble LTS (stable, well-supported)
- Python 3.12 available via apt (matches Python 3.12 requirement)
- .NET 8.0 runtime included (required for VintageStory server)
- Single base image simplifies maintenance
- Well-maintained by Microsoft

**Alternatives Rejected:**

- `python:3.13-slim`: Would need separate .NET installation anyway
- `ubuntu:noble`: Would need to install both Python and .NET
- Custom base: More maintenance burden

### Container Volume Strategy

**Single Volume Mount:** `/data`

All persistent data lives under one mount point for simplified management.

```
/data (single mounted volume)
├── server/                   # VintageStory server installation
│   ├── VintagestoryServer    # Server binary
│   ├── Mods/ → ../mods/      # Symlink to persist mods across updates
│   └── ...                   # Other server files
├── mods/                     # Mod files (persisted separately)
│   ├── smithingplus.zip
│   └── ...
├── config/                   # Game server configuration
│   ├── serverconfig.json
│   └── ...
├── state/                    # API state persistence
│   └── state.json
├── logs/                     # Application and game logs
│   ├── api.log
│   └── server.log
├── backups/                  # Server backups (future)
└── static/                   # Any static files needed
```

**Post-Install Symlink Strategy:**
After server installation, create symlink to preserve mods across server updates:

```bash
ln -s /data/mods /data/server/Mods
```

### Docker Compose Configuration

**Production (`docker-compose.yaml`):**
For community users pulling from container registry.

```yaml
services:
  manager:
    image: ghcr.io/craquehouse/vintagestory-server:latest
    container_name: vintagestory-manager
    ports:
      - "8080:8080"      # Web UI + API
      - "42420:42420"    # Game server (for future connectivity if needed)
    volumes:
      - ./data:/data
    environment:
      - VS_API_KEY_ADMIN=${VS_API_KEY_ADMIN}
      - VS_API_KEY_MONITOR=${VS_API_KEY_MONITOR:-}
      - VS_GAME_VERSION=${VS_GAME_VERSION:-stable}
      - VS_DEBUG=${VS_DEBUG:-false}
      - VS_DATA_DIR=${VS_DATA_DIR:-/data}
      - UV_LINK_MODE=copy
    env_file:
      - path: .env
        required: false
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/healthz')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

**Development (`docker-compose.dev.yaml`):**
For local development with live builds.

```yaml
services:
  manager:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: vintagestory-manager-dev
    ports:
      - "8080:8080"      # Web UI + API
      - "42420:42420"    # Game server (for future connectivity if needed)
    volumes:
      - ./data:/data
    environment:
      - VS_API_KEY_ADMIN=${VS_API_KEY_ADMIN:-dev-admin-key}
      - VS_API_KEY_MONITOR=${VS_API_KEY_MONITOR:-}
      - VS_GAME_VERSION=${VS_GAME_VERSION:-stable}
      - VS_DEBUG=true
      - VS_DATA_DIR=${VS_DATA_DIR:-/data}
      - UV_LINK_MODE=copy
    env_file:
      - path: .env
        required: false
    restart: unless-stopped
```

### Architectural Boundaries

**API Boundaries:**

| Boundary              | Internal          | External              |
| --------------------- | ----------------- | --------------------- |
| `/api/v1alpha1/*`     | All API routes    | Clients (Web UI, CLI) |
| `/ws/console`         | Console WebSocket | Admin clients only    |
| `/*` (static)         | Vite build output | Web browsers          |
| `/healthz`, `/readyz` | Health endpoints  | Load balancers, K8s   |

**Service Boundaries (Backend):**

```
┌─────────────────────────────────────────────────────────────┐
│                        Routers Layer                         │
│  (HTTP interface, request validation, response formatting)   │
│  server.py │ mods.py │ config.py │ health.py                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       Services Layer                         │
│  (Business logic, orchestration, external API calls)         │
│  ServerLifecycle │ ModService │ ConsoleBuffer │ StateManager │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        Models Layer                          │
│  (Data structures, validation, serialization)                │
│  Pydantic models for State, Mods, Responses, Errors          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      External Interfaces                     │
│  File System │ VintageStory API │ Docker API │ Game Process  │
└─────────────────────────────────────────────────────────────┘
```

**Component Boundaries (Frontend):**

```
┌─────────────────────────────────────────────────────────────┐
│                      Pages/Features                          │
│  Dashboard │ ModList │ ConfigEditor │ Terminal               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       Components                             │
│  Layout │ ServerStatusBadge │ ModCard │ ui/ (shadcn)         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    State & Data Layer                        │
│  TanStack Query (server) │ Context (UI) │ Hooks              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       API Client                             │
│  client.ts (fetch, transform) │ WebSocket connection         │
└─────────────────────────────────────────────────────────────┘
```

**Data Boundaries:**

| Data Type      | Storage                  | Access Pattern               |
| -------------- | ------------------------ | ---------------------------- |
| Server state   | `/data/state/state.json` | In-memory + atomic file sync |
| Mod files      | `/data/mods/`            | File system operations       |
| Game config    | `/data/config/`          | Read/write JSON files        |
| Console buffer | In-memory ring buffer    | WebSocket streaming          |
| Logs           | `/data/logs/`            | Append-only files            |

### Requirements to Structure Mapping

**Epic/Feature → Directory Mapping:**

| Feature Area     | Backend Location                          | Frontend Location         |
| ---------------- | ----------------------------------------- | ------------------------- |
| Server Lifecycle | `routers/server.py`, `services/server.py` | `features/dashboard/`     |
| Mod Management   | `routers/mods.py`, `services/mods.py`     | `features/mods/`          |
| Config Editing   | `routers/config.py`                       | `features/config/`        |
| Console Access   | `services/console.py`, WebSocket handler  | `features/terminal/`      |
| Authentication   | `middleware/auth.py`                      | `api/client.ts` (headers) |
| Health Checks    | `routers/health.py`                       | N/A (infrastructure)      |

**Cross-Cutting Concerns:**

| Concern             | Backend Files                          | Frontend Files                |
| ------------------- | -------------------------------------- | ----------------------------- |
| State Management    | `services/state.py`, `models/state.py` | `hooks/use-*.ts`, `contexts/` |
| Error Handling      | `models/errors.py`, exception handlers | Error boundaries, toast       |
| Logging             | `structlog` configuration              | Browser console               |
| API Response Format | `models/responses.py`                  | `api/types.ts`                |

### Integration Points

**Internal Communication:**

```
┌─────────────┐     HTTP/JSON      ┌─────────────┐
│   Web UI    │ ◀───────────────▶ │   FastAPI   │
└─────────────┘                    └─────────────┘
       │                                  │
       │ WebSocket                        │ Subprocess
       ▼                                  ▼
┌─────────────┐                    ┌─────────────┐
│  Console    │ ◀─────────────────│ Game Server │
│  (xterm.js) │   stdout/stdin    │  Process    │
└─────────────┘                    └─────────────┘
```

**External Integrations:**

| Integration               | Protocol       | Error Handling                    |
| ------------------------- | -------------- | --------------------------------- |
| VintageStory Mod API      | HTTPS (httpx)  | Timeout, cache, graceful fallback |
| GitHub Container Registry | Docker pull    | Version tags, SHA pinning         |
| Game Server Binary        | HTTPS download | Checksum verification             |

**Data Flow:**

```
User Action → API Request → Service Layer → State Update → File Sync
                                    │
                                    ▼
                           External API (if needed)
                                    │
                                    ▼
                              API Response
                                    │
                                    ▼
                    TanStack Query Cache Update
                                    │
                                    ▼
                            UI Re-render
```

### Development Workflow Integration

**Local Development:**

```bash
# Terminal 1: Backend (hot reload)
cd api && uv run fastapi dev

# Terminal 2: Frontend (HMR)
cd web && bun run dev

# Or use docker-compose.dev.yaml for full stack
docker compose -f docker-compose.dev.yaml up --build
```

**Build Process:**

```dockerfile
# Multi-stage Dockerfile
FROM node:22-slim AS web-build
# Install bun@1.3.5, build frontend → /app/dist

FROM mcr.microsoft.com/dotnet/runtime:8.0.22-noble-amd64 AS final
# Ubuntu 24.04 Noble with:
# - Python 3.12 (native to apt)
# - .NET 8.0 runtime (for VintageStory game server)
# Install uv, copy web build, install API deps, run uvicorn
```

**CI/CD Pipeline:**

```yaml
# .github/workflows/ci.yaml
# 1. Lint (ruff, eslint)
# 2. Test (pytest, vitest)
# 3. Build Docker image
# 4. Push to ghcr.io/craquehouse/vintagestory-server
```

### File Organization Patterns

**Configuration Files (Root):**

| File                      | Purpose                 |
| ------------------------- | ----------------------- |
| `.mise.toml`              | Tool version management |
| `docker-compose.yaml`     | Production deployment   |
| `docker-compose.dev.yaml` | Local development       |
| `Dockerfile`              | Container build         |
| `.env.example`            | Environment template    |
| `.gitignore`              | Git exclusions          |

**Environment Variables:**

| Variable             | Required | Description                    |
| -------------------- | -------- | ------------------------------ |
| `VS_API_KEY_ADMIN`   | Yes      | Admin API key                  |
| `VS_API_KEY_MONITOR` | No       | Read-only API key              |
| `VS_GAME_VERSION`    | No       | Game version (default: stable) |
| `VS_DEBUG`           | No       | Enable debug logging           |

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**
All technology choices work together without conflicts:

- Backend: Python 3.12+ + FastAPI + uv + httpx + structlog - fully compatible async stack
- Frontend: React 19.2 + Vite 7 + Bun + TypeScript + TanStack Query v5 - security-patched, modern stack
- Infrastructure: Single container with single volume mount - simplified deployment model
- Development: mise for consistent tool versions across environments

**Pattern Consistency:**

- JSON field naming boundary (snake_case API ↔ camelCase frontend) is well-defined
- Response envelope pattern is consistent across all endpoints
- Error codes are centralized and documented
- State management boundaries prevent React Context/TanStack Query confusion

**Structure Alignment:**

- Project structure directly supports all architectural patterns
- Integration points are properly mapped in directory structure
- Component boundaries align with feature areas

### Requirements Coverage Validation ✅

**Functional Requirements Coverage:**

| Category               | FRs     | Architectural Support                      |
| ---------------------- | ------- | ------------------------------------------ |
| Server Lifecycle       | FR1-5   | `routers/server.py` + `services/server.py` |
| Console Access         | FR6-9   | `services/console.py` + WebSocket handler  |
| Mod Management         | FR10-17 | `routers/mods.py` + `services/mods.py`     |
| Game Configuration     | FR18-22 | `routers/config.py`                        |
| Settings Management    | FR23-26 | `services/state.py` + config endpoints     |
| Health & Observability | FR27-30 | `routers/health.py`                        |
| Authentication         | FR31-37 | `middleware/auth.py`                       |
| Deployment             | FR38-39 | `docker-compose.yaml` + env vars           |

**Non-Functional Requirements Coverage:**

| NFR      | Requirement            | Architectural Support                 |
| -------- | ---------------------- | ------------------------------------- |
| NFR1     | <1s console latency    | WebSocket streaming, in-memory buffer |
| NFR2     | Real-time streaming    | Starlette WebSocket                   |
| NFR3     | <500ms API response    | In-memory state, async operations     |
| NFR4     | Secure key storage     | Environment variables                 |
| NFR5     | TLS termination        | Out of scope (reverse proxy)          |
| NFR6     | No console persistence | In-memory ring buffer only            |
| NFR7     | Auth failure logging   | structlog with security context       |
| NFR8     | API survives crashes   | Decoupled process management          |
| NFR9     | Crash recovery         | StateManager with file sync           |
| NFR10    | Auto-reconnect         | Exponential backoff pattern           |
| NFR11-13 | Graceful API failures  | httpx timeout + cache                 |
| NFR14-16 | Structured logs        | structlog JSON + context              |

### Implementation Readiness Validation ✅

**Decision Completeness:**

- ✅ All critical technologies have specific versions
- ✅ Implementation patterns include code examples
- ✅ Consistency rules are enforceable via Ruff and ESLint

**Structure Completeness:**

- ✅ Complete directory tree with all files defined
- ✅ Feature-to-directory mapping documented
- ✅ Integration points clearly specified

**Pattern Completeness:**

- ✅ All naming conventions comprehensive
- ✅ Error handling patterns with codes defined
- ✅ WebSocket reconnection pattern specified
- ✅ Atomic write pattern prevents data corruption

### Gap Analysis Results

**Critical Gaps:** None identified

**Important Gaps:** None identified

**Minor Refinements (Optional):**

1. Console ring buffer size can be made configurable (default: 10,000 lines)
2. Health endpoint can include game server version in response body
3. API rate limiting deferred to post-MVP per PRD

### Architecture Completeness Checklist

**✅ Requirements Analysis**

- [x] Project context thoroughly analyzed (37 FRs, 16 NFRs)
- [x] Scale and complexity assessed (Low-Medium)
- [x] Technical constraints identified (no database, TLS via proxy)
- [x] Cross-cutting concerns mapped (auth, error handling, state, real-time)

**✅ Architectural Decisions**

- [x] Critical decisions documented with versions
- [x] Technology stack fully specified
- [x] Integration patterns defined (API boundary, WebSocket)
- [x] Performance considerations addressed (in-memory, atomic writes)

**✅ Implementation Patterns**

- [x] Naming conventions established (8 categories)
- [x] Structure patterns defined (backend/frontend layouts)
- [x] Communication patterns specified (REST, WebSocket, TanStack Query)
- [x] Process patterns documented (error handling, loading states)

**✅ Project Structure**

- [x] Complete directory structure defined
- [x] Component boundaries established
- [x] Integration points mapped
- [x] Requirements to structure mapping complete
- [x] Docker volume strategy finalized (single /data mount)
- [x] Container registry specified (ghcr.io/craquehouse/vintagestory-server)

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** High

**Key Strengths:**

- Clean separation between API and frontend with well-defined boundary
- Single container deployment simplifies operations
- Atomic file writes prevent state corruption
- WebSocket reconnection pattern ensures reliability
- Comprehensive naming conventions prevent AI agent conflicts
- All 39 functional and 16 non-functional requirements have architectural support

**Areas for Future Enhancement:**

- Prometheus metrics endpoint (post-MVP per PRD)
- Backup management endpoints (Phase 2)
- Multi-server fleet patterns (Phase 3/Vision)

### Implementation Handoff

**AI Agent Guidelines:**

- Follow all architectural decisions exactly as documented
- Use implementation patterns consistently across all components
- Respect project structure and boundaries
- Refer to this document for all architectural questions
- Use atomic writes for all state persistence
- Transform JSON keys at the API client boundary only
- Write tests alongside implementation, not as a separate phase

### Architecture Specification Guidelines

_Added after Epic 1 retrospective (2025-12-27)_

When creating or updating architecture documents, calibrate specificity appropriately:

**Be Explicit About:**

- External runtime dependencies (e.g., "VintageStory requires .NET 8 runtime")
- Infrastructure constraints that affect technology choices
- Container base images and why they were chosen
- Integration points with third-party systems

**Use Ranges/Minimums For:**

- Language versions: `Python >= 3.12` not `Python 3.13`
- Framework versions unless specific features require exact version
- Dependencies that follow semver

**Always Document:**

- The _rationale_ behind decisions, not just the decision itself
- Tradeoffs considered and why alternatives were rejected
- Migration paths if the decision needs revisiting

**Why This Matters:**
During Epic 1, implementation discovered that the .NET base image ships Python 3.12, not 3.13. Because the architecture had over-specified Python version, it caused unnecessary friction. Conversely, under-specified container strategy led to implementation-time decisions that should have been made earlier.

**First Implementation Priority:**

```bash
# 1. Initialize development environment
mise trust && mise install

# 2. Scaffold backend (api/)
mkdir api && cd api
uv init --name vintagestory-api --python 3.12
uv add "fastapi[standard]" httpx pydantic-settings structlog
uv add --dev pytest pytest-asyncio ruff respx

# 3. Scaffold frontend (web/)
cd .. && bun create vite web -- --template react-ts
cd web && bun add react@19.2 react-dom@19.2
bun add -D tailwindcss @tailwindcss/vite
bunx shadcn@latest init
```

## Architecture Completion Summary

### Workflow Completion

**Architecture Decision Workflow:** COMPLETED ✅
**Total Steps Completed:** 8
**Date Completed:** 2025-12-26
**Document Location:** _bmad-output/planning-artifacts/architecture.md

### Final Architecture Deliverables

**Complete Architecture Document**

- All architectural decisions documented with specific versions
- Implementation patterns ensuring AI agent consistency
- Complete project structure with all files and directories
- Requirements to architecture mapping
- Validation confirming coherence and completeness

**Implementation Ready Foundation**

- 15+ architectural decisions made
- 8 implementation pattern categories defined
- 6 architectural component areas specified
- 39 functional + 16 non-functional requirements fully supported

**AI Agent Implementation Guide**

- Technology stack with verified versions
- Consistency rules that prevent implementation conflicts
- Project structure with clear boundaries
- Integration patterns and communication standards

### Implementation Handoff

**For AI Agents:**
This architecture document is your complete guide for implementing vintagestory-server. Follow all decisions, patterns, and structures exactly as documented.

**Development Sequence:**

1. Initialize project using documented starter template (mise, uv, bun)
2. Set up development environment per architecture
3. Implement core architectural foundations (state management, auth middleware)
4. Build features following established patterns
5. Maintain consistency with documented rules

### Quality Assurance Checklist

**✅ Architecture Coherence**

- [x] All decisions work together without conflicts
- [x] Technology choices are compatible
- [x] Patterns support the architectural decisions
- [x] Structure aligns with all choices

**✅ Requirements Coverage**

- [x] All functional requirements are supported
- [x] All non-functional requirements are addressed
- [x] Cross-cutting concerns are handled
- [x] Integration points are defined

**✅ Implementation Readiness**

- [x] Decisions are specific and actionable
- [x] Patterns prevent agent conflicts
- [x] Structure is complete and unambiguous
- [x] Examples are provided for clarity

### Project Success Factors

**Clear Decision Framework:**
Every technology choice was made collaboratively with clear rationale, ensuring all stakeholders understand the architectural direction.

**Container Strategy Decision (2025-12-26):**
During Story 1.4 implementation, the single container pattern (API + game server in same container) was chosen over the two-container alternative documented in initial architecture. This decision balances deployment simplicity with MVP requirements. Full rationale and tradeoff analysis documented in "Container Strategy Decision" section.

**Consistency Guarantee:**
Implementation patterns and rules ensure that multiple AI agents will produce compatible, consistent code that works together seamlessly.

**Complete Coverage:**
All project requirements are architecturally supported, with clear mapping from business needs to technical implementation.

**Solid Foundation:**
The chosen starter template and architectural patterns provide a production-ready foundation following current best practices.

---

**Architecture Status:** READY FOR IMPLEMENTATION ✅

**Next Phase:** Begin implementation using the architectural decisions and patterns documented herein.

**Document Maintenance:** Update this architecture when major technical decisions are made during implementation.

---

## Architecture Deviations & Evolutions

_Added during Epic 5 preparation (2025-12-28)_

This section documents how the actual implementation has evolved from the original architecture specification. These are **intentional evolutions**, not bugs.

### Backend Structure Changes

**Routers (evolved):**

| Original Spec                                    | Actual Implementation                                             | Reason                                                                                       |
| ------------------------------------------------ | ----------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `server.py`, `mods.py`, `config.py`, `health.py` | `server.py`, `health.py`, `console.py`, `auth.py`, `test_rbac.py` | Console became its own router (WebSocket complexity). Auth split out for security isolation. |

**Models (evolved):**

| Original Spec                                      | Actual Implementation                                  | Reason                                                                                                |
| -------------------------------------------------- | ------------------------------------------------------ | ----------------------------------------------------------------------------------------------------- |
| `state.py`, `mods.py`, `responses.py`, `errors.py` | `console.py`, `server.py`, `responses.py`, `errors.py` | Component-specific models (`console.py`, `server.py`) provide better cohesion than generic `state.py` |

**Services (current):**

| Service      | Status         | Notes                                               |
| ------------ | -------------- | --------------------------------------------------- |
| `server.py`  | ✅ Implemented | Handles lifecycle, installation, version management |
| `console.py` | ✅ Implemented | WebSocket streaming, console buffer                 |
| `state.py`   | ⏳ Future       | Will be added when needed for shared state patterns |
| `mods.py`    | ⏳ Epic 5       | Mod management service (Stories 5.1-5.6)            |

### Frontend API Client (enhanced)

The API client layer has been enhanced beyond original specification:

```
web/src/api/
├── client.ts           # Base HTTP client with transforms
├── client.test.ts      # Comprehensive tests
├── error-handler.ts    # Centralized error handling
├── errors.ts           # Error types and utilities
├── query-client.ts     # TanStack Query configuration
├── query-keys.ts       # Query key factory
├── server.ts           # Server API functions
├── types.ts            # API types
└── hooks/              # API-specific hooks
```

**Key enhancement:** Query keys moved to dedicated `query-keys.ts` for consistency and easy maintenance.

### Middleware Layer (added)

Middleware is now a first-class concept with dedicated directory:

```
middleware/
├── auth.py             # API key extraction and validation
└── permissions.py      # Role-based access control
```

This split allows clear separation between authentication (who are you?) and authorization (what can you do?).

---

## Epic 5: Mod Management Architecture

_Added during Epic 5 preparation (2025-12-28)_

This section defines architecture patterns specific to Epic 5 (Mod Management).

### External API Integration Pattern

**VintageStory Mod API Client:**

```python
# api/src/vintagestory_api/services/mod_api.py
import httpx
from typing import Optional
from vintagestory_api.config import get_settings

class ModApiClient:
    """Client for VintageStory mod database API."""

    BASE_URL = "https://mods.vintagestory.at/api"
    DOWNLOAD_URL = "https://mods.vintagestory.at/download"
    DEFAULT_TIMEOUT = 30.0

    def __init__(self, cache: Optional["ModCache"] = None):
        self.cache = cache
        self._client = httpx.AsyncClient(
            timeout=self.DEFAULT_TIMEOUT,
            follow_redirects=True
        )

    async def get_mod(self, slug: str) -> Optional[dict]:
        """Get mod details by slug. Returns None if not found."""
        # Check cache first
        if self.cache:
            cached = await self.cache.get_mod(slug)
            if cached:
                return cached

        try:
            response = await self._client.get(f"{self.BASE_URL}/mod/{slug}")
            data = response.json()

            # Note: Status is STRING, not int
            if data.get("statuscode") == "200":
                mod = data["mod"]
                if self.cache:
                    await self.cache.set_mod(slug, mod)
                return mod
            return None
        except httpx.HTTPError:
            # Graceful degradation - return cached if available
            if self.cache:
                return await self.cache.get_mod(slug, stale_ok=True)
            return None

    async def download_file(self, fileid: int, dest_path: Path) -> bool:
        """Download mod file to destination. Returns success status."""
        try:
            async with self._client.stream(
                "GET",
                f"{self.DOWNLOAD_URL}?fileid={fileid}"
            ) as response:
                response.raise_for_status()
                with open(dest_path, "wb") as f:
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)
            return True
        except httpx.HTTPError:
            return False
```

**Key patterns:**
- Async-first with `httpx.AsyncClient`
- Cache integration at client level
- Graceful degradation on API failures
- Status codes are strings (VintageStory API quirk)
- Follow redirects for download CDN

### Mod Service Boundaries

```
ModService
├── lookup(slug) → ModInfo
│   ├── Check local state for cached or installed mod
│   ├── Query API (via ModApiClient) for details
│   └── Return combined local + remote info
│
├── install(slug, version?) → InstallResult
│   ├── Lookup mod details
│   ├── Select appropriate release (version or latest compatible)
│   ├── Download file to /data/cache/mods/
│   ├── Link mod into /data/serverdata/mods
│   ├── Update mod state
│   └── Set pending_restart flag
│
├── enable(slug) → Result
│   ├── Verify mod exists
│   ├── Update mod state to enabled (softlink)
│   └── Set pending_restart flag
│
├── disable(slug) → Result
│   ├── Verify mod exists
│   ├── Update mod state to disabled (unlink)
│   └── Set pending_restart flag
│
├── remove(slug) → Result
│   ├── disable mod file (unlink)
│   ├── Delete mod file from cache
│   ├── Remove from mod state
│   └── Set pending_restart flag
│
├── update(slug) → Result
│   ├── disable outdated mod file (unlink)
│   ├── Remove from mod state
│   ├── Install current version
│   └── Set pending_restart flag
│
└── list() → List[ModInfo]
    ├── Get local mod state
    ├── Enrich with API data (if available)
    └── Return combined list
```

### Mod State Model

```python
# api/src/vintagestory_api/models/mods.py
from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime

class ModState(BaseModel):
    """State of an installed mod."""
    slug: str
    version: str
    filename: str
    enabled: bool = True
    installed_at: datetime

class ModInfo(BaseModel):
    """Combined local + remote mod information."""
    slug: str
    name: str
    author: str
    description: Optional[str] = None

    # Local state (if installed)
    installed: bool = False
    installed_version: Optional[str] = None
    enabled: Optional[bool] = None

    # Remote info (if available)
    latest_version: Optional[str] = None
    update_available: bool = False
    compatible_versions: list[str] = []
    downloads: Optional[int] = None

class CompatibilityStatus(Literal["compatible", "not_verified", "incompatible"]):
    """Mod compatibility with current game version."""
    pass
```

### Compatibility Check Logic

```python
def check_compatibility(
    releases: list[dict],
    game_version: str
) -> tuple[CompatibilityStatus, Optional[dict]]:
    """
    Check mod compatibility with game version.

    Returns:
        Tuple of (status, matching_release)
        - "compatible": Exact version match in release tags
        - "not_verified": Same major.minor version
        - "incompatible": No matching version
    """
    # Exact match
    for release in releases:
        if game_version in release.get("tags", []):
            return ("compatible", release)

    # Major.minor match (e.g., 1.21.x)
    major_minor = ".".join(game_version.split(".")[:2])
    for release in releases:
        if any(tag.startswith(major_minor) for tag in release.get("tags", [])):
            return ("not_verified", release)

    # No match - return latest anyway
    return ("incompatible", releases[0] if releases else None)
```

### Caching Architecture

**Two-tier caching strategy:**

1. **Artifact Cache** (file-based, permanent)
   - Server tarballs: `/data/cache/servers/`
   - Mod files: `/data/cache/mods/`

2. **API Response Cache** (TTL-based, ephemeral)
   - Mod details: 1 hour TTL
   - Game versions: 24 hour TTL
   - Mod list: 15 minute TTL

```
/data/cache/
├── servers/                    # Server tarballs (permanent)
│   └── vs_server_1.21.6.tar.gz
├── mods/                       # Downloaded mod files (permanent)
│   └── smithingplus_1.8.3.zip
└── api/                        # Cached API responses (TTL-based)
    ├── mod_smithingplus.json   # Individual mod lookup (1h TTL)
    ├── modlist.json            # All mods (15m TTL)
    └── gameversions.json       # Game versions (24h TTL)
```

**Cache implementation pattern:**

```python
# api/src/vintagestory_api/services/cache.py
from pathlib import Path
from datetime import datetime, timedelta
import json

class ModCache:
    """TTL-based cache for mod API responses."""

    TTL_MOD = timedelta(hours=1)
    TTL_VERSIONS = timedelta(hours=24)
    TTL_MODLIST = timedelta(minutes=15)

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir / "api"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    async def get_mod(self, slug: str, stale_ok: bool = False) -> Optional[dict]:
        """Get cached mod data. stale_ok allows expired entries."""
        path = self.cache_dir / f"mod_{slug}.json"
        if not path.exists():
            return None

        data = json.loads(path.read_text())
        expires = datetime.fromisoformat(data["expires"])

        if datetime.utcnow() > expires and not stale_ok:
            return None

        return data["mod"]

    async def set_mod(self, slug: str, mod: dict) -> None:
        """Cache mod data with TTL."""
        path = self.cache_dir / f"mod_{slug}.json"
        expires = datetime.utcnow() + self.TTL_MOD

        data = {
            "mod": mod,
            "expires": expires.isoformat(),
            "cached_at": datetime.utcnow().isoformat()
        }

        # Atomic write
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(data))
        temp.rename(path)
```

### Pending Restart Pattern

**State tracking:**

```python
# In StateManager
class AppState(BaseModel):
    pending_restart: bool = False
    pending_changes: list[str] = []  # Description of changes

    def require_restart(self, reason: str) -> None:
        """Mark that a restart is needed."""
        self.pending_restart = True
        self.pending_changes.append(reason)

    def clear_restart(self) -> None:
        """Clear restart requirement (after successful restart)."""
        self.pending_restart = False
        self.pending_changes = []
```

**API response extension:**

```python
# Success responses include pending_restart status
{
    "status": "ok",
    "data": {...},
    "pending_restart": true  # Added when pending_restart is true
}
```

**Frontend banner component:**

```typescript
// web/src/components/PendingRestartBanner.tsx
function PendingRestartBanner() {
  const { data: status } = useServerStatus();

  if (!status?.pending_restart) return null;

  return (
    <div className="bg-warning p-2 flex justify-between items-center">
      <span>
        ⟳ Restart required · {status.pending_changes?.length || 0} pending changes
      </span>
      <Button onClick={handleRestart}>Restart Now</Button>
    </div>
  );
}
```

**Triggering events:**
- Mod enabled/disabled
- Mod installed/removed
- Config file saved (future)
- Server settings changed (future)

**Clear conditions:**
- Server successfully restarted
- Manual acknowledgment without restart

### Error Handling for External APIs

**Error codes for mod operations:**

```python
# api/src/vintagestory_api/models/errors.py
class ErrorCode:
    # Existing codes...

    # Epic 5 additions
    MOD_NOT_FOUND = "MOD_NOT_FOUND"
    MOD_ALREADY_INSTALLED = "MOD_ALREADY_INSTALLED"
    MOD_NOT_INSTALLED = "MOD_NOT_INSTALLED"
    MOD_INCOMPATIBLE = "MOD_INCOMPATIBLE"
    MOD_DOWNLOAD_FAILED = "MOD_DOWNLOAD_FAILED"
    MOD_API_UNAVAILABLE = "MOD_API_UNAVAILABLE"
    MOD_API_TIMEOUT = "MOD_API_TIMEOUT"
```

**Graceful degradation pattern:**

```python
async def get_mod_info(slug: str) -> ModInfo:
    """Get mod info, gracefully handling API failures."""

    # Always get local state
    local = state_manager.get_mod(slug)

    try:
        remote = await mod_api.get_mod(slug)
    except httpx.TimeoutException:
        # Log but don't fail
        logger.warning("mod_api_timeout", slug=slug)
        remote = None
    except httpx.HTTPError as e:
        logger.warning("mod_api_error", slug=slug, error=str(e))
        remote = None

    # Return combined info
    return ModInfo(
        slug=slug,
        installed=local is not None,
        installed_version=local.version if local else None,
        latest_version=remote["releases"][0]["modversion"] if remote else None,
        # ... etc
    )
```

### Testing Patterns for External APIs

**Use `respx` for httpx mocking:**

```python
# tests/test_mod_api.py
import respx
from httpx import Response

@respx.mock
async def test_get_mod_success():
    respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
        return_value=Response(
            200,
            json={
                "statuscode": "200",
                "mod": {
                    "name": "Smithing Plus",
                    "urlalias": "smithingplus",
                    "releases": [{"modversion": "1.8.3", "tags": ["1.21.3"]}]
                }
            }
        )
    )

    client = ModApiClient()
    mod = await client.get_mod("smithingplus")

    assert mod is not None
    assert mod["name"] == "Smithing Plus"

@respx.mock
async def test_get_mod_api_unavailable():
    respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
        side_effect=httpx.TimeoutException("Connection timeout")
    )

    client = ModApiClient()
    mod = await client.get_mod("smithingplus")

    assert mod is None  # Graceful failure

@respx.mock
async def test_get_mod_with_cache_fallback():
    # First request succeeds and populates cache
    respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
        return_value=Response(200, json={"statuscode": "200", "mod": {...}})
    )

    cache = ModCache(tmp_path)
    client = ModApiClient(cache=cache)

    # First call - populates cache
    mod1 = await client.get_mod("smithingplus")

    # Simulate API failure
    respx.reset()
    respx.get("https://mods.vintagestory.at/api/mod/smithingplus").mock(
        side_effect=httpx.HTTPError("API unavailable")
    )

    # Second call - should return stale cache
    mod2 = await client.get_mod("smithingplus")
    assert mod2 is not None  # From stale cache
```

---

## Epic 6: Game Configuration Management Architecture

_Added during Epic 5 retrospective (2025-12-30)_

This section defines architecture patterns specific to Epic 6 (Game Configuration Management).

### Architectural Pivot: Console Commands vs. File Editing

**Research Finding (Epic 5 Retrospective):**

VintageStory server console commands can modify most server settings, and the game server handles JSON persistence automatically. This changes our approach from "file editing" to "command-based configuration."

**Reference Implementation:**
[DarkMatterProductions generate-config.py](https://raw.githubusercontent.com/DarkMatterProductions/vintagestory/refs/heads/main/generate-config.py) demonstrates a data model with ~20 configurable settings.

**Original Approach (Deferred):**
```
User → Web UI → JSON Editor → PUT /config/files/{name} → File Write → Restart
```

**New Approach:**
```
User → Web UI → Setting Form → POST /config/settings/{key} → API decides method → Game Server
                                                              ↓
                                              (Console command if running, file update otherwise)
```

**Key Boundary:** The frontend never constructs or sees console commands. It simply calls `POST /config/settings/{key}` with a value. The API server internally decides whether to use a console command or file update based on server state.

### Setting Categories

**1. Console-Commandable Settings (Live Update)**

Settings the API server can update via console commands while game server is running.

**⚠️ Implementation Detail:** The console command syntax below is internal to the API server. The frontend only sees setting keys and values. This is an incomplete list.

| Setting           | API Server Internal Command                | Effect    |
| ----------------- | ------------------------------------------ | --------- |
| ServerName        | `/serverconfig Name "value"`               | Immediate |
| ServerDescription | `/serverconfig Description "value"  `      | Immediate |
| WelcomeMessage    | `/serverconfig WelcomeMessage "value"`     | Immediate |
| MaxClients        | `/serverconfig MaxClients N`               | Immediate |
| Password          | `/serverconfig Password "value"`           | Immediate |
| AllowPvP          | `/serverconfig AllowPvP true/false`        | Immediate |
| OnlyWhitelisted   | `/serverconfig OnlyWhitelisted true/false` | Immediate |

**2. Restart-Required Settings**

Settings that require server restart to take effect:

| Setting           | Location          | Restart Required     |
| ----------------- | ----------------- | -------------------- |
| Port              | serverconfig.json | Yes                  |
| World seed        | serverconfig.json | Yes (new world only) |
| Game mode changes | serverconfig.json | Sometimes            |

**3. Environment Variable Managed Settings**

Settings controlled by container environment variables (read-only in UI):

| Setting        | Env Var           | Behavior                                       |
| -------------- | ----------------- | ---------------------------------------------- |
| Game version   | `VS_GAME_VERSION` | Display only, warn if different from installed |
| Data directory | `VS_DATA_DIR`     | Display only                                   |
| Debug mode     | `VS_DEBUG`        | Display only                                   |

### Initial Configuration Generation (ConfigInitService)

On first server start, if no `serverconfig.json` exists, the API generates one from:
1. A reference template (`serverconfig-template.json`)
2. VS_CFG_* environment variable overrides

**Pattern:** Inspired by [DarkMatterProductions](https://github.com/DarkMatterProductions/vintagestory) but adapted for our architecture.

```python
# api/src/vintagestory_api/services/config_init.py
import os
import json
from pathlib import Path
from typing import Any

class ConfigInitService:
    """Handles initial serverconfig.json generation from template + env vars."""

    # Maps VS_CFG_* env vars to serverconfig.json keys
    ENV_VAR_MAP = {
        "VS_CFG_SERVER_NAME": "ServerName",
        "VS_CFG_SERVER_PORT": "Port",
        "VS_CFG_MAX_CLIENTS": "MaxClients",
        "VS_CFG_PASSWORD": "Password",
        "VS_CFG_ALLOW_PVP": "AllowPvP",
        "VS_CFG_ONLY_WHITELISTED": "OnlyWhitelisted",
        "VS_CFG_ADVERTISE_SERVER": "AdvertiseServer",
        # ... additional mappings
    }

    def __init__(self, data_dir: Path, template_path: Path):
        self.config_path = data_dir / "config" / "serverconfig.json"
        self.template_path = template_path

    def needs_initialization(self) -> bool:
        """Check if config needs to be created."""
        return not self.config_path.exists()

    def initialize_config(self) -> Path:
        """Generate serverconfig.json from template + VS_CFG_* overrides."""
        # Load template
        config = self._load_template()

        # Apply environment variable overrides
        overrides = self._collect_env_overrides()
        config = self._apply_overrides(config, overrides)

        # Write config (atomic)
        self._write_config(config)

        return self.config_path

    def _load_template(self) -> dict[str, Any]:
        """Load the reference template."""
        with open(self.template_path) as f:
            return json.load(f)

    def _collect_env_overrides(self) -> dict[str, Any]:
        """Collect VS_CFG_* environment variables."""
        overrides = {}
        for env_key, config_key in self.ENV_VAR_MAP.items():
            if env_key in os.environ:
                value = os.environ[env_key]
                overrides[config_key] = self._parse_value(value)
        return overrides

    def _parse_value(self, value: str) -> Any:
        """Convert string env var to appropriate type."""
        if value.lower() in ("true", "false"):
            return value.lower() == "true"
        try:
            return int(value)
        except ValueError:
            return value

    def _apply_overrides(self, config: dict, overrides: dict) -> dict:
        """Apply overrides to config, handling nested keys."""
        for key, value in overrides.items():
            config[key] = value
        return config

    def _write_config(self, config: dict) -> None:
        """Atomic write to config file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.config_path.with_suffix(".tmp")
        temp.write_text(json.dumps(config, indent=2))
        temp.rename(self.config_path)
```

**Integration with ServerService:**

```python
# In ServerService.start()
async def start(self):
    if self.config_init.needs_initialization():
        self.config_init.initialize_config()
        logger.info("config_initialized", source="template+env")
    # proceed with start...
```

**Reference Template:**

Ship `serverconfig-template.json` with sensible defaults. The template is JSON (not YAML) since:
- Target format is JSON
- No conversion step needed
- Pydantic natively handles JSON

**Backlog: State Enforcement**

Future enhancement (not MVP): `enforce_env_on_restart` setting would re-apply VS_CFG_* values on each server restart, ensuring env vars always win over manual changes.

### Configuration Service Pattern

```python
# api/src/vintagestory_api/services/config.py
from typing import Optional, Literal
from pydantic import BaseModel

class ServerSetting(BaseModel):
    """Definition of a server setting."""
    key: str
    value_type: Literal["string", "int", "bool"]
    console_command: Optional[str] = None  # None = restart required
    requires_restart: bool = False
    env_var_override: Optional[str] = None  # If set, controlled by env

class ConfigService:
    """Service for reading and modifying server configuration."""

    LIVE_SETTINGS = {
        "ServerName": ServerSetting(
            key="ServerName",
            value_type="string",
            console_command='/serverconfig Name "{value}"'
        ),
        "MaxClients": ServerSetting(
            key="MaxClients",
            value_type="int",
            console_command="/serverconfig MaxClients {value}"
        ),
        "AllowPvP": ServerSetting(
            key="AllowPvP",
            value_type="bool",
            console_command="/serverconfig AllowPvP {value}"
        ),
        # ... more settings
    }

    async def get_settings(self) -> dict:
        """Get current settings from serverconfig.json."""
        config = await self._read_serverconfig()
        return self._enrich_with_metadata(config)

    async def update_setting(self, key: str, value: str) -> UpdateResult:
        """Update a setting using appropriate method."""
        setting = self.LIVE_SETTINGS.get(key)

        if not setting:
            raise ValueError(f"Unknown setting: {key}")

        if setting.env_var_override:
            return UpdateResult(
                success=False,
                error="Setting is managed by environment variable"
            )

        if setting.console_command and self.server_is_running:
            # Use console command for live update
            cmd = setting.console_command.format(value=value)
            await self.console_service.send_command(cmd)
            return UpdateResult(success=True, requires_restart=False)
        else:
            # Fall back to file edit + restart flag
            await self._update_config_file(key, value)
            return UpdateResult(success=True, requires_restart=True)
```

### API Endpoints for Epic 6

**Configuration Domain Separation:**

| Endpoint | Domain | Description |
|----------|--------|-------------|
| `/api/v1alpha1/config/game` | Game Server | Settings stored in serverconfig.json, managed by VintageStory |
| `/api/v1alpha1/config/api` | API Server | Operational settings for the management API itself |

---

#### Game Configuration (`/config/game`)

**Read Game Settings:**

```
GET /api/v1alpha1/config/game
```

Returns current game server settings with metadata:

```json
{
  "status": "ok",
  "data": {
    "settings": [
      {
        "key": "ServerName",
        "value": "My Server",
        "type": "string",
        "live_update": true,
        "env_managed": false
      },
      {
        "key": "Port",
        "value": 42420,
        "type": "int",
        "live_update": false,
        "requires_restart": true
      },
      {
        "key": "MaxClients",
        "value": 16,
        "type": "int",
        "live_update": true,
        "env_managed": true,
        "env_var": "VS_CFG_MAX_CLIENTS"
      }
    ],
    "source_file": "serverconfig.json",
    "last_modified": "2025-12-30T10:00:00Z"
  }
}
```

**Update Game Setting:**

```
POST /api/v1alpha1/config/game/settings/{key}
```

Request:
```json
{
  "value": "New Server Name"
}
```

Response (live update):
```json
{
  "status": "ok",
  "data": {
    "key": "ServerName",
    "value": "New Server Name",
    "method": "console_command",
    "pending_restart": false
  }
}
```

Response (requires restart):
```json
{
  "status": "ok",
  "data": {
    "key": "Port",
    "value": 42421,
    "method": "file_update",
    "pending_restart": true
  }
}
```

Response (env managed, blocked):
```json
{
  "status": "error",
  "error": {
    "code": "SETTING_ENV_MANAGED",
    "message": "Setting 'MaxClients' is managed by environment variable VS_CFG_MAX_CLIENTS"
  }
}
```

---

#### API Configuration (`/config/api`)

**Read API Settings:**

```
GET /api/v1alpha1/config/api
```

Returns API server operational settings:

```json
{
  "status": "ok",
  "data": {
    "settings": {
      "auto_start_server": false,
      "block_env_managed_settings": true,
      "enforce_env_on_restart": false,
      "mod_list_refresh_interval": 3600,
      "server_versions_refresh_interval": 86400
    }
  }
}
```

**Update API Setting:**

```
POST /api/v1alpha1/config/api/settings/{key}
```

Request:
```json
{
  "value": true
}
```

Response:
```json
{
  "status": "ok",
  "data": {
    "key": "auto_start_server",
    "value": true
  }
}
```

**API Settings Reference:**

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `auto_start_server` | bool | false | Start game server automatically when API launches |
| `block_env_managed_settings` | bool | true | Reject UI changes to settings controlled by VS_CFG_* env vars |
| `enforce_env_on_restart` | bool | false | Re-apply VS_CFG_* values on each game server restart (backlog) |
| `mod_list_refresh_interval` | int | 3600 | Seconds between mod API cache refreshes |
| `server_versions_refresh_interval` | int | 86400 | Seconds between checking for new VS versions |

---

#### Raw Config Files (`/config/files`)

**Read Raw Config File (Monitor + Admin):**

```
GET /api/v1alpha1/config/files/{filename}
```

Returns raw JSON content (read-only view for troubleshooting).

### UI Architecture

**Navigation Structure (Revised):**

```
Dashboard | GameServer | Mods | Settings
              │                   │
              ├── Console         ├── API Settings
              └── Game Config     └── File Manager (stub)
```

**Key UX Decision:** Game Config shares the GameServer tab with Console, so users see console commands execute in real-time when changing settings.

---

#### GameServer Page (Responsive Layout)

```typescript
// web/src/features/gameserver/GameServerPage.tsx
function GameServerPage() {
  return (
    <div className="flex flex-col lg:flex-row gap-4 h-full">
      {/* Console: top on mobile, right on desktop */}
      <div className="lg:order-2 lg:w-1/2 min-h-[300px] lg:min-h-[600px]">
        <ConsoleView />
      </div>

      {/* Config: bottom on mobile, left on desktop */}
      <div className="lg:order-1 lg:w-1/2 overflow-y-auto">
        <GameConfigPanel />
      </div>
    </div>
  );
}
```

**Responsive Behavior:**

| Viewport | Layout |
|----------|--------|
| Mobile/Narrow (<1024px) | Console (top) → Config (bottom, scrollable) |
| Desktop/Wide (≥1024px) | Config (left) ↔ Console (right) |

---

#### Auto-Save Pattern

**Per-field auto-save** - each setting saves immediately on change:

```typescript
// web/src/features/config/SettingField.tsx
function SettingField({ setting }: { setting: GameSetting }) {
  const updateSetting = useUpdateGameSetting();
  const { toast } = useToast();

  const handleChange = async (value: string | boolean) => {
    try {
      const result = await updateSetting.mutateAsync({
        key: setting.key,
        value: String(value)
      });

      if (result.data.pending_restart) {
        // Triggers PendingRestartBanner (same pattern as mods)
      } else {
        toast({ title: "Setting updated", variant: "success" });
      }
    } catch (error) {
      toast({ title: "Failed to update setting", variant: "destructive" });
    }
  };

  // ... render
}
```

**Restart-Required Fields (Option B - Consistent with Mods):**
- Allowed even when server is running
- Changes written to file
- PendingRestartBanner appears (reuses existing component from mod management)
- User restarts when ready

**Partial Failure Handling:**
- Each field independent - no batching
- Error shown on specific field that failed
- Other fields unaffected

---

#### Game Config Panel

```typescript
// web/src/features/config/GameConfigPanel.tsx
function GameConfigPanel() {
  const { data: settings } = useGameSettings();

  return (
    <div className="space-y-6">
      <SettingGroup title="Server Identity">
        <SettingField setting={settings.ServerName} />
        <SettingField setting={settings.ServerDescription} />
        <SettingField setting={settings.WelcomeMessage} />
      </SettingGroup>

      <SettingGroup title="Player Limits">
        <SettingField setting={settings.MaxClients} />
        <SettingField setting={settings.OnlyWhitelisted} />
      </SettingGroup>

      <SettingGroup title="Gameplay">
        <SettingField setting={settings.AllowPvP} />
        <SettingField setting={settings.AllowCreativeMode} />
      </SettingGroup>

      <SettingGroup title="Network">
        <SettingField setting={settings.Port} />
      </SettingGroup>

      <SettingGroup title="Environment Managed" variant="muted">
        <ReadonlySetting setting={settings.VS_GAME_VERSION} />
      </SettingGroup>
    </div>
  );
}
```

---

#### Setting Field Component

```typescript
// web/src/features/config/SettingField.tsx
function SettingField({ setting }: { setting: GameSetting }) {
  const updateSetting = useUpdateGameSetting();

  return (
    <div className="flex items-center justify-between py-2">
      <div className="flex items-center gap-2">
        <Label>{setting.label}</Label>
        {setting.live_update && <Badge variant="outline">Live</Badge>}
        {setting.requires_restart && <Badge variant="warning">Restart</Badge>}
        {setting.env_managed && (
          <Badge variant="muted">Env: {setting.env_var}</Badge>
        )}
      </div>

      <div className="w-48">
        {setting.type === "bool" ? (
          <Switch
            checked={setting.value}
            onCheckedChange={(v) => updateSetting.mutate({ key: setting.key, value: v })}
            disabled={setting.env_managed}
          />
        ) : setting.type === "int" ? (
          <Input
            type="number"
            value={setting.value}
            onBlur={(e) => updateSetting.mutate({ key: setting.key, value: e.target.value })}
            disabled={setting.env_managed}
          />
        ) : (
          <Input
            value={setting.value}
            onBlur={(e) => updateSetting.mutate({ key: setting.key, value: e.target.value })}
            disabled={setting.env_managed}
          />
        )}
      </div>
    </div>
  );
}
```

---

#### Settings Page (API + File Manager)

```typescript
// web/src/features/settings/SettingsPage.tsx
function SettingsPage() {
  return (
    <Tabs defaultValue="api">
      <TabsList>
        <TabsTrigger value="api">API Settings</TabsTrigger>
        <TabsTrigger value="files">File Manager</TabsTrigger>
      </TabsList>

      <TabsContent value="api">
        <ApiSettingsPanel />
      </TabsContent>

      <TabsContent value="files">
        <FileManagerStub />
      </TabsContent>
    </Tabs>
  );
}

function FileManagerStub() {
  return (
    <div className="text-center py-12 text-muted-foreground">
      <p>File Manager coming in a future release.</p>
      <p className="text-sm">Read-only config file viewing will be available here.</p>
    </div>
  );
}
```

---

#### API Settings Panel

```typescript
// web/src/features/settings/ApiSettingsPanel.tsx
function ApiSettingsPanel() {
  const { data: settings } = useApiSettings();

  return (
    <div className="space-y-6">
      <SettingGroup title="Startup">
        <ApiSettingField setting={settings.auto_start_server} />
      </SettingGroup>

      <SettingGroup title="Environment Handling">
        <ApiSettingField setting={settings.block_env_managed_settings} />
        <ApiSettingField
          setting={settings.enforce_env_on_restart}
          disabled
          hint="Coming in a future release"
        />
      </SettingGroup>

      <SettingGroup title="Refresh Intervals">
        <ApiSettingField
          setting={settings.mod_list_refresh_interval}
          suffix="seconds"
        />
        <ApiSettingField
          setting={settings.server_versions_refresh_interval}
          suffix="seconds"
        />
      </SettingGroup>
    </div>
  );
}
```

### Generic File Editing (Future Epic)

**Deferred to "File Manager" Epic:**

- Full JSON editor with syntax highlighting
- Create/delete config files
- Backup before edit
- Schema validation

**Rationale:**
- Console commands provide safer config changes for common settings
- File editing requires more security considerations (path traversal, validation)
- Deferring allows focus on high-value "live update" experience

### Open Questions for Implementation

| Question                                          | Answer                                   | Status           |
| ------------------------------------------------- | ---------------------------------------- | ---------------- |
| Which settings support console commands?          | Research console `/serverconfig` command | Needs Testing    |
| Do console changes persist to JSON automatically? | Believed yes, needs verification         | Needs Testing    |
| How to detect file changes made by game server?   | File watcher or poll on GET              | Decision Pending |
| How to handle partial command failures?           | Return error, don't set restart flag     | Decided          |

### Story Updates Required

Original Epic 6 stories need complete rewrite to reflect architectural pivot:

| Original Story               | Why It's Obsolete                                  |
| ---------------------------- | -------------------------------------------------- |
| 6.1: Config Files API        | File-centric approach replaced by settings API    |
| 6.2: Config File Editing API | Direct file editing replaced by console commands  |
| 6.3: Config Editor UI        | JSON editor replaced by form-based settings page  |

**Revised Epic 6 Story Structure:**

| Story | Title | Scope |
|-------|-------|-------|
| **6.0** | Epic 6 Technical Preparation | Research console commands, create serverconfig-template.json, test VS_CFG_* handling |
| **6.1** | ConfigInitService & Template | First-run config generation from template + VS_CFG_* env vars |
| **6.2** | Game Settings API | GET /config/game, POST /config/game/settings/{key} with console command path |
| **6.3** | API Settings Service | GET /config/api, POST /config/api/settings/{key}, api-settings.json persistence |
| **6.4** | Settings UI | Form-based settings page with Game and API tabs |
| **6.5** | Raw Config Viewer | Read-only /config/files/{filename} for troubleshooting |

**Key Changes from Original:**

1. **Two config domains** - Game (`/config/game`) and API (`/config/api`) separated
2. **ConfigInitService** - First-run initialization with VS_CFG_* environment variables
3. **Console command path** - Live updates via `/serverconfig` commands, not file editing
4. **Form-based UI** - Settings page with badges, not JSON editor
5. **Deferred file editing** - Raw file viewer is read-only; editing pushed to future "File Manager" epic

### Testing Strategy

**Console Command Integration Tests:**

```python
@pytest.mark.integration
async def test_setting_update_via_console(running_server):
    """Test that setting updates use console commands."""
    # Start with known value
    config = await api_client.get("/config")
    original_name = config["data"]["settings"]["ServerName"]["value"]

    # Update via API
    response = await api_client.post(
        "/config/settings/ServerName",
        json={"value": "Test Server Name"}
    )

    assert response["data"]["method"] == "console_command"
    assert response["data"]["pending_restart"] == False

    # Verify change took effect
    config = await api_client.get("/config")
    assert config["data"]["settings"]["ServerName"]["value"] == "Test Server Name"

    # Verify persisted to file (game server handles this)
    file_content = Path("/data/config/serverconfig.json").read_text()
    assert "Test Server Name" in file_content
```

### Error Codes for Epic 6

```python
# api/src/vintagestory_api/models/errors.py
class ErrorCode:
    # ... existing codes ...

    # Epic 6 additions
    CONFIG_NOT_FOUND = "CONFIG_NOT_FOUND"
    CONFIG_READ_ERROR = "CONFIG_READ_ERROR"
    SETTING_UNKNOWN = "SETTING_UNKNOWN"
    SETTING_ENV_MANAGED = "SETTING_ENV_MANAGED"
    SETTING_UPDATE_FAILED = "SETTING_UPDATE_FAILED"
    CONSOLE_COMMAND_FAILED = "CONSOLE_COMMAND_FAILED"
```

---

## Epic 7 & 8: APScheduler Integration & Periodic Tasks

_Added during Epic 5 retrospective (2025-12-30)_

### Background Task Scheduling Decision

**Decision:** Use APScheduler with AsyncIOScheduler and MemoryJobStore

**Rationale:**
- Cron syntax support for flexible scheduling
- Built-in job management (pause, resume, remove)
- Async-native with `AsyncIOScheduler`
- No external dependencies (MemoryJobStore is in-memory)
- Good learning opportunity for the team

**Alternatives Considered:**

| Option | Rejected Because |
|--------|------------------|
| Manual asyncio loop | No cron syntax, manual job management |
| Celery Beat | Requires broker, overkill for our needs |
| arq | Requires Redis |
| rocketry | Less proven, smaller community |

### APScheduler Architecture Pattern

**Scheduler Setup:**

```python
# api/src/vintagestory_api/services/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor

class SchedulerService:
    """Manages periodic background tasks."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler(
            jobstores={"default": MemoryJobStore()},
            executors={"default": AsyncIOExecutor()},
            job_defaults={
                "coalesce": True,  # Combine missed runs into one
                "max_instances": 1,  # Only one instance of each job
                "misfire_grace_time": 60,  # Allow 60s grace for misfires
            }
        )

    def start(self):
        """Start the scheduler."""
        self.scheduler.start()

    def shutdown(self, wait: bool = True):
        """Shutdown the scheduler."""
        self.scheduler.shutdown(wait=wait)

    def add_interval_job(
        self,
        func,
        seconds: int,
        job_id: str,
        **kwargs
    ):
        """Add an interval-based job."""
        self.scheduler.add_job(
            func,
            trigger="interval",
            seconds=seconds,
            id=job_id,
            replace_existing=True,
            **kwargs
        )

    def add_cron_job(
        self,
        func,
        cron_expression: str,
        job_id: str,
        **kwargs
    ):
        """Add a cron-based job."""
        from apscheduler.triggers.cron import CronTrigger
        self.scheduler.add_job(
            func,
            trigger=CronTrigger.from_crontab(cron_expression),
            id=job_id,
            replace_existing=True,
            **kwargs
        )

    def remove_job(self, job_id: str):
        """Remove a job by ID."""
        self.scheduler.remove_job(job_id)

    def get_jobs(self) -> list:
        """List all scheduled jobs."""
        return self.scheduler.get_jobs()
```

**Lifespan Integration:**

```python
# api/src/vintagestory_api/main.py
from vintagestory_api.services.scheduler import SchedulerService

scheduler_service: SchedulerService | None = None

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global scheduler_service

    # ... existing startup ...

    # Initialize scheduler
    scheduler_service = SchedulerService()
    scheduler_service.start()
    logger.info("scheduler_started")

    yield

    # Shutdown scheduler
    if scheduler_service:
        scheduler_service.shutdown(wait=True)
        logger.info("scheduler_stopped")

    # ... existing shutdown ...
```

### Epic 7: APScheduler Integration (Foundation)

**Scope:** Basic scheduler infrastructure, no jobs yet.

| Story | Title | Scope |
|-------|-------|-------|
| **7.0** | Epic 7 Preparation | Research APScheduler patterns, review async integration |
| **7.1** | SchedulerService | Core service with start/shutdown, lifespan integration |
| **7.2** | Job Management API | GET /jobs (list), DELETE /jobs/{id} (admin only) |
| **7.3** | Scheduler Health | Include scheduler status in /healthz, job count metrics |

### Epic 8: Periodic Task Patterns

**Scope:** Implement initial periodic jobs using the scheduler.

| Story | Title | Scope |
|-------|-------|-------|
| **8.0** | Epic 8 Preparation | Define job patterns, error handling strategy |
| **8.1** | Mod Cache Refresh Job | Periodic mod API cache refresh (uses `mod_list_refresh_interval`) |
| **8.2** | Server Versions Check Job | Check for new VS versions (uses `server_versions_refresh_interval`) |
| **8.3** | Job Configuration UI | Display scheduled jobs in settings, allow interval changes |

### Job Patterns

**Standard Job Template:**

```python
# api/src/vintagestory_api/jobs/mod_cache_refresh.py
import structlog

logger = structlog.get_logger()

async def refresh_mod_cache():
    """Periodic job to refresh mod API cache."""
    try:
        from vintagestory_api.services.mods import get_mod_service
        mod_service = get_mod_service()
        await mod_service.refresh_cache()
        logger.info("mod_cache_refreshed")
    except Exception as e:
        logger.error("mod_cache_refresh_failed", error=str(e))
        # Don't re-raise - let scheduler continue
```

**Job Registration Pattern:**

```python
# api/src/vintagestory_api/jobs/__init__.py
from vintagestory_api.services.scheduler import SchedulerService
from vintagestory_api.services.api_settings import get_api_settings

def register_default_jobs(scheduler: SchedulerService):
    """Register all default periodic jobs."""
    settings = get_api_settings()

    # Mod cache refresh
    if settings.mod_list_refresh_interval > 0:
        from vintagestory_api.jobs.mod_cache_refresh import refresh_mod_cache
        scheduler.add_interval_job(
            refresh_mod_cache,
            seconds=settings.mod_list_refresh_interval,
            job_id="mod_cache_refresh"
        )

    # Server versions check
    if settings.server_versions_refresh_interval > 0:
        from vintagestory_api.jobs.server_versions import check_server_versions
        scheduler.add_interval_job(
            check_server_versions,
            seconds=settings.server_versions_refresh_interval,
            job_id="server_versions_check"
        )
```

### Epic Reordering

**Updated Epic Sequence:**

| Epic | Title | Status |
|------|-------|--------|
| 1-5 | (Completed) | Done |
| **6** | Game Configuration Management | Planned |
| **7** | APScheduler Integration | New |
| **8** | Periodic Task Patterns | New |
| **9** | Server Settings & Whitelist | (Former Epic 7) |

**Note:** Original Epic 7 (Server Settings & Whitelist) becomes Epic 9.
