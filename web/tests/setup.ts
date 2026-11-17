import '@testing-library/jest-dom';
import { cleanup } from '@testing-library/react';
import { afterEach, beforeEach, vi } from 'vitest';
import { installMatchMedia, resetViewport } from './viewport';
import { resetTestUrl } from './location';

// Mock ResizeObserver for components like Recharts ResponsiveContainer
class MockResizeObserver {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}
globalThis.ResizeObserver = MockResizeObserver as unknown as typeof ResizeObserver;

// Mock localStorage
class LocalStorageMock {
  store: Record<string, string>;

  constructor() {
    this.store = {};
  }

  getItem(key: string): string | null {
    return this.store[key] || null;
  }

  setItem(key: string, value: string): void {
    this.store[key] = String(value);
  }

  removeItem(key: string): void {
    delete this.store[key];
  }

  clear(): void {
    this.store = {};
  }

  get length(): number {
    return Object.keys(this.store).length;
  }

  key(index: number): string | null {
    const keys = Object.keys(this.store);
    return keys[index] || null;
  }
}

// The DOM steps run only in jsdom; a `@vitest-environment node` file has no window (Story 20.2)
if (typeof window !== 'undefined') {
  // jsdom has no matchMedia; evaluate width queries against innerWidth (Story 16.5)
  installMatchMedia();

  Object.defineProperty(global, 'localStorage', {
    value: new LocalStorageMock(),
    writable: true,
  });
}

// jsdom has no Element.scrollIntoView and only a "not implemented" window.scrollTo.
// Fresh no-op stubs before each test, so a test that installs its own spy cannot leak it
// into the next test or, under vmThreads, the next file (Story 20.2 review)
beforeEach(() => {
  if (typeof window !== 'undefined') {
    Element.prototype.scrollIntoView = () => {};
    vi.stubGlobal('scrollTo', () => {});
  }
});

afterEach(() => {
  if (typeof window !== 'undefined') {
    cleanup();
    resetViewport();
    resetTestUrl();
    // Browse state (search, opened mod) lives in sessionStorage; no test inherits another's
    window.sessionStorage.clear();
  }
  vi.clearAllMocks();
});
