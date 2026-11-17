# Epic 21: Maintainer Decisions and Web Polish - Architecture Decisions

Decisions from the Epic 21 course correction (2026-11-17). Epic 21 has no preparation story. Each fact was checked by reading or running the code at commit `05436da` (`main` after Epic 20, release `v0.1.0-rc.6`); file and line references are to that commit. Where a story has to confirm something first, the ADR says so.

The scope was approved by the maintainer before planning (Matt, 2026-11-17): five decisions of his own (the Renovate hold for uv, the commit type of image digest refreshes, a working `VS_LOG_LEVEL`, the mod remove dialog, Prettier for the web) and fourteen beads. Those five are marked "Matt, 2026-11-17" and are not open. What the planner decided inside them, and for the beads, is marked "Planner" and listed as open questions in the change proposal (section 5), each with a default the stories follow unless he says otherwise.

| Story | ADRs |
|---|---|
| 21.1 The Web Is Formatted Once and Stays Formatted | ADR-1 |
| 21.2 Renovate: the uv Hold and Digest Refreshes | ADR-2, ADR-3 |
| 21.3 A Working `VS_LOG_LEVEL` and Config Viewer Edge Cases | ADR-4, ADR-5 |
| 21.4 The Mod Remove Dialog Waits, and One Toast per Failure | ADR-6, ADR-7 |
| 21.5 Version Sort, Sort State for Screen Readers and Close Buttons | ADR-8, ADR-9 |
| 21.6 Mod Detail Page Polish | ADR-10, ADR-11 |
| 21.7 Tabs and Tables on Phones | ADR-12, ADR-13 |
| 21.8 Sidebar Default and Content Width | ADR-14, ADR-15 |

## Facts Checked in the Code

**Web formatting today.**

- The web has no formatter and no linter of its own: `web/package.json` has no Prettier or ESLint dependency; its `lint` script is `tsc --noEmit` and its `typecheck` script is `tsc --noEmit && tsc --noEmit -p e2e/tsconfig.json`. `just lint-web` runs `bun run lint` (`Justfile:171-172`), so it repeats part of `just typecheck-web`.
- `just format-web` runs `bunx prettier --write "src/**/*.{ts,tsx,css,json}"` (`Justfile:231-232`): whatever Prettier version `bunx` fetches, with no configuration, over `src` only. `just format` is `format-api format-web` (`:224`).
- CI's `web` job runs `just install-web --frozen-lockfile`, `just typecheck-web`, `just test-web` and `just build-web` (`.github/workflows/ci.yml:42-45`). It does not run `just lint-web`. `scripts/tests/test-release.sh:321-324` pins the job names and each job's `if:`, not the steps.
- Tracked web files: 197 `.tsx`, 117 `.ts`, 15 `.json`, 1 `.css`, 1 `.html`, 1 `.md`. Of the JSON files, 11 are in `web/e2e/fixtures/` (1.2 MB): the seeded `serverconfig.json`, and the recorded mod database answers with their manifest in `moddb/`, written by `just record-moddb`.
- Style of the existing code, measured over the 311 `.ts` and `.tsx` files in `src`, `e2e` and `tests` (87,654 lines):
  - Quotes: 1,108 import lines use single quotes and 131 double; 258 files import with single quotes and 35 with double (18 of the 35 are the shadcn files in `src/components/ui`, 6 are in `src/components/layout`, 5 in `src/contexts`).
  - Semicolons: 1,182 import lines end with one and 57 do not.
  - Width: 4,032 lines are longer than 80 characters, 325 longer than 100, 68 longer than 120.
  - Indentation is two spaces everywhere (no tab). Single arrow parameters are always in parentheses (496 to 0).
- Prettier 3.10.1 (the current release), run on a copy of the tree with no configuration file:

  | Options | Files changed | Lines removed / added |
  |---|---|---|
  | Defaults (double quotes, width 80, trailing commas `all`), fixtures included | 318 of 332 | 61,170 / 59,246 |
  | `singleQuote`, `printWidth: 100`, `trailingComma: all`, fixtures included | 265 | 46,056 / 35,704 |
  | `singleQuote`, `printWidth: 100`, `trailingComma: es5`, fixtures included | 242 | 45,103 / 34,737 |
  | The same with width 90, 110, 120 | 256, 261, 266 | |
  | **`singleQuote`, `printWidth: 100`, `trailingComma: es5`; fixtures, Markdown and HTML ignored** | **231 of 319** | **5,888 / 3,826** |

  The two largest fixtures alone account for 53,934 changed lines, so they must be ignored. With the chosen options the 231 files are 213 in `src` (all 23 files of `src/components/ui` among them), 17 in `e2e` and `vitest.config.ts`; nothing in `tests` changes. After `--write`, `--check` reports every file as formatted. The maintainer's figure of 279 files is the old recipe's glob (`src` only, 284 files) with defaults.
- `.git-blame-ignore-revs` exists since Story 20.1 with one entry (`da33a55`, the API reformat). `scripts/worktree-setup.sh:95-96` sets `blame.ignoreRevsFile` to `:(optional).git-blame-ignore-revs` when Git accepts the prefix, and `README.md:106` explains it.
- The Dockerfile's `web-build` stage runs `bun install` and the build; a dev dependency is installed there and is not copied into the final image.

**Renovate today.**

- `renovate.json` extends `local>craquehouse/renovate-config` and has three `packageRules`; the third (`:27-36`) groups `uv` and `ghcr.io/astral-sh/uv`, types the group `chore(uv)` and sets `minimumReleaseAge: null` (`:32`), which Story 20.7 added.
- The organisation preset (`craquehouse/renovate-config` at `021869b`, read with `gh api` on 2026-11-17):
  - `autoMerge.json5` holds every `mise` manager update for one day (`minimumReleaseAge: "1 day"`), so that release assets have settled before `mise lock` records them. This repository has no `mise.lock`.
  - `semanticCommits.json5` types updates by update type: `major` is `feat` with a `!`, `minor` is `feat`, `patch` is `fix`, and **`digest` is `fix`**. Every `docker` datasource update gets the scope `container` and the topic `image <name>`. So a digest refresh of a Dockerfile image under an unchanged tag is committed as `fix(container): update image <name> digest (<old> → <new>)`. `pinDigest` is not typed by any rule of the preset.
  - No rule of the preset auto-merges or holds `docker` datasource updates.
