---
name: polish-backlog
description: Manage polish-backlog.md using helper scripts or just commands. Use when adding backlog items, updating item status, marking items done, listing items by category/status, or editing the polish backlog file.
allowed-tools: Bash(./scripts/polish-backlog.sh:*), Bash(just polish:*)
---

# Managing the Polish Backlog

## IMPORTANT: Never Edit Directly

**DO NOT use the Edit or Write tools to modify polish-backlog.md.** This file has markdown table formatting that is easily broken by direct text editing. Always use the helper scripts or just commands.

## Quick Reference: Using `just polish`

The simplest way to manage the polish backlog is via the `just polish` command:

```bash
# List all items
just polish list

# List items filtered by category and/or status
just polish list API
just polish list UI backlog
just polish list TOOLS in-progress

# Get details of a specific item
just polish get UI-029

# Add a new item (auto-generates ID)
just polish add UI "Add dark mode toggle" medium S
just polish add API "Add rate limiting" high M "Epic-11" "Consider redis"

# Update item status
just polish set UI-029 in-progress
just polish set API-031 done

# Mark done and archive (with optional PR link)
just polish done UI-029
just polish done UI-029 https://github.com/org/repo/pull/99

# See what the next ID would be
just polish next-id API
```

## Alternative: Direct Script

The `scripts/polish-backlog.sh` script provides the same functionality:

```bash
./scripts/polish-backlog.sh list
./scripts/polish-backlog.sh get UI-029
./scripts/polish-backlog.sh add UI "Description" medium S
./scripts/polish-backlog.sh set UI-029 in-progress
./scripts/polish-backlog.sh done UI-029 https://github.com/org/repo/pull/99
```

## Valid Values

### Categories
- `UI` - Frontend/web UI items
- `API` - Backend API items
- `INFRA` - Infrastructure/Docker/deployment
- `TOOLS` - Development tooling/scripts
- `CICD` - CI/CD pipeline items

### Statuses
- `backlog` - Identified but not started
- `in-progress` - Currently being worked on
- `done` - Completed

### Priorities
- `high` - Impacts usability or correctness; address soon
- `medium` - Noticeable improvement; address when convenient
- `low` - Nice-to-have; address opportunistically

### Efforts
- `S` - Small (less than 1 hour)
- `M` - Medium (1-4 hours)
- `L` - Large (4+ hours)

## File Location

The polish backlog file is at:
```
_bmad-output/implementation-artifacts/polish-backlog.md
```

## Common Workflows

### Discovering an Issue During Development

When you encounter a minor issue while working on a story:

```bash
# Add it to the backlog instead of fixing immediately
just polish add UI "Button alignment off on mobile" low S "Story-10.2"
```

### Starting Work on a Polish Item

```bash
# Mark as in-progress
just polish set UI-029 in-progress
```

### Completing a Polish Item

```bash
# If you have a PR, include the URL for the archive
just polish done UI-029 https://github.com/craquehouse/vintagestory-server/pull/50

# If no PR (small fix committed directly)
just polish done UI-029
```

### Reviewing What's Available

```bash
# See all high priority items
just polish list | grep high

# See all API items in backlog
just polish list API backlog

# See what's currently in progress
just polish list "" in-progress
```

## Add Command Details

The `add` command takes these arguments in order:

```bash
just polish add <category> <description> <priority> <effort> [related] [notes]
```

- **category** (required): UI, API, INFRA, TOOLS, or CICD
- **description** (required): Clear description of the improvement
- **priority** (required): high, medium, or low
- **effort** (required): S, M, or L
- **related** (optional): Related epic/story reference (e.g., "Epic-5.1") or "-"
- **notes** (optional): Additional context or "-"

Examples:

```bash
# Minimal (defaults related/notes to "-")
just polish add API "Add pagination to mods endpoint" medium M

# With related story
just polish add UI "Fix tooltip positioning" low S "Story-10.2"

# With notes
just polish add INFRA "Add health check retries" medium S "-" "Docker restart policy"

# Full example
just polish add API "Rate limiting for auth endpoints" high M "Epic-2" "Consider redis-based limiting"
```
