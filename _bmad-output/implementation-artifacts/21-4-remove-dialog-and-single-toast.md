# Story 21.4: The Mod Remove Dialog Waits, and One Toast per Failure

Status: review

<!-- Implements FR271-FR274 and FR286, Epic 21 ADR-6, ADR-7 and ADR-16. Beads: VSS-oc28 (UI-096), VSS-q38r (UI-097, pulled in by Matt, 2026-11-17); maintainer decision 4 (the remove dialog). Stories run in order 21.1 to 21.8, each stacked on the previous. Line references were verified at 966204f (epic-21-planning; its web/ is the code the ADRs cite at 05436da) and must be re-checked at implementation time: Story 21.1 reformats about 231 web files with Prettier first (quotes, wrapping and line numbers move; `Layout.tsx` and `App.tsx` change from double to single quotes). Web only. No API change, no new dependency. -->

## Story

As an **administrator**,
I want **the remove dialog to show me the removal until it is done, one message when something fails, and mod data that follows the installed game version**,
so that **I know whether the mod was removed, am not told the same error twice, and do not read badges for a game version I no longer run**.

## Acceptance Criteria

1. **Given** the remove dialog of an installed mod
   **When** I confirm
   **Then** the dialog stays open, the confirm button shows a spinner and "Removing...", and the confirm and Cancel buttons are disabled
   *(Covers FR271; Matt, 2026-11-17)*

2. **Given** a removal that is running
   **When** I press Escape
   **Then** the dialog stays open
   *(Covers FR271; ADR-6 decision 4; Matt, 2026-11-17)*

3. **Given** a removal that is running
   **When** the DELETE succeeds
   **Then** the dialog closes, the mod is no longer in the list, and the success message ("Removed <slug>") is shown once
   *(Covers FR271)*

4. **Given** a removal that is running
   **When** the DELETE fails (an API refusal, or a request that never reaches the API)
   **Then** exactly one error toast is shown, the dialog stays open with the confirm button enabled and labelled "Remove" again, Cancel is enabled, and the mod is back in the list behind it
   *(Covers FR272; ADR-6 decision 3; Matt, 2026-11-17)*

5. **Given** the dialog after a failed removal
   **When** I confirm again or cancel (the Cancel button or Escape)
   **Then** confirming sends a new DELETE and cancelling closes the dialog with the mod still installed
   *(Covers FR272)*

6. **Given** a removal of mod A that failed or finished
   **When** I open the remove dialog of mod B
   **Then** its confirm button reads "Remove" and is enabled; "Removing..." is shown only in the dialog of the mod whose DELETE is running, and the end of A's removal never closes B's dialog
   *(Covers FR273; Matt, 2026-11-17)*

7. **Given** the installed mods as cards (below 1024px)
   **When** I remove a mod from its card
   **Then** the dialog behaves the same as from the table
   *(Covers FR271)*

8. **Given** the only installed mod
   **When** I confirm its removal
   **Then** the dialog stays open over the "No mods installed yet" text until the DELETE finishes, and behaves as in AC 3 and AC 4
   *(Covers FR271; found in story validation, see Dev Notes "ADR against the code")*

9. **Given** the server uninstall dialog while its request runs
   **When** I press Escape
   **Then** the dialog stays open, as its disabled Cancel button already implies
   *(Covers FR271; ADR-6 decision 7, found in planning)*

10. **Given** a mod install that the API refuses
    **When** the install dialog shows the failure
    **Then** exactly one error toast is shown, titled "Installation failed" with the API's message
    *(Covers FR274; `VSS-oc28`)*

11. **Given** a failed server install, server uninstall, server restart or mod update webhook change
    **When** the request fails
    **Then** exactly one error toast is shown, with the caller's title and the API's message. This holds for every caller, the "Restart Now" button of the restart banner in the header included (title "Failed to restart server")
    *(Covers FR274; ADR-7 decision 2; Matt, 2026-11-17; the banner found in story validation)*

12. **Given** `project-context.md`
    **When** I read its frontend rules
    **Then** it says that a hook-level `onError` replaces the query client's default, that an `onError` passed to `mutate` runs in addition, and that a hook either reports its error or silences the default for its callers, in which case every caller must report it
    *(Covers FR274; ADR-7 decision 5; Matt, 2026-11-17)*

13. **Given** the mod browser was opened while game version A was installed
    **When** the server status reports game version B (after an install of another version has finished)
    **Then** the browse cards are fetched again without a reload and show the "Has a release for" badges of version B, within one status poll and not after the five-minute cache time
    *(Covers FR286; `VSS-q38r`)*

14. **Given** the installed game version changes, or the server is uninstalled, or a server is installed where none was
    **When** I next open the installed mods list or a mod detail page
    **Then** their compatibility and update information is fetched again for the new version
    *(Covers FR286; ADR-16 decision 3)*

15. **Given** the server status is polled and the installed game version has not changed
    **When** any number of polls arrive, including the first one after a page load (with a server installed or with none) and a poll that fails
    **Then** no mod query is invalidated, and an invalidation never causes another one
    *(Covers FR286; ADR-16 decision 2)*

16. **Given** a server install has been started and has not finished
    **When** the install request's success handler runs
    **Then** the refresh of mod data does not depend on it: the trigger is the version the server status reports
    *(Covers FR286; ADR-16 decision 1)*

17. **Given** the E2E suite
    **When** CI runs it
    **Then** untagged specs cover the remove dialog with the DELETE stubbed (a delayed success and an error, from the table and from a card) and the browse refresh with the server status and the browse answer stubbed (the version changes between two polls), send no request that changes the stack, and pass on the throwaway container
    *(Covers FR271, FR272, FR286)*

18. **Given** the whole change
    **When** `just check` runs
    **Then** it passes with no new lint or type suppression, no `cast`, no skipped test and no new dependency; every existing test passes except the three listed under "Existing tests that change"

## Tasks / Subtasks

<!-- Six tasks, the project's limit (change proposal, section 3); do not add a seventh. Each functional task includes its tests in the same commit, red first. Commit per task: type(story-21.4/task-N): ...; `fix` only where the subject below says so, written for admins. After Story 21.1, run Prettier on every web file you change (the recipe and check Story 21.1 leaves in `just format-web` / `just lint-web`). -->

