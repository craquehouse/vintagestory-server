import { renderHook, act } from '@testing-library/react';
import { SidebarProvider, useSidebar } from './SidebarContext';
import { PreferencesProvider, usePreferences } from './PreferencesContext';
import * as cookies from '@/lib/cookies';
import type { SidebarPreference } from '@/lib/sidebar-preference';
import { setViewportWidth } from '../../tests/viewport';

// Mock cookies module
vi.mock('@/lib/cookies', () => ({
  getCookie: vi.fn(),
  setCookie: vi.fn(),
}));

// Mock next-themes to avoid matchMedia issues
vi.mock('next-themes', () => ({
  useTheme: () => ({
    theme: 'system',
    setTheme: vi.fn(),
    systemTheme: 'dark',
    resolvedTheme: 'dark',
  }),
  ThemeProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

const mockedGetCookie = vi.mocked(cookies.getCookie);
const mockedSetCookie = vi.mocked(cookies.setCookie);

// Wrapper with both PreferencesProvider and SidebarProvider
function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <PreferencesProvider>
      <SidebarProvider>{children}</SidebarProvider>
    </PreferencesProvider>
  );
}

// Helper to create wrapper with initial cookie value
function createWrapperWithPrefs(prefsJson: string | null) {
  mockedGetCookie.mockReturnValue(prefsJson);
  return Wrapper;
}

/** The sidebar value of the last vs_ui_prefs cookie written. */
function storedSidebar(): unknown {
  const call = mockedSetCookie.mock.calls.at(-1);
  expect(call?.[0]).toBe('vs_ui_prefs');
  const written = JSON.parse(call?.[1] ?? '{}');
  expect(written).not.toHaveProperty('sidebarCollapsed');
  return written.sidebar;
}

describe('SidebarContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedGetCookie.mockReturnValue(null);
  });

  it('initializes isCollapsed from preferences when sidebarCollapsed is true', () => {
    const wrapper = createWrapperWithPrefs(JSON.stringify({ sidebarCollapsed: true }));

    const { result } = renderHook(() => useSidebar(), { wrapper });

    expect(result.current.isCollapsed).toBe(true);
  });

  describe('the width rule (Story 21.8)', () => {
    it.each<[SidebarPreference, number, boolean]>([
      ['auto', 767, true],
      ['auto', 768, true],
      ['auto', 1023, true],
      ['auto', 1024, false],
      ['auto', 1440, false],
      ['expanded', 767, false],
      ['expanded', 768, false],
      ['expanded', 1023, false],
      ['expanded', 1024, false],
      ['expanded', 1440, false],
      ['collapsed', 767, true],
      ['collapsed', 768, true],
      ['collapsed', 1023, true],
      ['collapsed', 1024, true],
      ['collapsed', 1440, true],
    ])('stored %s at %ipx is collapsed: %s', (sidebar, width, collapsed) => {
      setViewportWidth(width);
      const wrapper = createWrapperWithPrefs(JSON.stringify({ sidebar }));

      const { result } = renderHook(() => useSidebar(), { wrapper });

      expect(result.current.isCollapsed).toBe(collapsed);
    });

    it('is collapsed below 1024px with no cookie', () => {
      setViewportWidth(900);

      const { result } = renderHook(() => useSidebar(), { wrapper: Wrapper });

      expect(result.current.isCollapsed).toBe(true);
      expect(storedSidebar()).toBe('auto');
    });

    it('follows a resize with auto and writes no new cookie value', () => {
      setViewportWidth(1440);
      const { result } = renderHook(() => useSidebar(), { wrapper: Wrapper });
      expect(result.current.isCollapsed).toBe(false);
      const writes = mockedSetCookie.mock.calls.length;

      act(() => setViewportWidth(900));
      expect(result.current.isCollapsed).toBe(true);

      act(() => setViewportWidth(1440));
      expect(result.current.isCollapsed).toBe(false);

      expect(mockedSetCookie.mock.calls.length).toBe(writes);
      expect(storedSidebar()).toBe('auto');
    });

    // The table in the story's Dev Notes, "Decision: what an explicit choice is"
    it.each<[SidebarPreference, number, SidebarPreference, boolean, boolean]>([
      ['auto', 900, 'expanded', false, false],
      ['expanded', 900, 'collapsed', true, true],
      ['auto', 1440, 'collapsed', true, true],
      ['collapsed', 1440, 'expanded', false, false],
    ])(
      'stored %s at %ipx, toggle: stores %s, collapsed at 900px %s, at 1440px %s',
      (start, width, stored, at900, at1440) => {
        setViewportWidth(width);
        const wrapper = createWrapperWithPrefs(JSON.stringify({ sidebar: start }));
        const { result } = renderHook(() => useSidebar(), { wrapper });

        act(() => result.current.toggleCollapse());

        expect(storedSidebar()).toBe(stored);
        act(() => setViewportWidth(900));
        expect(result.current.isCollapsed).toBe(at900);
        act(() => setViewportWidth(1440));
        expect(result.current.isCollapsed).toBe(at1440);
        expect(storedSidebar()).toBe(stored);
      }
    );

    it('UI Preferences > Automatic: stores auto, collapsed at 900px, expanded at 1440px', () => {
      setViewportWidth(1440);
      const wrapper = createWrapperWithPrefs(JSON.stringify({ sidebar: 'collapsed' }));
      const { result } = renderHook(
        () => ({ sidebar: useSidebar(), preferences: usePreferences() }),
        { wrapper }
      );

      act(() => result.current.preferences.setSidebarPreference('auto'));

      expect(storedSidebar()).toBe('auto');
      act(() => setViewportWidth(900));
      expect(result.current.sidebar.isCollapsed).toBe(true);
      act(() => setViewportWidth(1440));
      expect(result.current.sidebar.isCollapsed).toBe(false);
    });

    it('reads the old sidebarCollapsed: true as collapsed at 1440px', () => {
      setViewportWidth(1440);
      const wrapper = createWrapperWithPrefs(JSON.stringify({ sidebarCollapsed: true }));

      const { result } = renderHook(() => useSidebar(), { wrapper });

      expect(result.current.isCollapsed).toBe(true);
    });

    it('reads the old sidebarCollapsed: false as auto (collapsed at 900px, expanded at 1440px)', () => {
      setViewportWidth(900);
      const wrapper = createWrapperWithPrefs(JSON.stringify({ sidebarCollapsed: false }));

      const { result } = renderHook(() => useSidebar(), { wrapper });

      expect(result.current.isCollapsed).toBe(true);
      act(() => setViewportWidth(1440));
      expect(result.current.isCollapsed).toBe(false);
    });
  });

  it('initializes isMobileOpen to false by default', () => {
    const { result } = renderHook(() => useSidebar(), { wrapper: Wrapper });

    expect(result.current.isMobileOpen).toBe(false);
  });

  it('persists isCollapsed to cookie when changed to true', () => {
    const { result } = renderHook(() => useSidebar(), { wrapper: Wrapper });

    act(() => {
      result.current.toggleCollapse();
    });

    expect(result.current.isCollapsed).toBe(true);
    expect(storedSidebar()).toBe('collapsed');
  });

  it('persists isCollapsed to cookie when changed to false', () => {
    const wrapper = createWrapperWithPrefs(JSON.stringify({ sidebarCollapsed: true }));

    const { result } = renderHook(() => useSidebar(), { wrapper });

    act(() => {
      result.current.toggleCollapse();
    });

    expect(result.current.isCollapsed).toBe(false);
    expect(storedSidebar()).toBe('expanded');
  });

  it('toggleCollapse flips state from false to true', () => {
    const { result } = renderHook(() => useSidebar(), { wrapper: Wrapper });

    expect(result.current.isCollapsed).toBe(false);

    act(() => {
      result.current.toggleCollapse();
    });

    expect(result.current.isCollapsed).toBe(true);
  });

  it('toggleCollapse flips state from true to false', () => {
    const wrapper = createWrapperWithPrefs(JSON.stringify({ sidebarCollapsed: true }));

    const { result } = renderHook(() => useSidebar(), { wrapper });

    expect(result.current.isCollapsed).toBe(true);

    act(() => {
      result.current.toggleCollapse();
    });

    expect(result.current.isCollapsed).toBe(false);
  });

  it('setMobileOpen updates mobile state to true', () => {
    const { result } = renderHook(() => useSidebar(), { wrapper: Wrapper });

    expect(result.current.isMobileOpen).toBe(false);

    act(() => {
      result.current.setMobileOpen(true);
    });

    expect(result.current.isMobileOpen).toBe(true);
  });

  it('setMobileOpen updates mobile state to false', () => {
    const { result } = renderHook(() => useSidebar(), { wrapper: Wrapper });

    act(() => {
      result.current.setMobileOpen(true);
    });

    expect(result.current.isMobileOpen).toBe(true);

    act(() => {
      result.current.setMobileOpen(false);
    });

    expect(result.current.isMobileOpen).toBe(false);
  });

  it('does not persist isMobileOpen to cookie', () => {
    const { result } = renderHook(() => useSidebar(), { wrapper: Wrapper });

    // Clear any initial cookie writes
    mockedSetCookie.mockClear();

    act(() => {
      result.current.setMobileOpen(true);
    });

    // isMobileOpen change should NOT trigger cookie update
    expect(mockedSetCookie).not.toHaveBeenCalled();
  });

  it('throws error when useSidebar is used outside SidebarProvider', () => {
    // Suppress console.error for this test
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => {
      renderHook(() => useSidebar());
    }).toThrow('useSidebar must be used within a SidebarProvider');

    consoleError.mockRestore();
  });

  it('persists isCollapsed on every state change', () => {
    const { result } = renderHook(() => useSidebar(), { wrapper: Wrapper });

    // First toggle
    act(() => {
      result.current.toggleCollapse();
    });
    expect(storedSidebar()).toBe('collapsed');

    // Second toggle
    act(() => {
      result.current.toggleCollapse();
    });
    expect(storedSidebar()).toBe('expanded');

    // Third toggle
    act(() => {
      result.current.toggleCollapse();
    });
    expect(storedSidebar()).toBe('collapsed');
  });
});
