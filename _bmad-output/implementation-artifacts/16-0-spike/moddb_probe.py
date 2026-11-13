"""Story 16.0 Task 3: probe the mod database for the most recent supported game version.

Read-only GETs against the public mod database (https://mods.vintagestory.at/api).
Run from the repository root with the standard library only:

    python3 -I _bmad-output/implementation-artifacts/16-0-spike/moddb_probe.py 1.22.7 \
        > _bmad-output/implementation-artifacts/16-0-spike/moddb_probe.out.txt

The version comparison deliberately mirrors `parse_base_version`/`is_prerelease`
in `api/src/vintagestory_api/services/mod_updates.py` (copied, not imported, so the
probe runs without the API environment). Story 16.3 reuses those helpers directly.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request

BASE = "https://mods.vintagestory.at/api"
MODS = ["playercorpse", "carryon", "instruments"]


def get(path: str) -> tuple[dict, float, int]:
    start = time.monotonic()
    req = urllib.request.Request(f"{BASE}{path}", headers={"User-Agent": "vss-story-16.0-probe"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = resp.read()
    return json.loads(body), time.monotonic() - start, len(body)


def is_prerelease(version: str) -> bool:
    return "-" in version


def parse_base_version(version: str) -> tuple[int, ...] | None:
    base = version.split("-", 1)[0]
    parts = base.split(".")
    if not base or not all(part.isascii() and part.isdigit() for part in parts):
        return None
    return tuple(int(part) for part in parts)


def sort_key(tag: str) -> tuple:
    """Order game version tags: base version, then stable above its pre-releases."""
    base = parse_base_version(tag) or ()
    return (base + (0,) * (4 - len(base)), 0 if is_prerelease(tag) else 1, tag)


def most_recent_supported(tags: list[str], include_prerelease: bool) -> str | None:
    candidates = [t for t in tags if parse_base_version(t) is not None]
    if not include_prerelease:
        candidates = [t for t in candidates if not is_prerelease(t)] or candidates
    return max(candidates, key=sort_key, default=None)


def main() -> None:
    installed = sys.argv[1] if len(sys.argv) > 1 else "1.22.7"
    out: list[str] = [f"Installed game version: {installed}", ""]

    listing, secs, size = get("/mods")
    mods = listing.get("mods", [])
    out.append(f"## Listing /mods: {len(mods)} items, {size / 1e6:.1f} MB, {secs:.1f}s")
    out.append(f"keys: {sorted(mods[0].keys())}")
    out.append(f"sample tags (categories, not game versions): {[m.get('tags') for m in mods[:3]]}")
    version_like = sum(
        1 for m in mods for t in (m.get("tags") or []) if parse_base_version(str(t)) is not None
    )
    out.append(f"listing tags that parse as versions: {version_like}")
    out.append("")

    versions, _, _ = get("/gameversions")
    gv = {v["name"]: v["tagid"] for v in versions.get("gameversions", [])}
    tagid = gv.get(installed)
    out.append(f"## /gameversions: {len(gv)} versions; tagid for {installed}: {tagid}")
    if tagid is not None:
        filtered, secs, size = get(f"/mods?gameversion={tagid}")
        n = len(filtered.get("mods", []))
        out.append(
            f"/mods?gameversion={tagid}: {n} mods, {size / 1e6:.1f} MB, {secs:.1f}s "
            "(one request answers 'has a release tagged for the installed version' for every listed mod)"
        )
    out.append("")

    for slug in MODS:
        detail, _, _ = get(f"/mod/{slug}")
        mod = detail.get("mod") or {}
        releases = mod.get("releases") or []
        out.append(f"## /mod/{slug}: {len(releases)} releases (publish order, newest first)")
        newest = releases[0] if releases else {}
        out.append(
            f"releases[0]: modidstr={newest.get('modidstr')} modversion={newest.get('modversion')} "
            f"tags={newest.get('tags')}"
        )
        out.append(f"  today's message names compatible_tags[:3] = {(newest.get('tags') or [])[:3]}")
        modids = sorted({r.get("modidstr") for r in releases if r.get("modidstr")})
        for modid in modids:
            own = [r for r in releases if r.get("modidstr") == modid]
            tags = [t for r in own for t in (r.get("tags") or [])]
            stable = most_recent_supported(tags, include_prerelease=False)
            any_ = most_recent_supported(tags, include_prerelease=True)
            installed_key = sort_key(installed)
            position = (
                "n/a" if stable is None
                else "same" if stable == installed
                else "behind" if sort_key(stable) < installed_key
                else "ahead"
            )
            out.append(
                f"  modid {modid}: {len(own)} releases; most recent supported "
                f"(stable preferred)={stable}, (any)={any_}; vs installed: {position}; "
                f"supports installed exactly: {installed in tags}"
            )
        out.append("")

    print("\n".join(out))


if __name__ == "__main__":
    main()
