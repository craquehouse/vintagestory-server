# Story 24.2: The Web UI Has Its Own Icon, and Missing Files Are 404

Status: done

<!-- Implements FR328, FR329, FR330, Epic 24 ADR-2. Beads: VSS-2bp (UI-075), closed by this story after merge; VSS-koo1 (API-094) item 1 (closes in Story 24.8). Branch story/24-2-web-ui-icon-and-missing-files-are-404, stacked on story/24-1-api-tests-run-on-a-fresh-clone at 2f40938f (24.1 in review); the PR targets main and merges after 24.1's. -->

## Story

As an **administrator**,
I want **the browser tab to show the Vintage Story icon and missing files to fail visibly**,
so that **I can find the manager's tab, and a broken asset is a 404 rather than a page**.

## Acceptance Criteria

1. **Given** the built web UI
   **When** a browser loads it
   **Then** `index.html` links `favicon.ico`, `favicon-32.png` and `apple-touch-icon.png`, each file exists, `vite.svg` is gone, and `/favicon.ico` is served as a file
   *(FR328; ADR-2 decision 1)*

2. **Given** a path outside the web UI's routes whose last segment has a file extension and that is not a file (`/missing.png`, `/favicon.svg`, `/vite.svg`)
   **When** it is requested
   **Then** it answers 404 with the page's security headers
   *(FR329; ADR-2 decision 2)*

3. **Given** a web UI route, including `/game-server/mods/browse/some.mod` and a route with a trailing slash
   **When** it is requested
   **Then** it gets `index.html`, as before; the list of route prefixes matches `web/src/App.tsx`
   *(FR329; ADR-2 decision 2)*

4. **Given** a file under `/assets`
   **When** it is requested
   **Then** the response carries `X-Content-Type-Options: nosniff` and `Referrer-Policy: no-referrer` in every CSP mode, and still no policy header
   *(FR330; ADR-2 decision 3)*

5. **(Quality gates.)** `just check` green; no suppression added.

## Tasks / Subtasks

- [x] Task 1: Icons (AC: 1, 5)
  - [x] 1.1: Generate the icons (command below); copy to `web/public/`; remove `vite.svg`; `index.html` links the three files
  - [x] 1.2: `web/src/index-html.test.ts`: the three links, every linked file exists in `public/`, `vite.svg` gone
  - [x] 1.3: Commit `feat(story-24.2/task-1): show the Vintage Story icon in the browser tab`

- [x] Task 2: 404 for missing files (AC: 2, 3, 5)
  - [x] 2.1: Red: `test_frontend_routes.py`: missing files with an extension are 404 with headers; dotted web UI routes get the page; `WEB_ROUTE_PREFIXES` covers App.tsx's top-level routes; the containment tests now expect 404 (still never the private file)
  - [x] 2.2: `main.py`: `WEB_ROUTE_PREFIXES`, `_asks_for_a_missing_file`, `_resolve_frontend_file` returns `None` for a 404, `serve_spa` answers 404 with the security headers
  - [x] 2.3: Commit `fix(story-24.2/task-2): answer 404 for missing static files instead of the web page`

- [x] Task 3: `/assets` headers (AC: 4, 5)
  - [x] 3.1: Red: `test_assets_carry_the_file_headers` for each mode; `test_assets_have_no_policy` kept
  - [x] 3.2: `main.py`: `FILE_SECURITY_HEADERS` (used by `frontend_security_headers`), `_StaticFilesWithHeaders` for the mount
  - [x] 3.3: Commit `fix(story-24.2/task-3): send security headers with the web UI's assets`

- [x] Task 4: Validate and move the story to review (AC: all)
  - [x] 4.1: `just check` green; CSP E2E on a throwaway container; `just changelog` lists the three entries
  - [x] 4.2: Status `review`; sprint status; Dev Agent Record and File List
  - [x] 4.3: Commit `chore(story-24.2/task-4): validate and move story 24.2 to review`

## Dev Notes

### The code today (verified at 804af73f)

- `web/index.html:5` linked `/vite.svg`; `web/public/` had `vintagestory-icon.webp` (24px) and `@2x` (48px), used by the collapsed sidebar.
- `_resolve_frontend_file` (`main.py:303`) returned `index.html` for any path that was not a file inside the static root.
- `/assets` was a plain `StaticFiles` mount with no security headers (`VSS-koo1` item 1). Epic 19 ADR-6 decision 1 gave the policy to page responses only, since a policy and `X-Frame-Options` apply to documents.

