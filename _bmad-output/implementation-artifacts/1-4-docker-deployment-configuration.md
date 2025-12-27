# Story 1.4: Docker Deployment Configuration

Status: done

## Story

As a **server administrator**,
I want **to deploy the application using docker-compose**,
So that **I can run VintageStory Server Manager with minimal configuration**.

## Acceptance Criteria

### AC1: Docker Compose Production Deployment

**Given** I have Docker and docker-compose installed
**When** I run `docker compose up -d` with `docker-compose.yaml`
**Then** the container starts successfully
**And** the web UI is accessible on port 8080
**And** the health endpoints respond correctly
*(Covers FR38)*

### AC2: Container Logging

**Given** the container is running
**When** I check the container logs
**Then** I see structured startup messages
**And** no errors are present for a clean start

### AC3: Environment Variable Configuration

**Given** I set environment variables (`VS_API_KEY_ADMIN`, etc.)
**When** the container starts
**Then** the application reads configuration from environment variables
**And** default values are used for optional unset variables
*(Covers FR39)*

### AC4: Development Build Configuration

**Given** a `docker-compose.dev.yaml` file exists
**When** I run `docker compose -f docker-compose.dev.yaml up --build`
**Then** the image builds from local source
**And** development defaults are applied (e.g., `VS_DEBUG=true`)

### AC5: Volume Mount Configuration

**Given** the container is running
**When** I examine the volume mounts
**Then** `/data` is mounted for persistent storage
**And** the directory structure matches Architecture specification (`/data/server/`, `/data/mods/`, `/data/state/`, etc.)

### AC6: Environment Documentation

**Given** I have a `.env.example` file
**When** I review it
**Then** all configurable environment variables are documented with descriptions

## Tasks / Subtasks