- `cliff.toml:47-50` turns every `feat`, `fix` and `perf` commit into a release note and skips every other type; the scope `container` is not one of the three shown scopes, so such a note reads "Update image ... digest (...)" with no prefix. Since Story 20.7 all three Dockerfile images carry a digest (`Dockerfile:9`, `:36`, `:52`), so base image rebuilds now arrive as digest pull requests.
- GHCR gives Renovate no release timestamps, so the image half of a uv update cannot be aged (Story 20.7 Dev Notes). With the hold on the `.mise.toml` half only, the group opens with the Dockerfile half alone.
- `scripts/tests/test-docker-context.sh:32-35` fails when the uv image tag in the Dockerfile differs from the uv version in `.mise.toml` (0.13.8 in both today).
- `RELEASING.md:57` says "Renovate updates uv in `.mise.toml` and the Dockerfile in one pull request", and `:71` says Renovate moves the pins.
- Pull request #185 (`chore(uv): Update uv (0.13.8 → 0.13.9)`, opened 2026-11-17) is the first uv update under the current rule and holds both halves.
- A copy of `renovate.json` with the uv rule's `minimumReleaseAge` removed and a fourth rule (`matchManagers: ["dockerfile"]`, `matchUpdateTypes: ["digest", "pinDigest"]`, `semanticCommitType: "chore"`) validates: Renovate 44.251.0, `renovate-config-validator --no-global renovate.json`, "Validating renovate.json as repo config", "Config validated successfully against 1 file(s)", exit 0.

**Logging today.**

- `Settings.log_level: str | None = None` (`api/src/vintagestory_api/config.py:40`) is read from `VS_LOG_LEVEL` and used nowhere.
- The level is set by `initialize_debug_state()` (`config.py:312-325`), which the lifespan calls first (`main.py:160`). It reads `VS_DEBUG` from the environment itself (`_read_debug_from_env`, `:301-309`: `true`, `1` or `yes`) and calls `configure_logging(debug=...)` with no level. `main.py:170` does not set the level; it writes `"DEBUG" if debug_enabled else "INFO"` into the `api_starting` log line.
- `configure_logging(debug, log_level)` (`config.py:371-433`) already takes a level and falls back silently when `getattr(logging, ...)` finds none (`:392-397`). `debug` also picks the renderer: the console renderer in debug mode, JSON otherwise (`:407-433`).
- The debug state can be changed at run time: `POST /api/v1alpha1/debug/enable` and `/disable` (`routers/debug.py:38-75`, Admin only, FR48) call `set_debug_enabled` (`config.py:337-356`), which calls `configure_logging(debug=enabled)`. The web's API Settings panel has the switch (`web/src/hooks/use-debug.ts`). `reconfigure_logging_if_changed` (`:439-470`) does the same from the stored state.
- `Settings.debug` is parsed by pydantic (which also accepts `on`, `t`, `y`), and decides the documentation pages, the test routes and the plain-HTTP `VS_MOD_DB_URL`. So `VS_DEBUG=on` serves the documentation pages while logging stays at INFO in JSON.
- A setting that must stop start-up on a bad value is a plain `str` with a `field_validator` that raises `ValueError` naming the variable (`validate_csp_mode`, `config.py:121-133`); `hide_input_in_errors=True` (`:37`) keeps the value out of the error.
- `VS_LOG_LEVEL` is not in the README's configuration table (`README.md:76-90`), not in `.env.example`, and not in any compose file. `project-context.md:398-400` describes it as working. `architecture/project-structure-boundaries.md:488` records that nothing reads it.
- The image starts uvicorn with no `--log-level` (`Dockerfile:92`); uvicorn's own log lines are not structlog's.

**Config file viewer today (`VSS-wv0w`).**

- `services/game_config.py:238` lists two Discord hosts for redaction (`discord.com`, `discordapp.com`); `services/mod_update_alerts.py:20-22` lists four for the webhook sender (the same two plus `ptb.discord.com` and `canary.discord.com`). Neither module imports the other.
- `ConfigFilesService._role_may_open` returns `True` for Admin before it compares the path with the server data directory (`services/config_files.py:230-231`), and `list_directories` filters entries only through it (`:292-296`). So an Admin listing shows a directory symlink that resolves outside the data directory; opening it is refused by `_safe_path` (`:185-221`) with 400.
- `list_directories` and `list_files` return an empty list when the server data directory does not exist (`:282-284`, `:326-328`), before `_target_directory` makes the role check (`:253-254`). `_safe_path` resolves a path that does not exist, so the check can run first.

**Mod removal and error toasts today.**

- `ModTable` holds one `useRemoveMod()` (`web/src/components/ModTable.tsx:130`) and takes `isPending` from it as `isRemoving`, which the confirm button shows for whichever mod's dialog is open (`:458-465`).
- The confirm button is Radix's `AlertDialogAction` (`:453-457`), which closes the dialog on click; `onOpenChange` then clears `modToRemove` (`:436-437`, `:240-242`). The DELETE runs after the dialog has closed.
- `useRemoveMod` removes the mod from the cached list at once and restores it on error (`web/src/hooks/use-mods.ts:218-258`); its hook-level `onError` calls `handleApiError`, which shows one toast.
- `UninstallConfirmDialog` (`web/src/components/UninstallConfirmDialog.tsx:66-123`) uses plain buttons inside the alert dialog: Cancel and confirm are disabled while `isPending`, and the page closes the dialog in the mutation's `onSuccess` (`features/game-server/VersionPage.tsx:73-87`). It passes `onOpenChange` straight through, so Escape still closes it while the request runs.
- The query client's default mutation `onError` shows a toast through `handleApiError` (`web/src/api/query-client.ts:34-39`). In TanStack Query v5 a hook's own `onError` replaces that default, and an `onError` passed to `mutate` runs in addition to whichever of the two applies. The rule is written in three code comments (`use-mods.ts:155`, `:204`, `:250`) and not in `project-context.md`.
- Hooks with no `onError` of their own, whose callers show a toast of their own (found by reading; `VSS-oc28` saw the first in the browser):

  | Hook | Caller's toast | Toasts on failure |
  |---|---|---|
  | `useInstallMod` (`use-mods.ts:88-98`) | `InstallConfirmDialog.tsx:117-122` "Installation failed" | 2 (`VSS-oc28`) |
  | `useRestartServer` (`use-server-status.ts:158`) | `ServerControls.tsx:90` "Failed to restart server" | 2 |
  | `useInstallServer` (`use-server-status.ts:188`) | `QuickInstallButton.tsx:93`, `InstallVersionDialog.tsx:209`, `ServerInstallCard.tsx:52` | 2 |
  | `useUninstallServer` (`use-server-status.ts:283`) | `VersionPage.tsx:82` "Failed to remove server" | 2 |
  | `useSetModUpdateWebhook` (`use-api-settings.ts:144`) | `ModUpdateWebhookSetting.tsx:41` "Update failed" | 2 |

  `useStartServer` and `useStopServer` have a hook-level `onError` that only rolls back (`:96`, `:140`), so their callers' toast is the only one. `useCheckModUpdates` and `useApplyAllModUpdates` silence the default with `onError: () => {}` and say so (`use-mods.ts:367-375`, `:420-427`).

