# Story 16.4: Shared Description Sanitizer and Safe Links

Status: review

<!-- Rescoped 2026-11-13 (maintainer decision): FR171 withdrawn because the mod lookup preview has not been mounted since VSS-195 (2026-01-19). Sprint key and filename keep the original "formatted-description-in-mod-lookup-preview" slug. Bead: VSS-4ll. Stacks on Story 16.3 (PR #150), itself on 16.2 (PR #149) and 16.1 (PR #148); Story 16.5 stacks on this branch. No new dependencies: DOMPurify 3.4.17 is already used by the detail page. -->

## Story

As an **administrator**,
I want **mod descriptions to be sanitized in one place, with their links opening safely in a new tab**,
so that **a mod author's HTML cannot run code, restyle the app or navigate me away from it**.

## Acceptance Criteria

1. **Given** a description that contains `<script>` elements, event handler attributes (`onerror`, `onclick`, ...), `javascript:` URLs (including mixed case, entity-encoded and inside SVG) or `<style>` elements
   **When** it is rendered on the mod detail page
   **Then** none of them reach the DOM, and the surrounding text, formatting and images are kept

2. **Given** a link with an `href` in a mod description
   **When** the detail page renders it
   **Then** it opens in a new tab with `rel="noopener noreferrer"`, replacing whatever `target`/`rel` the author wrote

3. **Given** the web UI
   **When** any code renders mod description HTML
   **Then** it goes through one shared module, `web/src/lib/mod-description.ts`, with one DOMPurify configuration on a private instance (the shared `DOMPurify` default instance is unchanged)

4. **Given** the unused `ModLookupInput` lookup preview (not mounted since VSS-195)
   **When** this story is done
   **Then** the component, its tests and the code only it used are removed, and every remaining test passes

## Tasks / Subtasks

<!-- Each functional task includes its tests in the same commit. Commit per task: type(story-16.4/task-N): ... ; feat/fix only for user-visible changes, subject written for users. -->

- [x] Task 1: Shared mod description sanitizer + tests (AC: 1, 2, 3)
  - [x] 1.1: New `web/src/lib/mod-description.ts`. A private DOMPurify instance (`DOMPurify(window)`), so its hook never affects other `DOMPurify.sanitize` callers, with an `afterSanitizeAttributes` hook that sets `target="_blank"` and `rel="noopener noreferrer"` on every `<a>` that kept an `href` (DOMPurify drops `target` by default, verified with 3.4.17)
  - [x] 1.2: `sanitizeModDescription(html: string): string`: DOMPurify defaults plus `FORBID_TAGS: ['style']` (DOMPurify keeps a `<style>` element that follows body content, which would restyle the whole app; verified). Images and inline styles stay, as today
  - [x] 1.3: (Superseded by Task 3) a text-only preview profile `sanitizeModDescriptionPreview`, added for the lookup preview and removed with it
  - [x] 1.4: `web/src/lib/mod-description.test.ts`: strips `<script>` (and its content), `onerror`/`onclick`/`onload`/`onmouseover`, `javascript:` in `href` (lower case, mixed case, leading whitespace, entity-encoded, tab-split) and in SVG `xlink:href`, `<style>` elements at the start and after content; links get `target="_blank"` and `rel="noopener noreferrer"` (an author's `rel="noopener"` and `target="_self"` are replaced), anchors without `href` get neither; keeps `<img>` without `onerror` and inline styles; the shared `DOMPurify` instance adds no `target` (hook isolation)

- [x] Task 2: Detail page uses the shared sanitizer + tests (AC: 1, 2, 3)
  - [x] 2.1: `ModDetailPage.tsx`: replace the inline `DOMPurify.sanitize(mod.description)` and the `dompurify` import with `sanitizeModDescription`; markup and classes unchanged
  - [x] 2.2: `ModDetailPage.test.tsx` "description section": links open in a new tab with `rel="noopener noreferrer"`; a `<style>` element after content is removed; the existing script/`onerror` test keeps passing

- [x] Task 3: Remove the unused lookup preview (AC: 3, 4)
  - [x] 3.1: (Done in bb4cfbf, then superseded) `ModLookupInput` rendered the sanitized, 3-line-clamped preview description; found unmounted during browser verification
  - [x] 3.2: Delete `web/src/components/ModLookupInput.tsx` and `ModLookupInput.test.tsx`, plus what only it used: `sanitizeModDescriptionPreview` and its configuration and tests, `useLookupMod` (`hooks/use-mods.ts`) and its tests and fixture, `extractSlug` (`lib/mod-utils.ts`) and its tests. Kept: `lookupMod` and `queryKeys.mods.lookup` (used by `useModsCompatibility`), `useDebounce` (BrowseTab), `isValidSlug`/`detectSlugOrUrl` (BrowseTab), `useInstallMod`, `CompatibilityBadge`. Fix the stale `ModsPage` doc comment

- [x] Task 4: Detail page verification via tests (AC: 1, 2, 3)
  - [x] 4.1: Run `just test-web src/lib/mod-description.test.ts` and `just test-web src/features/mods/ModDetailPage.test.tsx`: dangerous content stripped, links in a new tab with `rel="noopener noreferrer"`, images and text kept, shared instance untouched. The Docker browser check is skipped (maintainer instruction: the Docker stack is in use by Story 16.5)

- [x] Task 5: Quality gate and review hand-off (AC: all)
  - [x] 5.1: `just check` passes
  - [x] 5.2: Status review, `just sprint set 16-4-formatted-description-in-mod-lookup-preview review`, PR to `story/16-3-latest-supported-game-version-for-incompatible-mods` (stacks on #150, #149, #148), PR link and rescope on `VSS-4ll`

## Dev Notes

### Rescope decision (2026-11-13)

- The story was created for FR171 ("the mod lookup preview shows the description as formatted, sanitized HTML"). During Task 4's browser check, `/game-server/mods/installed` had no lookup input: `ModLookupInput` has not been mounted anywhere since VSS-195 (closed 2026-01-19, one day after VSS-4ll was filed), which moved mod discovery to the Browse tab. Only its own tests rendered it. The change proposal's evidence was true of the file, not of anything a user sees.
- Browse cards show ModDB's `summary`, which is plain text (1 of 9,561 live summaries matched a tag pattern, and that one is command syntax `<name>`). The detail page is the only live surface rendering description HTML.
- Maintainer chose to delete the dead component and keep the shared sanitizer and the detail-page link change. FR171 is marked withdrawn in `prd.md`; `epics.md` Story 16.4 is updated. The approved sprint-change-proposal is left as the historical record.
- **Release-notes side effect:** commit bb4cfbf (`fix(story-16.4/task-3): the mod lookup preview shows the description as formatted text instead of raw HTML`) was already pushed and history is not rewritten, so its `fix` subject will appear in release notes for a component that 995e222 then removed. Whoever cuts the release may want to drop that line from the notes by hand.

### Behavior before this story (verified on `story/16-3-latest-supported-game-version-for-incompatible-mods` a9511f0)

- `web/src/features/mods/ModDetailPage.tsx:506-509` sanitized the description with bare `DOMPurify.sanitize(mod.description)` and rendered it with `dangerouslySetInnerHTML` in `div.prose.prose-sm.prose-invert`. The `prose` classes are no-ops: `@tailwindcss/typography` is not installed. This is the codebase's only `dangerouslySetInnerHTML`; there is no lint rule against it (`just lint-web` is `tsc --noEmit`), so no suppression is involved.
- The field is ModDB's `mod.text` (`api/src/vintagestory_api/services/mods.py:614`), passed through unchanged.

### Live ModDB descriptions (fetched 2026-11-13)

| Mod | Length | Tags | Notes |
|---|---|---|---|
| `smithingplus` | 18 KB | a, div, em, h2-h4, img, li, p, span, strong, ul | starts with a `div` whose inline style sets a light gradient background and `color: #222` |
| `carryon` | 16 KB | a, code, div, em, h3, h4, img, li, ol, p, pre, strong, ul | absolute links to mods.vintagestory.at |
| `playercorpse` | 4 KB | a, br, div, h3, hr, img, p, span, strong, u | links wrapping 48px images |
| `betterruins` | 30 KB | a, br, code, div, h2, iframe, img, li, p, span, strong, ul | whole layout in inline-styled `div`/`a` with light backgrounds |

Authors write `target="_blank" rel="noopener"` themselves; DOMPurify 3.4.17 defaults (probed in jsdom): `target` dropped, `rel` kept, `javascript:` href removed, iframe removed, `video`/`form`/`input`/`button` kept, `style`/`class`/`id` attributes kept, a leading `<style>` removed but one after body content kept.

### Decisions

- **One module, one configuration, private instance.** DOMPurify hooks are per instance and the default export is shared, so the link hook lives on `DOMPurify(window)`.
- **Links open in a new tab.** Following a description link from the admin SPA in the same tab loses the page; mod authors already ask for `_blank`, which DOMPurify stripped. `rel="noopener noreferrer"` replaces whatever the author wrote. This changes the detail page's link behavior (same tab before).
- **`<style>` elements are removed.** They escape the description box and restyle the whole app. Images and inline styles stay, so the detail page looks as before.
- **Orphans removed with the component.** `useLookupMod` and `extractSlug` had no callers outside `ModLookupInput` and their own tests; leaving them would keep dead code alive. The API's `lookupMod` stays (the Installed list's compatibility lookups use it).

### Out of scope

- Detail page dark-theme readability of inline-styled descriptions, the no-op `prose` classes, forms in descriptions, browse cards, any other Epic 16 story.

### Testing Requirements

- Tests are committed with each task. Web tests run in jsdom (Vitest); DOMPurify works there.
- No browser check (Task 4 is test-based, per maintainer instruction).

### Security Requirements

- Every HTML string from ModDB goes through `web/src/lib/mod-description.ts` before `dangerouslySetInnerHTML`; nothing else renders description HTML.
- Tests prove scripts, event handlers, `javascript:` URLs and `<style>` elements are stripped (AC 1).

### Development Commands

- `just test-web src/lib/mod-description.test.ts`, `just test-web src/features/mods/ModDetailPage.test.tsx`, `just lint-web`, `just check`.

### Previous Story Intelligence

- **16.3:** changed the `ModDetailPage` header; the description section was untouched.
- **16.2 / 16.1:** `just lint-web` is `tsc --noEmit`; StrictMode double-mounts.
- **10.6:** chose frontend DOMPurify over server-side sanitizing.
- **5.6:** built `ModLookupInput`; VSS-195 later unmounted it.

### Git Intelligence

- Branch `story/16-4-formatted-description-in-mod-lookup-preview` from `origin/story/16-3-latest-supported-game-version-for-incompatible-mods` (a9511f0); PR base is that branch. Work after the rescope was done in a separate worktree because Story 16.5 uses the main checkout.

### Project Structure Notes

- New: `web/src/lib/mod-description.ts`, `web/src/lib/mod-description.test.ts`.
- Deleted: `web/src/components/ModLookupInput.tsx`, `web/src/components/ModLookupInput.test.tsx`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 16.4: Shared Description Sanitizer and Safe Links]
- [Source: _bmad-output/planning-artifacts/prd.md] FR171 (withdrawn)
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-13.md] (original scope, historical)
- [Source: _bmad-output/implementation-artifacts/10-6-mod-detail-view.md#HTML Sanitization Strategy]
- Beads: `VSS-4ll`, `VSS-195`
- `project-context.md` - critical implementation rules and patterns

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5)

