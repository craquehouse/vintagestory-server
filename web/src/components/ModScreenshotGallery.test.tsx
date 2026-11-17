/**
 * Tests for ModScreenshotGallery (Story 18.1, VSS-l4x).
 *
 * The gallery shows one screenshot at a time with its position, Previous and Next,
 * a strip of thumbnails and a dialog with the larger image. Keys are handled on the
 * section and on the dialog, never on the document.
 */

import { describe, it, expect, beforeAll } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ModScreenshotGallery } from './ModScreenshotGallery';
import type { ModScreenshot } from '@/api/types';

const CDN = 'https://moddbcdn.vintagestory.at';

function shots(count: number): ModScreenshot[] {
  return Array.from({ length: count }, (_, i) => {
    const name = String.fromCharCode(97 + i); // a, b, c, ...
    return {
      imageUrl: `${CDN}/${name}.png`,
      thumbnailUrl: `${CDN}/${name}_55_60.png`,
      filename: `${name}.png`,
    };
  });
}

const FIVE = shots(5);

function position() {
  return screen.getByTestId('mod-screenshot-position');
}

function currentImage() {
  return screen.getByTestId('mod-screenshot-image');
}

beforeAll(() => {
  // jsdom has no scrollIntoView; the gallery scrolls the selected thumbnail into view
  Element.prototype.scrollIntoView ??= () => {};
});

