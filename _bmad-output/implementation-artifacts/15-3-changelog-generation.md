# Story 15.3: Changelog Generation

Status: done

## Story

As a **maintainer**,
I want **release notes generated from commit messages**,
so that **each release describes its changes without manual assembly**.

## Acceptance Criteria

1. **Given** conventional commits since the last release
   **When** `just changelog` runs
   **Then** it prints the unreleased notes grouped into breaking changes, features, fixes and performance improvements
   **And** each entry links to its commit
   *(FR155, FR157)*

2. **Given** `docs`, `chore`, `test`, `ci`, `build`, `refactor`, `style` or review commits, merge commits, or non-conventional messages
   **When** notes are generated
   **Then** they are left out
   *(FR155)*

3. **Given** a commit scoped to a story, task or review (e.g. `feat(story-14.2/task-6): ...`)
   **When** notes are generated
   **Then** the entry shows the description without that scope
   *(FR156)*

## Tasks / Subtasks

- [x] Task 1: Pin git-cliff and add the configuration (AC: 1, 2, 3)
  - [x] 1.1: Add `git-cliff = "2.14.2"` to `.mise.toml` `[tools]`
  - [x] 1.2: Add `cliff.toml` at the repository root from `15-0-spike/cliff.toml`: header with `header_marker` (Story 15.4 prepends below it), template with groups, commit links and the scope allowlist (`api`, `web`, `docker`), parsers (breaking first, safety-net skips for `story-N.0` scopes and "move story X.Y to review", then `feat`/`fix`/`perf`, everything else skipped), `protect_breaking_commits`, `filter_unconventional`, stable-only `tag_pattern`, `[bump]` rules for 0.x
  - [x] 1.3: Keep scopes in the template, not a preprocessor, so parsers can still match them

- [x] Task 2: `just changelog` (AC: 1)
  - [x] 2.1: Recipe printing unreleased notes to stdout (`git cliff --unreleased --strip header`), accepting extra git-cliff arguments (e.g. a range)
  - [x] 2.2: No file is written and nothing is committed

- [x] Task 3: Tests against a fixture history (AC: 1, 2, 3)
  - [x] 3.1: `scripts/tests/test-changelog.sh`: build a temporary repository with commits covering every rule (each excluded type, merge commit, non-conventional message, story/task/review/`ad-hoc` scopes, allowlisted scope, `type!:` and `BREAKING CHANGE:` footer, `refactor!:`, `story-N.0` scope, "move story to review") and run the repository's `cliff.toml` against it
  - [x] 3.2: Assert group headings and order, included and excluded entries, scope display, commit links (full SHA in the URL, 7-character text)
  - [x] 3.3: Assert bump rules on 0.x (`--bumped-version`): fix→patch, feat→minor, breaking→minor, nothing releasable→unchanged; pre-release tags ignored by notes and bumps
  - [x] 3.4: CI's "Release scripts" job runs them (git-cliff comes from `.mise.toml` through `mise-action`)

- [x] Task 4: Validation (AC: all)
  - [x] 4.1: Run `just changelog e9358b9..f32fc26` and compare with `15-0-spike/sample-notes-epic-14.md` (header aside)
  - [x] 4.2: `just check`; update the Dev Agent Record and File List

### Review Follow-ups (AI)

- [x] [AI-Review][Low] `just changelog v0.1.0..HEAD` example prints nothing once tags exist (`--unreleased` plus a range): example is now `just changelog --tag v0.2.0`
- [x] [AI-Review][Low] Parser order (breaking before the preparation-story skip) was not pinned: fixture adds `feat(story-2.0/task-1)!:`, expected under Breaking Changes
- [x] [AI-Review][Low] A missing or unrunnable git-cliff gave confusing failures: the test exits early unless git-cliff runs from a temporary directory (a mise shim outside `mise exec` cannot resolve the version there, which explained the 8/23 run outside mise)
- [x] [AI-Review][Low] Git isolation missed settings such as `tag.forceSignAnnotated`: fixture git runs with `GIT_CONFIG_GLOBAL=/dev/null` and `GIT_CONFIG_SYSTEM=/dev/null`
- [x] [AI-Review][Low] Release heading format unasserted: test checks `## [0.3.0] - YYYY-MM-DD`
- [x] [Dev, found while fixing] `make_tmp` leaked every temporary directory: callers use `$(make_tmp)`, a subshell, so the parent never recorded them for cleanup (17 per run). `lib.sh` now creates one root per test file and removes it on exit; verified no leak. 263 leaked fixture directories from earlier runs removed (matched by fixture content only).

## Dev Notes

### Scope

FR155-FR157, Epic 15 ADR-2. Out of scope: writing `CHANGELOG.md` and computing the release version (Story 15.4); seeding `CHANGELOG.md` with the `v0.1.0` summary (Story 15.6).

