import { describe, it, expect } from 'vitest';
import { isServerInstalled } from './server-utils';
import type { ServerState } from '@/api/types';

describe('server-utils', () => {
  describe('isServerInstalled', () => {
    describe('returns false for not-installed states', () => {
      it('returns false for "not_installed" state', () => {
        expect(isServerInstalled('not_installed')).toBe(false);
      });

      it('returns false for "installing" state', () => {
        expect(isServerInstalled('installing')).toBe(false);
      });
    });

    describe('returns true for installed states', () => {
      it('returns true for "installed" state (stopped)', () => {
        expect(isServerInstalled('installed')).toBe(true);
      });

      it('returns true for "starting" state', () => {
        expect(isServerInstalled('starting')).toBe(true);
      });

      it('returns true for "running" state', () => {
        expect(isServerInstalled('running')).toBe(true);
      });

      it('returns true for "stopping" state', () => {
        expect(isServerInstalled('stopping')).toBe(true);
      });

      it('returns true for "error" state', () => {
        expect(isServerInstalled('error')).toBe(true);
      });
    });

    describe('handles all ServerState enum values', () => {
      it('covers all possible server states', () => {
        const allStates: ServerState[] = [
          'not_installed',
          'installing',
          'installed',
          'starting',
          'running',
          'stopping',
          'error',
        ];

        const results = allStates.map((state) => ({
          state,
          isInstalled: isServerInstalled(state),
        }));

        // Should have exactly 2 false values (not_installed, installing)
        const falseCount = results.filter((r) => !r.isInstalled).length;
        expect(falseCount).toBe(2);

        // Should have exactly 5 true values (all other states)
        const trueCount = results.filter((r) => r.isInstalled).length;
        expect(trueCount).toBe(5);
      });
    });
  });
});
