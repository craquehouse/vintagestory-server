# Sprint Change Proposal: Release Engineering (Epic 15)

**Date:** 2026-11-10
**Author:** Matt
**Workflow:** correct-course (incremental review)
**Scope classification:** Moderate

## 1. Issue Summary

**Trigger:** New requirement. The PRD's technical success criteria call for "GitHub Actions → Automated releases → Renovate integration" and "SBOM generation" as trust signals. Renovate and CI exist, but releases do not: all 14 epics are done and the project has never published a version.

**Problem:** There is no way to publish an official, versioned release. Users cannot install a known version, see what changed between versions, or verify where an image came from.

**Evidence:**

- No git tags, GitHub releases or `CHANGELOG.md` exist.
- `.github/workflows/ci.yml` builds the Docker image with `push: false`. `docker-compose.yaml` and the architecture (`project-structure-boundaries.md`, "Push to ghcr.io/craquehouse/vintagestory-server") point at `ghcr.io/craquehouse/vintagestory-server:latest`, which nothing publishes.
- The version is hard-coded in four places that already disagree: `api/pyproject.toml` (0.1.0), `api/src/vintagestory_api/__init__.py` (0.1.0), `FastAPI(version="0.1.0")` in `main.py`, and the sidebar footer (`v0.1.0` in `Sidebar.tsx`); `web/package.json` says 0.0.0.
- The web UI's API key is baked into the bundle at image build time (`ARG VS_API_KEY` → `VITE_API_KEY` in the Dockerfile; `client.ts` reads `import.meta.env.VITE_API_KEY`). An image built by CI for everyone would contain no key, so its UI would get 401 on every request. Locally built images today contain the key in the bundle.
- Commit messages are about 95% conventional (269 `feat`, 147 `fix`, 162 `docs`, 132 `chore` on `main`), but 270 of the `feat`/`fix` commits use BMAD scopes such as `story-14.2/task-6`, so raw commit lists are not readable release notes.

**Scope decisions made during review:**

| Decision | Choice |
|---|---|
| Release trigger | `just release` computes the version, updates the changelog and version files, commits, tags and pushes; the tag push triggers a publishing workflow |
| Changelog source | Conventional commits: features, fixes, performance and breaking changes, grouped by type; other types, merge commits and non-conventional messages excluded; BMAD scopes stripped |
| Published per release | GitHub release with notes; GHCR image tagged `X.Y.Z`, `X.Y`, `latest`; SBOM and signed provenance; version shown in the app |
| Versioning | One SemVer version for API, web and image; first release `v0.1.0` |
| Web UI API key | Supplied by the server at runtime (runtime config injection); no key in the image |
| Images from `main` | None; only version tags publish |
| Release health checks (image smoke test, extra CI gate) | Not in scope |

## 2. Impact Analysis

**Epic impact:** Epics 1-14 are done and none is invalidated. One new epic, Epic 15: Release Engineering, with 7 stories. No resequencing.

**Story impact:** No existing story changes.

**Artifact conflicts:**

| Artifact | Change |
|---|---|
| PRD | Add FR152-FR166 and NFR17-NFR18; mark the SBOM growth and Phase 2 items as Epic 15; add versioned releases to growth features; frontmatter |
| Epics | Add Epic 15; Post-MVP FR coverage rows; Story Summary row; frontmatter |
| Architecture | New `architecture/epic-15-release-engineering.md`; index entry; supersede note on the CI/CD pipeline sketch in `project-structure-boundaries.md` |
| UX spec | None. It already specifies version info in the sidebar footer; Epic 15 replaces the hard-coded value |
| Other | README install and upgrade docs, release guide, `docker-compose*.yaml`, `CLAUDE.md`/`AGENTS.md` commands, `.mise.toml` (git-cliff) |

**Technical impact:**

- New tool: git-cliff, pinned in `.mise.toml`, with `cliff.toml` at the repository root.
- New recipes `just version`, `just changelog`, `just release`, backed by `scripts/release.sh`.
- New workflow `.github/workflows/release.yml` with `packages: write`, `id-token: write`, `attestations: write` and `contents: write`.
- API: version read from package metadata; `/healthz` gains a `version` field; new unauthenticated `GET /config.js`.
- Web: version from `package.json` at build time; API key from runtime config, falling back to `VITE_API_KEY` for the dev server.
- Dockerfile: the `VS_API_KEY` build argument is removed.
- Development workflow: `feat`, `fix` and `perf` commit subjects become user-facing release notes.
- MVP is unaffected. Test strategy unchanged; release scripts get their own tests.