- [x] Task 1: Create Multi-Stage Dockerfile (AC: #1, #2, #4)
  - [x] 1.1: Create `Dockerfile` at project root with multi-stage build
  - [x] 1.2: Stage 1 (web-build): Build frontend with `node:22-slim` base
  - [x] 1.3: Stage 2 (final): Production image with `mcr.microsoft.com/dotnet/runtime:8.0.22-noble-amd64` (deviates from architecture - .NET base chosen for future VintageStory server compatibility)
  - [x] 1.4: Copy built frontend from stage 1 to `/app/static`
  - [x] 1.5: Install Python dependencies using `uv` from lockfile
  - [x] 1.6: Configure non-root user for security
  - [x] 1.7: Add HEALTHCHECK instruction for container health
  - [x] 1.8: Set appropriate CMD for uvicorn startup

- [x] Task 2: Configure Static File Serving (AC: #1)
  - [x] 2.1: Update `api/src/vintagestory_api/main.py` to serve static files from `/app/static`
  - [x] 2.2: Mount StaticFiles at root path "/" (after API routes)
  - [x] 2.3: Configure SPA fallback for React Router (serve index.html for client routes)
  - [x] 2.4: Ensure API routes `/api/*` and `/healthz`, `/readyz` take precedence

- [x] Task 3: Update docker-compose.yaml (AC: #1, #3, #5)
  - [x] 3.1: Replace placeholder with production configuration
  - [x] 3.2: Configure image from `ghcr.io/craquehouse/vintagestory-server:latest`
  - [x] 3.3: Expose port 8080 for web UI/API
  - [x] 3.4: Expose port 42420 for game server (reserved for future)
  - [x] 3.5: Configure `/data` volume mount
  - [x] 3.6: Set environment variables from `.env` file
  - [x] 3.7: Add `restart: unless-stopped` policy
  - [x] 3.8: Add healthcheck matching Dockerfile

- [x] Task 4: Update docker-compose.dev.yaml (AC: #4)
  - [x] 4.1: Configure local build from Dockerfile
  - [x] 4.2: Set development environment defaults (`VS_DEBUG=true`)
  - [x] 4.3: Use same volume and port configuration as production
  - [x] 4.4: Add dev-friendly API key defaults for local testing

- [x] Task 5: Update .env.example (AC: #6)
  - [x] 5.1: Document all environment variables with descriptions
  - [x] 5.2: Include example values and defaults
  - [x] 5.3: Note which variables are required vs optional

- [x] Task 6: Create Data Directory Structure (AC: #5)
  - [ ] 6.1: Document expected `/data` subdirectory structure in README (deferred - existing README sufficient)
  - [x] 6.2: Ensure application creates subdirectories on startup if missing
  - [x] 6.3: Update settings to use `/data/state/` for state persistence

- [x] Task 7: Verify and Test (AC: #1, #2, #3, #4, #5, #6)
  - [x] 7.0: Add test coverage for static file serving and SPA routing
  - [x] 7.1: Build image: `docker build -t vintagestory-server:local .` ✅ Build successful (21s)
  - [x] 7.2: Run container: `docker compose -f docker-compose.dev.yaml up --build` ✅ Container started healthy
  - [x] 7.3: Verify web UI loads at <http://localhost:8080> ✅ index.html served correctly
  - [x] 7.4: Verify `/healthz` returns 200 ✅ Returns `{"status": "ok", "data": {"api": "healthy", "game_server": "not_installed"}}`
  - [x] 7.5: Verify `/readyz` returns 200 ✅ Returns `{"status": "ok", "data": {"ready": true, "checks": {"api": true}}}`
  - [x] 7.6: Verify structured logs in container output (`docker logs <container>`) ✅ Structured key-value logging with `data_dir=/data debug_mode=True`
  - [x] 7.7: Verify `/data` directory is created with correct structure ✅ All subdirectories created: server/, mods/, config/, state/, logs/, backups/, vsmanager/
  - [x] 7.8: Test environment variable configuration ✅ VS_DEBUG=true working, SPA routes fall back to index.html correctly

## Dev Notes

### CRITICAL: Architecture Compliance

**Single Container Strategy (from Architecture):**
The application uses a single container that serves both the API and static frontend files. This simplifies deployment and reduces infrastructure complexity.

```
┌─────────────────────────────────────────┐
│  vintagestory-manager container         │
│  ┌─────────────────────────────────┐    │
│  │  FastAPI + Uvicorn              │    │
│  │  - Serves /api/* endpoints      │    │
│  │  - Serves /* static files       │    │
│  │  - WebSocket /ws/console        │    │
│  └─────────────────────────────────┘    │
│                 │                        │
│                 ▼                        │
│  ┌─────────────────────────────────┐    │
│  │  Mounted Volumes                │    │
│  │  - /data (state, config, mods)  │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

**Volume Mount Structure (MUST follow exactly):**

```
/data (single mounted volume)
├── server/                   # VintageStory server installation (future)
├── mods/                     # Mod files (future)
├── config/                   # Game server configuration (future)
├── state/                    # API state persistence
│   └── state.json            # Application state file
├── logs/                     # Application logs (optional)
└── backups/                  # Server backups (future)
```

### Docker Registry

**Container Registry:** `ghcr.io/craquehouse/vintagestory-server`

- Tags: `latest`, `vX.Y.Z` (semantic versions)
- Images are built and pushed via CI/CD (future story)

### Multi-Stage Dockerfile Pattern

```dockerfile
# Stage 1: Build frontend
FROM node:22-slim AS web-build
WORKDIR /app
COPY web/package.json web/bun.lock ./
RUN npm install -g bun && bun install --frozen-lockfile
COPY web/ ./
RUN bun run build

# Stage 2: Production image
FROM python:3.13-slim AS final
WORKDIR /app

# Create non-root user
RUN groupadd -r vsmanager && useradd -r -g vsmanager vsmanager

# Install uv for fast dependency installation
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy and install Python dependencies
COPY api/pyproject.toml api/uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application code
COPY api/src/ ./src/

# Copy built frontend
COPY --from=web-build /app/dist /app/static

# Create data directory
RUN mkdir -p /data/state && chown -R vsmanager:vsmanager /app /data

# Switch to non-root user
USER vsmanager

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/healthz')" || exit 1

EXPOSE 8080 42420

CMD ["uv", "run", "uvicorn", "vintagestory_api.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Static File Serving Pattern

```python
# api/src/vintagestory_api/main.py
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

STATIC_DIR = Path("/app/static")

# After all API routes are registered...

# Serve static files (JS, CSS, assets)
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    # SPA fallback - serve index.html for all non-API routes
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Check if it's a static file
        file_path = STATIC_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        # Otherwise serve index.html for client-side routing
        return FileResponse(STATIC_DIR / "index.html")
```

### docker-compose.yaml Pattern (Production)

```yaml
services:
  manager:
    image: ghcr.io/craquehouse/vintagestory-server:latest
    container_name: vintagestory-manager
    ports:
      - "8080:8080"      # Web UI + API
      - "42420:42420"    # Game server (future)
    volumes:
      - ./data:/data
    environment:
      - VS_API_KEY_ADMIN=${VS_API_KEY_ADMIN}
      - VS_API_KEY_MONITOR=${VS_API_KEY_MONITOR:-}
      - VS_GAME_VERSION=${VS_GAME_VERSION:-stable}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/healthz')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### docker-compose.dev.yaml Pattern (Development)

```yaml
services:
  manager:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: vintagestory-manager-dev
    ports:
      - "8080:8080"
      - "42420:42420"
    volumes:
      - ./data:/data
    environment:
      - VS_API_KEY_ADMIN=${VS_API_KEY_ADMIN:-dev-admin-key}
      - VS_API_KEY_MONITOR=${VS_API_KEY_MONITOR:-}
      - VS_GAME_VERSION=${VS_GAME_VERSION:-stable}
      - VS_DEBUG=true
    restart: unless-stopped
```

### Environment Variables (Complete List)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VS_API_KEY_ADMIN` | **Yes** | - | Admin API key for full access |
| `VS_API_KEY_MONITOR` | No | - | Read-only API key for monitoring |
| `VS_GAME_VERSION` | No | `stable` | VintageStory version to install |
| `VS_DEBUG` | No | `false` | Enable debug logging |
| `VS_DATA_DIR` | No | `/data` | Data directory path |

### Technology Stack (from Previous Stories)

| Technology | Version | Notes |
|------------|---------|-------|
| **Python** | 3.13 | Base image `python:3.13-slim` |
| **Node.js** | 22 | Build stage only `node:22-slim` |
| **FastAPI** | 0.127.1 | Installed in Story 1.2 |
| **Uvicorn** | 0.40.0 | Included via fastapi[standard] |
| **Bun** | 1.3.5 | Frontend build in docker |
| **uv** | latest | Python package management |

### Web Research: Docker Best Practices 2025

**Multi-Stage Build Benefits:**

- Single-Stage builds: ~273 MB
- Multi-Stage builds: ~225 MB
- Runtime Artifact builds: ~208 MB

**Security Requirements:**

- Create non-root user (`vsmanager`)
- Set file ownership with `chown`
- Use `USER vsmanager` in final stage

**Health Check Requirements:**

- Use built-in Python urllib (no curl needed in slim image)
- `--start-period` allows for application startup time
- `--retries=3` before marking unhealthy

**Docker Compose v2 (2025):**

- No `version:` field needed (deprecated)
- Use `docker compose` (not `docker-compose`)
- Rename files to `compose.yaml` (modern convention) - *but keeping docker-compose.yaml for user familiarity*
- Use `restart: unless-stopped` for production

### Previous Story Intelligence

**From Story 1.1:**

- `.mise.toml` pins uv 0.9.18, bun 1.3.5
- Placeholder Dockerfile exists (needs real implementation)
- Placeholder docker-compose files exist (need real implementation)
- `.env.example` exists (needs expansion)

**From Story 1.2:**

- Health endpoints `/healthz` and `/readyz` are implemented
- Structured logging via structlog is configured
- Settings class uses `pydantic-settings` with env var support
- API response envelope pattern established

**From Story 1.3:**

- Frontend builds with `bun run build` output to `dist/`
- React Router handles client-side routing (needs SPA fallback)
- Build verified working: 67 tests passing

**Git Patterns:**

- Commits use conventional commit format: `feat(scope): message`
- Code review runs after implementation

### Files to Modify

**Existing files (from Story 1.1 placeholders):**

- `Dockerfile` - Replace placeholder with multi-stage build
- `docker-compose.yaml` - Replace placeholder with production config
- `docker-compose.dev.yaml` - Replace placeholder with dev config
- `.env.example` - Expand with all environment variables

**New/Modified for static serving:**

- `api/src/vintagestory_api/main.py` - Add static file serving

### Dockerfile .dockerignore

Create `.dockerignore` to exclude unnecessary files:

```
.git
.gitignore
.env
.env.*
!.env.example
data/
*.md
.mise.toml
__pycache__
*.pyc
.pytest_cache
.venv
node_modules
.DS_Store
```

### Testing Checklist

After implementation, verify:

1. `docker build -t test .` completes successfully
2. Image size is under 300 MB
3. Container starts with `docker compose up`
4. <http://localhost:8080> shows React app
5. <http://localhost:8080/healthz> returns `{"status": "ok"}`
6. <http://localhost:8080/readyz> returns `{"status": "ok"}`
7. Client-side routes (e.g., `/mods`) work with browser refresh
8. Logs show structured JSON output
9. `/data` directory is writable

### Project Structure Notes

**Alignment with unified project structure:**

- Dockerfile at project root (builds both api/ and web/)
- Static files served from `/app/static` inside container
- Data volume at `/data` with subdirectories
- No changes to existing source code structure

**No conflicts detected** - Following Architecture doc exactly.

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Infrastructure-Deployment]
- [Source: _bmad-output/planning-artifacts/architecture.md#Docker-Architecture]
- [Source: _bmad-output/planning-artifacts/architecture.md#Container-Volume-Strategy]
- [Source: _bmad-output/planning-artifacts/architecture.md#Docker-Compose-Configuration]
- [Source: _bmad-output/planning-artifacts/epics.md#Story-1.4]
- [Source: _bmad-output/implementation-artifacts/1-1-initialize-development-environment-and-project-structure.md]
- [Source: _bmad-output/implementation-artifacts/1-2-backend-api-skeleton-with-health-endpoints.md]
- [Source: _bmad-output/implementation-artifacts/1-3-frontend-application-shell.md]
- [Web: FastAPI Docker Best Practices](https://betterstack.com/community/guides/scaling-python/fastapi-docker-best-practices/)
- [Web: Docker 2025 Best Practices](https://docs.benchhub.co/docs/tutorials/docker/docker-best-practices-2025)
- [Web: Docker Compose Health Checks](https://last9.io/blog/docker-compose-health-checks/)
- [Web: Python Docker Images with UV](https://digon.io/en/blog/2025_07_28_python_docker_images_with_uv)

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-20250514

### Debug Log References

None - implementation completed without major issues.

### Completion Notes List

**Implementation Summary:**

1. **Dockerfile Multi-Stage Build**: Created a production-ready multi-stage Dockerfile that builds the frontend with Bun/Node 22, then creates a final image using .NET 8.0 runtime on Ubuntu 24.04 Noble. The .NET base was chosen instead of `python:3.13-slim` (as specified in architecture) because VintageStory server requires .NET runtime, and this provides a single base image for both the API and future game server management. This is a documented architectural decision deviation.

2. **Static File Serving**: Implemented static file serving and SPA fallback routing in `main.py`. The API serves `/assets/` for JS/CSS files and falls back to `index.html` for all non-API routes, enabling client-side routing with React Router.

3. **Docker Compose Configurations**: Created both production (`docker-compose.yaml`) and development (`docker-compose.dev.yaml`) configurations. Production pulls from container registry, development builds locally. Both expose ports 8080 (web UI/API) and 42420 (game server, future).

4. **Environment Variables**: Expanded `.env.example` with complete documentation of all environment variables including VS_API_KEY_ADMIN (required), VS_API_KEY_MONITOR (optional), VS_GAME_VERSION (defaults to "stable"), VS_DEBUG (defaults to "false"), VS_DATA_DIR (defaults to "/data"), and UV_LINK_MODE. Docker-compose files allow overrides for all optional variables using the `${VAR:-default}` pattern.

5. **Data Directory Structure**: Implemented `ensure_data_directories()` in config.py to create `/data/server/`, `/data/mods/`, `/data/config/`, `/data/state/`, `/data/logs/`, and `/data/backups/` on startup. Added validation to reject empty VS_API_KEY_ADMIN for security.

6. **Security Enhancements**:
   - Non-root user (`vsmanager`) for container security
   - Health check using Python urllib (no curl dependency)
   - API key validation on startup (rejects empty strings)
   - Appropriate file ownership with chown

7. **Tests Added** (38 tests total, all passing):
   - `test_config.py` (13 tests): Data directory configuration, environment variable overrides, directory creation, API key validation
   - `test_static_serving.py` (11 tests): Static file mounting, SPA fallback routing, API route priority, favicon handling
   - `test_health.py` (14 tests from Story 1.2): Health endpoints, API response envelopes (still passing)

**Code Review Findings Applied:**

- Fixed Bun version pinning (now uses 1.3.5 matching .mise.toml)
- Removed unnecessary `python3.12-venv` package from Dockerfile
- Added UV_LINK_MODE documentation to .env.example
- Added VS_DATA_DIR to docker-compose files with `/data` default and override support (follows same pattern as VS_GAME_VERSION)
- Added security validation for empty api_key_admin

**Architectural Decision Documented:**

The Dockerfile uses `mcr.microsoft.com/dotnet/runtime:8.0.22-noble-amd64` as base image implementing a single container pattern (API + game server together). This decision has been fully documented in architecture.md with:

1. **Container Strategy Decision Section:** Added comprehensive analysis of single vs. two container alternatives
2. **Rationale:** Deployment simplicity, lower infrastructure overhead, shared volume management
3. **Tradeoffs:** Larger image (~300MB) vs independent scaling (not needed for MVP)
4. **Migration Path:** Documented path to two-container pattern if multi-server fleet becomes requirement
5. **Updated Diagrams:** Single container diagram replaces two-container diagram
6. **Updated Configs:** Docker Compose configurations reflect single container approach

This decision balances simplicity with MVP requirements and can be revisited in Phase 3 if multi-server fleet patterns become a requirement.

**Architecture Updates Summary:**

- Updated "Infrastructure & Deployment" section with single container + .NET base image
- Replaced two-container architecture diagram with single-container diagram
- Added comprehensive "Container Strategy Decision" section with full analysis
- Updated Docker Compose Configuration sections with complete environment variables
- Updated implementation sequence to reflect Docker deployment in Story 1.4
- Updated epics.md to reference single container pattern and .NET base image

**All Testing Complete (Manual Docker Testing Performed on 2025-12-26):**

Task 7 (Verify and Test) - All subtasks verified ✅:

- [x] 7.1: Build image successful (21s, multi-stage build completed)
- [x] 7.2: Run container successful (healthy status, all ports mapped)
- [x] 7.3: Web UI loads correctly (index.html served with React app)
- [x] 7.4: /healthz returns 200 with correct response envelope
- [x] 7.5: /readyz returns 200 with readiness checks
- [x] 7.6: Structured logs visible in container output (key-value pairs like `data_dir=/data debug_mode=True`)
- [x] 7.7: /data directory structure created correctly (server/, mods/, config/, state/, logs/, backups/, vsmanager/)
- [x] 7.8: Environment variables working (VS_DEBUG=true, SPA routes fall back to index.html)

**Additional Verification:**

- ✅ Client routes (e.g., /mods, /dashboard) fall back to index.html for SPA routing
- ✅ Assets served correctly (/assets/*.js,*.css)
- ✅ Favicon accessible
- ✅ Healthcheck passes (container shows "healthy" status)
- ✅ Non-root user (vsmanager) used correctly

### File List

**Modified Files:**

- `Dockerfile` - Multi-stage build configuration
- `docker-compose.yaml` - Production docker-compose configuration
- `docker-compose.dev.yaml` - Development docker-compose configuration
- `.env.example` - Environment variable documentation
- `api/src/vintagestory_api/main.py` - Added static file serving and SPA fallback
- `api/src/vintagestory_api/config.py` - Added ensure_data_directories() and api_key_admin validation
- `api/pyproject.toml` - Added structlog dependency
- `_bmad-output/planning-artifacts/architecture.md` - Updated container strategy with single-container decision
- `_bmad-output/planning-artifacts/epics.md` - Updated infrastructure references to single container pattern

**New Files:**

- `.dockerignore` - Docker build exclusion patterns
- `api/tests/test_config.py` - Tests for configuration module (13 test cases)
- `api/tests/test_static_serving.py` - Tests for static file serving and SPA routing (11 test cases)
- `_bmad-output/implementation-artifacts/1-4-docker-deployment-configuration.md` - This story file

**Lock Files Updated:**

- `api/uv.lock` - Python dependency lock file (structlog added)
- `.python-version` - Python 3.12 specified
