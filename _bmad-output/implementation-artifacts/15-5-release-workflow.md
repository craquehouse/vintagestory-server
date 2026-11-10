# Story 15.5: Release Workflow

Status: ready-for-dev

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

- [ ] Task 1: `scripts/release-notes.sh VERSION` (AC: 1, 3)
  - [ ] 1.1: Prints the notes for a version: the `CHANGELOG.md` section (exact `## [X.Y.Z]` heading match) when present; for a pre-release without a section, `git cliff --unreleased --tag vX --strip all` (everything since the last stable release); fails for a stable version without a section
  - [ ] 1.2: Tests in `scripts/tests/test-release-notes.sh` (fixture repositories as in `test-release.sh`)

- [ ] Task 2: `.github/workflows/release.yml` (AC: 1-5)
  - [ ] 2.1: Trigger `push: tags: ["v*"]`; `permissions: {}` at the top; one run per tag, never cancelled
  - [ ] 2.2: `verify` job (`contents: read`): full checkout; mise; tag equals `v` + `just version`; the tagged commit is on `origin/main`; pre-release flag; notes from `scripts/release-notes.sh`, uploaded as an artifact
  - [ ] 2.3: `image` job (`contents: read`, `packages: write`, `id-token: write`, `attestations: write`, `artifact-metadata: write`): buildx, GHCR login with `GITHUB_TOKEN`, `docker/metadata-action` (`{{version}}` priority 910, `{{major}}.{{minor}}`, default `latest=auto`), build and push `linux/amd64` with buildx `provenance`/`sbom` off, `actions/attest` provenance, `anchore/sbom-action` SPDX for the digest, `actions/attest` with `sbom-path`, SBOM artifact
  - [ ] 2.4: `release` job (`contents: write`): `gh release create vX --verify-tag --notes-file notes.md`, `--prerelease` for pre-releases, SBOM attached; runs only after `image` succeeds
  - [ ] 2.5: Actions pinned to the SHAs recorded in Story 15.0 (re-checked for newer releases), version comments for Renovate

- [ ] Task 3: Lint workflows (AC: 5)
  - [ ] 3.1: Pin `actionlint` in `.mise.toml`; `just lint-workflows`; run it in CI's "Release scripts" job
  - [ ] 3.2: `scripts/tests/test-docker-context.sh` sibling or a new check: every `uses:` in `.github/workflows/` is pinned to a 40-character SHA

- [ ] Task 4: End-to-end check with a release candidate (AC: 1-4) — after this branch is merged, with the maintainer's approval
  - [ ] 4.1: Maintainer approves; from `main`, `just release 0.1.0-rc.1`
  - [ ] 4.2: Verify: workflow green; GHCR has `0.1.0-rc.1` only (no `0.1`, no `latest`); GitHub pre-release with generated notes and the SBOM; `gh attestation verify oci://ghcr.io/craquehouse/vintagestory-server:0.1.0-rc.1 --owner craquehouse` passes for provenance and the SBOM predicate; image labels; the image runs
  - [ ] 4.3: Negative check without publishing: a tag/version mismatch fails in `verify` (covered by `release-notes.sh`/`version.sh` tests and the `verify` step logic; a real mismatched tag is not pushed)

- [ ] Task 5: Validation
  - [ ] 5.1: `just check`, `just lint-workflows`; update the Dev Agent Record and File List
  - [ ] 5.2: After Task 4: AAR on `VSS-3es` ([CICD-005] Add release action) and close it

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

### Completion Notes List

### File List

## Change Log

- 2026-11-10: Story created.
