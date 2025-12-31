# Story 1.4: Docker Deployment Configuration

Status: done

## Summary
Created multi-stage Dockerfile, docker-compose configs, and static file serving for production deployment.

## Key Architecture
- Single container: FastAPI serves API + static frontend
- Base image: mcr.microsoft.com/dotnet/runtime:8.0.22-noble-amd64 (.NET for VintageStory compatibility)
- Non-root user: vsmanager

## Volume Structure (/data)
```
/data
├── server/    # VintageStory server installation
├── mods/      # Mod files
├── config/    # Game server configuration
├── state/     # API state persistence
├── logs/      # Application logs
└── backups/   # Server backups
```

## Environment Variables
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| VS_API_KEY_ADMIN | Yes | - | Admin API key |
| VS_API_KEY_MONITOR | No | - | Read-only key |
| VS_GAME_VERSION | No | stable | VS version |
| VS_DEBUG | No | false | Debug logging |
| VS_DATA_DIR | No | /data | Data directory |

## Commands
```bash
docker build -t vintagestory-server:local .
docker compose -f docker-compose.dev.yaml up --build
```

## Ports
- 8080: Web UI + API
- 42420: Game server (future)
