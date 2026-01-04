import { describe, it, expect } from 'vitest';
import {
  catppuccinMocha,
  catppuccinLatte,
  getTerminalTheme,
} from './terminal-themes';

describe('terminal-themes', () => {
  describe('catppuccinMocha (dark theme)', () => {
    it('has valid hex color values for all required ITheme properties', () => {
      const hexColorRegex = /^#[0-9a-fA-F]{6}$/;

      // Core colors
      expect(catppuccinMocha.background).toMatch(hexColorRegex);
      expect(catppuccinMocha.foreground).toMatch(hexColorRegex);
      expect(catppuccinMocha.cursor).toMatch(hexColorRegex);
      expect(catppuccinMocha.cursorAccent).toMatch(hexColorRegex);
      expect(catppuccinMocha.selectionBackground).toMatch(hexColorRegex);
      expect(catppuccinMocha.selectionForeground).toMatch(hexColorRegex);

      // ANSI colors
      expect(catppuccinMocha.black).toMatch(hexColorRegex);
      expect(catppuccinMocha.red).toMatch(hexColorRegex);
      expect(catppuccinMocha.green).toMatch(hexColorRegex);
      expect(catppuccinMocha.yellow).toMatch(hexColorRegex);
      expect(catppuccinMocha.blue).toMatch(hexColorRegex);
      expect(catppuccinMocha.magenta).toMatch(hexColorRegex);
      expect(catppuccinMocha.cyan).toMatch(hexColorRegex);
      expect(catppuccinMocha.white).toMatch(hexColorRegex);

      // Bright ANSI colors
      expect(catppuccinMocha.brightBlack).toMatch(hexColorRegex);
      expect(catppuccinMocha.brightRed).toMatch(hexColorRegex);
      expect(catppuccinMocha.brightGreen).toMatch(hexColorRegex);
      expect(catppuccinMocha.brightYellow).toMatch(hexColorRegex);
      expect(catppuccinMocha.brightBlue).toMatch(hexColorRegex);
      expect(catppuccinMocha.brightMagenta).toMatch(hexColorRegex);
      expect(catppuccinMocha.brightCyan).toMatch(hexColorRegex);
      expect(catppuccinMocha.brightWhite).toMatch(hexColorRegex);
    });

    it('uses correct Catppuccin Mocha mantle color for background', () => {
      // Using mantle (#181825) for terminal background to match app's --background
      expect(catppuccinMocha.background).toBe('#181825');
    });

    it('uses correct Catppuccin Mocha text color for foreground', () => {
      // Mocha text color is #cdd6f4
      expect(catppuccinMocha.foreground).toBe('#cdd6f4');
    });

    it('has dark background (low luminance)', () => {
      // Parse hex to RGB and check luminance is low
      const hex = catppuccinMocha.background as string;
      const r = parseInt(hex.slice(1, 3), 16);
      const g = parseInt(hex.slice(3, 5), 16);
      const b = parseInt(hex.slice(5, 7), 16);

      // Simple luminance check - dark themes should have low values
      const avgLuminance = (r + g + b) / 3;
      expect(avgLuminance).toBeLessThan(100); // Dark themes have low luminance
    });
  });

  describe('catppuccinLatte (light theme)', () => {
    it('has valid hex color values for all required ITheme properties', () => {
      const hexColorRegex = /^#[0-9a-fA-F]{6}$/;

      // Core colors
      expect(catppuccinLatte.background).toMatch(hexColorRegex);
      expect(catppuccinLatte.foreground).toMatch(hexColorRegex);
      expect(catppuccinLatte.cursor).toMatch(hexColorRegex);
      expect(catppuccinLatte.cursorAccent).toMatch(hexColorRegex);
      expect(catppuccinLatte.selectionBackground).toMatch(hexColorRegex);
      expect(catppuccinLatte.selectionForeground).toMatch(hexColorRegex);

      // ANSI colors
      expect(catppuccinLatte.black).toMatch(hexColorRegex);
      expect(catppuccinLatte.red).toMatch(hexColorRegex);
      expect(catppuccinLatte.green).toMatch(hexColorRegex);
      expect(catppuccinLatte.yellow).toMatch(hexColorRegex);
      expect(catppuccinLatte.blue).toMatch(hexColorRegex);
      expect(catppuccinLatte.magenta).toMatch(hexColorRegex);
      expect(catppuccinLatte.cyan).toMatch(hexColorRegex);
      expect(catppuccinLatte.white).toMatch(hexColorRegex);

      // Bright ANSI colors
      expect(catppuccinLatte.brightBlack).toMatch(hexColorRegex);
      expect(catppuccinLatte.brightRed).toMatch(hexColorRegex);
      expect(catppuccinLatte.brightGreen).toMatch(hexColorRegex);
      expect(catppuccinLatte.brightYellow).toMatch(hexColorRegex);
      expect(catppuccinLatte.brightBlue).toMatch(hexColorRegex);
      expect(catppuccinLatte.brightMagenta).toMatch(hexColorRegex);
      expect(catppuccinLatte.brightCyan).toMatch(hexColorRegex);
      expect(catppuccinLatte.brightWhite).toMatch(hexColorRegex);
    });

    it('uses correct Catppuccin Latte base color for background', () => {
      // Latte base color is #eff1f5
      expect(catppuccinLatte.background).toBe('#eff1f5');
    });

    it('uses correct Catppuccin Latte text color for foreground', () => {
      // Latte text color is #4c4f69
      expect(catppuccinLatte.foreground).toBe('#4c4f69');
    });

    it('has light background (high luminance)', () => {
      // Parse hex to RGB and check luminance is high
      const hex = catppuccinLatte.background as string;
      const r = parseInt(hex.slice(1, 3), 16);
      const g = parseInt(hex.slice(3, 5), 16);
      const b = parseInt(hex.slice(5, 7), 16);

      // Simple luminance check - light themes should have high values
      const avgLuminance = (r + g + b) / 3;
      expect(avgLuminance).toBeGreaterThan(200); // Light themes have high luminance
    });
  });

  describe('getTerminalTheme', () => {
    it('returns catppuccinMocha for dark mode', () => {
      const theme = getTerminalTheme('dark');
      expect(theme).toBe(catppuccinMocha);
    });

    it('returns catppuccinLatte for light mode', () => {
      const theme = getTerminalTheme('light');
      expect(theme).toBe(catppuccinLatte);
    });
  });

  describe('ANSI command highlighting (Story 9.5)', () => {
    /**
     * Commands sent via console are echoed with ANSI cyan color codes:
     *   \x1b[36m[CMD] /command\x1b[0m
     *
     * Where:
     *   \x1b[36m = Set foreground to cyan (ANSI color index 6)
     *   \x1b[0m  = Reset all attributes
     *
     * xterm.js uses the theme's 'cyan' property for ANSI color index 6.
     * Server output arrives without ANSI codes, using default foreground.
     */
    it('dark theme defines cyan for command highlighting', () => {
      // Cyan should be defined for ANSI escape code rendering
      expect(catppuccinMocha.cyan).toBe('#89dceb');
    });

    it('light theme defines cyan for command highlighting', () => {
      // Cyan should be defined for ANSI escape code rendering
      expect(catppuccinLatte.cyan).toBe('#04a5e5');
    });

    it('dark theme cyan is distinct from default foreground', () => {
      // Commands should be visually distinct from server output
      expect(catppuccinMocha.cyan).not.toBe(catppuccinMocha.foreground);
    });

    it('light theme cyan is distinct from default foreground', () => {
      // Commands should be visually distinct from server output
      expect(catppuccinLatte.cyan).not.toBe(catppuccinLatte.foreground);
    });

    it('server output uses default foreground (no ANSI codes)', () => {
      // Verify foreground is defined for uncolored server output
      expect(catppuccinMocha.foreground).toBeDefined();
      expect(catppuccinLatte.foreground).toBeDefined();
    });
  });

  describe('theme contrast', () => {
    it('has sufficient contrast between background and foreground in dark theme', () => {
      // Simple contrast check - foreground should be significantly lighter than background
      const bgHex = catppuccinMocha.background as string;
      const fgHex = catppuccinMocha.foreground as string;

      const bgLum =
        (parseInt(bgHex.slice(1, 3), 16) +
          parseInt(bgHex.slice(3, 5), 16) +
          parseInt(bgHex.slice(5, 7), 16)) /
        3;
      const fgLum =
        (parseInt(fgHex.slice(1, 3), 16) +
          parseInt(fgHex.slice(3, 5), 16) +
          parseInt(fgHex.slice(5, 7), 16)) /
        3;

      // In dark theme, foreground should be lighter than background
      expect(fgLum).toBeGreaterThan(bgLum);
      expect(fgLum - bgLum).toBeGreaterThan(100); // Reasonable contrast difference
    });

    it('has sufficient contrast between background and foreground in light theme', () => {
      // Simple contrast check - foreground should be significantly darker than background
      const bgHex = catppuccinLatte.background as string;
      const fgHex = catppuccinLatte.foreground as string;

      const bgLum =
        (parseInt(bgHex.slice(1, 3), 16) +
          parseInt(bgHex.slice(3, 5), 16) +
          parseInt(bgHex.slice(5, 7), 16)) /
        3;
      const fgLum =
        (parseInt(fgHex.slice(1, 3), 16) +
          parseInt(fgHex.slice(3, 5), 16) +
          parseInt(fgHex.slice(5, 7), 16)) /
        3;

      // In light theme, foreground should be darker than background
      expect(bgLum).toBeGreaterThan(fgLum);
      expect(bgLum - fgLum).toBeGreaterThan(100); // Reasonable contrast difference
    });
  });
});
