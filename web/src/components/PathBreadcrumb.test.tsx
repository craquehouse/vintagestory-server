import { describe, it, expect, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { PathBreadcrumb } from './PathBreadcrumb';

/** Holds the path in state, like FileManagerPanel does. */
function Harness({
  initialPath,
  onNavigate,
}: {
  initialPath: string | null;
  onNavigate?: (path: string | null) => void;
}) {
  const [path, setPath] = useState<string | null>(initialPath);
  return (
    <>
      <PathBreadcrumb
        path={path}
        rootLabel="serverdata"
        onNavigate={(next) => {
          onNavigate?.(next);
          setPath(next);
        }}
      />
      <button type="button" onClick={() => setPath('Elsewhere/Deep')}>
        external change
      </button>
    </>
  );
}

describe('PathBreadcrumb (Story 16.7)', () => {
  describe('rendering', () => {
    it('shows only the root as the current location at the root', () => {
      render(<PathBreadcrumb path={null} rootLabel="serverdata" onNavigate={vi.fn()} />);

      const nav = screen.getByRole('navigation', { name: 'Breadcrumb' });
      expect(within(nav).queryAllByRole('button')).toHaveLength(0);
      const current = screen.getByTestId('path-breadcrumb-current');
      expect(current).toHaveTextContent('serverdata');
      expect(current).toHaveAttribute('aria-current', 'page');
      expect(within(nav).getAllByRole('listitem')).toHaveLength(1);
    });

    it('treats an empty path as the root', () => {
      render(<PathBreadcrumb path="" rootLabel="serverdata" onNavigate={vi.fn()} />);

      expect(screen.getByTestId('path-breadcrumb-current')).toHaveTextContent('serverdata');
      expect(screen.queryByTestId('path-breadcrumb-root')).not.toBeInTheDocument();
    });

    it('shows the root and ancestors as buttons and the last directory as current', () => {
      render(
        <PathBreadcrumb path="Cache/unpack/Mods" rootLabel="serverdata" onNavigate={vi.fn()} />
      );

      const nav = screen.getByRole('navigation', { name: 'Breadcrumb' });
      expect(nav.querySelector('ol')).not.toBeNull();
      const buttons = within(nav).getAllByRole('button');
      expect(buttons.map((b) => b.textContent)).toEqual(['serverdata', 'Cache', 'unpack']);
      expect(screen.getByTestId('path-breadcrumb-root')).toHaveAccessibleName('serverdata');
      expect(screen.getByTestId('path-breadcrumb-segment-0')).toHaveAccessibleName('Cache');
      expect(screen.getByTestId('path-breadcrumb-segment-1')).toHaveAccessibleName('unpack');

      const current = screen.getByTestId('path-breadcrumb-current');
      expect(current.tagName).toBe('SPAN');
      expect(current).toHaveTextContent('Mods');
      expect(current).toHaveAttribute('aria-current', 'page');
      expect(within(nav).getAllByRole('listitem')).toHaveLength(4);
      // Only one element marks the current location
      expect(nav.querySelectorAll('[aria-current]')).toHaveLength(1);
    });

    it('hides the separators from assistive technology', () => {
      render(<PathBreadcrumb path="Logs/Archive" rootLabel="serverdata" onNavigate={vi.fn()} />);

      const nav = screen.getByTestId('path-breadcrumb');
      const separators = nav.querySelectorAll('svg');
      expect(separators).toHaveLength(2);
      separators.forEach((svg) => expect(svg).toHaveAttribute('aria-hidden', 'true'));
    });

    it('ignores empty segments from stray slashes', () => {
      render(<PathBreadcrumb path="/Logs//Archive/" rootLabel="serverdata" onNavigate={vi.fn()} />);

      const nav = screen.getByTestId('path-breadcrumb');
      expect(within(nav).getAllByRole('button').map((b) => b.textContent)).toEqual([
        'serverdata',
        'Logs',
      ]);
      expect(screen.getByTestId('path-breadcrumb-current')).toHaveTextContent('Archive');
    });

    it('wraps segments and truncates long names, keeping the full name in the title', () => {
      const longName = 'Auto Map Markers 5.0.3 - Vintage Story 1.22.zip_ff41715051bc';
      render(
        <PathBreadcrumb
          path={`Cache/${longName}/x`}
          rootLabel="serverdata"
          onNavigate={vi.fn()}
        />
      );

      const list = screen.getByTestId('path-breadcrumb').querySelector('ol');
      expect(list).toHaveClass('flex-wrap', 'min-w-0');
      const segment = screen.getByTestId('path-breadcrumb-segment-1');
      expect(segment).toHaveAttribute('title', longName);
      expect(segment).toHaveClass('truncate', 'max-w-full');
      expect(screen.getByTestId('path-breadcrumb-current')).toHaveAttribute('title', 'x');
      expect(screen.getByTestId('path-breadcrumb-current')).toHaveClass('truncate');
    });

    it('renders special characters as text', () => {
      render(
        <PathBreadcrumb
          path="a b/100% & #1/<b>Ünïcødé"
          rootLabel="serverdata"
          onNavigate={vi.fn()}
        />
      );

      expect(screen.getByTestId('path-breadcrumb-segment-0')).toHaveTextContent('a b');
      expect(screen.getByTestId('path-breadcrumb-segment-1')).toHaveTextContent('100% & #1');
      const current = screen.getByTestId('path-breadcrumb-current');
      expect(current).toHaveTextContent('<b>Ünïcødé');
      expect(current.querySelector('b')).toBeNull();
    });
  });

  describe('navigation', () => {
    it('navigates to the root with null', async () => {
      const user = userEvent.setup();
      const onNavigate = vi.fn();
      render(<PathBreadcrumb path="Logs/Archive" rootLabel="serverdata" onNavigate={onNavigate} />);

      await user.click(screen.getByTestId('path-breadcrumb-root'));

      expect(onNavigate).toHaveBeenCalledExactlyOnceWith(null);
    });

    it('navigates to each ancestor with the path up to it', async () => {
      const user = userEvent.setup();
      const onNavigate = vi.fn();
      render(<PathBreadcrumb path="a/b/c/d" rootLabel="serverdata" onNavigate={onNavigate} />);

      await user.click(screen.getByTestId('path-breadcrumb-segment-0'));
      await user.click(screen.getByTestId('path-breadcrumb-segment-1'));
      await user.click(screen.getByTestId('path-breadcrumb-segment-2'));

      expect(onNavigate.mock.calls).toEqual([['a'], ['a/b'], ['a/b/c']]);
    });

    it('passes names with special characters back unchanged', async () => {
      const user = userEvent.setup();
      const onNavigate = vi.fn();
      render(
        <PathBreadcrumb
          path="a b/100% & #1/Ünïcødé"
          rootLabel="serverdata"
          onNavigate={onNavigate}
        />
      );

      await user.click(screen.getByTestId('path-breadcrumb-segment-1'));

      expect(onNavigate).toHaveBeenCalledExactlyOnceWith('a b/100% & #1');
    });

    it('does not make the current segment interactive', async () => {
      const user = userEvent.setup();
      const onNavigate = vi.fn();
      render(<PathBreadcrumb path="Logs" rootLabel="serverdata" onNavigate={onNavigate} />);

      await user.click(screen.getByTestId('path-breadcrumb-current'));

      expect(onNavigate).not.toHaveBeenCalled();
    });

    it('navigates with the keyboard', async () => {
      const user = userEvent.setup();
      const onNavigate = vi.fn();
      render(<Harness initialPath="Logs/Archive" onNavigate={onNavigate} />);

      await user.tab();
      expect(screen.getByTestId('path-breadcrumb-root')).toHaveFocus();
      await user.tab();
      expect(screen.getByTestId('path-breadcrumb-segment-0')).toHaveFocus();
      await user.keyboard('{Enter}');

      expect(onNavigate).toHaveBeenCalledExactlyOnceWith('Logs');
    });
  });

  describe('focus', () => {
    it('moves focus to the new current segment after a jump', async () => {
      const user = userEvent.setup();
      render(<Harness initialPath="a/b/c" />);

      await user.click(screen.getByTestId('path-breadcrumb-segment-0'));

      const current = screen.getByTestId('path-breadcrumb-current');
      expect(current).toHaveTextContent('a');
      expect(current).toHaveFocus();
    });

    it('moves focus to the root after jumping to the root', async () => {
      const user = userEvent.setup();
      render(<Harness initialPath="a/b" />);

      screen.getByTestId('path-breadcrumb-root').focus();
      await user.keyboard('{Enter}');

      const current = screen.getByTestId('path-breadcrumb-current');
      expect(current).toHaveTextContent('serverdata');
      expect(current).toHaveFocus();
    });

    it('does not take focus when the path changes from outside', async () => {
      const user = userEvent.setup();
      render(<Harness initialPath="a/b" />);

      const external = screen.getByRole('button', { name: 'external change' });
      await user.click(external);

      expect(screen.getByTestId('path-breadcrumb-current')).toHaveTextContent('Deep');
      expect(screen.getByTestId('path-breadcrumb-current')).not.toHaveFocus();
      expect(external).toHaveFocus();
    });

    it('keeps the current segment out of the tab order', () => {
      render(<PathBreadcrumb path="a/b" rootLabel="serverdata" onNavigate={vi.fn()} />);

      expect(screen.getByTestId('path-breadcrumb-current')).toHaveAttribute('tabindex', '-1');
    });
  });
});
