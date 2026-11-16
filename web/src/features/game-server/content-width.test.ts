import { describe, it, expect } from 'vitest';
import { SETTINGS_CONTENT_WIDTH } from './content-width';

describe('SETTINGS_CONTENT_WIDTH (Epic 16 ADR-3, Story 17.8)', () => {
  it('is at most 1280px wide and centered', () => {
    expect(SETTINGS_CONTENT_WIDTH).toBe('mx-auto max-w-[1280px]');
  });
});
