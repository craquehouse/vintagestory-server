# Story 15.6: Release Documentation and First Release

Status: review

## Story

As a **new user**,
I want **installation instructions for a specific release**,
so that **I can deploy and upgrade predictably**.

## Acceptance Criteria

1. **Given** the README
   **When** I follow the installation section
   **Then** it installs a pinned release, explains upgrading, explains verifying the image, and states that anyone who can load the web UI receives its API key

2. **Given** the release guide
   **When** a maintainer reads it
   **Then** it explains which commits become release notes, `just changelog`, `just release`, what the workflow publishes, and the one-time package visibility step
   *(FR166)*

3. **Given** the rest of the README
   **When** a reader compares it with the product
   **Then** it describes delivered features rather than planned ones
   **And** its tool versions and commands match `.mise.toml` and the Justfile

4. **Given** Stories 15.1-15.5 are merged
   **When** the maintainer cuts `v0.1.0`
   **Then** the GitHub release, image tags and attestations exist
   **And** the image starts with `docker-compose.yaml` and the UI works

## Tasks / Subtasks

- [x] Task 1: README (AC: 1, 3)
  - [x] 1.1: Installation from a pinned release (`ghcr.io/craquehouse/vintagestory-server:X.Y.Z` in `docker-compose.yaml`), configuration (`.env` from `.env.example`), first start
  - [x] 1.2: Upgrading (change the tag, `docker compose pull && docker compose up -d`; data lives in the volume), and where release notes are (GitHub releases, `CHANGELOG.md`)
  - [x] 1.3: Verifying an image: `gh attestation verify oci://ghcr.io/craquehouse/vintagestory-server:X.Y.Z --owner craquehouse`, and the SBOM attestation (`--predicate-type https://spdx.dev/Document/v2.3`)
  - [x] 1.4: Security note: the web UI receives `VS_API_KEY` (or the Admin key) at runtime, so anyone who can load the UI has that key; keep the port on a trusted network or behind authentication; `VS_API_KEY` set to the Monitor key gives a read-only UI
  - [x] 1.5: Accuracy pass: delivered features (Epics 1-14), components, development setup (tool versions from `.mise.toml`), commands from the Justfile (`just docker start`, `just test-e2e-api`, `just test-e2e-web`, …), link to `RELEASING.md`

- [x] Task 2: Release guide `RELEASING.md` (AC: 2)
  - [x] 2.1: Versioning (one SemVer version; 0.x rules; pre-releases `-alpha.N`/`-beta.N`/`-rc.N`), which commits become notes (types, `!`/`BREAKING CHANGE`, hidden scopes, the `api`/`web`/`docker` allowlist, `feat!(api):` is not valid and is dropped), `just changelog`
  - [x] 2.2: Cutting a release: `just release --dry-run`, `just release [patch|minor|major|X.Y.Z[-pre]]`, preconditions, confirmation, rollback, repository hooks skipped, pre-releases leave `CHANGELOG.md` alone, hand-written sections are kept, `uv.lock` `revision` churn after a Renovate uv bump
  - [x] 2.3: What the workflow publishes (GitHub release, GHCR tags, SBOM, provenance) and how to watch it; one-time GHCR package visibility step; recovering from a failed run (re-run failed jobs; deleting a broken tag and release)

- [x] Task 3: Agent and compose docs (AC: 2)
  - [x] 3.1: `CLAUDE.md`: commands (`just version`, `just changelog`, `just release`, `just test-scripts`, `just lint-scripts`, `just lint-workflows`); Git Workflow: `feat`/`fix`/`perf` subjects become release notes
  - [x] 3.2: `AGENTS.md`: the same commit-message rule for other agents
  - [x] 3.3: `docker-compose.yaml`: comment on pinning a version tag instead of `latest`

- [x] Task 4: Seed `CHANGELOG.md` (AC: 4)
  - [x] 4.1: `CHANGELOG.md` with the header from `cliff.toml` and a hand-written `## [0.1.0] - YYYY-MM-DD` summary of the product (Story 15.4 keeps it; `release-notes.sh` publishes it)
  - [x] 4.2: `just release --dry-run 0.1.0` in a temporary clone shows the hand-written notes

- [x] Task 5: Validation (AC: 1-3)
  - [x] 5.1: Check every command and path in the README and guide against the Justfile and repository
  - [x] 5.2: `just check`; update the Dev Agent Record and File List

- [ ] Task 6: First release, cut by the maintainer (AC: 4) — after Story 15.5's release-candidate run
  - [ ] 6.1: Maintainer runs `just release 0.1.0` from `main`
  - [ ] 6.2: Verify the release, tags `0.1.0`, `0.1`, `latest`, attestations, and the image with `docker-compose.yaml`; make the package public if not already

### Review Follow-ups (AI)

- [x] [AI-Review][Medium] "Fix the workflow on `main`, then re-run failed jobs" cannot work: a re-run uses the tagged commit's workflow and code. Recovery now separates transient failures (re-run) from bugs (fix on `main`, cut the next version)
- [x] [AI-Review][Medium] "Re-running is safe" was wrong for the release job: `gh release create` fails if the release already exists. The guide says how to finish or delete a partial release before re-running
- [x] [AI-Review][Low] README says MIT but there is no `LICENSE` file: maintainer chose MIT; `LICENSE` added
- [x] [AI-Review][Low] `CLAUDE.md` said a release publishes a "public image"; the image is private until the visibility step: now "pushes the image to GHCR"
- [x] [AI-Review][Low] `VS_API_KEY` "must equal" a role key: README now says other values log a warning and the UI cannot sign in
- [x] [AI-Review][Info] The Installation nav item reads "Version" once a server is installed: noted in the README

