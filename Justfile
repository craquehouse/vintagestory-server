# Justfile for vintagestory-server
# Provides unified commands for development tasks across api/ and web/ projects
# All commands use mise to ensure correct tool versions are used
#
# Usage: just <recipe> [args...]
# Examples:
#   just test                              - Run all tests
#   just test-api                          - Run all API tests
#   just test-api -k "restart or install"  - Run API tests matching "restart" or "install"
#   just test-api tests/test_health.py -xvs - Run specific file, verbose
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

# Run all tests (api + web + scripts)
test: test-api test-web test-scripts

# Run API tests (Python/pytest) - accepts optional pytest args
# Excludes E2E tests by default (run with just test-e2e-api)
# Examples: just test-api -k "restart or install" | just test-api tests/test_health.py -xvs
[positional-arguments]
test-api *ARGS:
    VS_DATA_DIR=../dev mise exec -C api -- uv run pytest --ignore=tests/e2e "$@"

# Run web tests (Vitest) - accepts optional vitest args
[positional-arguments]
test-web *ARGS:
    VS_DATA_DIR=../dev mise exec -C web -- bun run test --run "$@"

# Examples: just test-scripts | just test-scripts test-version.sh
# Run tests for the release and version scripts (bash) - accepts optional test files
[positional-arguments]
test-scripts *ARGS:
    mise exec -- ./scripts/tests/run.sh "$@"

# Run API tests in watch mode (TDD)
test-api-watch:
    VS_DATA_DIR=../dev mise exec -C api -- uv run pytest --watch

# Run web tests in watch mode (TDD)
test-web-watch:
    VS_DATA_DIR=../dev mise exec -C web -- bun run test --watch

# Run API E2E tests (pytest) - requires Docker stack running
# Examples: just test-e2e-api | just test-e2e-api -k "health"
[positional-arguments]
test-e2e-api *ARGS:
    VS_DATA_DIR=../dev mise exec -C api -- uv run pytest tests/e2e "$@"

# Run web E2E tests (Playwright) - manages Docker stack automatically
# Starts fresh Docker stack, waits for health, runs tests, then stops stack
# Uses DOCKER_PORT env var for host port (default: 8080)
# Examples: just test-e2e-web | just test-e2e-web --headed | just test-e2e-web --ui
[positional-arguments]
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
    mise exec -C web -- bun run test:e2e "$@" || TEST_EXIT=$?

    echo "🧹 Stopping Docker stack..."
    just docker stop

    exit ${TEST_EXIT:-0}

# Run the untagged E2E tests (the CI set) on a throwaway seeded container on port 18080
# Examples: just test-e2e-ci | just test-e2e-ci e2e/settings-as-saved.spec.ts
[positional-arguments]
test-e2e-ci *ARGS:
    mise exec -- ./scripts/e2e-ci.sh "$@"

# Install the Chromium builds the web and API E2E tests use (once per machine)
install-e2e-browsers:
    mise exec -C web -- bunx playwright install --with-deps chromium
    mise exec -C api -- uv run playwright install chromium

# Print the Playwright versions of the web and the API (the e2e job's browser cache key)
playwright-versions:
    @echo "web-$(mise exec -C web -- bunx playwright --version | cut -d' ' -f2)-api-$(mise exec -C api -- uv run playwright --version | cut -d' ' -f2)"

# Alias for backward compatibility
[positional-arguments]
test-e2e *ARGS:
    just test-e2e-api "$@"

# =============================================================================
# COVERAGE
# =============================================================================

# Run all tests with coverage summary
coverage: coverage-api coverage-web

# Run API tests with coverage report
[positional-arguments]
coverage-api *ARGS:
    VS_DATA_DIR=../dev mise exec -C api -- uv run pytest --ignore=tests/e2e --cov --cov-report=term-missing "$@"

# Run web tests with coverage report
[positional-arguments]
coverage-web *ARGS:
    VS_DATA_DIR=../dev mise exec -C web -- bun run test --run --coverage "$@"

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
lint: lint-api lint-web lint-scripts lint-workflows

# Lint API (ruff check, then ruff format --check) - optional args go to ruff check
[positional-arguments]
lint-api *ARGS:
    mise exec -C api -- uv run ruff check . "$@"
    mise exec -C api -- uv run ruff format --check .

# Lint web (TypeScript type checking)
lint-web:
    mise exec -C web -- bun run lint

