---
title: 'Beads Integration for Polish Backlog'
slug: 'beads-polish-backlog-integration'
created: '2026-01-17'
status: 'completed'
stepsCompleted: [1, 2, 3, 4]
tech_stack:
  - beads (bd CLI)
  - JSONL storage (.beads/issues.jsonl)
  - Git hooks (SessionStart/PreCompact via bd setup claude)
files_to_modify:
  - CLAUDE.md (lines 43-56)
  - project-context.md (lines 705, 731, 742, 751-752, 798-799, 811)
  - Justfile (lines 266-281, remove polish recipe)
  - scripts/polish-backlog.sh (DELETE)
  - .claude/skills/polish-backlog/SKILL.md (REPLACE with beads skill)
files_to_create:
  - .claude/skills/beads/SKILL.md
  - .beads/ (created by bd init)
code_patterns:
  - bd CLI commands with --json flag for programmatic access
  - Labels for categorization (UI, API, INFRA, TOOLS, CICD)
  - Labels for effort sizing (size-s, size-m, size-l)
  - Priority mapping (high=0, medium=1, low=2)
  - ID convention: [UI-029] prefix in issue title
  - Skill allowed-tools: Bash(bd:*)
test_patterns:
  - Manual verification of bd commands
  - Item count comparison post-migration
  - Skill invocation testing
---

# Tech-Spec: Beads Integration for Polish Backlog

**Created:** 2026-01-17

## Overview

### Problem Statement

Editing the markdown-based `polish-backlog.md` produces inconsistent results due to table formatting fragility. The markdown table structure is easily broken by direct text editing, requiring wrapper scripts (`scripts/polish-backlog.sh`) and special handling for macOS Bash version differences. AI agents struggle with structured markdown table manipulation, leading to formatting errors and merge conflicts.

### Solution

Replace the markdown-based polish backlog with the beads CLI issue tracker. Beads stores issues as JSONL in a `.beads/` directory, provides CLI commands for all operations, outputs JSON for programmatic access, and integrates natively with Git. This eliminates table formatting issues and provides a robust, AI-agent-friendly issue tracking system.

### Scope

**In Scope:**
- Install and configure beads CLI (`bd init`, `bd setup claude`)
- Create new `.claude/skills/beads/SKILL.md` skill
- Define conventions for IDs, categories, effort, and priority
- Migrate existing ~40 active polish backlog items
- Migrate archived items as closed issues
- Update CLAUDE.md with beads workflow instructions
- Update project-context.md references
- Remove old infrastructure (script, Justfile recipe, old skill)

**Out of Scope:**
- Sprint-status tracking replacement (would require deep BMAD modifications)
- Beads MCP server setup (CLI + hooks sufficient for this use case)
- Beads plugin installation (optional enhancement, not required)
- Beads TUI viewer (Beads Viewer) installation

## Context for Development

### Codebase Patterns

**Current polish backlog workflow:**
- `just polish <command>` wraps `scripts/polish-backlog.sh`
- Script requires Bash 4+ (macOS compatibility handled in Justfile)
- Items have: ID (UI-029), Description, Priority, Effort, Status, Related, Notes
- Categories are table sections: UI, API, Infrastructure, Tools, CI/CD
- Archive section tracks completed items with PR links

**Beads workflow (target):**
- `bd create "[UI-NNN] Description" -t task -p 1 -l UI,size-m`
- `bd update <id> --status in_progress`
- `bd close <id> --reason "PR: https://..."`
- `bd list --label API --status open --json`
- `bd ready` shows unblocked tasks
- All data stored in `.beads/issues.jsonl` (committed to Git)

### Files to Reference

| File | Purpose | Action |
| ---- | ------- | ------ |
| `.claude/skills/polish-backlog/SKILL.md` | Current skill (172 lines) | REPLACE with beads skill |
| `scripts/polish-backlog.sh` | Current script (466 lines) | DELETE |
| `Justfile` (lines 266-281) | `polish` recipe | REMOVE recipe |
| `CLAUDE.md` (lines 43-56) | Polish backlog docs | UPDATE to beads workflow |
| `project-context.md` | 6 references to polish-backlog | UPDATE all references |
| `_bmad-output/implementation-artifacts/polish-backlog.md` | ~40 active + ~25 archived items | MIGRATE then archive |

**BMAD files - No changes needed** (use "polish" generically):
- `_bmad/bmm/workflows/4-implementation/create-story/template-api-spike.md`
- `_bmad/bmm/workflows/3-solutioning/check-implementation-readiness/steps/step-06-final-assessment.md`
- `_bmad/bmm/testarch/knowledge/test-priorities-matrix.md`
- 4 files in `_bmad/bmb/` (legacy workflows)

### Technical Decisions

**Convention Mappings:**

