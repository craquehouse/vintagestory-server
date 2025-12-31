# VintageStory Server Manager - Project Overview

## Purpose
Custom VintageStory game server infrastructure providing a web-based admin interface for managing dedicated game servers.

## Architecture

### Components

| Component | Tech Stack | Location |
|-----------|------------|----------|
| **API Server** | Python 3.x / FastAPI | `api/` |
| **Web UI** | React / TypeScript / Vite | `web/` |
| **Docker** | Container deployment | `Dockerfile`, `docker-compose.yaml` |

### Component Interaction
```
[Web UI] <--HTTP--> [FastAPI] <--Docker API/Process--> [VS Server]
                         |
                    [Config Files]
                    [Mod Storage]
```

## API Structure (`api/src/vintagestory_api/`)

### Routers
- `auth.py` - Authentication endpoints
- `server.py` - Server lifecycle control
- `console.py` - WebSocket console streaming
- `config.py` - Configuration management
- `mods.py` - Mod management
- `health.py` - Health check endpoints

### Key Services
- **ServerService** (`services/server.py`) - Game server lifecycle (install, start, stop, restart), version management, process monitoring
- **ConsoleService** (`services/console.py`) - Real-time console buffer and WebSocket streaming
- **ModService** (`services/mods.py`) - Mod installation from VintageStory mod database
- **ModApiService** (`services/mod_api.py`) - External mod database API client
- **GameConfigService** (`services/game_config.py`) - Server configuration read/write
- **ConfigInitService** (`services/config_init_service.py`) - Initial config setup from templates
- **ApiSettingsService** (`services/api_settings.py`) - API-level settings management

### Models
- `server.py` - Server status, version info
- `console.py` - Console messages
- `mods.py` - Mod metadata, compatibility
- `responses.py` - Standard API response envelope

## Web Structure (`web/src/`)

### Features
- `dashboard/` - Server controls and status display
- `terminal/` - Real-time console streaming via xterm.js
- `mods/` - Mod management UI
- `config/` - Configuration editor

### Key Components
- `components/layout/` - Header, Sidebar, Layout
- `components/terminal/` - TerminalView, ConnectionStatus
- `components/ui/` - Reusable UI components (shadcn/ui)

### API Client
- `api/client.ts` - Base HTTP client
- `api/server.ts` - Server API calls
- `api/mods.ts` - Mod API calls
- `api/hooks/` - React Query hooks

## Development

### Commands (via Justfile)
```bash
just test          # Run all tests
just test-api      # API tests only
just test-web      # Web tests only
just check         # Full validation (lint + typecheck + test)
just dev-api       # Start API dev server
just dev-web       # Start web dev server
```

### Methodology
Uses **BMad method** for structured AI-assisted development:
- Stories in `docs/stories/`
- Planning artifacts in `_bmad-output/planning-artifacts/`
- Implementation tracking via `_bmad-output/implementation-artifacts/sprint-status.yaml`

## External APIs
- VintageStory mod database: `https://mods.vintagestory.at/api/`
- Documentation in `agentdocs/vintagestory-modapi.md`

## Conventions
- API responses use envelope: `{"status": "ok/error", "data": {...}}`
- WebSocket at `/ws/console` for real-time console
- Config files are JSON (VintageStory native format)
