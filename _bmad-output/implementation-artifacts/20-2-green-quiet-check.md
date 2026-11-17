# Story 20.2: A Green, Quiet `just check`

Status: done

<!-- Implements FR237-FR239, Epic 20 ADR-2 and ADR-3. Beads: VSS-1ar (TEST-003), VSS-hnl (TEST-004), VSS-37a (bug, verify and close), VSS-6wj (TEST-005), VSS-eh41 (UI-098, pulled in by Matt on 2026-11-17). Stacked on Story 20.1 (stories run in order 20.1 to 20.7). Line references were verified at 7f04ea2 (epic-20-planning; its api/ and web/ are identical to 3f1c6ea, the commit the ADRs cite) and must be re-checked at implementation time: Story 20.1 reformats every API test file, so the three fixture lines in Task 1 will move. Test and test-configuration changes, plus the deletion of two unused web source files; nothing an admin can see changes. No new dependencies. -->

## Story

As a **developer**,
I want **`just check` to end with no warning and no skipped test, and the web tests to run faster**,
so that **a new warning or skip is seen the day it appears, and the check is quick enough to run every time**.

## Acceptance Criteria

1. **Given** `just typecheck-api`
   **When** it runs
   **Then** it prints `0 errors, 0 warnings, 0 informations`; the three fixtures (`test_mod_service.py` `mod_without_releases` and `mod_without_tags`, `test_mods_router.py` `mods_without_tags`) each have a type annotation; no `# pyright: ignore` or `# type: ignore` was added; no rule level in `api/pyproject.toml` changed
   *(Covers FR237; `VSS-1ar`)*

2. **Given** the three empty placeholder tests (`FilterControls.test.tsx:156`, `use-browse-mods.test.tsx:247` and `:253`)
   **When** the story is done
   **Then** they are gone, and the story names the existing tests with assertions that cover selecting a game version in the filter controls and filtering the browse list by game version (Dev Notes "The placeholders": they exist, so no test is written)
   *(Covers FR238; `VSS-hnl`)*

3. **Given** `ModTable.test.tsx` "shows loading state in remove button when removing" (`:1056`)
   **When** the web tests run
   **Then** it is replaced by a test that runs without `act` around the click and passes, and asserts what the remove dialog really does while the remove request is pending: the dialog closes as soon as Remove is clicked, the DELETE is sent once, `onRemoved` is not called until the request resolves, and is called with the slug after it resolves. The story records why the "Removing..." state is not tested (Dev Notes "The remove-button test"; ADR against the code)
   *(Covers FR238; `VSS-hnl`)*

4. **Given** `just test-web`
   **When** it runs
   **Then** it reports 0 skipped tests, and no web unit test contains `it.skip`, `test.skip` or `describe.skip`
   *(Covers FR238)*

5. **Given** `VSS-37a`'s three tests ("shows confirmation dialog when remove button is clicked" `:456`, "closes dialog when cancel is clicked" `:480`, "removes mod when confirm is clicked" `:506`, in `describe('remove mod (AC: 8)')`)
   **When** the web tests run
   **Then** all three run and pass, and the bead is closed with an AAR that names commit `f393c3a`, which re-enabled them
   *(Covers FR238; `VSS-37a`)*

6. **Given** the pull-in `VSS-eh41`
   **When** the story is done
   **Then** `web/src/features/terminal/Terminal.tsx`, `Terminal.test.tsx`, and `web/src/lib/mod-compatibility.ts` with its test (the file holds only `checkVersionCompatibility`) are deleted; `rg "features/terminal|mod-compatibility'|checkVersionCompatibility" web/src web/e2e web/tests` finds nothing; the E2E spec `web/e2e/terminal.spec.ts` (which tests the Console page, not this component) passes in CI's `e2e` job; the bead is closed with an AAR
   *(Covers FR239; `VSS-eh41`)*

