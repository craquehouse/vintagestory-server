#!/usr/bin/env bash
#
# sprint-status.sh - Manage sprint-status.yaml using yq
#
# This script provides safe YAML manipulation for sprint-status.yaml,
# avoiding formatting issues that occur when agents edit the file directly.
#
# Usage:
#   ./scripts/sprint-status.sh <command> [args...]
#
# Commands:
#   get <key>                    - Get status of a story/epic
#   set <key> <status>           - Set status of existing story/epic
#   add-story <epic> <story-id>  - Add a new story to an epic (status: backlog)
#   add-epic <epic-id>           - Add a new epic (status: backlog)
#   list [status]                - List all entries, optionally filtered by status
#   retro-set <key> <status>     - Set status of a retro action item
#   retro-add <key>              - Add a new retro action item (status: pending)
#
# Valid statuses for stories:
#   backlog, ready-for-dev, in-progress, review, done
#
# Valid statuses for epics:
#   backlog, in-progress, done
#
# Valid statuses for retro items:
#   pending, done
#
# Examples:
#   ./scripts/sprint-status.sh get 10-1-mod-browse-api
#   ./scripts/sprint-status.sh set 10-1-mod-browse-api review
#   ./scripts/sprint-status.sh set epic-10 in-progress
#   ./scripts/sprint-status.sh add-story 10 10-9-new-feature
#   ./scripts/sprint-status.sh add-epic 11
#   ./scripts/sprint-status.sh list in-progress
#   ./scripts/sprint-status.sh retro-set A1-example done
#

set -euo pipefail

# Change to repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$REPO_ROOT"

SPRINT_FILE="_bmad-output/implementation-artifacts/sprint-status.yaml"

# Validate file exists
if [[ ! -f "$SPRINT_FILE" ]]; then
    echo "Error: Sprint status file not found: $SPRINT_FILE" >&2
    exit 1
fi

# Check yq is available
if ! command -v yq &> /dev/null; then
    echo "Error: yq is required but not installed. Install with: brew install yq" >&2
    exit 1
fi

usage() {
    head -40 "$0" | grep '^#' | sed 's/^# \?//'
    exit 1
}

cmd_get() {
    local key="$1"

    # Try development_status first, then retro_action_items
    local value
    value=$(yq ".development_status.\"$key\" // .retro_action_items.\"$key\"" "$SPRINT_FILE")

    if [[ "$value" == "null" ]]; then
        echo "Error: Key '$key' not found in sprint-status.yaml" >&2
        exit 1
    fi

    echo "$value"
}

cmd_set() {
    local key="$1"
    local status="$2"

    # Validate status for stories
    local valid_story_statuses="backlog ready-for-dev in-progress review done"
    local valid_epic_statuses="backlog in-progress done"
    local valid_retro_statuses="optional pending done"

    # Determine if this is an epic, story, or retro
    if [[ "$key" == epic-* ]]; then
        if [[ ! " $valid_epic_statuses " =~ " $status " ]]; then
            echo "Error: Invalid epic status '$status'. Valid: $valid_epic_statuses" >&2
            exit 1
        fi
    elif [[ "$key" == *-retrospective ]]; then
        if [[ ! " $valid_retro_statuses " =~ " $status " ]]; then
            echo "Error: Invalid retrospective status '$status'. Valid: $valid_retro_statuses" >&2
            exit 1
        fi
    else
        if [[ ! " $valid_story_statuses " =~ " $status " ]]; then
            echo "Error: Invalid story status '$status'. Valid: $valid_story_statuses" >&2
            exit 1
        fi
    fi

    # Check if key exists
    local current
    current=$(yq ".development_status.\"$key\"" "$SPRINT_FILE")

    if [[ "$current" == "null" ]]; then
        echo "Error: Key '$key' not found in development_status" >&2
        exit 1
    fi

    # Update the status
    yq -i ".development_status.\"$key\" = \"$status\"" "$SPRINT_FILE"
    echo "Updated: $key -> $status"
}

cmd_add_story() {
    local epic="$1"
    local story_id="$2"

    # Validate epic exists
    local epic_key="epic-$epic"
    local epic_status
    epic_status=$(yq ".development_status.\"$epic_key\"" "$SPRINT_FILE")

    if [[ "$epic_status" == "null" ]]; then
        echo "Error: Epic '$epic_key' not found" >&2
        exit 1
    fi

    # Check if story already exists
    local existing
    existing=$(yq ".development_status.\"$story_id\"" "$SPRINT_FILE")

    if [[ "$existing" != "null" ]]; then
        echo "Error: Story '$story_id' already exists with status: $existing" >&2
        exit 1
    fi

    # Find the position after the epic's retrospective or last story
    # This uses yq to insert in the right place while preserving structure
    yq -i ".development_status.\"$story_id\" = \"backlog\"" "$SPRINT_FILE"
    echo "Added story: $story_id -> backlog"
}

