# System-Level Test Design

**Project:** vintagestory-server
**Date:** 2025-12-26
**Author:** Matt
**Status:** Draft
**Mode:** System-Level Testability Review (Phase 3)

---

## Executive Summary

This document provides a system-level testability assessment for the VintageStory Server Manager project before the implementation readiness gate check. It evaluates the architecture's testability, identifies Architecturally Significant Requirements (ASRs), defines the test levels strategy, and provides recommendations for Sprint 0 test infrastructure setup.

**Assessment Result:** PASS with minor recommendations

---

## Testability Assessment

### Controllability: PASS

The architecture provides excellent controllability for testing:

| Aspect | Assessment | Evidence |
|--------|------------|----------|
| **State Control** | ✅ Excellent | In-memory StateManager with JSON file sync enables easy state seeding and reset |
| **External Dependency Mocking** | ✅ Excellent | httpx client is mockable with respx; external API calls isolated in ModService |
| **Process Control** | ✅ Good | Game server process managed through ServerLifecycle service with clear start/stop interface |
| **Configuration** | ✅ Excellent | pydantic-settings with environment variables enables test configuration injection |
| **Error Injection** | ✅ Good | Atomic write pattern with temp files allows failure simulation |

**Specific Enablers:**

- Dependency injection pattern in FastAPI allows service mocking
- StateManager's atomic write pattern (temp + rename) is testable
- Environment-based configuration via `pydantic-settings`
- respx library specified for httpx mocking

### Observability: PASS

| Aspect | Assessment | Evidence |
|--------|------------|----------|
| **Structured Logging** | ✅ Excellent | structlog configured for JSON (prod) and console (dev) |
| **Health Endpoints** | ✅ Excellent | `/healthz` and `/readyz` provide system state visibility |
| **API Response Envelope** | ✅ Excellent | Consistent `{"status": "ok|error", "data": {...}}` format |
| **Error Codes** | ✅ Excellent | Centralized error codes in `models/errors.py` |
| **WebSocket State** | ✅ Good | Connection state observable via console buffer |

**Specific Enablers:**

- Health endpoints differentiate API health vs game server health (NFR15)
- Error responses include sufficient context without exposing internals (NFR16)
- Console buffer state trackable in-memory

### Reliability: PASS with Notes

| Aspect | Assessment | Evidence |
|--------|------------|----------|
| **Test Isolation** | ✅ Excellent | Stateless API design, no shared mutable state across requests |
| **Parallel Safety** | ✅ Good | File operations use atomic writes; state manager serializes access |
| **Cleanup Discipline** | ⚠️ Needs Pattern | Tests will need temp directory fixtures for file operations |
| **Determinism** | ✅ Good | No random values in core logic; time can be mocked |
| **Component Coupling** | ✅ Excellent | Clean separation: Routers → Services → Models → External |

**Notes:**

- File system tests should use `pytest` `tmp_path` fixture
- WebSocket tests need connection lifecycle management
- Game server process tests should use mock subprocess

---

## Architecturally Significant Requirements (ASRs)

These are the quality requirements that drive architecture decisions and pose testability challenges:

### High Priority (Score ≥6)

| ASR ID | Requirement | Category | Probability | Impact | Score | Testability Impact |
|--------|-------------|----------|-------------|--------|-------|-------------------|
| ASR-1 | Console output appears within 1 second (NFR1) | PERF | 3 | 2 | 6 | Requires WebSocket latency measurement |
| ASR-2 | API endpoints respond within 500ms (NFR3) | PERF | 2 | 3 | 6 | Requires response time assertions |
| ASR-3 | API survives game server crashes (NFR8) | TECH | 2 | 3 | 6 | Requires process crash simulation |
| ASR-4 | Console restricted to Admin only (FR9, FR34) | SEC | 3 | 3 | 9 | Requires role-based access testing |
| ASR-5 | API keys never logged in plaintext (NFR4) | SEC | 2 | 3 | 6 | Requires log scanning in tests |

### Medium Priority (Score 3-5)

| ASR ID | Requirement | Category | Probability | Impact | Score | Testability Impact |
|--------|-------------|----------|-------------|--------|-------|-------------------|
| ASR-6 | WebSocket auto-reconnect (NFR10) | TECH | 2 | 2 | 4 | Frontend-specific testing |
| ASR-7 | Graceful mod API failures (NFR11) | TECH | 2 | 2 | 4 | Requires external API mocking |
| ASR-8 | Structured JSON logs (NFR14) | OPS | 2 | 2 | 4 | Requires log format validation |
| ASR-9 | Atomic file writes prevent corruption | DATA | 2 | 3 | 6 | Requires crash-during-write simulation |

### Low Priority (Score 1-2)

