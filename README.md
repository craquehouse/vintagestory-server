# VintageStory Server Manager

A Docker image that runs a VintageStory dedicated server together with a web UI and API for managing it: start and stop the server, watch the console, install and update mods, and edit configuration without a shell.

## Artificial Intelligence Disclaimer

This project is developed with the assistance of AI coding tools (such as Claude Code, opencode, cursor, or similar). All AI-generated code is reviewed and tested before inclusion. While we strive for quality and correctness, users should evaluate the code independently for their specific use cases.

## Features

- **Server lifecycle:** install any stable or unstable VintageStory version, start, stop and restart the server, and see its status, uptime and pending restarts
- **Console:** live console streaming with history and command input
- **Mods:** browse and search the mod database, install with compatibility checks, enable, disable and remove mods, see available updates, update one or all mods, and switch any mod to another release
- **Update alerts:** scheduled update checks with a count in the navigation and Dashboard, and optional webhook alerts (Discord or any HTTP receiver)
- **Configuration:** edit the game's JSON configuration files and server settings, and manage server files
- **Dashboard:** server status, player and resource metrics, disk space warnings
- **Scheduled jobs:** background tasks such as mod cache refreshes, with their status in the UI
- **API:** a versioned REST API (`/api/v1alpha1`) with Admin and Monitor (read-only) keys, health endpoints (`/healthz`, `/readyz`) and an OpenAPI document

## Installation

