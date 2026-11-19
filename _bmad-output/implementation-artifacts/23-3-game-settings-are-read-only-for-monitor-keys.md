# Story 23.3: Game Settings Are Read-Only for Monitor Keys

Status: done

<!-- Implements FR313, Epic 23 ADR-6. Bead: VSS-7z3 (UI-084), closed by this story after merge. Branch story/23-3-game-settings-are-read-only-for-monitor-keys, stacked on story/23-2-file-browser-paths-are-lists-of-names at f2405f9a (23.2 in review); the PR targets main and merges after 23.2's. Web only: no API change, no new dependency. Line references verified at f2405f9a. -->

## Story

As an **operator with a Monitor key**,
I want **Game Settings to show me the values without letting me edit them**,
so that **I do not type a change that then fails with "Update failed"**.

## Acceptance Criteria

1. **Given** a Monitor key
   **When** I open Game Settings
   **Then** every field and switch is disabled, the note "Only an Admin key can change settings." is shown once at the top, Password keeps its status display (`SecretSettingStatus`), and no request is sent when I click or type
   *(FR313; ADR-6 decision 1)*

2. **Given** an Admin key
   **When** I open Game Settings
   **Then** the page is as before (fields enabled unless env-managed) and no note is shown
   *(FR313; ADR-6 decision 1)*

3. **Given** the role is loading, or `GET /auth/me` fails
   **When** I open Game Settings
   **Then** the fields are disabled; while it loads there is no note; on failure the note reads "Could not check this key's role; settings cannot be changed until it loads."
   *(FR313; ADR-6 decision 2)*

4. **Given** `useIsAdmin`
   **When** the file browser's note (Story 19.1) and `SettingsPage`'s tab hiding (Epic 22 ADR-12) use it
   **Then** their existing tests pass unchanged
   *(ADR-6 decision 3)*