| ASR ID | Requirement | Category | Probability | Impact | Score | Testability Impact |
|--------|-------------|----------|-------------|--------|-------|-------------------|
| ASR-10 | Console buffer no disk persistence (NFR6) | SEC | 1 | 2 | 2 | Verify no file creation |
| ASR-11 | Failed auth attempts logged (NFR7) | OPS | 1 | 2 | 2 | Log assertion in auth tests |

---

## Test Levels Strategy

Based on the architecture (API + SPA + Docker container):

### Recommended Test Distribution

| Level | Percentage | Rationale |
|-------|------------|-----------|
| **Unit** | 50% | Business logic in services (StateManager, ModService, ServerLifecycle), Pydantic models |
| **Integration** | 35% | API endpoint testing with TestClient, service integration, file I/O |
| **E2E** | 15% | Critical user journeys, WebSocket console, full auth flow |

### Level-Specific Guidance

#### Unit Tests (50%)

**Scope:**

- StateManager atomic write logic
- ModService compatibility calculation
- ServerLifecycle state machine
- Pydantic model validation
- Error code generation
- JSON key transformation

**Tools:** pytest, pytest-asyncio

**Patterns:**

```python
# Pure function tests - no I/O, no external deps
def test_mod_compatibility_calculation():
    assert calculate_compatibility("1.21.3", "1.21.3") == "compatible"
    assert calculate_compatibility("1.21.3", "1.21.0") == "not_verified"
```

#### Integration Tests (35%)

**Scope:**

- API endpoint request/response via FastAPI TestClient
- Authentication middleware behavior
- Service-to-service interactions
- File system operations (with temp directories)
- External API mocking with respx

**Tools:** pytest, httpx, respx, TestClient

**Patterns:**