## Dev Notes

### Scope

FR166 and the first release. **The maintainer cuts every release and approves every outward-facing step;** this story prepares the documents and the `CHANGELOG.md` seed.

### Facts

- Image: `ghcr.io/craquehouse/vintagestory-server`, `linux/amd64`; tags `X.Y.Z`, `X.Y`, `latest` (pre-releases: `X.Y.Z-rc.N` only).
- Runtime configuration: `VS_API_KEY_ADMIN` (required), `VS_API_KEY_MONITOR`, `VS_API_KEY` (web UI key, default Admin; must equal one of the role keys or start-up warns), `VS_GAME_VERSION`, `VS_DEBUG`, `VS_DATA_DIR`, `VS_CORS_ORIGINS`, others in `config.py`/`.env.example`.
- The current README says "Features (Planned)", Python 3.13, `just docker-start` and `just test-e2e`; `.mise.toml` pins Python 3.14, uv 0.13.7, bun 1.4.4, yq, just, git-cliff, actionlint, shellcheck.
- SBOM predicate type for SPDX 2.3 JSON from `anchore/sbom-action` / `actions/attest`: confirm against `gh attestation verify --help` or the attest README before documenting.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 15.6]
- [Source: _bmad-output/planning-artifacts/architecture/epic-15-release-engineering.md]
- Stories 15.1-15.5 completion notes and reviews

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5)

### Completion Notes List

- **Review scope:** Tasks 1-5 are complete. Task 6 (cutting `v0.1.0`) is the maintainer's, after the merge and Story 15.5's release-candidate run.
- Task 1: README rewritten: what it is, delivered features (Epics 1-14), installation from a pinned GHCR release, security note on the runtime key (and the read-only Monitor option), upgrading, verifying provenance and the SBOM attestation (`--predicate-type https://spdx.dev/Document/v2.3`, the SPDX 2.3 predicate `actions/attest` uses for SPDX JSON; Story 15.5's release-candidate run confirms it), a configuration table, development setup from `.mise.toml`, the real commands (`just docker start`, `just test-e2e-api`, `just test-e2e-web`), and a link to `RELEASING.md`. The old README's "Features (Planned)", Python 3.13 and `just docker-start`/`just test-e2e` are gone.
- **Found:** `VS_GAME_VERSION` is no longer read by the API since `VSS-tpe` (nothing uses `Settings.game_version`), though compose files and `.env.example` still set it. The README does not document it; filed `VSS-ms0`.
- **Found:** there was no `LICENSE` file although the README says MIT; the maintainer chose MIT and `LICENSE` was added.
- Task 2: `RELEASING.md`: versions and 0.x bump rules, pre-release forms and their PEP 440 spelling, which commits become notes (types, breaking markers, hidden scopes, the `api`/`web`/`docker` allowlist, the invalid `feat!(api):` spelling), `just changelog`, `just release` (preconditions, steps, rollback, hooks skipped, hand-written sections, `uv.lock` revision churn), what the workflow publishes, the one-time package visibility step, and recovery (re-run failed jobs, withdrawing a release, fixing notes).
- Task 3: `CLAUDE.md` commands (scripts, workflows, releases) and a rule never to run a real release or push a tag unless asked; Git Workflow rule that commit types are release notes. `AGENTS.md` gets the same rule. `docker-compose.yaml` comments on pinning a version.
- Task 4: `CHANGELOG.md` with the `cliff.toml` header and a hand-written `## [0.1.0] - 2026-11-10` summary. A dry run of `release.sh 0.1.0` in a temporary clone uses this section, and `release-notes.sh 0.1.0` prints it. **If `v0.1.0` is cut on a later day, update the date in the heading first.**
- Task 5: every `just` recipe and file link in the README and guide checked against the Justfile and repository. `just check` passes.

### File List

- Created: `RELEASING.md`, `CHANGELOG.md`, `LICENSE`
- Modified: `README.md`, `CLAUDE.md`, `AGENTS.md`, `docker-compose.yaml`

## Change Log

- 2026-11-10: Story created.
- 2026-11-10: Tasks 1-5 done; `just check` passes. Status review; Task 6 follows the merge and the release-candidate run.
- 2026-11-10: Code review (GLM-5.3-Flash, Changes Requested). Fixed both Mediums and two Lows; `LICENSE` left to the maintainer. Code review complete; the story stays in review until Task 6 (`v0.1.0`).
- 2026-11-10: Maintainer chose MIT; `LICENSE` added.

## Senior Developer Review (AI)

**Date:** 2026-11-10
**Reviewer:** GLM-5.3-Flash via OpenCode (Z.ai coding plan), delegated read-only review of `7275d7f`..`82be309`
**Outcome:** Changes Requested → resolved

**Summary:** Every command, path, variable and behavior claim in the README and release guide was checked against the Justfile, `.mise.toml`, the scripts, `cliff.toml`, the workflow and the API; the SPDX predicate type was confirmed in `actions/attest`'s source; the `CHANGELOG.md` summary was traced to shipped code (no overclaims). The recovery section misdescribed re-runs.

### Action Items

- [x] [Medium] Re-runs use the tagged commit's workflow
- [x] [Medium] Partial GitHub release on re-run
- [x] [Low] `LICENSE` file (maintainer chose MIT)
- [x] [Low] "Public image" wording
- [x] [Low] `VS_API_KEY` enforcement wording