describe('ModScreenshotGallery', () => {
  describe('several screenshots', () => {
    it('shows the first image, its position and one thumbnail per screenshot', () => {
      render(<ModScreenshotGallery screenshots={FIVE} />);

      expect(screen.getByTestId('mod-screenshots')).toBeInTheDocument();
      expect(screen.getByText('Screenshots')).toBeInTheDocument();
      expect(position()).toHaveTextContent('1 of 5');
      expect(currentImage()).toHaveAttribute('src', FIVE[0].imageUrl);
      const strip = screen.getByTestId('mod-screenshot-thumbnails');
      const thumbs = within(strip).getAllByRole('img');
      expect(thumbs.map((img) => img.getAttribute('src'))).toEqual(FIVE.map((s) => s.thumbnailUrl));
    });

    it('Next, Previous and a thumbnail change the image and the position', async () => {
      const user = userEvent.setup();
      render(<ModScreenshotGallery screenshots={FIVE} />);

      await user.click(screen.getByTestId('mod-screenshot-next'));
      expect(position()).toHaveTextContent('2 of 5');
      expect(currentImage()).toHaveAttribute('src', FIVE[1].imageUrl);

      await user.click(screen.getByTestId('mod-screenshot-thumb-3'));
      expect(position()).toHaveTextContent('4 of 5');
      expect(currentImage()).toHaveAttribute('src', FIVE[3].imageUrl);

      await user.click(screen.getByTestId('mod-screenshot-prev'));
      expect(position()).toHaveTextContent('3 of 5');
      expect(currentImage()).toHaveAttribute('src', FIVE[2].imageUrl);
    });

    it('wraps around at both ends', async () => {
      const user = userEvent.setup();
      render(<ModScreenshotGallery screenshots={FIVE} />);

      await user.click(screen.getByTestId('mod-screenshot-prev'));
      expect(position()).toHaveTextContent('5 of 5');
      await user.click(screen.getByTestId('mod-screenshot-next'));
      expect(position()).toHaveTextContent('1 of 5');
    });

    it('marks the selected thumbnail with aria-current', async () => {
      const user = userEvent.setup();
      render(<ModScreenshotGallery screenshots={FIVE} />);

      expect(screen.getByTestId('mod-screenshot-thumb-0')).toHaveAttribute('aria-current', 'true');
      expect(screen.getByTestId('mod-screenshot-thumb-1')).not.toHaveAttribute('aria-current');
      await user.click(screen.getByTestId('mod-screenshot-thumb-2'));
      expect(screen.getByTestId('mod-screenshot-thumb-2')).toHaveAttribute('aria-current', 'true');
      expect(screen.getByTestId('mod-screenshot-thumb-0')).not.toHaveAttribute('aria-current');
    });

    it('requests only the current full-size image (AC 8)', async () => {
      const user = userEvent.setup();
      render(<ModScreenshotGallery screenshots={FIVE} />);

      const fullSize = new Set(FIVE.map((s) => s.imageUrl));
      const section = screen.getByTestId('mod-screenshots');
      const countFull = () =>
        Array.from(section.querySelectorAll('img')).filter((img) =>
          fullSize.has(img.getAttribute('src') ?? '')
        );
      expect(countFull()).toHaveLength(1);
      await user.click(screen.getByTestId('mod-screenshot-next'));
      expect(countFull()).toHaveLength(1);
      expect(countFull()[0]).toHaveAttribute('src', FIVE[1].imageUrl);
    });

    it('loads every image lazily and without a referrer', async () => {
      const user = userEvent.setup();
      render(<ModScreenshotGallery screenshots={FIVE} />);
      await user.click(screen.getByTestId('mod-screenshot-current'));

      const images = document.querySelectorAll('img');
      // the current image, five thumbnails and the dialog image
      expect(images).toHaveLength(7);
      for (const img of images) {
        expect(img).toHaveAttribute('loading', 'lazy');
        expect(img).toHaveAttribute('referrerpolicy', 'no-referrer');
      }
    });

    it('builds alt text from the position and the file name', async () => {
      const user = userEvent.setup();
      const withEmptyName = FIVE.map((s, i) => (i === 1 ? { ...s, filename: '' } : s));
      render(<ModScreenshotGallery screenshots={withEmptyName} />);

      expect(currentImage()).toHaveAttribute('alt', 'Screenshot 1 of 5: a.png');
      expect(within(screen.getByTestId('mod-screenshot-thumb-2')).getByRole('img')).toHaveAttribute(
        'alt',
        'Screenshot 3 of 5: c.png'
      );
      await user.click(screen.getByTestId('mod-screenshot-next'));
      expect(currentImage()).toHaveAttribute('alt', 'Screenshot 2 of 5');
      // A thumbnail button's accessible name is its image's alt text
      expect(screen.getByRole('button', { name: 'Screenshot 4 of 5: d.png' })).toBe(
        screen.getByTestId('mod-screenshot-thumb-3')
      );
    });
  });

  describe('keyboard', () => {
    it('Tab reaches the current image, Previous, Next and every thumbnail', async () => {
      const user = userEvent.setup();
      render(<ModScreenshotGallery screenshots={FIVE} />);

      await user.tab();
      expect(screen.getByTestId('mod-screenshot-current')).toHaveFocus();
      await user.tab();
      expect(screen.getByTestId('mod-screenshot-prev')).toHaveFocus();
      await user.tab();
      expect(screen.getByTestId('mod-screenshot-next')).toHaveFocus();
      for (let i = 0; i < FIVE.length; i++) {
        await user.tab();
        expect(screen.getByTestId(`mod-screenshot-thumb-${i}`)).toHaveFocus();
      }
    });

    it('arrow keys move one step with focus on a thumbnail or on Next', async () => {
      const user = userEvent.setup();
      render(<ModScreenshotGallery screenshots={FIVE} />);

      screen.getByTestId('mod-screenshot-thumb-2').focus();
      await user.keyboard('{ArrowRight}');
      expect(position()).toHaveTextContent('2 of 5');
      await user.keyboard('{ArrowLeft}');
      expect(position()).toHaveTextContent('1 of 5');

      screen.getByTestId('mod-screenshot-next').focus();
      await user.keyboard('{ArrowLeft}');
      expect(position()).toHaveTextContent('5 of 5');
      await user.keyboard('{ArrowRight}');
      expect(position()).toHaveTextContent('1 of 5');
    });

    it('ignores arrow keys with a modifier held', async () => {
      const user = userEvent.setup();
      render(<ModScreenshotGallery screenshots={FIVE} />);

      screen.getByTestId('mod-screenshot-next').focus();
      await user.keyboard('{Alt>}{ArrowRight}{/Alt}');
      await user.keyboard('{Control>}{ArrowRight}{/Control}');
      await user.keyboard('{Meta>}{ArrowLeft}{/Meta}');
      await user.keyboard('{Shift>}{ArrowLeft}{/Shift}');
      expect(position()).toHaveTextContent('1 of 5');
    });

    it.each([['{Enter}'], [' ']])('%s on the current image opens the dialog', async (key) => {
      const user = userEvent.setup();
      render(<ModScreenshotGallery screenshots={FIVE} />);

      screen.getByTestId('mod-screenshot-current').focus();
      await user.keyboard(key);
      expect(await screen.findByTestId('mod-screenshot-dialog')).toBeInTheDocument();
    });
  });

  describe('dialog', () => {
    it('opens on the same image and position', async () => {
      const user = userEvent.setup();
      render(<ModScreenshotGallery screenshots={FIVE} />);

      await user.click(screen.getByTestId('mod-screenshot-thumb-3'));
      await user.click(screen.getByTestId('mod-screenshot-current'));

      const dialog = await screen.findByTestId('mod-screenshot-dialog');
      expect(within(dialog).getByTestId('mod-screenshot-dialog-image')).toHaveAttribute(
        'src',
        FIVE[3].imageUrl
      );
      expect(within(dialog).getByTestId('mod-screenshot-dialog-position')).toHaveTextContent(
        '4 of 5'
      );
      expect(
        within(dialog).getByRole('heading', { name: 'Screenshot 4 of 5: d.png' })
      ).toBeVisible();
    });

    it('Next and ArrowRight move exactly one step in the dialog', async () => {
      const user = userEvent.setup();
      render(<ModScreenshotGallery screenshots={FIVE} />);

      await user.click(screen.getByTestId('mod-screenshot-current'));
      const dialog = await screen.findByTestId('mod-screenshot-dialog');
      const dialogPosition = within(dialog).getByTestId('mod-screenshot-dialog-position');

      await user.click(within(dialog).getByTestId('mod-screenshot-dialog-next'));
      expect(dialogPosition).toHaveTextContent('2 of 5');
      await user.keyboard('{ArrowRight}');
      expect(dialogPosition).toHaveTextContent('3 of 5');
      await user.keyboard('{ArrowLeft}');
      expect(dialogPosition).toHaveTextContent('2 of 5');
      await user.click(within(dialog).getByTestId('mod-screenshot-dialog-prev'));
      expect(dialogPosition).toHaveTextContent('1 of 5');
      await user.click(within(dialog).getByTestId('mod-screenshot-dialog-prev'));
      expect(dialogPosition).toHaveTextContent('5 of 5');
    });

    it('Escape closes it, returns focus to the current image and keeps its position', async () => {
      const user = userEvent.setup();
      render(<ModScreenshotGallery screenshots={FIVE} />);

      await user.click(screen.getByTestId('mod-screenshot-current'));
      await screen.findByTestId('mod-screenshot-dialog');
      await user.keyboard('{ArrowRight}{ArrowRight}');
      await user.keyboard('{Escape}');

      expect(screen.queryByTestId('mod-screenshot-dialog')).not.toBeInTheDocument();
      expect(screen.getByTestId('mod-screenshot-current')).toHaveFocus();
      expect(position()).toHaveTextContent('3 of 5');
      expect(currentImage()).toHaveAttribute('src', FIVE[2].imageUrl);
    });
  });

  describe('one screenshot', () => {
    it('shows the image without navigation, and it still opens in the dialog', async () => {
      const user = userEvent.setup();
      const one = shots(1);
      render(<ModScreenshotGallery screenshots={one} />);

      expect(currentImage()).toHaveAttribute('src', one[0].imageUrl);
      expect(currentImage()).toHaveAttribute('alt', 'Screenshot 1 of 1: a.png');
      expect(screen.queryByTestId('mod-screenshot-prev')).not.toBeInTheDocument();
      expect(screen.queryByTestId('mod-screenshot-next')).not.toBeInTheDocument();
      expect(screen.queryByTestId('mod-screenshot-position')).not.toBeInTheDocument();
      expect(screen.queryByTestId('mod-screenshot-thumbnails')).not.toBeInTheDocument();

      await user.click(screen.getByTestId('mod-screenshot-current'));
      const dialog = await screen.findByTestId('mod-screenshot-dialog');
      expect(within(dialog).getByTestId('mod-screenshot-dialog-image')).toHaveAttribute(
        'src',
        one[0].imageUrl
      );
      expect(within(dialog).queryByTestId('mod-screenshot-dialog-prev')).not.toBeInTheDocument();
      expect(within(dialog).queryByTestId('mod-screenshot-dialog-next')).not.toBeInTheDocument();
      expect(
        within(dialog).queryByTestId('mod-screenshot-dialog-position')
      ).not.toBeInTheDocument();
      await user.keyboard('{ArrowRight}');
      expect(within(dialog).getByTestId('mod-screenshot-dialog-image')).toHaveAttribute(
        'src',
        one[0].imageUrl
      );
    });

    it('arrow keys change nothing in the section', async () => {
      const user = userEvent.setup();
      const one = shots(1);
      render(<ModScreenshotGallery screenshots={one} />);

      screen.getByTestId('mod-screenshot-current').focus();
      await user.keyboard('{ArrowRight}{ArrowLeft}');
      expect(currentImage()).toHaveAttribute('src', one[0].imageUrl);
    });
  });

  it('renders nothing for an empty list', () => {
    const { container } = render(<ModScreenshotGallery screenshots={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
