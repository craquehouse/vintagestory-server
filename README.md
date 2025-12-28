# VintageStory Server

Dockerized VintageStory dedicated game server with a web-based admin interface.

## Artificial Intelligence Disclaimer

This project is developed with the assistance of AI coding tools (such as Claude Code, opencode, cursor, or similar). All AI-generated code is reviewed and tested before inclusion. While we strive for quality and correctness, users should evaluate the code independently for their specific use cases.

## Components

- **Docker Image** - VintageStory dedicated server container
- **API Server** - Python/FastAPI backend for server control and mod management
- **Web UI** - Node.js admin interface

## Features (Planned)

- Start/stop game server
- Edit server configuration
- Manage mods (install, update, remove)
- Access game console via web interface

## Development Setup

### Prerequisites

- [mise](https://mise.jdx.dev/) - Runtime version manager

### Install Development Tools

```bash
mise trust && mise install
```

This installs Python 3.13, uv, and Bun at the pinned versions specified in `.mise.toml`.

### Development Commands

Run `just` to see all available commands. Common ones:

```bash
just test           # Run all tests (unit + integration)
just test-api       # Run API tests only
just test-web       # Run web tests only
just test-e2e       # Run E2E tests (requires Docker app running)
just check          # Full validation: lint + typecheck + test
just dev-api        # Start API dev server
just dev-web        # Start web dev server
```

### End-to-End Testing

E2E tests use Playwright to test the full application running in Docker.

1. Start the application: `just docker-start`
2. Run E2E tests: `just test-e2e`
3. Run with visible browser: `just test-e2e --headed`
4. Run specific tests: `just test-e2e -k "health"`

E2E tests live in `api/tests/e2e/` and verify real browser interactions.

## Quick Start

```bash
docker compose up -d
```

## License

MIT
