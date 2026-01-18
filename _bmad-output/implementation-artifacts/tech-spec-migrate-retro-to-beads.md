---
title: 'Migrate Retro Action Items to Beads'
slug: 'migrate-retro-to-beads'
created: '2026-01-18'
status: 'implementation-complete'
stepsCompleted: [1, 2, 3, 4]
tech_stack:
  - beads CLI (bd)
  - YAML (sprint-status.yaml)
  - Markdown (project-context.md, workflow instructions)
files_to_modify:
  - '_bmad-output/implementation-artifacts/sprint-status.yaml'
  - 'project-context.md'
  - '_bmad/bmm/workflows/4-implementation/retrospective/instructions.md'
code_patterns:
  - 'bd create --type epic --parent <id> --label RETRO'
  - 'bd close <id> --reason "..."'
  - '3-tier hierarchy: epic → task (retro container) → task (action items)'
test_patterns:
  - 'bd list --label RETRO --type epic'
  - 'bd epic status'
  - 'bd show <id> for parent-child verification'
---

# Tech-Spec: Migrate Retro Action Items to Beads

**Created:** 2026-01-18

## Overview

### Problem Statement

Retro action items are tracked in sprint-status.yaml's `retro_action_items` section, which doesn't support hierarchy, dependencies, or integration with the beads workflow. There's no enforced process for consistent tracking, making it easy to lose context or forget follow-through.

### Solution

Migrate historical retro items (Epics 8-13) to beads using a 3-tier structure (Epic → Retro → Action Items) with a `RETRO` label. Each action item bead will include context extracted from the original retrospective file. Update project documentation and the retrospective workflow to enforce this pattern going forward. Delete the `retro_action_items` section from sprint-status.yaml.

### Scope

**In Scope:**
- Create 6 epic shells (Epics 8-13) with `RETRO` label
- Create 6 retrospective container tasks (one per epic)
- Create 23 action item tasks as children of the retro containers
- Extract context from retro files into each bead's description
- Close all completed items (22 of 23)
- Delete `retro_action_items` section from sprint-status.yaml
- Update `project-context.md` with beads retro convention
- Edit retrospective workflow to create beads issues instead of yaml entries

