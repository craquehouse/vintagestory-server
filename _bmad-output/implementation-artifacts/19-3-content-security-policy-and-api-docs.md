# Story 19.3: Content-Security-Policy and API Docs

Status: ready-for-dev

<!-- Implements FR213-FR217, Epic 19 ADR-6 and ADR-7. Beads: VSS-3qb8 (INFRA-005, size-m), VSS-my4c (UI-102, size-s), VSS-5mes (API-088, size-s). Stacked on Story 19.2 (stories run in order 19.1 to 19.7): this story uses 19.2's app factory, its cached settings object and its /config.js E2E helper, none of which exist at the commit this story was written against. Line references were verified at b6ae2f2 (epic-19-planning; api/ and web/ as on main after Epic 18) and must be re-checked at implementation time: Stories 19.1 and 19.2 edit config.py, main.py, .env.example, README.md and the compose files first. API and web change, API tests, web unit tests, one E2E spec, README and .env.example. No new dependencies. -->

## Story

As an **operator**,
I want **every page the manager serves to run under a Content-Security-Policy**,
so that **an injected script cannot run on an origin that holds an API key**.

## Acceptance Criteria

1. **Given** the published image
   **When** I request `/` or any web UI path
   **Then** the response has `Content-Security-Policy` with exactly the directives of Epic 19 ADR-6 decision 3 (the header value in Dev Notes "The policy"), and `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer` and `X-Frame-Options: DENY`
   *(Covers FR213, FR215; `VSS-3qb8`. The epic text says "ADR-5 decision 3"; the policy is ADR-6 decision 3.)*

2. **Given** the same image
   **When** I request `/api/v1alpha1/...`, `/healthz` or `/readyz`
   **Then** the response has no `Content-Security-Policy` and no `Content-Security-Policy-Report-Only` header
   *(Covers FR213)*

3. **Given** the Docker stack with the policy enforced
   **When** I open the dashboard, the console, the mod browser, a mod detail page with a gallery and a description with images, the installed list, the game settings, the version page and the settings page (`/config`), in the light and the dark theme
   **Then** each page works as before, the browser reports no `securitypolicyviolation` event and no console error, and toasts, dialogs and the terminal are styled
   *(Covers FR214)*

4. **Given** the console page with the policy enforced
   **When** it connects
   **Then** the console WebSocket and the log stream connect and carry data
   *(Covers FR214)*

5. **Given** a page of the web UI with the policy enforced
   **When** an inline script is injected into it, or the page is loaded inside a frame on another origin
   **Then** the script does not run and the frame does not load
   *(Covers FR213)*

6. **Given** a mod description with an image on any `https` host
   **When** I open the mod's detail page
   **Then** the image loads
   *(Covers FR214)*

7. **Given** `VS_CSP_MODE=report-only`, `VS_CSP_MODE=off`, and an unknown value
   **When** the API starts
   **Then** with `report-only` the same policy is sent as `Content-Security-Policy-Report-Only` (and no `Content-Security-Policy`), with `off` neither header is sent, an unset or blank value means `enforce`, and an unknown value stops start-up with a message naming `VS_CSP_MODE` and the three valid values
   *(Covers FR215)*

8. **Given** the Vite dev server (`just dev-web`)
   **When** I develop
   **Then** no policy applies and hot reload works as before (no change to `web/index.html` or `web/vite.config.ts`)
   *(Covers FR214)*

9. **Given** a mod description with an `<img>` whose address is `http:`, relative, or anything other than `https:` or a `data:image/` URL
   **When** I open the mod's detail page
   **Then** the image is replaced by the text "Image not shown: `<alt>`" ("Image not shown" without alt text), no request is made for it, no broken-image icon is shown, and the browser reports no policy violation
   *(Covers FR216; `VSS-my4c`)*