**Tables and dialogs today.**

- The installed mods Version column has no `sortFn` (`ModTable.tsx:271-282`). TanStack Table 9.3.1's `alphanumeric` function, run on sample values, gives `1.0.0, 1.0.0-pre.1, 1.0.0-rc.2, 1.0.0-rc.12, 1.0.1, 1.9.0, 1.10.0, 1.22.0, 1.22.0-rc.1`: numbers compare as numbers, and a release comes before its pre-releases (`VSS-qxxo`). The cards below 1024px use the same rows (`:408`).
- The Version page's Version column asks for `sortFn: 'alphanumeric'` (`VersionTable.tsx:161`) and has the same fault. `VersionTable.tsx:76-101` has a private `compareVersions`, used only to mark newer versions (`:314`): it puts a pre-release before its release but compares pre-release parts with `localeCompare`, so `rc.12` sorts before `rc.2`.
- No `semver` package is a dependency of the web.
- `SortableHeader` (`ModTable.tsx:90-112`) is a button inside the header cell with a chevron and no `aria-sort` on the `th`. `VersionTable.tsx:355-381` sets `aria-sort` to `ascending` or `descending` and leaves it off when the column is not sorted. No other table sorts (`JobsTable` has no sort).
- `VersionTable.tsx:352` and `:407` read `columnDef.meta` through `as { className?: string }`. `web/src/lib/table-column-meta.d.ts` types `ColumnMeta.className` since Story 18.4, and `ModTable.tsx:380` and `:393` read it with no cast.
- The dialog close button is a 16px icon with no size of its own at `top-4 right-4` (`web/src/components/ui/dialog.tsx:72-78`); the sheet's close button is the same (`ui/sheet.tsx:73-76`). The sheet is the phone navigation menu (`components/layout/Layout.tsx:24-32`). Alert dialogs have no close button.

**Mod detail page today.**

- Nine links in the web open a new tab. Four say so: the trailer link (`ModDetailPage.tsx:729-739`, a hidden `OPENS_IN_NEW_TAB` span) and three with "(opens in new tab)" in an `aria-label` (`VersionCard.tsx:80`, `VersionTable.tsx:154`, `ModCard.tsx:187`). Five do not: ModDB Page, Homepage and Source on the mod detail page (`ModDetailPage.tsx:693-726`), the link at `InstalledModParts.tsx:43` and the one at `layout/Sidebar.tsx:210`.
- Description links get `target="_blank"` from the sanitizer hook; HTML links also get a hidden note and, by CSS, an icon (`web/src/lib/mod-description.ts:61-81`, `styles/index.css:248-260`). SVG links get neither (`mod-description.ts:11`).
- The header is one `flex gap-6` row (`ModDetailPage.tsx:612`) of a 128px logo (`:616`), a `flex-1` info column and a `w-64` install card (`:229`, `:404`); nothing wraps. `VSS-pzj8` measured the page at 674px wide in a 390px viewport.
- The description container has the classes `mod-description prose prose-sm prose-invert max-w-none` (`:784`). `@tailwindcss/typography` is not installed (`web/package.json`), so the three `prose` classes do nothing, and Tailwind's base styles remove heading sizes, list markers and link colours. `prose-invert` would also be wrong in the light theme. The sanitizer keeps inline `style` attributes and removes `<style>` and form elements (`mod-description.ts:88-90`).

**Tabs, tables and layout today.**

- `TabsList` is `h-9` with 3px padding and `TabsTrigger` is `h-[calc(100%-1px)]` (`web/src/components/ui/tabs.tsx:27`, `:43`), about 30px. Three tab lists use them: Settings (`features/settings/SettingsPage.tsx:46-65`), Mods (`features/mods/ModsPage.tsx:101-121`) and the Version page's channel filter (`components/ChannelFilter.tsx`).
- The project's touch target pattern is a 44px minimum below `lg`: `max-lg:h-11` (`features/mods/InstalledTab.tsx:98`, `:109`), `min-h-11` on the cards (`InstalledModCard.tsx:52`, `:78`).
- The Settings tab list gains its fourth trigger after `useAuthMe` resolves (`SettingsPage.tsx:35-36`, `:59-64`). `VSS-vt4` reproduced lost arrow key presses in the first 400ms with scripted key presses in Chromium and asks for a check with a real keyboard.
- `JobsTable` has four columns (Job Name, Schedule, Next Run, Status; `components/JobsTable.tsx:74-99`) and needs 523px; `VersionTable` has five (Version, Channel, Size, Status, Actions) with Size already hidden below `sm` (`VersionTable.tsx:191-193`) and needs 361px. The shared `Table` wraps itself in `overflow-x-auto` (`components/ui/table.tsx:9`), so a wide table scrolls inside itself (`VSS-f9y`). Story 17.8 measured the Dashboard, the console and the mod browser only at 1920px.
- The sidebar state is `preferences.sidebarCollapsed`, a boolean that defaults to `false` (`web/src/contexts/PreferencesContext.tsx:40`, `:49`). The provider writes the cookie `vs_ui_prefs` whenever the preferences change, the first render included (`:169-171`), so every browser that has opened the app stores `sidebarCollapsed: false` whether or not the user ever chose. A stored `true` can only come from a choice.
- The sidebar is 160px, or 64px collapsed (`layout/Layout.tsx:19`), fixed from `md` up (`:36`); below `md` the same `Sidebar` is shown in a sheet (`:24-32`) and reads the same collapsed state. UI Preferences has a switch "Start with Sidebar Collapsed" on the same boolean (`features/settings/UIPreferencesPanel.tsx:129-137`). `MD_UP_QUERY` and `LG_UP_QUERY` exist (`web/src/hooks/use-media-query.ts:11`, `:17`).
- The UX spec asks for a collapsed sidebar by default from 768 to 1023px (`ux-design-specification.md:1209-1211`), a "full-width console" at tablet width (`:1214`), and a 1280px maximum content width, centered (`:1254-1258`).
- `Layout` puts every page in `<div className="p-4 md:p-6">` with no maximum (`Layout.tsx:46-50`). Only Game Settings is capped, by `SETTINGS_CONTENT_WIDTH = 'mx-auto max-w-[1280px]'` (`features/game-server/content-width.ts`). The mod browser grid has at most four columns, chosen by viewport width (`components/ModBrowseGrid.tsx:41`: `xl:grid-cols-4`), so a 1280px cap keeps four columns and makes each about 308px wide where it is about 416px at 1920px today. The mod detail page caps itself at `max-w-4xl` (`ModDetailPage.tsx:577`).

