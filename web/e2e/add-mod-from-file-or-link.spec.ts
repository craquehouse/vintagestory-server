import { randomUUID } from 'node:crypto';
import { crc32 } from 'node:zlib';
import { test, expect, type Page } from '@playwright/test';
import { pretendServerInstalled, serveConfigKey } from './config-js';

/**
 * E2E tests for "Add from file or link" on the Installed tab (Story 28.4, FR363, FR364).
 *
 * The upload tests install into the stack's mods folder, so they run only in the
 * throwaway container of `just test-e2e-ci` (scripts/e2e-ci.sh exports E2E_CONTAINER) and
 * skip, with the reason, on any other stack (Epic 24 ADR-8). Each removes the mod it
 * installed. The blocked-link test installs nothing and runs anywhere.
 *
 * Requirements:
 * - `just test-e2e-ci e2e/add-mod-from-file-or-link.spec.ts`
 */

const ADMIN_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';
const THROWAWAY_CONTAINER = 'vintagestory-manager-e2e'; // scripts/e2e-ci.sh CONTAINER
const NOT_THROWAWAY =
  'installs into the mods folder, so it runs only in the throwaway container of ' +
  `just test-e2e-ci (E2E_CONTAINER=${THROWAWAY_CONTAINER})`;

/** A zip archive holding the given files, stored without compression. */
function zipOf(files: Record<string, string>): Buffer {
  const locals: Buffer[] = [];
  const centrals: Buffer[] = [];
  let offset = 0;
  for (const [name, text] of Object.entries(files)) {
    const nameBytes = Buffer.from(name, 'utf8');
    const data = Buffer.from(text, 'utf8');
    const crc = crc32(data);
    const local = Buffer.alloc(30);
    local.writeUInt32LE(0x04034b50, 0);
    local.writeUInt16LE(20, 4); // version needed
    local.writeUInt32LE(crc, 14);
    local.writeUInt32LE(data.length, 18);
    local.writeUInt32LE(data.length, 22);
    local.writeUInt16LE(nameBytes.length, 26);
    const central = Buffer.alloc(46);
    central.writeUInt32LE(0x02014b50, 0);
    central.writeUInt16LE(20, 4); // version made by
    central.writeUInt16LE(20, 6); // version needed
    central.writeUInt32LE(crc, 16);
    central.writeUInt32LE(data.length, 20);
    central.writeUInt32LE(data.length, 24);
    central.writeUInt16LE(nameBytes.length, 28);
    central.writeUInt32LE(offset, 42);
    locals.push(local, nameBytes, data);
    centrals.push(central, nameBytes);
    offset += local.length + nameBytes.length + data.length;
  }
  const centralSize = centrals.reduce((sum, part) => sum + part.length, 0);
  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0);
  end.writeUInt16LE(Object.keys(files).length, 8);
  end.writeUInt16LE(Object.keys(files).length, 10);
  end.writeUInt32LE(centralSize, 12);
  end.writeUInt32LE(offset, 16);
  return Buffer.concat([...locals, ...centrals, end]);
}

async function openDialog(page: Page) {
  await page.goto('/game-server/mods/installed');
  await expect(page.getByTestId('installed-tab-content')).toBeVisible({ timeout: 30000 });
  await page.getByTestId('mods-add-from-file-or-link').click();
  await expect(page.getByTestId('add-mod-dialog')).toBeVisible();
}

test.describe('Add a mod from a file or a link (Story 28.4)', () => {
  test.beforeEach(async ({ page }) => {
    await serveConfigKey(page, ADMIN_KEY);
    await pretendServerInstalled(page);
  });

  test('an uploaded zip is installed and listed as an uploaded file', async ({ page, request }) => {
    test.skip(process.env.E2E_CONTAINER !== THROWAWAY_CONTAINER, NOT_THROWAWAY);
    const modid = `e2eupload${randomUUID().slice(0, 8)}`;
    const archive = zipOf({
      'modinfo.json': JSON.stringify({ modid, name: `E2E ${modid}`, version: '1.0.0' }),
    });

    try {
      await openDialog(page);
      await page.getByTestId('add-mod-file-input').setInputFiles({
        name: `${modid}.zip`,
        mimeType: 'application/zip',
        buffer: archive,
      });
      await page.getByTestId('add-mod-install').click();

      await expect(page.getByText(`Installed ${modid} 1.0.0`)).toBeVisible();
      await expect(page.getByTestId('add-mod-dialog')).toHaveCount(0);
      await expect(page.getByTestId(`mod-update-${modid}`).first()).toHaveText(/^Uploaded file/);
      await expect(page.getByTestId(`mod-link-${modid}`)).toHaveCount(0);

      // The same mod again: offered a replace, which goes through
      await page.getByTestId('mods-add-from-file-or-link').click();
      await page.getByTestId('add-mod-file-input').setInputFiles({
        name: `${modid}-fork.zip`,
        mimeType: 'application/zip',
        buffer: archive,
      });
      await page.getByTestId('add-mod-install').click();
      await expect(page.getByTestId('add-mod-installed')).toContainText(
        `${modid} 1.0.0 is already installed (an uploaded file)`
      );
      await page.getByTestId('add-mod-replace').click();
      await expect(page.getByText(`Replaced ${modid} 1.0.0`)).toBeVisible();
    } finally {
      const removed = await request.delete(`/api/v1alpha1/mods/${modid}`, {
        headers: { 'X-API-Key': ADMIN_KEY },
      });
      expect(removed.ok(), `removing ${modid} through the API`).toBeTruthy();
    }
  });

  test('a zip without modinfo.json shows why it was refused', async ({ page }) => {
    test.skip(process.env.E2E_CONTAINER !== THROWAWAY_CONTAINER, NOT_THROWAWAY);
    await openDialog(page);

    await page.getByTestId('add-mod-file-input').setInputFiles({
      name: 'not-a-mod.zip',
      mimeType: 'application/zip',
      buffer: zipOf({ 'readme.txt': 'hello' }),
    });
    await page.getByTestId('add-mod-install').click();

    await expect(page.getByTestId('add-mod-error')).toContainText('no usable modinfo.json');
    await expect(page.getByTestId('add-mod-dialog')).toBeVisible();
  });

  test('a link to a local address is refused as blocked', async ({ page }) => {
    await openDialog(page);

    await page.getByTestId('add-mod-tab-link').click();
    await page.getByTestId('add-mod-url-input').fill('https://127.0.0.1/mod.zip');
    await page.getByTestId('add-mod-install').click();

    await expect(page.getByTestId('add-mod-error')).toContainText('private or local network');
  });
});
