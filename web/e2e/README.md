# E2E tests

Playwright tests against a running Docker stack (the API serving the built web UI).

## Two ways to run them

- `just test-e2e-ci` runs the set CI runs on every pull request, in two passes, and removes
  everything it started afterwards, also after a failure. It never touches the dev stack,
  `./data` or `dev/`, and starts no game server.
  - First pass: the tests with no tag (219) and the API's E2E tests, against a throwaway
    container (`vintagestory-manager-e2e` on `127.0.0.1:18080`) from the image, seeded with
    `fixtures/serverconfig.json`, the empty directory `Logs/Archive`, placeholder keys and
    no game server. It exports `E2E_CONTAINER` for the one spec that creates a directory in
    it.
  - Second pass: the `@moddb` tests that are not `@moddb-live` or `@install` (27), on
    recorded mod database answers (below). It starts a replay container
    (`vintagestory-moddb-replay-e2e`) and a second API container
    (`vintagestory-manager-e2e-moddb` on `127.0.0.1:18081`, seeded like the first) with
    `VS_DEBUG=true` and `VS_MOD_DB_URL` pointed at the replay, on a Docker network of their
    own (`vintagestory-e2e`). Its report goes to `playwright-report-moddb/` and
    `test-results-moddb/`, so a failed first pass keeps its own.

  Neither API container can reach the mod database, its image host
  (`moddbcdn.vintagestory.at`) or the vendor's version API: they resolve to loopback, so a
  call to one fails at once, and the script fails the run if the second container logs a
  mod database request that did not go to the replay. Pass Playwright arguments through,
  for example `just test-e2e-ci e2e/settings-as-saved.spec.ts`; they go to both passes,
  and a pass that then finds no test passes.
- `just test-e2e-web` runs every spec, tagged or not, against the dev stack on port 8080
  (`./data`, usually with a game server installed). It starts and stops the stack itself.
  Every `@moddb` test runs against the live mod database here, with no recordings and no
  `VS_MOD_DB_URL`. No workflow runs the tests against the live service on a schedule.

Run `just install-e2e-browsers` once first.

## Tags

A test with no tag needs only the stack the first pass starts. A `@moddb` test also needs
mod database answers and runs in the second pass on recorded ones. CI leaves out every
test that carries `@moddb-live`, `@install` or `@game-server`:

| Tag | The test needs | Example |
|---|---|---|
| `@moddb` | mod database answers, recorded or live (runs in CI on recordings) | `mod-browse-name-sort.spec.ts` |
| `@moddb-live` | the live mod database: the test compares with live data (local only) | the live test of `browse-game-version.spec.ts` |
| `@game-server` | a game server that is installed or has run: files it wrote, a running process | no test today |
| `@install` | to install or remove a real mod (always with `@moddb`; local only) | the real-API block of `mod-install-release.spec.ts` |

`@moddb-live` replaces `@moddb` on a test; the first pass's pattern `@moddb` leaves it out as
well. Of the 250 tests, CI runs 246: 219 untagged and 27 `@moddb`. The four that stay
local-only are the live test of `browse-game-version.spec.ts` (`@moddb-live`: on recorded
answers and a stack with no game server its game version is null, so it would check
nothing) and the three `@install` tests in `installed-status.spec.ts` and
`mod-install-release.spec.ts` (they install a real mod).

Since Story 20.5 no test carries `@game-server`. It is the right tag for a test that needs a
running game server process, or files only a game server writes that the CI script cannot
seed (for example a world save or a server log with content). A test that only needs a
directory or a small file gets it seeded in `scripts/e2e-ci.sh` instead.

To tag, use Playwright's `tag` option on a `test.describe` or a single test, with a one-line
reason in a comment next to it:

```ts
// @moddb: checks the order of the browse list
test.describe('Mod browser Name (A-Z) sort', { tag: '@moddb' }, () => { ... });
```