# Lint every bash script in scripts/ and scripts/tests/ (ShellCheck), and the Python
# scripts in scripts/ with the API's ruff and pyright and their configuration
lint-scripts:
    mise exec -- shellcheck -x scripts/*.sh scripts/tests/*.sh
    mise exec -C api -- uv run ruff check --config pyproject.toml ../scripts
    mise exec -C api -- uv run ruff format --check --config pyproject.toml ../scripts
    mise exec -C api -- uv run pyright ../scripts/moddb-replay.py

# Lint GitHub Actions workflows (actionlint, which also runs ShellCheck on run: steps)
lint-workflows:
    mise exec -- actionlint

# =============================================================================
# SECURITY SCAN
# =============================================================================

# Static security scan (semgrep, pinned in scripts/semgrep.sh); needs the network; not in `just check`
# Examples: just semgrep | just semgrep --baseline-commit origin/main
[positional-arguments]
semgrep *ARGS:
    mise exec -- ./scripts/semgrep.sh "$@"

# =============================================================================
# TYPE CHECKING
# =============================================================================

# Run all type checks
typecheck: typecheck-api typecheck-web

# Type check API (Pyright) - includes src/ and tests/, accepts optional pyright args
[positional-arguments]
typecheck-api *ARGS:
    mise exec -C api -- uv run pyright src/ tests/ "$@"

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
[positional-arguments]
dev-api *ARGS:
    env VS_DATA_DIR=../dev mise exec -C api -- uv run uvicorn vintagestory_api.main:app --reload --port $API_PORT "$@"

# Start web dev server - accepts optional args
[positional-arguments]
dev-web *ARGS:
    mise exec -C web -- bun run dev --port $WEB_PORT "$@"

# Install all dependencies
install: install-api install-web

# Install API dependencies - accepts optional uv sync args
[positional-arguments]
install-api *ARGS:
    mise exec -C api -- uv sync --dev "$@"

# Install web dependencies - accepts optional bun install args
[positional-arguments]
install-web *ARGS:
    mise exec -C web -- bun install "$@"

# =============================================================================
# DOCKER
# =============================================================================

# Docker commands: build, start, stop, restart, status, logs
# Usage: just docker <command> [args]
# Uses DOCKER_PORT env var for host port mapping (default: 8080)
[positional-arguments]
docker COMMAND *ARGS:
    #!/usr/bin/env bash
    DOCKER_PORT="${DOCKER_PORT:-8080}"
    command="$1"
    shift
    case "$command" in
        build)
            VS_DATA_DIR=/data VITE_API_BASE_URL="http://localhost:$DOCKER_PORT" docker compose -f docker-compose.dev.yaml build "$@"
            ;;
        start)
            VS_DATA_DIR=/data VITE_API_BASE_URL="http://localhost:$DOCKER_PORT" docker compose -f docker-compose.dev.yaml up -d --build "$@"
            ;;
        stop)
            docker compose -f docker-compose.dev.yaml down "$@"
            docker rm -f vintagestory-manager-dev
            ;;
        restart)
            just docker stop "$@"
            just docker start "$@"
            ;;
        status)
            docker compose -f docker-compose.dev.yaml ps "$@"
            ;;
        logs)
            docker compose -f docker-compose.dev.yaml logs -f "$@"
            ;;
        *)
            echo "Unknown docker command: $command"
            echo "Available commands: build, start, stop, restart, status, logs"
            exit 1
            ;;
    esac

# =============================================================================
# RELEASES
# =============================================================================

# Print the manager version; fails if web/package.json, api/pyproject.toml and api/uv.lock disagree
version:
    @mise exec -- ./scripts/version.sh

# Examples: just changelog | just changelog --tag v0.2.0 (heading as the release would show it)
# Print the release notes for unreleased commits (writes nothing) - accepts git-cliff args
[positional-arguments]
changelog *ARGS:
    @mise exec -- git cliff --unreleased --strip header "$@"

# Examples: just release --dry-run | just release | just release minor | just release 0.3.0-rc.1
# Cut a release: version files, CHANGELOG.md, commit, tag, then push after confirmation
[positional-arguments]
release *ARGS:
    mise exec -- ./scripts/release.sh "$@"

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
[positional-arguments]
sprint *ARGS:
    ./scripts/sprint-status.sh "$@"

