/**
 * The game server settings width (Epic 16 ADR-3, Story 17.8): at most 1280px, centered.
 *
 * GameConfigPanel caps its content with it and the Game Settings page caps its title row
 * with it, so the title, the status badge and the panel share one edge and cannot drift.
 */
export const SETTINGS_CONTENT_WIDTH = 'mx-auto max-w-[1280px]';