- [x] Task 1: The remove dialog waits for the removal; the server uninstall dialog ignores Escape while it runs + tests (AC: 1, 2, 3, 4, 5, 7, 8, 9)
  - [x] 1.1: `web/src/components/ModTable.tsx`: the confirm button (`AlertDialogAction`, `:453-466`) becomes `<Button variant="destructive">` from `@/components/ui/button` (new import; remove `AlertDialogAction` from the import at `:40`), with `onClick={handleRemoveConfirm}`, `disabled={isRemoving}`, the same `data-testid="remove-dialog-confirm"` and the same spinner and labels. The `className` with the hand-written destructive colours goes; the variant supplies them
  - [x] 1.2: **Keep `AlertDialogCancel`** (`:447-452`) and add `disabled={isRemoving}`. Do not replace it with a plain button as `UninstallConfirmDialog` has: Radix's alert dialog moves focus to its Cancel element when it opens and to nothing else (Dev Notes "The dialog")
  - [x] 1.3: `handleRemoveConfirm` (`:226-238`): return early when `isRemoving`; drop the `onError` that closes the dialog (`:234-236`); keep `onSuccess` (`onRemoved`, then close). `handleRemoveCancel` (`:240-242`) does nothing while `isRemoving`. `onOpenChange` (`:437`) already calls `handleRemoveCancel` for a close, so Escape is covered by the same guard
  - [x] 1.4: Render the dialog in the empty state too (AC 8): build the dialog element once (a `const removeDialog = (...)` before the early returns at `:353-370`) and render it in the main return and beside the `mod-table-empty` block (`:361-370`, wrapped in a fragment). Without this the dialog unmounts the moment the last mod is removed optimistically
  - [x] 1.5: `web/src/components/UninstallConfirmDialog.tsx:66`: `onOpenChange` no longer goes straight through: a close request while `isPending` is ignored, any other call is passed on. Nothing else in the file changes (its Cancel button stays as it is; see "Not changed")
  - [x] 1.6: Update the file header of `ModTable.tsx` (`:1-16`) with one line for this story. Tests (Dev Notes "Unit tests", Task 1 rows) and the three rewrites in "Existing tests that change", red first
  - [x] 1.7: Commit `fix(story-21.4/task-1): the remove mod dialog stays open until the mod is removed`

- [x] Task 2: The pending state belongs to the dialog's own mod + test (AC: 6)
  - [x] 2.1: `ModTable.tsx:130`: also take `variables` from `useRemoveMod()` (the slug being removed). `isRemoving` is true only when the mutation is pending **and** a dialog is open **and** `variables === modToRemove.slug`; the pattern of `isTogglingMod` (`:244-249`)
  - [x] 2.2: In `handleRemoveConfirm`, read the slug into a local before calling `mutate`, and in `onSuccess` close the dialog only if it is still this mod's: `setModToRemove((current) => (current?.slug === slug ? null : current))`
  - [x] 2.3: Test: the second mod's dialog while the first DELETE is held open (Dev Notes "Unit tests", Task 2 row). It fails against Task 1's code and passes after 2.1 and 2.2
  - [x] 2.4: Commit `refactor(story-21.4/task-2): the remove dialog's pending state belongs to its own mod` (no release note: after Task 1 an admin cannot reach the fault with a pointer or keyboard; see Dev Notes "The dialog")

- [x] Task 3: A failed mod install shows one toast + tests (AC: 10) (`VSS-oc28`)
  - [x] 3.1: First write the test (Dev Notes "Unit tests", Task 3 row) and see it fail with **two** calls of `toast.error`; record the failing output in the Dev Agent Record
  - [x] 3.2: `web/src/hooks/use-mods.ts` `useInstallMod` (`:88-98`): add `onError: () => {}` with the comment the two existing hooks carry (`:374-375`): the caller reports errors, so the global toast is skipped. Update the hook's doc comment (`:69-87`): "Errors are not toasted globally; pass `onError` to `mutate` to report them"
  - [x] 3.3: Check the hook's only caller still reports: `InstallConfirmDialog.tsx:117-122` ("Installation failed" with the message). No change there
  - [x] 3.4: Commit `fix(story-21.4/task-3): a failed mod install shows one error message, not two`

- [x] Task 4: The same for the server install, uninstall and restart and the webhook setting; the rule in `project-context.md` + tests (AC: 11, 12)
  - [x] 4.1: Tests first (Dev Notes "Unit tests", Task 4 rows), each red with two toasts
  - [x] 4.2: `web/src/hooks/use-server-status.ts`: `useRestartServer` (`:158-167`), `useInstallServer` (`:188-200`), `useUninstallServer` (`:283-295`); `web/src/hooks/use-api-settings.ts`: `useSetModUpdateWebhook` (`:144-153`). Each gets `onError: () => {}` with the same comment and a line in its doc comment
  - [x] 4.3: **`web/src/components/PendingRestartBanner.tsx:33-39` passes no `onError`.** Add one: `toast.error('Failed to restart server', { description: error.message })` (import `toast` from `sonner`), the title `ServerControls.tsx:90` uses. Without it, silencing `useRestartServer` leaves a failed restart from the banner with no message at all (Dev Notes "ADR against the code")
  - [x] 4.4: Re-check every caller at implementation time with `grep -rn "useRestartServer\|useInstallServer\|useUninstallServer\|useSetModUpdateWebhook\|useInstallMod" web/src --include=*.tsx | grep -v test`; the list verified at 966204f is in Dev Notes "The five hooks". A caller added by Stories 21.1 to 21.3 must report its error too
  - [x] 4.5: Commit `fix(story-21.4/task-4): a failed server install, removal or restart shows one error message, not two` (the webhook setting and the banner are in this commit; ADR-7 consequences)
  - [x] 4.6: `project-context.md`, section "Frontend (TypeScript)" (`:491-506`), after the query keys block: the rule (text in Dev Notes "The rule for project-context.md"). Commit `docs(story-21.4/task-4): add the mutation onError rule to project-context`

- [x] Task 5: Mod data is fetched again when the server status reports another installed game version + tests (AC: 13, 14, 15, 16) (`VSS-q38r`)
  - [x] 5.1: `web/src/hooks/use-server-status.ts`: new exported hook `useRefreshModDataOnGameVersionChange()` after `useServerStateToasts` (`:230-263`); behaviour and a sketch in Dev Notes "The version watcher"
  - [x] 5.2: `web/src/components/layout/Layout.tsx:11-12`: call the hook once at the top of `Layout`. `Layout` is rendered once (`App.tsx:121`), and `Sidebar` (`layout/Sidebar.tsx:61`) already runs the status query on every page, so no request is added
  - [x] 5.3: Do not touch the `onSuccess` of `useInstallServer` or `useUninstallServer` for this (ADR-16 decision 4; AC 16). Do not change `BROWSE_STALE_TIME` (`use-browse-mods.ts:24`) or any other stale time
  - [x] 5.4: Tests (Dev Notes "Unit tests", Task 5 rows), red first
  - [x] 5.5: Commit `fix(story-21.4/task-5): browse cards update their game-version badges after the server version changes`

