/**
 * Tests for compareVersions (Story 21.5, Epic 21 ADR-8).
 */

import { describe, expect, it } from 'vitest';
import { compareVersionPrecedence, compareVersions } from './version-compare';

function sorted(list: readonly string[]): string[] {
  return [...list].sort(compareVersions);
}

describe('compareVersions', () => {
  describe('orders lists', () => {
    it.each([
      {
        rule: 'bead and AC 1',
        input: ['1.10.0', '1.0.0-rc.12', '1.0.0', '1.9.0', '1.0.0-rc.2'],
        expected: ['1.0.0-rc.2', '1.0.0-rc.12', '1.0.0', '1.9.0', '1.10.0'],
      },
      {
        rule: 'facts sample (ADR-8 decision 5)',
        input: [
          '1.22.0',
          '1.0.1',
          '1.0.0-rc.12',
          '1.10.0',
          '1.0.0',
          '1.22.0-rc.1',
          '1.0.0-pre.1',
          '1.9.0',
          '1.0.0-rc.2',
        ],
        expected: [
          '1.0.0-pre.1',
          '1.0.0-rc.2',
          '1.0.0-rc.12',
          '1.0.0',
          '1.0.1',
          '1.9.0',
          '1.10.0',
          '1.22.0-rc.1',
          '1.22.0',
        ],
      },
      {
        rule: 'unreadable after readable',
        input: ['beta', '1.0.0', '', '1.0.0 hotfix', '0.0.1', 'build 10', 'build 9'],
        expected: ['0.0.1', '1.0.0', '', '1.0.0 hotfix', 'beta', 'build 9', 'build 10'],
      },
    ])('$rule', ({ input, expected }) => {
      expect(sorted(input)).toEqual(expected);
    });
  });

  describe('orders each chain from lowest to highest', () => {
    it.each([
      {
        rule: "Semantic Versioning's own example",
        chain: [
          '1.0.0-alpha',
          '1.0.0-alpha.1',
          '1.0.0-alpha.beta',
          '1.0.0-beta',
          '1.0.0-beta.2',
          '1.0.0-beta.11',
          '1.0.0-rc.1',
          '1.0.0',
        ],
      },
      { rule: 'numeric core 1', chain: ['1.9.0', '1.10.0'] },
      { rule: 'numeric core 2', chain: ['1.10.0', '2.0.0'] },
      { rule: 'numeric core 3', chain: ['0.1.0', '1.0.0-rc.1'] },
      { rule: 'numeric identifiers 1', chain: ['1.0.0-2', '1.0.0-10'] },
      { rule: 'numeric identifiers 2', chain: ['1.0.0-rc.1.2', '1.0.0-rc.1.10'] },
      { rule: 'numeric before alphanumeric 1', chain: ['1.0.0-1', '1.0.0-alpha'] },
      { rule: 'numeric before alphanumeric 2', chain: ['1.0.0-rc.1', '1.0.0-rc.a'] },
      { rule: 'alphanumeric in ASCII order 1', chain: ['1.0.0-RC.1', '1.0.0-rc.1'] },
      { rule: 'alphanumeric in ASCII order 2', chain: ['1.0.0-alpha', '1.0.0-beta'] },
      { rule: 'alphanumeric in ASCII order 3', chain: ['1.0.0-pre.1', '1.0.0-rc.1'] },
      { rule: 'shorter identifier list first 1', chain: ['1.0.0-alpha', '1.0.0-alpha.1'] },
      { rule: 'shorter identifier list first 2', chain: ['1.0.0-rc', '1.0.0-rc.0'] },
      { rule: 'build metadata ignored 1', chain: ['1.0.0-rc.1+build.9', '1.0.0'] },
      { rule: 'build metadata ignored 2', chain: ['1.0.0+zzz', '1.0.1'] },
      { rule: 'build metadata ignored 3', chain: ['1.0.0-rc.2+b', '1.0.0-rc.12+a'] },
      { rule: 'leading v 1', chain: ['1.9.0', 'v1.10.0'] },
      { rule: 'leading v 2', chain: ['v1.0.0', 'V2.0.0'] },
      { rule: 'missing parts 1', chain: ['1.1.9', '1.2'] },
      { rule: 'missing parts 2', chain: ['1.2', '1.2.1'] },
      { rule: 'missing parts 3', chain: ['1', '1.0.1'] },
      { rule: 'missing parts 4', chain: ['1.0.0', '1.0.0.1'] },
      { rule: 'missing parts 5', chain: ['1.2-rc.1', '1.2'] },
    ])('$rule', ({ chain }) => {
      for (let i = 0; i < chain.length - 1; i++) {
        expect(compareVersions(chain[i], chain[i + 1]), `${chain[i]} < ${chain[i + 1]}`).toBe(-1);
        expect(compareVersions(chain[i + 1], chain[i]), `${chain[i + 1]} > ${chain[i]}`).toBe(1);
      }
    });
  });

  describe('malformed strings are unreadable and never throw', () => {
    it.each(['1..0', '.1', '1.0.0-', '1.0.0-rc..1', '1.0.0+', '-1.0.0', '1.0.0 '])(
      '%j sorts after 99.0.0',
      (value) => {
        expect(() => compareVersions(value, '99.0.0')).not.toThrow();
        expect(compareVersions(value, '99.0.0')).toBe(1);
        expect(compareVersions('99.0.0', value)).toBe(-1);
      }
    );
  });

  describe('equal precedence still gives a total order', () => {
    it.each(['1.0.0', 'v1.0.0', '1.0.0-rc.1', 'beta', ''])('%j equals itself', (value) => {
      expect(compareVersions(value, value)).toBe(0);
    });

    it('orders 1.0.0, v1.0.0, 1.0.0+b and 1.0 by the plain strings', () => {
      const same = ['1.0.0', 'v1.0.0', '1.0.0+b', '1.0'];
      for (const a of same) {
        for (const b of same) {
          if (a === b) continue;
          expect(compareVersions(a, b), `${a} vs ${b}`).toBe(a < b ? -1 : 1);
        }
      }
      expect(sorted(['v1.0.0', '1.0.0+b', '1.0', '1.0.0'])).toEqual([
        '1.0',
        '1.0.0',
        '1.0.0+b',
        'v1.0.0',
      ]);
    });
  });

  describe('properties', () => {
    const mixed = [
      '1.10.0',
      '1.0.0',
      'beta',
      '1.0.0-rc.12',
      '1.9.0',
      '1.0.0-rc.2',
      'v1.0.1',
      '1.2',
      '1.0.0+b',
      '1.0.0-alpha',
      '1.0.0-alpha.1',
      '1.0.0-1',
      '1.0.0.1',
      'alpha',
      '',
      '1.0.0 hotfix',
      'v1.0.0',
      '1.22.0-rc.1',
      '1..0',
      '2',
    ];

    it('is antisymmetric for every pair', () => {
      expect(mixed).toHaveLength(20);
      for (const a of mixed) {
        for (const b of mixed) {
          // a sum of 0 (not toBe(-x), which tells 0 from -0)
          expect(compareVersions(a, b) + compareVersions(b, a), `${a} vs ${b}`).toBe(0);
        }
      }
    });

    it('sorts every permutation into the same order', () => {
      const permutations = [
        mixed,
        [...mixed].reverse(),
        [...mixed.slice(10), ...mixed.slice(0, 10)],
        mixed.filter((_, i) => i % 2 === 0).concat(mixed.filter((_, i) => i % 2 === 1)),
        [...mixed.slice(7), ...mixed.slice(0, 7)].reverse(),
      ];
      const expected = [
        '1.0.0-1',
        '1.0.0-alpha',
        '1.0.0-alpha.1',
        '1.0.0-rc.2',
        '1.0.0-rc.12',
        '1.0.0',
        '1.0.0+b',
        'v1.0.0',
        '1.0.0.1',
        'v1.0.1',
        '1.2',
        '1.9.0',
        '1.10.0',
        '1.22.0-rc.1',
        '2',
        '',
        '1..0',
        '1.0.0 hotfix',
        'alpha',
        'beta',
      ];
      for (const permutation of permutations) {
        expect(sorted(permutation)).toEqual(expected);
      }
    });
  });
});

