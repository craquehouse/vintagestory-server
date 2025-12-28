# Justfile for vintagestory-server
# Provides unified commands for development tasks across api/ and web/ projects
# All commands use mise to ensure correct tool versions are used
#
# Usage: just <recipe> [args...]
# Examples:
#   just test                              - Run all tests
#   just test-api                          - Run all API tests
#   just test-api -k "restart"             - Run API tests matching "restart"
#   just test-api tests/test_server.py -xvs - Run specific file, verbose
#   just check                             - Full validation (lint + typecheck + test)
#   just build                             - Build all projects
#
# CI Usage:
#   Ensure `mise` is in PATH and run: just check
#   For CI environments, install mise first: https://mise.jdx.dev/getting-started.html

# Note: Run `just` from project root for correct relative paths

# Default recipe - show available commands
default:
    @just --list

# =============================================================================
# TESTING
# =============================================================================

# Run all tests (api + web)
test: test-api test-web

# Run API tests (Python/pytest) - accepts optional pytest args
# Examples: just test-api -k "restart" | just test-api tests/test_server.py -xvs
test-api *ARGS:
    mise exec -C api -- uv run pytest {{ARGS}}

# Run web tests (Vitest) - accepts optional vitest args
test-web *ARGS:
    mise exec -C web -- bun run test {{ARGS}}

# Run API tests in watch mode (TDD)
test-api-watch:
    mise exec -C api -- uv run pytest --watch

# Run web tests in watch mode (TDD)
test-web-watch:
    mise exec -C web -- bun run test --watch

# =============================================================================
# BUILDING
# =============================================================================

# Build all projects
build: build-api build-web

# Build/check API (sync dependencies)
build-api:
    mise exec -C api -- uv sync

# Build web (TypeScript + Vite)
build-web:
    mise exec -C web -- bun run build

# =============================================================================
# LINTING
# =============================================================================

# Run all linters
lint: lint-api lint-web

# Lint API (Ruff) - accepts optional ruff args
lint-api *ARGS:
    mise exec -C api -- uv run ruff check . {{ARGS}}

# Lint web (TypeScript type checking)
lint-web:
    mise exec -C web -- bun run lint

# =============================================================================
# TYPE CHECKING
# =============================================================================

# Run all type checks
typecheck: typecheck-api typecheck-web

# Type check API (Pyright) - includes src/ and tests/, accepts optional pyright args
typecheck-api *ARGS:
    mise exec -C api -- uv run pyright src/ tests/ {{ARGS}}

# Type check web (TypeScript)
typecheck-web:
    mise exec -C web -- bun run typecheck

# =============================================================================
# FULL VALIDATION
# =============================================================================

# Full validation: lint + typecheck + test
check: lint typecheck test

# =============================================================================
# FORMATTING
# =============================================================================

# Format all code
format: format-api format-web

# Format API code (Ruff)
format-api:
    mise exec -C api -- uv run ruff format .

# Format web code (Prettier via bunx)
format-web:
    mise exec -C web -- bunx prettier --write "src/**/*.{ts,tsx,css,json}"

# =============================================================================
# DEVELOPMENT
# =============================================================================

# Start API dev server - accepts optional uvicorn args
# Examples: just dev-api --port 8001 | just dev-api --host 0.0.0.0
# Sets up local development environment with relative data directory and dev API key
dev-api *ARGS:
    mise exec -C api -- uv run uvicorn vintagestory_api.main:app --reload {{ARGS}}

# Start web dev server - accepts optional args
dev-web *ARGS:
    mise exec -C web -- bun run dev {{ARGS}}

# Install all dependencies
install: install-api install-web

# Install API dependencies - accepts optional uv sync args
install-api *ARGS:
    mise exec -C api -- uv sync --dev {{ARGS}}

# Install web dependencies - accepts optional bun install args
install-web *ARGS:
    mise exec -C web -- bun install {{ARGS}}

# =============================================================================
# DOCKER
# =============================================================================

# Build Docker image for development
docker-build:
    docker compose -f docker-compose.dev.yaml build

# Start Docker container (builds if needed)
docker-start:
    docker compose -f docker-compose.dev.yaml up -d --build

# Stop Docker container
docker-stop:
    docker compose -f docker-compose.dev.yaml down

# Show Docker container status
docker-status:
    docker compose -f docker-compose.dev.yaml ps

# View Docker container logs
docker-logs:
    docker compose -f docker-compose.dev.yaml logs -f

# =============================================================================
# DATA MANAGEMENT
# =============================================================================

# Clean data directory (removes all data subdirectories - keeps .gitkeep)
# Useful for testing fresh installations
clean-data:
    rm -rf data/server data/serverdata data/vsmanager
    @echo "Data directory cleaned (server, serverdata, vsmanager removed)"