## ADR-1: The Web Is Formatted Once with Prettier, in One Commit, and the Check Keeps It So

**Status:** Accepted (Matt, 2026-11-17): Prettier as a pinned dev dependency, one dedicated commit, first among the web stories, in `.git-blame-ignore-revs`, a check in `just lint-web`. The options and the covered files (decisions 2 to 4, 7) are the planner's, from the measurements above. Implemented by Story 21.1.

**Context:** Epic 20 ADR-1 formatted the API once and left the web out. The web has 319 files Prettier could format and no agreed style on paper, although the code is consistent: single quotes, semicolons, two spaces, lines mostly under 100 characters. `just format-web` runs an unpinned Prettier with defaults, which would rewrite almost every file into a style the code does not use.

**Decision:**

1. **Prettier is a dev dependency of the web, pinned to an exact version** (3.10.1 today; the story takes the current release), in `web/package.json` and `web/bun.lock`. Exact, not a range: a formatter's output can change between versions, and the check must give the same answer for everyone. Renovate proposes updates; an update that changes the output is completed in its pull request by running `just format-web`.
2. **The configuration is `web/.prettierrc.json` with three options:** `singleQuote: true`, `printWidth: 100`, `trailingComma: "es5"`. Everything else is Prettier's default, which is what the code already does (semicolons, two spaces, parentheses around a single arrow parameter). These options are the ones that change the fewest files and lines of all combinations measured, and 100 is the API's line length too.
3. **It covers every `.ts`, `.tsx`, `.css` and `.json` file under `web/`** that is tracked: `src`, `e2e`, `tests` and the configuration files at the top (`package.json`, `tsconfig.json`, `components.json`, the Vite, Vitest and Playwright configurations). The shadcn files in `src/components/ui` are included: one style for the whole tree, and a file the shadcn CLI adds later is formatted by `just format-web`.
4. **`web/.prettierignore` leaves out** `e2e/fixtures/` (recorded answers, written by a script; reformatting them would change 54,000 lines and fight the recorder), Markdown and HTML files (prose and the one page shell; not code style), `public/`, and the output directories Prettier would not otherwise skip (`playwright-report*/`, `test-results*/`, `coverage/`, `dist/`).
5. **One commit reformats the web** (Matt, 2026-11-17): `prettier --write .` in `web/`, after the commit that adds the dependency, the configuration and the ignore file. The format commit holds nothing else: no hand edit, no configuration change. Its subject is `chore(story-21.1/task-2): format the web with prettier`. It is expected to touch about 231 files (about 5,900 lines removed, 3,800 added).
6. **It is its own story and pull request, and it merges before any other web branch of the epic is cut** (Matt, 2026-11-17), as Story 20.1 did. The review reproduces the commit (check out its parent, run the same command, compare the trees) and confirms that the type check, the unit tests and the build give the same results before and after.
7. **The commit's hash is added to `.git-blame-ignore-revs`** with a comment line, in a later commit of the same pull request. Nothing else is needed: the `:(optional)` setting from Story 20.1 already points at the file.
8. **`just lint-web` becomes the format check** (`prettier --check .` through a `format:check` script), replacing the `tsc --noEmit` it shares with `just typecheck-web`. **CI's `web` job gains `just lint-web`**, since it does not run it today. `just format-web` runs the pinned Prettier through a `format` script over the same files. `just check` reaches the check through `just lint`.
9. **The type check and the tests must give the same results after the format.** No `// prettier-ignore` is added in the format commit. If a file cannot be formatted without changing behaviour (none is expected), the story stops and reports it.

**Consequences:**

- From Story 21.1 on, every web commit is formatted, so `just format-web` is safe to run and a pull request with an unformatted file fails.
- `just check` type-checks the web once, not twice.
- Any web branch cut before Story 21.1 merges must be rebuilt on top of it; none is open.
- One new dev dependency. It is installed in the image's build stage and is not part of the final image.

## ADR-2: The uv Update Keeps the Preset's One-Day Hold

**Status:** Accepted (Matt, 2026-11-17). Implemented by Story 21.2. Replaces the `minimumReleaseAge: null` that Story 20.7 added (Epic 20 ADR-10 decision 3 is otherwise unchanged).

**Context:** Story 20.7 cleared the preset's one-day hold for uv so that both halves of a uv update (the Dockerfile image and the `.mise.toml` tool) open together, and asked the maintainer whether he preferred the hold. He does: the hold is the organisation's rule for every mise tool, and a day's wait costs nothing.

**Decision:**

1. **`minimumReleaseAge: null` is removed from the uv rule** in `renovate.json`. The grouping and the `chore(uv)` type stay.
2. **What then happens is documented, not worked around.** The `.mise.toml` half is held for one day by the preset; the Dockerfile half cannot be aged (GHCR gives no timestamps) and is ready at once. A uv pull request therefore opens with the Dockerfile half only, and `scripts/tests/test-docker-context.sh` fails it (the uv tag differs from `.mise.toml`) until Renovate adds the `.mise.toml` half about a day later.
3. **The rule's `description` and `RELEASING.md` say so:** a uv pull request is red for about its first day, that is expected, and it must not be merged until it holds both files and CI is green. `RELEASING.md:57` is rewritten accordingly.
4. **The script test is not relaxed.** It is what keeps a one-file uv update from being merged.
5. **The file is validated** with `renovate-config-validator --no-global`, run from a directory outside the repository as in Story 20.7.

**Consequences:**

- Each uv update shows a failing pull request for about a day. Nothing merges it automatically.
- uv follows the same hold as every other mise tool of the organisation.
- If the group behaves differently in practice (for example the half that is held never joins), the story records what Renovate did on the first update after the change and the maintainer decides again.

