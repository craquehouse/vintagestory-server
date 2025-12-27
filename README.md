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

## Quick Start

```bash
docker compose up -d
```

## License

MIT
