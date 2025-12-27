# Justfile for vintagestory-server
# Provides unified commands for development tasks across api/ and web/ projects
# All commands use mise to ensure correct tool versions are used
#
# Usage: just <recipe>
# Examples:
#   just test        - Run all tests
#   just check       - Full validation (lint + typecheck + test)
#   just build       - Build all projects
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

# Run API tests (Python/pytest)
test-api:
    mise exec -C api -- uv run pytest

# Run web tests (Vitest)
test-web:
    mise exec -C web -- bun run test

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

# Lint API (Ruff)
lint-api:
    mise exec -C api -- uv run ruff check .

# Lint web (TypeScript type checking)
lint-web:
    mise exec -C web -- bun run lint

# =============================================================================
# TYPE CHECKING
# =============================================================================

# Run all type checks
typecheck: typecheck-api typecheck-web

# Type check API (Pyright) - includes src/ and tests/
typecheck-api:
    mise exec -C api -- uv run pyright src/ tests/

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

# Start API dev server
dev-api:
    mise exec -C api -- uv run uvicorn vintagestory_api.main:app --reload

# Start web dev server
dev-web:
    mise exec -C web -- bun run dev

# Install all dependencies
install: install-api install-web

# Install API dependencies
install-api:
    mise exec -C api -- uv sync --dev

# Install web dependencies
install-web:
    mise exec -C web -- bun install
