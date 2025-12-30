# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## Technology Stack & Versions

| Component | Version | Notes |
|-----------|---------|-------|
| Python | >= 3.12 | Use minimum version, not exact pin |
| FastAPI | 0.127.1+ | Includes Uvicorn via `fastapi[standard]` |
| React | 19.2 | Security-patched version |
| TypeScript | 5.x | Strict mode enabled |
| Bun | 1.3.5 | Frontend runtime and package manager |
| uv | 0.9.18+ | Python package management |
| Tailwind CSS | v4 | CSS variables approach |
| TanStack Query | v5 | Server state management |
| structlog | latest | Structured logging |

**Base Container:** `mcr.microsoft.com/dotnet/runtime:8.0.22-noble-amd64`
- Ubuntu 24.04 Noble with .NET 8 (required for VintageStory server)
- Python 3.12 available via apt

---

## Available MCPs for Agents

All agents have access to three Model Context Protocol (MCP) tools for enhanced capabilities:

### 1. Playwright (Browser Automation)
**Purpose:** Real-world testing, UI validation, and browser automation

**When to use:**
- Testing the web UI end-to-end
- Validating user flows across multiple pages
- Capturing screenshots for documentation
- Debugging frontend issues in a real browser environment
- Verifying responsive behavior

**Key capabilities:**
- Navigate to URLs and interact with pages
- Fill forms, click buttons, and test UI components
- Take screenshots and accessibility snapshots
- Monitor console messages and network requests
- Test across different viewport sizes

**Best practices:**
- Use accessibility snapshots over screenshots when testing UI structure
- Clean up browser sessions after testing
- Use meaningful element descriptions when interacting with the page

### 2. GitHub Code Search (`grep_searchGitHub`)
**Purpose:** Find real-world code examples from public GitHub repositories

**When to use:**
- Learning how to use unfamiliar APIs or libraries
- Finding production-ready examples and best practices
- Understanding how others integrate similar technologies
- Looking for patterns in real codebases (not tutorials)

**Key capabilities:**
- Search for literal code patterns (not keywords)
- Filter by language, repository, or file path
- Support for regex patterns for flexible matching
- Access to over 1 million public repositories

**Best practices:**
- Search for actual code patterns, not natural language queries
- Use language filters to narrow results
- Look for well-maintained repositories with good documentation
- Examples: `'useState('`, `'from("fastapi")'`, `'export function'`

### 3. Context7 (Smart Documentation Search)
**Purpose:** Access up-to-date documentation for popular libraries and frameworks

**When to use:**
- Looking up API references and code examples
- Understanding library configuration options
- Finding best practices for specific technologies
- Getting conceptual guides and architectural information

**Available datasources include:**
- **Frontend:** React, Next.js, Tailwind CSS, shadcn/ui, TanStack Query
- **Backend:** FastAPI, Python web frameworks
- **Build tools:** Vite, esbuild, webpack
- **Testing:** Vitest, Playwright, Testing Library
- **And many more** - resolve library IDs dynamically

**Best practices:**
- Use `mode='code'` for API references and examples (default)
- Use `mode='info'` for conceptual guides and architecture
- Use `topic` parameter to focus documentation on specific areas
- Adjust `tokensNum` based on how much context you need (1000-50000)

**Example workflow:**
```python
# Step 1: Resolve the library ID
context7_resolve-library-id(libraryName="fastapi")

# Step 2: Get documentation (if not using a known library ID)
context7_get-library-docs(
    context7CompatibleLibraryID="/tiangolo/fastapi",
    topic="middleware",  # optional: focus on a specific topic
    mode="code"  # optional: "code" (default) or "info"
)
```

**Key advantages:**
- Always up-to-date documentation (unlike cached search results)
- Optimized for LLM consumption with clean context
- Code-focused by default, perfect for implementation questions
- Supports pagination for comprehensive research

---

## Critical Implementation Rules

### 1. Tests Must Accompany Implementation

**Every task that adds functionality must include its tests before marking complete.**

This is non-negotiable. Tests are not a separate phase - they are part of implementation.

**Pattern to follow:**
```
Task 1: Implement feature A + tests
Task 2: Implement feature B + tests
```

**Anti-pattern to avoid:**
```
Task 1: Implement feature A
Task 2: Implement feature B
Task 3: Write tests  <- TOO LATE
```

**Why:** Code review should verify implementation quality, not discover missing tests. Tests written alongside code catch design issues early.

### 2. A Task is Not Complete Until Tests Pass

