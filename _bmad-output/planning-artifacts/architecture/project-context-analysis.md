# Project Context Analysis

## Requirements Overview

**Functional Requirements:**

37 functional requirements spanning 8 capability areas:

| Category               | FRs     | Architectural Implication                                         |
| ---------------------- | ------- | ----------------------------------------------------------------- |
| Server Lifecycle       | FR1-5   | Process manager component, state machine for server status        |
| Console Access         | FR6-9   | WebSocket server, ring buffer implementation, Admin-only access   |
| Mod Management         | FR10-17 | External HTTP client, file system operations, compatibility logic |
| Game Configuration     | FR18-22 | JSON file I/O, validation layer                                   |
| Settings Management    | FR23-26 | Lightweight persistence (JSON files)                              |
| Health & Observability | FR27-30 | Kubernetes-compatible endpoints, process health checks            |
| Authentication         | FR31-37 | Middleware for API key validation, role-based access control      |
| Deployment             | FR38-39 | Docker Compose, environment variable configuration                |

**Non-Functional Requirements:**

| Category      | Key Requirements                                | Architectural Impact                                       |
| ------------- | ----------------------------------------------- | ---------------------------------------------------------- |
| Performance   | <1s console latency, <500ms API response        | In-memory operations, efficient WebSocket handling         |
| Security      | API keys never logged, in-memory console buffer | Logging configuration, no persistence for sensitive data   |
| Reliability   | API survives game crashes, auto-reconnect       | Decoupled process management, WebSocket reconnection logic |
| Integration   | Graceful mod API failures, clear error messages | Circuit breaker pattern, response caching                  |
| Observability | Structured JSON logs, contextual errors         | Logging framework configuration, error envelope design     |

**Scale & Complexity:**

- Primary domain: Full-stack web application (API + SPA + Docker)
- Complexity level: Low-Medium
- Estimated architectural components: 6-8 major components

## Technical Constraints & Dependencies

**External Dependencies:**

- VintageStory Mod Database API (`mods.vintagestory.at`) - mod lookup and downloads
- Existing Docker image (`quartzar/vintage-story-server`) or custom from `mcr.microsoft.com/dotnet/runtime:8.0`
- Game server binary downloaded at runtime

**Infrastructure Constraints:**

- No database required - JSON file persistence only
- TLS termination via external reverse proxy (Traefik, Caddy, nginx)
- Single server management (not multi-server fleet)

**Technology Decisions (from PRD/UX):**

- Backend: Python + FastAPI + uv + Ruff + pytest
- Frontend: React + Vite + TypeScript + Bun
- Components: shadcn/ui + Radix UI
- Terminal: xterm.js
- Theming: Catppuccin Mocha/Latte

## Cross-Cutting Concerns Identified

1. **Authentication & Authorization**
   - API key middleware for all protected routes
   - Role differentiation (Admin vs Monitor)
   - WebSocket authentication for console access

2. **Error Handling & Response Envelope**
   - Consistent `{"status": "ok|error", "data": {...}}` format
   - Graceful degradation for external API failures
   - Contextual error messages without exposing internals

3. **State Management**
   - Server status tracking (running/stopped/starting/stopping)
   - Pending restart queue for batched changes
   - Mod enable/disable state

4. **Real-Time Communication**
   - WebSocket for console streaming
   - Status updates pushed to connected clients
   - Reconnection handling

5. **File System Operations**
   - Config file read/write with validation
   - Mod file downloads and management
   - Game server binary installation
