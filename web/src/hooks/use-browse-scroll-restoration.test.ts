/**
 * Tests for returning to the opened mod card in the browser.
 *
 * Story 10.7: Scroll restoration after viewing mod details.
 * Story 16.1: Rewritten for Epic 16 ADR-1: the position is the opened card's slug,
 * restored only on a return from its detail page, instead of `{ scrollY, page }`
 * restored after a 100 ms timeout on any mount.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import {
  BROWSE_OPENED_MOD_KEY,
  saveOpenedMod,
  readOpenedMod,
  clearOpenedMod,
  shouldRestoreOpenedMod,
  scrollToModCard,
  useBrowseScrollRestoration,
} from './use-browse-scroll-restoration';

const scrollIntoView = vi.fn();

function addCard(slug: string): HTMLElement {
  const card = document.createElement('div');
  card.setAttribute('data-testid', `mod-card-${slug}`);
  document.body.appendChild(card);
  return card;
}

beforeEach(() => {
  sessionStorage.clear();
  document.body.innerHTML = '';
  scrollIntoView.mockClear();
  Element.prototype.scrollIntoView = scrollIntoView;
  window.scrollTo = vi.fn();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('opened mod entry (sessionStorage)', () => {
  it('uses its own key, not the retired browse-scroll-position', () => {
    expect(BROWSE_OPENED_MOD_KEY).toBe('browse-opened-mod');
  });

  it('saves and reads the browse search and slug', () => {
    saveOpenedMod({ search: '?q=food&version=1.22.7&page=2', slug: 'carryon' });
    expect(JSON.parse(sessionStorage.getItem(BROWSE_OPENED_MOD_KEY) ?? '')).toEqual({
      search: '?q=food&version=1.22.7&page=2',
      slug: 'carryon',
    });
    expect(readOpenedMod()).toEqual({ search: '?q=food&version=1.22.7&page=2', slug: 'carryon' });
  });

  it('reading does not consume the entry', () => {
    saveOpenedMod({ search: '', slug: 'carryon' });
    readOpenedMod();
    expect(readOpenedMod()).toEqual({ search: '', slug: 'carryon' });
  });

  it('clears the entry', () => {
    saveOpenedMod({ search: '', slug: 'carryon' });
    clearOpenedMod();
    expect(readOpenedMod()).toBeNull();
  });

  it.each([
    ['nothing saved', null],
    ['invalid JSON', '{not json'],
    ['the retired { scrollY, page } shape', JSON.stringify({ scrollY: 500, page: 2 })],
    ['a non-string slug', JSON.stringify({ search: '', slug: 5 })],
    ['an empty slug', JSON.stringify({ search: '', slug: '' })],
    ['a search that is not a query string', JSON.stringify({ search: '/x', slug: 'a' })],
  ])('reads null for %s', (_name, stored) => {
    if (stored !== null) sessionStorage.setItem(BROWSE_OPENED_MOD_KEY, stored);
    expect(readOpenedMod()).toBeNull();
  });

  it('survives sessionStorage being unavailable', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('denied');
    });
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('denied');
    });
    vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => {
      throw new Error('denied');
    });
    expect(() => saveOpenedMod({ search: '', slug: 'a' })).not.toThrow();
    expect(() => clearOpenedMod()).not.toThrow();
    expect(readOpenedMod()).toBeNull();
  });
});

describe('shouldRestoreOpenedMod', () => {
  const saved = { search: '?version=1.22.7&page=2', slug: 'carryon' };

  it('restores on a return to the same browse search', () => {
    expect(shouldRestoreOpenedMod(saved, '?version=1.22.7&page=2', true)).toBe(true);
  });

  it('does not restore when the arrival is not a return from the detail page', () => {
    expect(shouldRestoreOpenedMod(saved, '?version=1.22.7&page=2', false)).toBe(false);
  });

  it('does not restore for a different browse search', () => {
    expect(shouldRestoreOpenedMod(saved, '?version=1.22.6&page=2', true)).toBe(false);
    expect(shouldRestoreOpenedMod(saved, '?version=1.22.7', true)).toBe(false);
  });

  it('does not restore without a saved entry', () => {
    expect(shouldRestoreOpenedMod(null, '', true)).toBe(false);
  });
});

describe('scrollToModCard', () => {
  it('centers the card in the viewport', () => {
    const card = addCard('carryon');
    expect(scrollToModCard('carryon')).toBe(true);
    expect(scrollIntoView).toHaveBeenCalledTimes(1);
    expect(scrollIntoView.mock.contexts[0]).toBe(card);
    expect(scrollIntoView).toHaveBeenCalledWith({ block: 'center' });
  });

  it('returns false when the card is not rendered', () => {
    expect(scrollToModCard('missing')).toBe(false);
    expect(scrollIntoView).not.toHaveBeenCalled();
  });

  it('handles slugs with selector characters', () => {
    addCard('odd"slug]');
    expect(scrollToModCard('odd"slug]')).toBe(true);
  });
});

describe('useBrowseScrollRestoration', () => {
  interface Props {
    currentSearch: string;
    isReturn: boolean;
    renderedSlugs: string[];
    isReady: boolean;
  }

  function renderRestoration(initial: Props) {
    return renderHook((props: Props) => useBrowseScrollRestoration(props), {
      initialProps: initial,
    });
  }

  it('scrolls to the opened card once the results containing it are ready, then stops', () => {
    saveOpenedMod({ search: '?version=1.22.7&page=2', slug: 'carryon' });
    const { rerender } = renderRestoration({
      currentSearch: '?version=1.22.7&page=2',
      isReturn: true,
      renderedSlugs: [],
      isReady: false,
    });
    expect(scrollIntoView).not.toHaveBeenCalled();

    addCard('carryon');
    rerender({
      currentSearch: '?version=1.22.7&page=2',
      isReturn: true,
      renderedSlugs: ['other', 'carryon'],
      isReady: true,
    });
    expect(scrollIntoView).toHaveBeenCalledTimes(1);

    // Later renders (a refetch, a page change) do not scroll again
    rerender({
      currentSearch: '?version=1.22.7&page=3',
      isReturn: true,
      renderedSlugs: ['carryon'],
      isReady: true,
    });
    expect(scrollIntoView).toHaveBeenCalledTimes(1);
  });

  it('leaves the page at the top when the opened card is no longer in the results', () => {
    saveOpenedMod({ search: '', slug: 'carryon' });
    renderRestoration({ currentSearch: '', isReturn: true, renderedSlugs: ['other'], isReady: true });
    expect(scrollIntoView).not.toHaveBeenCalled();
    expect(window.scrollTo).toHaveBeenCalledWith({ top: 0, behavior: 'instant' });
  });

  it.each([
    ['a mount that is not a return (detour)', { currentSearch: '', isReturn: false }],
    ['a different browse search', { currentSearch: '?q=other', isReturn: true }],
  ])('does not scroll for %s', (_name, props) => {
    saveOpenedMod({ search: '', slug: 'carryon' });
    addCard('carryon');
    renderRestoration({ ...props, renderedSlugs: ['carryon'], isReady: true });
    expect(scrollIntoView).not.toHaveBeenCalled();
    expect(window.scrollTo).not.toHaveBeenCalled();
  });

  it('does nothing on a mount without a saved entry (refresh or first load)', () => {
    addCard('carryon');
    renderRestoration({ currentSearch: '', isReturn: true, renderedSlugs: ['carryon'], isReady: true });
    expect(scrollIntoView).not.toHaveBeenCalled();
    expect(window.scrollTo).not.toHaveBeenCalled();
  });

  it.each([
    ['restored', { currentSearch: '', isReturn: true }],
    ['not a return', { currentSearch: '', isReturn: false }],
    ['a different search', { currentSearch: '?q=x', isReturn: true }],
  ])('consumes or clears the entry on every mount (%s)', (_name, props) => {
    saveOpenedMod({ search: '', slug: 'carryon' });
    renderRestoration({ ...props, renderedSlugs: [], isReady: false });
    expect(readOpenedMod()).toBeNull();
  });

  it('saveOpenedMod saves the current browse search with the slug', () => {
    const { result } = renderRestoration({
      currentSearch: '?q=food&version=1.22.7',
      isReturn: false,
      renderedSlugs: [],
      isReady: false,
    });
    act(() => {
      result.current.saveOpenedMod('carryon');
    });
    expect(readOpenedMod()).toEqual({ search: '?q=food&version=1.22.7', slug: 'carryon' });
  });

  it('does not use timers', () => {
    const setTimeoutSpy = vi.spyOn(globalThis, 'setTimeout');
    saveOpenedMod({ search: '', slug: 'carryon' });
    addCard('carryon');
    renderRestoration({ currentSearch: '', isReturn: true, renderedSlugs: ['carryon'], isReady: true });
    expect(scrollIntoView).toHaveBeenCalledTimes(1);
    expect(setTimeoutSpy).not.toHaveBeenCalled();
  });
});
