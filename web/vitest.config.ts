/// <reference types="vitest" />
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { readFileSync } from 'fs';
import path from 'path';

const pkg = JSON.parse(readFileSync(path.resolve(import.meta.dirname, 'package.json'), 'utf8')) as {
  version: string;
};

export default defineConfig({
  plugins: [react()],
  // Same as vite.config.ts, so components can render the version under test
  define: {
    __APP_VERSION__: JSON.stringify(pkg.version),
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/setup.ts'],
    css: true,
    exclude: ['**/node_modules/**', '**/e2e/**'],
    // Suppress known false-positive warnings from third-party libraries
    onConsoleLog(log) {
      // Radix UI's Presence component triggers act() warnings due to internal animations
      if (log.includes('An update to Presence inside a test was not wrapped in act')) {
        return false;
      }
      // Recharts ResponsiveContainer can't measure dimensions in JSDOM since
      // getBoundingClientRect returns 0. Visual testing via Playwright instead.
      if (log.includes('width') && log.includes('height') && log.includes('chart should be greater than 0')) {
        return false;
      }
      return true;
    },
    env: {
      LOCALSTORAGE_FILE: '/tmp/localStorage.json',
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(import.meta.dirname, './src'),
    },
  },
});
