import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { UIPreferencesPanel } from './UIPreferencesPanel';
import { PreferencesProvider } from '@/contexts/PreferencesContext';
import * as cookies from '@/lib/cookies';

// Mock cookies module
vi.mock('@/lib/cookies', () => ({
  getCookie: vi.fn(),
  setCookie: vi.fn(),
}));

// Mock next-themes
vi.mock('next-themes', () => ({
  useTheme: () => ({
    theme: 'system',
    setTheme: vi.fn(),
    systemTheme: 'dark',
    resolvedTheme: 'dark',
  }),
}));

const mockedGetCookie = vi.mocked(cookies.getCookie);
const mockedSetCookie = vi.mocked(cookies.setCookie);

// Helper to render with PreferencesProvider
function renderPanel(initialPrefs: string | null = null) {
  mockedGetCookie.mockReturnValue(initialPrefs);
  return render(
    <PreferencesProvider>
      <UIPreferencesPanel />
    </PreferencesProvider>
  );
}

describe('UIPreferencesPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedGetCookie.mockReturnValue(null);
  });

  describe('rendering', () => {
    it('renders the panel with all setting groups', () => {
      renderPanel();

      expect(screen.getByText('Appearance')).toBeInTheDocument();
      expect(screen.getByText('Console')).toBeInTheDocument();
      expect(screen.getByText('Layout')).toBeInTheDocument();
    });

    it('renders theme selection buttons', () => {
      renderPanel();

      expect(screen.getByTestId('theme-system')).toBeInTheDocument();
      expect(screen.getByTestId('theme-light')).toBeInTheDocument();
      expect(screen.getByTestId('theme-dark')).toBeInTheDocument();
    });

    it('renders font size controls', () => {
      renderPanel();

      expect(screen.getByTestId('font-size-decrease')).toBeInTheDocument();
      expect(screen.getByTestId('font-size-value')).toBeInTheDocument();
      expect(screen.getByTestId('font-size-increase')).toBeInTheDocument();
    });

    it('renders sidebar toggle', () => {
      renderPanel();

      expect(screen.getByTestId('sidebar-collapsed-toggle')).toBeInTheDocument();
    });

    it('displays default font size of 14px', () => {
      renderPanel();

      expect(screen.getByTestId('font-size-value')).toHaveTextContent('14px');
    });
  });

  describe('theme selection', () => {
    it('highlights system theme by default', () => {
      renderPanel();

      const systemBtn = screen.getByTestId('theme-system');
      // Default variant should be applied (not outline)
      expect(systemBtn).not.toHaveClass('border');
    });

    it('updates theme when clicking light button', async () => {
      const user = userEvent.setup();
      renderPanel();

      await user.click(screen.getByTestId('theme-light'));

      expect(mockedSetCookie).toHaveBeenCalledWith(
        'vs_ui_prefs',
        expect.stringContaining('"theme":"light"')
      );
    });

    it('updates theme when clicking dark button', async () => {
      const user = userEvent.setup();
      renderPanel();

      await user.click(screen.getByTestId('theme-dark'));

      expect(mockedSetCookie).toHaveBeenCalledWith(
        'vs_ui_prefs',
        expect.stringContaining('"theme":"dark"')
      );
    });
  });

  describe('font size controls', () => {
    it('increases font size when clicking plus button', async () => {
      const user = userEvent.setup();
      renderPanel();

      await user.click(screen.getByTestId('font-size-increase'));

      expect(screen.getByTestId('font-size-value')).toHaveTextContent('15px');
    });

    it('decreases font size when clicking minus button', async () => {
      const user = userEvent.setup();
      renderPanel();

      await user.click(screen.getByTestId('font-size-decrease'));

      expect(screen.getByTestId('font-size-value')).toHaveTextContent('13px');
    });

    it('disables decrease button at minimum font size (10px)', () => {
      renderPanel(JSON.stringify({ consoleFontSize: 10 }));

      expect(screen.getByTestId('font-size-decrease')).toBeDisabled();
    });

    it('disables increase button at maximum font size (24px)', () => {
      renderPanel(JSON.stringify({ consoleFontSize: 24 }));

      expect(screen.getByTestId('font-size-increase')).toBeDisabled();
    });

    it('persists font size changes to cookie', async () => {
      const user = userEvent.setup();
      renderPanel();

      await user.click(screen.getByTestId('font-size-increase'));

      expect(mockedSetCookie).toHaveBeenCalledWith(
        'vs_ui_prefs',
        expect.stringContaining('"consoleFontSize":15')
      );
    });
  });

  describe('sidebar toggle', () => {
    it('shows "Expanded" when sidebar is not collapsed', () => {
      renderPanel();

      expect(screen.getByTestId('sidebar-collapsed-toggle')).toHaveTextContent('Expanded');
    });

    it('shows "Collapsed" when sidebar is collapsed', () => {
      renderPanel(JSON.stringify({ sidebarCollapsed: true }));

      expect(screen.getByTestId('sidebar-collapsed-toggle')).toHaveTextContent('Collapsed');
    });

    it('toggles sidebar state when clicked', async () => {
      const user = userEvent.setup();
      renderPanel();

      await user.click(screen.getByTestId('sidebar-collapsed-toggle'));

      expect(mockedSetCookie).toHaveBeenCalledWith(
        'vs_ui_prefs',
        expect.stringContaining('"sidebarCollapsed":true')
      );
    });
  });

  describe('persistence', () => {
    it('loads saved preferences from cookie', () => {
      renderPanel(
        JSON.stringify({
          theme: 'dark',
          consoleFontSize: 18,
          sidebarCollapsed: true,
        })
      );

      expect(screen.getByTestId('font-size-value')).toHaveTextContent('18px');
      expect(screen.getByTestId('sidebar-collapsed-toggle')).toHaveTextContent('Collapsed');
    });
  });
});
