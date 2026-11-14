import { describe, it, expect } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import { setViewportWidth } from '../../tests/viewport';
import { useMediaQuery, MD_UP_QUERY } from './use-media-query';

describe('useMediaQuery (Story 16.5)', () => {
  it('matches md and up at the default jsdom width of 1024px', () => {
    const { result } = renderHook(() => useMediaQuery(MD_UP_QUERY));
    expect(result.current).toBe(true);
  });

  it.each([
    [768, true],
    [767, false],
    [390, false],
  ])('at %ipx md-and-up is %s', (width, expected) => {
    setViewportWidth(width);
    const { result } = renderHook(() => useMediaQuery(MD_UP_QUERY));
    expect(result.current).toBe(expected);
  });

  it('updates when the viewport crosses the breakpoint', () => {
    const { result } = renderHook(() => useMediaQuery(MD_UP_QUERY));
    expect(result.current).toBe(true);

    act(() => setViewportWidth(390));
    expect(result.current).toBe(false);

    act(() => setViewportWidth(1440));
    expect(result.current).toBe(true);
  });

  it('stops listening after unmount', () => {
    const { result, unmount } = renderHook(() => useMediaQuery(MD_UP_QUERY));
    const last = result.current;
    unmount();
    // Would warn about an update on an unmounted component if still subscribed
    act(() => setViewportWidth(390));
    expect(result.current).toBe(last);
  });
});

describe('matchMedia test stand-in', () => {
  it('evaluates min-width and max-width in px and rem against innerWidth', () => {
    setViewportWidth(800);
    expect(window.matchMedia('(min-width: 48rem)').matches).toBe(true);
    expect(window.matchMedia('(min-width: 801px)').matches).toBe(false);
    expect(window.matchMedia('(max-width: 800px)').matches).toBe(true);
    expect(window.matchMedia('(max-width: 50rem)').matches).toBe(true);
    expect(window.matchMedia('(prefers-color-scheme: dark)').matches).toBe(false);
  });

  it('treats a comma-separated query list as OR, as browsers do', () => {
    setViewportWidth(390);
    expect(window.matchMedia('(min-width: 1024px), (max-width: 400px)').matches).toBe(true);
    setViewportWidth(800);
    expect(window.matchMedia('(min-width: 1024px), (max-width: 400px)').matches).toBe(false);
    expect(window.matchMedia('(min-width: 1024px), (prefers-color-scheme: dark)').matches).toBe(
      false
    );
    expect(window.matchMedia('(min-width: 1024px), (max-width: 50rem)').matches).toBe(true);
  });

  it('notifies only listeners whose result changed', () => {
    const md = window.matchMedia('(min-width: 768px)');
    const lg = window.matchMedia('(min-width: 1024px)');
    const mdEvents: boolean[] = [];
    const lgEvents: boolean[] = [];
    md.addEventListener('change', (event) => mdEvents.push(event.matches));
    lg.addEventListener('change', (event) => lgEvents.push(event.matches));

    setViewportWidth(900);
    expect(mdEvents).toEqual([]);
    expect(lgEvents).toEqual([false]);

    setViewportWidth(390);
    expect(mdEvents).toEqual([false]);
    expect(lgEvents).toEqual([false]);
  });

  it('starts every test at the jsdom default width', () => {
    expect(window.innerWidth).toBe(1024);
  });
});
