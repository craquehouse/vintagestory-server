# E2E tests

## Tags

A test with no tag needs only the stack `just test-e2e-ci` starts. CI leaves out every
test that carries one of these tags:

| Tag | The test needs | Example |
|---|---|---|
| `@moddb` | the live mod database (mods.vintagestory.at) | `mod-browse-name-sort.spec.ts` |
| `@game-server` | a game server that is installed or has run: files it wrote, a running process | `file-browser-navigation.spec.ts` |
| `@install` | to install or remove a real mod (always with `@moddb`) | the real-API block of `mod-install-release.spec.ts` |
