import { describe, it, expect } from 'vitest';
import {
  BROWSE_CARD_DEFAULT_STATUS,
  getBrowseCardCompatibility,
  checkVersionCompatibility,
} from './mod-compatibility';

describe('mod-compatibility', () => {
  describe('BROWSE_CARD_DEFAULT_STATUS', () => {
    it('is set to not_verified', () => {
      expect(BROWSE_CARD_DEFAULT_STATUS).toBe('not_verified');
    });
  });

  describe('getBrowseCardCompatibility', () => {
    it('returns not_verified for browse cards', () => {
      const status = getBrowseCardCompatibility();
      expect(status).toBe('not_verified');
    });

    it('always returns the same value (conservative default)', () => {
      // Call multiple times to ensure consistency
      const results = [
        getBrowseCardCompatibility(),
        getBrowseCardCompatibility(),
        getBrowseCardCompatibility(),
      ];
      expect(results.every((r) => r === 'not_verified')).toBe(true);
    });
  });

  describe('checkVersionCompatibility', () => {
    it('returns not_verified as placeholder (Story 10.6 will implement)', () => {
      const status = checkVersionCompatibility(['1.19.8', '1.20.0'], '1.19.8');
      expect(status).toBe('not_verified');
    });

    it('handles null server version', () => {
      const status = checkVersionCompatibility(['1.19.8'], null);
      expect(status).toBe('not_verified');
    });

    it('handles empty mod versions array', () => {
      const status = checkVersionCompatibility([], '1.19.8');
      expect(status).toBe('not_verified');
    });
  });
});
