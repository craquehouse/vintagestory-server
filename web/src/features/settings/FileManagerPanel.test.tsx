import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
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
});
