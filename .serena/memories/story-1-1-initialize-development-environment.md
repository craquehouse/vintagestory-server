# Story 1.1: Initialize Development Environment and Project Structure

Status: done

## Summary
Set up development environment with mise (Python 3.13, uv, Bun), FastAPI backend scaffolding, and React/Vite frontend with Tailwind CSS v4 and shadcn/ui.

## Key Decisions
- mise for tool version management (uv 0.9.18, bun 1.3.5)
- FastAPI 0.127.1 with pydantic-settings, structlog
- React 19.2 with Vite 7.x, Tailwind CSS v4, shadcn/ui canary
- src layout for Python (`api/src/vintagestory_api/`)

## Files Created
- .mise.toml, .env.example, Dockerfile, docker-compose.yaml
- api/pyproject.toml, api/src/vintagestory_api/{main.py, config.py}
- api/src/vintagestory_api/{routers,services,models,middleware}/__init__.py
- web/package.json, vite.config.ts, src/{App.tsx, main.tsx}
- web/src/components/ui/{button,card,sonner}.tsx

## Commands
```bash
mise trust && mise install
cd api && uv run python -c "import fastapi"
cd web && bun run build
```