## 3. Recommended Approach

**Selected:** Option 1, Direct Adjustment: add Epic 15 within the existing structure.

| Option | Assessment |
|---|---|
| 1. Direct Adjustment | Viable. Additive: new workflow, recipes and config, plus two small app changes (version display, runtime key). Effort medium, risk low. |
| 2. Rollback | Not viable. Nothing completed conflicts with the change. |
| 3. MVP Review | Not needed. The MVP is delivered; this completes a stated technical success criterion. |

**Effort:** Medium. Seven stories, most small: one preparation story, two app changes, three tooling and CI stories, one documentation and first-release story.

**Risks:**

- First GHCR publish from Actions creates the package; making it public is a one-time manual step in the organization's package settings.
- The runtime key keeps today's exposure: anyone who can load the page gets the key. Documented; deployments should stay on a trusted network or behind authentication.
- Release notes are only as good as commit subjects; Story 15.0 tunes the filters against real history, and the release guide states the convention.
- Publishing a release, image and attestations is outward-facing. End-to-end verification uses a release-candidate tag only with the maintainer's approval; `v0.1.0` is cut by the maintainer.

## 4. Detailed Change Proposals

### 4.1 PRD (`prd.md`) — approved

**Frontmatter:** `lastUpdated: '2026-11-10'`; update entry "Added FR152-FR166 and NFR17-NFR18 for Epic 15 (Release Engineering)".

**Growth Features (Post-MVP) and Phase 2 - Growth:**

OLD:
- SBOM generation and security scanning in CI *(Phase 2: "SBOM generation and security scanning")*

NEW:
- SBOM generation (Epic 15) and security scanning in CI *(Phase 2: "SBOM generation (Epic 15) and security scanning")*
- Versioned GitHub releases with changelogs and published images (Epic 15)

**Non-Functional Requirements, new subsection "Release & Supply Chain":**

- NFR17: Release automation uses least-privilege token permissions per job and actions pinned to commit SHAs
- NFR18: Published images carry OCI labels recording their version, source revision and repository

**Post-MVP Functional Requirements, new section:**

```markdown
### Epic 15: Release Engineering

#### Versioning

- FR152: The API, web UI and container image share one Semantic Versioning version, kept in the project files a release updates and hard-coded nowhere else
- FR153: The API reports its version in the OpenAPI document and the `/healthz` response
- FR154: The web UI shows the running version

#### Changelog

- FR155: The changelog is generated from conventional commit messages, listing features, fixes, performance improvements and breaking changes grouped by type; other commit types, merge commits and non-conventional messages are left out
- FR156: Changelog entries omit internal planning scopes (story, task and review identifiers)
- FR157: Developer can preview the changelog for unreleased changes without making a release

#### Cutting a Release

- FR158: Developer can cut a release with one command that uses the version computed from commits since the last release, or an explicit bump or version, then updates the version files and CHANGELOG.md, commits, tags and pushes
- FR159: The release command refuses to run unless on an up-to-date `main` with a clean working tree, and refuses a version that is already tagged or not newer than the last release
- FR160: The release command offers a dry run that shows the version and notes without changing anything

#### Publishing

- FR161: Pushing a version tag publishes a GitHub release whose notes are that version's changelog section
- FR162: Pushing a version tag publishes the image to GHCR as `X.Y.Z`, `X.Y` and `latest`; a pre-release version (e.g. `0.2.0-rc.1`) gets only its full tag and is marked as a pre-release on GitHub
- FR163: Publishing stops before anything is published if the tag does not match the repository's version
- FR164: Each published image has an SBOM and signed build provenance that users can verify; the SBOM is attached to the GitHub release

#### Runtime Configuration and Documentation

- FR165: The published image contains no API key; the web UI receives its API key from the server's configuration at runtime, so one image works for every deployment
- FR166: Documentation explains installing and upgrading to a specific release, verifying an image, writing commits that become release notes, and cutting a release
```

