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
2. In `.env`, set `VS_API_KEY_ADMIN` to a long random value (`openssl rand -hex 32`). Optionally set `VS_API_KEY_MONITOR` for read-only access.
3. In `docker-compose.yaml`, replace `:latest` with the version you want, for example `ghcr.io/craquehouse/vintagestory-server:0.1.0`.
4. Start it:

   ```bash
   docker compose up -d
   ```

5. Open `http://<host>:8080`, go to **Game Server → Installation** and install a VintageStory version (the item is called **Version** once a server is installed). Game data, mods and manager state live in `./data`.

### Security

The web UI receives its API key from the server at runtime (`/config.js`): `VS_API_KEY` if set, otherwise the Admin key. **Anyone who can load the web UI receives that key.** Keep port 8080 on a trusted network or put it behind a reverse proxy with authentication, and terminate TLS there. Setting `VS_API_KEY` to the Monitor key gives a read-only web UI. The image itself contains no key.

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
| `VS_API_KEY` | No | Key the web UI uses (default: the Admin key). Set it to the Admin or Monitor key; any other value logs a warning at start-up and the UI cannot sign in |
| `VS_DEBUG` | No | Verbose, human-readable logs (`false`) |
| `VS_CORS_ORIGINS` | No | Allowed browser origins for a separately hosted UI |

## Development

### Prerequisites

- [mise](https://mise.jdx.dev/) for tool versions, and Docker for the image and end-to-end tests

### Install development tools

```bash
mise trust && mise install
just install
```

`mise install` installs the versions pinned in [`.mise.toml`](.mise.toml): Python 3.14, uv, Bun, just, yq, git-cliff, actionlint and ShellCheck.

### Development commands

Run `just` to list every recipe. Common ones:

```bash
just check          # Full validation: lint + typecheck + test
just test           # API, web and script tests
just test-api       # API tests (pytest); accepts pytest arguments
just test-web       # Web tests (Vitest)
just dev-api        # API dev server
just dev-web        # Web dev server (reads web/.env, see web/.env.example)
just docker start   # Build and start the development stack (docker-compose.dev.yaml)
just docker stop    # Stop it
```

### End-to-end tests

```bash
mise exec -C api -- uv run playwright install chromium   # once
just test-e2e-api   # API E2E tests (pytest); needs the stack running (just docker start)
just test-e2e-web   # Web E2E tests (Playwright); starts and stops the stack itself
```

### Releases

Commit messages become release notes, and releases are cut with `just release`. See [`RELEASING.md`](RELEASING.md).

## License

MIT
