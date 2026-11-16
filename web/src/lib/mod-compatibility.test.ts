import { describe, it, expect } from 'vitest';
import { checkVersionCompatibility } from './mod-compatibility';

describe('mod-compatibility', () => {
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
