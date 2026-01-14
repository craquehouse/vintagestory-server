/**
 * QuickInstallButton Tests - Story 13.5
 *
 * Tests for the quick install/update button component.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';
import { QuickInstallButton } from './QuickInstallButton';
import type { VersionInfo } from '@/api/types';

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

// Wrapper component for rendering with QueryClientProvider
function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

// Mock versions data
const mockVersions: VersionInfo[] = [
  {
    version: '1.21.6',
    filename: 'vs_server_linux-x64_1.21.6.tar.gz',
    filesize: '45.2 MB',
    md5: 'abc123',
    cdnUrl: 'https://cdn.example.com/1.21.6',
    localUrl: '/local/1.21.6',
    isLatest: true,
    channel: 'stable',
  },
  {
    version: '1.21.5',
    filename: 'vs_server_linux-x64_1.21.5.tar.gz',
    filesize: '44.8 MB',
    md5: 'def456',
    cdnUrl: 'https://cdn.example.com/1.21.5',
    localUrl: '/local/1.21.5',
    isLatest: false,
    channel: 'stable',
  },
  {
    version: '1.22.0-pre.1',
    filename: 'vs_server_linux-x64_1.22.0-pre.1.tar.gz',
    filesize: '46.1 MB',
    md5: 'ghi789',
    cdnUrl: 'https://cdn.example.com/1.22.0-pre.1',
    localUrl: '/local/1.22.0-pre.1',
    isLatest: true,
    channel: 'unstable',
  },
];

describe('QuickInstallButton', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  describe('when not installed', () => {
    it('shows "Install Latest Stable" button with version', () => {
      const queryClient = createTestQueryClient();
      render(
        <QuickInstallButton
          versions={mockVersions}
          installedVersion={null}
          isLoadingVersions={false}
        />,
        { wrapper: createWrapper(queryClient) }
      );

      expect(screen.getByTestId('quick-install-button')).toBeInTheDocument();
      expect(screen.getByText(/Install Latest Stable/)).toBeInTheDocument();
      expect(screen.getByText(/1\.21\.6/)).toBeInTheDocument();
    });

    it('triggers install mutation when clicked', async () => {
      const user = userEvent.setup();
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ status: 'ok', data: { message: 'Installing' } }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(
        <QuickInstallButton
          versions={mockVersions}
          installedVersion={null}
          isLoadingVersions={false}
        />,
        { wrapper: createWrapper(queryClient) }
      );

      await user.click(screen.getByTestId('quick-install-button'));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringMatching(/\/api\/v1alpha1\/server\/install/),
          expect.objectContaining({
            method: 'POST',
          })
        );
      });
    });
  });

  describe('when installed with update available', () => {
    it('shows "Update to" button with new version', () => {
      const queryClient = createTestQueryClient();
      render(
        <QuickInstallButton
          versions={mockVersions}
          installedVersion="1.21.5"
          isLoadingVersions={false}
        />,
        { wrapper: createWrapper(queryClient) }
      );

      expect(screen.getByTestId('quick-install-button')).toBeInTheDocument();
      expect(screen.getByText(/Update to/)).toBeInTheDocument();
      expect(screen.getByText(/1\.21\.6/)).toBeInTheDocument();
    });

    it('triggers install mutation with force flag when clicked', async () => {
      const user = userEvent.setup();
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ status: 'ok', data: { message: 'Installing' } }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(
        <QuickInstallButton
          versions={mockVersions}
          installedVersion="1.21.5"
          isLoadingVersions={false}
        />,
        { wrapper: createWrapper(queryClient) }
      );

      await user.click(screen.getByTestId('quick-install-button'));

      await waitFor(() => {
        // Check that the request includes force: true in body for upgrade
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringMatching(/\/api\/v1alpha1\/server\/install/),
          expect.objectContaining({
            method: 'POST',
            body: expect.stringContaining('"force":true'),
          })
        );
      });
    });
  });

  describe('when installed and up to date', () => {
    it('does not render button when version is current', () => {
      const queryClient = createTestQueryClient();
      render(
        <QuickInstallButton
          versions={mockVersions}
          installedVersion="1.21.6"
          isLoadingVersions={false}
        />,
        { wrapper: createWrapper(queryClient) }
      );

      expect(screen.queryByTestId('quick-install-button')).not.toBeInTheDocument();
    });
  });

  describe('loading states', () => {
    it('does not render when versions are loading', () => {
      const queryClient = createTestQueryClient();
      render(
        <QuickInstallButton
          versions={[]}
          installedVersion={null}
          isLoadingVersions={true}
        />,
        { wrapper: createWrapper(queryClient) }
      );

      expect(screen.queryByTestId('quick-install-button')).not.toBeInTheDocument();
    });

    it('does not render when no versions available', () => {
      const queryClient = createTestQueryClient();
      render(
        <QuickInstallButton
          versions={[]}
          installedVersion={null}
          isLoadingVersions={false}
        />,
        { wrapper: createWrapper(queryClient) }
      );

      expect(screen.queryByTestId('quick-install-button')).not.toBeInTheDocument();
    });

    it('does not render when no latest stable version found', () => {
      const unstableOnly: VersionInfo[] = [
        {
          version: '1.22.0-pre.1',
          filename: 'vs_server_linux-x64_1.22.0-pre.1.tar.gz',
          filesize: '46.1 MB',
          md5: 'ghi789',
          cdnUrl: 'https://cdn.example.com/1.22.0-pre.1',
          localUrl: '/local/1.22.0-pre.1',
          isLatest: true,
          channel: 'unstable',
        },
      ];

      const queryClient = createTestQueryClient();
      render(
        <QuickInstallButton
          versions={unstableOnly}
          installedVersion={null}
          isLoadingVersions={false}
        />,
        { wrapper: createWrapper(queryClient) }
      );

      expect(screen.queryByTestId('quick-install-button')).not.toBeInTheDocument();
    });

    it('shows loading state during installation', async () => {
      const user = userEvent.setup();
      // Make the fetch never resolve to keep the button in loading state
      globalThis.fetch = vi.fn().mockReturnValue(new Promise(() => {}));

      const queryClient = createTestQueryClient();
      render(
        <QuickInstallButton
          versions={mockVersions}
          installedVersion={null}
          isLoadingVersions={false}
        />,
        { wrapper: createWrapper(queryClient) }
      );

      await user.click(screen.getByTestId('quick-install-button'));

      await waitFor(() => {
        expect(screen.getByText(/Installing/)).toBeInTheDocument();
      });

      // Button should be disabled during installation
      expect(screen.getByTestId('quick-install-button')).toBeDisabled();
    });
  });

  describe('server running confirmation', () => {
    it('shows confirmation dialog when server is running and update clicked', async () => {
      const user = userEvent.setup();
      const queryClient = createTestQueryClient();
      render(
        <QuickInstallButton
          versions={mockVersions}
          installedVersion="1.21.5"
          isLoadingVersions={false}
          serverState="running"
        />,
        { wrapper: createWrapper(queryClient) }
      );

      await user.click(screen.getByTestId('quick-install-button'));

      // Confirmation dialog should appear
      expect(screen.getByTestId('quick-install-confirm-dialog')).toBeInTheDocument();
      expect(screen.getByText(/Server Currently Running/)).toBeInTheDocument();
      expect(screen.getByText(/will be stopped/)).toBeInTheDocument();
    });

    it('does not show confirmation when server is not running', async () => {
      const user = userEvent.setup();
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ status: 'ok', data: { message: 'Installing' } }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(
        <QuickInstallButton
          versions={mockVersions}
          installedVersion="1.21.5"
          isLoadingVersions={false}
          serverState="installed"
        />,
        { wrapper: createWrapper(queryClient) }
      );

      await user.click(screen.getByTestId('quick-install-button'));

      // Should NOT show confirmation dialog
      expect(screen.queryByTestId('quick-install-confirm-dialog')).not.toBeInTheDocument();

      // Should trigger install directly
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      });
    });

    it('triggers install when confirmation is accepted', async () => {
      const user = userEvent.setup();
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ status: 'ok', data: { message: 'Installing' } }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(
        <QuickInstallButton
          versions={mockVersions}
          installedVersion="1.21.5"
          isLoadingVersions={false}
          serverState="running"
        />,
        { wrapper: createWrapper(queryClient) }
      );

      // Click update button
      await user.click(screen.getByTestId('quick-install-button'));

      // Click proceed in confirmation dialog
      await user.click(screen.getByTestId('confirm-dialog-proceed'));

      // Should trigger install
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringMatching(/\/api\/v1alpha1\/server\/install/),
          expect.objectContaining({
            method: 'POST',
          })
        );
      });
    });

    it('does not trigger install when confirmation is cancelled', async () => {
      const user = userEvent.setup();
      const mockFetch = vi.fn();
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(
        <QuickInstallButton
          versions={mockVersions}
          installedVersion="1.21.5"
          isLoadingVersions={false}
          serverState="running"
        />,
        { wrapper: createWrapper(queryClient) }
      );

      // Click update button
      await user.click(screen.getByTestId('quick-install-button'));

      // Click cancel in confirmation dialog
      await user.click(screen.getByTestId('confirm-dialog-cancel'));

      // Dialog should close
      await waitFor(() => {
        expect(screen.queryByTestId('quick-install-confirm-dialog')).not.toBeInTheDocument();
      });

      // Should NOT trigger install
      expect(mockFetch).not.toHaveBeenCalled();
    });

    it('does not show confirmation for fresh install even with serverState undefined', async () => {
      const user = userEvent.setup();
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ status: 'ok', data: { message: 'Installing' } }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(
        <QuickInstallButton
          versions={mockVersions}
          installedVersion={null}
          isLoadingVersions={false}
        />,
        { wrapper: createWrapper(queryClient) }
      );

      await user.click(screen.getByTestId('quick-install-button'));

      // Should NOT show confirmation dialog for fresh install
      expect(screen.queryByTestId('quick-install-confirm-dialog')).not.toBeInTheDocument();

      // Should trigger install directly
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      });
    });
  });
});