- [ ] Task 6: E2E specs with stubbed answers, the README counts, quality gate and review hand-off (AC: 17, 18, all)
  - [x] 6.1: New `web/e2e/mod-remove-dialog.spec.ts` and `web/e2e/browse-version-refresh.spec.ts` (Dev Notes "E2E"), untagged. Run them against the dev stack rebuilt from this branch (`just docker restart`, then `cd web && bunx playwright test e2e/mod-remove-dialog.spec.ts e2e/browse-version-refresh.spec.ts`) and in `just test-e2e-ci` (both passes green). Do not start or stop the game server; no screenshots
  - [x] 6.2: `web/e2e/README.md:10` and `:50`: add the number of new tests to the untagged count, the CI count and the total (at 966204f: 119 untagged, 146 of 150; five new tests give 124, 151 of 155). Read the counts the README has then, since Stories 21.1 to 21.3 may have changed them, and confirm with `cd web && bunx playwright test --list`. Commit `test(story-21.4/task-6): cover the remove dialog and the browse refresh end to end`
  - [x] 6.3: Record in the Dev Agent Record that `GET /api/v1alpha1/mods` and `GET /api/v1alpha1/server/status` (state and version) on the dev stack returned the same before and after the E2E run
  - [x] 6.4: `just check` passes; `just test-web` reports no skipped test beyond the pre-existing ones (`VSS-hnl`); the diff adds no suppression and no `cast`; `git status --short` shows nothing under `dev/`
  - [ ] 6.5: (left for the maintainer) Manual check on the Docker stack (needs the maintainer's confirmation before it is ticked, `project-context.md`): Dev Notes "Manual check"
  - [ ] 6.6: (status and sprint status done; PR and the bead links left to the orchestrator, the dev brief forbids push and PR) Story status `review`, `just sprint set 21-4-remove-dialog-and-single-toast review`, PR (base: Story 21.3's branch while its PR is open, otherwise `main`; Story 21.1 must be merged first), PR link on `VSS-oc28` and `VSS-q38r`. The PR description says "API contract changes: none" and lists the four release-note subjects. Commit `chore(story-21.4/task-6): validate and move story 21.4 to review`

## Dev Notes

### The faults (verified at 966204f)

- **The dialog closes before the removal.** The confirm button is Radix's `AlertDialogAction` (`ModTable.tsx:453-457`), which closes the dialog on click; the DELETE then runs with nothing on screen. `handleRemoveConfirm` also closes on error (`:234-236`).
- **One pending flag for every mod.** `isRemoving` is `useRemoveMod().isPending` (`:130`), shown by whichever dialog is open (`:458-465`). Because the dialog closes at once today, an admin can open mod B's dialog while mod A's DELETE runs and read "Removing..." there.
- **Two toasts.** The query client's default mutation `onError` shows a toast (`web/src/api/query-client.ts:34-39`, through `handleApiError`, `web/src/api/error-handler.ts:20-42`: title "Error", "Access Denied" or "Authentication Failed"). Five hooks declare no `onError`, so the default runs, and their callers pass an `onError` to `mutate` that shows a second toast with the same message. Reproduced in story validation with a throwaway test (a query client built like the app's, each hook's `mutate` called with an `onError` that shows a toast, the request answered 409): all five gave `expected "vi.fn()" to be called 1 times, but got 2 times`; with `onError: () => {}` on the hook all five gave one call, the caller's.
- **Stale badges.** Browse pages are kept five minutes (`BROWSE_STALE_TIME`, `use-browse-mods.ts:24`); nothing invalidates them when the installed game version changes.

### The dialog (Tasks 1 and 2)

The whole change is in `ModTable.tsx`; the table and the cards share the one dialog (`:419` and `:337` both call `handleRemoveClick`), so AC 7 needs no code of its own.

- **Order of events on success** (TanStack Query v5): the hook's `onMutate` removes the row from the cached list (`use-mods.ts:223-245`), the request runs, the hook's `onSettled` invalidates the list (`:253-255`), then the `onSuccess` passed to `mutate` runs: `onRemoved` (the "Removed <slug>" toast, `InstalledTab.tsx:75-81`) and the close. So the row disappears behind the open dialog at once and the dialog closes when the request has answered. The dialog's title comes from `modToRemove` (component state, `:125`, `:441`), not from the list, so it keeps the name while the row is gone.
- **On error** the hook's `onError` restores the list and calls `handleApiError` (`use-mods.ts:246-252`): one toast, titled "Error" (or "Access Denied" / "Authentication Failed"). `ModTable` passes no `onError` any more, so nothing closes the dialog; `isPending` becomes false and the button reads "Remove" again. `useRemoveMod` is **not** one of the five hooks and does not change.
- **Cancel stays `AlertDialogCancel`.** `@radix-ui/react-alert-dialog` handles `onOpenAutoFocus` by preventing the default focus and focusing its Cancel element (`node_modules/@radix-ui/react-alert-dialog/dist/index.mjs:58-61`: `cancelRef.current?.focus(...)`). With no `AlertDialogCancel` in the content nothing is focused when the dialog opens. `AlertDialogCancel` accepts `disabled`, and its click asks for a close through `onOpenChange`, which the guard handles; the existing `onClick={handleRemoveCancel}` may stay.
- **Escape.** Radix listens for Escape on the document and calls `onOpenChange(false)`; a controlled dialog whose state does not change stays open. The guard is one condition in `handleRemoveCancel`. An alert dialog never closes on an outside click.
- **The empty state (AC 8).** `ModTable` returns early when the list is empty (`:361-370`), and the dialog is in the main return only (`:434-469`). The optimistic removal of the last mod empties the list, so today's structure would unmount the dialog on confirm. The component itself stays mounted (so the `mutate` callbacks still run); only the dialog element has to be rendered in both branches. The loading branch (`:353-359`) needs no dialog: `isLoading` is true only before the first answer.
- **Task 1 against Task 2.** After Task 1 the dialog is modal for the whole request, so a second dialog cannot be opened with a pointer or the keyboard while a DELETE runs, and the shared flag is false again by the time any other dialog opens. Task 2 makes that true by construction instead of by the modal (FR273, ADR-6 decision 5), and makes the close on success belong to the mod: a unit test can reach the state with `fireEvent.click` on the second row's remove button (jsdom does not apply the modal's `pointer-events`), and there the shared flag shows "Removing..." in B's dialog and A's success closes it.
- **Focus after an error.** While the request runs both buttons are disabled, so the browser drops focus to the document. Escape still works (the listener is on the document) and Tab re-enters the dialog (Radix's focus scope). The E2E checks Escape after an error. Do not add focus management beyond that.
- A removal that never answers holds the dialog open; any failure, a network failure included, returns it to "Remove" (change proposal, section 3). The unit test with a rejected `fetch` covers it.

Prototype result (story validation, since discarded): with 1.1 to 1.4 and Task 2 applied, `Cancel` has focus on open, the dialog survives Escape and the empty state while pending, and the tests described below pass.

### The uninstall dialog (Task 1.5)

`UninstallConfirmDialog.tsx:66` passes `onOpenChange` straight to `AlertDialog`, so Escape closes it while `isPending` although both buttons are disabled (`:105`, `:113`). The page closes it in the mutation's `onSuccess` (`VersionPage.tsx:73-80`) and leaves it open on error (`:81-85`). The guard is inside the component:

```tsx
onOpenChange={(next) => {
  if (!next && isPending) return;
  onOpenChange(next);
}}
```

`VersionPage`'s `setIsUninstallDialogOpen(false)` in `onSuccess` does not go through this handler, so the dialog still closes on success. Prototype: `UninstallConfirmDialog.test.tsx` and `VersionPage.test.tsx` pass unchanged with the guard.

### The five hooks (Tasks 3 and 4)

Every caller, read at 966204f:

| Hook | Callers | Caller's toast on error |
|---|---|---|
| `useInstallMod` (`use-mods.ts:88-98`) | `InstallConfirmDialog.tsx:101` | `:117-122` "Installation failed" |
| `useRestartServer` (`use-server-status.ts:158-167`) | `features/dashboard/ServerControls.tsx:28` | `:89-93` "Failed to restart server" |
| | `components/PendingRestartBanner.tsx:31` | **none** (`:33-39` passes `onSuccess` only) |
| `useInstallServer` (`use-server-status.ts:188-200`) | `QuickInstallButton.tsx:64` | `:92-96` "Installation failed" |
| | `InstallVersionDialog.tsx:158` | `:208-212` "Installation failed" |
| | `ServerInstallCard.tsx:35` | `:51-55` "Failed to start installation" |
| `useUninstallServer` (`use-server-status.ts:283-295`) | `features/game-server/VersionPage.tsx:71` | `:81-85` "Failed to remove server" |
| `useSetModUpdateWebhook` (`use-api-settings.ts:144-153`) | `features/settings/ModUpdateWebhookSetting.tsx:32` | `:40-42` "Update failed" |

- The fix per hook is one option, in the existing form (`use-mods.ts:374-375`, `:427`):

  ```ts
  // The caller reports errors; skip the global toast so they are not shown twice.
  onError: () => {},
  ```

- A hook-level `onError` replaces the client default; the `onError` passed to `mutate` still runs. Nothing else in the hooks changes: `onSuccess` and `onSettled` stay.
- `PendingRestartBanner` is rendered in the header on every page (`layout/Header.tsx:41`). Today a failed restart from it shows one toast, the default "Error". With the hook silenced it must show its own (Task 4.3).
- Not touched: `useStartServer` and `useStopServer` (their hook `onError` only rolls back, `:96-101`, `:140-145`, and `ServerControls` shows the one toast), `useEnableMod`, `useDisableMod`, `useRemoveMod` (they call `handleApiError` themselves), `useCheckModUpdates`, `useChangeModVersion`, `useApplyAllModUpdates`, `useUpdateApiSetting`.
- **Consequence to accept (ADR-7):** a 401 or 403 on these five actions now shows the caller's title ("Installation failed") with the server's message, where the default handler titled it "Authentication Failed" or "Access Denied".

### The rule for project-context.md (Task 4.6)

Under "Frontend (TypeScript)", after the query keys block (`project-context.md:498-506`):

> **Mutation errors (TanStack Query v5):** the query client's default `onError` shows a toast for every failed mutation (`web/src/api/query-client.ts`). An `onError` declared in a hook's `useMutation` options **replaces** that default; an `onError` passed to `mutate(...)` runs **in addition** to whichever of the two applies. So each mutation hook does one of two things, never both and never neither: it reports the error itself (its `onError` calls `handleApiError`, as the hooks that roll back an optimistic update do), or it silences the default with `onError: () => {}` and a comment, and then **every** caller passes an `onError` to `mutate` that shows a toast. A hook with no `onError` whose callers show a toast shows two.

Keep the wording; adjust only to the file's style. The three code comments that state half the rule (`use-mods.ts:155`, `:204`, `:250`) stay.

### The version watcher (Task 5)

Behaviour (ADR-16 decisions 1 to 3):

- It reads the status query (`useServerStatus()`, key `['server', 'status']`, polled every 5 s, `use-server-status.ts:25`, `:43-52`) and looks only at `data.data.version` (`ServerStatus.version: string | null`, `web/src/api/types.ts:63`).
- **Not loaded is not "no version".** While the query has no data yet, the hook remembers nothing. The first loaded value is remembered and invalidates nothing, whether it is a version or `null` (no server installed). This is the difference from a plain "previous !== current" on `string | null | undefined`: an initial `undefined` followed by `'1.22.7'` must not count as a change, but `'1.22.7'` followed by `null` (uninstall) must.
- After that, a value different from the remembered one (version to version, version to `null`, `null` to version) calls `queryClient.invalidateQueries({ queryKey: queryKeys.mods.all })` once and is remembered. An equal value does nothing.
- A failed poll keeps the query's last data, so the version does not change and nothing is invalidated.
- **No loop:** `['mods']` is a prefix of every mod query (`web/src/api/query-keys.ts:14-41`: the installed list, detail, lookup, browse, game versions, tags, update status) and of nothing else. The status query is under `['server']`, so the invalidation cannot change the hook's own input. The effect depends on the loaded flag and the version only.

A sketch (the prototype's shape; name the ref and write the comments as the file does):

```ts
export function useRefreshModDataOnGameVersionChange(): void {
  const queryClient = useQueryClient();
  const { data } = useServerStatus();
  const isLoaded = data?.data !== undefined;
  const version = data?.data?.version ?? null;
  const previousRef = useRef<{ version: string | null } | null>(null);

  useEffect(() => {
    if (!isLoaded) return;
    const previous = previousRef.current;
    previousRef.current = { version };
    if (previous !== null && previous.version !== version) {
      queryClient.invalidateQueries({ queryKey: queryKeys.mods.all });
    }
  }, [isLoaded, version, queryClient]);
}
```

Why the status and not the install mutation: `POST /server/install` answers when the installation has **started** (the callers' toast reads "Server installation started", `InstallVersionDialog.tsx:201`), so its `onSuccess` runs while version A is still installed. The API writes the version file at the end of an install (`api/src/vintagestory_api/services/server.py:841-842`, `_save_installed_version`, before the state becomes `installed` at `:845`), and both `GET /server/status` (`:916-918`) and the browse route (`routers/mods.py:356`, through the mod service's game version provider) read the installed version on every request. So a status answer that names version B is never earlier than a browse answer for B. This order was checked by reading the code; it is not checked by installing another game version on the dev stack, which would change real state that cannot be restored exactly (see "Manual check").

What an admin sees: queries on screen (the browse page, the installed list, an open mod detail page) are fetched again at once; the others are stale and are fetched when next shown (AC 14). During an install the status may report no version for a moment; then mod data is fetched twice, which is correct (ADR-16 consequences). On a stack with no game server the Mods pages show the empty state (`App.tsx:90-101`), so nothing is on screen to fetch.

### Unit tests

All web unit tests run in Vitest's `vmThreads` pool: stub `fetch` as the neighbouring tests in each file do, and follow the stubbing rule in `project-context.md:167-172`. Where a test counts toasts, build the query client like the app's (default mutation `onError: (error) => handleApiError(error)`), as `ModTable.test.tsx:2274-2281` (`createAppLikeQueryClient`) does; a client without the default cannot show the fault.

| Task | File | Test | Asserts |
|---|---|---|---|
| 1 | `ModTable.test.tsx` "remove dialog" | stays open while the DELETE is held | after confirm: dialog present, confirm shows "Removing..." and is disabled, Cancel disabled, the row is gone, the title still names the mod; `fireEvent.keyDown(document, { key: 'Escape' })` leaves it open; `onRemoved` not called |
| 1 | same | closes when the DELETE succeeds | resolve the held request: dialog gone, `onRemoved` called once with the slug |
| 1 | same | stays open when the DELETE is refused | 409 with a message: `toast.error` called once (`'Error'`, the message), dialog present, confirm enabled with text "Remove", Cancel enabled, the row is back |
| 1 | same | a second confirm sends a second DELETE; Escape then closes | two DELETE calls; after the second failure Escape removes the dialog; `onRemoved` never called |
| 1 | same | a request that fails without an answer returns the dialog to "Remove" | `fetch` rejects for DELETE: one toast, confirm enabled |
| 1 | same | Cancel has focus when the dialog opens | `expect(screen.getByTestId('remove-dialog-cancel')).toHaveFocus()` |
| 1 | same | the only mod: the dialog stays over the empty state | a list of one mod, DELETE held: `mod-table-empty` and `remove-dialog` both present, "Removing..."; resolve: dialog gone |
| 1 | `ModTable.test.tsx` "cards below lg" | from a card, DELETE held | at phone width: the same pending assertions, then success closes |
| 1 | `UninstallConfirmDialog.test.tsx` "pending state" | Escape while pending is ignored | `isPending: true`, Escape on the document: `onOpenChange` not called |
| 1 | same | Escape when not pending closes | `isPending: false`: `onOpenChange` called with `false` |
| 2 | `ModTable.test.tsx` "remove dialog" | another mod's dialog never shows "Removing..." | hold A's DELETE; `fireEvent.click` B's remove button: title names B, confirm reads "Remove" and is enabled; resolve A: `onRemoved('smithingplus')` once and B's dialog still open |
| 3 | `use-mods.test.tsx` `useInstallMod` | a refused install shows one toast | app-like client; `mutate({ slug }, { onError: (e) => toast.error('Installation failed', { description: e.message }) })`; 409: `toast.error` called once, with `'Installation failed'` and the API's message |
| 4 | `use-server-status.test.tsx` | the same for `useRestartServer`, `useInstallServer`, `useUninstallServer` | one test each, one call with the caller's title |
| 4 | `use-api-settings.test.tsx` | the same for `useSetModUpdateWebhook` | one call |
| 4 | `PendingRestartBanner.test.tsx` | a failed restart shows one toast | mock `sonner`; app-like client; restart answered with an error: `toast.error` called once with `'Failed to restart server'` and the message; `onRestart` not called |
| 5 | `use-server-status.test.tsx` | first status load invalidates nothing | spy on `queryClient.invalidateQueries`; status answers version A: not called |
| 5 | same | first load with no server invalidates nothing | status answers `not_installed`, `version: null`: not called |
| 5 | same | an unchanged version invalidates nothing | refetch the status twice with A: not called |
| 5 | same | a new version invalidates the mod queries once | seed `queryKeys.mods.all` and `queryKeys.mods.browse({ page: 1 })`; A then B: called once with `{ queryKey: ['mods'] }`; both seeded queries have `isInvalidated: true`; the status query has `isInvalidated: false` |
| 5 | same | nothing loops | after the change, wait (for example 50 ms inside `act`): still one call and no further status request |
| 5 | same | uninstall and install | B then `null`: a second call; `null` then B: a third |
| 5 | same | a failed poll invalidates nothing | A, then a 500, then A: not called |
| 5 | `layout/Layout.test.tsx` | the layout runs the watcher | render `Layout` with the status answering A, then B after a refetch: `invalidateQueries` called with `{ queryKey: ['mods'] }` |

To drive the status in the Task 5 tests, change what the stubbed `fetch` answers and call `await queryClient.refetchQueries({ queryKey: queryKeys.server.status })` inside `act`; do not use fake timers for the poll. The seeded mod queries have no observer, so invalidating them sends no request.

### Existing tests that change (deliberately)

Found by running the whole web suite against a throwaway prototype of Tasks 1, 2, 4.2, 3.2 and 5 (since discarded): 3,304 passed, 3 failed, all in `ModTable.test.tsx`. They assert the old behaviour and are rewritten as the Task 1 tests above:

- `ModTable.test.tsx:1053` "closes the dialog at once and reports the removal when the request completes": becomes "stays open while the DELETE is held" and "closes when the DELETE succeeds".
- `ModTable.test.tsx:1114` "closes dialog on remove error": becomes "a request that fails without an answer returns the dialog to 'Remove'".
- `ModTable.test.tsx:2352` "keeps the row of a refused removal, closes the dialog and shows the message" (Story 17.3): becomes "keeps the row of a refused removal, keeps the dialog open and shows the message"; its other assertions (the row, `onRemoved` not called, one toast `'Error'` with the busy message) stay.

Not failing, and unchanged: every other test of `ModTable.test.tsx` (the remove tests at `:506`, `:1855`, `:1950` and `:2072` only wait for the DELETE); `UninstallConfirmDialog.test.tsx`, `VersionPage.test.tsx`, `PendingRestartBanner.test.tsx`, `Layout.test.tsx`, `use-mods.test.tsx` (`:1660-1720` pins the one toast of enable, disable and remove), the component tests that mock the five hooks (`InstallConfirmDialog.test.tsx`, `InstallVersionDialog.test.tsx`, `ModCard.test.tsx`, `ModBrowseGrid.test.tsx`, `BrowseTab.test.tsx`, `ConsolePage.test.tsx`). `PendingRestartBanner.test.tsx` has no `sonner` mock; its existing failure test (`:428`) keeps passing with the real `toast`, and the new test mocks `sonner` in that file (check the other tests still pass with the mock in place).

No existing E2E test changes: `installed-mods-phone.spec.ts:271-273` and `content-security-policy.spec.ts:472-477` only open and cancel the dialog; `mod-file-refusals.spec.ts:165`, `:176` assert the "Error" toast of enable and disable, which this story does not touch; `install-file-conflict.spec.ts:71` filters for the "Installation failed" toast, which is the one kept.

Anything else that fails is a regression: fix the code, not the test.

### E2E

Both specs are read-only and untagged: they need no mod database and no game server, so CI's first pass runs them. Style of `e2e/installed-mods-phone.spec.ts` (`fakeInstalledMods`, `:64-175`) and `e2e/browse-game-version.spec.ts` (`browseBody`, `stubBrowse`, `:65-90`); copy helpers, do not import across specs. Header comment with the story, the FRs, what is stubbed and the requirements, as those files have. Use `serveConfigKey(page, API_KEY)` in `beforeEach`. Any stub that passes a request on to the API uses `fetchOnNewConnection(route)` (`e2e/config-js.ts`). The specs are type-checked (`just typecheck-web`).

**`web/e2e/mod-remove-dialog.spec.ts`** (FR271, FR272). `pretendServerInstalled(page)`; a stateful stub of the mod routes like `fakeInstalledMods`, with two or three made-up mods:

- `GET /mods` serves the current list; `GET /mods/updates` and `GET /mods/lookup/<slug>` as in the model.
- `DELETE /mods/<slug>` waits (about 1.5 s; `await new Promise((resolve) => setTimeout(resolve, 1500))` inside the route handler), then either removes the mod from the stub's list and fulfills `{ status: 'ok', data: { slug, pending_restart: false } }`, or fulfills 409 `{ detail: { code: 'MOD_OPERATION_IN_PROGRESS', message: '<a message>' } }`, as the test chose. Count the DELETEs.
- Every other non-GET is answered 500 `E2E_BLOCKED`, as in the model, so no write reaches the stack.

Tests:

1. **Table, delayed success** (1440 x 900): click `mod-remove-<slug>`, click `remove-dialog-confirm`; while the DELETE waits: `remove-dialog` visible, confirm has text "Removing..." and is disabled, `remove-dialog-cancel` disabled, `page.keyboard.press('Escape')` leaves the dialog visible, `mod-row-<slug>` has count 0. Then: the dialog has count 0, the row is still gone, a toast containing `Removed <slug>` is visible and `page.locator('[data-sonner-toast]')` has count 1. One DELETE.
2. **Table, error**: the same up to the wait; after the 409: exactly one toast (`[data-sonner-toast]` count 1) containing the message, the dialog visible, confirm enabled with text "Remove", `mod-row-<slug>` visible again. Then Escape: the dialog has count 0 and the row is still there. One DELETE.
3. **Cards, delayed success then nothing left** (390 x 844): from `installed-mod-card-<slug>`, the same pending assertions as test 1 and the close on success. Use the stub's last mod for it, or remove down to one first, so the dialog is seen over `mod-table-empty` (AC 8).

**`web/e2e/browse-version-refresh.spec.ts`** (FR286). Do **not** call `pretendServerInstalled`; stub the status completely so the test owns the version:

- `GET **/api/v1alpha1/server/status`: fulfill `{ status: 'ok', data: { state: 'installed', version: <current>, uptime_seconds: null, last_exit_code: null, available_stable_version: null, available_unstable_version: null, version_last_checked: null, disk_space: null } }`, where `<current>` is a variable of the test; `route.fallback()` for other methods. Count the answers.
- `GET /api/v1alpha1/mods/browse`: fulfill a body like `browseBody` whose `game_version` is the status stub's current version and whose `has_release_for_game_version` flags differ by version (for A: `e2e-has` true, `e2e-none` false; for B the other way round). Count the requests.
- Made-up versions (for example `1.22.7` and `1.22.8`); never the stack's own.

Tests:

4. **A version change refreshes the cards within one poll**: open `/game-server/mods/browse`, expect `mod-card-game-version-e2e-has` to have text `Has a release for 1.22.7`. Set the current version to B. Expect `mod-card-game-version-e2e-none` to have text `Has a release for 1.22.8` and `mod-card-game-version-e2e-has` to have text `No release for 1.22.8`, with a timeout of 15 s (one 5 s poll plus the request), and the browse request count to have grown. No reload, no navigation.
5. **Unchanged polls fetch nothing**: open the page, note the browse request count once the cards show, wait for two more status answers (`page.waitForResponse` on the status URL, twice), and expect the browse count unchanged.

The page's other mod requests (`/mods`, `/mods/gameversions`, `/mods/tags`) go to the stack as in `browse-game-version.spec.ts`; they are GETs. On the throwaway container the two that need the mod database fail fast and the filters show their error state, before and after the refresh; the tests assert only the cards.

Neither spec changes real state, so no snapshot guard is needed; Task 6.3 records the before and after anyway. No screenshots; nothing instance-specific (server name, keys) appears in an assertion or a message.

### Manual check (Task 6.5)

On the Docker stack built from this branch, without starting or stopping the game server and without installing or removing anything real. Run the two specs headed (`cd web && bunx playwright test e2e/mod-remove-dialog.spec.ts e2e/browse-version-refresh.spec.ts --headed`) and watch: the dialog holds with "Removing..." and closes on success; after the stubbed error it reads "Remove" again with one toast; the browse badges flip without a reload. With a real keyboard, in the remove dialog after a stubbed error: Tab moves into the dialog and Escape closes it.

Optional, the maintainer's own decision and not part of the dev agent's work: installing another game version on a stack he can spare and watching the browse page follow. The story does not ask for it, since it changes real state.

### Not changed (do not "fix" these here)

- `useRemoveMod` and its optimistic removal (ADR-6 decision 6); `useEnableMod`, `useDisableMod`; the query client's default `onError` and `handleApiError`. No `MutationCache` redesign (ADR-7 decision 4).
- `UninstallConfirmDialog`'s buttons. Its Cancel is a plain `Button`, so by the Radix code quoted above nothing is focused when it opens. That is listed as a follow-up, not fixed here: it was read in the library's code and not confirmed in a browser.
- `InstallConfirmDialog`, `InstallVersionDialog` and `VersionChangeConfirmDialog`: their dismissal while a request runs is as today.
- The `onSuccess` of `useInstallServer` and `useUninstallServer`; every stale time; the 5 s status poll.
- The toast titles of the callers, except the one added to `PendingRestartBanner`.
- `ModTable`'s sorting, columns and `SortableHeader` (Story 21.5 edits them next).
- The comment `// eslint-disable-next-line react-hooks/exhaustive-deps` at `ModTable.tsx:252` predates this story (the web has no ESLint); leave it, and add none.

### API contract changes

None. No route, request, response field, status code or error code changes. The web sends the same `GET` requests for mod data again when the server status reports another installed game version, and the same `DELETE /api/v1alpha1/mods/{slug}` as before.

### ADR against the code

- **ADR-7 decision 2 and the facts table** say each caller of the five hooks already shows a toast. `PendingRestartBanner.tsx:33-39` calls `useRestartServer` with no `onError` (the table lists only `ServerControls.tsx:90`). Silencing the hook as written would leave a failed restart from the header banner with no message. Task 4.3 gives the banner its own toast; AC 11 covers it.
- **ADR-6 decision 6** says the dialog keeps the mod's name because its text comes from component state. True, but the dialog element sits behind the early return for an empty list (`ModTable.tsx:361-370`), so removing the only installed mod would unmount it on confirm. Task 1.4 renders it in both branches; AC 8.
- **ADR-6 decision 1** says the confirm button becomes a plain button "as in `UninstallConfirmDialog`". Only the confirm button is changed; Cancel stays Radix's `AlertDialogCancel`, because the alert dialog focuses that element on open and `UninstallConfirmDialog`'s plain Cancel gets no focus.
- **ADR-6 decision 5** (pending per mod): after decision 4 the fault cannot be reached through the UI, so the commit is a `refactor` with no release note, and the close on success is tied to the mod as well (Task 2.2), which the ADR does not mention.
- **ADR-16 decision 2** says to compare "in the way `useServerStateToasts` compares states". That hook treats `undefined` as "no previous value" (`use-server-status.ts:237`), which works for a state that is never `null`. The version can be `null` (no server), and `null` must count as a value: the watcher keeps "not loaded" apart from "loaded with no version" (Dev Notes "The version watcher").
- **Change proposal, section 3** ("the story checks the real order once on the dev stack"): replaced by reading the API code (`services/server.py:841-845`, `:916-918`; `routers/mods.py:356`), because an install on the dev stack changes real state that cannot be restored exactly.
- Everything else in ADR-6, ADR-7 and ADR-16 matches the code at 966204f (line numbers re-read).

### Testing Requirements

**CRITICAL:** Tests are written with each task and committed with it, red first. `just test-web <file>` after each task; `just check` before review.

- Count toasts with `toHaveBeenCalledTimes(1)` **and** check the title and message; a test that only checks "called with" passes with two toasts.
- Hold a request open with a promise the test resolves (the pattern at `ModTable.test.tsx:1054-1071`), not with timers.
- No skipped test, no `cast`, no suppression. Web tests must not write into `dev/`.
- E2E: stubbed, read-only, untagged; `just test-e2e-ci` must pass both passes.

### Security Requirements

- No new endpoint and no new request. `DELETE /mods/{slug}`, the server install, uninstall and restart and the webhook setting stay Admin-only; the web's role handling is untouched. Toast text is rendered as text. The webhook URL is never put in a toast or a test message (`use-api-settings.ts:141-142`).

### Development Commands

- `just test-web src/components/ModTable.test.tsx src/components/UninstallConfirmDialog.test.tsx`
- `just test-web src/hooks/use-mods.test.tsx src/hooks/use-server-status.test.tsx src/hooks/use-api-settings.test.tsx src/components/PendingRestartBanner.test.tsx src/components/layout/Layout.test.tsx`
- `just typecheck-web`, `just lint-web`, `just check`; `just test-e2e-ci e2e/mod-remove-dialog.spec.ts e2e/browse-version-refresh.spec.ts`, then `just test-e2e-ci`
- Never raw `mise exec`. Do not run a whole-repo formatter beyond what Story 21.1 set up for the web.

### Previous Story Intelligence

- **17.3 (Task 4) and 18.2 ("Web"):** a hook-level `onError` replaces the query client's default, so a hook with one must call `handleApiError` itself; 18.2 saw the opposite effect on install in the browser and filed `VSS-oc28`. This story writes the rule down.
- **18.3:** the browse cards' flags refer to `game_version` in the browse answer; its review filed `VSS-q38r`.
- **16.5, 17.8:** the cards below `lg` share the table's handlers and the one dialog; `setViewportWidth` from `web/tests/viewport` switches the layout in unit tests.
- **19.7, 20.5, 20.6:** E2E specs run in CI on a throwaway container with no game server; `pretendServerInstalled` rewrites only a `not_installed` status; stubs that pass a request on use `fetchOnNewConnection`; untagged means CI's first pass.
- **20.2:** the `vmThreads` pool and its stubbing rule; no skipped unit tests.
- **17.x to 20.x reviews:** a `feat` or `fix` subject must describe what an admin can see; a completion note must be true of the code; manual checks wait for the maintainer; E2E that changes real state needs a snapshot guard (this story's E2E changes none).

### Git Intelligence

- Base `966204f` (`docs(epic-21): record the maintainer's answers and pull in VSS-q38r`) on `05436da` (`v0.1.0-rc.6`). Stories 21.1 (the Prettier reformat of the web), 21.2 and 21.3 land first; 21.1 moves lines in every file this story edits. Story 21.5 follows and edits `ModTable.tsx` and its test again.
- Planned commits: Task 1 `fix(story-21.4/task-1): the remove mod dialog stays open until the mod is removed`; Task 2 `refactor(story-21.4/task-2): ...`; Task 3 `fix(story-21.4/task-3): a failed mod install shows one error message, not two`; Task 4 `fix(story-21.4/task-4): a failed server install, removal or restart shows one error message, not two` and `docs(story-21.4/task-4): ...`; Task 5 `fix(story-21.4/task-5): browse cards update their game-version badges after the server version changes`; Task 6 `test(story-21.4/task-6): ...` and `chore(story-21.4/task-6): ...`. Four release notes, the four the change proposal lists for this story (section 2).

### Project Structure Notes

- New: `web/e2e/mod-remove-dialog.spec.ts`, `web/e2e/browse-version-refresh.spec.ts`.
- Modified source: `web/src/components/ModTable.tsx`, `UninstallConfirmDialog.tsx`, `PendingRestartBanner.tsx`, `layout/Layout.tsx`; `web/src/hooks/use-mods.ts`, `use-server-status.ts`, `use-api-settings.ts`.
- Modified tests: `web/src/components/ModTable.test.tsx`, `UninstallConfirmDialog.test.tsx`, `PendingRestartBanner.test.tsx`, `layout/Layout.test.tsx`; `web/src/hooks/use-mods.test.tsx`, `use-server-status.test.tsx`, `use-api-settings.test.tsx`.
- Modified documents: `project-context.md`, `web/e2e/README.md`. No file under `api/`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 21.4: The Mod Remove Dialog Waits, and One Toast per Failure]
- [Source: _bmad-output/planning-artifacts/prd.md] FR271, FR272, FR273, FR274, FR286
- [Source: _bmad-output/planning-artifacts/architecture/epic-21-maintainer-decisions-and-web-polish.md#ADR-6, #ADR-7, #ADR-16] and "Facts Checked in the Code" ("Mod removal and error toasts today")
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-17-epic-21.md] (section 2 release notes; section 3 risks; section 5 answers 3, 4 and 10)
- [Source: _bmad-output/implementation-artifacts/18-2-install-and-version-change-keep-records-right.md] ("Web"), [17-3-mod-operations-are-safe-against-each-other.md]
- Beads: `VSS-oc28`, `VSS-q38r`, parent `VSS-syuj`
- `project-context.md` (no suppressions; the `vmThreads` stubbing rule; manual test tasks need the maintainer's confirmation; commit format), `web/e2e/README.md` (tags and counts)

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5), BMAD dev-story, non-interactive.

### Debug Log References

- Task 3.1, red before the fix (`just test-web src/hooks/use-mods.test.tsx -t "one error toast"`):

  ```
  FAIL  src/hooks/use-mods.test.tsx > useInstallMod > one error toast (Story 21.4) > shows only the caller's toast for a refused install
  AssertionError: expected "vi.fn()" to be called 1 times, but got 2 times
  ```
- Task 4.1, red before the fix: the three `use-server-status` tests and the webhook test failed with `expected "vi.fn()" to be called 1 times, but got 2 times`; the banner test failed because the only toast was the default `'Error'`, not `'Failed to restart server'`.
- Task 1, red before the fix: the seven new remove dialog tests, the card test, the rewritten Story 17.3 test and the uninstall Escape test failed; the install dialogs' two "ignores Escape and the close button" tests failed before their guard.
- Task 5: the watcher tests were also run against a naive `previous !== current` comparison (no "not loaded" state); all seven failed, so the first-load tests do test the loaded/not-loaded distinction. The naive version was discarded.
- Task 5 tests: TanStack Query notifies observers on a timer tick, so `poll()` waits one `setTimeout(0)` inside `act` after `refetchQueries`; without it an assertion could run before the hook saw the new status.
- Browser check of `UninstallConfirmDialog` on the dev stack (read-only script; every non-GET API request refused): before the fix, the focused element on open was the page's `remove-server-button` behind the modal (nothing inside the dialog); after, `cancel-button`. Escape closed it in both (not pending).

### Completion Notes List

- **Task 1 (AC 1-5, 7-9):** the remove dialog's confirm is a `Button variant="destructive"` (no hand-written colours); Cancel stays `AlertDialogCancel` with `disabled={isRemoving}` and keeps the focus on open (unit test). `handleRemoveConfirm` returns early while removing and passes no `onError`; `handleRemoveCancel` does nothing while removing, which covers Cancel, Escape and `onOpenChange`. The dialog element is built once (`removeDialog`) and rendered both in the main return and beside `mod-table-empty`. `UninstallConfirmDialog` ignores a close request while `isPending`.
- **Task 1, backlog drawdown (maintainer note, own commit `cb38d1ea`):** `InstallConfirmDialog` and `InstallVersionDialog` ignore a close request (Escape, outside click, the X button) while their install request is pending; tests for pending and not pending. `InstallVersionDialog` still closes while the server installs after the request was accepted (test), since that is the progress view with a "Close" button. **`VersionChangeConfirmDialog` is not changed:** its request never runs while it is open (the first request has already ended with the 409 that opens it, and confirm closes it before the retry starts, through `useVersionChangeFlow.confirm`), so there is no pending state to guard. Making it wait for the retry like the remove dialog would be a behaviour change beyond the note; listed as a follow-up.
- **Task 2 (AC 6):** `isRemoving` is true only when the mutation is pending, a dialog is open and `variables === modToRemove.slug`; the success handler closes only that mod's dialog (`setModToRemove((current) => (current?.slug === slug ? null : current))`).
- **Task 3 (AC 10):** `useInstallMod` has `onError: () => {}` with the existing comment; its only caller, `InstallConfirmDialog`, shows "Installation failed".
- **Task 4 (AC 11, 12):** `useRestartServer`, `useInstallServer`, `useUninstallServer` and `useSetModUpdateWebhook` silence the default the same way, each with a doc-comment line. Callers re-checked with the grep in 4.4 on this branch: the list in "The five hooks" is complete and unchanged; every caller reports its error. `PendingRestartBanner` now shows "Failed to restart server" with the message. The rule is in `project-context.md` under "Frontend (TypeScript)" with the story's wording.
- **Task 5 (AC 13-16):** `useRefreshModDataOnGameVersionChange()` in `use-server-status.ts`, called once at the top of `Layout`. It remembers nothing until the status has data, remembers the first value (version or `null`) without invalidating, and invalidates `['mods']` once per change. The install and uninstall `onSuccess` handlers and every stale time are unchanged.
- **Task 6 (AC 17, 18):** two untagged, stubbed specs (5 tests). `UninstallConfirmDialog` focus on open (maintainer note): confirmed in the browser that nothing in the dialog had the focus, so its Cancel is now `AlertDialogCancel` (focused on open, still disabled while pending, its click asks for a close through the guarded `onOpenChange`), with a unit test; own commit `cc75e340`. This overrides the story's "Not changed" entries for the uninstall dialog's buttons and for the install dialogs, as the maintainer's notes asked.
- **Tests:** web unit 3,337 passed (0 skipped; `ModTable.test.tsx` 93, `UninstallConfirmDialog.test.tsx` 20); API 3,458 passed. The three tests listed under "Existing tests that change" were rewritten as planned (the two old remove dialog tests became the "waits for the removal" block; the Story 17.3 test now keeps the dialog open); no other existing test changed. `createAppLikeQueryClient` in `ModTable.test.tsx` moved to module scope for the new tests.
- **E2E:** the two new specs passed against the dev stack rebuilt from this branch (5 passed; 15 of 15 with `--repeat-each=3`) and in `just test-e2e-ci` (first pass 124 passed, second pass 27 passed). `GET /api/v1alpha1/mods` (slug, version, enabled of each mod) and `GET /api/v1alpha1/server/status` (state, version) on the dev stack returned the same before and after the E2E runs. No game server was started or stopped (checked before each `just docker restart`); no screenshots.
- **Gate:** `just check` passed (ruff, Pyright 0 errors 0 warnings, tsc, Prettier check, all tests, script tests). The diff adds no suppression and no `cast`/`as`; nothing under `dev/`.
- **API contract changes:** none.
- **Left for the maintainer:** 6.5 (manual check, headed run and real keyboard). 6.6's PR and bead links are not done here (the dev brief forbids push and PR).

### File List

- `web/src/components/ModTable.tsx` (modified)
- `web/src/components/ModTable.test.tsx` (modified)
- `web/src/components/UninstallConfirmDialog.tsx` (modified)
- `web/src/components/UninstallConfirmDialog.test.tsx` (modified)
- `web/src/components/InstallConfirmDialog.tsx` (modified)
- `web/src/components/InstallConfirmDialog.test.tsx` (modified)
- `web/src/components/InstallVersionDialog.tsx` (modified)
- `web/src/components/InstallVersionDialog.test.tsx` (modified)
- `web/src/components/PendingRestartBanner.tsx` (modified)
- `web/src/components/PendingRestartBanner.test.tsx` (modified)
- `web/src/components/layout/Layout.tsx` (modified)
- `web/src/components/layout/Layout.test.tsx` (modified)
- `web/src/hooks/use-mods.ts` (modified)
- `web/src/hooks/use-mods.test.tsx` (modified)
- `web/src/hooks/use-server-status.ts` (modified)
- `web/src/hooks/use-server-status.test.tsx` (modified)
- `web/src/hooks/use-api-settings.ts` (modified)
- `web/src/hooks/use-api-settings.test.tsx` (modified)
- `web/e2e/mod-remove-dialog.spec.ts` (new)
- `web/e2e/browse-version-refresh.spec.ts` (new)
- `web/e2e/README.md` (modified)
- `project-context.md` (modified)
- `_bmad-output/implementation-artifacts/21-4-remove-dialog-and-single-toast.md` (this story)

## Change Log

| Date | Change |
|---|---|
| 2026-11-17 | Story created and validated (ready-for-dev) |
| 2026-11-17 | Implemented Tasks 1-6 (with the install dialogs' guard and the uninstall dialog's focus fix from the maintainer's notes); status review |
