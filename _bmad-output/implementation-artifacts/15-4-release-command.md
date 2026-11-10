# Story 15.4: Release Command

Status: ready-for-dev

## Story

As a **maintainer**,
I want **to cut a release with one command**,
so that **version, changelog, commit and tag are always consistent**.

## Acceptance Criteria

1. **Given** unreleased commits on `main`
   **When** I run `just release`
   **Then** the next version is computed from the commits
   **And** `just release patch|minor|major` or `just release X.Y.Z[-pre]` overrides it

2. **Given** a version is chosen
   **When** the release runs
   **Then** it updates `api/pyproject.toml`, `api/uv.lock`, `web/package.json` and `CHANGELOG.md`
   **And** commits them as `chore(release): vX.Y.Z` with an annotated tag `vX.Y.Z`
   **And** asks for confirmation, then pushes the commit and tag together
   *(FR158)*

3. **Given** I am not on `main`, the working tree is dirty, `main` differs from its remote, the tag exists, or the version is not newer than the last release
   **When** I run `just release`
   **Then** it stops with a clear message and changes nothing
   *(FR159)*

4. **Given** `just release --dry-run`
   **When** it runs
   **Then** it shows the version and notes and changes nothing
   *(FR160)*

5. **Given** an explicit pre-release version such as `0.3.0-rc.1`
   **When** the release runs
   **Then** it updates the version files, commits and tags, but leaves `CHANGELOG.md` unchanged
   **And** the next stable release's notes cover everything since the last stable release

6. **Given** no releasable commits since the last release and no explicit version
   **When** I run `just release`
   **Then** it reports that there is nothing to release

7. **Given** a step fails before the push
   **When** the release stops
   **Then** no release commit or tag is left behind

8. **Given** `CHANGELOG.md` already has a section for the version (written by hand, as for `v0.1.0` in Story 15.6)
   **When** the release runs
   **Then** it keeps that section instead of generating one, and shows it as the notes

## Tasks / Subtasks

- [ ] Task 1: `scripts/release.sh` and `just release` (AC: 1, 3, 4, 6)
  - [ ] 1.1: Arguments: `[--dry-run] [patch|minor|major|X.Y.Z[-alpha.N|-beta.N|-rc.N]]` (a leading `v` is accepted); usage on `-h`/unknown flags
  - [ ] 1.2: Preconditions, each with a clear message: required tools (`git`, `git-cliff`, `uv`, `bun`, `yq`); on `main`; clean working tree (`git status --porcelain` empty); `git fetch origin` then `HEAD` equals `origin/main`; `scripts/version.sh` passes
  - [ ] 1.3: Version: none → `git cliff --bumped-version`; a bump word → `git cliff --bump <word> --bumped-version`; explicit → validated like `version.sh`. Refuse an existing tag and a version not newer (SemVer precedence) than the newest existing release tag, stable or pre-release. With no argument, stop with "nothing to release" when the computed version equals the last stable tag
  - [ ] 1.4: Notes: the existing `CHANGELOG.md` section for the version if present (AC 8), else `git cliff --unreleased --tag vX --strip header` (since the last stable tag); print version and notes; `--dry-run` stops here
  - [ ] 1.5: `just release *ARGS` runs the script through `mise exec`

- [ ] Task 2: Version files, changelog, commit, tag, confirmed push (AC: 2, 5, 7, 8)
  - [ ] 2.1: `uv version X --no-sync` in `api/` (writes PEP 440 to `pyproject.toml` and `uv.lock`); `bun pm version X --no-git-tag-version` in `web/`; then `scripts/version.sh` must print `X`
  - [ ] 2.2: Stable versions only: prepend the generated section to `CHANGELOG.md` below its header marker (`git cliff --unreleased --tag vX --prepend CHANGELOG.md`, without `--strip header`), creating the file with the header if it does not exist; refuse a `CHANGELOG.md` without the marker; skip when the section already exists (AC 8). Pre-releases leave `CHANGELOG.md` alone
  - [ ] 2.3: Commit the changed files as `chore(release): vX.Y.Z`; annotated tag `vX.Y.Z`
  - [ ] 2.4: Ask `Push vX.Y.Z to origin? [y/N]` (reads stdin); on yes `git push --atomic origin main vX.Y.Z`
  - [ ] 2.5: Any failure after the first change, a declined confirmation, or a failed push: delete the tag and reset `main` to the starting commit (the tree was clean, so nothing else is lost), then exit non-zero (declined exits 1 with "release cancelled")

