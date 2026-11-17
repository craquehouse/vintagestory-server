#!/usr/bin/env python3
"""Record the mod database answers the E2E tests replay (Story 20.6, Epic 20 ADR-9).

Reads web/e2e/fixtures/moddb/manifest.json, fetches each entry's request from the mod
database with an unauthenticated GET, trims the answer the way the entry says, and writes
the entry's file and its `recorded` date. Prints, per request, the fields (key paths, list
positions collapsed) that appeared or disappeared since the last recording.

Everything is fetched and checked before anything is written, so a failed request or an
answer that is not JSON leaves the recordings as they were. The script reads no environment
variable and no file but the manifest and the old recordings, and sends a fixed, generic
User-Agent, so nothing about a developer's instance reaches a request or a recording.

Usage (via `just record-moddb`):
  scripts/moddb-record.py                        record every request
  scripts/moddb-record.py --only /api/mod/carryon   record only that request (repeatable)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TypeGuard

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "web" / "e2e" / "fixtures" / "moddb" / "manifest.json"
DEFAULT_SOURCE = "https://mods.vintagestory.at"
USER_AGENT = "moddb-fixture-recorder"
MIN_LISTING_MODS = 41  # three browse pages of 20 (mod-browse-name-sort.spec.ts)
RELEASES_FIRST = re.compile(r"^releases-first-(\d+)$")


class RecordError(Exception):
    """The run stops; nothing has been written."""


def is_json_object(value: object) -> TypeGuard[dict[str, object]]:
    """A JSON object (json.loads gives str keys)."""
    return isinstance(value, dict)


def is_json_array(value: object) -> TypeGuard[list[object]]:
    """A JSON array."""
    return isinstance(value, list)


@dataclass
class Entry:
    """One manifest entry: the request, its file and how its answer is trimmed."""

    request: str
    file: str
    trim: str
    raw: dict[str, object]


def text(value: object) -> str:
    return value if isinstance(value, str) else ""


def string_list(value: object) -> list[str]:
    return [item for item in value if isinstance(item, str)] if is_json_array(value) else []


def read_manifest(path: Path) -> tuple[dict[str, object], list[Entry]]:
    try:
        manifest: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise RecordError(f"cannot read {path}: {e}") from e
    if not is_json_object(manifest):
        raise RecordError(f"{path} is not a JSON object")
    raw_entries = manifest.get("requests")
    if not is_json_array(raw_entries):
        raise RecordError(f"{path} has no list of requests")
    entries: list[Entry] = []
    for index, raw in enumerate(raw_entries):
        if not is_json_object(raw):
            raise RecordError(f"entry {index} is not an object")
        request, file, trim = text(raw.get("request")), text(raw.get("file")), text(raw.get("trim"))
        if not request.startswith("/") or not file or "/" in file or ".." in file:
            raise RecordError(f"entry {index} needs a request path and a plain file name")
        if trim not in ("none", "listing", "listing-subset") and not RELEASES_FIRST.match(trim):
            raise RecordError(f"entry {index} ({request}) has an unknown trim: {trim!r}")
        entries.append(Entry(request, file, trim, raw))
    return manifest, entries


def fetch(base_url: str, request: str, timeout: float) -> object:
    """GET base_url + request; the parsed JSON answer, or RecordError."""
    url = base_url + request
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body: bytes = response.read()
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise RecordError(f"GET {url} failed: {e}") from e
    try:
        return json.loads(body)
    except ValueError as e:
        raise RecordError(f"GET {url} did not answer JSON") from e


def answer_object(answer: object, request: str) -> dict[str, object]:
    if not is_json_object(answer):
        raise RecordError(f"{request}: the answer is not a JSON object")
    return answer


def mod_list(answer: object, request: str) -> list[object]:
    mods = answer_object(answer, request).get("mods")
    if not is_json_array(mods):
        raise RecordError(f"{request}: the answer has no list of mods")
    return mods


def mod_matches(mod: dict[str, object], slugs: set[str], terms: list[str]) -> list[str]:
    """The reasons (`slug` or the terms) a listing item is kept; empty means drop it."""
    reasons: list[str] = []
    names = {
        text(mod.get("urlalias")).lower(),
        *(s.lower() for s in string_list(mod.get("modidstrs"))),
    }
    if names & slugs:
        reasons.append("slug")
    # The fields the API's own search reads (search_mods, services/mod_api.py)
    fields = [text(mod.get(key)).lower() for key in ("name", "summary", "author")]
    fields += [tag.lower() for tag in string_list(mod.get("tags"))]
    reasons += [term for term in terms if any(term in field for field in fields)]
    return reasons


def trim_listing(answer: object, request: str, listing: dict[str, object]) -> object:
    slugs = {s.lower() for s in string_list(listing.get("keep_slugs"))}
    terms = [t.lower() for t in string_list(listing.get("keep_terms"))]
    kept: list[object] = []
    counts = {name: 0 for name in ["slug", *terms]}
    for mod in mod_list(answer, request):
        if not is_json_object(mod):
            continue
        reasons = mod_matches(mod, slugs, terms)
        if reasons:
            kept.append(mod)
            for reason in reasons:
                counts[reason] += 1
    per = ", ".join(f"{name!r}: {count}" for name, count in counts.items())
    print(f"{request}: kept {len(kept)} mods ({per})")
    if len(kept) < MIN_LISTING_MODS:
        raise RecordError(f"{request}: kept {len(kept)} mods, fewer than {MIN_LISTING_MODS}")
    return {**answer_object(answer, request), "mods": kept}


def listing_modids(answer: object, request: str) -> set[object]:
    return {mod.get("modid") for mod in mod_list(answer, request) if is_json_object(mod)}


def trim_subset(answer: object, request: str, keep: set[object]) -> object:
    mods = [m for m in mod_list(answer, request) if is_json_object(m) and m.get("modid") in keep]
    print(f"{request}: kept {len(mods)} mods of the recorded listing")
    return {**answer_object(answer, request), "mods": mods}


def trim_releases(answer: object, request: str, count: int) -> object:
    body = answer_object(answer, request)
    mod = body.get("mod")
    releases = mod.get("releases") if is_json_object(mod) else None
    if not is_json_object(mod) or not is_json_array(releases):
        raise RecordError(f"{request}: the answer has no mod with releases")
    return {**body, "mod": {**mod, "releases": releases[:count]}}


def key_paths(value: object, prefix: str = "") -> set[str]:
    """Every key path in a JSON value, list positions collapsed: `mod.releases[].fileid`."""
    paths: set[str] = set()
    if is_json_object(value):
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else key
            paths.add(path)
            paths |= key_paths(item, path)
    elif is_json_array(value):
        for item in value:
            paths |= key_paths(item, f"{prefix}[]")
    return paths


def field_report(request: str, old_file: Path, new: object) -> None:
    if not old_file.is_file():
        print(f"{request}: first recording")
        return
    try:
        old: object = json.loads(old_file.read_text(encoding="utf-8"))
    except ValueError:
        print(f"{request}: the old recording does not parse; first recording")
        return
    before, after = key_paths(old), key_paths(new)
    added, removed = sorted(after - before), sorted(before - after)
    if not added and not removed:
        print(f"{request}: no change in fields")
        return
    print(f"{request}:")
    for path in added:
        print(f"  + {path}")
    for path in removed:
        print(f"  - {path}")


def dump(value: object) -> str:
    return json.dumps(value, indent=1, ensure_ascii=False, sort_keys=False) + "\n"


def record(args: argparse.Namespace) -> None:
    manifest_path: Path = args.manifest
    out: Path = args.out or manifest_path.parent
    manifest, entries = read_manifest(manifest_path)
    base_url: str = (args.base_url or text(manifest.get("source")) or DEFAULT_SOURCE).rstrip("/")
    listing_rule = manifest.get("listing")
    listing: dict[str, object] = listing_rule if is_json_object(listing_rule) else {}

    only: list[str] = args.only or []
    unknown = sorted(set(only) - {entry.request for entry in entries})
    if unknown:
        raise RecordError(f"--only names requests the manifest does not have: {unknown}")
    selected = [entry for entry in entries if not only or entry.request in only]
    # The listing first, so a subset can be trimmed against the new listing
    selected.sort(key=lambda entry: entry.trim != "listing")

    answers: dict[str, object] = {}
    for index, entry in enumerate(selected):
        if index:
            time.sleep(args.pause)
        answers[entry.request] = fetch(base_url, entry.request, args.timeout)

    trimmed: dict[str, object] = {}
    listing_ids: set[object] | None = None
    for entry in selected:
        answer = answers[entry.request]
        if entry.trim == "listing":
            trimmed[entry.request] = trim_listing(answer, entry.request, listing)
            listing_ids = listing_modids(trimmed[entry.request], entry.request)
    for entry in selected:
        answer = answers[entry.request]
        match = RELEASES_FIRST.match(entry.trim)
        if entry.trim == "none":
            trimmed[entry.request] = answer
        elif entry.trim == "listing-subset":
            if listing_ids is None:
                listing_ids = recorded_listing_ids(entries, out)
            trimmed[entry.request] = trim_subset(answer, entry.request, listing_ids)
        elif match:
            trimmed[entry.request] = trim_releases(answer, entry.request, int(match.group(1)))

    today = datetime.now(UTC).strftime("%Y-%m-%d")
    for entry in selected:
        field_report(entry.request, out / entry.file, trimmed[entry.request])
    out.mkdir(parents=True, exist_ok=True)
    for entry in selected:
        (out / entry.file).write_text(dump(trimmed[entry.request]), encoding="utf-8")
        entry.raw["recorded"] = today
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", "utf-8")
    total = sum(
        (out / entry.file).stat().st_size for entry in entries if (out / entry.file).exists()
    )
    print(f"Recorded {len(selected)} of {len(entries)} requests; recordings total {total} bytes")


def recorded_listing_ids(entries: list[Entry], out: Path) -> set[object]:
    """The modids of the listing already recorded, for a subset recorded on its own."""
    for entry in entries:
        if entry.trim == "listing":
            path = out / entry.file
            try:
                answer: object = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as e:
                raise RecordError(f"the recorded listing {path} cannot be read: {e}") from e
            return listing_modids(answer, entry.request)
    raise RecordError("a listing-subset entry needs a listing entry in the manifest")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Record mod database answers for the E2E tests.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--out", type=Path, help="where to write (default: the manifest's directory)"
    )
    parser.add_argument("--base-url", help="default: the manifest's source")
    parser.add_argument("--only", action="append", metavar="REQUEST", help="repeatable")
    parser.add_argument("--pause", type=float, default=1.0, help="seconds between requests")
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args(argv)
    try:
        record(args)
    except RecordError as e:
        print(f"moddb-record: {e}; nothing was written", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