Releases are published as `ghcr.io/craquehouse/vintagestory-server`, tagged with their version (`0.1.0`), their minor version (`0.1`) and `latest`. The image is built for `linux/amd64`. Pin a full version so upgrades happen only when you choose; release notes are on the [GitHub releases page](https://github.com/craquehouse/vintagestory-server/releases) and in [`CHANGELOG.md`](CHANGELOG.md).

1. Download [`docker-compose.yaml`](docker-compose.yaml) and [`.env.example`](.env.example) into an empty directory, and rename `.env.example` to `.env`.
2. In `.env`, set `VS_API_KEY_ADMIN` to a long random value (`openssl rand -hex 32`). Optionally set `VS_API_KEY_MONITOR` for read-only access. Also set `VS_API_KEY` to the key the web UI should use (see [Security](#security)), or the web UI shows a set-up message instead of the app.
3. In `docker-compose.yaml`, replace `:latest` with the version you want, for example `ghcr.io/craquehouse/vintagestory-server:0.1.0`.
4. Start it:

   ```bash
   docker compose up -d
   ```

5. Open `http://<host>:8080`, go to **Game Server → Installation** and install a VintageStory version (the item is called **Version** once a server is installed). Game data, mods and manager state live in `./data`. Mod archives (`.zip`, or `.zip.disabled` for a disabled mod) copied into or deleted from `data/serverdata/Mods` by hand are picked up the next time the manager container starts (a file replaced by hand under the same name keeps the listed version until it is reinstalled or removed and added again).

### Security

The web UI receives its API key from the server at runtime (`/config.js`): the value of `VS_API_KEY`. There is no fallback: with `VS_API_KEY` unset, the page shows what to set instead of the app. **Anyone who can load the web UI receives that key.** Set it to the Monitor key for a read-only web UI (recommended). Setting it to the Admin key means everyone who can load the page has full access, including the game server password, and the API logs a warning at every start. Keep port 8080 on a trusted network or put it behind a reverse proxy with authentication, and terminate TLS there; that is the way to use the Admin key in the page safely. The image itself contains no key.

**Content-Security-Policy.** The web UI's pages are sent with a Content-Security-Policy, so a script injected into a page does not run, and the pages cannot be shown in a frame. `VS_CSP_MODE=report-only` sends the policy as a report only (the browser logs what it would block) and `off` sends none; both also allow framing again. Use them only when a reverse proxy injects its own scripts or styles into the page, or a dashboard frames the web UI. `VS_DEBUG=true` serves the API documentation at `/docs`, so leave it off outside development.

**Mod database address.** `VS_MOD_DB_URL` replaces `https://mods.vintagestory.at` as the address the manager asks for mod listings and downloads mod files from. It is for a mirror of the same database, or for tests. The game server runs the mod files that come from that address, so point it only at a server you trust. An address other than the default is logged at every start as `mod_db_url_overridden`. It must serve the same database, because the download cache and the records of installed mods are kept by the database's IDs. Mod images still load only from `moddbcdn.vintagestory.at`, and links to mod pages still go to `mods.vintagestory.at`.

**What a Monitor key can read.** In the file manager, a Monitor key sees the configuration files in the root of the server data directory and under `ModConfig` only; saves, backups, logs and player data are for the Admin key. Values under key names that look like secrets (password, token, secret, API key, webhook and similar), `StartupCommands`, URLs that contain a user name or password, and Discord webhook URLs are shown as `[redacted]`, and a file that is not valid JSON is not shown at all. A secret stored under another key name (for example `Key1`) is not recognised, so give Monitor keys only to people you would show your mod configuration to.

### Upgrading

1. Read the release notes for every version between yours and the new one.
2. Change the image tag in `docker-compose.yaml`.
3. Pull and restart:

   ```bash
   docker compose pull
   docker compose up -d
   ```

Your data in `./data` is kept. The running version is shown in the sidebar and reported by `/healthz` (`data.version`).

### Verifying an image

Each release image has signed build provenance and an SBOM attestation, created by the release workflow. With the [GitHub CLI](https://cli.github.com):

```bash
# Build provenance: built by this repository's release workflow
gh attestation verify oci://ghcr.io/craquehouse/vintagestory-server:0.1.0 --owner craquehouse

# SBOM attestation (SPDX)
gh attestation verify oci://ghcr.io/craquehouse/vintagestory-server:0.1.0 --owner craquehouse \
  --predicate-type https://spdx.dev/Document/v2.3
```

The SBOM file is also attached to each GitHub release (`sbom.spdx.json`).

### Configuration

Set these in `.env` (see [`.env.example`](.env.example) for all of them). The game version is chosen in the UI, under **Game Server → Installation**.

| Variable | Required | Description |
|---|---|---|
| `VS_API_KEY_ADMIN` | Yes | Admin API key (full access) |
| `VS_API_KEY_MONITOR` | No | Read-only API key |
| `VS_API_KEY` | For the web UI | Key the web UI uses. Unset: the web UI shows a set-up message. Set it to the Monitor key (read-only) or the Admin key (full access); any other value logs a warning at start-up and the UI cannot sign in |
| `VS_DEBUG` | No | Verbose, human-readable logs; also serves the API documentation at `/docs` and the RBAC test routes, so it is for development (`false`) |
| `VS_LOG_LEVEL` | No | Level of the API's log lines: `DEBUG`, `INFO`, `WARNING` or `ERROR`, any letter case. Unset: `DEBUG` with `VS_DEBUG=true`, `INFO` otherwise. It changes only the level, nothing else that `VS_DEBUG` does. Turning debug logging on in the web UI gives `DEBUG`; turning it off returns to this level. uvicorn's own lines are not affected. Any other value stops start-up |
| `VS_CSP_MODE` | No | How the web UI's Content-Security-Policy is sent: `enforce`, `report-only` or `off` (`enforce`). Any other value stops start-up |
| `VS_MOD_DB_URL` | No | Base address of the mod database (`https://mods.vintagestory.at`). Set it only to use a mirror of the same database; mods are downloaded from this address. Must be an `https` URL with a host and nothing else; `http` is accepted only with `VS_DEBUG=true`. Any other value stops start-up |
| `VS_CORS_ORIGINS` | No | Allowed browser origins for a separately hosted UI |
| `VS_DATA_DIR` | No | Data directory inside the container (`/data`); change it only with a matching volume mount |
| `VS_CONSOLE_HISTORY_LINES` | No | Console lines sent when the console connects (`100`) |
| `VS_DISK_SPACE_WARNING_THRESHOLD_GB` | No | Free space below which the health check warns (`1.0`; `0` turns the fixed threshold off). Negative values stop start-up |
| `VS_MOD_CACHE_MAX_SIZE_MB` | No | Size of the downloaded-mods cache before old files are evicted (`500`; `0` turns eviction off) |

## Development

### Prerequisites

- [mise](https://mise.jdx.dev/) for tool versions, and Docker for the image and end-to-end tests

### Install development tools

```bash
mise trust && mise install
just install
```

`mise install` installs the versions pinned in [`.mise.toml`](.mise.toml): Python 3.14, uv, Bun, just, yq, git-cliff, actionlint and ShellCheck.

`git blame` can skip formatting-only commits, listed in [`.git-blame-ignore-revs`](.git-blame-ignore-revs). GitHub's blame view does this by itself. Locally it needs the git setting `blame.ignoreRevsFile`, which `scripts/worktree-setup.sh` sets; in another clone run `git config blame.ignoreRevsFile ':(optional).git-blame-ignore-revs'` once (the `:(optional)` prefix keeps `git blame` working on branches without the file; on an older Git leave it out).

### Development commands

Run `just` to list every recipe. Common ones:

```bash
just check          # Full validation: lint + typecheck + test
just test           # API, web and script tests
just test-api       # API tests (pytest); accepts pytest arguments
just test-web       # Web tests (Vitest)
just format         # Format the API (ruff) and the web (Prettier); just check checks both
just dev-api        # API dev server
just dev-web        # Web dev server (reads web/.env, see web/.env.example)
just docker start   # Build and start the development stack (docker-compose.dev.yaml)
just docker stop    # Stop it
just semgrep        # Static security scan (needs the network; not part of just check)
```

CI runs the same scan on every pull request and fails only on findings the pull request adds; `main`'s findings are under Security > Code scanning.

### End-to-end tests

```bash
just install-e2e-browsers   # once: the Chromium builds Playwright uses
just test-e2e-ci    # The CI set: untagged tests, then the mod database tests on recorded answers
just test-e2e-api   # API E2E tests (pytest); needs the stack running (just docker start)
just test-e2e-web   # Every web E2E test (Playwright); starts and stops the stack itself
```

The CI set includes the mod database tests, on recorded answers replayed to a second throwaway container. What each test tag means, and what the CI set needs, is in [`web/e2e/README.md`](web/e2e/README.md).

### Releases

Commit messages become release notes, and releases are cut with `just release`. See [`RELEASING.md`](RELEASING.md).

## License

MIT, see [`LICENSE`](LICENSE).
