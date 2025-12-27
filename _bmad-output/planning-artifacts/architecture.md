---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
status: 'complete'
completedAt: '2025-12-26'
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/ux-design-specification.md'
  - 'agentdocs/vintagestory-modapi.md'
workflowType: 'architecture'
project_name: 'vintagestory-server'
user_name: 'Matt'
date: '2025-12-26'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**

37 functional requirements spanning 8 capability areas:

| Category | FRs | Architectural Implication |
|----------|-----|---------------------------|
| Server Lifecycle | FR1-5 | Process manager component, state machine for server status |
| Console Access | FR6-9 | WebSocket server, ring buffer implementation, Admin-only access |
| Mod Management | FR10-17 | External HTTP client, file system operations, compatibility logic |
| Game Configuration | FR18-22 | JSON file I/O, validation layer |
| Settings Management | FR23-26 | Lightweight persistence (JSON files) |
| Health & Observability | FR27-30 | Kubernetes-compatible endpoints, process health checks |
| Authentication | FR31-37 | Middleware for API key validation, role-based access control |
| Deployment | FR38-39 | Docker Compose, environment variable configuration |

**Non-Functional Requirements:**

| Category | Key Requirements | Architectural Impact |
|----------|-----------------|---------------------|
| Performance | <1s console latency, <500ms API response | In-memory operations, efficient WebSocket handling |
| Security | API keys never logged, in-memory console buffer | Logging configuration, no persistence for sensitive data |
| Reliability | API survives game crashes, auto-reconnect | Decoupled process management, WebSocket reconnection logic |
| Integration | Graceful mod API failures, clear error messages | Circuit breaker pattern, response caching |
| Observability | Structured JSON logs, contextual errors | Logging framework configuration, error envelope design |

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

| Option | Evaluation |
|--------|------------|
| uv-fastapi-example (Official) | ✅ Selected - Official Astral pattern, minimal, production-ready |
| py-fastapi-starter | Modular but includes PostgreSQL/Alembic we don't need |
| Full starter templates | Over-engineered for our no-database requirement |

#### Frontend (React + shadcn/ui)

| Option | Evaluation |
|--------|------------|
| Official shadcn/ui + Vite | ✅ Selected - Documented, Tailwind v4, full control |
| react-ts-shadcn-starter | Good but third-party maintenance |
| vite-react-ts-shadcn-ui | Includes extras (Husky, etc.) we may not need |

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

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Persistence** | In-memory + JSON file sync | Fast reads, durable writes, no database overhead |
| **State Location** | `data/state.json` | Single source of truth for server state, mod states, pending restarts |
| **Validation** | Pydantic v2 models | Type-safe, automatic serialization |
| **Write Safety** | Atomic file writes | Prevents corruption on crash (temp file + rename) |

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

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Auth Method** | API key via `X-API-Key` header | Simple, stateless, sufficient for single-server |
| **Roles** | Admin / Monitor / None | Three-tier access per PRD |
| **Key Storage** | Environment variables | `VS_API_KEY_ADMIN`, `VS_API_KEY_MONITOR` |
| **WebSocket Auth** | Query param on connection | `?api_key=xxx` validated on connect |

### API & Communication Patterns

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **API Style** | REST + WebSocket | REST for CRUD, WebSocket for streaming |
| **Versioning** | `/api/v1alpha1` | Kubernetes-style, signals API maturity |
| **HTTP Client** | httpx | Async-native, modern, mockable with respx |
| **WebSocket** | Starlette built-in | No additional dependencies, well-integrated |
| **Response Envelope** | `{"status": "ok\|error", "data": {...}}` | Consistent, predictable |

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

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Server State** | TanStack Query v5 | Caching, auto-refresh, optimistic updates |
| **Client State** | React Context | Theme, sidebar state, simple UI state |
| **Routing** | React Router v7 | Standard, well-documented, stable |
| **Forms** | React Hook Form (if needed) | Type-safe, performant |
| **API Mocking (tests)** | MSW (Mock Service Worker) | Realistic API mocking for tests |

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

