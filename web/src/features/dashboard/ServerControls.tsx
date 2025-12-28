import { Play, Square, RotateCcw, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import {
  useStartServer,
  useStopServer,
  useRestartServer,
} from '@/hooks/use-server-status';
import type { ServerState } from '@/api/types';

interface ServerControlsProps {
  serverState: ServerState;
}

/**
 * Server control buttons for Start, Stop, and Restart actions.
 *
 * Button enable/disable logic based on server state:
 * - Start: Enabled when server is installed (stopped)
 * - Stop: Enabled when server is running
 * - Restart: Enabled when server is running
 *
 * All buttons disabled during transitional states (starting, stopping, installing).
 */
export function ServerControls({ serverState }: ServerControlsProps) {
  const startMutation = useStartServer();
  const stopMutation = useStopServer();
  const restartMutation = useRestartServer();

  const isTransitional =
    serverState === 'starting' ||
    serverState === 'stopping' ||
    serverState === 'installing';

  const canStart =
    serverState === 'installed' &&
    !startMutation.isPending &&
    !isTransitional;

  const canStop =
    serverState === 'running' &&
    !stopMutation.isPending &&
    !restartMutation.isPending &&
    !isTransitional;

  const canRestart =
    serverState === 'running' &&
    !restartMutation.isPending &&
    !stopMutation.isPending &&
    !isTransitional;

  const handleStart = () => {
    startMutation.mutate(undefined, {
      onSuccess: () => {
        toast.success('Server starting', {
          description: 'The server is now starting up.',
        });
      },
      onError: (error) => {
        toast.error('Failed to start server', {
          description: error.message,
        });
      },
    });
  };

  const handleStop = () => {
    stopMutation.mutate(undefined, {
      onSuccess: () => {
        toast.success('Server stopping', {
          description: 'The server is shutting down.',
        });
      },
      onError: (error) => {
        toast.error('Failed to stop server', {
          description: error.message,
        });
      },
    });
  };

  const handleRestart = () => {
    restartMutation.mutate(undefined, {
      onSuccess: () => {
        toast.success('Server restarting', {
          description: 'The server is restarting.',
        });
      },
      onError: (error) => {
        toast.error('Failed to restart server', {
          description: error.message,
        });
      },
    });
  };

  return (
    <div className="flex items-center gap-2">
      <Button
        onClick={handleStart}
        disabled={!canStart}
        variant="default"
        size="sm"
        aria-label="Start server"
      >
        {startMutation.isPending ? (
          <Loader2 className="animate-spin" />
        ) : (
          <Play />
        )}
        Start
      </Button>

      <Button
        onClick={handleStop}
        disabled={!canStop}
        variant="outline"
        size="sm"
        className="border-destructive text-destructive hover:bg-destructive/10"
        aria-label="Stop server"
      >
        {stopMutation.isPending ? (
          <Loader2 className="animate-spin" />
        ) : (
          <Square />
        )}
        Stop
      </Button>

      <Button
        onClick={handleRestart}
        disabled={!canRestart}
        variant="secondary"
        size="sm"
        aria-label="Restart server"
      >
        {restartMutation.isPending ? (
          <Loader2 className="animate-spin" />
        ) : (
          <RotateCcw />
        )}
        Restart
      </Button>
    </div>
  );
}
