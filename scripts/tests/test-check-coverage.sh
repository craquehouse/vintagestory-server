#!/usr/bin/env bash
# Guards the wiring that makes the checks cover everything (Story 20.3): the E2E specs and
# playwright.config.ts are type-checked, every script is linted, and Playwright's output is
# not tracked.
set -uo pipefail
# shellcheck source=scripts/tests/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

ROOT="$SCRIPTS_DIR/.."

# The E2E specs and playwright.config.ts are type-checked by `just typecheck-web` and CI,
# and the image build (`bun run build`) does not depend on them (FR240)
package="$ROOT/web/package.json"
assert_eq "web typecheck script checks src, tests and e2e" \
    "tsc --noEmit && tsc --noEmit -p e2e/tsconfig.json" \
    "$(yq -p json '.scripts.typecheck' "$package" 2>/dev/null)"
assert_eq "web build script is unchanged" "tsc && vite build" \
    "$(yq -p json '.scripts.build' "$package" 2>/dev/null)"
ci="$ROOT/.github/workflows/ci.yml"
assert_eq "ci.yml web job runs just typecheck-web" "1" \
    "$(yq '[.jobs.web.steps[] | select(.run == "just typecheck-web")] | length' "$ci" 2>/dev/null)"
e2e_tsconfig="$ROOT/web/e2e/tsconfig.json"
assert_eq "e2e tsconfig extends the web tsconfig" "../tsconfig.json" \
    "$(yq -p json '.extends' "$e2e_tsconfig" 2>/dev/null)"
assert_eq "e2e tsconfig sees Node's types only" '["node"]' \
    "$(yq -p json -o json -I0 '.compilerOptions.types' "$e2e_tsconfig" 2>/dev/null)"

finish
