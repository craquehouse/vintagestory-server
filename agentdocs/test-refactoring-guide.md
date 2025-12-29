# Test Refactoring Guide

_Migration plan for splitting large test files into focused modules_

## Overview

This guide documents the plan for refactoring large test files (>500 lines) into focused, maintainable modules. The goal is to improve test organization, make it easier to find relevant tests, and reduce cognitive load.

## Current State

| File | Lines | Classes | Status |
|------|-------|---------|--------|
| `test_server.py` | 2929 | 28 | Needs refactoring |
| `test_console.py` | 1656 | 8 | Needs refactoring |
| `test_auth.py` | 301 | 3 | OK |
| `test_permissions.py` | 355 | 4 | OK |
| `test_rbac_integration.py` | 295 | 3 | OK |
| `test_health.py` | 115 | 2 | OK |
| `test_config.py` | 116 | 2 | OK |
| `test_static_serving.py` | 117 | 2 | OK |
| `test_debug_gating.py` | 101 | 2 | OK |

## Target Structure

### Server Tests (`tests/server/`)

```
tests/server/
├── __init__.py
├── conftest.py                    # Shared fixtures (created)
├── test_validation.py             # Version validation, path security
├── test_versions.py               # Version fetching, availability
├── test_install.py                # Installation, download, extraction
├── test_lifecycle.py              # Start, stop, restart, state
├── test_endpoints.py              # REST API endpoint tests
└── test_install_endpoints.py      # Installation endpoint tests
```

### Console Tests (`tests/console/`)

```
tests/console/
├── __init__.py
├── conftest.py                    # Shared fixtures
├── test_buffer.py                 # ConsoleBuffer unit tests
├── test_service_integration.py    # ServerService + ConsoleBuffer
├── test_history_endpoint.py       # GET /console/history
├── test_command_endpoint.py       # POST /console/command
└── test_websocket.py              # WebSocket tests
```

## Migration Strategy

### Step 1: Create Package Structure (Done)

Created `tests/server/` package with:
- `__init__.py`
- `conftest.py` with shared fixtures

### Step 2: Extract Test Classes

For each target file, extract the relevant classes from the original:

**test_validation.py** (from test_server.py):
- `TestVersionValidation` (lines 122-187)
- `TestPathTraversalProtection` (lines 188-229)

**test_versions.py** (from test_server.py):
- `TestGetAvailableVersions` (lines 230-284)
- `TestCheckVersionAvailable` (lines 285-340)
- `TestGetVersionInfo` (lines 341-387)

**test_install.py** (from test_server.py):
- `TestInstallProgress` (lines 388-416)
- `TestServerInstallation` (lines 417-582)
- `TestDownloadServer` (lines 583-662)
- `TestChecksumVerification` (lines 663-692)
- `TestExtractServer` (lines 693-781)
- `TestInstallProgressTracking` (lines 782-843)
- `TestCleanupOnFailure` (lines 844-877)

**test_lifecycle.py** (from test_server.py):
- `TestServerStateManagement` (lines 878-948)
- `TestPostInstallSetup` (lines 949-986)
- `TestServerLifecycleStateEnum` (lines 1356-1371)
- `TestStartServer` (lines 1372-1466)
- `TestStopServer` (lines 1467-1610)
- `TestRestartServer` (lines 1611-1652)
- `TestProcessMonitoring` (lines 1653-1692)
- `TestServerStatus` (lines 1693-1774)
- `TestConcurrentLifecycleOperations` (lines 1775-1813)
- `TestRestartPartialFailures` (lines 2237-2437)

**test_endpoints.py** (from test_server.py):
- `TestServerStartEndpoint` (lines 1814-1939)
- `TestServerStopEndpoint` (lines 1940-2072)
- `TestServerRestartEndpoint` (lines 2073-2236)
- `TestRestartEndpointErrorHandling` (lines 2438-2532)
- `TestServerStatusEndpoint` (lines 2533-2929)

**test_install_endpoints.py** (from test_server.py):
- `TestServerInstallEndpoint` (lines 987-1191)
- `TestServerInstallStatusEndpoint` (lines 1192-1355)

### Step 3: Update Imports

Each new file needs these imports:

```python
"""Tests for [specific functionality]."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
import respx
from httpx import Response

from vintagestory_api.config import Settings
from vintagestory_api.models.errors import ErrorCode
from vintagestory_api.models.server import (
    InstallationStage,
    InstallProgress,
    LifecycleAction,
    ServerState,
)
from vintagestory_api.services.server import (
    VS_CDN_BASE,
    VS_STABLE_API,
    VS_UNSTABLE_API,
    ServerService,
)

# Import from conftest (automatically available via pytest)
# MOCK_STABLE_API_RESPONSE, MOCK_UNSTABLE_API_RESPONSE, create_mock_tarball
```

### Step 4: Run Tests After Each File

After creating each new file:

```bash
just test-api tests/server/test_<name>.py -v
```

### Step 5: Delete Original and Re-export

Once all tests pass in new locations:

1. Delete `tests/test_server.py`
2. Verify all tests still run: `just test-api`
3. Commit the migration

## Console Tests Migration

Similar approach for `test_console.py`:

**test_buffer.py**:
- `TestConsoleBuffer` (lines 28-337)

**test_service_integration.py**:
- `TestServerServiceConsoleIntegration` (lines 339-603)

**test_history_endpoint.py**:
- `TestConsoleHistoryEndpoint` (lines 605-835)

**test_command_endpoint.py**:
- `TestServerServiceSendCommand` (lines 837-1015)
- `TestConsoleCommandEndpoint` (lines 1209-1397)

**test_websocket.py**:
- `TestConsoleWebSocket` (lines 1018-1207)
- `TestConsoleWebSocketCommands` (lines 1399-1656)

## Timeline

This refactoring was completed in Story 5.0:

1. **Story 5.0 Tasks 6-12**: Migrated `test_server.py` (136 tests) to `tests/server/` package ✅ Done
2. **Story 5.0 Tasks 13-19**: Migrated `test_console.py` (75 tests) to `tests/console/` package ✅ Done
3. **Story 5.2-5.4**: Add new mod tests in `tests/mods/` package (new structure)

## Benefits

1. **Faster test runs**: Can run subset with `just test-api tests/server/test_lifecycle.py`
2. **Better organization**: Easy to find tests for specific functionality
3. **Reduced conflicts**: Smaller files = fewer merge conflicts
4. **Clear ownership**: Each file covers one domain
5. **Easier onboarding**: New developers can understand scope quickly

## Notes

- Keep `conftest.py` fixtures minimal - only truly shared ones
- Each file should be self-contained (import what it needs)
- Maintain the same test structure (class-based, pytest fixtures)
- Preserve all existing test comments and docstrings

---

_Created: 2025-12-28_
