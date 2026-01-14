# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## Technology Stack & Versions

| Component | Version | Notes |
|-----------|---------|-------|
| Python | >= 3.12 | Use minimum version, not exact pin |
| FastAPI | 0.127.1+ | Includes Uvicorn via `fastapi[standard]` |
| React | 19.2 | Security-patched version |
| TypeScript | 5.x | Strict mode enabled |
| Bun | 1.3.5 | Frontend runtime and package manager |
| uv | 0.9.18+ | Python package management |
| Tailwind CSS | v4 | CSS variables approach |
| TanStack Query | v5 | Server state management |
| structlog | latest | Structured logging |

**Base Container:** `mcr.microsoft.com/dotnet/runtime:8.0.22-noble-amd64`
- Ubuntu 24.04 Noble with .NET 8 (required for VintageStory server)
- Python 3.12 available via apt

---

## Available MCPs for Agents

All agents have access to three Model Context Protocol (MCP) tools for enhanced capabilities:

### 1. Playwright (Browser Automation)
**Purpose:** Real-world testing, UI validation, and browser automation

**When to use:**
- Testing the web UI end-to-end
- Validating user flows across multiple pages
- Capturing screenshots for documentation
- Debugging frontend issues in a real browser environment
- Verifying responsive behavior

**Key capabilities:**
- Navigate to URLs and interact with pages
- Fill forms, click buttons, and test UI components
- Take screenshots and accessibility snapshots
- Monitor console messages and network requests
- Test across different viewport sizes

**Best practices:**
- Use accessibility snapshots over screenshots when testing UI structure
- Clean up browser sessions after testing
- Use meaningful element descriptions when interacting with the page

### 2. GitHub Code Search (`grep_searchGitHub`)
**Purpose:** Find real-world code examples from public GitHub repositories

**When to use:**
- Learning how to use unfamiliar APIs or libraries
- Finding production-ready examples and best practices
- Understanding how others integrate similar technologies
- Looking for patterns in real codebases (not tutorials)

**Key capabilities:**
- Search for literal code patterns (not keywords)
- Filter by language, repository, or file path
- Support for regex patterns for flexible matching
- Access to over 1 million public repositories

**Best practices:**
- Search for actual code patterns, not natural language queries
- Use language filters to narrow results
- Look for well-maintained repositories with good documentation
- Examples: `'useState('`, `'from("fastapi")'`, `'export function'`

### 3. Context7 (Smart Documentation Search)
**Purpose:** Access up-to-date documentation for popular libraries and frameworks

**When to use:**
- Looking up API references and code examples
- Understanding library configuration options
- Finding best practices for specific technologies
- Getting conceptual guides and architectural information

**Available datasources include:**
- **Frontend:** React, Next.js, Tailwind CSS, shadcn/ui, TanStack Query
- **Backend:** FastAPI, Python web frameworks
- **Build tools:** Vite, esbuild, webpack
- **Testing:** Vitest, Playwright, Testing Library
- **And many more** - resolve library IDs dynamically

**Best practices:**
- Be specific in your query - include what you're trying to accomplish
- Resolve library ID first, then query with detailed questions
- Use the same query for both resolve and query calls for best relevance

**Example workflow:**
```python
# Step 1: Resolve the library ID
mcp__context7__resolve-library-id(
    libraryName="fastapi",
    query="How to add middleware to FastAPI"
)

# Step 2: Query documentation
mcp__context7__query-docs(
    libraryId="/tiangolo/fastapi",
    query="How to add middleware to FastAPI"
)
```

**Key advantages:**
- Always up-to-date documentation (unlike cached search results)
- Optimized for LLM consumption with clean context
- Requires resolving library ID first, then querying with specific questions

---

## Critical Implementation Rules

### 1. Tests Must Accompany Implementation

**Every task that adds functionality must include its tests before marking complete.**

This is non-negotiable. Tests are not a separate phase - they are part of implementation.

**Pattern to follow:**
```
Task 1: Implement feature A + tests
Task 2: Implement feature B + tests
```

