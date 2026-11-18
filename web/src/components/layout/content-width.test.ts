import { describe, it, expect } from 'vitest';
import { FULL_WIDTH_ROUTES, PAGE_CONTENT_WIDTH } from './content-width';

describe('PAGE_CONTENT_WIDTH (Epic 21 ADR-15, Story 21.8)', () => {
  it('is at most 1280px wide and centered', () => {
    expect(PAGE_CONTENT_WIDTH).toBe('mx-auto max-w-[1280px]');
  });
});

describe('FULL_WIDTH_ROUTES (Epic 21 ADR-15 decision 4, Story 21.8)', () => {
  it('lists the console only', () => {
    expect(FULL_WIDTH_ROUTES).toEqual(['/game-server/console']);
  });
});
