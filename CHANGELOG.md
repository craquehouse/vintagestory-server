# Changelog

All notable changes to this project are listed here. Versions follow [Semantic Versioning](https://semver.org).
<!-- git-cliff: end of header -->

## [0.1.0] - 2026-11-10

The first release of VintageStory Server Manager: a Docker image that runs a VintageStory dedicated server with a web UI and API to manage it.

### Features

- Install any stable or unstable VintageStory server version from the UI, and start, stop and restart it
- Live console with history and command input
- Browse and search the mod database; install mods with compatibility checks; enable, disable and remove them
- Mod updates: see available updates, update one mod or all compatible mods, switch a mod to any listed release, scheduled update checks with a count in the navigation and Dashboard, and optional webhook alerts (Discord or any HTTP receiver)
- Edit the game's configuration files and server settings, and manage server files
- Dashboard with server status, CPU, memory and player metrics, and disk space warnings
- Scheduled background jobs with their status in the UI
- Versioned REST API with Admin and Monitor (read-only) keys, health endpoints and an OpenAPI document
- Versioned releases: the version is shown in the sidebar and `/healthz`; images are published to `ghcr.io/craquehouse/vintagestory-server` with signed build provenance and an SBOM
- The web UI receives its API key from the server at runtime, so one image works for every deployment and contains no key
