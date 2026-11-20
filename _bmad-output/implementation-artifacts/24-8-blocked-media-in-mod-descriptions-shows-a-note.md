# Story 24.8: Blocked Media in Mod Descriptions Shows a Note

Status: review

<!-- Implements FR343, Epic 24 ADR-7. Bead: VSS-koo1 (API-094), item 2; Story 24.2 carried item 1; this story closes the bead after merge. Branch story/24-8-blocked-media-in-mod-descriptions-shows-a-note, stacked on story/24-7-installed-mods-can-be-filtered at 8b7d2fec (24.7 in review); the PR targets main and merges after 24.7's. Web only. -->

## Story

As an **administrator**,
I want **media a mod description cannot load to show a note**,
so that **I know something is missing instead of seeing a silent gap**.

## Acceptance Criteria

1. **Given** a description with a `<video>` or an `<audio>` (with or without `<source>`, `<track>`, `poster`)
   **When** the mod detail page shows it
   **Then** it is replaced by a note, "Video not shown" or "Audio not shown" (with its `title` or `aria-label` when it has one), styled as the image note; the policy has no `media-src`, so none would load
   *(FR343; ADR-7 decision 1)*

2. **Given** a `<picture>` with `<source srcset>`
   **When** it is shown
   **Then** the sources are dropped and its `<img>` is used, checked as any image (kept from `https:`, else the image note)
   *(FR343; ADR-7 decision 1)*

3. **Given** an SVG `<image>` whose `href` or `xlink:href` the policy refuses
   **When** it is shown
   **Then** the `<image>` is removed and the rest of the drawing kept; one from `https:` is kept
   *(FR343; ADR-7 decision 1)*

4. **Given** a `background` attribute, or an inline style declaration with a `url()` the policy refuses
   **When** it is shown
   **Then** the attribute or the declaration is removed without a note; other declarations, and `url()`s from `https:` or `data:image/`, are kept
   *(FR343; ADR-7 decision 2)*

5. **Given** an `https:` image
   **Then** it is unchanged, and the Content-Security-Policy is unchanged
   *(FR343; ADR-7 decision 3)*

6. **(Quality gates.)** `just check` green with 0 skipped unit tests; no suppression added; `git diff` of `api/` empty.

## Tasks / Subtasks

- [x] Task 1: The sanitizer (AC: 1 to 6)
  - [x] 1.1: Red first: `mod-description.test.ts` "media the page cannot load" (13 cases)
  - [x] 1.2: `mod-description.ts`: `VIDEO_NOT_SHOWN`, `AUDIO_NOT_SHOWN`, `replaceMedia`, `removeBlockedStyleUrls`, `cssUrlsLoadable`; the hook handles video, audio, picture sources, SVG images, `background` and inline `url()`; `index.css` styles `[data-media-not-shown]` as the image note
  - [x] 1.3: Commit `fix(story-24.8/task-1): show a note in place of video, audio and other media a mod description cannot load`

- [x] Task 2: Validate and move the story to review (AC: all)
  - [x] 2.1: `just check` green; CSP and mod detail E2E on a throwaway container; `just changelog` lists Task 1
  - [x] 2.2: Status `review`; sprint status; ADR-7 as implemented; Dev Agent Record and File List
  - [x] 2.3: Commit `chore(story-24.8/task-2): validate and move story 24.8 to review`

## Dev Notes

### The code today (verified at 804af73f)

- `web/src/lib/mod-description.ts` replaced an `<img>` the policy would block with `<span data-image-not-shown>` (Story 19.3) and did nothing for other media.
- The policy (Epic 19 ADR-6): `default-src 'self'`, `img-src 'self' data: https:`, `style-src 'self' 'unsafe-inline'`, no `media-src`. So video and audio from any other host are always blocked, while `<picture>` sources, SVG images, `background` and CSS `url()` are images, allowed from `https:`.

### Decisions made in implementation (ADR-7 refined)

- **Only blocked addresses are removed.** ADR-7 listed the media kinds; the policy allows images from `https:`, so a picture's image, an SVG image and a CSS `url()` from `https:` stay. Video and audio are always replaced, since nothing allows them.
- **A picture's sources are dropped, not noted.** Its `<img>` is the fallback and gets the image rule, so the reader sees the image or the image note.
- **An SVG image is removed without a note:** an SVG cannot hold an HTML note.
- **`background` is removed always:** a legacy attribute, never needed for the text.

### References

- `epics.md` "Story 24.8"; `architecture/epic-24-mod-management-follow-ups.md` ADR-7; Epic 19 ADR-6; Story 19.3

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5), as the epic's controller.

### Debug Log References

- `just check` (2026-11-20): API 4087 passed, web 3925 passed, 0 skipped; Pyright 0/0; lints green.
- `just test-e2e-ci e2e/content-security-policy.spec.ts e2e/mod-detail-layout.spec.ts` (throwaway container): web 12 passed, API E2E 4 passed.
- `just changelog`: one entry from this story (Task 1).

### Completion Notes List

- 2026-11-20 (create-story and dev-story): created from Epic 24's Story 24.8 and ADR-7; Tasks 1 and 2 done.

### File List

- `web/src/lib/mod-description.ts`, `mod-description.test.ts` (modified)
- `web/src/styles/index.css` (modified)
- `_bmad-output/planning-artifacts/architecture/epic-24-mod-management-follow-ups.md` (ADR-7 as implemented)
- `_bmad-output/implementation-artifacts/24-8-blocked-media-in-mod-descriptions-shows-a-note.md` (this file)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (through `just sprint set` only)

## Change Log

- 2026-11-20: Story 24.8 created and implemented (dev-story): Tasks 1 and 2; status review.
