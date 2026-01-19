/**
 * Hook for fetching available game versions for mod filtering.
 *
 * Story VSS-vth: Game version filter for mod browser.
 */

import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/api/query-keys';
import { fetchGameVersions } from '@/api/mods';

/**
 * Cache time for game versions (30 minutes).
 * Game versions rarely change, so we can cache aggressively.
 */
const GAMEVERSIONS_STALE_TIME = 30 * 60 * 1000;

/**
 * Hook to fetch available game versions for mod filtering.
 *
 * Returns a list of game version strings sorted newest to oldest.
 * Results are cached for 30 minutes since versions rarely change.
 *
 * @example
 * function VersionFilter() {
 *   const { data, isLoading } = useGameVersions();
 *
 *   if (isLoading) return <div>Loading...</div>;
 *
 *   return (
 *     <select>
 *       {data?.data?.versions.map(v => (
 *         <option key={v} value={v}>{v}</option>
 *       ))}
 *     </select>
 *   );
 * }
 */
export function useGameVersions() {
  return useQuery({
    queryKey: queryKeys.mods.gameVersions,
    queryFn: fetchGameVersions,
    staleTime: GAMEVERSIONS_STALE_TIME,
  });
}
