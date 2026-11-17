// @vitest-environment node
import { describe, it, expect } from 'vitest';
import { getCookie, setCookie, deleteCookie } from './cookies';

// The node environment has no document, as during server-side rendering.
describe('SSR compatibility', () => {
  it('getCookie returns null when document is undefined', () => {
    expect(typeof document).toBe('undefined');
    expect(getCookie('any')).toBeNull();
  });

  it('setCookie does nothing when document is undefined', () => {
    expect(() => setCookie('ssr-test', 'value')).not.toThrow();
  });

  it('deleteCookie does nothing when document is undefined', () => {
    expect(() => deleteCookie('ssr-delete-test')).not.toThrow();
  });
});
