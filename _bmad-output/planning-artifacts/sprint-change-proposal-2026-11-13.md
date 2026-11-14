# Sprint Change Proposal: UI Polish (Epic 16)

**Date:** 2026-11-13
**Author:** Matt
**Workflow:** correct-course (incremental review)
**Scope classification:** Minor
**Status:** Approved by Matt, 2026-11-13

## 1. Issue Summary

**Trigger:** Accumulated feedback. Using the manager on the cluster deployment showed that the mod browser forgets the search and sort whenever a mod's detail page is opened (`VSS-dkl`), and seven older UI items in beads describe the same kind of rough edge.

**Problem:** Day-to-day use of the web UI loses the admin's place, shows inaccurate or unreadable mod information, and has layouts that do not fit phones or wide screens. None of it blocks a task, but together it makes the UI feel unfinished now that it has a published release.

**Evidence:**

- `BrowseTab.tsx` keeps `searchInput`, `filters` and `sort` in `useState`, so they reset to defaults when the tab remounts after a detail page. Story 10.7's restoration saves only `{ scrollY, page }` and clears it when search, filters or sort change.
- `ModDetailPage.tsx` matches the installed mod with `installedMod.slug === slug`; the browse slug is the entry's first mod ID (`VSS-ywb`, from the Story 14.3 review).
- `ModLookupInput.tsx` renders `modData.description` as text, so its HTML shows as markup; the detail page already sanitizes the same field with DOMPurify (`VSS-4ll`).
- The Installed tab is a horizontally scrolling table on every screen size, while Story 14.3 AC1 and the UX spec call for mobile cards (`VSS-rr5`).
- `GameConfigPanel.tsx` stacks every settings card full width (`space-y-4`) (`VSS-dfx`).
- `FileManagerPanel.tsx` navigates up only with a Back button (`VSS-8lh`).
- No view names the most recent game version an incompatible mod supports: the incompatible message lists the first three tags of the newest release, which are its oldest, and browse cards show no compatibility at all (`VSS-udh`).

**Scope decisions made during review:**

| Decision | Choice |
|---|---|
| Items in scope | `VSS-dkl`, `VSS-901`, `VSS-ywb`, `VSS-udh`, `VSS-4ll`, `VSS-rr5`, `VSS-dfx`, `VSS-8lh` |
| Mod filters | Persisted with search and sort; they are lost the same way |
| Browse state mechanism | Decided in Story 16.0; URL query parameters are the expected choice because they also survive refresh and browser back |
| `VSS-jna` (lost API connection) | Not in scope: reliability work, not polish |
| `VSS-glz` (file editing) | Not in scope: a new capability |
| Test-only items `VSS-3mr`, `VSS-37a` | Not in scope: moved under the Web UI Test Coverage epic (`VSS-029`) |

## 2. Impact Analysis

**Epic impact:** Epics 1-14 are done and Epic 15 is finishing; none is invalidated. One new epic, Epic 16: UI Polish, with 8 stories. No resequencing.

**Story impact:** No existing story changes. Story 16.1 extends Story 10.7's restoration; Story 16.5 delivers the mobile layout that Story 14.3 AC1 describes.

**Artifact conflicts:**

| Artifact | Change |
|---|---|
| PRD | Add FR167-FR174; frontmatter |
| Epics | Add Epic 16; FR coverage rows; Story Summary row; frontmatter |
| Architecture | New `architecture/epic-16-ui-polish.md` from Story 16.0; index entry |
| UX spec | None. Story 16.5 implements the mobile mod cards it already describes |
| Beads | Epic `Epic 16: UI Polish` with the eight in-scope issues as children |

**Technical impact:**

- Web only, except Story 16.3, which may add the most recent supported game version to the compatibility data the API returns.
- No new dependencies: DOMPurify is already used by the detail page.
- Test strategy unchanged; Story 16.1 adds an end-to-end test of the detail round trip.

## 3. Recommended Approach

**Selected:** Option 1, Direct Adjustment: add Epic 16 within the existing structure.

| Option | Assessment |
|---|---|
| 1. Direct Adjustment | Viable. Small, independent web changes. Effort small to medium, risk low. |
| 2. Rollback | Not viable. Nothing completed conflicts with the change. |
| 3. MVP Review | Not needed. |

