# Story 1.1: Initialize Development Environment and Project Structure

Status: done

## Story

As a **developer**,
I want **a properly configured development environment with project scaffolding**,
So that **I can begin implementing features with consistent tooling across the team**.

## Acceptance Criteria

### AC1: mise Environment Setup
**Given** a fresh clone of the repository
**When** I run `mise trust && mise install`
**Then** Python 3.13, uv, and Bun are installed at the pinned versions
**And** a `.mise.toml` file exists at the project root with tool versions specified

### AC2: Backend Scaffolding
**Given** the development environment is set up
**When** I navigate to the `api/` directory
**Then** a `pyproject.toml` exists with project name `vintagestory-api`
**And** dependencies include `fastapi[standard]`, `httpx`, `pydantic-settings`, `structlog`
**And** dev dependencies include `pytest`, `pytest-asyncio`, `ruff`, `respx`

### AC3: Frontend Scaffolding
**Given** the development environment is set up
**When** I navigate to the `web/` directory
**Then** a `package.json` exists with React 19.2 and TypeScript configured
**And** Tailwind CSS v4 is installed and configured
**And** shadcn/ui is initialized with the project's component configuration

### AC4: Project Structure
**Given** the project structure is initialized
**When** I examine the repository root
**Then** the directory structure matches the Architecture specification
**And** `.gitignore` excludes appropriate files (node_modules, .venv, __pycache__, data/)

## Tasks / Subtasks

