import { test, expect } from '@playwright/test';

/**
 * E2E tests for the Terminal page.
 *
 * These tests verify:
 * - Terminal page renders correctly
 * - Terminal component initializes (xterm.js)
 * - Connection status is displayed
 * - WebSocket connection is attempted
 *
 * IMPORTANT: These tests do NOT require the game server to be running.
 * They test UI rendering and WebSocket connection attempts only.
 *
 * For tests that verify actual command execution and console output,
 * the game server must be running via Docker:
 *   docker compose up -d
 *
 * Such tests would go in a separate file (e.g., terminal-with-server.spec.ts)
 * and be tagged appropriately for conditional CI execution.
 */

// API key from environment or default from docker-compose.dev.yaml
const API_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';

test.describe('Terminal Page', () => {
  test.beforeEach(async ({ page }) => {
    // Set up authentication - store API key in localStorage
    // The API key must match VS_API_KEY_ADMIN from docker-compose.dev.yaml
    await page.addInitScript((apiKey) => {
      localStorage.setItem('apiKey', apiKey);
    }, API_KEY);
  });

  test('renders the terminal page with header', async ({ page }) => {
    await page.goto('/terminal');

    // Verify the page title/header
    await expect(page.getByText('Server Console')).toBeVisible();

    // Verify the terminal page container exists
    await expect(page.getByLabel('Terminal page')).toBeVisible();
  });

  test('displays the terminal component', async ({ page }) => {
    await page.goto('/terminal');

    // Verify the terminal container with proper ARIA label
    await expect(
      page.getByRole('application', { name: 'Server console terminal' })
    ).toBeVisible();
  });

  test('shows connection status indicator', async ({ page }) => {
    await page.goto('/terminal');

    // Connection status should be visible (either "Connecting...", "Connected", or other state)
    const statusElement = page.getByRole('status');
    await expect(statusElement).toBeVisible();

    // Should have aria-live for accessibility
    await expect(statusElement).toHaveAttribute('aria-live', 'polite');
  });

  test('terminal container has proper styling for full height', async ({
    page,
  }) => {
    await page.goto('/terminal');

    const terminalPage = page.getByLabel('Terminal page');
    await expect(terminalPage).toHaveClass(/flex/);
    await expect(terminalPage).toHaveClass(/h-full/);
  });

  test('navigates to terminal from sidebar', async ({ page }) => {
    // Start at dashboard
    await page.goto('/');

    // Click on Terminal in sidebar
    await page.getByRole('link', { name: /terminal/i }).click();

    // Verify we're on the terminal page
    await expect(page).toHaveURL('/terminal');
    await expect(page.getByText('Server Console')).toBeVisible();
  });

  test('xterm.js canvas is rendered', async ({ page }) => {
    await page.goto('/terminal');

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

test.describe('Terminal WebSocket Connection', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript((apiKey) => {
      localStorage.setItem('apiKey', apiKey);
    }, API_KEY);
  });

  test('attempts WebSocket connection on page load', async ({ page }) => {
    // Track WebSocket connections
    const wsConnections: string[] = [];

    page.on('websocket', (ws) => {
      wsConnections.push(ws.url());
    });

    await page.goto('/terminal');

    // Wait for connection attempt
    await page.waitForTimeout(1000);

    // Verify a WebSocket connection was attempted to the console endpoint
    expect(wsConnections.some((url) => url.includes('/console/ws'))).toBe(true);
  });

  test('shows connecting state initially', async ({ page }) => {
    await page.goto('/terminal');

    // The status should show "Connecting..." initially
    // (It may quickly change to connected or disconnected depending on server state)
    const status = page.getByRole('status');
    await expect(status).toBeVisible();
  });
});
