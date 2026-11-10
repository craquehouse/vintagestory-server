# Story 15.0: Epic 15 Technical Preparation

Status: done

<!-- Spike story (template-api-spike). Complete before Stories 15.1-15.6: their designs rest on the assumptions this story verifies. Nothing is published in this story. -->

## Story

As a **developer**,
I want **the release toolchain verified against this repository**,
so that **the release stories rest on confirmed behavior**.

## Acceptance Criteria

1. **Given** this repository's history
   **When** git-cliff runs with a draft configuration
   **Then** findings show generated notes for a recent range, and the filter and scope rules that make them readable
   **And** the component scope allowlist (ADR-2) is chosen from the scopes actually used

2. **Given** a 0.x version
   **When** the next version is computed from commits
   **Then** findings confirm that features bump the minor version, fixes the patch version, and breaking changes the minor version

3. **Given** the container image
   **When** the API reads its version from package metadata
   **Then** findings confirm it returns the version in `pyproject.toml`
   **And** findings name the commands that set the version in `pyproject.toml` with `uv.lock`, and in `web/package.json`

4. **Given** GitHub Actions on this public organization repository
   **When** publishing to GHCR with attestations is researched
   **Then** findings document the required permissions, the tag rules for 0.x and pre-release versions, the SBOM and provenance approach with pinned action versions, and the one-time package visibility step

5. **Given** the findings
   **When** they are compared with Epic 15 ADR-1 to ADR-5
   **Then** each ADR is marked confirmed or changed in `architecture/epic-15-release-engineering.md`
   **And** any assumption that failed has a recorded decision, with affected Epic 15 stories updated or beads created

## Tasks / Subtasks

<!-- Research story: no application code changes. Tasks produce documentation and spike scripts under 15-0-spike/. -->

- [x] Task 1: Changelog generation against real history (AC: 1)
  - [x] 1.1: Install git-cliff through mise without changing `.mise.toml` (e.g. `mise exec git-cliff@<version> -- git cliff ...`); record the latest version
  - [x] 1.2: Draft `15-0-spike/cliff.toml` per ADR-2: conventional commits only, merge commits dropped, groups Breaking Changes / Features / Fixes / Performance, commit links, scopes hidden except an allowlist
  - [x] 1.3: Tally scopes on `feat`/`fix`/`perf` commits and choose the allowlist
  - [x] 1.4: Generate notes for a recent range (Epic 14: from the planning commit `e9358b9` to the merge `f32fc26`) and save the output; review it for unreadable entries and adjust the rules
  - [x] 1.5: Confirm how breaking changes are detected (`!` and `BREAKING CHANGE` footer) and that a breaking commit of an otherwise skipped type (e.g. `refactor!:`) is kept

- [x] Task 2: Version bump rules (AC: 2)
  - [x] 2.1: In a throwaway repository under the scratchpad, tag `v0.1.0`, then add `fix`, `feat` and breaking commits in turn and record `git cliff --bumped-version` after each
  - [x] 2.2: Record the `[bump]` settings that give feat→minor, fix→patch, breaking→minor on 0.x; record behavior with no releasable commits
  - [x] 2.3: Check how a pre-release tag (e.g. `v0.2.0-rc.1`) affects the next computed version

- [x] Task 3: Version files and package metadata (AC: 3)
  - [x] 3.1: Build the image (`docker build --target final`, a throwaway tag) and run `python -c "import importlib.metadata as m; print(m.version('vintagestory-api'))"` inside it with the image's environment; record the result
  - [x] 3.2: On a scratch copy of `api/`, verify the uv command that sets the project version and updates `uv.lock` (e.g. `uv version X.Y.Z`), and that it does not upgrade dependencies
  - [x] 3.3: On a scratch copy of `web/package.json`, verify a command that sets the version without creating a git commit or tag (e.g. `bun pm version X.Y.Z --no-git-tag-version`, or `yq`/`jq`); record the one chosen
  - [x] 3.4: Remove the throwaway image afterwards (ask the user if the removal safety check blocks it)

