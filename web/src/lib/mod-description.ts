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
 *   `.mod-description` container. An SVG link cannot hold an HTML span; it gets one SVG
 *   `<title>` as its first child instead, "<its text> (opens in a new tab)", and an
 *   `xlink:href`-only link also gets the same `href`, without which Chromium does not
 *   expose it as a link (Story 21.6, VSS-woae, Epic 21 ADR-10 decisions 4 to 6).
 * - An HTML `<img>` loads only from an `https://` or `data:image/` address, which the
 *   web UI's Content-Security-Policy allows (Epic 19 ADR-6 decision 14). Any other image
 *   is replaced by `<span data-image-not-shown>Image not shown: <alt></span>`, built with
 *   `createElement` and `textContent`, so no request is made and no broken image shows.
 *   `srcset` and `sizes` are dropped from every image: the browser would pick from
 *   `srcset` instead of `src` (Story 19.3, VSS-my4c). Nothing is rewritten to `https`.
 * - Story 24.8 (VSS-koo1, Epic 24 ADR-7): a `<video>` or `<audio>` is replaced by
 *   `<span data-media-not-shown>Video not shown</span>` (the policy has no `media-src`);
 *   every `<source>` is dropped, so a `<picture>`'s `<img>` (checked as above) is used; an
 *   SVG `<image>` or `<feImage>` from an address the policy refuses is removed (an SVG cannot hold an
 *   HTML note); the `background` attribute is removed; an inline style declaration
 *   whose `url()` the policy refuses is removed. The policy itself is not widened.
 * - `<style>` elements are removed: DOMPurify keeps one that follows body content,
 *   and it would restyle the whole app, not just the description.
 * - Forms and their controls are removed.
 */

import DOMPurify, { type Config } from 'dompurify';
import { OPENS_IN_NEW_TAB } from './new-tab';

// Re-exported for the callers and tests that imported it from here before Story 21.6
export { OPENS_IN_NEW_TAB };

/** Text shown in place of a description image the page cannot load (Story 19.3). */
export const IMAGE_NOT_SHOWN = 'Image not shown';

/** Text shown in place of a description video or audio (Story 24.8): no media-src. */
export const VIDEO_NOT_SHOWN = 'Video not shown';
export const AUDIO_NOT_SHOWN = 'Audio not shown';

const CSS_URL = /url\(\s*(['"]?)(.*?)\1\s*\)/gi;

/** True when every url() in a CSS value is one the policy lets the page load. */
function cssUrlsLoadable(value: string): boolean {
  return Array.from(value.matchAll(CSS_URL)).every(([, , url]) => isLoadableImage(url));
}

/** Story 24.8: replace a video or audio, which the policy never loads, by a note. */
function replaceMedia(node: Element, text: string): void {
  const label = (node.getAttribute('title') ?? node.getAttribute('aria-label') ?? '').trim();
  const note = node.ownerDocument.createElement('span');
  note.setAttribute('data-media-not-shown', '');
  note.textContent = label ? `${text}: ${label}` : text;
  node.replaceWith(note);
}

/** Story 24.8: drop inline style declarations whose url() the policy refuses. */
function removeBlockedStyleUrls(node: Element): void {
  if (!(node instanceof HTMLElement || node instanceof SVGElement)) return;
  const style = node.style;
  for (const property of Array.from(style)) {
    if (!cssUrlsLoadable(style.getPropertyValue(property))) {
      style.removeProperty(property);
    }
  }
  if (style.length === 0) node.removeAttribute('style');
}

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
const SVG_NAMESPACE = 'http://www.w3.org/2000/svg';

/** Collapse runs of whitespace to one space and trim. */
function collapse(text: string): string {
  return text.replace(/\s+/g, ' ').trim();
}

/** Remove every trailing new-tab note (and the space before it) from a title's text. */
function stripNote(text: string): string {
  let base = collapse(text);
  while (base.endsWith(OPENS_IN_NEW_TAB)) {
    base = base.slice(0, -OPENS_IN_NEW_TAB.length).trim();
  }
  return base;
}

/**
 * Give an SVG link one `<title>` naming it and the new tab (Story 21.6). The base text is
 * the author's first title, else the text of the link's `text` elements, without any note.
 * Every existing title is removed and the new one, built with `textContent`, goes first, so
 * a second pass gives the same single title and an author's title cannot stand in for the
 * note. The `href` copied from `xlink:href` has already passed DOMPurify's URI check.
 */
function addSvgLinkTitle(link: Element) {
  const xlinkHref = link.getAttribute('xlink:href');
  if (!link.hasAttribute('href') && xlinkHref !== null) {
    link.setAttribute('href', xlinkHref);
  }

  const titles = Array.from(link.children).filter((child) => child.localName === 'title');
  let base = titles.length > 0 ? stripNote(titles[0].textContent ?? '') : '';
  if (!base) {
    base = stripNote(
      Array.from(link.querySelectorAll('text'))
        .map((text) => text.textContent ?? '')
        .join(' ')
    );
  }
  for (const title of titles) {
    title.remove();
  }

  const title = link.ownerDocument.createElementNS(SVG_NAMESPACE, 'title');
  title.textContent = base ? `${base} ${OPENS_IN_NEW_TAB}` : OPENS_IN_NEW_TAB;
  link.insertBefore(title, link.firstChild);
}

purifier.addHook('afterSanitizeAttributes', (node) => {
  // Story 24.8 (Epic 24 ADR-7): media the policy blocks never reaches the page silently
  if (node.namespaceURI === HTML_NAMESPACE) {
    if (node.nodeName === 'VIDEO') return replaceMedia(node, VIDEO_NOT_SHOWN);
    if (node.nodeName === 'AUDIO') return replaceMedia(node, AUDIO_NOT_SHOWN);
    // A picture's sources would be chosen over its image, which is checked below; a
    // source anywhere else fetches nothing, so every one is dropped (review L-1)
    if (node.nodeName === 'SOURCE') {
      node.remove();
      return;
    }
  }
  // <feImage> loads an image as <image> does (review M-1)
  if (
    (node.nodeName === 'image' || node.nodeName === 'feImage') &&
    node.namespaceURI === SVG_NAMESPACE
  ) {
    const href = node.getAttribute('href') ?? node.getAttribute('xlink:href');
    if (!isLoadableImage(href)) {
      node.remove();
      return;
    }
  }
  node.removeAttribute('background');
  if (node.hasAttribute('style')) removeBlockedStyleUrls(node);

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
    } else if (node.namespaceURI === SVG_NAMESPACE) {
      addSvgLinkTitle(node);
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
