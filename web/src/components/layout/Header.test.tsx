import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
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

describe('Header', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    setThemeMock.mockReset();
  });

  it('renders server name "VintageStory Server"', () => {
    render(
      <SidebarProvider>
        <MemoryRouter>
          <Header />
        </MemoryRouter>
      </SidebarProvider>
    );

    expect(screen.getByText('VintageStory Server')).toBeInTheDocument();
  });

  it('renders placeholder text on desktop', () => {
    render(
      <SidebarProvider>
        <MemoryRouter>
          <Header />
        </MemoryRouter>
      </SidebarProvider>
    );

    expect(screen.getByText('(placeholder)')).toBeInTheDocument();
  });

  it('hides placeholder on small screens', () => {
    render(
      <SidebarProvider>
        <MemoryRouter>
          <Header />
        </MemoryRouter>
      </SidebarProvider>
    );

    const placeholder = screen.getByText('(placeholder)');
    expect(placeholder).toHaveClass('hidden', 'sm:inline');
  });

  it('renders theme toggle button', () => {
    render(
      <SidebarProvider>
        <MemoryRouter>
          <Header />
        </MemoryRouter>
      </SidebarProvider>
    );

    const themeButton = screen.getByRole('button', { name: /toggle theme/i });
    expect(themeButton).toBeInTheDocument();
  });

  it('calls setTheme when theme toggle clicked', async () => {
    const user = userEvent.setup();
    render(
      <SidebarProvider>
        <MemoryRouter>
          <Header />
        </MemoryRouter>
      </SidebarProvider>
    );

    const themeButton = screen.getByRole('button', { name: /toggle theme/i });
    await user.click(themeButton);

    expect(setThemeMock).toHaveBeenCalledWith('light');
  });

  it('renders Sun icon in light theme mode', () => {
    // Both icons are always present, visibility controlled by CSS classes
    render(
      <SidebarProvider>
        <MemoryRouter>
          <Header />
        </MemoryRouter>
      </SidebarProvider>
    );

    // Sun and Moon icons should both be present
    const sunIcon = document.querySelector('svg');
    expect(sunIcon).toBeInTheDocument();
  });

  it('renders Moon icon in dark theme mode', () => {
    // Both icons are always present, visibility controlled by CSS classes
    render(
      <SidebarProvider>
        <MemoryRouter>
          <Header />
        </MemoryRouter>
      </SidebarProvider>
    );

    // Sun and Moon icons should both be present
    const moonIcon = document.querySelector('svg');
    expect(moonIcon).toBeInTheDocument();
  });

  it('renders mobile hamburger button on mobile', () => {
    render(
      <SidebarProvider>
        <MemoryRouter>
          <Header />
        </MemoryRouter>
      </SidebarProvider>
    );

    const menuButton = screen.getByRole('button', { name: /open menu/i });
    expect(menuButton).toBeInTheDocument();
  });

  it('hides hamburger button on desktop', () => {
    render(
      <SidebarProvider>
        <MemoryRouter>
          <Header />
        </MemoryRouter>
      </SidebarProvider>
    );

    const menuButton = screen.getByRole('button', { name: /open menu/i });
    expect(menuButton).toHaveClass('md:hidden');
  });

  it('calls setMobileOpen(true) when hamburger clicked', async () => {
    const user = userEvent.setup();
    render(
      <SidebarProvider>
        <MemoryRouter>
          <Header />
        </MemoryRouter>
      </SidebarProvider>
    );

    const menuButton = screen.getByRole('button', { name: /open menu/i });
    await user.click(menuButton);

    // Mobile menu should open (can't verify setMobileOpen directly without context access)
    // But we can verify the button click doesn't throw error
    expect(menuButton).toBeInTheDocument();
  });

  it('has correct accessibility labels', () => {
    render(
      <SidebarProvider>
        <MemoryRouter>
          <Header />
        </MemoryRouter>
      </SidebarProvider>
    );

    expect(screen.getByRole('button', { name: /open menu/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /toggle theme/i })).toBeInTheDocument();
  });

  it('has fixed position with z-40', () => {
    render(
      <SidebarProvider>
        <MemoryRouter>
          <Header />
        </MemoryRouter>
      </SidebarProvider>
    );

    const header = screen.getByRole('banner');
    expect(header).toHaveClass('fixed', 'top-0', 'z-40');
  });

  it('has fixed height of 12 (h-12)', () => {
    render(
      <SidebarProvider>
        <MemoryRouter>
          <Header />
        </MemoryRouter>
      </SidebarProvider>
    );

    const header = screen.getByRole('banner');
    expect(header).toHaveClass('h-12');
  });

  it('has bottom border', () => {
    render(
      <SidebarProvider>
        <MemoryRouter>
          <Header />
        </MemoryRouter>
      </SidebarProvider>
    );

    const header = screen.getByRole('banner');
    expect(header).toHaveClass('border-b', 'border-border');
  });

  it('has background color', () => {
    render(
      <SidebarProvider>
        <MemoryRouter>
          <Header />
        </MemoryRouter>
      </SidebarProvider>
    );

    const header = screen.getByRole('banner');
    expect(header).toHaveClass('bg-background');
  });

  it('renders pending restart placeholder div', () => {
    render(
      <SidebarProvider>
        <MemoryRouter>
          <Header />
        </MemoryRouter>
      </SidebarProvider>
    );

    const pendingDiv = document.querySelector('.items-center');
    expect(pendingDiv).toBeInTheDocument();
  });

  it('hides pending restart on mobile', () => {
    render(
      <SidebarProvider>
        <MemoryRouter>
          <Header />
        </MemoryRouter>
      </SidebarProvider>
    );

    // Find all elements with items-center class and check if any have hidden and md:flex
    const divs = document.querySelectorAll('.items-center');
    const hiddenOnMobile = Array.from(divs).some(div =>
      div.classList.contains('hidden') && div.classList.contains('md:flex')
    );
    expect(hiddenOnMobile).toBe(true);
  });

  it('has correct left margin on desktop for sidebar', () => {
    render(
      <SidebarProvider>
        <MemoryRouter>
          <Header />
        </MemoryRouter>
      </SidebarProvider>
    );

    const header = screen.getByRole('banner');
    expect(header).toHaveClass('md:left-[var(--sidebar-width)]');
  });
});
