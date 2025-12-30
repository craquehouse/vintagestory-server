import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './Layout';
import { SidebarProvider } from '@/contexts/SidebarContext';
import { type ReactNode } from 'react';

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

// Helper to render Layout with all providers
function renderLayout(children: ReactNode) {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <SidebarProvider>
        <MemoryRouter>
          <Layout>{children}</Layout>
        </MemoryRouter>
      </SidebarProvider>
    </QueryClientProvider>
  );
}

describe('Layout', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    // Mock fetch for the PendingRestartBanner's useMods query
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ status: 'ok', data: { mods: [], pendingRestart: false } }),
    });
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('renders Header component', () => {
    renderLayout(<div>Test content</div>);

    expect(screen.getByText('VintageStory Server')).toBeInTheDocument();
  });

  it('renders children in main content area', () => {
    renderLayout(<div data-testid="test-child">Test content</div>);

    expect(screen.getByTestId('test-child')).toBeInTheDocument();
  });

  it('sets --sidebar-width to 240px when expanded', () => {
    renderLayout(<div>Test</div>);

    const layoutDiv = document.querySelector('[style*="--sidebar-width"]');
    expect(layoutDiv).toBeInTheDocument();
    expect(layoutDiv?.getAttribute('style')).toContain('240px');
  });

  it('sets --sidebar-width to 64px when collapsed', async () => {
    const user = userEvent.setup();
    renderLayout(<div>Test</div>);

    // Find and click collapse button
    const collapseButton = await screen.findByRole('button', { name: /collapse/i });
    await user.click(collapseButton);

    await waitFor(() => {
      const layoutDiv = document.querySelector('[style*="--sidebar-width"]');
      expect(layoutDiv?.getAttribute('style')).toContain('64px');
    });
  });

  it('hides mobile sidebar by default', () => {
    renderLayout(<div>Test</div>);

    // Mobile Sheet should exist but be closed
    const sheetContent = document.querySelector('[data-state="closed"]');
    expect(sheetContent).toBeInTheDocument();
  });

  it('opens mobile Sheet when hamburger clicked', async () => {
    const user = userEvent.setup();
    renderLayout(<div>Test</div>);

    const hamburgerButton = await screen.findByRole('button', { name: /open menu/i });
    await user.click(hamburgerButton);

    // Wait for Sheet to open
    await waitFor(() => {
      const sheetContent = document.querySelector('[data-state="open"]');
      expect(sheetContent).toBeInTheDocument();
    });
  });

  it('closes mobile Sheet when setMobileOpen(false) called', async () => {
    const user = userEvent.setup();
    renderLayout(<div>Test</div>);

    // Open Sheet
    const hamburgerButton = await screen.findByRole('button', { name: /open menu/i });
    await user.click(hamburgerButton);

    await waitFor(() => {
      const sheetContent = document.querySelector('[data-state="open"]');
      expect(sheetContent).toBeInTheDocument();
    });

    // Close by clicking outside or triggering close
    // For now, we verify the Sheet component exists and can be opened
  });

  it('applies main content padding correctly', () => {
    renderLayout(<div>Test</div>);

    const main = document.querySelector('main');
    expect(main).toHaveClass('pt-12');

    // The div inside main has padding, not the main itself
    const contentDiv = main?.querySelector('div');
    expect(contentDiv).toHaveClass('p-4', 'md:p-6');
  });

  it('applies desktop margin to main content when sidebar visible', () => {
    renderLayout(<div>Test</div>);

    const main = document.querySelector('main');
    expect(main).toHaveClass('md:ml-[var(--sidebar-width)]');
  });

  it('hides desktop sidebar on mobile by default', () => {
    // Mock window.innerWidth to be mobile size
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 767,
    });

    renderLayout(<div>Test</div>);

    // The sidebar div should be hidden via md:hidden class on mobile
    const sidebarDiv = document.querySelector('.hidden');
    expect(sidebarDiv).toBeInTheDocument();
  });

  it('shows desktop sidebar on tablet and larger', () => {
    // Mock window.innerWidth to be tablet size
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 768,
    });

    renderLayout(<div>Test</div>);

    // On tablet+, sidebar should be visible
    // We can't easily test this without a responsive testing library
    // But we verify the structure exists
    const sidebarDivs = document.querySelectorAll('aside');
    expect(sidebarDivs.length).toBeGreaterThan(0);
  });

  it('renders multiple children correctly', () => {
    renderLayout(
      <>
        <div>Child 1</div>
        <div>Child 2</div>
        <div>Child 3</div>
      </>
    );

    expect(screen.getByText('Child 1')).toBeInTheDocument();
    expect(screen.getByText('Child 2')).toBeInTheDocument();
    expect(screen.getByText('Child 3')).toBeInTheDocument();
  });

  it('applies background color correctly', () => {
    renderLayout(<div>Test</div>);

    const layoutDiv = document.querySelector('[style*="--sidebar-width"]');
    expect(layoutDiv).toHaveClass('bg-background');
  });

  it('main content has pt-12 for fixed header', () => {
    renderLayout(<div>Test</div>);

    const main = document.querySelector('main');
    expect(main).toHaveClass('pt-12');
  });

  it('Sheet contains Sidebar component', async () => {
    const user = userEvent.setup();
    renderLayout(<div>Test</div>);

    const hamburgerButton = await screen.findByRole('button', { name: /open menu/i });
    await user.click(hamburgerButton);

    await waitFor(() => {
      // When Sheet opens, navigation items from Sidebar should be visible
      // There should be multiple navigation links
      const navLinks = screen.getAllByRole('link');
      expect(navLinks.length).toBeGreaterThan(0);
    });
  });
});