**Effort:** Small to medium. Eight stories: one preparation story and seven small changes, mostly size-s or size-m in beads.

**Risks:**

- URL query parameters change the browse URL; existing links to `/game-server/mods/browse` must keep working with default state.
- The most recent supported game version may only come from mod details, which browse cards do not fetch; Story 16.3 then limits it to the detail page and Installed list rather than adding a request per card.
- Rendering description HTML in the preview reuses the detail page's sanitizing; it must not be rendered unsanitized.

## 4. Detailed Change Proposals

### 4.1 PRD (`prd.md`) — approved

**Frontmatter:** `lastUpdated: '2026-11-13'`; update entry "Added FR167-FR174 for Epic 16 (UI Polish)".

**Post-MVP Functional Requirements, new section:**

```markdown
### Epic 16: UI Polish

#### Mod Browser

- FR167: The mod browser keeps its search term, filters and sort when the admin opens a mod's detail page and returns with Back to Browse or the browser's back button
- FR168: Returning to the mod browser restores the page and scroll position that went with that search, filters and sort
- FR169: The mod detail page recognizes an installed mod when any mod ID in the database entry matches it
- FR170: For a mod that is not verified or is incompatible with the installed game version, the UI shows the most recent game version the mod supports
- FR171: The mod lookup preview shows the mod description as formatted, sanitized HTML instead of raw markup

#### Layout and Navigation

- FR172: On narrow screens, installed mods are shown as cards with version, update status and Update action, enable toggle and remove action, without horizontal scrolling
- FR173: Game server settings use the available width on desktop screens instead of full-width stacked cards
- FR174: The file browser shows the current path as clickable segments, each opening that directory
```

### 4.2 Epics Structure (`epics.md`) — approved

**Frontmatter:** `lastUpdated: '2026-11-13'`; update entry "Added Epic 16 (8 stories) for UI Polish".

**FR Coverage Map**, appended after FR166:

```markdown
| FR167 | Epic 16 | Mod browser keeps search, filters and sort |
| FR168 | Epic 16 | Page and scroll restored with browse state |
| FR169 | Epic 16 | Installed mod recognized by any mod ID |
| FR170 | Epic 16 | Latest supported game version for incompatible mods |
| FR171 | Epic 16 | Formatted description in lookup preview |
| FR172 | Epic 16 | Installed mods as cards on phones |
| FR173 | Epic 16 | Settings use desktop width |
| FR174 | Epic 16 | File browser breadcrumbs |
```

**Story Summary:**

OLD:
```markdown
| **Total** | | **85** |
```

NEW:
```markdown
| Epic 16: UI Polish | 16.0, 16.1, 16.2, 16.3, 16.4, 16.5, 16.6, 16.7 | 8 |
| **Total** | | **93** |
```

### 4.3 Epic 16 Stories (appended to `epics.md`) — approved

## Epic 16: UI Polish

**Goal:** Admins keep their place when moving around the web UI, see accurate mod information, and get layouts that fit their screen.

### Current State

- The mod browser keeps search, filters and sort in component state, so opening a mod's detail page and coming back resets them to newest, descending, no search; page and scroll restoration from Story 10.7 is cleared whenever they change
- The mod detail page matches an installed mod only by the browse slug, so an installed mod whose ID is not the entry's first mod ID shows the install flow
- An unverified or incompatible mod gives no hint of which game version it does support
- The mod lookup preview card prints the mod description's HTML as plain text
- The Installed mods table scrolls horizontally on phones
- Game server settings cards stretch across the full width on desktop
- The file browser has only a Back button

### Target State

- Returning from a mod's detail page restores the browser exactly: search, filters, sort, page and scroll position
- Mod information is accurate: installed mods are recognized by any mod ID, and incompatible mods name the game version they last supported
- The lookup preview card, Installed mods and settings pages read well at every screen size, and the file browser path is clickable

---

### Story 16.0: Epic 16 Technical Preparation

As a **developer**,
I want **the open questions behind the polish stories answered against the running app**,
So that **each story starts from confirmed behavior and data**.

**Acceptance Criteria:**