### Debug Log References

- Task 1: red run of `mod-description.test.ts` (module missing, collection error), then 30 passed. First cut of the preview profile used `RETURN_DOM: true`; its overload is typed `Node` (no `innerHTML`), so `tsc` failed; switched to an inert `DOMParser` text check. `tsc` clean.
- Task 2: red run, the 2 new detail page tests failing (link without `target`/`rel`, `<style>` kept), then 73 passed; `tsc` clean.
- Task 3 (first version, bb4cfbf): red run, 5 of 7 new preview tests failing, then 40 passed. Browser check (`just docker restart` from bb4cfbf) found no lookup input in the app: `ModLookupInput` unmounted since VSS-195. Story paused; maintainer chose to remove the component.
- Task 3 (removal, 995e222): deleting `useLookupMod` left an unused `mockLookupResponse` fixture in `use-mods.test.tsx` (`tsc` TS6133); removed. Web 3,043 passed, 4 skipped (pre-existing `it.skip`s; down from 3,158 by the removed tests); `tsc` clean.
- Task 4: `mod-description.test.ts` 14 passed, `ModDetailPage.test.tsx` 73 passed.
- Task 5: `just check` passed in the worktree: ruff and `tsc` clean, pyright 0 errors (3 pre-existing warnings in API tests), API 2,108 passed, web 3,043 passed and 4 skipped (pre-existing `it.skip`s), script tests 190 passed. No suppressions added.

