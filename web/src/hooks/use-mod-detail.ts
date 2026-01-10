/**
 * Hook for fetching mod detail data using TanStack Query.
 *
 * Story 10.6: Provides detailed mod information for the mod detail view,
 * including full description, all releases, tags, and metadata.
 */

import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/api/query-keys';
import { lookupMod } from '@/api/mods';

/**
 * Hook to fetch detailed mod information from the VintageStory mod database.
 *
 * Uses the extended lookup endpoint which now returns full release data,
 * tags, follower count, and other metadata needed for the detail view.
 *
 * @param slug - Mod slug to look up (empty string disables query)
 * @returns TanStack Query result with ModLookupData
 *
 * @example
 * function ModDetailPage() {
 *   const { slug } = useParams();
 *   const { data, isLoading, error } = useModDetail(slug ?? '');
 *
 *   if (isLoading) return <Skeleton />;
 *   if (error) return <ErrorDisplay error={error} />;
 *
 *   const mod = data?.data;
 *   return (
 *     <div>
 *       <h1>{mod?.name}</h1>
 *       <p>{mod?.author}</p>
 *       <p>Releases: {mod?.releases.length}</p>
 *     </div>
 *   );
 * }
 */
export function useModDetail(slug: string) {
  return useQuery({
    queryKey: queryKeys.mods.detail(slug),
    queryFn: () => lookupMod(slug),
    // Only fetch when slug is non-empty
    enabled: !!slug.trim(),
    // Keep detail results fresh for 5 minutes (same as lookup)
    staleTime: 5 * 60 * 1000,
    // Don't refetch on window focus for detail view
    refetchOnWindowFocus: false,
  });
}
