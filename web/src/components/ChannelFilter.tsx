/**
 * ChannelFilter - Tab-based filter for server version channels.
 *
 * Provides filter tabs for All, Stable, and Unstable version channels.
 * Uses shadcn/ui Tabs component per ADR-5 from Epic 13 Architecture.
 *
 * Story 13.3: Version List Page
 */

import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import type { VersionChannel } from '@/api/types';

/** Channel filter value - undefined means "All" */
export type ChannelFilterValue = VersionChannel | undefined;

interface ChannelFilterProps {
  /** Current selected channel (undefined = All) */
  value: ChannelFilterValue;
  /** Callback when channel selection changes */
  onChange: (channel: ChannelFilterValue) => void;
}

/**
 * Tab-based channel filter for version browsing.
 *
 * Uses "all" as the tab value for undefined/all channels,
 * and "stable"/"unstable" for specific channels.
 *
 * @example
 * <ChannelFilter value={channel} onChange={setChannel} />
 */
export function ChannelFilter({ value, onChange }: ChannelFilterProps) {
  // Convert undefined to "all" for tab value
  const tabValue = value ?? 'all';

  const handleValueChange = (newValue: string) => {
    // Convert "all" back to undefined for API compatibility
    onChange(newValue === 'all' ? undefined : (newValue as VersionChannel));
  };

  return (
    <Tabs
      value={tabValue}
      onValueChange={handleValueChange}
      data-testid="channel-filter"
    >
      <TabsList data-testid="channel-filter-tabs">
        <TabsTrigger value="all" data-testid="channel-filter-all">
          All
        </TabsTrigger>
        <TabsTrigger value="stable" data-testid="channel-filter-stable">
          Stable
        </TabsTrigger>
        <TabsTrigger value="unstable" data-testid="channel-filter-unstable">
          Unstable
        </TabsTrigger>
      </TabsList>
    </Tabs>
  );
}