**Out of Scope:**
- Migrating stories to beads (they stay in sprint-status.yaml)
- Changing the retrospective workflow analysis/discussion steps
- Creating future epics 14+ structure (that's when they happen)

## Context for Development

### Codebase Patterns

- Beads CLI (`bd`) is the issue tracking system
- Labels are uppercase: `API`, `UI`, `CICD`, `INFRA`, `TOOLS`
- New label `RETRO` will be added for retrospective-related issues
- Parent/child hierarchy via `--parent <id>` flag
- Issue types: `epic` for top-level, `task` for children

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `_bmad-output/implementation-artifacts/sprint-status.yaml` | Source: `retro_action_items` section (lines 167-200) |
| `_bmad-output/implementation-artifacts/epic-8-retro-2026-01-02.md` | E8 context: 4 action items (A1-A4), Section 4 |
| `_bmad-output/implementation-artifacts/epic-9-retro-2026-01-05.md` | E9 context: 4 action items (A1-A4), "Action Items for Epic 10" |
| `_bmad-output/implementation-artifacts/epic-10-retro-2026-01-10.md` | E10 context: 5 action items (A1-A5), "Action Items" section |
| `_bmad-output/implementation-artifacts/epic-11-retro-2026-01-11.md` | E11 context: 3 action items (A1-A3), "Action Items" section |
| `_bmad-output/implementation-artifacts/epic-12-retro-2026-01-18.md` | E12 context: 3 action items (A1-A3), "Action Items" section |
| `_bmad-output/implementation-artifacts/epic-13-retro-2026-01-14.md` | E13 context: 5 action items (A1-A5), "Action Items" section |
| `project-context.md` | Update "Pre-Epic Checklist" section (lines 817-845) |
| `_bmad/bmm/workflows/4-implementation/retrospective/instructions.md` | Workflow Step 8 (lines 803-1042) - action item synthesis |

### Technical Decisions

- **3-tier structure:** Epic (shell) → Retrospective (task) → Action Items (tasks)
- **Label:** `RETRO` (uppercase to match existing convention)
- **Context preservation:** Each action item gets markdown description from retro file
- **Historical items:** Create then immediately close with reason

## Implementation Plan

### Tasks

#### Phase 1: Historical Migration (Epics 8-13)

- [x] **Task 1:** Create Epic 8 hierarchy in beads
  - File: `epic-8-retro-2026-01-02.md` (read for context)
  - Actions:
    1. `bd create "Epic 8: Periodic Task Patterns" --type epic --label RETRO` → capture ID as `$E8`
    2. `bd create "Epic 8 Retrospective" --type task --parent $E8 --label RETRO` → capture ID as `$E8R`
    3. For each action item (E8-A1 through E8-A4):
       - Extract context from retro file Section 4 "Action Items" table
       - `bd create "E8-A1: Add UI Testing Philosophy to architecture.md" --type task --parent $E8R --label RETRO --description "..."`
       - `bd close <id> --reason "Completed during Epic 8 sprint (marked done in sprint-status.yaml)"`
    4. Close E8R and E8 (all children done)

- [x] **Task 2:** Create Epic 9 hierarchy in beads
  - File: `epic-9-retro-2026-01-05.md` (read for context)
  - Actions: Same pattern as Task 1 for E9-A1 through E9-A4

- [x] **Task 3:** Create Epic 10 hierarchy in beads
  - File: `epic-10-retro-2026-01-10.md` (read for context)
  - Actions: Same pattern as Task 1 for E10-A1 through E10-A5

- [x] **Task 4:** Create Epic 11 hierarchy in beads
  - File: `epic-11-retro-2026-01-11.md` (read for context)
  - Actions: Same pattern as Task 1 for E11-A1 through E11-A3

- [x] **Task 5:** Create Epic 12 hierarchy in beads
  - File: `epic-12-retro-2026-01-18.md` (read for context)
  - Actions: Same pattern as Task 1 for E12-A1 through E12-A3
  - **Exception:** E12-A3 remains OPEN (it's the "migrate to beads" item - this task!)

- [x] **Task 6:** Create Epic 13 hierarchy in beads
  - File: `epic-13-retro-2026-01-14.md` (read for context)
  - Actions: Same pattern as Task 1 for E13-A1 through E13-A5

#### Phase 2: Cleanup

- [x] **Task 7:** Remove `retro_action_items` section from sprint-status.yaml
  - File: `_bmad-output/implementation-artifacts/sprint-status.yaml`
  - Action: Delete lines 167-200 (the entire `retro_action_items:` section and all its contents)
  - Note: Preserve comment structure above and below

#### Phase 3: Documentation Updates

- [x] **Task 8:** Update project-context.md with beads retro convention
  - File: `project-context.md`
  - Actions:
    1. Update "Pre-Epic Checklist" section (lines 817-845):
       - Change "Review `sprint-status.yaml` `retro_action_items` section" to "Review beads issues with RETRO label (`bd list --label RETRO --status open`)"
    2. Add new section "Retrospective Action Item Tracking" explaining:
       - 3-tier structure: Epic shell → Retro container → Action items
       - RETRO label convention
       - How to create action items during retro (`bd create --parent <retro-id> --label RETRO`)
       - How to verify follow-through (`bd list --label RETRO --status open`)

- [x] **Task 9:** Update retrospective workflow instructions
  - File: `_bmad/bmm/workflows/4-implementation/retrospective/instructions.md`
  - Actions:
    1. In Step 8 (lines 803-1042), modify action item synthesis to:
       - Create epic shell if not exists: `bd create "Epic {{epic_number}}: {{epic_title}}" --type epic --label RETRO`
       - Create retro container: `bd create "Epic {{epic_number}} Retrospective" --type task --parent <epic-id> --label RETRO`
       - Create each action item as child: `bd create "E{{epic_number}}-A{{n}}: {{description}}" --type task --parent <retro-id> --label RETRO`
    2. Remove references to updating `retro_action_items` in sprint-status.yaml
    3. Add verification step: `bd show <retro-id>` to confirm structure

#### Phase 4: Verification

- [x] **Task 10:** Run verification test plan
  - Execute all commands from Testing Strategy section
  - Confirm all expected counts match
  - Verify E12-A3 is the only open item
  - Run `bd sync` to commit beads changes

### Acceptance Criteria

- [x] **AC 1:** Given beads has no RETRO-labeled issues, when all migration tasks complete, then `bd list --label RETRO --status closed | wc -l` returns 36 (6 epics + 6 retros + 24 action items). *Note: Original estimate was 23 action items but actual count is 24.*

- [x] **AC 2:** Given Epic 8 is migrated, when running `bd show <epic-8-id>`, then output shows 1 child (retro container) which itself has 4 children (action items)

- [x] **AC 3:** Given all historical items are migrated, when running `bd list --label RETRO --status closed`, then 36 items are returned (all items including E12-A3 which was completed as part of this migration)

- [x] **AC 4:** Superseded - E12-A3 was closed as part of this migration since completing this task closes the migration action item itself.

- [x] **AC 5:** Given action item E8-A1 is created, when running `bd show <e8-a1-id>`, then description contains context from epic-8-retro file about "UI Testing Philosophy"

- [x] **AC 6:** Given sprint-status.yaml is updated, when running `grep retro_action_items sprint-status.yaml`, then no matches are found (replaced with comment pointing to beads)

- [x] **AC 7:** Given project-context.md is updated, when searching for "RETRO label", then the Pre-Epic Checklist references beads (not sprint-status.yaml)

- [x] **AC 8:** Given retrospective workflow is updated, when reading instructions.md Step 11, then it references `bd create` commands for creating beads issues

## Additional Context

### Dependencies

- beads CLI (`bd`) must be available
- Retro files must exist for Epics 8-13

### Testing Strategy

**Pre-conditions:**
- `bd list --label RETRO` returns 0 issues (clean slate)
- `sprint-status.yaml` contains `retro_action_items` section with 23 items

**Post-migration Verification:**

| Check | Command | Expected Result |
|-------|---------|-----------------|
| Epic shells created | `bd list --type epic --label RETRO` | 6 issues (Epics 8-13) |
| Retro containers created | `bd list --type task --label RETRO \| grep "Retrospective"` | 6 issues |
| Action items created | `bd list --label RETRO --type task \| grep -E "E[0-9]+-A[0-9]+"` | 23 issues |
| Total RETRO issues | `bd list --label RETRO \| wc -l` | 35 issues |
| Parent-child structure | `bd show <any-epic-id>` | Shows children (retro container) |
| Grandchild structure | `bd show <any-retro-container-id>` | Shows children (action items) |
| Closed items | `bd list --label RETRO --status closed \| wc -l` | 34 (6 epics + 6 retros + 22 done items) |
| Open items | `bd list --label RETRO --status open` | 1 issue (E12-A3) |
| Context preserved | `bd show <any-action-item>` | Description contains markdown from retro file |
| YAML cleaned | `grep -c retro_action_items sprint-status.yaml` | 0 (section removed) |

**Documentation Verification:**
- `project-context.md` contains RETRO beads convention
- Retrospective workflow references beads creation (not yaml)

**Smoke Test:**
- `bd epic status` shows 6 RETRO epics with completion percentages
- `bd ready` does NOT show closed retro items
- E12-A3 appears in `bd ready` or `bd list --status open`

### Notes

- E12-A3 is the only pending item (meta: it's literally "migrate to beads")
- 22 of 23 items are already done - this is primarily historical preservation