- [x] Task 4: GHCR publishing, tags and attestations (AC: 4)
  - [x] 4.1: From current documentation, record the latest release and commit SHA of `docker/login-action`, `docker/metadata-action`, `docker/setup-buildx-action`, `docker/build-push-action`, `actions/attest-build-provenance` (or its successor), `actions/attest-sbom` (or its successor) and an SBOM generator (e.g. `anchore/sbom-action`)
  - [x] 4.2: Confirm `docker/metadata-action` tag output for `v0.1.0`, `v0.2.3` and `v0.2.0-rc.1` with patterns `{{version}}` and `{{major}}.{{minor}}` and `latest=auto`: which tags each gets, and whether `{{major}}` would produce `0` (ADR-4 excludes it)
  - [x] 4.3: Record the permissions each job needs, how `push-to-registry` attestations appear in GHCR, and the `gh attestation verify` command users run
  - [x] 4.4: Record how a GHCR package created by `GITHUB_TOKEN` gets its visibility and repository link, and the manual step to make it public
  - [x] 4.5: Record whether buildx's own `provenance`/`sbom` attestations should be disabled to avoid duplicate or unknown-platform manifests
  - [x] 4.6: Validate a draft `15-0-spike/release.yml` with `actionlint` (via `mise exec`) if available; do not add it to `.github/workflows/`

- [x] Task 5: Record findings and update plans (AC: 5)
  - [x] 5.1: Write `15-0-spike/README.md`: what each script and output is, how to rerun it
  - [x] 5.2: Mark each ADR in `architecture/epic-15-release-engineering.md` confirmed or changed, with evidence
  - [x] 5.3: If an assumption failed, record the decision; update the affected stories in `epics.md`, or create a bead
  - [x] 5.4: Run `just check` to confirm nothing broke

### Review Follow-ups (AI)