| Aspect | Current System | Beads Convention |
|--------|---------------|------------------|
| ID Format | `UI-029`, `API-003` | Title prefix: `[UI-029] Description` |
| Categories | Table sections | Labels: `UI`, `API`, `INFRA`, `TOOLS`, `CICD` |
| Effort | Column: S/M/L | Labels: `size-s`, `size-m`, `size-l` |
| Priority | Column: high/medium/low | Numeric: `0`=high, `1`=medium, `2`=low |
| Status | backlog/in-progress/done | open/in_progress/closed |
| Related | Column with Epic/Story ref | In description or as dependency |
| Notes | Column | In description body |
| PR Links | Archive table | Close reason: `--reason "PR: https://..."` |

**Beads Setup:**
- Use `bd setup claude` for SessionStart/PreCompact hooks
- Hooks provide ~1-2k tokens of workflow context automatically
- `.beads/issues.jsonl` committed alongside code

## Implementation Plan

### Tasks

#### Task 1: Install and Configure Beads
- **Files**: `.beads/` (created), `.claude/hooks/` (if hooks added)
- **Actions**:
  1. Install beads CLI: `brew tap steveyegge/beads && brew install bd`
  2. Initialize beads in project root: `bd init --quiet`
  3. Configure Claude Code hooks: `bd setup claude`
  4. Verify setup: `bd setup claude --check`
  5. Add `.beads/` directory to git: `git add .beads/`
  6. Create test issue to verify workflow: `bd create "[TEST-001] Verify beads setup" -t task -p 2 -l TOOLS,size-s`
  7. Close test issue: `bd close <id> --reason "Setup verification complete"`
- **Notes**: This task establishes the beads infrastructure. All subsequent tasks depend on this.

#### Task 2: Create Beads Skill
- **File**: `.claude/skills/beads/SKILL.md` (CREATE)
- **Actions**:
  1. Create directory: `.claude/skills/beads/`
  2. Write `SKILL.md` with:
     - Frontmatter: `name: beads`, `description`, `allowed-tools: Bash(bd:*)`
     - Section: "IMPORTANT: Never Edit .beads/ Directly"
     - Section: Quick Reference with `bd` command examples
     - Section: Convention mappings (IDs, categories, effort, priority)
     - Section: Common Workflows (discovering issues, starting work, completing items)
     - Section: Valid Values (categories, priorities, effort labels)
- **Template Reference**: Model after current `.claude/skills/polish-backlog/SKILL.md` structure
- **Notes**: Skill must be complete before migration so workflow is documented.

