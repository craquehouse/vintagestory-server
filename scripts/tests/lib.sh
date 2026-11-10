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

# One root per test file, removed on exit. make_tmp creates directories inside it, so
# callers can use $(make_tmp) even though command substitution runs in a subshell.
TEST_TMP_ROOT=$(mktemp -d)
cleanup_tmp() { [[ -n ${TEST_TMP_ROOT:-} && -d $TEST_TMP_ROOT ]] && rm -rf "$TEST_TMP_ROOT"; return 0; }
trap cleanup_tmp EXIT

# A fresh temporary directory inside the test file's root
make_tmp() {
    mktemp -d "$TEST_TMP_ROOT/tmp.XXXXXX"
}

finish() {
    echo "$(basename "$0"): $((TESTS_RUN - TESTS_FAILED))/$TESTS_RUN passed"
    ((TESTS_FAILED == 0))
}
