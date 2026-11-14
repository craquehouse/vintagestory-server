import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';
import { FileManagerPanel } from './FileManagerPanel';

// Create a fresh QueryClient for each test
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
}

// Wrapper component for rendering with QueryClientProvider
function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

// Mock responses
const mockFilesResponse = {
  status: 'ok',
  data: {
    files: ['serverconfig.json', 'worldconfig.json', 'clientsettings.json'],
  },
};

const mockEmptyFilesResponse = {
  status: 'ok',
  data: {
    files: [],
  },
};

const mockFileContentResponse = {
  status: 'ok',
  data: {
    filename: 'serverconfig.json',
    content: {
      ServerName: 'My Test Server',
      Port: 42420,
      MaxClients: 16,
    },
  },
};

describe('FileManagerPanel', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  describe('loading state', () => {
    it('shows loading state for file list', async () => {
      let resolvePromise: () => void;
      const pendingPromise = new Promise<void>((resolve) => {
        resolvePromise = resolve;
      });

      globalThis.fetch = vi.fn().mockImplementation(async () => {
        await pendingPromise;
        return {
          ok: true,
          json: () => Promise.resolve(mockFilesResponse),
        };
      });

      const queryClient = createTestQueryClient();
      render(<FileManagerPanel />, { wrapper: createWrapper(queryClient) });

      expect(screen.getByTestId('file-list-loading')).toBeInTheDocument();

      // Resolve the fetch
      await act(async () => {
        resolvePromise!();
      });

      await waitFor(() => {
        expect(screen.queryByTestId('file-list-loading')).not.toBeInTheDocument();
      });
    });

    it('shows empty viewer state while file list loads', async () => {
      globalThis.fetch = vi.fn().mockReturnValue(new Promise(() => {}));

      const queryClient = createTestQueryClient();
      render(<FileManagerPanel />, { wrapper: createWrapper(queryClient) });

      expect(screen.getByTestId('file-viewer-empty')).toBeInTheDocument();
    });
  });

  describe('error state', () => {
    it('shows error when file list fails to load', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: () =>
          Promise.resolve({
            detail: {
              code: 'INTERNAL_ERROR',
              message: 'Something went wrong',
            },
          }),
      });

      const queryClient = createTestQueryClient();
      render(<FileManagerPanel />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('file-manager-error')).toBeInTheDocument();
      });

      expect(screen.getByText('Failed to load files')).toBeInTheDocument();
    });

    it('shows default error message when error has empty message', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        statusText: '',
        json: () =>
          Promise.resolve({
            detail: {
              code: 'INTERNAL_ERROR',
              message: '',
            },
          }),
      });

      const queryClient = createTestQueryClient();
      render(<FileManagerPanel />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('file-manager-error')).toBeInTheDocument();
      });

      expect(screen.getByText('Failed to load files')).toBeInTheDocument();
      expect(screen.getByText('Unable to load configuration files')).toBeInTheDocument();
    });

    it('shows error in viewer when file content fails to load', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/config/files/serverconfig.json')) {
          return {
            ok: false,
            status: 404,
            statusText: 'Not Found',
            json: () =>
              Promise.resolve({
                detail: {
                  code: 'CONFIG_FILE_NOT_FOUND',
                  message: 'Config file not found',
                },
              }),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockFilesResponse),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<FileManagerPanel />, { wrapper: createWrapper(queryClient) });

      // Wait for file list to load
      await waitFor(() => {
        expect(screen.getByTestId('file-list')).toBeInTheDocument();
      });

      // Click on a file
      await act(async () => {
        fireEvent.click(screen.getByTestId('file-item-serverconfig.json'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('file-viewer-error')).toBeInTheDocument();
      });
    });
  });

  describe('empty state (AC: 5)', () => {
    it('shows empty state when no files available', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockEmptyFilesResponse),
      });

      const queryClient = createTestQueryClient();
      render(<FileManagerPanel />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('file-list-empty')).toBeInTheDocument();
      });

      expect(screen.getByText('No configuration files found')).toBeInTheDocument();
    });
  });

  describe('file list display (AC: 1)', () => {
    it('displays list of configuration files', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockFilesResponse),
      });

      const queryClient = createTestQueryClient();
      render(<FileManagerPanel />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('file-list')).toBeInTheDocument();
      });

      expect(screen.getByText('serverconfig.json')).toBeInTheDocument();
      expect(screen.getByText('worldconfig.json')).toBeInTheDocument();
      expect(screen.getByText('clientsettings.json')).toBeInTheDocument();
    });
  });

  describe('file selection (AC: 2)', () => {
    it('loads file content when a file is clicked', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/config/files/serverconfig.json')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockFileContentResponse),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockFilesResponse),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<FileManagerPanel />, { wrapper: createWrapper(queryClient) });

      // Wait for file list to load
      await waitFor(() => {
        expect(screen.getByTestId('file-list')).toBeInTheDocument();
      });

      // Click on a file
      await act(async () => {
        fireEvent.click(screen.getByTestId('file-item-serverconfig.json'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('file-viewer')).toBeInTheDocument();
      });

      // Verify the content is displayed (filename appears in both list and viewer)
      const allFilenameElements = screen.getAllByText('serverconfig.json');
      expect(allFilenameElements.length).toBe(2); // One in list, one in viewer header
      const content = screen.getByTestId('file-viewer-content');
      expect(content.textContent).toContain('"ServerName"');
      expect(content.textContent).toContain('"My Test Server"');
    });

    it('highlights selected file in the list', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/config/files/serverconfig.json')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockFileContentResponse),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockFilesResponse),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<FileManagerPanel />, { wrapper: createWrapper(queryClient) });

      // Wait for file list to load
      await waitFor(() => {
        expect(screen.getByTestId('file-list')).toBeInTheDocument();
      });

      // Click on a file
      await act(async () => {
        fireEvent.click(screen.getByTestId('file-item-serverconfig.json'));
      });

      // Verify the file is highlighted
      const selectedItem = screen.getByTestId('file-item-serverconfig.json');
      expect(selectedItem).toHaveClass('font-medium');
      expect(selectedItem).toHaveAttribute('aria-selected', 'true');
    });

    it('loads different file when selection changes', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/config/files/worldconfig.json')) {
          return {
            ok: true,
            json: () =>
              Promise.resolve({
                status: 'ok',
                data: {
                  filename: 'worldconfig.json',
                  content: { WorldName: 'Test World' },
                },
              }),
          };
        }
        if (url.includes('/config/files/serverconfig.json')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockFileContentResponse),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockFilesResponse),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<FileManagerPanel />, { wrapper: createWrapper(queryClient) });

      // Wait for file list to load
      await waitFor(() => {
        expect(screen.getByTestId('file-list')).toBeInTheDocument();
      });

      // Select first file
      await act(async () => {
        fireEvent.click(screen.getByTestId('file-item-serverconfig.json'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('file-viewer-content')).toHaveTextContent(
          '"ServerName"'
        );
      });

      // Select second file
      await act(async () => {
        fireEvent.click(screen.getByTestId('file-item-worldconfig.json'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('file-viewer-content')).toHaveTextContent(
          '"WorldName"'
        );
      });
    });
  });

  describe('content formatting (AC: 3)', () => {
    it('displays JSON content with proper formatting', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/config/files/serverconfig.json')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockFileContentResponse),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockFilesResponse),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<FileManagerPanel />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('file-list')).toBeInTheDocument();
      });

      await act(async () => {
        fireEvent.click(screen.getByTestId('file-item-serverconfig.json'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('file-viewer-content')).toBeInTheDocument();
      });

      const content = screen.getByTestId('file-viewer-content');
      // Verify it's in a pre tag with proper classes
      expect(content.tagName).toBe('PRE');
      expect(content).toHaveClass('font-mono');
      expect(content).toHaveClass('whitespace-pre');
    });
  });

  describe('no file selected (AC: 4)', () => {
    it('shows prompt to select a file when none selected', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockFilesResponse),
      });

      const queryClient = createTestQueryClient();
      render(<FileManagerPanel />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('file-list')).toBeInTheDocument();
      });

      expect(screen.getByTestId('file-viewer-empty')).toBeInTheDocument();
      expect(
        screen.getByText('Select a file to view its contents')
      ).toBeInTheDocument();
    });
  });

  describe('layout', () => {
    it('renders split layout with file list and viewer', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockFilesResponse),
      });

      const queryClient = createTestQueryClient();
      render(<FileManagerPanel />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('file-manager-panel')).toBeInTheDocument();
      });

      const panel = screen.getByTestId('file-manager-panel');
      expect(panel).toHaveClass('flex');
    });
  });

  describe('styling', () => {
    it('applies custom className', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockFilesResponse),
      });

      const queryClient = createTestQueryClient();
      render(<FileManagerPanel className="custom-class" />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('file-manager-panel')).toHaveClass('custom-class');
      });
    });
  });

  describe('directory navigation (Story 9.7)', () => {
    const mockDirectoriesResponse = {
      status: 'ok',
      data: {
        directories: ['ModConfigs', 'Playerdata', 'Worlds'],
      },
    };

    const mockSubdirectoryFilesResponse = {
      status: 'ok',
      data: {
        files: ['mod1.json', 'mod2.json'],
      },
    };

    it('shows only the root in the breadcrumb at the root directory', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockFilesResponse),
      });

      const queryClient = createTestQueryClient();
      render(<FileManagerPanel />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('file-list')).toBeInTheDocument();
      });

      expect(screen.getByTestId('path-breadcrumb-current')).toHaveTextContent('serverdata');
    });

    it('shows the root as a breadcrumb button when in a subdirectory', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/config/directories')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockDirectoriesResponse),
          };
        }
        if (url.includes('/config/files') && url.includes('directory=ModConfigs')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockSubdirectoryFilesResponse),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockFilesResponse),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<FileManagerPanel />, { wrapper: createWrapper(queryClient) });

      // Wait for initial load
      await waitFor(() => {
        expect(screen.getByTestId('file-list')).toBeInTheDocument();
      });

      // Click on a directory
      await act(async () => {
        fireEvent.click(screen.getByTestId('file-item-ModConfigs'));
      });

      // The root is now a breadcrumb button
      await waitFor(() => {
        expect(screen.getByTestId('path-breadcrumb-root')).toBeInTheDocument();
      });
    });

    it('navigates into directory and updates current path', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/config/directories')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockDirectoriesResponse),
          };
        }
        if (url.includes('/config/files') && url.includes('directory=ModConfigs')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockSubdirectoryFilesResponse),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockFilesResponse),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<FileManagerPanel />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('file-list')).toBeInTheDocument();
      });

      // Click on a directory
      await act(async () => {
        fireEvent.click(screen.getByTestId('file-item-ModConfigs'));
      });

      // Verify we're now in the subdirectory
      await waitFor(() => {
        expect(screen.getByTestId('path-breadcrumb-root')).toBeInTheDocument();
        expect(screen.getByTestId('path-breadcrumb-current')).toHaveTextContent('ModConfigs');
      });

      // Verify subdirectory files are displayed
      expect(screen.getByText('mod1.json')).toBeInTheDocument();
      expect(screen.getByText('mod2.json')).toBeInTheDocument();
    });

    it('navigates back to the parent directory through the breadcrumb', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/config/directories')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockDirectoriesResponse),
          };
        }
        if (url.includes('/config/files') && url.includes('directory=ModConfigs')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockSubdirectoryFilesResponse),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockFilesResponse),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<FileManagerPanel />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('file-list')).toBeInTheDocument();
      });

      // Navigate into directory
      await act(async () => {
        fireEvent.click(screen.getByTestId('file-item-ModConfigs'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('path-breadcrumb-root')).toBeInTheDocument();
      });

      // Click the root segment
      await act(async () => {
        fireEvent.click(screen.getByTestId('path-breadcrumb-root'));
      });

      // Back at root - the root is the current segment
      await waitFor(() => {
        expect(screen.getByTestId('path-breadcrumb-current')).toHaveTextContent('serverdata');
      });

      // Original files should be visible again
      expect(screen.getByText('serverconfig.json')).toBeInTheDocument();
    });

    it('navigates back to root from a first-level subdirectory through the breadcrumb', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/config/directories')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockDirectoriesResponse),
          };
        }
        if (url.includes('/config/files') && url.includes('directory=ModConfigs')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockSubdirectoryFilesResponse),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockFilesResponse),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<FileManagerPanel />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('file-list')).toBeInTheDocument();
      });

      // Navigate into first-level directory
      await act(async () => {
        fireEvent.click(screen.getByTestId('file-item-ModConfigs'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('path-breadcrumb-root')).toBeInTheDocument();
      });

      // Click the root segment
      await act(async () => {
        fireEvent.click(screen.getByTestId('path-breadcrumb-root'));
      });

      // Verify we're at root
      await waitFor(() => {
        expect(screen.getByTestId('path-breadcrumb-current')).toHaveTextContent('serverdata');
      });
    });

    it('filters out hidden directories (starting with .)', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/config/directories')) {
          return {
            ok: true,
            json: () =>
              Promise.resolve({
                status: 'ok',
                data: {
                  directories: ['.git', 'ModConfigs', '.vscode', 'Playerdata'],
                },
              }),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockFilesResponse),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<FileManagerPanel />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('file-list')).toBeInTheDocument();
      });

      // Visible directories should be in the list
      expect(screen.getByTestId('file-item-ModConfigs')).toBeInTheDocument();
      expect(screen.getByTestId('file-item-Playerdata')).toBeInTheDocument();

      // Hidden directories should NOT be in the list
      expect(screen.queryByTestId('file-item-.git')).not.toBeInTheDocument();
      expect(screen.queryByTestId('file-item-.vscode')).not.toBeInTheDocument();
    });

    it('clears file selection when navigating to directory', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/config/directories')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockDirectoriesResponse),
          };
        }
        if (url.includes('/config/files') && url.includes('directory=ModConfigs')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockSubdirectoryFilesResponse),
          };
        }
        if (url.includes('/config/files/serverconfig.json')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockFileContentResponse),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockFilesResponse),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<FileManagerPanel />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('file-list')).toBeInTheDocument();
      });

      // Select a file first
      await act(async () => {
        fireEvent.click(screen.getByTestId('file-item-serverconfig.json'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('file-viewer')).toBeInTheDocument();
      });

      // Navigate into directory
      await act(async () => {
        fireEvent.click(screen.getByTestId('file-item-ModConfigs'));
      });

      // Viewer should be empty (selection cleared)
      await waitFor(() => {
        expect(screen.getByTestId('file-viewer-empty')).toBeInTheDocument();
      });
    });

    it('clears file selection when navigating back through the breadcrumb', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/config/directories')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockDirectoriesResponse),
          };
        }
        if (url.includes('/config/files') && url.includes('ModConfigs%2Fmod1.json')) {
          return {
            ok: true,
            json: () =>
              Promise.resolve({
                status: 'ok',
                data: {
                  filename: 'ModConfigs/mod1.json',
                  content: { ModName: 'Test Mod' },
                },
              }),
          };
        }
        if (url.includes('/config/files') && url.includes('directory=ModConfigs')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockSubdirectoryFilesResponse),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockFilesResponse),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<FileManagerPanel />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('file-list')).toBeInTheDocument();
      });

      // Navigate into directory
      await act(async () => {
        fireEvent.click(screen.getByTestId('file-item-ModConfigs'));
      });

      // Wait for file list to load in subdirectory
      await waitFor(() => {
        expect(screen.getByTestId('file-list')).toBeInTheDocument();
      });

      // Select a file in the subdirectory
      await act(async () => {
        fireEvent.click(screen.getByTestId('file-item-mod1.json'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('file-viewer-content')).toHaveTextContent('ModName');
      });

      // Navigate up through the breadcrumb
      await act(async () => {
        fireEvent.click(screen.getByTestId('path-breadcrumb-root'));
      });

      // Viewer should be empty (selection cleared)
      await waitFor(() => {
        expect(screen.getByTestId('file-viewer-empty')).toBeInTheDocument();
      });
    });

    it('navigates into nested subdirectories', async () => {
      const nestedDirectoriesResponse = {
        status: 'ok',
        data: {
          directories: ['unpack', 'downloads'],
        },
      };

      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/config/directories')) {
          if (url.includes('directory=ModConfigs')) {
            return {
              ok: true,
              json: () => Promise.resolve(nestedDirectoriesResponse),
            };
          }
          return {
            ok: true,
            json: () => Promise.resolve(mockDirectoriesResponse),
          };
        }
        if (url.includes('/config/files') && url.includes('directory=ModConfigs%2Funpack')) {
          return {
            ok: true,
            json: () =>
              Promise.resolve({
                status: 'ok',
                data: { files: ['nested.json'] },
              }),
          };
        }
        if (url.includes('/config/files') && url.includes('directory=ModConfigs')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockSubdirectoryFilesResponse),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockFilesResponse),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<FileManagerPanel />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('file-list')).toBeInTheDocument();
      });

      // Navigate into first level
      await act(async () => {
        fireEvent.click(screen.getByTestId('file-item-ModConfigs'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('path-breadcrumb-current')).toHaveTextContent('ModConfigs');
      });

      // Navigate into nested directory
      await act(async () => {
        fireEvent.click(screen.getByTestId('file-item-unpack'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('path-breadcrumb-current')).toHaveTextContent('unpack');
        expect(screen.getByText('nested.json')).toBeInTheDocument();
      });
    });

    it('navigates back from a nested subdirectory to its parent segment', async () => {
      const nestedDirectoriesResponse = {
        status: 'ok',
        data: {
          directories: ['unpack', 'downloads'],
        },
      };

      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/config/directories')) {
          if (url.includes('directory=ModConfigs')) {
            return {
              ok: true,
              json: () => Promise.resolve(nestedDirectoriesResponse),
            };
          }
          return {
            ok: true,
            json: () => Promise.resolve(mockDirectoriesResponse),
          };
        }
        if (url.includes('/config/files') && url.includes('directory=ModConfigs%2Funpack')) {
          return {
            ok: true,
            json: () =>
              Promise.resolve({
                status: 'ok',
                data: { files: ['nested.json'] },
              }),
          };
        }
        if (url.includes('/config/files') && url.includes('directory=ModConfigs')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockSubdirectoryFilesResponse),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockFilesResponse),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<FileManagerPanel />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('file-list')).toBeInTheDocument();
      });

      // Navigate into first level
      await act(async () => {
        fireEvent.click(screen.getByTestId('file-item-ModConfigs'));
      });

      // Wait for file list to load in subdirectory
      await waitFor(() => {
        expect(screen.getByTestId('file-list')).toBeInTheDocument();
      });

      // Navigate into nested directory
      await act(async () => {
        fireEvent.click(screen.getByTestId('file-item-unpack'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('path-breadcrumb-current')).toHaveTextContent('unpack');
      });

      // Navigate up through the breadcrumb
      await act(async () => {
        fireEvent.click(screen.getByTestId('path-breadcrumb-segment-0'));
      });

      // Should be back at ModConfigs level
      await waitFor(() => {
        expect(screen.getByTestId('path-breadcrumb-current')).toHaveTextContent('ModConfigs');
        expect(screen.getByText('mod1.json')).toBeInTheDocument();
      });
    });
  });

  describe('word wrap toggle', () => {
    it('toggles word wrap in the viewer', async () => {
      const user = userEvent.setup();
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockFilesResponse),
      });

      const queryClient = createTestQueryClient();
      render(<FileManagerPanel />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('file-list')).toBeInTheDocument();
      });

      // Select a file to show content
      const mockContentFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/config/files/serverconfig.json')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockFileContentResponse),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockFilesResponse),
        };
      });
      globalThis.fetch = mockContentFetch;

      await act(async () => {
        fireEvent.click(screen.getByTestId('file-item-serverconfig.json'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('file-viewer')).toBeInTheDocument();
      });

      // Click word wrap toggle
      await user.click(screen.getByTestId('file-viewer-wrap-toggle'));

      // The toggle should work (handled by FileViewer component)
      expect(screen.getByTestId('file-viewer-wrap-toggle')).toBeInTheDocument();
    });
  });

  describe('directory and file list combination', () => {
    const mockDirectoriesResponse = {
      status: 'ok',
      data: {
        directories: ['ModConfigs', 'Playerdata', 'Worlds'],
      },
    };

    const mockMixedFilesResponse = {
      status: 'ok',
      data: {
        files: ['serverconfig.json', 'worldconfig.json'],
      },
    };

    it('displays directories before files in the list', async () => {
      globalThis.fetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/config/directories')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockDirectoriesResponse),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockMixedFilesResponse),
        };
      });

      const queryClient = createTestQueryClient();
      render(<FileManagerPanel />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('file-list')).toBeInTheDocument();
      });

      // Get all list items (they have role="option" in the listbox)
      const listItems = screen.getAllByRole('option');

      // Find indices of directories and files
      const modConfigsIndex = listItems.findIndex(
        (item) => item.getAttribute('data-testid') === 'file-item-ModConfigs'
      );
      const playerdataIndex = listItems.findIndex(
        (item) => item.getAttribute('data-testid') === 'file-item-Playerdata'
      );
      const worldsIndex = listItems.findIndex(
        (item) => item.getAttribute('data-testid') === 'file-item-Worlds'
      );
      const serverConfigIndex = listItems.findIndex(
        (item) => item.getAttribute('data-testid') === 'file-item-serverconfig.json'
      );
      const worldConfigIndex = listItems.findIndex(
        (item) => item.getAttribute('data-testid') === 'file-item-worldconfig.json'
      );

      // Verify directories come before files
      expect(modConfigsIndex).toBeGreaterThanOrEqual(0);
      expect(playerdataIndex).toBeGreaterThanOrEqual(0);
      expect(worldsIndex).toBeGreaterThanOrEqual(0);
      expect(serverConfigIndex).toBeGreaterThanOrEqual(0);
      expect(worldConfigIndex).toBeGreaterThanOrEqual(0);

      expect(modConfigsIndex).toBeLessThan(serverConfigIndex);
      expect(playerdataIndex).toBeLessThan(serverConfigIndex);
      expect(worldsIndex).toBeLessThan(worldConfigIndex);
    });

    it('displays both directories and files correctly', async () => {
      globalThis.fetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/config/directories')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockDirectoriesResponse),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockMixedFilesResponse),
        };
      });

      const queryClient = createTestQueryClient();
      render(<FileManagerPanel />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('file-list')).toBeInTheDocument();
      });

      // Verify all directories are present
      expect(screen.getByTestId('file-item-ModConfigs')).toBeInTheDocument();
      expect(screen.getByTestId('file-item-Playerdata')).toBeInTheDocument();
      expect(screen.getByTestId('file-item-Worlds')).toBeInTheDocument();

      // Verify all files are present
      expect(screen.getByTestId('file-item-serverconfig.json')).toBeInTheDocument();
      expect(screen.getByTestId('file-item-worldconfig.json')).toBeInTheDocument();
    });
  });

  describe('edge cases', () => {
    it('handles directory with no files, only subdirectories', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/config/directories')) {
          if (url.includes('directory=EmptyDir')) {
            return {
              ok: true,
              json: () =>
                Promise.resolve({
                  status: 'ok',
                  data: { directories: ['subdir1', 'subdir2'] },
                }),
            };
          }
          return {
            ok: true,
            json: () =>
              Promise.resolve({
                status: 'ok',
                data: { directories: ['EmptyDir'] },
              }),
          };
        }
        if (url.includes('/config/files') && url.includes('directory=EmptyDir')) {
          return {
            ok: true,
            json: () => Promise.resolve({ status: 'ok', data: { files: [] } }),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve({ status: 'ok', data: { files: [] } }),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<FileManagerPanel />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('file-list')).toBeInTheDocument();
      });

      // Navigate into EmptyDir
      await act(async () => {
        fireEvent.click(screen.getByTestId('file-item-EmptyDir'));
      });

      // Should show subdirectories but no "no files" message
      await waitFor(() => {
        expect(screen.getByTestId('file-item-subdir1')).toBeInTheDocument();
        expect(screen.getByTestId('file-item-subdir2')).toBeInTheDocument();
      });
    });

    it('handles root with no directories, only files', async () => {
      globalThis.fetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/config/directories')) {
          return {
            ok: true,
            json: () => Promise.resolve({ status: 'ok', data: { directories: [] } }),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockFilesResponse),
        };
      });

      const queryClient = createTestQueryClient();
      render(<FileManagerPanel />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('file-list')).toBeInTheDocument();
      });

      // Should show files only
      expect(screen.getByTestId('file-item-serverconfig.json')).toBeInTheDocument();
      expect(screen.getByTestId('file-item-worldconfig.json')).toBeInTheDocument();
      expect(screen.getByTestId('file-item-clientsettings.json')).toBeInTheDocument();
    });

    it('handles completely empty directory (no files, no subdirectories)', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/config/directories')) {
          if (url.includes('directory=EmptyDir')) {
            return {
              ok: true,
              json: () =>
                Promise.resolve({ status: 'ok', data: { directories: [] } }),
            };
          }
          return {
            ok: true,
            json: () =>
              Promise.resolve({
                status: 'ok',
                data: { directories: ['EmptyDir'] },
              }),
          };
        }
        if (url.includes('/config/files') && url.includes('directory=EmptyDir')) {
          return {
            ok: true,
            json: () => Promise.resolve({ status: 'ok', data: { files: [] } }),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockFilesResponse),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<FileManagerPanel />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('file-list')).toBeInTheDocument();
      });

      // Navigate into EmptyDir
      await act(async () => {
        fireEvent.click(screen.getByTestId('file-item-EmptyDir'));
      });

      // Should show empty state
      await waitFor(() => {
        expect(screen.getByTestId('file-list-empty')).toBeInTheDocument();
      });
    });

    it('constructs correct file path in deeply nested directories', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/config/directories')) {
          if (url.includes('directory=level1%2Flevel2%2Flevel3')) {
            return {
              ok: true,
              json: () =>
                Promise.resolve({ status: 'ok', data: { directories: [] } }),
            };
          }
          if (url.includes('directory=level1%2Flevel2')) {
            return {
              ok: true,
              json: () =>
                Promise.resolve({ status: 'ok', data: { directories: ['level3'] } }),
            };
          }
          if (url.includes('directory=level1')) {
            return {
              ok: true,
              json: () =>
                Promise.resolve({ status: 'ok', data: { directories: ['level2'] } }),
            };
          }
          return {
            ok: true,
            json: () =>
              Promise.resolve({ status: 'ok', data: { directories: ['level1'] } }),
          };
        }
        if (url.includes('/config/files/level1%2Flevel2%2Flevel3%2Fdeep.json')) {
          return {
            ok: true,
            json: () =>
              Promise.resolve({
                status: 'ok',
                data: {
                  filename: 'level1/level2/level3/deep.json',
                  content: { deep: 'value' },
                },
              }),
          };
        }
        if (
          url.includes('/config/files') &&
          url.includes('directory=level1%2Flevel2%2Flevel3')
        ) {
          return {
            ok: true,
            json: () =>
              Promise.resolve({ status: 'ok', data: { files: ['deep.json'] } }),
          };
        }
        if (url.includes('/config/files') && url.includes('directory=level1%2Flevel2')) {
          return {
            ok: true,
            json: () => Promise.resolve({ status: 'ok', data: { files: [] } }),
          };
        }
        if (url.includes('/config/files') && url.includes('directory=level1')) {
          return {
            ok: true,
            json: () => Promise.resolve({ status: 'ok', data: { files: [] } }),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockEmptyFilesResponse),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<FileManagerPanel />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('file-list')).toBeInTheDocument();
      });

      // Navigate through all levels
      await act(async () => {
        fireEvent.click(screen.getByTestId('file-item-level1'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('path-breadcrumb-current')).toHaveTextContent('level1');
      });

      await act(async () => {
        fireEvent.click(screen.getByTestId('file-item-level2'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('path-breadcrumb-current')).toHaveTextContent('level2');
      });

      await act(async () => {
        fireEvent.click(screen.getByTestId('file-item-level3'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('path-breadcrumb-current')).toHaveTextContent('level3');
        expect(screen.getByTestId('file-item-deep.json')).toBeInTheDocument();
      });

      // Select the deeply nested file
      await act(async () => {
        fireEvent.click(screen.getByTestId('file-item-deep.json'));
      });

      // Verify the full path was used
      await waitFor(() => {
        expect(screen.getByTestId('file-viewer-content')).toHaveTextContent('deep');
      });

      // Verify the fetch was called with the correct full path
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('level1%2Flevel2%2Flevel3%2Fdeep.json'),
        expect.anything()
      );
    });

    it('handles multiple sequential breadcrumb navigations correctly', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/config/directories')) {
          if (url.includes('directory=level1%2Flevel2')) {
            return {
              ok: true,
              json: () =>
                Promise.resolve({ status: 'ok', data: { directories: [] } }),
            };
          }
          if (url.includes('directory=level1')) {
            return {
              ok: true,
              json: () =>
                Promise.resolve({ status: 'ok', data: { directories: ['level2'] } }),
            };
          }
          return {
            ok: true,
            json: () =>
              Promise.resolve({ status: 'ok', data: { directories: ['level1'] } }),
          };
        }
        if (url.includes('/config/files') && url.includes('directory=level1%2Flevel2')) {
          return {
            ok: true,
            json: () =>
              Promise.resolve({ status: 'ok', data: { files: ['file2.json'] } }),
          };
        }
        if (url.includes('/config/files') && url.includes('directory=level1')) {
          return {
            ok: true,
            json: () =>
              Promise.resolve({ status: 'ok', data: { files: ['file1.json'] } }),
          };
        }
        return {
          ok: true,
          json: () =>
            Promise.resolve({ status: 'ok', data: { files: ['root.json'] } }),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<FileManagerPanel />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('file-list')).toBeInTheDocument();
      });

      // Navigate to level1
      await act(async () => {
        fireEvent.click(screen.getByTestId('file-item-level1'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('path-breadcrumb-current')).toHaveTextContent('level1');
      });

      // Navigate to level2
      await act(async () => {
        fireEvent.click(screen.getByTestId('file-item-level2'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('path-breadcrumb-current')).toHaveTextContent('level2');
        expect(screen.getByTestId('file-item-file2.json')).toBeInTheDocument();
      });

      // Navigate back to level1
      await act(async () => {
        fireEvent.click(screen.getByTestId('path-breadcrumb-segment-0'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('path-breadcrumb-current')).toHaveTextContent('level1');
        expect(screen.getByTestId('file-item-file1.json')).toBeInTheDocument();
      });

      // Navigate back to root
      await act(async () => {
        fireEvent.click(screen.getByTestId('path-breadcrumb-root'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('path-breadcrumb-current')).toHaveTextContent('serverdata');
        expect(screen.getByTestId('file-item-root.json')).toBeInTheDocument();
      });
    });

    it('handles directory loading error gracefully', async () => {
      globalThis.fetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/config/directories')) {
          return {
            ok: false,
            status: 500,
            statusText: 'Internal Server Error',
            json: () =>
              Promise.resolve({
                detail: {
                  code: 'INTERNAL_ERROR',
                  message: 'Failed to list directories',
                },
              }),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockFilesResponse),
        };
      });

      const queryClient = createTestQueryClient();
      render(<FileManagerPanel />, { wrapper: createWrapper(queryClient) });

      // Should still show files even if directories fail
      await waitFor(() => {
        expect(screen.getByTestId('file-list')).toBeInTheDocument();
        expect(screen.getByTestId('file-item-serverconfig.json')).toBeInTheDocument();
      });
    });

    it('handles repeated root clicks safely', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/config/directories')) {
          return {
            ok: true,
            json: () =>
              Promise.resolve({
                status: 'ok',
                data: { directories: ['TestDir'] },
              }),
          };
        }
        if (url.includes('/config/files') && url.includes('directory=TestDir')) {
          return {
            ok: true,
            json: () =>
              Promise.resolve({ status: 'ok', data: { files: ['test.json'] } }),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockFilesResponse),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<FileManagerPanel />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('file-list')).toBeInTheDocument();
      });

      // Navigate into directory
      await act(async () => {
        fireEvent.click(screen.getByTestId('file-item-TestDir'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('path-breadcrumb-root')).toBeInTheDocument();
      });

      // Simulate multiple rapid clicks without waiting for state updates
      // This tests the guard clause's ability to handle race conditions
      const rootButton = screen.getByTestId('path-breadcrumb-root');
      fireEvent.click(rootButton);
      fireEvent.click(rootButton);
      fireEvent.click(rootButton);

      // Should safely navigate to root without errors
      await waitFor(() => {
        expect(screen.getByTestId('path-breadcrumb-current')).toHaveTextContent('serverdata');
      });

      expect(screen.getByTestId('file-item-serverconfig.json')).toBeInTheDocument();
    });

    it('shows loading state for directories separately from files', async () => {
      let resolveDirectories: () => void;
      const directoriesPromise = new Promise<void>((resolve) => {
        resolveDirectories = resolve;
      });

      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/config/directories')) {
          await directoriesPromise;
          return {
            ok: true,
            json: () =>
              Promise.resolve({
                status: 'ok',
                data: { directories: ['TestDir'] },
              }),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockFilesResponse),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<FileManagerPanel />, { wrapper: createWrapper(queryClient) });

      // Should show loading while directories are being fetched
      expect(screen.getByTestId('file-list-loading')).toBeInTheDocument();

      // Resolve directories
      await act(async () => {
        resolveDirectories!();
      });

      // Should show files and directories
      await waitFor(() => {
        expect(screen.queryByTestId('file-list-loading')).not.toBeInTheDocument();
        expect(screen.getByTestId('file-item-TestDir')).toBeInTheDocument();
        expect(screen.getByTestId('file-item-serverconfig.json')).toBeInTheDocument();
      });
    });
  });
  describe('breadcrumb navigation (Story 16.7)', () => {
    interface Listing {
      directories: string[];
      files: string[];
    }

    /**
     * Fetch mock serving a directory tree keyed by path ('' is the root).
     * Paths in `failing` answer the file listing with a 500.
     */
    function treeFetch(tree: Record<string, Listing>, failing: string[] = []) {
      return vi.fn().mockImplementation(async (input: string) => {
        const url = new URL(input);
        const directory = url.searchParams.get('directory') ?? '';
        const listing = tree[directory] ?? { directories: [], files: [] };
        if (url.pathname.endsWith('/config/directories')) {
          return {
            ok: true,
            json: () =>
              Promise.resolve({ status: 'ok', data: { directories: listing.directories } }),
          };
        }
        if (url.pathname.endsWith('/config/files')) {
          if (failing.includes(directory)) {
            return {
              ok: false,
              status: 500,
              statusText: 'Internal Server Error',
              json: () =>
                Promise.resolve({
                  detail: { code: 'INTERNAL_ERROR', message: 'Listing failed' },
                }),
            };
          }
          return {
            ok: true,
            json: () => Promise.resolve({ status: 'ok', data: { files: listing.files } }),
          };
        }
        // File content: /config/files/<encoded path>
        const filename = decodeURIComponent(url.pathname.split('/config/files/')[1] ?? '');
        return {
          ok: true,
          json: () =>
            Promise.resolve({ status: 'ok', data: { filename, content: { file: filename } } }),
        };
      });
    }

    const tree: Record<string, Listing> = {
      '': { directories: ['Cache', 'Logs'], files: ['root.json'] },
      Cache: { directories: ['unpack'], files: ['cache.json'] },
      'Cache/unpack': { directories: ['Some Mod'], files: ['unpack.json'] },
      'Cache/unpack/Some Mod': { directories: [], files: ['modinfo.json'] },
      Logs: { directories: [], files: [] },
    };

    const current = () => screen.getByTestId('path-breadcrumb-current');

    async function renderPanel(fetchMock = treeFetch(tree)) {
      globalThis.fetch = fetchMock;
      const queryClient = createTestQueryClient();
      render(<FileManagerPanel />, { wrapper: createWrapper(queryClient) });
      await waitFor(() => {
        expect(screen.getByTestId('file-item-root.json')).toBeInTheDocument();
      });
      return fetchMock;
    }

    async function openDirectory(name: string) {
      await act(async () => {
        fireEvent.click(screen.getByTestId(`file-item-${name}`));
      });
      await waitFor(() => {
        expect(current()).toHaveTextContent(name);
      });
    }

    it('shows the breadcrumb above the list and viewer at the root', async () => {
      await renderPanel();

      const panel = screen.getByTestId('file-manager-panel');
      expect(panel).toHaveClass('flex-col');
      const bar = screen.getByTestId('file-manager-breadcrumb-bar');
      expect(bar.parentElement).toBe(panel);
      expect(panel.firstElementChild).toBe(bar);
      expect(within(bar).getByRole('navigation', { name: 'Breadcrumb' })).toBeInTheDocument();
      expect(bar).not.toContainElement(screen.getByTestId('file-list'));
      expect(current()).toHaveTextContent('serverdata');
      expect(current()).toHaveAttribute('aria-current', 'page');
      expect(screen.queryByTestId('path-breadcrumb-root')).not.toBeInTheDocument();
    });

    it('has no Back button at any level', async () => {
      await renderPanel();
      expect(screen.queryByTestId('file-manager-back')).not.toBeInTheDocument();

      await openDirectory('Cache');
      await openDirectory('unpack');

      expect(screen.queryByTestId('file-manager-back')).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /back/i })).not.toBeInTheDocument();
    });

    it('shows every directory of the path, ancestors as buttons', async () => {
      await renderPanel();
      await openDirectory('Cache');
      await openDirectory('unpack');
      await openDirectory('Some Mod');

      const nav = screen.getByRole('navigation', { name: 'Breadcrumb' });
      expect(within(nav).getAllByRole('button').map((b) => b.textContent)).toEqual([
        'serverdata',
        'Cache',
        'unpack',
      ]);
      expect(current()).toHaveTextContent('Some Mod');
      expect(screen.getByTestId('file-item-modinfo.json')).toBeInTheDocument();
    });

    it('jumps from three levels deep to the root in one click', async () => {
      const fetchMock = await renderPanel();
      await openDirectory('Cache');
      await openDirectory('unpack');
      await openDirectory('Some Mod');

      await act(async () => {
        fireEvent.click(screen.getByTestId('path-breadcrumb-root'));
      });

      await waitFor(() => {
        expect(current()).toHaveTextContent('serverdata');
        expect(screen.getByTestId('file-item-root.json')).toBeInTheDocument();
        expect(screen.getByTestId('file-item-Cache')).toBeInTheDocument();
      });
      expect(screen.queryByTestId('path-breadcrumb-root')).not.toBeInTheDocument();
      // Only the root and prefixes of the path were ever requested
      const requested = fetchMock.mock.calls.map(([url]) =>
        new URL(url).searchParams.get('directory')
      );
      expect(new Set(requested)).toEqual(
        new Set([null, 'Cache', 'Cache/unpack', 'Cache/unpack/Some Mod'])
      );
    });

    it('jumps to a middle segment and clears the selected file', async () => {
      await renderPanel();
      await openDirectory('Cache');
      await openDirectory('unpack');
      await openDirectory('Some Mod');

      await act(async () => {
        fireEvent.click(screen.getByTestId('file-item-modinfo.json'));
      });
      await waitFor(() => {
        expect(screen.getByTestId('file-viewer-content')).toHaveTextContent(
          'Cache/unpack/Some Mod/modinfo.json'
        );
      });

      await act(async () => {
        fireEvent.click(screen.getByTestId('path-breadcrumb-segment-0'));
      });

      await waitFor(() => {
        expect(current()).toHaveTextContent('Cache');
        expect(screen.getByTestId('file-item-cache.json')).toBeInTheDocument();
        expect(screen.getByTestId('file-item-unpack')).toBeInTheDocument();
      });
      expect(screen.getByTestId('file-viewer-empty')).toBeInTheDocument();
      expect(
        within(screen.getByRole('navigation', { name: 'Breadcrumb' }))
          .getAllByRole('button')
          .map((b) => b.textContent)
      ).toEqual(['serverdata']);
    });

    it('moves keyboard focus to the new current segment after a jump', async () => {
      const user = userEvent.setup();
      await renderPanel();
      await openDirectory('Cache');
      await openDirectory('unpack');

      screen.getByTestId('path-breadcrumb-segment-0').focus();
      await user.keyboard('{Enter}');

      await waitFor(() => {
        expect(current()).toHaveTextContent('Cache');
      });
      expect(current()).toHaveFocus();
    });

    it('requests a directory with spaces URL-encoded and shows its name as text', async () => {
      const fetchMock = await renderPanel();
      await openDirectory('Cache');
      await openDirectory('unpack');
      await openDirectory('Some Mod');

      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/config/files?directory=Cache%2Funpack%2FSome%20Mod'),
        expect.anything()
      );
      expect(current()).toHaveTextContent('Some Mod');
      expect(current()).toHaveAttribute('title', 'Some Mod');
    });

    it('keeps the breadcrumb when a subdirectory fails to load, so the root can be reached', async () => {
      await renderPanel(treeFetch(tree, ['Cache/unpack']));
      await act(async () => {
        fireEvent.click(screen.getByTestId('file-item-Cache'));
      });
      await waitFor(() => {
        expect(screen.getByTestId('file-item-unpack')).toBeInTheDocument();
      });
      await act(async () => {
        fireEvent.click(screen.getByTestId('file-item-unpack'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('file-manager-error')).toBeInTheDocument();
      });
      expect(screen.getByText('Failed to load files')).toBeInTheDocument();
      const error = screen.getByTestId('file-manager-error');
      expect(within(error).getByRole('navigation', { name: 'Breadcrumb' })).toBeInTheDocument();
      expect(current()).toHaveTextContent('unpack');

      await act(async () => {
        fireEvent.click(screen.getByTestId('path-breadcrumb-root'));
      });

      await waitFor(() => {
        expect(screen.queryByTestId('file-manager-error')).not.toBeInTheDocument();
        expect(screen.getByTestId('file-item-root.json')).toBeInTheDocument();
      });
    });

    it('shows no breadcrumb in the error state at the root', async () => {
      globalThis.fetch = treeFetch(tree, ['']);
      render(<FileManagerPanel />, { wrapper: createWrapper(createTestQueryClient()) });

      await waitFor(() => {
        expect(screen.getByTestId('file-manager-error')).toBeInTheDocument();
      });
      expect(screen.queryByTestId('path-breadcrumb')).not.toBeInTheDocument();
    });
  });
});
