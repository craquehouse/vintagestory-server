/**
 * GameServerPage - Main game server management page.
 *
 * Provides a responsive split layout:
 * - Desktop (lg+): GameConfigPanel left, ConsolePanel right
 * - Mobile: ConsolePanel top, GameConfigPanel bottom
 *
 * Story 6.4: Settings UI - AC1, AC2
 */

import { ConsolePanel } from '@/components/ConsolePanel';
import { GameConfigPanel } from './GameConfigPanel';

/**
 * Game server management page with responsive layout.
 *
 * On desktop (lg+), displays:
 * - Left panel: Game settings configuration
 * - Right panel: Server console output
 *
 * On mobile, displays:
 * - Top: Server console (prioritized for monitoring)
 * - Bottom: Game settings (scrollable)
 */
export function GameServerPage() {
  return (
    <div
      className="flex h-full flex-col lg:flex-row gap-4"
      data-testid="game-server-page"
      aria-label="Game Server page"
    >
      {/* Desktop: left panel, Mobile: bottom panel */}
      <div className="order-2 lg:order-1 lg:w-1/2 overflow-auto">
        <GameConfigPanel />
      </div>
      {/* Desktop: right panel, Mobile: top panel */}
      <div className="order-1 lg:order-2 lg:w-1/2 flex-1 lg:flex-none min-h-[300px] lg:min-h-0">
        <ConsolePanel className="h-full" />
      </div>
    </div>
  );
}
