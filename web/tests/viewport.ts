/**
 * Viewport width for tests (Story 16.5).
 *
 * jsdom has no `window.matchMedia` and applies no CSS, so layouts chosen with a media
 * query (see `useMediaQuery`) need a stand-in. This one evaluates `min-width` and
 * `max-width` (in px or rem at 16px) against `window.innerWidth`; a comma-separated
 * list matches when any of its queries does, and a query without a width feature
 * never matches. `setViewportWidth` changes the width and fires `change` on every
 * media query list whose result changed. Wrap it in `act` when components are mounted.
 *
 * `tests/setup.ts` installs the stand-in and calls `resetViewport` after each test, so
 * every test starts at jsdom's default width of 1024px (desktop layouts).
 */

const DEFAULT_WIDTH = 1024;
const ROOT_FONT_SIZE = 16;

const WIDTH_FEATURE = /\(\s*(min|max)-width\s*:\s*([\d.]+)(px|rem)\s*\)/g;

/**
 * Whether `query` matches a viewport `width` px wide. A comma-separated list matches
 * when any of its queries does (as in browsers); a query matches when it has at least
 * one width feature and all of its width features match.
 */
export function evaluateWidthQuery(query: string, width: number): boolean {
  return query.split(',').some((part) => {
    const features = [...part.matchAll(WIDTH_FEATURE)];
    if (features.length === 0) return false;
    return features.every(([, kind, value, unit]) => {
      const px = Number(value) * (unit === 'rem' ? ROOT_FONT_SIZE : 1);
      return kind === 'min' ? width >= px : width <= px;
    });
  });
}

class FakeMediaQueryListEvent extends Event implements MediaQueryListEvent {
  readonly matches: boolean;
  readonly media: string;

  constructor(type: string, init: MediaQueryListEventInit) {
    super(type, init);
    this.matches = init.matches ?? false;
    this.media = init.media ?? '';
  }
}

type ChangeHandler = (this: MediaQueryList, ev: MediaQueryListEvent) => unknown;

class FakeMediaQueryList extends EventTarget implements MediaQueryList {
  readonly media: string;
  onchange: ChangeHandler | null = null;
  private lastMatches: boolean;
  private readonly legacyListeners = new Map<ChangeHandler, EventListener>();

  constructor(media: string) {
    super();
    this.media = media;
    this.lastMatches = this.matches;
  }

  get matches(): boolean {
    return evaluateWidthQuery(this.media, window.innerWidth);
  }

  /** Deprecated alias of addEventListener('change', ...), still part of the interface. */
  addListener(callback: ChangeHandler | null): void {
    if (!callback || this.legacyListeners.has(callback)) return;
    const listener = (event: Event) => {
      if (event instanceof FakeMediaQueryListEvent) callback.call(this, event);
    };
    this.legacyListeners.set(callback, listener);
    this.addEventListener('change', listener);
  }

  /** Deprecated alias of removeEventListener('change', ...), still part of the interface. */
  removeListener(callback: ChangeHandler | null): void {
    const listener = callback && this.legacyListeners.get(callback);
    if (!callback || !listener) return;
    this.legacyListeners.delete(callback);
    this.removeEventListener('change', listener);
  }

  /** Fire `change` if the result differs from the last one seen. */
  notifyIfChanged(): void {
    const matches = this.matches;
    if (matches === this.lastMatches) return;
    this.lastMatches = matches;
    const event = new FakeMediaQueryListEvent('change', { matches, media: this.media });
    this.onchange?.call(this, event);
    this.dispatchEvent(event);
  }
}

const lists = new Set<FakeMediaQueryList>();

function matchMedia(query: string): MediaQueryList {
  const list = new FakeMediaQueryList(query);
  lists.add(list);
  return list;
}

/** Install the `matchMedia` stand-in on `window`. */
export function installMatchMedia(): void {
  Object.defineProperty(window, 'matchMedia', {
    value: matchMedia,
    writable: true,
    configurable: true,
  });
}

/** Set the viewport width and notify media query lists whose result changed. */
export function setViewportWidth(width: number): void {
  Object.defineProperty(window, 'innerWidth', {
    value: width,
    writable: true,
    configurable: true,
  });
  for (const list of lists) list.notifyIfChanged();
}

/** Back to the jsdom default width; forget the lists created by the last test. */
export function resetViewport(): void {
  setViewportWidth(DEFAULT_WIDTH);
  lists.clear();
}
