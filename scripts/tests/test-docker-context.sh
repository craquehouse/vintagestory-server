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

# Every action in every workflow is pinned to a full commit SHA (NFR17)
unpinned=$(grep -hE '^\s*-?\s*uses:' "$SCRIPTS_DIR"/../.github/workflows/*.yml |
    grep -vE 'uses:\s*([^@[:space:]]+@[0-9a-f]{40}|\./[^[:space:]]+|docker://[^[:space:]]+@sha256:[0-9a-f]{64})(\s|$)' || true)
assert_eq "workflow actions are pinned to commit SHAs" "" "$unpinned"

# Every image the Dockerfile builds from or copies from is pinned by digest, and the uv
# image's tag is the uv version .mise.toml pins (Epic 20 ADR-10)
images=$(sed -nE 's/^FROM[[:space:]]+([^[:space:]]+).*/\1/p; s/^COPY[[:space:]]+--from=([^[:space:]]+).*/\1/p' "$dockerfile")
stages=$(sed -nE 's/^FROM[[:space:]].*[[:space:]]AS[[:space:]]+([^[:space:]]+).*/\1/p' "$dockerfile")
external=$(grep -vxF -f <(printf '%s\n' "$stages") <<<"$images" || true)
assert_eq "the Dockerfile uses three images" 3 "$(grep -c . <<<"$external")"
unpinned=$(grep -vE '@sha256:[0-9a-f]{64}$' <<<"$external" || true)
assert_eq "every Dockerfile image is pinned by digest" "" "$unpinned"
mise_uv=$(sed -nE 's/^uv[[:space:]]*=[[:space:]]*"([^"]+)".*/\1/p' "$SCRIPTS_DIR/../.mise.toml")
uv_tag=$(sed -nE 's|^ghcr\.io/astral-sh/uv:([^@]+)@.*|\1|p' <<<"$external")
if [[ -n $mise_uv ]]; then pass; else fail ".mise.toml pins uv"; fi
assert_eq "the uv image tag is the uv version .mise.toml pins" "$mise_uv" "$uv_tag"

finish