**Given** the mod browser with Story 10.7's scroll restoration
**When** it is exercised manually, including on a throttled network
**Then** findings record whether page and scroll restoration work today, and whether the 100 ms timeout is reliable (`VSS-901`)

**Given** the browse state that has to survive navigation
**When** URL query parameters and sessionStorage are compared
**Then** findings record the chosen mechanism and why, including browser back, refresh and shared links

**Given** the mod database API
**When** its release data is checked for incompatible mods
**Then** findings record where the most recent supported game version comes from, and whether it is available on browse cards or only from mod details

**Given** the game server settings page
**When** it is reviewed at common desktop widths
**Then** findings record the target layout for the settings cards

**Tasks:**
- [ ] Verify Story 10.7 scroll restoration manually and record the result on `VSS-901`
- [ ] Choose the browse state persistence mechanism
- [ ] Find the source of a mod's most recent supported game version
- [ ] Sketch the desktop settings layout
- [ ] Write `architecture/epic-16-ui-polish.md` with the findings and add it to the index

---

### Story 16.1: Mod Browser State Survives Mod Details

As an **administrator**,
I want **the mod browser to keep my search, filters and sort when I look at a mod and come back**,
So that **I can compare several mods without searching again each time**.

**Acceptance Criteria:**

**Given** I have entered a search term, set filters or changed the sort
**When** I open a mod's detail page and return with Back to Browse or the browser's back button
**Then** the search term, filters and sort are as I left them, and the results match them

*(Covers FR167)*

**Given** I was on a later page and scrolled down
**When** I return from a mod's detail page
**Then** the same page is shown and scrolled to the card I opened, with the search, filters and sort I had set

*(Covers FR168)*

**Given** I change the search, filters or sort after returning
**When** the results change
**Then** the browser goes back to page 1, as it does today

**Tasks:**
- [ ] Persist search, filters and sort with the mechanism chosen in Story 16.0 (`VSS-dkl`)
- [ ] Restore page and scroll position together with them; fix restoration timing if Story 16.0 found it unreliable (`VSS-901`)
- [ ] Tests, including an end-to-end test of the detail round trip

---

### Story 16.2: Installed Mods Recognized by Any Mod ID

As an **administrator**,
I want **a mod's detail page to know when I already have it installed**,
So that **I am not offered an install for a mod I have**.

**Acceptance Criteria:**

**Given** a database entry that ships several mod IDs, and I have installed one that is not its first
**When** I open the entry's detail page
**Then** it shows the installed state, version and update actions, not the install flow

*(Covers FR169)*

**Tasks:**
- [ ] Match installed mods against every mod ID in the entry's releases (`ModRelease.modidstr`) instead of the browse slug (`VSS-ywb`)
- [ ] Tests

---

### Story 16.3: Latest Supported Game Version for Incompatible Mods

As an **administrator**,
I want **to see which game version an unverified or incompatible mod last supported**,
So that **I can judge how far behind it is before installing it**.

**Acceptance Criteria:**

**Given** a mod that is not verified or is incompatible with my installed game version
**When** I view it on its detail page or in the Installed mods list
**Then** the compatibility message names the most recent game version the mod supports

*(Covers FR170)*

**Given** Story 16.0 found the version available without fetching each mod's details
**When** I browse mods
**Then** browse cards show it too

**Tasks:**
- [ ] Add the most recent supported game version to the compatibility data, from the source chosen in Story 16.0 (`VSS-udh`)
- [ ] Show it in the compatibility message on the detail page and Installed mods list, and on browse cards if available
- [ ] Tests

---

### Story 16.4: Formatted Description in the Mod Lookup Preview

As an **administrator**,
I want **the mod lookup preview to show the description as formatted text**,
So that **I can read it instead of raw HTML tags**.

**Acceptance Criteria:**

**Given** I look up a mod by slug or URL
**When** the preview card shows its description
**Then** the description is rendered from sanitized HTML, as on the mod detail page, and kept to a short preview

*(Covers FR171)*

**Tasks:**
- [ ] Render the preview description with DOMPurify, sharing the detail page's sanitizing (`VSS-4ll`)
- [ ] Clamp the preview length
- [ ] Tests, including that scripts and event handlers are stripped

---

### Story 16.5: Installed Mods on Phones

