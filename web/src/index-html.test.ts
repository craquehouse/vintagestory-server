import { existsSync, readFileSync } from 'fs';
import path from 'path';

const webRoot = path.resolve(import.meta.dirname, '..');
const indexHtml = readFileSync(path.join(webRoot, 'index.html'), 'utf8');

/** The href of every <link> in index.html. */
function linkHrefs(): string[] {
  return [...indexHtml.matchAll(/<link\b[^>]*\bhref="([^"]+)"/g)].map((match) => match[1]);
}

describe('index.html', () => {
  // Story 24.2 (VSS-2bp): the browser tab shows the Vintage Story icon, not Vite's
  it('links the Vintage Story icons', () => {
    expect(linkHrefs()).toEqual(
      expect.arrayContaining(['/favicon.ico', '/favicon-32.png', '/apple-touch-icon.png'])
    );
    expect(indexHtml).toContain('rel="apple-touch-icon"');
    expect(indexHtml).not.toContain('vite.svg');
  });

  // public/ is copied to the build's root, so each linked file must exist there
  it('links only files that exist in public/', () => {
    const hrefs = linkHrefs();

    expect(hrefs.length).toBeGreaterThan(0);
    for (const href of hrefs) {
      expect(existsSync(path.join(webRoot, 'public', href)), href).toBe(true);
    }
  });

  it('no longer ships the Vite placeholder icon', () => {
    expect(existsSync(path.join(webRoot, 'public', 'vite.svg'))).toBe(false);
  });
});
