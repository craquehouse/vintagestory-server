import { render, screen } from '@testing-library/react';
import { ThemeProvider } from './ThemeContext';

vi.mock('next-themes', () => ({
  ThemeProvider: ({ children, attribute, defaultTheme, enableSystem, disableTransitionOnChange }: any) => {
    // Verify props are passed correctly
    expect(attribute).toBe('class');
    expect(defaultTheme).toBe('system');
    expect(enableSystem).toBe(true);
    expect(disableTransitionOnChange).toBe(true);

    return <div data-testid="mock-theme-provider">{children}</div>;
  },
}));

describe('ThemeProvider', () => {
  it('wraps next-themes with correct props', () => {
    render(
      <ThemeProvider>
        <div>Test content</div>
      </ThemeProvider>
    );

    const mockProvider = screen.getByTestId('mock-theme-provider');
    expect(mockProvider).toBeInTheDocument();
  });

  it('renders children without errors', () => {
    render(
      <ThemeProvider>
        <div>Child component</div>
      </ThemeProvider>
    );

    expect(screen.getByText('Child component')).toBeInTheDocument();
  });

  it('sets attribute="class" on next-themes', () => {
    render(
      <ThemeProvider>
        <div>Test</div>
      </ThemeProvider>
    );

    // Mock verify called in the mock function above
    expect(screen.getByTestId('mock-theme-provider')).toBeInTheDocument();
  });

  it('sets defaultTheme="system" on next-themes', () => {
    render(
      <ThemeProvider>
        <div>Test</div>
      </ThemeProvider>
    );

    // Mock verify called in the mock function above
    expect(screen.getByTestId('mock-theme-provider')).toBeInTheDocument();
  });

  it('enables system preference detection', () => {
    render(
      <ThemeProvider>
        <div>Test</div>
      </ThemeProvider>
    );

    // Mock verify called in the mock function above
    expect(screen.getByTestId('mock-theme-provider')).toBeInTheDocument();
  });

  it('disables transition on theme change', () => {
    render(
      <ThemeProvider>
        <div>Test</div>
      </ThemeProvider>
    );

    // Mock verify called in the mock function above
    expect(screen.getByTestId('mock-theme-provider')).toBeInTheDocument();
  });
});
