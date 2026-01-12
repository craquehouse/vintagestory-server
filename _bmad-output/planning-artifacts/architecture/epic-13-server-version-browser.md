# Epic 13: Server Version Browser Architecture

_Decisions made during Epic 13 (Server Version Browser) technical preparation._

## Overview

Epic 13 provides a UI for browsing and installing VintageStory server versions. The implementation follows patterns established in Epic 10 (Mod Browser) but with significant simplifications due to the smaller dataset and simpler metadata.

## ADR-1: Simpler Than Mod Browser Architecture

**Context:**
The version browser serves a similar purpose to the mod browser but has fundamentally different characteristics:

| Characteristic | Mod Browser | Version Browser |
|---------------|-------------|-----------------|
| Dataset size | 1000+ mods | <20 versions |
| Metadata fields | Many (tags, side, author, description) | Few (version, channel, filesize) |
| Search needed | Yes (text search) | No (scannable list) |
| Filtering | Complex (tags, side, compatibility) | Simple (channel only) |
| Pagination | Required | Not needed |
| External API | Rich mod database | Simple JSON files |

**Decision:**
Implement a **simplified version** of the mod browser architecture:

- No text search (version numbers are easily scannable)
- No tag filtering (versions have no tags)
- No pagination (dataset is small enough to display all)
- Channel filter only (stable/unstable toggle)
- Focus on card display and install flow

**Consequences:**

- Faster implementation (reuse patterns, not complexity)
- Better UX for the specific use case
- Less code to maintain
- Pattern: Match architecture complexity to problem complexity

## ADR-2: UI Component Reuse Strategy

**Context:**
Epic 10 established UI patterns for browsing and displaying items. Which patterns apply to versions?

**Decision:**
Reuse these Epic 10 patterns:

| Pattern | Epic 10 Location | Epic 13 Application |
|---------|------------------|---------------------|
| Card layout | `ModCard` | `VersionCard` (similar structure) |
| Grid display | `ModBrowseGrid` | `VersionGrid` (simpler, no pagination) |
| Channel badges | Side badges (client/server) | Channel badges (stable/unstable) |
| "Installed" badge | `ModCard` installed indicator | "Currently Installed" badge |
| TanStack Query | `useBrowseMods` | `useVersions` hook |
| Loading skeleton | `ModBrowseGrid` skeleton | `VersionGrid` skeleton |
| Error state | `BrowseTab` error handling | Similar error UI |

**Do NOT reuse:**

| Pattern | Why Not Needed |
|---------|----------------|
| Text search with debounce | Versions are easily scannable |
| FilterControls component | Only channel filter needed (simple toggle) |
| SortControl component | No meaningful sort options |
| Pagination component | All versions fit on one page |
| Scroll restoration | No pagination to restore |
| URL state for filters | Too simple to warrant URL state |

**Consequences:**

- Consistent look and feel with mod browser
- Familiar UX patterns for users
- Reduced code duplication for common patterns
- Simpler components for simpler requirements

## ADR-3: Version Card Design

**Context:**
What information should the version card display?

**Decision:**
Version cards show:

```text
┌─────────────────────────────────┐
│ [Channel Badge: Stable/Unstable]│
│                                 │
│   1.21.6                       │
│   40.2 MB                       │
│                                 │
│   [Latest] [Installed]          │
│                                 │
│   [Install/Upgrade Button]      │
└─────────────────────────────────┘
```

**Fields:**

