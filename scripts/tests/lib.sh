#!/usr/bin/env bash
# Assertions for scripts/tests/test-*.sh. Source this file; call `finish` at the end.

TESTS_RUN=0
TESTS_FAILED=0
SCRIPTS_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

# script <name> [args...]: run scripts/<name>
script() {
    local name=$1
    shift
    "$SCRIPTS_DIR/$name" "$@"
}

pass() { TESTS_RUN=$((TESTS_RUN + 1)); }

fail() {
    TESTS_RUN=$((TESTS_RUN + 1))
    TESTS_FAILED=$((TESTS_FAILED + 1))
    echo "  FAIL: $1" >&2
    [[ -n ${2:-} ]] && printf '    %s\n' "$2" >&2
    return 0
}

# assert_eq <name> <expected> <actual>
assert_eq() {
    if [[ $2 == "$3" ]]; then pass; else fail "$1" "expected '$2', got '$3'"; fi
}

# assert_contains <name> <needle> <haystack>
assert_contains() {
    if [[ $3 == *"$2"* ]]; then pass; else fail "$1" "'$2' not in: $3"; fi
}

# A fresh temporary directory, removed when the test file exits
make_tmp() {
    local dir
    dir=$(mktemp -d)
    TMP_DIRS+=("$dir")
    echo "$dir"
}
TMP_DIRS=()
cleanup_tmp() { ((${#TMP_DIRS[@]})) && rm -rf "${TMP_DIRS[@]}"; return 0; }
trap cleanup_tmp EXIT

finish() {
    echo "$(basename "$0"): $((TESTS_RUN - TESTS_FAILED))/$TESTS_RUN passed"
    ((TESTS_FAILED == 0))
}
