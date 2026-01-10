# Project Structure & Boundaries

## Complete Project Directory Structure

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

## Container Strategy Decision

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

## Container Volume Strategy

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

## Docker Compose Configuration

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

## Architectural Boundaries

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

## Requirements to Structure Mapping

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

## Integration Points

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

## Development Workflow Integration

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

## File Organization Patterns

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