- [x] Task 1: Create mise configuration (AC: #1)
  - [x] 1.1: Create `.mise.toml` with Python 3.13, uv (pin to latest), and Bun (pin to latest)
  - [x] 1.2: Set VIRTUAL_ENV path to `api/.venv`
  - [x] 1.3: Document mise install command in README

- [x] Task 2: Initialize Backend API (AC: #2)
  - [x] 2.1: Create `api/` directory
  - [x] 2.2: Run `uv init --name vintagestory-api --python 3.13` inside api/
  - [x] 2.3: Add production dependencies: `fastapi[standard]`, `httpx`, `pydantic-settings`, `structlog`
  - [x] 2.4: Add dev dependencies: `pytest`, `pytest-asyncio`, `ruff`, `respx`
  - [x] 2.5: Create initial source structure: `api/src/vintagestory_api/__init__.py`, `main.py`
  - [x] 2.6: Create placeholder directories: `routers/`, `services/`, `models/`, `middleware/`
  - [x] 2.7: Create `api/tests/` directory with `conftest.py`

- [x] Task 3: Initialize Frontend Web App (AC: #3)
  - [x] 3.1: Run `bun create vite web -- --template react-ts` from project root
  - [x] 3.2: Update React to 19.2: `bun add react@19.2 react-dom@19.2`
  - [x] 3.3: Update React types: `bun add -D @types/react@19 @types/react-dom@19`
  - [x] 3.4: Install Tailwind CSS v4: `bun add -D tailwindcss @tailwindcss/vite`
  - [x] 3.5: Configure vite.config.ts with Tailwind plugin and @ alias
  - [x] 3.6: Update tsconfig.json and tsconfig.app.json with path aliases
  - [x] 3.7: Replace CSS directives with `@import "tailwindcss";` in index.css
  - [x] 3.8: Initialize shadcn/ui: `bunx shadcn@canary init` (select new-york style)
  - [x] 3.9: Add initial components: button, card, toast

- [x] Task 4: Create Project Structure (AC: #4)
  - [x] 4.1: Create root directory structure per Architecture spec
  - [x] 4.2: Update `.gitignore` with comprehensive exclusions
  - [x] 4.3: Create `data/.gitkeep` for volume mount placeholder
  - [x] 4.4: Create placeholder `docker-compose.yaml` and `docker-compose.dev.yaml`
  - [x] 4.5: Create placeholder `Dockerfile`
  - [x] 4.6: Create `.env.example` with documented environment variables

- [x] Task 5: Verify Setup (AC: #1, #2, #3, #4)
  - [x] 5.1: Run `mise install` and verify tool versions
  - [x] 5.2: Run `cd api && uv run python -c "import fastapi; print(fastapi.__version__)"` to verify backend deps
  - [x] 5.3: Run `cd web && bun run build` to verify frontend builds
  - [x] 5.4: Verify directory structure matches Architecture specification

## Dev Notes

### CRITICAL: Technology Versions (Research as of 2025-12-26)

| Technology | Version | Notes |
|------------|---------|-------|
| **mise** | 2025.12.13 | Latest stable release |
| **Python** | 3.13 | Specified in Architecture |
| **uv** | latest | Managed by mise |
| **Bun** | latest | Managed by mise |
| **FastAPI** | 0.127.0 | Latest stable (supports Python 3.13+) |
| **Uvicorn** | 0.40.0 | Included via fastapi[standard] |
| **React** | 19.2 | **SECURITY FIX** - must be exactly 19.2 |
| **Vite** | 7.x | Current stable |
| **Tailwind CSS** | v4 | Uses @tailwindcss/vite plugin |
| **shadcn/ui** | canary | Required for Tailwind v4 + React 19 support |

### Architecture Compliance Requirements

**Backend Structure (MUST follow exactly):**
```
api/
├── pyproject.toml
├── uv.lock
├── src/
│   └── vintagestory_api/
│       ├── __init__.py
│       ├── main.py              # FastAPI app entry
│       ├── config.py            # pydantic-settings (placeholder)
│       ├── routers/
│       │   └── __init__.py
│       ├── services/
│       │   └── __init__.py
│       ├── models/
│       │   └── __init__.py
│       └── middleware/
│           └── __init__.py
└── tests/
    └── conftest.py
```

**Frontend Structure (MUST follow exactly):**
```
web/
├── package.json
├── bun.lockb
├── vite.config.ts
├── tsconfig.json
├── index.html
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── api/                     # Placeholder
│   ├── components/
│   │   └── ui/                  # shadcn/ui components
│   ├── features/                # Placeholder
│   ├── hooks/                   # Placeholder
│   ├── contexts/                # Placeholder
│   ├── lib/
│   │   └── utils.ts             # shadcn/ui utilities
│   └── styles/
│       └── index.css            # Tailwind imports
└── public/
```

**Root Structure:**
```
vintagestory-server/
├── .mise.toml
├── .gitignore
├── README.md
├── LICENSE (if adding)
├── docker-compose.yaml          # Placeholder
├── docker-compose.dev.yaml      # Placeholder
├── Dockerfile                   # Placeholder
├── .env.example
├── api/
├── web/
├── data/
│   └── .gitkeep
└── agentdocs/                   # Already exists
```

### mise Configuration (exact content)

```toml
[tools]
python = "3.13"
uv = "latest"
bun = "latest"

[env]
VIRTUAL_ENV = "{{config_root}}/api/.venv"
```

### vite.config.ts (exact content for Tailwind v4)

```typescript
import path from 'path';
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
```

### tsconfig.json additions

The `tsconfig.json` needs path aliases (Vite 7 uses a single tsconfig):
```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

### index.css (Tailwind v4 style)

```css
@import "tailwindcss";
```

### .gitignore additions

```gitignore
# Dependencies
node_modules/
.venv/
__pycache__/
*.pyc

# Build outputs
dist/
build/
*.egg-info/

# IDE
.idea/
.vscode/
*.swp

# Environment
.env
.env.local

# Data (runtime)
data/
!data/.gitkeep

# Logs
*.log
logs/

# OS
.DS_Store
Thumbs.db

# Testing
.coverage
htmlcov/
.pytest_cache/

# Lock files managed by package managers
# uv.lock - tracked
# bun.lockb - tracked
```

### .env.example content

```bash
# VintageStory Server Manager Configuration

# API Authentication (REQUIRED)
VS_API_KEY_ADMIN=change-me-to-a-secure-random-string

# Optional: Read-only monitoring key
# VS_API_KEY_MONITOR=optional-monitor-key

# Optional: Game server version (default: stable)
# VS_GAME_VERSION=1.21.3

# Optional: Enable debug logging
# VS_DEBUG=false
```

### shadcn/ui Initialization Answers

When running `bunx shadcn@canary init`, select:
- Style: **new-york** (default being deprecated)
- Base color: Use defaults or customize for Catppuccin later
- CSS variables: **Yes**

### Project Structure Notes

- **Alignment**: Full alignment with unified project structure per Architecture doc
- **No conflicts detected**: All paths, modules, and naming conventions match

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Starter-Template-Evaluation]
- [Source: _bmad-output/planning-artifacts/architecture.md#Project-Structure-Boundaries]
- [Source: _bmad-output/planning-artifacts/architecture.md#Backend-Initialization]
- [Source: _bmad-output/planning-artifacts/architecture.md#Frontend-Initialization]
- [Source: _bmad-output/planning-artifacts/epics.md#Story-1.1]
- [Web: mise releases](https://github.com/jdx/mise/releases)
- [Web: FastAPI on PyPI](https://pypi.org/project/fastapi/)
- [Web: shadcn/ui Tailwind v4](https://ui.shadcn.com/docs/tailwind-v4)
- [Web: shadcn/ui Vite Installation](https://ui.shadcn.com/docs/installation/vite)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- Fixed TSConfig missing `jsx: "react-jsx"` setting causing build failure
- Used `sonner` instead of deprecated `toast` component for shadcn/ui
- Pinned uv (0.9.18) and bun (1.3.5) versions instead of `latest` per user request

### Completion Notes List

- **Task 1**: Created `.mise.toml` with Python 3.13, uv 0.9.18, bun 1.3.5; documented in README
- **Task 2**: Initialized FastAPI backend with src layout, all dependencies installed (FastAPI 0.127.1)
- **Task 3**: Created React 19.2 frontend with Vite 7.x, Tailwind CSS v4, shadcn/ui (button, card, sonner)
- **Task 4**: Created project structure with docker placeholders, .env.example, data/.gitkeep
- **Task 5**: Verified all tools install, backend imports work, frontend builds successfully

### File List

**New Files:**
- .mise.toml
- .env.example
- Dockerfile
- docker-compose.yaml
- docker-compose.dev.yaml
- data/.gitkeep
- api/pyproject.toml
- api/uv.lock
- api/.python-version
- api/src/vintagestory_api/__init__.py
- api/src/vintagestory_api/main.py
- api/src/vintagestory_api/config.py
- api/src/vintagestory_api/routers/__init__.py
- api/src/vintagestory_api/services/__init__.py
- api/src/vintagestory_api/models/__init__.py
- api/src/vintagestory_api/middleware/__init__.py
- api/tests/conftest.py
- web/package.json
- web/bun.lock
- web/vite.config.ts
- web/tsconfig.json
- web/index.html
- web/components.json
- web/src/main.tsx
- web/src/App.tsx
- web/src/lib/utils.ts
- web/src/styles/index.css
- web/src/components/ui/button.tsx
- web/src/components/ui/card.tsx
- web/src/components/ui/sonner.tsx
- web/src/api/.gitkeep
- web/src/hooks/.gitkeep
- web/src/contexts/.gitkeep
- web/src/features/.gitkeep

**Modified Files:**
- README.md (added Development Setup section)
- .gitignore (added node_modules, data/ exclusions)
- api/src/vintagestory_api/config.py (code review: updated to Pydantic v2 model_config pattern)

### Change Log

- 2025-12-26: Implemented Story 1.1 - Full development environment setup with mise, Python/FastAPI backend, React/Vite frontend
- 2025-12-26: Code review fixes - Updated pydantic-settings to use model_config, added .gitkeep to placeholder directories

