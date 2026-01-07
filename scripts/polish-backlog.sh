#!/usr/bin/env bash
#
# polish-backlog.sh - Manage polish-backlog.md markdown tables
#
# This script provides safe manipulation of the polish backlog markdown file,
# avoiding formatting issues that occur when agents edit tables directly.
#
# Usage:
#   ./scripts/polish-backlog.sh <command> [args...]
#
# Commands:
#   list [category] [status]     - List items, optionally filtered
#   get <id>                     - Get details of a specific item
#   add <category> <desc> <priority> <effort> [related] [notes]
#                                - Add a new item (auto-generates ID)
#   set <id> <status>            - Update item status
#   done <id> [pr-url]           - Mark item done and move to archive
#   next-id <category>           - Show what the next ID would be
#
# Categories: UI, API, INFRA, TOOLS, CICD
# Statuses: backlog, in-progress, done
# Priorities: high, medium, low
# Efforts: S, M, L
#
# Examples:
#   ./scripts/polish-backlog.sh list
#   ./scripts/polish-backlog.sh list API backlog
#   ./scripts/polish-backlog.sh get UI-029
#   ./scripts/polish-backlog.sh add UI "Add dark mode toggle" medium S
#   ./scripts/polish-backlog.sh set UI-029 in-progress
#   ./scripts/polish-backlog.sh done UI-029 https://github.com/org/repo/pull/99
#

set -euo pipefail

# Change to repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$REPO_ROOT"

BACKLOG_FILE="_bmad-output/implementation-artifacts/polish-backlog.md"

# Category to section header mapping
declare -A CATEGORY_HEADERS=(
    ["UI"]="## UI"
    ["API"]="## API"
    ["INFRA"]="## Infrastructure"
    ["TOOLS"]="## Tools"
    ["CICD"]="## CI/CD"
)

# Validate file exists
if [[ ! -f "$BACKLOG_FILE" ]]; then
    echo "Error: Polish backlog file not found: $BACKLOG_FILE" >&2
    exit 1
fi

usage() {
    head -36 "$0" | grep '^#' | sed 's/^# \?//'
    exit 1
}

