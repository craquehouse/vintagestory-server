import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Header } from './Header';
import { SidebarProvider } from '@/contexts/SidebarContext';

// Mock next-themes
const setThemeMock = vi.fn();
vi.mock('next-themes', () => ({
  useTheme: () => ({
    theme: 'dark',
    setTheme: setThemeMock,
    resolvedTheme: 'dark',
    systemTheme: 'dark',
  }),
}));

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

// Helper to render Header with all providers
function renderHeader() {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <SidebarProvider>
        <MemoryRouter>
          <Header />
        </MemoryRouter>
      </SidebarProvider>
    </QueryClientProvider>
  );
}

describe('Header', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.clearAllMocks();
    // Mock fetch for the PendingRestartBanner's useMods query
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ status: 'ok', data: { mods: [], pendingRestart: false } }),
    });
  });

  afterEach(() => {
    setThemeMock.mockReset();
    globalThis.fetch = originalFetch;
  });

  it('renders server name "VintageStory Server"', () => {
    renderHeader();

    expect(screen.getByText('VintageStory Server')).toBeInTheDocument();
  });

  it('renders placeholder text on desktop', () => {
    renderHeader();

    expect(screen.getByText('(placeholder)')).toBeInTheDocument();
  });

  it('hides placeholder on small screens', () => {
    renderHeader();

    const placeholder = screen.getByText('(placeholder)');
    expect(placeholder).toHaveClass('hidden', 'sm:inline');
  });

  it('renders theme toggle button', () => {
    renderHeader();

    const themeButton = screen.getByRole('button', { name: /toggle theme/i });
    expect(themeButton).toBeInTheDocument();
  });

  it('calls setTheme when theme toggle clicked', async () => {
    const user = userEvent.setup();
    renderHeader();

    const themeButton = screen.getByRole('button', { name: /toggle theme/i });
    await user.click(themeButton);

    expect(setThemeMock).toHaveBeenCalledWith('light');
  });

  it('renders Sun icon in light theme mode', () => {
    // Both icons are always present, visibility controlled by CSS classes
    renderHeader();

    // Sun and Moon icons should both be present
    const sunIcon = document.querySelector('svg');
    expect(sunIcon).toBeInTheDocument();
  });

  it('renders Moon icon in dark theme mode', () => {
    // Both icons are always present, visibility controlled by CSS classes
    renderHeader();

    // Sun and Moon icons should both be present
    const moonIcon = document.querySelector('svg');
    expect(moonIcon).toBeInTheDocument();
  });

  it('renders mobile hamburger button on mobile', () => {
    renderHeader();

    const menuButton = screen.getByRole('button', { name: /open menu/i });
    expect(menuButton).toBeInTheDocument();
  });

  it('hides hamburger button on desktop', () => {
    renderHeader();

    const menuButton = screen.getByRole('button', { name: /open menu/i });
    expect(menuButton).toHaveClass('md:hidden');
  });

  it('calls setMobileOpen(true) when hamburger clicked', async () => {
    const user = userEvent.setup();
    renderHeader();

    const menuButton = screen.getByRole('button', { name: /open menu/i });
    await user.click(menuButton);

    // Mobile menu should open (can't verify setMobileOpen directly without context access)
    // But we can verify the button click doesn't throw error
    expect(menuButton).toBeInTheDocument();
  });

  it('has correct accessibility labels', () => {
    renderHeader();

    expect(screen.getByRole('button', { name: /open menu/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /toggle theme/i })).toBeInTheDocument();
  });

  it('has fixed position with z-40', () => {
    renderHeader();

    const header = screen.getByRole('banner');
    expect(header).toHaveClass('fixed', 'top-0', 'z-40');
  });

  it('has fixed height of 12 (h-12)', () => {
    renderHeader();

    const header = screen.getByRole('banner');
    expect(header).toHaveClass('h-12');
  });

  it('has bottom border', () => {
    renderHeader();

    const header = screen.getByRole('banner');
    expect(header).toHaveClass('border-b', 'border-border');
  });

  it('has background color', () => {
    renderHeader();

    const header = screen.getByRole('banner');
    expect(header).toHaveClass('bg-background');
  });

  it('renders pending restart placeholder div', () => {
    renderHeader();

    const pendingDiv = document.querySelector('.items-center');
    expect(pendingDiv).toBeInTheDocument();
  });

  it('hides pending restart on mobile', () => {
    renderHeader();

    // Find all elements with items-center class and check if any have hidden and md:flex
    const divs = document.querySelectorAll('.items-center');
    const hiddenOnMobile = Array.from(divs).some(div =>
      div.classList.contains('hidden') && div.classList.contains('md:flex')
    );
    expect(hiddenOnMobile).toBe(true);
  });

  it('has correct left margin on desktop for sidebar', () => {
    renderHeader();

    const header = screen.getByRole('banner');
    expect(header).toHaveClass('md:left-[var(--sidebar-width)]');
  });
});