### Current state

- `15-0-spike/cliff.toml` is the reviewed draft; `15-0-spike/bump_test.sh` and `bump_test.out` show the expected behavior; `sample-notes-epic-14.md` is the expected Epic 14 output.
- No tags exist yet, so `just changelog` lists the project's whole history until `v0.1.0` is tagged. That is expected.
- `scripts/tests/lib.sh` provides `assert_eq`, `assert_contains`, `make_tmp`, `script`, `pass`/`fail`, `finish`; `just test-scripts` runs `scripts/tests/test-*.sh`; CI job "Release scripts" runs `just version` and `just test-scripts` after `jdx/mise-action`.
- Commit types follow user impact since Story 15.0 (`project-context.md`), so task commits for this story are `chore`/`test`/`docs` (tooling), not `feat`.

### Rules

- ADR-2 (with Story 15.0 status): groups Breaking Changes, Features, Fixes, Performance; scopes hidden except `api`, `web`, `docker`; stable-only `tag_pattern = "^v[0-9]+\\.[0-9]+\\.[0-9]+$"`; `features_always_bump_minor = true`, `breaking_always_bump_major = false`, `initial_tag = "v0.1.0"`.
- The fixture repository must not inherit the developer's git config in ways that change output (set `user.name`/`user.email` locally; commit with fixed dates if dates appear in assertions).
- No lint suppressions; shellcheck-clean scripts.

### Testing Requirements

- Bash tests in `scripts/tests/`, run by `just test-scripts` and CI.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 15.3]
- [Source: _bmad-output/planning-artifacts/architecture/epic-15-release-engineering.md] ADR-2
- [Source: _bmad-output/implementation-artifacts/15-0-spike/README.md] §1-§2

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5)

### Completion Notes List

- Task 1: `git-cliff = "2.14.2"` in `.mise.toml`; `cliff.toml` at the root from the reviewed spike draft, with a header comment explaining the rules, a blank line after the header marker (so prepended sections start cleanly), and the empty `commit_preprocessors` removed. Scopes stay in the template.
- Task 2: `just changelog [git-cliff args]` runs `git cliff --unreleased --strip header` and writes nothing. With no tags yet it lists the whole history (392 entries), as expected until `v0.1.0`.
- Task 3: `scripts/tests/test-changelog.sh` (22 assertions) builds fixture repositories with git isolated from the developer's config, hooks and signing, and runs the root `cliff.toml`. It covers group order, every excluded type, review/`ad-hoc`/story scopes, the `api`/`web`/`docker` allowlist and an unlisted scope, `type!:`, the `BREAKING CHANGE:` footer, `refactor!:`, the `story-N.0` and "move story to review" skips, a non-conventional commit, a merge commit (its branch commit still listed), the commit link (7-character text, full SHA URL), and bumps: initial version, nothing releasable, fix/perf → patch, feat → minor, breaking → minor, pre-release tags ignored by bumps and notes, explicit `--bump patch`. A sabotaged config (scope allowlist widened) makes the suite fail. CI's "Release scripts" job already runs `just test-scripts`; `mise-action` installs git-cliff from `.mise.toml`.
- Task 4: `just changelog e9358b9..f32fc26` matches `15-0-spike/sample-notes-epic-14.md` apart from the header. `just check` passes: 2065 API tests, 3007 web tests, 50 script assertions.

### File List

- Created: `cliff.toml`, `scripts/tests/test-changelog.sh`
- Modified: `.mise.toml`, `Justfile`

## Change Log

- 2026-11-10: Story created.
- 2026-11-10: Implemented; `just check` passes. Status review.
- 2026-11-10: Code review (GLM-5.3-Flash, Approve with Lows). Fixed all five Lows and a temp-directory leak found while fixing. Status done.

## Senior Developer Review (AI)

**Date:** 2026-11-10
**Reviewer:** GLM-5.3-Flash via OpenCode (Z.ai coding plan), delegated read-only review of `cb93aba`..`b184e7c`
**Outcome:** Approve (all findings Low)

**Summary:** Verified live with git-cliff 2.14.2: ACs, exact Epic 14 output, bump rules, edge cases (breaking commit in a preparation story kept, `fix!` and footers, reverts and uppercase types dropped, multi-scope, body lines cannot create entries, tag pattern, tag on HEAD gives an empty Unreleased section), and fit for Story 15.4 (`--prepend` keeps the header when `--strip header` is not used) and 15.5 (pre-release headings). Informational: `feat!(api):` is silently dropped (for the release guide in Story 15.6); Story 15.4 must prepend without `--strip header`.

### Action Items

- [x] [Low] Range example in `just changelog`
- [x] [Low] Pin parser order
- [x] [Low] Guard against a missing git-cliff
- [x] [Low] Full git isolation
- [x] [Low] Assert the release heading
