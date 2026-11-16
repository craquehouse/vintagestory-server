# ModDB API fixtures

Trimmed `GET https://mods.vintagestory.at/api/mod/{key}` responses captured on 2026-11-09 for Story 14.0. They contain only public ModDB data.

Each mod keeps `modid`, `assetid`, `name`, `author`, `urlalias`, `side`, `type` and `lastreleased`. Each release keeps `releaseid`, `modversion`, `modidstr`, `filename`, `fileid`, `downloads`, `tags` and `created`, in the original newest-first order. Descriptions, screenshots, changelogs and CDN URLs were removed, except in `mod_betterruins.json`, which also keeps the entry's `screenshots` (unchanged) and `trailervideourl`.

| File | Source | Releases | Cases covered |
|---|---|---|---|
| `mod_carryon.json` | `carryon` | First 12 of 89 | Release order differs from version order (`2.0.0-rc.1`, then `1.14.3`, then `2.0.0-pre.8`); pre-release mod versions; releases tagged for 1.22 |
| `mod_instruments.json` | `instruments` | All 33 | One entry spanning three modids (`instruments`, `vsinstruments`, `vsinstrumentsbase`); `modversion` `1.0.1` repeated under different modids; `urlalias` is `null` |
| `mod_egocaribautomapmarkers.json` | `egocaribautomapmarkers` | All 24 | Repeated `filename` values (`Auto Map Markers.zip`); filenames with spaces; a second modid (`egocaribresinmapmarkers`); `urlalias` (`automapmarkers`) that does not resolve as a lookup key |
| `mod_playercorpse.json` | `playercorpse` | All 37 (captured 2026-11-13, Story 16.0) | Newest release (`1.12.0`) is tagged only up to `1.21.1`, so it is incompatible with 1.22.x; tags within a release are oldest first and include pre-releases (`1.21.1-rc.1`, `1.21.1-rc.2`) |
| `mod_canjewelry.json` | `canjewelry` | 9 of 179 (captured 2026-11-15, Story 17.1) | `fileid` null on three releases (with `filename` `""`); `changelog` null; a `null` in the entry's `tags` |
| `mod_betterruins.json` | `betterruins` | First 3 of 61 (captured 2026-11-16, Story 18.1) | 10 screenshots with CDN URLs and thumbnails; a file name with spaces (`Timeline 1_01_02_04_26.jpg`); a `youtube-nocookie.com/watch` trailer URL |
| `mod_not_found.json` | `maltiezfirearms` | None | A mod removed from ModDB: the response is `{"statuscode": "404"}` with no `mod` key |

ModDB returns `statuscode` as a string. See `agentdocs/vintagestory-modapi.md` for the API reference.