10. **Given** the image started without `VS_DEBUG=true`
    **When** I request `/docs`, `/redoc` or `/openapi.json`
    **Then** none of them serves the API documentation or the schema (in the image each returns the web UI's page with the headers of AC 1; without the built frontend each is 404), and no response from the manager loads a script from another origin
    *(Covers FR217; `VSS-5mes`)*

11. **Given** the API started with `VS_DEBUG=true`
    **When** I open `/docs`
    **Then** the API documentation renders as before, without the web UI's policy, and `/redoc` and `/openapi.json` are served as before
    *(Covers FR217)*

12. **Given** the API tests
    **When** they check the documentation paths and the RBAC test routes
    **Then** they build one app with debug on and one with debug off through the app factory and assert both, and `main.py` no longer calls `Settings()` itself
    *(Covers FR217)*

13. **Given** every existing test
    **When** the suites run
    **Then** they pass, apart from the changes listed in Dev Notes "Existing tests that change"; no test run writes into the dev data directory (`dev/`)

## Tasks / Subtasks

<!-- Each functional task includes its tests in the same commit. Commit per task: type(story-19.3/task-N): ...; feat/fix only for changes an operator or admin can see, subject written for them. Red first. The epic lists six tasks; its "API tests" task is folded into Tasks 1, 3 and 4 (tests ride with the code, as in 17.x and 18.x), and the quality gate is Task 6. -->

- [x] Task 1: `VS_CSP_MODE`, the policy constant and the headers on the web UI's responses + tests (AC: 1, 2, 7, 13) (`VSS-3qb8`)
  - [x] 1.1: `config.py` `Settings`: new field `csp_mode: str = "enforce"` after `mod_cache_max_size_mb` (`:29`), with a comment naming `VS_CSP_MODE` and Epic 19 ADR-6. A `field_validator("csp_mode")` in the style of the others (`:42-126`): strip and lower-case the value; a blank value means unset and becomes `enforce` (Dev Notes "Headers by mode"); if it is otherwise not one of `enforce`, `report-only`, `off`, raise `ValueError("VS_CSP_MODE must be one of: enforce, report-only, off.")`; return the normalized value. A plain `str` with a validator, not a `Literal`: pydantic's own message for a `Literal` names `csp_mode`, not `VS_CSP_MODE` (AC 7)
  - [x] 1.2: `main.py`: the policy as one module-level constant, `CONTENT_SECURITY_POLICY`, built from a tuple of the eleven directives joined with `"; "` (Dev Notes "The policy"), placed above `_resolve_frontend_file` (`:230`). One pure function `frontend_security_headers(csp_mode: str) -> dict[str, str]` next to it (Dev Notes "Headers by mode")
  - [x] 1.3: `main.py` `serve_spa` (`:275-278`): return `FileResponse(_resolve_frontend_file(static_root, full_path), headers=frontend_security_headers(<mode>))`. It gets the mode from the same settings object `serve_runtime_config` (`:260-272`) uses after Story 19.2: if that route still takes `settings: Settings = Depends(get_settings)`, `serve_spa` takes the same dependency; if 19.2 made `register_frontend` take the settings, use that argument. One mechanism for both routes. The headers go on every `serve_spa` response (the fallback page and files such as `/vite.svg`), not on `/assets` (a `StaticFiles` mount, `:253`) and not on `/config.js`, which keeps its own three headers. Update the comment at `:274` and the `register_frontend` docstring
  - [x] 1.4: No middleware, no `<meta>` tag, nothing in `web/index.html` or `web/vite.config.ts` (ADR-6 decisions 1, 2 and 11; AC 8)
  - [x] 1.5: Tests (Dev Notes "API tests", Task 1 rows), red first; the change in "Existing tests that change" for `FakeFileResponse`
  - [x] 1.6: Commit `feat(story-19.3/task-1): serve the web UI with a Content-Security-Policy (VS_CSP_MODE)`

- [x] Task 2: Browser checks on the Docker stack before anything else is built on the policy (AC: 3, 4, 5) (ADR-6 decisions 7 and 12)
  - [x] 2.1: Rebuild the dev stack from the branch (`just docker restart`; do not start or stop the game server) and confirm `curl -s -D- -o /dev/null http://localhost:8080/` shows the four headers of AC 1
  - [x] 2.2: In a Chromium browser driven by Playwright, with a `securitypolicyviolation` listener added by `page.addInitScript` and the console recorded, load `/game-server/console` and one other page in the light and the dark theme. Record in the Dev Agent Record, for each of the two questions, what was seen: (a) the next-themes inline `<script>` element is in the DOM; is there a `script-src` violation or console message for it? (b) does the console WebSocket (`/api/v1alpha1/console/ws`) open and stay open under `connect-src 'self'`, and the log stream (`/api/v1alpha1/console/logs/ws`) when a log file is chosen in `source-selector` (only if the stack lists a log file)? The story's prototype saw no violation for (a) and a working console socket for (b) (Dev Notes "Browser checks"); this task repeats it on the real image
  - [x] 2.3 (not needed: no violation): Only if (a) shows a violation: add that script's `'sha256-...'` hash (taken from the browser's console message) to `script-src` in the constant, record the hash and the next-themes version (`web/node_modules/next-themes/package.json`, 0.4.6 at b6ae2f2) in a comment beside it and in the Dev Agent Record, and add the hash to the API test's expected value. Never add `'unsafe-inline'` or `'unsafe-eval'` to `script-src`
  - [x] 2.4 (not needed: both sockets connected): Only if (b) fails in a supported browser: Dev Notes "WebSocket fallback". Record which browser and version
  - [x] 2.5: If neither fallback was needed, this task has no code change: record the observations (browser, version, what was seen) in the Dev Agent Record and commit the story file as `chore(story-19.3/task-2): record the browser checks for the policy` (the dev-story workflow wants a commit per task; `chore` has no release note). If a fallback was needed, commit it as `fix(story-19.3/task-2): ...` with a subject an operator understands (for example `the console connects under the Content-Security-Policy in <browser>`)

- [ ] Task 3: The sanitizer replaces description images the policy would block + tests (AC: 6, 9, 13) (`VSS-my4c`)
  - [ ] 3.1: `web/src/lib/mod-description.ts`: in the existing `afterSanitizeAttributes` hook (`:33-55`), before the link branch, handle HTML `<img>` elements (Dev Notes "The image rule"). Export the two texts as constants (`IMAGE_NOT_SHOWN = 'Image not shown'`) so tests and the E2E do not repeat literals; update the module comment (`:1-15`) with the new rule
  - [ ] 3.2: `web/src/styles/index.css`: one rule beside the `.mod-description` rules (`:248-263`): `.mod-description [data-image-not-shown] { @apply text-muted-foreground text-sm italic; }` (the description's own text color comes from `prose-invert`, `ModDetailPage.tsx:783`; check both themes in Task 5's E2E run that the note is readable)
  - [ ] 3.3: Tests in `web/src/lib/mod-description.test.ts` (Dev Notes "Web tests"), red first. The existing test `keeps images and inline styles as the detail page shows them today` (`:231-237`) uses an `https` image and stays as it is
  - [ ] 3.4: Commit `fix(story-19.3/task-3): mod description images that cannot be loaded securely show a note instead of a broken image`

- [ ] Task 4: The API documentation pages only in debug mode, set in the app factory; no `Settings()` call left in `main.py` + tests (AC: 10, 11, 12, 13) (`VSS-5mes`)
  - [ ] 4.1: In Story 19.2's app factory (called `create_app(settings)` in this story; use its real name and signature), pass `docs_url="/docs" if settings.debug else None`, `redoc_url="/redoc" if settings.debug else None` and `openapi_url="/openapi.json" if settings.debug else None` to `FastAPI(...)` (at b6ae2f2 the constructor is `main.py:165-170`). No new setting (ADR-7 decisions 1 and 5)
  - [ ] 4.2: Move the two remaining import-time `Settings()` uses into the factory, reading the factory's settings argument: the CORS origins (`settings = Settings()` at `:177`, used at `:188`) and the RBAC test router gate (`if Settings().debug:` at `:219-221`). After this task `grep -n "Settings()" api/src/vintagestory_api/main.py` finds nothing (AC 12). Behavior is unchanged: the same middleware in the same order (`:186-200`), the same routers, the `test_rbac_router_enabled` warning as before. Services that build their own `Settings()` are not part of this epic (ADR-5 decision 11)
  - [ ] 4.3: Tests (Dev Notes "API tests", Task 4 rows), red first; `test_version.py`, `test_debug_gating.py` and `test_main.py` as listed in "Existing tests that change"
  - [ ] 4.4: Commits: if 4.2 is separable, first `refactor(story-19.3/task-4): build the CORS and RBAC test wiring from the app's settings object` (no release note), then `fix(story-19.3/task-4): serve the API documentation pages only when VS_DEBUG is on`. One `fix` commit with that subject is also fine. Not marked breaking: no `!`, no `BREAKING CHANGE:` footer (maintainer decision, 2026-11-17)
  - [ ] 4.5: `just changelog` lists the subject of 4.4 under Fixes and the subject of 1.6 under Features, and nothing from this story under Breaking Changes; paste the three lines into the Dev Agent Record