- [x] [AI-Review][High] `VSS-flj` reported as never filed (rejected: it exists in the Dolt store, `bd show VSS-flj`; the reviewer read `.beads/issues.jsonl`, a passive export last committed in January)
- [x] [AI-Review][Medium] AC3 evidence was prose only: added `version_check.sh` and its captured output `version_check.out`
- [x] [AI-Review][Medium] Draft `release.yml` prerequisites not named: README and ADR-4 now list `just version`, git-cliff in `.mise.toml`, root `cliff.toml`, `CHANGELOG.md`
- [x] [AI-Review][Low] Default-pattern pre-release bump not in `bump_test.out`: added the case
- [x] [AI-Review][Low] Notes extraction used the version as a regex: exact heading match
- [x] [AI-Review][Low] Scope allowlist rationale read backwards: reworded with the real tallies; the allowlist stays forward-looking
- [x] [AI-Review][Low] `--latest` claim not demonstrated: test now adds a commit after the tag
- [x] [AI-Review][Low] Current-state tallies differ from the reviewer's (accepted: they reproduce with `git log --no-merges --format=%s main | grep -cE '^feat(\(|!|:)'` → 269, docs 162; counting-method difference)
- [x] [AI-Review][Low] `bump_test.sh` ran `rm -rf` on a caller-supplied path: now uses `mktemp -d` with cleanup on exit

## Dev Notes

### Why this story matters

| Assumption | Used by | If it fails |
|---|---|---|
| git-cliff can drop BMAD scopes and produce readable notes from this history | ADR-2, Story 15.3 | Different filter rules, or a commit-message convention change in the release guide |
| git-cliff bumps 0.x as feat→minor, fix→patch, breaking→minor | ADR-2/3, Story 15.4 | The release command computes the version itself |
| `importlib.metadata` resolves inside the image (`uv sync` runs before `src/` is copied) | ADR-1, Story 15.1 | Version needs another runtime source, e.g. a generated `_version.py` or a Dockerfile change |
| `uv` and `bun` can set the version without side effects | ADR-3, Story 15.4 | Edit the files with `yq`/`sed` and run `uv lock` |
| `metadata-action` gives `X.Y.Z`, `X.Y`, `latest`, and only `X.Y.Z` for pre-releases | ADR-4, Story 15.5 | Explicit tag rules in the workflow |
| GitHub artifact attestations work for GHCR images from a public org repo | ADR-4, FR164 | A different signing approach (e.g. cosign) |

### Constraints

- **Publish nothing.** No tags pushed, no images pushed, no workflows added to `.github/workflows/`, no GitHub releases. Story 15.5 does the first end-to-end run, with the maintainer's approval.
- Do not change `.mise.toml`, `cliff.toml` at the root, the Dockerfile or application code; Stories 15.1-15.4 do that.
- Use the scratchpad for throwaway repositories and copies; keep scripts and outputs worth keeping in `_bmad-output/implementation-artifacts/15-0-spike/`.
- Never use the repo's `./data` volume for the image check; run with no host volume.
- `docker image rm` is blocked by the removal safety check; ask the user to remove throwaway images if needed.
- Requires `VS_API_KEY_ADMIN` only if the API is started; the metadata check does not start it.

### Current state (verified 2026-11-10)

- Versions: `api/pyproject.toml` 0.1.0, `api/src/vintagestory_api/__init__.py` `__version__ = "0.1.0"`, `main.py` `FastAPI(version="0.1.0")`, `web/src/components/layout/Sidebar.tsx` hard-codes `v0.1.0`, `web/package.json` 0.0.0.
- Dockerfile: `COPY api/pyproject.toml api/uv.lock ./` then `RUN uv sync --frozen --no-dev`, then `COPY api/src/ ./src/`; CMD `uv run uvicorn ...`.
- CI: `.github/workflows/ci.yml` pins actions by SHA with a version comment (e.g. `docker/build-push-action@c3c9e26... # v7.4.0`); Renovate updates them.
- Commits on `main`: 269 `feat`, 147 `fix`, 162 `docs`, 132 `chore`, 26 `test`, 15 `refactor`, 9 `review`, 7 `ci`; 34 non-conventional. Of `feat`/`fix` scopes, 270 start with `story`; others include `api` 20, `web` 14, `deps` 12, `ui` 9, `VSS` 5, `container` 4, `auth` 4, `ad-hoc` 3.
- Tools in `.mise.toml`: python 3.14, uv 0.13.7, bun 1.4.4, yq 4.54.2, just 1.59.0.

### Output artifacts

- `_bmad-output/implementation-artifacts/15-0-spike/`: `README.md`, draft `cliff.toml`, sample notes, the bump test script and its output, draft `release.yml`.
- Updated `architecture/epic-15-release-engineering.md` (ADR status lines).

### Testing Requirements

- Research story with no application code; no new tests required.
- `just check` must still pass.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 15.0]
- [Source: _bmad-output/planning-artifacts/architecture/epic-15-release-engineering.md] ADR-1 to ADR-5
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-10.md]
- [Source: _bmad-output/implementation-artifacts/14-0-epic-14-technical-preparation.md] spike structure

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5)

### Findings Summary

Full evidence: `15-0-spike/README.md`.

1. **Changelog (AC1):** git-cliff 2.14.2 with the draft `cliff.toml` produces grouped notes with commit links; scopes are hidden in the template except `api`, `web`, `docker`. Epic 14 yields 58 `feat`/`fix` entries; two safety-net parsers (preparation stories, "move story to review") cut that to 43. The remaining noise comes from the `dev-story` rule that every task commit is `feat(story-X.Y/task-N)`.
2. **Bumps (AC2):** confirmed on a throwaway repository: feat → minor, fix/perf → patch, breaking (`!` or footer, including `refactor!`) → minor, explicit `--bump` works. With nothing releasable the computed version equals the last tag. A stable-only `tag_pattern` makes pre-release tags invisible, so stable notes cover everything since the last stable release.
3. **Version files and metadata (AC3):** package metadata returns the `pyproject.toml` version inside the image. `uv version X --no-sync` and `bun pm version X --no-git-tag-version` change only the version lines. uv writes pre-releases in PEP 440 form (`0.2.0rc1`). Found `VSS-flj`: the image's `uv run` CMD downloads dev dependencies at every start and fails offline.
4. **GHCR and attestations (AC4):** `actions/attest` v4.2.2 replaces `attest-build-provenance`/`attest-sbom` and needs `artifact-metadata: write`; attestations work for public repositories on every plan; `gh attestation verify oci://… --owner craquehouse`; metadata-action tag rules from its README; first publish creates a private package linked to the repository, made public by hand. Draft `release.yml` passes `actionlint`.
5. **Plans (AC5):** every ADR marked with its status; Stories 15.1, 15.4 and 15.5 updated in `epics.md`.

