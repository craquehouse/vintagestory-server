/**
 * Sanitizing for mod descriptions from the VintageStory mod database.
 *
 * ModDB returns each mod's description as author-written HTML. Every surface that
 * renders it goes through this module, so the DOMPurify configuration lives in one place.
 *
 * - Links that keep an `href` open in a new tab with `rel="noopener noreferrer"`.
 *   An HTML link also ends with a screen reader note, `<span class="sr-only"
 *   data-new-tab-note> (opens in a new tab)</span>`, built with `createElement` and
 *   `textContent` (Story 18.1, VSS-tzl). The visible icon is CSS on the page's
 *   `.mod-description` container. SVG links get no note: they cannot hold an HTML span.
 * - An HTML `<img>` loads only from an `https://` or `data:image/` address, which the
 *   web UI's Content-Security-Policy allows (Epic 19 ADR-6 decision 14). Any other image
 *   is replaced by `<span data-image-not-shown>Image not shown: <alt></span>`, built with
 *   `createElement` and `textContent`, so no request is made and no broken image shows.
 *   `srcset` and `sizes` are dropped from every image: the browser would pick from
 *   `srcset` instead of `src` (Story 19.3, VSS-my4c). Nothing is rewritten to `https`.
 * - `<style>` elements are removed: DOMPurify keeps one that follows body content,
 *   and it would restyle the whole app, not just the description.
 * - Forms and their controls are removed.
 */

import DOMPurify, { type Config } from 'dompurify';

/**
 * Screen reader text after a link that opens in a new tab (Story 18.1). Shared by the
 * description links and the detail page's trailer link so the two cannot drift.
 */
export const OPENS_IN_NEW_TAB = '(opens in a new tab)';

/** Text shown in place of a description image the page cannot load (Story 19.3). */
export const IMAGE_NOT_SHOWN = 'Image not shown';

/** True when an image address is one the Content-Security-Policy lets the page load. */
function isLoadableImage(src: string | null): boolean {
  return src !== null && (/^https:\/\//i.test(src) || /^data:image\//i.test(src));
}

/**
 * Private instance: hooks are per instance, so the link hook below never affects
 * other code that calls the shared `DOMPurify.sanitize`.
 */
const purifier = DOMPurify(window);

const HTML_NAMESPACE = 'http://www.w3.org/1999/xhtml';

purifier.addHook('afterSanitizeAttributes', (node) => {
  if (node.nodeName === 'IMG' && node.namespaceURI === HTML_NAMESPACE) {
    node.removeAttribute('srcset');
    node.removeAttribute('sizes');
    if (!isLoadableImage(node.getAttribute('src'))) {
      const alt = (node.getAttribute('alt') ?? '').trim();
      const note = node.ownerDocument.createElement('span');
      note.setAttribute('data-image-not-shown', '');
      note.textContent = alt ? `${IMAGE_NOT_SHOWN}: ${alt}` : IMAGE_NOT_SHOWN;
      node.replaceWith(note);
    }
    return;
  }

  // nodeName is "A" for HTML links but "a" for SVG links, which carry xlink:href
  const isLink =
    node.nodeName.toLowerCase() === 'a' &&
    (node.hasAttribute('href') || node.hasAttribute('xlink:href'));
  if (isLink) {
    node.setAttribute('target', '_blank');
    node.setAttribute('rel', 'noopener noreferrer');
    // HTML links only. Any marked span already inside the link is removed first: a
    // second pass then still ends with one note, and a marker the mod author wrote
    // cannot stand in for the real note.
    if (node.namespaceURI === HTML_NAMESPACE) {
      for (const existing of Array.from(node.querySelectorAll('[data-new-tab-note]'))) {
        existing.remove();
      }
      const note = node.ownerDocument.createElement('span');
      note.className = 'sr-only';
      note.setAttribute('data-new-tab-note', '');
      note.textContent = ` ${OPENS_IN_NEW_TAB}`;
      node.appendChild(note);
    }
  }
});

/**
 * DOMPurify defaults (images, inline styles kept) minus `<style>` and forms:
 * a form inside the admin UI could pass for one of its own controls.
 */
const DESCRIPTION_CONFIG: Config = {
  FORBID_TAGS: ['style', 'form', 'input', 'button', 'select', 'textarea'],
};

/** Sanitize a mod description for the mod detail page. */
export function sanitizeModDescription(html: string): string {
  return purifier.sanitize(html, DESCRIPTION_CONFIG);
}
