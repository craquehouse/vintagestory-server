import { cn } from '@/lib/utils';
import type { ConnectionState } from '@/hooks/use-console-websocket';

export interface ConnectionStatusProps {
  /** Current connection state */
  state: ConnectionState;
  /** Additional CSS classes */
  className?: string;
}

interface StatusConfig {
  label: string;
  indicatorClass: string;
  textClass: string;
}

/**
 * Get configuration for a connection state.
 */
function getStatusConfig(state: ConnectionState): StatusConfig {
  switch (state) {
    case 'connecting':
      return {
        label: 'Connecting...',
        indicatorClass: 'bg-yellow-500',
        textClass: 'text-yellow-600 dark:text-yellow-400',
      };
    case 'connected':
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
 * - Green: Connected
 * - Yellow: Connecting
 * - Gray: Disconnected
 * - Red: Access Denied (forbidden)
 *
 * Includes ARIA live region for screen reader announcements.
 *
 * @example
 * ```tsx
 * <ConnectionStatus state={connectionState} />
 * ```
 */
export function ConnectionStatus({ state, className }: ConnectionStatusProps) {
  const config = getStatusConfig(state);

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
          state === 'connecting' && 'animate-pulse'
        )}
        aria-hidden="true"
      />
      <span className={cn('text-xs font-medium', config.textClass)}>
        {config.label}
      </span>
    </div>
  );
}
