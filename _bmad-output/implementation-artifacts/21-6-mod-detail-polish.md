# Story 21.6: Mod Detail Page Polish

Status: ready-for-dev

<!-- Implements FR278, FR279, FR280; Epic 21 ADR-10 and ADR-11. Beads: VSS-woae (UI-094), VSS-pzj8 (UI-092), VSS-4vbj (UI-093). Stories run in order 21.1 to 21.8, each stacked on the previous; this one comes after 21.5 (which changes the shared dialog close button the screenshot dialog uses). Line references were verified at 966204f (epic-21-planning), BEFORE Story 21.1's Prettier reformat and Story 21.5's VersionTable changes: they will have moved. Re-find every location by its content at implementation time. Web only; no API change; no new dependency. -->

## Story

As a **user reading about a mod**,
I want **the page to fit my phone, the description to look like a document, and links to say where they open**,
so that **I can read and install from a phone, and a screen reader tells me before a link leaves the app**.

## Acceptance Criteria

1. **Given** the mod detail page of a mod with a homepage, a source URL and a trailer
   **When** a screen reader reads the ModDB Page, Homepage, Source and trailer links
   **Then** their accessible names are exactly `ModDB Page (opens in a new tab)`, `Homepage (opens in a new tab)`, `Source (opens in a new tab)` and `Watch trailer (opens in a new tab)`, and each shows a visible external-link mark (ModDB Page and Watch trailer keep their leading icon; Homepage and Source gain a trailing one)
   *(Covers FR278; `VSS-woae`; ADR-10 decisions 1 and 3)*

2. **Given** the other links in the web UI that open a new tab: the mod name link in the installed mods table and cards, the ModDB link on browse cards, the changelog links on the Version page (table and cards), and the GitHub link in the sidebar
   **When** a screen reader reads them
   **Then** each name ends with exactly `(opens in a new tab)`, the text of `OPENS_IN_NEW_TAB` (the GitHub link's name is `GitHub (opens in a new tab)`), and no source file under `web/src` still contains the old wording `(opens in new tab)`
   *(Covers FR278; ADR-10 decisions 1 and 2)*

3. **Given** a mod description that contains an SVG link (with `href` or only `xlink:href`)
   **When** the description is shown
   **Then** the link has `target="_blank"` and `rel="noopener noreferrer"`, and its first child is one SVG `<title>` whose text is the link's text (or the author's own title) followed by ` (opens in a new tab)`; in Chromium the link is exposed with the role `link` and that accessible name; sanitizing the result again leaves exactly one title with the same text; and a title the mod author wrote, including one that already ends with the note, still ends with exactly one note
   *(Covers FR278; `VSS-woae`; ADR-10 decisions 4 to 6)*

4. **Given** the mod detail page at 320, 390 and 430px, in the light and the dark theme
   **When** I open a mod with a long name, four tags, homepage, source and trailer links and an install card
   **Then** the page does not scroll sideways (`document.documentElement.scrollWidth` equals the viewport width), the install card is below the logo and info at the full content width, the breadcrumb and every header control are inside the viewport, and the version select and the install button are at least 44px tall
   *(Covers FR279; `VSS-pzj8`; ADR-11 decisions 1 and 2)*

5. **Given** the mod detail page at 768px and wider
   **When** I open the same mod
   **Then** the logo, the info column and the install card are in one row as today (the install card's top equals the logo's top and it is right of the info column), and the page does not scroll sideways
   *(Covers FR279; ADR-11 decision 1; see "ADR against the code")*

6. **Given** a description with headings `h1` to `h6`, paragraphs, a bulleted and a numbered list (one nested), a link, a quote, inline code, a code block, a horizontal rule and a table
   **When** it is shown in the light and in the dark theme
   **Then** every heading is larger than body text and at least semi-bold, and `h1` is smaller than the page's own title; lists show their markers and are indented; the link is underlined and in the theme's primary colour; the quote has a left border in the theme's border colour; inline code, the code block and the table cells have a background or border from the theme; and those colours differ between the two themes because they come from the theme tokens
   *(Covers FR280; `VSS-4vbj`; ADR-11 decision 3)*

7. **Given** a description with a wide table, a wide image, a long code line and a long URL
   **When** it is shown at 320px
   **Then** the table and the code block scroll inside themselves, the image is no wider than the card, the URL wraps, and the page does not scroll sideways
   *(Covers FR279, FR280; ADR-11 decision 4)*

8. **Given** `web/package.json` and the description container
   **When** the story is done
   **Then** no dependency was added, the container has the class `mod-description`, and it has no `prose`, `prose-sm` or `prose-invert` class
   *(Covers FR280; ADR-11 decisions 5 and 6)*

9. **Given** a description whose author set inline styles (for example `<p style="color: #c33">`)
   **When** it is shown
   **Then** the author's styles still apply over the defaults, and the Content-Security-Policy behaviour of Story 19.3 is unchanged (inline style kept, `https:` and `data:image/` images shown, any other image replaced by the "Image not shown" note in its muted style)
   *(Covers FR280; ADR-11 decision 7)*

10. **Given** every existing test
    **When** the suites run
    **Then** they pass, apart from the changes listed in Dev Notes "Existing tests that change"; no unit test is skipped; no E2E test needs the live mod database or a game server

11. **Given** the install card on the mod detail page (installing or installed)
    **When** a screen reader reaches the version select
    **Then** its accessible name is `Version`, from the visible label linked with `htmlFor`/`id`, not the selected value
    *(Backlog drawdown, maintainer rule; added to the story at implementation)*

## Tasks / Subtasks