**Rationale:** The PRD lists automated releases and SBOMs as success criteria without requirements. FR165 is a prerequisite: a generic image would otherwise ship a UI that cannot authenticate.

### 4.2 Epics Structure (`epics.md`) — approved

**Frontmatter:** `lastUpdated: '2026-11-10'`; update entry "Added Epic 15 (7 stories) for Release Engineering".

**FR Coverage Map**, appended after FR151:

```markdown
| FR152 | Epic 15 | One version across API, web and image |
| FR153 | Epic 15 | API reports its version |
| FR154 | Epic 15 | Web UI shows the running version |
| FR155 | Epic 15 | Changelog from conventional commits |
| FR156 | Epic 15 | Planning scopes omitted from changelog |
| FR157 | Epic 15 | Preview unreleased changelog |
| FR158 | Epic 15 | One-command release |
| FR159 | Epic 15 | Release preconditions |
| FR160 | Epic 15 | Release dry run |
| FR161 | Epic 15 | GitHub release with notes on tag push |
| FR162 | Epic 15 | GHCR image tags, pre-release handling |
| FR163 | Epic 15 | Tag and version mismatch blocks publishing |
| FR164 | Epic 15 | SBOM and signed provenance |
| FR165 | Epic 15 | Runtime web API key, none in the image |
| FR166 | Epic 15 | Release and install documentation |
```

**Story Summary:**

OLD:
```markdown
| **Total** | | **78** |
```

NEW:
```markdown
| Epic 15: Release Engineering | 15.0, 15.1, 15.2, 15.3, 15.4, 15.5, 15.6 | 7 |
| **Total** | | **85** |
```

**Rationale:** Keeps coverage and the summary consistent with the PRD. The summary total was already inaccurate before Epic 14 (see the 2026-11-09 proposal); this change only adds to it.

### 4.3 Epic 15 Stories (appended to `epics.md`) — approved

````markdown
## Epic 15: Release Engineering

**Goal:** Maintainers cut a versioned release with one command, and users install a published, verifiable image whose changes are described in a changelog.

### Current State

- CI lints, tests and builds the image on pull requests and `main`, but never publishes it
- No tags, releases or changelog exist; the version is hard-coded in four places that disagree
- The web UI's API key is baked into the image at build time

### Target State

- One version, shown in the API and the UI, set by the release command
- `just changelog` previews and `just release` cuts a release; a tag push publishes the GitHub release, GHCR image tags, SBOM and provenance
- One published image works for every deployment, with no key inside it

---

### Story 15.0: Epic 15 Technical Preparation

As a **developer**,
I want **the release toolchain verified against this repository**,
So that **the release stories rest on confirmed behavior**.

**Acceptance Criteria:**

**Given** this repository's history
**When** git-cliff runs with a draft configuration
**Then** findings show generated notes for a recent range, and the filter and scope rules that make them readable

**Given** a 0.x version
**When** the next version is computed from commits
**Then** findings confirm that features bump the minor version, fixes the patch version, and breaking changes the minor version

**Given** the container image
**When** the API reads its version from package metadata
**Then** findings confirm it returns the version in `pyproject.toml`

**Given** GitHub Actions on this public organization repository
**When** publishing to GHCR with attestations is researched
**Then** findings document the required permissions, the tag rules for 0.x and pre-release versions, the SBOM and provenance approach, and the one-time package visibility step

**Tasks:**
- [ ] Draft `cliff.toml` and compare its output with recent history
- [ ] Confirm version bump rules for 0.x
- [ ] Verify reading the version from package metadata inside the image
- [ ] Research GHCR publishing, image tags and attestations
- [ ] Update architecture documentation with findings

---

### Story 15.1: Single Version Source and Version Display

As an **administrator**,
I want **to see which version of the manager I am running**,
So that **I can tell whether I am up to date and report problems accurately**.

**Acceptance Criteria:**

**Given** the version in `api/pyproject.toml`
**When** the API starts
**Then** the OpenAPI document and `/healthz` report that version
**And** no other API file hard-codes it

*(Covers FR152, FR153)*

**Given** the version in `web/package.json`
**When** the web UI is built
**Then** the sidebar footer shows that version instead of a hard-coded value

