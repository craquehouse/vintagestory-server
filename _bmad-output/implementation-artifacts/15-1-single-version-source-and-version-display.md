# Story 15.1: Single Version Source and Version Display

Status: review

## Story

As an **administrator**,
I want **to see which version of the manager I am running**,
so that **I can tell whether I am up to date and report problems accurately**.

## Acceptance Criteria

1. **Given** the version in `api/pyproject.toml`
   **When** the API starts
   **Then** the OpenAPI document and `/healthz` report that version
   **And** no other API file hard-codes it
   *(FR152, FR153)*

2. **Given** the version in `web/package.json`
   **When** the web UI is built
   **Then** the sidebar footer shows that version instead of a hard-coded value
   *(FR154)*

3. **Given** both version files
   **When** `just version` runs
   **Then** it prints the version
   **And** fails if the two files disagree, comparing pre-release versions in their PEP 440 form (`0.2.0-rc.1` = `0.2.0rc1`)

4. **Given** the image is started with no network access
   **When** the container starts
   **Then** the API comes up without installing or downloading anything, and without dev dependencies
   *(`VSS-flj`, found in Story 15.0)*

## Tasks / Subtasks

- [x] Task 1: Install the project at image build time and start without syncing (AC: 4)
  - [x] 1.1: Dockerfile: `uv sync --frozen --no-dev --no-install-project` before copying `src/`, then `uv sync --frozen --no-dev` after it, so the project is installed at build time
  - [x] 1.2: Start without syncing: `CMD ["uv", "run", "--no-sync", "uvicorn", ...]` (or the venv's `uvicorn`); keep the HEALTHCHECK as is
  - [x] 1.3: Build the image and verify with `--network none`: the API starts, `/healthz` answers, no dev packages are installed (`uv pip list` shows no pytest/ruff/pyright)

- [x] Task 2: API version from package metadata (AC: 1)
  - [x] 2.1: `vintagestory_api/__init__.py`: `__version__ = importlib.metadata.version("vintagestory-api")`
  - [x] 2.2: `main.py`: `FastAPI(version=__version__)`
  - [x] 2.3: `HealthData.version: str` (description: manager version); `/healthz` sets it
  - [x] 2.4: Tests: `__version__` equals `[project].version` read from `pyproject.toml` with `tomllib`; OpenAPI `info.version`; `/healthz` `data.version`; a grep-style test that no file under `src/` contains the literal version string

- [x] Task 3: Web version from `package.json` (AC: 2)
  - [x] 3.1: Set `web/package.json` `version` to `0.1.0` (matches `pyproject.toml`)
  - [x] 3.2: Inject `__APP_VERSION__` with Vite `define` from `package.json` in both `vite.config.ts` and `vitest.config.ts`; declare it in a `src/globals.d.ts`; expose it as `APP_VERSION` from `src/lib/version.ts`
  - [x] 3.3: Sidebar footer renders `v{APP_VERSION}`; update `Sidebar.test.tsx` to use `APP_VERSION` instead of the literal

- [x] Task 4: `just version` (AC: 3)
  - [x] 4.1: `scripts/version.sh`: read `web/package.json` `.version`, `api/pyproject.toml` `.project.version` and the `vintagestory-api` entry in `api/uv.lock` with `yq`; validate SemVer `X.Y.Z` with optional `-alpha.N`, `-beta.N` or `-rc.N`; convert to PEP 440 (`aN`, `bN`, `rcN`); fail with a clear message naming the files if any disagree; print the SemVer version
  - [x] 4.2: `just version` recipe calling the script
  - [x] 4.3: Tests in `scripts/tests/test-version.sh` (plain bash with a small assert helper, run against temporary copies): equal stable versions, equal pre-release versions in both spellings, mismatch, `uv.lock` mismatch, invalid version, unsupported pre-release form
  - [x] 4.4: `just test-scripts` runs `scripts/tests/test-*.sh`; `just test` includes it; CI runs it

- [x] Task 5: Verification and validation (AC: all)
  - [x] 5.1: Run the built image with `--network none`, open the UI in a browser: sidebar shows `v0.1.0`, `/healthz` and `/openapi.json` report `0.1.0`; check the browser console
  - [x] 5.2: `just check`; update the Dev Agent Record and File List

## Dev Notes

### Scope

FR152-FR154 and `VSS-flj`. Out of scope: the release command (15.4), changelog (15.3), runtime API key (15.2). Do not bump the version: it stays `0.1.0` until `v0.1.0` is released in Story 15.6.

### Current state

- Hard-coded versions: `api/src/vintagestory_api/__init__.py` (`__version__ = "0.1.0"`), `api/src/vintagestory_api/main.py:160` (`version="0.1.0"`), `web/src/components/layout/Sidebar.tsx:216` (`v0.1.0`), test `Sidebar.test.tsx:244`; `web/package.json` is `0.0.0`.
- `HealthData` in `api/src/vintagestory_api/models/responses.py:94`; `/healthz` in `routers/health.py` builds it; tests in `api/tests/test_health.py`.
- Dockerfile (final stage): `COPY api/pyproject.toml api/uv.lock ./` → `RUN uv sync --frozen --no-dev` → `COPY api/src/ ./src/` → … → `CMD ["uv", "run", "uvicorn", "vintagestory_api.main:app", "--host", "0.0.0.0", "--port", "8080"]`. Build backend is hatchling (`[build-system]` in `pyproject.toml`).
- `vite.config.ts` and `vitest.config.ts` are separate files; a `define` must be in both. `tsconfig.json` includes `src` and `tests`.

### Rules

- Epic 15 ADR-1 (as updated by Story 15.0): `pyproject.toml` is the version; `package.json` and `uv.lock` match it; pre-releases compare by PEP 440 normalization; only `-alpha.N`, `-beta.N`, `-rc.N` pre-release forms are allowed.
- `yq` is pinned in `.mise.toml` (4.54.2) and reads TOML (`-p toml`), the lock file and JSON; verified in Story 15.0.
- Commit types follow user impact (`project-context.md`): the version display and `/healthz` field are `feat`; the start-up fix is `fix`; scripts and tests are `chore`/`test`.
- No lint or type suppressions.

### Testing Requirements

- API: pytest in `api/tests/` (`test_health.py`, a new `test_version.py`).
- Web: Vitest; `Sidebar.test.tsx`.
- Scripts: bash tests under `scripts/tests/`, no new tool dependency.
- Browser verification required (UI change), against the built image.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 15.1]
- [Source: _bmad-output/planning-artifacts/architecture/epic-15-release-engineering.md] ADR-1
- [Source: _bmad-output/implementation-artifacts/15-0-spike/README.md] §3, `version_check.out`

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5)

