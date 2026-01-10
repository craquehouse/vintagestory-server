# Starter Template Evaluation

## Primary Technology Domains

**Backend API:** Python 3.12 + FastAPI + uv (API server with WebSocket support)
**Frontend SPA:** React 19.2 + Vite + TypeScript + Bun + shadcn/ui (Admin web interface)

## Development Environment: mise

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

## Starter Options Considered

### Backend (FastAPI)

| Option                        | Evaluation                                                       |
| ----------------------------- | ---------------------------------------------------------------- |
| uv-fastapi-example (Official) | ✅ Selected - Official Astral pattern, minimal, production-ready |
| py-fastapi-starter            | Modular but includes PostgreSQL/Alembic we don't need            |
| Full starter templates        | Over-engineered for our no-database requirement                  |

### Frontend (React + shadcn/ui)

| Option                    | Evaluation                                          |
| ------------------------- | --------------------------------------------------- |
| Official shadcn/ui + Vite | ✅ Selected - Documented, Tailwind v4, full control |
| react-ts-shadcn-starter   | Good but third-party maintenance                    |
| vite-react-ts-shadcn-ui   | Includes extras (Husky, etc.) we may not need       |

## Selected Approach: Official Patterns

**Rationale:**

- Official documentation ensures long-term maintenance and compatibility
- Minimal starting point avoids removing unwanted dependencies
- Full control over project structure from day one
- Both patterns are actively maintained by their ecosystems
- mise ensures all developers use identical tool versions

## Backend Initialization

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

## Frontend Initialization

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

## Architectural Decisions Provided by Starters

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
