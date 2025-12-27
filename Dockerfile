# VintageStory Server Manager
# Multi-stage build: Build frontend, then create production image
# Base: .NET 8 runtime on Ubuntu 24.04 Noble (required for VintageStory)
# Python 3.12 installed from Ubuntu apt (native to Noble)

# ==============================================================================
# Stage 1: Build frontend
# ==============================================================================
FROM node:22-slim AS web-build

WORKDIR /app

# Install bun for faster builds (version pinned per Architecture/.mise.toml)
RUN npm install -g bun@1.3.5

# Copy dependency files first for layer caching
COPY web/package.json web/bun.lock ./

# Install dependencies
RUN bun install --frozen-lockfile

# Copy source and build
COPY web/ ./
RUN bun run build

# ==============================================================================
# Stage 2: Production image
# Base: .NET 8.0 runtime on Ubuntu 24.04 Noble (required for VintageStory)
# Python 3.12 is native to Ubuntu 24.04
# ==============================================================================
FROM mcr.microsoft.com/dotnet/runtime:8.0.22-noble-amd64 AS final

WORKDIR /app

# Update system packages for security fixes, then install Python 3.12
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
    python3.12 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.12 /usr/bin/python3 \
    && ln -sf /usr/bin/python3.12 /usr/bin/python

# Install uv for fast Python dependency installation
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first for layer caching
COPY api/pyproject.toml api/uv.lock ./

# Install Python dependencies (production only, no dev deps)
RUN uv sync --frozen --no-dev

# Copy application source code
COPY api/src/ ./src/

# Copy built frontend from web-build stage
COPY --from=web-build /app/dist /app/static

# Create non-root user with home in /data for cache persistence
RUN groupadd -r vsmanager && useradd -r -g vsmanager -d /data/vsmanager -s /bin/bash vsmanager

# Create data directory structure and set ownership
RUN mkdir -p /data/server /data/mods /data/config /data/state /data/logs /data/backups /data/vsmanager \
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

# Start uvicorn server
CMD ["uv", "run", "uvicorn", "vintagestory_api.main:app", "--host", "0.0.0.0", "--port", "8080"]