### Infrastructure & Deployment

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Logging** | structlog | Structured JSON, beautiful dev output |
| **Container Strategy** | Single container (API + game server) | API serves static files, manages game server binary, simplified deployment |
| **Base Image** | `mcr.microsoft.com/dotnet/runtime:8.0.22-noble-amd64` | Ubuntu 24.04 Noble with .NET 8 (for game server) + Python 3.12 native to apt |
| **Process Manager** | Uvicorn (single process) + Subprocess management | Uvicorn serves API, game server runs as subprocess |

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

| Component | Testing Strategy | Tools |
|-----------|-----------------|-------|
| StateManager | Unit tests with temp files | pytest |
| Mod API integration | Mock external API | respx |
| WebSocket streaming | Abstract stdout capture as service | pytest-asyncio |
| Frontend components | Component + integration tests | @testing-library/react + MSW |

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

| Element | Convention | Example |
|---------|------------|---------|
| Endpoints | Plural nouns, kebab-case | `/api/v1alpha1/mods`, `/api/v1alpha1/config-files` |
| Route params | snake_case | `/mods/{mod_slug}` |
| Query params | snake_case | `?game_version=1.21.3` |
| Headers | X-Prefix for custom | `X-API-Key` |

**Python Naming Conventions:**

| Element | Convention | Example |
|---------|------------|---------|
| Files/modules | snake_case | `mod_service.py`, `server_router.py` |
| Classes | PascalCase | `ModService`, `StateManager` |
| Functions | snake_case | `get_mod_details()`, `install_mod()` |
| Variables | snake_case | `mod_slug`, `game_version` |
| Constants | SCREAMING_SNAKE | `DEFAULT_TIMEOUT`, `MAX_RETRIES` |

**TypeScript Naming Conventions:**

| Element | Convention | Example |
|---------|------------|---------|
| Files | kebab-case | `mod-card.tsx`, `use-server-status.ts` |
| Components | PascalCase | `ModCard`, `ServerStatus` |
| Hooks | camelCase with `use` prefix | `useServerStatus`, `useInstallMod` |
| Functions | camelCase | `formatModVersion()`, `parseSlug()` |
| Variables | camelCase | `modSlug`, `isLoading` |
| Types/Interfaces | PascalCase | `Mod`, `ServerState`, `ApiResponse` |

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

| Stack | Pattern | Location |
|-------|---------|----------|
| Backend | Separate `tests/` directory | `api/tests/test_*.py` |
| Frontend | Co-located with components | `*.test.tsx` next to component |

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

| Status | Usage |
|--------|-------|
| 200 | Success (GET, PUT) |
| 201 | Created (POST that creates) |
| 204 | No content (DELETE) |
| 400 | Bad request (validation error) |
| 401 | Unauthorized (missing/invalid key) |
| 403 | Forbidden (insufficient role) |
| 404 | Not found |
| 500 | Server error |
| 502 | External API error |

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

| Avoid | Do Instead |
|-------|------------|
| `getUserData()` in Python | `get_user_data()` |
| `mod-service.py` filename | `mod_service.py` |
| `ModCard.tsx` filename with default export | Keep PascalCase, it's correct for React |
| Mixing snake_case in frontend code | Transform at API boundary |
| Storing API data in React Context | Use TanStack Query |
| `tests/` folder in web/ | Co-locate tests with components |
| Custom loading state variables | Use TanStack Query's isLoading |
| Generic error messages | Use error codes + descriptive messages |

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

| Pattern | Description | Pros | Cons |
|---------|-------------|------|------|
| **Single Container** (CHOSEN) | API and game server run in same container | ✓ Simpler deployment (one service) <br> ✓ Shared data volume <br> ✓ No inter-container networking <br> ✓ Lower infrastructure overhead | ✗ Larger image (~300MB) <br> ✗ Cannot scale independently <br> ✗ Game server crash impacts API (mitigated by subprocess management) |
| **Two Containers** | Separate API and game server containers | ✓ Smaller API image (~150MB) <br> ✓ Independent scaling <br> ✓ Isolated failures | ✗ More complex deployment <br> ✗ Inter-container networking <br> ✗ Shared volume management <br> ✗ Higher infrastructure overhead |

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

| Boundary | Internal | External |
|----------|----------|----------|
| `/api/v1alpha1/*` | All API routes | Clients (Web UI, CLI) |
| `/ws/console` | Console WebSocket | Admin clients only |
| `/*` (static) | Vite build output | Web browsers |
| `/healthz`, `/readyz` | Health endpoints | Load balancers, K8s |

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

