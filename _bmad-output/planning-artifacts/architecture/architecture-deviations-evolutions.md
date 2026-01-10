# Architecture Deviations & Evolutions

_Added during Epic 5 preparation (2025-12-28)_

This section documents how the actual implementation has evolved from the original architecture specification. These are **intentional evolutions**, not bugs.

## Backend Structure Changes

**Routers (evolved):**

| Original Spec                                    | Actual Implementation                                             | Reason                                                                                       |
| ------------------------------------------------ | ----------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `server.py`, `mods.py`, `config.py`, `health.py` | `server.py`, `health.py`, `console.py`, `auth.py`, `test_rbac.py` | Console became its own router (WebSocket complexity). Auth split out for security isolation. |

**Models (evolved):**

| Original Spec                                      | Actual Implementation                                  | Reason                                                                                                |
| -------------------------------------------------- | ------------------------------------------------------ | ----------------------------------------------------------------------------------------------------- |
| `state.py`, `mods.py`, `responses.py`, `errors.py` | `console.py`, `server.py`, `responses.py`, `errors.py` | Component-specific models (`console.py`, `server.py`) provide better cohesion than generic `state.py` |

**Services (current):**

| Service      | Status         | Notes                                               |
| ------------ | -------------- | --------------------------------------------------- |
| `server.py`  | ✅ Implemented | Handles lifecycle, installation, version management |
| `console.py` | ✅ Implemented | WebSocket streaming, console buffer                 |
| `state.py`   | ⏳ Future       | Will be added when needed for shared state patterns |
| `mods.py`    | ⏳ Epic 5       | Mod management service (Stories 5.1-5.6)            |

## Frontend API Client (enhanced)

The API client layer has been enhanced beyond original specification:

```
web/src/api/
├── client.ts           # Base HTTP client with transforms
├── client.test.ts      # Comprehensive tests
├── error-handler.ts    # Centralized error handling
├── errors.ts           # Error types and utilities
├── query-client.ts     # TanStack Query configuration
├── query-keys.ts       # Query key factory
├── server.ts           # Server API functions
├── types.ts            # API types
└── hooks/              # API-specific hooks
```

**Key enhancement:** Query keys moved to dedicated `query-keys.ts` for consistency and easy maintenance.

## Middleware Layer (added)

Middleware is now a first-class concept with dedicated directory:

```
middleware/
├── auth.py             # API key extraction and validation
└── permissions.py      # Role-based access control
```

This split allows clear separation between authentication (who are you?) and authorization (what can you do?).

---
