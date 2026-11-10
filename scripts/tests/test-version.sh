#!/usr/bin/env bash
# Tests for scripts/version.sh (Story 15.1).
set -uo pipefail
# shellcheck source=scripts/tests/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

# version_files <dir> <package.json version> <pyproject version> <uv.lock version>
version_files() {
    mkdir -p "$1/web" "$1/api"
    printf '{\n  "name": "web",\n  "version": "%s"\n}\n' "$2" > "$1/web/package.json"
    printf '[project]\nname = "vintagestory-api"\nversion = "%s"\n' "$3" > "$1/api/pyproject.toml"
    printf 'version = 1\n\n[[package]]\nname = "anyio"\nversion = "4.0.0"\n\n[[package]]\nname = "vintagestory-api"\nversion = "%s"\nsource = { editable = "." }\n' "$4" > "$1/api/uv.lock"
}

# run_version <package.json> <pyproject> <uv.lock>: sets OUT, ERR and STATUS
run_version() {
    local dir
    dir=$(make_tmp)
    version_files "$dir" "$1" "$2" "$3"
    OUT=$(script version.sh "$dir" 2>"$dir/err")
    STATUS=$?
    ERR=$(<"$dir/err")
}

run_version 0.1.0 0.1.0 0.1.0
assert_eq "stable versions agree: exit" 0 "$STATUS"
assert_eq "stable versions agree: prints version" 0.1.0 "$OUT"

run_version 0.2.0-rc.1 0.2.0rc1 0.2.0rc1
assert_eq "rc in both spellings: exit" 0 "$STATUS"
assert_eq "rc prints the SemVer spelling" 0.2.0-rc.1 "$OUT"

run_version 1.0.0-alpha.2 1.0.0a2 1.0.0a2
assert_eq "alpha normalizes to aN" 0 "$STATUS"

run_version 1.0.0-beta.3 1.0.0b3 1.0.0b3
assert_eq "beta normalizes to bN" 0 "$STATUS"

run_version 0.2.0 0.1.0 0.1.0
assert_eq "pyproject mismatch: exit" 1 "$STATUS"
assert_contains "pyproject mismatch: names the file" "api/pyproject.toml has '0.1.0'" "$ERR"
assert_eq "pyproject mismatch: prints nothing" "" "$OUT"

run_version 0.2.0 0.2.0 0.1.0
assert_eq "uv.lock mismatch: exit" 1 "$STATUS"
assert_contains "uv.lock mismatch: names the file" "api/uv.lock has '0.1.0'" "$ERR"

run_version 0.2.0-rc.1 0.2.0-rc.1 0.2.0-rc.1
assert_eq "pyproject in SemVer spelling is a mismatch" 1 "$STATUS"

run_version 0.2 0.2 0.2
assert_eq "not X.Y.Z: exit" 1 "$STATUS"
assert_contains "not X.Y.Z: explains the format" "is not X.Y.Z" "$ERR"

run_version 0.2.0-preview.1 0.2.0 0.2.0
assert_eq "unsupported pre-release form: exit" 1 "$STATUS"

run_version 0.2.0-rc 0.2.0rc0 0.2.0rc0
assert_eq "rc without a number: exit" 1 "$STATUS"

run_version 01.2.0 1.2.0 1.2.0
assert_eq "leading zero: exit" 1 "$STATUS"

dir=$(make_tmp)
version_files "$dir" 0.1.0 0.1.0 0.1.0
printf 'version = 1\n' > "$dir/api/uv.lock"
script version.sh "$dir" >/dev/null 2>"$dir/err"
assert_eq "uv.lock without the project: exit" 1 "$?"
assert_contains "uv.lock without the project: explains" "api/uv.lock has ''" "$(<"$dir/err")"

dir=$(make_tmp)
version_files "$dir" 0.1.0 0.1.0 0.1.0
rm "$dir/api/uv.lock"
script version.sh "$dir" >/dev/null 2>"$dir/err"
assert_eq "missing uv.lock: exit" 1 "$?"
assert_contains "missing uv.lock: names the file" "api/uv.lock not found" "$(<"$dir/err")"

dir=$(make_tmp)
version_files "$dir" 0.1.0 0.1.0 0.1.0
printf '[project\nversion = \n' > "$dir/api/pyproject.toml"
script version.sh "$dir" >/dev/null 2>"$dir/err"
assert_eq "unparseable pyproject.toml: exit" 1 "$?"
assert_contains "unparseable pyproject.toml: names the file" "cannot parse api/pyproject.toml" "$(<"$dir/err")"

finish
