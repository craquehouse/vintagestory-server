# Story 15.5: Release Workflow

Status: review

## Story

As a **user of the published image**,
I want **each release published with notes and verifiable provenance**,
so that **I can install a specific version and trust where it came from**.

## Acceptance Criteria

1. **Given** a pushed tag `vX.Y.Z`
   **When** the release workflow runs
   **Then** a GitHub release is published with that version's changelog section as notes
   *(FR161)*

2. **Given** a stable version
   **When** the image is published
   **Then** GHCR has tags `X.Y.Z`, `X.Y` and `latest`
   **And** a pre-release version gets only its full tag and a GitHub pre-release
   *(FR162)*

3. **Given** a tag that does not match the repository's version
   **When** the workflow runs
   **Then** it fails before publishing anything
   *(FR163)*

4. **Given** a published image
   **When** a user runs `gh attestation verify` against it
   **Then** its signed build provenance verifies
   **And** an SBOM is attested for the image and attached to the release
   *(FR164)*

5. **Given** the workflow
   **When** it is reviewed
   **Then** each job has least-privilege permissions, actions are pinned to commit SHAs, and the image carries OCI version, revision and source labels
   *(NFR17, NFR18)*

## Tasks / Subtasks

- [x] Task 1: `scripts/release-notes.sh VERSION` (AC: 1, 3)
  - [x] 1.1: Prints the notes for a version: the `CHANGELOG.md` section (exact `## [X.Y.Z]` heading match) when present; for a pre-release without a section, `git cliff --unreleased --tag vX --strip all` (everything since the last stable release); fails for a stable version without a section
  - [x] 1.2: Tests in `scripts/tests/test-release-notes.sh` (fixture repositories as in `test-release.sh`)

- [x] Task 2: `.github/workflows/release.yml` (AC: 1-5)
  - [x] 2.1: Trigger `push: tags: ["v*"]`; `permissions: {}` at the top; one run per tag, never cancelled
  - [x] 2.2: `verify` job (`contents: read`): full checkout; mise; tag equals `v` + `just version`; the tagged commit is on `origin/main`; pre-release flag; notes from `scripts/release-notes.sh`, uploaded as an artifact
  - [x] 2.3: `image` job (`contents: read`, `packages: write`, `id-token: write`, `attestations: write`, `artifact-metadata: write`): buildx, GHCR login with `GITHUB_TOKEN`, `docker/metadata-action` (`{{version}}` priority 910, `{{major}}.{{minor}}`, default `latest=auto`), build and push `linux/amd64` with buildx `provenance`/`sbom` off, `actions/attest` provenance, `anchore/sbom-action` SPDX for the digest, `actions/attest` with `sbom-path`, SBOM artifact
  - [x] 2.4: `release` job (`contents: write`): `gh release create vX --verify-tag --notes-file notes.md`, `--prerelease` for pre-releases, SBOM attached; runs only after `image` succeeds
  - [x] 2.5: Actions pinned to the SHAs recorded in Story 15.0 (re-checked for newer releases), version comments for Renovate

- [x] Task 3: Lint workflows (AC: 5)
  - [x] 3.1: Pin `actionlint` in `.mise.toml`; `just lint-workflows`; run it in CI's "Release scripts" job
  - [x] 3.2: Check in `scripts/tests/test-docker-context.sh`: every `uses:` in `.github/workflows/` is pinned to a 40-character SHA

- [ ] Task 4: End-to-end check with a release candidate (AC: 1-4) — after this branch is merged, with the maintainer's approval
  - [ ] 4.1: Maintainer approves; from `main`, `just release 0.1.0-rc.1`
  - [ ] 4.2: Verify: workflow green; GHCR has `0.1.0-rc.1` only (no `0.1`, no `latest`); GitHub pre-release with generated notes and the SBOM; `gh attestation verify oci://ghcr.io/craquehouse/vintagestory-server:0.1.0-rc.1 --owner craquehouse` passes for provenance and the SBOM predicate; image labels; the image runs
  - [ ] 4.3: Negative check without publishing: a tag/version mismatch fails in `verify` (covered by `release-notes.sh`/`version.sh` tests and the `verify` step logic; a real mismatched tag is not pushed)

- [ ] Task 5: Validation
  - [x] 5.1: `just check`, `just lint-workflows`; update the Dev Agent Record and File List
  - [ ] 5.2: After Task 4: AAR on `VSS-3es` ([CICD-005] Add release action) and close it

### Review Follow-ups (AI)

- [x] [AI-Review][Medium] The release job was not idempotent: a failure after `gh release create` (e.g. the SBOM upload) left a release without its SBOM that no re-run could fix. The job now edits an existing release or creates it, then uploads the SBOM with `--clobber`; `RELEASING.md` updated
- [x] [AI-Review][Low] `release-notes.sh` hid git-cliff's errors: stderr is captured separately and shown on failure
- [x] [AI-Review][Low] The pin check flagged local (`./`) and digest-pinned `docker://` actions: both are accepted
- [x] [AI-Review][Low] Release builds are not reproducible (`uv:latest`, `apt-get upgrade`; pre-existing): filed `VSS-870`
- [x] [AI-Review][Low] Pre-release notes will contain old bookkeeping entries until the first stable tag (history before the commit-type change; expected for `v0.1.0-rc.1`)
- [x] [AI-Review][Low] Empty pre-release notes: `release-notes.sh` prints "No user-facing changes since the last stable release."; test added