## ADR-3: A Digest Refresh of a Dockerfile Image Is `chore(container)`

**Status:** Accepted (Matt, 2026-11-17). The rule's form is the planner's. Implemented by Story 21.2.

**Context:** Since Story 20.7 the three Dockerfile images are pinned by digest, so a rebuild of a base image under the same tag arrives as a pull request. The preset types every `digest` update `fix`, so each rebuild would add a line such as "Update image node digest (e6bedef → 1a2b3c4)" to the release notes, which tells a user nothing.

**Decision:**

1. **One more `packageRules` entry in `renovate.json`:** `matchManagers: ["dockerfile"]`, `matchUpdateTypes: ["digest", "pinDigest"]`, `semanticCommitType: "chore"`, with a description. Repository rules are applied after the preset's, so it wins over the preset's `digest` rule; the preset's scope (`container`) and topic are kept, giving `chore(container): update image <name> digest (...)`.
2. **`pinDigest` is named too** although the preset does not type it, so that the result does not depend on Renovate's default.
3. **A version change is not touched:** a new tag is a `patch`, `minor` or `major` update even though the digest moves with it, so it keeps the preset's `fix(container)` or `feat(container)` and its release note.
4. **The rule is limited to the Dockerfile manager.** GitHub Actions digests are already `ci` by the preset.
5. **Validated** with the same validator run as ADR-2.

**Consequences:**

- Base image rebuilds are still proposed, built and tested by CI; they no longer appear in the release notes.
- A release that contains only digest refreshes has no note for them. The image's SBOM and provenance still describe exactly what it was built from.

## ADR-4: `VS_LOG_LEVEL` Sets the Level at Start-Up, the Debug Switch Still Means DEBUG, and a Bad Value Stops Start-Up

**Status:** Accepted (Matt, 2026-11-17) for the setting, its four values, the unchanged default and the start-up error. The precedence against the run-time debug switch (decision 3) and decision 6 are the planner's (open question 1). Implemented by Story 21.3.

**Context:** `Settings.log_level` has existed since Epic 1 and `project-context.md` describes it as working, but nothing reads it. An operator who wants fewer log lines in production, or debug lines without the rest of debug mode (the API documentation pages, the test routes), has no way to ask.

**Decision:**

