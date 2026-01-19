/**
 * PendingRestartBanner - Banner shown when mod changes require a server restart.
 *
 * Features:
 * - Shows when pendingRestart is true from mods endpoint
 * - Displays restart indicator with "Restart Now" button
 * - Loading state during restart
 */

import { RefreshCw, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useRestartServer } from '@/hooks/use-server-status';
import { useModsPendingRestart } from '@/hooks/use-mods';

interface PendingRestartBannerProps {
  /** Callback when restart is initiated */
  onRestart?: () => void;
}

/**
 * Banner indicating that mod changes require a server restart.
 *
 * The banner reads the pending restart state from the mods query and provides
 * a button to trigger a server restart.
 *
 * @example
 * <PendingRestartBanner onRestart={() => toast.success('Restarting server...')} />
 */
export function PendingRestartBanner({ onRestart }: PendingRestartBannerProps) {
  const pendingRestart = useModsPendingRestart();
  const { mutate: restart, isPending: isRestarting } = useRestartServer();

  const handleRestart = () => {
    restart(undefined, {
      onSuccess: () => {
        onRestart?.();
      },
    });
  };

  if (!pendingRestart) {
    return null;
  }

  return (
    <div
      className="flex items-center gap-2 rounded-md bg-primary/20 px-3 py-1.5 text-sm"
      data-testid="pending-restart-banner"
    >
      <RefreshCw
        className="h-4 w-4 text-primary"
        aria-hidden="true"
        data-testid="restart-icon"
      />
      <span className="text-primary">Restart required</span>
      <Button
        variant="ghost"
        size="sm"
        onClick={handleRestart}
        disabled={isRestarting}
        className="h-6 px-2 text-xs font-medium text-primary hover:bg-primary/20 hover:text-primary"
        data-testid="restart-button"
      >
        {isRestarting ? (
          <>
            <Loader2 className="mr-1 h-3 w-3 animate-spin" />
            Restarting...
          </>
        ) : (
          'Restart Now'
        )}
      </Button>
    </div>
  );
}