Do not mark a task as complete if:
- Tests are failing
- Implementation is partial
- You encountered unresolved errors
- Test coverage for the new functionality is missing

### 3. API Response Envelope

All API endpoints must use the standard envelope:

```python
# Success
{"status": "ok", "data": {...}}

# Error (FastAPI Standard)
{"detail": {"code": "ERROR_CODE", "message": "Human readable"}}
```

**Note:** Error responses follow FastAPI's standard `detail` pattern for HTTPExceptions.
This avoids requiring custom exception handlers. The `detail` field contains structured
error data with `code` and `message` fields, providing the same information
as a custom envelope would.

### 4. JSON Field Naming Boundary

- **API (Python):** snake_case
- **Frontend (TypeScript):** camelCase
- **Transform at:** API client boundary only (`web/src/api/client.ts`)

### 5. State Management Boundaries

| State Type | Tool | Examples |
|------------|------|----------|
| Server state (from API) | TanStack Query | mods, server status, config |
| UI-only state | React Context | theme, sidebar collapsed |

**Never mix these.** If data comes from the API, use TanStack Query.

### 6. Atomic File Writes

All state persistence must use the temp-file-then-rename pattern:

```python
temp = path.with_suffix('.tmp')
temp.write_text(content)
temp.rename(path)  # atomic on POSIX
```

This prevents corruption if the process crashes mid-write.

### 7. Version Specifications in Architecture

When documenting or requiring versions:
- **Use minimum versions** (e.g., `Python >= 3.12`) unless there's a specific reason to pin
- **Document rationale** for any exact version pins
- **Consider external dependencies** when specifying infrastructure (e.g., VintageStory requires .NET)

---

## Security Patterns

These patterns were established in Epic 2 and must be followed for all security-related code.

### 1. DEBUG Mode Gating for Test Endpoints

Test or development-only endpoints MUST be gated behind `VS_DEBUG=true`:

```python
from vintagestory_api.config import get_settings

settings = get_settings()
if settings.debug:
    app.include_router(test_router, prefix="/api/v1alpha1")
```

**Why:** Prevents test endpoints from being exposed in production.

### 2. Timing-Safe API Key Comparison

Always use `secrets.compare_digest` for API key validation:

```python
import secrets

def verify_key(provided: str, expected: str) -> bool:
    return secrets.compare_digest(provided.encode(), expected.encode())
```

**Why:** Prevents timing attacks that could leak information about valid keys.

### 3. Never Log Sensitive Data

API keys, passwords, and tokens must NEVER appear in logs:

```python
# WRONG - logs the actual key
logger.warning(f"Invalid API key: {api_key}")

# CORRECT - logs metadata only
logger.warning("Invalid API key attempt",
    extra={"ip": client_ip, "key_prefix": api_key[:8] + "..."})
```

### 4. Proxy-Aware Client IP Logging

When logging client IPs (e.g., for failed auth), check proxy headers:

```python
def get_client_ip(request: Request) -> str:
    """Get real client IP, accounting for reverse proxies."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    return request.client.host if request.client else "unknown"
```

### 5. Role-Based Access Control Pattern

Use FastAPI dependency injection for role checks:

```python
from vintagestory_api.middleware.auth import get_current_user
from vintagestory_api.middleware.permissions import require_admin

# Read endpoint - any authenticated user
@router.get("/data")
async def get_data(role: str = Depends(get_current_user)):
    pass

# Write endpoint - Admin only
@router.post("/data")
async def create_data(role: str = Depends(require_admin)):
    pass
```

---

## Logging Conventions

### Configuration

Logging is configured via environment variables:
- `VS_DEBUG=true` - Enable debug mode (colorful console output)
- `VS_LOG_LEVEL` - Override log level (DEBUG, INFO, WARNING, ERROR)

Default behavior:
- **Dev mode** (`VS_DEBUG=true`): DEBUG level, colorful ConsoleRenderer
- **Prod mode** (`VS_DEBUG=false`): INFO level, JSON output for machine parsing

### Standards

1. **Always use ISO 8601 timestamps** - Configured automatically by structlog
2. **Use structured logging** - Key=value pairs, not string interpolation:

```python
# CORRECT - structured key=value
logger.info("server_starting", version="1.19.8", port=8080)

# WRONG - string interpolation
logger.info(f"Server version {version} starting on port {port}")
```

3. **Use event names as first argument** - Lowercase with underscores:
   - `api_starting`, `server_stopped`, `download_complete`

