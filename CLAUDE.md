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

### Sprint Status

**NEVER edit `_bmad-output/implementation-artifacts/sprint-status.yaml` directly.** Use the `just sprint` commands instead:

```bash
just sprint get 10-1-mod-browse-api       # Get status of a story
just sprint set 10-1-mod-browse-api done  # Update story status
just sprint list in-progress              # List items by status
just sprint add-story 10 10-9-new-feature # Add a new story
```

See the skill at `.claude/skills/sprint-status-yaml/SKILL.md` for complete documentation.

### Polish Backlog

`_bmad-output/implementation-artifacts/polish-backlog.md` tracks small-to-medium improvements discovered during development that don't belong to a specific epic. Items are categorized (UI, API, Infrastructure, Tools, CI/CD) with priority, effort estimates, and status tracking. When you encounter minor issues or improvements while working on features, add them to this backlog rather than addressing them immediately.

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

### IMPORTANT: Use `just` for All Development Tasks

**ALWAYS use `just` commands. NEVER use raw `mise exec` commands.** The Justfile wraps all operations and ensures consistency. All recipes accept optional arguments for flexibility.

```bash
# Testing - ALWAYS use just for tests
just test                                    # Run all tests (api + web)
just test-api                                # Run all API tests
just test-api -k "restart"                   # Run tests matching pattern
just test-api tests/test_server.py -xvs      # Run specific file, verbose
just test-api --tb=short                     # Run with short traceback
just test-web                                # Run all web tests

# Validation
just check                                   # Full validation: lint + typecheck + test
just lint                                    # Run all linters
just lint-api --fix                          # Lint API with auto-fix
just typecheck                               # Run all type checks

# Building
just build                                   # Build all projects
just build-api                               # Sync API dependencies
just build-web                               # Build web frontend

# Development
just dev-api                                 # Start API dev server
just dev-api --port 8001                     # Dev server on custom port
just dev-web                                 # Start web dev server
just install                                 # Install all dependencies

# Formatting
just format                                  # Format all code
```

Run `just` with no arguments to see all available commands.

**Note:** This project uses [mise](https://mise.jdx.dev/) for tool version management. The `just` recipes wrap `mise exec` internally - you should never need to call `mise exec` directly.

### Docker
```bash
docker build -t vintagestory-server ./docker
docker compose up -d                   # Start stack
docker compose logs -f vintagestory    # Follow game logs
```

## Git Workflow

- **Merge PRs, do not squash** - Preserve individual commit history when merging pull requests
- **Delete branches after merge** - Clean up feature branches once merged to main
- **Commit after each task** - Create checkpoint commits at logical boundaries (see BMad methodology above)

## Key Conventions

- **API responses** use consistent envelope: `{"status": "ok/error", "data": {...}}`
- **WebSocket** at `/api/v1alpha1/console/ws` for real-time game console streaming
- **Mod files** stored in mounted volume, not in container image
- **Config files** are JSON (VintageStory native format)
