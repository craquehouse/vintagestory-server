#!/usr/bin/env bash
# Run scripts/tests/test-*.sh (or the test files named, e.g. test-version.sh) and fail if any fails.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1
files=()
for arg in "$@"; do
    files+=("$(basename "$arg")") # names are resolved in scripts/tests/
done
((${#files[@]})) || files=(test-*.sh)
failed=0
for file in "${files[@]}"; do
    bash "$file" || failed=1
done
exit "$failed"