**Anti-pattern to avoid:**
```
Task 1: Implement feature A
Task 2: Implement feature B
Task 3: Write tests  <- TOO LATE
```

**Why:** Code review should verify implementation quality, not discover missing tests. Tests written alongside code catch design issues early.

### 2. Testing Discipline is Non-Negotiable

> **Rule:** Every test must pass, all the time. No exceptions without explicit user confirmation.

**FAILING TESTS ARE UNACCEPTABLE UNDER ANY CIRCUMSTANCE EXCEPT RED TESTING.**

This applies to:

- Tests you wrote as part of the current task, except for red testing.
- Pre-existing tests that were passing before your changes
- Tests in any part of the codebase, not just files you modified

Do not mark a task as complete if:

- Tests are failing (ANY tests, not just new ones)
- Implementation is partial
- You encountered unresolved errors
- Test coverage for the new functionality is missing

**Critical:**
- Manual test tasks require **explicit user confirmation** before marking complete
- Never auto-complete manual testing tasks
- Deferring or excluding failing tests is a **grievous error in judgment**
- If you think excluding a test is appropriate, stop and ask the user first
- **If tests fail, you MUST investigate and fix them** - do not proceed with other work
- **User confirmation is REQUIRED to accept any failing test** - never assume failures are acceptable

### 3. API Response Envelope

All API endpoints must use the standard envelope:

```python
# Success
{"status": "ok", "data": {...}}

# Error (FastAPI Standard)
{"detail": {"code": "ERROR_CODE", "message": "Human readable"}}
```

**Note:** Error responses follow FastAPI's standard `detail` pattern for HTTPExceptions.
This avoids requiring custom exception handlers. The `detail` field contains structured
error data with `code` and `message` fields, providing the same information
as a custom envelope would.

### 4. JSON Field Naming Boundary

- **API (Python):** snake_case
- **Frontend (TypeScript):** camelCase
- **Transform at:** API client boundary only (`web/src/api/client.ts`)

### 5. State Management Boundaries

| State Type | Tool | Examples |
|------------|------|----------|
| Server state (from API) | TanStack Query | mods, server status, config |
| UI-only state | React Context | theme, sidebar collapsed |

**Never mix these.** If data comes from the API, use TanStack Query.

### 6. Atomic File Writes

All state persistence must use the temp-file-then-rename pattern:

```python
temp = path.with_suffix('.tmp')
temp.write_text(content)
temp.rename(path)  # atomic on POSIX
```

This prevents corruption if the process crashes mid-write.

### 7. Version Specifications in Architecture

When documenting or requiring versions:
- **Use minimum versions** (e.g., `Python >= 3.12`) unless there's a specific reason to pin
- **Document rationale** for any exact version pins
- **Consider external dependencies** when specifying infrastructure (e.g., VintageStory requires .NET)

### 8. No Silent Failures Rule

**Code Suppressions Require Justification and Tracking** (Epic 5/6 Retrospective Enforcement)

Code suppressions hide real issues instead of fixing them. They are **forbidden** unless ALL requirements are met:

1. **Inline comment** explaining WHY suppression is necessary (not just "fixing build")
2. **Tracking issue** linked (GitHub issue, backlog item) for proper fix
3. **Explicit approval** in code review

**Forbidden Patterns Without Justification:**
- `// eslint-disable`
- `@ts-ignore` / `@ts-expect-error`
- `pytest.skip` / `pytest.mark.xfail`
- `# noqa` / `# type: ignore`

**Good Example:**
```typescript
// eslint-disable-next-line @typescript-eslint/no-explicit-any
// TODO(#123): Remove when API types are available from upstream
const data: any = await fetchThirdPartyAPI();
```

**Bad Example:**
```typescript
// @ts-ignore - fixing build
const data = await fetchThirdPartyAPI();
```

**Enforcement:**
- `code-review` workflow scans for undocumented suppressions and auto-rejects PR
- Zero tolerance policy for HIGH severity findings (undocumented suppressions)

**Why This Matters (from Epic 6):**
- Suppressions accumulate as technical debt
- They hide real problems instead of fixing them
- Epic 6 found `eslint-disable` in TerminalView.tsx with no justification
- Make suppressions painful to add so we fix root causes instead