- [ ] Task 5: E2E spec against the Docker dev stack, README and `.env.example` (AC: 1, 2, 3, 4, 5, 6, 9) (ADR-6 decision 13)
  - [ ] 5.1: New `web/e2e/content-security-policy.spec.ts` (Dev Notes "E2E"). Read-only: every write to the API is refused, mod data is stubbed, nothing is installed or changed, the game server is neither started nor stopped, no screenshot. It gets its key through Story 19.2's `/config.js` helper in `web/e2e/` (do not copy another `readOnly` helper's own `/config.js` route)
  - [ ] 5.2: Rebuild the stack from this branch (`just docker restart`), run `cd web && bunx playwright test e2e/content-security-policy.spec.ts` with `VS_API_KEY_ADMIN` exported; also re-run `e2e/mod-detail-media.spec.ts`, `e2e/mod-detail-bad-data.spec.ts`, `e2e/layout-widths.spec.ts` and `e2e/terminal.spec.ts`, which load the pages the policy touches. Record the results, and that `GET /api/v1alpha1/mods` returned the same body before and after the run
  - [ ] 5.3: `README.md`: a `VS_CSP_MODE` row in the Configuration table (`:70-77`); the `VS_DEBUG` row (`:76`) also says it serves the API documentation at `/docs` and the RBAC test routes, so it is for development; two or three sentences in "Security" (`:35-37`): the web UI's pages are sent with a Content-Security-Policy, what `report-only` and `off` are for (a proxy that injects scripts or styles, or a dashboard that frames the UI), and that the pages cannot be framed while the mode is `enforce`. `.env.example`: a `VS_CSP_MODE` block after `VS_DEBUG` (`:30-33`) with the three values and the default, and the `VS_DEBUG` comment gains the `/docs` sentence. The compose files need no entry: both pass `.env` through `env_file` (`docker-compose.yaml:26-28`, `docker-compose.dev.yaml:25-27`); say so in the PR, and confirm with `VS_CSP_MODE=report-only` in `.env` and `curl` (then remove it and rebuild)
  - [ ] 5.4: `_bmad-output/planning-artifacts/architecture/project-structure-boundaries.md`: add `VS_CSP_MODE` to its environment table (`:471` is the `VS_DEBUG` row) if Stories 19.1 and 19.2 updated that table for their variables; otherwise leave it and note it for the maintainer
  - [ ] 5.5: Commits `test(story-19.3/task-5): ...` for the spec and `docs(story-19.3/task-5): ...` for README and `.env.example`