### Completion Notes List

- Task 1: `web/src/lib/mod-description.ts` exports `sanitizeModDescription` (DOMPurify defaults, `FORBID_TAGS: ['style']`) on a private DOMPurify instance whose `afterSanitizeAttributes` hook sets `target="_blank"` and `rel="noopener noreferrer"` on links with an `href`; a test proves the shared default instance is untouched.
- Task 2: `ModDetailPage` calls `sanitizeModDescription` instead of `DOMPurify.sanitize`; markup and classes unchanged. Description links now open in a new tab (same tab before) and a `<style>` element in a description no longer reaches the page.
- Task 3: removed `ModLookupInput` and its tests, the preview sanitizer profile, `useLookupMod` and `extractSlug` with their tests; fixed the `ModsPage` doc comment. bb4cfbf's `fix` subject remains in history (see Dev Notes, release-notes side effect).
- Task 4: detail-page behavior verified by tests; no browser check (Docker stack in use by Story 16.5).
- Task 5: status review; PR targets `story/16-3-latest-supported-game-version-for-incompatible-mods` (stacks on #150, #149, #148); Story 16.5 stacks on this branch.

### File List

- `web/src/lib/mod-description.ts` (new)
- `web/src/lib/mod-description.test.ts` (new)
- `web/src/features/mods/ModDetailPage.tsx`
- `web/src/features/mods/ModDetailPage.test.tsx`
- `web/src/components/ModLookupInput.tsx` (deleted)
- `web/src/components/ModLookupInput.test.tsx` (deleted)
- `web/src/features/mods/ModsPage.tsx`
- `web/src/hooks/use-mods.ts`
- `web/src/hooks/use-mods.test.tsx`
- `web/src/lib/mod-utils.ts`
- `web/src/lib/mod-utils.test.ts`
- `_bmad-output/implementation-artifacts/16-4-formatted-description-in-mod-lookup-preview.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/epics.md`

## Change Log

- 2026-11-13: Story 16.4 created (ready-for-dev) for FR171, the formatted description in the mod lookup preview.
- 2026-11-13: Tasks 1-3 implemented (shared sanitizer, detail-page links, preview rendering). Browser check found `ModLookupInput` unmounted since VSS-195 (2026-01-19); story paused.
- 2026-11-13: Rescoped by maintainer decision: dead lookup preview removed (995e222), FR171 withdrawn, title changed to "Shared Description Sanitizer and Safe Links" (sprint key and filename unchanged), Task 4 replaced by test-based detail-page verification.
- 2026-11-13: `just check` passed; status review.
