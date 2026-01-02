import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';
import { SettingsPage } from './SettingsPage';
import { PreferencesProvider } from '@/contexts/PreferencesContext';

// Mock cookies module
vi.mock('@/lib/cookies', () => ({
  getCookie: vi.fn().mockReturnValue(null),
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

// Create a fresh QueryClient for each test
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

// Wrapper component for rendering with QueryClientProvider and PreferencesProvider
function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <PreferencesProvider>{children}</PreferencesProvider>
      </QueryClientProvider>
    );
  };
}

// Mock API settings response
const mockApiSettings = {
  status: 'ok',
  data: {
    settings: {
      autoStartServer: true,
      blockEnvManagedSettings: true,
      enforceEnvOnRestart: true,
      modListRefreshInterval: 300,
      serverVersionsRefreshInterval: 3600,
    },
  },
};

// Mock config files response
const mockConfigFiles = {
  status: 'ok',
  data: {
    files: ['serverconfig.json', 'worldconfig.json'],
  },
};

describe('SettingsPage', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';

    // Default mock that returns appropriate responses
    globalThis.fetch = vi.fn().mockImplementation(async (url: string) => {
      if (url.includes('/config/files')) {
        return {
          ok: true,
          json: () => Promise.resolve(mockConfigFiles),
        };
      }
      return {
        ok: true,
        json: () => Promise.resolve(mockApiSettings),
      };
    });
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  describe('rendering', () => {
    it('renders the page container', async () => {
      const queryClient = createTestQueryClient();
      render(<SettingsPage />, {
        wrapper: createWrapper(queryClient),
      });

      expect(screen.getByTestId('settings-page')).toBeInTheDocument();
    });

    it('has aria-label on container', async () => {
      const queryClient = createTestQueryClient();
      render(<SettingsPage />, {
        wrapper: createWrapper(queryClient),
      });

      expect(screen.getByTestId('settings-page')).toHaveAttribute(
        'aria-label',
        'Settings page'
      );
    });

    it('renders tabs component', async () => {
      const queryClient = createTestQueryClient();
      render(<SettingsPage />, {
        wrapper: createWrapper(queryClient),
      });

      expect(screen.getByRole('tablist')).toBeInTheDocument();
    });
  });

  describe('tab navigation', () => {
    it('renders UI Preferences tab', async () => {
      const queryClient = createTestQueryClient();
      render(<SettingsPage />, {
        wrapper: createWrapper(queryClient),
      });

      expect(screen.getByTestId('ui-preferences-tab')).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /ui preferences/i })).toBeInTheDocument();
    });

    it('renders API Settings tab', async () => {
      const queryClient = createTestQueryClient();
      render(<SettingsPage />, {
        wrapper: createWrapper(queryClient),
      });

      expect(screen.getByTestId('api-settings-tab')).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /api settings/i })).toBeInTheDocument();
    });

    it('renders File Manager tab', async () => {
      const queryClient = createTestQueryClient();
      render(<SettingsPage />, {
        wrapper: createWrapper(queryClient),
      });

      expect(screen.getByTestId('file-manager-tab')).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /file manager/i })).toBeInTheDocument();
    });

    it('UI Preferences tab is active by default', async () => {
      const queryClient = createTestQueryClient();
      render(<SettingsPage />, {
        wrapper: createWrapper(queryClient),
      });

      const uiPrefsTab = screen.getByTestId('ui-preferences-tab');
      expect(uiPrefsTab).toHaveAttribute('data-state', 'active');
    });

    it('switches to API Settings tab on click', async () => {
      const user = userEvent.setup();
      const queryClient = createTestQueryClient();
      render(<SettingsPage />, {
        wrapper: createWrapper(queryClient),
      });

      const apiTab = screen.getByTestId('api-settings-tab');
      await user.click(apiTab);

      await waitFor(() => {
        expect(apiTab).toHaveAttribute('data-state', 'active');
      });
      expect(screen.getByTestId('ui-preferences-tab')).toHaveAttribute('data-state', 'inactive');
    });

    it('switches to File Manager tab on click', async () => {
      const user = userEvent.setup();
      const queryClient = createTestQueryClient();
      render(<SettingsPage />, {
        wrapper: createWrapper(queryClient),
      });

      const fileManagerTab = screen.getByTestId('file-manager-tab');
      await user.click(fileManagerTab);

      await waitFor(() => {
        expect(fileManagerTab).toHaveAttribute('data-state', 'active');
      });
      expect(screen.getByTestId('ui-preferences-tab')).toHaveAttribute('data-state', 'inactive');
    });
  });

  describe('UI Preferences tab content', () => {
    it('shows UI Preferences panel by default', async () => {
      const queryClient = createTestQueryClient();
      render(<SettingsPage />, {
        wrapper: createWrapper(queryClient),
      });

      expect(screen.getByTestId('ui-preferences-panel')).toBeInTheDocument();
    });

    it('displays appearance settings', async () => {
      const queryClient = createTestQueryClient();
      render(<SettingsPage />, {
        wrapper: createWrapper(queryClient),
      });

      expect(screen.getByText('Appearance')).toBeInTheDocument();
      expect(screen.getByText('Console')).toBeInTheDocument();
      expect(screen.getByText('Layout')).toBeInTheDocument();
    });
  });

  describe('API Settings tab content', () => {
    it('shows API Settings panel when tab is active', async () => {
      const user = userEvent.setup();
      const queryClient = createTestQueryClient();
      render(<SettingsPage />, {
        wrapper: createWrapper(queryClient),
      });

      // Switch to API Settings tab
      await user.click(screen.getByTestId('api-settings-tab'));

      await waitFor(() => {
        // Should show API settings content (loading or loaded)
        expect(
          screen.queryByTestId('api-settings-loading') ||
            screen.queryByTestId('api-settings-panel')
        ).toBeInTheDocument();
      });
    });

    it('loads API settings data', async () => {
      const user = userEvent.setup();
      const queryClient = createTestQueryClient();
      render(<SettingsPage />, {
        wrapper: createWrapper(queryClient),
      });

      // Switch to API Settings tab
      await user.click(screen.getByTestId('api-settings-tab'));

      await waitFor(() => {
        expect(screen.getByTestId('api-settings-panel')).toBeInTheDocument();
      });

      // Verify settings are displayed
      expect(screen.getByText('Server Behavior')).toBeInTheDocument();
    });
  });

  describe('File Manager tab content (Story 6.6)', () => {
    it('shows FileManagerPanel when File Manager tab is active', async () => {
      const user = userEvent.setup();
      const queryClient = createTestQueryClient();
      render(<SettingsPage />, {
        wrapper: createWrapper(queryClient),
      });

      // Switch to File Manager tab
      await user.click(screen.getByTestId('file-manager-tab'));

      await waitFor(() => {
        expect(screen.getByTestId('file-manager-panel')).toBeInTheDocument();
      });
    });

    it('displays file list in File Manager', async () => {
      const user = userEvent.setup();
      const queryClient = createTestQueryClient();
      render(<SettingsPage />, {
        wrapper: createWrapper(queryClient),
      });

      // Switch to File Manager tab
      await user.click(screen.getByTestId('file-manager-tab'));

      await waitFor(() => {
        expect(screen.getByTestId('file-list')).toBeInTheDocument();
      });

      // Verify file names are displayed
      expect(screen.getByText('serverconfig.json')).toBeInTheDocument();
      expect(screen.getByText('worldconfig.json')).toBeInTheDocument();
    });

    it('shows prompt to select a file when none selected', async () => {
      const user = userEvent.setup();
      const queryClient = createTestQueryClient();
      render(<SettingsPage />, {
        wrapper: createWrapper(queryClient),
      });

      // Switch to File Manager tab
      await user.click(screen.getByTestId('file-manager-tab'));

      await waitFor(() => {
        expect(screen.getByTestId('file-viewer-empty')).toBeInTheDocument();
      });

      expect(
        screen.getByText('Select a file to view its contents')
      ).toBeInTheDocument();
    });
  });

  describe('layout', () => {
    it('has flex layout for full height', async () => {
      const queryClient = createTestQueryClient();
      render(<SettingsPage />, {
        wrapper: createWrapper(queryClient),
      });

      const container = screen.getByTestId('settings-page');
      expect(container).toHaveClass('flex');
      expect(container).toHaveClass('h-full');
      expect(container).toHaveClass('flex-col');
    });
  });
});
