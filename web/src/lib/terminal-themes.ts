import type { ITheme } from '@xterm/xterm';

/**
 * Catppuccin Mocha theme for dark mode.
 * Colors aligned with the app's CSS theme variables.
 */
export const catppuccinMocha: ITheme = {
  background: '#181825',    // --background (dark)
  foreground: '#cdd6f4',    // --foreground (dark)
  cursor: '#f5e0dc',        // rosewater
  cursorAccent: '#181825',
  selectionBackground: '#585b70',  // --secondary (dark)
  selectionForeground: '#cdd6f4',
  black: '#45475a',         // --popover (dark)
  red: '#f38ba8',           // --destructive (dark)
  green: '#a6e3a1',         // --chart-3 (dark)
  yellow: '#f9e2af',
  blue: '#89b4fa',
  magenta: '#cba6f7',       // --primary (dark)
  cyan: '#89dceb',          // --accent (dark)
  white: '#bac2de',
  brightBlack: '#585b70',
  brightRed: '#f38ba8',
  brightGreen: '#a6e3a1',
  brightYellow: '#f9e2af',
  brightBlue: '#89b4fa',
  brightMagenta: '#cba6f7',
  brightCyan: '#89dceb',
  brightWhite: '#a6adc8',   // --muted-foreground (dark)
};

/**
 * Catppuccin Latte theme for light mode.
 * Colors aligned with the app's CSS theme variables.
 */
export const catppuccinLatte: ITheme = {
  background: '#eff1f5',    // --background (light)
  foreground: '#4c4f69',    // --foreground (light)
  cursor: '#dc8a78',        // rosewater
  cursorAccent: '#eff1f5',
  selectionBackground: '#ccd0da',  // --secondary (light)
  selectionForeground: '#4c4f69',
  black: '#5c5f77',
  red: '#d20f39',           // --destructive (light)
  green: '#40a02b',         // --chart-3 (light)
  yellow: '#df8e1d',
  blue: '#1e66f5',
  magenta: '#8839ef',       // --primary (light)
  cyan: '#04a5e5',          // --accent (light)
  white: '#acb0be',
  brightBlack: '#6c6f85',   // --muted-foreground (light)
  brightRed: '#d20f39',
  brightGreen: '#40a02b',
  brightYellow: '#df8e1d',
  brightBlue: '#1e66f5',
  brightMagenta: '#8839ef',
  brightCyan: '#04a5e5',
  brightWhite: '#bcc0cc',   // --border (light)
};

/**
 * Returns the appropriate terminal theme based on the mode.
 */
export function getTerminalTheme(mode: 'light' | 'dark'): ITheme {
  return mode === 'dark' ? catppuccinMocha : catppuccinLatte;
}