### 9. Story Sizing Guidelines

**Maximum Story Size: 4-6 Tasks** (Epic 5/6 Retrospective Enforcement)

Stories with more than 6 tasks should be split into multiple stories. Large stories cause:
- Context compaction issues (documentation gaps)
- Harder code review (mega-PRs)
- Reduced granularity for progress tracking

**How to Split Stories:**
- Each story should accomplish ONE user-facing capability
- Group related tasks (e.g., "API hooks + components", "Page layouts", "Settings panels")
- Better to have 3 focused PRs than 1 mega-PR

**Enforcement:**
- `create-story` workflow validates task count and warns if >6 tasks
- User must explicitly approve proceeding with large stories

**Example - Story Too Large:**
- ❌ Story 6.4: Settings UI (10 tasks - hooks, components, pages, routing, tabs)
- Impact: Context compaction caused empty File List in Story 6.5

**Example - Proper Split:**
- ✅ Story 6.4a: Game Settings Hooks & Components (4 tasks)
- ✅ Story 6.4b: Game Server Page (3 tasks)
- ✅ Story 6.4c: API Settings Interface (3 tasks)

---

## Security Patterns

These patterns were established in Epic 2 and must be followed for all security-related code.

### 1. DEBUG Mode Gating for Test Endpoints

Test or development-only endpoints MUST be gated behind `VS_DEBUG=true`:

```python
from vintagestory_api.config import get_settings

settings = get_settings()
if settings.debug:
    app.include_router(test_router, prefix="/api/v1alpha1")
```

**Why:** Prevents test endpoints from being exposed in production.

### 2. Timing-Safe API Key Comparison

Always use `secrets.compare_digest` for API key validation:

```python
import secrets

def verify_key(provided: str, expected: str) -> bool:
    return secrets.compare_digest(provided.encode(), expected.encode())
```

**Why:** Prevents timing attacks that could leak information about valid keys.

### 3. Never Log Sensitive Data

API keys, passwords, and tokens must NEVER appear in logs:

```python
# WRONG - logs the actual key
logger.warning(f"Invalid API key: {api_key}")

# CORRECT - logs metadata only
logger.warning("Invalid API key attempt",
    extra={"ip": client_ip, "key_prefix": api_key[:8] + "..."})
```

### 4. Proxy-Aware Client IP Logging

When logging client IPs (e.g., for failed auth), check proxy headers:

```python
def get_client_ip(request: Request) -> str:
    """Get real client IP, accounting for reverse proxies."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    return request.client.host if request.client else "unknown"
```

### 5. Role-Based Access Control Pattern

Use FastAPI dependency injection for role checks:

```python
from vintagestory_api.middleware.auth import get_current_user
from vintagestory_api.middleware.permissions import require_admin

# Read endpoint - any authenticated user
@router.get("/data")
async def get_data(role: str = Depends(get_current_user)):
    pass

# Write endpoint - Admin only
@router.post("/data")
async def create_data(role: str = Depends(require_admin)):
    pass
```

---

## Logging Conventions

### Configuration

Logging is configured via environment variables:
- `VS_DEBUG=true` - Enable debug mode (colorful console output)
- `VS_LOG_LEVEL` - Override log level (DEBUG, INFO, WARNING, ERROR)

Default behavior:
- **Dev mode** (`VS_DEBUG=true`): DEBUG level, colorful ConsoleRenderer
- **Prod mode** (`VS_DEBUG=false`): INFO level, JSON output for machine parsing

### Standards

1. **Always use ISO 8601 timestamps** - Configured automatically by structlog
2. **Use structured logging** - Key=value pairs, not string interpolation:

```python
# CORRECT - structured key=value
logger.info("server_starting", version="1.19.8", port=8080)

# WRONG - string interpolation
logger.info(f"Server version {version} starting on port {port}")
```

3. **Use event names as first argument** - Lowercase with underscores:
   - `api_starting`, `server_stopped`, `download_complete`

