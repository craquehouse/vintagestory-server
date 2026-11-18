/**
 * Screen reader text for a link that opens in a new tab (Story 18.1; Story 21.6, Epic 21
 * ADR-10). Shared by `NewTabLink`, the icon-only links' `aria-label`s and the description
 * sanitizer, so the wording cannot drift. It lives in its own module so the sidebar (in
 * the main bundle) can use it without importing the sanitizer and DOMPurify.
 */
export const OPENS_IN_NEW_TAB = '(opens in a new tab)';
