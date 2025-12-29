import { cn } from '@/lib/utils';
import type { ConnectionState } from '@/hooks/use-console-websocket';
import type { ServerState } from '@/api/types';

export interface ConnectionStatusProps {
  /** Current WebSocket connection state */
  state: ConnectionState;
  /** Current game server state (optional - for showing server not running) */
  serverState?: ServerState;
  /** Additional CSS classes */
  className?: string;
}

interface StatusConfig {
  label: string;
  indicatorClass: string;
  textClass: string;
  pulse?: boolean;
}

/**
 * Get configuration for a connection state, considering server state.
 */
function getStatusConfig(
  state: ConnectionState,
  serverState?: ServerState
): StatusConfig {
  switch (state) {
    case 'connecting':
      return {
        label: 'Connecting...',
        indicatorClass: 'bg-yellow-500',
        textClass: 'text-yellow-600 dark:text-yellow-400',
        pulse: true,
      };
    case 'connected':
      // If connected but server not running, show yellow warning
      if (serverState && serverState !== 'running') {
        return {
          label: 'Server not running',
          indicatorClass: 'bg-yellow-500',
          textClass: 'text-yellow-600 dark:text-yellow-400',
        };
      }
      return {
        label: 'Connected',
        indicatorClass: 'bg-green-500',
        textClass: 'text-green-600 dark:text-green-400',
      };
    case 'disconnected':
      return {
        label: 'Disconnected',
        indicatorClass: 'bg-gray-500',
        textClass: 'text-gray-600 dark:text-gray-400',
      };
    case 'forbidden':
      return {
        label: 'Access Denied',
        indicatorClass: 'bg-red-500',
        textClass: 'text-red-600 dark:text-red-400',
      };
    default: {
      // TypeScript exhaustive check
      const _exhaustive: never = state;
      return _exhaustive;
    }
  }
}

/**
 * Connection status indicator with colored dot and label.
 *
 * Displays the current WebSocket connection state with appropriate
 * visual feedback:
 * - Green: Connected (WebSocket connected AND server running)
 * - Yellow: Connecting, or Server not running (WebSocket connected but server stopped)
 * - Gray: Disconnected
 * - Red: Access Denied (forbidden)
 *
 * Includes ARIA live region for screen reader announcements.
 *
 * @example
 * ```tsx
 * <ConnectionStatus state={connectionState} serverState={serverStatus?.state} />
 * ```
 */
export function ConnectionStatus({
  state,
  serverState,
  className,
}: ConnectionStatusProps) {
  const config = getStatusConfig(state, serverState);

  return (
    <div
      className={cn('flex items-center gap-2', className)}
      role="status"
      aria-live="polite"
      aria-label={`Connection status: ${config.label}`}
    >
      <span
        className={cn(
          'inline-block h-2 w-2 rounded-full',
          config.indicatorClass,
          config.pulse && 'animate-pulse'
        )}
        aria-hidden="true"
      />
      <span className={cn('text-xs font-medium', config.textClass)}>
        {config.label}
      </span>
    </div>
  );
}
