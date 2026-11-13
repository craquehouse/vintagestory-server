# Story 16.0 Spike: UI Polish Questions

Evidence for `architecture/epic-16-ui-polish.md`. Run on 2026-11-13 against the dev stack (`just docker restart`, game 1.22.7 installed, server stopped) and the public mod database. Nothing was published, and no application code changed.

| File | What it is |
|---|---|
| `browse_probe.mjs` | Playwright probe of mod browser restoration (four return paths, Slow 4G, a search term, a stale return) and of every sort option |
| `browse_probe.out.json` | Output of `browse_probe.mjs` |
| `moddb_probe.py` | Standard-library probe of the mod database: listing fields, the `?gameversion=` filter, and the most recent supported game version per mod ID for `playercorpse`, `carryon` and `instruments` |
| `moddb_probe.out.txt` | Output of `moddb_probe.py 1.22.7` |
| `settings_shots.mjs` | Screenshots and card measurements of game server settings at 1024, 1440 and 1920px; masks the server name and password |
| `settings_shots.out.json`, `settings-*.png` | Output of `settings_shots.mjs` |

Rerun (dev stack running on port 8080; the browser scripts use the web package's Playwright, which needs `bunx playwright install chromium` once):

```bash
SP=_bmad-output/implementation-artifacts/16-0-spike
(cd web && bun ../$SP/browse_probe.mjs > ../$SP/browse_probe.out.json)
(cd web && bun ../$SP/settings_shots.mjs > ../$SP/settings_shots.out.json)
python3 -I $SP/moddb_probe.py 1.22.7 > $SP/moddb_probe.out.txt
```

Results depend on live data: the mod database changes daily, and the browse probe opens whichever card is mid-screen.

## 1. Browse restoration (ADR-1, `VSS-901`)

| Case | Page | Scroll | Opened card visible |
|---|---|---|---|
| Unfiltered, Back to Browse / breadcrumb / Browse tab / browser back | Restored (3) | Restored (1500) | Yes, at 150 ms, 1 s and 3 s |
| Unfiltered, Slow 4G, Back to Browse and browser back | Restored | Restored | Yes |
| Search "food", page 2, Back to Browse | Restored (2) | Restored (900) | No: search reset to empty, so page 2 of the unfiltered results |
| Stale: detour through Settings and Installed, then Browse tab | Restored (3) | Restored (1500) | Old position restored after the detour |

- On Slow 4G the returning grid renders from the React Query cache, so the 100 ms timeout is not racing the network on this path; a cold cache was not exercised.
- The gap is browse state, not timing. ADR-1 moves search, filters, sort and page into the URL and restores to the opened card only on a return from its detail page.

## 2. Sort options

| Sort | Request | Result |
|---|---|---|
| Newest | cached from the initial load | 20 of 9,560 |
| Most Downloaded | `page_size=20&sort=downloads` → 200 | 20 of 9,560 |
| Trending | `page_size=20&sort=trending` → 200 | 20 of 9,560 |
| Name (A-Z) | `page_size=1000` → 422, three times | No cards and no error message (`VSS-stm.1`) |

## 3. Most recent supported game version (ADR-2)

- Listing items carry category tags only: 0 of 9,560 parse as game versions.
- `?gameversion=<tagid>` for 1.22.7: 5,582 mods in one request (2.5 MB, 1.5 s); "any release tagged for this version". `get_mods_by_version` does not cache it. Browse cards stay unchanged (`VSS-4f3` records the option).
- Per mod ID: `playercorpse` 1.21.1 (behind; today's message names 1.21.0, 1.21.1-rc.1, 1.21.1-rc.2), `carryon` supports 1.22.7, `instruments` 1.18.6 / `vsinstruments` 1.19.3 / `vsinstrumentsbase` 1.21.6. Today's lookup for `instruments` evaluates `vsinstrumentsbase`'s release.
- New fixture: `api/tests/fixtures/moddb/mod_playercorpse.json`.

## 4. Settings layout (ADR-3)

- Cards are the full panel width at every size (768, 1184, 1664px); page height 1,984px everywhere.
- Empty settings show the text `null` (Description, Password, IP Address) and Password is a plain text field: `VSS-7ed`.