<!-- Each functional task includes its tests in the same commit, red first. Commit per task: type(story-21.6/task-N): ...; fix only for what a user would notice, subject written for users (Dev Notes "Commits and release notes"). Run Prettier (Story 21.1's pinned version and config) on every web file you change; never on the whole tree. -->

- [ ] Task 1: Every new-tab link says so, SVG links in descriptions included + tests (AC: 1, 2, 3, 10) (`VSS-woae`)
  - [ ] 1.1: New `web/src/lib/new-tab.ts` exporting `OPENS_IN_NEW_TAB = '(opens in a new tab)'` with the doc comment now at `mod-description.ts:25-28`. `mod-description.ts` imports it and re-exports it (`export { OPENS_IN_NEW_TAB } from './new-tab'` or import + `export`), so `ModDetailPage.tsx:86` and the existing tests keep working. Reason: the sidebar is in the main bundle, and importing `mod-description.ts` there would pull DOMPurify into it and run `DOMPurify(window)` (`:43`) at app start (Dev Notes "Links")
  - [ ] 1.2: New `web/src/components/NewTabLink.tsx`: props `Omit<ComponentProps<'a'>, 'target' | 'rel' | 'aria-label'>`; renders `<a {...props} target="_blank" rel="noopener noreferrer">{children}{' '}<span className="sr-only">{OPENS_IN_NEW_TAB}</span></a>` (the trailer link's shape, `ModDetailPage.tsx:737-738`; `aria-label` is left out of the props because it would replace the note). Short doc comment citing Story 21.6 / ADR-10
  - [ ] 1.3: `ModDetailPage.tsx:693-740`: ModDB Page, Homepage, Source and Watch trailer use `NewTabLink` (keep their `className` and `data-testid`; drop the trailer link's own span and `{' '}`). Icons get `aria-hidden="true"` explicitly. Homepage and Source get a trailing `<ExternalLink className="h-3 w-3" aria-hidden="true" data-testid="mod-detail-homepage-new-tab-mark" />` (resp. `...-source-new-tab-mark`) after their text. Add a Story 21.6 paragraph to the file comment (`:1-44`): new-tab links, the stacked header, the description styles
  - [ ] 1.4: `InstalledModParts.tsx:41-50` (`ModNameLink`): `NewTabLink`; the `ExternalLink` icon gets `aria-hidden="true"`
  - [ ] 1.5: `layout/Sidebar.tsx:208-216`: `NewTabLink` with the `aria-label="GitHub"` replaced by `<span className="sr-only">GitHub</span>` after the icon, so the name is `GitHub (opens in a new tab)` (an `aria-label` would hide the note; Dev Notes "Links")
  - [ ] 1.6: `VersionCard.tsx:80`, `VersionTable.tsx:154`, `ModCard.tsx:187`: keep the `aria-label` (ADR-10 decision 2) but build its end from the constant: `` `View changelog for version ${version} ${OPENS_IN_NEW_TAB}` ``, `` `Open ${mod.name} on ModDB ${OPENS_IN_NEW_TAB}` ``, importing from `@/lib/new-tab`. Their icons get `aria-hidden="true"`
  - [ ] 1.7: `mod-description.ts` hook (`:47-82`), SVG branch after the HTML branch (`:71-80`), exact rules in Dev Notes "SVG links": copy a sanitized `xlink:href` to `href` when `href` is missing; build the title text; remove every direct `title` child; insert one `title` (created with `createElementNS(SVG_NAMESPACE, 'title')` and `textContent`) as the first child. Update the module comment (`:7-11`): SVG links get a `<title>` note instead of no note
  - [ ] 1.8: Unit tests (Dev Notes "Unit tests", Task 1 rows) and the changes in "Existing tests that change", red first
  - [ ] 1.9: Browser confirmation of ADR-10 decision 5, recorded in the Dev Agent Record: in Chromium, the accessibility snapshot (`locator.ariaSnapshot()` or the Playwright MCP snapshot) of a description with an `href` SVG link and an `xlink:href`-only SVG link shows both as `link "<text> (opens in a new tab)"`. The `aria-label` fallback is not needed if this holds; if it does not, use the fallback (ADR-10 decision 5) and record which was used. Task 5's E2E keeps this check
  - [ ] 1.10: Commit `fix(story-21.6/task-1): say which links open in a new tab`
  - [ ] 1.11: Backlog drawdown: `web/src/components/ModCard.test.tsx`'s `createQueryResultMock` ends in an `as ReturnType<...>` cast; replace it with typed union-member fakes, as Story 21.5 did for `useInstallStatus` in `InstallVersionDialog.test.tsx` (a047feee). Own commit `test(story-21.6/task-1): type the query result fakes in the mod card tests`

- [ ] Task 2: The mod detail header stacks on phones and the page fits from 320px + tests (AC: 4, 5, 10) (`VSS-pzj8`)
  - [ ] 2.1: Before changing anything, measure the page on the dev stack (Task 5's stub) at 320, 390, 430 and 768px and record `scrollWidth` and the install card's left/right in the Dev Agent Record (drafting numbers in Dev Notes "Header")
  - [ ] 2.2: Header (`ModDetailPage.tsx:612-767`) as in Dev Notes "Header": outer `flex flex-col gap-4 md:flex-row md:gap-6`; logo and info in a new wrapping group (`data-testid="mod-detail-summary"`); info `min-w-0 grow basis-48`; title row, stats row and tags wrap; install card `w-full md:w-64 md:shrink-0` in both sections (`:229`, `:404`)
  - [ ] 2.3: Install and version controls: the `SelectTrigger`s (`:238`, `:423`) get `w-full max-lg:min-h-11`; the buttons (`:258-266`, `:362`, `:369-381`, `:385-398`) get `max-lg:min-h-11` (the pattern of `InstalledModsSortControl.tsx:57` and `InstalledTab.tsx:98`; `min-h` is needed because the trigger's `data-[size=default]:h-9` outranks a plain `h-*`)
  - [ ] 2.4: Breadcrumb row (`:579-609`): the row and the `nav` wrap (`flex-wrap`, `gap-2`, `min-w-0`); the name span (`:605`) gets `min-w-0 break-words`. Metadata slug (`:836`): `break-all`
  - [ ] 2.5: Skeleton (`:112-147`): the header part follows the same layout (`data-testid="mod-detail-loading-header"`, same outer classes, the lines `w-full max-w-64` etc.), so nothing in it is wider than 288px below `md`
  - [ ] 2.6: Unit tests (Dev Notes "Unit tests", Task 2 rows), red first
  - [ ] 2.6a: Backlog drawdown: the `Back to Browse` button (`size="sm"`, 32px) gets `max-lg:min-h-11` like the other controls, with a class assertion
  - [ ] 2.7: Commit `fix(story-21.6/task-2): fit the mod detail page on phone screens`

- [ ] Task 3: Descriptions are typeset by `.mod-description` rules + tests (AC: 6, 7, 8, 9, 10) (`VSS-4vbj`)
  - [ ] 3.1: `web/src/styles/index.css`, in `@layer components` next to the two `.mod-description` rules (`:246-264`): the rules in Dev Notes "Description styles", every selector wrapped in `:where()` after `.mod-description` so its specificity stays (0,1,0), every colour a theme token (`var(--primary)`, `var(--border)`, `var(--muted)`, `var(--muted-foreground)`), and the wide-content rules. Keep the 18.1 icon rule and the 19.3 image note rule unchanged
  - [ ] 3.2: `ModDetailPage.tsx:784`: the container's class is `mod-description` only (remove `prose prose-sm prose-invert max-w-none`)
  - [ ] 3.3: Unit tests (Dev Notes "Unit tests", Task 3 rows), red first; the computed styles are checked in Task 5's E2E (jsdom does not load the stylesheet)
  - [ ] 3.4: Commit `fix(story-21.6/task-3): show headings, lists and links in mod descriptions`

- [ ] Task 4: The install card's "Version" label names its select + tests (AC: 11) (backlog drawdown, maintainer rule)
  - [ ] 4.1: `ModDetailPage.tsx` install card (`InstallSection`, `InstalledVersionSection`): the "Version" `<label>` gets `htmlFor` and the `SelectTrigger` the matching `id` (one id per section, from `useId`), so the select's accessible name is "Version" and no longer its value
  - [ ] 4.2: Unit tests, red first: `getByRole('combobox', { name: 'Version' })` in both sections
  - [ ] 4.3: Commit `fix(story-21.6/task-4): name the version select on the mod detail page for screen readers`

- [ ] Task 5: E2E on a stubbed mod detail answer against the Docker dev stack + tests (AC: 1, 3, 4, 5, 6, 7, 9)
  - [ ] 5.1: New untagged `web/e2e/mod-detail-layout.spec.ts` as in Dev Notes "E2E"; type-checked by `web/e2e/tsconfig.json` (`just typecheck-web`)
  - [ ] 5.2: Rebuild the stack from this branch (`just docker restart`), export `VS_API_KEY_ADMIN`, run `cd web && bunx playwright test e2e/mod-detail-layout.spec.ts`, and re-run `e2e/mod-detail-media.spec.ts`, `e2e/content-security-policy.spec.ts` and `e2e/layout-widths.spec.ts` (the installed mod name links' heights). Record the before (Task 2.1) and after widths in the Dev Agent Record. Do not start or stop the game server; no screenshots
  - [ ] 5.3: `web/e2e/README.md`: update the test counts (`:10` "119", `:50` "Of the 150 tests, CI runs 146: 119 untagged") from `bunx playwright test --list` after this spec is added (Stories 21.5 and 21.7 change them too; count, do not add)
  - [ ] 5.4: Commit `test(story-21.6/task-5): check the mod detail page on phones, its links, its version label and its description styles`

- [ ] Task 6: Quality gate and review hand-off (AC: all)
  - [ ] 6.1: `just check` passes (Story 21.1's format check included); the diff adds no lint or type suppression, no `as` cast and no dependency (`git diff main -- web/package.json web/bun.lock` empty); 0 skipped unit tests beyond the 4 known (`VSS-hnl`); `git status --short` shows nothing under `dev/`
  - [ ] 6.2: Manual check on the Docker stack (needs the maintainer's confirmation before it is ticked, `project-context.md:160-161`): open a real mod with a rich description (for example one with headings and lists) at 390px and at desktop width in both themes; check the description reads well and the header looks right; with VoiceOver or the browser's accessibility tree, check the four header links and one description link. Do not install or change anything; no screenshots
  - [ ] 6.3: Story status `review`, `just sprint set 21-6-mod-detail-polish review`, PR (base: Story 21.5's branch while its PR is open, otherwise `main`), PR link on `VSS-woae`, `VSS-pzj8` and `VSS-4vbj`. Commit `chore(story-21.6/task-6): validate and move story 21.6 to review`

## Dev Notes

### What is wrong today (verified at 966204f)

- **New-tab links (`VSS-woae`).** Nine links in `web/src` open a new tab (`rg '_blank' web/src`): four say so (the trailer link, `ModDetailPage.tsx:729-739`, with a hidden `OPENS_IN_NEW_TAB` span; and three `aria-label`s saying "(opens in new tab)", without "a": `VersionCard.tsx:80`, `VersionTable.tsx:154`, `ModCard.tsx:187`); five say nothing: ModDB Page, Homepage, Source (`ModDetailPage.tsx:693-726`), `InstalledModParts.tsx:41-50` and `layout/Sidebar.tsx:208-216`. Description links come from the sanitizer hook (`mod-description.ts:61-81`): HTML links get the hidden note and, by CSS, an icon (`styles/index.css:248-260`); SVG links get `target`/`rel` only.
- **Header width (`VSS-pzj8`).** One `flex gap-6` row (`ModDetailPage.tsx:612`) of a 128px logo (`:614-630`), a `flex-1` info column (`:633`) whose stats row (`:661-677`, `flex`, no wrap) is about 350px wide, and a `w-64` install card (`:229`, `:404`) that shrinks but does not wrap. The breadcrumb row (`:579-609`) does not wrap either.
- **Description (`VSS-4vbj`).** The container (`:784`) has `mod-description prose prose-sm prose-invert max-w-none`; `@tailwindcss/typography` is not a dependency, so `prose*` do nothing, and Tailwind's preflight removes heading sizes, list markers and link styles. Measured on the dev stack: `h2` 16px/400 like `p`, `ul` `list-style-type: none`, link `text-decoration-line: none`.

### Commits and release notes

Three release notes, exactly the proposal's subjects (`sprint-change-proposal-2026-11-17-epic-21.md:101`; ADR-10 and ADR-11 "Consequences"): Task 1 `fix(...): say which links open in a new tab`, Task 2 `fix(...): fit the mod detail page on phone screens`, Task 3 `fix(...): show headings, lists and links in mod descriptions`. The epic lists the component and the SVG note as two tasks (`epics.md` Story 21.6 "Tasks" 1 and 2); this story makes them one task because both are `VSS-woae`'s one user-visible fix and two `fix` commits would print the release note twice (`cliff.toml:40-48` keeps every `fix` commit). Task 4 (added by the backlog drawdown) is `fix` with its own release note, Task 5 is `test`, Task 6 `chore`; the `ModCard.test.tsx` cleanup in Task 1 is its own `test` commit.

### Links (Task 1)

- **Why a new module for the constant.** `mod-description.ts` creates a DOMPurify instance at import (`:43`). `ModCard`, `VersionCard`, `VersionTable` and the mods pages are in lazily loaded chunks (`App.tsx:18-21`), but `Sidebar` is in every page; importing the constant from `mod-description.ts` there would move DOMPurify into the main bundle. `new-tab.ts` holds only the string.
- **Why the GitHub link loses its `aria-label`.** An `aria-label` replaces the content as the accessible name, so a hidden span inside an `aria-label` link is never read. The icon-only links on browse cards and the Version page keep their `aria-label` (ADR-10 decision 2) and get the words from the constant instead; the GitHub link is moved to `NewTabLink` (ADR-10 decision 1 names it) with visually hidden text.
- **Spacing.** `{children}{' '}<span className="sr-only">...` is the shape Story 18.1 verified (its Completion Notes, deviation 1): the separating space is a text node, an `inline-flex` link drops it visually, and the name is `Watch trailer (opens in a new tab)` in jsdom and Chromium. The `sr-only` span is absolutely positioned, so the installed mod name links keep their height (`e2e/layout-widths.spec.ts:353-382` compares those heights; re-run it).
- **Icons.** lucide-react 1.72 already renders `aria-hidden="true"` when no accessibility prop is passed (`node_modules/lucide-react/dist/esm/shared/src/build/buildLucideIconNode.mjs:47-49`); pass it explicitly anyway, as the trailer link does, so the intent is in the code. `GithubIcon` (`Sidebar.tsx:41-52`) already sets it.
- Prototype (discarded): `NewTabLink` on the five links and the three reworded labels; `bunx vitest run src/components src/features/mods src/lib`: 1977 passed, 2 failed, exactly the two `aria-label` assertions listed in "Existing tests that change".

### SVG links (Task 1.7)

Rules for the hook's SVG branch (`node.namespaceURI === 'http://www.w3.org/2000/svg'`; add `const SVG_NAMESPACE` next to `HTML_NAMESPACE`, `:45`):

1. If the link has `xlink:href` and no `href`, set `href` to the `xlink:href` value. The hook runs in `afterSanitizeAttributes`, so the value has already passed DOMPurify's URI check; a `javascript:` `xlink:href` is removed before the hook and the node is then not a link (`isLink`, `:62-64`), as the existing "javascript: URLs inside SVG" case (`mod-description.test.ts:80-85`) shows. Reason: Chromium does not expose an `xlink:href`-only SVG `<a>` as a link at all (prototype below), so no title or label on it reaches a screen reader.
2. Base text: the text of the first direct `title` child, trimmed, with any trailing `OPENS_IN_NEW_TAB` (and the space before it) removed, repeatedly; if there is no title or it is then empty, the link's visible text: the `textContent` of its `text` descendants, joined with a space and with whitespace collapsed. Never read `innerHTML`; the title is built with `textContent` only.
3. Remove every direct `title` child of the link.
4. Insert one new `title` as the link's first child with the text `` `${base} ${OPENS_IN_NEW_TAB}` ``, or `OPENS_IN_NEW_TAB` alone when the base is empty (a link around a shape with no text).

So a second pass gives the same single title (the note is stripped and re-added), and an author's title cannot stand in for the note (it is stripped and the real note appended). No `data-new-tab-note` marker is needed in SVG, and the HTML branch is unchanged.

Prototype at 966204f (discarded), DOMPurify 3.4.17 (`title` is an allowed SVG tag; a `title` inserted by the hook survives the rest of the walk):

- `<svg><a xlink:href="https://example.com"><text>Lib</text></a></svg>` gave `<a xlink:href=... target="_blank" rel="noopener noreferrer"><title>Lib (opens in a new tab)</title><text>Lib</text></a>`; a second pass gave the same title once; an author title `Safe (opens in a new tab)` plus a second `<title>x</title>` gave one title `Safe (opens in a new tab)`.
- jsdom (Testing Library) gives an SVG `<a>` no `link` role, so unit tests assert the DOM (title text, attributes), not `getByRole`.
- Chromium 159 (Playwright), markup set with `innerHTML`: `<a href>` with the title: `link "Lib (opens in a new tab)"`; `<a href>` with `aria-label` instead: the same; `<a xlink:href>` only, with a title or an `aria-label`: no link in the tree (the `svg` shows as `img: Lib`), although the link takes focus; `<a xlink:href href>` with the title: `link "Lib (opens in a new tab)"`. Hence rule 1, and the title (ADR-10 decision 4) is enough without the fallback. Task 1.9 confirms this on the real page.

### Header (Task 2)

Target structure (checked by changing the live page's DOM to it with inline styles on the dev stack: `scrollWidth` 320/390/430/768 at those widths, install card inside the viewport):

```tsx
<div className="flex flex-col gap-4 md:flex-row md:gap-6" data-testid="mod-detail-header">
  <div className="flex min-w-0 flex-wrap gap-4 md:flex-1 md:flex-nowrap md:gap-6" data-testid="mod-detail-summary">
    <div className="flex-shrink-0">{/* logo, unchanged */}</div>
    <div className="min-w-0 grow basis-48 space-y-2">{/* info */}</div>
  </div>
  {/* InstallSection / InstalledVersionSection: Card className="w-full md:w-64 md:shrink-0" */}
</div>
```

- `basis-48` (12rem): at 390px (358px content) the logo and info stay side by side (128 + 16 + 214); at 320px (288px) the info goes under the logo (ADR-11 decision 1). Use `grow basis-48`, not `flex-1 basis-48` (two utilities setting `flex-basis`).
- `md:flex-nowrap` keeps logo and info side by side from `md` up, as today. At 768px with the sidebar expanded the content is 560px (`Layout.tsx:19`, `:46-50`), so the info column is about 128px wide; long words must wrap there: the `h1` (`:636`) and the info get `break-words`, the title row (`:634`) gets `gap-2` with `min-w-0` on its text block, the stats row (`:661`) gets `flex-wrap gap-x-4 gap-y-1`.
- Before (dev stack at drafting, stubbed mod with homepage, source, trailer; long name and four tags): `scrollWidth` 731 at 320, 390 and 430px, 899 at 768px (sidebar expanded); the install card at x 542-731 (768px: 710-899); select and button 36px tall. `VSS-pzj8` measured 674px with fewer links. A wide description added 1,058px more (1,789 at 390px), which Task 3 fixes.
- The `Back to Browse` button (32px, `size="sm"`, `:152-165`) and the text links are not install or version controls; ADR-11 does not ask for 44px there (see "Not changed").

### Description styles (Task 3)

In `@layer components` (which beats Tailwind's preflight in the base layer and loses to utilities), after the 18.1 rules. Every selector `.mod-description :where(...)` so it is (0,1,0) and an author's inline `style` always wins (inline styles beat any rule without `!important`; do not use `!important`). Values are a starting point; the AC fix the relations, not the numbers:

| Elements | Rules |
|---|---|
| container | `overflow-wrap: anywhere` (long URLs, AC 7); body text inherits (16px today) |
| `h1`-`h6` | `font-weight: 700` (`h4`-`h6`: 600); sizes `h1` 1.375rem, `h2` 1.25rem, `h3` 1.125rem, `h4`-`h6` 1.0625rem (all above body 1rem, all below the page title's 1.5rem, `:636` `text-2xl`); `margin: 1.25em 0 0.5em`; `line-height: 1.3` |
| `p`, `ul`, `ol`, `blockquote`, `pre`, `table`, `hr` | `margin: 0.75em 0`; first child `margin-top: 0` (`.mod-description > :where(:first-child)`) |
| `ul`, `ol` | `padding-left: 1.5em`; `list-style: disc` / `decimal`; nested `ul ul` `circle`; `li + li` small top margin |
| `a` | `color: var(--primary)`, `text-decoration: underline`, `text-underline-offset: 2px`; keep the 18.1 `::after` icon rule |
| `blockquote` | `border-left: 4px solid var(--border)`, `padding-left: 1em`, `color: var(--muted-foreground)`, `font-style: italic` |
| `code` | `background: var(--muted)`, `border-radius`, `padding: 0.1em 0.3em`, `font-family` mono, `font-size: 0.875em` |
| `pre` | `background: var(--muted)`, padding, `border-radius`, `overflow-x: auto`, `max-width: 100%`, `white-space: pre`; `pre code` no background or padding |
| `hr` | `border: 0; border-top: 1px solid var(--border)` |
| `table` | `display: block; max-width: 100%; overflow-x: auto; border-collapse: collapse`; `th`, `td` `border: 1px solid var(--border)`, padding; `th` `font-weight: 600`, `background: var(--muted)` |
| `strong`, `b` / `em`, `i` | `font-weight: 700` / `font-style: italic` (preflight keeps `bolder`; explicit is fine) |
| `img`, `video` | `max-width: 100%; height: auto`; `svg` `max-width: 100%` only |

- Colours: only `var(--...)` tokens from `:root` (`index.css:6-69`) and `.dark` (`:71-132`), or `@apply` with the token utilities (`text-primary`, `border-border`, `bg-muted`), as the existing rules do (`:262-264`). No hex value, no `prose-invert`.
- `display: block` on `table` gives the scroll inside the card without a wrapper element; Safari can drop table semantics for a `display: block` table. Description tables are author layout, and a wrapper would need the sanitizer to insert elements; this story accepts the trade-off (record it in the Completion Notes if you see a problem).
- The 19.3 image note rule (`[data-image-not-shown]`, `:262-264`) and the CSP spec's checks of it (`e2e/content-security-policy.spec.ts:424-440`) must still pass; the note is a `span`, which no new rule targets.

### Unit tests

| Task | File | Tests |
|---|---|---|
| 1 | new `web/src/components/NewTabLink.test.tsx` | `target="_blank"`, `rel="noopener noreferrer"`, exact name `Docs (opens in a new tab)` by role; `href`, `className`, `data-testid` passed through; children (an icon and text) kept |
| 1 | `web/src/lib/new-tab.test.ts` (or in `mod-description.test.ts`) | `OPENS_IN_NEW_TAB` from `mod-description.ts` is the same string as from `new-tab.ts` |
| 1 | `web/src/lib/mod-description.test.ts` "new tab note" block (`:158-217`) | replace `:187-195` (Existing tests that change); SVG `href` link: one `title`, first child, text `Lib (opens in a new tab)`, `target`/`rel` set; `xlink:href`-only link also gets `href` with the same value; author title `Diagram` becomes `Diagram (opens in a new tab)`; author title ending with the note, and two titles, give one title with one note; a second pass leaves one title with the same text (compare text and count, not the string: attribute order changes, 18.1 deviation 3); link with no text gets `(opens in a new tab)`; no `[data-new-tab-note]` inside the SVG; `javascript:` `xlink:href` gives no `href` and no title; the HTML link tests unchanged |
| 1 | `ModDetailPage.test.tsx` "external links" (`:654-752`) | exact names for ModDB Page, Homepage, Source, Watch trailer; `rel` on each; the two `*-new-tab-mark` icons present; an SVG link in the description has its title (one test through the page) |
| 1 | `InstalledModParts.test.tsx` (`:39-55`) | `getByRole('link', { name: 'Player Corpse (opens in a new tab)' })`; slug-only mod: `playercorpse (opens in a new tab)` |
| 1 | `layout/Sidebar.test.tsx` "External Links" (`:301-312`) | name exactly `GitHub (opens in a new tab)`; no `aria-label` |
| 1 | `ModCard.test.tsx:184`, `VersionCard.test.tsx:282-285`, `VersionTable.test.tsx` (`:73-76`, add) | the new wording; `VersionTable` gains the `aria-label` assertion it lacks |
| 2 | `ModDetailPage.test.tsx` "header section" (`:210-304`) | `mod-detail-header` has `flex-col` and `md:flex-row`; `mod-detail-summary` contains the logo and the name; `mod-detail-install-section` has `w-full` and `md:w-64`, for the install section and the installed version section; the version select and the install, Installed, Update and Switch buttons have `max-lg:min-h-11` (pattern `InstalledTab.test.tsx:752-753`); the breadcrumb `nav` has `flex-wrap` |
| 2 | `ModDetailPage.test.tsx` "loading state" (`:157-171`) | `mod-detail-loading-header` has `flex-col` and `md:flex-row` |
| 3 | `ModDetailPage.test.tsx` "description section" (`:383-505`) | the container (`:400`) has `mod-description` and its `className` does not match `/\bprose/`; an author's `style="color: #c33"` attribute is kept on the rendered paragraph |

New tests that stub `fetch` use `vi.stubGlobal('fetch', ...)` with `vi.unstubAllGlobals()` in `afterEach` (`project-context.md:170`); the existing `ModDetailPage.test.tsx` tests assign `globalThis.fetch` and stay as they are.

### Existing tests that change (deliberately)

Found with the Task 1 prototype (`bunx vitest run src/components src/features/mods src/lib`, 1977 passed, 2 failed) and by reading:

- `web/src/components/ModCard.test.tsx:184`: `aria-label` `Open Carry Capacity on ModDB (opens in new tab)` becomes `... (opens in a new tab)`.
- `web/src/components/VersionCard.test.tsx:282-285`: `View changelog for version 1.21.6 (opens in new tab)` becomes `... (opens in a new tab)`.
- `web/src/lib/mod-description.test.ts:187-195` ("adds no note to an SVG link, which keeps target and rel"): still passes, but states the old behaviour; replace it with the SVG title tests above.
- `web/src/features/mods/ModDetailPage.test.tsx:732` (trailer name) keeps passing through `NewTabLink`; keep it.
- `web/src/components/layout/Sidebar.test.tsx:305` (`/github/i`) keeps passing; tighten it to the exact name.
- E2E: `mod-detail-media.spec.ts:261` and `:264` keep passing (same names); `layout-widths.spec.ts:353-382` must keep passing (name link heights).
- Anything else that fails is a regression (AC 10): fix the code, not the test.

### E2E (`web/e2e/mod-detail-layout.spec.ts`)

Untagged (no live mod database, no game server), so the first CI pass runs it. Style and helpers of `e2e/mod-detail-media.spec.ts` (header comment with story, FRs, beads, "Reads only", requirements; `readOnly` that refuses every non-GET API call, `:102-113`; copy what you need, do not import across specs) and `config-js.ts` (`serveConfigKey`, `pretendServerInstalled`; any stub that passes a request on to the API with `route.fetch` must use `fetchOnNewConnection`).

- Lookup stub: `page.route(new RegExp('/api/v1alpha1/mods/lookup/e2elayoutmod(\\?.*)?$'), ...)` with a body shaped like `lookupBody` (`mod-detail-media.spec.ts:55-99`): name `An Extremely Long Mod Name That Keeps Going Past The Edge`, tags `Library`, `Utility`, `Worldgen`, `Crafting`, `homepage_url` and `source_url` on `https://example.com/...`, a `trailer_url` (`https://www.youtube-nocookie.com/embed/mJHZH_sThDM`), `logo_url: null`, `screenshots: []`, one release with a file. Description: `h1`-`h6`, paragraphs, a nested `ul` and an `ol`, an HTML link, a `blockquote`, inline `code`, a `pre` with a 300-character line, an `hr`, a 12-column table of long cells, `<img width="1200" height="40" src="data:image/png;base64,...">` (the 1x1 PNG of the media spec; `data:` passes the CSP and the sanitizer, so no network), a 200-character URL as text, `<p style="color: rgb(204, 51, 51)">`, an SVG with an `href` link and one with an `xlink:href`-only link (`<svg width="240" height="24"><a ...><text x="0" y="16">Diagram</text></a></svg>`).
- Guard: record every request whose host is not the manager's; expect none (the links are never clicked; the images are `data:`).
- **Links (1440px):** the four header links by exact name (AC 1); the two `*-new-tab-mark` icons visible; the HTML description link and both SVG links by role `link` and exact name (`Diagram (opens in a new tab)` twice; AC 3, the browser check of ADR-10 decision 5); the sidebar `GitHub (opens in a new tab)` (AC 2).
- **Phones (320, 390, 430px; light and dark via `page.emulateMedia({ colorScheme })`, asserting `html` has or lacks `dark` as `mod-detail-media.spec.ts:322-326` does):** `scrollWidth` equals the width; `mod-detail-install-section` below the `mod-detail-summary` box and as wide as the header (±1px); breadcrumb, header links, select and button boxes inside `[0, width]`; select and install button height ≥ 44 (AC 4).
- **768px:** install card top equals the logo's top (±1px), its left ≥ the info column's right; `scrollWidth` 768 (AC 5). Do not depend on the sidebar state (Story 21.8 changes its default at this width).
- **Description styles (390px, both themes):** computed `font-size` of each `h1`-`h6` > that of a `p`, `font-weight` ≥ 600, `h1` < the size of the page title (`mod-detail-name`); `ul` `list-style-type` `disc`, `ol` `decimal`, `padding-left` > 0; link `text-decoration-line` `underline` and `color` equal to a probe element's colour (`style.color = 'var(--primary)'` appended inside the description card for the check and removed after); blockquote `border-left-color` equal to a `var(--border)` probe; `code` background equal to a `var(--muted)` probe; link colour differs between light and dark (AC 6). Table and `pre`: `scrollWidth > clientWidth` and right edge inside the card; image box width ≤ the card content width; author paragraph colour `rgb(204, 51, 51)` (AC 7, 9).
- Nothing changes real state; no game server start or stop; no screenshot.

### Not changed (do not "fix" these here)

- Description media the CSP blocks other than images (`VSS-koo1`, not pulled in, change proposal `:1025`); the image rules of Story 19.3.
- The sanitizer's allowed tags and attributes; HTML link handling (note span, marker removal, icon).
- Breadcrumb link sizes (`Back to Browse` was added to Task 2 by the backlog drawdown); the Releases and Metadata cards beyond the slug wrap; the screenshot gallery (Story 18.1 fits it at 390px; its dialog's close button is Story 21.5's).
- The mod detail page's `max-w-4xl` (`:577`) and the app's content width (Story 21.8).
- Links in the Releases changelog: release changelogs are not rendered as HTML on this page (`ReleaseItem`, `:462-501`).

### API contract changes

None. No route, field, status code or error code changes; the web reads the same lookup response.

### ADR against the code

- **ADR-11 decision 1** says "from `md` up the row is as today". At 768px with the sidebar expanded, today's row is 899px wide for a mod with a long name (the stats row does not wrap and the info column has no `min-w-0`). The story keeps the one row from `md` up (AC 5) and adds wrapping inside the info column so it fits; otherwise AC 5 and FR279 ("does not scroll sideways from 320px up") would contradict each other.
- **ADR-10 decision 4** assumes a `<title>` reaches the accessibility tree. In Chromium it does for an SVG `<a href>`, but an SVG `<a>` with only `xlink:href` is not exposed as a link at all, with a title or with the decision 5 fallback (`aria-label`). The story adds rule 1 (copy the sanitized `xlink:href` to `href`) so both kinds are announced; the title stays the mechanism.
- **ADR-10 decision 1** names one component "used by the five unmarked links"; it also replaces the trailer link's hand-written span (the same markup), so there is one implementation for all four header links.
- **Epic task list:** the epic's Tasks 1 and 2 are one task here ("Commits and release notes").
- Everything else in ADR-10 and ADR-11 matches the code at 966204f.

### Testing Requirements

**CRITICAL:** Tests are written with each task and committed with it, red first. `just test-web <file>` after each task; `just check` before review.

- Unit tests run in Vitest's `vmThreads` pool; follow `project-context.md:167-172` (stubbing rule, Story 20.2). No skipped unit tests.
- jsdom has no layout and does not load `index.css`: class assertions in unit tests, sizes and computed styles in the E2E only.
- E2E specs are type-checked (`web/e2e/tsconfig.json`); untagged specs run in the first CI pass (`web/e2e/README.md:5-21`, `:38-56`); `just test-e2e-ci` runs both passes on throwaway containers if you want the CI view.

### Security Requirements

- The SVG title text is set with `textContent`, never parsed. The copied `href` comes only from an `xlink:href` that DOMPurify kept; the hook never adds a URL of its own. Links keep `rel="noopener noreferrer"`.
- The CSP (`api/src/vintagestory_api/main.py:238-239`: `style-src 'self' 'unsafe-inline'`, `img-src 'self' data: https:`) is unchanged; the new CSS is in the bundled stylesheet.
- No instance data in tests or the E2E (stubbed mod, `example.com` links).

### Development Commands

- `just test-web src/lib/mod-description.test.ts src/components/NewTabLink.test.tsx src/components/InstalledModParts.test.tsx src/components/layout/Sidebar.test.tsx src/components/ModCard.test.tsx src/components/VersionCard.test.tsx src/components/VersionTable.test.tsx src/features/mods/ModDetailPage.test.tsx`, `just typecheck-web`, `just lint-web`, `just check`.
- Prettier on changed files only, with Story 21.1's pinned version and config (for example `cd web && bunx prettier --write <files>` as Story 21.1 documents); never `just format-web` on the whole tree.
- E2E: `just docker restart`, then `cd web && bunx playwright test e2e/mod-detail-layout.spec.ts` with `VS_API_KEY_ADMIN` exported.

### Previous Story Intelligence

- **18.1** (`VSS-tzl`, `VSS-l4x`): `OPENS_IN_NEW_TAB`, the HTML note and marker handling (its review L1: every marker removed, then one note), the `.mod-description` icon rule; jsdom trims the note's leading space in names (deviation 2), a second pass reorders attributes (deviation 3); the 390px measurement that found `VSS-pzj8`.
- **19.3** (`VSS-my4c`): image rules in the hook; `[data-image-not-shown]` style; `content-security-policy.spec.ts` checks the description's inline style and image note.
- **19.6**: only `https` homepage, source and logo URLs reach the page; the links can be null (`ModDetailPage.test.tsx:696-713`).
- **20.2**: `vmThreads` stubbing rule. **20.5**: `fetchOnNewConnection` for stubs that pass a request on. **20.6**: untagged vs `@moddb` and the README counts.
- **17.x/18.x/19.x reviews:** a `fix` subject must describe something a user can see; a completion note must be true of the code; manual checks wait for the maintainer; E2E that changes real state needs a snapshot guard (this one changes none).

### Git Intelligence

- Base `966204f` (`docs(epic-21): record the maintainer's answers and pull in VSS-q38r`). Before this story: 21.1 reformats every web file (all line numbers move), 21.4 and 21.5 edit `ModTable.tsx` and `VersionTable.tsx` (21.5 changes the `VersionTable` Version column next to the changelog link and the dialog close button). Re-find each location by content.
- Last changes to the touched files: `a1c3777` (19.6, https-only links), `43138d9` (19.3, image note), `5baeb5d` (18.1, description link note).

### Project Structure Notes

- New: `web/src/lib/new-tab.ts`, `web/src/components/NewTabLink.tsx`, `web/src/components/NewTabLink.test.tsx`, `web/e2e/mod-detail-layout.spec.ts`.
- Modified: `web/src/lib/mod-description.ts` (+ test), `web/src/features/mods/ModDetailPage.tsx` (+ test), `web/src/components/InstalledModParts.tsx`, `layout/Sidebar.tsx`, `ModCard.tsx`, `VersionCard.tsx`, `VersionTable.tsx` (+ their tests), `web/src/styles/index.css`, `web/e2e/README.md`.
- No API file, no `package.json` or lockfile change.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 21.6: Mod Detail Page Polish]
- [Source: _bmad-output/planning-artifacts/prd.md] FR278, FR279, FR280 (`:871-873`)
- [Source: _bmad-output/planning-artifacts/architecture/epic-21-maintainer-decisions-and-web-polish.md#ADR-10, #ADR-11, "Mod detail page today"]
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-11-17-epic-21.md] section 2 release notes (`:101`), answer 5 (`:1013`), `VSS-koo1` not pulled in (`:1025`)
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md] 44px touch targets (`:515`, `:1180`, `:1290`)
- [Source: _bmad-output/implementation-artifacts/18-1-mod-detail-media-and-links.md], [19-3-content-security-policy-and-api-docs.md]
- Beads: `VSS-woae`, `VSS-pzj8`, `VSS-4vbj`, parent `VSS-syuj`
- `project-context.md` (no suppressions; manual checks need the maintainer; commit format `:643-697`; stubbing rule `:167-172`)

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

- Story created 2026-11-17 from Epic 21 (Story 21.6), ADR-10, ADR-11, FR278-FR280, the change proposal, the three beads and the code at 966204f. Prototypes, all discarded: the Task 1 links (2 unit tests fail, listed), the SVG title in the hook (DOMPurify keeps it; jsdom gives SVG links no role), Chromium accessibility snapshots of SVG links (`xlink:href`-only links are not exposed), and the Task 2 layout applied to the live page on the dev stack (fits at 320-768px).

### File List

## Change Log

- 2026-11-17: Story created and validated (ready-for-dev).