*(Covers FR154)*

**Given** both version files
**When** `just version` runs
**Then** it prints the version
**And** fails if the two files disagree

**Tasks:**
- [ ] Read the API version from package metadata; remove hard-coded versions
- [ ] Add `version` to the `/healthz` response
- [ ] Build the web version from `package.json` into the sidebar footer
- [ ] Set `web/package.json` to 0.1.0; add `just version`
- [ ] Tests

---

### Story 15.2: Runtime API Key for the Web UI

As an **administrator running the published image**,
I want **the web UI to get its API key from my container's configuration**,
So that **one image works for every deployment and no key is baked into it**.

**Acceptance Criteria:**

**Given** `VS_API_KEY` is set on the container
**When** the web UI loads
**Then** its requests use that key

**Given** `VS_API_KEY` is not set
**When** the web UI loads
**Then** it uses the Admin key, matching the existing compose default

**Given** an image built from the Dockerfile
**When** its build arguments, layers and web bundle are inspected
**Then** they contain no API key

*(Covers FR165)*

**Given** the web dev server with `VITE_API_KEY` in `web/.env`
**When** a developer runs `just dev-web`
**Then** the UI authenticates as before

**Tasks:**
- [ ] Serve runtime web configuration from the API, never cached
- [ ] Read the key from runtime configuration in the web client, falling back to `VITE_API_KEY`
- [ ] Remove the API key build argument from the Dockerfile and compose files
- [ ] Tests; browser verification in a container

---

### Story 15.3: Changelog Generation

As a **maintainer**,
I want **release notes generated from commit messages**,
So that **each release describes its changes without manual assembly**.

**Acceptance Criteria:**

**Given** conventional commits since the last release
**When** `just changelog` runs
**Then** it prints the unreleased notes grouped into breaking changes, features, fixes and performance improvements
**And** each entry links to its commit

*(Covers FR155, FR157)*

**Given** `docs`, `chore`, `test`, `ci`, `build`, `refactor`, `style` or review commits, merge commits, or non-conventional messages
**When** notes are generated
**Then** they are left out

*(Covers FR155)*

**Given** a commit scoped to a story, task or review (e.g. `feat(story-14.2/task-6): ...`)
**When** notes are generated
**Then** the entry shows the description without that scope

*(Covers FR156)*

**Tasks:**
- [ ] Pin git-cliff in `.mise.toml`; add `cliff.toml`
- [ ] Add `just changelog`
- [ ] Automated tests against a fixture history, run in CI

---

### Story 15.4: Release Command

As a **maintainer**,
I want **to cut a release with one command**,
So that **version, changelog, commit and tag are always consistent**.

**Acceptance Criteria:**

**Given** unreleased commits on `main`
**When** I run `just release`
**Then** the next version is computed from the commits
**And** `just release patch|minor|major` or `just release X.Y.Z[-pre]` overrides it

**Given** a version is chosen
**When** the release runs
**Then** it updates `api/pyproject.toml`, `api/uv.lock`, `web/package.json` and `CHANGELOG.md`
**And** commits them as `chore(release): vX.Y.Z` with an annotated tag `vX.Y.Z`
**And** asks for confirmation, then pushes the commit and tag together

*(Covers FR158)*

**Given** I am not on `main`, the working tree is dirty, `main` differs from its remote, the tag exists, or the version is not newer than the last release
**When** I run `just release`
**Then** it stops with a clear message and changes nothing

*(Covers FR159)*

**Given** `just release --dry-run`
**When** it runs
**Then** it shows the version and notes and changes nothing

*(Covers FR160)*

**Given** a step fails before the push
**When** the release stops
**Then** no release commit or tag is left behind

**Tasks:**
- [ ] `scripts/release.sh` and `just release`
- [ ] Version file updates, changelog, commit, tag, confirmed push
- [ ] Preconditions, dry run, cleanup on failure
- [ ] Automated tests with a temporary repository and remote, run in CI

---

### Story 15.5: Release Workflow

As a **user of the published image**,
I want **each release published with notes and verifiable provenance**,
So that **I can install a specific version and trust where it came from**.

**Acceptance Criteria:**

