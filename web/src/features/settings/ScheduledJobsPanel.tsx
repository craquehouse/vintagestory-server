/**
 * ScheduledJobsPanel - Displays scheduled background jobs.
 *
 * Shows a table of registered jobs with their schedules and next run times.
 * Only visible to Admin users (Monitor role cannot see this panel).
 *
 * Story 8.3: Job Configuration UI - AC1, AC4
 */

import { AlertCircle, Loader2 } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { JobsTable } from '@/components/JobsTable';
import { useAuthMe } from '@/api/hooks/use-auth-me';
import { useJobs } from '@/hooks/use-jobs';

/**
 * Panel displaying scheduled jobs.
 *
 * Only renders for Admin users - returns null for Monitor role.
 * Shows loading, error, and empty states appropriately.
 *
 * @example
 * <ScheduledJobsPanel />
 */
export function ScheduledJobsPanel() {
  const { data: auth, isLoading: authLoading } = useAuthMe();
  const { data: jobsData, isLoading: jobsLoading, error } = useJobs();

  // Don't render for non-Admin users (AC: 4)
  if (!authLoading && auth?.data?.role !== 'admin') {
    return null;
  }

  // Loading state
  if (authLoading || jobsLoading) {
    return (
      <Card data-testid="scheduled-jobs-loading">
        <CardHeader>
          <CardTitle>Scheduled Jobs</CardTitle>
          <CardDescription>Background tasks running on a schedule</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        </CardContent>
      </Card>
    );
  }

  // Error state
  if (error) {
    return (
      <Card data-testid="scheduled-jobs-error">
        <CardHeader>
          <CardTitle>Scheduled Jobs</CardTitle>
          <CardDescription>Background tasks running on a schedule</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 rounded-lg border border-destructive/50 bg-destructive/10 p-4">
            <AlertCircle className="h-5 w-5 text-destructive" />
            <div>
              <p className="font-medium text-destructive">Failed to load jobs</p>
              <p className="text-sm text-muted-foreground">
                {error.message || 'Unable to load scheduled jobs'}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  const jobs = jobsData?.data?.jobs ?? [];

  return (
    <Card data-testid="scheduled-jobs-panel">
      <CardHeader>
        <CardTitle>Scheduled Jobs</CardTitle>
        <CardDescription>Background tasks running on a schedule</CardDescription>
      </CardHeader>
      <CardContent>
        <JobsTable jobs={jobs} />
      </CardContent>
    </Card>
  );
}
