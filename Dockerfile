# VintageStory Server Manager
# Multi-stage build: Build frontend, then create production image
# Base: .NET 10 runtime on Ubuntu 26.04 Resolute (required for VintageStory 1.22+)
# Python 3.14 installed from Ubuntu apt (native to Resolute)

# ==============================================================================
# Stage 1: Build frontend
# ==============================================================================
FROM node:26-slim AS web-build

# No API key is built in: the API serves it at runtime from /config.js (Epic 15 ADR-5),
# so one image works for every deployment.

WORKDIR /app

# Install bun for faster builds (version pinned per Architecture/.mise.toml)
RUN npm install -g bun@1.4.4

# Copy dependency files first for layer caching
COPY web/package.json web/bun.lock ./

# Install dependencies
RUN bun install --frozen-lockfile

# Copy source and build. VITE_API_BASE_URL is empty for same-origin requests in Docker;
# VITE_API_KEY is empty so no key reaches the bundle (.dockerignore also keeps web/.env out)
COPY web/ ./
RUN VITE_API_KEY="" VITE_API_BASE_URL="" bun run build

# ==============================================================================
# Stage 2: Production image
# Base: .NET 10 runtime on Ubuntu 26.04 Resolute (required for VintageStory 1.22+)
# Python 3.14 is native to Ubuntu 26.04
# ==============================================================================
FROM mcr.microsoft.com/dotnet/runtime:10.0.14-resolute-amd64 AS final

WORKDIR /app

# Update system packages for security fixes, then install Python 3.14
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
    python3.14 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.14 /usr/bin/python3 \
    && ln -sf /usr/bin/python3.14 /usr/bin/python

# Install uv for fast Python dependency installation
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first for layer caching
COPY api/pyproject.toml api/uv.lock ./

# Install Python dependencies (production only, no dev deps); the project itself
# is installed after its source is copied, so this layer stays cached
RUN uv sync --frozen --no-dev --no-install-project

# Copy application source code and install the project, so start-up needs no sync
COPY api/src/ ./src/
RUN uv sync --frozen --no-dev

# Copy built frontend from web-build stage
COPY --from=web-build /app/dist /app/static

# Create non-root user with home in /data for cache persistence
RUN groupadd -r vsmanager && useradd -r -g vsmanager -d /data/vsmanager -s /bin/bash vsmanager

# Create data directory structure and set ownership
# /data/server     - VintageStory installation (extracted tarball)
# /data/serverdata - Persistent game data (Mods, Saves, configs) via --dataPath
# /data/vsmanager  - API manager state (version tracking)
RUN mkdir -p /data/server /data/serverdata /data/vsmanager \
    && chown -R vsmanager:vsmanager /app /data

# Switch to non-root user
USER vsmanager

# Health check using Python urllib (no curl needed)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/healthz')" || exit 1

# Expose ports
# 8080: Web UI + API
# 42420: VintageStory game server (future)
EXPOSE 8080 42420

# Start uvicorn server. --no-sync: everything is installed at build time; a sync here
# would add the dev group and download it from PyPI on every start (VSS-flj)
CMD ["uv", "run", "--no-sync", "uvicorn", "vintagestory_api.main:app", "--host", "0.0.0.0", "--port", "8080"]