### Icon source and command (ADR-2 decision 1, changed in implementation)

ADR-2 named `vintagestory-icon@2x.webp` as the source. It is 48px, too small for a 180px apple-touch icon. The same tree is about 200px tall in the repository's `assets/vintagestory-logobanner.png` (1114x211, RGBA), so the icons are cut from it with macOS `sips`, padded to a transparent square, and packed into a PNG-entry `.ico`:

```bash
sips -c 205 162 --cropOffset 4 482 assets/vintagestory-logobanner.png --out tree-narrow.png
sips --padToHeightWidth 205 205 tree-narrow.png --out tree-sq.png
for n in 16 32 48 180; do sips -z $n $n tree-sq.png --out t$n.png; done
# favicon.ico: t16, t32, t48 as PNG entries (ICONDIR + ICONDIRENTRY + PNG data), a 15-line
# Python script using struct; favicon-32.png = t32.png; apple-touch-icon.png = t180.png
```

### `/assets` headers (ADR-2 decision 3, refined in implementation)

ADR-2 said the mount sends `frontend_security_headers(csp_mode)`. Implemented as the two headers that apply to files, `X-Content-Type-Options: nosniff` and `Referrer-Policy: no-referrer` (`FILE_SECURITY_HEADERS`), in every mode, and no policy or `X-Frame-Options`, which only apply to documents (Epic 19 ADR-6 decision 1). The existing `test_assets_have_no_policy` stays true. ADR-2 decision 3 is updated to match.

### 404 rule and containment

The containment tests (`..%2Fprivate.txt`, an absolute path, a symlink out of the root) used to get `index.html`; their last segment has an extension, so they now get 404. They still never get the private file, which is what they check.

### References

- `epics.md` "Story 24.2"; `architecture/epic-24-mod-management-follow-ups.md` ADR-2; Epic 19 ADR-6

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5), as the epic's controller.

### Debug Log References

- `just check` (2026-11-20): API 4024 passed, web 3862 passed, 0 skipped; Pyright 0/0; lints green.
- `just test-e2e-ci e2e/content-security-policy.spec.ts` (throwaway container, the built image): web 6 passed, API E2E 4 passed.
- `just changelog`: three entries from this story (Tasks 1, 2, 3).
- `test_api_docs.py`: with debug off, `/openapi.json` now answers 404 (it names a missing file) instead of the web page; `/docs` and `/redoc` still get the page. The test and the `create_app` comment were updated in the Task 2 commit.

### Completion Notes List

- 2026-11-20 (create-story and dev-story): created from Epic 24's Story 24.2 and ADR-2; Tasks 1 to 4 done.

### File List

- `web/public/favicon.ico`, `web/public/favicon-32.png`, `web/public/apple-touch-icon.png` (new); `web/public/vite.svg` (removed)
- `web/index.html` (modified)
- `web/src/index-html.test.ts` (new)
- `api/src/vintagestory_api/main.py` (modified)
- `api/tests/test_frontend_routes.py`, `api/tests/test_api_docs.py` (modified)
- `_bmad-output/planning-artifacts/architecture/epic-24-mod-management-follow-ups.md` (ADR-2 decisions 1 and 3 as implemented)
- `_bmad-output/implementation-artifacts/24-2-web-ui-icon-and-missing-files-are-404.md` (this file)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (through `just sprint set` only)

## Review

Reviewer: GLM-5.3-Flash via opencode. Verdict: approve with changes. 0 HIGH, one MEDIUM, four LOW, all fixed:

1. **MEDIUM: error responses under `/assets` had no headers.** StaticFiles raises for a missing file (404) or another method (405), and the exception was rendered outside the mount. `_StaticFilesWithHeaders` now renders it with the file headers (and keeps `Allow`); two tests.
2. **LOW: a mixed-case web UI URL with a dotted last segment answered 404,** while React Router matches routes ignoring case. The prefix is compared lower-cased; one test row.
3. **LOW: no test pinned `/favicon.ico`'s image content type.** Asserted.
4. **LOW: Epic 19 ADR-7 decision 3 still said `/openapi.json` gets the page.** Amended.
5. **LOW: 404 headers tested in enforce mode only.** Parametrized over the three modes.

## Change Log

- 2026-11-20: Story 24.2 created and implemented (dev-story): Tasks 1 to 4; status review.
- 2026-11-20: Code review (GLM-5.3-Flash via opencode): approve with changes; 0 HIGH, 1 MEDIUM, 4 LOW, all fixed (see "Review"). Status done.