| Field | Source | Notes |
|-------|--------|-------|
| Version number | API `version` | Primary identifier |
| Channel | API `channel` | Badge: "Stable" or "Unstable" |
| File size | API `filesize` | Human-readable string |
| Is Latest | API `is_latest` | Badge if true |
| Is Installed | Compare to current | Badge if matches installed version (see [Version Tracking](../../../agentdocs/server-installation.md#version-tracking)) |

**Not shown (metadata limitations):**

- Release date (not available from API)
- Changelog/release notes (not available)
- Download count (not available)

**Consequences:**

- Clean, simple card design
- Shows all available information
- Clear install/upgrade action
- Pattern: Display what you have, don't fake what you don't

## ADR-4: TanStack Query Cache Sync for Version Operations

**Context:**
When a user installs or upgrades a version, related queries should update.

**Decision:**
Use query invalidation on version operations:

```typescript
// In useInstallVersion mutation
onSuccess: () => {
  // Invalidate version list (to refresh "installed" badges)
  queryClient.invalidateQueries({ queryKey: queryKeys.versions.all });
  // Invalidate server status (shows current version)
  queryClient.invalidateQueries({ queryKey: queryKeys.server.status });
}
```

**Consequences:**

- Version list updates "Installed" badges automatically
- Server status reflects new version
- Consistent with mod browser pattern
- No manual state management needed

## ADR-5: Channel Filter Implementation

**Context:**
Users need to filter between stable and unstable versions.

**Decision:**
Implement as a **simple toggle/tabs** rather than FilterControls:

```typescript
// Simple channel tabs instead of complex FilterControls
<Tabs value={channel} onValueChange={setChannel}>
  <TabsList>
    <TabsTrigger value="all">All</TabsTrigger>
    <TabsTrigger value="stable">Stable</TabsTrigger>
    <TabsTrigger value="unstable">Unstable</TabsTrigger>
  </TabsList>
</Tabs>
```

**Why not FilterControls:**

- Only one filter dimension (channel)
- Only 3 options (all, stable, unstable)
- No need for collapsible sections
- Tabs provide better UX for this case

**Consequences:**

- Simpler implementation
- More appropriate UX for the use case
- Consistent with other tab patterns in the app

## ADR-6: Version Detail View Design

**Context:**
What should the detail view show when a user clicks on a version card?

**Decision:**
Given metadata limitations (no changelog, no release date), the detail view provides:

```text
┌─────────────────────────────────────────────┐
│ Server Version 1.21.6              [Stable] │
│                                             │
│ File Size: 40.2 MB                          │
│ MD5: abc123def456...                        │
│                                             │
│ Download URLs:                              │
│   CDN: https://cdn.vintagestory.at/...      │
│   Local: https://vintagestory.at/...        │
│                                             │
│ [Latest Version] [Currently Installed]      │
│                                             │
│ ┌─────────────────────────────────────────┐ │
│ │ [Install] or [Reinstall] or [Upgrade]  │ │
│ └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

**Why minimal:**

- No changelog available from API
- No release date/notes available
- Focus on actionable information (install, verify checksum)

**Action button logic:**

| Current State | Button Text | Action |
|--------------|-------------|--------|
| Not installed | "Install" | Install this version |
| Same version installed | "Reinstall" | Reinstall same version |
| Older version installed | "Upgrade" | Upgrade to this version |
| Newer version installed | "Downgrade" | Downgrade to this version |

**Consequences:**

- Detail view is simple but provides all available information
- Checksum display enables manual verification if needed
- Clear action based on current state
- Pattern: Don't create fake UI for missing data

## Component Architecture Summary

### New Components (Stories 13.2-13.5)

| Component | Purpose | Based On |
|-----------|---------|----------|
| `VersionCard` | Display single version | `ModCard` (simplified) |
| `VersionGrid` | Grid layout for versions | `ModBrowseGrid` (no pagination) |
| `VersionListPage` | Main version browser page | `BrowseTab` (simplified) |
| `VersionDetailView` | Expanded version info | `ModDetailPage` (simplified) |

### Hooks

| Hook | Purpose | Based On |
|------|---------|----------|
| `useVersions` | Fetch version list | `useBrowseMods` (simplified) |
| `useInstallVersion` | Install/upgrade mutation | `useInstallMod` |

### Shared Components (Reuse from Epic 10)

- `Button`, `Card`, `Badge` (shadcn/ui)
- Loading skeleton patterns
- Error state patterns

## References

- [Epic 10 Architecture Decisions](epic-10-architecture-decisions.md) - Source patterns
- [agentdocs/server-installation.md](../../../agentdocs/server-installation.md) - API documentation
- [Story 13-1 Implementation](../../implementation-artifacts/13-1-server-versions-api.md) - API layer

---

_Created: 2026-01-12 (Epic 13 Technical Preparation - Story 13.0)_
