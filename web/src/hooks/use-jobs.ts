/**
 * Hook for fetching scheduled jobs using TanStack Query.
 *
 * Provides a simple query for fetching all registered jobs from the scheduler.
 * Jobs are returned with camelCase keys (transformed at API boundary).
 *
 * Story 8.3: Job Configuration UI
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import { queryKeys } from '@/api/query-keys';

/**
 * Job information returned by the jobs API.
 *
 * @property id - Unique job identifier (e.g., "mod_cache_refresh")
 * @property nextRunTime - ISO datetime string or null if job is paused/disabled
 * @property triggerType - Type of trigger ("interval", "cron", or "unknown")
 * @property triggerDetails - Human-readable trigger description
 */
export interface JobInfo {
  id: string;
  nextRunTime: string | null;
  triggerType: 'interval' | 'cron' | 'unknown';
  triggerDetails: string;
}

/**
 * Response shape for the jobs API endpoint.
 */
export interface JobsResponse {
  status: 'ok';
  data: {
    jobs: JobInfo[];
  };
}

/**
 * Default polling interval for jobs (30 seconds).
 * Jobs may change less frequently, but we want reasonably current next_run_time.
 */
const JOBS_POLL_INTERVAL = 30000;

/**
 * Hook to fetch all scheduled jobs.
 *
 * Polls every 30 seconds to keep next_run_time current.
 * Returns an array of JobInfo objects.
 *
 * @example
 * function JobsPanel() {
 *   const { data, isLoading, error } = useJobs();
 *
 *   if (isLoading) return <div>Loading...</div>;
 *   if (error) return <div>Error: {error.message}</div>;
 *
 *   return (
 *     <ul>
 *       {data?.data.jobs.map(job => (
 *         <li key={job.id}>{job.id}: {job.triggerDetails}</li>
 *       ))}
 *     </ul>
 *   );
 * }
 */
export function useJobs() {
  return useQuery({
    queryKey: queryKeys.jobs.all,
    queryFn: async () => {
      return apiClient<JobsResponse>('/api/v1alpha1/jobs');
    },
    refetchInterval: JOBS_POLL_INTERVAL,
    refetchIntervalInBackground: false,
  });
}