#### Task 3: Migrate Polish Backlog Items
- **Files**: `_bmad-output/implementation-artifacts/polish-backlog.md` (READ), `.beads/issues.jsonl` (WRITE via bd)
- **Actions**:
  1. Count active items in polish-backlog.md (expect ~40)
  2. Count archived items (expect ~25)
  3. Write simple migration script (Python or jq) that parses markdown tables and outputs `bd create` commands
  4. **Execute migration in one sitting** (per Barry's advice - avoid split-brain)
  5. For each active item, run: `bd create "[ID] Description" -t task -p N -l CATEGORY,size-X`
  6. For each archived item, run: `bd create ... && bd close <id> --reason "PR: <url> | Completed: <date>"`
  7. Verify counts match: `bd list --json | jq length` should equal source counts
  8. Commit `.beads/issues.jsonl`: `git add .beads/ && git commit -m "feat: migrate polish backlog to beads"`
- **Notes**: Migration script should be disposable - run once, verify, delete script.

#### Task 4: Update Documentation and Remove Old Infrastructure
- **Files**:
  - `CLAUDE.md` (lines 43-56) - UPDATE
  - `project-context.md` (6 locations) - UPDATE
  - `Justfile` (lines 266-281) - REMOVE
  - `scripts/polish-backlog.sh` - DELETE
  - `.claude/skills/polish-backlog/` - DELETE directory
- **Actions**:
  1. **CLAUDE.md**: Replace "Polish Backlog" section (lines 43-56) with "Issue Tracking (Beads)" section documenting `bd` commands
  2. **project-context.md**: Update all 6 references:
     - Line 705: Update comment placeholder
     - Line 731: Change `polish-backlog.md` to beads workflow
     - Line 742: Update "polish backlog item" reference
     - Lines 751-752: Update workflow diagram
     - Lines 798-799: Rename section, update file reference
     - Line 811: Update "polish items" reference
  3. **Justfile**: Remove lines 266-281 (the `polish` recipe)
  4. **scripts/polish-backlog.sh**: Delete file
  5. **`.claude/skills/polish-backlog/`**: Delete entire directory
  6. **Verify no orphans**: Run `grep -r "polish-backlog" .` to confirm no remaining references
  7. Rename `polish-backlog.md` to `polish-backlog.md.archived` (preserve history)
  8. Commit all changes: `git commit -m "feat: complete beads migration, remove polish-backlog infrastructure"`
- **Notes**: Do cleanup in single commit for clean git history.

### Acceptance Criteria

- [x] **AC1**: Given beads is not installed, when I run `brew tap steveyegge/beads && brew install bd`, then `bd --version` returns a valid version string. ✅ v0.47.1

- [x] **AC2**: Given beads is installed, when I run `bd init --quiet` in project root, then `.beads/` directory is created with initial database files. ✅

- [x] **AC3**: Given beads is initialized, when I run `bd setup claude`, then Claude Code hooks are configured and `bd setup claude --check` passes. ✅

- [x] **AC4**: Given the beads skill exists at `.claude/skills/beads/SKILL.md`, when I invoke the skill, then I can run `bd` commands with `allowed-tools: Bash(bd:*)` permission. ✅

- [x] **AC5**: Given ~40 active items exist in `polish-backlog.md`, when migration completes, then `bd list --status open --json | jq length` equals the active item count. ✅ 47 open

- [x] **AC6**: Given ~25 archived items exist in `polish-backlog.md`, when migration completes, then `bd list --status closed --json | jq length` equals the archived item count. ✅ 24 closed (22 archived + 2 test)

- [x] **AC7**: Given a migrated item `[UI-029]`, when I run `bd list --json | jq '.[] | select(.title | contains("[UI-029]"))'`, then the item is found with correct labels (category, effort) and priority. ✅ Verified

- [x] **AC8**: Given migration is complete, when I run `bd create "[UI-999] Test item" -t task -p 1 -l UI,size-s`, then the item is created and appears in `bd ready`. ✅

- [x] **AC9**: Given CLAUDE.md is updated, when I search for "polish", then the only reference is historical context, not active instructions. ✅

- [x] **AC10**: Given cleanup is complete, when I run `grep -r "polish-backlog.sh\|just polish" .`, then no matches are found (excluding archived files and git history). ✅

## Additional Context

### Dependencies

- **External**:
  - beads CLI (`bd`) - Install via Homebrew, npm, or Go
  - `jq` (optional) - For JSON parsing during migration verification
- **Internal**:
  - No code dependencies
  - No API changes required
  - No test infrastructure changes

### Testing Strategy

**Manual Verification (Task 1):**
- Run `bd --version` to confirm installation
- Run `bd setup claude --check` to verify hooks
- Create and close a test issue to verify full workflow

**Migration Verification (Task 3):**
- Count items before: `grep -c "^\|.*\|$" polish-backlog.md` (approximate)
- Count items after: `bd list --json | jq length`
- Spot-check 3-5 items for correct field mapping

**Skill Verification (Task 2):**
- Invoke skill and run sample commands
- Verify `allowed-tools` permits `bd` commands

**Cleanup Verification (Task 4):**
- `grep -r "polish-backlog" .` returns no active references
- `ls scripts/polish-backlog.sh` returns "No such file"
- `ls .claude/skills/polish-backlog/` returns "No such file or directory"

### Notes

**Risk Assessment:**
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Migration data loss | Low | High | Verify counts, keep polish-backlog.md.archived |
| Beads CLI breaking change | Low | Medium | Pin version in docs, JSONL is recoverable |
| Skill permissions too broad | Low | Low | `Bash(bd:*)` is scoped to beads only |

**Future Considerations (Out of Scope):**
- Beads plugin for slash commands (`/beads:ready`, etc.)
- Beads TUI viewer for browsing issues
- Integration with sprint-status.yaml tracking
- Beads MCP server for non-CLI environments

**Beads Installation Options:**
```bash
# Homebrew (recommended for macOS)
brew tap steveyegge/beads && brew install bd

# npm
npm install -g @beads/bd

# Go (requires Go 1.24+)
go install github.com/steveyegge/beads/cmd/bd@latest
```

**Key Beads Commands for Skill:**
```bash
bd ready --json                              # Unblocked tasks
bd create "[ID] desc" -t task -p N -l X,Y    # Create issue
bd update <id> --status in_progress          # Update status
bd close <id> --reason "PR: url"             # Close with PR link
bd list --label API --status open --json     # Filter and list
bd label add <id> size-m                     # Add effort label
bd show <id> --json                          # Show details
```

---

## Review Notes

- Adversarial review completed
- Findings: 6 total, 5 fixed, 1 skipped (undecided)
- Resolution approach: auto-fix

**Fixed findings:**
- F1: Data migration verified (47 open + 24 closed)
- F2: Migration notes added to SKILL.md
- F4: ID format documentation clarified
- F5: Stale permissions removed from .claude/settings*.json
- F6: Gitignore documentation expanded

**Skipped finding:**
- F3: `allowed-tools: Bash(bd:*)` pattern validity (undecided - works in practice)

## Party Mode Insights (2026-01-17)

**From Winston (Architect):**
- Beads is a good "boring technology" choice - Git-native, simple JSONL storage
- Consider pinning beads version and documenting schema for future-proofing

**From Barry (Quick Flow Solo Dev):** ✅ ACCEPTED
- Migration script should be simple (jq/Python one-liner) - no framework
- **Do migration in one sitting** to avoid split-brain with new items during migration

**From Amelia (Dev):** ✅ ACCEPTED
- Skill `allowed-tools` directive confirmed: `Bash(bd:*)`
- Simpler and sufficient for all beads operations

**From Bob (Scrum Master):** ✅ ACCEPTED
- Add to cleanup task: `grep -r "polish" _bmad/` to find ALL references
- Ensure no orphaned documentation references