- [ ] Task 3: Tests with a temporary repository and remote (AC: all)
  - [ ] 3.1: `scripts/tests/test-release.sh`: fixture project (minimal `api/pyproject.toml` + `uv.lock`, `web/package.json`, the repository's `cliff.toml`, `CHANGELOG.md` with the header), a bare remote, git isolated as in `test-changelog.sh`
  - [ ] 3.2: Cases: dry run changes nothing; auto version; each bump word; explicit version; pre-release (files updated, `CHANGELOG.md` unchanged) then a stable release whose notes include pre-release-era commits; hand-written section kept; first release without `CHANGELOG.md`; declined confirmation; every precondition; nothing to release; invalid version; `CHANGELOG.md` without marker; push rejected by the remote (pre-receive hook) leaves no local commit or tag
  - [ ] 3.3: After a successful release assert: one new commit with the expected message and files, annotated tag on it, both on the remote, `version.sh` agrees, `CHANGELOG.md` section placement
  - [ ] 3.4: Runs in CI through `just test-scripts`

- [ ] Task 4: Validation (AC: all)
  - [ ] 4.1: `just release --dry-run` in this repository (no tags yet: expect `v0.1.0` and the whole history); confirm nothing changed
  - [ ] 4.2: `just check`; update the Dev Agent Record and File List

## Dev Notes

### Scope

FR158-FR160, Epic 15 ADR-3 (with Story 15.0 status). Out of scope: the release workflow (15.5); the real `v0.1.0` release and `CHANGELOG.md` seed (15.6). **Never run a real (non-dry) release or push a tag in this repository**; tests use temporary repositories only.

### Facts from Stories 15.0-15.3

- `uv version X --no-sync` changes only the version lines in `pyproject.toml` and `uv.lock`, normalizing to PEP 440 (`0.2.0-rc.1` → `0.2.0rc1`); `bun pm version X --no-git-tag-version` changes only `package.json`, keeping SemVer.
- `git cliff --bumped-version` returns the last stable tag unchanged when nothing is releasable, and `v0.1.0` (`initial_tag`) with no tags. Pre-release tags are invisible (`tag_pattern`). `--prepend` must not be combined with `--strip header` (it eats the header). The release heading is `## [X.Y.Z] - YYYY-MM-DD`; the header ends with `<!-- git-cliff: end of header -->` and a blank line.
- `scripts/version.sh [root]` prints the SemVer version and fails if the files disagree; validation regex and PEP 440 mapping live there.
- Test helpers: `scripts/tests/lib.sh` (`assert_eq`, `assert_contains`, `make_tmp` inside a per-file root, `script`, `finish`); `test-changelog.sh` shows git isolation (`GIT_CONFIG_GLOBAL=/dev/null`, `GIT_CONFIG_SYSTEM=/dev/null`, identity, no signing, `core.hooksPath=/dev/null`) and the git-cliff availability guard.
- The script runs in the current repository (`git rev-parse --show-toplevel`), not the script's own checkout, so tests can call it from fixture repositories.

### Rules

- ADR-3: preconditions, version choice, dry run, file updates, commit and annotated tag, confirmed atomic push, reset on failure; no `just check` inside the command.
- Commit types: the release command is tooling (`chore`), tests `test`.
- shellcheck-clean, bash 3.2 compatible (macOS), no suppressions.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 15.4]
- [Source: _bmad-output/planning-artifacts/architecture/epic-15-release-engineering.md] ADR-1, ADR-2, ADR-3
- [Source: _bmad-output/implementation-artifacts/15-3-changelog-generation.md] review notes

## Dev Agent Record

### Agent Model Used

### Completion Notes List

### File List

## Change Log

- 2026-11-10: Story created. AC 8 added so the hand-written `v0.1.0` section (Story 15.6) is kept.
