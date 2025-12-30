/**
 * CompatibilityBadge - Displays mod compatibility status with color-coded badge.
 *
 * Visual indicators:
 * - Compatible: Green (#a6e3a1) with checkmark icon
 * - Not verified: Yellow (#f9e2af) with warning icon
 * - Incompatible: Red (#f38ba8) with X icon
 *
 * Uses Catppuccin Mocha colors from the UX spec.
 */

import { Check, AlertTriangle, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { CompatibilityStatus } from '@/api/types';

interface CompatibilityBadgeProps {
  /** The compatibility status to display */
  status: CompatibilityStatus;
  /** Optional additional message for tooltip */
  message?: string;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Badge configuration for each compatibility status.
 */
const statusConfig = {
  compatible: {
    label: 'Compatible',
    icon: Check,
    // Catppuccin Mocha green - subtle treatment (success = quiet)
    className: 'bg-[#a6e3a1]/20 text-[#a6e3a1] border-[#a6e3a1]/30',
  },
  not_verified: {
    label: 'Not verified',
    icon: AlertTriangle,
    // Catppuccin Mocha yellow
    className: 'bg-[#f9e2af]/20 text-[#f9e2af] border-[#f9e2af]/30',
  },
  incompatible: {
    label: 'Incompatible',
    icon: X,
    // Catppuccin Mocha red - prominent treatment (error = loud)
    className: 'bg-[#f38ba8]/20 text-[#f38ba8] border-[#f38ba8]/30',
  },
} as const;

/**
 * Displays mod compatibility status with appropriate color and icon.
 *
 * @example
 * <CompatibilityBadge status="compatible" />
 * <CompatibilityBadge status="not_verified" message="No version match found" />
 * <CompatibilityBadge status="incompatible" message="Requires server 1.20+" />
 */
export function CompatibilityBadge({
  status,
  message,
  className,
}: CompatibilityBadgeProps) {
  const config = statusConfig[status];
  const Icon = config.icon;

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium',
        config.className,
        className
      )}
      title={message}
      data-testid="compatibility-badge"
      data-status={status}
    >
      <Icon className="h-3 w-3" aria-hidden="true" />
      <span>{config.label}</span>
    </span>
  );
}