7. **Given** the three files that fail under `vmThreads` and remain (`use-log-stream.test.ts`, `use-console-websocket.test.ts`, `cookies.test.ts`)
   **When** the web tests run under `--pool=vmThreads` and under `--pool=forks`
   **Then** every test passes under both; no web test redefines `window.location` with `Object.defineProperty`, deletes `global.document`, or assigns `global.WebSocket`; the two hook tests and `cookies.test.ts` no longer contain `@ts-expect-error`; and the tests assert what they asserted before (Dev Notes "The stub changes" says where the SSR tests' assertions differ and why)
   *(Covers FR239; `VSS-6wj`)*

8. **Given** `web/vitest.config.ts`
   **When** I read it
   **Then** it sets `pool: 'vmThreads'`, does not set `isolate: false`, and no test file is moved to another pool (a per-file `@vitest-environment` is an environment, not a pool; Dev Notes "The stub changes"). If a file cannot be made to pass, the dev stops and asks the maintainer
   *(Covers FR239; Matt, 2026-11-17)*

9. **Given** the web suite before (133 files, 3,353 tests: 3,349 passed, 4 skipped) and after the story
   **When** I compare the counts
   **Then** it has 132 files and 3,307 tests, all passing; the 46 tests gone are exactly those listed in Dev Notes "Tests deleted on purpose", and the three SSR cookie tests are in `cookies.ssr.test.ts`
   *(Covers FR239)*

10. **Given** CI's `web` job on the story's pull request
    **When** it runs
    **Then** `just test-web` passes, and the Dev Agent Record has its time before (60 s, `main`, 2026-11-17) and after, and the local before and after numbers (wall time, pool, jsdom setups)
    *(Covers FR239)*

11. **Given** `project-context.md`
    **When** I read its testing rules
    **Then** it says how to stub a browser global so the test passes under `vmThreads` (`setTestUrl` for the URL, `vi.stubGlobal` for configurable globals, a `@vitest-environment node` file for "no document"), and its forbidden-pattern list names `it.skip`, `test.skip` in unit tests and `describe.skip` beside `pytest.skip`, with the E2E precondition skip still allowed
    *(Covers FR238, FR239)*

12. **Given** every other existing test
    **When** `just check` runs
    **Then** it passes with 0 Pyright warnings and 0 skipped web tests; no test changed apart from those in Dev Notes "Existing tests that change"; nothing is written under `dev/`

## Tasks / Subtasks

<!-- Commit per task: type(story-20.2/task-N): ...; nothing here is visible to an admin, so no feat or fix. Tasks run in this order: the VSS-eh41 deletion (Task 4) comes before the stub changes (Task 5) because Terminal.test.tsx is one of the four failing files. -->

- [x] Task 1: Annotate the three fixtures; Pyright at 0 warnings (AC: 1, 12) (`VSS-1ar`)
  - [x] 1.1: `api/tests/test_mod_service.py`: `mod_without_releases: dict[str, Any] = {` (`:1640` at 7f04ea2) and `mod_without_tags: dict[str, Any] = {` (`:1719`). `Any` is already imported (`:8`)
  - [x] 1.2: `api/tests/test_mods_router.py`: `mods_without_tags: dict[str, Any] = {` (`:3099`). `Any` is already imported (`:10`)
  - [x] 1.3: `just typecheck-api` prints `0 errors, 0 warnings, 0 informations`; `just test-api tests/test_mod_service.py tests/test_mods_router.py` passes (prototype: 297 passed); `ruff format` on the two files changes nothing else (Story 20.1 has formatted them)
  - [x] 1.4: Commit `test(story-20.2/task-1): annotate three API test fixtures so Pyright has no warnings`

- [x] Task 2: Remove the placeholders and rewrite the remove-button test (AC: 2, 3, 4) (`VSS-hnl`)
  - [x] 2.1: Delete `web/src/components/FilterControls.test.tsx:156-158` ("handles version filter selection - DISABLED ...") and `web/src/hooks/use-browse-mods.test.tsx:246-255` (the comment line and both "DISABLED" tests in `describe('filterModsByFilters')` `:190`). Check the coverage named in Dev Notes "The placeholders" is still there; write nothing new
  - [x] 2.2: `web/src/components/ModTable.test.tsx:1053-1117`: replace the comment and the skipped test with "closes the dialog at once and reports the removal when the request completes" (Dev Notes "The remove-button test"). Keep the deferred promise; no `act`
  - [x] 2.3: `just test-web src/components/ModTable.test.tsx src/components/FilterControls.test.tsx src/hooks/use-browse-mods.test.tsx`: all pass, 0 skipped
  - [x] 2.4: Commit `test(story-20.2/task-2): remove empty placeholder tests and test the remove dialog as it behaves`

- [x] Task 3: Verify `VSS-37a` (AC: 5) (`VSS-37a`)
  - [x] 3.1: `just test-web src/components/ModTable.test.tsx -t "remove mod"`; record in the Debug Log that the three tests at `:456`, `:480`, `:506` ran and passed. No code change and no commit; the AAR is added in Task 7

- [x] Task 4: Remove the unused Terminal component and `checkVersionCompatibility` (AC: 6, 9) (`VSS-eh41`)
  - [x] 4.1: `git rm web/src/features/terminal/Terminal.tsx web/src/features/terminal/Terminal.test.tsx` (the directory is then empty and goes)
  - [x] 4.2: `git rm web/src/lib/mod-compatibility.ts web/src/lib/mod-compatibility.test.ts`: the file exports only `checkVersionCompatibility` (`:30-37`), and only its own test imports it
  - [x] 4.3: `rg "features/terminal|mod-compatibility'|checkVersionCompatibility" web/src web/e2e web/tests` finds nothing (the `mod-compatibility-message-*` test IDs in `InstalledModParts.tsx` are unrelated and stay); `cd web && bunx tsc --noEmit` passes; `just test-web` passes
  - [x] 4.4: Commit `refactor(story-20.2/task-4): remove the unused Terminal component and checkVersionCompatibility`

- [x] Task 5: Change how the three remaining files stub browser globals (AC: 7, 9, 12) (`VSS-6wj`)
  - [x] 5.1: First run `just test-web --pool=vmThreads` and read every failure. Expected (prototype at 7f04ea2, after Task 4): 84 failures in 3 files, from `Cannot redefine property: location` (25 call sites) and `Cannot delete property 'document'` (3). If any other message appears, read it before going on
  - [x] 5.2: New `web/tests/location.ts` with `setTestUrl(url)` and `resetTestUrl()` (Dev Notes "The stub changes", 1); `web/tests/setup.ts` calls `resetTestUrl()` in its `afterEach`
  - [x] 5.3: `use-console-websocket.test.ts` (12 sites: `:108`, `:121`, `:134`, `:146`, `:159`, `:362`, `:588`, `:672`, `:767`, `:911`, `:971`, `:992`) and `use-log-stream.test.ts` (13 sites: `:108`, `:121`, `:134`, `:145`, `:156`, `:169`, `:371`, `:482`, `:768`, `:835`, `:908`, `:941`, `:1004`): each `Object.defineProperty(window, 'location', { value: { protocol: P, host: H }, writable: true })` becomes `setTestUrl('P//H/')`; drop the "// Mock window.location" comments
  - [x] 5.4: Both hook tests, `:95-96`: `// @ts-expect-error` + `global.WebSocket = MockWebSocket;` becomes `vi.stubGlobal('WebSocket', MockWebSocket);`, and the top-level `afterEach` (`:101`) adds `vi.unstubAllGlobals()` (Dev Notes "The stub changes", 2)
  - [x] 5.5: `cookies.test.ts`: move the `describe("SSR compatibility")` block (`:93-147`) to a new `web/src/lib/cookies.ssr.test.ts` with `// @vitest-environment node` on line 1; `web/tests/setup.ts` runs its DOM-only steps only when `window` exists (Dev Notes "The stub changes", 3)
  - [x] 5.6: `just test-web --pool=vmThreads src/hooks src/lib` and `just test-web --pool=forks src/hooks src/lib`: all pass. Then the whole suite under both pools. `cd web && bunx tsc --noEmit` passes
  - [x] 5.7: Commit `test(story-20.2/task-5): stub location, document and WebSocket in a way the vmThreads pool accepts`

- [x] Task 6: Switch the pool, measure, and write the rules down (AC: 8, 10, 11) (`VSS-6wj`)
  - [x] 6.1: Before the switch, on this branch: `/usr/bin/time -p just test-web` three times; record wall time, the Duration line and the "jsdom was created N times" line. Then add `pool: 'vmThreads',` after `environment: 'jsdom',` in `web/vitest.config.ts` (`:18`) with a one-line comment (one jsdom per worker; per-file isolation stays). Run three times again and record the same; Vitest no longer prints the jsdom notice
  - [x] 6.2: Run the full suite twice more under `vmThreads` to look for order-dependent failures and for the memory warnings ADR-2's consequences mention; record any
  - [x] 6.3: `project-context.md`: the stubbing pattern (new "Stubbing browser globals in web unit tests" paragraph at the end of "### 2. Testing Discipline is Non-Negotiable", after `:165`) and the skip patterns in "### 8. No Silent Failures Rule" (`:228-232`) (Dev Notes "project-context.md")
  - [x] 6.4: Commit `test(story-20.2/task-6): run the web unit tests in the vmThreads pool` (config) and `docs(story-20.2/task-6): document stubbing browser globals and forbid skipped unit tests` (project-context.md)

- [ ] Task 7: Quality gate and review hand-off (AC: all)
  - [x] 7.1: `just check` passes and prints `0 errors, 0 warnings` from Pyright and no `skipped` from Vitest; the diff adds no suppression, no `cast` and no `as unknown as`; after the run, `git status --short` shows nothing under `dev/`
  - [x] 7.2: Test counts as in AC 9 (132 files, 3,307 tests); list the deleted tests in Completion Notes
  - [ ] 7.3: Status `review`; `just sprint set 20-2-green-quiet-check review`; PR to `main` (Story 20.1 merged first). After CI: record the `web` job's `just test-web` time and that `terminal.spec.ts` passed in the `e2e` job
  - [ ] 7.4: AARs and closes (after merge, per CLAUDE.md): `VSS-1ar`, `VSS-hnl`, `VSS-6wj`, `VSS-eh41` with their commits; `VSS-37a` naming `f393c3a` and Task 3's run. Do not close `VSS-029` (Story 20.5 does)

## Dev Notes

### What `just check` prints today (verified at 7f04ea2)

- `just typecheck-api`: `0 errors, 3 warnings`, all `reportUnknownVariableType` on dict literals holding an empty list: `test_mod_service.py:1640:9` (`dict[str, int | str | list[Unknown]]`), `:1719:9`, `test_mods_router.py:3099:9`. The lines in `VSS-1ar` (1589, 1668, 2424) are older. `api/pyproject.toml:56` sets the rule to `warning`; it stays.
- `just test-web`: 133 files, 3,353 tests, 3,349 passed, 4 skipped (`FilterControls.test.tsx:156`, `use-browse-mods.test.tsx:247`, `:253`, `ModTable.test.tsx:1056`).
- Prototype of Task 1: `dict[str, Any]` on the three names gives `0 errors, 0 warnings, 0 informations` and the two files pass. A narrower type is allowed by ADR-3 but buys nothing: the dicts are JSON bodies handed to `respx` `Response(json=...)`.

### The placeholders (Task 2.1)

The three bodies are empty, and the reason they give ("requires API enhancement") is out of date: the game version filter exists (`FilterControls.tsx:84-86`, `:186-196`) and is sent to the server (`use-browse-mods.ts:108`, `:119`). Coverage that already exists, with assertions:

- Selecting a game version: `FilterControls.test.tsx:329` "calls onChange when version is selected" (opens `version-filter-button`, clicks `version-option-1.21.2`, expects `onChange` with `gameVersion: '1.21.2'`), and `:351` (removing the filter badge).
- Filtering the browse list by game version: `use-browse-mods.test.tsx:1515` "accepts filters.gameVersion (legacy format)", `:1537` "accepts version (flat format)", `:1835` "handles game version filtering" (each asserts `version=1.19.0` in the request URL). Filtering is server-side; `filterModsByFilters` (`use-browse-mods.ts:258`, the `describe` the two placeholders sit in) was `@deprecated`, unused by product code (this story deletes it), and had no game version branch, so a client-side game version test there would test nothing.

So ADR-3 decision 1's "write the missing test" has nothing to write. The `null lastReleased` placeholder (`:253`) refers to a field the filter never used.

### The remove-button test (Task 2.2)

**Why the old test can never pass.** The confirm button is `AlertDialogAction` (`ModTable.tsx:453-466`), a Radix `AlertDialog.Action`, which closes the dialog on click: `onOpenChange(false)` runs `handleRemoveCancel` (`:240-242`), `modToRemove` becomes `null`, and `AlertDialogContent` unmounts in the same click, before `isRemoving` turns true. "Removing..." (`:458-462`) is never in the DOM. A prototype without `act` confirmed it: right after `fireEvent.click(remove-dialog-confirm)` the dialog is gone, and it stays gone while the DELETE is pending. The skip comment (`:1053-1055`) blamed `act` and TanStack Query; the cause is the dialog. A Playwright test would not help: in a browser the text can at most flash during the close animation.

**The replacement** (prototype passed under both pools, 85 tests in the file):

```tsx
it('closes the dialog at once and reports the removal when the request completes', async () => {
  // keep: resolveRemove / removePromise / removeFetch / globalThis.fetch from the old test
  const queryClient = createTestQueryClient();
  const onRemoved = vi.fn();
  render(<ModTable onRemoved={onRemoved} />, { wrapper: createWrapper(queryClient) });
  await waitFor(() => {
    expect(screen.getByTestId('mod-remove-smithingplus')).toBeInTheDocument();
  });
  fireEvent.click(screen.getByTestId('mod-remove-smithingplus'));
  await waitFor(() => {
    expect(screen.getByTestId('remove-dialog-confirm')).toBeInTheDocument();
  });

  fireEvent.click(screen.getByTestId('remove-dialog-confirm'));

  // The dialog closes at once; the request is still pending
  expect(screen.queryByTestId('remove-dialog')).not.toBeInTheDocument();
  await waitFor(() => {
    expect(removeFetch).toHaveBeenCalledTimes(1);
  });
  expect(onRemoved).not.toHaveBeenCalled();

  resolveRemove!();

  await waitFor(() => {
    expect(onRemoved).toHaveBeenCalledWith('smithingplus');
  });
});
```

`resolveRemove!` is the old test's existing non-null assertion on a `let` assigned inside the `Promise` executor; it is not a suppression. If the dev prefers, declare `let resolveRemove: () => void = () => {};` and drop the `!`.

The product code is not changed: the unreachable "Removing..." branch and whether the dialog should stay open with a spinner (as `UninstallConfirmDialog.tsx:101-118` does) are follow-ups for the maintainer (see "ADR against the code").

### `VSS-37a` (Task 3)

The three tests are plain `it` at `ModTable.test.tsx:456`, `:480`, `:506`; `f393c3a` ("test: fix test warnings and enable skipped ModTable tests") re-enabled them; `:453-454` holds the comment that `fireEvent.click` must not be wrapped in `act` there. At 7f04ea2 the file runs 84 passed, 1 skipped (the `:1056` test).

### The `vmThreads` failures (Task 5, prototype at 7f04ea2)

| Pool | Wall time (`/usr/bin/time`) | Vitest Duration | Result | jsdom setups |
|---|---|---|---|---|
| forks (today) | 9.7 s | 9.1 s | 133 files, 3,349 passed, 4 skipped | 133 ("37.48 s total, 36% of tracked time") |
| vmThreads (today) | 4.7 s | 4.4 s | 111 failed in 4 files | one per worker; no notice |
| vmThreads (prototype of this story) | 4.9-5.6 s | 4.5-5.3 s | 132 files, all passed | one per worker; no notice |
| forks (prototype of this story) | 8.7 s | 8.5 s | 132 files, all passed | 132 |

Other agents were running on the same 14-core machine, so the absolute numbers are noisy; planning measured 15.2 s and 6.3 s. Task 6 measures again.

The 111 failures: `use-log-stream.test.ts` 45, `use-console-websocket.test.ts` 36, `Terminal.test.tsx` 27, `cookies.test.ts` 3. Only two messages, 26 + 3 sites: `TypeError: Cannot redefine property: location` (12 sites in `use-console-websocket.test.ts`, 13 in `use-log-stream.test.ts`, 1 in `Terminal.test.tsx:151`; failures in `beforeEach` blocks fail every test below them) and `TypeError: Cannot delete property 'document' of [object Window]` (`cookies.test.ts:100`, `:114`, `:136`). Under `vmThreads` the jsdom window is the `vm` context's global, and `location` and `document` on it are not configurable.

### The stub changes (Task 5)

Tried in the prototype, in ADR-2's order of preference:

- `vi.stubGlobal('location', ...)` and `vi.stubGlobal('document', undefined)`: **fail** under `vmThreads` (`Cannot redefine property: location` / `document`), pass under forks. ADR-2 decision 2's plan for `cookies.test.ts` therefore does not work.
- Setting the document URL through the jsdom instance (`jsdom.reconfigure({ url })`): **passes** under both pools; `window.location.protocol` and `.host` follow.

1. **Location.** `web/tests/location.ts`, beside `tests/viewport.ts` (same pattern, imported as `'../../tests/location'`):

   ```ts
   /// <reference types="vitest/jsdom" />
   /** Vitest's jsdom default URL; every test starts here. */
   export const DEFAULT_TEST_URL = 'http://localhost:3000/';

   /** Point the jsdom document at another URL; window.location follows. */
   export function setTestUrl(url: string): void {
     jsdom.reconfigure({ url });
   }

   /** Back to the default URL (called after each test by tests/setup.ts). */
   export function resetTestUrl(): void {
     jsdom.reconfigure({ url: DEFAULT_TEST_URL });
   }
   ```

   `vitest/jsdom` declares the `jsdom` global, but `jsdom` ships no types and `@types/jsdom` is not installed (no new dependency), so `jsdom` is `any` under `skipLibCheck`. The two typed wrappers keep that to these two lines; tests never touch `jsdom` directly. Do not add `vitest/jsdom` to `tsconfig.json` `types`: that would put the global in product code's type space.

   The reset matters under `vmThreads`: one jsdom serves every file in a worker, so a URL set in one file would otherwise leak into the next. It also cleans up after `ModsPage.test.tsx:532` (`window.history.replaceState`), which changes the shared URL today. The values used in the two files are `http://localhost:8080/` (18 sites), `http://localhost/` (5) and `https://example.com/` (2); the assertions (`ws://localhost:8080/api/v1alpha1/console/ws?...`, `wss://example.com`) are unchanged.

2. **WebSocket.** `global.WebSocket = MockWebSocket` works under both pools today, but it needs a `@ts-expect-error` and is never restored. `vi.stubGlobal('WebSocket', MockWebSocket)` with `vi.unstubAllGlobals()` in the file's `afterEach` passes under both pools and type-checks without the comment (prototype: `src/hooks` 571 passed under each pool, `tsc` clean). `App.no-key.test.tsx:27-32` already does this. This fits `VSS-6wj` (which names WebSocket), so it is in this story under the backlog-drawdown rule.

3. **No document (cookies).** `document` cannot be removed or replaced under `vmThreads`. The three SSR tests move to `web/src/lib/cookies.ssr.test.ts`, whose first line is `// @vitest-environment node`: the file then runs where `document` really is undefined, which is what `cookies.ts:15`, `:39`, `:51` (`typeof document === "undefined"`) guard against. This is an environment, not a pool, so ADR-2 decision 5 holds; the prototype passed under both pools. Content:

   ```ts
   // @vitest-environment node
   import { describe, it, expect } from "vitest";
   import { getCookie, setCookie, deleteCookie } from "./cookies";

   // The node environment has no document, as during server-side rendering.
   describe("SSR compatibility", () => {
     it("getCookie returns null when document is undefined", () => {
       expect(typeof document).toBe("undefined");
       expect(getCookie("any")).toBeNull();
     });
     it("setCookie does nothing when document is undefined", () => {
       expect(() => setCookie("ssr-test", "value")).not.toThrow();
     });
     it("deleteCookie does nothing when document is undefined", () => {
       expect(() => deleteCookie("ssr-delete-test")).not.toThrow();
     });
   });
   ```

   What changes in the assertions: the old `setCookie` and `deleteCookie` tests restored the document and then checked the cookie jar (not set; still set). With no document there is no jar to check, and without the guard each call would throw `ReferenceError: document is not defined`, so `not.toThrow()` is the check that the guard returns early. The `getCookie` assertion is the same. The three `@ts-expect-error` lines go with the old block. `cookies.test.ts` keeps its other tests unchanged.

   `tests/setup.ts` runs for every file, and today it touches `window` at load (`installMatchMedia()`, `:15`) and defines `localStorage` (`:51-54`). Guard only the DOM steps; keep the rest:

   ```ts
   if (typeof window !== 'undefined') {
     installMatchMedia();
     Object.defineProperty(global, 'localStorage', { value: new LocalStorageMock(), writable: true });
   }

   afterEach(() => {
     if (typeof window !== 'undefined') {
       cleanup();
       resetViewport();
       resetTestUrl();
     }
     vi.clearAllMocks();
   });
   ```

   Keep `installMatchMedia()` before the `LocalStorageMock` class as today if that reads better; the point is the guard. Without it the node file fails at setup with `ReferenceError: window is not defined` (seen in the prototype).

If any of this fails at implementation time in a way these notes do not cover, stop and ask (ADR-2 decision 5); do not leave a file on the forks pool.

### Tests deleted on purpose (AC 9)

- `web/src/features/terminal/Terminal.test.tsx`, 27 tests: renders the terminal page; renders the "Server Console" header; renders the connection status indicator; renders the terminal container; renders the command input field; renders the send button; shows "Connecting..." initially; displays connection status component in header; renders connection status with correct aria-label for initial state; creates WebSocket connection with correct URL; creates WebSocket with history_lines parameter; disables input when not connected; enables input when connected; disables send button when input is empty; enables send button when input has content; sends command when form is submitted; clears input after sending command; does not send command when input is whitespace only; does not send command when server is not running even if connected; sends command on Enter key; shows placeholder based on connection state; shows "Server not running" placeholder when connected but server is stopped; has proper aria-label on terminal container; has connection status with ARIA live region; has aria-label on command input; has proper flex layout for full height; queues messages received before terminal initialization and flushes them when ready. The live console is `ConsolePanel.tsx`, covered by `ConsolePanel.test.tsx` and `web/e2e/terminal.spec.ts`.
- `web/src/lib/mod-compatibility.test.ts`, 3 tests: returns not_verified as placeholder; handles null server version; handles empty mod versions array.
- 3 placeholders: `FilterControls.test.tsx` "handles version filter selection - DISABLED ..."; `use-browse-mods.test.tsx` "filters by gameVersion - DISABLED ..." and "handles mods with null lastReleased - DISABLED ...".
- `use-browse-mods.test.tsx` `describe('filterModsByFilters')`, 13 tests, deleted with the deprecated, unused function (controller decision at implementation, backlog drawdown; names in Completion Notes).

Counts: 3,353 - 27 - 3 - 3 - 13 = 3,307 tests; 133 - 2 + 1 (`cookies.ssr.test.ts`) = 132 files.

### Existing tests that change

| File | Change |
|---|---|
| `api/tests/test_mod_service.py:1640`, `:1719`; `api/tests/test_mods_router.py:3099` | Type annotation only |
| `web/src/components/FilterControls.test.tsx:156-158` | Placeholder deleted |
| `web/src/hooks/use-browse-mods.test.tsx:246-255` | Two placeholders and their comment deleted |
| `web/src/components/ModTable.test.tsx:1053-1117` | Skipped test replaced (new name and assertions, AC 3) |
| `web/src/hooks/use-console-websocket.test.ts`, `use-log-stream.test.ts` | `setTestUrl` instead of `Object.defineProperty(window, 'location')`; `vi.stubGlobal('WebSocket')`; `vi.unstubAllGlobals()` in `afterEach`. Assertions unchanged |
| `web/src/lib/cookies.test.ts:93-147` | SSR block moved to `cookies.ssr.test.ts` (assertion change above) |
| `web/tests/setup.ts` | DOM steps guarded; `resetTestUrl()` after each test |

### Not changed (do not "fix" these here)

- `ModTable.tsx`, including its unreachable `isRemoving` "Removing..." branch (`:458-462`) and the dialog closing on confirm. Follow-up.
- `ConsolePanel.tsx`, `components/terminal/TerminalView.tsx`, `components/terminal/ConnectionStatus.tsx`, `hooks/use-console-websocket.ts`, `hooks/use-log-stream.ts`: still used by the Console page. ADR-2 decision 2's third option (move the URL building into a pure function) is not needed.
- `api/pyproject.toml` rule levels; `tsconfig.json`; `web/package.json`; `isolate`; any per-file pool.
- `delete window.__VSM_CONFIG__` in `App.no-key.test.tsx:33` and `api/client.test.ts:133`: an own, configurable property; passes under both pools.
- `web/e2e/terminal.spec.ts` (it tests `/game-server/console`, untagged, in the CI set).

### API contract changes

None. No route, response, error code or setting changes. No release note: every commit is `test`, `refactor` or `docs`.

### ADR against the code

- **ADR-2 decision 2, `cookies.test.ts`:** `vi.stubGlobal('document', undefined)` fails under `vmThreads` (`Cannot redefine property: document`), as does `vi.stubGlobal('location', ...)`. The story uses `jsdom.reconfigure` for the URL (ADR-2's first choice, which works) and a `@vitest-environment node` file for "no document". The SSR tests' `setCookie`/`deleteCookie` assertions change from "cookie jar unchanged" to "does not throw" (above).
- **ADR-2 decision 3 / `VSS-eh41`:** `checkVersionCompatibility` is the only export of `web/src/lib/mod-compatibility.ts`, so the file and its 3-test file go; the epic's test list did not count those 3.
- **ADR-3 decision 1:** coverage for the game version filter already exists; nothing to write.
- **ADR-3 decision 2:** the "Removing..." state is never rendered (the Radix Action closes the dialog first), so neither a unit test nor a Playwright test can observe it. The test asserts what happens instead (AC 3). Whether the dialog should stay open with a spinner until the request ends is a product decision for the maintainer, not in this story.
- **Facts:** `use-console-websocket.test.ts` has 12 `defineProperty(window, 'location')` sites, not 13; `use-log-stream.test.ts` has 13.

### `project-context.md` (Task 6.3)

After `:165` in "### 2. Testing Discipline is Non-Negotiable", a short paragraph "Stubbing browser globals in web unit tests (Vitest `vmThreads`, Story 20.2)":
- `window.location` and `document` cannot be redefined or deleted; `Object.defineProperty(window, 'location', ...)`, `delete global.document` and `vi.stubGlobal` on them fail.
- To change the URL, call `setTestUrl(url)` from `web/tests/location.ts`; `tests/setup.ts` resets it after each test.
- For configurable globals (`WebSocket`, `fetch`, `EventSource`), use `vi.stubGlobal` and `vi.unstubAllGlobals()` in `afterEach`, not assignment.
- To test code with no `document`, put the tests in their own file with `// @vitest-environment node`.

In "### 8. No Silent Failures Rule", forbidden list (`:228-232`): change `pytest.skip` / `pytest.mark.xfail` to also name `it.skip` / `test.skip` / `describe.skip` in unit tests, and add one line: a precondition skip inside an E2E test body (`test.skip(!MONITOR_KEY, ...)`) is allowed.

### E2E and manual check

Nothing an admin can see changes, so there is no new E2E spec and no manual check. `web/e2e/terminal.spec.ts` must still pass; it is in the CI set (`just test-e2e-ci`), so the PR's `e2e` job proves AC 6. Do not run the Docker dev stack for this story.

### Testing Requirements

- Every new or changed web test passes under `--pool=vmThreads` and `--pool=forks` (Task 5.6).
- No test writes into `dev/` (`just test-api` sets `VS_DATA_DIR=../dev`; Task 1 changes annotations only).
- No `act` around the confirm click in the rewritten test.

### Development Commands

`just test-web --pool=vmThreads <files>`, `just test-web --pool=forks <files>`, `just test-web src/components/ModTable.test.tsx -t "remove mod"`, `just typecheck-api`, `cd web && bunx tsc --noEmit`, `just check`. Story 20.3 fixes argument splitting in recipes; none of these arguments contain spaces.

### Previous Story Intelligence

- **19.7:** moved `terminal.spec.ts` from `/terminal` to the Console page and found `Terminal.tsx` dead (the `VSS-eh41` comment). Its review: an all-skip pytest run passes, so "0 skipped" is checked on Vitest's summary line, not by the exit code.
- **18.3:** removed `getBrowseCardCompatibility` and `BROWSE_CARD_DEFAULT_STATUS` beside `checkVersionCompatibility` and left the placeholder (origin of `VSS-eh41`).
- **18.2 / 17.x:** `ruff format` was avoided on unformatted files; after Story 20.1 it is safe on the two API test files. A completion note must be true of the code. `feat`/`fix` only for what an admin can see (none here). Router tests must not write into `dev/`.

### Git Intelligence

- Base `7f04ea2` (`docs(epic-20): record the maintainer's answers ...`) on `3f1c6ea`. Story 20.1 lands first and reformats the API tests; nothing else in the epic touches these files before this story.
- Planned commits: `test(story-20.2/task-1): ...`, `test(story-20.2/task-2): ...`, `refactor(story-20.2/task-4): ...`, `test(story-20.2/task-5): ...`, `test(story-20.2/task-6): ...`, `docs(story-20.2/task-6): ...`, `docs(story-20.2): ...` for bookkeeping. Task 3 has no commit.

### Project Structure Notes

- New: `web/tests/location.ts`, `web/src/lib/cookies.ssr.test.ts`.
- Deleted: `web/src/features/terminal/Terminal.tsx`, `Terminal.test.tsx`, `web/src/lib/mod-compatibility.ts`, `mod-compatibility.test.ts`.
- Modified: `web/vitest.config.ts`, `web/tests/setup.ts`, `web/src/components/ModTable.test.tsx`, `FilterControls.test.tsx`, `web/src/hooks/use-browse-mods.test.tsx`, `use-console-websocket.test.ts`, `use-log-stream.test.ts`, `web/src/lib/cookies.test.ts`, `api/tests/test_mod_service.py`, `api/tests/test_mods_router.py`, `project-context.md`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 20.2: A Green, Quiet `just check`]
- [Source: _bmad-output/planning-artifacts/prd.md] FR237, FR238, FR239
- [Source: _bmad-output/planning-artifacts/architecture/epic-20-tooling-and-test-health.md#Facts Checked in the Code, #ADR-2, #ADR-3]
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-17-epic-20.md] (section 2 rows for 20.2; question 10: stop and ask under `vmThreads`)
- [Source: _bmad-output/implementation-artifacts/19-7-e2e-runs-in-ci.md] (`terminal.spec.ts`)
- Beads: `VSS-1ar`, `VSS-hnl`, `VSS-37a`, `VSS-6wj`, `VSS-eh41`; parent `VSS-lzgg`; `VSS-37a` also under `VSS-029`
- `project-context.md` (no suppressions; testing discipline; commit format)

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (`claude-opus-5-5`), BMAD dev-story workflow, non-interactive.

### Debug Log References

- Task 1: the three fixtures were at `test_mod_service.py:1627`, `:1704` and `test_mods_router.py:3046` after Story 20.1. `just typecheck-api`: `0 errors, 0 warnings, 0 informations`. `just test-api tests/test_mod_service.py tests/test_mods_router.py`: 297 passed. `ruff format` on both files: "2 files left unchanged".
- Task 2: `ModTable.test.tsx`, `FilterControls.test.tsx`, `use-browse-mods.test.tsx`: 186 passed, 0 skipped, under `--pool=vmThreads` and `--pool=forks`.
- Task 2, probe (not committed): in the new test, after confirming the removal of `smithingplus` and while its DELETE was pending, opening the remove dialog for `carrycapacity` showed the confirm button text `Removing...`. The "Removing..." branch is reachable in that case (see Completion Notes).
- Task 3 (`VSS-37a`): `vitest --run src/components/ModTable.test.tsx -t "remove mod" --reporter=verbose`: "shows confirmation dialog when remove button is clicked" (`:456`), "closes dialog when cancel is clicked" (`:480`), "removes mod when confirm is clicked" (`:506`) ran and passed (3 passed; the other 82 were filtered out by `-t`). `just test-web ... -t "remove mod"` splits the quoted pattern on spaces (Story 20.3), so a dotted pattern or a direct `vitest` call is needed.
- Task 4: `rg "features/terminal|mod-compatibility'|checkVersionCompatibility|filterModsByFilters" web/src web/e2e web/tests` finds nothing; `bunx tsc --noEmit` clean; `just test-web`: 131 files, 3,307 passed.
- Task 5.1: `just test-web --pool=vmThreads` after Task 4: 84 failed in 3 files; only `TypeError: Cannot redefine property: location` (25) and `TypeError: Cannot delete property 'document' of [object Window]` (3), as expected.
- Task 5.6: `src/hooks src/lib`: 37 files, 1,049 passed under each pool. Whole suite: 132 files, 3,307 passed under `vmThreads` (Duration 4.29 s) and under `forks` (12.24 s). `tsc` clean.
- Task 6.1, before the switch (forks, this branch after Task 5): wall 8.90 / 9.01 / 9.43 s; Duration 8.69 / 8.83 / 9.24 s; "jsdom was created 132 times" (37.66 / 38.29 / 39.47 s total, 37% of tracked time).
- Task 6.1-6.2, after the switch (`vmThreads`), five runs: wall 5.54 / 4.78 / 5.13 / 4.68 / 4.75 s; Duration 5.19 / 4.53 / 4.83 / 4.40 / 4.46 s; 132 files, 3,307 passed every run; no jsdom notice. No order-dependent failure; no memory, heap or listener warning in the output (one more run grepped for them: none).
- Review LOW-1: `BrowseTab.test.tsx` failed under `--sequence.shuffle` (2 of 4 runs before the fix, `TypeError: card.scrollIntoView is not a function`). After `tests/setup.ts` stubs `scrollIntoView`/`scrollTo` before each test and clears `sessionStorage` after each: `BrowseTab.test.tsx --sequence.shuffle` 12/12 green under `vmThreads` and 4/4 under `forks` (63 passed each); the whole suite with `--sequence.shuffle` 3/3 green under each pool (3,307 passed). No other file failed under shuffle.
- Task 7.1: `just check` exit 0 in 56.3 s wall: ruff "All checks passed!", Pyright `0 errors, 0 warnings, 0 informations`, API 3,334 passed, web 132 files / 3,307 passed (no `skipped`), script tests green. `git status --short` afterwards: nothing under `dev/`. The diff adds no suppression, `cast` or `as unknown as`; `rg "(it|test|describe)\.skip" web/src web/tests` finds nothing.

### Completion Notes List

- AC 1: the three fixtures are `dict[str, Any]`; Pyright has 0 warnings; no ignore added; `api/pyproject.toml` unchanged.
- AC 2: the three placeholders are deleted. Existing coverage, unchanged: selecting a game version, `FilterControls.test.tsx` "calls onChange when version is selected" and the badge-removal test after it; filtering the browse list by game version, `use-browse-mods.test.tsx` "accepts filters.gameVersion (legacy format)", "accepts version (flat format)", "handles game version filtering".
- AC 3: "shows loading state in remove button when removing" is replaced by "closes the dialog at once and reports the removal when the request completes", with no `act` around the click: the dialog is gone right after the confirm click, the DELETE is sent once, `onRemoved` is not called while it is pending and is called with `smithingplus` after it resolves. `resolveRemove` is declared `let resolveRemove: () => void = () => {};`, so no `!` is needed.
- AC 3, a correction to Dev Notes: "Removing..." is not unreachable in all cases. The dialog for the mod being removed does close before `isRemoving` turns true, so the old test could never pass. But `isPending` belongs to the one `useRemoveMod` mutation in `ModTable`, so if the admin opens the remove dialog for a second mod while the first DELETE is pending, the second dialog's confirm button reads "Removing..." with a spinner (seen in a probe; not committed). The controller asked for the branch to be deleted as a refactor with no visible change. Because deleting it would change what the admin sees in this case (the label would read "Remove"), `ModTable.tsx` is not changed, as the story's "Not changed" list says. Left to the maintainer.
- AC 4: `just test-web` reports 0 skipped; no `it.skip`, `test.skip` or `describe.skip` in web unit tests.
- AC 5 (`VSS-37a`): the three tests run and pass (Debug Log, Task 3). The AAR naming `f393c3a` is left for after merge (Task 7.4); no bead was changed.
- AC 6 (`VSS-eh41`): `Terminal.tsx`, `Terminal.test.tsx`, `mod-compatibility.ts` and its test are deleted; the `rg` check finds nothing. Under the backlog-drawdown rule and the controller's decision, the deprecated `filterModsByFilters` (`use-browse-mods.ts`, unused by product and E2E code; only its own tests imported it) and its `describe` with 13 tests are deleted in the same commit, along with the import of `ModFilters` that only it used. `terminal.spec.ts` was not run locally (no Docker for this story); CI's `e2e` job checks it on the PR.
- AC 7: under both pools every test passes. No web test redefines `window.location`, deletes `global.document` or assigns `global.WebSocket`; the two hook tests and `cookies.test.ts` have no `@ts-expect-error`. URL: `setTestUrl` from new `web/tests/location.ts` (`jsdom.reconfigure`), reset after each test by `tests/setup.ts`. WebSocket: `vi.stubGlobal` with `vi.unstubAllGlobals()` in the top-level `afterEach`. SSR cookie tests: `cookies.ssr.test.ts` with `// @vitest-environment node`; `setCookie`/`deleteCookie` now assert `not.toThrow()` instead of the cookie jar (Dev Notes "The stub changes", 3). `tests/setup.ts` runs its DOM steps only when `window` exists.
- AC 8: `web/vitest.config.ts` sets `pool: 'vmThreads'`; no `isolate: false`; no per-file pool.
- AC 9, a deviation: the suite is 132 files and 3,307 tests, all passing, not 3,320, because the 13 `filterModsByFilters` tests are also deleted (controller decision 5). 3,353 - 3 placeholders - 27 Terminal - 3 mod-compatibility - 13 `filterModsByFilters` = 3,307; 133 - 2 + 1 = 132 files.
- Tests deleted on purpose: the 33 in Dev Notes "Tests deleted on purpose", plus `use-browse-mods.test.tsx` `describe('filterModsByFilters')`: returns all mods when filters are undefined; returns all mods when filters are empty object; filters by side (exact match); filters by side "both"; filters by single tag (OR logic within tags); filters by multiple tags (OR logic); filters tags case-insensitively; filters by modType; filters out mods that do not match modType; combines multiple filters with AND logic; returns empty array when no mods match filters; handles empty mods array; filters with multiple filter types combined. The skipped remove-button test was replaced, not deleted, so the count is unchanged by it.
- AC 10: local numbers in the Debug Log (forks about 9.1 s wall, 132 jsdom setups; `vmThreads` about 5.0 s wall, one jsdom per worker). CI's `web` job time (before: 60 s on `main`) is recorded after the PR runs (Task 7.3); no PR was opened here.
- AC 11: `project-context.md` has the stubbing paragraph in section 2 and names `it.skip` / `test.skip` / `describe.skip` in section 8, with the E2E precondition skip allowed.
- AC 12: `just check` passes with 0 Pyright warnings and 0 skipped web tests; nothing written under `dev/`.
- Not done here (not authorized in this run): Task 7.3 PR and CI numbers; Task 7.4 AARs and closes for `VSS-1ar`, `VSS-hnl`, `VSS-6wj`, `VSS-eh41`, `VSS-37a` (after merge).
- No E2E or manual check: nothing an admin can see changes.
- Review (LOW-1, backlog drawdown, beyond the story's "no other test changed"): `tests/setup.ts` installs no-op `Element.prototype.scrollIntoView` and `scrollTo` (`vi.stubGlobal`) before each test and clears `sessionStorage` after each, which removes a pre-existing order dependence in `BrowseTab.test.tsx`. The per-describe stubs in `BrowseTab.test.tsx` and `use-browse-scroll-restoration.test.ts` stay: they install the spies those tests assert on. `project-context.md` says shared jsdom-missing APIs are stubbed once in setup. Test count unchanged.

### File List

- Modified: `api/tests/test_mod_service.py`
- Modified: `api/tests/test_mods_router.py`
- Modified: `web/src/components/FilterControls.test.tsx`
- Modified: `web/src/components/ModTable.test.tsx`
- Modified: `web/src/hooks/use-browse-mods.ts`
- Modified: `web/src/hooks/use-browse-mods.test.tsx`
- Modified: `web/src/hooks/use-console-websocket.test.ts`
- Modified: `web/src/hooks/use-log-stream.test.ts`
- Modified: `web/src/lib/cookies.test.ts`
- Added: `web/src/lib/cookies.ssr.test.ts`
- Added: `web/tests/location.ts`
- Modified: `web/tests/setup.ts`
- Modified: `web/vitest.config.ts`
- Modified: `project-context.md`
- Deleted: `web/src/features/terminal/Terminal.tsx`
- Deleted: `web/src/features/terminal/Terminal.test.tsx`
- Deleted: `web/src/lib/mod-compatibility.ts`
- Deleted: `web/src/lib/mod-compatibility.test.ts`
- Modified: `_bmad-output/implementation-artifacts/20-2-green-quiet-check.md`

## Senior Developer Review (AI)

**Date:** 2026-11-17
**Reviewer:** GLM-5.3-Flash via OpenCode (Z.ai coding plan), delegated read-only review of `800af7a..ef2d6ee`
**Outcome:** Approve → low findings fixed

**Summary:** All 12 ACs are met with the recorded deviations. 0 Pyright warnings, with annotations only. 0 skipped web tests, and no skip calls remain. The claimed game-version filter coverage exists, with assertions. The deleted code has no remaining uses (including E2E and dynamic imports). The new remove-dialog test is sensitive to each behaviour it pins. The dev's deviation was verified correct: the "Removing..." branch is reachable through a second dialog, so `ModTable.tsx` is unchanged. Stubbing is restored between tests and passes under `vmThreads` and `forks`; there is no `isolate`, no per-file pool and no new dependency. Reviewer ran `just lint`, `just typecheck`, `just test-api` (3334), and `just test-web` (3307) several times under both pools, plus `--sequence.shuffle` runs.

### Action Items

- [x] [Low] LOW-1 `BrowseTab.test.tsx` had a within-file order dependence under `--sequence.shuffle` in both pools. It predates this story: a `scrollIntoView` stub that was never restored, plus a `sessionStorage` entry leaking between tests. Fixed in 351eec8, per the maintainer's backlog-drawdown rule rather than as a bead: `web/tests/setup.ts` stubs `scrollIntoView` and `scrollTo` fresh before each test and clears `sessionStorage` after each, and `project-context.md` gains the rule. Shuffle runs after the fix: the file 12/12 (vmThreads) and 4/4 (forks); the whole suite 3/3 in each pool; the controller re-ran the whole suite shuffled twice, 3307/3307.
- [x] [Low] LOW-2 the "Not changed" bullet and AC 9 counts were stale after `filterModsByFilters` was removed (fixed, fbc82c0).
- Info: no vmThreads memory warnings in full runs.

## Change Log

- 2026-11-17: Story created and validated (create-story workflow, non-interactive). Prototype of Tasks 1, 2, 4 and 5 at 7f04ea2, discarded.
- 2026-11-17: Implemented Tasks 1-6 and the gate (dev-story workflow); `filterModsByFilters` removed per the controller; `ModTable.tsx` left unchanged because "Removing..." is reachable (Completion Notes). Status review.
- 2026-11-17: Review fixes: browser scroll stubs and a `sessionStorage` clear in `tests/setup.ts` (LOW-1); Dev Notes and AC 9 corrected to what shipped (LOW-2).
- 2026-11-17: Code review (GLM-5.3-Flash): approved; LOW-1 (shuffle-order flake) and LOW-2 fixed. Status done.
