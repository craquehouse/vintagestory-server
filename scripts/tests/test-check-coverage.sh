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

# `just lint-scripts` checks every script through globs, so a new one is covered (FR241)
justfile="$ROOT/Justfile"
assert_eq "lint-scripts runs ShellCheck on every script" \
    "mise exec -- shellcheck -x scripts/*.sh scripts/tests/*.sh" \
    "$(grep -A1 '^lint-scripts:' "$justfile" | tail -1 | sed 's/^[[:space:]]*//')"
assert_eq "the Justfile names no ShellCheck follow-up (VSS-1eb)" "0" "$(grep -c 'VSS-1eb' "$justfile")"

# Playwright's output is not tracked and stays out of the image build context; CI still
# uploads it when the e2e job fails (FR243)
assert_eq "no Playwright output is tracked" "" \
    "$(git -C "$ROOT" ls-files web/playwright-report web/test-results)"
# The second pass of scripts/e2e-ci.sh writes its own (Story 20.6)
for ignore in .gitignore .dockerignore; do
    for path in web/playwright-report/ web/test-results/ web/playwright-report-moddb/ web/test-results-moddb/; do
        if grep -qxF -- "$path" "$ROOT/$ignore"; then pass; else fail "$ignore has $path"; fi
    done
done
assert_eq "ci.yml e2e job uploads the Playwright output" \
    "$(printf '%s\n' web/playwright-report/ web/test-results/ web/playwright-report-moddb/ web/test-results-moddb/)" \
    "$(yq '.jobs.e2e.steps[] | select(.uses == "actions/upload-artifact@*") | .with.path' "$ci" | sed '/^$/d')"

finish