4. **Never log sensitive data**:
```python
# WRONG
logger.warning(f"Auth failed for key: {api_key}")

# CORRECT
logger.warning("auth_failed", key_prefix=api_key[:8] + "...")
```

5. **Log levels**:
   - `DEBUG` - Detailed diagnostic info (dev only)
   - `INFO` - Normal operations (startup, shutdown, requests)
   - `WARNING` - Recoverable issues (timeouts, retries)
   - `ERROR` - Failures requiring attention

---

## Code Review Checklist

Before marking a task complete, verify:

- [ ] Tests written alongside implementation (not batched at end)
- [ ] All tests passing
- [ ] Security patterns applied (DEBUG gating, timing-safe comparison, no sensitive logging)
- [ ] Error responses use standard envelope format
- [ ] No hardcoded secrets or credentials

---

## Code Patterns

### Backend (Python)

**File naming:** snake_case (`mod_service.py`)
**Classes:** PascalCase (`ModService`)
**Functions/variables:** snake_case (`get_mod_details()`)
**Constants:** SCREAMING_SNAKE (`MAX_RETRIES`)

**Error handling:**
```python
from vintagestory_api.models.errors import ErrorCode

raise HTTPException(
    status_code=404,
    detail={
        "code": ErrorCode.MOD_NOT_FOUND,
        "message": f"Mod '{slug}' not found",
    }
)
```

### Frontend (TypeScript)

**File naming:** kebab-case (`mod-card.tsx`)
**Components:** PascalCase (`ModCard`)
**Hooks:** camelCase with `use` prefix (`useServerStatus`)
**Booleans:** always `is` prefix (`isLoading`, `isConnected`)

**Query keys:**
```typescript
const queryKeys = {
  mods: {
    all: ["mods"] as const,
    detail: (slug: string) => ["mods", slug] as const,
  },
};
```

---

## Anti-Patterns to Avoid

| Avoid | Do Instead |
|-------|------------|
| Writing tests after all features complete | Write tests with each feature |
| Storing API data in React Context | Use TanStack Query |
| Separate `tests/` folder for component tests | Co-locate tests with components (`*.test.tsx`) |
| Generic error messages | Use error codes + descriptive messages |
| Exact version pins without rationale | Use minimum versions with ranges |
| Mixing snake_case in frontend | Transform at API boundary |

---

## Project Structure Quick Reference

```
vintagestory-server/
├── api/                    # FastAPI backend
│   ├── src/vintagestory_api/
│   │   ├── routers/        # HTTP endpoints
│   │   ├── services/       # Business logic
│   │   ├── models/         # Pydantic models
│   │   └── middleware/     # Auth, etc.
│   └── tests/              # Backend tests
├── web/                    # React frontend
│   └── src/
│       ├── api/            # API client
│       ├── components/     # UI components
│       ├── features/       # Feature modules
│       ├── hooks/          # Custom hooks
│       └── contexts/       # UI state contexts
├── Dockerfile              # Multi-stage build
└── docker-compose.yaml     # Deployment
```

---

## Development Commands

**ALWAYS use `just` commands. NEVER use raw `mise exec` commands.**

All recipes accept optional arguments for flexibility:

```bash
# Testing - ALWAYS use just for tests
just test                                # Run all tests (api + web)
just test-api                            # Run all API tests
just test-api -k "restart"               # Run tests matching pattern
just test-api tests/test_server.py -xvs  # Run specific file, verbose
just test-web                            # Run all web tests

# Validation
just check                               # Full validation (lint + typecheck + test)
just lint                                # Run all linters
just lint-api --fix                      # Lint with auto-fix
just typecheck                           # Run all type checks

# Development
just dev-api                             # Start API dev server
just dev-api --port 8001                 # Dev server on custom port
just dev-web                             # Start web dev server
just install                             # Install all dependencies
just format                              # Format all code
```

Run `just` with no arguments to see all available commands.

**Why:** Prevents tooling confusion (e.g., `bun test` vs `bun run test`). All commands use correct tool versions via mise. Variadic args enable specific test file/pattern targeting without bypassing `just`.

---

## Git Workflow

