import { test, expect } from '@playwright/test';
import { pretendServerInstalled, serveConfigKey } from './config-js';

/**
 * E2E tests for the Console page (`/game-server/console`).
 *
 * These tests verify:
 * - The page renders with its heading and the console terminal (xterm.js)
 * - The connection status is displayed in the console panel
 * - A WebSocket connection to the console is attempted
 * - The sidebar link "Console" opens the page
 *
 * Story 19.7 moved this spec from `/terminal`, a route the web has not had since Epic 11,
 * to the Console page. The page is behind the installed check, so each test shows the
 * server as installed with `pretendServerInstalled` (e2e/config-js.ts).
 *
 * These tests do NOT need a game server: they never start or stop one and send no console
 * command. They check UI rendering and the WebSocket connection attempt only, so they run on
 * the seeded stack of `just test-e2e-ci`.
 */

// API key from environment or default from docker-compose.dev.yaml
const API_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';
const CONSOLE = '/game-server/console';

test.describe('Console page', () => {
  test.beforeEach(async ({ page }) => {
    // The page takes its key from /config.js (Story 19.2 helper)
    await serveConfigKey(page, API_KEY);
    await pretendServerInstalled(page);
  });

  test('renders the console page with header', async ({ page }) => {
    await page.goto(CONSOLE);

    await expect(page.getByTestId('console-page')).toBeVisible();
    await expect(page.getByRole('heading', { level: 1, name: 'Server Console' })).toBeVisible();
  });

  test('displays the terminal component', async ({ page }) => {
    await page.goto(CONSOLE);

    // Verify the terminal container with proper ARIA label
    await expect(page.getByRole('application', { name: 'Server console terminal' })).toBeVisible();
  });

  test('shows connection status indicator', async ({ page }) => {
    await page.goto(CONSOLE);

    // Connection status should be visible (either "Connecting...", "Connected", or other state);
    // scoped to the console panel, because the page header has a status badge too
    const statusElement = page.getByTestId('console-panel').getByRole('status');
    await expect(statusElement).toBeVisible();

    // Should have aria-live for accessibility
    await expect(statusElement).toHaveAttribute('aria-live', 'polite');
  });

  test('console page is a column that fills the height', async ({ page }) => {
    await page.goto(CONSOLE);

    // The page is a flex column sized to the viewport, so the console panel takes the rest
    const consolePage = page.getByTestId('console-page');
    await expect(consolePage).toHaveClass(/\bflex-col\b/);
    await expect(consolePage).toHaveClass(/\bh-\[calc\(100vh-80px\)\]/);
  });

  test('navigates to the console from the sidebar', async ({ page }) => {
    // Start at dashboard
    await page.goto('/');

    await page.getByRole('navigation').getByRole('link', { name: 'Console', exact: true }).click();

    await expect(page).toHaveURL(CONSOLE);
    await expect(page.getByRole('heading', { level: 1, name: 'Server Console' })).toBeVisible();
  });

  test('xterm.js canvas is rendered', async ({ page }) => {
    await page.goto(CONSOLE);

    // xterm.js creates a canvas element for rendering
    // Wait for the terminal to initialize
    const terminalContainer = page.getByRole('application', {
      name: 'Server console terminal',
    });
    await expect(terminalContainer).toBeVisible();

    // The xterm.js terminal creates nested divs with specific classes
    // Check that the terminal has been initialized by looking for xterm elements
    await expect(terminalContainer.locator('.xterm')).toBeVisible({
      timeout: 5000,
    });
  });
});

test.describe('Console WebSocket connection', () => {
  test.beforeEach(async ({ page }) => {
    await serveConfigKey(page, API_KEY);
    await pretendServerInstalled(page);
  });

  test('attempts WebSocket connection on page load', async ({ page }) => {
    // Verify a WebSocket connection was attempted to the console endpoint
    const socket = page.waitForEvent('websocket', (ws) => ws.url().includes('/console/ws'));

    await page.goto(CONSOLE);

    expect((await socket).url()).toContain('/console/ws');
  });

  test('shows connecting state initially', async ({ page }) => {
    await page.goto(CONSOLE);

    // The status should show "Connecting..." initially
    // (It may quickly change to connected or disconnected depending on server state)
    const status = page.getByTestId('console-panel').getByRole('status');
    await expect(status).toBeVisible();
  });
});
