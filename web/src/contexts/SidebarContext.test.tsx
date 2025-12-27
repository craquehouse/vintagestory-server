import { renderHook, act } from '@testing-library/react';
import { SidebarProvider, useSidebar } from './SidebarContext';

const SIDEBAR_COLLAPSED_KEY = 'sidebar-collapsed';

describe('SidebarContext', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();
    // Reset all mocks
    vi.restoreAllMocks();
  });

  it('initializes isCollapsed from localStorage on mount', () => {
    localStorage.setItem(SIDEBAR_COLLAPSED_KEY, 'true');

    const { result } = renderHook(() => useSidebar(), {
      wrapper: SidebarProvider,
    });

    expect(result.current.isCollapsed).toBe(true);
  });

  it('initializes isCollapsed to false when localStorage is empty', () => {
    const { result } = renderHook(() => useSidebar(), {
      wrapper: SidebarProvider,
    });

    expect(result.current.isCollapsed).toBe(false);
  });

  it('initializes isCollapsed to false when localStorage has "false"', () => {
    localStorage.setItem(SIDEBAR_COLLAPSED_KEY, 'false');

    const { result } = renderHook(() => useSidebar(), {
      wrapper: SidebarProvider,
    });

    expect(result.current.isCollapsed).toBe(false);
  });

  it('initializes isMobileOpen to false by default', () => {
    const { result } = renderHook(() => useSidebar(), {
      wrapper: SidebarProvider,
    });

    expect(result.current.isMobileOpen).toBe(false);
  });

  it('persists isCollapsed to localStorage when changed to true', () => {
    const { result } = renderHook(() => useSidebar(), {
      wrapper: SidebarProvider,
    });

    act(() => {
      result.current.toggleCollapse();
    });

    expect(result.current.isCollapsed).toBe(true);
    expect(localStorage.getItem(SIDEBAR_COLLAPSED_KEY)).toBe('true');
  });

  it('persists isCollapsed to localStorage when changed to false', () => {
    localStorage.setItem(SIDEBAR_COLLAPSED_KEY, 'true');

    const { result } = renderHook(() => useSidebar(), {
      wrapper: SidebarProvider,
    });

    act(() => {
      result.current.toggleCollapse();
    });

    expect(result.current.isCollapsed).toBe(false);
    expect(localStorage.getItem(SIDEBAR_COLLAPSED_KEY)).toBe('false');
  });

  it('toggleCollapse flips state from false to true', () => {
    const { result } = renderHook(() => useSidebar(), {
      wrapper: SidebarProvider,
    });

    expect(result.current.isCollapsed).toBe(false);

    act(() => {
      result.current.toggleCollapse();
    });

    expect(result.current.isCollapsed).toBe(true);
  });

  it('toggleCollapse flips state from true to false', () => {
    localStorage.setItem(SIDEBAR_COLLAPSED_KEY, 'true');

    const { result } = renderHook(() => useSidebar(), {
      wrapper: SidebarProvider,
    });

    expect(result.current.isCollapsed).toBe(true);

    act(() => {
      result.current.toggleCollapse();
    });

    expect(result.current.isCollapsed).toBe(false);
  });

  it('setMobileOpen updates mobile state to true', () => {
    const { result } = renderHook(() => useSidebar(), {
      wrapper: SidebarProvider,
    });

    expect(result.current.isMobileOpen).toBe(false);

    act(() => {
      result.current.setMobileOpen(true);
    });

    expect(result.current.isMobileOpen).toBe(true);
  });

  it('setMobileOpen updates mobile state to false', () => {
    const { result } = renderHook(() => useSidebar(), {
      wrapper: SidebarProvider,
    });

    act(() => {
      result.current.setMobileOpen(true);
    });

    expect(result.current.isMobileOpen).toBe(true);

    act(() => {
      result.current.setMobileOpen(false);
    });

    expect(result.current.isMobileOpen).toBe(false);
  });

  it('does not persist isMobileOpen to localStorage', () => {
    localStorage.setItem(SIDEBAR_COLLAPSED_KEY, 'false');

    const { result } = renderHook(() => useSidebar(), {
      wrapper: SidebarProvider,
    });

    act(() => {
      result.current.setMobileOpen(true);
    });

    // isMobileOpen change should NOT update localStorage key
    // The key should still be 'false' from initial setup
    expect(localStorage.getItem(SIDEBAR_COLLAPSED_KEY)).toBe('false');
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
    const { result } = renderHook(() => useSidebar(), {
      wrapper: SidebarProvider,
    });

    // First toggle
    act(() => {
      result.current.toggleCollapse();
    });
    expect(localStorage.getItem(SIDEBAR_COLLAPSED_KEY)).toBe('true');

    // Second toggle
    act(() => {
      result.current.toggleCollapse();
    });
    expect(localStorage.getItem(SIDEBAR_COLLAPSED_KEY)).toBe('false');

    // Third toggle
    act(() => {
      result.current.toggleCollapse();
    });
    expect(localStorage.getItem(SIDEBAR_COLLAPSED_KEY)).toBe('true');
  });
});