cmd_add_epic() {
    local epic_id="$1"
    local epic_key="epic-$epic_id"

    # Check if epic already exists
    local existing
    existing=$(yq ".development_status.\"$epic_key\"" "$SPRINT_FILE")

    if [[ "$existing" != "null" ]]; then
        echo "Error: Epic '$epic_key' already exists with status: $existing" >&2
        exit 1
    fi

    # Add epic and retrospective
    yq -i ".development_status.\"$epic_key\" = \"backlog\"" "$SPRINT_FILE"
    yq -i ".development_status.\"$epic_key-retrospective\" = \"optional\"" "$SPRINT_FILE"
    echo "Added epic: $epic_key -> backlog"
    echo "Added retrospective: $epic_key-retrospective -> optional"
}

cmd_list() {
    local filter="${1:-}"

    echo "=== development_status ==="
    if [[ -z "$filter" ]]; then
        yq '.development_status | to_entries | .[] | .key + ": " + .value' "$SPRINT_FILE"
    else
        yq ".development_status | to_entries | .[] | select(.value == \"$filter\") | .key + \": \" + .value" "$SPRINT_FILE"
    fi

    echo ""
    echo "=== retro_action_items ==="
    if [[ -z "$filter" ]]; then
        yq '.retro_action_items | to_entries | .[] | .key + ": " + .value' "$SPRINT_FILE" 2>/dev/null || echo "(none)"
    else
        yq ".retro_action_items | to_entries | .[] | select(.value == \"$filter\") | .key + \": \" + .value" "$SPRINT_FILE" 2>/dev/null || echo "(none matching)"
    fi
}

cmd_retro_set() {
    local key="$1"
    local status="$2"

    local valid_statuses="pending done"
    if [[ ! " $valid_statuses " =~ " $status " ]]; then
        echo "Error: Invalid retro status '$status'. Valid: $valid_statuses" >&2
        exit 1
    fi

    # Check if key exists
    local current
    current=$(yq ".retro_action_items.\"$key\"" "$SPRINT_FILE")

    if [[ "$current" == "null" ]]; then
        echo "Error: Retro item '$key' not found" >&2
        exit 1
    fi

    yq -i ".retro_action_items.\"$key\" = \"$status\"" "$SPRINT_FILE"
    echo "Updated retro item: $key -> $status"
}

cmd_retro_add() {
    local key="$1"
    local comment="${2:-}"

    # Check if key already exists
    local existing
    existing=$(yq ".retro_action_items.\"$key\"" "$SPRINT_FILE")

    if [[ "$existing" != "null" ]]; then
        echo "Error: Retro item '$key' already exists with status: $existing" >&2
        exit 1
    fi

    yq -i ".retro_action_items.\"$key\" = \"pending\"" "$SPRINT_FILE"
    echo "Added retro item: $key -> pending"
}

# Main dispatch
if [[ $# -lt 1 ]]; then
    usage
fi

command="$1"
shift

case "$command" in
    get)
        [[ $# -lt 1 ]] && { echo "Error: get requires a key"; usage; }
        cmd_get "$1"
        ;;
    set)
        [[ $# -lt 2 ]] && { echo "Error: set requires key and status"; usage; }
        cmd_set "$1" "$2"
        ;;
    add-story)
        [[ $# -lt 2 ]] && { echo "Error: add-story requires epic number and story-id"; usage; }
        cmd_add_story "$1" "$2"
        ;;
    add-epic)
        [[ $# -lt 1 ]] && { echo "Error: add-epic requires epic-id"; usage; }
        cmd_add_epic "$1"
        ;;
    list)
        cmd_list "${1:-}"
        ;;
    retro-set)
        [[ $# -lt 2 ]] && { echo "Error: retro-set requires key and status"; usage; }
        cmd_retro_set "$1" "$2"
        ;;
    retro-add)
        [[ $# -lt 1 ]] && { echo "Error: retro-add requires key"; usage; }
        cmd_retro_add "$1"
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        echo "Error: Unknown command '$command'"
        usage
        ;;
esac
