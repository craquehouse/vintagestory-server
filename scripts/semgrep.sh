#!/usr/bin/env bash
# Static security scan of the source with semgrep (Story 20.4, Epic 20 ADR-6).
#
# Runs one pinned semgrep through uvx with six registry packs, fetched at run time (needs
# the network), over the source. Files that only hold tests are left out by .semgrepignore.
# Exits 1 on a finding and 2 or more when semgrep could not run.
#
# Usage: scripts/semgrep.sh [semgrep scan args...]   (via `just semgrep`)
#   just semgrep --baseline-commit origin/main   only findings the branch adds
#   SEMGREP_REPORT_ONLY=1   report findings without failing (CI's full scan of main)
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

# Renovate updates this line (renovate.json customManagers); test-semgrep.sh pins its form
SEMGREP_VERSION="1.186.0"
PACKS=(p/python p/typescript p/react p/secrets p/github-actions p/dockerfile)
PATHS=(api/src web/src .github Dockerfile scripts)

# The registry serves a logged-in user a different, larger rule set. CI is never logged in,
# so ignore a developer's `semgrep login` and scan with the rules CI uses.
export SEMGREP_SETTINGS_FILE=/dev/null
unset SEMGREP_APP_TOKEN

args=(scan --metrics=off)
[[ ${SEMGREP_REPORT_ONLY:-} == 1 ]] || args+=(--error)
for pack in "${PACKS[@]}"; do
    args+=(--config "$pack")
done

exec uvx "semgrep==$SEMGREP_VERSION" "${args[@]}" "$@" "${PATHS[@]}"
