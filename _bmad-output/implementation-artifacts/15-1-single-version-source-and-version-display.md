# Story 15.1: Single Version Source and Version Display

Status: ready-for-dev

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

- [ ] Task 1: Install the project at image build time and start without syncing (AC: 4)
  - [ ] 1.1: Dockerfile: `uv sync --frozen --no-dev --no-install-project` before copying `src/`, then `uv sync --frozen --no-dev` after it, so the project is installed at build time
  - [ ] 1.2: Start without syncing: `CMD ["uv", "run", "--no-sync", "uvicorn", ...]` (or the venv's `uvicorn`); keep the HEALTHCHECK as is
  - [ ] 1.3: Build the image and verify with `--network none`: the API starts, `/healthz` answers, no dev packages are installed (`uv pip list` shows no pytest/ruff/pyright)

- [ ] Task 2: API version from package metadata (AC: 1)
  - [ ] 2.1: `vintagestory_api/__init__.py`: `__version__ = importlib.metadata.version("vintagestory-api")`
  - [ ] 2.2: `main.py`: `FastAPI(version=__version__)`
  - [ ] 2.3: `HealthData.version: str` (description: manager version); `/healthz` sets it
  - [ ] 2.4: Tests: `__version__` equals `[project].version` read from `pyproject.toml` with `tomllib`; OpenAPI `info.version`; `/healthz` `data.version`; a grep-style test that no file under `src/` contains the literal version string

- [ ] Task 3: Web version from `package.json` (AC: 2)
  - [ ] 3.1: Set `web/package.json` `version` to `0.1.0` (matches `pyproject.toml`)
  - [ ] 3.2: Inject `__APP_VERSION__` with Vite `define` from `package.json` in both `vite.config.ts` and `vitest.config.ts`; declare it in a `src/globals.d.ts`; expose it as `APP_VERSION` from `src/lib/version.ts`
  - [ ] 3.3: Sidebar footer renders `v{APP_VERSION}`; update `Sidebar.test.tsx` to use `APP_VERSION` instead of the literal

- [ ] Task 4: `just version` (AC: 3)
  - [ ] 4.1: `scripts/version.sh`: read `web/package.json` `.version`, `api/pyproject.toml` `.project.version` and the `vintagestory-api` entry in `api/uv.lock` with `yq`; validate SemVer `X.Y.Z` with optional `-alpha.N`, `-beta.N` or `-rc.N`; convert to PEP 440 (`aN`, `bN`, `rcN`); fail with a clear message naming the files if any disagree; print the SemVer version
  - [ ] 4.2: `just version` recipe calling the script
  - [ ] 4.3: Tests in `scripts/tests/test-version.sh` (plain bash with a small assert helper, run against temporary copies): equal stable versions, equal pre-release versions in both spellings, mismatch, `uv.lock` mismatch, invalid version, unsupported pre-release form
  - [ ] 4.4: `just test-scripts` runs `scripts/tests/test-*.sh`; `just test` includes it; CI runs it

- [ ] Task 5: Verification and validation (AC: all)
  - [ ] 5.1: Run the built image with `--network none`, open the UI in a browser: sidebar shows `v0.1.0`, `/healthz` and `/openapi.json` report `0.1.0`; check the browser console
  - [ ] 5.2: `just check`; update the Dev Agent Record and File List

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

### Completion Notes List

### File List

## Change Log

- 2026-11-10: Story created.
