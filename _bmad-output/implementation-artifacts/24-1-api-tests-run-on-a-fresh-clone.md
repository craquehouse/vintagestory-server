# Story 24.1: API Tests Run on a Fresh Clone

Status: review

<!-- Implements FR327, Epic 24 ADR-8 decision 2. Bead: VSS-uhek (TOOLS-010), closed by this story after merge. Branch story/24-1-api-tests-run-on-a-fresh-clone from main at 804af73f, carrying the Epic 24 planning commit (967cd4a6). Test tooling only: no product change, no release note. -->

## Story

As a **developer**,
I want **the API tests to run on a fresh clone or a new worktree**,
so that **I do not have to copy a `.env` file before `just test-api` works**.

## Acceptance Criteria

1. **Given** no `VS_API_KEY_ADMIN` in the environment (a fresh clone or worktree without `.env`)
   **When** the API tests run
   **Then** every test collects and passes, with no "VS_API_KEY_ADMIN must be set" error
   *(FR327; ADR-8 decision 2)*

2. **Given** `VS_API_KEY_ADMIN` is set (from `.env` through mise, or by CI)
   **When** the tests run
   **Then** that value is kept, not replaced by the placeholder
   *(FR327)*

3. **Given** the README's Development section
   **When** a developer reads it
   **Then** it says the tests need no `.env`, and running the app still does

4. **(Quality gates.)** `just check` green; no suppression added; `git diff` of `web/` empty.

## Tasks / Subtasks

<!-- Red first. Subjects: type(story-24.1/task-N): ... No user-visible commit. -->

- [x] Task 1: Placeholder key for the tests + tests (AC: 1, 2)
  - [x] 1.1: Red: `tests/test_test_environment.py` imports `conftest.py` in a fresh interpreter (cwd `tests/`): without `VS_API_KEY_ADMIN` the key is the placeholder; with `from-dot-env` it is kept
  - [x] 1.2: `tests/conftest.py`: `os.environ.setdefault("VS_API_KEY_ADMIN", "test-placeholder-admin-key")` next to the existing environment lines, before the app is imported. (A helper module called from `conftest.py` was tried first; ruff E402 refuses a function call before the imports, while it accepts `os.environ` statements, so the line stays in `conftest.py` and the test checks the real file.)
  - [x] 1.3: Full suite with `env -u VS_API_KEY_ADMIN` and with the key set
  - [x] 1.4: Commit `test(story-24.1/task-1): run the API tests without a .env file`

- [x] Task 2: README (AC: 3)
  - [x] 2.1: Development section: the API tests need no `.env`; the app does
  - [x] 2.2: Commit `docs(story-24.1/task-2): say the API tests run without a .env file`

- [x] Task 3: Validate and move the story to review (AC: all)
  - [x] 3.1: `just check` green; `just changelog` lists no entry from this story
  - [x] 3.2: Status `review`; `just sprint set 24-1-api-tests-run-on-a-fresh-clone review`; Dev Agent Record and File List
  - [x] 3.3: Commit `chore(story-24.1/task-3): validate and move story 24.1 to review`

## Dev Notes

### The code today (verified at 804af73f)

- `Settings.ensure_directories` raises `ValueError("VS_API_KEY_ADMIN must be set ...")` (`api/src/vintagestory_api/config.py:290`); the app module builds its settings at import, so a missing key fails collection of every test module that imports the app (19 collection errors with `env -u VS_API_KEY_ADMIN`).
- Locally the key comes from the root `.env` through `.mise.toml` (`env_file = ".env"`); CI sets `VS_API_KEY_ADMIN: ci-placeholder-key` (`.github/workflows/ci.yml:25`).
- `api/tests/conftest.py:8-16` already adjusts the environment before importing the app (`VS_DEBUG`, `VS_MOD_DB_URL`, `VS_LOG_LEVEL`).
- `TEST_ADMIN_KEY` in `conftest.py` is the key the tests send; tests that need a specific admin key set it through their own settings, so the placeholder only has to be non-empty.

### References

- `epics.md` "Story 24.1"; `architecture/epic-24-mod-management-follow-ups.md` ADR-8

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5), as the epic's controller.

### Debug Log References

- Red, at 967cd4a6 with `env -u VS_API_KEY_ADMIN VS_DATA_DIR=../dev .venv/bin/python -m pytest --ignore=tests/e2e` (the `just test-api` command without mise, so no `.env`): 7 failed, 3923 passed, 80 errors (the bead's numbers).
- Green, same command after Task 1: 4010 passed.
- `just check` (2026-11-20): API 4009 passed, web 3859 passed (147 files), 0 skipped; Pyright 0/0; lints and script tests green.
- `just changelog`: no entry from this story.

### Completion Notes List

- 2026-11-20 (create-story): created from Epic 24's Story 24.1 and ADR-8.
- 2026-11-20 (dev-story): Tasks 1 to 3 done. The placeholder is set in `conftest.py` with `setdefault`, so `.env` (through mise) and CI keep their keys. The two tests run `import conftest` in a subprocess and read the key it leaves (the last stdout line, as the app logs at import).

### File List

- `api/tests/conftest.py` (modified)
- `api/tests/test_test_environment.py` (new)
- `README.md` (Development commands: tests need no `.env`)
- `_bmad-output/implementation-artifacts/24-1-api-tests-run-on-a-fresh-clone.md` (this file)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (through `just sprint set` only)

## Change Log

- 2026-11-20: Story 24.1 created (ready-for-dev).
- 2026-11-20: Implemented (dev-story): Tasks 1 to 3; status review.
