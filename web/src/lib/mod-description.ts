/**
 * Sanitizing for mod descriptions from the VintageStory mod database.
 *
 * ModDB returns each mod's description as author-written HTML. Every surface that
 * renders it (mod detail page, mod lookup preview) goes through this module, so the
 * DOMPurify configuration lives in one place.
 *
 * - Links that keep an `href` open in a new tab with `rel="noopener noreferrer"`.
 * - `<style>` elements are removed: DOMPurify keeps one that follows body content,
 *   and it would restyle the whole app, not just the description.
 * - The preview keeps text formatting only: no media, forms, SVG or inline styling.
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

/** Detail page: DOMPurify defaults (images, inline styles kept) minus `<style>`. */
const DETAIL_CONFIG: Config = {
  FORBID_TAGS: ['style'],
};

/** Lookup preview: text formatting only, readable in light and dark themes. */
const PREVIEW_CONFIG: Config = {
  ALLOWED_TAGS: [
    'p', 'br', 'div', 'span',
    'strong', 'b', 'em', 'i', 'u', 's', 'code',
    'a', 'ul', 'ol', 'li', 'blockquote',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
  ],
  ALLOWED_ATTR: ['href', 'title'],
};

/** Sanitize a mod description for the mod detail page. */
export function sanitizeModDescription(html: string): string {
  return purifier.sanitize(html, DETAIL_CONFIG);
}

/**
 * Sanitize a mod description for the short lookup preview.
 *
 * @returns the sanitized markup, or `null` when no visible text is left
 *   (for example a description made only of images).
 */
export function sanitizeModDescriptionPreview(html: string): string | null {
  const sanitized = purifier.sanitize(html, PREVIEW_CONFIG);
  // DOMParser documents are inert: parsing the sanitized markup runs nothing and loads nothing.
  const text = new DOMParser().parseFromString(sanitized, 'text/html').body.textContent;
  return text.trim() ? sanitized : null;
}
