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

# Error
{"status": "error", "error": {"code": "ERROR_CODE", "message": "Human readable"}}
```

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

## References

- Full architecture: `_bmad-output/planning-artifacts/architecture.md`
- Epic breakdown: `_bmad-output/planning-artifacts/epics.md`
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml`

---

_Last updated: 2025-12-27 (Epic 1 Retrospective)_
