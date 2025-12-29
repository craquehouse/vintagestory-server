# Manual Test Checklist

This checklist contains smoke tests for verifying core functionality before releases and after major changes.

**Last verified:** {{date}}
**Verified by:** {{verifier}}

---

## Pre-Test Setup

Before running manual tests, ensure:

1. [ ] Docker is running
2. [ ] Run `docker compose -f docker-compose.dev.yaml up -d --build`
3. [ ] Wait for container to be healthy (check with `docker compose ps`)
4. [ ] Web UI accessible at `http://localhost:8080`
5. [ ] `.env` file contains valid `VS_API_KEY_ADMIN`

---

## Epic 1: Project Foundation & Health Monitoring

### Health Endpoints

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| 1.1 | Health check | `curl http://localhost:8080/healthz` | Returns `{"status": "ok"}` | [ ] |
| 1.2 | Readiness check | `curl http://localhost:8080/readyz` | Returns `{"status": "ok"}` | [ ] |

### API Documentation

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| 1.3 | OpenAPI docs | Open `http://localhost:8080/docs` | Swagger UI loads with all endpoints | [ ] |
| 1.4 | ReDoc | Open `http://localhost:8080/redoc` | ReDoc documentation loads | [ ] |

### Web UI Shell

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| 1.5 | Homepage loads | Navigate to `http://localhost:8080` | Dashboard page renders | [ ] |
| 1.6 | Sidebar navigation | Click sidebar menu items | Pages change correctly | [ ] |

---

## Epic 2: Authentication & API Security

### API Key Authentication

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| 2.1 | Protected endpoint without key | `curl http://localhost:8080/api/v1alpha1/server/status` | 401 Unauthorized | [ ] |
| 2.2 | Protected endpoint with valid key | `curl -H "X-API-Key: $VS_API_KEY_ADMIN" http://localhost:8080/api/v1alpha1/server/status` | 200 OK with server status | [ ] |
| 2.3 | Invalid API key | `curl -H "X-API-Key: invalid-key" http://localhost:8080/api/v1alpha1/server/status` | 401 Unauthorized | [ ] |

### Role-Based Access Control

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| 2.4 | Admin can access all endpoints | Use admin key for restart endpoint | 200 OK (or appropriate response) | [ ] |
| 2.5 | Monitor key for read endpoints | Use monitor key for status endpoint | 200 OK with status | [ ] |
| 2.6 | Monitor key blocked from write | Use monitor key for restart | 403 Forbidden | [ ] |

### Frontend Authentication

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| 2.7 | API key set in settings | Open web UI, check Settings | Can enter and save API key | [ ] |
| 2.8 | Authenticated API calls | After setting key, check dashboard | Server status shows (not auth error) | [ ] |

---

## Epic 3: Server Lifecycle Management

### Server Status

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| 3.1 | Get server status | `curl -H "X-API-Key: $VS_API_KEY_ADMIN" http://localhost:8080/api/v1alpha1/server/status` | Returns server state JSON | [ ] |
| 3.2 | Status shows in UI | View Dashboard | Server status badge displays | [ ] |

### Server Installation

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| 3.3 | Install server | Click "Install" or call install API | Server downloads and installs | [ ] |
| 3.4 | Version selection | Select a specific version | That version is installed | [ ] |
| 3.5 | Installation progress | Watch during install | Progress shown in UI | [ ] |

### Server Lifecycle Controls

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| 3.6 | Start server | Click Start or call start API | Server starts, status changes to "running" | [ ] |
| 3.7 | Stop server | Click Stop or call stop API | Server stops gracefully | [ ] |
| 3.8 | Restart server | Click Restart or call restart API | Server stops then starts | [ ] |

### Dashboard UI

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| 3.9 | Dashboard loads | Navigate to Dashboard | Shows server status and controls | [ ] |
| 3.10 | Control buttons work | Click Start/Stop/Restart | Buttons trigger correct actions | [ ] |
| 3.11 | Status updates live | Start/stop server | UI updates to reflect new status | [ ] |

---

## Epic 4: Real-Time Console Access

### Console Buffer

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| 4.1 | Console history | Start server, navigate to Console | Shows recent server output | [ ] |
| 4.2 | Live streaming | Watch console while server runs | New lines appear in real-time | [ ] |

### WebSocket Connection

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| 4.3 | WebSocket connects | Open Console page | Connection indicator shows connected | [ ] |
| 4.4 | Reconnection | Restart API container | Console reconnects automatically | [ ] |

### Command Input

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| 4.5 | Send command | Type `/help` in console, press Enter | Command sent, response appears | [ ] |
| 4.6 | Command history | Press Up arrow | Previous command recalled | [ ] |

### Terminal UI

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| 4.7 | Terminal renders | Open Console page | xterm.js terminal displays | [ ] |
| 4.8 | Scroll behavior | Scroll up in console | Can view history | [ ] |
| 4.9 | Theme matches | Toggle dark/light mode | Console colors match theme | [ ] |
| 4.10 | Connection indicator | Check header bar | Shows server status in connection indicator | [ ] |

---

## Epic 5: Mod Management (Placeholder)

_To be filled in during Epic 5 implementation_

### Mod API Integration

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| 5.1 | Search mods | TBD | TBD | [ ] |
| 5.2 | View mod details | TBD | TBD | [ ] |

### Mod Installation

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| 5.3 | Install mod | TBD | TBD | [ ] |
| 5.4 | Compatibility check | TBD | TBD | [ ] |

### Mod Management

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| 5.5 | Enable/disable mod | TBD | TBD | [ ] |
| 5.6 | Remove mod | TBD | TBD | [ ] |
| 5.7 | Pending restart banner | TBD | TBD | [ ] |

### Mod List UI

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| 5.8 | Mod list displays | TBD | TBD | [ ] |
| 5.9 | Install from UI | TBD | TBD | [ ] |

---

## Cross-Cutting Concerns

### Error Handling

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| C.1 | API error response | Trigger a 404 error | Returns standard error envelope | [ ] |
| C.2 | Network error UI | Disconnect network briefly | Shows error toast/message | [ ] |

### Logging

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| C.3 | Structured logs | View container logs | JSON-formatted log entries | [ ] |
| C.4 | Debug mode | Set VS_DEBUG=true | Colorful dev-friendly logs | [ ] |

### Theme

| # | Test | Steps | Expected Result | Status |
|---|------|-------|-----------------|--------|
| C.5 | Dark mode | Toggle to dark mode | Catppuccin Mocha theme applies | [ ] |
| C.6 | Light mode | Toggle to light mode | Catppuccin Latte theme applies | [ ] |
| C.7 | Theme persists | Refresh page | Theme preference maintained | [ ] |

---

## Test Execution Notes

### How to Use This Checklist

1. Copy this file for each test run
2. Fill in date and verifier name
3. Work through each section
4. Mark tests as passing [x] or failing with notes
5. Document any issues found in the "Issues Found" section below

### Issues Found

_Document any issues discovered during verification here:_

| Date | Epic | Test # | Issue Description | Severity | Resolution |
|------|------|--------|-------------------|----------|------------|
| | | | | | |

---

_Last updated: 2025-12-28_
