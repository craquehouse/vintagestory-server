# Story 15.2: Runtime API Key for the Web UI

Status: review

## Story

As an **administrator running the published image**,
I want **the web UI to get its API key from my container's configuration**,
so that **one image works for every deployment and no key is baked into it**.

## Acceptance Criteria

1. **Given** `VS_API_KEY` is set on the container
   **When** the web UI loads
   **Then** its requests use that key

2. **Given** `VS_API_KEY` is not set
   **When** the web UI loads
   **Then** it uses the Admin key, matching the existing compose default

3. **Given** an image built from the Dockerfile
   **When** its build arguments, layers and web bundle are inspected
   **Then** they contain no API key
   *(FR165)*

4. **Given** the web dev server with `VITE_API_KEY` in `web/.env`
   **When** a developer runs `just dev-web`
   **Then** the UI authenticates as before

## Tasks / Subtasks

- [x] Task 1: Serve the runtime web configuration (AC: 1, 2)
  - [x] 1.1: `Settings.api_key: str | None` (env `VS_API_KEY`) and a `web_api_key` property returning it, or `api_key_admin` when unset or blank
  - [x] 1.2: `register_frontend` registers `GET /config.js` before the SPA fallback, returning `window.__VSM_CONFIG__ = {"apiKey": ...};` (JSON-encoded) as `application/javascript` with `Cache-Control: no-store`; settings through the `get_settings` dependency
  - [x] 1.3: Tests in `test_frontend_routes.py`: key from `VS_API_KEY`; Admin key fallback (unset and blank); JSON escaping of a key with quotes or `</script>`; headers; the route wins over a `config.js` file in the static directory (that the key is not logged is checked in the container, Task 4.2)

- [x] Task 2: Web client reads the runtime key (AC: 1, 2, 4)
  - [x] 2.1: `index.html` loads `<script src="/config.js"></script>` before the module script
  - [x] 2.2: `web/public/config.js` placeholder (`window.__VSM_CONFIG__ = window.__VSM_CONFIG__ || {};`) for the dev server; the API route takes precedence in the image
  - [x] 2.3: `client.ts` `getConfig()`: `window.__VSM_CONFIG__?.apiKey || import.meta.env.VITE_API_KEY || ''`; `Window.__VSM_CONFIG__` typed in `src/globals.d.ts`
  - [x] 2.4: Tests in `client.test.ts`: runtime key sent; runtime key wins over `VITE_API_KEY`; empty runtime key falls back to `VITE_API_KEY`

- [x] Task 3: No key in the image (AC: 3)
  - [x] 3.1: Dockerfile: remove `ARG VS_API_KEY` and `VITE_API_KEY` from the web build; keep `VITE_API_BASE_URL=""`
  - [x] 3.2: `.dockerignore`: exclude `.env` files at any depth (`**/.env`, `**/.env.*`, keep `**/.env.example`); today only the root `.env` is excluded, so `web/.env` reaches the build and Vite would bake its `VITE_API_KEY` once the build argument is gone
  - [x] 3.3: `docker-compose.dev.yaml`: remove the `VS_API_KEY` build argument; keep the runtime `VS_API_KEY` environment line; update comments in `docker-compose.yaml` if they mention the build-time key

- [x] Task 4: Verification and validation (AC: all)
  - [x] 4.1: Build the image with `web/.env` present; confirm `docker history`/`inspect` show no key argument and the bundle contains neither the `web/.env` key nor the runtime key (compare without printing the key)
  - [x] 4.2: Run the image with `VS_API_KEY_ADMIN` only, then with a different `VS_API_KEY`; in a browser the UI loads data both times and requests carry the expected key (check the request header, not just the page); console clean apart from known errors
  - [x] 4.3: `just dev-web` against `just dev-api` still authenticates with `web/.env` (or confirm with a Vite dev server smoke check)
  - [x] 4.4: `just check`; update the Dev Agent Record and File List

## Dev Notes

### Scope

FR165, Epic 15 ADR-5. Out of scope: a login screen; README wording on exposure (Story 15.6). Exposure is unchanged from today: anyone who can load the page receives the key.

### Current state

- `web/src/api/client.ts:28` `getConfig()` reads `import.meta.env.VITE_API_BASE_URL` and `VITE_API_KEY`; every request (including the WebSocket token request) goes through `apiClient`.
- Dockerfile web stage: `ARG VS_API_KEY=""` and `RUN VITE_API_KEY="${VS_API_KEY}" VITE_API_BASE_URL="" bun run build`.
- `docker-compose.dev.yaml` passes `VS_API_KEY` as a build argument and sets `VS_API_KEY=${VS_API_KEY_ADMIN:-changeme}` at runtime; `docker-compose.yaml` sets the same runtime variable.
- `api/src/vintagestory_api/main.py` `register_frontend(target, static_dir)` mounts `/assets` and a catch-all SPA route; tests in `api/tests/test_frontend_routes.py` build a fresh `FastAPI()` and call it.
- `Settings` (`config.py`) uses `env_prefix="VS_"`; `get_settings()` in `middleware/auth.py` returns `Settings()`.
- `.dockerignore` has `.env`, `.env.*`, `!.env.example`, which match only at the context root.
- Many web tests set `import.meta.env.VITE_API_KEY = 'test-api-key'`; they keep working because the runtime config is absent under Vitest.

