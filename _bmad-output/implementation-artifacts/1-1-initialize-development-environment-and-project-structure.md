# Story 1.1: Initialize Development Environment and Project Structure

Status: ready-for-dev

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

- [ ] Task 1: Create mise configuration (AC: #1)
  - [ ] 1.1: Create `.mise.toml` with Python 3.13, uv (pin to latest), and Bun (pin to latest)
  - [ ] 1.2: Set VIRTUAL_ENV path to `api/.venv`
  - [ ] 1.3: Document mise install command in README

- [ ] Task 2: Initialize Backend API (AC: #2)
  - [ ] 2.1: Create `api/` directory
  - [ ] 2.2: Run `uv init --name vintagestory-api --python 3.13` inside api/
  - [ ] 2.3: Add production dependencies: `fastapi[standard]`, `httpx`, `pydantic-settings`, `structlog`
  - [ ] 2.4: Add dev dependencies: `pytest`, `pytest-asyncio`, `ruff`, `respx`
  - [ ] 2.5: Create initial source structure: `api/src/vintagestory_api/__init__.py`, `main.py`
  - [ ] 2.6: Create placeholder directories: `routers/`, `services/`, `models/`, `middleware/`
  - [ ] 2.7: Create `api/tests/` directory with `conftest.py`

- [ ] Task 3: Initialize Frontend Web App (AC: #3)
  - [ ] 3.1: Run `bun create vite web -- --template react-ts` from project root
  - [ ] 3.2: Update React to 19.2: `bun add react@19.2 react-dom@19.2`
  - [ ] 3.3: Update React types: `bun add -D @types/react@19 @types/react-dom@19`
  - [ ] 3.4: Install Tailwind CSS v4: `bun add -D tailwindcss @tailwindcss/vite`
  - [ ] 3.5: Configure vite.config.ts with Tailwind plugin and @ alias
  - [ ] 3.6: Update tsconfig.json and tsconfig.app.json with path aliases
  - [ ] 3.7: Replace CSS directives with `@import "tailwindcss";` in index.css
  - [ ] 3.8: Initialize shadcn/ui: `bunx shadcn@canary init` (select new-york style)
  - [ ] 3.9: Add initial components: button, card, toast

- [ ] Task 4: Create Project Structure (AC: #4)
  - [ ] 4.1: Create root directory structure per Architecture spec
  - [ ] 4.2: Update `.gitignore` with comprehensive exclusions
  - [ ] 4.3: Create `data/.gitkeep` for volume mount placeholder
  - [ ] 4.4: Create placeholder `docker-compose.yaml` and `docker-compose.dev.yaml`
  - [ ] 4.5: Create placeholder `Dockerfile`
  - [ ] 4.6: Create `.env.example` with documented environment variables

- [ ] Task 5: Verify Setup (AC: #1, #2, #3, #4)
  - [ ] 5.1: Run `mise install` and verify tool versions
  - [ ] 5.2: Run `cd api && uv run python -c "import fastapi; print(fastapi.__version__)"` to verify backend deps
  - [ ] 5.3: Run `cd web && bun run build` to verify frontend builds
  - [ ] 5.4: Verify directory structure matches Architecture specification

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
| **Vite** | 6.x | Current stable |
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

Both `tsconfig.json` and `tsconfig.app.json` need:
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

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

