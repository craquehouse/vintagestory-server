# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Custom VintageStory game server infrastructure with three components:

1. **Docker Image** - VintageStory dedicated server container
2. **API Server** (Python/FastAPI) - Game control, configuration, and mod management
3. **Web UI** (Node.js) - Admin interface for server management

## Development Methodology: BMad

This project uses the BMad method for structured AI-assisted development:

1. **Stories** live in `docs/stories/` - Each feature is a standalone story file
2. **Tasks** break down stories into implementation steps
3. **Checklist-driven** - Stories contain acceptance criteria that must be verified
4. **Incremental commits** - Commit after each task completion

When implementing features:
- Read the story file completely before starting
- Work through tasks sequentially
- Mark checklist items as complete in the story file
- Create checkpoint commits at logical boundaries

## Architecture

```
vintagestory-server/
├── docker/              # Dockerfile and container configs
├── api/                 # FastAPI backend
│   ├── routers/         # API route handlers
│   ├── services/        # Business logic
│   └── models/          # Pydantic models
├── web/                 # Node.js frontend
└── agentdocs/           # Reference documentation for AI agents
```

### Component Interaction

```
[Web UI] <--HTTP--> [FastAPI] <--Docker API/RCON--> [VS Server Container]
                         |
                    [Config Files]
                    [Mod Storage]
```

### External APIs

The VintageStory mod database API is documented in `agentdocs/modstoryapi.md`. Key endpoints:
- `GET https://mods.vintagestory.at/api/mod/{slug}` - Mod details and releases
- `GET https://mods.vintagestory.at/download?fileid={id}` - Download mod files
- Releases are ordered newest-first; `releases[0]` is always latest
- Status codes are strings (`"200"`), not integers

## Commands

### API Server (Python/FastAPI)
```bash
cd api
uv sync --dev                          # Install dependencies
uvicorn main:app --reload              # Development server
pytest                                  # Run all tests
pytest tests/test_mods.py::test_name   # Single test
ruff check .                           # Lint
ruff format .                          # Format
uv run pyright src/                    # Type check (strict mode)
```

### Web UI (Node.js)
```bash
cd web
npm install
npm run dev                            # Development server
npm test                               # Run tests
npm run lint                           # Lint
```

### Docker
```bash
docker build -t vintagestory-server ./docker
docker compose up -d                   # Start stack
docker compose logs -f vintagestory    # Follow game logs
```

## Key Conventions

- **API responses** use consistent envelope: `{"status": "ok/error", "data": {...}}`
- **WebSocket** at `/ws/console` for real-time game console streaming
- **Mod files** stored in mounted volume, not in container image
- **Config files** are JSON (VintageStory native format)