```python
# API integration test
async def test_health_endpoint(client: TestClient):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

#### E2E Tests (15%)

**Scope:**

- Full authentication flow (Admin and Monitor roles)
- WebSocket console streaming
- Mod install → verify → enable flow
- Server lifecycle: install → start → stop

**Tools:** pytest-asyncio, websockets library, httpx

**Note:** Frontend E2E tests will use Playwright but are scoped to Epic 1.3+ frontend stories.

### Test Level Selection by Feature

| Feature Area | Unit | Integration | E2E |
|--------------|------|-------------|-----|
| StateManager | ✅ High | ✅ Medium | - |
| Authentication | ✅ Medium | ✅ High | ✅ Critical |
| Server Lifecycle | ✅ Medium | ✅ High | ✅ Critical |
| Console Streaming | ✅ Low | ✅ Medium | ✅ Critical |
| Mod Management | ✅ High | ✅ High | ✅ Medium |
| Config Management | ✅ Low | ✅ High | - |
| Health Endpoints | - | ✅ High | - |

---

## NFR Testing Approach

### Security (NFR4-7)

| NFR | Testing Approach | Tools |
|-----|-----------------|-------|
| NFR4: API keys not logged | Capture log output, assert no key values | pytest-caplog |
| NFR5: TLS via proxy | Out of scope (documented, not tested) | - |
| NFR6: Console not persisted | Assert no file creation in data dir | pytest fixtures |
| NFR7: Failed auth logged | Assert log entries on 401 responses | pytest-caplog |

**Security Test Categories:**

- Authentication bypass attempts (missing key, invalid key, wrong role)
- Authorization boundary testing (Monitor accessing Admin endpoints)
- Input validation (path traversal in config endpoints)

### Performance (NFR1-3)

| NFR | Testing Approach | Tools |
|-----|-----------------|-------|
| NFR1: <1s console latency | WebSocket round-trip timing | asyncio timing |
| NFR2: WebSocket preferred | Architecture validation (documented) | - |
| NFR3: <500ms API response | Response time assertions in integration tests | pytest-benchmark (optional) |

**Performance Testing Strategy:**

- Add timing assertions to critical path integration tests
- Defer load testing to post-MVP (single-user scenario)
- Console latency tested in E2E WebSocket tests

### Reliability (NFR8-10)

| NFR | Testing Approach | Tools |
|-----|-----------------|-------|
| NFR8: API survives game crashes | Mock process crash, verify API responsiveness | subprocess mocking |
| NFR9: Graceful crash recovery | Simulate process termination, verify state | pytest fixtures |
| NFR10: WebSocket auto-reconnect | Frontend E2E test (Playwright) | Playwright |

### Observability (NFR14-16)

| NFR | Testing Approach | Tools |
|-----|-----------------|-------|
| NFR14: Structured JSON logs | Validate log format in production mode | pytest-caplog |
| NFR15: Health differentiates API/game | Assert separate status fields | TestClient |
| NFR16: Error context without secrets | Validate error response structure | pytest |

---

## Test Environment Requirements

### Local Development

| Component | Requirement |
|-----------|-------------|
| Python | 3.13 (via mise) |
| Package Manager | uv |
| Test Runner | pytest with pytest-asyncio |
| Mocking | respx (for httpx), unittest.mock |
| Fixtures | temp directories, mock environment variables |

### CI Environment (GitHub Actions)

| Component | Requirement |
|-----------|-------------|
| Container | Python 3.13 official image |
| Services | None (no database, no external services) |
| Parallelization | pytest-xdist for parallel test execution |
| Coverage | pytest-cov with 80% target |

### Test Data Strategy

| Data Type | Strategy |
|-----------|----------|
| State files | Generate in fixtures, cleanup via tmp_path |
| Mod files | Mock download responses with respx |
| Config files | Template fixtures with known content |
| Console buffer | In-memory, no persistence needed |

---

## Testability Concerns

### No Blockers Identified

The architecture has been designed with testability in mind:

1. **Clear service boundaries** enable unit testing
2. **Dependency injection** via FastAPI enables mocking
3. **Stateless request handling** enables parallel testing
4. **Atomic writes** enable crash simulation
5. **Centralized error handling** enables consistent assertions

### Minor Concerns (Recommendations)

| Concern | Impact | Recommendation |
|---------|--------|----------------|
| WebSocket testing complexity | Medium | Create reusable WebSocket test fixtures |
| Process management testing | Medium | Create subprocess mock utilities |
| File system test isolation | Low | Standardize on pytest tmp_path |
| Frontend API mocking | Low | MSW (Mock Service Worker) per architecture |

---

## Recommendations for Sprint 0

### Test Infrastructure Setup

1. **pytest Configuration** (`api/pytest.ini` or `pyproject.toml`)

   ```toml
   [tool.pytest.ini_options]
   asyncio_mode = "auto"
   testpaths = ["tests"]
   addopts = "-v --cov=src/vintagestory_api --cov-report=term-missing"
   ```

2. **Fixtures Module** (`api/tests/conftest.py`)
   - Test client fixture
   - Temp data directory fixture
   - Mock state manager fixture
   - Environment variable overrides
   - respx mock for VintageStory mod API

3. **CI Workflow** (`.github/workflows/ci.yaml`)
   - Backend: lint (ruff) → test (pytest) → coverage check
   - Frontend: lint (eslint) → test (vitest) → build
   - Docker: build image → run health check

### Coverage Targets

| Component | Target | Rationale |
|-----------|--------|-----------|
| API Services | 85% | Core business logic |
| API Routers | 80% | Request handling |
| API Models | 70% | Mostly Pydantic validation |
| Frontend Components | 70% | Component isolation |
| Frontend Hooks | 80% | State management logic |

### Test Naming Convention

- Python: `test_<module>.py` with `test_<scenario>_<expected>` functions
- TypeScript: `<Component>.test.tsx` with `describe/it` blocks
- Pattern: Given-When-Then in docstrings for complex scenarios

---

## Quality Gate Criteria (System-Level)

### Pre-Implementation Gate

- [x] Architecture supports unit testing via service isolation
- [x] Architecture supports integration testing via TestClient
- [x] Architecture supports E2E testing for critical paths
- [x] External dependencies are mockable (httpx + respx)
- [x] File operations use atomic writes for reliability
- [x] No testability blockers identified

### Per-Epic Gate

- [ ] Unit tests pass for all new services
- [ ] Integration tests pass for all new endpoints
- [ ] Coverage ≥80% for critical paths
- [ ] No security test failures
- [ ] Performance assertions pass (where applicable)

### Release Gate (MVP)

- [ ] All P0 tests pass (100%)
- [ ] P1 tests pass rate ≥95%
- [ ] Overall coverage ≥80%
- [ ] No high-severity security findings
- [ ] Health endpoints functional in container

---

## Summary

**Testability Assessment:** PASS

The vintagestory-server architecture is well-designed for testability:

- **Controllability:** Excellent - clean separation, DI patterns, mockable dependencies
- **Observability:** Excellent - structured logging, health endpoints, consistent error format
- **Reliability:** Good - atomic writes, stateless design, clear boundaries

**High-Priority ASRs for Testing:**

1. Console security (Admin-only access)
2. API performance (<500ms response)
3. Console latency (<1s)
4. Crash resilience (API survives game crashes)
5. Security logging (keys not in logs)

**Test Level Strategy:** 50% Unit / 35% Integration / 15% E2E

**Sprint 0 Actions:**

1. Set up pytest configuration with async support
2. Create conftest.py with core fixtures
3. Configure CI workflow with coverage checks
4. Establish test naming conventions

---

**Generated by:** BMad TEA Agent - Test Architect Module
**Workflow:** `_bmad/bmm/testarch/test-design`
**Version:** 4.0 (BMad v6)
