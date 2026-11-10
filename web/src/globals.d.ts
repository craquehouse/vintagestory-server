/** The manager version from package.json, injected by Vite `define` (vite.config.ts, vitest.config.ts). */
declare const __APP_VERSION__: string;

/** Runtime configuration set by /config.js before the app starts (Epic 15 ADR-5). */
interface Window {
  __VSM_CONFIG__?: { apiKey?: string };
}
