# Story 20.6: The Mod Database E2E Tests Run in CI

Status: review

<!-- Implements FR252, FR253, FR254, FR258, FR259 and Epic 20 ADR-9 (as revised by the maintainer on 2026-11-17). Beads: VSS-571h (TEST-006), part 1, closed here; VSS-zhv3 (DOCS-001), pulled in. Stacked on Story 20.5 (stories run in order 20.1 to 20.7). Line references were verified at 7f04ea2 (epic-20-planning; its api/, web/ and scripts/ are identical to 3f1c6ea, the commit the ADRs cite) and must be re-checked at implementation time: Story 20.1 reformats 23 files under api/src and 52 under api/tests, Story 20.3 changes the Justfile recipes and .gitignore, and Story 20.5 edits scripts/e2e-ci.sh, scripts/tests/test-e2e-ci.sh, the e2e job and web/e2e/README.md. -->

## Story

As a **maintainer**,
I want **the tests that read the mod database to run in CI against recorded answers**,
so that **the mod pages are covered on every pull request, the same way every time, without calling the live service**.

## Acceptance Criteria

1. **Given** a deployment that does not set `VS_MOD_DB_URL` (or sets it blank)
   **When** the API starts and talks to the mod database
   **Then** it uses `https://mods.vintagestory.at` for its API calls (`/api/...`) and downloads (`/download`) exactly as before, and logs no warning about the address
   *(Covers FR258; Matt, 2026-11-17)*

2. **Given** `VS_MOD_DB_URL` set to another `https` address
   **When** the API lists mods, lists mods for a game version, looks a mod up, reads the game version list or downloads a mod file
   **Then** each request goes to that address (`<base>/api/mods`, `<base>/api/mods?gameversion=<id>`, `<base>/api/mod/<slug>`, `<base>/api/gameversions`, `<base>/download?fileid=<id>`), none goes to `mods.vintagestory.at`, and the start-up log has exactly one `mod_db_url_overridden` warning that carries the scheme and the host and nothing else
   *(Covers FR258, FR259)*

3. **Given** `VS_MOD_DB_URL` set to another address
   **When** the API passes on a mod's logo, screenshots, homepage and source links, and the web UI builds a link to a mod's page
   **Then** the image host allow-list and the link rules are the same as without the setting (only `moddbcdn.vintagestory.at` images, `https` links), install-by-URL accepts the same forms, and the web UI's links still point at `mods.vintagestory.at`
   *(Covers FR258)*

4. **Given** `VS_MOD_DB_URL` with the scheme `http` and `VS_DEBUG` unset or false
   **When** the API starts
   **Then** start-up stops with an error that names `VS_MOD_DB_URL` and says plain HTTP is for testing and needs `VS_DEBUG=true`
   *(Covers FR259; Matt, 2026-11-17)*

5. **Given** `VS_MOD_DB_URL` with the scheme `http` and `VS_DEBUG=true`
   **When** the API starts
   **Then** it starts, uses the address, and logs the warning
   *(Covers FR259; Matt, 2026-11-17)*

6. **Given** a value that is not an absolute URL, has another scheme, has no host, or carries a user name, a password, a path, a query, a fragment, a port that is empty or not a number from 1 to 65535, or white space or a control character inside it
   **When** the API starts
   **Then** start-up stops with an error that names the setting and what is wrong; a single trailing `/` and white space around the value are accepted and ignored; the error text does not repeat the value (so a password typed into the address is not printed) and prints no other setting
   *(Covers FR259)*

7. **Given** the README, `.env.example` and the release notes
   **When** I read them
   **Then** the setting is documented as optional, with its default, what it is for (a mirror of the same database, or tests), the `http` rule, and that mods are downloaded from that address; and the commit that adds it has the subject `feat(api): add VS_MOD_DB_URL to use a mirror of the mod database`
   *(Covers FR258)*

8. **Given** the built image with the setting pointed at a stub, before anything is recorded
   **When** Task 2 is done
   **Then** the story has shown that the listing, the mod lookup, the game version list and the download reach the stub, that no request goes to the live host (which stays blocked in the container), and that a request the stub has no answer for is reported with its URL
   *(Covers FR252)*

9. **Given** `just test-e2e-ci`
   **When** it runs
   **Then** its first pass is as before (the tests with no tag against a container in production mode), and a second pass starts a replay container and a second API container with `VS_DEBUG=true` and `VS_MOD_DB_URL` set to the replay, runs the `@moddb` tests that are not `@moddb-live` or `@install` against it, and removes everything it started (two API containers, the replay container, the network, the temporary directory), also after a failure
   *(Covers FR252)*

10. **Given** the CI run
    **When** I look at where its requests go
    **Then** neither API container nor the browser sends a request to the live mod database or its image host; the browser's image requests are answered by a placeholder
    *(Covers FR252)*

11. **Given** two CI runs of the same commit
    **When** I compare the `@moddb` tests' results
    **Then** they are the same, and no test of the second pass is reported as flaky (passed only on a retry)
    *(Covers FR252)*

12. **Given** `web/e2e/fixtures/moddb/`
    **When** I read it
    **Then** it holds one file per recorded request and a manifest that gives each request, its recording date, how it was trimmed and which spec needs it; the answers are real ones, trimmed, with their image and link URLs unchanged, and nothing but what the mod database's public API returned
    *(Covers FR253; Matt, 2026-11-17)*

13. **Given** `just record-moddb`
    **When** I run it with network access
    **Then** it fetches the manifest's requests from the live mod database, rewrites the recordings with the same trimming, and prints which fields appeared or disappeared since the last recording
    *(Covers FR253)*

14. **Given** the 31 `@moddb` tests
    **When** the story has run each against the recordings
    **Then** each one either runs in CI, or carries `@moddb-live` (it compares with live data) or `@install` (it installs a real mod) with a one-line reason, and the story lists how many tests are in each group
    *(Covers FR254; Matt, 2026-11-17)*

15. **Given** `just test-e2e-web` on a developer's machine
    **When** it runs
    **Then** every spec still runs against the live mod database, with no recordings and no setting involved, and no workflow runs them against the live service on a schedule
    *(Covers FR254; Matt, 2026-11-17)*

16. **Given** `web/e2e/README.md`
    **When** I read it
    **Then** it explains the tags as they now are, the two passes, how the replay works, how and when to refresh the recordings, and which tests remain live-only
    *(Covers FR253, FR254)*

17. **Given** the `e2e` job
    **When** the story is done
    **Then** it still finishes within its 30 minute limit, it is green on this story's pull request, and the story records its time before (3 min 16 s at `3f1c6ea`, and the time after Story 20.5) and after
    *(Covers FR252)*

18. **Given** the pull-in `VSS-zhv3`
    **When** the story is done
    **Then** `agentdocs/vintagestory-modapi.md` documents the fields and filters the bead lists, checked against the recordings, and the bead is closed with an AAR
    *(Covers FR253; pulled in, Matt, 2026-11-17)*

## Tasks / Subtasks

<!-- Six tasks, the project limit. Each functional task includes its tests in the same commit. Commit per task: type(story-20.6/task-N): ... with one exception: Task 1's commit subject is exactly `feat(api): add VS_MOD_DB_URL to use a mirror of the mod database` (AC 7; it is the epic's only release note, and cliff.toml:26 shows the `api` scope). No other commit of this story is feat, fix or perf. Red first. Story 20.1 has landed, so run `ruff format` on every API file this story changes. -->