### Debug Log References

- Browser screenshot kept locally only (`.playwright-mcp/story-15-1-sidebar-version.png`, git-ignored).

### Completion Notes List

- Task 1 (`VSS-flj`): the Dockerfile installs dependencies with `--no-install-project`, copies `src/`, then installs the project; the CMD is `uv run --no-sync uvicorn …`. Verified with `--network none`: the container reports healthy, `/healthz` answers, and `uv pip list` shows none of pytest, ruff, pyright, playwright, respx or coverage. The only log warnings are the expected game-version lookups failing without DNS.
- Task 2: `__version__` comes from `importlib.metadata.version("vintagestory-api")`, with no fallback (the project is always installed: `uv sync` locally, the build in the image). `FastAPI(version=__version__)`; `HealthData.version` is required and set by `/healthz`. 4 tests in `test_version.py`, including one that fails if any file under `src/` contains the version literal.
- Task 3: `web/package.json` is `0.1.0`. `__APP_VERSION__` is injected by Vite `define` from `package.json` in both `vite.config.ts` and `vitest.config.ts`, declared in `src/globals.d.ts` and exposed as `APP_VERSION` from `src/lib/version.ts`. The sidebar renders `v{APP_VERSION}`. 2 new tests (version equals `package.json`; sidebar shows it when expanded); the collapsed test uses `APP_VERSION`.
- Task 4: `scripts/version.sh` reads the three files with `yq`, accepts `X.Y.Z` and `-alpha.N`/`-beta.N`/`-rc.N`, compares `pyproject.toml` and `uv.lock` with the PEP 440 form, and names the file that disagrees. `just version` runs it; `just test-scripts` runs bash tests in `scripts/tests/` (19 assertions, small `lib.sh` helper, temporary directories cleaned on exit); `just test` includes it; CI has a "Release scripts" job running both. Shellcheck is clean (one `source=` path hint so it can follow `lib.sh`); `actionlint` passes on `ci.yml`.
- Task 5: image built and run on port 8081: sidebar shows `v0.1.0`, `/healthz` and `/openapi.json` report `0.1.0`. Console: only `404 /api/v1alpha1/config/game`, which is existing behavior with no game server installed. `just check` passes: 2052 API tests (+4), 3001 web tests (+2), 19 script assertions.

### File List

- Modified: `Dockerfile`, `Justfile`, `.github/workflows/ci.yml`
- Modified: `api/src/vintagestory_api/__init__.py`, `api/src/vintagestory_api/main.py`, `api/src/vintagestory_api/models/responses.py`, `api/src/vintagestory_api/routers/health.py`
- Created: `api/tests/test_version.py`
- Modified: `web/package.json`, `web/vite.config.ts`, `web/vitest.config.ts`, `web/src/components/layout/Sidebar.tsx`, `web/src/components/layout/Sidebar.test.tsx`
- Created: `web/src/globals.d.ts`, `web/src/lib/version.ts`, `web/src/lib/version.test.ts`
- Created: `scripts/version.sh`, `scripts/tests/lib.sh`, `scripts/tests/run.sh`, `scripts/tests/test-version.sh`

## Change Log

- 2026-11-10: Story created.
- 2026-11-10: Implemented; image starts offline (`VSS-flj`); browser-verified. `just check` passes. Status review.