**Given** a pushed tag `vX.Y.Z`
**When** the release workflow runs
**Then** a GitHub release is published with that version's changelog section as notes

*(Covers FR161)*

**Given** a stable version
**When** the image is published
**Then** GHCR has tags `X.Y.Z`, `X.Y` and `latest`
**And** a pre-release version gets only its full tag and a GitHub pre-release

*(Covers FR162)*

**Given** a tag that does not match the repository's version
**When** the workflow runs
**Then** it fails before publishing anything

*(Covers FR163)*

**Given** a published image
**When** a user runs `gh attestation verify` against it
**Then** its signed build provenance verifies
**And** an SBOM is attested for the image and attached to the release

*(Covers FR164)*

**Given** the workflow
**When** it is reviewed
**Then** each job has least-privilege permissions, actions are pinned to commit SHAs, and the image carries OCI version, revision and source labels

*(Covers NFR17, NFR18)*

**Tasks:**
- [ ] `.github/workflows/release.yml`: verify, build and push, attest, release
- [ ] Image tags and labels; pre-release handling
- [ ] SBOM and provenance attestations; SBOM release asset
- [ ] End-to-end check with a release-candidate tag, pushed only with the maintainer's approval

---

### Story 15.6: Release Documentation and First Release

As a **new user**,
I want **installation instructions for a specific release**,
So that **I can deploy and upgrade predictably**.

**Acceptance Criteria:**

**Given** the README
**When** I follow the installation section
**Then** it installs a pinned release, explains upgrading, explains verifying the image, and states that anyone who can load the web UI receives its API key

**Given** the release guide
**When** a maintainer reads it
**Then** it explains which commits become release notes, `just changelog`, `just release`, what the workflow publishes, and the one-time package visibility step

*(Covers FR166)*

**Given** the rest of the README
**When** a reader compares it with the product
**Then** it describes delivered features rather than planned ones
**And** its tool versions and commands match `.mise.toml` and the Justfile

**Given** Stories 15.1-15.5 are merged
**When** the maintainer cuts `v0.1.0`
**Then** the GitHub release, image tags and attestations exist
**And** the image starts with `docker-compose.yaml` and the UI works

**Tasks:**
- [ ] README installation, upgrade and verification sections
- [ ] README accuracy pass: delivered features, tool versions, commands
- [ ] Release guide; `CLAUDE.md` and `AGENTS.md` commands
- [ ] `docker-compose.yaml` comment on pinning a version
- [ ] Seed `CHANGELOG.md` with a summary for `v0.1.0`
- [ ] First release, cut by the maintainer
````

**Rationale:** Story 15.0 front-loads the unknowns (changelog quality, bump rules, metadata inside the image, GHCR attestations), as in Epics 13 and 14. Stories 15.1 and 15.2 make the image releasable; 15.3-15.5 build the tooling bottom-up; 15.6 documents it and ships `v0.1.0`. `v0.1.0` gets a written summary instead of about 420 generated entries covering the project's whole history; generated notes start with the next release.

### 4.4 Architecture — approved

**New file `architecture/epic-15-release-engineering.md`** with five ADRs:

| ADR | Decision |
|---|---|
| ADR-1: One Version, Kept in the Project Files | `api/pyproject.toml` is the version; `web/package.json` and `uv.lock` match it; the API reads package metadata, the web build injects `__APP_VERSION__`; `just version` checks agreement |
| ADR-2: Changelog from Conventional Commits with git-cliff | Breaking/Features/Fixes/Performance groups; other types, merges and non-conventional commits dropped; only allowlisted component scopes shown; 0.x bump rules; `CHANGELOG.md` with a hand-written `v0.1.0`; release notes are the tag's section of `CHANGELOG.md` |
| ADR-3: Release Command | `scripts/release.sh` behind `just release`: preconditions, version choice, dry run, file updates, commit and annotated tag, confirmed atomic push; reset on failure or decline; no `just check` |
| ADR-4: Tag-Triggered Release Workflow | `release.yml` on `v*` tags: verify → image (metadata-action tags, amd64, provenance and SBOM attestations) → GitHub release last; least-privilege per job; one-time package visibility step |
| ADR-5: Runtime Web Configuration | Unauthenticated, uncached `GET /config.js` sets `window.__VSM_CONFIG__.apiKey` from `VS_API_KEY`, else `VS_API_KEY_ADMIN`; client falls back to `VITE_API_KEY`; placeholder in `web/public/`; build argument removed |

