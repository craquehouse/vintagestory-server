# E2E tests

Playwright tests against a running Docker stack (the API serving the built web UI).

## Two ways to run them

- `just test-e2e-ci` runs the tests with no tag, the set CI runs on every pull request. It
  starts a throwaway container (`vintagestory-manager-e2e` on `127.0.0.1:18080`) from the
  image, seeded with `fixtures/serverconfig.json`, placeholder keys and no game server, and
  removes it afterwards. It never touches the dev stack, `./data` or `dev/`. The container
  cannot reach the mod database or the vendor's version API: a call to either fails at once.
  Pass Playwright arguments through, for example `just test-e2e-ci e2e/settings-as-saved.spec.ts`.
- `just test-e2e-web` runs every spec, tagged or not, against the dev stack on port 8080
  (`./data`, usually with a game server installed). It starts and stops the stack itself.

Run `just install-e2e-browsers` once first.

## Tags

A test with no tag needs only the stack `just test-e2e-ci` starts. CI leaves out every
test that carries one of these tags:

| Tag | The test needs | Example |
|---|---|---|
| `@moddb` | the live mod database (mods.vintagestory.at) | `mod-browse-name-sort.spec.ts` |
| `@game-server` | a game server that is installed or has run: files it wrote, a running process | `file-browser-navigation.spec.ts` |
| `@install` | to install or remove a real mod (always with `@moddb`) | the real-API block of `mod-install-release.spec.ts` |

To tag, use Playwright's `tag` option on a `test.describe` or a single test, with a one-line
reason in a comment next to it:

```ts
// @moddb: checks the order of the live browse list
test.describe('Mod browser Name (A-Z) sort', { tag: '@moddb' }, () => { ... });
```

Do not put a tag in a title and do not use `test.skip` instead. A test that fails on the CI
stack gets a tag only when it needs what the tag names. When it needs one answer that the
stack cannot give (for example the mod database's game version list), stub that answer
with `page.route` and say why. Anything else is a bug in the test or in the product.

## Helpers (`config-js.ts`)

`serveConfigKey(page, apiKey)` answers `/config.js` with the key the page should use, so a
spec chooses its key whatever the stack hands the web UI. `pretendServerInstalled(page)`
answers the page's `GET /api/v1alpha1/server/status` as installed when the stack says
`not_installed`, so Game Settings, the Mods pages and the Console render on a stack with no
game server; a stack with a game server is passed through unchanged.

## The fixture

`fixtures/serverconfig.json` is the manager's own template with made-up values: the server
name `E2E Fixture Server` and the password `e2e-fixture-password`. The password is set so
that the check that a Monitor key never sees it (`monitor-password-redaction.spec.ts`) runs
in CI. It is not a real password, and `scripts/tests/test-e2e-ci.sh` pins it.
