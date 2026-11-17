#!/usr/bin/env bash
# Pins the Renovate rules of Epic 21 ADR-2 and ADR-3 in renovate.json: the uv group keeps
# the preset's one-day hold (no minimumReleaseAge of its own) and is chore(uv); a digest
# refresh of a Dockerfile image is chore, and no rule retypes a version update.
set -uo pipefail
# shellcheck source=scripts/tests/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

problems=$(python3 -I - "$SCRIPTS_DIR/../renovate.json" <<'PY'
import json, sys

try:
    rules = json.load(open(sys.argv[1]))["packageRules"]
except Exception as e:
    print(f"renovate.json does not parse: {e}")
    sys.exit()
problems = []

uv = [r for r in rules if sorted(r.get("matchDepNames", [])) == ["ghcr.io/astral-sh/uv", "uv"]]
if len(uv) != 1:
    problems.append(f"one rule groups uv and ghcr.io/astral-sh/uv (found {len(uv)})")
else:
    r = uv[0]
    if "minimumReleaseAge" in r:
        problems.append("the uv rule sets no minimumReleaseAge (the preset's hold applies)")
    for key, want in (("groupName", "uv"), ("semanticCommitType", "chore"), ("semanticCommitScope", "uv")):
        if r.get(key) != want:
            problems.append(f"the uv rule has {key} {want!r}, not {r.get(key)!r}")

digest = [r for r in rules if r.get("matchManagers") == ["dockerfile"]
          and sorted(r.get("matchUpdateTypes", [])) == ["digest", "pinDigest"]]
if len(digest) != 1 or digest[0].get("semanticCommitType") != "chore" or rules[-1] is not digest[0]:
    problems.append("one rule types dockerfile digest and pinDigest updates chore")

for r in rules:
    versions = {"patch", "minor", "major"} & set(r.get("matchUpdateTypes", []))
    if versions and "semanticCommitType" in r:
        problems.append(f"a rule retypes {sorted(versions)} updates: {r.get('description', r)}")

print("\n".join(problems))
PY
)
assert_eq "renovate.json: the uv hold and the digest rule (Epic 21 ADR-2, ADR-3)" "" "$problems"

finish