- [x] Task 1: The `VS_MOD_DB_URL` setting + tests + documentation (AC: 1, 2, 3, 4, 5, 6, 7) (`VSS-571h`)
  - [x] 1.1: `api/src/vintagestory_api/config.py`: a module constant `DEFAULT_MOD_DB_URL = "https://mods.vintagestory.at"`; a field `mod_db_url: str = DEFAULT_MOD_DB_URL` after `csp_mode` (`:33`) with a comment in the style of the `csp_mode` one (`:31-32`); a `@field_validator("mod_db_url")` after `validate_csp_mode` (`:99-111`) that implements the guard of Dev Notes "The guard" and returns the normalised address. A field validator, not a model validator (Dev Notes "Why a field validator")
  - [x] 1.2: `config.py` `model_config` (`:17`): add `hide_input_in_errors=True`, so no settings error prints the value it refused (AC 6). Check that `TestCspMode` and the other `ValidationError` tests in `api/tests/test_config.py` still pass (they assert on the message only); nothing under `api/src` or `api/tests` reads `input_value` from a settings error (checked with `grep -rn input_value api`)
  - [x] 1.3: `api/src/vintagestory_api/services/mod_api.py`: `ModApiClient.__init__` (`:358-362`) gains `mod_db_url: str = DEFAULT_MOD_DB_URL` (import the constant from `vintagestory_api.config`) and sets `self._api_url = f"{mod_db_url}/api"` and `self._download_url = f"{mod_db_url}/download"`. Remove the class constants `BASE_URL` and `DOWNLOAD_URL` (`:348-349`) and their two docstring lines (`:333-334`), and replace all six uses: `:415` (the log's `endpoint`), `:477`, `:676`, `:764`, `:919`, `:993`. Nothing under `api/src` or `api/tests` reads the constants from outside the class (checked with `grep -rn "\.BASE_URL\|\.DOWNLOAD_URL" api`)
  - [x] 1.4: `api/src/vintagestory_api/services/mods.py`: `ModService.__init__` (`:345-354`) gains `mod_db_url: str = DEFAULT_MOD_DB_URL`, keeps it, and passes it to the one place a `ModApiClient` is built (`:1014-1017`); `get_mod_service` (`:106-114`) passes `settings.mod_db_url`. The default keeps every existing `ModService(...)` and `ModApiClient(...)` call in the tests working unchanged
  - [x] 1.5: `api/src/vintagestory_api/main.py`: a function `log_mod_db_url(settings)` after `log_web_api_key_state` (`:92-121`) that logs `logger.warning("mod_db_url_overridden", scheme=..., host=..., hint=...)` when `settings.mod_db_url != DEFAULT_MOD_DB_URL` and nothing otherwise; call it in the lifespan directly after `log_web_api_key_state(settings)` (`:138`). `host` is the host name without the port; the hint says that mod database requests and mod downloads go to this address
  - [x] 1.6: `api/tests/conftest.py`: `os.environ.pop("VS_MOD_DB_URL", None)` next to the `VS_DEBUG` line (`:11`), before the app is imported, with a comment (mise loads a developer's `.env`, `.mise.toml:12-13`; a mirror address there must not reach tests that mock `https://mods.vintagestory.at/...`)
  - [x] 1.7: Tests (Dev Notes "API tests", Task 1 rows), red first
  - [x] 1.8: `README.md`: a row in the configuration table after `VS_CSP_MODE` (`:81`) and a short paragraph in the security notes near `:39`; `.env.example`: a commented block after the `VS_CSP_MODE` block (`:33-39`). Text in Dev Notes "Documentation text"
  - [x] 1.9: Commit exactly as `feat(api): add VS_MOD_DB_URL to use a mirror of the mod database`. Run `just changelog` and check the subject shows under Features with the `api` scope

- [x] Task 2: The replay server, and the proof in the built image against a stub (AC: 8) (`VSS-571h`)
  - [x] 2.1: New `scripts/moddb-replay.py` (Dev Notes "The replay server"): Python standard library only, serves a directory by its `manifest.json`, answers a request it has no recording for with 404 and a plain-text body that names the URL, and logs every request
  - [x] 2.2: New `scripts/tests/test-moddb-replay.sh` (Dev Notes "Script tests"), run by `just test-scripts`; add both Python scripts of this story to `just lint-scripts` (Dev Notes "Lint for the two Python scripts")
  - [x] 2.3: The proof (Dev Notes "The proof in the built image"): build the image from this branch, start the replay with a made-up directory in a temporary location, start an API container with `VS_DEBUG=true`, `VS_MOD_DB_URL` and the blocked hosts, and show the four request kinds reaching the replay, the missing answer named by URL, the warning in the log, and the refusal of `http` without `VS_DEBUG`. Nothing made up for the proof is committed
  - [x] 2.4: Paste the commands and the relevant log lines into Debug Log References. Commit: `test(story-20.6/task-2): add the mod database replay server`

- [x] Task 3: The recording script, the manifest, the first recordings, and the mod API reference (AC: 12, 13, 18) (`VSS-571h`, `VSS-zhv3`)
  - [x] 3.1: New `scripts/moddb-record.py` and the recipe `record-moddb *ARGS` in the `Justfile` (after `test-e2e-ci`, `:94-96`, in the argument style Story 20.3 left): Dev Notes "The recording script"
  - [x] 3.2: New `scripts/tests/test-moddb-record.sh`: the recorder run against the replay server serving a made-up "live" directory, so trimming and the field report are tested without the network (Dev Notes "Script tests")
  - [x] 3.3: `web/e2e/fixtures/moddb/manifest.json` with the requests of Dev Notes "What to record", then `just record-moddb` once. Check the result: every file parses, the listing holds what the trim rule says, no file holds anything but the mod database's answer, total size noted in Completion Notes
  - [x] 3.4: `scripts/tests/test-e2e-ci.sh`: pin the recordings (Dev Notes "Guards in test-e2e-ci.sh", the manifest rows)
  - [x] 3.5: `agentdocs/vintagestory-modapi.md` (Dev Notes "The mod API reference"): the fields and filters `VSS-zhv3` lists, each checked against a recording. Its own commit: `docs(story-20.6/task-3): complete the mod API reference from the recordings`
  - [x] 3.6: Commit for 3.1 to 3.4: `test(story-20.6/task-3): record mod database answers for the E2E tests`

- [x] Task 4: The second pass in `scripts/e2e-ci.sh` (AC: 9, 10) (`VSS-571h`)
  - [x] 4.1: `scripts/e2e-ci.sh`: the network, the replay container, the second API container, the second Playwright run and the cleanup, as in Dev Notes "The second pass". The first pass does not change
  - [x] 4.2: `web/e2e/config-js.ts`: `serveModImagePlaceholders(page)` (Dev Notes "Images"); call it in the `beforeEach` of every spec that keeps a `@moddb` test
  - [x] 4.3: `scripts/tests/test-e2e-ci.sh`: pin the new pieces (Dev Notes "Guards in test-e2e-ci.sh", the script rows); `.github/workflows/ci.yml` and `.gitignore`: the second pass's report directories (Dev Notes "The second pass", step 7)
  - [x] 4.4: `just test-e2e-ci` locally: both passes run; `docker ps -a`, `docker network ls` and the temporary directory show nothing left, after a green run and after a run made to fail (for example an unknown spec path). Commit: `test(story-20.6/task-4): run the mod database tests on recorded answers in the E2E script`

- [x] Task 5: Each `@moddb` test on the recordings; tags; the README (AC: 11, 14, 15, 16) (`VSS-571h`)
  - [x] 5.1: Run the second pass and work through the 31 tests with the table in Dev Notes "The 31 tests". For a request the replay did not have: add it to the manifest and record only that request (`just record-moddb --only <request>`). Fill the "Result" column of the table in this file
  - [x] 5.2: Retag: a test that compares with live data loses `@moddb` and gets `@moddb-live` with a one-line reason next to the tag. A test that fails on recordings for a fault of its own is fixed, not retagged, and the fix is named in Completion Notes. No `test.skip`, no weakened assertion
  - [x] 5.3: Run the second pass three times in a row locally (`just test-e2e-ci` three times): the same tests pass each time and none needs a retry
  - [x] 5.4: Dev stack check (AC 15): rebuild the dev stack from this branch (`just docker restart`), then `cd web && bunx playwright test --grep '@moddb'` against port 8080 with no `E2E_MODDB_REPLAY` set. The tests run against the live mod database as before; record the result, and for any failure whether it also fails on `main` (the live tests are known to be flaky, ADR-9 Context). The `@install` tests restore what they install (their own snapshot guards); record that `GET /api/v1alpha1/mods` returned the same body before and after
  - [x] 5.5: `web/e2e/README.md` (Dev Notes "README for the E2E tests"); `README.md` "End-to-end tests" (`:114-120`): one line saying the CI set includes the mod database tests on recorded answers; the header comment of `web/playwright.config.ts` (`:6-9`) likewise. Commit: `test(story-20.6/task-5): tag the live-only mod database tests and document the replay`

- [ ] Task 6: Quality gate, CI and review hand-off (AC: all)
  - [x] 6.1: `just check` passes with 0 Pyright warnings and 0 skipped tests (Story 20.2's state); `just test-scripts`, `just lint-scripts` and `just lint-workflows` pass; the diff adds no lint or type suppression and no `cast`; after `just test-api`, `git status --short` shows nothing under `dev/`; after `just test-e2e-ci`, `git status --short` is clean
  - [x] 6.2: No new dependency: `git diff main -- api/pyproject.toml api/uv.lock web/package.json web/bun.lock` is empty
  - [ ] 6.3: CI (the controller pushes and opens the pull request): the `E2E tests` job is green. Record in Completion Notes the run URL, the job's duration, the two passes' test counts, and the duration before. Re-run the job once on the same commit and record that the second pass gave the same results with no flaky test (AC 11)
  - [ ] 6.4: Close `VSS-zhv3` and then `VSS-571h`, each with an AAR (`.claude/skills/beads/SKILL.md`); the AAR of `VSS-571h` names Story 20.5 for parts 2 to 4 and this story for part 1
  - [ ] 6.5: Story status `review`, `just sprint set 20-6-mod-database-tests-in-ci review`, pull request (base: Story 20.5's branch while its pull request is open, otherwise `main`). The description lists "API contract changes" below and the test counts of "The 31 tests". Commit: `chore(story-20.6/task-6): validate and move story 20.6 to review`

## Dev Notes

### Where the code builds a mod database address (verified at 7f04ea2)

**API, follows the setting after this story** (all in `api/src/vintagestory_api/services/mod_api.py`):

| Line | Today | Request |
|---|---|---|
| `:348` | `BASE_URL = "https://mods.vintagestory.at/api"` | the constant |
| `:349` | `DOWNLOAD_URL = "https://mods.vintagestory.at/download"` | the constant |
| `:415` | `url.removeprefix(self.BASE_URL)` | the `endpoint` field of the `mod_api_*` log events; must strip the configured prefix, or an overridden address would be logged in full |
| `:477` | `f"{self.BASE_URL}/mod/{slug}"` | mod lookup (`get_mod`) |
| `:676` | `f"{self.DOWNLOAD_URL}?fileid={fileid}"` | download (`download_release_file`) |
| `:764` | `f"{self.BASE_URL}/mods"` | the full listing |
| `:919` | `f"{self.BASE_URL}/mods"` with `params={"gameversion": ...}` | the listing for one game version |
| `:993` | `f"{self.BASE_URL}/gameversions"` | the game version list |

The client is built in one place, `services/mods.py:1014-1017`, by a `ModService` that `get_mod_service` builds at `services/mods.py:106-114` from `Settings()` (`:101`). The cache refresh job uses the same client through `ModService.api_client`.

**API, stays fixed** (do not make these read the setting):

- `services/mod_media.py:38`: `MOD_MEDIA_HOSTS = frozenset({"moddbcdn.vintagestory.at"})`, the image host allow-list (Epic 18 ADR-1) and the link rules beside it (Epic 19 ADR-12)
- `services/mod_api.py:168-186` `extract_slug`: takes the slug from any `http...` URL's path; the form install-by-URL accepts does not depend on the host today and does not change
- `templates/serverconfig-template.json:17`: `"ModDbUrl": "https://mods.vintagestory.at/"` is the game server's own setting, a different thing
- Text only (docstrings and field descriptions, no request): `routers/mods.py:606`, `:625`, `:713`; `models/mods.py:222`, `:360`; `services/mods.py:652`, `:664`, `:1331`, `:1342`; `services/mod_api.py:4`, `:173`, `:330`

**Web, stays fixed** (links a browser is given):

- `web/src/features/mods/ModDetailPage.tsx:694`, `web/src/components/ModCard.tsx:180`: `https://mods.vintagestory.at/show/mod/${mod.assetId}`
- `web/src/components/InstalledModParts.tsx:32-33`: the same, or `https://mods.vintagestory.at/${mod.slug}`
- `web/src/lib/mod-utils.ts:12-13`, `:42` and `web/src/api/types.ts:188`, `:418`: comments

No file under `web/src` changes in this story.

**Other hosts the API calls** (not the mod database, not touched): `api.vintagestory.at` and `cdn.vintagestory.at` for game server versions and downloads. They stay blocked in both CI containers.

### The guard (Task 1.1)

The validator receives the raw string and `info: ValidationInfo`. Rules, in this order:

1. Strip white space around the value. Blank means unset: return `DEFAULT_MOD_DB_URL` (as `VS_CSP_MODE` treats blank, `config.py:107-108`; a compose file that passes `${VS_MOD_DB_URL:-}` gives a blank value).
2. Refuse a value that contains white space or a control character anywhere inside it. `urlsplit` does not: the planning prototype showed it accepts `https://h h` and silently removes a tab from `https://exa<TAB>mple.com`.
3. Parse with `urllib.parse.urlsplit` and read `.port` inside a `try`: a port that is not a number or is out of range raises `ValueError` there.
4. Scheme must be `https` or `http` (`urlsplit` lowercases it). A value with no scheme (`mods.example.com`, `//host`) or another scheme (`ftp://x`) is refused.
5. A host is required (`https://`, `https:/host` have none).
6. No user name or password: refuse when `"@"` is in the network location (this also catches `https://@host`).
7. An empty port is refused (`https://host:` parses with `port is None`; check that the network location does not end in `:`).
8. Path must be `""` or `"/"`. No query and no fragment, including empty ones: `https://host?` and `https://host#` are refused (check the raw string for `?` and `#`, since `urlsplit` reports both as empty).
9. `http` is accepted only when `info.data.get("debug") is True`. `debug` is declared before `mod_db_url` (`config.py:19`), so it is in `info.data` unless `VS_DEBUG` itself failed to parse; then it is absent and `http` is refused, which is right.
10. Return `f"{scheme}://{host}"` plus `:{port}` when a port was given, with the host in lower case and an IPv6 host in its brackets. The result never ends in `/`.

Messages (each starts with `VS_MOD_DB_URL` and never contains the value):

- `VS_MOD_DB_URL must be an absolute https URL with a host, for example https://mods.vintagestory.at.` (rules 2, 3, 4, 5, 7)
- `VS_MOD_DB_URL must not contain a user name or password.` (rule 6)
- `VS_MOD_DB_URL must not contain a path, a query or a fragment; give the site's base address only.` (rule 8)
- `VS_MOD_DB_URL uses plain HTTP, which is for testing and needs VS_DEBUG=true. Use an https address.` (rule 9)

The guard reads the `VS_DEBUG` the process started with (`Settings.debug`, the same value that serves `/docs` and the role test routes, `main.py:323-325`, `:374`). The run-time debug-logging toggle (`set_debug_enabled`, `config.py`) does not change it.

`Settings.debug` is parsed by pydantic (`true`, `1`, `yes`, `on`, ...); `_read_debug_from_env` in `config.py` accepts only `true`, `1`, `yes`. The guard uses `Settings.debug`. Do not unify the two here.

After normalisation `https://mods.vintagestory.at/` equals the default and logs no warning. `https://mods.vintagestory.at:443` does not equal it and logs the warning; that is acceptable (the operator did set it).

### Why a field validator (Task 1.1, 1.2)

Checked with a prototype at planning time (pydantic 2.14):

- A failing `@model_validator(mode="after")` prints the whole input of the model in the error, `input_value={'debug': ..., 'api_key_admin': ...}`, which can put an API key into the start-up log. Do not use one.
- A failing `@field_validator` prints only that field's value, `input_value='https://user:PASSWORD@host'`. With `hide_input_in_errors=True` in `model_config` the error prints no input at all, for this and every other setting. `ValidationError` text then reads `mod_db_url` / `Value error, VS_MOD_DB_URL ...`.

Start-up stops the same way a bad `VS_CSP_MODE` stops it: `Settings()` raises when `main.py:393` runs `create_app(get_settings())` at import, and uvicorn exits.

### API tests

All new tests are unit tests with `respx` or plain `Settings(...)`; none calls the network. Use made-up hosts under `.example` (`https://mirror.example`).

| Task | File, class | Cases |
|---|---|---|
| 1 | `api/tests/test_config.py`, new `TestModDbUrl` after `TestCspMode` (`:437-473`) | default when unset; blank and spaces give the default; `https://mods.vintagestory.at/` gives the default; `HTTPS://Mirror.Example:8443/` gives `https://mirror.example:8443`; spaces around the value ignored; `https://[::1]:8443` accepted; `http://replay:8099` accepted with `debug=True`; the same refused with `debug=False` and with `VS_DEBUG` unset in the environment, message names `VS_DEBUG=true`; parametrised refusals, each asserting its message: `mods.example.com`, `//host`, `ftp://host`, `https://`, `https:/host`, `https://u:p@host`, `https://u@host`, `https://@host`, `https://host/api`, `https://host//`, `https://host?x=1`, `https://host?`, `https://host#f`, `https://host#`, `https://host:abc`, `https://host:99999`, `https://host:`, `https://ho st`, a value with a tab inside; for `https://user:PASSWORD@host` the error text contains neither `PASSWORD` nor `user`; with `api_key_admin` set, no error text contains the key. Set the environment with `monkeypatch.setenv`/`delenv` (conftest sets `VS_DEBUG=true` for the whole run, `api/tests/conftest.py:11`, so the "without debug" cases must remove it or pass `debug=False`) |
| 1 | `api/tests/test_mod_api.py`, new `TestModApiClientModDbUrl` | a client built with `mod_db_url="https://mirror.example"`, under `respx.mock(assert_all_mocked=True)` with only `https://mirror.example/...` routes: `get_mod` calls `/api/mod/<slug>`; the full listing calls `/api/mods`; the game-version listing calls `/api/mods?gameversion=<id>`; the game version list calls `/api/gameversions`; `download_release_file` calls `/download?fileid=<id>`. One more: with a route only for the default host, each of the five raises (nothing falls back to the default). The `endpoint` field of a `mod_api_http_error` log is `/mods`, not the full address (use `captured_logs`). A client built with no argument still calls `https://mods.vintagestory.at` |
| 1 | `api/tests/test_mod_service.py` | `ModService(..., mod_db_url="https://mirror.example").api_client` calls the mirror for a lookup; `get_mod_service()` with `VS_MOD_DB_URL` set in the environment builds a service whose client calls the mirror (reset the `_mod_service` singleton as the neighbouring tests do, and restore it) |
| 1 | `api/tests/test_main.py` | `log_mod_db_url`: no log line for the default; one `mod_db_url_overridden` warning for a mirror, with `scheme` and `host` and without port, path or the full URL; the lifespan logs it once at start-up (in the style of the existing lifespan tests, `TestLifespanAutoStart` `:285`) |
| 1 | `api/tests/test_mod_media.py` (the file that tests `MOD_MEDIA_HOSTS` today) | with a client on `https://mirror.example` and a recorded-style mod answer: an image on `mirror.example` is dropped, an image on `moddbcdn.vintagestory.at` is kept, an `http` homepage link is dropped (AC 3). `extract_slug("https://mods.vintagestory.at/smithingplus")` and `extract_slug("https://mirror.example/smithingplus")` give the same slug as today (pins "the accepted forms do not change") |

### Existing tests that change

Checked with a prototype at planning time (the field, a validator and the two instance attributes; `just test-api`: 3,334 passed, with and without `VS_MOD_DB_URL` in the environment). No existing API test fails, because every test builds `ModService`/`ModApiClient` with the default and mocks `https://mods.vintagestory.at/...` as a literal (15 files, for example `api/tests/test_mod_api.py:487`, `:964`, `:1116`; `api/tests/console/conftest.py:121`, `:128`). The prototype did not wire `get_mod_service` to the setting; Task 1.6 keeps the wired version independent of a developer's `.env`.

Tests that change on purpose:

- `scripts/tests/test-e2e-ci.sh`: new assertions (below). The existing `TAGS=` assertion stays as Story 20.5 left it; the first pass's tag list does not change, because the pattern `@moddb` also matches `@moddb-live`.
- The specs that are retagged or get the placeholder helper (Task 4.2, 5.2).

No web unit test changes: nothing under `web/src` changes.

### Documentation text (Task 1.8)

README table row:

`| `VS_MOD_DB_URL` | No | Base address of the mod database (`https://mods.vintagestory.at`). Set it only to use a mirror of the same database; mods are downloaded from this address. Must be an `https` URL with a host and nothing else; `http` is accepted only with `VS_DEBUG=true`. Any other value stops start-up |`

README paragraph (near `:39`): what it is for (a mirror of the same database, or tests); that mod listings and mod files come from that address and the game server runs those files, so point it only at a server you trust; that an address other than the default is logged at every start as `mod_db_url_overridden`; that it must serve the same database, because the download cache and the installed mods' records are kept by the database's IDs; that images still load only from `moddbcdn.vintagestory.at` and links to mod pages still go to `mods.vintagestory.at`.

`.env.example` block: the same facts in comment form, ending with `# Default: https://mods.vintagestory.at` and `# VS_MOD_DB_URL=https://mods.vintagestory.at`.

`docker-compose.yaml` needs no change: it reads `.env` through `env_file` (`:27-29`), as it does for `VS_CSP_MODE`.

### The replay server (Task 2.1)

`scripts/moddb-replay.py`, standard library only (`http.server.ThreadingHTTPServer`, `json`, `argparse`, `urllib.parse`). It runs inside the image (Python 3.14, `Dockerfile:41-48`) and on a developer's machine.

- Arguments: `--dir <directory>` (holds `manifest.json` and the files it names), `--port <n>` (default 8099), `--host` (default `0.0.0.0`; the container is on a private Docker network and publishes no port).
- At start it reads the manifest and builds a table from request key to entry. The request key is the path plus the query with its parameters sorted (`/api/mods?gameversion=123`). It refuses to start, with a message, if the manifest does not parse, names a file that does not exist, names a file with a path separator or `..` in it, or has two entries with the same key.
- `GET <key in the table>`: the entry's `status` (default 200) and `content_type` (default `application/json`), the file's bytes unchanged.
- `GET /healthz`: `200`, body `ok` (for the script's wait; not a recording).
- Any other `GET`: `404`, `Content-Type: text/plain`, body `No recording for GET <path and query>`. The body must not be JSON: `get_mod` would read a JSON object with `"statuscode": "404"` as "mod not found" and answer 404 (`mod_api.py:477-480`); plain text makes every caller raise `ExternalApiError`, which the routers turn into 502 `EXTERNAL_API_ERROR` (`routers/mods.py:466`, `:542`, `:594`, `:701`, `:843`).
- Any other method: `405`.
- File names come only from the manifest, never from the request, so a request path cannot reach another file.
- One log line per request on stdout, flushed: `served GET /api/mods` or `no_recording GET /api/mod/unknown`. `docker logs` on the replay container is then the list of what the API asked for.

### The proof in the built image (Task 2.3)

This is a one-time, manual proof with Docker; its evidence goes into Debug Log References. Unit tests (Task 1) keep the client following the setting afterwards, and the second pass (Task 4) keeps the listing, lookup and game version list proven on every pull request. The download is proven here and by the unit test only, because no `@install` test runs in CI.

1. Build: `docker build --platform linux/amd64 -t vintagestory-server:e2e .`
2. In a temporary directory (`mktemp -d`, removed afterwards) write a made-up manifest and files: `/api/mods` (a listing of two made-up mods), `/api/mod/e2estub` (one made-up mod with one release whose `fileid` is `1`), `/api/gameversions` (two made-up versions), `/download?fileid=1` (`content_type: application/zip`, a small zip with a valid `modinfo.json`, built in that directory). Shape them after `api/tests/fixtures/moddb/mod_carryon.json`.
3. `docker network create`, then the replay: a container from the same image on that network, `docker cp` of the script and the directory into it, command `python3 /tmp/moddb-replay.py --dir /tmp/moddb`.
4. The API container on the same network: `-e VS_DEBUG=true -e VS_MOD_DB_URL=http://<replay container name>:8099`, placeholder keys, `--add-host` for the blocked hosts (as `scripts/e2e-ci.sh:25`, `:49-52`), a published loopback port.
5. With the Admin placeholder key: `GET /api/v1alpha1/mods/browse`, `GET /api/v1alpha1/mods/gameversions`, `GET /api/v1alpha1/mods/lookup/e2estub`, `POST /api/v1alpha1/mods` with `{"slug": "e2estub"}` (it installs into the throwaway container only), `GET /api/v1alpha1/mods/lookup/nosuchmod`.
6. Evidence to record: the replay log has `served` lines for `/api/mods`, `/api/gameversions`, `/api/mod/e2estub` and `/download?fileid=1`, and `no_recording GET /api/mod/nosuchmod`; the last API call answered 502; the API log has one `mod_db_url_overridden` (scheme `http`, the replay's host) and no `mod_api_connection_error` and no `mod_download_failed` (a call to a blocked host would log one of them); the install answered 200.
7. The refusal: the same `docker run` without `VS_DEBUG` exits non-zero, its output names `VS_MOD_DB_URL` and `VS_DEBUG=true`, and contains neither the placeholder keys nor the address.
8. Remove both containers, the network and the temporary directory.

Do not start a game server in these containers, and do not use the dev stack or `./data`.

### The recording script (Task 3.1)

`scripts/moddb-record.py`, standard library only (`urllib.request`, `json`, `argparse`). `just record-moddb *ARGS` runs it with the Python that mise provides.

- It reads `web/e2e/fixtures/moddb/manifest.json`, fetches each entry's `request` from the base address (default `https://mods.vintagestory.at`; `--base-url` changes it, which is how the script test points it at a local replay), applies the entry's trimming, and writes the entry's file and its new `recorded` date (UTC, `YYYY-MM-DD`).
- `--only <request>` (repeatable) records only those entries and leaves every other file and date untouched. Without it, everything is recorded.
- Requests are unauthenticated `GET`s, one at a time with a short pause between them, a timeout, and a fixed generic `User-Agent` (`moddb-fixture-recorder`) that holds no host name, user name, key or version. The script reads no environment variable and no file but the manifest and the old recordings, so nothing about a developer's instance can reach a request or a recording. If the mod database refuses that `User-Agent`, stop and ask; do not imitate a browser.
- A request that fails, or answers with something that is not JSON, stops the run with a message before any file is written (fetch everything first, then write).
- Output is written with `json.dumps(..., indent=1, ensure_ascii=False, sort_keys=False)` and a final newline, so a refresh gives a readable diff and key order stays the mod database's.
- **The field report.** Before a file is replaced, the script computes the set of key paths in the old and the new answer, with list positions collapsed (`mod.releases[].fileid`, `mods[].lastreleased`), and prints per request the paths that appeared (`+`) and disappeared (`-`), or "no change in fields". For a request with no earlier file it prints "first recording". Because trimming removes list elements and never keys, the report shows changes in the mod database's shape, not changes caused by the trimming.

**Trimming.** The manifest states it, and the script applies only what the manifest states:

- `"trim": "none"`: the answer as returned.
- `"trim": "listing"` (for `/api/mods`): keep a mod when its slug list (`urlalias` or a `modidstrs` entry) is in the manifest's `listing.keep_slugs`, or when one of `listing.keep_terms` occurs, ignoring case, in its `name`, `summary`, `author` or a tag (the fields the API's own search reads, `search_mods`, `services/mod_api.py:1090`; re-check them there and keep the rule at least as wide as the search); drop the rest. Kept mods are unchanged and stay in the returned order. The full listing has more than 9,000 mods; with the terms below the recording holds a few hundred. Keeping every match of a term matters: a search for that term then returns the same mods from the recording as from the live listing on the recording day.
- `"trim": "listing-subset"` (for `/api/mods?gameversion=<id>`): keep the mods whose `modid` is in the recorded `/api/mods` file.
- `"trim": "releases-first-N"` (for `/api/mod/<slug>`, optional): keep the first N releases (they are newest first). Use it only where a spec does not need the older releases; `instruments` needs all of its releases (three mod IDs in one entry).

The script prints, after trimming the listing, how many mods it kept in total and per term, and fails if the total is under 41 (three browse pages of 20, which `mod-browse-name-sort.spec.ts:150` needs).

No value inside a kept element is edited. Image and link URLs stay as the mod database returned them (ADR-9 decision 9).

### What to record (Task 3.3)

Manifest shape (`web/e2e/fixtures/moddb/manifest.json`):

```json
{
  "source": "https://mods.vintagestory.at",
  "listing": { "keep_slugs": ["carryon", "..."], "keep_terms": ["food", "farm", "carry on", "jewelry", "instruments"] },
  "requests": [
    { "request": "/api/mods", "file": "api-mods.json", "trim": "listing", "recorded": "", "specs": ["mod-browse-name-sort", "..."] },
    { "request": "/api/gameversions", "file": "api-gameversions.json", "trim": "none", "recorded": "", "specs": ["mod-browse-state"] },
    { "request": "/api/mod/carryon", "file": "api-mod-carryon.json", "trim": "none", "recorded": "", "specs": ["install-file-conflict", "mod-install-release"] }
  ]
}
```

Starting list, from reading the ten specs at 7f04ea2:

| Request | Needed by |
|---|---|
| `/api/mods` | every browse test; terms: `food` (`mod-browse-state.spec.ts:25`, `mods-navigation.spec.ts`), `farm` (`mod-browse-name-sort.spec.ts:172`), `carry on` (`mod-install-release.spec.ts`, `browse-game-version.spec.ts:176`), `jewelry` (`mod-detail-bad-data.spec.ts`), `instruments` (`installed-status.spec.ts:151`) |
| `/api/gameversions` | the game version filter (`mod-browse-state.spec.ts:55-61`) |
| `/api/mods?gameversion=<id>` | the same test picks the first version in the filter; `<id>` is that version's tag ID in the recorded `/api/gameversions`. Find which the page asks for from the replay log |
| `/api/mod/carryon` | `install-file-conflict.spec.ts:94`, `mod-install-release.spec.ts` |
| `/api/mod/instruments` | `installed-mod-any-modid.spec.ts`, `mod-install-release.spec.ts` |
| `/api/mod/canjewelry` | `mod-detail-bad-data.spec.ts:56` |
| `/api/mod/betterruins` | `mod-detail-media.spec.ts:380` |
| `/api/mod/<slug>` for each card a test opens from the grid | `mods-navigation.spec.ts:62`, `:91` (first card of `?q=food&sort=downloads`); `mod-detail-bad-data.spec.ts:77` (first card of `?q=jewelry&sort=downloads`); `mod-browse-state.spec.ts:143` (card 15 of page 2 of the filtered `food` state, `:79-91`) |

The last row's slugs are fixed once the listing is recorded: run the second pass, read the `no_recording` lines in the replay log, add those requests, and record them with `--only` so the listing (and with it the cards) does not move. The API may look a mod up by a key other than the slug shown; record what the log shows.

A recorded "not found" answer is a recording like any other (the mod database answers `{"statuscode": "404"}` with HTTP 200; `api/tests/fixtures/moddb/mod_not_found.json`).

`api/tests/fixtures/moddb/` (the API unit tests' fixtures) is a different set with different trimming and is not touched or reused.

### The mod API reference (Task 3.5, `VSS-zhv3`)

`agentdocs/vintagestory-modapi.md` today lists `screenshots` as `[...]` (`:64`), has a "Screenshot Object" section (`:297`), and does not mention `trailervideourl` or the `gameversion` filter. Add, each checked against a recording and with the recording's file named as the source:

- `mod.screenshots[]`: `fileid`, `filename`, `mainfile`, `thumbnailfilename`, `created` (from `api-mod-betterruins.json`); correct the existing section where it differs.
- `mod.trailervideourl`: often `""` or `null`; a `youtube-nocookie.com/watch` URL does not load and the embed URL must be rebuilt (see `services/mod_media.py`).
- `/api/mods?gameversion=<tagid>` (from the recorded filtered listing) against the undocumented `?gameversions[]=` form, which the bead says gives different results. The second form is not recorded and not used by the API; one manual `curl` at writing time may confirm the difference, and the document then says "checked by hand on <date>". If it cannot be confirmed, say that the form is not used and was not checked.
- `issuetrackerurl` and `wikiurl`: documented at `:51-52`, `:263-264`; add that this project's API does not read them.
- In "Base URL" (`:3`): one sentence that the manager's base address is the setting `VS_MOD_DB_URL`.

Do not rewrite the rest of the document.

### The second pass (Task 4.1)

`scripts/e2e-ci.sh` after Story 20.5. Keep everything the first pass does (container, seeding, tags, the health check before pytest, the API E2E tests). Add:

1. Constants at the top, next to the existing ones (`:16-29`): `REPLAY_CONTAINER="vintagestory-moddb-replay-e2e"`, `MODDB_CONTAINER="vintagestory-manager-e2e-moddb"`, `NETWORK="vintagestory-e2e"`, `REPLAY_PORT=8099`, `MODDB_DIR="web/e2e/fixtures/moddb"`, `MODDB_PORT="${E2E_MODDB_PORT:-18081}"`, `LIVE_ONLY_TAGS='@moddb-live|@install'`. Add `moddbcdn.vintagestory.at` to `BLOCKED_HOSTS` (`:25`): the API never needs the image host in CI, and a download that was redirected there would then fail at once in either container.
2. `cleanup` (`:31-41`): on failure print the last 200 log lines of each of the three containers that exists; always remove the three containers, then the network, then the temporary directory. Removal of something that does not exist is not an error. Remove leftovers of an earlier, killed run before creating anything (as `:55` does for the first container).
3. After the first pass's Playwright run and the API E2E tests: `docker network create "$NETWORK"`.
4. The replay container: from `$IMAGE`, on the network, with `--no-healthcheck` (the image's health check probes the API's port), no published port, no `--add-host`, command `python3 /tmp/moddb-replay.py --dir /tmp/moddb --port "$REPLAY_PORT"`. Use `docker create`, `docker cp` the script and `$MODDB_DIR` in, then `docker start` (the pattern of `:56-66`; no bind mount). Wait until it answers `/healthz` (from inside, `docker exec ... python3 -c "import urllib.request; ..."`, as the image's own health check does, `Dockerfile:81-82`), with a time limit and an error message.
5. The second API container: as the first (`:56-63`) with `--network "$NETWORK"`, `-p "127.0.0.1:$MODDB_PORT:8080"`, `-e VS_DEBUG=true`, `-e VS_MOD_DB_URL="http://$REPLAY_CONTAINER:$REPLAY_PORT"`, the same placeholder keys, the same seeded `serverconfig.json` and nested directory, and the same `--add-host` list. Wait for its `/healthz` with the existing loop (make the loop a function taking the URL).
6. The second Playwright run: `E2E_BASE_URL` and `PLAYWRIGHT_BASE_URL` set to the second container, `E2E_MODDB_REPLAY=1`, and `bun run test:e2e --grep '@moddb' --grep-invert "$LIVE_ONLY_TAGS" "$@"`. A failure sets `failed=1` like the first pass; the second pass runs even when the first failed, so one run reports both.
7. Reports: the second run must not overwrite the first run's `web/playwright-report/` and `web/test-results/`, or a failed first pass would lose its report. Give the second run its own directories (`--output test-results-moddb` and the HTML reporter's output directory variable; check the name for the installed Playwright, 1.65.1, in its documentation), add both to the artifact paths in `.github/workflows/ci.yml` (`:106-108`) and to `.gitignore` next to the entries Story 20.3 added.
8. Arguments: `just test-e2e-ci e2e/settings-as-saved.spec.ts` passes a spec to both runs, and the second then finds no test. Pass `--pass-with-no-tests` to both runs when arguments were given, and say in the usage comment (`:9-11`) that arguments apply to both passes.
9. After the second run, fail the script if the second API container's log holds `mod_api_connection_error` or `mod_download_failed`: either means a mod database request did not follow the setting and went to a blocked host. Print the replay container's `no_recording` lines, if any, at the end of a failed run.
10. Update the header comment (`:2-7`) to describe both passes.

The script still never reads a `VS_API_KEY*` from the caller, never touches the dev stack, `./data` or `dev/`, and starts no game server.

`.github/workflows/ci.yml` needs no new step: `just test-e2e-ci` runs both passes. The job list pinned in `scripts/tests/test-release.sh:319-325` does not change.

### Images (Task 4.2)

`web/e2e/config-js.ts` gains:

```ts
/** In the replay run (scripts/e2e-ci.sh sets E2E_MODDB_REPLAY=1), answer the mod database's
 *  image host with a 1x1 PNG and abort any request to the mod database itself, so the run
 *  sends nothing to the live hosts. Does nothing in any other run. */
export async function serveModImagePlaceholders(page: Page): Promise<void>
```

- When `process.env.E2E_MODDB_REPLAY !== '1'` it returns at once: a local run against the dev stack loads real images as today (AC 15).
- Otherwise `page.route('https://moddbcdn.vintagestory.at/**', ...)` fulfils with a 1x1 PNG held as a base64 constant in the file (`contentType: 'image/png'`), and `page.route('https://mods.vintagestory.at/**', (route) => route.abort())`.
- Call it in the `beforeEach` (or the helper that sets a page up, for example `readOnly` in `mod-detail-media.spec.ts`) of each spec that keeps a `@moddb` test, next to `serveConfigKey`. A test that opens a second page (`context.newPage()` in `mods-navigation.spec.ts:91` and `mod-browse-state.spec.ts:177`) calls it for that page too, or the helper is given the context; choose one and use it in all specs.
- `mod-detail-media.spec.ts` already stubs images for its untagged tests; do not change those.
- A mod's trailer is an embed on another host. Check in the replay run whether a detail page requests it without a click (Playwright's `page.on('request')` in a scratch run, not committed); if it does, route that host to an empty answer in the same helper and say so in the README.

### Guards in test-e2e-ci.sh (Task 3.4, 4.3)

In the file's style (`assert_eq`, `pass`, `fail`, `yq`):

Manifest rows:

- `web/e2e/fixtures/moddb/manifest.json` parses; every entry has `request`, `file`, `trim`, a `recorded` date of the form `YYYY-MM-DD`, and at least one spec; every named file exists and parses as JSON; every `.json` file in the directory other than the manifest is named by exactly one entry; every named spec exists as `web/e2e/<name>.spec.ts`.
- No recording holds the replay's address or `localhost`/`127.0.0.1` (the answers were not rewritten), and the listing holds at least 41 mods.

Script rows:

- `LIVE_ONLY_TAGS='@moddb-live|@install'` exactly, and the second run uses `--grep '@moddb'` with `--grep-invert "$LIVE_ONLY_TAGS"`.
- `web/e2e/README.md` explains `@moddb-live` (extend the tag loop at `:27-29` of the test).
- The second API container gets `VS_DEBUG=true` and a `VS_MOD_DB_URL` that starts with `http://$REPLAY_CONTAINER`; the first container's `docker create` block has neither.
- `BLOCKED_HOSTS` holds `mods.vintagestory.at`, `api.vintagestory.at`, `cdn.vintagestory.at` and `moddbcdn.vintagestory.at`, and both API containers are created with the `add_hosts` list.
- `cleanup` removes both API containers, the replay container and the network (a `docker rm -f` naming each, a `docker network rm`).
- The script sets `E2E_MODDB_REPLAY=1` only for the second run, and `web/e2e/config-js.ts` reads that name.
- No workflow under `.github/workflows` has a `schedule:` trigger that runs E2E tests (AC 15).

### Script tests (Task 2.2, 3.2)

`scripts/tests/test-moddb-replay.sh` (uses `scripts/tests/lib.sh`; picks a free port; kills the server in a trap; needs only `python3` and `curl`): a made-up directory in `mktemp -d` with a manifest of three entries (a JSON answer, an answer with a query, a non-JSON file with its own `content_type` and `status`). Checks: the JSON answer comes back byte for byte with 200; the query entry matches with its parameters in another order; an unknown path gives 404 and a body that holds the path and query; `/../manifest.json` and `/manifest.json` give 404; `POST` gives 405; the log holds a `served` and a `no_recording` line; the server refuses to start on a manifest that names a missing file, a file with `/` in its name, or the same request twice.

`scripts/tests/test-moddb-record.sh`: a made-up "live" directory served by the replay server on a local port; a manifest copy and an output directory in `mktemp -d` (the script takes `--manifest` and `--out` for this; the defaults are the real paths). Checks: `listing` keeps the named slug and the term matches and drops the rest, in order; `listing-subset` keeps only the listing's mods; `releases-first-N` keeps N; `none` is byte-equivalent JSON; a second run after a field was added to and another removed from the "live" answer prints the `+` and `-` lines with collapsed list positions; `--only` rewrites one file and leaves the others' bytes and dates; a request that fails writes nothing; the request the replay logged carries the fixed `User-Agent` (have the replay log it when started with `--log-user-agent`, or check with a few lines of Python in the test). The test never calls the live mod database, and the real `web/e2e/fixtures/moddb/` is not written.

### Lint for the two Python scripts (Task 2.2)

`just lint-scripts` covers bash only (`Justfile:151-153` at 7f04ea2; Story 20.3 widened it). Add `ruff check` and `ruff format --check` over `scripts/*.py` to that recipe, using the API project's ruff and its configuration (`api/pyproject.toml:36`, line length 100), for example `mise exec -C api -- uv run ruff check --config pyproject.toml ../scripts`. Check that the command fails on a deliberately unformatted line before relying on it. Write both scripts with full type hints and try `uv run pyright ../scripts/moddb-replay.py ../scripts/moddb-record.py` from `api/`; if it runs with 0 errors by a path argument alone, add it to the recipe as well; if it needs configuration changes, leave it out and say so in Completion Notes. Semgrep (Story 20.4) already scans `scripts`.

### The 31 tests (Task 5)

Listed with `bunx playwright test --list --grep '@moddb'` at 7f04ea2: 31 tests in 10 files. "Planned" is the decision from reading each test; Task 5.1 confirms it by running and fills "Result".

| # | Spec and line | Test | Planned | Why | Result |
|---|---|---|---|---|---|
| 1 | `browse-game-version.spec.ts:168` | live: the cards agree with the browse response | `@moddb-live` | named by ADR-9 decision 12; its point is a live comparison, and on the CI stack `game_version` is null so it would check nothing || `@moddb-live` (retagged, not run in CI) |
| 2 | `install-file-conflict.spec.ts:89` | detail page shows the refusal | CI | `carryon` lookup; the install POST is stubbed || CI: pass (3 of 3 local runs) |
| 3 | `install-file-conflict.spec.ts:103` | browse card shows the refusal | CI | listing; POST stubbed || CI: pass |
| 4 | `installed-mod-any-modid.spec.ts:96` | installed state for `vsinstrumentsbase` | CI | `instruments` lookup; installed list stubbed || CI: pass |
| 5 | `installed-mod-any-modid.spec.ts:96` | installed state for `vsinstruments` | CI | same || CI: pass |
| 6 | `installed-mod-any-modid.spec.ts:125` | install flow when no mod ID is installed | CI | same || CI: pass |
| 7 | `installed-status.spec.ts:151` | the Instruments card shows Installed | CI | listing search; installed list stubbed || CI: pass |
| 8 | `installed-status.spec.ts:243` | an installed mod has a real update status | `@install` (stays) | installs a real mod || `@install`, not in CI; dev stack: pass |
| 9 | `mod-browse-name-sort.spec.ts:112` | first page alphabetically | CI | needs 20 or more mods || CI: pass |
| 10 | `mod-browse-name-sort.spec.ts:136` | pages 1, 2 and a later page | CI | needs 3 or more pages || CI: pass |
| 11 | `mod-browse-name-sort.spec.ts:171` | search with Name (A-Z) | CI | more than one `farm` match || CI: pass |
| 12-15 | `mod-browse-state.spec.ts:143` (four) | Back to Browse / breadcrumb / tab / browser back keep the state | CI | `food` + side + type + first game version + page 2 with more than 8 cards; the opened card's lookup || CI: pass (all four); the opened card is `composter` (recorded with `--only`) |
| 16 | `mod-browse-state.spec.ts:156` | refresh keeps the state | CI | same listing || CI: pass |
| 17 | `mod-browse-state.spec.ts:165` | a detour through Installed | CI | same || CI: pass |
| 18 | `mod-browse-state.spec.ts:177` | a copied browse link | CI | same || CI: pass after a fix of the test: the new page gets `serveConfigKey` and `pretendServerInstalled` (routes on `page` do not reach a new page; on a stack with no game server it showed no Mods content) |
| 19 | `mod-detail-bad-data.spec.ts:56` | releases that have no file | CI | `canjewelry` lookup; the recording keeps the releases with `fileid: null` || CI: pass |
| 20 | `mod-detail-bad-data.spec.ts:77` | Back to Browse on a failed mod | CI | `jewelry` search; first card's lookup || CI: pass (the failing lookup is stubbed; no recording needed) |
| 21 | `mod-detail-media.spec.ts:380` | the live betterruins lookup passes only CDN images | CI | it checks the API's allow-list on real values, which is what unchanged recordings are for (ADR-9 decision 9); drop "live" from its title and comment || CI: pass; "live" dropped from the title and comment |
| 22 | `mod-install-release.spec.ts:133` | lookup reports the install mod ID | CI | `carryon`, `instruments` lookups || CI: pass |
| 23 | `mod-install-release.spec.ts:143` | detail page preselects the newest stable release | CI | POST stubbed || CI: pass |
| 24 | `mod-install-release.spec.ts:179` | Instruments lists only instruments releases | CI | all `instruments` releases || CI: pass |
| 25 | `mod-install-release.spec.ts:195` | browse card installs the newest stable release | CI | `carry on` search || CI: pass |
| 26 | `mod-install-release.spec.ts:250` | a version of another mod ID is refused | `@install` (stays) | real install path || `@install`, not in CI; dev stack: pass |
| 27 | `mod-install-release.spec.ts:293` | a plain install of carryon | `@install` (stays) | installs a real mod || `@install`, not in CI; dev stack: skipped by its own guard (the mod was already installed there) |
| 28 | `mods-navigation.spec.ts:62` | Browse is the active tab on a detail page | CI | `food` search; first card's lookup || CI: pass; the first card is `primitivesurvival` (recorded with `--only`) |
| 29 | `mods-navigation.spec.ts:91` | detail page opened directly | CI | same, second page || CI: pass after the same fix as 18 (the directly opened page gets the two routes) |
| 30 | `mods-navigation.spec.ts:109` | a link past the last page | CI | `food` search || CI: pass |
| 31 | `mods-navigation.spec.ts:137` | a search without results | CI | listing only || CI: pass |

Planned counts: 27 run in CI on recordings, 1 `@moddb-live`, 3 `@install`. With Story 20.5's 119 the CI set becomes 146 of 150 tests. Record the real counts in Completion Notes and in the README.

Rules for the decisions:

- `@moddb` now means "needs mod database answers, recorded or live". `@moddb-live` replaces `@moddb` on a test (the first pass's pattern `@moddb` still leaves it out). `@install` tests keep both of their tags.
- Test 1 is a single test inside a describe that has untagged tests; change only that test's tag (`:167-168`) and its comment.
- If the filtered `food` state of tests 12 to 18 has too few mods on the recording day for a second page with more than 8 cards, that is a property of live data too; do not weaken the test. Report it and ask before changing the search term.
- A test that passes only because the CI stack has no game server (for example a `null` game version) is still a pass on recordings if what it asserts was exercised; say so in the "Result" column where it applies.
- Update each spec's header comment where it says "live" or "Network access to the public mod database" for a test that now also runs on recordings.

### README for the E2E tests (Task 5.5)

`web/e2e/README.md` (55 lines at 7f04ea2; Story 20.5 edits it first). Change:

- "Two ways to run them": `just test-e2e-ci` runs two passes; say what each starts and that neither can reach the mod database, its image host or the vendor's version API.
- The tag table: `@moddb` "mod database answers, recorded or live (runs in CI on recordings)"; new row `@moddb-live` "the live mod database: the test compares with live data" with its example; `@install` unchanged. The sentence "CI leaves out every test that carries one of these tags" becomes true for `@moddb-live`, `@install` and `@game-server` only.
- New section "Recorded mod database answers": where they are, what the manifest holds, that the answers are real and trimmed and hold only public mod database data, how the replay answers and what a `no_recording` line means, `just record-moddb` and `--only`, the field report, and when to refresh: when a live run (`just test-e2e-web`) fails on data, and before a release that changes mod database handling. A refresh is a normal pull request.
- "Helpers": `serveModImagePlaceholders`.
- The counts: how many tests each pass runs and which stay local-only.

### Not changed (do not "fix" these here)

- `MOD_MEDIA_HOSTS`, the link rules, `extract_slug`, and every `mods.vintagestory.at` link in `web/src`: fixed by design (ADR-9 decision 3).
- The API's caches (the listing in memory, downloads on disk by file ID) do not look at the address. The README says to use an address that serves the same database; no cache key changes.
- `_read_debug_from_env` and the run-time debug toggle.
- The environment table in `_bmad-output/planning-artifacts/architecture/project-structure-boundaries.md` (`:466-468`): Story 20.7 adds `VS_MOD_DB_URL` there.
- `api/tests/fixtures/moddb/` and the API unit tests' literal `https://mods.vintagestory.at/...` mocks.
- `docker-compose.yaml`, `docker-compose.dev.yaml`, the `Dockerfile`: no change. The replay script is copied into a container at run time and is not part of the image.
- No scheduled workflow, and no workflow that calls the live mod database.
- `just test-e2e-web`: unchanged; it sets no `VS_MOD_DB_URL` and no `E2E_MODDB_REPLAY`.
- The first pass of `scripts/e2e-ci.sh`, except the one host added to `BLOCKED_HOSTS`.
- No new npm or Python dependency: both scripts use the standard library only, and the specs use Playwright as it is.

### API contract changes

For the pull request and the release note (`sprint-change-proposal-2026-11-17-epic-20.md`, section 2):

| Where | Change | Kind |
|---|---|---|
| `VS_MOD_DB_URL` (new, optional) | The base address the API uses for mod database requests (`<base>/api`) and mod downloads (`<base>/download`). Default `https://mods.vintagestory.at`. Must be an `https` URL with a host and nothing else; `http` is accepted only with `VS_DEBUG=true`; a bad value stops start-up with an error naming the setting | Added setting |
| Start-up log | New warning `mod_db_url_overridden` (`scheme`, `host`) when the address is not the default | Added |
| Start-up errors for any setting | The error no longer prints the refused value (`hide_input_in_errors`) | Changed text of an error |
| Image host allow-list, link rules, the web UI's links to mod pages | Unchanged; they do not follow the setting | None |

No response field, route, status code or error code changes. Nothing is breaking.

### ADR against the code

- **ADR-9 decision 6**, "a request it has no recording for is answered 404 with a body that names the URL, which the API turns into its usual 502": true only when the body is not a JSON object. `get_mod` does not require HTTP 200 (`mod_api.py:477`), and a JSON object with `"statuscode": "404"` would read as "mod not found" (a 404 from the manager, hiding the missing recording). The story makes the body plain text.
- **ADR-9 decision 4**, "the same behaviour as a bad `VS_CSP_MODE`": a guard that depends on `VS_DEBUG` cannot be an ordinary single-field check. Done as a model-level validator it would print every setting, API keys included, in the error. The story uses a field validator that reads `debug` from the already-validated data and hides inputs in errors.
- **ADR-9 decision 4** lists the refused forms; `urlsplit` alone also lets through white space inside the host, a silently removed tab and an empty port. The story refuses them.
- **ADR-9 decision 6**, "all removed by its existing cleanup": the cleanup trap exists but removes one container; it is extended.
- **ADR-9 Consequences**, "up to 28 more tests": the plan is 27, because the test ADR-9 decision 12 names as live-only is one of the 31.
- ADR-9 does not block the image host for the API containers; the story adds `moddbcdn.vintagestory.at` to the blocked hosts so AC 10 holds for a redirected download as well.

### Testing Requirements

- API: the rows in "API tests"; `just test-api` green; coverage of the new validator's every branch (each message, each accepted form).
- Scripts: `just test-scripts` runs the two new test files and the extended `test-e2e-ci.sh`; `just lint-scripts` covers the new bash and Python.
- E2E: this story changes no page, so it adds no new spec. Its E2E work is the second pass (Tasks 4 and 5) on the throwaway containers and the dev stack check of Task 5.4. No test starts or stops the game server. No screenshot is needed; if one is taken for a failure report it must not show a server name or password (the CI containers hold only the fixture's made-up values).
- Real state: only the `@install` tests change real state, only on the dev stack, and they restore it under their snapshot guards (`mod-install-release.spec.ts:221-246`, `installed-status.spec.ts`). Nothing in this story adds a state-changing test.
- Tests must not write into `dev/`, `./data` or `web/e2e/fixtures/` (the recorder's test writes to a temporary directory).

### Security Requirements

- The setting decides where mod files are downloaded from, and the game server runs them. The guard, the warning at every start and the documentation are the controls; do not relax any of them to make a test easier (the second pass uses `VS_DEBUG=true`, not a weaker guard).
- An error or a log line never prints the configured value in full, a user name, a password or an API key. The warning carries scheme and host only.
- The replay server serves only files its manifest names, binds inside a private Docker network in CI, and is never part of the image.
- The recorder sends nothing but unauthenticated `GET`s for the manifest's requests, with a fixed `User-Agent`.
- Public repository: recordings hold only what the mod database's public API returned (mod names, descriptions, authors' public names). No key, host name, server name or path of any instance appears in a recording, the manifest, a test or a log pasted into this file.
- Semgrep: a verified false positive may carry an inline `# nosemgrep: <rule-id> — <reason>`; no other suppression.

### Development Commands

```bash
just test-api tests/test_config.py -k ModDbUrl -xvs
just test-api tests/test_mod_api.py -k ModDbUrl
just test-scripts test-moddb-replay.sh test-moddb-record.sh test-e2e-ci.sh
just lint-scripts
just record-moddb                      # needs network; rewrites web/e2e/fixtures/moddb/
just record-moddb --only /api/mod/carryon
just test-e2e-ci                       # both passes on throwaway containers
just check
```

### Previous Story Intelligence

- Story 19.7 built `scripts/e2e-ci.sh` and its guard. Its review found that a container that died could pass the run (pytest passes on all-skip); the script now re-checks `/healthz`. Keep that check for the first container, and wait for the second container's `/healthz` before its run.
- Story 19.7 counted tests with `bunx playwright test --list`; `--list` rewrote the tracked `web/playwright-report/index.html` at planning time for this story too. After Story 20.3 the directory is ignored; until then restore it before committing.
- Story 19.7's script unsets `VS_API_KEY` before the tests so no developer key reaches them (`scripts/e2e-ci.sh:83`); the second pass runs in the same shell and keeps that.
- Story 19.2: `serveConfigKey(page, apiKey)` in `web/e2e/config-js.ts` is the only way a spec chooses its key; the new helper sits beside it.
- Stories 18.x and 19.x reviews: a `feat` subject must describe something an admin can see (Task 1's does; nothing else here is `feat`); a completion note must be true of the code (paste real counts and durations, not the planned ones); tests must not write into `dev/`.
- Story 20.1 (before this one): the API is formatted and `just lint-api` checks it; format the API files this story changes.
- Story 20.5 (directly before this one): it seeds a nested directory, exports the container name for its new test, may cache the browsers, and edits the README. Rebase the second pass onto its script; the second API container gets the same seeding, and the new-directory test stays in the first pass (it is untagged).

### Git Intelligence

- Base for line references: `7f04ea2` (`docs(epic-20): record the maintainer's answers and use a mod database address setting`), on `3f1c6ea` (`main` after Epic 19, `v0.1.0-rc.5`).
- `cliff.toml:26` shows only the scopes `api`, `web` and `docker` in release notes and hides story scopes (`:38`); that is why Task 1's subject is `feat(api): ...` and not `feat(story-20.6/task-1): ...`.
- `scripts/tests/test-docker-context.sh:19-22` fails on an action not pinned by commit; this story adds no action.

### Project Structure Notes

New files: `scripts/moddb-replay.py`, `scripts/moddb-record.py`, `scripts/tests/test-moddb-replay.sh`, `scripts/tests/test-moddb-record.sh`, `web/e2e/fixtures/moddb/manifest.json` and its recordings.

Changed files: `api/src/vintagestory_api/config.py`, `services/mod_api.py`, `services/mods.py`, `main.py`; `api/tests/conftest.py`, `test_config.py`, `test_mod_api.py`, `test_mod_service.py`, `test_main.py`, `test_mod_media.py`; `scripts/e2e-ci.sh`, `scripts/tests/test-e2e-ci.sh`; `Justfile`; `.github/workflows/ci.yml` (artifact paths only); `.gitignore`; `web/e2e/config-js.ts` and the specs with `@moddb` tests; `web/e2e/README.md`, `web/playwright.config.ts` (comment), `README.md`, `.env.example`, `agentdocs/vintagestory-modapi.md`.

`scripts/` holds bash only today; two Python files there are new for the project. They are stand-alone tools with no import from `api/`, which is why they are not under `api/src`.

### References

- `_bmad-output/planning-artifacts/epics.md`, "Story 20.6: The Mod Database E2E Tests Run in CI" (ACs, tasks, beads, FRs)
- `_bmad-output/planning-artifacts/architecture/epic-20-tooling-and-test-health.md`, ADR-9 (decisions 1 to 14), "Facts Checked in the Code" (E2E), ADR-8 (Story 20.5's changes to the same script)
- `_bmad-output/planning-artifacts/architecture/epic-19-api-security-and-mod-file-safety.md`, ADR-12 (link rules), ADR-13 (mod database answers are checked), ADR-14 decision 9 (replaced by Epic 20 ADR-9)
- `_bmad-output/planning-artifacts/prd.md`, FR252-FR254, FR258, FR259 (`:814-816`, `:826-827`)
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-11-17-epic-20.md`, section 2 (contract table, release-note text)
- `web/e2e/README.md`, `scripts/e2e-ci.sh`, `scripts/tests/test-e2e-ci.sh`
- `project-context.md`, "Commit Message Format" (`:615-648`), "No Silent Failures Rule"
- Beads: `bd show VSS-571h`, `bd show VSS-zhv3`; `bd memories backlog-drawdown`, `bd memories semgrep-exceptions`

## Dev Agent Record

### Agent Model Used

claude-opus-5-5 (Claude Code, BMAD dev-story, non-interactive), 2026-11-17

### Debug Log References

**Task 2.3, the proof in the built image** (2026-11-17; image built from this branch at Task 2 with `docker build --platform linux/amd64 -t vintagestory-server:e2e .`). A made-up directory in a `mktemp -d` under the session scratch directory: a manifest, `api-mods.json` (two made-up mods), `api-mod-e2estub.json` (one release, `fileid` 1), `api-gameversions.json` (`1.22.0`, `1.21.6`) and `e2estub_1.0.0.zip` (a `modinfo.json` only, `content_type: application/zip`).

```bash
docker network create vss-206-net
docker create --name vss-206-replay --platform linux/amd64 --network vss-206-net --no-healthcheck \
    vintagestory-server:e2e python3 /tmp/moddb-replay.py --dir /tmp/moddb
docker cp scripts/moddb-replay.py vss-206-replay:/tmp/moddb-replay.py
docker cp "$P/moddb" vss-206-replay:/tmp/moddb
docker start vss-206-replay
docker create --name vss-206-api --platform linux/amd64 --network vss-206-net -p 127.0.0.1:18090:8080 \
    -e VS_DEBUG=true -e VS_MOD_DB_URL=http://vss-206-replay:8099 \
    -e VS_API_KEY_ADMIN=proof-admin-placeholder -e VS_API_KEY_MONITOR=proof-monitor-placeholder \
    -e VS_API_KEY=proof-admin-placeholder -e VS_DATA_DIR=/data \
    --add-host mods.vintagestory.at:127.0.0.1 --add-host api.vintagestory.at:127.0.0.1 \
    --add-host cdn.vintagestory.at:127.0.0.1 --add-host moddbcdn.vintagestory.at:127.0.0.1 \
    vintagestory-server:e2e
docker start vss-206-api
```

API calls with the placeholder Admin key: `GET /api/v1alpha1/mods/browse` 200, `GET /mods/gameversions` 200 (`["1.22.0","1.21.6"]`), `GET /mods/lookup/e2estub` 200, `POST /mods {"slug":"e2estub"}` 200 (`version 1.0.0`, `e2estub_1.0.0.zip`, installed into the throwaway container only), `GET /mods/lookup/nosuchmod` 502 `EXTERNAL_API_ERROR` ("VintageStory mod API returned invalid JSON").

Replay log (`docker logs vss-206-replay`):

```
moddb-replay: 4 recordings on 0.0.0.0:8099
served GET /api/mods
served GET /api/gameversions
served GET /api/mod/e2estub
served GET /api/mod/e2estub
served GET /download?fileid=1
no_recording GET /api/mod/nosuchmod
```

API log: exactly one `mod_db_url_overridden` (`scheme=http`, `host=vss-206-replay`, and the hint); `mod_download_complete fileid=1`; `mod_api_invalid_body endpoint=/mod/nosuchmod http_status=404`; no `mod_api_connection_error` and no `mod_download_failed` (count 0).

Refusal: the same `docker run` without `VS_DEBUG` exited 1 with

```
pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings
mod_db_url
  Value error, VS_MOD_DB_URL uses plain HTTP, which is for testing and needs VS_DEBUG=true. Use an https address. [type=value_error]
```

and its output held neither placeholder key nor the replay's host (grep count 0). Both containers, the network and the directory were removed; `docker ps -a` and `docker network ls` showed nothing `vss-206`.

**Task 4.2, trailer and other hosts** (a scratch spec, not committed; replay and API container as above on the real recordings, `E2E_MODDB_REPLAY=1`, `page.on('request')` on the detail pages of the six recorded mods and on `?q=food&sort=downloads`): no request to a YouTube host without a click (`betterruins` has a trailer), so the helper routes no trailer host. `moddbcdn.vintagestory.at` requests were answered by the placeholder route. Mod descriptions (the HTML `text`) embed images from other hosts, which the browser does load: `github.com`, `repository-images.githubusercontent.com`, `i.imgur.com` (betterruins, composter), `i.ibb.co` (primitivesurvival), an S3 bucket (carryon). They are not the mod database or its image host (AC 10), the helper does not route them, and the README says so (follow-up in Completion Notes).

**Task 4.4 / 5.1 / 5.3, local runs of `just test-e2e-ci`:**

- First run, before the card lookups were recorded: first pass 119 passed, API E2E 3 passed; second pass 25 passed, 3 failed. The replay's `no_recording` lines named `/api/mod/composter` and `/api/mod/primitivesurvival`; both were added to the manifest and recorded with `just record-moddb --only /api/mod/primitivesurvival --only /api/mod/composter` (the listing and the other files unchanged).
- Second run: 26 passed, 2 failed (the copied-link and the directly opened detail page tests: the new page had neither `serveConfigKey` nor `pretendServerInstalled`, so on a stack with no game server it showed no Mods content). Fixed in the two tests, not retagged.
- Failure run (`just test-e2e-ci --no-such-option`, both Playwright runs refuse the option): exit 1, the logs of all three containers and "(none)" for `no_recording` printed, then `docker ps -a` and `docker network ls` showed nothing of the run and the number of `$TMPDIR/tmp.*` directories was the same as before.
- Three runs in a row with `CI=1 just test-e2e-ci` (CI's retries and list reporter), after Task 5: each first pass 119 passed, API E2E 3 passed, second pass 27 passed, 0 flaky, 0 failed; the same 27 tests passed in each run (sorted lists compared). Wall time 3 min 10 s, 3 min 10 s, 3 min 9 s (local, image cached; the second pass took 55-56 s with one worker).
- One more run with the replay's log printed (a local edit of the script, reverted): every request was `served`, none `no_recording` (`/api/mods` 1, `/api/mods?gameversion=-281569466515455` 1, `/api/gameversions` 1, lookups of betterruins 1, canjewelry 2, carryon 5, composter 5, instruments 6, primitivesurvival 2).

**Task 5.4, the dev stack** (`docker exec vintagestory-manager-dev ... VintagestoryServer` found no game server process; `just docker restart` from this branch; `/healthz` `game_server: stopped`; no `mod_db_url_overridden` in its log): `cd web && mise exec -- bunx playwright test --grep '@moddb' --reporter=list` with no `E2E_MODDB_REPLAY`: 30 passed, 1 skipped (the plain carryon install, by its own guard: the mod is installed on that stack), 0 failed, 16.9 s. `GET /api/v1alpha1/mods` returned the same body before and after (`cmp`, same SHA-256).

### Completion Notes List

- Story created 2026-11-17 (create-story, non-interactive) and validated against the create-story checklist. Prototypes, run and discarded: the `mod_db_url` field with a validator and the two per-client addresses (`just test-api`: 3,334 passed, with and without `VS_MOD_DB_URL` in the environment); the guard's edge cases with `urlsplit` (found: white space inside the host, a removed tab and an empty port are accepted by `urlsplit`); what a failing model validator and a failing field validator print (found: the model validator prints every setting; `hide_input_in_errors` prints none). `bunx playwright test --list --grep '@moddb'` gave the 31 tests of the table. No container was started, no E2E test was run and nothing was recorded, so the "Planned" column, the list of requests to record and the size of the recordings are predictions that Tasks 3 and 5 confirm.

- Task 1: `VS_MOD_DB_URL` (`Settings.mod_db_url`, `DEFAULT_MOD_DB_URL`) with a field validator in the order of Dev Notes "The guard"; a port of `0` is refused as well (rule 3 asks for 1 to 65535 and `urlsplit` accepts 0). `hide_input_in_errors=True` on the settings model. `ModApiClient(mod_db_url=...)` builds `_api_url`/`_download_url`; `BASE_URL`/`DOWNLOAD_URL` are gone; the log's `endpoint` strips the configured prefix. `ModService(mod_db_url=...)` and `get_mod_service` pass `settings.mod_db_url`. `log_mod_db_url` logs `mod_db_url_overridden` (scheme, host) once from the lifespan. `conftest.py` drops `VS_MOD_DB_URL` before the app is imported. `just changelog` lists "**api:** Add VS_MOD_DB_URL to use a mirror of the mod database" under Features.
- Existing tests that changed (not in the story's list): the six `MagicMock` settings of `TestLifespanAutoStart` in `api/tests/test_main.py` get `mod_db_url = DEFAULT_MOD_DB_URL`. A `MagicMock` attribute is not equal to the default, so `log_mod_db_url` tried to parse it (11 tests failed); the mock now carries the real default, as it carries `data_dir`.
- API tests: 3,387 passed (53 new: 36 in `TestModDbUrl`, 8 in `TestModApiClientModDbUrl`, 4 in `TestLogModDbUrl`, 2 in `test_mod_service.py`, 3 in `TestRulesDoNotFollowModDbUrl`); also green with `VS_MOD_DB_URL=https://mirror.example` in the environment. The lifespan test is in `test_main.py` and uses `create_app` with a `tmp_path` data directory, as `test_app_factory.py` does, rather than the mocked lifespan.
- Red first: the config tests failed at collection without the implementation (checked by stashing `config.py`); the other new tests were written alongside the code in the same task and were not each run red first.
- Task 2: `scripts/moddb-replay.py` (standard library, typed); it loads every recorded file at start. `--log-user-agent` adds the User-Agent to each log line (used by the recorder's test). `scripts/tests/test-moddb-replay.sh`: 29 checks. `just lint-scripts` now also runs `ruff check`, `ruff format --check` (over `scripts/`, with the API's ruff and `pyproject.toml`) and `pyright` on the two Python scripts (by path from `api/`, strict as configured there, 0 errors and 0 warnings without any configuration change). Checked that `ruff format --check` fails on an over-long unformatted line before relying on it. Semgrep scans both scripts (listed in `--json` `paths.scanned`) with 0 findings.
- Task 3: `scripts/moddb-record.py` and `just record-moddb *ARGS` (`[positional-arguments]`, `"$@"`, with a case in `test-justfile-args.sh`). Options `--manifest`, `--out`, `--base-url`, `--only`, `--pause` (default 1 s), `--timeout`. Everything is fetched and trimmed before anything is written; the manifest's `recorded` dates are written back to the manifest. `scripts/tests/test-moddb-record.sh`: 29 checks, against the replay on a local port. The live mod database accepted the `moddb-fixture-recorder` User-Agent.
- Recordings (2026-11-17): 9 requests, 1,224,282 bytes (1.2 MB on disk). `keep_slugs` carryon, instruments, canjewelry, betterruins; `keep_terms` food, farm, carry, jewelry, instruments: the listing kept 772 mods (`slug` 4, `food` 577, `farm` 176, `carry` 32, `jewelry` 9, `instruments` 22). `carry` replaces the planned `carry on` because `install-file-conflict.spec.ts` searches `?q=carry` (and `carry` covers `carry on`). The first version in the filter is 1.22.7 (`tagid` -281569466515455); its listing kept 488 mods; 299 of them match `food` with side `both` and type `mod`, so page 2 of the `mod-browse-state` state has 20 cards. Two card lookups were added from the replay log: `composter` (`mod-browse-state`), `primitivesurvival` (`mods-navigation`). Every file parses; no file holds `localhost`, `127.0.0.1` or the replay's name (pinned in `test-e2e-ci.sh`).
- `agentdocs/vintagestory-modapi.md`: the base URL sentence, the `gameversion` filter (and `?gameversions[]=`, checked by hand on 2026-11-17 with one request each: 5,672 against 2,855 mods for 1.22.7), `trailervideourl`, the screenshot object checked against `api-mod-betterruins.json`, and that the API does not read `issuetrackerurl`/`wikiurl`.
- Task 4: `scripts/e2e-ci.sh` as Dev Notes "The second pass". Deviation: the first container's `docker create`, seeding and `/healthz` wait moved into two functions (`start_api_container`, `wait_healthy`) that both containers use; the first pass's arguments, seeding, tags and order are unchanged. `moddbcdn.vintagestory.at` added to `BLOCKED_HOSTS`. The second run's report directories (`PLAYWRIGHT_HTML_OUTPUT_DIR=playwright-report-moddb`, the variable of Playwright 1.65.1's HTML reporter, and `--output test-results-moddb`) are in the artifact paths, `.gitignore` and also `.dockerignore`, and `scripts/tests/test-check-coverage.sh` (Story 20.3's pin of those lists) pins the two new paths; that pin failed after the Task 4 commit and was fixed in a second Task 4 commit. `serveModImagePlaceholders(page)` sets its routes on the page's browser context, so a page a test opens later is covered; every spec with a `@moddb` test calls it in its set-up (in `mod-detail-media.spec.ts` inside the one `@moddb` test).
- Task 5: the 31 tests: 27 run in CI on recordings, 1 `@moddb-live` (`browse-game-version.spec.ts`, the live comparison), 3 `@install`. The CI set is 146 of 150 tests (119 + 27). Two tests fixed for a fault of their own (tests 18 and 29 in the table): their second page now gets `serveConfigKey` and `pretendServerInstalled`. No `test.skip`, no weakened assertion. Spec header comments no longer call the data "live" where the tests also run on recordings.
- No manual check is reserved for the maintainer in this story.
- Not done here (controller): Task 6.3 (push, pull request, the `E2E tests` job green twice on one commit, the run URL and the job time against 3 min 16 s at `3f1c6ea` and 3 min 06 s after Story 20.5, warm cache) and Task 6.5's pull request. Task 6.4: no bead was changed (`VSS-zhv3` and `VSS-571h` are still open), per the run's instructions.
- Follow-ups: (1) fixed in review (L-1), see below. (2) The recorded lookups (`/api/mod/<slug>`) have no `modidstrs` field, which `lookup_mod` reads for the response slug (it falls back to the requested slug); unchanged here.
- `just check`: green; Pyright 0 errors, 0 warnings; API 3,387 passed; web 3,307 passed in 132 files, 0 skipped; scripts all files passed (`test-e2e-ci.sh` 47, `test-moddb-record.sh` 29, `test-moddb-replay.sh` 29, `test-check-coverage.sh` 17, `test-justfile-args.sh` 44). `git diff 8742ff8 -- api/pyproject.toml api/uv.lock web/package.json web/bun.lock` is empty. After `just test-api` and `just test-e2e-ci`, `git status --short` showed nothing but `sprint-status.yaml`.

- Review (GLM-5.3-Flash, APPROVE, nothing above LOW; CI green on PR #183, run 44133676214: 119 + 3, replay pass 27, `E2E tests` 4 min 14 s). L-1 fixed in `1775ebb`: in the replay run `serveModImagePlaceholders` adds a context route, registered before the two explicit ones, that passes the manager's own requests (the `E2E_BASE_URL` host, `127.0.0.1`, `localhost`, and non-http URLs) through, answers every other image with the 1x1 PNG and aborts every other request. Proof, a scratch spec (not committed) on a replay and API container with the real recordings, `requestfinished`/`requestfailed` on six detail pages, two browse searches, Installed and the dashboard: every non-local request was an image (github.com, repository-images.githubusercontent.com, i.imgur.com, i.ibb.co, the S3 bucket, moddbcdn) answered by the route, none carried a `date` or `server` header, none was aborted; the same page without the helper showed those headers on every one (they went to the network). `CI=1 just test-e2e-ci`: 119 passed, API E2E 3 passed, replay pass 27 passed, 0 flaky, 3 min 16 s (the first try failed in `docker build` on a registry timeout before any test, unrelated). `test-e2e-ci.sh` pins the catch-all route (52 checks); `web/e2e/README.md` describes it and adds the `--host 127.0.0.1` hint for running the replay by hand. `just check` green: API 3,387, web 3,307 (0 skipped), Pyright 0/0. The info items (hostname guard, `hide_input_in_errors` for every setting, `0.0.0.0` bind) are unchanged.

### File List

New:
- `scripts/moddb-replay.py`
- `scripts/moddb-record.py`
- `scripts/tests/test-moddb-replay.sh`
- `scripts/tests/test-moddb-record.sh`
- `web/e2e/fixtures/moddb/manifest.json`
- `web/e2e/fixtures/moddb/api-mods.json`
- `web/e2e/fixtures/moddb/api-mods-gameversion-1.22.7.json`
- `web/e2e/fixtures/moddb/api-gameversions.json`
- `web/e2e/fixtures/moddb/api-mod-betterruins.json`
- `web/e2e/fixtures/moddb/api-mod-canjewelry.json`
- `web/e2e/fixtures/moddb/api-mod-carryon.json`
- `web/e2e/fixtures/moddb/api-mod-composter.json`
- `web/e2e/fixtures/moddb/api-mod-instruments.json`
- `web/e2e/fixtures/moddb/api-mod-primitivesurvival.json`

Modified:
- `api/src/vintagestory_api/config.py`
- `api/src/vintagestory_api/main.py`
- `api/src/vintagestory_api/services/mod_api.py`
- `api/src/vintagestory_api/services/mods.py`
- `api/tests/conftest.py`
- `api/tests/test_config.py`
- `api/tests/test_main.py`
- `api/tests/test_mod_api.py`
- `api/tests/test_mod_media.py`
- `api/tests/test_mod_service.py`
- `scripts/e2e-ci.sh`
- `scripts/tests/test-e2e-ci.sh`
- `scripts/tests/test-check-coverage.sh`
- `scripts/tests/test-justfile-args.sh`
- `Justfile`
- `.github/workflows/ci.yml`
- `.gitignore`
- `.dockerignore`
- `web/e2e/config-js.ts`
- `web/e2e/browse-game-version.spec.ts`
- `web/e2e/install-file-conflict.spec.ts`
- `web/e2e/installed-mod-any-modid.spec.ts`
- `web/e2e/installed-status.spec.ts`
- `web/e2e/mod-browse-name-sort.spec.ts`
- `web/e2e/mod-browse-state.spec.ts`
- `web/e2e/mod-detail-bad-data.spec.ts`
- `web/e2e/mod-detail-media.spec.ts`
- `web/e2e/mod-install-release.spec.ts`
- `web/e2e/mods-navigation.spec.ts`
- `web/e2e/README.md`
- `web/playwright.config.ts`
- `README.md`
- `.env.example`
- `agentdocs/vintagestory-modapi.md`
- `_bmad-output/implementation-artifacts/20-6-mod-database-tests-in-ci.md`

## Change Log

| Date | Change |
|---|---|
| 2026-11-17 | Story created and validated (create-story); status `ready-for-dev` |
| 2026-11-17 | Review L-1 fixed: the replay pass's browser reaches only the manager; status stays `review` |
| 2026-11-17 | Implemented (dev-story): Tasks 1 to 5, Task 6.1 and 6.2; status `review`. CI runs (6.3), beads (6.4) and the pull request (6.5) are left to the controller |
