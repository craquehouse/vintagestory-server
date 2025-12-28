import { Circle, Square, X, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ServerState } from '@/api/types';

export type { ServerState };

interface ServerStatusBadgeProps {
  state: ServerState;
  className?: string;
}

/**
 * Visual indicator for server status with appropriate color and icon.
 *
 * States and their visual representation:
 * - Not Installed: Gray, empty circle
 * - Installing: Yellow, animated spinner
 * - Stopped (installed): Red, square icon
 * - Starting/Stopping: Yellow, animated spinner
 * - Running: Green, filled circle
 * - Error: Red, X icon
 */
export function ServerStatusBadge({ state, className }: ServerStatusBadgeProps) {
  const config = getStateConfig(state);

  return (
    <div
      className={cn(
        'inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm font-medium',
        config.bgClass,
        config.textClass,
        className
      )}
      role="status"
      aria-label={`Server status: ${config.label}`}
    >
      <config.Icon
        className={cn('size-4', config.isAnimated && 'animate-spin')}
        aria-hidden="true"
      />
      <span>{config.label}</span>
    </div>
  );
}

interface StateConfig {
  label: string;
  Icon: typeof Circle;
  bgClass: string;
  textClass: string;
  isAnimated: boolean;
}

function getStateConfig(state: ServerState): StateConfig {
  switch (state) {
    case 'not_installed':
      return {
        label: 'Not Installed',
        Icon: Circle,
        bgClass: 'bg-muted/50',
        textClass: 'text-muted-foreground',
        isAnimated: false,
      };
    case 'installing':
      return {
        label: 'Installing',
        Icon: Loader2,
        bgClass: 'bg-warning/20',
        textClass: 'text-warning',
        isAnimated: true,
      };
    case 'installed':
      return {
        label: 'Stopped',
        Icon: Square,
        bgClass: 'bg-destructive/20',
        textClass: 'text-destructive',
        isAnimated: false,
      };
    case 'starting':
      return {
        label: 'Starting',
        Icon: Loader2,
        bgClass: 'bg-warning/20',
        textClass: 'text-warning',
        isAnimated: true,
      };
    case 'running':
      return {
        label: 'Running',
        Icon: Circle,
        bgClass: 'bg-success/20',
        textClass: 'text-success',
        isAnimated: false,
      };
    case 'stopping':
      return {
        label: 'Stopping',
        Icon: Loader2,
        bgClass: 'bg-warning/20',
        textClass: 'text-warning',
        isAnimated: true,
      };
    case 'error':
      return {
        label: 'Error',
        Icon: X,
        bgClass: 'bg-destructive/20',
        textClass: 'text-destructive',
        isAnimated: false,
      };
    default: {
      // TypeScript exhaustive check
      const _exhaustive: never = state;
      return _exhaustive;
    }
  }
}