5. **Given** the Monitor key is configured for E2E (the existing Monitor specs' precondition)
   **When** the E2E opens Game Settings with it
   **Then** the fields are disabled and the note is shown (skipped, as the other Monitor specs are, when the key is not configured)
   *(FR313)*

6. **(Quality gates.)** `just check` green with 0 skipped unit tests; no suppression, `cast`, skip or `.only` added; `git diff` of `api/` empty.

## Tasks / Subtasks

<!-- Red first. Subjects: type(story-23.3/task-N): ... One user-visible commit: Task 2 (fix(web)). -->

- [x] Task 1: `useIsAdmin`, and the two existing users moved to it + tests (AC: 4, 6)
  - [x] 1.1: Red first: `use-auth-me.test.tsx` rows for `useIsAdmin`: Admin `{ isAdmin: true, isKnown: true, isError: false }`; Monitor `{ false, true, false }`; loading `{ false, false, false }`; failed `{ false, false, true }`
  - [x] 1.2: `web/src/api/hooks/use-auth-me.ts`: `export function useIsAdmin(): { isAdmin: boolean; isKnown: boolean; isError: boolean }` over `useAuthMe` (`isKnown`: a role string was returned)
  - [x] 1.3: `FileManagerPanel.tsx` (`showAdminNote = isKnown && !isAdmin`, same as today's `role !== undefined && role !== 'admin'`) and `SettingsPage.tsx` (`isAdmin`) use it; their tests unchanged and green
  - [x] 1.4: Commit `refactor(story-23.3/task-1): read the key's role through one hook`

- [x] Task 2: Game Settings disabled unless the key is Admin + tests (AC: 1, 2, 3, 6)
  - [x] 2.1: Red first: `SettingField.test.tsx`: with `disabled`, the text input, number input and switch are disabled, no `onSave` on blur or toggle, and no env badge is shown; `GameConfigPanel.test.tsx`: the four AC rows (Admin, Monitor, loading, error), mocking `/auth/me` as the existing panel tests mock fetch
  - [x] 2.2: `SettingField.tsx`: new prop `disabled?: boolean` (doc: "Read-only for this key, e.g. a Monitor key (Story 23.3); unlike envManaged, no badge"); `useSettingField({ disabled: envManaged || disabled })`; `isDisabled = envManaged || disabled || field.isPending`
  - [x] 2.3: `GameConfigPanel.tsx`: `const { isAdmin, isKnown, isError } = useIsAdmin()`; pass `disabled={!isAdmin}` to each `SettingField`; render the note above the first group when `isKnown && !isAdmin` ("Only an Admin key can change settings.") or `isError` (the failure text), as `<p data-testid="game-config-read-only-note" role="note" className="text-sm text-muted-foreground">`, inside the `PAGE_CONTENT_WIDTH` container
  - [x] 2.4: `just test-web`; `just typecheck-web`; `just format-web`, `just lint-web`
  - [x] 2.5: Commit `fix(story-23.3/task-2): show game settings read-only to Monitor keys`

- [x] Task 3: E2E with the Monitor key (AC: 5)
  - [x] 3.1: A spec next to the existing Monitor specs (`web/e2e/file-browser-monitor-note.spec.ts` is the model: how it loads the Monitor key and skips without it), visiting the Game Settings page, asserting `game-config-read-only-note` and that the `ServerName` input is disabled. Read-only: it never saves a setting
  - [x] 3.2: `just typecheck-web` (covers `e2e/`); run the spec only if the dev stack is up and the Monitor key is configured; otherwise record that it was not run locally (CI runs the untagged set)
  - [x] 3.3: Commit `test(story-23.3/task-3): check Game Settings are read-only for a Monitor key`

- [x] Task 4: Validate and move the story to review (AC: all)
  - [x] 4.1: `just check` green; `git diff f2405f9a -- api` empty; no suppression added
  - [x] 4.2: `just changelog` lists exactly one entry from this story (Task 2)
  - [x] 4.3: Status `review`; `just sprint set 23-3-game-settings-are-read-only-for-monitor-keys review`; Dev Agent Record and File List
  - [x] 4.4: Commit `chore(story-23.3/task-4): validate and move story 23.3 to review`

## Dev Notes

### The code today (verified at f2405f9a)

- `web/src/features/game-server/GameConfigPanel.tsx`: renders each setting through `SettingField` (or `SecretSettingStatus` when the API withheld a secret: `setting.configured !== undefined`); `handleSave` toasts "Update failed" on error. No role is read.
- `web/src/components/SettingField.tsx`: `envManaged` disables the input/switch and shows an env badge; `useSettingField({ disabled: envManaged })` (`:132`) refuses to save when disabled (`use-setting-field.ts:278`, `:326`); `isDisabled = envManaged || field.isPending` (`:138`) feeds every control.
- `web/src/api/hooks/use-auth-me.ts`: `useAuthMe()` (staleTime Infinity). Users: `FileManagerPanel.tsx` (`role !== undefined && role !== 'admin'` note), `SettingsPage.tsx` (`auth?.data?.role === 'admin'` hides two tabs).
- The API refuses the save for Monitor anyway (`RequireAdmin` on `POST /config/game/settings/{key}`); this story only stops the useless edit.

### Testing rules

- Web unit tests mock `fetch` as the panel tests already do. The E2E is read-only and runs against whichever stack `just test-e2e-web` targets; it must not save anything.

### References

- `epics.md` "Story 23.3"; `architecture/epic-23-config-file-editing.md` ADR-6
- Story 17.5 (`17-5-monitor-keys-cannot-read-the-server-password.md`) for `SecretSettingStatus`; Story 19.1 for the file browser note; Epic 22 ADR-12 for the hidden tabs

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5), as the epic's controller.

### Debug Log References

- `just check` (2026-11-19, with Stories 23.1's review fixes and 23.2 merged in): API 3866 passed, web 3757 passed (139 files), 0 skipped; Pyright 0/0; lints green.
- `just test-e2e-ci e2e/game-settings-read-only.spec.ts e2e/monitor-password-redaction.spec.ts e2e/file-browser-monitor-note.spec.ts e2e/file-browser-navigation.spec.ts`: 18 passed (the throwaway container has a Monitor key, so the real-key test ran); API E2E 4 passed.

### Completion Notes List

- 2026-11-19 (create-story): created from Epic 23's Story 23.3 and ADR-6.
- 2026-11-19 (dev-story): Tasks 1 to 4 done.
- **What changed.** `useIsAdmin` in `use-auth-me.ts` (`isKnown` is "a role string was returned"); `FileManagerPanel` and `SettingsPage` use it, unchanged in behaviour. `SettingField`: `disabled` prop (feeds `useSettingField`'s `disabled` and the controls; no badge). `GameConfigPanel`: `disabled={!isAdmin}` on every field; one `role="note"` paragraph (`game-config-read-only-note`) at the top for a known non-Admin role or a failed role read.
- **Tests.** 4 `useIsAdmin` rows; 4 `SettingField` disabled rows; 4 `GameConfigPanel` role rows. The existing panel tests now start with the Admin role in the query cache (`createTestQueryClient('admin')`), because their fetch mock answers every URL, `/auth/me` included, with the game config, which would leave the role unknown and every field disabled. New E2E spec `e2e/game-settings-read-only.spec.ts` (3 tests).
- `git diff f2405f9a -- api` is only Story 23.1's merged review docstring fix. `just changelog`: one entry from this story, 04e58ba (Task 2).

### File List

- `web/src/api/hooks/use-auth-me.ts`, `web/src/api/hooks/use-auth-me.test.tsx` (modified)
- `web/src/components/SettingField.tsx`, `web/src/components/SettingField.test.tsx` (modified)
- `web/src/features/game-server/GameConfigPanel.tsx`, `web/src/features/game-server/GameConfigPanel.test.tsx` (modified)
- `web/src/features/settings/FileManagerPanel.tsx`, `web/src/features/settings/SettingsPage.tsx` (modified: `useIsAdmin`)
- `web/e2e/game-settings-read-only.spec.ts` (new)
- `_bmad-output/implementation-artifacts/23-3-game-settings-are-read-only-for-monitor-keys.md` (this file)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (through `just sprint set` only)

## Review

Reviewer: GLM-5.3-Flash via opencode. Verdict: approve. 0 HIGH, 0 MEDIUM, three LOW:

1. **LOW: `isKnown` (`typeof role === 'string'`) differs from the old check (`role !== undefined`) for a non-string role.** Only reachable if `/auth/me` broke its schema (`role: string`). Accepted without a change: a role that is not a string is not a known role.
2. **LOW: the E2E's "no POST" check is passive** (the stubbed Monitor test never tries to edit). Accepted: the disabled-control assertions carry it, and the unit panel test types and blurs with 0 POSTs.
3. **LOW: the read-only note was not linked to the disabled controls.** Fixed: `SettingField` takes `disabledReasonId`, added to the control's `aria-describedby` while disabled; Game Settings passes the note's id. Two `SettingField` rows and one panel assertion.

Observation (no change): `ScheduledJobsPanel` still reads `useAuthMe` directly, as ADR-6 decision 3 does not list it; it also needs the query's loading state, which `useIsAdmin` does not expose.

## Change Log

- 2026-11-19: Story 23.3 created (ready-for-dev).
- 2026-11-19: Implemented (dev-story): Tasks 1 to 4; status review.
- 2026-11-19: Code review (GLM-5.3-Flash via opencode): approve; 0 HIGH, 0 MEDIUM, three LOW (one fixed: the note is named in the disabled fields' aria-describedby; two accepted) (see "Review"). Status done.
