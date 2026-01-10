import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { toast } from 'sonner';
import { InstallConfirmDialog } from './InstallConfirmDialog';
import * as useMods from '@/hooks/use-mods';

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock useInstallMod hook
vi.mock('@/hooks/use-mods', async () => {
  const actual = await vi.importActual('@/hooks/use-mods');
  return {
    ...actual,
    useInstallMod: vi.fn(),
  };
});

// Test data
const mockMod = {
  slug: 'carrycapacity',
  name: 'Carry Capacity',
  version: '1.2.0',
  author: 'copygirl',
  logoUrl: null,
};

const mockModWithLogo = {
  ...mockMod,
  logoUrl: 'https://mods.vintagestory.at/assets/logo.png',
};

// Helper to create a QueryClient wrapper
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe('InstallConfirmDialog', () => {
  const mockMutate = vi.fn();
  const mockOnOpenChange = vi.fn();
  const mockOnSuccess = vi.fn();
  const mockOnError = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useMods.useInstallMod).mockReturnValue({
      mutate: mockMutate,
      isPending: false,
      isError: false,
      error: null,
      isSuccess: false,
      isIdle: true,
      data: undefined,
      variables: undefined,
      reset: vi.fn(),
      status: 'idle',
      mutateAsync: vi.fn(),
      context: undefined,
      failureCount: 0,
      failureReason: null,
      submittedAt: 0,
      isPaused: false,
    });
  });

  describe('rendering', () => {
    it('renders dialog with mod info', () => {
      render(
        <InstallConfirmDialog
          mod={mockMod}
          compatibility={{ status: 'compatible' }}
          open={true}
          onOpenChange={mockOnOpenChange}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByTestId('install-confirm-dialog')).toBeInTheDocument();
      expect(screen.getByTestId('install-dialog-mod-name')).toHaveTextContent('Carry Capacity');
      expect(screen.getByTestId('install-dialog-mod-author')).toHaveTextContent('by copygirl');
      expect(screen.getByTestId('install-dialog-mod-version')).toHaveTextContent('Version: 1.2.0');
    });

    it('renders dialog title and description', () => {
      render(
        <InstallConfirmDialog
          mod={mockMod}
          compatibility={{ status: 'compatible' }}
          open={true}
          onOpenChange={mockOnOpenChange}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText('Install Mod')).toBeInTheDocument();
      expect(screen.getByText('Confirm installation of this mod to your server.')).toBeInTheDocument();
    });

    it('renders placeholder when no logo provided', () => {
      render(
        <InstallConfirmDialog
          mod={mockMod}
          compatibility={{ status: 'compatible' }}
          open={true}
          onOpenChange={mockOnOpenChange}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByTestId('install-dialog-placeholder')).toBeInTheDocument();
      expect(screen.queryByTestId('install-dialog-logo')).not.toBeInTheDocument();
    });

    it('renders logo when provided', () => {
      render(
        <InstallConfirmDialog
          mod={mockModWithLogo}
          compatibility={{ status: 'compatible' }}
          open={true}
          onOpenChange={mockOnOpenChange}
        />,
        { wrapper: createWrapper() }
      );

      const logo = screen.getByTestId('install-dialog-logo');
      expect(logo).toBeInTheDocument();
      expect(logo).toHaveAttribute('src', 'https://mods.vintagestory.at/assets/logo.png');
    });

    it('renders CompatibilityBadge', () => {
      render(
        <InstallConfirmDialog
          mod={mockMod}
          compatibility={{ status: 'compatible' }}
          open={true}
          onOpenChange={mockOnOpenChange}
        />,
        { wrapper: createWrapper() }
      );

      const badge = screen.getByTestId('compatibility-badge');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveAttribute('data-status', 'compatible');
    });
  });

  describe('compatibility warnings', () => {
    it('shows warning for not_verified status', () => {
      render(
        <InstallConfirmDialog
          mod={mockMod}
          compatibility={{ status: 'not_verified' }}
          open={true}
          onOpenChange={mockOnOpenChange}
        />,
        { wrapper: createWrapper() }
      );

      const warning = screen.getByTestId('install-dialog-warning');
      expect(warning).toBeInTheDocument();
      expect(warning).toHaveTextContent('has not been verified');
    });

    it('shows warning for incompatible status', () => {
      render(
        <InstallConfirmDialog
          mod={mockMod}
          compatibility={{ status: 'incompatible' }}
          open={true}
          onOpenChange={mockOnOpenChange}
        />,
        { wrapper: createWrapper() }
      );

      const warning = screen.getByTestId('install-dialog-warning');
      expect(warning).toBeInTheDocument();
      expect(warning).toHaveTextContent('known to be incompatible');
    });

    it('does not show warning for compatible status', () => {
      render(
        <InstallConfirmDialog
          mod={mockMod}
          compatibility={{ status: 'compatible' }}
          open={true}
          onOpenChange={mockOnOpenChange}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.queryByTestId('install-dialog-warning')).not.toBeInTheDocument();
    });
  });

  describe('button interactions', () => {
    it('calls onOpenChange(false) when Cancel is clicked', async () => {
      const user = userEvent.setup();

      render(
        <InstallConfirmDialog
          mod={mockMod}
          compatibility={{ status: 'compatible' }}
          open={true}
          onOpenChange={mockOnOpenChange}
        />,
        { wrapper: createWrapper() }
      );

      await user.click(screen.getByTestId('install-dialog-cancel'));

      expect(mockOnOpenChange).toHaveBeenCalledWith(false);
    });

    it('calls install mutation when Install is clicked', async () => {
      const user = userEvent.setup();

      render(
        <InstallConfirmDialog
          mod={mockMod}
          compatibility={{ status: 'compatible' }}
          open={true}
          onOpenChange={mockOnOpenChange}
        />,
        { wrapper: createWrapper() }
      );

      await user.click(screen.getByTestId('install-dialog-confirm'));

      expect(mockMutate).toHaveBeenCalledWith(
        { slug: 'carrycapacity', version: '1.2.0' },
        expect.objectContaining({
          onSuccess: expect.any(Function),
          onError: expect.any(Function),
        })
      );
    });
  });

  describe('loading state', () => {
    it('shows loading state when isPending', () => {
      vi.mocked(useMods.useInstallMod).mockReturnValue({
        mutate: mockMutate,
        isPending: true,
        isError: false,
        error: null,
        isSuccess: false,
        isIdle: false,
        data: undefined,
        variables: { slug: 'carrycapacity', version: '1.2.0' },
        reset: vi.fn(),
        status: 'pending',
        mutateAsync: vi.fn(),
        context: undefined,
        failureCount: 0,
        failureReason: null,
        submittedAt: 0,
        isPaused: false,
      });

      render(
        <InstallConfirmDialog
          mod={mockMod}
          compatibility={{ status: 'compatible' }}
          open={true}
          onOpenChange={mockOnOpenChange}
        />,
        { wrapper: createWrapper() }
      );

      const installButton = screen.getByTestId('install-dialog-confirm');
      expect(installButton).toHaveTextContent('Installing...');
      expect(installButton).toBeDisabled();

      const cancelButton = screen.getByTestId('install-dialog-cancel');
      expect(cancelButton).toBeDisabled();
    });
  });

  describe('success callback', () => {
    it('calls onSuccess and closes dialog on successful install', async () => {
      const user = userEvent.setup();

      // Make mutate call onSuccess synchronously for testing
      mockMutate.mockImplementation((_params, options) => {
        options?.onSuccess?.();
      });

      render(
        <InstallConfirmDialog
          mod={mockMod}
          compatibility={{ status: 'compatible' }}
          open={true}
          onOpenChange={mockOnOpenChange}
          onSuccess={mockOnSuccess}
        />,
        { wrapper: createWrapper() }
      );

      await user.click(screen.getByTestId('install-dialog-confirm'));

      await waitFor(() => {
        expect(toast.success).toHaveBeenCalledWith(
          'Installed Carry Capacity',
          expect.objectContaining({
            description: 'Version 1.2.0 installed successfully.',
          })
        );
      });

      expect(mockOnOpenChange).toHaveBeenCalledWith(false);
      expect(mockOnSuccess).toHaveBeenCalled();
    });
  });

  describe('error callback', () => {
    it('calls onError and shows error toast on install failure', async () => {
      const user = userEvent.setup();
      const testError = new Error('Installation failed: network error');

      // Make mutate call onError synchronously for testing
      mockMutate.mockImplementation((_params, options) => {
        options?.onError?.(testError);
      });

      render(
        <InstallConfirmDialog
          mod={mockMod}
          compatibility={{ status: 'compatible' }}
          open={true}
          onOpenChange={mockOnOpenChange}
          onError={mockOnError}
        />,
        { wrapper: createWrapper() }
      );

      await user.click(screen.getByTestId('install-dialog-confirm'));

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith(
          'Installation failed',
          expect.objectContaining({
            description: 'Installation failed: network error',
          })
        );
      });

      expect(mockOnError).toHaveBeenCalledWith(testError);
      // Dialog should remain open on error
      expect(mockOnOpenChange).not.toHaveBeenCalledWith(false);
    });
  });

  describe('dialog visibility', () => {
    it('is not visible when open is false', () => {
      render(
        <InstallConfirmDialog
          mod={mockMod}
          compatibility={{ status: 'compatible' }}
          open={false}
          onOpenChange={mockOnOpenChange}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.queryByTestId('install-confirm-dialog')).not.toBeInTheDocument();
    });

    it('is visible when open is true', () => {
      render(
        <InstallConfirmDialog
          mod={mockMod}
          compatibility={{ status: 'compatible' }}
          open={true}
          onOpenChange={mockOnOpenChange}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByTestId('install-confirm-dialog')).toBeInTheDocument();
    });
  });
});