describe('compareVersionPrecedence (Story 21.5 review)', () => {
  it.each([
    ['1.0.0', 'v1.0.0'],
    ['1.0.0', '1.0.0+build'],
    ['1.0.0', '01.0.0'],
    ['1.0', '1.0.0'],
    ['1.0.0-rc.1', '1.0.0-rc.1+b'],
    ['beta', 'beta'],
  ])('%j and %j have equal precedence', (a, b) => {
    expect(compareVersionPrecedence(a, b)).toBe(0);
    expect(compareVersionPrecedence(b, a)).toBe(0);
  });

  it.each([
    ['1.0.0-rc.2', '1.0.0-rc.12'],
    ['1.0.0-rc.12', '1.0.0'],
    ['1.9.0', '1.10.0'],
    ['1.0.0', 'beta'],
    ['beta', 'build'],
  ])('%j has lower precedence than %j', (a, b) => {
    expect(compareVersionPrecedence(a, b)).toBe(-1);
    expect(compareVersionPrecedence(b, a)).toBe(1);
  });

  it('agrees with compareVersions whenever the precedence differs', () => {
    const list = ['1.0.0', 'v1.0.0', '1.0.0-rc.2', '1.2', 'beta', '', '1.0.0+b', '2'];
    for (const a of list) {
      for (const b of list) {
        const precedence = compareVersionPrecedence(a, b);
        if (precedence !== 0) expect(compareVersions(a, b), `${a} vs ${b}`).toBe(precedence);
      }
    }
  });
});
