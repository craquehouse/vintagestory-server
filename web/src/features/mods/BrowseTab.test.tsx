/**
 * BrowseTab component tests.
 *
 * Story 10.2: Mods Tab Restructure - AC3
 *
 * Tests the placeholder Browse tab that will be implemented
 * in Stories 10.3-10.8.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowseTab } from './BrowseTab';

describe('BrowseTab', () => {
  describe('AC3: Browse tab placeholder', () => {
    it('renders the browse tab container', () => {
      render(<BrowseTab />);

      expect(screen.getByTestId('browse-tab-content')).toBeInTheDocument();
    });

    it('displays the placeholder heading', () => {
      render(<BrowseTab />);

      expect(screen.getByText('Browse Mods')).toBeInTheDocument();
    });

    it('displays the coming soon message', () => {
      render(<BrowseTab />);

      expect(
        screen.getByText('Mod discovery coming soon in Stories 10.3-10.8')
      ).toBeInTheDocument();
    });

    it('has centered layout', () => {
      render(<BrowseTab />);

      const container = screen.getByTestId('browse-tab-content');
      expect(container).toHaveClass('flex', 'flex-col', 'items-center', 'justify-center');
    });
  });
});
