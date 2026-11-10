# Epic 15: Release Engineering Architecture

_Added during the Epic 15 course correction (2026-11-10). Story 15.0 verifies the assumptions marked below._

## ADR-1: One Version, Kept in the Project Files

**Decision:** The `[project].version` in `api/pyproject.toml` is the product version. `web/package.json` holds the same value, and `api/uv.lock` records it. Only the release command (ADR-3) changes them.

- API: `__version__` comes from `importlib.metadata.version("vintagestory-api")`; `FastAPI(version=__version__)`; `/healthz` adds `data.version`.
- Web: Vite `define` injects `__APP_VERSION__` from `package.json`; the sidebar footer shows it.
- `just version` prints the version and fails if the two files disagree. The release workflow checks the tag against it (ADR-4).

**Rationale:** The version is hard-coded in four places that already disagree. The API and web ship in one image, so one version describes both.

**Consequences:** Between releases, `main` carries the last released version. Only tags publish images, so no published image is mislabeled; local builds show the last release. **Verify (15.0):** `uv sync --frozen --no-dev` runs before `src/` is copied in the Dockerfile, so package metadata must still resolve inside the image.

## ADR-2: Changelog from Conventional Commits with git-cliff

**Decision:** git-cliff, pinned in `.mise.toml`, configured by `cliff.toml` at the repository root, generates `CHANGELOG.md` and release notes.

- Only conventional commits are used; non-conventional messages and merge commits are dropped.
- Groups, in order: Breaking Changes (any type marked with `!` or a `BREAKING CHANGE` footer), Features (`feat`), Fixes (`fix`), Performance (`perf`). All other types, including `chore(release)` commits, are skipped.
- Scopes are not shown, except an allowlist of component scopes that Story 15.0 settles from history (for example `api`, `web`). Story, task, review and `ad-hoc` scopes never appear.
- Each entry links to its commit on GitHub. Bead IDs in subjects are kept.
- Version bumps while on 0.x: features and breaking changes bump the minor version, fixes and performance changes bump the patch version. Revisit at 1.0.

**Changelog file:** `CHANGELOG.md` at the root, newest first. The `v0.1.0` section is a written summary of the product (Story 15.6); each later release prepends its generated section. The GitHub release notes for a tag are that version's section of `CHANGELOG.md` at the tag, so they always match what was committed, including the hand-written `v0.1.0`.

**Rationale:** About 95% of commits are already conventional, so no workflow change is needed beyond writing `feat`/`fix` subjects for users. git-cliff is a single binary with first-class filtering, scope rewriting and version bumping.

**Verify (15.0):** filters and scope handling against recent history; bump behavior for 0.x.

## ADR-3: Release Command

**Decision:** `just release *ARGS` runs `scripts/release.sh` (bash, like `scripts/sprint-status.sh`). `just changelog` prints unreleased notes (`git cliff --unreleased`).

**Sequence:**
1. Check preconditions: on `main`, clean working tree, `git fetch` shows `HEAD` equal to `origin/main`, required tools present.
2. Choose the version: no argument uses `git cliff --bumped-version`; `patch`, `minor` or `major` bumps the last tag; `X.Y.Z[-pre]` is used as given. It must be valid SemVer, newer than the last tag and not already tagged. With no argument and nothing to release, stop.
3. Show the version and notes. `--dry-run` stops here.
4. Update `api/pyproject.toml` and `api/uv.lock`, `web/package.json`, and prepend the section to `CHANGELOG.md`. Run `just version` to confirm the files agree.
5. Commit `chore(release): vX.Y.Z` and create the annotated tag `vX.Y.Z`.
6. Ask for confirmation, then `git push --atomic origin main vX.Y.Z`.

A failure or a declined confirmation before step 6 completes resets `main` to the starting commit and deletes the tag. The tree was clean at step 1, so nothing else is lost.

**Rationale:** The command does not run `just check`: the release commit differs from the commit CI tested only in version files and the changelog, and the release workflow builds the image from the tag.

**Verify (15.0):** the commands that set the version in `pyproject.toml` with `uv.lock`, and in `package.json`.

## ADR-4: Tag-Triggered Release Workflow

**Decision:** `.github/workflows/release.yml` runs on pushed tags `v*`, one run per tag, never cancelled. Its jobs:

1. **verify** (`contents: read`): the tag is SemVer and equals the version from `just version`; `CHANGELOG.md` has a section for it. Saves that section as the notes.
2. **image** (`contents: read`, `packages: write`, `id-token: write`, `attestations: write`): log in to GHCR with `GITHUB_TOKEN`; `docker/metadata-action` produces tags `{{version}}`, `{{major}}.{{minor}}` and `latest` (pre-releases get only `{{version}}`) and the OCI labels; `docker/build-push-action` builds `linux/amd64` and pushes; `actions/attest-build-provenance` attests the pushed digest; an SPDX SBOM is generated for the digest and attested with `actions/attest-sbom`.
3. **release** (`contents: write`): `gh release create vX.Y.Z --verify-tag --notes-file`, with `--prerelease` for pre-release versions, and the SBOM attached.

The GitHub release is created last, so a failed build publishes no release. Actions are pinned to commit SHAs and kept current by Renovate, as in CI. `ci.yml` is unchanged: pull requests and `main` still build without pushing.

**Consequences:** The first push creates the GHCR package. Making it public is a one-time manual step in the organization's package settings; the `org.opencontainers.image.source` label links it to the repository. Users verify with `gh attestation verify oci://ghcr.io/craquehouse/vintagestory-server:X.Y.Z --owner craquehouse`.

**Verify (15.0):** permissions, metadata-action tag rules for 0.x and pre-releases, and the SBOM and attestation actions.

## ADR-5: Runtime Web Configuration

**Decision:** The API serves `GET /config.js`, unauthenticated, as `application/javascript` with `Cache-Control: no-store`:

```js
window.__VSM_CONFIG__ = {"apiKey": "..."};
```

- `index.html` loads it with a classic `<script src="/config.js">` before the module bundle. The route is registered with the frontend, ahead of the SPA fallback.
- The key comes from `VS_API_KEY`; if that is unset, from `VS_API_KEY_ADMIN`. This matches the existing compose default. Setting it to the Monitor key gives a read-only UI.
- The web client uses `window.__VSM_CONFIG__?.apiKey`, then `import.meta.env.VITE_API_KEY`, then an empty string. A placeholder `web/public/config.js` defines an empty config for the Vite dev server and tests; in the image, the API route takes precedence over it.
- The Dockerfile drops `ARG VS_API_KEY` and `VITE_API_KEY`; `docker-compose.dev.yaml` drops the build argument.

**Rationale:** One published image must work for every deployment. Chosen over a login screen as the smaller change.

**Consequences:** Exposure is unchanged from today: anyone who can load the page receives the key. The README states this; deployments should stay on a trusted network or behind authentication. The image itself no longer contains a key. The key is never logged.
