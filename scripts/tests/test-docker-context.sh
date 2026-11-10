#!/usr/bin/env bash
# Guards the Docker build context against developer secrets (Story 15.2): web/.env holds
# a VITE_API_KEY that Vite would build into the bundle if it reached the image build.
set -uo pipefail
# shellcheck source=scripts/tests/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

ignore="$SCRIPTS_DIR/../.dockerignore"
patterns=$(grep -v '^[[:space:]]*#' "$ignore")

for pattern in '**/.env' '**/.env.*' '!**/.env.example'; do
    if grep -qxF -- "$pattern" <<<"$patterns"; then pass; else fail ".dockerignore has $pattern"; fi
done

dockerfile="$SCRIPTS_DIR/../Dockerfile"
if grep -qE '^ARG .*API_KEY' "$dockerfile"; then fail "Dockerfile declares no API key build argument"; else pass; fi
assert_contains "web build sets VITE_API_KEY empty" 'VITE_API_KEY=""' "$(<"$dockerfile")"

finish