As an **administrator**,
I want **installed mods to fit a phone screen**,
So that **I can update, enable and remove mods without scrolling sideways**.

**Acceptance Criteria:**

**Given** a screen narrower than the `md` breakpoint
**When** I open Installed mods
**Then** each mod is a card showing its version, update status and Update action, enable toggle and remove action, with no horizontal scrolling

*(Covers FR172)*

**Given** a wider screen
**When** I open Installed mods
**Then** the existing table is unchanged

**Tasks:**
- [ ] Add a card layout below `md` for the Installed tab (`VSS-rr5`)
- [ ] Tests at both breakpoints

---

### Story 16.6: Settings Layout on Desktop

As an **administrator**,
I want **game server settings to use the width of a desktop screen**,
So that **I can see more settings without scrolling past half-empty cards**.

**Acceptance Criteria:**

**Given** a desktop-width screen
**When** I open game server settings
**Then** the settings cards follow the layout chosen in Story 16.0 instead of stretching across the full width

*(Covers FR173)*

**Given** a phone-width screen
**When** I open game server settings
**Then** the cards stack in one column as they do today

**Tasks:**
- [ ] Apply the desktop layout to the settings cards (`VSS-dfx`)
- [ ] Tests

---

### Story 16.7: File Browser Breadcrumbs

As an **administrator**,
I want **to jump to any folder in the current path**,
So that **I can move up several levels in one click**.

**Acceptance Criteria:**

**Given** I am in a subdirectory of the file browser
**When** I look at the path
**Then** each segment, and the root, is a link to that directory

*(Covers FR174)*

**Given** I click a segment
**When** the directory loads
**Then** its listing is shown and the path updates

**Tasks:**
- [ ] Replace the Back button with breadcrumb segments (`VSS-8lh`)
- [ ] Tests, including the end-to-end directory navigation test from `VSS-3mr` if it is still open

### 4.4 Other Artifacts — approved

| Artifact | Change | When |
|---|---|---|
| `sprint-status.yaml` | Add `epic-16` (backlog), stories `16-0` to `16-7` (backlog) and `epic-16-retrospective` (optional), via `just sprint` | Now |
| Beads | Create epic `Epic 16: UI Polish`; parent `VSS-dkl`, `VSS-901`, `VSS-ywb`, `VSS-udh`, `VSS-4ll`, `VSS-rr5`, `VSS-dfx`, `VSS-8lh` to it; close each with an AAR when its story is done | Now, and per story |
| Beads | Parent `VSS-3mr` and `VSS-37a` to the Web UI Test Coverage epic `VSS-029` | Now |
| `architecture/epic-16-ui-polish.md` (new), `architecture/index.md` | Findings and decisions from Story 16.0 | Story 16.0 |

## 5. Implementation Handoff

**Scope:** Minor. A new epic in the backlog; no replanning of existing work.

| Role | Responsibility |
|---|---|
| Scrum Master (`create-story`) | Create story files 16.0 to 16.7 in order from `epics.md` and the Epic 16 architecture notes |
| Developer (`dev-story`) | Implement each story; Story 16.0 records its findings before 16.1 starts |
| Reviewer (`code-review`) | Delegated read-only review per story |
| Maintainer (Matt) | Approves this proposal and the Story 16.0 decisions |

**Success criteria:**

- Opening a mod's detail page and returning restores search, filters, sort, page and scroll, with Back to Browse and with browser back
- Each in-scope beads issue is closed with an AAR by its story
- `just check` and CI pass throughout

## Addendum (2026-11-13)

After Stories 16.0-16.7 were done, the maintainer added **Story 16.8: Name Sort and Empty Settings** to Epic 16 for two bugs found during the epic:

- `VSS-stm.1` [UI-067]: the Name (A-Z) sort requests 1,000 mods per page, the browse API allows at most 100, and the grid shows no mods. The API already sorts by name server-side, so the web UI uses it and pages normally.
- `VSS-7ed` [UI-069]: game settings with no value show the text "null" and can save it, and Password is shown in clear text.

New requirements FR175-FR176 (`prd.md`); story in `epics.md`; sprint key `16-8-name-sort-and-empty-settings` added with `just sprint add-story`. The approved proposal above is unchanged.
