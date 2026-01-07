---
name: sprint-status-yaml
description: Edit sprint-status.yaml using helper scripts or yq commands. Use when updating story status, marking tasks done, changing epic status, modifying sprint tracking, or editing the sprint status file.
allowed-tools: Bash(./scripts/sprint-status.sh:*), Bash(yq:*), Bash(just sprint:*)
---

# Editing sprint-status.yaml

## IMPORTANT: Never Edit Directly

**DO NOT use the Edit or Write tools to modify sprint-status.yaml.** This file has specific YAML formatting requirements that are easily broken by direct text editing. Always use the helper scripts or yq commands.

## Quick Reference: Using `just sprint`

The simplest way to manage sprint status is via the `just sprint` command:

```bash
# Get status
just sprint get 10-1-mod-browse-api

# Set status
just sprint set 10-1-mod-browse-api review

# List by status
just sprint list in-progress

# Add new story
just sprint add-story 10 10-9-new-feature
```

## Alternative: Direct Script

The `scripts/sprint-status.sh` script provides the same functionality:

```bash
# Get current status of a story or epic
./scripts/sprint-status.sh get 10-1-mod-browse-api

# Set status of a story
./scripts/sprint-status.sh set 10-1-mod-browse-api review
./scripts/sprint-status.sh set 10-1-mod-browse-api done

# Set status of an epic
./scripts/sprint-status.sh set epic-10 in-progress
./scripts/sprint-status.sh set epic-10 done

# List all entries with a specific status
./scripts/sprint-status.sh list in-progress
./scripts/sprint-status.sh list backlog

# Add a new story to an epic
./scripts/sprint-status.sh add-story 10 10-9-new-feature

# Add a new epic
./scripts/sprint-status.sh add-epic 11

# Manage retrospective action items
./scripts/sprint-status.sh retro-set A1-example done
./scripts/sprint-status.sh retro-add A5-new-action-item
```

## Valid Status Values

### Story Status (workflow order)
1. `backlog` - Story only exists in epic file
2. `ready-for-dev` - Story file created in stories folder
3. `in-progress` - Developer actively working
4. `review` - Ready for code review
5. `done` - Story completed

### Epic Status
- `backlog` - Epic not yet started
- `in-progress` - At least one story being worked
- `done` - All stories completed

### Retrospective Status
- `optional` - Can be completed but not required
- `done` - Retrospective completed

### Retro Action Item Status
- `pending` - Not yet addressed
- `done` - Completed

## File Location

The sprint status file is at:
```
_bmad-output/implementation-artifacts/sprint-status.yaml
```

## Common Workflows

### Starting Work on a Story

```bash
# Mark story as in-progress
./scripts/sprint-status.sh set 10-2-mods-tab-restructure in-progress
```

### Completing Implementation (Before Code Review)

```bash
# Mark ready for review (NOT done - code review happens first)
./scripts/sprint-status.sh set 10-2-mods-tab-restructure review
```

### After Successful Code Review

```bash
# Only after code review passes, mark as done
./scripts/sprint-status.sh set 10-2-mods-tab-restructure done
```

### Completing an Epic

```bash
# After all stories are done
./scripts/sprint-status.sh set epic-10 done
./scripts/sprint-status.sh set epic-10-retrospective done
```

## Direct yq Commands (Advanced)

If you need operations not covered by the helper script:

```bash
# Read the full development_status section
yq '.development_status' _bmad-output/implementation-artifacts/sprint-status.yaml

# Read a specific value
yq '.development_status."10-1-mod-browse-api"' _bmad-output/implementation-artifacts/sprint-status.yaml

# Update a value (in-place)
yq -i '.development_status."10-1-mod-browse-api" = "done"' _bmad-output/implementation-artifacts/sprint-status.yaml

# Add a comment before a key (advanced)
yq -i '.development_status."new-story" = "backlog" | .development_status."new-story" line_comment="Added by automation"' _bmad-output/implementation-artifacts/sprint-status.yaml

# Count items by status
yq '.development_status | to_entries | map(select(.value == "done")) | length' _bmad-output/implementation-artifacts/sprint-status.yaml
```

## Validation

After any modification, verify the file is still valid YAML:

```bash
yq '.' _bmad-output/implementation-artifacts/sprint-status.yaml > /dev/null && echo "Valid YAML"
```
