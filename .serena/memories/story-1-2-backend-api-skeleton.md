# Story 1.2: Backend API Skeleton with Health Endpoints

Status: done

## Summary
Implemented health check endpoints (/healthz, /readyz), structured logging with structlog, and API response envelope pattern.

## Key Patterns

### Response Envelope
```python
{"status": "ok", "data": {...}}        # Success
{"status": "error", "error": {...}}    # Error
```

### GameServerStatus Enum
- not_installed, stopped, starting, running, stopping

### Health Endpoints (NOT versioned)
- GET /healthz - Liveness probe (API health + game server status)
- GET /readyz - Readiness probe

### API Versioning
- Future endpoints at `/api/v1alpha1`
- Health endpoints at root level (K8s convention)

## Files Created
- api/src/vintagestory_api/models/{responses.py, errors.py}
- api/src/vintagestory_api/routers/health.py
- api/tests/test_health.py

## Tests
12 tests passing - covers envelope format, health endpoints, no auth required