### Rules

- ADR-5: unauthenticated, uncached `/config.js`; key from `VS_API_KEY`, else `VS_API_KEY_ADMIN`; never log the key.
- Commit types by user impact: the runtime key is `feat`; the `.dockerignore` and Dockerfile changes are `fix`/`build`; tests `test`.
- No lint or type suppressions.

### Testing Requirements

- API: pytest (`test_frontend_routes.py`, `test_config.py` if settings tests live there).
- Web: Vitest (`client.test.ts`).
- Browser verification against the built image is required.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 15.2]
- [Source: _bmad-output/planning-artifacts/architecture/epic-15-release-engineering.md] ADR-5
- [Source: _bmad-output/implementation-artifacts/15-1-single-version-source-and-version-display.md] image verification pattern

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5)

### Debug Log References

- Browser screenshot kept locally only (`.playwright-mcp/story-15-2-monitor-key.png`, git-ignored).

### Completion Notes List

- Task 1: `Settings.api_key` (`VS_API_KEY`) and `Settings.web_api_key` (that key, or `api_key_admin` when unset or blank). `register_frontend` registers `GET /config.js` before the SPA fallback; it returns `window.__VSM_CONFIG__ = {"apiKey": …};` built with `json.dumps` (non-ASCII escaped), `application/javascript`, `Cache-Control: no-store`, excluded from the OpenAPI schema, settings through `get_settings`. 3 settings tests, 5 route tests (key, fallback, encoding of quotes, `</script>` and U+2028, headers, precedence over a built `config.js`). The "not logged" check needs the real middleware stack, so it was done in the container (Task 4.2).
- Task 2: `index.html` loads `/config.js` as a classic script before the module; `web/public/config.js` is the dev-server placeholder (copied to `dist/`, shadowed by the API route in the image); `getConfig()` prefers `window.__VSM_CONFIG__.apiKey`, then `VITE_API_KEY`; `Window.__VSM_CONFIG__` typed in `globals.d.ts`. 4 new client tests. Vite builds without warnings.
- Task 3: the Dockerfile has no key argument and builds with `VITE_API_KEY=""`. **Found:** `.dockerignore`'s `.env` patterns matched only the context root, so `web/.env` (a developer's `VITE_API_KEY`) reached the web build stage; once the argument was gone, Vite would have built it in. Now `**/.env` and `**/.env.*` (keeping `**/.env.example`). Both compose files set `VS_API_KEY=${VS_API_KEY:-}` (empty means the Admin key) instead of forcing the Admin key, and the dev compose file has no build argument. With the maintainer's `.env`, `VS_API_KEY` equals the Admin key, so the dev stack behaves as before.
- Task 4: built the image with `web/.env` present. The `web/.env` key occurs 0 times in the extracted bundle (compared without printing it); the image's `config.js` is the placeholder; `docker history` and the image environment carry no key; the web build stage contains only `.env.example`. Run with `VS_API_KEY_ADMIN` only: `/config.js` serves the Admin key, requests send it (checked on the request header), API calls return 200. Run with `VS_API_KEY` set to the Monitor key: requests send the Monitor key and return 200. Neither key appears in the container logs. Console: only the known `404 /api/v1alpha1/config/game` with no game server installed. The Vite dev server serves the placeholder before the app, so the client falls back to `VITE_API_KEY` (covered by the client tests). `just check` passes: 2060 API tests (+8), 3007 web tests (+6 including the Story 15.1 review tests), 23 script assertions.

### File List

- Modified: `api/src/vintagestory_api/config.py`, `api/src/vintagestory_api/main.py`
- Modified: `api/tests/test_config.py`, `api/tests/test_frontend_routes.py`
- Modified: `web/index.html`, `web/src/api/client.ts`, `web/src/api/client.test.ts`, `web/src/globals.d.ts`
- Created: `web/public/config.js`
- Modified: `Dockerfile`, `.dockerignore`, `docker-compose.yaml`, `docker-compose.dev.yaml`

## Change Log

- 2026-11-10: Story created.
- 2026-11-10: Implemented; fixed `.dockerignore` letting `web/.env` into the build; verified in the image and a browser. `just check` passes. Status review.