# Get the next available ID for a category
get_next_id() {
    local category="$1"
    local prefix="${category}-"

    # Handle INFRA prefix mapping
    if [[ "$category" == "INFRA" ]]; then
        prefix="INFRA-"
    fi

    # Find the highest existing ID number for this category
    local max_num=0
    while IFS= read -r line; do
        if [[ "$line" =~ \|[[:space:]]*${prefix}([0-9]+)[[:space:]]*\| ]]; then
            local num="${BASH_REMATCH[1]}"
            # Remove leading zeros for comparison
            num=$((10#$num))
            if (( num > max_num )); then
                max_num=$num
            fi
        fi
    done < "$BACKLOG_FILE"

    local next_num=$((max_num + 1))
    printf "%s%03d" "$prefix" "$next_num"
}

# Validate category
validate_category() {
    local category="$1"
    local valid_categories="UI API INFRA TOOLS CICD"
    if [[ ! " $valid_categories " =~ " $category " ]]; then
        echo "Error: Invalid category '$category'. Valid: $valid_categories" >&2
        exit 1
    fi
}

# Validate status
validate_status() {
    local status="$1"
    local valid_statuses="backlog in-progress done"
    if [[ ! " $valid_statuses " =~ " $status " ]]; then
        echo "Error: Invalid status '$status'. Valid: $valid_statuses" >&2
        exit 1
    fi
}

# Validate priority
validate_priority() {
    local priority="$1"
    local valid_priorities="high medium low"
    if [[ ! " $valid_priorities " =~ " $priority " ]]; then
        echo "Error: Invalid priority '$priority'. Valid: $valid_priorities" >&2
        exit 1
    fi
}

# Validate effort
validate_effort() {
    local effort="$1"
    local valid_efforts="S M L s m l"
    if [[ ! " $valid_efforts " =~ " $effort " ]]; then
        echo "Error: Invalid effort '$effort'. Valid: S, M, L" >&2
        exit 1
    fi
}

# Find line number of an item by ID
find_item_line() {
    local id="$1"
    grep -n "| *${id} *|" "$BACKLOG_FILE" | head -1 | cut -d: -f1
}

# Parse a table row into fields
parse_row() {
    local line="$1"
    # Remove leading/trailing pipes and split by pipe
    echo "$line" | sed 's/^|//;s/|$//' | tr '|' '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
}

cmd_list() {
    local filter_category="${1:-}"
    local filter_status="${2:-}"

    # Validate filters if provided
    if [[ -n "$filter_category" ]]; then
        validate_category "$filter_category"
    fi
    if [[ -n "$filter_status" ]]; then
        validate_status "$filter_status"
    fi

    local current_category=""
    local in_table=false
    local header_printed=false

    while IFS= read -r line; do
        # Track current category
        if [[ "$line" =~ ^##[[:space:]]+(UI|API|Infrastructure|Tools|CI/CD) ]]; then
            case "${BASH_REMATCH[1]}" in
                "UI") current_category="UI" ;;
                "API") current_category="API" ;;
                "Infrastructure") current_category="INFRA" ;;
                "Tools") current_category="TOOLS" ;;
                "CI/CD") current_category="CICD" ;;
            esac
            in_table=false
            header_printed=false
            continue
        fi

        # Skip if filtering by category and this isn't it
        if [[ -n "$filter_category" && "$current_category" != "$filter_category" ]]; then
            continue
        fi

        # Detect table header row
        if [[ "$line" =~ ^\|[[:space:]]*ID[[:space:]]*\| ]]; then
            in_table=true
            continue
        fi

        # Skip separator row
        if [[ "$line" =~ ^\|[[:space:]]*-+ ]]; then
            continue
        fi

        # Process data rows
        if [[ "$in_table" == true && "$line" =~ ^\|.*\|$ ]]; then
            # Extract fields
            local id desc priority effort status related notes
            IFS='|' read -r _ id desc priority effort status related notes _ <<< "$line"

            # Trim whitespace (using sed instead of xargs to handle special chars)
            id=$(echo "$id" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            desc=$(echo "$desc" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            priority=$(echo "$priority" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            effort=$(echo "$effort" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            status=$(echo "$status" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

            # Skip if filtering by status and this isn't it
            if [[ -n "$filter_status" && "$status" != "$filter_status" ]]; then
                continue
            fi

            # Skip items that look like the archive header
            if [[ "$id" == "ID" || -z "$id" ]]; then
                continue
            fi

            # Print category header once
            if [[ "$header_printed" == false ]]; then
                echo "=== $current_category ==="
                header_printed=true
            fi

            printf "%-8s %-12s %-6s %-2s  %s\n" "$id" "[$status]" "$priority" "$effort" "${desc:0:60}"
        fi

        # Stop at archive section
        if [[ "$line" =~ ^##[[:space:]]+Completed ]]; then
            break
        fi
    done < "$BACKLOG_FILE"
}

cmd_get() {
    local id="$1"

    local line_num
    line_num=$(find_item_line "$id")

    if [[ -z "$line_num" ]]; then
        echo "Error: Item '$id' not found" >&2
        exit 1
    fi

    local line
    line=$(sed -n "${line_num}p" "$BACKLOG_FILE")

    # Parse and display
    IFS='|' read -r _ item_id desc priority effort status related notes _ <<< "$line"

    echo "ID:          $(echo "$item_id" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    echo "Description: $(echo "$desc" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    echo "Priority:    $(echo "$priority" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    echo "Effort:      $(echo "$effort" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    echo "Status:      $(echo "$status" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    echo "Related:     $(echo "$related" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    echo "Notes:       $(echo "$notes" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
}

cmd_add() {
    local category="$1"
    local desc="$2"
    local priority="$3"
    local effort="$4"
    local related="${5:--}"
    local notes="${6:--}"

    validate_category "$category"
    validate_priority "$priority"
    validate_effort "$effort"

    # Normalize effort to uppercase
    effort=$(echo "$effort" | tr '[:lower:]' '[:upper:]')

    local new_id
    new_id=$(get_next_id "$category")

    # Find the section and the last row before the next section or separator
    local section_header="${CATEGORY_HEADERS[$category]}"
    local insert_after_line=0
    local in_section=false
    local line_num=0

    while IFS= read -r line; do
        ((++line_num))

        if [[ "$line" == "$section_header" ]]; then
            in_section=true
            continue
        fi

        if [[ "$in_section" == true ]]; then
            # If we hit another section or the separator, insert before this
            if [[ "$line" =~ ^##[[:space:]] || "$line" =~ ^---$ ]]; then
                break
            fi
            # Track the last table row
            if [[ "$line" =~ ^\|.*\|$ && ! "$line" =~ ^\|[[:space:]]*ID && ! "$line" =~ ^\|[[:space:]]*-+ ]]; then
                insert_after_line=$line_num
            fi
        fi
    done < <(cat "$BACKLOG_FILE")

    if [[ $insert_after_line -eq 0 ]]; then
        echo "Error: Could not find insertion point in $category section" >&2
        exit 1
    fi

    # Build the new row
    local new_row="| $new_id | $desc | $priority | $effort | backlog | $related | $notes |"

    # Insert the new row
    sed -i '' "${insert_after_line}a\\
${new_row}
" "$BACKLOG_FILE"

    echo "Added: $new_id -> backlog"
    echo "  Description: $desc"
    echo "  Priority: $priority, Effort: $effort"
}

cmd_set() {
    local id="$1"
    local new_status="$2"

    validate_status "$new_status"

    local line_num
    line_num=$(find_item_line "$id")

    if [[ -z "$line_num" ]]; then
        echo "Error: Item '$id' not found" >&2
        exit 1
    fi

    # Get current line
    local line
    line=$(sed -n "${line_num}p" "$BACKLOG_FILE")

    # Parse fields
    IFS='|' read -r _ item_id desc priority effort status related notes _ <<< "$line"

    # Trim whitespace (using sed to handle special chars)
    item_id=$(echo "$item_id" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    desc=$(echo "$desc" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    priority=$(echo "$priority" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    effort=$(echo "$effort" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    related=$(echo "$related" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    notes=$(echo "$notes" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

    # Build updated row
    local new_row="| $item_id | $desc | $priority | $effort | $new_status | $related | $notes |"

    # Replace the line (use # as delimiter since row contains |)
    sed -i '' "${line_num}s#.*#${new_row}#" "$BACKLOG_FILE"

    echo "Updated: $id -> $new_status"
}

cmd_done() {
    local id="$1"
    local pr_url="${2:-}"

    local line_num
    line_num=$(find_item_line "$id")

    if [[ -z "$line_num" ]]; then
        echo "Error: Item '$id' not found" >&2
        exit 1
    fi

    # Get current line
    local line
    line=$(sed -n "${line_num}p" "$BACKLOG_FILE")

    # Parse fields
    IFS='|' read -r _ item_id desc priority effort status related notes _ <<< "$line"

    # Trim whitespace (using sed to handle special chars)
    item_id=$(echo "$item_id" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    desc=$(echo "$desc" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    notes=$(echo "$notes" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

    # First, update the status to done in place
    cmd_set "$id" "done"

    # Get today's date
    local today
    today=$(date +%Y-%m-%d)

    # Build archive row - format: | ID | Description | Completed | Notes |
    local archive_id="$item_id"
    if [[ -n "$pr_url" ]]; then
        archive_id="[$item_id]($pr_url)"
    fi

    local archive_row="| $archive_id | $desc | $today | $notes |"

    # Find the archive section and the last row
    local archive_insert_line=0
    local in_archive=false
    local current_line=0

    while IFS= read -r file_line; do
        ((current_line++))

        if [[ "$file_line" =~ ^##[[:space:]]+Completed[[:space:]]+Items ]]; then
            in_archive=true
            continue
        fi

        if [[ "$in_archive" == true && "$file_line" =~ ^\|.*\|$ && ! "$file_line" =~ ^\|[[:space:]]*ID && ! "$file_line" =~ ^\|[[:space:]]*-+ ]]; then
            archive_insert_line=$current_line
        fi
    done < "$BACKLOG_FILE"

    if [[ $archive_insert_line -gt 0 ]]; then
        sed -i '' "${archive_insert_line}a\\
${archive_row}
" "$BACKLOG_FILE"
        echo "Archived: $id -> Completed Items Archive"
    fi
}

cmd_next_id() {
    local category="$1"
    validate_category "$category"
    get_next_id "$category"
}

# Main dispatch
if [[ $# -lt 1 ]]; then
    usage
fi

command="$1"
shift

case "$command" in
    list)
        cmd_list "${1:-}" "${2:-}"
        ;;
    get)
        [[ $# -lt 1 ]] && { echo "Error: get requires an ID"; usage; }
        cmd_get "$1"
        ;;
    add)
        [[ $# -lt 4 ]] && { echo "Error: add requires category, description, priority, effort"; usage; }
        cmd_add "$1" "$2" "$3" "$4" "${5:-}" "${6:-}"
        ;;
    set)
        [[ $# -lt 2 ]] && { echo "Error: set requires ID and status"; usage; }
        cmd_set "$1" "$2"
        ;;
    done)
        [[ $# -lt 1 ]] && { echo "Error: done requires an ID"; usage; }
        cmd_done "$1" "${2:-}"
        ;;
    next-id)
        [[ $# -lt 1 ]] && { echo "Error: next-id requires a category"; usage; }
        cmd_next_id "$1"
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        echo "Error: Unknown command '$command'"
        usage
        ;;
esac
