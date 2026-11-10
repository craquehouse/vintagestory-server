#!/usr/bin/env bash
# Story 15.0 spike: AC3 evidence. Version-file commands on scratch copies, then package metadata
# and start-up behavior inside the image. Usage: version_check.sh [--image]
# --image builds a throwaway image tagged vss-150-spike (remove it afterwards with `docker image rm vss-150-spike`).
set -euo pipefail
REPO=$(git rev-parse --show-toplevel)
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

echo "== uv version on a scratch copy of api/ =="
mkdir -p "$WORK/repo/api" "$WORK/repo/web"
cp "$REPO/api/pyproject.toml" "$REPO/api/uv.lock" "$WORK/repo/api/"
cp "$REPO/web/package.json" "$REPO/web/bun.lock" "$WORK/repo/web/"
git -C "$WORK/repo" init -q && git -C "$WORK/repo" add -A
git -C "$WORK/repo" -c user.email=spike@example.invalid -c user.name=spike commit -qm base
(cd "$WORK/repo/api" && mise exec uv@0.13.7 -- uv version 0.2.0-rc.1 --no-sync 2>&1 | grep '=>')
git -C "$WORK/repo" diff --stat
git -C "$WORK/repo" diff -U0 | grep '^[-+][^-+]'
(cd "$WORK/repo/api" && echo "short: $(mise exec uv@0.13.7 -- uv version --short 2>/dev/null)")
git -C "$WORK/repo" checkout -q .

echo "== bun pm version on a scratch copy of web/ =="
(cd "$WORK/repo/web" && mise exec bun@1.4.4 -- bun pm version 0.2.0-rc.1 --no-git-tag-version)
git -C "$WORK/repo" diff --stat
git -C "$WORK/repo" diff -U0 | grep '^[-+][^-+]'
echo "commits: $(git -C "$WORK/repo" rev-list --count HEAD), tags: [$(git -C "$WORK/repo" tag | tr '\n' ' ')]"

[ "${1:-}" = "--image" ] || exit 0

echo "== image: build (linux/amd64, final stage) =="
docker build -q --platform linux/amd64 -t vss-150-spike --target final "$REPO" >/dev/null
run() { docker run --rm --platform linux/amd64 "$@" 2>&1 | grep -v 'platform (linux/amd64) does not match'; }
echo "-- metadata without syncing --"
run --network none --entrypoint "" vss-150-spike sh -c 'cd /app && uv run --no-sync python -c "import importlib.metadata as m; print(m.version(\"vintagestory-api\"))"'
echo "-- project importable from the build-time install? --"
run --network none --entrypoint "" vss-150-spike sh -c 'cd /app && uv run --no-sync python -c "import vintagestory_api" 2>&1 | tail -1'
echo "-- uv run (as in CMD), no network --"
run --network none --entrypoint "" vss-150-spike sh -c 'cd /app && uv run python -c "print(\"started\")" > /tmp/out 2>&1; rc=$?; tail -3 /tmp/out; echo "uv run exit=$rc"'
echo "-- uv run (as in CMD), with network: packages added at start --"
run --entrypoint "" vss-150-spike sh -c 'cd /app && uv pip list --quiet 2>/dev/null | sort > /tmp/before && uv run python -c "import importlib.metadata as m; print(\"version\", m.version(\"vintagestory-api\"))" 2>&1 | grep -E "Installed|Uninstalled|version"; uv pip list --quiet 2>/dev/null | sort > /tmp/after; echo "added:"; comm -13 /tmp/before /tmp/after | awk "{print \$1}" | tr "\n" " "; echo'