### Architecture Decisions Made

- ADR-1: version check compares PEP 440 normalization for pre-releases; image installs the project at build time and starts without syncing (Story 15.1).
- ADR-2: template-level scope allowlist, safety-net parsers, stable-only `tag_pattern`; **maintainer decision:** task commits are typed by user impact (`project-context.md`, `dev-story/instructions.xml` updated).
- ADR-3: exact version-file commands; "nothing to release" detection; pre-releases explicit and outside `CHANGELOG.md`.
- ADR-4: `actions/attest` for provenance and SBOM, `artifact-metadata: write`, buildx `provenance`/`sbom` off, pre-release notes from git-cliff.

### Backlog Items Created

- `VSS-flj` [INFRA-003] Container start re-syncs uv and downloads dev dependencies; API cannot start offline (fixed in Story 15.1).

### Completion Notes List

- Nothing was published: no tags, images, workflows or releases. Tools ran through `mise exec` with `.mise.toml` unchanged.
- The throwaway image `vss-150-spike` is removed by the maintainer (`docker image rm` is blocked by the removal safety check); rerunning `version_check.sh --image` recreates it.
- `just check` passes: 2048 API tests, 2999 web tests.

### File List

- Created: `_bmad-output/implementation-artifacts/15-0-spike/` (`README.md`, `cliff.toml`, `sample-notes-epic-14.md`, `bump_test.sh`, `bump_test.out`, `version_check.sh`, `version_check.out`, `release.yml`)
- Modified: `_bmad-output/planning-artifacts/architecture/epic-15-release-engineering.md`, `_bmad-output/planning-artifacts/epics.md`
- Modified: `project-context.md`, `_bmad/bmm/workflows/4-implementation/dev-story/instructions.xml`

## Change Log

- 2026-11-10: Story created.
- 2026-11-10: Spike complete; ADRs and Stories 15.1, 15.4, 15.5 updated; commit-type rule changed by maintainer decision; `VSS-flj` filed. Status review.
- 2026-11-10: Code review (GLM-5.3-Flash, Changes Requested). Rejected H1 (bead exists), fixed M1, M2, L1-L4, L6, accepted L5. Status done.

## Senior Developer Review (AI)

**Date:** 2026-11-10
**Reviewer:** GLM-5.3-Flash via OpenCode (Z.ai coding plan), delegated read-only review of `0edcf72`^..`b4e8104`
**Outcome:** Changes Requested → resolved

**Summary:** The reviewer regenerated `sample-notes-epic-14.md` and `bump_test.out` byte-identically, re-ran `actionlint`, verified all ten SHA pins against upstream, the per-job permissions, release-after-image ordering and quoted tag handling, and confirmed the `actions/attest` and metadata-action claims from their READMEs. It could not check the Docker, uv and bun claims without a build, which `version_check.sh` now records.

### Action Items

- [x] [High] `VSS-flj` not filed (rejected: exists in Dolt; the JSONL export is stale by design)
- [x] [Medium] Capture AC3 evidence in a script
- [x] [Medium] Name the draft workflow's prerequisites
- [x] [Low] Record the default-pattern pre-release bump
- [x] [Low] Exact-match the CHANGELOG heading
- [x] [Low] Reword the scope allowlist rationale
- [x] [Low] Demonstrate `--latest` behavior
- [x] [Low] Tallies differ (accepted)
- [x] [Low] Guard `rm -rf` in `bump_test.sh`