4. **Never log sensitive data**:
```python
# WRONG
logger.warning(f"Auth failed for key: {api_key}")

# CORRECT
logger.warning("auth_failed", key_prefix=api_key[:8] + "...")
```

5. **Log levels**:
   - `DEBUG` - Detailed diagnostic info (dev only)
   - `INFO` - Normal operations (startup, shutdown, requests)
   - `WARNING` - Recoverable issues (timeouts, retries)
   - `ERROR` - Failures requiring attention

---

## Code Review Checklist

Before marking a task complete, verify:

- [ ] Tests written alongside implementation (not batched at end)
- [ ] All tests passing
- [ ] Security patterns applied (DEBUG gating, timing-safe comparison, no sensitive logging)
- [ ] Error responses use standard envelope format
- [ ] No hardcoded secrets or credentials

---

## Code Patterns

### Backend (Python)

**File naming:** snake_case (`mod_service.py`)
**Classes:** PascalCase (`ModService`)
**Functions/variables:** snake_case (`get_mod_details()`)
**Constants:** SCREAMING_SNAKE (`MAX_RETRIES`)

**Error handling:**
```python
from vintagestory_api.models.errors import ErrorCode

raise HTTPException(
    status_code=404,
    detail={
        "code": ErrorCode.MOD_NOT_FOUND,
        "message": f"Mod '{slug}' not found",
    }
)
```

### Frontend (TypeScript)

**File naming:** kebab-case (`mod-card.tsx`)
**Components:** PascalCase (`ModCard`)
**Hooks:** camelCase with `use` prefix (`useServerStatus`)
**Booleans:** always `is` prefix (`isLoading`, `isConnected`)

**Query keys:**
```typescript
const queryKeys = {
  mods: {
    all: ["mods"] as const,
    detail: (slug: string) => ["mods", slug] as const,
  },
};
```

---

## Anti-Patterns to Avoid

| Avoid | Do Instead |
|-------|------------|
| Writing tests after all features complete | Write tests with each feature |
| Storing API data in React Context | Use TanStack Query |
| `tests/` folder in `web/` | Co-locate tests with components |
| Generic error messages | Use error codes + descriptive messages |
| Exact version pins without rationale | Use minimum versions with ranges |
| Mixing snake_case in frontend | Transform at API boundary |

---

## Project Structure Quick Reference

```
vintagestory-server/
├── api/                    # FastAPI backend
│   ├── src/vintagestory_api/
│   │   ├── routers/        # HTTP endpoints
│   │   ├── services/       # Business logic
│   │   ├── models/         # Pydantic models
│   │   └── middleware/     # Auth, etc.
│   └── tests/              # Backend tests
├── web/                    # React frontend
│   └── src/
│       ├── api/            # API client
│       ├── components/     # UI components
│       ├── features/       # Feature modules
│       ├── hooks/          # Custom hooks
│       └── contexts/       # UI state contexts
├── Dockerfile              # Multi-stage build
└── docker-compose.yaml     # Deployment
```

---

## Development Commands

**ALWAYS use `just` commands. NEVER use raw `mise exec` commands.**

All recipes accept optional arguments for flexibility:

```bash
# Testing - ALWAYS use just for tests
just test                                # Run all tests (api + web)
just test-api                            # Run all API tests
just test-api -k "restart"               # Run tests matching pattern
just test-api tests/test_server.py -xvs  # Run specific file, verbose
just test-web                            # Run all web tests

# Validation
just check                               # Full validation (lint + typecheck + test)
just lint                                # Run all linters
just lint-api --fix                      # Lint with auto-fix
just typecheck                           # Run all type checks

# Development
just dev-api                             # Start API dev server
just dev-api --port 8001                 # Dev server on custom port
just dev-web                             # Start web dev server
just install                             # Install all dependencies
just format                              # Format all code
```

Run `just` with no arguments to see all available commands.

**Why:** Prevents tooling confusion (e.g., `bun test` vs `bun run test`). All commands use correct tool versions via mise. Variadic args enable specific test file/pattern targeting without bypassing `just`.

---

## References

- Full architecture: `_bmad-output/planning-artifacts/architecture.md`
- Epic breakdown: `_bmad-output/planning-artifacts/epics.md`
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- **VintageStory server troubleshooting:** `agentdocs/vs-server-troubleshooting.md` - Known quirks, path resolution issues, config file behaviors

---

_Last updated: 2025-12-29 (Added VintageStory troubleshooting reference)_
