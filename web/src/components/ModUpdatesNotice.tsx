/**
 * ModUpdatesNotice - Dashboard notice for available mod updates (Story 14.5).
 *
 * Shows how many installed mods have an update available and links to the Installed
 * tab. Renders nothing when there are none or the status has not loaded.
 */

import { ArrowUpCircle } from 'lucide-react';
import { Link } from 'react-router';
import { useModUpdates } from '@/hooks/use-mods';

export function ModUpdatesNotice() {
  const { data } = useModUpdates();
  const count = data?.data?.updateCount ?? 0;

  if (count === 0) {
    return null;
  }

  return (
    <Link
      to="/game-server/mods/installed"
      className="flex items-center gap-2 rounded-md bg-primary/10 px-3 py-1.5 text-sm hover:bg-primary/20"
      data-testid="mod-updates-notice"
    >
      <ArrowUpCircle className="h-4 w-4 text-primary" aria-hidden="true" />
      <span>
        {count} mod {count === 1 ? 'update' : 'updates'} available
      </span>
      <span className="ml-auto text-primary">Review</span>
    </Link>
  );
}