### Branch Strategy

Each story gets its own branch. Branch names align with story filenames:

```bash
# Branch naming: story/<epic>-<story>-<slug>
git checkout -b story/5-2-mod-installation-api
git checkout -b story/6-1-config-files-api
```

**Flow:**
```
main (stable)
    │
    └── git checkout -b story/5-2-mod-installation-api
            │
            ├── feat(story-5.2/task-1): create ModApiClient
            ├── feat(story-5.2/task-2): implement install_mod
            ├── feat(story-5.2/task-3): add API endpoint + tests
            │
            └── Push branch, create PR
                    │
                    ├── Code review on PR
                    ├── fix(story-5.2/review): address findings
                    │
                    └── Regular merge to main (not squash)
```

### Commit Message Format

Task-level commits using slash notation:

```
type(story-X.Y/task-N): description
```

**Types:**
- `feat` - New functionality
- `fix` - Bug fixes
- `test` - Test-only changes
- `docs` - Documentation
- `refactor` - Code restructuring

**Standard suffixes:**
- `/task-N` - Work directly tied to task N
- `/ad-hoc` - Discovered issues fixed opportunistically
- `/user` - User-directed changes during story execution
- `/review` - Code review findings

**Examples:**
```bash
git commit -m "feat(story-5.2/task-1): create ModApiClient with httpx"
git commit -m "feat(story-5.2/task-2): implement install_mod method + tests"
git commit -m "fix(story-5.2/ad-hoc): correct typo in error message"
git commit -m "fix(story-5.2/user): handle edge case per user feedback"
git commit -m "fix(story-5.2/review): address code review findings"
```

### Commit Discipline

**Task-Level Commits Are Mandatory** (Epic 5/6 Retrospective Enforcement)

Every completed task MUST have a corresponding git commit before marking the task complete in the story file.

**Why This Matters:**
- Enables task-level verification (git bisect)
- Creates audit trail for code review
- Prevents "big bang" commits that are hard to review
- Documents incremental progress for retrospectives

**Enforcement:**
- The `dev-story` workflow verifies commit exists with correct format before allowing task completion
- Tasks cannot be marked complete without a proper commit
- Commit message MUST match pattern: `feat(story-X.Y/task-N): description`

**Pattern from Violations:**
- ❌ Story 6.1: Single commit for all 3 tasks → Hard to review, no granularity
- ✅ Expected: 3 commits (task-1, task-2, task-3) → Clear progress, reviewable chunks

**How the Enforcement Works:**
```xml
<check if="commit missing or format incorrect">
  <action>ERROR: Task cannot be marked complete without proper git commit</action>
  <action>Create commit NOW with correct format before proceeding</action>
</check>
```

### Code Review Process

**CRITICAL: Code review MUST start with checking for an existing Pull Request.**

When beginning a code review for a story:

1. **Check for existing PR first:**
   ```bash
   gh pr list --head story/<epic>-<story>-<slug>
   ```

2. **If PR exists:**
   - Review code directly on PR (GitHub web UI or via `gh pr view/diff`)
   - Use PR commits, not uncommitted changes
   - Review changes against `main` branch

3. **If PR does NOT exist:**
   - Create PR first using the PR template below
   - Then proceed with code review
   - **NEVER review code on branch without PR**

4. **Review on PR, not local files:**
   - Use `gh pr diff` to see cumulative changes vs main
   - Use `gh pr view` to see PR details and commits
   - Review test results from CI/CD if available
   - Verify PR body matches story acceptance criteria

**Why PR-First Review:**
- PR provides full commit history context
- PR shows all changes vs main in one place
- PR comments become permanent review record
- CI/CD results are tied to PR
- Review on uncommitted files misses context

### Pull Request Process

1. **Push branch when implementation complete:**
   ```bash
   git push -u origin story/5-2-mod-installation-api
   ```

2. **Create PR with template:**
   ```bash
   gh pr create --title "Story 5.2: Mod Installation API" --body "..."
   ```

3. **Code review happens on PR** (not on uncommitted changes)

