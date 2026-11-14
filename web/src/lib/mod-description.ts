/**
 * Sanitizing for mod descriptions from the VintageStory mod database.
 *
 * ModDB returns each mod's description as author-written HTML. Every surface that
 * renders it goes through this module, so the DOMPurify configuration lives in one place.
 *
 * - Links that keep an `href` open in a new tab with `rel="noopener noreferrer"`.
 * - `<style>` elements are removed: DOMPurify keeps one that follows body content,
 *   and it would restyle the whole app, not just the description.
 */

import DOMPurify, { type Config } from 'dompurify';

/**
 * Private instance: hooks are per instance, so the link hook below never affects
 * other code that calls the shared `DOMPurify.sanitize`.
 */
const purifier = DOMPurify(window);

purifier.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName === 'A' && node.hasAttribute('href')) {
    node.setAttribute('target', '_blank');
    node.setAttribute('rel', 'noopener noreferrer');
  }
});

/** DOMPurify defaults (images, inline styles kept) minus `<style>`. */
const DESCRIPTION_CONFIG: Config = {
  FORBID_TAGS: ['style'],
};

/** Sanitize a mod description for the mod detail page. */
export function sanitizeModDescription(html: string): string {
  return purifier.sanitize(html, DESCRIPTION_CONFIG);
}