- [ ] Task 6: Quality gate and review hand-off (AC: all)
  - [ ] 6.1: `just check` passes; the diff adds no lint or type suppression and no `cast`; pyright stays at 0 errors and the 3 pre-existing warnings (`VSS-1ar`); web tests keep the 4 pre-existing skips (`VSS-hnl`); after `just test-api`, `git status --short` shows nothing under `dev/`
  - [ ] 6.2: Manual check on the Docker stack (needs the maintainer's confirmation before it is ticked, `project-context.md`): Dev Notes "Manual check"
  - [ ] 6.3: Story status `review`, `just sprint set 19-3-content-security-policy-and-api-docs review`, PR (base: Story 19.2's branch while its PR is open, otherwise `main`), PR link on `VSS-3qb8`, `VSS-my4c` and `VSS-5mes`. The PR description lists "API contract changes" from this story and the follow-ups under "Not changed"

## Dev Notes

### Current state (verified at b6ae2f2)

- **No policy.** `serve_spa` (`main.py:275-278`) returns a bare `FileResponse`; the middleware are CORS, CORS logging and request context (`:186-200`); `web/index.html` has no CSP `<meta>`. The built `index.html` has two same-origin scripts (the module bundle and `<script src="/config.js">`), one linked stylesheet, no inline script and no inline style. A local build has no `eval(` or `new Function(` in `web/dist/assets`.
- **Docs pages.** `FastAPI(...)` (`main.py:165-170`) sets no `docs_url`, `redoc_url` or `openapi_url`, so all three are served without a key. `Settings()` is constructed three times in `main.py` (`:96` lifespan, `:177` CORS, `:219` RBAC gate); Story 19.2 replaces the first and adds the factory, this story removes the other two.
- **Debug.** `docker-compose.dev.yaml:22` sets `VS_DEBUG=true`; `docker-compose.yaml:23` defaults it to `false`; `api/tests/conftest.py:11` sets `VS_DEBUG=true` before importing the app. So the dev stack and the test suite's module-level `app` are debug apps. `Settings.debug` (`config.py:18`) is what gates routes; `initialize_debug_state()` (`config.py:223-236`) reads the same variable for log levels and is not touched.
- **Description images.** `sanitizeModDescription` (`web/src/lib/mod-description.ts:66-68`) keeps `<img>` with any `src` DOMPurify accepts. The only caller is `ModDetailPage.tsx:785`.

### The policy

Header value, one line, directives in this order, joined with `; `, no trailing semicolon:

```
default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self'; frame-src 'none'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'
```

The API test compares the whole string, so a changed directive is a deliberate edit in two places. Reasons for each directive are in ADR-6 decisions 4 to 8; do not loosen one without the maintainer.

### Headers by mode

| `VS_CSP_MODE` | `Content-Security-Policy` | `Content-Security-Policy-Report-Only` | `X-Frame-Options: DENY` | `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer` |
|---|---|---|---|---|
| `enforce` (default) | the policy | absent | sent | sent |
| `report-only` | absent | the policy | absent | sent |
| `off` | absent | absent | absent | sent |

- `X-Frame-Options: DENY` is the older form of `frame-ancestors 'none'` (ADR-6 decision 8). ADR-6 does not say what it does in the other two modes. It follows the policy here: if it stayed on, an operator whose dashboard frames the UI could not get out of trouble with `VS_CSP_MODE`, which is what the setting is for (decision 10). This is a decision of this story; see "ADR against the code".
- `nosniff` and `Referrer-Policy: no-referrer` are sent in every mode; neither can break a page.
- `frontend_security_headers` is pure and takes the validated mode, so it is tested without an app.
- `FileResponse(path, headers=...)` keeps its own `content-type`, `etag` and `last-modified`; the prototype confirmed the four headers on `/vite.svg` and on the fallback page.
- **A blank `VS_CSP_MODE` is the default, not an error.** `VS_CSP_MODE=` in `.env` reaches `Settings` as an empty string. Refusing it would stop the API, and with it the game server it supervises, over an empty line (the reasoning of ADR-5 decision 3, and how a blank `VS_API_KEY` is treated). ADR-6 decision 10 says "any other value fails"; the story reads a blank value as no value. See "ADR against the code".
- An unknown mode never reaches the function: `Settings` refuses it. The module-level `app` is built from `get_settings()`, so the process exits at import with pydantic's `ValidationError`, whose text contains the validator's message. That is "stops start-up" (AC 7); no extra handling.

### Browser checks (Task 2): what the prototype saw

Prototype at b6ae2f2: the headers of Task 1 on `serve_spa`, the web built with `vite build`, served by the API on one local port, no game server; Playwright 1.65.1 driving Chrome for Testing 156 (headless shell); a `securitypolicyviolation` listener from `page.addInitScript`. Since discarded.

- **Every page, both themes:** `/`, `/game-server/console`, `/game-server/mods/browse`, a stubbed mod detail page, `/game-server/mods/installed`, `/game-server/settings`, `/game-server/version`, `/config`: no violation event, except the one for a plain `http:` description image, which Task 3 removes.
- **next-themes (decision 12):** the inline `<script>` element is in the DOM on every page, and Chromium reported no violation and no console message for it. React creates the element on the client and the browser never tries to run it, so no hash was needed. The theme class was applied on load and after the header's "Toggle theme" button. Expected outcome of Task 2: no hash. If a browser does report it, Task 2.3.
- **WebSocket (decision 7):** with the server status stubbed as installed, the console page opened `ws://<host>/api/v1alpha1/console/ws?...` under `connect-src 'self'`, and it stayed open with no error and no violation. No frames arrived because no game server was running. The log stream was not exercised (no log file without an installed server). Expected outcome: no `ws:` source. Firefox and Safari were not available to the prototype; Task 6.2 asks the maintainer to look at one of them.
- **Styles:** the terminal rendered with xterm's injected styles (4 `<style>` elements on the console page) and its font under `font-src 'self'`.
- **Control:** a script element with inline text appended to the page did not run and produced a `script-src-elem` violation; the page framed from another origin did not load (`chrome-error://chromewebdata/`).
- **A stack without a game server** shows "Server Not Installed" on the console and mods pages, so no socket opens and no mod page renders; and `GET /api/v1alpha1/config/game` answers 404, which the browser logs as a console error. The E2E spec therefore stubs the server status and the game config (Dev Notes "E2E").

### WebSocket fallback (Task 2.4, only if needed)

ADR-6 decision 7: add `ws:` and `wss:` sources for the request's host. That makes the header depend on the request, so:

- Build the `connect-src` directive per request as `connect-src 'self' ws://<host> wss://<host>`, where `<host>` is the request's `Host` header, used only if it matches `^[A-Za-z0-9.-]+(:[0-9]{1,5})?$` or a bracketed IPv6 form `^\[[0-9A-Fa-f:]+\](:[0-9]{1,5})?$`. The `Host` header is the client's input; a value with a space, `;` or `,` would add directives. If it does not match, send the constant policy unchanged.
- Never the bare schemes `ws:` and `wss:`: they allow a socket to any host.
- Add API tests: a normal host, a host with a port, an IPv6 host, and a hostile host (`evil.test; script-src *`) that leaves the policy unchanged. Update the E2E's expected header to a pattern.

### The image rule (Task 3)

```ts
// in the afterSanitizeAttributes hook, before the link branch
if (node.nodeName === 'IMG' && node.namespaceURI === HTML_NAMESPACE) {
  node.removeAttribute('srcset');
  node.removeAttribute('sizes');
  if (!isLoadableImage(node.getAttribute('src'))) {
    const alt = (node.getAttribute('alt') ?? '').trim();
    const note = node.ownerDocument.createElement('span');
    note.setAttribute('data-image-not-shown', '');
    note.textContent = alt ? `${IMAGE_NOT_SHOWN}: ${alt}` : IMAGE_NOT_SHOWN;
    node.replaceWith(note);
  }
  return;
}
```

- **`isLoadableImage(src)`**: true only when `src` is not null and matches `/^https:\/\//i` or `/^data:image\//i`. The test is on the attribute text, deliberately strict: `https:foo.png` without `//` is a relative URL on an `https` page, `//host/a.png` takes the page's scheme, and a `src` with a control character inside the scheme fails the test and is replaced, which is the safe side. DOMPurify has already trimmed leading spaces by the time the hook runs (the prototype's `" https://..."` came out as `https://...`) and has removed a `javascript:` `src`, which leaves an `<img>` without `src`; that is replaced too.
- **No rewrite to `https`** (ADR-6 decision 14): it would be a guess.
- **`srcset` and `sizes` are removed from every description `<img>`.** DOMPurify keeps `srcset`, and the browser would pick a candidate from it instead of `src`, so an `https` `src` with an `http` `srcset` would still request the blocked image. Without this AC 9's "no request is made" is not true of an `<img>`. ADR-6 decision 14 names `src` only; see "ADR against the code".
- **The note** is a `<span>` built with `createElement` and `textContent`, like the new-tab note (`:48-52`), so alt text is never parsed as markup (prototype: an alt of `<b>bold</b>` came out escaped). It carries `data-image-not-shown` for the CSS rule and the tests.
- **Replacing the node inside the hook is safe:** the prototype replaced four images in one description, one inside a link and one between paragraphs, and DOMPurify's walk continued correctly; the 134 tests of `mod-description.test.ts` and `ModDetailPage.test.tsx` passed with the hook in place.
- **Inside a link** the note becomes the link's text, followed by the existing screen reader note. Sanitizing the output again leaves the note and adds no second one.
- **A mod author can write `<span data-image-not-shown>` themselves.** It only gets the muted style; nothing depends on the attribute for safety.
- **The rule does not depend on how the page is served** (decision 14): it also applies under the Vite dev server and with `VS_CSP_MODE=off`.

### The docs routes and the app factory (Task 4)

- **How they plug in.** `docs_url`, `redoc_url` and `openapi_url` are constructor arguments of `FastAPI`, so they are decided where the factory builds the app from its settings. FastAPI registers the three routes in its constructor, before any router and before the frontend's catch-all, so in debug mode they win over `serve_spa`. With `None` they are not registered, and neither is `/docs/oauth2-redirect`.
- **Debug off, frontend present (the image):** `/docs`, `/redoc` and `/openapi.json` fall through to `serve_spa` and return `index.html` with the headers of Task 1 (ADR-7 decision 3). The router then shows whatever the web app shows for an unknown path. **Debug off, no frontend:** 404.
- **Debug on:** served as today, from the CDN, with none of Task 1's headers, because those are set by `serve_spa` only.
- **`app.openapi()` still works** when `openapi_url` is `None`; `tests/test_routers_config.py:1637` calls it and needs no change.
- **Assumed from Story 19.2 (not in the tree at b6ae2f2):** a factory that takes a `Settings` and returns the app; a module-level `app` built from the cached `get_settings()` (`middleware/auth.py:23-30`) for the server; the lifespan using `get_settings()`. If 19.2's factory also registers the frontend, the tests below pass a static directory the way 19.2's tests do; if not, they call `register_frontend(app, static_dir)` on the built app as `tests/test_frontend_routes.py:36-40` does. If 19.2 left any part of this undone, stop and raise it; do not build a second factory.
- **CORS** (`:186-193`) reads `settings.cors_origins.split(",")`; keep the comment block about middleware order (`:172-184`) with the code when it moves.

### API tests

| Task | File | Test |
|---|---|---|
| 1 | `tests/test_config.py`, new `TestCspMode` after `TestCorsOriginsValidation` (`:309`) | Default is `enforce`. `VS_CSP_MODE` from the environment (`monkeypatch.setenv`) for each valid value. ` Report-Only ` (spaces, upper case) normalizes to `report-only`. The empty string and a string of spaces give `enforce`. `bogus`, `enforced` and `report_only` raise `ValidationError` whose text contains `VS_CSP_MODE must be one of: enforce, report-only, off.` |
| 1 | `tests/test_frontend_routes.py`, new `TestSecurityHeaders` (fixtures `static_dir` `:19-33`; build the client as `TestRuntimeConfig._client` does, `:117-121`, with a `Settings(api_key_admin="admin", csp_mode=...)`) | `enforce`: `GET /`, `/dashboard`, `/game-server/mods/browse/x` and the file `/favicon.ico` each have `content-security-policy` equal to the whole string of "The policy" (written out in the test, not imported from `main`), `x-content-type-options: nosniff`, `referrer-policy: no-referrer`, `x-frame-options: DENY`, and no `content-security-policy-report-only`. `report-only`: the same string under `content-security-policy-report-only`, no `content-security-policy`, no `x-frame-options`, the other two present. `off`: neither policy header, no `x-frame-options`, the other two present. Parametrize over the modes |
| 1 | same class | `/config.js` keeps exactly its three headers and has no policy header; `/assets/main.js` has no policy header (both unchanged, pinned) |
| 1 | same file or `tests/test_main.py` | `frontend_security_headers` for the three modes returns the dicts of "Headers by mode" |
| 1 | new `tests/test_security_headers_scope.py` (or a class in `tests/test_static_serving.py`) | An app from the factory with `Settings(api_key_admin=..., debug=False)` and a frontend on a temp static directory: `/healthz`, `/readyz` and `/api/v1alpha1/auth/me` (with and without a key: 200 and 401) have neither policy header and no `x-frame-options` (AC 2); `/` on the same app has them |
| 4 | new `tests/test_api_docs.py` | Two apps from the factory, `debug=True` and `debug=False`, no frontend: with debug on `/docs` and `/redoc` are 200 `text/html` and `/openapi.json` is 200 JSON whose `info.version` is `__version__`; with debug off all three are 404. Parametrize paths and both states (AC 12) |
| 4 | same | The same two apps with a frontend on a temp static directory: debug off, each of the three paths returns the index page's bytes with the policy header (AC 10); debug on, `/docs` is the Swagger page (contains `swagger-ui`), has no `content-security-policy` header, and `/` on the same app has it (AC 11) |
| 4 | same, or `tests/test_debug_gating.py` rewritten | RBAC test routes both ways through the factory: debug on, `GET /api/v1alpha1/test/read` without a key is 401; debug off it is 404. Exact status codes |
| 4 | `tests/test_main.py` | A test that reads `main.py`'s source (`inspect.getsource(main_module)`) and asserts it has no `Settings(` call (AC 12), if 19.2 did not already add one for its own call |

The factory tests must not run the lifespan with real settings: use `TestClient(app)` without the `with` block, as the existing tests do, so no scheduler starts and nothing is written under `dev/`.

### Web tests (`web/src/lib/mod-description.test.ts`)

New `describe('images the page cannot load (Story 19.3, VSS-my4c)')`, using the file's `parse` helper (`:6-10`):

- Replaced, with the text `Image not shown: <alt>`, the `data-image-not-shown` attribute, and no `img` left: `http://x.test/a.png`, `/rel.png`, `rel.png`, `//x.test/a.png`, `https:a.png`, `data:text/html,x`, `javascript:alert(1)`, an `<img>` with no `src`. `it.each`.
- Without alt, or with a blank alt: the text is exactly `Image not shown`.
- Kept with `src` unchanged: `https://x.test/a.png`, `HTTPS://x.test/a.png`, `data:image/png;base64,AAAA`.
- `srcset` and `sizes` are gone from a kept image (`src="https://x.test/a.png" srcset="http://x.test/b.png 2x"`).
- Alt text `<b>bold</b>` appears as text: the note has no child element.
- Four images in a row, the third `https`: three notes and one `img`, in order; the paragraphs around them are intact.
- An `http` image inside a link: the link keeps `target` and `rel`, contains the note, and ends with exactly one `[data-new-tab-note]`.
- Sanitizing the output a second time: still one note per replaced image, no `img`.
- The existing "hook isolation" test (`:244-252`) gains one line: the shared `DOMPurify.sanitize('<img src="http://x.test/a.png">')` still returns an `img`.

`ModDetailPage.test.tsx` needs no change (it passed against the prototype); add one test there only if the page gains code, which this story does not plan.

### Existing tests that change (deliberately)

Found by running the whole API suite and the two web test files against a throwaway prototype of Task 1, Task 3 and the docs arguments of Task 4 (since discarded): API 2857 passed, 1 failed; web 134 passed in `mod-description.test.ts` and `ModDetailPage.test.tsx`; pyright 0 errors and the 3 known warnings; ruff clean. The prototype did not have Story 19.2's factory, so re-check this list after 19.2.

- **Fails:** `tests/test_main.py::TestImportTimeWiring::test_client_routes_are_served_with_static_dir` (`:267-273`). Its `FakeFileResponse.__init__(self, path)` (`:225-229`) does not accept `headers`, so `serve_spa` raises `TypeError`. Give it `headers: Mapping[str, str] | None = None` and pass it to `super().__init__`. If Story 19.2 replaced `load_fresh_app` (`:232-246`) with the factory, apply the same change wherever the stand-in now lives; `test_frontend_route_does_not_capture_api_routes` (`:275-281`) uses it too.
- **Passes by accident, must change:** `tests/test_version.py::test_openapi_reports_version` (`:23-27`) reads `/openapi.json` from the shared `client` fixture, which works only because `conftest.py:11` sets `VS_DEBUG=true` before the app is imported. Build its app explicitly: the factory with `Settings(api_key_admin=..., debug=True)`, then `GET /openapi.json` and the same two assertions. The other three tests in the file do not change.
- **Rewritten:** `tests/test_debug_gating.py` (`:20-101`). Its `production_app` fixture overrides `get_settings` on the shared debug app and its tests accept `404`, `200` or `401`, so they assert nothing (the file's own docstring says so, `:5-7`, `:32-34`). Replace the three RBAC tests with the exact two-way test of "API tests" on factory-built apps and keep `test_auth_endpoints_still_work_in_production_mode` on the debug-off app with exact codes. Fix the module docstring: the tests no longer depend on the environment.
- **Depends on 19.2:** `tests/test_main.py::TestImportTimeWiring::test_rbac_test_routes_only_exist_in_debug_mode` (`:252-260`) re-executes `main.py` with `VS_DEBUG` in the environment. With the factory it becomes two factory calls; if 19.2 already converted it, leave it and do not duplicate it in `test_api_docs.py`.
- **Unchanged, checked:** `tests/test_frontend_routes.py` (all classes: they assert bodies and `/config.js` headers, not the absence of others); `tests/test_static_serving.py`; `tests/test_routers_config.py:1637` (`app.openapi()`); `tests/conftest.py` (keeps `VS_DEBUG=true`: the shared app stays a debug app, which the RBAC integration tests need).
- Environment note: in a fresh worktree without `.env`, `just test-api` needs `VS_API_KEY_ADMIN` set (lifespan, scheduler and console tests fail without it); that is not caused by this story.
- Anything else that fails is a regression (AC 13): fix the code, not the test.

### E2E (`web/e2e/content-security-policy.spec.ts`)

Style of `e2e/mod-detail-media.spec.ts` (header comment with story, FRs, beads and requirements; `stubMedia` `:124-146`; the 1x1 `PNG` `:38-41`; `lookupBody` `:53-97`) and `e2e/layout-widths.spec.ts` (`readOnly` `:102-118`, the installed-mods stub `:122`). Copy what is needed; do not import across specs. The key comes from Story 19.2's `/config.js` helper. Chromium only, as `playwright.config.ts` defines.

- **Set-up for every test.** The 19.2 helper with the Admin key; refuse every non-GET to `**/api/**` (500 `E2E_BLOCKED`); `page.addInitScript` that collects `securitypolicyviolation` events into `window.__cspViolations` (effective directive, blocked URI, source file); record `page.on('console')` messages of type `error` and `page.on('pageerror')`.
- **Stubs, so the spec needs neither a game server nor the mod database** (Story 19.7 runs it in CI): `GET /api/v1alpha1/server/status` answered as installed and stopped (the shape of the real answer: `state: 'installed'`, `version`, `uptime_seconds: null`, `last_exit_code: null`, the two available versions, `version_last_checked`, `disk_space`); the installed mods, their updates and lookups as in `layout-widths.spec.ts`; the browse list as in `browse-game-version.spec.ts` (`:87`) with `logo_url` on `https://moddbcdn.vintagestory.at`; the lookup of a made-up slug (`e2ecspmod`) with three screenshots on the CDN and the description below; every `https://moddbcdn.vintagestory.at/**` and `https://images.example.com/**` request fulfilled with the PNG; `GET /api/v1alpha1/config/game` and whatever else answers 4xx on a stack without a game server, found by running the spec once against the stack and stubbing each request that logs a console error. List the stubs in the spec's header comment.
- **Description under test:** `<p style="color: #c33">Styled</p>`, `<img alt="secure" src="https://images.example.com/a.png">`, `<img alt="plain" src="http://images.example.com/b.png">`, `<img alt="relative" src="/c.png">`, a `data:image/png` image.
- **Test 1, headers (AC 1, 2), with `request`:** `GET /` and `GET /game-server/mods/browse` have `content-security-policy` equal to the whole string of "The policy" and the three other headers; `GET /healthz`, `GET /readyz` and `GET /api/v1alpha1/auth/me` (with the key) have no `content-security-policy` and no `content-security-policy-report-only`. No assertion about `/docs` here: the dev stack runs with `VS_DEBUG=true` and a CI stack may not; the API tests cover both.
- **Test 2, every page in both themes (AC 3, 6, 9):** for `colorScheme` of `light` and `dark` (`page.emulateMedia`, as `browse-game-version.spec.ts:135`; assert the `dark` class on `<html>` matches), open `/`, `/game-server/console`, `/game-server/mods/browse`, `/game-server/mods/browse/e2ecspmod`, `/game-server/mods/installed`, `/game-server/settings`, `/game-server/version`, `/config`; on each wait for its heading or test id, then expect `window.__cspViolations` to be empty, no recorded console error and no page error. On the detail page also: the `secure` and `data:` images have `naturalWidth > 0`; `mod-detail-description` contains `Image not shown: plain` and `Image not shown: relative`; no request was made to `http://images.example.com/` or for `/c.png` (record requests with `page.on('request')`); the gallery (`mod-screenshots`) shows its image.
- **Test 3, styled (AC 3):** on the console page the terminal exists (`.xterm`) and its computed `position` is `relative` (xterm's injected stylesheet applied); a toast raised by a refused write (for example a click that triggers a POST, which the read-only route answers with 500) is visible and has a non-transparent background; a dialog opened from the installed list (the remove confirmation, cancelled) is visible. If raising a toast needs more than one click on existing controls, assert on `[data-sonner-toaster]` being present and styled instead and say so in the spec.
- **Test 4, sockets (AC 4):** on the console page wait for `page.waitForEvent('websocket')` whose URL contains `/api/v1alpha1/console/ws`; after two seconds it is not closed and there is no `connect-src` violation. If `source-selector` offers a log file, choose it and expect a socket to `/api/v1alpha1/console/logs/ws` the same way; if the stack has no log file, annotate the test (`test.info().annotations`) that the log stream was not exercised. Frames are asserted only if the game server happens to be running; the spec never starts it.
- **Test 5, the control (AC 5):** on `/`, append a `<script>` element whose text sets `window.__injected = true` (inside `page.evaluate`); `window.__injected` stays undefined and one violation with effective directive `script-src-elem` is recorded. Then a second page, routed at a made-up other origin (`http://other.test/`, fulfilled by `page.route` with a document holding an `<iframe>` of the base URL): the frame's document has no `#root` and its URL is not the app's.
- The control test expects a violation, so it uses its own page and is not part of Test 2's "none" assertion.
- No real state changes: compare `GET /api/v1alpha1/mods` before and after in the Dev Agent Record. No screenshots; if a failure trace is attached to a PR, check it shows no server name or key.

### Manual check (Task 6.2)

On the Docker stack built from this branch, with the game server left as it is (do not start or stop it):

- `curl -s -D- -o /dev/null http://localhost:8080/` shows the four headers; `/healthz` shows none of them.
- The dev stack runs with `VS_DEBUG=true`: `/docs` renders and its response has no policy header. To see the production behavior, start the API once with `VS_DEBUG=false` only if the maintainer wants it; the API tests already cover it.
- In Firefox or Safari (the E2E covers Chromium only): open the console page, confirm the terminal connects and shows output if the game server is running, pick a log file in the source selector, and look at the browser console for a Content-Security-Policy message on each main page in both themes.
- Open a mod whose description has images and confirm they load; confirm a toast and a dialog look as before.
- No screenshots that show the server name or a key. The maintainer ticks 6.2.

### Not changed (do not "fix" these here)

- `/assets/*` (the `StaticFiles` mount) and `/config.js` get no policy header; `/config.js` keeps its three headers.
- `script-src` never gets `'unsafe-inline'`, `'unsafe-eval'` or another origin; there is no `report-uri` or `report-to` (ADR-6 decision 10).
- `web/index.html`, `web/vite.config.ts` and the Vite dev server (AC 8).
- Other markup DOMPurify keeps in a description and the policy blocks or restricts: `<picture><source srcset>`, `<video>` and `<audio>` (with no `media-src`, `default-src 'self'` blocks them from any other host, `https` included), `<video poster>`, the `background` attribute, `url(...)` in an inline `style`, and SVG `<image href>`. The prototype confirmed each survives the sanitizer. They do not load from a blocked address, the browser logs a violation, and the page is otherwise fine. Follow-up for the maintainer; the E2E's stubbed description has none of them. List this in the PR.
- The services' own `Settings()` calls, `initialize_debug_state()` and the debug log toggle.
- `api/tests/conftest.py` setting `VS_DEBUG=true`.
- The compose files (no `VS_CSP_MODE` entry needed) and `scripts/worktree-setup.sh`.
- `HEAD /` answers 405 today (`serve_spa` is GET only); check headers with a GET.
- Converting the other E2E specs to 19.2's helper is Story 19.7.

### API contract changes

- **Web UI pages** (`/` and every path `serve_spa` answers, not `/assets/*`, `/config.js`, `/api/...`, `/healthz`, `/readyz`): new response headers `Content-Security-Policy` (the value in "The policy"), `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY`. The pages can no longer be framed, an inline or third-party script does not run, and requests the page starts no longer send the manager's address as referrer. Behavior change.
- **New setting `VS_CSP_MODE`**: `enforce` (default), `report-only` (the policy in `Content-Security-Policy-Report-Only`; no `X-Frame-Options`), `off` (no policy header; no `X-Frame-Options`). Case and surrounding spaces are ignored and a blank value is the default; any other value stops start-up. Added setting.
- **`/docs`, `/redoc`, `/openapi.json`** (and `/docs/oauth2-redirect`): served only when `VS_DEBUG=true`. Otherwise they return the web UI's page in the image and 404 without the frontend. Before: always served. They are outside `v1alpha1`; a client that fetched the schema from a production deployment loses it. Not marked breaking (maintainer decision); named in the release notes by Task 4's commit subject.
- **Mod descriptions (web only, no API field changes):** an `<img>` whose address is not `https://` or `data:image/` is shown as "Image not shown" with its alt text, and `srcset` is dropped from description images. Audio and video from other hosts in a description no longer load under the policy (see "Not changed").
- No new error code, no response field added or removed.

### ADR against the code

- **ADR-6 decision 9 and `VS_CSP_MODE`.** The ADR puts `X-Frame-Options: DENY` "on the same responses" and does not say what `report-only` and `off` do to it. The story sends it only in `enforce`, so the setting can actually stop framing from being blocked. If the maintainer wants it in every mode, it is one line in `frontend_security_headers` and two rows of the test table.
- **ADR-6 decision 10 and a blank value.** The ADR fails start-up for any value other than the three. The story treats a blank `VS_CSP_MODE` as unset (`enforce`), so an empty line in `.env` cannot stop the API and the game server.
- **ADR-6 decision 14 names `src` only.** DOMPurify keeps `srcset`, which overrides `src`, so the story also drops `srcset` and `sizes` from description images. The other elements that can load an image or media file (listed under "Not changed") are outside decision 14 and outside this story.
- **ADR-6 decision 3 has no `media-src`.** With `default-src 'self'`, audio and video from other hosts in a description are blocked. The story implements the eleven directives as written and reports it.
- **Epics AC 1** cites "ADR-5 decision 3" for the directives; the directives are in ADR-6 decision 3.
- **ADR-7 decision 1** says `Settings().debug`; with the factory it is the factory's settings argument (decision 6 says so).
- **ADR-6 decision 13** asks the E2E to open the console with the WebSocket connected. Without an installed game server the console page shows an empty state and opens no socket, so the spec stubs the server status.
- Everything else in ADR-6 and ADR-7 matches the code at b6ae2f2 (line numbers re-read; the facts section's `main.py` and `config.py` lines are unchanged since `048fea9`).

### Testing Requirements

**CRITICAL:** Tests are written with each task and committed with it, red first. `just test-api <file>` / `just test-web <file>` after each task; `just check` before review.

- API tests build apps from the factory with explicit `Settings(...)`; they do not set `VS_DEBUG` in the environment and do not re-execute `main.py`.
- Expected header values are written out in the tests, not imported from the code under test.
- Tests must not write into `dev/` (`just test-api` sets `VS_DATA_DIR=../dev`): no lifespan with real settings; `git status --short` after `just test-api` shows nothing under `dev/`.
- Tests must not read private members (`reportPrivateUsage`); `frontend_security_headers` and the constant are public names.
- Web tests inspect parsed elements, not substrings (the file's `parse` helper).

### Security Requirements

- `script-src 'self'` is the point of the story; no task may add an inline or remote script source. A hash for next-themes is allowed only by Task 2.3 and only if a browser reports that script.
- No new endpoint. The headers are constants; no request data reaches a header unless the WebSocket fallback is needed, and then only a `Host` value that passed the pattern.
- The docs routes are removed by default, not protected by a key (ADR-7 decision 5).
- The image note's text is set with `textContent`.
- Never log or print an API key in a test, the E2E or the Dev Agent Record.

### Development Commands

- `just test-api tests/test_config.py tests/test_frontend_routes.py tests/test_main.py tests/test_version.py tests/test_debug_gating.py tests/test_api_docs.py`, `just test-web src/lib/mod-description.test.ts src/features/mods/ModDetailPage.test.tsx`, `just typecheck`, `just lint`, `just check`, `just changelog`.
- `just docker restart` rebuilds the dev stack; `cd web && bunx playwright test e2e/content-security-policy.spec.ts`.
- Do not run `just format-api` or a whole-repo formatter (it reformats unrelated files; Story 17.2 process note).

### Previous Story Intelligence

- **19.2 (prerequisite):** the app factory, `get_settings()` in the lifespan, `/config.js` with an empty key, and the `/config.js` E2E helper. Read its Completion Notes for the factory's name, whether it registers the frontend, and what happened to `load_fresh_app` before starting Task 4.
- **19.1:** edits `config.py` (`VS_GAME_VERSION` removed, so the field list around `:24` moves), `.env.example` and the compose files; re-read line numbers.
- **18.1:** added the new-tab note to the same sanitizer hook with `createElement` and `textContent`, and the CSS for it on the `.mod-description` container; this story follows both patterns. Its E2E (`mod-detail-media.spec.ts`) is the model for stubbing a lookup and the CDN.
- **18.2 / 17.4:** router and app tests that reach real singletons write into `dev/`; build apps with explicit settings and temp directories.
- **17.2:** E2E that changes real state needs a snapshot guard and an exact restore; this story's E2E changes nothing. `feat`/`fix` subjects must describe what an operator or admin can see.
- **17.x / 18.x reviews:** a completion note must be true of the code; manual checks wait for the maintainer; a TanStack Query hook-level `onError` replaces the client default (this story adds no hook).

### Git Intelligence

- Base `b6ae2f2` (`docs(epic-19): fold the maintainer's observation decisions into epic 19`). Stories 19.1 and 19.2 land first; 19.2 touches `main.py`, `config.py`, `tests/test_main.py` and `tests/test_frontend_routes.py` in the places this story edits.
- Planned commits: Task 1 `feat(story-19.3/task-1): serve the web UI with a Content-Security-Policy (VS_CSP_MODE)`. Task 2 `chore(story-19.3/task-2): record the browser checks for the policy`, or a `fix` if a fallback was needed. Task 3 `fix(story-19.3/task-3): mod description images that cannot be loaded securely show a note instead of a broken image`. Task 4 `fix(story-19.3/task-4): serve the API documentation pages only when VS_DEBUG is on` (optionally preceded by a `refactor`). Task 5 `test(...)` and `docs(...)`. Task 6 `chore(story-19.3/task-6): ...`.
- The subjects are the ones in `sprint-change-proposal-2026-11-17.md` section 2 (`:127`, `:129`), which writes them with the scopes `api` and `web`. Task commits carry the `story-19.3/task-N` scope, which `cliff.toml` hides (`:5`, `:26`), so the release note lines appear under Features and Fixes without a component prefix. The maintainer asked that the docs change be in the notes and not marked breaking; Task 4.5 checks that with `just changelog`.

### Project Structure Notes

- New: `web/e2e/content-security-policy.spec.ts`, `api/tests/test_api_docs.py` (and `api/tests/test_security_headers_scope.py` if not folded into an existing file).
- Modified: `api/src/vintagestory_api/config.py`, `api/src/vintagestory_api/main.py`; `api/tests/test_config.py`, `test_frontend_routes.py`, `test_main.py`, `test_version.py`, `test_debug_gating.py`; `web/src/lib/mod-description.ts`, `web/src/lib/mod-description.test.ts`, `web/src/styles/index.css`; `README.md`, `.env.example`; possibly `_bmad-output/planning-artifacts/architecture/project-structure-boundaries.md`.
- Not modified: `web/index.html`, `web/vite.config.ts`, the compose files, the `Dockerfile`, any router or service.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 19.3: Content-Security-Policy and API Docs]
- [Source: _bmad-output/planning-artifacts/prd.md] FR213-FR217
- [Source: _bmad-output/planning-artifacts/architecture/epic-19-api-security-and-mod-file-safety.md#ADR-6, #ADR-7; ADR-5 decision 11; "Facts Checked in the Code"]
- [Source: _bmad-output/planning-artifacts/architecture/epic-18-mod-media-and-fixes.md] (ADR-2: the trailer is a link, so the app frames nothing)
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-17.md] (section 2 API change table and release-note subjects; section 5 answered questions)
- [Source: _bmad-output/implementation-artifacts/18-1-mod-detail-media-and-links.md], [18-2-install-and-version-change-keep-records-right.md], [17-4-installed-status-is-right-everywhere.md]
- Beads: `VSS-3qb8`, `VSS-my4c`, `VSS-5mes`, parent `VSS-fl9b`
- `project-context.md` (no suppressions; manual test tasks need the maintainer's confirmation; commit format)

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5), Claude Code, BMAD dev-story (non-interactive)

### Debug Log References

- Line numbers re-checked against Story 19.2's tree: `create_app(settings, static_dir)` holds the old constructor; `register_frontend(target, static_dir, settings)` serves `/config.js` from its `settings` argument, so `serve_spa` reads `settings.csp_mode` from the same argument (one mechanism, no dependency). `Settings()` was left in `main.py` twice, both inside the factory (`cors_settings = Settings()` and `if Settings().debug:`).
- Task 2 browser checks (2026-11-17), on the dev stack rebuilt from `4dae4b5` with `just docker restart` (no game server process before or after). `curl -s -D- -o /dev/null http://localhost:8080/` showed `content-security-policy` (the whole string of "The policy"), `x-frame-options: DENY`, `x-content-type-options: nosniff`, `referrer-policy: no-referrer`; `/healthz` showed none of them. Playwright 1.65.1 (from `web/node_modules`) driving Chromium 156.0.8078.4 headless, a `securitypolicyviolation` listener from `page.addInitScript`, console messages recorded, every non-GET to `/api/` refused apart from `POST /api/v1alpha1/ws-token` (the console needs a token to open its socket; the token store is in memory). Pages `/game-server/console` and `/game-server/mods/installed`, `colorScheme` light and dark (the `dark` class on `<html>` matched each time).
  - (a) next-themes 0.4.6: the inline `<script>` element (`((e,t,n,r,i,a,o,s)=>{let c=document.docu...`) is in the DOM on both pages in both themes; no `securitypolicyviolation` event and no console message of any kind about it. No hash added (2.3 not needed).
  - (b) `ws://localhost:8080/api/v1alpha1/console/ws?...` opened under `connect-src 'self'` and stayed open with no socket error and no violation (0 frames: no game server running). Choosing the first log file in `source-selector` (the stack lists log files) opened `ws://localhost:8080/api/v1alpha1/console/logs/ws?...`, which stayed open and carried 100 frames, no violation. No `ws:` source needed (2.4 not needed).
  - No console error on either page in either theme once the token request was let through (with it refused, the console page logged one 500 for the token POST, which is the test's own refusal).

### Completion Notes List

- Story created 2026-11-16 (create-story, non-interactive) and validated against the create-story checklist. A throwaway prototype at b6ae2f2 (the headers on `serve_spa`, `csp_mode` with its validator, the three docs arguments, the image rule in the sanitizer hook) was run against the whole API suite (2857 passed, 1 failed: the `FakeFileResponse` test listed above), pyright (0 errors, 3 known warnings), ruff, the two web test files (134 passed) and a Chromium browser on a local build served by the API, then discarded. What the browser showed is in Dev Notes "Browser checks".

### File List

## Change Log

- 2026-11-16: Story 19.3 created and validated (ready-for-dev).