| Data Type | Storage | Access Pattern |
|-----------|---------|----------------|
| Server state | `/data/state/state.json` | In-memory + atomic file sync |
| Mod files | `/data/mods/` | File system operations |
| Game config | `/data/config/` | Read/write JSON files |
| Console buffer | In-memory ring buffer | WebSocket streaming |
| Logs | `/data/logs/` | Append-only files |

### Requirements to Structure Mapping

**Epic/Feature → Directory Mapping:**

| Feature Area | Backend Location | Frontend Location |
|--------------|-----------------|-------------------|
| Server Lifecycle | `routers/server.py`, `services/server.py` | `features/dashboard/` |
| Mod Management | `routers/mods.py`, `services/mods.py` | `features/mods/` |
| Config Editing | `routers/config.py` | `features/config/` |
| Console Access | `services/console.py`, WebSocket handler | `features/terminal/` |
| Authentication | `middleware/auth.py` | `api/client.ts` (headers) |
| Health Checks | `routers/health.py` | N/A (infrastructure) |

**Cross-Cutting Concerns:**

| Concern | Backend Files | Frontend Files |
|---------|---------------|----------------|
| State Management | `services/state.py`, `models/state.py` | `hooks/use-*.ts`, `contexts/` |
| Error Handling | `models/errors.py`, exception handlers | Error boundaries, toast |
| Logging | `structlog` configuration | Browser console |
| API Response Format | `models/responses.py` | `api/types.ts` |

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

| Integration | Protocol | Error Handling |
|-------------|----------|----------------|
| VintageStory Mod API | HTTPS (httpx) | Timeout, cache, graceful fallback |
| GitHub Container Registry | Docker pull | Version tags, SHA pinning |
| Game Server Binary | HTTPS download | Checksum verification |

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

| File | Purpose |
|------|---------|
| `.mise.toml` | Tool version management |
| `docker-compose.yaml` | Production deployment |
| `docker-compose.dev.yaml` | Local development |
| `Dockerfile` | Container build |
| `.env.example` | Environment template |
| `.gitignore` | Git exclusions |

**Environment Variables:**

| Variable | Required | Description |
|----------|----------|-------------|
| `VS_API_KEY_ADMIN` | Yes | Admin API key |
| `VS_API_KEY_MONITOR` | No | Read-only API key |
| `VS_GAME_VERSION` | No | Game version (default: stable) |
| `VS_DEBUG` | No | Enable debug logging |

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

| Category | FRs | Architectural Support |
|----------|-----|----------------------|
| Server Lifecycle | FR1-5 | `routers/server.py` + `services/server.py` |
| Console Access | FR6-9 | `services/console.py` + WebSocket handler |
| Mod Management | FR10-17 | `routers/mods.py` + `services/mods.py` |
| Game Configuration | FR18-22 | `routers/config.py` |
| Settings Management | FR23-26 | `services/state.py` + config endpoints |
| Health & Observability | FR27-30 | `routers/health.py` |
| Authentication | FR31-37 | `middleware/auth.py` |
| Deployment | FR38-39 | `docker-compose.yaml` + env vars |

**Non-Functional Requirements Coverage:**

| NFR | Requirement | Architectural Support |
|-----|-------------|----------------------|
| NFR1 | <1s console latency | WebSocket streaming, in-memory buffer |
| NFR2 | Real-time streaming | Starlette WebSocket |
| NFR3 | <500ms API response | In-memory state, async operations |
| NFR4 | Secure key storage | Environment variables |
| NFR5 | TLS termination | Out of scope (reverse proxy) |
| NFR6 | No console persistence | In-memory ring buffer only |
| NFR7 | Auth failure logging | structlog with security context |
| NFR8 | API survives crashes | Decoupled process management |
| NFR9 | Crash recovery | StateManager with file sync |
| NFR10 | Auto-reconnect | Exponential backoff pattern |
| NFR11-13 | Graceful API failures | httpx timeout + cache |
| NFR14-16 | Structured logs | structlog JSON + context |

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
- The *rationale* behind decisions, not just the decision itself
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

