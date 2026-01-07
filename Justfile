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
# Excludes E2E tests by default (run with just test-e2e-api)
# Examples: just test-api -k "restart" | just test-api tests/test_server.py -xvs
test-api *ARGS:
    VS_DATA_DIR=../dev mise exec -C api -- uv run pytest --ignore=tests/e2e {{ARGS}}

# Run web tests (Vitest) - accepts optional vitest args
test-web *ARGS:
    VS_DATA_DIR=../dev mise exec -C web -- bun run test --run {{ARGS}}

# Run API tests in watch mode (TDD)
test-api-watch:
    VS_DATA_DIR=../dev mise exec -C api -- uv run pytest --watch

# Run web tests in watch mode (TDD)
test-web-watch:
    VS_DATA_DIR=../dev mise exec -C web -- bun run test --watch

# Run API E2E tests (pytest) - requires Docker stack running
# Examples: just test-e2e-api | just test-e2e-api -k "health"
test-e2e-api *ARGS:
    VS_DATA_DIR=../dev mise exec -C api -- uv run pytest tests/e2e {{ARGS}}

# Run web E2E tests (Playwright) - manages Docker stack automatically
# Starts fresh Docker stack, waits for health, runs tests, then stops stack
# Uses DOCKER_PORT env var for host port (default: 8080)
# Examples: just test-e2e-web | just test-e2e-web --headed | just test-e2e-web --ui
test-e2e-web *ARGS:
    #!/usr/bin/env bash
    set -e
    DOCKER_PORT="${DOCKER_PORT:-8080}"
    echo "🐳 Starting Docker stack..."
    just docker start

    echo "⏳ Waiting for API to be ready..."
    for i in {1..30}; do
        if curl -sf "http://localhost:$DOCKER_PORT/healthz" > /dev/null 2>&1; then
            echo "✅ API is ready"
            break
        fi
        if [ $i -eq 30 ]; then
            echo "❌ API failed to start within 30 seconds"
            just docker logs
            just docker stop
            exit 1
        fi
        sleep 1
    done

    echo "🎭 Running Playwright tests..."
    mise exec -C web -- bun run test:e2e {{ARGS}} || TEST_EXIT=$?

    echo "🧹 Stopping Docker stack..."
    just docker stop

    exit ${TEST_EXIT:-0}

# Alias for backward compatibility
test-e2e *ARGS: test-e2e-api

# =============================================================================
# COVERAGE
# =============================================================================

# Run all tests with coverage summary
coverage: coverage-api coverage-web

# Run API tests with coverage report
coverage-api *ARGS:
    VS_DATA_DIR=../dev mise exec -C api -- uv run pytest --ignore=tests/e2e --cov --cov-report=term-missing {{ARGS}}

# Run web tests with coverage report
coverage-web *ARGS:
    VS_DATA_DIR=../dev mise exec -C web -- bun run test --run --coverage {{ARGS}}

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
    env VS_DATA_DIR=../dev mise exec -C api -- uv run uvicorn vintagestory_api.main:app --reload --port $API_PORT {{ARGS}}

# Start web dev server - accepts optional args
dev-web *ARGS:
    mise exec -C web -- bun run dev --port $WEB_PORT {{ARGS}}

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

# Docker commands: build, start, stop, restart, status, logs
# Usage: just docker <command> [args]
# Uses DOCKER_PORT env var for host port mapping (default: 8080)
docker COMMAND *ARGS:
    #!/usr/bin/env bash
    DOCKER_PORT="${DOCKER_PORT:-8080}"
    case "{{COMMAND}}" in
        build)
            VS_DATA_DIR=/data VITE_API_BASE_URL="http://localhost:$DOCKER_PORT" docker compose -f docker-compose.dev.yaml build {{ARGS}}
            ;;
        start)
            VS_DATA_DIR=/data VITE_API_BASE_URL="http://localhost:$DOCKER_PORT" docker compose -f docker-compose.dev.yaml up -d --build {{ARGS}}
            ;;
        stop)
            docker compose -f docker-compose.dev.yaml down {{ARGS}}
            docker rm -f vintagestory-manager-dev
            ;;
        restart)
            just docker stop {{ARGS}}
            just docker start {{ARGS}}
            ;;
        status)
            docker compose -f docker-compose.dev.yaml ps {{ARGS}}
            ;;
        logs)
            docker compose -f docker-compose.dev.yaml logs -f {{ARGS}}
            ;;
        *)
            echo "Unknown docker command: {{COMMAND}}"
            echo "Available commands: build, start, stop, restart, status, logs"
            exit 1
            ;;
    esac

# =============================================================================
# DATA MANAGEMENT
# =============================================================================

# Clean data directory (removes all data subdirectories - keeps .gitkeep)
# Useful for testing fresh installations
clean-data:
    rm -rf data/*/.gitkeep
    find data -mindepth 1 -delete 2>/dev/null || true
    @echo "Data directory cleaned"

# =============================================================================
# SPRINT STATUS MANAGEMENT
# =============================================================================

# Sprint status commands: get, set, list, add-story, add-epic
# Usage: just sprint <command> [args]
# Examples:
#   just sprint get 10-1-mod-browse-api
#   just sprint set 10-1-mod-browse-api review
#   just sprint list in-progress
#   just sprint add-story 10 10-9-new-feature
sprint *ARGS:
    ./scripts/sprint-status.sh {{ARGS}}

# =============================================================================
# POLISH BACKLOG MANAGEMENT
# =============================================================================

# Polish backlog commands: list, get, add, set, done
# Usage: just polish <command> [args]
# Examples:
#   just polish list
#   just polish list API backlog
#   just polish get UI-029
#   just polish add UI "Add dark mode toggle" medium S
#   just polish set UI-029 in-progress
#   just polish done UI-029 https://github.com/org/repo/pull/99
polish *ARGS:
    ./scripts/polish-backlog.sh {{ARGS}}