1. **The value is validated when the settings are read.** A `field_validator` on `log_level` strips and upper-cases it; blank means unset; anything but `DEBUG`, `INFO`, `WARNING` or `ERROR` raises `ValueError("VS_LOG_LEVEL must be one of: DEBUG, INFO, WARNING, ERROR.")`. The field stays `str | None`, like `csp_mode`, so the error names the variable, and the settings are built at import (`main.py:420`), so the API does not start.
2. **At start-up the level is `VS_LOG_LEVEL` when it is set.** When it is not, it is DEBUG with `VS_DEBUG=true` and INFO otherwise, as today. `VS_LOG_LEVEL` changes the level only: `VS_DEBUG` still decides the renderer (console or JSON), the documentation pages, the test routes and whether a plain-HTTP `VS_MOD_DB_URL` is accepted. `VS_DEBUG=true` with `VS_LOG_LEVEL=WARNING` is debug mode with quiet logs.
3. **The run-time debug switch keeps its meaning.** Turning debug logging on (`POST /debug/enable`, the web's switch) sets DEBUG. Turning it off returns to the configured level: `VS_LOG_LEVEL` when set, INFO otherwise. A switch named "debug logging" that produced no debug lines because of an environment variable would be a trap; and the most recent explicit instruction wins. The response shapes of the three `/debug` routes do not change.
4. **Where it is done:** the lifespan passes `settings.log_level` to `initialize_debug_state` (`config.py:312`), which remembers it; `set_debug_enabled` and `reconfigure_logging_if_changed` use it; `configure_logging` keeps its signature. The `api_starting` line (`main.py:167-172`) reports the level actually set.
5. **Only structlog's level changes.** uvicorn's own lines are not affected, and the README says so in one sentence.
6. **The debug state is initialised from `settings.debug`,** not from a second reading of the environment, so `VS_DEBUG=on` means the same thing for logging as for everything else.
7. **Documentation:** a `VS_LOG_LEVEL` row in the README's configuration table, an entry in `.env.example`, the environment table in `architecture/project-structure-boundaries.md` (which says today that nothing reads it), and the Logging section of `project-context.md`.
8. **Tests:** each of the four values in mixed case; blank and unset; an invalid value (the error names the setting and not the value); the level with and without `VS_DEBUG`; the switch on and off with and without `VS_LOG_LEVEL`.

**Consequences:**

- One release note: `feat(api): VS_LOG_LEVEL sets the log level`.
- A deployment that already sets `VS_LOG_LEVEL` to a valid value will now get that level. One that sets an invalid value (for example `warn` or `trace`) will not start, and the error says why. No compose file or example in the repository sets it. The change is not marked breaking (open question 2).

## ADR-5: Config Viewer Edge Cases: One List of Discord Hosts, No Listing Outside the Data Directory, and the Role Check First

**Status:** Proposed by the planner; no open question. Implemented by Story 21.3 (`VSS-wv0w`). Completes Epic 19 ADR-2 and ADR-3.

**Decision:**

1. **One set of Discord hosts.** The redaction rule and the webhook sender use the same four hosts (`discord.com`, `discordapp.com`, `ptb.discord.com`, `canary.discord.com`), defined once; `is_secret_value` matches them as it does today (host equal to one of them, path starting with `/api/webhooks/`). Where the set lives is the story's choice; it must not create an import cycle.
2. **A directory listing shows only entries that resolve inside the server data directory, for every role.** The containment check is made before the Admin shortcut, in the listing of directories and of files. What Admin may open does not change: the read path already refuses such a path with 400.
3. **The path and role checks run before the "data directory does not exist" shortcut.** A key that is not Admin asking for a directory it may not list gets 403 `FORBIDDEN` whether or not the data directory exists; a traversal gets 400. An allowed request still gets an empty list when the directory is missing.
4. **Tests** for each: the two added hosts with and without the webhook path; a directory symlink and a file symlink pointing outside, as Admin and as Monitor; the missing data directory with an allowed and a forbidden directory for both roles.

**Consequences:**

- Three small corrections to responses (listed in the change proposal), in two commits with a release note each: `fix(api): hide Discord webhook URLs on ptb and canary hosts from read-only keys`, and `fix(api): leave links that point outside the data directory out of the config file listing` (which also holds the 403 correction; the web UI never asks for a forbidden directory, so no user of it sees that one).

## ADR-6: The Remove Dialog Stays Open Until the Removal Finishes, and Its Pending State Belongs to One Mod

**Status:** Accepted (Matt, 2026-11-17) for the behaviour after confirm. What happens on an error and during the wait (decisions 3 to 5) is the planner's (open question 3). Implemented by Story 21.4.

**Decision:**

1. **The confirm button no longer closes the dialog.** It becomes a plain destructive button, as in `UninstallConfirmDialog`. After a click the dialog stays open, the button shows a spinner and "Removing...", and both buttons are disabled.
2. **The dialog closes when the DELETE succeeds,** and `onRemoved` runs as today.
3. **On an error the dialog stays open and the confirm button is enabled again** with its normal label. The error is shown by one toast (the hook's `handleApiError`, unchanged). The user can try again or cancel. Closing on error, as today, would hide the dialog at the moment the user needs to decide; keeping it open matches `UninstallConfirmDialog` and `InstallConfirmDialog`.
4. **While the removal runs the dialog cannot be dismissed:** Cancel is disabled and Escape is ignored (the `onOpenChange` guard). A dialog that could be closed would let a second removal start while the first runs.
5. **The pending state is tracked per mod:** the dialog is pending when the mutation is pending and its `variables` (the slug being removed) equal the slug of the mod the dialog is for. This is the pattern `isTogglingMod` uses (`ModTable.tsx:244-249`). A dialog for another mod never shows "Removing...".
6. **The optimistic removal in `useRemoveMod` is unchanged:** the row disappears behind the dialog at once and returns on error. The dialog's text comes from the component's own state, not from the list, so it keeps the mod's name.
7. **`UninstallConfirmDialog` gets the same Escape guard,** since it is the model and has the gap (found in planning).
8. **Tests:** unit tests with a mutation that is held open (the dialog stays, the label, both buttons disabled, Escape ignored), that succeeds (closes, `onRemoved` once), and that fails (stays open, button enabled, one toast, the mod is back in the list); a second mod's dialog after a failure shows "Remove". One E2E, in the stubbed read-only style of `installed-mods-phone.spec.ts`: the DELETE is answered by `page.route` after a delay, once with success and once with an error; nothing is removed from the stack.

**Consequences:**

- One release note: `fix(web): the remove mod dialog stays open until the mod is removed`.
- The user waits in the dialog for the length of one request (normally well under a second).

## ADR-7: A Failed Mutation Shows One Toast: the Caller's, with the Hook's Default Silenced

**Status:** Proposed by the planner (open question 4 for the four hooks beyond the bead). Implemented by Story 21.4 (`VSS-oc28`).

**Context:** The client's default `onError` shows a generic "Error" toast. A caller that passes its own `onError` to `mutate` shows a second, specific one. Five hooks have this combination (facts above); the bead names one.

**Decision:**

1. **The rule:** a mutation's failure is reported once. When the callers report it with a specific title, the hook declares its own `onError` that shows nothing, with a comment saying the callers report the error. This is the existing form of `useCheckModUpdates` and `useApplyAllModUpdates`. Because a hook-level `onError` replaces the client default, nothing else changes.
2. **Applied to all five hooks:** `useInstallMod` (the bead), and `useRestartServer`, `useInstallServer`, `useUninstallServer` and `useSetModUpdateWebhook`, which have the same fault. Each of their callers already shows a toast with a specific title and the error's message; every caller is checked so that none is left with no toast.
3. **The specific toast is the one kept,** not the generic one: "Installation failed" says more than "Error". The message text is the same in both.
4. **Not chosen: moving the default into a `MutationCache` handler with an opt-out flag.** It would remove the replace-the-default trap for good, but it changes how every hook reports errors (the hooks that call `handleApiError` themselves would then show two toasts until each is edited) for a fault that five one-line changes fix.
5. **The rule goes into `project-context.md`** (it is only in code comments today): a hook-level `onError` replaces the client default; an `onError` passed to `mutate` runs in addition; so a hook either reports the error itself or silences the default and leaves the report to its callers, never both.
6. **Tests:** for each of the five, a failing request produces exactly one error toast.

**Consequences:**

- Two release notes, one per commit: `fix(web): a failed mod install shows one error message, not two` and `fix(web): a failed server install, removal or restart shows one error message, not two` (the webhook setting is in the second commit).
- With the default silenced, a 401 or 403 on these five actions shows the caller's title ("Installation failed") with the server's message, where the generic handler would have titled it "Authentication Failed" or "Access Denied". The message still says what happened.

## ADR-8: Versions Are Compared by Semantic Versioning Precedence, with One Function and No New Dependency

**Status:** Proposed by the planner; no open question. Implemented by Story 21.5 (`VSS-qxxo`).

**Decision:**

1. **One function, `compareVersions(a, b)`, in `web/src/lib/version-compare.ts`,** used by the installed mods Version column (table and cards), by the Version page's Version column, and by the Version page's "newer" mark in place of the private function in `VersionTable.tsx`.
2. **It follows Semantic Versioning 2.0.0 precedence:** the dot-separated numeric core compares number by number (a missing part counts as 0); a version with a pre-release part comes before the same version without one; pre-release identifiers compare one by one, numeric ones as numbers and before alphanumeric ones, alphanumeric ones in ASCII order, and a shorter list first when all else is equal; build metadata after `+` is ignored. So `1.0.0-rc.2 < 1.0.0-rc.12 < 1.0.0 < 1.0.1 < 1.9.0 < 1.10.0`.
3. **It never throws and always gives a total order.** A leading `v` is ignored. A version it cannot read (mods publish strings such as `1.2` or free text) is compared with the others by a numeric-aware string comparison and sorts after the versions it can read; equal results fall back to the plain strings, so the order is stable.
4. **No package is added.** The rules above are about thirty lines, and the `semver` package would be a new runtime dependency that rejects the loose strings mods use.
5. **Tests:** the bead's cases, the samples in the facts above, numeric pre-release parts, mixed parts, build metadata, a leading `v`, unreadable strings, and both sort directions in each table.

**Consequences:**

- One release note: `fix(web): sort versions with pre-releases before their release`.
- The Version page's "newer" mark is now right for pre-releases numbered 10 and up.

## ADR-9: Sortable Headers Carry `aria-sort`, Column Meta Is Read Without Casts, and Close Buttons Are 44px

**Status:** Proposed by the planner; no open question. Implemented by Story 21.5 (`VSS-whnb`, `VSS-759m`, `VSS-nuef`).

**Decision:**

1. **Every sortable column's `th` has `aria-sort`:** `ascending` or `descending` for the sorted column and `none` for a sortable column that is not sorted. A column that cannot be sorted has no `aria-sort`. This applies to the installed mods table (three sortable columns) and to the Version table, which today leaves the attribute off when unsorted.
2. **In the installed mods table the attribute is set where the `th` is rendered** (`ModTable.tsx:380`), from the column's sort state; `SortableHeader` stays a button inside the cell. The chevron icons are hidden from screen readers.
3. **The two casts in `VersionTable.tsx` are removed** (`VSS-759m`); the typed `ColumnMeta` gives `className` directly. No behaviour changes; the commit is a `refactor`.
4. **The close button of `ui/dialog.tsx` and of `ui/sheet.tsx` is a 44 by 44px box at every width,** with the icon centered where it is today (the box moves up and right by the difference, so the icon does not move). One change for every dialog and for the phone navigation sheet. At every width, not only on phones: the box is invisible, and a larger target costs nothing on a desktop.
5. **Tests:** unit tests for `aria-sort` in each state and each table; the close button's size is asserted in an E2E at 390px for one dialog and for the navigation sheet (jsdom has no layout), and that it does not cover the dialog's title for the dialogs that have a long one.

**Consequences:**

- One release note: `fix(web): announce the sort order of table columns to screen readers`. The close button change is a `fix(web)` with a note too: `fix(web): make dialog close buttons easier to tap`.

## ADR-10: Every Link That Opens a New Tab Says So

**Status:** Proposed by the planner; no open question. Implemented by Story 21.6 (`VSS-woae`).

**Decision:**

1. **One small component for an application link that opens a new tab** (`target="_blank"`, `rel="noopener noreferrer"`, its children, and a hidden span with `OPENS_IN_NEW_TAB`), used by the five unmarked links: ModDB Page, Homepage and Source on the mod detail page, and the links at `InstalledModParts.tsx:43` and `layout/Sidebar.tsx:210`. The decorative icons get `aria-hidden`.
2. **The three links that say it in an `aria-label` keep it,** reworded to the same text as the constant ("opens in a new tab"), so every link announces the same words.
3. **Homepage and Source also get the visible external-link mark** (the icon that follows a description link), since their own icons (a globe, code brackets) do not show that a new tab opens.
4. **An SVG link in a description gets an SVG `<title>` child** whose text ends with the constant, added by the sanitizer hook where the HTML note is added today. An existing `<title>` is extended, not duplicated, and a second sanitizing pass leaves one note, like the HTML case. An SVG `<title>` is the element's accessible name or description and also its tooltip; no CSS icon is possible inside an SVG.
5. **The story confirms decision 4 in a browser** (the accessibility snapshot of a description with an SVG link). If the title does not reach the accessibility tree, the fallback is `aria-label` built from the link's text content plus the constant, and the story records which was used.
6. **Tests:** unit tests for the component and for the sanitizer (SVG link with and without a title, idempotence, a hostile pre-existing title); the existing description tests keep passing.

**Consequences:**

- One release note: `fix(web): say which links open in a new tab`.

## ADR-11: The Mod Detail Header Stacks on Phones, and Descriptions Are Styled by Hand-Written CSS

**Status:** Proposed by the planner; the choice against the typography plugin is open question 5. Implemented by Story 21.6 (`VSS-pzj8`, `VSS-4vbj`).

**Decision:**

1. **Below `md` the header stacks:** the logo and the info column stay side by side when they fit and the install card moves below them at full width; at the narrowest widths the info column goes under the logo. From `md` up the row is as today. The install and version controls keep 44px targets below `lg`, and the loading skeleton follows the same layout.
2. **The page does not scroll sideways from 320px up.** Long names and slugs wrap; the breadcrumb wraps or truncates.
3. **Descriptions are styled by rules under `.mod-description` in `styles/index.css`,** in the components layer next to the two rules already there: sizes and spacing for `h1` to `h6` (kept below the page's own title), paragraphs, ordered and unordered lists with markers and nesting, links in the primary colour with an underline, `blockquote`, `code` and `pre`, `hr`, tables with borders, `strong`, `em`, and images at `max-width: 100%` with automatic height. All colours come from the theme tokens, so both themes work.
4. **Wide content stays inside the card:** tables and `pre` blocks scroll inside themselves, long words and URLs wrap, embedded media do not exceed the container.
5. **The dead classes `prose prose-sm prose-invert` are removed.**
6. **`@tailwindcss/typography` is not added.** It is a new dependency for one container; `prose-invert` is a fixed dark palette, so the light theme would need overrides anyway; and the rules needed are few. The bead allows either.
7. **An author's inline styles still win** (the sanitizer keeps `style` attributes); the rules are defaults, written with low specificity.
8. **Tests:** unit tests that the container has the class and no `prose` class; an E2E on a stubbed mod detail answer with headings, lists, a link, a wide table, a wide image and a long URL: computed heading size larger than body text, list markers shown, link underlined, no sideways scroll of the page at 320, 390 and 430px, and the header stacked with every control inside the viewport.

**Consequences:**

- Two release notes: `fix(web): fit the mod detail page on phone screens` and `fix(web): show headings, lists and links in mod descriptions`.
- Descriptions with unusual markup may look different from the mod database's own page; the rules cover the elements the sanitizer lets through, not every case.

## ADR-12: Tab Triggers Are 44px Tall Below 1024px, and the Arrow Key Fault Is Investigated Before It Is Fixed

**Status:** Proposed by the planner; no open question. Implemented by Story 21.7 (`VSS-3ry`, `VSS-vt4`).

**Decision:**

1. **Below `lg` every tab trigger is at least 44px tall;** from `lg` up the tab lists are as today. The change is made once in `components/ui/tabs.tsx` (the list's height becomes automatic below `lg`, the trigger gets the minimum), following the project's existing pattern of 44px targets below `lg`.
2. **All three tab lists are checked together** at 320, 390, 430 and 768px: Settings (which wraps to two rows below about 550px and must keep both rows inside its background), Mods and the Version page's channel filter. No page may scroll sideways and no list may overlap what follows it.
3. **`VSS-vt4` starts with a reproduction, with a time box of half a day:** first with a real keyboard in Chromium and Firefox, as the bead asks, then with the scripted steps. Suspects in order: the tab list changes while it has focus (the fourth trigger appears when `useAuthMe` resolves, `SettingsPage.tsx:59-64`); the page or the tabs remount when the first queries settle; focus is set before Radix has registered the triggers.
4. **If the cause is in this project's code, it is fixed there** (the likely form: the set of triggers does not change after the list can be focused, for example by rendering the list once the role is known), with a unit test that presses an arrow key straight after the render and an E2E without the wait.
5. **If a real keyboard cannot reproduce it, or the cause is inside Radix,** no workaround is added: the story records what was tried and what was seen in the bead and closes it with that evidence.

**Consequences:**

- One release note: `fix(web): make tabs easier to tap on phones`. A second, `fix(web): settings tabs respond to arrow keys as soon as they appear`, only if decision 4 applies.
- Tab lists are taller below 1024px, so each of the three pages loses about 14px of height there.

## ADR-13: On Phones the Jobs and Version Tables Fit Their Container, and Every Page Is Measured

**Status:** Proposed by the planner; no open question. Implemented by Story 21.7 (`VSS-f9y`).

**Decision:**

1. **Scheduled Jobs becomes a list of cards below `lg`,** one per job with its four values labelled, using the pattern of the installed mods cards (one layout mounted, chosen by `useMediaQuery(LG_UP_QUERY)`). Four text columns that need 523px cannot fit a 320px screen by hiding one; and at 768px with the sidebar expanded the table has 510px.
2. **The Version table drops columns instead:** it needs 361px and has 256px at 320px. Below `sm` the Channel column is hidden and the channel is shown as a small badge under the version number (Size is already hidden there). If that does not bring it under 256px, the story may shorten the action button to an icon with a label for screen readers, keeping a 44px target.
3. **Neither table scrolls inside itself from 320 to 1023px, in both sidebar states,** and neither page scrolls sideways.
4. **Every page is measured at 320, 390, 430, 768 and 1023px in both sidebar states,** as the bead's comment asks: Dashboard, Version, Game Settings, Mods (both tabs), mod detail, both console pages and Settings (each tab). The measurements go into the story's folder. A page that scrolls sideways or has a table scrolling inside itself is fixed in this story when the fix is of the same kind (a table or a row that does not wrap); anything larger is reported to the maintainer in the pull request, not filed and not silently skipped.
5. **Tests:** unit tests for both layouts of the jobs list; `layout-widths.spec.ts` gains the two tables at the listed widths.

**Consequences:**

- One release note: `fix(web): fit the scheduled jobs and version tables on phone screens`.

## ADR-14: With No Choice Stored the Sidebar Follows the Width; a Choice Wins at Every Width

**Status:** Proposed by the planner (open question 6). Implemented by Story 21.8 (`VSS-w85`).

**Context:** The UX spec wants the sidebar collapsed by default from 768 to 1023px. The stored preference is a boolean that every browser already holds as `false`, written on first render, so "never chose" and "chose expanded" cannot be told apart today.

**Decision:**

1. **The preference becomes one of three values:** `auto` (the default), `expanded` or `collapsed`, stored in the same cookie under a new key (`sidebar`). The old `sidebarCollapsed` key is no longer written.
2. **Reading an old cookie:** `sidebarCollapsed: true` becomes `collapsed` (it can only come from a choice); `false` or a missing key becomes `auto`. A user who collapsed and later expanded again is treated as never having chosen: at 1024px and up nothing changes for them, and at tablet widths they get the spec's default until they choose.
3. **With `auto` the sidebar is collapsed from 768 to 1023px and expanded from 1024px,** and follows the width live as the window is resized (`useMediaQuery(LG_UP_QUERY)`).
4. **An explicit choice wins at every width and is kept.** The sidebar's own toggle stores the opposite of what is shown, as `expanded` or `collapsed`. One choice for all widths, not one per breakpoint: a per-width memory is more state than a 96px difference deserves.
5. **UI Preferences replaces its switch with a three-way choice** (Automatic, Expanded, Collapsed), so a user can return to the default.
6. **Below `md` the navigation sheet always shows the full sidebar with labels,** whatever is stored, and hides the collapse toggle there. Today a stored `true` shows the icon-only sidebar inside a 256px sheet (found by reading; the story confirms it first).
7. **Tests:** unit tests for the three values at 767, 768, 1023 and 1024px, the migration of both old values, the toggle, the preferences control and the sheet; `layout-widths.spec.ts` writes the new key where it sets the sidebar state, and gains a test that a fresh browser at 900px has a 64px sidebar.

**Consequences:**

- One release note: `feat(web): collapse the sidebar by default on tablet-sized screens`.
- Existing users see the sidebar collapsed at 768 to 1023px after the update unless they had collapsed it themselves (then it stays collapsed everywhere, as now).

## ADR-15: Page Content Is at Most 1280px Wide and Centered; the Console Pages Are the Exception

**Status:** Proposed by the planner (open question 7 for the exceptions). Implemented by Story 21.8 (`VSS-alx`). Completes Epic 16 ADR-3 decision 1, which left the application-wide maximum out.

**Decision:**

1. **`Layout` caps the content at 1280px and centers it** (the padding stays outside the cap), with one exported constant for the classes. `SETTINGS_CONTENT_WIDTH` becomes that constant or is removed, so the number is written once.
2. **The cap applies to:** the Dashboard, the Version page, Game Settings (already capped), the Mods page with both tabs, the mod detail page (which stays at its narrower `max-w-4xl`) and Settings (`/config`).
3. **The mod browser grid is capped too.** It never has more than four columns (`ModBrowseGrid.tsx:41`), so the cap does not remove a column; it makes the cards about 308px wide at 1920px where they are about 416px today, which is closer to their width at 1280px and keeps descriptions readable. More columns on wide screens would be a different change and is not planned.
4. **The console pages are not capped:** the Console page and the game server page with the side-by-side console (`GameServerPage.tsx`) use the full width. Log lines are long, a terminal is the one place where width is content, and the UX spec asks for a full-width console. A route opts out through the layout (a route handle or a wrapper), not by negative margins.
5. **The header bar and the sidebar are not affected;** only the content area is.
6. **Each capped page is checked at 1440, 1920 and 2560px in both sidebar states:** content centered, at most 1280px, nothing clipped, charts and tables resized. `layout-widths.spec.ts` gains these checks and one that the console is wider than 1280px at 1920px.

**Consequences:**

- One release note: `feat(web): limit page width to 1280px on wide screens`.
- On screens wider than about 1500px, pages have empty margins left and right, as the UX spec intends.