## Dev Notes

### Scope and sequencing

FR161-FR164, NFR17-NFR18, Epic 15 ADR-4. A tag-triggered workflow runs the workflow file in the tagged commit, and `just release` runs only on `main`, so Task 4 needs this branch merged first. Tasks 1-3 and 5.1 are done and reviewed on the branch; Task 4 and 5.2 follow the merge. **Do not push any tag, image or release without the maintainer's explicit approval.**

### Facts from earlier stories

- Draft workflow: `15-0-spike/release.yml` (passes actionlint; pins and permissions in `15-0-spike/README.md` §4). It needs `just version` (15.1), git-cliff in `.mise.toml` and `cliff.toml` (15.3), `CHANGELOG.md` (15.4/15.6), all now present except `CHANGELOG.md`, which `release.sh` creates or Story 15.6 seeds.
- `actions/attest` v4 replaces `attest-build-provenance` and `attest-sbom`; it needs `artifact-metadata: write` for the storage record.
- `docker/metadata-action`: pre-releases only get `{{version}}`; `{{version}}` with higher priority sets the `org.opencontainers.image.version` label.
- The first push creates a private GHCR package linked to the repository; making it public is a manual step (Story 15.6 documents it).
- `CHANGELOG.md` lists stable releases; pre-release notes are generated (stable-only `tag_pattern` in `cliff.toml`).
- Story 15.4: `release.sh` keeps an existing section and runs git without repository hooks.

### Rules

- NFR17: `permissions: {}` at the workflow level, minimal per job; every action SHA-pinned with a version comment.
- NFR18: OCI labels from metadata-action (`version`, `revision`, `source`, `created`).
- Commit types: workflow and scripts are `ci`/`chore`; tests `test`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 15.5]
- [Source: _bmad-output/planning-artifacts/architecture/epic-15-release-engineering.md] ADR-4
- [Source: _bmad-output/implementation-artifacts/15-0-spike/README.md] §4

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5)

### Completion Notes List

- **Review scope:** Tasks 1-3 and 5.1 are complete. Task 4 (release-candidate run) and 5.2 (`VSS-3es`) need this branch merged and the maintainer's approval; the story stays open for them after review.
- Task 1: `scripts/release-notes.sh VERSION` prints a version's `CHANGELOG.md` section (exact heading match, leading blank lines trimmed); a pre-release without a section gets `git cliff --unreleased --tag vX --strip all` with the version heading removed; a stable version without a section fails. 11 assertions in `test-release-notes.sh` (stable, leading `v`, `0.1.0` vs `0.10.0`, pre-release notes across an rc tag, missing section, invalid version).
- Task 2: `.github/workflows/release.yml` from the spike draft. `verify` runs `just version`, requires the tag to equal `v` + version and the tagged commit to be on `origin/main` (releases are cut from `main`), sets the pre-release flag, writes notes with `release-notes.sh` (also to the job summary) and uploads them. `image` and `release` follow ADR-4 with the Story 15.0 pins (re-checked: no newer releases). `release` needs `image`, so a failed build publishes no release. Top-level `permissions: {}`; per-job minimum; concurrency per tag, never cancelled.
- Task 3: `actionlint` 1.7.12 and `shellcheck` 0.11.0 pinned in `.mise.toml`; `just lint-scripts` and `just lint-workflows` (actionlint also runs ShellCheck on `run:` steps) are part of `just lint`; CI's "Release scripts" job runs both. `test-docker-context.sh` checks every workflow `uses:` is pinned to a 40-character SHA. `scripts/sprint-status.sh` has existing ShellCheck findings and is excluded; filed `VSS-1eb`.
- Task 5.1: `just check` passes: 2065 API tests, 3007 web tests, 189 script assertions; lints clean.

### File List

- Created: `.github/workflows/release.yml`, `scripts/release-notes.sh`, `scripts/tests/test-release-notes.sh`
- Modified: `.mise.toml`, `Justfile`, `.github/workflows/ci.yml`, `scripts/tests/test-docker-context.sh`

## Change Log

- 2026-11-10: Story created.
- 2026-11-10: Tasks 1-3 and 5.1 implemented; `just check` passes. Status review; Task 4 follows the merge.
- 2026-11-10: Code review (GLM-5.3-Flash, Approve with findings). Fixed the Medium and four Lows, filed one. Code review complete; Task 4 (release candidate) and 5.2 follow the merge.

## Senior Developer Review (AI)

**Date:** 2026-11-10
**Reviewer:** GLM-5.3-Flash via OpenCode (Z.ai coding plan), delegated read-only review of `4de2688`..`7275d7f`
**Outcome:** Approve (one Medium, five Low)

**Summary:** All ten SHA pins resolved against their versions; per-job permissions match the `actions/attest` README at the pinned SHA (including `artifact-metadata: write`); metadata-action tag and label behavior confirmed from its README; no untrusted interpolation in `run:` blocks; the version argument is regex-validated; `release` needs `verify` and `image`, so a mismatch or failed build publishes nothing. Script suites pass under bash 3.2.57 and 5.3. Not checked by design: the real GHCR push, attestation and verification round-trip (Task 4).

### Action Items

- [x] [Medium] Idempotent release job
- [x] [Low] Show git-cliff errors
- [x] [Low] Pin check false positives
- [x] [Low] Reproducible builds (`VSS-870`)
- [x] [Low] Bookkeeping in pre-release notes (expected)
- [x] [Low] Empty pre-release notes
