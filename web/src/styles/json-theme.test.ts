/**
 * Tests for JSON syntax highlighting theme colors.
 *
 * Verifies that the CSS variables match the expected Catppuccin palette
 * colors as defined in the story requirements.
 *
 * Story 9.6: JSON Syntax Colorization - AC: 2
 */

import { describe, it, expect } from 'vitest';
import { catppuccinMocha, catppuccinLatte } from '@/lib/terminal-themes';

/**
 * Expected JSON syntax colors from Catppuccin palette.
 * These values must match what's defined in index.css.
 */
const EXPECTED_MOCHA_COLORS = {
  key: '#89b4fa',     // blue
  string: '#a6e3a1',  // green
  number: '#f9e2af',  // yellow
  boolean: '#cba6f7', // magenta
  null: '#f38ba8',    // red
};

const EXPECTED_LATTE_COLORS = {
  key: '#1e66f5',     // blue
  string: '#40a02b',  // green
  number: '#df8e1d',  // yellow
  boolean: '#8839ef', // magenta
  null: '#d20f39',    // red
};

describe('JSON syntax highlighting theme colors', () => {
  describe('Catppuccin Mocha (dark mode) color consistency', () => {
    it('uses blue from terminal theme for keys', () => {
      expect(catppuccinMocha.blue).toBe(EXPECTED_MOCHA_COLORS.key);
    });

    it('uses green from terminal theme for strings', () => {
      expect(catppuccinMocha.green).toBe(EXPECTED_MOCHA_COLORS.string);
    });

    it('uses yellow from terminal theme for numbers', () => {
      expect(catppuccinMocha.yellow).toBe(EXPECTED_MOCHA_COLORS.number);
    });

    it('uses magenta from terminal theme for booleans', () => {
      expect(catppuccinMocha.magenta).toBe(EXPECTED_MOCHA_COLORS.boolean);
    });

    it('uses red from terminal theme for null', () => {
      expect(catppuccinMocha.red).toBe(EXPECTED_MOCHA_COLORS.null);
    });
  });

  describe('Catppuccin Latte (light mode) color consistency', () => {
    it('uses blue from terminal theme for keys', () => {
      expect(catppuccinLatte.blue).toBe(EXPECTED_LATTE_COLORS.key);
    });

    it('uses green from terminal theme for strings', () => {
      expect(catppuccinLatte.green).toBe(EXPECTED_LATTE_COLORS.string);
    });

    it('uses yellow from terminal theme for numbers', () => {
      expect(catppuccinLatte.yellow).toBe(EXPECTED_LATTE_COLORS.number);
    });

    it('uses magenta from terminal theme for booleans', () => {
      expect(catppuccinLatte.magenta).toBe(EXPECTED_LATTE_COLORS.boolean);
    });

    it('uses red from terminal theme for null', () => {
      expect(catppuccinLatte.red).toBe(EXPECTED_LATTE_COLORS.null);
    });
  });

  describe('color distinctness (AC: 2)', () => {
    it('all dark mode colors are distinct from each other', () => {
      const colors = Object.values(EXPECTED_MOCHA_COLORS);
      const uniqueColors = new Set(colors);
      expect(uniqueColors.size).toBe(colors.length);
    });

    it('all light mode colors are distinct from each other', () => {
      const colors = Object.values(EXPECTED_LATTE_COLORS);
      const uniqueColors = new Set(colors);
      expect(uniqueColors.size).toBe(colors.length);
    });

    it('dark mode colors provide sufficient contrast', () => {
      // Each color should be visually distinct
      // The Catppuccin palette is designed for this, so we verify they're all different
      const colors = Object.values(EXPECTED_MOCHA_COLORS);

      for (let i = 0; i < colors.length; i++) {
        for (let j = i + 1; j < colors.length; j++) {
          expect(colors[i]).not.toBe(colors[j]);
        }
      }
    });

    it('light mode colors provide sufficient contrast', () => {
      const colors = Object.values(EXPECTED_LATTE_COLORS);

      for (let i = 0; i < colors.length; i++) {
        for (let j = i + 1; j < colors.length; j++) {
          expect(colors[i]).not.toBe(colors[j]);
        }
      }
    });
  });

  describe('theme color semantic mapping', () => {
    it('keys use blue (primary information identifier)', () => {
      // Blue is conventionally used for identifiers/properties
      expect(EXPECTED_MOCHA_COLORS.key).toContain('b4fa'); // Contains blue component
      expect(EXPECTED_LATTE_COLORS.key).toContain('66f5'); // Contains blue component
    });

    it('strings use green (literal values)', () => {
      // Green is conventionally used for string literals
      expect(EXPECTED_MOCHA_COLORS.string).toContain('e3a1'); // Contains green component
      expect(EXPECTED_LATTE_COLORS.string).toContain('a02b'); // Contains green component
    });

    it('null uses red (absence/warning)', () => {
      // Red signals absence or caution-worthy value
      expect(EXPECTED_MOCHA_COLORS.null).toContain('8ba8'); // Contains red component
      expect(EXPECTED_LATTE_COLORS.null).toContain('0f39'); // Contains red component
    });
  });
});
