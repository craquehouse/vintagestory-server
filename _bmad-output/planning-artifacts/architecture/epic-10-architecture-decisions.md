# Epic 10: Architecture Decisions

_Decisions made during Epic 10 (Advanced Mod Browser) that establish patterns for future work._

## ADR-1: Hybrid Client/Server Filtering Architecture

**Context:**
The mod browser needs to support filtering by side (client/server/both), tag, and sorting options. The VintageStory Mod API only supports a subset of filtering/sorting server-side.

**Decision:**
Use a **hybrid approach** with clear separation:

| Capability | Where | Rationale |
|------------|-------|-----------|
| Pagination | Server | API supports `offset`/`limit` natively |
| Text search | Server | API `q` parameter performs server-side search |
| Sort by downloads/trending/updated | Server | API `sort` parameter supports these |
| Side filter (client/server/both) | Client | API doesn't support this filter |
| Tag filter | Client | API doesn't support tag filtering |
| Sort by name (A-Z) | Client | API doesn't support alphabetical sort |

**Consequences:**
- Client-side filtering works because page sizes are reasonable (~50 items per page)
- Some filter combinations may return fewer results than `page_size` due to client-side filtering
- Future API improvements could move more filtering server-side
- Pattern: Prefer server-side when available, fall back to client-side when necessary

**Code Location:**
- Client-side filtering: `web/src/features/mods/utils/mod-filters.ts`
- Server-side params: `api/src/vintagestory_api/routers/mods.py` browse endpoint

## ADR-2: Conservative Compatibility Badge

**Context:**
Mod cards in browse results need to show compatibility status. However, determining true compatibility requires:
1. Current server game version
2. Full release history from mod detail endpoint
3. Complex version matching logic

For browse cards, we only have limited mod data (no full release history).

**Decision:**
Use a **conservative default** for browse cards:

```typescript
// Browse cards: always show "not_verified"
export function getBrowseCardCompatibility(): CompatibilityInfo {
  return { status: 'not_verified', message: undefined };
}

// Detail view: full compatibility check with release data
export function getCompatibility(
  serverVersion: string | null,
  releases: ModRelease[]
): CompatibilityInfo {
  // Full version matching logic here
}
```

**Consequences:**
- Users see "Not Verified" on browse cards, avoiding false confidence
- Full compatibility check only runs on detail page where we have complete data
- Prevents showing "Compatible" for mods that might not work
- Pattern: When data is incomplete, show conservative/neutral status rather than optimistic guess

**Code Location:**
- `web/src/features/mods/utils/compatibility.ts`

## ADR-3: TanStack Query Cache Invalidation for Cross-Tab Sync

**Context:**
When a user installs a mod from the Browse tab, the Installed tab should reflect the change immediately.

**Decision:**
Use TanStack Query's cache invalidation to sync across tabs:

```typescript
// In useInstallMod hook
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: queryKeys.mods.all });
}
```

**Consequences:**
- All `mods.*` queries are invalidated on install/uninstall
- Installed tab refetches automatically without manual coordination
- No additional state management or event bus needed
- Pattern: Use TanStack Query as the single source of truth for server state

**Code Location:**
- `web/src/hooks/use-mods.ts` (queryKeys and mutation hooks)

## ADR-4: URL State for Filters

**Context:**
Browse filters (search query, side filter, tag filter, sort order) need to persist across navigation and page refreshes.

**Decision:**
Store filter state in URL search parameters:

```typescript
const [searchParams, setSearchParams] = useSearchParams();

// Read from URL
const query = searchParams.get('q') || '';
const side = searchParams.get('side') as ModSide | null;

// Write to URL
setSearchParams(prev => {
  prev.set('q', newQuery);
  return prev;
});
```

**Consequences:**
- Shareable URLs: users can share filtered browse states
- Browser history works: back/forward navigates filter states
- Page refresh preserves state: no lost context
- Pattern: Use URL as single source of truth for UI state that should be shareable/bookmarkable

**Code Location:**
- `web/src/features/mods/components/browse-filters.tsx`

## ADR-5: In-Memory Cache for Browse API

**Context:**
The browse endpoint calls the external VintageStory mod API, which has rate limits and latency.

**Decision:**
Use in-memory caching with the existing mod cache infrastructure:

```python
# Browse results cached with query-specific keys
cache_key = f"browse:{query}:{sort}:{offset}:{limit}"
cached = self._browse_cache.get(cache_key)
if cached and not cached.is_expired(ttl=300):  # 5 min TTL
    return cached.data
```

**Consequences:**
- Repeated searches within TTL don't hit external API
- Cache is scoped per query combination
- Leverages existing cache eviction from Epic 9.3
- Pattern: Cache external API responses with appropriate TTL based on data freshness requirements

**Code Location:**
- `api/src/vintagestory_api/services/mods.py` (BrowseCache class)
