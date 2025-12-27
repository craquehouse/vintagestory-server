# Story 1.2: Backend API Skeleton with Health Endpoints

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **operations engineer**,
I want **health check endpoints that report system status**,
So that **I can configure Kubernetes probes and monitoring systems**.

## Acceptance Criteria

### AC1: Health Endpoint (/healthz)
**Given** the API server is running
**When** I send a GET request to `/healthz`
**Then** I receive a 200 status code
**And** the response follows the envelope format `{"status": "ok", "data": {...}}`
**And** no authentication is required
*(Covers FR27)*

### AC2: Readiness Endpoint (/readyz)
**Given** the API server is running
**When** I send a GET request to `/readyz`
**Then** I receive a 200 status code when the API is ready to serve requests
**And** the response includes readiness information
**And** no authentication is required
*(Covers FR28)*

### AC3: Game Server Status in Health Response
**Given** the API server is running
**When** I query the health endpoints
**Then** the response includes game server process status (running/stopped/not_installed)
**And** the API health is reported separately from game server health
*(Covers FR29, NFR15)*

### AC4: API Availability When Game Server Down
**Given** the API server is running
**When** the game server process is not running
**Then** the API still responds to health checks (API healthy, game stopped)
*(Covers NFR8)*

### AC5: Structured Logging
**Given** any API request is made
**When** the server processes the request
**Then** structured JSON logs are emitted (in production mode)
**And** human-readable logs are emitted (in development mode)
*(Covers NFR14)*

## Tasks / Subtasks

