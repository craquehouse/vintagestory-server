# Architecture Decision Document

> **This document has been split into smaller files for easier navigation and reduced context consumption.**

## Finding Architecture Information

The full architecture documentation is now organized in the [architecture/](architecture/) directory:

| File | Contents |
|------|----------|
| [index.md](architecture/index.md) | **Start here** - Table of contents with document frontmatter |
| [project-context-analysis.md](architecture/project-context-analysis.md) | Requirements overview, constraints, cross-cutting concerns |
| [starter-template-evaluation.md](architecture/starter-template-evaluation.md) | Technology selection rationale |
| [core-architectural-decisions.md](architecture/core-architectural-decisions.md) | Core ADRs (API framework, auth, state management, etc.) |
| [implementation-patterns-consistency-rules.md](architecture/implementation-patterns-consistency-rules.md) | Coding patterns, naming conventions, error handling |
| [project-structure-boundaries.md](architecture/project-structure-boundaries.md) | Directory structure, module boundaries |
| [architecture-validation-results.md](architecture/architecture-validation-results.md) | Validation checklist results |
| [architecture-completion-summary.md](architecture/architecture-completion-summary.md) | Summary of architectural decisions |
| [architecture-deviations-evolutions.md](architecture/architecture-deviations-evolutions.md) | Changes and pivots over time |

### Epic-Specific Architecture

| File | Contents |
|------|----------|
| [epic-5-mod-management-architecture.md](architecture/epic-5-mod-management-architecture.md) | Mod management patterns, caching, compatibility |
| [epic-6-game-configuration-management-architecture.md](architecture/epic-6-game-configuration-management-architecture.md) | Configuration via console commands, settings maps |
| [epic-7-8-apscheduler-integration-periodic-tasks.md](architecture/epic-7-8-apscheduler-integration-periodic-tasks.md) | Scheduler integration, periodic tasks |
| [epic-10-architecture-decisions.md](architecture/epic-10-architecture-decisions.md) | Mod browsing, hybrid filtering, URL state |
| [epic-12-dashboard-metrics.md](architecture/epic-12-dashboard-metrics.md) | Process metrics with psutil, Recharts charting, ring buffer storage |
| [epic-13-server-version-browser.md](architecture/epic-13-server-version-browser.md) | Version browser, UI reuse from Epic 10 |

## Quick Reference

- **Looking for coding patterns?** → [implementation-patterns-consistency-rules.md](architecture/implementation-patterns-consistency-rules.md)
- **Looking for project structure?** → [project-structure-boundaries.md](architecture/project-structure-boundaries.md)
- **Looking for a specific ADR?** → [core-architectural-decisions.md](architecture/core-architectural-decisions.md)
- **Working on a specific epic?** → See the epic-specific files above

## Original Document

The original monolithic architecture.md (130KB) is archived at [archive/architecture.md](archive/architecture.md) for reference.