Do not put a tag in a title and do not use `test.skip` instead. A test that fails on the CI
stack gets a tag only when it needs what the tag names. When it needs one answer that the
stack cannot give (for example the mod database's game version list), stub that answer
with `page.route` and say why. Anything else is a bug in the test or in the product.

## Recorded mod database answers

`fixtures/moddb/` holds one file per recorded request and `manifest.json`, which gives for
each request its file, its recording date, how it was trimmed and the specs that need it.
The answers are real ones from the mod database's public API, unauthenticated, trimmed
and otherwise unchanged: image and link URLs stay as the mod database returned them, and
nothing about any instance is in them.

- Trimming: the full listing (`/api/mods`, several thousand mods) keeps the mods named in
  `listing.keep_slugs` and every mod whose name, summary, author or a tag contains one of
  `listing.keep_terms` (the fields the API's search reads), so a search for one of those
  terms finds the same mods it found live on the recording day. The listing for one game
  version keeps only the mods in the recorded listing. A mod lookup is kept whole.
- The replay (`scripts/moddb-replay.py`) answers a request from the manifest only: the
  path plus the query with its parameters sorted. A request it has no recording for gets
  404 with a plain-text body that names it, which the API turns into a 502, and a
  `no_recording GET <path>` line in the replay's log; a failed run prints those lines at
  the end. A test that opens a card picked from the grid needs that card's lookup: add the
  request the log names to the manifest and record only it.
  To run it by hand, pass `--host 127.0.0.1` so it listens on loopback only:
  `python3 scripts/moddb-replay.py --dir web/e2e/fixtures/moddb --host 127.0.0.1`
  (its default, `0.0.0.0`, is for the private Docker network of the second pass).
- `just record-moddb` fetches every request of the manifest from the live mod database
  (it needs the network), writes the files with the same trimming and their new dates, and
  prints per request the fields (key paths, list positions collapsed) that appeared (`+`)
  or disappeared (`-`) since the last recording. `just record-moddb --only <request>`
  (repeatable) records only those requests and leaves the others and their dates as they
  are; use it for a new lookup, so the listing and with it the cards do not move.
- Refresh the recordings when a live run (`just test-e2e-web`) fails on data, and before a
  release that changes how the manager handles mod database answers. A refresh is a
  normal pull request; read the field report in it.

## Tests that change the throwaway stack

`file-browser-new-directory.spec.ts` creates a uniquely named empty directory under `Logs`
with `docker exec`. It runs only when `E2E_CONTAINER` is `vintagestory-manager-e2e`, and
skips with a message on any other stack, so it never changes a developer's data.
`scripts/tests/test-e2e-ci.sh` checks that the script exports that name and that the spec
names the same container, so CI cannot skip it.

## Helpers (`config-js.ts`)

`serveConfigKey(page, apiKey)` answers `/config.js` with the key the page should use, so a
spec chooses its key whatever the stack hands the web UI. `pretendServerInstalled(page)`
answers the page's `GET /api/v1alpha1/server/status` as installed when the stack says
`not_installed`, so Game Settings, the Mods pages and the Console render on a stack with no
game server; a stack with a game server is passed through unchanged. Both are routes on
the page, so a test that opens a second page calls them for that page too.
`serveModImagePlaceholders(page)` does nothing unless `E2E_MODDB_REPLAY=1` (the second
pass sets it): then it keeps the browser off the internet. Every image request that does
not go to the manager (`moddbcdn.vintagestory.at`, and the GitHub, image-host and other
images that mod descriptions embed) gets a 1x1 PNG, a request to `mods.vintagestory.at` is
aborted, and so is any other request that does not go to the manager (the host of
`E2E_BASE_URL`, `127.0.0.1` or `localhost`). The manager's own pages, scripts, styles and
API pass untouched. The routes are on the page's browser context, so a second page is
covered too. Every spec with a `@moddb` test calls it in its set-up. A trailer is an
embed that loads only on a click, so no test loads one.

## The fixture

`fixtures/serverconfig.json` is the manager's own template with made-up values: the server
name `E2E Fixture Server` and the password `e2e-fixture-password`. The password is set so
that the check that a Monitor key never sees it (`monitor-password-redaction.spec.ts`) runs
in CI. It is not a real password, and `scripts/tests/test-e2e-ci.sh` pins it.
