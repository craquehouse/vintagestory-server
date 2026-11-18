/**
 * Tests for ariaSort (Story 21.5, Epic 21 ADR-9).
 */

import { describe, expect, it } from 'vitest';
import { ariaSort } from './table-aria-sort';

interface Row {
  canSort: boolean;
  sorted: false | 'asc' | 'desc';
  expected: ReturnType<typeof ariaSort>;
}

const rows: Row[] = [
  { canSort: true, sorted: 'asc', expected: 'ascending' },
  { canSort: true, sorted: 'desc', expected: 'descending' },
  { canSort: true, sorted: false, expected: 'none' },
  { canSort: false, sorted: false, expected: undefined },
];

describe('ariaSort', () => {
  it.each(rows)('($canSort, $sorted) gives $expected', ({ canSort, sorted, expected }) => {
    expect(ariaSort(canSort, sorted)).toBe(expected);
  });
});
