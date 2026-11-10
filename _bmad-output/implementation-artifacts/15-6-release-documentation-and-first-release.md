# Story 15.6: Release Documentation and First Release

Status: ready-for-dev

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

- [ ] Task 1: README (AC: 1, 3)
  - [ ] 1.1: Installation from a pinned release (`ghcr.io/craquehouse/vintagestory-server:X.Y.Z` in `docker-compose.yaml`), configuration (`.env` from `.env.example`), first start
  - [ ] 1.2: Upgrading (change the tag, `docker compose pull && docker compose up -d`; data lives in the volume), and where release notes are (GitHub releases, `CHANGELOG.md`)
  - [ ] 1.3: Verifying an image: `gh attestation verify oci://ghcr.io/craquehouse/vintagestory-server:X.Y.Z --owner craquehouse`, and the SBOM attestation (`--predicate-type https://spdx.dev/Document/v2.3`)
  - [ ] 1.4: Security note: the web UI receives `VS_API_KEY` (or the Admin key) at runtime, so anyone who can load the UI has that key; keep the port on a trusted network or behind authentication; `VS_API_KEY` set to the Monitor key gives a read-only UI
  - [ ] 1.5: Accuracy pass: delivered features (Epics 1-14), components, development setup (tool versions from `.mise.toml`), commands from the Justfile (`just docker start`, `just test-e2e-api`, `just test-e2e-web`, …), link to `RELEASING.md`

- [ ] Task 2: Release guide `RELEASING.md` (AC: 2)
  - [ ] 2.1: Versioning (one SemVer version; 0.x rules; pre-releases `-alpha.N`/`-beta.N`/`-rc.N`), which commits become notes (types, `!`/`BREAKING CHANGE`, hidden scopes, the `api`/`web`/`docker` allowlist, `feat!(api):` is not valid and is dropped), `just changelog`
  - [ ] 2.2: Cutting a release: `just release --dry-run`, `just release [patch|minor|major|X.Y.Z[-pre]]`, preconditions, confirmation, rollback, repository hooks skipped, pre-releases leave `CHANGELOG.md` alone, hand-written sections are kept, `uv.lock` `revision` churn after a Renovate uv bump
  - [ ] 2.3: What the workflow publishes (GitHub release, GHCR tags, SBOM, provenance) and how to watch it; one-time GHCR package visibility step; recovering from a failed run (re-run failed jobs; deleting a broken tag and release)

- [ ] Task 3: Agent and compose docs (AC: 2)
  - [ ] 3.1: `CLAUDE.md`: commands (`just version`, `just changelog`, `just release`, `just test-scripts`, `just lint-scripts`, `just lint-workflows`); Git Workflow: `feat`/`fix`/`perf` subjects become release notes
  - [ ] 3.2: `AGENTS.md`: the same commit-message rule for other agents
  - [ ] 3.3: `docker-compose.yaml`: comment on pinning a version tag instead of `latest`

- [ ] Task 4: Seed `CHANGELOG.md` (AC: 4)
  - [ ] 4.1: `CHANGELOG.md` with the header from `cliff.toml` and a hand-written `## [0.1.0] - YYYY-MM-DD` summary of the product (Story 15.4 keeps it; `release-notes.sh` publishes it)
  - [ ] 4.2: `just release --dry-run 0.1.0` in a temporary clone shows the hand-written notes

- [ ] Task 5: Validation (AC: 1-3)
  - [ ] 5.1: Check every command and path in the README and guide against the Justfile and repository
  - [ ] 5.2: `just check`; update the Dev Agent Record and File List

- [ ] Task 6: First release, cut by the maintainer (AC: 4) — after Story 15.5's release-candidate run
  - [ ] 6.1: Maintainer runs `just release 0.1.0` from `main`
  - [ ] 6.2: Verify the release, tags `0.1.0`, `0.1`, `latest`, attestations, and the image with `docker-compose.yaml`; make the package public if not already

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

### Completion Notes List

### File List

## Change Log

- 2026-11-10: Story created.
