/**
 * The page content width (Epic 16 ADR-3, Epic 21 ADR-15, Story 21.8).
 *
 * `Layout` caps every page's content with it, inside its padding, so on wide screens pages are
 * centered in the area right of the sidebar. The Game Settings page and GameConfigPanel use it
 * too (Story 17.8), so their title, status badge and panel share one edge.
 */

/** At most 1280px, centered (UX spec "Content Width Constraints", Epic 21 ADR-15). Written once. */
export const PAGE_CONTENT_WIDTH = 'mx-auto max-w-[1280px]';

/**
 * Routes whose page uses the full width of the content area: the console (ADR-15 decision 4).
 * A page that shows the console and is given a route of its own belongs here too.
 */
export const FULL_WIDTH_ROUTES: readonly string[] = ['/game-server/console'];
