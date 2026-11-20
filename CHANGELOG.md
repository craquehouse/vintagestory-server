# Changelog

All notable changes to this project are listed here. Versions follow [Semantic Versioning](https://semver.org).
<!-- git-cliff: end of header -->

## [0.1.0] - 2026-11-20

The first release of VintageStory Server Manager: a Docker image that runs a VintageStory dedicated server with a web UI and API to manage it.

### Features

- Install any stable or unstable VintageStory server version from the UI, and start, stop and restart it
- Live console with history and command input
- Browse and search the mod database; install mods with compatibility checks; enable, disable and remove them
- Filter the installed mods by name or mod ID, compatibility and available update; the filters are kept in the page address, so a filtered view can be bookmarked or shared
- Mods copied into the mods folder by hand appear after a Rescan, without a restart, and get their mod database link and update status; a mod the database does not know is shown as a local mod
- Find leftover files in the mods folder (interrupted downloads, backups, skipped archives and duplicate copies of a mod) and delete them from the Installed tab
- Mod descriptions show a note where a video or audio clip cannot be played
- Mod updates: see available updates, update one mod or all compatible mods, switch a mod to any listed release, scheduled update checks with a count in the navigation and Dashboard, and optional webhook alerts (Discord or any HTTP receiver)
- Edit the game's configuration files and server settings, and manage server files
- Dashboard with server status, CPU, memory and player metrics, and disk space warnings
- Scheduled background jobs with their status in the UI
- Versioned REST API with Admin and Monitor (read-only) keys, health endpoints and an OpenAPI document
- Versioned releases: the version is shown in the sidebar and `/healthz`; images are published to `ghcr.io/craquehouse/vintagestory-server` with signed build provenance and an SBOM
- The web UI receives its API key from the server at runtime, so one image works for every deployment and contains no key
- A Vintage Story icon in the browser tab
