# Story 16.4: Formatted Description in the Mod Lookup Preview

Status: in-progress

<!-- Implements FR171. Bead: VSS-4ll (empty description; this file is the spec). Stacks on Story 16.3 (PR #150), itself on 16.2 (PR #149) and 16.1 (PR #148). No new dependencies: DOMPurify 3.4.17 is already used by the detail page. -->

## Story

As an **administrator**,
I want **the mod lookup preview to show the description as formatted text**,
so that **I can read it instead of raw HTML tags**.

## Acceptance Criteria

1. **Given** I look up a mod by slug or URL
   **When** the preview card shows its description
   **Then** the description is rendered from sanitized HTML (paragraphs, bold, italics, lists, links show as formatting, never as `<p>`/`<strong>` text), and it is kept to a short preview: the rendered element is clamped to 3 lines with CSS; the HTML string is never sliced
   *(Covers FR171; `VSS-4ll`)*

2. **Given** a description that contains `<script>` elements, event handler attributes (`onerror`, `onclick`, ...), `javascript:` URLs (including mixed case and inside SVG) or `<style>` elements
   **When** it is rendered in the lookup preview or on the mod detail page
   **Then** none of them reach the DOM, and the surrounding text is kept

3. **Given** the lookup preview and the mod detail page
   **When** they render a description
   **Then** both use one shared sanitizing module (`web/src/lib/mod-description.ts`) with one DOMPurify configuration, and every link with an `href` opens in a new tab with `rel="noopener noreferrer"` on both

4. **Given** a description with images, embedded videos (`<iframe>`, `<video>`), forms, SVG, tables or inline `style`/`class`/`id` attributes
   **When** it is shown in the lookup preview
   **Then** the preview keeps only text formatting (media, forms and SVG are dropped; table text is kept as text), uses the app's theme colors (muted text, links in the primary color, underlined) so it reads in light and dark themes, and shows no description block when nothing visible is left. The detail page keeps showing images as it does today

## Tasks / Subtasks

<!-- Each functional task includes its tests in the same commit. Commit per task: type(story-16.4/task-N): ... ; feat/fix only for user-visible changes, subject written for users. -->

- [x] Task 1: Shared mod description sanitizer + tests (AC: 2, 3, 4)
  - [x] 1.1: New `web/src/lib/mod-description.ts`. Create a private DOMPurify instance (`DOMPurify(window)`), so its hook never affects other `DOMPurify.sanitize` callers, with an `afterSanitizeAttributes` hook that sets `target="_blank"` and `rel="noopener noreferrer"` on every `<a>` that kept an `href` (DOMPurify drops `target` by default, verified with 3.4.17)
  - [x] 1.2: `sanitizeModDescription(html: string): string` for the detail page: DOMPurify defaults plus `FORBID_TAGS: ['style']` (DOMPurify keeps a `<style>` element that follows body content, which would restyle the whole app; verified). Images and inline styles stay, as today
  - [x] 1.3: `sanitizeModDescriptionPreview(html: string): string | null` for the lookup preview: same instance and hook, `ALLOWED_TAGS` limited to text formatting (`p`, `br`, `div`, `span`, `strong`, `b`, `em`, `i`, `u`, `s`, `code`, `a`, `ul`, `ol`, `li`, `h1`-`h6`, `blockquote`), `ALLOWED_ATTR: ['href', 'title']` (no `style`, `class`, `id`); returns `null` when the result has no visible text (the sanitized string is parsed with `DOMParser`, which is inert, and its `textContent` trimmed). The two configurations are constants in this module only
  - [x] 1.4: `web/src/lib/mod-description.test.ts`: both functions strip `<script>` (and its content), `onerror`/`onclick`/`onload`, `javascript:` in `href` (lower case, mixed case, leading whitespace, entity-encoded) and in SVG `xlink:href`, `<style>` elements at the start and after content; links get `target="_blank"` and `rel="noopener noreferrer"` (an author's `rel="noopener"` and `target="_self"` are replaced), anchors without `href` get neither; detail keeps `<img>` without `onerror`; preview drops `img`, `iframe`, `video`, `form`/`input`/`button`, `svg`, `style`/`class`/`id` attributes, keeps text of tables and unknown wrappers, returns `null` for an image-only description and for `''`; calling `DOMPurify.sanitize` directly after the helpers does not add `target` (hook isolation)

- [x] Task 2: Detail page uses the shared sanitizer + tests (AC: 2, 3)
  - [x] 2.1: `ModDetailPage.tsx`: replace the inline `DOMPurify.sanitize(mod.description)` and the `dompurify` import with `sanitizeModDescription`; markup and classes unchanged
  - [x] 2.2: `ModDetailPage.test.tsx` "description section": links open in a new tab with `rel="noopener noreferrer"`; a `<style>` element after content is removed; the existing script/`onerror` test keeps passing

- [x] Task 3: Lookup preview renders the formatted, clamped description + tests (AC: 1, 2, 3, 4)
  - [x] 3.1: `ModLookupInput.tsx`: compute `sanitizedDescription = modData.description ? sanitizeModDescriptionPreview(modData.description) : null`; render it only when non-null in a `div` with `data-testid="mod-preview-description"`, `dangerouslySetInnerHTML` (the detail page pattern, no lint suppression exists or is needed), classes `text-sm text-muted-foreground line-clamp-3 break-words` plus link styling `[&_a]:text-primary [&_a]:underline`
  - [x] 3.2: `ModLookupInput.test.tsx` ("Story 16.4" block): HTML description renders `<strong>`/`<a>` elements and no literal `<strong>` text; the element has `line-clamp-3` and its `innerHTML` holds the full sanitized text (no slicing); scripts, `onerror` and `javascript:` hrefs are absent; links have `target`/`rel`; `img`/`iframe` and `style` attributes are absent; image-only description renders no description element; plain-text descriptions still render (update the existing "displays mod description" test if its selector changes)

- [ ] Task 4: Browser verification against the Docker dev stack (AC: 1, 3, 4)
  - [ ] 4.1: `just docker restart` (rebuild from this branch), open http://localhost:8080 Mods page, look up `smithingplus` (styled `div` with a light inline background, links), `betterruins` (inline-styled layout, `iframe`), `playercorpse` (images inside links) and `carryon` (headings, lists): formatted text, 3 lines at most, no tags as text, no images or embeds, links underlined in the primary color with `target="_blank"` and `rel="noopener noreferrer"` in the DOM
  - [ ] 4.2: Same checks in light and dark themes; open one mod's detail page and check its description still shows images and its links open in a new tab. Browser console clean
  - [ ] 4.3: Screenshots kept in the session scratchpad, not committed (committed screenshots would need the server name, `span.font-semibold` in the header and `#ServerName`, and password masked). Record results in the Dev Agent Record

- [ ] Task 5: Quality gate and review hand-off (AC: all)
  - [ ] 5.1: `just check` passes
  - [ ] 5.2: Status review, `just sprint set 16-4-formatted-description-in-mod-lookup-preview review`, PR to `story/16-3-latest-supported-game-version-for-incompatible-mods` (stacks on #150, #149, #148), PR link on `VSS-4ll`

## Dev Notes

### Today's behavior (verified on `story/16-3-latest-supported-game-version-for-incompatible-mods` a9511f0)

- `web/src/components/ModLookupInput.tsx:174-179` renders `{modData.description}` as a React text child in a `<p className="text-sm text-muted-foreground line-clamp-2">`, so ModDB's HTML shows as literal tags.
- `web/src/features/mods/ModDetailPage.tsx:506-509` sanitizes the same field with bare `DOMPurify.sanitize(mod.description)` and renders it at `:704-709` with `dangerouslySetInnerHTML` in `div.prose.prose-sm.prose-invert`. The `prose` classes are no-ops: `@tailwindcss/typography` is not installed (not in `web/package.json`, no `@plugin` in `web/src/styles/index.css`). This is the codebase's only `dangerouslySetInnerHTML`; there is no lint rule against it (`just lint-web` is `tsc --noEmit`), so no suppression is involved.
- The field is ModDB's `mod.text` (`api/src/vintagestory_api/services/mods.py:614`), passed through unchanged. The test fixtures in `api/tests/fixtures/moddb/` do not carry `text`.

### Live ModDB descriptions (fetched 2026-11-13)

| Mod | Length | Tags | Notes |
|---|---|---|---|
| `smithingplus` | 18 KB | a, div, em, h2-h4, img, li, p, span, strong, ul | starts with a `div` whose inline style sets a light gradient background and `color: #222` |
| `carryon` | 16 KB | a, code, div, em, h3, h4, img, li, ol, p, pre, strong, ul | absolute links to mods.vintagestory.at |
| `playercorpse` | 4 KB | a, br, div, h3, hr, img, p, span, strong, u | links wrapping 48px images |
| `betterruins` | 30 KB | a, br, code, div, h2, iframe, img, li, p, span, strong, ul | whole layout in inline-styled `div`/`a` with light backgrounds |

Authors write `target="_blank" rel="noopener"` themselves; DOMPurify 3.4.17 defaults (probed in jsdom): `target` dropped, `rel` kept, `javascript:` href removed, iframe removed, `video`/`form`/`input`/`button` kept, `style`/`class`/`id` attributes kept, a leading `<style>` removed but one after body content kept.

### Decisions

- **One module, two named configurations.** `sanitizeModDescription` (detail) and `sanitizeModDescriptionPreview` (preview) share a private DOMPurify instance, its link hook and the forbidden-tag baseline; the configurations live only in `web/src/lib/mod-description.ts`. A private instance is needed because DOMPurify hooks are per instance and the default export is shared.
- **Links open in a new tab, everywhere.** Following a description link from the admin SPA in the same tab loses the page; mod authors already ask for `_blank`, which DOMPurify currently strips. `rel="noopener noreferrer"` replaces whatever the author wrote. This changes the detail page's link behavior (same tab today) so both surfaces match, as AC 3 requires.
- **Preview is text formatting only.** A 3-line preview has no room for images or embeds; images also load third-party content for every lookup keystroke result, and inline styles carry light backgrounds and fixed dark text (`#222`) that are unreadable in the dark theme, while `class` could collide with Tailwind utilities (`fixed`, `hidden`). An allowlist (rather than a forbid list) keeps anything new ModDB authors use out of the preview; DOMPurify keeps the text of removed wrappers and drops the content of `script`, `style`, `iframe`, `video`, `svg` (its `FORBID_CONTENTS` default).
- **Clamp the element, never the string.** `line-clamp-3` on the container; the full sanitized description stays in the DOM, so no tag is ever cut. 3 lines (today 2) because block elements (headings, list items) each take a line. Tailwind preflight resets heading sizes, margins and list markers, so the clamped text stays compact.
- **Detail page is otherwise unchanged.** It keeps images and inline styles (its look today); only `<style>` elements are removed (they escape the description and restyle the app) and links get `target`/`rel`. Inline-style readability in the dark theme and the dead `prose` classes on the detail page are not this story (see Out of scope).
- **No new dependencies.** `@types/dompurify` is a deprecated stub (DOMPurify ships its own types); removing it is not this story.

### Out of scope

- Detail page dark-theme readability of inline-styled descriptions, the no-op `prose` classes, forms in detail descriptions, browse cards (`ModCard` descriptions come from the browse API), any other Epic 16 story. Adjacent problems become beads.

### Testing Requirements

**CRITICAL:** Tests are written with each task and committed with it. `just test-web <file>` after each task; `just check` before review.

- Web tests run in jsdom (Vitest); DOMPurify works there. `line-clamp` cannot be measured in jsdom: assert the class and that `innerHTML` holds the full text; the visual clamp is checked in Task 4.
- `ModLookupInput.test.tsx` mocks `fetch` with snake_case lookup responses and uses fake timers with `shouldAdvanceTime` for the 300ms debounce; follow its existing pattern for the new block.

**UI Stories - Manual Browser Verification:** Docker stack (`just docker restart`, http://localhost:8080). The lookup is read-only; nothing is installed, so `./data` is untouched. Screenshots committed to this public repo must mask the server name (`span.font-semibold` in the header, `#ServerName`) and password; keep them in the scratchpad instead. Check the browser console. API key for scripts: `VS_API_KEY_ADMIN` in `.env` (Story 16.2 lesson).

### Security Requirements

- Every HTML string from ModDB goes through `web/src/lib/mod-description.ts` before `dangerouslySetInnerHTML`; nothing else renders description HTML.
- Tests prove scripts, event handlers, `javascript:` URLs and `<style>` elements are stripped (AC 2).

### Development Commands

- `just test-web src/lib/mod-description.test.ts`, `just test-web src/features/mods/ModDetailPage.test.tsx`, `just test-web src/components/ModLookupInput.test.tsx`, `just lint-web`, `just check`, `just docker restart`.

### Previous Story Intelligence

- **16.3:** changed `ModDetailPage` header (compatibility message, version); the description section was untouched. Browser verification used a scratchpad Playwright script with the API key from `.env`; screenshots stayed in the scratchpad.
- **16.2 / 16.1:** `just lint-web` is `tsc --noEmit`; StrictMode double-mounts.
- **10.6:** chose frontend DOMPurify over server-side sanitizing; `dompurify` and `@types/dompurify` added then.
- **5.6:** built `ModLookupInput` (preview card: name, author, description truncated, side, badge, Install).

### Git Intelligence

- Branch `story/16-4-formatted-description-in-mod-lookup-preview` from `origin/story/16-3-latest-supported-game-version-for-incompatible-mods` (a9511f0); PR base is that branch. Planned types: Task 1 `refactor` (helper not used yet), Task 2 `fix` (description links open in a new tab), Task 3 `fix` (preview shows raw HTML today), Task 4 `docs`, Task 5 `chore`.

### Latest Technical Information

- DOMPurify 3.4.17 (resolved in `web/bun.lock`, Story 16.0): `DOMPurify(window)` returns a new instance; `addHook('afterSanitizeAttributes', node => ...)` is the documented way to add `target`/`rel`; `RETURN_DOM: true` returns an element whose `innerHTML` is the sanitized markup. Types ship with the package.
- Tailwind v4 `line-clamp-3` and arbitrary variants `[&_a]:underline` are built in.

### Project Structure Notes

- New: `web/src/lib/mod-description.ts`, `web/src/lib/mod-description.test.ts` (kebab-case lib module with co-located test, like `mod-ids.ts`).
- Modified: `web/src/features/mods/ModDetailPage.tsx`, `web/src/features/mods/ModDetailPage.test.tsx`, `web/src/components/ModLookupInput.tsx`, `web/src/components/ModLookupInput.test.tsx`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 16.4: Formatted Description in the Mod Lookup Preview]
- [Source: _bmad-output/planning-artifacts/prd.md] FR171
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-13.md] (evidence, "must not be rendered unsanitized", no new dependencies)
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md] ModLookupInput (states, preview Card), Typography, Catppuccin tokens
- [Source: _bmad-output/implementation-artifacts/10-6-mod-detail-view.md#HTML Sanitization Strategy]
- [Source: _bmad-output/implementation-artifacts/5-6-mod-management-ui.md]
- Bead: `VSS-4ll`
- `project-context.md` - critical implementation rules and patterns

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5)

### Debug Log References

- Task 1: red run of `mod-description.test.ts` (module missing, collection error), then 30 passed. First cut used `RETURN_DOM: true`; its overload is typed `Node` (no `innerHTML`), so `tsc` failed; switched to sanitizing to a string and checking its text with an inert `DOMParser` document. `tsc` clean.
- Task 2: red run, the 2 new detail page tests failing (link without `target`/`rel`, `<style>` kept), then 73 passed; `tsc` clean.
- Task 3: red run, 5 of the 7 new preview tests failing (the two "no description" cases passed before the change because no element carried the new test ID), then 40 passed. Web 3,158 passed, 4 skipped (pre-existing `it.skip`s); `tsc` clean.
- Task 4 BLOCKED (product decision): `just docker restart` rebuilt the stack from bb4cfbf, but `/game-server/mods/installed` has no lookup input. `ModLookupInput` is not mounted anywhere in the app: VSS-195 (closed 2026-01-19, one day after VSS-4ll was filed) removed it from the Installed tab and moved discovery to the Browse tab; only its own tests render it. The change proposal's evidence (`ModLookupInput.tsx` renders the description as text) is true of the file but not of anything a user sees. Browse cards show ModDB's `summary`, which is plain text (1 of 9,561 live summaries matched a tag pattern, and that one is a command syntax `<name>`, not HTML). The only live surface rendering description HTML is the detail page (Task 2). Story paused at Task 4 pending a decision; see Completion Notes.

### Completion Notes List

- Task 1: `web/src/lib/mod-description.ts` exports `sanitizeModDescription` (DOMPurify defaults, `FORBID_TAGS: ['style']`) and `sanitizeModDescriptionPreview` (text-formatting allowlist, `href`/`title` only, `null` when no visible text). One private DOMPurify instance carries the `afterSanitizeAttributes` hook that sets `target="_blank"` and `rel="noopener noreferrer"` on links with an `href`; a test proves the shared default instance is untouched. Not used yet; Tasks 2 and 3 wire it in.
- Task 2: `ModDetailPage` calls `sanitizeModDescription` instead of `DOMPurify.sanitize`; markup and classes unchanged. Description links now open in a new tab (same tab before) and a `<style>` element in a description no longer reaches the page.
- Task 3: `ModLookupInput` renders `sanitizeModDescriptionPreview(modData.description)` with `dangerouslySetInnerHTML` in a `div` (`data-testid="mod-preview-description"`, `text-sm text-muted-foreground line-clamp-3 break-words [&_a]:text-primary [&_a]:underline`), and renders nothing when the helper returns `null`. The existing plain-text description test passes unchanged.
- Open question (blocks Task 4 and the PR): the lookup preview this story targets is dead code since VSS-195. Options: (a) keep Tasks 1-3 as hardening (shared sanitizer, detail-page links in a new tab, dead component fixed for any future reuse), drop Task 4's preview checks to a detail-page check, and reword Task 3's commit type (`fix` is a release note for a change no user can see); (b) delete `ModLookupInput` and its tests as dead code and keep only Tasks 1-2; (c) remount a lookup preview somewhere (reverses VSS-195; new scope). FR171 and AC 1 assume (c)'s surface exists.

### File List

- `web/src/lib/mod-description.ts` (new)
- `web/src/lib/mod-description.test.ts` (new)
- `web/src/features/mods/ModDetailPage.tsx`
- `web/src/features/mods/ModDetailPage.test.tsx`
- `web/src/components/ModLookupInput.tsx`
- `web/src/components/ModLookupInput.test.tsx`
- `_bmad-output/implementation-artifacts/16-4-formatted-description-in-mod-lookup-preview.md`

## Change Log

- 2026-11-13: Story 16.4 created (ready-for-dev).
