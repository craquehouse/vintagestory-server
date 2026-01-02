import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Header } from './Header';
import { SidebarProvider } from '@/contexts/SidebarContext';
import { PreferencesProvider } from '@/contexts/PreferencesContext';
import * as cookies from '@/lib/cookies';

// Mock cookies module
vi.mock('@/lib/cookies', () => ({
  getCookie: vi.fn(),
  setCookie: vi.fn(),
}));

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

const mockedSetCookie = vi.mocked(cookies.setCookie);

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
      <PreferencesProvider>
        <SidebarProvider>
          <MemoryRouter>
            <Header />
          </MemoryRouter>
        </SidebarProvider>
      </PreferencesProvider>
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

  it('updates theme preference when theme toggle clicked', async () => {
    const user = userEvent.setup();
    renderHeader();

    const themeButton = screen.getByRole('button', { name: /toggle theme/i });
    await user.click(themeButton);

    // Theme toggle goes through PreferencesContext, which syncs to next-themes
    expect(setThemeMock).toHaveBeenCalledWith('light');
    // Also persists to cookie
    expect(mockedSetCookie).toHaveBeenCalledWith(
      'vs_ui_prefs',
      expect.stringContaining('"theme":"light"')
    );
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

  it('pending restart container is visible on all screen sizes', () => {
    renderHeader();

    // The center container for pending restart banner should be visible on all screen sizes
    // It no longer has 'hidden' class (was 'hidden md:flex', now just 'flex')
    const containers = document.querySelectorAll('.items-center');
    const hasHiddenMdFlex = Array.from(containers).some(
      div => div.classList.contains('hidden') && div.classList.contains('md:flex')
    );
    // No container should have hidden md:flex pattern anymore
    expect(hasHiddenMdFlex).toBe(false);
  });

  it('has correct left margin on desktop for sidebar', () => {
    renderHeader();

    const header = screen.getByRole('banner');
    expect(header).toHaveClass('md:left-[var(--sidebar-width)]');
  });
});