4. **Review fixes committed to branch:**
   ```bash
   git commit -m "fix(story-5.2/review): address code review findings"
   git push
   ```

5. **Regular merge (not squash)** - Preserves task-level history

6. **Delete story branch after merge**

### PR Template

```markdown
## Story Reference
- Story: [5-2-mod-installation-api](_bmad-output/implementation-artifacts/5-2-mod-installation-api.md)
- Epic: 5 - Mod Management

## Summary
<!-- 1-3 bullet points of what was implemented -->

## Changes
<!-- Key files modified/created -->

## Test Results
- [ ] `just check` passes
- [ ] Manual tests completed (if applicable)

## Acceptance Criteria Status
- [x] AC 1: ...
- [x] AC 2: ...

## Deferred Items
<!-- Any polish backlog items added -->

## Notes for Reviewers
<!-- Anything the reviewer should pay attention to -->
```

### Why This Workflow

1. **Transparency** - Task-level commits show exactly when each piece was implemented
2. **Verification** - Git history proves tests were written with features, not batched
3. **Isolation** - Story branches keep main stable during development
4. **Review integration** - Code review happens on PRs with full context
5. **Easy rollback** - Revert merge commit if something goes wrong
6. **Audit trail** - PR becomes permanent documentation of story completion

---

## Story Lifecycle

### Enhancement Story Process

**Discoveries during testing become new backlog items, not post-done commits.** (Epic 9 Retrospective Enforcement)

When testing reveals useful enhancements or edge cases:

1. **Do NOT add commits to completed stories** - Once a story is marked "done", its PR should be mergeable as-is
2. **Create a backlog item** - Add the enhancement to `polish-backlog.md` with appropriate category, priority, and effort
3. **If significant, create a new story** - Valuable enhancements that warrant their own PR should become a new story in the next epic

**Why This Matters:**
- Keeps PRs focused and reviewable
- Prevents scope creep that blurs definition of done
- Maintains clean git history with clear story boundaries
- Ensures proper testing and review for all changes

**Pattern from Violations:**
- ❌ Story 9.7 marked "done" before nested directory support added → Post-story commits after "done" status
- ✅ Expected: Nested directory support becomes polish backlog item or new story

**Workflow:**
```
During testing, discover enhancement opportunity
    │
    ├── Is it a bug fix for the current story?
    │   └── YES → Fix it now, before marking done
    │
    ├── Is it a small polish item?
    │   └── YES → Add to polish-backlog.md
    │
    └── Is it a significant new feature?
        └── YES → Create new story for next epic
```

---

## Pre-Epic Checklist

Before starting a new epic, verify the following:

### 1. Previous Retro Action Items (Required)
- [ ] Review `sprint-status.yaml` `retro_action_items` section
- [ ] Verify all action items from previous epic are either:
  - Completed and marked `done`
  - Explicitly deferred with documented reasoning
- [ ] Address any outstanding items before starting new work

### 2. Polish Backlog Review (Required)
- [ ] Review `polish-backlog.md` for items relevant to the new epic
- [ ] Decide for each relevant item: include in epic or explicitly defer
- [ ] Document decisions in epic kickoff notes or first story

### 3. Epic Kickoff Tasks
- [ ] Read epic definition and understand all stories
- [ ] Identify dependencies between stories
- [ ] Note any technical preparation needed (API research, architecture spikes)
- [ ] Update sprint-status.yaml to move epic to `in-progress` when first story starts

**Why This Matters:**
- Prevents action item accumulation across epics
- Ensures polish items don't get lost indefinitely
- Creates accountability for retrospective commitments
- Epic 9 retro found only 1/4 Epic 8 action items completed due to no visibility

---

## References

- Full architecture: `_bmad-output/planning-artifacts/architecture.md`
- Epic breakdown: `_bmad-output/planning-artifacts/epics.md`
- Sprint status: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- **VintageStory server troubleshooting:** `agentdocs/vs-server-troubleshooting.md` - Known quirks, path resolution issues, config file behaviors

---

_Last updated: 2026-01-14 (Strengthened testing discipline rule: failing tests are unacceptable, user confirmation required to accept failures)_
