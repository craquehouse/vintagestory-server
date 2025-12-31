/**
 * SettingGroup component for grouping related settings.
 *
 * Wraps settings in a Card with optional collapsible sections.
 * Uses shadcn/ui Card for consistent styling.
 *
 * Story 6.4: Settings UI
 */

import { useState, type ReactNode } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';

/**
 * Props for the SettingGroup component.
 */
export interface SettingGroupProps {
  /**
   * Title for the group.
   */
  title: string;

  /**
   * Optional description for the group.
   */
  description?: string;

  /**
   * Whether the group is collapsible.
   * @default false
   */
  collapsible?: boolean;

  /**
   * Initial collapsed state (only applies if collapsible is true).
   * @default false
   */
  defaultCollapsed?: boolean;

  /**
   * Child elements (typically SettingField components).
   */
  children: ReactNode;

  /**
   * Additional CSS class names for the card.
   */
  className?: string;
}

/**
 * Groups related settings in a Card container.
 *
 * @example
 * <SettingGroup title="Server Info" description="Basic server configuration">
 *   <SettingField ... />
 *   <SettingField ... />
 * </SettingGroup>
 *
 * @example
 * <SettingGroup title="Advanced" collapsible defaultCollapsed>
 *   <SettingField ... />
 * </SettingGroup>
 */
export function SettingGroup({
  title,
  description,
  collapsible = false,
  defaultCollapsed = false,
  children,
  className,
}: SettingGroupProps) {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);

  const handleToggle = () => {
    if (collapsible) {
      setIsCollapsed(!isCollapsed);
    }
  };

  const ChevronIcon = isCollapsed ? ChevronRight : ChevronDown;

  return (
    <Card className={className}>
      <CardHeader
        className={cn(
          collapsible && 'cursor-pointer select-none hover:bg-muted/50 transition-colors rounded-t-xl'
        )}
        onClick={handleToggle}
        role={collapsible ? 'button' : undefined}
        aria-expanded={collapsible ? !isCollapsed : undefined}
        tabIndex={collapsible ? 0 : undefined}
        onKeyDown={
          collapsible
            ? (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  handleToggle();
                }
              }
            : undefined
        }
      >
        <div className="flex items-center gap-2">
          {collapsible && (
            <ChevronIcon
              className="h-4 w-4 text-muted-foreground transition-transform"
              aria-hidden="true"
            />
          )}
          <CardTitle>{title}</CardTitle>
        </div>
        {description && (
          <p className="text-sm text-muted-foreground col-start-1">{description}</p>
        )}
      </CardHeader>

      {!isCollapsed && (
        <CardContent className="space-y-4">{children}</CardContent>
      )}
    </Card>
  );
}