**`architecture/index.md`:** add an "Epic 15: Release Engineering Architecture" entry listing ADR-1 to ADR-5.

**`architecture/project-structure-boundaries.md`**, CI/CD Pipeline sketch:

OLD:
```yaml
# 3. Build Docker image
# 4. Push to ghcr.io/craquehouse/vintagestory-server
```

NEW:
```yaml
# 3. Build Docker image (not pushed)
# Publishing: .github/workflows/release.yml on version tags (Epic 15 ADR-4)
```

**Rationale:** Records how releases, versions and runtime configuration work so the stories share one design; supersedes the never-implemented push step.

### 4.5 Other Artifacts — approved

| Artifact | Change | When |
|---|---|---|
| `sprint-status.yaml` | Add `epic-15` (backlog), stories `15-0` to `15-6` (backlog) and `epic-15-retrospective` (optional), via `just sprint` | Now |
| Beads | `VSS-3es` "[CICD-005] Add release action" is delivered by Epic 15; close it with an AAR when Story 15.5 is done | Story 15.5 |
| `RELEASING.md` (new, repository root) | Release guide: commit conventions that become notes, `just changelog`, `just release`, what the workflow publishes, the one-time package visibility step, recovering from a failed release | Story 15.6 |
| `README.md` | Installation from a pinned release, upgrading, verifying the image, key exposure note; link to `RELEASING.md` | Story 15.6 |
| `CLAUDE.md` | Commands: `just version`, `just changelog`, `just release`; Git Workflow: `feat`/`fix`/`perf` subjects become release notes, so write them for users | Story 15.6 |
| `AGENTS.md` | Same commit-message note for other agents | Story 15.6 |
| `.mise.toml` | Pin git-cliff | Story 15.3 |
| `Dockerfile`, `docker-compose.dev.yaml` | Remove the API key build argument | Story 15.2 |
| `docker-compose.yaml` | Comment on pinning a version tag instead of `latest` | Story 15.6 |
| `.github/workflows/ci.yml` | Run the release script tests | Stories 15.3, 15.4 |

**Found during review, and the maintainer's decisions:**

- `README.md` is stale beyond installation: "Features (Planned)" lists delivered features, it says Python 3.13 (the project uses 3.14), and it names `just docker-start` and `just test-e2e`, which are `just docker start` and `just test-e2e-api`/`just test-e2e-web`. **Decision:** add a README accuracy pass to Story 15.6 (done in 4.3).
- Beads `VSS-3dm` (Renovate), `VSS-dde` (tests in pipeline) and `VSS-h7p` (linting in pipeline) were already delivered: `renovate.json` exists and `ci.yml` runs lint, typecheck and tests. **Decision:** closed with AARs on 2026-11-10.
- Beads `VSS-4ac` and `VSS-djg` (semgrep) remain open; security scanning was not selected for this epic.

## 5. Implementation Handoff

**Scope:** Moderate. A new epic in the backlog; no replanning of existing work.

| Role | Responsibility |
|---|---|
| Scrum Master (`create-story`) | Create story files 15.0 to 15.6 in order from `epics.md` and the Epic 15 ADRs |
| Developer (`dev-story`) | Implement each story; Story 15.0 updates the ADRs before 15.1 starts |
| Reviewer (`code-review`) | Delegated read-only review per story (Z.ai coding-plan model) |
| Maintainer (Matt) | Approves pushing any release-candidate tag (15.5); makes the GHCR package public; cuts `v0.1.0` (15.6) |

**Success criteria:**

- `just release --dry-run` shows the next version and readable notes; `just release` produces one commit and one tag with consistent version files
- A pushed tag publishes the GitHub release with notes, GHCR tags `X.Y.Z`, `X.Y` and `latest`, an SBOM, and provenance that `gh attestation verify` accepts
- The published `v0.1.0` image runs from `docker-compose.yaml`, its UI authenticates with a runtime key, and the sidebar shows `v0.1.0`
- `just check` and CI pass throughout
