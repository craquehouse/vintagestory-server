/**
 * StatCard component for displaying dashboard metrics.
 *
 * Story 12.4: Dashboard Stats Cards
 *
 * A reusable card component for displaying statistics with an icon,
 * title, main value, and optional subtitle. Designed for the dashboard
 * grid layout with responsive styling.
 */

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import type { LucideIcon } from 'lucide-react';

export interface StatCardProps {
  /** Lucide icon component to display */
  icon: LucideIcon;
  /** Card title/label */
  title: string;
  /** Main value to display prominently */
  value: string | number;
  /** Optional subtitle or additional context */
  subtitle?: string;
  /** Optional additional class names */
  className?: string;
  /** Optional children for custom content */
  children?: React.ReactNode;
  /** Test ID for testing */
  testId?: string;
}

/**
 * StatCard displays a single metric with icon, title, and value.
 *
 * @example
 * ```tsx
 * import { MemoryStick } from 'lucide-react';
 *
 * <StatCard
 *   icon={MemoryStick}
 *   title="Memory Usage"
 *   value="128.5 MB"
 *   subtitle="API Server"
 * />
 * ```
 */
export function StatCard({
  icon: Icon,
  title,
  value,
  subtitle,
  className,
  children,
  testId,
}: StatCardProps) {
  return (
    <Card className={cn('min-h-[140px]', className)} data-testid={testId}>
      <CardHeader className="pb-2">
        <div className="flex items-center gap-3">
          <Icon className="size-5 text-muted-foreground" aria-hidden="true" />
          <CardTitle className="text-base font-medium">{title}</CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold" data-testid={testId ? `${testId}-value` : undefined}>
          {value}
        </div>
        {subtitle && (
          <div
            className="mt-1 text-sm text-muted-foreground"
            data-testid={testId ? `${testId}-subtitle` : undefined}
          >
            {subtitle}
          </div>
        )}
        {children}
      </CardContent>
    </Card>
  );
}