- [x] Task 1: Create Response Models (AC: #1, #2, #3)
  - [x] 1.1: Create `api/src/vintagestory_api/models/responses.py` with `ApiResponse` envelope model
  - [x] 1.2: Create `api/src/vintagestory_api/models/errors.py` with `ErrorCode` constants
  - [x] 1.3: Create health-specific response models: `HealthResponse`, `ReadinessResponse`
  - [x] 1.4: Add game server status enum: `GameServerStatus` (not_installed, stopped, starting, running, stopping)

- [x] Task 2: Configure Structured Logging (AC: #5)
  - [x] 2.1: Add structlog configuration to `api/src/vintagestory_api/config.py`
  - [x] 2.2: Configure JSON output for production, colorful dev output for development
  - [x] 2.3: Add `VS_DEBUG` environment variable handling
  - [x] 2.4: Create logging middleware or lifespan handler to log requests

- [x] Task 3: Create Health Router (AC: #1, #2, #3, #4)
  - [x] 3.1: Create `api/src/vintagestory_api/routers/health.py`
  - [x] 3.2: Implement `GET /healthz` endpoint returning API health + game server status
  - [x] 3.3: Implement `GET /readyz` endpoint returning readiness check
  - [x] 3.4: Mock game server status as `not_installed` for now (real implementation in Epic 3)
  - [x] 3.5: Register health router in `main.py` (no prefix, at root level)

- [x] Task 4: Set Up API Versioning Structure (AC: #1, #2)
  - [x] 4.1: Update `main.py` to mount future routers at `/api/v1alpha1`
  - [x] 4.2: Keep health endpoints at root level (`/healthz`, `/readyz`) - NOT versioned
  - [x] 4.3: Add CORS middleware if needed for local development

- [x] Task 5: Write Tests (AC: #1, #2, #3, #4)
  - [x] 5.1: Create `api/tests/test_health.py`
  - [x] 5.2: Test `/healthz` returns 200 with correct envelope format
  - [x] 5.3: Test `/readyz` returns 200 with readiness info
  - [x] 5.4: Test health endpoints require no authentication
  - [x] 5.5: Test game server status field is present in response
  - [x] 5.6: Run tests: `cd api && uv run pytest tests/test_health.py -v`

- [x] Task 6: Verify Development Server (AC: #1, #2, #5)
  - [x] 6.1: Start dev server: `cd api && uv run fastapi dev src/vintagestory_api/main.py`
  - [x] 6.2: Test `/healthz` with curl
  - [x] 6.3: Test `/readyz` with curl
  - [x] 6.4: Verify structured logging output in terminal

## Dev Notes

### CRITICAL: Architecture Compliance

**Response Envelope Pattern (MUST follow exactly):**
```python
# Success Response
{
    "status": "ok",
    "data": { ... }
}

# Error Response
{
    "status": "error",
    "error": {
        "code": "ERROR_CODE",      # Machine-readable
        "message": "Human message", # Human-readable
        "details": {}              # Optional context
    }
}
```

**Health Endpoint Paths (NOT versioned):**
- `GET /healthz` - Liveness probe (is the API process alive?)
- `GET /readyz` - Readiness probe (is the API ready to serve traffic?)

**API Versioning (for future endpoints):**
- Base path: `/api/v1alpha1`
- Health endpoints are NOT under this path (standard K8s convention)

### Technology Stack (from Story 1.1)

| Technology | Version | Installed In Story 1.1 |
|------------|---------|------------------------|
| **Python** | 3.13 | ✓ |
| **FastAPI** | 0.127.1 | ✓ |
| **Uvicorn** | 0.40.0 | ✓ (via fastapi[standard]) |
| **pydantic-settings** | 2.x | ✓ |
| **structlog** | latest | ✓ |
| **pytest** | latest | ✓ |
| **pytest-asyncio** | latest | ✓ |
| **ruff** | latest | ✓ |

### Logging Configuration (structlog)

```python
# api/src/vintagestory_api/config.py
import structlog

def configure_logging(debug: bool = False):
    """Configure structlog for dev (colorful) or prod (JSON) output."""
    if debug:
        # Development: human-readable, colorful
        structlog.configure(
            processors=[
                structlog.stdlib.add_log_level,
                structlog.dev.ConsoleRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        # Production: JSON, machine-parseable
        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.stdlib.add_log_level,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
```

### Response Models

```python
# api/src/vintagestory_api/models/responses.py
from typing import Any, Literal
from pydantic import BaseModel

class ApiResponse(BaseModel):
    """Standard API response envelope."""
    status: Literal["ok", "error"]
    data: dict[str, Any] | None = None
    error: dict[str, Any] | None = None

class GameServerStatus(str, Enum):
    NOT_INSTALLED = "not_installed"
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"

class HealthData(BaseModel):
    """Health check response data."""
    api: str = "healthy"
    game_server: GameServerStatus

class ReadinessData(BaseModel):
    """Readiness check response data."""
    ready: bool = True
    checks: dict[str, bool] = {}
```

### Error Codes

```python
# api/src/vintagestory_api/models/errors.py
class ErrorCode:
    """Machine-readable error codes for API responses."""
    # Authentication
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"

    # Server
    SERVER_NOT_RUNNING = "SERVER_NOT_RUNNING"
    SERVER_NOT_INSTALLED = "SERVER_NOT_INSTALLED"

    # Mods
    MOD_NOT_FOUND = "MOD_NOT_FOUND"
    MOD_INCOMPATIBLE = "MOD_INCOMPATIBLE"

    # Config
    INVALID_CONFIG = "INVALID_CONFIG"

    # External
    EXTERNAL_API_ERROR = "EXTERNAL_API_ERROR"
```

### Health Router Implementation

```python
# api/src/vintagestory_api/routers/health.py
from fastapi import APIRouter
from vintagestory_api.models.responses import ApiResponse, HealthData, ReadinessData, GameServerStatus

router = APIRouter(tags=["Health"])

@router.get("/healthz")
async def health_check() -> ApiResponse:
    """
    Liveness probe - is the API process alive?

    Returns API health status and game server status.
    No authentication required (per K8s convention).
    """
    return ApiResponse(
        status="ok",
        data=HealthData(
            api="healthy",
            game_server=GameServerStatus.NOT_INSTALLED  # TODO: Replace with actual check
        ).model_dump()
    )

@router.get("/readyz")
async def readiness_check() -> ApiResponse:
    """
    Readiness probe - is the API ready to serve traffic?

    Returns True when all required services are initialized.
    No authentication required (per K8s convention).
    """
    return ApiResponse(
        status="ok",
        data=ReadinessData(
            ready=True,
            checks={"api": True}
        ).model_dump()
    )
```

### Main.py Structure

```python
# api/src/vintagestory_api/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
import structlog

from vintagestory_api.config import Settings, configure_logging
from vintagestory_api.routers import health

logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    settings = Settings()
    configure_logging(debug=settings.debug)
    logger.info("api_starting", debug_mode=settings.debug)
    yield
    logger.info("api_shutting_down")

app = FastAPI(
    title="VintageStory Server Manager",
    version="0.1.0",
    lifespan=lifespan,
)

# Health endpoints at root (NOT versioned - K8s convention)
app.include_router(health.router)

# API v1alpha1 endpoints will be added here
# from vintagestory_api.routers import server, mods, config
# api_v1 = APIRouter(prefix="/api/v1alpha1")
# api_v1.include_router(server.router, prefix="/server", tags=["Server"])
# app.include_router(api_v1)
```

### Test Examples

```python
# api/tests/test_health.py
import pytest
from fastapi.testclient import TestClient
from vintagestory_api.main import app

client = TestClient(app)

def test_healthz_returns_200():
    response = client.get("/healthz")
    assert response.status_code == 200

def test_healthz_follows_envelope_format():
    response = client.get("/healthz")
    data = response.json()
    assert data["status"] == "ok"
    assert "data" in data
    assert data["data"]["api"] == "healthy"

def test_healthz_includes_game_server_status():
    response = client.get("/healthz")
    data = response.json()
    assert "game_server" in data["data"]
    assert data["data"]["game_server"] in ["not_installed", "stopped", "starting", "running", "stopping"]

def test_readyz_returns_200():
    response = client.get("/readyz")
    assert response.status_code == 200

def test_readyz_includes_ready_status():
    response = client.get("/readyz")
    data = response.json()
    assert data["status"] == "ok"
    assert data["data"]["ready"] == True

def test_health_endpoints_require_no_auth():
    # No X-API-Key header, should still work
    response = client.get("/healthz")
    assert response.status_code == 200
    response = client.get("/readyz")
    assert response.status_code == 200
```

### Previous Story Intelligence (from Story 1.1)

**Learnings to Apply:**
1. **TSConfig requires explicit jsx setting** - Already configured in 1.1, not relevant for backend
2. **Use Pydantic v2 patterns** - Use `model_config = ConfigDict(...)` not class Config
3. **Use sonner instead of toast** - Frontend only, not relevant here
4. **Pin tool versions** - uv 0.9.18, bun 1.3.5 already pinned in .mise.toml

**Files Created in 1.1 (available for this story):**
- `api/src/vintagestory_api/main.py` - Needs updating with health router
- `api/src/vintagestory_api/config.py` - Needs structlog configuration
- `api/src/vintagestory_api/models/__init__.py` - Needs response models
- `api/src/vintagestory_api/routers/__init__.py` - Needs health router
- `api/tests/conftest.py` - Ready for test fixtures

**Pattern from 1.1:** Files are created as placeholders, ready to populate with real code.

### Project Structure Notes

**Alignment with unified project structure:**
- All new files go in established directories from Story 1.1
- Response models in `models/responses.py` (new file)
- Error codes in `models/errors.py` (new file)
- Health router in `routers/health.py` (new file)
- Tests in `tests/test_health.py` (new file)

**No conflicts detected** - Following Architecture doc exactly.

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#API-Communication-Patterns]
- [Source: _bmad-output/planning-artifacts/architecture.md#Response-Envelope-Format]
- [Source: _bmad-output/planning-artifacts/architecture.md#Logging-Configuration]
- [Source: _bmad-output/planning-artifacts/architecture.md#Backend-Structure]
- [Source: _bmad-output/planning-artifacts/epics.md#Story-1.2]
- [Source: _bmad-output/planning-artifacts/prd.md#Health-Observability]
- [Source: _bmad-output/implementation-artifacts/1-1-initialize-development-environment-and-project-structure.md]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- Fixed UP035 linting error: Changed `from typing import AsyncIterator` to `from collections.abc import AsyncIterator` per ruff recommendation

### Completion Notes List

- **Task 1**: Created `ApiResponse` envelope model, `ErrorCode` constants, `GameServerStatus` enum, `HealthData` and `ReadinessData` models
- **Task 2**: Added `configure_logging()` function to config.py with dev/prod mode detection via VS_DEBUG
- **Task 3**: Created health router with `/healthz` and `/readyz` endpoints, game server status mocked as `not_installed`
- **Task 4**: Updated main.py with lifespan handler, CORS middleware, and API v1alpha1 versioning structure (commented placeholder)
- **Task 5**: Created comprehensive test suite with 10 tests covering all acceptance criteria - all passing
- **Task 6**: Verified dev server starts correctly, endpoints return expected responses, structured logging works

### File List

**New Files:**
- api/src/vintagestory_api/models/responses.py
- api/src/vintagestory_api/models/errors.py
- api/src/vintagestory_api/routers/health.py
- api/tests/test_health.py

**Modified Files:**
- api/src/vintagestory_api/main.py (added lifespan, health router, CORS)
- api/src/vintagestory_api/config.py (added configure_logging function)
- api/src/vintagestory_api/models/__init__.py (added exports)
- api/src/vintagestory_api/routers/__init__.py (added health export)

### Change Log

- 2025-12-26: Implemented Story 1.2 - Backend API skeleton with health endpoints (/healthz, /readyz), structured logging, and comprehensive test suite
- 2025-12-26: Code Review - Fixed 5 issues (M1-M4 medium, L1-L2 low): removed overly permissive CORS, added envelope tests, removed duplicate Settings, added response_model decorators, fixed ReadinessData default, added __all__ exports

## Senior Developer Review (AI)

**Reviewer:** Claude Opus 4.5
**Date:** 2025-12-26
**Outcome:** ✅ APPROVED

### Review Summary

All acceptance criteria verified as implemented. Code quality is solid with good test coverage (12 tests passing).

### Issues Found & Fixed

| ID | Severity | Issue | Resolution |
|----|----------|-------|------------|
| M1 | MEDIUM | CORS `allow_origins=["*"]` with credentials | User removed manually |
| M2 | MEDIUM | No tests for error envelope format | Added `TestApiResponseEnvelope` class |
| M3 | MEDIUM | Duplicate Settings instantiation | Removed module-level instance from config.py |
| M4 | MEDIUM | Missing `response_model` on endpoints | Added to both `/healthz` and `/readyz` |
| L1 | LOW | `ReadinessData.ready` defaulted True | Changed default to False, explicitly set True |
| L2 | LOW | Missing `__all__` in responses.py | Added exports list |

### Verification

- ✅ 12/12 tests passing
- ✅ Ruff linter clean
- ✅ All ACs implemented
- ✅ Architecture compliance verified

